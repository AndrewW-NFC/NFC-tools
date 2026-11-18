/* Regression tests for autosave request ordering, failures, and uploads. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
  const requests = [], timers = new Map(), windowEvents = {}, elements = new Map();
  let timerId = 0;
  function element() {
    return {textContent: '', value: '', hidden: false, listeners: {},
      classList: {add() {}, remove() {}, toggle() {}}, setAttribute() {},
      addEventListener(name, fn) { this.listeners[name] = fn; },
      after(child) { this.sibling = child; }, dispatchEvent() {},
    };
  }
  const roots = new Map();
  for (const name of ['microphone', 'analyzers', 'ebird', 'site']) {
    const root = {dataset: {settingsSection: name}, controls: [],
      append(status) { this.status = status; },
      querySelector() { return {textContent: name}; },
      querySelectorAll() { return this.controls; },
    };
    roots.set(name, root);
  }
  function control(section, name, value = '', type = 'text') {
    const root = roots.get(section);
    const c = {...element(), name, value, type, checked: false, files: [], disabled: false,
      checkValidity() { return this.valid !== false; }, closest() { return root; }};
    root.controls.push(c);
    return c;
  }
  const mic = control('microphone', 'device_id', 'name:MacBook Air Microphone', 'select-one');
  const wing = control('analyzers', 'enabled_analyzers', 'wingbeats', 'checkbox');
  const file = control('ebird', 'ebird_rarity_csv', '', 'file');
  const confirm = control('ebird', 'ebird_rarity_confirm', 'on', 'checkbox');
  const lat = control('site', 'latitude', '42');
  elements.set('device-selection-status', element());
  const form = {...element(), action: '/settings/save', querySelectorAll: () => [...roots.values()],
    querySelector: () => confirm, append(child) { this.retry = child; }};
  const context = vm.createContext({
    document: {querySelector: () => form, createElement: element, getElementById: key => elements.get(key)},
    window: {addEventListener: (name, fn) => { windowEvents[name] = fn; }},
    FormData: class { constructor() {this.rows = [];} append(k, v) {this.rows.push([k, v]);} },
    setTimeout: fn => {timers.set(++timerId, fn); return timerId;}, clearTimeout: id => timers.delete(id),
    Event: function(type) {this.type = type;},
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({url, options, resolve, reject})),
  });
  vm.runInContext(fs.readFileSync('src/nfc_tools/web/static/settings_autosave.js', 'utf8'), context);
  function flushTimers() { const values = [...timers.values()]; timers.clear(); values.forEach(fn => fn()); }
  async function respond(index, data = {ok: true}, ok = true) {
    requests[index].resolve({ok, headers: {get: () => 'application/json'}, json: async () => data});
    await new Promise(setImmediate);
  }
  function edit(c, type = 'change') {form.listeners[type]({target: c, type});}
  return {requests, roots, mic, wing, file, confirm, lat, form, elements, windowEvents, edit, flushTimers, respond};
}

test('mic selection saves without submit and updates device status only after confirmation', async () => {
  const c = harness();
  c.mic.value = 'name:External Microphone'; c.edit(c.mic); c.flushTimers();
  assert.equal(c.requests.length, 1);
  assert.deepEqual(c.requests[0].options.body.rows.map(row => Array.from(row)), [['_section', 'microphone'], ['device_id', 'name:External Microphone']]);
  assert.match(c.roots.get('microphone').status.textContent, /Saving/);
  await c.respond(0, {ok: true, device_status: 'Input for the next recording: External Microphone.'});
  assert.match(c.roots.get('microphone').status.textContent, /^Saved/);
  assert.match(c.elements.get('device-selection-status').textContent, /External Microphone/);
});

test('rapid edits serialize and an old response cannot mark a new choice saved', async () => {
  const c = harness();
  c.edit(c.mic); c.flushTimers();
  c.mic.value = 'name:External Microphone'; c.edit(c.mic); c.flushTimers();
  assert.equal(c.requests.length, 1);
  await c.respond(0, {ok: true, device_status: 'Old input'});
  assert.match(c.roots.get('microphone').status.textContent, /Saving/);
  assert.equal(c.elements.get('device-selection-status').textContent, '');
  assert.equal(c.requests.length, 2);
  await c.respond(1, {ok: true, device_status: 'External Microphone'});
  assert.match(c.roots.get('microphone').status.textContent, /^Saved/);
});

test('network failure retains unsaved edits, warns on leaving, and retries', async () => {
  const c = harness(); c.edit(c.mic); c.flushTimers();
  c.requests[0].reject(new Error('Network offline')); await new Promise(setImmediate);
  assert.match(c.roots.get('microphone').status.textContent, /Not saved: Network offline/);
  let warned = false;
  c.windowEvents.beforeunload({preventDefault() {warned = true;}});
  assert.ok(warned);
  c.form.retry.listeners.click(); c.flushTimers(); await c.respond(1);
  warned = false; c.windowEvents.beforeunload({preventDefault() {warned = true;}});
  assert.equal(warned, false);
});

test('a failed section does not block another section or lose its error feedback', async () => {
  const c = harness(); c.file.files = ['bad.csv']; c.edit(c.file); c.flushTimers();
  c.edit(c.mic); c.flushTimers();
  await c.respond(0, {error: 'Confirm coverage'}, false);
  assert.equal(c.requests.length, 2);
  await c.respond(1);
  assert.match(c.roots.get('ebird').status.textContent, /Not saved: Confirm coverage/);
  assert.equal(c.form.retry.hidden, false);
  assert.equal(c.file.files[0], 'bad.csv');
});

test('checkbox clearing is sent as an empty section and text edits debounce', async () => {
  const c = harness(); c.edit(c.wing, 'input'); c.edit(c.wing, 'input');
  assert.equal(c.requests.length, 0); c.flushTimers();
  assert.equal(c.requests.length, 1);
  assert.equal(c.requests[0].options.body.rows.length, 1);
  await c.respond(0);
  assert.match(c.roots.get('analyzers').status.textContent, /^Saved/);
});

test('accepted uploads clear but newer edits are never cleared by an older response', async () => {
  const c = harness(); c.file.value = 'first.csv'; c.file.files = ['first.csv'];
  c.edit(c.file); c.flushTimers();
  c.file.value = 'second.csv'; c.file.files = ['second.csv']; c.edit(c.file); c.flushTimers();
  await c.respond(0); assert.equal(c.file.value, 'second.csv');
  await c.respond(1); assert.equal(c.file.value, '');
});

test('invalid local values keep unsaved feedback without blocking another section', async () => {
  const c = harness(); c.lat.valid = false; c.lat.validationMessage = 'Enter a valid latitude';
  c.edit(c.lat); c.flushTimers(); assert.equal(c.requests.length, 0);
  c.edit(c.mic); c.flushTimers(); await c.respond(0);
  assert.equal(c.form.retry.hidden, false);
  assert.match(c.roots.get('site').status.textContent, /valid latitude/);
});
