(() => {
  document.querySelectorAll('.ebird-options').forEach(root => {
    const prefix = root.dataset.prefix;
    const field = key => document.getElementById(`${prefix}ebird-${key}`);
    const enabled = field('export-enabled'), kind = field('location-type'), select = field('hotspot-id');
    const refresh = () => {
      root.querySelector('[data-ebird-details]').hidden = !enabled.checked;
      root.querySelector('[data-hotspot-controls]').hidden = kind.value !== 'hotspot';
      root.querySelector('[data-personal-help]').hidden = kind.value === 'hotspot';
    };
    root.addEventListener('change', refresh);
    root.addEventListener('ebird-refresh', refresh);
    refresh();
    const keyInput = root.querySelector('[data-api-key]');
    const keyStatus = root.querySelector('[data-api-key-status]');
    const forgetKey = root.querySelector('[data-api-key-forget]');
    async function refreshKeyStatus() {
      try {
        const response = await fetch('/api/ebird/key', {cache:'no-store'});
        if (!response.ok) throw new Error();
        const data = await response.json();
        keyStatus.textContent = data.saved ? 'API key saved on this computer for future runs. Leave the field blank to reuse it.' :
          data.environment ? 'Using the API key configured on this computer through EBIRD_API_KEY.' : 'No API key saved yet.';
        forgetKey.hidden = !data.saved;
      } catch (_) { keyStatus.textContent = 'Could not check saved API key status.'; }
    }
    refreshKeyStatus();
    forgetKey.addEventListener('click', async () => {
      forgetKey.disabled = true;
      try {
        const response = await fetch('/api/ebird/key', {method:'DELETE'});
        if (!response.ok) throw new Error();
        keyInput.value = '';
        await refreshKeyStatus();
      } catch (_) { keyStatus.textContent = 'Could not forget the saved API key. Try again.'; }
      finally { forgetKey.disabled = false; }
    });
    let results = [];
    select.addEventListener('change', () => {
      const row = results.find(item => item.locId === select.value);
      if (!row) return;
      field('country-code').value = row.countryCode || '';
      field('state-province').value = (row.subnational1Code || '').split('-').slice(1).join('-');
      field('state-province').dispatchEvent(new Event('input', {bubbles:true}));
    });
    root.querySelector('[data-hotspot-search]').addEventListener('click', async event => {
      const button = event.currentTarget, status = root.querySelector('[data-hotspot-status]');
      const coordinate = name => prefix ? document.getElementById(`${prefix}${name}`).value : document.querySelector(`[name="${name}"]`).value;
      button.disabled = true; status.textContent = 'Searching eBird…';
      try {
        const response = await fetch('/api/ebird/hotspots', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({latitude:coordinate('latitude'),longitude:coordinate('longitude'),api_key:keyInput.value})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Search failed.');
        keyInput.value = '';
        await refreshKeyStatus();
        results = data.hotspots;
        select.replaceChildren(new Option('Select a search result', ''));
        results.forEach(row => select.add(new Option(`${row.locName} (${row.locId})`, row.locId)));
        select.dispatchEvent(new Event('change', {bubbles:true}));
        select.dispatchEvent(new Event('input', {bubbles:true}));
        status.textContent = results.length ? `${results.length} public hotspots found. Select one above.` : 'No public hotspots found nearby. You can choose a personal location in eBird instead.';
      } catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    });
  });
})();
