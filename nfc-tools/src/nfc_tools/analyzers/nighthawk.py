"""Nighthawk analyzer plugin."""
from __future__ import annotations
import subprocess
from pathlib import Path

from .base import AnalyzerResult, register
from ..installer import status as installer_status, install_nighthawk
from ..logging_setup import get

log = get("analyzer.nighthawk")


class NighthawkPlugin:
	name = "nighthawk"

	def _python(self) -> str:
		s = installer_status()["nighthawk"]
		if not s["installed"]:
			install_nighthawk()
			s = installer_status()["nighthawk"]
		return s["python"]

	def run(self, wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult:
		output_dir.mkdir(parents=True, exist_ok=True)
		py = self._python()
		cmd = [
			py, "-m", "nighthawk.run_nighthawk", str(wav_path),
			"--raven-output", "--audacity-output",
			"--output-dir", str(output_dir),
		]
		log.info("running nighthawk: %s", " ".join(cmd))
		proc = subprocess.run(cmd, capture_output=True, text=True)
		if proc.returncode != 0:
			log.error("nighthawk stderr:\n%s", proc.stderr)
			return AnalyzerResult(self.name, False, output_dir, message=proc.stderr[-500:])

		count = sum(1 for _ in output_dir.rglob("*.txt"))
		return AnalyzerResult(self.name, True, output_dir, detections_count=count)


register(NighthawkPlugin())
