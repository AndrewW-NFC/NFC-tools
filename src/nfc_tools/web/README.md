# Recorder web interface

`server.py` assembles the FastAPI application, mounts browser assets, and registers routes. `state.py` holds shared configuration/session state. Route modules translate browser requests into application-service calls; they render [templates](templates/README.md), which load [static assets](static/README.md).

FastAPI, Uvicorn, and Jinja2 provide the server stack. The browser uses plain JavaScript; the settings/import maps load Leaflet. This is distinct from the listening-review server in [review](../review/README.md).

## Files

| File | Purpose |
| --- | --- |
| [__init__.py](__init__.py) | Local web UI package. |
| [geocode.py](geocode.py) | Optional location helpers for recorder-site coordinates. |
| [routes.py](routes.py) | Main HTTP routes: dashboard, settings, session control, and diagnostics. |
| [routes_diagnostics.py](routes_diagnostics.py) | Diagnostics HTTP routes and downloadable support artifacts. |
| [routes_import.py](routes_import.py) | Imported-recording planning routes. |
| [routes_nights.py](routes_nights.py) | Night coverage and explicitly requested recovery of saved recordings. |
| [routes_readiness.py](routes_readiness.py) | Night readiness HTTP routes. |
| [routes_schedule.py](routes_schedule.py) | Auto-schedule UI routes. |
| [server.py](server.py) | FastAPI app factory and uvicorn launcher. |
| [state.py](state.py) | Per-process app state (singleton-ish). |
