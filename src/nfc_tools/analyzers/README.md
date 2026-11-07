# Analyzer implementations

Adapters expose the `Analyzer` protocol and return `AnalyzerResult` objects from `base.py`. Importing this package registers the built-ins. Sessions and imports select plugins through that registry.

BirdNET and Nighthawk run in managed external environments. The experimental wingbeat screen runs locally with NumPy and ffmpeg and produces candidates for review, not species identifications. Frame caching and accompaniment features support that screen.

## Files

| File | Purpose |
| --- | --- |
| [__init__.py](__init__.py) | Eager-import built-in analyzers so they self-register. |
| [base.py](base.py) | Analyzer plugin protocol. |
| [birdnet.py](birdnet.py) | BirdNET analyzer plugin. |
| [nighthawk.py](nighthawk.py) | Nighthawk analyzer plugin. |
| [wingbeat_accompaniment.py](wingbeat_accompaniment.py) | Experimental pulse-linked energy around spectral ridges; not a species ID. |
| [wingbeat_frames.py](wingbeat_frames.py) | Bounded reuse of frame-local calculations within one decoded audio stream. |
| [wingbeats.py](wingbeats.py) | Experimental pulse-train screening; WING means possible wingbeats, not an ID. |
