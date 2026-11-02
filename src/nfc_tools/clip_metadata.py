"""Portable clip provenance. Never include review information, in any schema version."""
from __future__ import annotations

import json
import struct
from datetime import timedelta, timezone
from pathlib import Path

from .filenames import parse
from .version import __version__

REPOSITORY = "https://github.com/AndrewW-NFC/NFC-tools"


def build_metadata(wav_path: Path, spec, start: float, end: float, cfg) -> dict:
    parsed = parse(wav_path.name)
    recorded = parsed.recorded_at if parsed else None
    # Offset-bearing filenames are authoritative. Do not assign today's site
    # timezone to a legacy recording whose offset is unknown.
    call = None
    if recorded is not None:
        base = recorded.astimezone(timezone.utc) if recorded.tzinfo else recorded
        call = base + timedelta(seconds=spec.start_seconds)
        if recorded.tzinfo:
            call = call.astimezone(recorded.tzinfo)
    return {
        "schema": "nfc-tools.clip",
        "schema_version": 1,
        "software": {"name": "NFC Tools", "version": __version__, "repository": REPOSITORY},
        "source": {"filename": wav_path.name, "recording_start": recorded.isoformat() if recorded else None},
        "timing": {
            "call_timestamp": call.isoformat() if call else None,
            "timestamp_source": "source_filename" if recorded else "unknown",
            "timezone_status": "explicit_offset" if recorded and recorded.tzinfo else "unknown",
            "detection_start_seconds": spec.start_seconds,
            "detection_end_seconds": spec.end_seconds,
            "clip_start_seconds": start,
            "clip_end_seconds": end,
            "call_start_in_clip_seconds": spec.start_seconds - start,
            "call_end_in_clip_seconds": min(spec.end_seconds, end) - start,
        },
        "site": {"name": cfg.site.name, "latitude": cfg.site.latitude,
                 "longitude": cfg.site.longitude, "timezone": cfg.site.timezone,
                 "source": "export_configuration"},
        "detection": {"analyzer": spec.analyzer_label, "label": spec.label,
                      "suggested_identification": spec.identification,
                      "score": spec.score, "model_version": None},
    }


def summary(metadata: dict) -> str:
    timing = metadata["timing"]
    stamp = timing["call_timestamp"] or "unknown"
    if timing["timezone_status"] == "unknown":
        stamp += " (timezone unknown)"
    return (
        f"Call: {stamp}; source: {metadata['source']['filename']}; "
        f"detection: {timing['detection_start_seconds']:g}-{timing['detection_end_seconds']:g}s; "
        f"clip: {timing['clip_start_seconds']:g}-{timing['clip_end_seconds']:g}s; "
        f"site: {metadata['site']['name']}; "
        f"suggested detection: {metadata['detection']['label']} ({metadata['detection']['analyzer']}); "
        f"Exported with NFC Tools {__version__}; {REPOSITORY}"
    )


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack("<I", len(payload)) + payload + (b"\0" if len(payload) % 2 else b"")


def embed_metadata(path: Path, metadata: dict) -> None:
    """Append INFO text and an application-specific UTF-8 JSON `nfct` chunk.

    Called only on freshly exported, staged RIFF WAV files. Audio bytes are not
    rewritten. The caller publishes the completed file atomically.
    """
    info = b"INFO" + _chunk(b"ICMT", summary(metadata).encode("utf-8") + b"\0")
    info += _chunk(b"ISFT", f"NFC Tools {__version__}".encode() + b"\0")
    extra = _chunk(b"LIST", info) + _chunk(
        b"nfct", json.dumps(metadata, ensure_ascii=False, allow_nan=False).encode("utf-8")
    )
    with path.open("r+b") as handle:
        header = handle.read(12)
        if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("Clip metadata requires RIFF/WAVE")
        handle.seek(0, 2)
        size = handle.tell()
        padding = b"\0" if size % 2 else b""
        riff_size = size + len(padding) + len(extra) - 8
        if riff_size > 0xFFFFFFFF:
            raise ValueError("Clip exceeds RIFF size limit")
        handle.write(padding + extra)
        handle.seek(4)
        handle.write(struct.pack("<I", riff_size))
