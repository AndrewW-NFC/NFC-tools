"""ffmpeg-based segment recorder."""
from __future__ import annotations
import asyncio
import re
import shlex
from datetime import date
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
		sample_rate: int = 22050,
		channels: int = 1,
		bit_depth: int = 16,
		segment_seconds: int = 3600,
		on_segment_complete: Optional[Callable[[Path], None]] = None,
		on_level: Optional[Callable[[float], None]] = None,
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
		self._proc: Optional[asyncio.subprocess.Process] = None
		self._tasks: list[asyncio.Task] = []
		self._stopping = False

	def _segment_pattern(self) -> str:
		prefix = f"{self.prefix}_{self.session_date.isoformat()}"
		return str(self.out_dir / f"{prefix}_%Y-%m-%d_%H-%M-%S.wav")

	def _build_cmd(self, ffmpeg: str) -> list[str]:
		sample_fmt = {16: "s16", 24: "s32", 32: "flt"}.get(self.bit_depth, "s16")
		cmd = [
			ffmpeg, "-hide_banner", "-loglevel", "info",
			"-nostdin",
			*self.device_input,
			"-ac", str(self.channels),
			"-ar", str(self.sample_rate),
			"-sample_fmt", sample_fmt,
			"-f", "segment",
			"-segment_time", str(self.segment_seconds),
			"-segment_atclocktime", "0",
			"-reset_timestamps", "1",
			"-strftime", "1",
			"-af", "ebur128=peak=true",
			self._segment_pattern(),
		]
		return cmd

	async def start(self) -> None:
		ffmpeg = ensure_ffmpeg()
		self.out_dir.mkdir(parents=True, exist_ok=True)
		cmd = self._build_cmd(ffmpeg)
		log.info("starting recorder: %s", " ".join(shlex.quote(c) for c in cmd))
		self._proc = await asyncio.create_subprocess_exec(
			*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
		)
		self._tasks.append(asyncio.create_task(self._read_stderr()))

	async def _read_stderr(self):
		assert self._proc and self._proc.stderr
		opening = re.compile(r"Opening '([^']+)' for writing")
		loud = re.compile(r"M:\s*(-?\d+\.\d+)")
		last_open: Optional[Path] = None
		async for raw in self._proc.stderr:
			line = raw.decode(errors="replace").rstrip()
			log.debug("ffmpeg: %s", line)
			m = opening.search(line)
			if m:
				new_path = Path(m.group(1))
				if last_open and self.on_segment_complete:
					try:
						self.on_segment_complete(last_open)
					except Exception as e:  # noqa: BLE001
						log.exception("segment callback failed: %s", e)
				last_open = new_path
				continue
			m = loud.search(line)
			if m and self.on_level:
				try:
					self.on_level(float(m.group(1)))
				except Exception:
					pass
		if last_open and not self._stopping and self.on_segment_complete:
			self.on_segment_complete(last_open)

	async def stop(self) -> None:
		self._stopping = True
		if self._proc and self._proc.returncode is None:
			self._proc.terminate()
			try:
				await asyncio.wait_for(self._proc.wait(), timeout=10)
			except asyncio.TimeoutError:
				self._proc.kill()
		for t in self._tasks:
			t.cancel()


async def measure_levels(device_input: list[str], seconds: int = 5) -> dict:
	"""Quick non-recording level check used by the wizard."""
	ffmpeg = ensure_ffmpeg()
	cmd = [
		ffmpeg, "-hide_banner", "-loglevel", "info", "-nostdin",
		*device_input, "-t", str(seconds),
		"-af", "volumedetect", "-f", "null", "-",
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
