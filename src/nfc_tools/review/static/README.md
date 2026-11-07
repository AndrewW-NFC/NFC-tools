# Listening-review browser assets

The standalone review UI served by `../server.py`. `index.html` defines the listening queue, audio player, and annotation form; `app.js` handles playback, waveform navigation, and persistence; `style.css` provides layout and styling.

The controller uses the review server's batch/review APIs and browser audio, canvas, and localStorage. These assets are separate from `nfc_tools/web/static`, even though both servers expose a `/static` URL.
