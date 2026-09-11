// Run with: node --test tests/test_import_timeline.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function controller() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '0', checked: false, disabled: false, textContent: '',
      classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {},
      querySelector() { return null; }, checkValidity() { return true; }
    });
    return elements.get(id);
  }
  const context = vm.createContext({ document: { getElementById: element, querySelector() { return null; } } });
  const source = fs.readFileSync('src/nfc_tools/web/static/import_page.js', 'utf8');
  const end = source.indexOf('  byId("start-import-run")?.addEventListener');
  vm.runInContext(source.slice(0, end) + '\nglobalThis.api = { state, addSecondsToInputValue, buildTimelineEntries, applyTimeShift, confirmTimeline, confirmStoragePlan };})();', context);
  return { ...context.api, element };
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
