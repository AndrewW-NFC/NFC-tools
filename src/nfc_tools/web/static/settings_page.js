/* NFC Tools Settings page controller */
(function () {
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
    const inputs = Array.from(document.querySelectorAll("input, select"));
    const name = inputs.find(i => sig(i).includes("name") && !sig(i).includes("filename"));
    const lat = inputs.find(i => sig(i).includes("latitude") || /\blat\b/.test(sig(i)));
    const lon = inputs.find(i => sig(i).includes("longitude") || sig(i).includes("lng") || /\blon\b/.test(sig(i)));
    return { name, lat, lon };
  }

  function findHeading(text) {
    return Array.from(document.querySelectorAll("h1,h2,h3")).find(h => textOf(h).toLowerCase() === text.toLowerCase());
  }

  function siteInsertionPoint(inputs) {
    const siteHeading = findHeading("Recorder site") || findHeading("Site");
    const wrappers = [inputs.name, inputs.lat, inputs.lon].map(wrapperFor).filter(Boolean);
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

  function parseCoordinatePair(latInput, lonInput) {
    const latValue = Number.parseFloat(String(latInput?.value || "").trim());
    const lonValue = Number.parseFloat(String(lonInput?.value || "").trim());
    if (!Number.isFinite(latValue) || !Number.isFinite(lonValue)) return null;
    if (latValue < -90 || latValue > 90 || lonValue < -180 || lonValue > 180) return null;
    return { lat: latValue, lng: lonValue };
  }

  function browserTimezone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  }

  function updateHiddenTimezone() {
    const tz = document.getElementById("tz");
    if (tz && !tz.value) tz.value = browserTimezone();
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

  function saveCoordinates(latInput, lonInput) {
    const point = parseCoordinatePair(latInput, lonInput);
    if (!point) return;

    const body = new FormData();
    body.append("latitude", String(point.lat));
    body.append("longitude", String(point.lng));
    const timezone = document.getElementById("tz");
    if (timezone?.value) body.append("timezone", timezone.value);

    fetch("/settings/site-coordinates", { method: "POST", body })
      .catch(() => {});
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
      marker.setPopupContent(`Recorder location<br>(${Number(latInput.value).toFixed(7)}, ${Number(lonInput.value).toFixed(7)})`);
    }
  }

  function buildMapBlock(inputs) {
    const { lat, lon } = inputs;
    if (!lat || !lon) return null;

    const block = document.createElement("div");
    block.className = "nfc-settings-map-block";
    block.id = "nfc-settings-map-block";

    const actions = document.createElement("div");
    actions.className = "nfc-settings-map-actions";

    const currentLocationButton = document.createElement("button");
    currentLocationButton.type = "button";
    currentLocationButton.textContent = "Set to My Current Location";
    actions.appendChild(currentLocationButton);
    block.appendChild(actions);

    const map = document.createElement("div");
    map.id = "nfc-settings-map";
    block.appendChild(map);

    const parsed = parseCoordinatePair(lat, lon);
    const currentLat = parsed ? parsed.lat : 42.415;
    const currentLon = parsed ? parsed.lng : -71.156;

    loadLeaflet()
      .then(() => {
        updateHiddenTimezone();

        const leafletMap = L.map(map).setView([currentLat, currentLon], 13);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
          maxZoom: 20,
          attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
        }).addTo(leafletMap);

        const marker = L.marker([currentLat, currentLon], { draggable: true }).addTo(leafletMap);
        marker.bindPopup(`Recorder location<br>(${currentLat.toFixed(7)}, ${currentLon.toFixed(7)})`).openPopup();

        let saveTimer = null;
        function scheduleSave(delay = 650) {
          clearTimeout(saveTimer);
          saveTimer = setTimeout(() => saveCoordinates(lat, lon), delay);
        }

        function moveToPoint(latLng, options = {}) {
          setLatLon(lat, lon, marker, latLng);
          if (options.pan !== false) leafletMap.panTo(latLng, { animate: false });
          if (options.save !== false) scheduleSave(options.delay ?? 650);
        }

        function updateMapFromTypedCoordinates(options = {}) {
          const point = parseCoordinatePair(lat, lon);
          if (!point) return;
          const latLng = L.latLng(point.lat, point.lng);
          marker.setLatLng(latLng);
          marker.setPopupContent(`Recorder location<br>(${point.lat.toFixed(7)}, ${point.lng.toFixed(7)})`);
          if (options.pan !== false) leafletMap.panTo(latLng, { animate: false });
          scheduleSave();
        }

        async function setToCurrentLocation(options = {}) {
          if (options.userInitiated) currentLocationButton.disabled = true;
          const oldText = currentLocationButton.textContent;
          if (options.userInitiated) currentLocationButton.textContent = "Locating...";
          try {
            const pos = await getCurrentPosition();
            const latLng = L.latLng(pos.coords.latitude, pos.coords.longitude);
            moveToPoint(latLng, { delay: 100, save: true });
          } catch (error) {
            if (options.userInitiated) currentLocationButton.textContent = "Location unavailable";
          } finally {
            if (options.userInitiated) {
              setTimeout(() => {
                currentLocationButton.disabled = false;
                currentLocationButton.textContent = oldText;
              }, 900);
            }
          }
        }

        leafletMap.on("click", event => moveToPoint(event.latlng));
        marker.on("dragend", () => moveToPoint(marker.getLatLng()));
        currentLocationButton.addEventListener("click", () => setToCurrentLocation({ userInitiated: true }));
        [lat, lon].forEach(input => {
          input.addEventListener("input", () => updateMapFromTypedCoordinates());
          input.addEventListener("change", () => updateMapFromTypedCoordinates());
        });

        setTimeout(() => leafletMap.invalidateSize(), 200);
        setTimeout(() => leafletMap.invalidateSize(), 1000);
      })
      .catch(() => {
        map.textContent = "Map unavailable.";
      });

    return block;
  }

  function initSettingsPage() {
    const inputs = findInputs();
    if (!inputs.lat || !inputs.lon) return;

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
})();
