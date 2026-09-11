"""BirdNET analyzer plugin."""
from __future__ import annotations
import csv
import shutil
import subprocess
from pathlib import Path

from .base import AnalyzerResult, register
from ..installer import status as installer_status, install_birdnet
from ..logging_setup import get
from ..filenames import parse

log = get("analyzer.birdnet")


class BirdNETPlugin:
    name = "birdnet"

    def _python(self) -> str:
        s = installer_status()["birdnet"]
        if not s["installed"]:
            install_birdnet()
            s = installer_status()["birdnet"]
        return s["python"]

    def run(self, wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        py = self._python()
        week = -1
        if not cfg.analyzers.birdnet_year_round:
            recorded = parse(wav_path.name)
            if not recorded:
                raise ValueError("BirdNET seasonal filtering needs a recording date in the filename.")
            date = recorded.recorded_at.date()
            # BirdNET uses four weeks per month (1–48), not ISO weeks.
            week = (date.month - 1) * 4 + min((date.day - 1) // 7, 3) + 1
        cmd = [
            py, "-m", "birdnet_analyzer.analyze", str(wav_path),
            "--output", str(output_dir),
            "--lat", str(cfg.site.latitude),
            "--lon", str(cfg.site.longitude),
            "--week", str(week),
            "--min_conf", str(cfg.analyzers.birdnet_min_conf),
            "--rtype", "csv", "table",
        ]
        log.info("Running BirdNET: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            log.error("BirdNET stderr:\n%s", proc.stderr)
            return AnalyzerResult(self.name, False, output_dir, message=proc.stderr[-500:])

        # Move sidecar files BirdNET sometimes drops next to the audio.
        for f in wav_path.parent.iterdir():
            if (f.is_file() and f.stem.startswith(wav_path.stem)
                    and f.suffix in (".csv", ".txt", ".parquet")):
                shutil.move(str(f), str(output_dir / f.name))

        count = _count_detections(output_dir)
        return AnalyzerResult(self.name, True, output_dir, detections_count=count)


def _count_detections(output_dir: Path) -> int:
    total = 0
    for csvf in output_dir.rglob("*.csv"):
        try:
            with csvf.open() as f:
                total += sum(1 for _ in csv.reader(f)) - 1
        except Exception:  # noqa: BLE001
            pass
    return max(total, 0)


register(BirdNETPlugin())
