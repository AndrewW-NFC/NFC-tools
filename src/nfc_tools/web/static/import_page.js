/* NFC Tools imported-recordings page controller */
(function () {
  const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  const page = document.getElementById("import-recordings-page");
  if (!page) return;

  const state = {
    scan: null,
    timelineConfirmed: false,
    storageConfirmed: false,
    job: null,
    submitting: false,
    planSubmitted: false,
    recovering: false,
    scanning: false,
    logCursor: 0,
    logJobId: null,
    restoredJobId: null,
    ignoredJobId: null,
    requestId: null,
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

  function analyzerText(value) {
    return String(value || "").replace(/\bbirdnet\b/gi, "BirdNET").replace(/\bnighthawk\b/gi, "Nighthawk");
  }

  function setupLocked() {
    return state.submitting || state.recovering || state.scanning || state.planSubmitted;
  }

  function timelineReadyToStart() {
    return state.timelineConfirmed && state.storageConfirmed && timelineReviewState().canConfirm;
  }

  function setHidden(el, hidden) {
    if (el) el.hidden = hidden;
  }

  function createRequestId() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    const values = new Uint8Array(16);
    globalThis.crypto?.getRandomValues?.(values);
    if (!values.some(Boolean)) {
      for (let index = 0; index < values.length; index += 1) values[index] = Math.floor(Math.random() * 256);
    }
    values[6] = (values[6] & 0x0f) | 0x40;
    values[8] = (values[8] & 0x3f) | 0x80;
    const hex = Array.from(values, value => value.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  function syncSetupUI() {
    const locked = setupLocked();
    byId("import-setup-fields").disabled = locked;
    byId("import-location-map").inert = locked;
    setStatus(byId("import-setup-status"), state.recovering ? "Checking for an existing run…" :
      state.submitting ? "Submitting the confirmed plan…" : state.scanning ? "Scanning recordings…" :
      state.planSubmitted ? "Steps 1–4 are confirmed and read-only for this run." : "Complete and confirm each step before starting.");
    const labels = {
      folders: [foldersSelected(), "Folders selected", "Awaiting folders"],
      session: [Boolean(state.scan), "Details reviewed", "Awaiting details and scan"],
      timeline: [state.timelineConfirmed, "Timeline confirmed", state.scan ? "Needs review" : "Awaiting scan"],
      output: [state.storageConfirmed, "Storage plan confirmed", state.timelineConfirmed ? "Ready for review" : "Awaiting timeline confirmation"]
    };
    Object.entries(labels).forEach(([key, [complete, done, pending]]) => {
      const badge = byId(`import-step-status-${key}`);
      badge.textContent = complete ? done : pending;
      badge.classList.toggle("is-complete", complete);
    });
    byId("confirm-import-timeline").textContent = state.timelineConfirmed ? "Timeline confirmed" : "Confirm timeline";
    byId("confirm-import-timeline").disabled = state.timelineConfirmed || !timelineReviewState().canConfirm;
    byId("confirm-import-storage").textContent = state.storageConfirmed ? "Storage plan confirmed" : "Confirm storage plan";
    byId("confirm-import-storage").disabled = !state.timelineConfirmed || state.storageConfirmed;
    byId("start-import-run").disabled = locked || !timelineReadyToStart();
  }

  function rememberLocation() {
    if (setupLocked() || !parseCoordinatePair(byId("import-latitude"), byId("import-longitude"))) return;
    const timezone = byId("import-timezone").value.trim();
    try {
      new Intl.DateTimeFormat("en", { timeZone: timezone });
      const saved = {};
      ["site-name", "latitude", "longitude", "timezone", "ebird-state-province"].forEach(key => {
        saved[key] = byId(`import-${key}`).value;
      });
      localStorage.setItem("nfc-import-location", JSON.stringify(saved));
    } catch (_) { /* Invalid timezone or browser storage unavailable. */ }
  }

  function restoreLocation() {
    try {
      const saved = JSON.parse(localStorage.getItem("nfc-import-location") || "null");
      if (!saved || !parseCoordinatePair({ value: saved.latitude }, { value: saved.longitude })) return;
      new Intl.DateTimeFormat("en", { timeZone: saved.timezone });
      ["site-name", "latitude", "longitude", "timezone", "ebird-state-province"].forEach(key => {
        if (typeof saved[key] === "string") byId(`import-${key}`).value = saved[key];
      });
      byId("import-timezone-label").textContent = saved.timezone;
      setStatus(byId("import-location-status"), "Last-used import location restored. Check it for these recordings.");
    } catch (_) { /* Use Settings defaults if no valid saved location exists. */ }
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
    if (setupLocked()) return;
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
        if (setupLocked() || Number(latInput.value) !== point.lat || Number(lonInput.value) !== point.lng) return;
        if (!payload?.timezone) return;
        if (timezone && timezone.value !== payload.timezone) {
          timezone.value = payload.timezone;
          invalidateTimelineConfirmation();
          updateTimelineReviewState();
        }
        if (label) label.textContent = payload.timezone;
        if (options.showStatus) setStatus(status, "Location updated for this import.");
        rememberLocation();
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
        state.importLocationMarker = marker;
        marker.bindPopup(`Recording location<br>(${currentLat.toFixed(7)}, ${currentLon.toFixed(7)})`).openPopup();
        const latestPoint = parseCoordinatePair(lat, lon);
        if (latestPoint) {
          leafletMap.setView([latestPoint.lat, latestPoint.lng], 13);
          marker.setLatLng(latestPoint);
          marker.setPopupContent(`Recording location<br>(${latestPoint.lat.toFixed(7)}, ${latestPoint.lng.toFixed(7)})`);
        }

        let saveTimer = null;
        function scheduleTimezoneUpdate(delay = 650, options = {}) {
          clearTimeout(saveTimer);
          saveTimer = setTimeout(() => updateImportTimezone(lat, lon, options), delay);
        }

        function moveToPoint(latLng, options = {}) {
          if (setupLocked()) return;
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
        // Keep a remembered or manually entered timezone until coordinates change.
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
    syncSetupUI();
  }

  function resetReviewResults() {
    state.requestId = null;
    state.planSubmitted = false;
    state.scan = null;
    state.timelineConfirmed = false;
    state.storageConfirmed = false;
    byId("start-import-run").disabled = true;
    byId("start-import-run").hidden = false;
    state.timelineEntries = [];
    byId("apply-import-time-shift").disabled = true;
    byId("import-shift-hours").value = "0";
    byId("import-shift-minutes").value = "0";
    setStatus(byId("import-shift-status"), "");

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
    syncSetupUI();
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
      if (setupLocked()) return;
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
    if (setupLocked()) return;
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
    state.scanning = true;
    syncSetupUI();
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
      state.storageConfirmed = false;
      renderScanSummary(payload);
      buildTimelineReview();
    } catch (error) {
      setStatus(status, "Scan did not finish.", true);
    } finally {
      state.scanning = false;
      reviewButton.textContent = "Scan and build timeline review";
      updateReviewButtonState();
    }
  }

  function detectedStartToInputValue(value) {
    if (!value) return null;
    const text = String(value).trim().replace(" ", "T");
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(text)) return null;
    const full = text.length === 16 ? `${text}:00` : text;
    const date = new Date(`${full}Z`);
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 19) === full ? full : null;
  }

  function addSecondsToInputValue(value, seconds) {
    if (!value || !Number.isFinite(seconds)) return null;
    // Treat recorder readings as wall-clock values, independent of browser timezone/DST.
    const parsed = new Date(`${value}Z`);
    if (Number.isNaN(parsed.getTime())) return null;
    const next = new Date(parsed.getTime() + seconds * 1000);
    if (!Number.isFinite(next.getTime()) || next.getUTCFullYear() < 1 || next.getUTCFullYear() > 9999) return null;
    return next.toISOString().slice(0, 19);
  }

  function invalidateTimelineConfirmation() {
    if (state.planSubmitted) return;
    state.timelineConfirmed = false;
    state.storageConfirmed = false;
    byId("start-import-run").disabled = true;
    byId("timeline-responsibility-check").checked = false;
    byId("confirm-import-storage").disabled = true;
    byId("planned-output-tree").textContent = "Confirm the timeline to preview the archive structure.";
    byId("import-storage-estimate").textContent = "Confirm the timeline to review storage estimates.";
    setStageLocked("import-stage-output");
    setStageLocked("import-stage-run");
    setStatus(byId("import-session-status"), "Details or times changed. Review and confirm the timeline again.");
    syncSetupUI();
  }

  function applyTimeShift() {
    if (setupLocked()) return;
    const hours = byId("import-shift-hours");
    const minutes = byId("import-shift-minutes");
    const status = byId("import-shift-status");
    if (!hours.value || !minutes.value || !hours.checkValidity() || !minutes.checkValidity()) {
      setStatus(status, "Enter whole hours and minutes (0–59 minutes).", true);
      return;
    }
    const seconds = (Number(hours.value) * 3600 + Number(minutes.value) * 60) *
      (byId("import-shift-direction").value === "backward" ? -1 : 1);
    // Always use the original suggestion so applying twice does not compound the correction.
    const changes = state.timelineEntries.filter(entry => entry.inferredValue && !entry.manual)
      .map(entry => ({ entry, value: addSecondsToInputValue(entry.inferredValue, seconds) }));
    if (changes.some(change => !change.value)) {
      setStatus(status, "That correction would put a date outside the supported range.", true);
      return;
    }
    changes.forEach(({ entry, value }) => { entry.value = value; });
    invalidateTimelineConfirmation();
    renderTimelineRows();
    updateTimelineReviewState();
    setStatus(status, `Correction applied to ${changes.length} inferred start times. Review the updated dates and times, then confirm again.`);
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
      } else if (!Number.isFinite(file.duration_seconds)) {
        nextSequentialStart = null;
      } else if (!value) {
        nextSequentialStart = null;
      }

      return {
        index,
        file,
        value,
        source,
        inferredValue: value,
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
    if (state.timelineConfirmed) return "Confirmed";
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
            type="text"
            class="import-start-input"
            placeholder="YYYY-MM-DD HH:MM:SS"
            value="${escapeHtml(entry.draft ?? entry.value.replace("T", " "))}"
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
        if (setupLocked()) return;
        const index = Number(event.target.dataset.timelineIndex);
        const entry = state.timelineEntries[index];
        if (!entry) return;
        entry.draft = event.target.value;
        entry.value = detectedStartToInputValue(event.target.value) || "";
        event.target.setCustomValidity(entry.value ? "" : "Use a valid date and 24-hour time: YYYY-MM-DD HH:MM:SS.");
        entry.source = entry.value ? "manual" : "missing";
        entry.manual = true;
        invalidateTimelineConfirmation();
        updateTimelineReviewState();
      });
    });
  }

  function renderTimelineGuidance(reviewState) {
    const summary = byId("timeline-suggestion-summary");
    if (!summary || !reviewState) return;

    let title = "Timeline draft";
    let message = "Review the suggested start times, edit anything wrong, then confirm.";

    if (state.timelineConfirmed) {
      title = "Timeline confirmed";
      message = `${reviewState.entries.length} recording start times confirmed.`;
    } else if (!reviewState.totalFiles) {
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
    byId("apply-import-time-shift").disabled = !state.timelineEntries.some(entry => entry.inferredValue && !entry.manual);
    const confirmButton = byId("confirm-import-timeline");
    if (confirmButton) confirmButton.disabled = !reviewState.canConfirm;
    renderTimelineGuidance(reviewState);

    reviewState.entries.forEach(entry => {
      const source = document.querySelector(`[data-source-index="${entry.index}"]`);
      const status = document.querySelector(`[data-status-index="${entry.index}"]`);
      if (source) source.textContent = sourceLabel(entry.source);
      if (status) status.textContent = entryStatus(entry);
    });
    syncSetupUI();
  }

  function buildTimelineReview() {
    const status = byId("import-session-status");
    if (!state.scan) return;

    state.timelineEntries = buildTimelineEntries(state.scan.source.review_files || []);
    renderTimelineRows();
    setStageUnlocked("import-stage-timeline");
    updateTimelineReviewState();
    const reviewState = timelineReviewState();
    if (reviewState.missingCount === 0 && reviewState.totalFiles > 0) {
      setStatus(status, "Timeline review built. Review it carefully before confirming.");
    } else if (reviewState.hiddenCount > 0) {
      setStatus(status, "Timeline review is capped for this large import.", true);
    } else {
      setStatus(status, "Timeline review needs more information before it can be confirmed.", true);
    }
  }

  function dateForOutputPlan() {
    const reviewed = (state.timelineEntries || []).find(entry => entry.value)?.value;
    if (reviewed) {
      // Night folders use the evening date, including recordings after midnight.
      const date = new Date(`${reviewed}Z`);
      if (date.getUTCHours() < 12) date.setUTCDate(date.getUTCDate() - 1);
      return date.toISOString().slice(0, 10);
    }
    const detected = (state.scan?.source?.review_files || []).find(file => file.detected_start)?.detected_start;
    if (detected) return String(detected).slice(0, 10);
    return "selected-night";
  }

  function renderOutputTree() {
    const tree = byId("planned-output-tree");
    const outputDisplay = byId("import-output-folder-display")?.value || "selected output folder";
    const sessionDate = dateForOutputPlan();
    const recordingDate = state.timelineEntries.find(entry => entry.value)?.value.slice(0, 10) || sessionDate;
    if (!tree) return;
    tree.textContent = `${outputDisplay}/
  ${sessionDate}/
    audio/
      001_NFC_${recordingDate}_...wav
      … later segments (civil-period labels where applicable)
    results/
      birdnet/
      nighthawk/
    clips/
      HH-MM-SS/
    logs/
    eBird checklists/
      ebird_record_import_yyyy-mm-dd_hh-mm.csv
      ebird_review_yyyy-mm-dd_hh-mm.csv
    manifest.csv
  … additional night folders as needed
  .nfc-imports/
    saved run and source metadata`;
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
      <p>${escapeHtml(estimate.basis || "")}</p>
      <p class="estimate-status estimate-${estimateStatus}">${escapeHtml(estimate.message)}</p>
    `;
  }

  function confirmTimeline() {
    if (setupLocked() || state.timelineConfirmed || !timelineReviewState().canConfirm) return;
    state.timelineConfirmed = true;
    setStageUnlocked("import-stage-output");
    renderOutputTree();
    renderEstimate();
    const storageButton = byId("confirm-import-storage");
    if (storageButton) storageButton.disabled = false;
    setStatus(byId("import-session-status"), "Session details and timeline confirmed.");
    rememberLocation();
    updateTimelineReviewState();
  }

  function confirmStoragePlan() {
    if (setupLocked() || state.storageConfirmed || !state.timelineConfirmed) return;
    state.storageConfirmed = true;
    byId("start-import-run").disabled = state.submitting || Boolean(state.job && state.job.state !== "complete");
    setStageUnlocked("import-stage-run");
    syncSetupUI();
  }

  function rememberRun(value) {
    try { localStorage.setItem("nfc-import-run", JSON.stringify(value)); } catch (_) { /* Storage may be disabled. */ }
  }

  function renderRun(job) {
    state.job = job;
    if (!job) return;
    state.planSubmitted = true;
    state.timelineConfirmed = true;
    state.storageConfirmed = true;
    setStageUnlocked("import-stage-run");
    const message = job.pause_requested && job.state === "running" ? "Pause requested—finishing the current part." : job.message;
    setStatus(byId("import-run-status"), analyzerText(`${job.state}: ${message}`), job.state === "failed");
    const elapsed = job.analyzer_started_at ? Math.max(0, Math.floor((Date.now() - Date.parse(job.analyzer_started_at)) / 1000)) : null;
    byId("import-run-details").textContent =
      `Current recording: ${job.current_file || "—"}\n` +
      `Analyzer: ${analyzerText(job.current_analyzer) || "—"}${elapsed !== null ? ` (${elapsed}s elapsed)` : ""}\n` +
      `Archive: ${job.output}`;
    const batchProgress = byId("import-batch-progress");
    if (batchProgress) {
      batchProgress.max = Math.max(job.total_files, 1);
      batchProgress.value = job.file_index;
    }
    const startButton = byId("start-import-run");
    const pauseButton = byId("pause-import-run");
    const resumeButton = byId("resume-import-run");
    const newButton = byId("new-import-plan");
    if (startButton) startButton.hidden = true;
    if (pauseButton) {
      pauseButton.disabled = job.state !== "running" || job.pause_requested;
      setHidden(pauseButton, job.state !== "running");
    }
    if (resumeButton) {
      resumeButton.disabled = !["paused", "failed"].includes(job.state);
      setHidden(resumeButton, !["paused", "failed"].includes(job.state));
    }
    if (newButton) {
      newButton.disabled = job.state === "running";
      setHidden(newButton, job.state === "running");
    }
    setStatus(byId("import-session-status"), "Session details and timeline confirmed for this run.");
    syncSetupUI();
    rememberRun({ output: job.output, id: job.id });
  }

  async function restoreRunPlan(job) {
    if (state.restoredJobId === job.id) return;
    const response = await fetch(`/import-recordings/run/${job.id}/plan?${new URLSearchParams({ output: job.output })}`);
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Unable to restore the confirmed plan.");
    const plan = payload.plan;
    byId("import-source-folder").value = plan.source;
    byId("import-source-folder-display").value = plan.source;
    byId("import-output-folder").value = plan.output;
    byId("import-output-folder-display").value = plan.output;
    byId("import-site-name").value = plan.config.site.name;
    byId("import-latitude").value = plan.config.site.latitude;
    byId("import-longitude").value = plan.config.site.longitude;
    byId("import-timezone").value = plan.config.site.timezone;
    byId("import-timezone-label").textContent = plan.config.site.timezone;
    byId("import-ebird-state-province").value = plan.config.site.ebird_state_province || "";
    byId("import-ebird-hotspot-id").value = "";
    const point = { lat: plan.config.site.latitude, lng: plan.config.site.longitude };
    if (state.importLocationMap) state.importLocationMap.setView([point.lat, point.lng], 13);
    if (state.importLocationMarker) {
      state.importLocationMarker.setLatLng(point);
      state.importLocationMarker.setPopupContent(`Recording location<br>(${point.lat.toFixed(7)}, ${point.lng.toFixed(7)})`);
    }
    const yearRound = plan.config.analyzers.birdnet_year_round ?? true;
    byId("import-birdnet-year-round").checked = yearRound;
    byId("import-analyzer-summary").textContent = analyzerText(`Analyzers: ${plan.config.analyzers.enabled.join(", ")}. `) +
      `BirdNET minimum confidence: ${plan.config.analyzers.birdnet_min_conf}. ` +
      (yearRound ? "BirdNET species filter: year-round at this location." : "BirdNET species filter: each recording date and location.");
    const files = plan.files.map(file => ({ ...file, name: file.relative_path, detected_start: file.start.slice(0, 19),
      duration_seconds: file.duration, duration_display: `${Math.ceil(file.duration)} seconds` }));
    state.scan = { source: { audio_count: files.length, review_files: files, path: plan.source }, output: { path: plan.output } };
    state.timelineEntries = buildTimelineEntries(files);
    byId("timeline-responsibility-check").checked = true;
    state.timelineConfirmed = true;
    state.storageConfirmed = true;
    renderTimelineRows();
    updateTimelineReviewState();
    ["folders", "session", "timeline", "output"].forEach(key => setStageUnlocked(`import-stage-${key}`));
    renderOutputTree();
    byId("import-storage-estimate").textContent = "Storage plan confirmed when this run started. Current free space is shown in the run monitor.";
    state.restoredJobId = job.id;
  }

  async function pollRun() {
    try {
      if (state.submitting || state.scanning) return;
      let saved = state.job;
      if (!saved) {
        try { saved = JSON.parse(localStorage.getItem("nfc-import-run") || "null"); } catch (_) { /* No saved run. */ }
      }
      const params = saved ? `?${new URLSearchParams({ output: saved.output, job_id: saved.id })}` : "";
      const response = await fetch(`/import-recordings/run${params}`);
      const payload = await response.json();
      if (payload.ok && payload.job && payload.job.id !== state.ignoredJobId) {
        renderRun(payload.job);
        await restoreRunPlan(payload.job);
      }
      else if (!payload.ok) {
        try { localStorage.removeItem("nfc-import-run"); } catch (_) { /* Storage may be disabled. */ }
        state.job = null;
        state.restoredJobId = null;
        state.planSubmitted = false;
        setStatus(byId("import-run-status"), "Previous saved run was not found. You can start a new import.");
      }
    } catch (_) {
      if (state.job) setStatus(byId("import-run-status"), "Run status unavailable. Reconnecting…", true);
    } finally {
      state.recovering = false;
      syncSetupUI();
      setTimeout(pollRun, 2500);
    }
  }

  async function startRun() {
    if (setupLocked()) return;
    if (!timelineReadyToStart()) {
      setStatus(byId("import-run-status"), "Review and confirm the complete timeline and storage plan before starting.", true);
      syncSetupUI();
      return;
    }
    const coordinates = parseCoordinatePair(byId("import-latitude"), byId("import-longitude"));
    if (!coordinates) {
      setStatus(byId("import-run-status"), "Enter valid recording coordinates.", true);
      return;
    }
    const ebirdStateInput = byId("import-ebird-state-province").value.trim().toUpperCase();
    const ebirdStateProvince = /^[A-Z]{2}-[A-Z0-9]{1,3}$/.test(ebirdStateInput)
      ? ebirdStateInput.split("-", 2)[1]
      : ebirdStateInput;
    byId("import-ebird-state-province").value = ebirdStateProvince;
    if (!ebirdStateProvince) {
      setStatus(byId("import-run-status"), "Enter the eBird state/province code before starting.", true);
      return;
    }
    rememberLocation();
    state.submitting = true;
    syncSetupUI();
    byId("start-import-run").disabled = true;
    setStatus(byId("import-run-status"), "Validating files, times, and output space…");
    state.requestId = state.requestId || createRequestId();
    const body = {
      request_id: state.requestId,
      source_folder: state.scan.source.path, output_folder: state.scan.output.path,
      site_name: byId("import-site-name").value, latitude: coordinates.lat, longitude: coordinates.lng,
      timezone: byId("import-timezone").value, ambiguous_time: byId("import-ambiguous-time").value,
      ebird_state_province: ebirdStateProvince,
      ebird_hotspot_id: byId("import-ebird-hotspot-id").value,
      birdnet_year_round: byId("import-birdnet-year-round").checked,
      timeline_confirmed: true, storage_confirmed: true,
      files: state.timelineEntries.map(entry => ({
        relative_path: entry.file.relative_path, start: entry.value,
        size_bytes: entry.file.size_bytes, mtime_ns: entry.file.mtime_ns
      }))
    };
    try {
      rememberRun({ output: body.output_folder, id: state.requestId });
      const response = await fetch("/import-recordings/start", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const detail = Array.isArray(payload.detail) ? payload.detail.map(item => item.msg).join("; ") : payload.detail;
        throw new Error(payload.error || detail || "Import could not start.");
      }
      state.planSubmitted = true;
      renderRun(payload.job);
    } catch (error) {
      setStatus(byId("import-run-status"), error.message, true);
      byId("start-import-run").disabled = false;
    } finally {
      state.submitting = false;
      syncSetupUI();
    }
  }

  async function controlRun(action) {
    if (!state.job) return;
    const body = new FormData();
    body.append("output", state.job.output);
    byId(`${action}-import-run`).disabled = true;
    try {
      const response = await fetch(`/import-recordings/run/${state.job.id}/${action}`, { method: "POST", body });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "Could not update run.");
      renderRun(payload.job);
    } catch (error) {
      setStatus(byId("import-run-status"), error.message, true);
      byId(`${action}-import-run`).disabled = false;
    }
  }

  function newImportPlan() {
    if (state.job?.state === "running") return;
    state.ignoredJobId = state.job?.id;
    state.job = null;
    state.restoredJobId = null;
    try { localStorage.removeItem("nfc-import-run"); } catch (_) { /* Storage may be disabled. */ }
    resetReviewResults();
    updateReviewButtonState();
    byId("pause-import-run").disabled = true;
    byId("resume-import-run").disabled = true;
    byId("new-import-plan").disabled = true;
    setStatus(byId("import-run-status"), "Review and confirm the new import plan.");
  }

  byId("start-import-run")?.addEventListener("click", startRun);
  byId("pause-import-run")?.addEventListener("click", () => controlRun("pause"));
  byId("resume-import-run")?.addEventListener("click", () => controlRun("resume"));
  byId("new-import-plan")?.addEventListener("click", newImportPlan);
  ["import-site-name", "import-latitude", "import-longitude", "import-timezone", "import-ebird-state-province", "import-ebird-hotspot-id", "import-ambiguous-time", "import-birdnet-year-round"].forEach(id => {
    byId(id)?.addEventListener("input", () => {
      if (setupLocked()) return;
      invalidateTimelineConfirmation(); updateTimelineReviewState(); rememberLocation();
    });
  });
  restoreLocation();
  state.recovering = true;
  pollRun();

  byId("apply-import-time-shift")?.addEventListener("click", applyTimeShift);
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
  byId("timeline-responsibility-check")?.addEventListener("change", () => {
    if (!byId("timeline-responsibility-check").checked) invalidateTimelineConfirmation();
    updateTimelineReviewState();
  });
  updateReviewButtonState();
})();
