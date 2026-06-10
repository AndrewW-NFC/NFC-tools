// NFC Tools - small, no-framework UI script.

// ---- Wizard helpers ----
const lookupBtn = document.getElementById("lookup");
if (lookupBtn) {
  lookupBtn.addEventListener("click", async () => {
	const q = document.getElementById("locq").value;
	const fd = new FormData();
	fd.append("query", q);
	const r = await fetch("/wizard/geocode", { method: "POST", body: fd });
	const j = await r.json();
	if (j.error) { alert("Couldn't find that place."); return; }
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
	if (j.error) { out.textContent = j.error; return; }
	out.textContent = `Peak: ${j.peak_db ?? "?"} dB - Mean: ${j.mean_db ?? "?"} dB - ${j.hint}`;
  });
}

// ---- Sun-based presets (used in wizard and settings) ----
const loadPresetsBtn = document.getElementById("loadPresets");
if (loadPresetsBtn) {
  loadPresetsBtn.addEventListener("click", async () => {
	const lat = document.getElementById("lat").value;
	const lon = document.getElementById("lon").value;
	const tz  = document.getElementById("tz").value;
	const r = await fetch(`/api/sun-presets?lat=${lat}&lon=${lon}&tz=${encodeURIComponent(tz)}`);
	const presets = await r.json();
	const list = document.getElementById("presetList");
	list.innerHTML = presets.map(p => `
	  <div class="preset">
		<strong>${p.label}</strong> (${p.start_time}-${p.end_time}) -
		<span class="muted">${p.description}</span>
		<button type="button" data-start="${p.start_time}" data-end="${p.end_time}" class="usePreset">Use</button>
	  </div>`).join("");
	list.querySelectorAll(".usePreset").forEach(b => b.addEventListener("click", () => {
	  document.querySelector('input[name="start_time"]').value = b.dataset.start;
	  document.querySelector('input[name="end_time"]').value   = b.dataset.end;
	}));
  });
}

// ---- Dashboard live status ----
const stateEl = document.getElementById("state");
if (stateEl) {
  const meta = document.getElementById("meta");
  const fill = document.getElementById("meter-fill");
  const meterLabel = document.getElementById("meter-label");
  const recordings = document.getElementById("recordings");

  const ws = new WebSocket(`ws://${location.host}/ws/status`);
  ws.onmessage = (ev) => {
	const m = JSON.parse(ev.data);
	if (m.type !== "status") return;
	const s = m.data;
	stateEl.textContent = s.state;
	if (s.session_date) {
	  meta.textContent = `Session: ${s.session_date} - ends at ${s.ends_at ?? "?"}`;
	}
	if (typeof s.level_db === "number") {
	  const pct = Math.max(0, Math.min(100, (s.level_db + 60) * (100 / 60)));
	  fill.style.width = `${pct}%`;
	  meterLabel.textContent = `${s.level_db.toFixed(1)} dB`;
	}
	if (Array.isArray(s.recordings)) {
	  recordings.innerHTML = s.recordings.map(r => `<li>${r}</li>`).join("");
	}
  };

  document.getElementById("start").addEventListener("click", async () => {
	await fetch("/session/start", { method: "POST" });
  });
  document.getElementById("stop").addEventListener("click", async () => {
	await fetch("/session/stop", { method: "POST" });
  });
}

// ---- Settings: install buttons ----
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
