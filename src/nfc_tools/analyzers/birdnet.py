"""BirdNET analyzer plugin."""
from __future__ import annotations
import os
import csv
import json
import tempfile
import shutil
import subprocess
from pathlib import Path

from .base import AnalyzerResult, register
from ..installer import status as installer_status, install_birdnet, BIRDNET_REQUIREMENT
from ..paths import data_dir
from ..logging_setup import get
from ..filenames import parse
from ..birdnet_policy import enabled_species, keep_detection, HIGH_SENSITIVITY_CONFIDENCE

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
        subprocess_options = {"capture_output": True, "text": True}
        subprocess_options["env"] = dict(os.environ, BIRDNET_APP_DATA=str(data_dir() / "birdnet-models"))
        week = -1
        if not cfg.analyzers.birdnet_year_round:
            recorded = parse(wav_path.name)
            if not recorded:
                raise ValueError("BirdNET seasonal filtering needs a recording date in the filename.")
            date = recorded.recorded_at.date()
            # BirdNET uses four weeks per month (1–48), not ISO weeks.
            week = (date.month - 1) * 4 + min((date.day - 1) // 7, 3) + 1
        overrides = enabled_species(cfg.analyzers)
        species_path = output_dir / "species_list.txt"
        if overrides:
            # Run in BirdNET's private environment; NFC Tools need not import TensorFlow.
            with tempfile.TemporaryDirectory(prefix="birdnet-species-") as temporary:
                normal_path = Path(temporary) / "normal.txt"
                labels_path = Path(temporary) / "labels.json"
                proc = subprocess.run([
                    py, "-c", _SPECIES_SCRIPT_V3, str(normal_path), str(labels_path),
                    str(cfg.site.latitude), str(cfg.site.longitude), str(week),
                ], **subprocess_options)
                if proc.returncode != 0:
                    return AnalyzerResult(self.name, False, output_dir, message="BirdNET species list failed: " + proc.stderr[-500:])
                labels = json.loads(labels_path.read_text(encoding="utf-8"))
                additions = {label for label in labels if label.split("_", 1)[0] in overrides}
                if not additions:
                    return AnalyzerResult(self.name, False, output_dir, message="BirdNET model has no labels for the enabled sensitivity groups.")
                eligible = set(normal_path.read_text(encoding="utf-8").splitlines()) | additions
                species_path.write_text("\n".join(sorted(eligible)) + "\n", encoding="utf-8")
        location_args = ["--slist", str(species_path)] if overrides else [
            "--lat", str(cfg.site.latitude), "--lon", str(cfg.site.longitude),
            *([] if week == -1 else ["--week", str(week)]),
        ]
        threshold = cfg.analyzers.birdnet_min_conf
        if overrides:
            threshold = min(threshold, HIGH_SENSITIVITY_CONFIDENCE)
        cmd = [
            py, "-m", "birdnet_analyzer.analyze", str(wav_path),
            "--output", str(output_dir),
            *location_args,
            "--min_conf", str(threshold),
            "--rtype", "csv", "table",
            "--birdnet", "3.0", "--split_tables", "--n_workers", "1",
        ]
        log.info("Running BirdNET: %s", " ".join(cmd))
        proc = subprocess.run(cmd, **subprocess_options)
        if proc.returncode != 0:
            log.error("BirdNET stderr:\n%s", proc.stderr)
            return AnalyzerResult(self.name, False, output_dir, message=proc.stderr[-500:])

        # Move sidecar files BirdNET sometimes drops next to the audio.
        for f in wav_path.parent.iterdir():
            if (f.is_file() and f.stem.startswith(wav_path.stem)
                    and f.suffix in (".csv", ".txt", ".parquet")):
                shutil.move(str(f), str(output_dir / f.name))

        if overrides:
            _filter_results(output_dir, cfg.analyzers)
        (output_dir / "nfc_birdnet_policy.json").write_text(json.dumps({
            "model": "3.0",
            "analyzer_requirement": BIRDNET_REQUIREMENT,
            "model_release": "preview3.1",
            "birdnet_library": "1.4.0",
            "latitude": cfg.site.latitude,
            "longitude": cfg.site.longitude,
            "week": week,
            "general_min_confidence": cfg.analyzers.birdnet_min_conf,
            "winter_finch_sensitivity": getattr(cfg.analyzers, "birdnet_winter_finch_sensitivity", False),
            "owl_sensitivity": getattr(cfg.analyzers, "birdnet_owl_sensitivity", False),
            "override_min_confidence": min(cfg.analyzers.birdnet_min_conf, HIGH_SENSITIVITY_CONFIDENCE) if overrides else None,
            "override_species": sorted(overrides),
        }, indent=2) + "\n", encoding="utf-8")
        count = _count_detections(output_dir)
        return AnalyzerResult(self.name, True, output_dir, detections_count=count)


_SPECIES_SCRIPT_V3 = """
import json
import sys
from pathlib import Path
from birdnet_analyzer.species import species
from birdnet_analyzer.model_utils import acoustic_species_list
week = int(sys.argv[5])
species(sys.argv[1], lat=float(sys.argv[3]), lon=float(sys.argv[4]), week=None if week == -1 else week, sf_thresh=0.03)
Path(sys.argv[2]).write_text(json.dumps(acoustic_species_list("3.0")), encoding="utf-8")
"""


def _filter_results(output_dir: Path, analyzers) -> None:
    """Keep CSV and Raven tables consistent with the per-species review policy."""
    for path in sorted(output_dir.rglob("*")):
        if path.suffix != ".csv" and not path.name.endswith(".selection.table.txt"):
            continue
        if path.name in {"BirdNET_analysis_params.csv", "birdnet.analyze-params.csv"}:
            continue
        delimiter = "\t" if path.suffix == ".txt" else ","
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            fields = reader.fieldnames
            if not fields or "confidence" not in {field.lower().strip() for field in fields}:
                raise ValueError(f"Unrecognized BirdNET results: {path.name}")
            rows = [row for row in reader if keep_detection(row, analyzers)]
        staged = path.with_suffix(path.suffix + ".tmp")
        with staged.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
            writer.writeheader()
            for index, row in enumerate(rows, 1):
                if "Selection" in row:
                    row["Selection"] = str(index)
                writer.writerow(row)
        staged.replace(path)


def _count_detections(output_dir: Path) -> int:
    total = 0
    for csvf in output_dir.rglob("*.csv"):
        try:
            with csvf.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and "Confidence" in reader.fieldnames:
                    total += sum(1 for _ in reader)
        except Exception:  # noqa: BLE001
            pass
    return max(total, 0)


register(BirdNETPlugin())
