"""Checkpointed, read-only source import into the normal nightly archive."""
from __future__ import annotations

import json
import errno
import filecmp
import math
import os
import re
import shutil
import subprocess
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from . import analyzers, filenames, manifest
from .config import Config, normalize_ebird_hotspot_id, normalize_ebird_state_province
from .ebird_export import EbirdExportOptions, prepare_record_export, options_for_site
from .ephemeris import astronomical_nfc_window, civil_recording_window
from .ffmpeg_locator import find_ffmpeg
from .paths import night_dir
from .segments import segment_period_for_start
from .session import Session
from .weather import environmental_snapshot, append_environment_csv, append_environment_text

UTC = timezone.utc


class ImportFile(BaseModel):
    relative_path: str
    start: datetime
    size_bytes: int = Field(ge=0)
    mtime_ns: int = Field(ge=0)


class ImportRequest(BaseModel):
    request_id: UUID
    source_folder: str
    output_folder: str
    site_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str
    ebird_state_province: str = ""
    ebird_hotspot_id: str = ""
    ebird_export_enabled: bool | None = None
    ebird_location_type: str = "personal"
    ebird_country_code: str = "US"
    ambiguous_time: str = "earlier"
    birdnet_year_round: bool = False
    enabled_analyzers: list[Literal["birdnet", "nighthawk", "wingbeats"]] | None = None
    wingbeats_enabled: bool | None = None
    files: list[ImportFile] = Field(min_length=1)
    timeline_confirmed: bool
    storage_confirmed: bool


