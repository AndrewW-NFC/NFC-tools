// NFC Tools - small, no-framework UI script.

const lookupBtn = document.getElementById("lookup");
if (lookupBtn) {
  lookupBtn.addEventListener("click", async () => {
    const q = document.getElementById("locq").value;
    const fd = new FormData();
    fd.append("query", q);
    const r = await fetch("/wizard/geocode", { method: "POST", body: fd });
    const j = await r.json();
    if (j.error) {
      alert("Couldn't find that place.");
      return;
    }
    document.getElementById("lat").value = j.latitude;
    document.getElementById("lon").value = j.longitude;
    const tzInput = document.getElementById("tz");
    if (tzInput && j.timezone) tzInput.value = j.timezone;
    const lbl = document.getElementById("tzlabel");
    if (lbl) lbl.textContent = j.timezone;
  });
}

const testBtn = document.getElementById("test");
if (testBtn) {
  testBtn.addEventListener("click", async () => {
    const id = document.getElementById("device").value;
    const out = document.getElementById("test-result");
    out.textContent = "Listening for 4 seconds...";
    const fd = new FormData();
    fd.append("device_id", id);
    const r = await fetch("/wizard/test-mic", { method: "POST", body: fd });
    const j = await r.json();
    if (j.error) {
      out.textContent = j.error;
      return;
    }
    out.textContent = `Peak: ${j.peak_db ?? "?"} dB - Mean: ${j.mean_db ?? "?"} dB - ${j.hint}`;
  });
}

const loadPresetsBtn = document.getElementById("loadPresets");
if (loadPresetsBtn) {
  loadPresetsBtn.addEventListener("click", async () => {
    const lat = document.getElementById("lat").value;
    const lon = document.getElementById("lon").value;
    const tzInput = document.getElementById("tz");
    const tz = tzInput?.value || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const r = await fetch(`/api/sun-presets?lat=${lat}&lon=${lon}&tz=${encodeURIComponent(tz)}`);
    const presets = await r.json();
    const list = document.getElementById("presetList");
    list.innerHTML = presets.map(p => `
      <div class="preset">
        <strong>${p.label}</strong> (${p.start_time}-${p.end_time}) - ${p.description}
        <button type="button" class="usePreset" data-start="${p.start_time}" data-end="${p.end_time}">Use</button>
      </div>
    `).join("");
    list.querySelectorAll(".usePreset").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelector('input[name="start_time"]').value = b.dataset.start;
        document.querySelector('input[name="end_time"]').value = b.dataset.end;
      });
    });
  });
}

