// Run with: node --test tests/test_import_timeline.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function controller(options = {}) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '0', checked: ['import-birdnet-enabled', 'import-nighthawk-enabled'].includes(id), disabled: false, textContent: '', dataset: {},
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
    FormData,
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
  vm.runInContext(source.slice(0, end) + '\nglobalThis.api = { state, addSecondsToInputValue, buildTimelineEntries, applyTimeShift, confirmTimeline, confirmStoragePlan, invalidateTimelineConfirmation, detectedStartToInputValue, renderRun, pollRun, rememberLocation, restoreLocation, restoreRunPlan, syncSetupUI, renderOutputTree, initFolderPicker, resetReviewResults, changeAnalyzerSelection, selectedAnalyzers };})();', context);
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
  c.element('import-wingbeats-enabled').checked = true;
  c.element('timeline-responsibility-check').checked = true;
  c.confirmTimeline();
  c.confirmStoragePlan();

  assert.equal(c.element('start-import-run').disabled, false);
  await c.element('start-import-run').click();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, '/import-recordings/start');
  const body = JSON.parse(requests[0].options.body);
  assert.deepEqual(body.enabled_analyzers, ['birdnet', 'nighthawk', 'wingbeats']);
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

test('checking for a saved run does not block new folder choices', () => {
  const c = controller();
  c.state.recovering = true;
  c.state.scan = null;
  c.state.job = null;
  c.element('import-setup-fields').disabled = true;

  c.syncSetupUI();

  assert.equal(c.element('import-setup-fields').disabled, false);
});

