(() => {
  const select = document.getElementById('night-select');
  const report = document.getElementById('night-report');
  const message = document.getElementById('night-message');
  const recover = document.getElementById('night-recover');
  let timer;
  const precipitationButton = document.getElementById('precipitation-refresh');
  const precipitationAttempted = new Set();
  const duration = n => n == null ? 'Unknown' : `${(n / 3600).toFixed(2)} hours`;
  function line(text, tag = 'p') {
    const node = document.createElement(tag);
    node.textContent = text;
    report.appendChild(node);
  }
  async function refresh() {
    clearTimeout(timer);
    if (!select.value) { message.textContent = 'No saved nights found in the recording folder.'; return; }
    const selectedNight = select.value;
    recover.disabled = true;
    try {
      const response = await fetch(`/api/nights/${selectedNight}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not load night.');
      if (selectedNight !== select.value) return;
      if ((!data.precipitation || data.precipitation.status !== 'complete') && !precipitationAttempted.has(selectedNight)) {
        precipitationAttempted.add(selectedNight);
        try { data.precipitation = await fetchPrecipitation(selectedNight); }
        catch (error) { data.precipitation_error = error.message; }
      }
      if (selectedNight !== select.value) return;
      report.replaceChildren();
      line('Overnight precipitation (18:00–06:00 local)', 'h2');
      const rain = data.precipitation;
      if (rain) {
        line(rain.total_mm == null ? `Total unavailable (${rain.status}); ${rain.available_hours}/${rain.expected_hours} hours available.` :
          `${rain.total_in.toFixed(3)} in (${rain.total_mm.toFixed(2)} mm); ${rain.available_hours}/${rain.expected_hours} hours.`);
        line(`${rain.window_start} to ${rain.window_end} (${rain.timezone}). Open-Meteo ECMWF IFS model estimate, not a station measurement. Retrieved ${rain.retrieved_at_utc}.`);
        line(`Site: ${rain.latitude}, ${rain.longitude}. Saved in logs/overnight_precipitation.json. Original recording snapshots are provisional and must not be summed.`);
      } else line('No overnight precipitation report is available.');
      if (data.precipitation_error) line(data.precipitation_error);
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
  async function fetchPrecipitation(night) {
    const response = await fetch(`/api/nights/${night}/precipitation`, {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Precipitation unavailable.');
    return result;
  }
  precipitationButton.addEventListener('click', async () => {
    if (!select.value) return;
    precipitationButton.disabled = true;
    try { await fetchPrecipitation(select.value); await refresh(); }
    catch (error) { message.textContent = error.message; }
    finally { precipitationButton.disabled = false; }
  });
  select.addEventListener('change', refresh);
  document.getElementById('night-refresh').addEventListener('click', refresh);
  refresh();
})();
