"""ffmpeg-based segment recorder."""

from __future__ import annotations

import asyncio
import json
import re
import shlex
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .ffmpeg_locator import ensure_ffmpeg
from .filenames import make
from .logging_setup import get

log = get("recorder")


class Recorder:
    def __init__(
        self,
        device_input: list[str],
        out_dir: Path,
        prefix: str,
        session_date: date,
        sample_rate: int = 44100,
        channels: int = 1,
        bit_depth: int = 16,
        format_preset: str = "auto_native",
        segment_seconds: int = 3600,
        segment_seconds_for_start: Optional[Callable[[datetime, int], int]] = None,
        period_for_start: Optional[Callable[[datetime], str]] = None,
        on_segment_complete: Optional[Callable[[Path], None]] = None,
        on_level: Optional[Callable[[float], None]] = None,
        diagnostics_dir: Optional[Path] = None,
        diagnostics_metadata: Optional[dict] = None,
        timezone_name: str | None = None,
    ):
        self.device_input = device_input
        self.out_dir = out_dir
        self.prefix = prefix
        self.session_date = session_date
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_depth = bit_depth
        self.format_preset = format_preset
        self.segment_seconds = segment_seconds
        self.segment_seconds_for_start = segment_seconds_for_start
        self.period_for_start = period_for_start
        self.on_segment_complete = on_segment_complete
        self.on_level = on_level
        self.diagnostics_dir = diagnostics_dir
        self.diagnostics_metadata = diagnostics_metadata or {}
        self.timezone_name = timezone_name
        self.diagnostics_path: Optional[Path] = None
        self.command_line: list[str] = []

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._tasks: list[asyncio.Task] = []
        self._stopping = False
        self._last_open_path: Optional[Path] = None
        self._completed_paths: set[Path] = set()

    def _now(self) -> datetime:
        if self.timezone_name:
            try:
                return datetime.now(ZoneInfo(self.timezone_name))
            except ZoneInfoNotFoundError:
                pass
        return datetime.now()

    def _write_diagnostics_header(self, cmd: list[str]) -> None:
        if not self.diagnostics_dir:
            return
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        now = self._now()
        stamp = now.strftime("%Y%m%d-%H%M%S")
        self.diagnostics_path = self.diagnostics_dir / f"ffmpeg_recording_{stamp}.log"
        self.command_line = list(cmd)
        payload = {
            "started_at": now.isoformat(timespec="seconds"),
            "command": cmd,
            "command_shell": " ".join(shlex.quote(c) for c in cmd),
            "metadata": self.diagnostics_metadata,
        }
        with self.diagnostics_path.open("w", encoding="utf-8") as f:
            f.write("NFC Tools ffmpeg recording diagnostics\n")
            f.write(json.dumps(payload, indent=2, sort_keys=True, default=str))
            f.write("\n\n--- ffmpeg stderr ---\n")

    def _write_diagnostics_line(self, line: str) -> None:
        if not self.diagnostics_path:
            return
        try:
            with self.diagnostics_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:  # noqa: BLE001
            pass

    def diagnostics_info(self) -> dict:
        return {
            "ffmpeg_command": list(self.command_line),
            "ffmpeg_command_shell": " ".join(shlex.quote(c) for c in self.command_line) if self.command_line else "",
            "ffmpeg_log": str(self.diagnostics_path) if self.diagnostics_path else "",
            "metadata": dict(self.diagnostics_metadata),
        }

    def _segment_path(self, started_at: datetime) -> Path:
        period = self.period_for_start(started_at) if self.period_for_start else "nfc"
        filename_started_at = started_at.replace(microsecond=0)
        return self.out_dir / make(self.prefix, self.session_date, filename_started_at, period=period)

    def _segment_duration(self, started_at: datetime) -> int:
        if self.segment_seconds_for_start:
            return self.segment_seconds_for_start(started_at, self.segment_seconds)
        return max(1, int(self.segment_seconds))

    def _format_args(self) -> list[str]:
        """Return ffmpeg output-format args for the selected recording preset.

        The default is intentionally native/float-friendly. On macOS avfoundation
        commonly hands ffmpeg 48 kHz 32-bit float audio. Preserving that path is
        the closest match to DAW-style 48 kHz / 32-bit recording and avoids
        forcing 44.1 kHz / 16-bit unless the user asks for it.
        """
        preset = (self.format_preset or "auto_native").lower()
        channels = ["-ac", str(self.channels)]

        if preset in {"auto", "auto_native", "native", "native_float"}:
            return [*channels, "-c:a", "pcm_f32le"]
        if preset == "float_48k":
            return [*channels, "-ar", "48000", "-c:a", "pcm_f32le"]
        if preset == "s16_48k":
            return [*channels, "-ar", "48000", "-sample_fmt", "s16"]
        if preset in {"s16_441", "s16_44k", "s16_44_1k"}:
            return [*channels, "-ar", "44100", "-sample_fmt", "s16"]
        if preset == "s16_96k":
            return [*channels, "-ar", "96000", "-sample_fmt", "s16"]
        if preset == "float_96k":
            return [*channels, "-ar", "96000", "-c:a", "pcm_f32le"]

        sample_fmt = {16: "s16", 24: "s32", 32: "flt"}.get(self.bit_depth, "s16")
        return [*channels, "-ar", str(self.sample_rate), "-sample_fmt", sample_fmt]

    def _build_cmd(self, ffmpeg: str, output_path: Path, segment_seconds: int) -> list[str]:
        format_args = self._format_args()
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "info",
            "-nostdin",
            "-y",
            *self.device_input,
            "-t",
            str(max(1, int(segment_seconds))),
            *format_args,
            "-af",
            "ebur128=peak=true",
            str(output_path),
        ]
        return cmd

    async def _open_next_segment(self, ffmpeg: str) -> None:
        started_at = self._now()
        segment_seconds = self._segment_duration(started_at)
        output_path = self._segment_path(started_at)
        cmd = self._build_cmd(ffmpeg, output_path, segment_seconds)
        log.info("starting recorder: %s", " ".join(shlex.quote(c) for c in cmd))
        self.command_line = list(cmd)
        self._last_open_path = output_path
        self._write_diagnostics_line("--- segment command ---")
        self._write_diagnostics_line(" ".join(shlex.quote(c) for c in cmd))

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def start(self) -> None:
        ffmpeg = ensure_ffmpeg()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._write_diagnostics_header([])
        await self._open_next_segment(ffmpeg)
        self._tasks.append(asyncio.create_task(self._record_loop(ffmpeg)))

    def _mark_segment_complete(self, wav_path: Path) -> None:
        """Send a WAV to the analysis callback exactly once."""
        wav_path = wav_path.resolve()

        if wav_path in self._completed_paths:
            return

        if not wav_path.exists():
            log.warning("segment complete skipped because file does not exist: %s", wav_path)
            return

        if wav_path.stat().st_size == 0:
            log.warning("segment complete skipped because file is empty: %s", wav_path)
            return

        self._completed_paths.add(wav_path)

        if self.on_segment_complete:
            try:
                self.on_segment_complete(wav_path)
            except Exception as e:  # noqa: BLE001
                log.exception("segment callback failed: %s", e)

    async def _read_stderr(self, proc: asyncio.subprocess.Process):
        assert proc.stderr

        loud = re.compile(r"M:\s*(-?\d+\.\d+)")

        async for raw in proc.stderr:
            line = raw.decode(errors="replace").rstrip()
            log.debug("ffmpeg: %s", line)
            self._write_diagnostics_line(line)

            m = loud.search(line)
            if m and self.on_level:
                try:
                    self.on_level(float(m.group(1)))
                except Exception:
                    pass

    async def _record_loop(self, ffmpeg: str) -> None:
        while not self._stopping and self._proc:
            proc = self._proc
            completed = self._last_open_path
            await self._read_stderr(proc)
            await proc.wait()
            if completed:
                self._mark_segment_complete(completed)
            if self._stopping:
                break
            await self._open_next_segment(ffmpeg)

    async def stop(self) -> None:
        self._stopping = True

        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                self._proc.kill()
                await self._proc.wait()

        # Manual/scheduled stops often close a partial WAV before ffmpeg opens a
        # next segment. Treat that partial file as a completed segment so it is
        # analyzed immediately after Stop/Cancel.
        if self._last_open_path:
            self._mark_segment_complete(self._last_open_path)

        for t in self._tasks:
            if not t.done():
                t.cancel()

        self._tasks.clear()
        self._proc = None