const startBtn = document.getElementById("start");
if (startBtn) {
  const stopBtn = document.getElementById("stop");
  const forceNow = document.getElementById("force-now");
  const sessionWindow = document.getElementById("session-window");
  const nfcWindow = document.getElementById("nfc-window");
  const meter = document.getElementById("meter");
  const fill = document.getElementById("meter-fill");
  const meterLabel = document.getElementById("meter-label");
  const activeSettings = document.getElementById("active-settings");
  const statusMessage = document.getElementById("analysis-message");
  const statusDetails = document.getElementById("analysis-history");
  const sessionLogRows = document.getElementById("session-log-rows");
  const downloadSessionLog = document.getElementById("download-session-log");
  const analyzePendingBtn = document.getElementById("analyze-pending");

  let currentState = "idle";
  let latestStatus = null;
  const METER_PREVIEW_POLL_MS = 250;
  const METER_AUDIO_FRAME_MS = 50;
  const METER_RENDER_MS = Math.round((METER_PREVIEW_POLL_MS + METER_AUDIO_FRAME_MS) / 2);
  const METER_INACTIVITY_MS = 30000;
  const STATUS_POLL_MS = 3000;
  let backendMeterTimer = null;
  let backendMeterBusy = false;
  let meterRenderTimer = null;
  let meterTarget = null;
  let meterInactivityTimer = null;
  let meterPausedReason = null;
  let meterPauseRequestBusy = false;
  let meterPreviewRequiresDemand = false;
  let statusPollTimer = null;
  let statusPollBusy = false;
  let statusSocket = null;
  let statusSocketReconnectTimer = null;
  let statusSocketShouldRun = false;

  function isDashboardActive() {
    return !document.hidden;
  }

  function canRunMetering() {
    return isDashboardActive() && meterPausedReason !== "inactivity";
  }

  function parseLocalDate(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function sameLocalDate(a, b) {
    return a && b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();
  }

  function normalizeStartEnd(startValue, endValue) {
    const start = parseLocalDate(startValue);
    const end = parseLocalDate(endValue);
    if (!start || !end) return { start, end };
    if (start.getHours() < 12 && end.getDate() !== start.getDate() && end.getHours() < 12) {
      start.setHours(start.getHours() + 12);
    }
    return { start, end };
  }

  function dayLabel(d) {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    if (sameLocalDate(d, now)) return "Tonight";
    if (sameLocalDate(d, tomorrow)) return "Tomorrow";
    return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  }

  function timeLabel(d) {
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function formatWindow(startValue, endValue, label = "Recording") {
    const { start, end } = normalizeStartEnd(startValue, endValue);
    if (!start || !end) return `${label}: ${startValue || "?"} to ${endValue || "?"}`;
    return `${label}: ${dayLabel(start)}, ${timeLabel(start)} to ${dayLabel(end)}, ${timeLabel(end)}`;
  }

  function updateSessionWindow(s) {
    const start = s.scheduled_starts_at || s.started_at;
    const end = s.scheduled_ends_at || s.ends_at;
    if (start && end && sessionWindow) sessionWindow.textContent = formatWindow(start, end);
    if (s.nfc_starts_at && s.nfc_ends_at && nfcWindow) {
      nfcWindow.textContent = formatWindow(s.nfc_starts_at, s.nfc_ends_at, "NFC counting window");
    }
  }

  function isOutsideWindow(s) {
    const { start, end } = normalizeStartEnd(s.scheduled_starts_at, s.scheduled_ends_at || s.ends_at);
    const now = new Date();
    if (!start || !end) return true;
    return now < start || now >= end;
  }

  function setButtonVisual(kind, text, disabled = false) {
    startBtn.classList.remove("recording", "awaiting", "scheduled");
    if (kind) startBtn.classList.add(kind);
    startBtn.textContent = text;
    startBtn.disabled = disabled;
  }

  function updateNavLock(s) {
    const locked = s && (s.state === "recording" || s.state === "awaiting_start");
    document.body.classList.toggle("session-locked", Boolean(locked));
  }

  function updateStopButton(s) {
    if (!stopBtn) return;

    const state = s?.state || "idle";

    if (state === "recording") {
      stopBtn.hidden = false;
      stopBtn.textContent = "Stop";
      stopBtn.disabled = false;
      return;
    }

    if (state === "awaiting_start") {
      stopBtn.hidden = false;
      stopBtn.textContent = "Cancel";
      stopBtn.disabled = false;
      return;
    }

    stopBtn.hidden = true;
    stopBtn.textContent = "Stop";
    stopBtn.disabled = false;
  }

  function updateButton(s) {
    latestStatus = s;
    currentState = s.state || "idle";
    updateNavLock(s);

    if (currentState === "recording") {
      setButtonVisual("recording", "Recording...", true);
      if (forceNow) forceNow.disabled = true;
      return;
    }

    if (currentState === "awaiting_start") {
      setButtonVisual("scheduled", "Session Scheduled", true);
      if (forceNow) forceNow.disabled = true;
      return;
    }

    if (forceNow) forceNow.disabled = false;

    if (forceNow && forceNow.checked) {
      setButtonVisual(null, "Start Recording", false);
      return;
    }

    if (isOutsideWindow(s)) {
      setButtonVisual(null, "Schedule Tonight's Session", false);
      return;
    }

    setButtonVisual(null, "Start Recording", false);
  }

  function meterGradientColor(pct) {
    const stops = [
      [0, 46, 125, 50],     // green
      [55, 251, 192, 45],   // yellow
      [78, 245, 124, 0],    // orange
      [100, 198, 40, 40]    // red
    ];
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    for (let i = 0; i < stops.length - 1; i += 1) {
      const a = stops[i];
      const b = stops[i + 1];
      if (p >= a[0] && p <= b[0]) {
        const t = (p - a[0]) / Math.max(1, b[0] - a[0]);
        const r = Math.round(a[1] + (b[1] - a[1]) * t);
        const g = Math.round(a[2] + (b[2] - a[2]) * t);
        const bl = Math.round(a[3] + (b[3] - a[3]) * t);
        return `rgb(${r}, ${g}, ${bl})`;
      }
    }
    const last = stops[stops.length - 1];
    return `rgb(${last[1]}, ${last[2]}, ${last[3]})`;
  }

  function meterPayloadFromDb(rmsDb, peakDb = null, source = "backend") {
    const rms = Number.isFinite(Number(rmsDb)) ? Number(rmsDb) : -120;
    const peak = Number.isFinite(Number(peakDb)) ? Number(peakDb) : rms;
    const displayDb = Math.max(rms, peak - 12);
    const floorDb = -75;
    const ceilingDb = -6;
    const liveMinimumPct = 2;
    const rawPct = ((displayDb - floorDb) / (ceilingDb - floorDb)) * 100;
    const pct = Math.max(liveMinimumPct, Math.min(100, rawPct));

    return { pct, peak, source: source || "backend" };
  }

  function renderMeterPayload(payload) {
    if (!fill || !payload) return;

    const pct = Math.max(0, Math.min(100, Number(payload.pct) || 0));
    const peak = Number.isFinite(Number(payload.peak)) ? Number(payload.peak) : -120;

    fill.style.width = `${pct.toFixed(1)}%`;
    fill.style.backgroundColor = meterGradientColor(peak >= -3.0 ? Math.max(pct, 94) : pct);
    fill.classList.toggle("meter-warn", pct >= 68 && pct < 90);
    fill.classList.toggle("meter-hot", pct >= 90 || peak >= -3.0);
    fill.setAttribute("aria-valuenow", String(Math.round(pct)));
    fill.dataset.meterSource = payload.source;
  }

  function renderQueuedMeter() {
    if (!canRunMetering()) return;
    renderMeterPayload(meterTarget);
  }

  function startMeterRenderLoop() {
    if (meterRenderTimer || !fill || !canRunMetering()) return;
    renderQueuedMeter();
    meterRenderTimer = setInterval(renderQueuedMeter, METER_RENDER_MS);
  }

  function stopMeterRenderLoop() {
    if (meterRenderTimer) {
      clearInterval(meterRenderTimer);
      meterRenderTimer = null;
    }
  }

  function updateMeterFromDb(rmsDb, peakDb = null, source = "backend") {
    meterTarget = meterPayloadFromDb(rmsDb, peakDb, source);
    startMeterRenderLoop();
  }

  function renderMeterFromStatus(s) {
    const meter = s?.meter || {};
    const state = s?.state || "idle";
    if (state === "recording" && (meter.rms_db != null || meter.peak_db != null || s?.level_db != null)) {
      updateMeterFromDb(
        meter.rms_db ?? s.level_db,
        meter.peak_db ?? meter.rms_db ?? s.level_db,
        meter.source || "recording-backend"
      );
      setMeterLabel("Meter is using the recording stream.");
      return true;
    }
    return false;
  }

  async function refreshBackendMeterOnce() {
    if (!fill || backendMeterBusy || !canRunMetering()) return;
    backendMeterBusy = true;
    try {
      const r = await fetch("/api/mic-level?on_demand=1", { cache: "no-store" });
      const j = await r.json();
      if (!canRunMetering()) return;
      if (j?.requires_on_demand) {
        meterPreviewRequiresDemand = true;
      }
      if (j && !j.error && (j.rms_db != null || j.peak_db != null || j.level_db != null)) {
        meterPreviewRequiresDemand = Boolean(j.requires_on_demand);
        updateMeterFromDb(j.rms_db ?? j.level_db, j.peak_db ?? j.rms_db ?? j.level_db, j.source || "backend-preview");
        setMeterLabel(j.recording ? "Meter is using the recording stream." : "Meter is previewing the configured input.");
      } else if (j?.error) {
        setMeterLabel(j.error);
      }
    } catch (_) {
      setMeterLabel("Meter preview could not reach the recording input.");
    } finally {
      backendMeterBusy = false;
    }
  }

  function startBackendMeterPolling() {
    if (!fill || backendMeterTimer || !canRunMetering()) return;
    refreshBackendMeterOnce();
    backendMeterTimer = setInterval(refreshBackendMeterOnce, METER_PREVIEW_POLL_MS);
  }

  function stopBackendMeterPolling() {
    if (backendMeterTimer) {
      clearInterval(backendMeterTimer);
      backendMeterTimer = null;
    }
  }

  function setMeterLabel(text) {
    if (meterLabel) meterLabel.textContent = text;
  }

  function notifyBackendMeterPaused() {
    if (meterPauseRequestBusy) return;
    meterPauseRequestBusy = true;
    fetch("/api/mic-level/pause", {
      method: "POST",
      cache: "no-store",
      keepalive: true
    }).catch(() => {
      // The server-side preview stream also has its own idle timeout.
    }).finally(() => {
      meterPauseRequestBusy = false;
    });
  }

  function resumeMeterIfNeeded() {
    if (!canRunMetering()) return;
    startBackendMeterPolling();
    startMeterRenderLoop();
  }

  function clearMeterInactivityTimer() {
    if (meterInactivityTimer) {
      clearTimeout(meterInactivityTimer);
      meterInactivityTimer = null;
    }
  }

  function scheduleMeterInactivityTimeout() {
    clearMeterInactivityTimer();
    if (!isDashboardActive()) return;
    meterInactivityTimer = setTimeout(() => {
      pauseMetering("inactivity");
    }, METER_INACTIVITY_MS);
  }

  function pauseMetering(reason = "inactive") {
    if (reason === "inactivity") {
      meterPausedReason = "inactivity";
      setMeterLabel("Metering paused due to user inactivity.");
    }
    stopBackendMeterPolling();
    stopMeterRenderLoop();
    stopStatusPolling();
    stopStatusSocket();
    notifyBackendMeterPaused();
    if (reason !== "inactivity") clearMeterInactivityTimer();
  }

  function noteMeterActivity() {
    if (!isDashboardActive()) return;
    const wasPausedForInactivity = meterPausedReason === "inactivity";
    meterPausedReason = null;
    scheduleMeterInactivityTimeout();
    if (wasPausedForInactivity) setMeterLabel("Metering resumed.");
    resumeMeterIfNeeded();
    startStatusPolling();
    startStatusSocket();
  }

  async function requestOnDemandMeterPreview() {
    if (!fill || backendMeterBusy || !isDashboardActive()) return;
    backendMeterBusy = true;
    setMeterLabel("Checking microphone level...");
    try {
      const r = await fetch("/api/mic-level?on_demand=1", { cache: "no-store" });
      const j = await r.json();
      if (j && !j.error && (j.rms_db != null || j.peak_db != null || j.level_db != null)) {
        meterPreviewRequiresDemand = Boolean(j.requires_on_demand || j.source === "ffmpeg_avfoundation_preview");
        updateMeterFromDb(j.rms_db ?? j.level_db, j.peak_db ?? j.rms_db ?? j.level_db, j.source || "backend-preview");
        setMeterLabel(j.recording ? "Meter is using the recording stream." : "Meter checked. Click again for another quick level check.");
      } else if (j?.error) {
        setMeterLabel(j.error);
      }
    } catch (_) {
      setMeterLabel("Meter check could not reach the recording input.");
    } finally {
      backendMeterBusy = false;
    }
  }

  function sampleRateLabel(value) {
    const n = Number(value);
    if (n === 44100) return "44.1 kHz";
    if (n === 96000) return "96 kHz";
    if (!Number.isNaN(n)) return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)} kHz`;
    return value || "?";
  }

  function backendLabel(value) {
    const backend = String(value || "auto");
    if (backend === "auto") return "Auto (CoreAudio/sounddevice on macOS)";
    if (backend === "sounddevice" || backend === "coreaudio") return "CoreAudio / sounddevice";
    if (backend === "ffmpeg" || backend === "avfoundation") return "ffmpeg / avfoundation";
    return backend;
  }

  function formatPresetLabel(value, sampleRate, channels, bitDepth) {
    const preset = String(value || "auto_native");
    if (preset === "auto_native") return "Auto/native device format, 32-bit float WAV";
    if (preset === "float_48k") return "48 kHz, 32-bit float WAV";
    if (preset === "s16_48k") return "48 kHz, 16-bit WAV";
    if (preset === "s16_441") return "44.1 kHz, 16-bit WAV";
    if (preset === "s16_96k") return "96 kHz, 16-bit WAV";
    if (preset === "float_96k") return "96 kHz, 32-bit float WAV";
    return `${sampleRateLabel(sampleRate)}, ${channels || "?"} channel(s), ${bitDepth || "?"}-bit`;
  }

  function updateActiveSettings(s) {
    if (!activeSettings) return;
    const active = s && (s.state === "recording" || s.state === "awaiting_start");
    activeSettings.hidden = !active;
    if (!active) return;

    const start = s.scheduled_starts_at || s.started_at;
    const end = s.scheduled_ends_at || s.ends_at;
    const folderDate = s.session_date || "yyyy-mm-dd";
    const data = activeSettings.dataset;

    activeSettings.querySelector('[data-setting="site"]').textContent = data.site || "—";
    activeSettings.querySelector('[data-setting="window"]').textContent = formatWindow(start, end).replace(/^Recording: /, "");
    const nfcWindowEl = activeSettings.querySelector('[data-setting="nfc-window"]');
    if (nfcWindowEl) {
      nfcWindowEl.textContent = formatWindow(s.nfc_starts_at, s.nfc_ends_at, "NFC counting window").replace(/^NFC counting window: /, "");
    }
    activeSettings.querySelector('[data-setting="output"]').textContent = `${data.desktopPrefix || "~/Desktop"}/${folderDate}/`;
    activeSettings.querySelector('[data-setting="device"]').textContent = data.device || "—";
    const backendEl = activeSettings.querySelector('[data-setting="backend"]');
    if (backendEl) backendEl.textContent = backendLabel(data.recordingBackend);
    activeSettings.querySelector('[data-setting="audio"]').textContent =
      formatPresetLabel(data.formatPreset, data.sampleRate, data.channels, data.bitDepth);
    activeSettings.querySelector('[data-setting="segment"]').textContent = `${data.segmentMinutes || "?"} minute(s)`;
    activeSettings.querySelector('[data-setting="analyzers"]').textContent = data.analyzers || "—";
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function analyzerName(name) {
    const n = String(name || "").toLowerCase();
    if (n === "birdnet") return "BirdNET";
    if (n === "nighthawk") return "Nighthawk";
    return name || "";
  }

  function plainResult(value) {
    const v = String(value || "").toLowerCase();
    if (v === "ok" || v === "success" || v === "successful") return "successful";
    if (v === "failed" || v === "error") return "had a problem";
    if (v === "lock_timeout") return "could not start";
    return v || "unknown";
  }

  function fileNameFrom(value) {
    if (!value) return "";
    if (typeof value === "string") {
      const match = value.match(/(NFC_[^\s:]+\.wav)/);
      return match ? match[1] : "";
    }
    return value.file || value.current_file || fileNameFrom(value.message || "");
  }

  function enabledAnalyzers() {
    const raw = activeSettings?.dataset?.analyzers || "";
    const names = raw
      .split(",")
      .map(x => x.trim().toLowerCase())
      .filter(Boolean);
    return names.length ? names : ["birdnet", "nighthawk"];
  }

  function resultFromText(text, analyzer) {
    const re = new RegExp(`${analyzer}\\s*=\\s*([a-z_]+)`, "i");
    const match = String(text || "").match(re);
    return match ? plainResult(match[1]) : "";
  }

  function analysisProgress(analysis) {
    const enabled = enabledAnalyzers();
    const files = new Set();
    const completedFiles = new Set();
    const resultsByAnalyzer = {};

    for (const analyzer of enabled) resultsByAnalyzer[analyzer] = "";

    const queue = Array.isArray(analysis.queue) ? analysis.queue : [];
    for (const item of queue) {
      const file = fileNameFrom(item);
      if (file) files.add(file);
    }

    const currentFile = fileNameFrom(analysis.current_file || "");
    if (currentFile) files.add(currentFile);

    const history = Array.isArray(analysis.history) ? analysis.history : [];
    const perFileResults = {};

    function noteResult(file, analyzer, result) {
      if (!file || !analyzer || !result) return;
      files.add(file);
      const key = analyzer.toLowerCase();
      perFileResults[file] ||= {};
      perFileResults[file][key] = result;
      resultsByAnalyzer[key] = result;
    }

    for (const item of history) {
      const file = fileNameFrom(item);
      const analyzer = String(item.analyzer || "").toLowerCase();
      const result = plainResult(item.status || "");
      if (file) files.add(file);
      if (file && analyzer && result) noteResult(file, analyzer, result);

      const msg = item.message || "";
      if (file && msg) {
        for (const a of enabled) {
          const fromMsg = resultFromText(msg, a);
          if (fromMsg) noteResult(file, a, fromMsg);
        }
      }
    }

    const message = analysis.message || "";
    const messageFile = fileNameFrom(message);
    if (messageFile) {
      files.add(messageFile);
      for (const a of enabled) {
        const fromMsg = resultFromText(message, a);
        if (fromMsg) noteResult(messageFile, a, fromMsg);
      }
    }

    for (const [file, resultMap] of Object.entries(perFileResults)) {
      const complete = enabled.every(a => resultMap[a] && resultMap[a] !== "had a problem" && resultMap[a] !== "unknown");
      const hasProblem = enabled.some(a => resultMap[a] === "had a problem");
      if (complete || hasProblem || /analysis complete/i.test(message)) completedFiles.add(file);
    }

    if (/analysis complete/i.test(message) && messageFile) completedFiles.add(messageFile);

    const total = Math.max(files.size, completedFiles.size + queue.length + (currentFile && !completedFiles.has(currentFile) ? 1 : 0));
    const analyzed = completedFiles.size;
    const left = Math.max(0, total - analyzed);

    return { total, analyzed, left, resultsByAnalyzer, enabled };
  }

  function resultLines(progress) {
    const lines = [];
    for (const analyzer of progress.enabled) {
      const result = progress.resultsByAnalyzer[analyzer];
      if (result) lines.push(`${analyzerName(analyzer)}: ${result}`);
    }
    return lines;
  }

  function statusLines(s) {
    const state = s?.state || "idle";
    const analysis = s?.analysis || {};
    const progress = analysisProgress(analysis);

    if (state === "awaiting_start") {
      return ["Standing by for start of recording."];
    }

    if (state === "recording") {
      return ["Recording…"];
    }

    if (analysis.active) {
      const lines = [];
      const index = progress.total ? Math.min(progress.analyzed + 1, progress.total) : 1;
      lines.push(progress.total ? `Analyzing the recording ${index} of ${progress.total}.` : "Analyzing the recording.");

      if (analysis.current_analyzer) {
        lines.push(`${analyzerName(analysis.current_analyzer)} is analyzing the recording.`);
      }

      if (progress.total) {
        lines.push(`Recordings analyzed: ${progress.analyzed} of ${progress.total}.`);
        lines.push(`Recordings left: ${progress.left}.`);
      }

      return lines;
    }

    if (progress.total && progress.left > 0) {
      if (/deferred/i.test(analysis.message || "")) {
        return [
          analysis.message,
          `Recordings analyzed: ${progress.analyzed} of ${progress.total}.`,
          `Recordings left: ${progress.left}.`
        ];
      }
      return [
        "Recording stopped. Analysis will begin soon.",
        `Recordings analyzed: ${progress.analyzed} of ${progress.total}.`,
        `Recordings left: ${progress.left}.`
      ];
    }

    if (progress.total && progress.left === 0 && progress.analyzed > 0) {
      return [
        "Analysis complete.",
        `Recordings analyzed: ${progress.analyzed} of ${progress.total}.`,
        "Recordings left: 0.",
        ...resultLines(progress)
      ];
    }

    if (/analysis will start|analysis queued|queued/i.test(analysis.message || "")) {
      return ["Recording stopped. Analysis will begin soon."];
    }

    return ["Standing by for start of recording."];
  }

  function renderStatus(s) {
    if (!statusMessage) return;

    const lines = statusLines(s || {});
    statusMessage.textContent = lines[0] || "Standing by for start of recording.";

    if (statusDetails) {
      const details = lines.slice(1);
      statusDetails.hidden = details.length === 0;
      statusDetails.innerHTML = details.map(line => `<li>${escapeHtml(line)}</li>`).join("");
    }
  }

  function updateAnalyzePendingButton(s) {
    if (!analyzePendingBtn) return;
    const analysis = s?.analysis || {};
    const progress = analysisProgress(analysis);
    const state = s?.state || "idle";
    analyzePendingBtn.hidden = state !== "idle" || Boolean(analysis.active) || progress.left <= 0;
    analyzePendingBtn.disabled = false;
  }
  function sessionLogTime(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value || "";
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
  }

  function renderSessionLog(s) {
    if (!sessionLogRows) return;

    const rows = Array.isArray(s?.session_log) ? s.session_log : [];
    sessionLogRows.innerHTML = rows.map(row => {
      const time = escapeHtml(sessionLogTime(row.timestamp));
      const event = escapeHtml(row.event || "event");
      const message = escapeHtml(row.message || "");
      return `<li><span class="session-log-time">${time}</span> <span class="session-log-event">${event}</span> <span class="session-log-message">${message}</span></li>`;
    }).join("");

    if (downloadSessionLog) {
      const date = s?.session_date ? `?session_date=${encodeURIComponent(s.session_date)}` : "";
      downloadSessionLog.href = `/session/log.csv${date}`;
    }
  }
  function applyStatus(s) {
    window.__nfcLastStatus = s;
    updateButton(s);
    updateStopButton(s);
    updateSessionWindow(s);
    updateActiveSettings(s);
    renderStatus(s);
    updateAnalyzePendingButton(s);
    renderSessionLog(s);

    if (canRunMetering() && (s?.state || "idle") === "recording") {
      renderMeterFromStatus(s);
    }
    resumeMeterIfNeeded();
  }

  async function refreshStatus() {
    if (statusPollBusy || !canRunMetering()) return;
    statusPollBusy = true;
    try {
      const r = await fetch("/session/status", { cache: "no-store" });
      const s = await r.json();
      applyStatus(s);
    } finally {
      statusPollBusy = false;
    }
  }

  function startStatusPolling() {
    if (statusPollTimer || !canRunMetering()) return;
    refreshStatus();
    statusPollTimer = setInterval(refreshStatus, STATUS_POLL_MS);
  }

  function stopStatusPolling() {
    if (statusPollTimer) {
      clearInterval(statusPollTimer);
      statusPollTimer = null;
    }
  }

  function clearStatusSocketReconnect() {
    if (statusSocketReconnectTimer) {
      clearTimeout(statusSocketReconnectTimer);
      statusSocketReconnectTimer = null;
    }
  }

  function startStatusSocket() {
    if (!canRunMetering()) return;
    statusSocketShouldRun = true;
    clearStatusSocketReconnect();

    if (
      statusSocket &&
      (statusSocket.readyState === WebSocket.OPEN || statusSocket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const wsProtocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${wsProtocol}://${location.host}/ws/status`);
    statusSocket = ws;

    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type !== "status" && m.ty !== "status") return;
      applyStatus(m.data);
    };

    ws.onclose = () => {
      if (statusSocket === ws) statusSocket = null;
      if (statusSocketShouldRun && canRunMetering()) {
        statusSocketReconnectTimer = setTimeout(startStatusSocket, 3000);
      }
    };
  }

  function stopStatusSocket() {
    statusSocketShouldRun = false;
    clearStatusSocketReconnect();

    if (!statusSocket) return;
    const ws = statusSocket;
    statusSocket = null;
    try {
      ws.close();
    } catch (_) {
      // Closing a stale socket is best-effort.
    }
  }

  async function refreshStatusOnce() {
    const r = await fetch("/session/status", { cache: "no-store" });
    const s = await r.json();
    applyStatus(s);
  }

  forceNow?.addEventListener("change", () => {
    if (latestStatus) updateButton(latestStatus);
  });

  startBtn.addEventListener("click", async () => {
    const fd = new FormData();
    if (forceNow && forceNow.checked) fd.append("force_now", "on");
    startBtn.disabled = true;

    try {
      const r = await fetch("/session/start", { method: "POST", body: fd });
      const text = await r.text();
      let s;
      try { s = JSON.parse(text); } catch { s = null; }

      if (!r.ok) {
        alert(`Could not start session.\n\n${s?.detail || s?.error || text || r.statusText}`);
        if (latestStatus) updateButton(latestStatus);
        return;
      }
      applyStatus(s);
      resumeMeterIfNeeded();
    } catch (e) {
      alert(`Could not start session.\n\n${e}`);
      if (latestStatus) updateButton(latestStatus);
    }
  });

  stopBtn?.addEventListener("click", async () => {
    stopBtn.disabled = true;
    if (statusMessage) statusMessage.textContent = "Recording stopped. Analysis will begin soon.";
    if (statusDetails) {
      statusDetails.hidden = true;
      statusDetails.innerHTML = "";
    }

    const r = await fetch("/session/stop", { method: "POST" });
    const s = await r.json();
    applyStatus(s);
    resumeMeterIfNeeded();
  });

  analyzePendingBtn?.addEventListener("click", async () => {
    analyzePendingBtn.disabled = true;
    const fd = new FormData();
    fd.append("force", "true");
    const r = await fetch("/session/analyze-pending", { method: "POST", body: fd });
    const s = await r.json();
    if (!r.ok) {
      alert(s?.error || "No pending recordings are available for analysis.");
      analyzePendingBtn.disabled = false;
      return;
    }
    applyStatus(s);
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pauseMetering("inactive");
    else noteMeterActivity();
  });
  window.addEventListener("pagehide", () => pauseMetering("inactive"));
  window.addEventListener("focus", noteMeterActivity);
  meter?.addEventListener("click", () => {
    noteMeterActivity();
    requestOnDemandMeterPreview();
  });
  document.addEventListener("pointerdown", noteMeterActivity, { passive: true });
  document.addEventListener("pointermove", noteMeterActivity, { passive: true });
  document.addEventListener("wheel", noteMeterActivity, { passive: true });
  document.addEventListener("keydown", noteMeterActivity);

  noteMeterActivity();
  refreshStatusOnce();
  startStatusPolling();
  startStatusSocket();
}