def local_start(value: datetime, zone: ZoneInfo, ambiguous_time: str) -> datetime:
    if value.tzinfo:
        return value.astimezone(zone)
    candidates = [value.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
    valid = [dt for dt in candidates if dt.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == value]
    if not valid:
        raise ValueError(f"{value} does not exist in {zone.key} because the clocks move forward. Correct this start time.")
    return valid[-1] if ambiguous_time == "later" else valid[0]


def checked_source(root: Path, relative: str, expected: dict | None = None) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or root not in path.parents or not path.is_file():
        raise ValueError(f"Source must be a file inside the selected folder: {relative}")
    info = path.stat()
    if expected and (info.st_size != expected['size_bytes'] or info.st_mtime_ns != expected['mtime_ns']):
        raise ValueError(f"Source changed since review: {relative}. Scan and review again.")
    return path


def prepare(request: ImportRequest, cfg: Config, extensions: set[str], duration_reader) -> dict:
    if not request.timeline_confirmed or not request.storage_confirmed:
        raise ValueError("Confirm the timeline and storage plan before starting.")
    source = Path(request.source_folder).expanduser().resolve()
    output = Path(request.output_folder).expanduser().resolve()
    if not source.is_dir() or not output.is_dir():
        raise ValueError("Source and output folders must exist.")
    if source == output:
        raise ValueError("Choose separate source and output folders; they must be different folders.")
    zone = ZoneInfo(request.timezone)
    if request.ambiguous_time not in {"earlier", "later"}:
        raise ValueError("Choose earlier or later for repeated daylight-saving times.")
    enabled = list(dict.fromkeys(request.enabled_analyzers if request.enabled_analyzers is not None else cfg.analyzers.enabled))
    if request.enabled_analyzers is None and request.wingbeats_enabled is not None:
        enabled = [name for name in enabled if name != "wingbeats"]
        if request.wingbeats_enabled:
            enabled.append("wingbeats")
    if not enabled:
        raise ValueError("Select at least one analyzer before starting.")
    for name in enabled:
        analyzers.get(name)
    if not re.fullmatch(r"[A-Za-z0-9]+", cfg.recording.filename_prefix):
        raise ValueError("The recording filename prefix must contain only letters and numbers.")
    if cfg.schedule.segment_minutes < 1 or cfg.schedule.segment_minutes > 1440:
        raise ValueError("Segment length must be between 1 and 1440 minutes in Settings.")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise ValueError("FFmpeg is unavailable. Open Diagnostics to repair the installation.")
    actual = set()
    for directory, _, names in os.walk(source, followlinks=False):
        for name in names:
            path = Path(directory) / name
            if path.suffix.lower() in extensions:
                actual.add(str(path.relative_to(source)))
    supplied = [entry.relative_path for entry in request.files]
    if len(set(supplied)) != len(supplied) or set(supplied) != actual:
        raise ValueError("The source file list changed or is incomplete. Scan and review every file again.")
    files = []
    for entry in request.files:
        data = entry.model_dump(mode="json")
        path = checked_source(source, entry.relative_path, data)
        duration = duration_reader(path, ffmpeg)
        if duration is None or not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"Cannot read a positive audio duration for {entry.relative_path}.")
        start = local_start(entry.start, zone, request.ambiguous_time)
        if start.microsecond:
            raise ValueError("Start times must use whole seconds.")
        # Exercise date arithmetic during validation, before creating any output.
        end = start.astimezone(UTC) + timedelta(seconds=duration)
        if start.year < 1900 or end.year > 9998:
            raise ValueError("Recording dates must be between 1900 and 9998.")
        files.append({**data, "start": start.isoformat(), "duration": duration})
    # Fixed lossless PCM output: no compressed-source-size assumption.
    pcm_bytes = sum(file['duration'] for file in files) * 48000 * 1 * 4
    required = int(pcm_bytes * 1.35) + 128 * 1024 * 1024
    if shutil.disk_usage(output).free < required:
        raise ValueError("Insufficient output space for 48 kHz mono WAV audio, results, and estimated clips.")
    snapshot = cfg.model_copy(deep=True)
    snapshot.site.name = request.site_name
    snapshot.site.latitude = request.latitude
    snapshot.site.longitude = request.longitude
    snapshot.site.timezone = zone.key
    snapshot.site.ebird_state_province = normalize_ebird_state_province(request.ebird_state_province)
    snapshot.site.ebird_export_enabled = request.ebird_export_enabled
    snapshot.site.ebird_location_type = request.ebird_location_type
    snapshot.site.ebird_country_code = request.ebird_country_code
    from .ebird_locations import selected_hotspot
    snapshot.site.ebird_hotspot_details = selected_hotspot(request.ebird_hotspot_id, cfg.site) if request.ebird_location_type == "hotspot" and snapshot.site.exports_enabled else {}
    if snapshot.site.exports_enabled and not snapshot.site.ebird_state_province:
        raise ValueError("Enter the eBird state/province code before starting.")
    if snapshot.site.exports_enabled and not re.fullmatch(r"[A-Z0-9]{1,3}", snapshot.site.ebird_state_province):
        raise ValueError("eBird state/province must be a 1-3 character region code, such as MA.")
    snapshot.site.ebird_hotspot_id = normalize_ebird_hotspot_id(request.ebird_hotspot_id)
    if snapshot.site.exports_enabled and not re.fullmatch(r"[A-Z]{2}", snapshot.site.ebird_country_code):
        raise ValueError("eBird country code must be two uppercase letters.")
    snapshot.analyzers.enabled = enabled
    snapshot.analyzers.birdnet_year_round = request.birdnet_year_round
    snapshot.recording.save_location = str(output)
    return {
        "id": str(request.request_id), "source": str(source), "output": str(output),
        "config": snapshot.model_dump(), "files": files, "file_index": 0,
        "offset": 0.0, "segment": None, "completed_segments": 0,
        "state": "ready", "message": "Ready to import.",
    }


