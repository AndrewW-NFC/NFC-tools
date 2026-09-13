// Run with: node --test tests/test_import_timeline.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function controller(options = {}) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '0', checked: false, disabled: false, textContent: '',
      classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {},
      listeners: {},
      addEventListener(event, handler) { this.listeners[event] = handler; },
      click() { return this.listeners.click?.({ target: this }); },
      querySelector() { return null; }, querySelectorAll() { return []; },
      checkValidity() { return true; }
    });
    return elements.get(id);
  }
  const saved = new Map();
  const context = vm.createContext({
    document: { getElementById: element, querySelector() { return null; } },
    fetch: options.fetch || (async () => ({ ok: true, json: async () => ({ ok: true, job: null }) })),
    setTimeout() {},
    URLSearchParams,
    localStorage: {
      getItem: key => saved.get(key),
      setItem: (key, value) => saved.set(key, value),
      removeItem: key => saved.delete(key)
    },
    crypto: options.crypto || { randomUUID: () => '11111111-1111-4111-8111-111111111111' }
  });
  const source = fs.readFileSync('src/nfc_tools/web/static/import_page.js', 'utf8');
  const end = options.includeStartListener
    ? source.indexOf('  byId("pause-import-run")?.addEventListener')
    : source.indexOf('  byId("start-import-run")?.addEventListener');
  vm.runInContext(source.slice(0, end) + '\nglobalThis.api = { state, addSecondsToInputValue, buildTimelineEntries, applyTimeShift, confirmTimeline, confirmStoragePlan, invalidateTimelineConfirmation, detectedStartToInputValue, renderRun, pollRun, rememberLocation, restoreLocation };})();', context);
  return { ...context.api, element, saved };
}

for (const [start, seconds, expected] of [
  ['2026-08-08T23:30:00', 14400, '2026-08-09T03:30:00'],
  ['2026-09-01T01:30:00', -14400, '2026-08-31T21:30:00'],
  ['2026-12-31T23:30:15', 5400, '2027-01-01T01:00:15'],
  ['2024-03-01T00:30:00', -3600, '2024-02-29T23:30:00'],
  ['2025-03-01T00:30:00', -3600, '2025-02-28T23:30:00'],
  ['2026-03-08T01:30:00', 7200, '2026-03-08T03:30:00'],
  ['2026-11-01T00:30:00', 7200, '2026-11-01T02:30:00']
]) test(`clock correction ${start} ${seconds}`, () => {
  assert.equal(controller().addSecondsToInputValue(start, seconds), expected);
});

test('bulk correction preserves manual/missing rows, replaces offsets, restores and invalidates confirmation', () => {
  const c = controller();
  c.state.timelineEntries = c.buildTimelineEntries([
    { detected_start: '2026-08-08 23:30:00', duration_seconds: 3600 },
    { duration_seconds: 3600 },
    { detected_start: '2026-08-09 02:30:00' },
    {}
  ]);
  c.state.timelineEntries[2].manual = true;
  c.state.timelineEntries[2].value = '2026-08-10T05:00:00';
  c.state.timelineConfirmed = true;
  c.element('timeline-responsibility-check').checked = true;
  c.element('import-shift-hours').value = '4';
  c.element('import-shift-direction').value = 'forward';
  c.applyTimeShift();
  const values = () => Array.from(c.state.timelineEntries, e => e.value);
  assert.deepEqual(values(), ['2026-08-09T03:30:00', '2026-08-09T04:30:00', '2026-08-10T05:00:00', '']);
  assert.equal(c.state.timelineConfirmed, false);
  assert.equal(c.element('timeline-responsibility-check').checked, false);
  assert.equal(c.element('confirm-import-storage').disabled, true);
  c.applyTimeShift();
  assert.equal(values()[0], '2026-08-09T03:30:00');
  c.element('import-shift-hours').value = '0';
  c.applyTimeShift();
  assert.equal(values()[0], '2026-08-08T23:30:00');
});

test('unknown duration stops sequential inference', () => {
  const entries = controller().buildTimelineEntries([
    { detected_start: '2026-08-08 23:30:00', duration_seconds: 3600 }, {}, {}
  ]);
  assert.equal(entries[1].value, '2026-08-09T00:30:00');
  assert.equal(entries[2].value, '');
});

test('24-hour input accepts midnight and rejects invalid calendar values and AM/PM', () => {
  const c = controller();
  assert.equal(c.detectedStartToInputValue('2026-08-09 03:30:00'), '2026-08-09T03:30:00');
  assert.equal(c.detectedStartToInputValue('2026-08-09 00:00'), '2026-08-09T00:00:00');
  for (const invalid of ['2026-02-29 03:30:00', '2026-08-09 24:00:00', '2026-08-09 03:30 AM']) {
    assert.equal(c.detectedStartToInputValue(invalid), null);
  }
});

test('confirmations disable their buttons, clear stale guidance, and invalidate on edits', () => {
  const c = controller();
  c.state.scan = { source: { audio_count: 1 } };
  c.state.timelineEntries = c.buildTimelineEntries([{ detected_start: '2026-08-09 03:30:00' }]);
  c.element('timeline-responsibility-check').checked = true;
  c.confirmTimeline();
  assert.equal(c.element('confirm-import-timeline').disabled, true);
  assert.equal(c.element('import-session-status').textContent, 'Session details and timeline confirmed.');
  c.confirmStoragePlan();
  assert.equal(c.element('confirm-import-storage').disabled, true);
  assert.equal(c.element('start-import-run').disabled, false);
  c.invalidateTimelineConfirmation();
  assert.equal(c.state.storageConfirmed, false);
  assert.equal(c.element('start-import-run').disabled, true);
});

