/* NFC Tools imported-recordings page controller */
(function () {
  const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  const page = document.getElementById("import-recordings-page");
  if (!page) return;

  const state = {
    scan: null,
    timelineConfirmed: false,
    importLocationMap: null,
    timelineEntries: []
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
    if (state.importLocationMap) {
      setTimeout(() => state.importLocationMap.invalidateSize(), 100);
      setTimeout(() => state.importLocationMap.invalidateSize(), 600);
    }
  }

  function setStageLocked(stageId, fieldsetId) {
    const stage = byId(stageId);
    if (stage) {
      stage.classList.add("is-locked");
      stage.setAttribute("aria-disabled", "true");
    }
    const fieldset = fieldsetId ? byId(fieldsetId) : null;
    if (fieldset) fieldset.disabled = true;
  }

  function loadLeaflet() {
    if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = LEAFLET_CSS;
      document.head.appendChild(link);
    }

    if (window.L) return Promise.resolve();

    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${LEAFLET_JS}"]`);
      if (existing) {
        existing.addEventListener("load", resolve, { once: true });
        existing.addEventListener("error", reject, { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = LEAFLET_JS;
      script.async = true;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function parseCoordinatePair(latInput, lonInput) {
    const latValue = Number.parseFloat(String(latInput?.value || "").trim());
    const lonValue = Number.parseFloat(String(lonInput?.value || "").trim());
    if (!Number.isFinite(latValue) || !Number.isFinite(lonValue)) return null;
    if (latValue < -90 || latValue > 90 || lonValue < -180 || lonValue > 180) return null;
    return { lat: latValue, lng: lonValue };
  }

  function getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not available in this browser."));
        return;
      }
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      });
    });
  }

  function updateImportTimezone(latInput, lonInput, options = {}) {
    const point = parseCoordinatePair(latInput, lonInput);
    const timezone = byId("import-timezone");
    const label = byId("import-timezone-label");
    const status = byId("import-location-status");
    if (!point) {
      if (options.showStatus) setStatus(status, "Enter valid coordinates before checking timezone.", true);
      return;
    }

    const body = new FormData();
    body.append("latitude", String(point.lat));
    body.append("longitude", String(point.lng));
    body.append("fallback", timezone?.value || label?.textContent || "UTC");

    fetch("/import-recordings/site-timezone", { method: "POST", body })
      .then(response => response.ok ? response.json() : null)
      .then(payload => {
        if (!payload?.timezone) return;
        if (timezone) timezone.value = payload.timezone;
        if (label) label.textContent = payload.timezone;
        if (options.showStatus) setStatus(status, "Location updated for this import.");
      })
      .catch(() => {
        if (options.showStatus) {
          setStatus(status, "Timezone could not be checked. Review the coordinates before processing.", true);
        }
      });
  }

  function setLatLon(latInput, lonInput, marker, latLng) {
    latInput.value = Number(latLng.lat).toFixed(7);
    lonInput.value = Number(latLng.lng).toFixed(7);
    latInput.dispatchEvent(new Event("input", { bubbles: true }));
    lonInput.dispatchEvent(new Event("input", { bubbles: true }));
    latInput.dispatchEvent(new Event("change", { bubbles: true }));
    lonInput.dispatchEvent(new Event("change", { bubbles: true }));
    if (marker) {
      marker.setLatLng(latLng);
      marker.setPopupContent(`Recording location<br>(${Number(latInput.value).toFixed(7)}, ${Number(lonInput.value).toFixed(7)})`);
    }
  }

  function initImportLocationMap() {
    const lat = byId("import-latitude");
    const lon = byId("import-longitude");
    const map = byId("import-location-map");
    const currentLocationButton = byId("import-current-location");
    const status = byId("import-location-status");
    if (!lat || !lon || !map || !currentLocationButton) return;

    const parsed = parseCoordinatePair(lat, lon);
    const currentLat = parsed ? parsed.lat : 42.415;
    const currentLon = parsed ? parsed.lng : -71.156;

    loadLeaflet()
      .then(() => {
        const leafletMap = L.map(map).setView([currentLat, currentLon], 13);
        state.importLocationMap = leafletMap;
        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
          maxZoom: 20,
          attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
        }).addTo(leafletMap);

        const marker = L.marker([currentLat, currentLon], { draggable: true }).addTo(leafletMap);
        marker.bindPopup(`Recording location<br>(${currentLat.toFixed(7)}, ${currentLon.toFixed(7)})`).openPopup();

        let saveTimer = null;
        function scheduleTimezoneUpdate(delay = 650, options = {}) {
          clearTimeout(saveTimer);
          saveTimer = setTimeout(() => updateImportTimezone(lat, lon, options), delay);
        }

        function moveToPoint(latLng, options = {}) {
          setLatLon(lat, lon, marker, latLng);
          if (options.pan !== false) leafletMap.panTo(latLng, { animate: false });
          scheduleTimezoneUpdate(options.delay ?? 650, { showStatus: Boolean(options.showStatus) });
        }

        function updateMapFromTypedCoordinates() {
          const point = parseCoordinatePair(lat, lon);
          if (!point) {
            setStatus(status, "Coordinates must be valid latitude and longitude values.", true);
            return;
          }
          const latLng = L.latLng(point.lat, point.lng);
          marker.setLatLng(latLng);
          marker.setPopupContent(`Recording location<br>(${point.lat.toFixed(7)}, ${point.lng.toFixed(7)})`);
          leafletMap.panTo(latLng, { animate: false });
          scheduleTimezoneUpdate(650, { showStatus: true });
        }

        async function setToCurrentLocation() {
          const oldText = currentLocationButton.textContent;
          currentLocationButton.disabled = true;
          currentLocationButton.textContent = "Locating...";
          setStatus(status, "Checking this computer's location...");
          try {
            const pos = await getCurrentPosition();
            const latLng = L.latLng(pos.coords.latitude, pos.coords.longitude);
            moveToPoint(latLng, { delay: 100, showStatus: true });
          } catch (error) {
            setStatus(status, "Location is unavailable. Move the map marker instead.", true);
          } finally {
            setTimeout(() => {
              currentLocationButton.disabled = false;
              currentLocationButton.textContent = oldText;
            }, 900);
          }
        }

        leafletMap.on("click", event => moveToPoint(event.latlng, { showStatus: true }));
        marker.on("dragend", () => moveToPoint(marker.getLatLng(), { showStatus: true }));
        currentLocationButton.addEventListener("click", setToCurrentLocation);
        [lat, lon].forEach(input => {
          input.addEventListener("change", updateMapFromTypedCoordinates);
        });

        setTimeout(() => leafletMap.invalidateSize(), 200);
        setTimeout(() => leafletMap.invalidateSize(), 1000);
        updateImportTimezone(lat, lon);
      })
      .catch(() => {
        map.textContent = "Map unavailable.";
      });
  }

  function foldersSelected() {
    const source = byId("import-source-folder");
    const output = byId("import-output-folder");
    return Boolean(source?.value && output?.value);
  }

  function updateReviewButtonState() {
    const reviewButton = byId("scan-and-build-import-review");
    const readyForSession = foldersSelected();
    if (readyForSession) setStageUnlocked("import-stage-session", "import-session-fields");
    if (!reviewButton) return;
    reviewButton.disabled = !readyForSession;
  }

  function resetReviewResults() {
    state.scan = null;
    state.timelineConfirmed = false;
    state.timelineEntries = [];

    const scanSummary = byId("import-scan-summary");
    if (scanSummary) {
      scanSummary.hidden = true;
      scanSummary.innerHTML = "";
    }

    const timelineSummary = byId("timeline-suggestion-summary");
    if (timelineSummary) {
      timelineSummary.classList.remove("needs-review");
      timelineSummary.textContent = "Choose folders and session details, then scan and build the timeline review.";
    }

    const tableBody = byId("import-timeline-table")?.querySelector("tbody");
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5">Scan and build the timeline review.</td>
        </tr>
      `;
    }

    const confirmButton = byId("confirm-import-timeline");
    if (confirmButton) confirmButton.disabled = true;
    const responsibilityCheck = byId("timeline-responsibility-check");
    if (responsibilityCheck) responsibilityCheck.checked = false;
    const storageButton = byId("confirm-import-storage");
    if (storageButton) storageButton.disabled = true;
    const tree = byId("planned-output-tree");
    if (tree) tree.textContent = "Confirm the timeline to preview the archive\nstructure.";
    const estimate = byId("import-storage-estimate");
    if (estimate) estimate.textContent = "Confirm the timeline to review storage estimates.";

    setStageLocked("import-stage-timeline");
    setStageLocked("import-stage-output");
    setStageLocked("import-stage-run");
  }

  function setFolder(kind, path, display) {
    const valueInput = byId(`import-${kind}-folder`);
    const displayInput = byId(`import-${kind}-folder-display`);
    const previous = valueInput?.value || "";
    if (valueInput) valueInput.value = path || "";
    if (displayInput) displayInput.value = display || path || `No ${kind} folder selected`;
    if (previous !== (path || "")) resetReviewResults();
    updateReviewButtonState();
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

  async function scanAndBuildTimelineReview() {
    const reviewButton = byId("scan-and-build-import-review");
    const status = byId("import-session-status");
    const source = byId("import-source-folder");
    const output = byId("import-output-folder");
    if (!reviewButton || !source || !output) return;

    if (!foldersSelected()) {
      setStatus(status, "Choose a source folder and an output folder first.", true);
      return;
    }
    resetReviewResults();
    reviewButton.disabled = true;
    reviewButton.textContent = "Scanning...";
    setStatus(status, "Scanning folders and building the timeline review...");

    const body = new FormData();
    body.append("source_folder", source.value);
    body.append("output_folder", output.value);

    try {
      const response = await fetch("/import-recordings/scan", { method: "POST", body });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        setStatus(status, payload.error || "Scan did not finish.", true);
        return;
      }
      state.scan = payload;
      state.timelineConfirmed = false;
      renderScanSummary(payload);
      buildTimelineReview();
    } catch (error) {
      setStatus(status, "Scan did not finish.", true);
    } finally {
      reviewButton.textContent = "Scan and build timeline review";
      updateReviewButtonState();
    }
  }

  function detectedStartToInputValue(value) {
    if (!value) return null;
    const text = String(value).trim().replace(" ", "T");
    return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(text) ? text : null;
  }

  function addSecondsToInputValue(value, seconds) {
    if (!value || !Number.isFinite(seconds)) return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    const next = new Date(parsed.getTime() + Math.max(0, Number(seconds) || 0) * 1000);
    const pad = number => String(number).padStart(2, "0");
    return (
      `${next.getFullYear()}-${pad(next.getMonth() + 1)}-${pad(next.getDate())}` +
      `T${pad(next.getHours())}:${pad(next.getMinutes())}:${pad(next.getSeconds())}`
    );
  }

  function sourceLabel(source) {
    if (source === "filename") return "Filename";
    if (source === "sequence") return "Nearby time + duration";
    if (source === "manual") return "Edited by user";
    return "Needs entry";
  }

  function buildTimelineEntries(files) {
    let nextSequentialStart = null;
    return files.map((file, index) => {
      const filenameStart = detectedStartToInputValue(file.detected_start);
      let value = "";
      let source = "missing";
      if (filenameStart) {
        value = filenameStart;
        source = "filename";
      } else if (nextSequentialStart) {
        value = nextSequentialStart;
        source = "sequence";
      }

      if (value && Number.isFinite(file.duration_seconds)) {
        nextSequentialStart = addSecondsToInputValue(value, file.duration_seconds);
      } else if (filenameStart && !Number.isFinite(file.duration_seconds)) {
        nextSequentialStart = null;
      } else if (!value) {
        nextSequentialStart = null;
      }

      return {
        index,
        file,
        value,
        source,
        manual: false
      };
    });
  }

  function timelineReviewState() {
    const entries = state.timelineEntries || [];
    const totalFiles = state.scan?.source?.audio_count || 0;
    const hiddenCount = state.scan?.source?.review_hidden_count || 0;
    const reviewedVisibleCount = entries.filter(entry => entry.value).length;
    const filenameCount = entries.filter(entry => entry.source === "filename").length;
    const sequenceCount = entries.filter(entry => entry.source === "sequence").length;
    const manualCount = entries.filter(entry => entry.source === "manual").length;
    const missingCount = entries.length - reviewedVisibleCount;
    const responsibilityChecked = Boolean(byId("timeline-responsibility-check")?.checked);
    const canConfirm = (
      entries.length > 0 &&
      missingCount === 0 &&
      hiddenCount === 0 &&
      responsibilityChecked
    );

    return {
      canConfirm,
      entries,
      totalFiles,
      hiddenCount,
      reviewedVisibleCount,
      filenameCount,
      sequenceCount,
      manualCount,
      missingCount,
      responsibilityChecked
    };
  }

  function entryStatus(entry) {
    if (!entry.value) return "Needs a start time";
    if (entry.source === "filename") return "Suggested, check before confirming";
    if (entry.source === "sequence") return "Suggested from file order and duration";
    return "Edited, check before confirming";
  }

  function renderTimelineRows() {
    const tableBody = byId("import-timeline-table")?.querySelector("tbody");
    if (!tableBody) return;
    const entries = state.timelineEntries || [];
    if (!entries.length) {
      tableBody.innerHTML = `<tr><td colspan="5">No supported audio files were found.</td></tr>`;
      return;
    }

    tableBody.innerHTML = entries.map(entry => `
      <tr>
        <td>${escapeHtml(entry.file.relative_path || entry.file.name)}</td>
        <td>
          <input
            type="datetime-local"
            step="1"
            value="${escapeHtml(entry.value)}"
            data-timeline-index="${entry.index}"
            aria-label="Start time for ${escapeHtml(entry.file.relative_path || entry.file.name)}"
          >
        </td>
        <td>${escapeHtml(entry.file.duration_display)}</td>
        <td data-source-index="${entry.index}">${escapeHtml(sourceLabel(entry.source))}</td>
        <td data-status-index="${entry.index}">${escapeHtml(entryStatus(entry))}</td>
      </tr>
    `).join("");

    tableBody.querySelectorAll("input[data-timeline-index]").forEach(input => {
      input.addEventListener("input", event => {
        const index = Number(event.target.dataset.timelineIndex);
        const entry = state.timelineEntries[index];
        if (!entry) return;
        entry.value = event.target.value;
        entry.source = entry.value ? "manual" : "missing";
        entry.manual = Boolean(entry.value);
        updateTimelineReviewState();
      });
    });
  }

  function renderTimelineGuidance(reviewState) {
    const summary = byId("timeline-suggestion-summary");
    if (!summary || !reviewState) return;

    let title = "Timeline draft";
    let message = "Review the suggested start times, edit anything wrong, then confirm.";

    if (!reviewState.totalFiles) {
      title = "No timeline to review";
      message = "No supported audio files were found in the selected source folder.";
    } else if (reviewState.hiddenCount > 0) {
      title = "Bulk review is capped";
      message = (
        `Showing ${reviewState.entries.length} of ${reviewState.totalFiles} files. ` +
        "Confirmation is disabled until NFC Tools has a paged all-file review."
      );
    } else if (reviewState.missingCount > 0) {
      title = "Start times need review";
      message = (
        `NFC Tools pre-filled ${reviewState.reviewedVisibleCount} of ${reviewState.entries.length} start times. ` +
        "Fill the remaining rows before confirming."
      );
    } else {
      title = "All visible files have start times";
      message = (
        `${reviewState.filenameCount} from filenames, ${reviewState.sequenceCount} from nearby times and durations, ` +
        `${reviewState.manualCount} edited by you. Check them before confirming.`
      );
    }

    summary.classList.toggle("needs-review", !reviewState.canConfirm);
    summary.innerHTML = `
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(message)}</p>
    `;
  }

  function updateTimelineReviewState() {
    const reviewState = timelineReviewState();
    const confirmButton = byId("confirm-import-timeline");
    if (confirmButton) confirmButton.disabled = !reviewState.canConfirm;
    renderTimelineGuidance(reviewState);

    reviewState.entries.forEach(entry => {
      const source = document.querySelector(`[data-source-index="${entry.index}"]`);
      const status = document.querySelector(`[data-status-index="${entry.index}"]`);
      if (source) source.textContent = sourceLabel(entry.source);
      if (status) status.textContent = entryStatus(entry);
    });
  }

  function buildTimelineReview() {
    const status = byId("import-session-status");
    if (!state.scan) return;

    state.timelineEntries = buildTimelineEntries(state.scan.source.review_files || []);
    renderTimelineRows();
    setStageUnlocked("import-stage-timeline");
    updateTimelineReviewState();
    const reviewState = timelineReviewState();
    if (reviewState.canConfirm) {
      setStatus(status, "Timeline review built. Review it carefully before confirming.");
    } else if (reviewState.hiddenCount > 0) {
      setStatus(status, "Timeline review is capped for this large import.", true);
    } else {
      setStatus(status, "Timeline review needs more information before it can be confirmed.", true);
    }
  }

  function dateForOutputPlan() {
    const reviewed = (state.timelineEntries || []).find(entry => entry.value)?.value;
    if (reviewed) return reviewed.slice(0, 10);
    const detected = (state.scan?.source?.review_files || []).find(file => file.detected_start)?.detected_start;
    if (detected) return String(detected).slice(0, 10);
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

  initImportLocationMap();
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

  byId("scan-and-build-import-review")?.addEventListener("click", scanAndBuildTimelineReview);
  byId("confirm-import-timeline")?.addEventListener("click", confirmTimeline);
  byId("confirm-import-storage")?.addEventListener("click", confirmStoragePlan);
  byId("timeline-responsibility-check")?.addEventListener("change", updateTimelineReviewState);
  updateReviewButtonState();
})();