@contextmanager
def output_lock(output: Path):
    """OS lock releases on process exit, allowing checkpoint recovery after a crash."""
    path = output / ".nfc-import.lock"
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError("Another importer is using this output folder.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError("Another importer is using this output folder.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def segment_details(start: datetime, remaining: float, cfg: Config) -> tuple[str, str, float]:
    date = start.date() - timedelta(days=1) if start.hour < 12 else start.date()
    astro = astronomical_nfc_window(date, cfg.site.latitude, cfg.site.longitude, cfg.site.timezone)
    civil = civil_recording_window(date, cfg.site.latitude, cfg.site.longitude, cfg.site.timezone)
    tomorrow = start.date() + timedelta(days=1)
    midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=start.tzinfo)
    noon = start.replace(hour=12, minute=0, second=0, microsecond=0)
    if noon <= start:
        noon += timedelta(days=1)
    current = start.astimezone(UTC)
    lengths = [(dt.astimezone(UTC) - current).total_seconds() for dt in (*astro, *civil, midnight, noon)]
    # Round protocol boundaries to whole seconds to match archive filenames.
    length = min(remaining, cfg.schedule.segment_minutes * 60,
                 *(math.ceil(n) for n in lengths if n > 0.001))
    period = segment_period_for_start(current, astro[0].astimezone(UTC), astro[1].astimezone(UTC))
    return date.isoformat(), period, length