document.querySelectorAll("[data-install]").forEach(btn => {
  btn.addEventListener("click", async () => {
    const name = btn.dataset.install;
    const log = document.getElementById("install-log");
    log.textContent = `Installing ${name}...\n`;
    await fetch(`/install/${name}`, { method: "POST" });
    const tick = setInterval(async () => {
      const r = await fetch("/install/log");
      const j = await r.json();
      log.textContent = j.lines.join("\n");
    }, 1000);
    setTimeout(() => clearInterval(tick), 10 * 60 * 1000);
  });
});

function setupRecordingChecklistMemory() {
  const boxes = Array.from(document.querySelectorAll(".recording-checklist input[type='checkbox'][id]"));
  if (!boxes.length) return;

  boxes.forEach(box => {
    const key = `nfcToolsRecordingChecklist.${box.id}`;
    box.checked = localStorage.getItem(key) === "true";
    box.addEventListener("change", () => {
      localStorage.setItem(key, box.checked ? "true" : "false");
    });
  });
}

setupRecordingChecklistMemory();

// ---- Recording path diagnostics ----
function nfcEscapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function nfcRenderRawTestResult(j) {
  const resultEl = document.getElementById("raw-recording-test-result");
  if (!resultEl) return;
  if (!j || j.error || j.ok === false) {
    resultEl.textContent = j?.error || "Raw test failed.";
    return;
  }
  const wav = j.download_url ? `<a href="${j.download_url}" download>Download WAV</a>` : "";
  const log = j.log_download_url ? `<a href="${j.log_download_url}" download>Download log</a>` : "";
  const size = j.size_bytes ? `${Math.round(j.size_bytes / 1024)} KB` : "unknown size";
  const variant = nfcEscapeHtml(j.variant || "raw");
  const desc = nfcEscapeHtml(j.variant_description || "");
  resultEl.innerHTML = `<strong>${variant}</strong> test complete (${size}). ${desc}<br>${wav} ${log}`;
}

