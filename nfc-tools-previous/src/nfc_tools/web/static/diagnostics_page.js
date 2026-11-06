/* NFC Tools diagnostics page controller */

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
  if (resultEl) resultEl.textContent = `Recording 10-second ${variant} test...`;
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
    listEl.textContent = "Listing avfoundation devices...";
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
  if (resultEl) resultEl.textContent = "Recording 10-second sounddevice/CoreAudio 48 kHz float test...";
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