async def measure_levels(device_input: list[str], seconds: int = 5) -> dict:
    """Quick non-recording level check used by the wizard."""
    ffmpeg = ensure_ffmpeg()
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "info",
        "-nostdin",
        *device_input,
        "-t",
        str(seconds),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, err = await proc.communicate()
    text = err.decode(errors="replace")

    mean = re.search(r"mean_volume:\s*(-?\d+\.\d+)\s*dB", text)
    peak = re.search(r"max_volume:\s*(-?\d+\.\d+)\s*dB", text)

    return {
        "mean_db": float(mean.group(1)) if mean else None,
        "peak_db": float(peak.group(1)) if peak else None,
    }

async def record_test_clip(
    device_input: list[str],
    out_path: Path,
    *,
    seconds: int = 10,
    sample_rate: int = 44100,
    channels: int = 1,
    bit_depth: int = 16,
    diagnostics_metadata: Optional[dict] = None,
) -> dict:
    """Record a short WAV through the same ffmpeg capture path used by NFC Tools."""
    ffmpeg = ensure_ffmpeg()
    sample_fmt = {16: "s16", 24: "s32", 32: "flt"}.get(bit_depth, "s16")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.with_suffix(".ffmpeg.log")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "info",
        "-nostdin",
        *device_input,
        "-t",
        str(seconds),
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        sample_fmt,
        str(out_path),
    ]

    header = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": seconds,
        "command": cmd,
        "command_shell": " ".join(shlex.quote(c) for c in cmd),
        "metadata": diagnostics_metadata or {},
    }

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stderr_text = stderr.decode(errors="replace")
    stdout_text = stdout.decode(errors="replace")

    with log_path.open("w", encoding="utf-8") as f:
        f.write("NFC Tools raw recording test diagnostics\n")
        f.write(json.dumps(header, indent=2, sort_keys=True, default=str))
        f.write("\n\n--- stdout ---\n")
        f.write(stdout_text)
        f.write("\n--- stderr ---\n")
        f.write(stderr_text)

    return {
        "ok": proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0,
        "returncode": proc.returncode,
        "wav_path": str(out_path),
        "wav_name": out_path.name,
        "log_path": str(log_path),
        "log_name": log_path.name,
        "command": cmd,
        "command_shell": header["command_shell"],
        "stderr_tail": "\n".join(stderr_text.splitlines()[-25:]),
        "size_bytes": out_path.stat().st_size if out_path.exists() else 0,
    }