test('run monitor shows the expected output folders', () => {
  const c = controller();
  c.saved.set('nfc-import-run', JSON.stringify({ output: '/processed', id: 'test' }));
  c.renderRun({ id: 'test', state: 'complete', message: 'Done', file_index: 1, total_files: 1,
    output: '/processed/2026-08-08', free_bytes: 1024, part_index: 1, parts_in_file: 1,
    file_duration: 10, file_completed_seconds: 10 });

  assert.equal(c.element('import-output-summary').hidden, false);
  assert.match(c.element('import-output-summary').innerHTML, /eBird checklists/);
  assert.match(c.element('import-output-summary').innerHTML, /Manifest/);
  assert.equal(c.element('import-setup-fields').disabled, false);
  assert.equal(c.state.planSubmitted, false);
  assert.equal(c.saved.get('nfc-import-run'), undefined);
  assert.match(c.element('import-setup-status').textContent, /Import complete/);
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

test('unrestorable recovered run is ignored and unlocks a new import', async () => {
  const c = controller({
    fetch: async url => {
      if (String(url).includes('/plan')) {
        return { ok: false, json: async () => ({ ok: false, error: 'Missing checkpoint.' }) };
      }
      return { ok: true, json: async () => ({ ok: true, job: {
        id: 'old-job', state: 'complete', message: 'Done', file_index: 1, total_files: 1,
        output: '/out', current_file: 'one.wav', current_analyzer: null,
        completed_segments: 1, part_index: 1, parts_in_file: 1,
        file_duration: 60, file_completed_seconds: 60
      } }) };
    }
  });
  c.state.recovering = true;

  await c.pollRun();

  assert.equal(c.state.job, null);
  assert.equal(c.state.planSubmitted, false);
  assert.equal(c.state.ignoredJobId, 'old-job');
  assert.equal(c.element('import-setup-fields').disabled, false);
  assert.match(c.element('import-run-status').textContent, /could not be restored/);
});

test('restored run plan keeps the saved eBird hotspot code', async () => {
  const c = controller({
    fetch: async () => ({ ok: true, json: async () => ({ ok: true, plan: {
      id: 'job-with-hotspot', source: '/src', output: '/out',
      config: {
        site: {
          name: 'Mt. Vernon St.', latitude: 42.4142547, longitude: -71.1729537,
          timezone: 'America/New_York', ebird_state_province: 'MA', ebird_hotspot_id: 'L16353129'
        },
        analyzers: { enabled: ['birdnet', 'nighthawk', 'wingbeats'], birdnet_min_conf: 0.5, birdnet_year_round: false }
      },
      files: [{ relative_path: 'one.wav', start: '2026-09-13T23:00:00-04:00', duration: 60 }]
    } }) })
  });

  await c.restoreLocation();
  await c.restoreRunPlan({ id: 'job-with-hotspot' });

  assert.equal(c.element('import-ebird-hotspot-id').value, 'L16353129');
  assert.equal(c.element('import-wingbeats-enabled').checked, true);
  assert.match(c.element('planned-output-tree').textContent, /wingbeats/);
  assert.match(c.element('import-analyzer-summary').textContent, /Possible wingbeats \(experimental\)/);
});


test('archive preview includes only enabled analyzers and shared review content', () => {
  const c = controller();
  c.element('import-birdnet-enabled').checked = false;
  c.element('import-nighthawk-enabled').checked = true;
  c.element('import-wingbeats-enabled').checked = true;
  c.renderOutputTree();
  let tree = c.element('planned-output-tree').textContent;
  assert.match(tree, /nighthawk\//);
  assert.match(tree, /wingbeats\//);
  assert.doesNotMatch(tree, /birdnet\//);
  assert.match(tree, /clips\/\n      HH-MM-SS\//);
  assert.match(tree, /environmental_conditions.csv/);
  assert.match(tree, /analysis_progress.json/);
  c.element('import-wingbeats-enabled').checked = false;
  c.renderOutputTree();
  assert.doesNotMatch(c.element('planned-output-tree').textContent, /wingbeats\//);
});


for (const status of ['paused', 'failed']) {
  test(`${status} import allows a folder choice to start a new plan`, async () => {
    const requests = [];
    const c = controller({ fetch: async (url, options) => {
      requests.push(url);
      return { json: async () => ({ ok: true, path: '/new-source' }) };
    } });
    c.state.job = { id: 'saved-job', state: status };
    c.state.planSubmitted = true;
    c.saved.set('nfc-import-run', JSON.stringify({ id: 'saved-job', output: '/old' }));
    c.syncSetupUI();
    assert.equal(c.element('import-setup-fields').disabled, true);
    assert.equal(c.element('choose-import-source-folder').disabled, false);
    assert.equal(c.element('choose-import-output-folder').disabled, false);
    c.initFolderPicker('source', '/choose-source', 'current_source_folder');
    await c.element('choose-import-source-folder').click();
    assert.deepEqual(requests, ['/choose-source']);
    assert.equal(c.state.ignoredJobId, 'saved-job');
    assert.equal(c.state.job, null);
    assert.equal(c.state.planSubmitted, false);
    assert.equal(c.element('import-source-folder').value, '/new-source');
    assert.equal(c.element('import-setup-fields').disabled, false);
  });
}

for (const result of ['cancel', 'error']) {
  test(`folder chooser ${result} preserves a paused plan and restores buttons`, async () => {
    const c = controller({ fetch: async () => {
      if (result === 'error') throw new Error('Picker unavailable');
      return { json: async () => ({ cancelled: true }) };
    } });
    c.state.job = { id: 'saved-job', state: 'paused' };
    c.state.planSubmitted = true;
    c.initFolderPicker('output', '/choose-output', 'current_output_folder');
    await c.element('choose-import-output-folder').click();
    assert.equal(c.state.job.id, 'saved-job');
    assert.equal(c.state.planSubmitted, true);
    assert.equal(c.state.choosingFolder, false);
    assert.equal(c.element('choose-import-output-folder').disabled, false);
  });
}

test('folder buttons remain locked during running, scanning, submission and a pending chooser', async () => {
  for (const mode of ['running', 'scanning', 'submitting', 'choosingFolder']) {
    const c = controller({ fetch: async () => { throw new Error('Must not call picker'); } });
    if (mode === 'running') c.state.job = { state: 'running' };
    else c.state[mode] = true;
    c.syncSetupUI();
    assert.equal(c.element('choose-import-source-folder').disabled, true);
    c.initFolderPicker('source', '/choose-source', 'current_source_folder');
    await c.element('choose-import-source-folder').click();
    assert.equal(c.element('import-source-folder-status').textContent, '');
  }
});


for (const phase of ['status', 'plan']) {
  test(`late recovery ${phase} response cannot replace a freshly scanned timeline`, async () => {
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    let planRequested;
    const planStarted = new Promise(resolve => { planRequested = resolve; });
    const oldJob = { id: 'old-run', state: 'paused', output: '/old' };
    const c = controller({ fetch: async url => {
      if (String(url).includes('/plan?')) {
        planRequested();
        if (phase === 'plan') await pending;
        return { json: async () => ({ ok: true, plan: {
          source: '/old', output: '/old-output',
          config: { site: { name: 'Old', latitude: 42, longitude: -71, timezone: 'America/New_York' },
            analyzers: { enabled: ['birdnet'] } },
          files: [{ relative_path: 'old.wav', start: '2026-08-22T20:00:00', duration: 60 }]
        } }) };
      }
      if (phase === 'status') await pending;
      return { json: async () => ({ ok: true, job: oldJob }) };
    } });
    const recovery = c.pollRun();
    if (phase === 'plan') await planStarted;
    // Folder selection and a fresh scan complete while recovery is in flight.
    c.resetReviewResults();
    c.state.scan = { source: { audio_count: 1 } };
    c.state.timelineEntries = c.buildTimelineEntries([
      { relative_path: 'new.wav', detected_start: '2026-09-18 23:00:00', duration_seconds: 60 }
    ]);
    release();
    await recovery;
    assert.equal(c.state.job, null);
    assert.equal(c.state.planSubmitted, false);
    assert.equal(c.element('import-setup-fields').disabled, false);
    assert.equal(c.state.timelineEntries[0].file.relative_path, 'new.wav');
    c.element('import-shift-hours').value = '1';
    c.element('import-shift-direction').value = 'forward';
    c.applyTimeShift();
    assert.equal(c.state.timelineEntries[0].value, '2026-09-19T00:00:00');
    c.element('timeline-responsibility-check').checked = true;
    c.confirmTimeline();
    assert.equal(c.state.timelineConfirmed, true);
    await c.pollRun();
    assert.equal(c.state.timelineConfirmed, true);
    assert.equal(c.state.job, null);
  });
}


test('analyzer step requires a selection and changes invalidate confirmations', () => {
  const c = controller();
  c.state.scan = { source: { audio_count: 1 } };
  c.state.timelineEntries = c.buildTimelineEntries([{ detected_start: '2026-09-18 23:00:00' }]);
  c.element('timeline-responsibility-check').checked = true;
  c.confirmTimeline(); c.confirmStoragePlan();
  c.element('import-birdnet-enabled').checked = false;
  c.element('import-nighthawk-enabled').checked = false;
  c.changeAnalyzerSelection();
  assert.equal(c.state.timelineConfirmed, false);
  assert.equal(c.state.storageConfirmed, false);
  assert.equal(c.element('choose-import-source-folder').disabled, true);
  assert.equal(c.element('start-import-run').disabled, true);
  assert.match(c.element('import-next-action').textContent, /choose at least one analyzer/);
  c.element('import-wingbeats-enabled').checked = true;
  c.changeAnalyzerSelection();
  assert.deepEqual(Array.from(c.selectedAnalyzers()), ['wingbeats']);
  assert.equal(c.element('choose-import-source-folder').disabled, false);
  assert.equal(c.state.timelineEntries.length, 1);
});
