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
  assert.equal(lines[1], 'Nighthawk: done with 3 of 17 recordings; 14 remaining.');
  assert.equal(lines[2], 'BirdNET: done with 2 of 17 recordings; 15 remaining.');
  assert.equal(lines[3], 'Wingbeat detector: done with 2 of 17 recordings; 15 remaining.');
});

test('failed analysis remains incomplete and clip failures are distinguished', () => {
  let lines = context.statusLines({analysis: {progress: {total: 2, analyzed: 1, left: 1,
    by_analyzer: {birdnet: {done: 1, remaining: 1, failed: 1}}}}});
  assert.match(lines[0], /needs attention/);
  assert.match(lines[1], /1 failed \(included in remaining\)/);
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
