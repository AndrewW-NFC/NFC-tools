/* NFC Tools imported-recordings page controller */
(function () {
  const page = document.getElementById("import-recordings-page");
  if (!page) return;

  const state = {
    scan: null,
    timelineConfirmed: false
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setStatus(el, message, isError = false) {
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("error", isError);
  }

  function setStageUnlocked(stageId, fieldsetId) {
    const stage = byId(stageId);
    if (stage) {
      stage.classList.remove("is-locked");
      stage.setAttribute("aria-disabled", "false");
    }
    const fieldset = fieldsetId ? byId(fieldsetId) : null;
    if (fieldset) fieldset.disabled = false;
  }

  function updateScanButtonState() {
    const scanButton = byId("scan-import-folders");
    const source = byId("import-source-folder");
    const output = byId("import-output-folder");
    if (!scanButton || !source || !output) return;
    scanButton.disabled = !(source.value && output.value);
  }

  function setFolder(kind, path, display) {
    const valueInput = byId(`import-${kind}-folder`);
    const displayInput = byId(`import-${kind}-folder-display`);
    if (valueInput) valueInput.value = path || "";
    if (displayInput) displayInput.value = display || path || `No ${kind} folder selected`;
    updateScanButtonState();
  }

  function initFolderPicker(kind, endpoint, currentFieldName) {
    const button = byId(`choose-import-${kind}-folder`);
    const valueInput = byId(`import-${kind}-folder`);
    const status = byId(`import-${kind}-folder-status`);
    if (!button || !valueInput) return;

    button.addEventListener("click", async () => {
      const originalText = button.textContent;
      button.disabled = true;
      button.textContent = "Choosing...";
      setStatus(status, "Opening folder chooser...");

      const body = new FormData();
      body.append(currentFieldName, valueInput.value);

      try {
        const response = await fetch(endpoint, { method: "POST", body });
        const payload = await response.json().catch(() => ({}));
        if (payload.ok && payload.path) {
          setFolder(kind, payload.path, payload.display || payload.path);
          setStatus(status, "Folder selected.");
        } else if (payload.cancelled) {
          setStatus(status, "No folder selected.");
        } else {
          setStatus(status, payload.error || "Folder chooser could not be opened.", true);
        }
      } catch (error) {
        setStatus(status, "Folder chooser could not be opened.", true);
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    });
  }

  function extensionSummary(counts) {
    const entries = Object.entries(counts || {});
    if (!entries.length) return "None";
    return entries.map(([ext, count]) => `${escapeHtml(ext)}: ${count}`).join(", ");
  }

  function renderSampleRows(samples) {
    if (!samples || !samples.length) {
      return `<p class="muted">No supported audio files found in the selected source folder.</p>`;
    }
    const rows = samples.map(file => `
      <tr>
        <td>${escapeHtml(file.relative_path || file.name)}</td>
        <td>${escapeHtml(file.size_display)}</td>
        <td>${escapeHtml(file.duration_display)}</td>
        <td>${escapeHtml(file.detected_start || "Not detected")}</td>
      </tr>
    `).join("");
    return `
      <div class="timeline-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sample file</th>
              <th>Size</th>
              <th>Duration</th>
              <th>Filename time</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function renderScanSummary(payload) {
    const summary = byId("import-scan-summary");
    if (!summary) return;
    const warnings = (payload.warnings || []).map(warning => `<li>${escapeHtml(warning)}</li>`).join("");
    const scanErrors = (payload.source.errors || []).map(error => `<li>${escapeHtml(error)}</li>`).join("");
    summary.innerHTML = `
      <h3>Scan summary</h3>
      <dl class="compact-dl">
        <div>
          <dt>Audio files found</dt>
          <dd>${payload.source.audio_count}</dd>
        </div>
        <div>
          <dt>Source audio size</dt>
          <dd>${escapeHtml(payload.source.source_display)}</dd>
        </div>
        <div>
          <dt>Formats found</dt>
          <dd>${extensionSummary(payload.source.extension_counts)}</dd>
        </div>
        <div>
          <dt>Output free space</dt>
          <dd>${escapeHtml(payload.output.free_display)} free of ${escapeHtml(payload.output.total_display)}</dd>
        </div>
      </dl>
      ${warnings
        ? `<div class="notice warning"><strong>Check this before processing:</strong><ul>${warnings}</ul></div>`
        : ""}
      ${scanErrors
        ? `<div class="notice warning"><strong>Some files or folders could not be scanned:</strong>`
          + `<ul>${scanErrors}</ul></div>`
        : ""}
      ${renderSampleRows(payload.source.samples)}
    `;
    summary.hidden = false;
  }

  async function scanFolders() {
    const scanButton = byId("scan-import-folders");
    const scanStatus = byId("import-scan-status");
    const source = byId("import-source-folder");
    const output = byId("import-output-folder");
    if (!scanButton || !source || !output) return;

    scanButton.disabled = true;
    scanButton.textContent = "Scanning...";
    setStatus(scanStatus, "Scanning selected folders...");

    const body = new FormData();
    body.append("source_folder", source.value);
    body.append("output_folder", output.value);

    try {
      const response = await fetch("/import-recordings/scan", { method: "POST", body });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        setStatus(scanStatus, payload.error || "Scan did not finish.", true);
        return;
      }
      state.scan = payload;
      state.timelineConfirmed = false;
      renderScanSummary(payload);
      setStageUnlocked("import-stage-session", "import-session-fields");
      setStatus(scanStatus, "Scan complete. Review the session details next.");
    } catch (error) {
      setStatus(scanStatus, "Scan did not finish.", true);
    } finally {
      scanButton.disabled = !(source.value && output.value);
      scanButton.textContent = "Scan recordings";
    }
  }

  function selectedTimingMode() {
    const selected = document.querySelector('input[name="import-timing-mode"]:checked');
    return selected ? selected.value : "sequential";
  }

  function parseFirstStart() {
    const date = byId("import-start-date")?.value;
    const time = byId("import-start-time")?.value;
    if (!date || !time) return null;
    const parsed = new Date(`${date}T${time}`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function parseDetectedStart(value) {
    if (!value) return null;
    const parsed = new Date(String(value).replace(" ", "T"));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function formatDateTime(value) {
    if (!value) return "Needs review";
    return value.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit"
    });
  }

  function addSeconds(value, seconds) {
    return new Date(value.getTime() + Math.max(0, Number(seconds) || 0) * 1000);
  }

  function timelineRowsForSamples() {
    const samples = state.scan?.source?.samples || [];
    if (!samples.length) {
      return {
        rows: [
          `<tr><td colspan="4">No supported audio files were found.</td></tr>`
        ],
        canConfirm: false
      };
    }

    const mode = selectedTimingMode();
    const rows = [];
    let canConfirm = false;

    if (mode === "sequential") {
      let current = parseFirstStart();
      canConfirm = Boolean(current);
      if (!current) {
        return {
          rows: [
            `<tr><td colspan="4">Enter the first recording date and start time to preview sequential files.</td></tr>`
          ],
          canConfirm: false
        };
      }
      for (const file of samples) {
        const startText = formatDateTime(current);
        const durationKnown = Number.isFinite(file.duration_seconds);
        const startKnown = Boolean(current);
        rows.push(`
          <tr>
            <td>${escapeHtml(file.relative_path || file.name)}</td>
            <td>${escapeHtml(startText)}</td>
            <td>${escapeHtml(file.duration_display)}</td>
            <td>${startKnown && durationKnown ? "Ready for review" : "Needs review before processing"}</td>
          </tr>
        `);
        if (startKnown && durationKnown) {
          current = addSeconds(current, file.duration_seconds);
        } else {
          current = null;
          canConfirm = false;
        }
      }
    } else if (mode === "filename") {
      for (const file of samples) {
        const detected = parseDetectedStart(file.detected_start);
        if (detected) canConfirm = true;
        rows.push(`
          <tr>
            <td>${escapeHtml(file.relative_path || file.name)}</td>
            <td>${escapeHtml(formatDateTime(detected))}</td>
            <td>${escapeHtml(file.duration_display)}</td>
            <td>${detected ? "Detected from filename, must be confirmed" : "No date or time detected"}</td>
          </tr>
        `);
      }
    } else {
      for (const file of samples) {
        rows.push(`
          <tr>
            <td>${escapeHtml(file.relative_path || file.name)}</td>
            <td>Needs per-file entry</td>
            <td>${escapeHtml(file.duration_display)}</td>
            <td>Per-file editor will be needed before processing</td>
          </tr>
        `);
      }
      canConfirm = false;
    }

    return { rows, canConfirm };
  }

  function buildTimelineReview() {
    const status = byId("import-session-status");
    const tableBody = byId("import-timeline-table")?.querySelector("tbody");
    const confirmButton = byId("confirm-import-timeline");
    if (!state.scan || !tableBody) return;

    const preview = timelineRowsForSamples();
    tableBody.innerHTML = preview.rows.join("");
    setStageUnlocked("import-stage-timeline");
    if (confirmButton) confirmButton.disabled = !preview.canConfirm;
    if (preview.canConfirm) {
      setStatus(status, "Timeline preview built. Review it carefully before confirming.");
    } else {
      setStatus(status, "Timeline preview needs more information before it can be confirmed.", true);
    }
  }

  function dateForOutputPlan() {
    const dateText = byId("import-start-date")?.value;
    if (dateText) return dateText;
    const firstStart = parseFirstStart();
    if (firstStart) return formatDateTime(firstStart).split(",")[0] || "selected-night";
    const detected = (state.scan?.source?.samples || []).find(file => file.detected_start)?.detected_start;
    if (detected) return detected.slice(0, 10);
    return "selected-night";
  }

  function renderOutputTree() {
    const tree = byId("planned-output-tree");
    const outputDisplay = byId("import-output-folder-display")?.value || "selected output folder";
    const sessionDate = dateForOutputPlan();
    if (!tree) return;
    tree.textContent = `${outputDisplay}/
  ${sessionDate}/
    audio/
      001_NFC_CIVIL_EVENING_${sessionDate}_...
      002_NFC_${sessionDate}_...
      003_NFC_CIVIL_MORNING_${sessionDate}_...
    results/
      birdnet/
      nighthawk/
    clips/
      HH-MM-SS/
    logs/
    manifest.csv`;
  }

  function renderEstimate() {
    const panel = byId("import-storage-estimate");
    const estimate = state.scan?.estimate;
    if (!panel || !estimate) return;
    const estimateStatus = String(estimate.status || "").replace(/[^a-z-]/g, "") || "tight";
    panel.innerHTML = `
      <dl class="compact-dl estimate-list">
        <div>
          <dt>Processed audio</dt>
          <dd>${escapeHtml(estimate.processed_audio.display)}</dd>
        </div>
        <div>
          <dt>Analyzer results</dt>
          <dd>${escapeHtml(estimate.analyzer_results.display)}</dd>
        </div>
        <div>
          <dt>Review clips</dt>
          <dd>${escapeHtml(estimate.clips.display)}</dd>
        </div>
        <div>
          <dt>Total estimate</dt>
          <dd>${escapeHtml(estimate.total.display)}</dd>
        </div>
      </dl>
      <p class="estimate-status estimate-${estimateStatus}">${escapeHtml(estimate.message)}</p>
    `;
  }

  function confirmTimeline() {
    state.timelineConfirmed = true;
    setStageUnlocked("import-stage-output");
    renderOutputTree();
    renderEstimate();
    const storageButton = byId("confirm-import-storage");
    if (storageButton) storageButton.disabled = false;
  }

  function confirmStoragePlan() {
    setStageUnlocked("import-stage-run");
  }

  initFolderPicker(
    "source",
    "/import-recordings/choose-source-folder",
    "current_source_folder"
  );
  initFolderPicker(
    "output",
    "/import-recordings/choose-output-folder",
    "current_output_folder"
  );

  byId("scan-import-folders")?.addEventListener("click", scanFolders);
  byId("build-import-timeline")?.addEventListener("click", buildTimelineReview);
  byId("confirm-import-timeline")?.addEventListener("click", confirmTimeline);
  byId("confirm-import-storage")?.addEventListener("click", confirmStoragePlan);
  updateScanButtonState();
})();
