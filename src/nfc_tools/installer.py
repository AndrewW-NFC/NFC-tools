"""Installs ffmpeg, BirdNET-Analyzer, and Nighthawk into managed venvs."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv
from pathlib import Path
from typing import Callable, Optional

from .paths import analyzers_root, cache_dir
from .logging_setup import get

log = get("installer")

ProgressCb = Optional[Callable[[str, "float | None"], None]]


def _emit(cb: ProgressCb, msg: str, frac: "float | None" = None) -> None:
    if cb:
        cb(msg, frac)
    log.info("[install] %s%s", msg, f" ({frac:.0%})" if frac is not None else "")


# -------- ffmpeg --------


def install_ffmpeg(cb: ProgressCb = None) -> str:
    _emit(cb, "Installing ffmpeg via imageio-ffmpeg...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "imageio-ffmpeg"])
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # noqa: BLE001
        log.warning("imageio-ffmpeg install failed: %s", e)
        raise RuntimeError("Could not install ffmpeg automatically.") from e


# -------- analyzer environments --------


def _venv_for(name: str) -> Path:
    return analyzers_root() / name / "venv"


def _mamba_for(name: str) -> Path:
    return analyzers_root() / name / "mamba"


def _venv_python(env_dir: Path) -> Path:
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def _ensure_venv(name: str, cb: ProgressCb) -> Path:
    env_dir = _venv_for(name)
    if _venv_python(env_dir).exists():
        return env_dir

    _emit(cb, f"Creating environment for {name}...")
    env_dir.mkdir(parents=True, exist_ok=True)
    venv.create(env_dir, with_pip=True, clear=True)
    return env_dir


def _pip_install(env_dir: Path, packages: list, cb: ProgressCb) -> None:
    py = _venv_python(env_dir)
    cmd = [str(py), "-m", "pip", "install", "--upgrade", *packages]
    _emit(cb, f"Installing: {', '.join(packages)} (this can take several minutes)...")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout
    for line in proc.stdout:
        log.debug("[pip] %s", line.rstrip())

    if proc.wait() != 0:
        raise RuntimeError(f"pip install failed for {packages}")


def _python_imports(py: Path | str | None, module: str) -> bool:
    if not py:
        return False

    py_path = Path(py)
    if not py_path.exists():
        return False

    try:
        proc = subprocess.run(
            [str(py_path), "-c", f"import {module}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _python_version_tuple(py: Path | str | None) -> tuple[int, int] | None:
    if not py:
        return None

    py_path = Path(py)
    if not py_path.exists():
        return None

    try:
        proc = subprocess.run(
            [
                str(py_path),
                "-c",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return None

        major, minor = proc.stdout.strip().split(".", 1)
        return int(major), int(minor)
    except Exception:  # noqa: BLE001
        return None


def _valid_nighthawk_python(py: Path | str | None) -> bool:
    return _python_imports(py, "nighthawk")


def install_birdnet(cb: ProgressCb = None) -> Path:
    env_dir = _ensure_venv("birdnet", cb)
    _pip_install(env_dir, ["birdnet-analyzer"], cb)
    _emit(cb, "BirdNET installed.", 1.0)
    return _venv_python(env_dir)


def install_nighthawk(cb: ProgressCb = None) -> Path:
    """Install Nighthawk into a valid managed environment.

    Important: Nighthawk currently requires Python 3.10. A previous NFC Tools
    build could create a Python 3.13 venv and then mark that venv as installed
    even though pip could not install Nighthawk. This function treats that as
    broken and falls back to a Python 3.10 micromamba environment.
    """

    # If we already have a valid mamba install, prefer it. This avoids a broken
    # venv shadowing a working Python 3.10 environment.
    mamba_py = _venv_python(_mamba_for("nighthawk"))
    if _valid_nighthawk_python(mamba_py):
        _emit(cb, "Nighthawk already installed in the Python 3.10 environment.", 1.0)
        return mamba_py

    env_dir = _venv_for("nighthawk")
    venv_py = _venv_python(env_dir)

    # Remove the broken Python 3.13 venv if it exists without Nighthawk.
    if venv_py.exists() and not _valid_nighthawk_python(venv_py):
        version = _python_version_tuple(venv_py)
        _emit(
            cb,
            f"Removing incomplete Nighthawk environment at {env_dir}"
            + (f" (Python {version[0]}.{version[1]})" if version else ""),
        )
        shutil.rmtree(env_dir, ignore_errors=True)

    # Try pip in a local venv only if the running Python is compatible. This
    # keeps BirdNET on the app Python but avoids guaranteed Nighthawk failure
    # under Python 3.13.
    running_version = sys.version_info[:2]
    if running_version == (3, 10):
        try:
            env_dir = _ensure_venv("nighthawk", cb)
            _pip_install(env_dir, ["nighthawk"], cb)
            py = _venv_python(env_dir)
            if _valid_nighthawk_python(py):
                _emit(cb, "Nighthawk installed (pip).", 1.0)
                return py
            raise RuntimeError("pip finished, but import nighthawk still failed")
        except Exception as e:  # noqa: BLE001
            log.warning("pip install of nighthawk failed (%s); falling back to micromamba", e)
    else:
        _emit(
            cb,
            f"Skipping pip venv for Nighthawk because app Python is {running_version[0]}.{running_version[1]}; Nighthawk needs Python 3.10.",
        )

    micromamba = _ensure_micromamba(cb)
    env_dir = _mamba_for("nighthawk")

    # Rebuild if present but invalid.
    py = _venv_python(env_dir)
    if env_dir.exists() and not _valid_nighthawk_python(py):
        _emit(cb, f"Removing incomplete Nighthawk micromamba environment at {env_dir}")
        shutil.rmtree(env_dir, ignore_errors=True)

    if not py.exists():
        env_dir.mkdir(parents=True, exist_ok=True)
        _emit(cb, "Creating Nighthawk Python 3.10 environment via micromamba (this may take a few minutes)...")
        subprocess.check_call(
            [
                str(micromamba),
                "create",
                "-y",
                "-p",
                str(env_dir),
                "-c",
                "conda-forge",
                "python=3.10",
                "pip",
            ]
        )

    py = _venv_python(env_dir)
    _emit(cb, "Installing Nighthawk into the Python 3.10 environment...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "nighthawk"])

    if not _valid_nighthawk_python(py):
        raise RuntimeError(
            "Nighthawk installation completed but import nighthawk still failed. "
            f"Managed Python: {py}"
        )

    _emit(cb, "Nighthawk installed (Python 3.10 micromamba environment).", 1.0)
    return py


# -------- micromamba bootstrap --------


def _ensure_micromamba(cb: ProgressCb) -> Path:
    existing = shutil.which("micromamba") or shutil.which("mamba") or shutil.which("conda")
    if existing:
        return Path(existing)

    target = cache_dir() / "micromamba"
    target.mkdir(parents=True, exist_ok=True)

    bin_path = target / ("micromamba.exe" if platform.system() == "Windows" else "micromamba")
    if bin_path.exists():
        return bin_path

    system = platform.system()
    arch = platform.machine().lower()
    base = "https://micro.mamba.pm/api/micromamba"
    url_map = {
        ("Darwin", "arm64"): f"{base}/osx-arm64/latest",
        ("Darwin", "x86_64"): f"{base}/osx-64/latest",
        ("Linux", "x86_64"): f"{base}/linux-64/latest",
        ("Linux", "aarch64"): f"{base}/linux-aarch64/latest",
        ("Windows", "amd64"): f"{base}/win-64/latest",
    }

    key = (system, arch)
    url = url_map.get(key)
    if not url:
        raise RuntimeError(f"No micromamba build for {system}/{arch}")

    _emit(cb, "Downloading micromamba (~10 MB)...")
    archive = target / "mm.tar.bz2"

    with urllib.request.urlopen(url) as r, archive.open("wb") as f:
        shutil.copyfileobj(r, f)

    with tarfile.open(archive, "r:bz2") as tf:
        for m in tf.getmembers():
            name = Path(m.name).name
            if name.startswith("micromamba"):
                tf.extract(m, target)
                src = target / m.name
                shutil.move(str(src), str(bin_path))
                break

    archive.unlink(missing_ok=True)
    bin_path.chmod(0o755)
    return bin_path


def status() -> dict:
    out = {}

    # BirdNET can use the app Python venv.
    birdnet_py = _venv_python(_venv_for("birdnet"))
    out["birdnet"] = {
        "installed": birdnet_py.exists(),
        "python": str(birdnet_py) if birdnet_py.exists() else None,
    }

    # Nighthawk must be importable. Prefer the Python 3.10 mamba environment
    # over a stale/broken venv.
    nighthawk_mamba_py = _venv_python(_mamba_for("nighthawk"))
    nighthawk_venv_py = _venv_python(_venv_for("nighthawk"))

    if _valid_nighthawk_python(nighthawk_mamba_py):
        out["nighthawk"] = {"installed": True, "python": str(nighthawk_mamba_py)}
    elif _valid_nighthawk_python(nighthawk_venv_py):
        out["nighthawk"] = {"installed": True, "python": str(nighthawk_venv_py)}
    else:
        # Preserve the path for diagnostics, but do not call it installed.
        py = nighthawk_mamba_py if nighthawk_mamba_py.exists() else nighthawk_venv_py
        out["nighthawk"] = {
            "installed": False,
            "python": str(py) if py.exists() else None,
        }

    return out
