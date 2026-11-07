# Recorder browser assets

Plain JavaScript controllers and CSS for the main recorder UI. `app.js` is loaded by the shared template and handles recording/live status plus installation controls. Other controllers belong to named pages or shared eBird fields.

[Templates](../templates/README.md) supply DOM elements and load these files. Parent route modules supply HTTP/WebSocket endpoints. Settings and import maps load Leaflet dynamically; no frontend bundling step is required. See file headers for each controller's exact partners.
