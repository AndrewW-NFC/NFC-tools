
/* NFC Tools Settings page controller v9 */
(function () {
  const TIME_FORMAT_KEY = "nfcToolsSettingsTimeFormatV9";
  const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";

  function textOf(el) {
    return (el?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function fieldLabel(input) {
    const id = input.getAttribute("id");
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) return textOf(label);
    }

    const wrapperLabel = input.closest("label");
    if (wrapperLabel) return textOf(wrapperLabel).replace(input.value || "", "").trim();

    const parent = input.closest(".field, .form-row, p, div, section, fieldset");
    if (parent) {
      const label = parent.querySelector("label");
      if (label) return textOf(label);
      const textNode = Array.from(parent.childNodes).find(n => n.nodeType === Node.TEXT_NODE && n.nodeValue.trim());
      if (textNode) return textNode.nodeValue.trim();
    }

    return "";
  }

  function sig(input) {
    return `${input.name || ""} ${input.id || ""} ${fieldLabel(input)}`.toLowerCase();
  }

  function wrapperFor(input) {
    return input?.closest(".field, .form-row, label, p, div") || input;
  }

  function findInputs() {
    const inputs = Array.from(document.querySelectorAll("input"));
    const name = inputs.find(i => sig(i).includes("name") && !sig(i).includes("filename"));
    const lat = inputs.find(i => sig(i).includes("latitude") || /\blat\b/.test(sig(i)));
    const lon = inputs.find(i => sig(i).includes("longitude") || sig(i).includes("lng") || /\blon\b/.test(sig(i)));
    const timezone = inputs.find(i => sig(i).includes("timezone") || sig(i).includes("time zone") || sig(i).includes("iana"));
    const start = inputs.find(i => sig(i).includes("start") && /^\d{1,2}:\d{2}$/.test(i.value || ""));
    const end = inputs.find(i => sig(i).includes("end") && /^\d{1,2}:\d{2}$/.test(i.value || ""));
    const segment = inputs.find(i => sig(i).includes("segment"));
    return { name, lat, lon, timezone, start, end, segment };
  }

  function removeOldInjectedBlocks() {
    document.querySelectorAll([
      ".nfc-friendly-schedule",
      ".nfc-schedule-picker",
      ".nfc-v4-schedule",
      ".nfc-v4-location-picker",
      ".nfc-v5-map-picker",
      ".nfc-settings-clean-schedule",
      ".nfc-settings-clean-map",
      ".nfc-v7-location",
      ".nfc-v7-schedule",
      ".nfc-settings-v8-location",
      ".nfc-settings-v8-schedule",
      ".nfc-settings-v9-map-block",
      ".nfc-settings-v9-schedule"
    ].join(",")).forEach(el => el.remove());

    document.querySelectorAll("[data-nfc-settings-hidden]").forEach(el => {
      const wrap = wrapperFor(el);
      if (wrap) wrap.style.display = "";
      else el.style.display = "";
      delete el.dataset.nfcSettingsHidden;
    });
  }

  function removeClutter() {
    document.querySelectorAll("a").forEach(a => {
      const label = textOf(a).toLowerCase();
      const href = (a.getAttribute("href") || "").toLowerCase();
      if (label === "files" || href === "/files" || href.endsWith("/files")) {
        const li = a.closest("li");
        if (li) li.remove();
        else a.remove();
      }
    });

    document.querySelectorAll("section, fieldset, div, p, li").forEach(el => {
      const t = textOf(el).toLowerCase();
      if (
        t.includes("currently enabled: birdnet, nighthawk") ||
        (t.includes("status") && t.includes("birdnet: installed") && t.includes("nighthawk: installed"))
      ) {
        el.remove();
      }
    });

    document.querySelectorAll("button, a, label, span, p, h1, h2, h3").forEach(el => {
      if (/install audio engine/i.test(textOf(el))) {
        for (const node of el.childNodes) {
          if (node.nodeType === Node.TEXT_NODE) {
            node.nodeValue = node.nodeValue.replace(/Install audio engine/gi, "Install recording engine");
          }
        }
      }
    });

    document.querySelectorAll(".help-text").forEach(el => {
      if (/ffmpeg|small recording engine/i.test(textOf(el))) el.remove();
    });
  }

  function findHeading(text) {
    return Array.from(document.querySelectorAll("h1,h2,h3")).find(h => textOf(h).toLowerCase() === text.toLowerCase());
  }

  function siteInsertionPoint(inputs) {
    const siteHeading = findHeading("Site");
    const wrappers = [inputs.name, inputs.lat, inputs.lon, inputs.timezone].map(wrapperFor).filter(Boolean);
    const sharedParent = wrappers.length ? wrappers[0].parentElement : null;

    if (sharedParent && wrappers.every(w => w.parentElement === sharedParent)) {
      return { parent: sharedParent.parentElement || sharedParent, after: sharedParent };
    }

    const lastWrapper = wrappers.filter(Boolean).pop();
    if (lastWrapper && lastWrapper.parentElement) return { parent: lastWrapper.parentElement, after: lastWrapper };

    if (siteHeading && siteHeading.parentElement) return { parent: siteHeading.parentElement, after: siteHeading };

    return { parent: document.querySelector("form") || document.body, after: null };
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

  function setLatLon(latInput, lonInput, marker, status, latLng) {
    latInput.value = Number(latLng.lat).toFixed(7);
    lonInput.value = Number(latLng.lng).toFixed(7);
    latInput.dispatchEvent(new Event("input", { bubbles: true }));
    lonInput.dispatchEvent(new Event("input", { bubbles: true }));
    latInput.dispatchEvent(new Event("change", { bubbles: true }));
    lonInput.dispatchEvent(new Event("change", { bubbles: true }));
    if (marker) {
      marker.setLatLng(latLng);
      marker.setPopupContent(`Recorder location<br>(${Number(latInput.value).toFixed(7)}, ${Number(lonInput.value).toFixed(7)})`);
    }
    if (status) status.textContent = `Selected ${Number(latInput.value).toFixed(5)}, ${Number(lonInput.value).toFixed(5)}`;
  }

  function buildMapBlock(inputs) {
    const { lat, lon } = inputs;
    if (!lat || !lon) return null;

    const block = document.createElement("section");
    block.className = "nfc-settings-v9-map-block";
    block.id = "nfc-settings-v9-map-block";

    const title = document.createElement("h3");
    title.textContent = "Map-selected location";
    block.appendChild(title);

    const map = document.createElement("div");
    map.id = "nfc-settings-v9-map";
    map.style.width = "100%";
    map.style.height = "360px";
    map.style.minHeight = "360px";
    map.style.border = "1px solid #ccc";
    map.style.borderRadius = "0.7rem";
    map.style.overflow = "hidden";
    block.appendChild(map);

    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Click the map or drag the marker to select latitude and longitude. Requires an internet connection.";
    block.appendChild(note);

    const actions = document.createElement("div");
    actions.className = "nfc-settings-v9-map-actions";

    const browserLocation = document.createElement("button");
    browserLocation.type = "button";
    browserLocation.textContent = "Use my current browser location";

    const status = document.createElement("span");
    status.className = "muted";

    actions.appendChild(browserLocation);
    actions.appendChild(status);
    block.appendChild(actions);

    const currentLat = Number(lat.value) || 42.415;
    const currentLon = Number(lon.value) || -71.156;

    loadLeaflet()
      .then(() => {
        const leafletMap = L.map(map).setView([currentLat, currentLon], 13);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
          maxZoom: 20,
          attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
        }).addTo(leafletMap);

        const marker = L.marker([currentLat, currentLon], { draggable: true }).addTo(leafletMap);
        marker.bindPopup(`Recorder location<br>(${currentLat.toFixed(7)}, ${currentLon.toFixed(7)})`).openPopup();

        leafletMap.on("click", event => setLatLon(lat, lon, marker, status, event.latlng));
        marker.on("dragend", () => setLatLon(lat, lon, marker, status, marker.getLatLng()));

        browserLocation.addEventListener("click", () => {
          if (!navigator.geolocation) {
            status.textContent = "Browser location is not available.";
            return;
          }

          status.textContent = "Requesting browser location…";
          navigator.geolocation.getCurrentPosition(
            pos => {
              const point = L.latLng(pos.coords.latitude, pos.coords.longitude);
              leafletMap.setView(point, 15);
              setLatLon(lat, lon, marker, status, point);
            },
            err => {
              status.textContent = `Could not get browser location: ${err.message}`;
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
          );
        });

        status.textContent = `Selected ${currentLat.toFixed(5)}, ${currentLon.toFixed(5)}`;
        setTimeout(() => leafletMap.invalidateSize(), 200);
        setTimeout(() => leafletMap.invalidateSize(), 1000);
      })
      .catch(() => {
        status.textContent = "Map could not load. Enter latitude and longitude directly.";
      });

    return block;
  }

  function pad2(n) {
    return String(Number(n) || 0).padStart(2, "0");
  }

  function parseTime(value) {
    const m = String(value || "00:00").match(/^(\d{1,2}):(\d{2})$/);
    let hour = m ? Number(m[1]) : 0;
    let minute = m ? Number(m[2]) : 0;
    if (!Number.isFinite(hour)) hour = 0;
    if (!Number.isFinite(minute)) minute = 0;
    return { hour: Math.max(0, Math.min(23, hour)), minute: Math.max(0, Math.min(59, minute)) };
  }

  function formatTime(hour, minute) {
    return `${pad2(hour)}:${pad2(minute)}`;
  }

  function to12(hour24) {
    const period = hour24 >= 12 ? "PM" : "AM";
    let hour = hour24 % 12;
    if (hour === 0) hour = 12;
    return { hour, period };
  }

  function to24(hour12, period) {
    let hour = Number(hour12);
    if (!Number.isFinite(hour)) hour = 12;
    if (period === "AM") return hour === 12 ? 0 : hour;
    return hour === 12 ? 12 : hour + 12;
  }

  function makeSelect(items, selected) {
    const select = document.createElement("select");
    for (const item of items) {
      const value = Array.isArray(item) ? item[0] : item;
      const label = Array.isArray(item) ? item[1] : item;
      const opt = document.createElement("option");
      opt.value = String(value);
      opt.textContent = String(label);
      if (String(value) === String(selected)) opt.selected = true;
      select.appendChild(opt);
    }
    return select;
  }

  function hideOriginal(input) {
    if (!input) return;
    input.dataset.nfcSettingsHidden = "1";
    const wrap = wrapperFor(input);
    if (wrap) wrap.style.display = "none";
    else input.style.display = "none";
  }

  function buildTimePicker(labelText, original, formatSelect) {
    const current = parseTime(original.value);
    const current12 = to12(current.hour);

    const row = document.createElement("div");
    row.className = "nfc-settings-v9-row";

    const label = document.createElement("label");
    label.className = "nfc-settings-v9-row-label";
    label.textContent = labelText;

    const hour12 = makeSelect(Array.from({ length: 12 }, (_, i) => [i + 1, i + 1]), current12.hour);
    const hour24 = makeSelect(Array.from({ length: 24 }, (_, i) => [i, pad2(i)]), current.hour);
    const minute = makeSelect(["00","05","10","15","20","25","30","35","40","45","50","55"], pad2(Math.round(current.minute / 5) * 5 % 60));
    const period = makeSelect(["AM", "PM"], current12.period);

    function syncOriginal() {
      const use24 = formatSelect.value === "24";
      const hour = use24 ? Number(hour24.value) : to24(hour12.value, period.value);
      original.value = formatTime(hour, Number(minute.value));
      original.dispatchEvent(new Event("input", { bubbles: true }));
      original.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function syncControls() {
      const next = parseTime(original.value);
      const converted = to12(next.hour);
      hour12.value = String(converted.hour);
      hour24.value = String(next.hour);
      minute.value = pad2(Math.round(next.minute / 5) * 5 % 60);
      period.value = converted.period;
    }

    function applyFormat() {
      const use24 = formatSelect.value === "24";
      hour24.hidden = !use24;
      hour12.hidden = use24;
      period.hidden = use24;
      localStorage.setItem(TIME_FORMAT_KEY, formatSelect.value);
      syncOriginal();
    }

    [hour12, hour24, minute, period].forEach(el => el.addEventListener("change", syncOriginal));
    formatSelect.addEventListener("change", applyFormat);
    original.addEventListener("input", syncControls);
    original.addEventListener("change", syncControls);

    row.appendChild(label);
    row.appendChild(hour12);
    row.appendChild(hour24);
    row.appendChild(document.createTextNode(":"));
    row.appendChild(minute);
    row.appendChild(period);

    hideOriginal(original);
    applyFormat();

    return { row, syncControls };
  }

  function approximateSunTimes(date, latDeg, lonDeg) {
    const rad = Math.PI / 180;
    const zenith = 90.833;

    function dayOfYear(d) {
      const start = new Date(d.getFullYear(), 0, 0);
      return Math.floor((d - start) / 86400000);
    }

    function calc(isRise) {
      const N = dayOfYear(date);
      const lngHour = lonDeg / 15;
      const t = N + ((isRise ? 6 : 18) - lngHour) / 24;
      const M = (0.9856 * t) - 3.289;
      let L = M + 1.916 * Math.sin(M * rad) + 0.020 * Math.sin(2 * M * rad) + 282.634;
      L = (L + 360) % 360;

      let RA = Math.atan(0.91764 * Math.tan(L * rad)) / rad;
      RA = (RA + 360) % 360;
      RA = RA + (Math.floor(L / 90) * 90 - Math.floor(RA / 90) * 90);
      RA = RA / 15;

      const sinDec = 0.39782 * Math.sin(L * rad);
      const cosDec = Math.cos(Math.asin(sinDec));
      const cosH = (Math.cos(zenith * rad) - sinDec * Math.sin(latDeg * rad)) / (cosDec * Math.cos(latDeg * rad));
      if (cosH > 1 || cosH < -1) return null;

      let H = isRise ? 360 - Math.acos(cosH) / rad : Math.acos(cosH) / rad;
      H = H / 15;

      const T = H + RA - 0.06571 * t - 6.622;
      const UT = (T - lngHour + 24) % 24;

      const local = new Date(date);
      local.setHours(0, 0, 0, 0);
      local.setMinutes(Math.round(UT * 60 - local.getTimezoneOffset()));
      return local;
    }

    return { sunrise: calc(true), sunset: calc(false) };
  }

  function setInputTime(input, dateObj) {
    if (!input || !dateObj) return;
    input.value = formatTime(dateObj.getHours(), dateObj.getMinutes());
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function findSuggestButton() {
    return Array.from(document.querySelectorAll("button, input[type='button'], a")).find(el => {
      const t = textOf(el).toLowerCase();
      return t.includes("set to local astronomical sunset and sunrise") ||
             t.includes("suggest times based on sunset/sunrise") ||
             t.includes("suggest times based on sunrise/sunset");
    });
  }

  function buildScheduleBlock(inputs) {
    return null;
    const { start, end, segment, lat, lon } = inputs;
    if (!start || !end) return null;

    const block = document.createElement("section");
    block.className = "nfc-settings-v9-schedule";
    block.id = "nfc-settings-v9-schedule";

    const title = document.createElement("h2");
    title.textContent = "Set Schedule";
    block.appendChild(title);

    const formatRow = document.createElement("div");
    formatRow.className = "nfc-settings-v9-row";

    const formatLabel = document.createElement("label");
    formatLabel.className = "nfc-settings-v9-row-label";
    formatLabel.textContent = "Time format";

    const formatSelect = makeSelect([["12", "AM/PM"], ["24", "24 hour"]], localStorage.getItem(TIME_FORMAT_KEY) || "12");

    formatRow.appendChild(formatLabel);
    formatRow.appendChild(formatSelect);
    block.appendChild(formatRow);

    const startPicker = buildTimePicker("Start time", start, formatSelect);
    const endPicker = buildTimePicker("End time", end, formatSelect);
    block.appendChild(startPicker.row);
    block.appendChild(endPicker.row);

    if (segment) {
      const oldWrap = wrapperFor(segment);
      const row = document.createElement("div");
      row.className = "nfc-settings-v9-row";

      const label = document.createElement("label");
      label.className = "nfc-settings-v9-row-label";
      label.textContent = "Segment minutes";

      row.appendChild(label);
      row.appendChild(segment);
      block.appendChild(row);

      if (oldWrap && oldWrap !== segment && !block.contains(oldWrap)) oldWrap.style.display = "none";
    }

    const suggest = findSuggestButton();
    if (suggest) {
      suggest.textContent = "Set to local astronomical sunset and sunrise";
      const oldWrap = wrapperFor(suggest);
      const row = document.createElement("div");
      row.className = "nfc-settings-v9-row";
      row.appendChild(suggest);
      block.appendChild(row);

      if (oldWrap && oldWrap !== suggest && !block.contains(oldWrap)) oldWrap.style.display = "none";

      suggest.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();

        const latVal = Number(lat?.value);
        const lonVal = Number(lon?.value);
        const times = approximateSunTimes(
          new Date(),
          Number.isFinite(latVal) ? latVal : 42.415,
          Number.isFinite(lonVal) ? lonVal : -71.156
        );

        setInputTime(start, times.sunset);
        setInputTime(end, times.sunrise);
        startPicker.syncControls();
        endPicker.syncControls();
      }, true);
    }

    return block;
  }

  function hideOldScheduleShell(inputs) {
    [inputs.start, inputs.end].forEach(hideOriginal);

    const scheduleHeading = Array.from(document.querySelectorAll("h1,h2,h3")).find(h => textOf(h).toLowerCase() === "schedule");
    if (scheduleHeading) scheduleHeading.style.display = "none";
  }

  function setupStopFeedback() {
    document.addEventListener("click", event => {
      const btn = event.target.closest("button, input[type='submit'], a");
      if (!btn) return;
      const t = textOf(btn).toLowerCase();
      if (t === "stop" || t.includes("stop recording")) {
        const msg = document.getElementById("analysis-message");
        if (msg) msg.textContent = "Analysis will start in a moment.";
      }
    }, true);
  }

  function initSettingsPage() {
    removeClutter();

    const inputs = findInputs();
    if (!inputs.lat || !inputs.lon) return;

    removeOldInjectedBlocks();

    // Do not move existing lat/lon/timezone inputs. Leave them where the
    // template put them, then add a map underneath.
    const mapBlock = buildMapBlock(inputs);
    const insertion = siteInsertionPoint(inputs);
    if (mapBlock && insertion.parent) {
      if (insertion.after?.nextSibling) insertion.parent.insertBefore(mapBlock, insertion.after.nextSibling);
      else insertion.parent.appendChild(mapBlock);
    }

  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSettingsPage);
  } else {
    initSettingsPage();
  }

  setupStopFeedback();
})();
