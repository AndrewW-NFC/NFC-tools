const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/nfc_tools/web/static/app.js', 'utf8');
const context = vm.createContext({});
vm.runInContext(source.slice(source.indexOf('  function analyzerName('), source.indexOf('  function renderStatus(')), context);

test('live log reports each analyzer against the full night despite truncated history', () => {
  const lines = context.statusLines({state: 'idle', analysis: {
    active: true, current_analyzer: 'wingbeats', history: [], queue: ['remaining.wav'],
    progress: {total: 17, analyzed: 2, left: 15, by_analyzer: {
      nighthawk: {done: 3, remaining: 14}, birdnet: {done: 2, remaining: 15}, wingbeats: {done: 2, remaining: 15}
    }}
  }});
  assert.equal(lines[0], 'Wingbeat detector is analyzing the recording.');
  assert.equal(lines[2], 'Nighthawk: done with 3 of 17 recordings; 14 remaining.');
  assert.equal(lines[3], 'BirdNET: done with 2 of 17 recordings; 15 remaining.');
  assert.equal(lines[4], 'Wingbeat detector: done with 2 of 17 recordings; 15 remaining.');
});

test('failed analysis remains incomplete and clip failures are distinguished', () => {
  let lines = context.statusLines({analysis: {progress: {total: 2, analyzed: 1, left: 1,
    by_analyzer: {birdnet: {done: 1, remaining: 1, failed: 1}}}}});
  assert.match(lines[0], /needs attention/);
  assert.match(lines[2], /1 failed \(included in remaining\)/);
  lines = context.statusLines({analysis: {progress: {total: 2, analyzed: 2, left: 0,
    by_analyzer: {birdnet: {done: 2, remaining: 0, clips_failed: 1}}}}});
  assert.match(lines[0], /clip exports need attention/);
});

test('missing checkpoint counts do not fabricate totals from short history', () => {
  const lines = context.statusLines({analysis: {active: true, queue: ['a.wav'], history: [{file:'b.wav'}],
    progress_error: 'Recording progress is unavailable.'}});
  assert.equal(lines.length, 2);
  assert.match(lines[1], /unavailable/);
});

vm.runInContext(source.slice(source.indexOf('  function activityLogMessage('), source.indexOf('  const newLogActivity =')), context);

test('activity entries sort by full timestamp and reverse insertion order for ties', () => {
  const rows = [
    {timestamp: '2026-10-21T09:00:00', event: 'analyzer_finished'},
    {timestamp: '2026-10-20T23:00:00'},
    {timestamp: '2026-10-21T09:00:00', event: 'sleep_prevention_stopped'},
    {date: '2026-10-21', time: '03-00-00'},
  ];
  const entries = context.activityLogEntries(rows);
  assert.equal(entries[0].row.event, 'sleep_prevention_stopped');
  assert.equal(entries[1].row.event, 'analyzer_finished');
  assert.equal(entries[2].timestamp, '2026-10-21T03:00:00');
  assert.equal(entries[3].row, rows[1]);
  assert.equal(rows[0].event, 'analyzer_finished');
});

test('analysis activity describes the action and filename without internal status labels', () => {
  for (const [analyzer, label] of [['birdnet', 'BirdNET analysis'], ['nighthawk', 'Nighthawk analysis'], ['wingbeats', 'Wing detection']]) {
    for (const state of ['started', 'finished']) {
      assert.equal(context.activityLogMessage({event: `analyzer_${state}`, analyzer, filename: '0300.wav'}),
        `${label} ${state} for 0300.wav.`);
    }
  }
  assert.equal(context.activityLogMessage({event: 'session_scheduled'}), 'Session scheduled and waiting for its start time.');
  assert.match(context.activityLogMessage({event: 'recording_stopped', message: 'Recording stopped (critical_battery).'}), /critically low/);
  assert.match(context.activityLogMessage({event: 'analyzer_failed', analyzer: 'birdnet', filename: '0300.wav', message: 'Model missing.'}), /0300.wav.*Model missing/);
  assert.equal(context.activityLogMessage({event: 'unknown_internal_code'}), 'Activity recorded.');
});

test('rendered activity has only time and message, with safely escaped filenames and keys', () => {
  const list = {children: [], scrollTop: 0, innerHTML: '', addEventListener() {}};
  const button = {hidden: true, addEventListener() {}};
  const renderContext = vm.createContext({sessionLogRows: list, downloadSessionLog: {},
    document: {getElementById: () => button}});
  vm.runInContext(source.slice(source.indexOf('  function escapeHtml('), source.indexOf('  function analyzerName(')), renderContext);
  vm.runInContext(source.slice(source.indexOf('  function sessionLogTime('), source.indexOf('  function applyStatus(')), renderContext);
  renderContext.renderSessionLog({session_log: [
    {timestamp: '2026-10-21T09:00:00', event: 'analyzer_finished', analyzer: 'wingbeats', filename: 'bird"<test>.wav', details: {secret: 'raw metadata'}},
    {timestamp: '2026-10-21T09:00:00', event: 'sleep_prevention_stopped'},
  ]});
  assert.ok(list.innerHTML.indexOf('This computer can sleep again.') < list.innerHTML.indexOf('Wing detection finished'));
  assert.match(list.innerHTML, /bird&quot;&lt;test&gt;.wav/);
  assert.doesNotMatch(list.innerHTML, /<strong>|<details>|<th/);
  assert.doesNotMatch(list.innerHTML.replace(/<[^>]*>/g, ''), /raw metadata/);
  assert.equal((list.innerHTML.match(/<time /g) || []).length, 2);
  assert.equal((list.innerHTML.match(/<div>/g) || []).length, 2);
});