class ImportRunner:
    def __init__(self, job: dict):
        self.job = job
        self.guard = threading.RLock()
        self.pause_requested = threading.Event()
        self.thread: threading.Thread | None = None
        self.directory = Path(job['output']) / '.nfc-imports' / job['id']
        if Path(job['output']).resolve() not in self.directory.resolve().parents:
            raise ValueError('Import checkpoint folder must stay inside the output folder.')
        self.directory.mkdir(parents=True, exist_ok=True)
        self._last_analysis_message = None
        self._part_counts = {}
        self._seen_session_events = set()

    def log_event(self, message: str, level: str = 'info'):
        """Keep the entire run history outside the bounded status response."""
        message = re.sub(r'\bbirdnet\b', 'BirdNET', message, flags=re.I)
        message = re.sub(r'\bnighthawk\b', 'Nighthawk', message, flags=re.I)
        message = re.sub(r'\bsegment(s)?\b', lambda m: 'parts' if m[1] else 'part', message, flags=re.I)
        with self.guard:
            row = {'time': datetime.now(ZoneInfo(self.job['config']['site']['timezone'])).isoformat(timespec='seconds'),
                   'level': level, 'file': self.job.get('current_file'), 'message': message}
            with (self.directory / 'events.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(row) + '\n')

    def read_events(self, cursor: int = 0, limit: int = 200):
        with self.guard:
            path = self.directory / 'events.jsonl'
            if not path.exists():
                return {'events': [], 'cursor': 0}
            rows = []
            with path.open('rb') as handle:
                handle.seek(min(cursor, path.stat().st_size))
                for _ in range(limit):
                    line = handle.readline()
                    if not line:
                        break
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
                return {'events': rows, 'cursor': handle.tell()}

    def plan(self):
        return {key: self.job[key] for key in ('id', 'source', 'output', 'files', 'config')}

    def part_counts(self):
        index = self.job['file_index']
        if index >= len(self.job['files']):
            return 0, 0
        if index not in self._part_counts:
            file = self.job['files'][index]
            cfg = Config(**self.job['config'])
            start = datetime.fromisoformat(file['start']).astimezone(UTC)
            zone = ZoneInfo(cfg.site.timezone)
            offsets = []
            offset = 0.0
            while file['duration'] - offset >= 0.001:
                offsets.append(offset)
                _, _, length = segment_details((start + timedelta(seconds=offset)).astimezone(zone),
                                                file['duration'] - offset, cfg)
                offset += length
            self._part_counts[index] = offsets
        offsets = self._part_counts[index]
        done = sum(offset < self.job['offset'] - 0.001 for offset in offsets)
        return min(done + 1, len(offsets)), len(offsets)

    def save(self):
        with self.guard:
            temp = self.directory / 'job.tmp'
            with temp.open('w') as handle:
                json.dump(self.job, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(self.directory / 'job.json')

    def update(self, **values):
        with self.guard:
            changed = values.get('message') and values['message'] != self.job.get('message')
            self.job.update(values)
            self.save()
            if changed:
                self.log_event(values['message'], 'error' if values.get('state') == 'failed' else 'info')

    def status(self):
        with self.guard:
            index = self.job['file_index']
            file = self.job['files'][index] if index < len(self.job['files']) else None
            part, parts = self.part_counts()
            try:
                free = shutil.disk_usage(self.job['output']).free
            except OSError:
                free = None
            return {key: self.job.get(key) for key in (
                'id', 'state', 'message', 'file_index', 'completed_segments', 'current_file',
                'current_segment', 'current_analyzer', 'output',
            )} | {"total_files": len(self.job['files']), "pause_requested": self.pause_requested.is_set(),
                 'part_index': part, 'parts_in_file': parts,
                 'file_duration': file['duration'] if file else 0,
                 'file_completed_seconds': self.job['offset'] if file else 0,
                 'analyzer_started_at': self.job.get('analyzer_started_at'),
                 'free_bytes': free}

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.pause_requested.clear()
        self._last_analysis_message = None
        self.update(state='running', message='Starting import…')
        self.thread = threading.Thread(target=self.run, name='nfc-import', daemon=True)
        self.thread.start()

    def pause(self):
        self.pause_requested.set()
        self.log_event('Pause requested. Finishing the current part before pausing.')

    def run(self):
        cfg = Config(**self.job['config'])
        # Old checkpoints did not use seasonal filtering. Preserve their run settings.
        if 'birdnet_year_round' not in self.job['config']['analyzers']:
            cfg.analyzers.birdnet_year_round = True
        session = Session(cfg, on_status=self.analysis_status)
        try:
            with output_lock(Path(self.job['output'])):
                session._start_sleep_prevention('analysis')
                while self.job['file_index'] < len(self.job['files']):
                    if self.pause_requested.is_set():
                        self.update(state='paused', message='Paused. Resume to continue from the next unfinished part.')
                        return
                    allowed, reason, _ = session._analysis_power_decision()
                    if not allowed:
                        self.update(state='paused', message=reason + ' Resume when power conditions allow.')
                        return
                    self.process_segment(session)
                self.update(state='complete', message='All recordings processed and analyzed.', current_analyzer=None)
        except Exception as exc:
            self.update(state='failed', message=str(exc), current_analyzer=None)
        finally:
            session._sleep_preventer.stop()
            session._pool.shutdown(wait=True)

    def analysis_status(self, status):
        for row in status.get('session_log', []):
            if row.get('event') not in {'clips_exported', 'clip_export_failed'}:
                continue
            key = (row.get('timestamp'), row.get('event'), row.get('filename'), row.get('analyzer'), row.get('message'))
            if key not in self._seen_session_events:
                self._seen_session_events.add(key)
                self.log_event(row.get('message', ''), 'warning' if row['event'] == 'clip_export_failed' else 'info')
        analysis = status.get('analysis') or {}
        message = analysis.get('message')
        if analysis.get('current_file') and message != self._last_analysis_message:
            self._last_analysis_message = message
            analyzer = analysis.get('current_analyzer')
            values = {}
            if analyzer != self.job.get('current_analyzer'):
                values['analyzer_started_at'] = datetime.now(UTC).isoformat() if analyzer else None
            message = message.replace(analysis['current_file'], self.job.get('current_file') or analysis['current_file'])
            # An analyzer completing a part is not a whole recording completing.
            if message.startswith('Analysis complete for'):
                message = 'Part analysis finished: ' + message.split(': ', 1)[-1]
            self.update(current_analyzer=analyzer, message=message, **values)

    def process_segment(self, session):
        file = self.job['files'][self.job['file_index']]
        source = checked_source(Path(self.job['source']), file['relative_path'], file)
        cfg = session.cfg
        start = (datetime.fromisoformat(file['start']).astimezone(UTC) +
                 timedelta(seconds=self.job['offset'])).astimezone(ZoneInfo(cfg.site.timezone))
        remaining = file['duration'] - self.job['offset']
        if remaining < 0.001:
            self.log_event(f"Recording complete: {file['relative_path']}")
            self.update(file_index=self.job['file_index'] + 1, offset=0.0, segment=None)
            return
        if self.job['segment'] is None:
            date, period, length = segment_details(start, remaining, cfg)
            root = Path(cfg.recording.save_location).resolve()
            for folder in ('audio', 'results', 'logs', 'clips'):
                if root not in (root / date / folder).resolve().parents:
                    raise ValueError('Archive folders must stay inside the selected output folder.')
            nd = night_dir(date, cfg.recording.save_location)
            name = filenames.make(cfg.recording.filename_prefix, start.date(), start, period,
                                  filenames.next_index_for_directory(nd / 'audio'))
            self.update(segment={'path': str(nd / 'audio' / name), 'duration': length, 'published': False})
        segment = self.job['segment']
        wav = Path(segment['path'])
        nd = wav.parent.parent
        session._prepare_session_log(nd)
        # Existing night logs may include other runs; only relay newly emitted events.
        self._seen_session_events.update(
            (row.get('timestamp'), row.get('event'), row.get('filename'), row.get('analyzer'), row.get('message'))
            for row in session.status.get('session_log', [])
        )
        part, parts = self.part_counts()
        self.update(current_file=file['relative_path'], current_segment=wav.name, current_analyzer=None,
                    analyzer_started_at=None,
                    message=f"Preparing part {part} of {parts} of recording {self.job['file_index'] + 1}: {file['relative_path']}")
        temp = self.directory / 'segment.wav'
        if not segment['published']:
            # A completed staging file is retained until the publication checkpoint is durable.
            if wav.exists():
                if not temp.exists() or not (os.path.samefile(temp, wav) or filecmp.cmp(temp, wav, shallow=False)):
                    raise ValueError(f"Output already exists; refusing to overwrite {wav}")
            else:
                if shutil.disk_usage(nd).free < segment['duration'] * 192000 + 64 * 1024 * 1024:
                    raise ValueError('Output drive is low on space. Free space and resume.')
                temp.unlink(missing_ok=True)
                command = [find_ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
                           '-ss', str(self.job['offset']), '-i', str(source), '-t', str(segment['duration']),
                           '-map', '0:a:0', '-vn', '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s32le', str(temp)]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    raise ValueError(f"Conversion failed for {file['relative_path']}: {result.stderr[-1500:]}")
                integrity = session._check_recording_integrity(temp)
                if not integrity.ok_to_analyze or abs((integrity.duration_seconds or 0) - segment['duration']) > 0.15:
                    raise ValueError(f"Converted audio is incomplete for {file['relative_path']}.")
                checked_source(Path(self.job['source']), file['relative_path'], file)
                # Atomic no-overwrite publication; staging and archive are on the same volume.
                try:
                    os.link(temp, wav)
                except OSError as exc:
                    if exc.errno not in {errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS, errno.EXDEV}:
                        raise
                    # Some removable drives do not support hard links. Exclusive creation
                    # still prevents overwrites; a failed copy is removed before retry.
                    with wav.open('xb') as destination:
                        try:
                            with temp.open('rb') as audio:
                                shutil.copyfileobj(audio, destination)
                            destination.flush()
                            os.fsync(destination.fileno())
                        except BaseException:
                            destination.close()
                            wav.unlink(missing_ok=True)
                            raise
            manifest.append(nd, {'session_date': nd.name, 'recorded_at': start,
                                'filename': wav.name, 'size_bytes': wav.stat().st_size,
                                'statuses': 'import=ok',
                                'notes': f"Import {self.job['id']}; source={file['relative_path']}; offset={self.job['offset']}; start={start.isoformat()}"})
            self.update(segment={**segment, 'published': True, 'size_bytes': wav.stat().st_size, 'mtime_ns': wav.stat().st_mtime_ns})
        temp.unlink(missing_ok=True)
        segment = self.job['segment']
        if (not wav.is_file() or wav.stat().st_size != segment['size_bytes']
                or wav.stat().st_mtime_ns != segment['mtime_ns']):
            raise ValueError(f"Processed segment is missing or changed: {wav}")
        if not segment.get('environment_logged'):
            self.log_event('Looking up environmental conditions for ' + start.isoformat(timespec='seconds'))
            row = environmental_snapshot(cfg.site.latitude, cfg.site.longitude, cfg.site.timezone, start, historical=True)
            append_environment_csv(nd, row)
            append_environment_text(nd, row)
            self.update(segment={**segment, 'environment_logged': True})
            self.log_event('Environmental conditions saved.' if row['available'] else
                           'Environmental conditions unavailable: ' + row.get('notes', ''),
                           'info' if row['available'] else 'warning')
        statuses = session._analyze_one(wav)
        if not statuses or any(value != 'ok' for value in statuses.values()):
            raise ValueError(f"Analysis failed for {wav.name}: {statuses}. Check the night logs, then resume to retry.")
        self.refresh_ebird_exports(nd, cfg)
        self.update(offset=self.job['offset'] + segment['duration'], segment=None,
                    completed_segments=self.job['completed_segments'] + 1)
        self.log_event(f"Part {part} of {parts} finished for {file['relative_path']}.")
        if file['duration'] - self.job['offset'] < 0.001:
            self.log_event(f"Recording complete: {file['relative_path']}")
            self.update(file_index=self.job['file_index'] + 1, offset=0.0)

    def refresh_ebird_exports(self, night_path: Path, cfg: Config):
        result = prepare_record_export(
            night_path,
            options_for_site(cfg.site),
        )
        paths = ", ".join(str(path) for path in [result.get("combined_import_path"), *result["import_paths"]] if path)
        self.log_event(f"eBird import files updated: {paths or 'none'}" if cfg.site.exports_enabled else "Review CSVs updated in review/; eBird exports not requested.")


class ImportManager:
    def __init__(self):
        self.guard = threading.Lock()
        self.runner: ImportRunner | None = None

    def active(self):
        return self.runner and self.runner.thread and self.runner.thread.is_alive()

    def start(self, request, cfg, extensions, duration_reader):
        with self.guard:
            if self.runner and self.runner.job['id'] == str(request.request_id):
                if self.runner.job['state'] != 'complete':
                    self.runner.start()
                return self.runner.status()
            if self.active():
                raise ValueError('An import is already running. Pause it before starting another.')
            checkpoint = Path(request.output_folder).expanduser() / '.nfc-imports' / str(request.request_id) / 'job.json'
            if checkpoint.exists():
                self.runner = ImportRunner(json.loads(checkpoint.read_text()))
                if self.runner.job['state'] != 'complete':
                    self.runner.start()
                return self.runner.status()
            job = prepare(request, cfg, extensions, duration_reader)
            self.runner = ImportRunner(job)
            self.runner.start()
            return self.runner.status()

    def recover(self, output: str, job_id: UUID):
        with self.guard:
            if self.runner and self.runner.job['id'] == str(job_id):
                return self.runner
            if self.active():
                raise ValueError('Another import is running.')
            root = Path(output).expanduser().resolve()
            path = root / '.nfc-imports' / str(job_id) / 'job.json'
            job = json.loads(path.read_text())
            if job['id'] != str(job_id) or Path(job['output']).resolve() != root:
                raise ValueError('Checkpoint does not match this output folder.')
            self.runner = ImportRunner(job)
            if job['state'] != 'complete':
                self.runner.update(state='paused', message='Saved import recovered. Resume to continue.')
            return self.runner


manager = ImportManager()
