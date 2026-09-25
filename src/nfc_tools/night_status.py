"""Durable analysis checkpoints and recording coverage, independent of app uptime."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import manifest
from .filenames import parse
from .session_logging import read_log_rows


def load_progress(nd: Path) -> dict:
    path = nd / "logs" / "analysis_progress.json"
    if not path.exists():
        return {"files": {}}
    # A damaged checkpoint must not silently cause completed work to be rerun.
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError("Invalid night analysis checkpoint")
    return data


def save_progress(nd: Path, data: dict) -> None:
    folder = nd / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, folder / "analysis_progress.json")
    finally:
        Path(name).unlink(missing_ok=True)


def file_progress(nd: Path, wav: Path, data: dict) -> dict:
    stat = wav.stat()
    identity = [stat.st_size, stat.st_mtime_ns]
    entry = data.setdefault("files", {}).get(wav.name)
    if entry is None:
        # Older versions persisted successful inference only in the manifest.
        prior = {}
        for row in manifest.read_all(nd):
            if row.get("filename") == wav.name and str(stat.st_size) == row.get("size_bytes"):
                prior.update(part.split("=", 1) for part in row.get("statuses", "").split(";") if "=" in part)
        entry = {"identity": identity, "analyzers": {
            name: {"analysis": "ok", "clips": "pending"}
            for name, status in prior.items() if status == "ok"
        }}
        data["files"][wav.name] = entry
    elif entry.get("identity") != identity:
        entry = {"identity": identity, "analyzers": {}}
        data["files"][wav.name] = entry
    for stage in entry["analyzers"].values():
        if stage.get("analysis") == "ok" and any(not (nd / name).is_file() for name in stage.get("outputs", [])):
            stage.update(analysis="pending", clips="pending", error="Saved analyzer output is missing; recovery will rebuild it.")
    return entry


def summarize(nd: Path, cfg) -> dict:
    from .session import Session

    progress = load_progress(nd)
    rows = read_log_rows(nd / "logs" / "session_log.csv")
    windows = []
    for row in rows:
        if row["event"] not in {"session_scheduled", "recording_started"}:
            continue
        try:
            detail = json.loads(row.get("details") or "{}")
            start = datetime.fromisoformat(detail["scheduled_starts_at"])
            end = datetime.fromisoformat(detail["scheduled_ends_at"])
            windows.append((start.timestamp(), end.timestamp()))
        except (ValueError, KeyError, TypeError):
            continue
    files, intervals = [], []
    session = Session(cfg)
    try:
        for wav in sorted((nd / "audio").glob("*")):
            if not wav.is_file() or wav.suffix.lower() != ".wav":
                continue
            integrity = session._check_recording_integrity(wav)
            entry = file_progress(nd, wav, progress)
            stages = {name: entry["analyzers"].get(name, {"analysis": "pending", "clips": "pending"})
                      for name in cfg.analyzers.enabled}
            pending = any(s.get("analysis") != "ok" or s.get("clips") != "ok" for s in stages.values())
            files.append({"filename": wav.name, "duration_seconds": integrity.duration_seconds or 0,
                          "valid": integrity.ok_to_analyze, "message": integrity.message,
                          "analyzers": stages, "pending": pending and integrity.ok_to_analyze})
            try:
                parsed = parse(wav.name)
                if parsed and integrity.ok_to_analyze:
                    start = parsed.recorded_at.replace(tzinfo=ZoneInfo(cfg.site.timezone)).timestamp()
                    intervals.append((start, start + integrity.duration_seconds))
            except ValueError:
                pass
    finally:
        session._pool.shutdown(wait=False)
    known = {row["filename"] for row in manifest.read_all(nd) if row.get("filename")}
    known.update(progress.get("files", {}))
    present = {item["filename"] for item in files}
    for name in sorted(known - present):
        files.append({"filename": name, "duration_seconds": 0, "valid": False,
                      "message": "Recording file is missing. Restore it from a backup before recovery.",
                      "analyzers": {}, "pending": False})
    expected = merge_intervals(windows)
    recorded = merge_intervals(intervals)
    gaps = []
    covered = 0.0
    for start, end in expected:
        cursor = start
        for a, b in recorded:
            a, b = max(a, start), min(b, end)
            if b <= a:
                continue
            if a > cursor:
                gaps.append((cursor, a))
            covered += b - a
            cursor = max(cursor, b)
        if cursor < end:
            gaps.append((cursor, end))
    significant = [(a, b) for a, b in gaps if b - a > 2]
    return {"night": nd.name, "files": files, "expected_seconds": sum(b-a for a,b in expected) if expected else None,
            "recorded_seconds": sum(f["duration_seconds"] for f in files if f["valid"]),
            "covered_seconds": covered, "missing_seconds": sum(b-a for a,b in gaps),
            "gaps": [{"start": datetime.fromtimestamp(a, ZoneInfo(cfg.site.timezone)).isoformat(),
                      "end": datetime.fromtimestamp(b, ZoneInfo(cfg.site.timezone)).isoformat(),
                      "seconds": b-a} for a,b in significant],
            "pending_files": sum(f["pending"] for f in files),
            "invalid_files": sum(not f["valid"] for f in files),
            "exports": progress.get("ebird", {"status": "unknown"}),
            "coverage": "unknown" if not expected else "incomplete" if significant else "complete"}


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(set(intervals)):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def write_status_files(nd: Path, cfg, *, report: dict | None = None) -> None:
    """Publish a readable snapshot without interpreting unfinished work as silence."""
    from .clip_exporter import _segment_folder_name

    report = summarize(nd, cfg) if report is None else report
    updated = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"NFC Tools night status — {nd.name}", f"Updated: {updated}",
             "Snapshot only: recording or analysis may continue after this update.", "",
             f"Recording coverage: {report['coverage']} (gaps over 2 seconds are listed below).",
             f"Uncovered time within the scheduled window: {report['missing_seconds']:.1f} seconds." if report['expected_seconds'] is not None else "Scheduled recording window unknown.",
             f"Unreadable or missing recordings: {report['invalid_files']}.",
             f"Recordings awaiting completed analysis/review clips: {report['pending_files']}.",
             f"Exports: {report['exports'].get('status', 'unknown')}.",
             "Pending or failed analysis does NOT mean there were no detections.", ""]
    lines.extend(report.get("notes", []))
    for gap in report['gaps']:
        lines.append(f"Recording gap: {gap['start']} to {gap['end']} ({gap['seconds']:.1f}s).")
    for item in report['files']:
        stages = item['analyzers']
        if not item['valid']:
            status = "RECORDING PROBLEM — " + item['message']
        elif not stages:
            status = "RECORDED — no analyzers selected; detection status unknown."
        elif any(s.get('analysis') in {'failed', 'error'} or s.get('clips') == 'failed' for s in stages.values()):
            status = "ANALYSIS/CLIP EXPORT FAILED — detection results are incomplete."
        elif item['pending']:
            status = "RECORDED — analysis/clip export incomplete; detection status unknown."
        elif all(s.get('clip_count') == 0 for s in stages.values()):
            status = "COMPLETE — no detections meeting review criteria; no review clips produced."
        else:
            status = "COMPLETE — analysis and clip export finished; see results and review clips."
        detail = [item['filename'], status, f"Recording duration: {item['duration_seconds']:.1f} seconds.",
                  item['message'], f"Updated: {updated}"]
        for name, stage in stages.items():
            detail.append(f"{name}: analysis={stage.get('analysis', 'pending')}; clips={stage.get('clips', 'pending')}"
                          + (f"; review clips={stage['clip_count']}" if 'clip_count' in stage else '')
                          + (f"; {stage['error']}" if stage.get('error') else ''))
        detail.append("Incomplete analysis is not evidence of no detections. See ../../NIGHT_STATUS.txt for the night summary.")
        folder = nd / 'clips' / _segment_folder_name(Path(item['filename']))
        folder.mkdir(parents=True, exist_ok=True)
        _write_status_text(folder / 'STATUS.txt', '\n'.join(detail) + '\n')
        lines.append(f"{item['filename']}: {status}")
    _write_status_text(nd / 'NIGHT_STATUS.txt', '\n'.join(lines) + '\n')


def _write_status_text(path: Path, text: str) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
