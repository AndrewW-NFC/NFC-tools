"""ffmpeg-based segment recorder."""

from __future__ import annotations

import asyncio
import json
import re
import shlex
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from .ffmpeg_locator import ensure_ffmpeg
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
        segment_seconds: int = 3600,
        on_segment_complete: Optional[Callable[[Path], None]] = None,
        on_level: Optional[Callable[[float], None]] = None,
        diagnostics_dir: Optional[Path] = None,
        diagnostics_metadata: Optional[dict] = None,
    ):
        self.device_input = device_input
        self.out_dir = out_dir
        self.prefix = prefix
        self.session_date = session_date
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_depth = bit_depth
        self.segment_seconds = segment_seconds
        self.on_segment_complete = on_segment_complete
        self.on_level = on_level
        self.diagnostics_dir = diagnostics_dir
        self.diagnostics_metadata = diagnostics_metadata or {}
        self.diagnostics_path: Optional[Path] = None
        self.command_line: list[str] = []

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._tasks: list[asyncio.Task] = []
        self._stopping = False
        self._last_open_path: Optional[Path] = None
        self._completed_paths: set[Path] = set()


    def _write_diagnostics_header(self, cmd: list[str]) -> None:
        if not self.diagnostics_dir:
            return
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.diagnostics_path = self.diagnostics_dir / f"ffmpeg_recording_{stamp}.log"
        self.command_line = list(cmd)
        payload = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
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

    def _segment_pattern(self) -> str:
        prefix = f"{self.prefix}_{self.session_date.isoformat()}"
        return str(self.out_dir / f"{prefix}_%Y-%m-%d_%H-%M-%S.wav")

    def _build_cmd(self, ffmpeg: str) -> list[str]:
        sample_fmt = {16: "s16", 24: "s32", 32: "flt"}.get(self.bit_depth, "s16")
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "info",
            "-nostdin",
            *self.device_input,
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            "-sample_fmt",
            sample_fmt,
            "-f",
            "segment",
            "-segment_time",
            str(self.segment_seconds),
            "-segment_atclocktime",
            "0",
            "-reset_timestamps",
            "1",
            "-strftime",
            "1",
            "-af",
            "ebur128=peak=true",
            self._segment_pattern(),
        ]
        return cmd

    async def start(self) -> None:
        ffmpeg = ensure_ffmpeg()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        cmd = self._build_cmd(ffmpeg)
        log.info("starting recorder: %s", " ".join(shlex.quote(c) for c in cmd))
        self._write_diagnostics_header(cmd)

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._tasks.append(asyncio.create_task(self._read_stderr()))

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

    async def _read_stderr(self):
        assert self._proc and self._proc.stderr

        opening = re.compile(r"Opening '([^']+)' for writing")
        loud = re.compile(r"M:\s*(-?\d+\.\d+)")

        async for raw in self._proc.stderr:
            line = raw.decode(errors="replace").rstrip()
            log.debug("ffmpeg: %s", line)
            self._write_diagnostics_line(line)

            m = opening.search(line)
            if m:
                new_path = Path(m.group(1))

                # A new file opening means the previous file is finished and can
                # be analyzed while this new segment records.
                if self._last_open_path:
                    self._mark_segment_complete(self._last_open_path)

                self._last_open_path = new_path
                continue

            m = loud.search(line)
            if m and self.on_level:
                try:
                    self.on_level(float(m.group(1)))
                except Exception:
                    pass

        # If ffmpeg exits naturally, analyze the final file. When stop() is
        # called, stop() also calls this; _completed_paths prevents duplicates.
        if self._last_open_path:
            self._mark_segment_complete(self._last_open_path)

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