test('start button click posts the confirmed import plan', async () => {
  const requests = [];
  const c = controller({
    includeStartListener: true,
    fetch: async (url, options) => {
      requests.push({ url, options });
      return { ok: true, json: async () => ({ ok: true, job: {
        id: '11111111-1111-4111-8111-111111111111', state: 'running', message: 'Starting import...',
        output: '/out', file_index: 0, completed_segments: 0, total_files: 1, current_file: 'one.wav',
        current_analyzer: null, free_bytes: 1024, part_index: 1, parts_in_file: 1,
        file_duration: 60, file_completed_seconds: 0
      } }) };
    }
  });
  c.state.scan = { source: { audio_count: 1, path: '/src' }, output: { path: '/out' } };
  c.state.timelineEntries = c.buildTimelineEntries([
    { relative_path: 'one.wav', detected_start: '2026-08-09 03:30:00',
      duration_seconds: 60, duration_display: '60 seconds', size_bytes: 123, mtime_ns: 456 }
  ]);
  c.element('import-site-name').value = 'Merrill Lake Sanctuary';
  c.element('import-latitude').value = '45.953';
  c.element('import-longitude').value = '-122.311';
  c.element('import-timezone').value = 'America/Los_Angeles';
  c.element('import-ebird-state-province').value = 'US-WA';
  c.element('import-ebird-hotspot-id').value = 'L5129545';
  c.element('import-ambiguous-time').value = 'earlier';
  c.element('timeline-responsibility-check').checked = true;
  c.confirmTimeline();
  c.confirmStoragePlan();

  assert.equal(c.element('start-import-run').disabled, false);
  await c.element('start-import-run').click();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, '/import-recordings/start');
  const body = JSON.parse(requests[0].options.body);
  assert.equal(body.source_folder, '/src');
  assert.equal(body.output_folder, '/out');
  assert.equal(body.ebird_state_province, 'WA');
  assert.equal(body.ebird_hotspot_id, 'L5129545');
  assert.equal(body.files[0].relative_path, 'one.wav');
  assert.equal(body.files[0].start, '2026-08-09T03:30:00');
});

test('running or paused jobs lock all setup controls and clock corrections', () => {
  const c = controller();
  c.state.timelineEntries = c.buildTimelineEntries([{ detected_start: '2026-08-09 03:30:00' }]);
  c.renderRun({ id: 'test', state: 'running', message: 'nighthawk is running', file_index: 0, total_files: 1,
    output: '/test', free_bytes: 1024, part_index: 1, parts_in_file: 2, file_duration: 10, file_completed_seconds: 0 });
  assert.equal(c.element('import-setup-fields').disabled, true);
  assert.equal(c.element('import-location-map').inert, true);
  assert.match(c.element('import-run-status').textContent, /Nighthawk/);
  c.element('import-shift-hours').value = '4';
  c.applyTimeShift();
  assert.equal(c.state.timelineEntries[0].value, '2026-08-09T03:30:00');
  c.invalidateTimelineConfirmation();
  assert.equal(c.state.timelineConfirmed, true);
});

test('run monitor shows the expected output folders', () => {
  const c = controller();
  c.renderRun({ id: 'test', state: 'complete', message: 'Done', file_index: 1, total_files: 1,
    output: '/processed/2026-08-08', free_bytes: 1024, part_index: 1, parts_in_file: 1,
    file_duration: 10, file_completed_seconds: 10 });

  assert.equal(c.element('import-output-summary').hidden, false);
  assert.match(c.element('import-output-summary').innerHTML, /eBird checklists/);
  assert.match(c.element('import-output-summary').innerHTML, /Manifest/);
});

test('import location is remembered independently of Settings', () => {
  const c = controller();
  c.element('import-site-name').value = 'Test location';
  c.element('import-latitude').value = '42';
  c.element('import-longitude').value = '-71';
  c.element('import-timezone').value = 'America/New_York';
  c.element('import-ebird-state-province').value = 'US-MA';
  c.element('import-ebird-hotspot-id').value = 'L5129545';
  c.rememberLocation();
  c.element('import-site-name').value = 'Settings default';
  c.element('import-ebird-state-province').value = '';
  c.element('import-ebird-hotspot-id').value = '';
  c.restoreLocation();
  assert.equal(c.element('import-site-name').value, 'Test location');
  assert.equal(c.element('import-timezone').value, 'America/New_York');
  assert.equal(c.element('import-ebird-state-province').value, 'US-MA');
  assert.equal(c.element('import-ebird-hotspot-id').value, '');
});

test('stale saved run is forgotten so a new import can start', async () => {
  const c = controller({
    fetch: async () => ({ ok: false, json: async () => ({ ok: false, error: 'Checkpoint not found.' }) })
  });
  c.saved.set('nfc-import-run', JSON.stringify({ output: '/missing', id: 'c0cbfd6c-366b-44d2-9ebc-8659763ea4c4' }));
  c.state.recovering = true;
  await c.pollRun();
  assert.equal(c.saved.get('nfc-import-run'), undefined);
  assert.equal(c.state.planSubmitted, false);
  assert.match(c.element('import-run-status').textContent, /Previous saved run was not found/);
});