function nfcRenderAvfoundationDevices(j) {
  const listEl = document.getElementById("avfoundation-device-list");
  if (!listEl) return;
  if (!j || j.error) {
    listEl.hidden = false;
    listEl.textContent = j?.error || "Could not list avfoundation devices.";
    return;
  }
  const audio = Array.isArray(j.devices?.audio) ? j.devices.audio : [];
  const video = Array.isArray(j.devices?.video) ? j.devices.video : [];
  const lines = ["Audio devices:"];
  if (audio.length) {
    for (const d of audio) lines.push(`  [${d.index}] ${d.name}`);
  } else {
    lines.push("  none found");
  }
  lines.push("", "Video devices:");
  if (video.length) {
    for (const d of video) lines.push(`  [${d.index}] ${d.name}`);
  } else {
    lines.push("  none found");
  }
  if (j.download_url) {
    lines.push("", `Raw device-list log: ${j.download_url}`);
  }
  listEl.hidden = false;
  listEl.textContent = lines.join("\n");
}

async function nfcRunRawRecordingVariant(btn, variant) {
  const buttons = Array.from(document.querySelectorAll(".raw-recording-variant"));
  const resultEl = document.getElementById("raw-recording-test-result");
  btn.disabled = true;
  for (const other of buttons) other.disabled = true;
  if (resultEl) resultEl.textContent = `Recording 10-second ${variant} test…`;
  try {
    const r = await fetch(`/diagnostics/raw-recording-test?variant=${encodeURIComponent(variant)}`, { method: "POST" });
    const j = await r.json();
    nfcRenderRawTestResult(j);
  } catch (e) {
    if (resultEl) resultEl.textContent = `Raw test failed: ${e}`;
  } finally {
    btn.disabled = false;
    for (const other of buttons) other.disabled = false;
  }
}

