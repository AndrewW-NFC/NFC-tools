/*
Purpose: Persist Settings sections with local feedback and ordered requests.
Dependencies: settings.html data-settings-section controls and /settings/save.
*/
(() => {
  const form = document.querySelector('.settings-form');
  if (!form) return;
  const summary = document.getElementById('settings-save-status');
  const sections = new Map();
  let sending = false;
  const retry = document.createElement('button');
  retry.type = 'button';
  retry.textContent = 'Retry unsaved changes';
  retry.hidden = true;
  summary.after(retry);

  function refreshSummary() {
    const values = [...sections.values()];
    const failed = values.filter(item => item.error);
    const pending = values.some(item => item.dirty);
    summary.textContent = failed.length ? `Not saved: ${failed.map(item => item.label).join(', ')}. Check the message in that section or retry.` :
      pending ? 'Saving changes… Wait before leaving.' : 'Saved. All settings are up to date.';
    summary.classList.toggle('error', failed.length > 0);
    retry.hidden = !failed.length;
  }

  form.querySelectorAll('[data-settings-section]').forEach(root => {
    const status = document.createElement('p');
    status.className = 'settings-section-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    root.append(status);
    sections.set(root.dataset.settingsSection, {
      root, status, label: root.querySelector('h2, h3')?.textContent || 'Settings',
      version: 0, dirty: false, ready: false, error: '', timer: null,
    });
  });

  function queue(item, delay) {
    item.version += 1;
    item.dirty = true;
    item.ready = false;
    item.error = '';
    item.status.textContent = 'Saving…';
    item.status.classList.remove('error');
    clearTimeout(item.timer);
    item.timer = setTimeout(() => { item.ready = true; pump(); }, delay);
    refreshSummary();
  }

  function edit(event) {
    const control = event.target;
    if (!control.name || control.disabled) return;
    const root = control.closest('[data-settings-section]');
    const item = sections.get(root?.dataset.settingsSection);
    if (!item) return;
    // Coverage confirmation belongs to a particular location, not later edits.
    if (item === sections.get('site') || ['ebird_hotspot_id', 'ebird_country_code', 'ebird_state_province', 'ebird_location_type', 'ebird_rarity_csv'].includes(control.name)) {
      const confirmation = form.querySelector('[name="ebird_rarity_confirm"]');
      if (confirmation) confirmation.checked = false;
    }
    queue(item, event.type === 'input' ? 600 : 0);
  }
  form.addEventListener('input', edit);
  form.addEventListener('change', edit);
  form.addEventListener('submit', event => {
    event.preventDefault();
    for (const item of sections.values()) if (item.dirty) queue(item, 0);
  });

  async function pump() {
    if (sending) return;
    const item = [...sections.values()].find(value => value.ready);
    if (!item) return;
    item.ready = false;
    const version = item.version;
    const controls = [...item.root.querySelectorAll('input, select, textarea')];
    const invalid = controls.find(control => !control.disabled && !control.checkValidity());
    if (invalid) {
      item.error = invalid.validationMessage || 'Complete this section with valid values.';
      item.status.textContent = `Not saved: ${item.error}`;
      item.status.classList.add('error');
      refreshSummary();
      pump();
      return;
    }
    const body = new FormData();
    body.append('_section', item.root.dataset.settingsSection);
    for (const control of controls) {
      if (!control.name || control.disabled || (['checkbox', 'radio'].includes(control.type) && !control.checked)) continue;
      if (control.type === 'file') {
        for (const file of control.files) body.append(control.name, file);
      } else if (control.multiple) {
        for (const option of control.selectedOptions) body.append(control.name, option.value);
      } else body.append(control.name, control.value);
    }
    sending = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body, headers: {'Accept': 'application/json'}});
      const isJson = response.headers.get('content-type')?.includes('application/json');
      const result = isJson ? await response.json() : {error: await response.text()};
      if (!response.ok || !result.ok) throw new Error(result.error || 'The server did not confirm saving.');
      if (version === item.version) {
        item.dirty = false;
        item.error = '';
        item.status.textContent = 'Saved';
        item.status.classList.remove('error');
        if (result.device_status) document.getElementById('device-selection-status').textContent = result.device_status;
        if (item === sections.get('site')) {
          const timezone = document.getElementById('tz');
          timezone.value = result.timezone;
          document.getElementById('tz-label').textContent = result.timezone;
          // Update schedule preview without generating another save.
          timezone.dispatchEvent(new Event('change'));
          const rarity = document.getElementById('ebird-rarity-enabled');
          if (rarity?.checked && result.rarity_enabled === false) {
            rarity.checked = false;
            document.getElementById('ebird-rarity-notice').textContent = 'Location changed. Confirm filter coverage before re-enabling reminders.';
          }
        }
        // Do not re-upload an accepted CSV on subsequent changes.
        for (const control of controls) if (control.type === 'file') control.value = '';
      }
    } catch (error) {
      if (version === item.version) {
        item.error = error.message;
        item.status.textContent = `Not saved: ${error.message} Your edits are still here.`;
        item.status.classList.add('error');
      }
    } finally {
      sending = false;
      refreshSummary();
      pump();
    }
  }

  function retryPending() {
    for (const item of sections.values()) if (item.dirty) queue(item, 0);
  }
  retry.addEventListener('click', retryPending);
  window.addEventListener('online', retryPending);
  window.addEventListener('beforeunload', event => {
    if (![...sections.values()].some(item => item.dirty)) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