def _diagnostic_shell(cmd: list[str]) -> str:
    return " ".join(shlex.quote(c) for c in cmd)


def _write_test_log(log_path: Path, title: str, header: dict, stdout_text: str, stderr_text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write(title + "\n")
        f.write(json.dumps(header, indent=2, sort_keys=True, default=str))
        f.write("\n\n--- stdout ---\n")
        f.write(stdout_text)
        f.write("\n--- stderr ---\n")
        f.write(stderr_text)


async def list_avfoundation_devices(log_path: Optional[Path] = None) -> dict:
    """Return ffmpeg's avfoundation device list and save the raw listing when requested."""
    ffmpeg = ensure_ffmpeg()
    cmd = [ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""]
    started_at = datetime.now().isoformat(timespec="seconds")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stdout_text = stdout.decode(errors="replace")
    stderr_text = stderr.decode(errors="replace")
    combined = stdout_text + "\n" + stderr_text

    devices: dict[str, list[dict[str, str]]] = {"video": [], "audio": []}
    section: Optional[str] = None
    for line in combined.splitlines():
        clean = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
        if "AVFoundation video devices" in clean:
            section = "video"
            continue
        if "AVFoundation audio devices" in clean:
            section = "audio"
            continue
        m = re.match(r"\[(\d+)\]\s+(.+)$", clean)
        if section and m:
            devices[section].append({"index": m.group(1), "name": m.group(2).strip()})

    header = {
        "started_at": started_at,
        "command": cmd,
        "command_shell": _diagnostic_shell(cmd),
        "returncode": proc.returncode,
        "note": "ffmpeg usually exits nonzero after listing avfoundation devices; the stderr list is the useful output.",
    }
    if log_path:
        _write_test_log(log_path, "NFC Tools avfoundation device-list diagnostics", header, stdout_text, stderr_text)

    return {
        "ok": bool(devices["audio"] or devices["video"]),
        "returncode": proc.returncode,
        "command": cmd,
        "command_shell": header["command_shell"],
        "devices": devices,
        "raw_output_tail": "\n".join(combined.splitlines()[-80:]),
        "log_path": str(log_path) if log_path else "",
        "log_name": log_path.name if log_path else "",
    }


def _raw_test_command_for_variant(
    ffmpeg: str,
    device_input: list[str],
    out_path: Path,
    *,
    variant: str,
    seconds: int,
    sample_rate: int,
    channels: int,
    bit_depth: int,
) -> tuple[list[str], dict]:
    """Build a test command that isolates format/rate choices in the capture path."""
    variant = variant or "current"
    base = [ffmpeg, "-hide_banner", "-loglevel", "info", "-nostdin", *device_input, "-t", str(seconds)]
    meta = {"variant": variant, "requested_channels": channels}

    if variant == "native_float":
        cmd = [*base, "-ac", str(channels), "-c:a", "pcm_f32le", str(out_path)]
        meta.update({
            "description": "Native input rate, 32-bit float WAV; no forced -ar or s16 conversion.",
            "forced_sample_rate": None,
            "codec": "pcm_f32le",
        })
        return cmd, meta

    if variant == "float_48k":
        cmd = [*base, "-ac", str(channels), "-ar", "48000", "-c:a", "pcm_f32le", str(out_path)]
        meta.update({
            "description": "Forced 48 kHz, 32-bit float WAV.",
            "forced_sample_rate": 48000,
            "codec": "pcm_f32le",
        })
        return cmd, meta

    if variant == "s16_48k":
        cmd = [*base, "-ac", str(channels), "-ar", "48000", "-sample_fmt", "s16", str(out_path)]
        meta.update({
            "description": "Forced 48 kHz, 16-bit WAV.",
            "forced_sample_rate": 48000,
            "sample_fmt": "s16",
        })
        return cmd, meta

    sample_fmt = {16: "s16", 24: "s32", 32: "flt"}.get(bit_depth, "s16")
    cmd = [
        *base,
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        sample_fmt,
        str(out_path),
    ]
    meta.update({
        "description": "Current NFC Tools raw-test path, using saved sample rate and bit depth.",
        "forced_sample_rate": sample_rate,
        "sample_fmt": sample_fmt,
        "bit_depth": bit_depth,
    })
    return cmd, meta


async def record_test_clip_variant(
    device_input: list[str],
    out_path: Path,
    *,
    variant: str = "current",
    seconds: int = 10,
    sample_rate: int = 44100,
    channels: int = 1,
    bit_depth: int = 16,
    diagnostics_metadata: Optional[dict] = None,
) -> dict:
    """Record a short WAV using a named diagnostic capture-path variant."""
    ffmpeg = ensure_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    safe_variant = re.sub(r"[^A-Za-z0-9_.-]+", "_", variant or "current")
    if safe_variant not in out_path.stem:
        out_path = out_path.with_name(f"{out_path.stem}_{safe_variant}{out_path.suffix}")
    log_path = out_path.with_suffix(".ffmpeg.log")

    cmd, variant_meta = _raw_test_command_for_variant(
        ffmpeg,
        device_input,
        out_path,
        variant=safe_variant,
        seconds=seconds,
        sample_rate=sample_rate,
        channels=channels,
        bit_depth=bit_depth,
    )
    header = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": seconds,
        "command": cmd,
        "command_shell": _diagnostic_shell(cmd),
        "metadata": diagnostics_metadata or {},
        "variant": variant_meta,
    }

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stdout_text = stdout.decode(errors="replace")
    stderr_text = stderr.decode(errors="replace")
    _write_test_log(log_path, "NFC Tools raw recording test diagnostics", header, stdout_text, stderr_text)

    return {
        "ok": proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0,
        "returncode": proc.returncode,
        "variant": safe_variant,
        "variant_description": variant_meta.get("description", safe_variant),
        "wav_path": str(out_path),
        "wav_name": out_path.name,
        "log_path": str(log_path),
        "log_name": log_path.name,
        "command": cmd,
        "command_shell": header["command_shell"],
        "stderr_tail": "\n".join(stderr_text.splitlines()[-30:]),
        "size_bytes": out_path.stat().st_size if out_path.exists() else 0,
    }
