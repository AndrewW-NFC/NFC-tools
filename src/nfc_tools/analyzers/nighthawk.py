"""Nighthawk analyzer plugin."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import AnalyzerResult, register
from ..installer import install_nighthawk
from ..installer import status as installer_status
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

    def _run_probe(self, py: str, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [py, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _diagnostics(self, py: str) -> str:
        py_path = Path(py)
        bin_dir = py_path.parent
        lines: list[str] = []

        lines.append(f"Managed Python: {py}")
        lines.append(f"Managed bin dir: {bin_dir}")

        try:
            lines.append("Managed bin contents: " + ", ".join(sorted(p.name for p in bin_dir.iterdir())[:80]))
        except Exception as e:  # noqa: BLE001
            lines.append(f"Could not list managed bin dir: {e}")

        probes = [
            ("python version", ["-c", "import sys; print(sys.version)"]),
            ("pip show nighthawk", ["-m", "pip", "show", "nighthawk"]),
            (
                "import nighthawk",
                [
                    "-c",
                    (
                        "import json, sys; "
                        "import nighthawk; "
                        "print(json.dumps({"
                        "'python': sys.version, "
                        "'module_file': getattr(nighthawk, '__file__', None)"
                        "}))"
                    ),
                ],
            ),
            (
                "import nighthawk.run_nighthawk",
                ["-c", "import nighthawk.run_nighthawk as r; print('ok')"],
            ),
        ]

        for label, args in probes:
            try:
                proc = self._run_probe(py, args)
                lines.append(f"[{label}] returncode={proc.returncode}")
                if proc.stdout.strip():
                    lines.append(proc.stdout.strip()[-1000:])
                if proc.stderr.strip():
                    lines.append("stderr: " + proc.stderr.strip()[-1000:])
            except Exception as e:  # noqa: BLE001
                lines.append(f"[{label}] probe failed: {e}")

        return "\n".join(lines)

    def _candidate_commands(self, py: str, wav_path: Path, output_dir: Path) -> list[list[str]]:
        py_path = Path(py)
        bin_dir = py_path.parent

        candidates: list[list[str]] = []

        for exe_name in ("nighthawk", "nighthawk.exe"):
            exe = bin_dir / exe_name
            if exe.exists():
                candidates.append(
                    [
                        str(exe),
                        str(wav_path),
                        "--raven-output",
                        "--audacity-output",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        candidates.append(
            [
                py,
                "-m",
                "nighthawk.run_nighthawk",
                str(wav_path),
                "--raven-output",
                "--audacity-output",
                "--output-dir",
                str(output_dir),
            ]
        )

        return candidates

    def run(self, wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        py = self._python()

        log.info("nighthawk managed python: %s", py)

        failures: list[str] = []
        for cmd in self._candidate_commands(py, wav_path, output_dir):
            log.info("running nighthawk candidate: %s", " ".join(cmd))
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError as e:
                failures.append(f"Command not found: {cmd[0]} ({e})")
                continue
            except Exception as e:  # noqa: BLE001
                failures.append(f"Command crashed before running: {' '.join(cmd)}\n{e}")
                continue

            if proc.returncode == 0:
                count = sum(1 for _ in output_dir.rglob("*.txt")) + sum(1 for _ in output_dir.rglob("*.csv"))
                return AnalyzerResult(self.name, True, output_dir, detections_count=count)

            failures.append(
                "Command failed:\n"
                + " ".join(cmd)
                + f"\nreturncode={proc.returncode}\n"
                + (proc.stderr or proc.stdout or "")[-2000:]
            )

        diagnostics = self._diagnostics(py)
        log.error("nighthawk diagnostics:\n%s", diagnostics)

        message = (
            "Nighthawk could not be run from its managed environment. "
            "The most likely cause is that the managed environment is not a valid Nighthawk Python 3.10 environment. "
            "Nighthawk's package declares Python ~=3.10, while this app may be running under a newer Python.\n\n"
            + "\n\n".join(failures)[-3000:]
            + "\n\nDiagnostics:\n"
            + diagnostics[-3000:]
        )

        return AnalyzerResult(self.name, False, output_dir, message=message)


register(NighthawkPlugin())
