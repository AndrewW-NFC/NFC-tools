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
    document.getElementById("tz").value = j.timezone;
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
    const tz = document.getElementById("tz").value;
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
  const fill = document.getElementById("meter-fill");
  const meterLabel = document.getElementById("meter-label");
  const activeSettings = document.getElementById("active-settings");
  const statusMessage = document.getElementById("analysis-message");
  const statusDetails = document.getElementById("analysis-history");

  let currentState = "idle";
  let latestStatus = null;

  let micStream = null;
  let micAudioContext = null;
  let micAnalyser = null;
  let micSamples = null;
  let micAnimationFrame = null;
  let micStarting = false;

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

  function formatWindow(startValue, endValue) {
    const { start, end } = normalizeStartEnd(startValue, endValue);
    if (!start || !end) return `Scheduled: ${startValue || "?"} to ${endValue || "?"}`;
    return `Scheduled: ${dayLabel(start)}, ${timeLabel(start)} to ${dayLabel(end)}, ${timeLabel(end)}`;
  }

  function updateSessionWindow(s) {
    const start = s.scheduled_starts_at || s.started_at;
    const end = s.scheduled_ends_at || s.ends_at;
    if (start && end && sessionWindow) sessionWindow.textContent = formatWindow(start, end);
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

  function updateMeterFromRms(rms, peak = 0) {
    if (!fill) return;

    // This is a practical live-input meter, not a calibrated SPL meter.
    // The browser gives normalized digital samples. RMS is good for steady
    // sound, but it under-represents short transients like claps, ticks, and
    // sudden aircraft noise. Use both RMS and peak so the display feels like a
    // live level meter instead of a conservative average meter.
    //
    // Approximate visual targets:
    //   near silence        -> tiny live tick
    //   quiet room          -> low movement
    //   normal speech       -> middle-ish
    //   clap / yell / plane -> immediate far-right jump and red
    const safeRms = Math.max(Number(rms) || 0, 0.000001);
    const safePeak = Math.max(Number(peak) || 0, 0.000001);

    const rmsDb = 20 * Math.log10(safeRms);
    const peakDb = 20 * Math.log10(safePeak);

    // Peaks need to matter for a live meter. Subtract only 4 dB so short,
    // loud events register immediately without every tiny click pinning the bar.
    const effectiveDb = Math.max(rmsDb, peakDb - 4);

    const floorDb = -72;
    const ceilingDb = -34;
    const liveMinimumPct = 2;

    const rawPct = ((effectiveDb - floorDb) / (ceilingDb - floorDb)) * 100;
    const targetPct = Math.max(liveMinimumPct, Math.min(100, rawPct));

    // Instant attack, smooth decay. Spikes should jump immediately; the
    // fall-back should be gradual enough that the eye can follow it.
    const previousPct = Number.isFinite(updateMeterFromRms.displayedPct)
      ? updateMeterFromRms.displayedPct
      : targetPct;
    const displayedPct = targetPct >= previousPct
      ? targetPct
      : previousPct + (targetPct - previousPct) * 0.14;
    updateMeterFromRms.displayedPct = displayedPct;

    const pct = Math.max(liveMinimumPct, Math.min(100, Math.round(displayedPct)));
    fill.style.width = `${pct}%`;
    fill.classList.toggle("meter-warn", pct >= 55 && pct < 82);
    fill.classList.toggle("meter-hot", pct >= 82);
    fill.setAttribute("aria-valuenow", String(pct));
  }

  function setMeterLabel(text) {
    if (meterLabel) meterLabel.textContent = text;
  }

  function hasLiveMicStream() {
    return Boolean(
      micStream &&
      micStream.getAudioTracks().some(track => track.readyState === "live")
    );
  }

  function resumeMeterIfNeeded() {
    if (micAudioContext && micAudioContext.state === "suspended") {
      micAudioContext.resume().catch(() => {});
    }

    if (!hasLiveMicStream() && !micStarting) {
      startLiveMicMeter();
    }
  }

  async function startLiveMicMeter() {
    if (hasLiveMicStream() && micAudioContext && micAudioContext.state !== "closed") {
      resumeMeterIfNeeded();
      return;
    }

    if (micStarting) return;
    micStarting = true;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMeterLabel("Microphone meter is not available in this browser.");
      micStarting = false;
      return;
    }

    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        },
        video: false
      });

      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) {
        setMeterLabel("Microphone meter is not available in this browser.");
        micStarting = false;
        return;
      }

      micAudioContext = new AudioContext();
      const source = micAudioContext.createMediaStreamSource(micStream);
      micAnalyser = micAudioContext.createAnalyser();
      micAnalyser.fftSize = 2048;
      micAnalyser.smoothingTimeConstant = 0.8;
      source.connect(micAnalyser);
      micSamples = new Float32Array(micAnalyser.fftSize);

      setMeterLabel("Microphone meter is running.");

      function tick() {
        if (!hasLiveMicStream()) {
          updateMeterFromRms(0);
          setMeterLabel("Microphone meter stopped. Trying to restart…");
          micAnimationFrame = null;
          micStarting = false;
          setTimeout(startLiveMicMeter, 1000);
          return;
        }

        if (micAudioContext && micAudioContext.state === "suspended") {
          micAudioContext.resume().catch(() => {});
        }

        if (micAnalyser && micSamples) {
          micAnalyser.getFloatTimeDomainData(micSamples);
          let sum = 0;
          let peak = 0;
          for (const sample of micSamples) {
            sum += sample * sample;
            const abs = Math.abs(sample);
            if (abs > peak) peak = abs;
          }
          updateMeterFromRms(Math.sqrt(sum / micSamples.length), peak);
        }

        micAnimationFrame = requestAnimationFrame(tick);
      }

      if (micAnimationFrame) cancelAnimationFrame(micAnimationFrame);
      tick();
    } catch (_) {
      updateMeterFromRms(0);
      setMeterLabel("Allow microphone access to keep the meter running.");
    } finally {
      micStarting = false;
    }
  }

  function sampleRateLabel(value) {
    const n = Number(value);
    if (n === 44100) return "44.1 kHz";
    if (n === 96000) return "96 kHz";
    if (!Number.isNaN(n)) return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)} kHz`;
    return value || "?";
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
    activeSettings.querySelector('[data-setting="window"]').textContent = formatWindow(start, end).replace(/^Scheduled: /, "");
    activeSettings.querySelector('[data-setting="output"]').textContent = `${data.desktopPrefix || "~/Desktop"}/${folderDate}/`;
    activeSettings.querySelector('[data-setting="device"]').textContent = data.device || "—";
    activeSettings.querySelector('[data-setting="audio"]').textContent =
      `${sampleRateLabel(data.sampleRate)}, ${data.channels || "?"} channel(s), ${data.bitDepth || "?"}-bit`;
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

  function applyStatus(s) {
    window.__nfcLastStatus = s;
    updateButton(s);
    updateStopButton(s);
    updateSessionWindow(s);
    updateActiveSettings(s);
    renderStatus(s);
    resumeMeterIfNeeded();
  }

  async function refreshStatus() {
    const r = await fetch("/session/status", { cache: "no-store" });
    const s = await r.json();
    applyStatus(s);
  }

  function connectStatusSocket() {
    const wsProtocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${wsProtocol}://${location.host}/ws/status`);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type !== "status" && m.ty !== "status") return;
      applyStatus(m.data);
    };
    ws.onclose = () => setTimeout(connectStatusSocket, 3000);
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

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) resumeMeterIfNeeded();
  });
  window.addEventListener("focus", resumeMeterIfNeeded);
  document.addEventListener("pointerdown", resumeMeterIfNeeded);
  document.addEventListener("keydown", resumeMeterIfNeeded);

  refreshStatus();
  startLiveMicMeter();
  setInterval(refreshStatus, 3000);
  connectStatusSocket();
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


// ---- Detections folder browser ----
const browseFolderBtn = document.getElementById("browse-folder");
if (browseFolderBtn) {
  browseFolderBtn.addEventListener("click", async () => {
    const pathInput = document.getElementById("folder-path");
    browseFolderBtn.disabled = true;
    const originalText = browseFolderBtn.textContent;
    browseFolderBtn.textContent = "Choosing…";
    try {
      const r = await fetch("/detections/pick-folder", { cache: "no-store" });
      const j = await r.json();
      if (!r.ok || j.error) {
        alert(`${j.error || "Could not open folder picker."}${j.detail ? "\n\n" + j.detail : ""}`);
        return;
      }
      if (j.folder_path) {
        pathInput.value = j.folder_path;
      }
    } catch (e) {
      alert(`Could not open folder picker. The local NFC Tools server may have stopped.\n\n${e}`);
    } finally {
      browseFolderBtn.disabled = false;
      browseFolderBtn.textContent = originalText;
    }
  });
}
