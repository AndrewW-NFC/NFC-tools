const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function controller({saved = false, failSearch = false} = {}) {
  const elements = new Map();
  function element(key) {
    if (!elements.has(key)) elements.set(key, {
      value: '', checked: true, hidden: false, textContent: '', disabled: false,
      listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
      replaceChildren() {}, add() {}, dispatchEvent() {},
    });
    return elements.get(key);
  }
  element('ebird-location-type').value = 'hotspot';
  const root = {dataset: {prefix: ''}, querySelector: element, addEventListener() {}};
  const requests = [];
  const context = vm.createContext({
    document: {
      querySelectorAll: () => [root], getElementById: element,
      querySelector: key => ({value: key.includes('latitude') ? '42' : '-71'}),
    },
    Option: function() {}, Event: function() {},
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      if (url === '/api/ebird/key') {
        if (options.method === 'DELETE') saved = false;
        return {ok: true, json: async () => ({saved, environment: false})};
      }
      if (failSearch) return {ok: false, json: async () => ({error: 'Key rejected'})};
      if (JSON.parse(options.body).api_key) saved = true;
      return {ok: true, json: async () => ({hotspots: []})};
    },
  });
  vm.runInContext(fs.readFileSync('src/nfc_tools/web/static/ebird_location.js', 'utf8'), context);
  await new Promise(setImmediate);
  return {element, requests};
}

test('saved-key status is visible on a fresh page and blank searches reuse it', async () => {
  const c = await controller({saved: true});
  assert.match(c.element('[data-api-key-status]').textContent, /saved on this computer/);
  assert.equal(c.element('[data-api-key-forget]').hidden, false);
  assert.equal(c.element('[data-api-key]').value, '');
  const button = c.element('[data-hotspot-search]');
  await button.listeners.click({currentTarget: button});
  const request = c.requests.find(r => r.url === '/api/ebird/hotspots');
  assert.equal(JSON.parse(request.options.body).api_key, '');
});

test('successful search clears the entered key and forget updates saved status', async () => {
  const c = await controller();
  c.element('[data-api-key]').value = 'new-key';
  const button = c.element('[data-hotspot-search]');
  await button.listeners.click({currentTarget: button});
  assert.equal(c.element('[data-api-key]').value, '');
  assert.match(c.element('[data-api-key-status]').textContent, /saved on this computer/);
  await c.element('[data-api-key-forget]').listeners.click();
  assert.equal(c.element('[data-api-key-forget]').hidden, true);
  assert.match(c.element('[data-api-key-status]').textContent, /No API key saved/);
});

test('failed search retains input for correction and never claims to have saved it', async () => {
  const c = await controller({failSearch: true});
  c.element('[data-api-key]').value = 'bad-key';
  const button = c.element('[data-hotspot-search]');
  await button.listeners.click({currentTarget: button});
  assert.equal(c.element('[data-api-key]').value, 'bad-key');
  assert.equal(c.element('[data-hotspot-status]').textContent, 'Key rejected');
  assert.match(c.element('[data-api-key-status]').textContent, /No API key saved/);
  assert.equal(button.disabled, false);
});