document.querySelectorAll(".raw-recording-variant").forEach(btn => {
  btn.addEventListener("click", () => nfcRunRawRecordingVariant(btn, btn.dataset.variant || "current"));
});

document.getElementById("avfoundation-devices")?.addEventListener("click", async (ev) => {
  const btn = ev.currentTarget;
  const listEl = document.getElementById("avfoundation-device-list");
  btn.disabled = true;
  if (listEl) {
    listEl.hidden = false;
    listEl.textContent = "Listing avfoundation devices…";
  }
  try {
    const r = await fetch("/diagnostics/avfoundation-devices", { cache: "no-store" });
    const j = await r.json();
    nfcRenderAvfoundationDevices(j);
  } catch (e) {
    if (listEl) listEl.textContent = `Could not list devices: ${e}`;
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("sounddevice-raw-test")?.addEventListener("click", async (ev) => {
  const btn = ev.currentTarget;
  const resultEl = document.getElementById("raw-recording-test-result");
  btn.disabled = true;
  if (resultEl) resultEl.textContent = "Recording 10-second sounddevice/CoreAudio 48 kHz float test…";
  try {
    const r = await fetch("/diagnostics/sounddevice-raw-test", { method: "POST" });
    const j = await r.json();
    nfcRenderRawTestResult(j);
  } catch (e) {
    if (resultEl) resultEl.textContent = `sounddevice/CoreAudio test failed: ${e}`;
  } finally {
    btn.disabled = false;
  }
});
