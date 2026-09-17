(() => {
  const select = document.getElementById('night-select');
  const report = document.getElementById('night-report');
  const message = document.getElementById('night-message');
  const recover = document.getElementById('night-recover');
  let timer;
  const duration = n => n == null ? 'Unknown' : `${(n / 3600).toFixed(2)} hours`;
  function line(text, tag = 'p') {
    const node = document.createElement(tag);
    node.textContent = text;
    report.appendChild(node);
  }
  async function refresh() {
    clearTimeout(timer);
    if (!select.value) { message.textContent = 'No saved nights found in the recording folder.'; return; }
    recover.disabled = true;
    try {
      const response = await fetch(`/api/nights/${select.value}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not load night.');
      report.replaceChildren();
      line(`Recording coverage: ${data.coverage}`, 'h2');
      line(`Expected: ${duration(data.expected_seconds)} · Recorded audio: ${duration(data.recorded_seconds)} · Missing within expected window: ${data.expected_seconds == null ? 'Unknown' : duration(data.missing_seconds)}`);
      if (data.coverage === 'unknown') line('The original recording window was not saved. Completeness cannot be established for this night.');
      for (const gap of data.gaps) line(`Gap: ${gap.start} to ${gap.end} (${Math.round(gap.seconds)} seconds)`);
      line(`${data.pending_files} recording(s) need analysis or clip export; ${data.invalid_files} unreadable recording(s).`, 'h2');
      line(`eBird export: ${data.exports.status}. ${data.exports.message || ''}`);
      if (data.pending_files || data.invalid_files) line('Exports may be partial until the unfinished or unreadable recordings are resolved.');
      for (const file of data.files) {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = `${file.filename} — ${!file.valid ? 'Unreadable' : file.pending ? 'Unfinished work' : 'Analysis finished'}`;
        details.appendChild(summary);
        const text = document.createElement('p');
        text.textContent = `${file.message} ${Object.entries(file.analyzers).map(([name, s]) => `${name}: analysis ${s.analysis || 'pending'}, clips ${s.clips || 'pending'}${s.error ? ': ' + s.error : ''}`).join('; ')}`;
        details.appendChild(text);
        report.appendChild(details);
      }
      message.textContent = data.recovery.night === select.value ? data.recovery.message : '';
      if (data.busy) message.textContent += ' Recording, analysis, or import is active. Recovery is unavailable until it finishes.';
      recover.disabled = data.busy || !data.files.some(f => f.valid);
      if (data.busy) timer = setTimeout(refresh, 5000);
    } catch (error) { message.textContent = error.message; }
  }
  recover.addEventListener('click', async () => {
    recover.disabled = true;
    try {
      const response = await fetch(`/api/nights/${select.value}/recover`, {method: 'POST'});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Recovery could not start.');
      await refresh();
    } catch (error) { message.textContent = error.message; recover.disabled = false; }
  });
  select.addEventListener('change', refresh);
  document.getElementById('night-refresh').addEventListener('click', refresh);
  refresh();
})();
