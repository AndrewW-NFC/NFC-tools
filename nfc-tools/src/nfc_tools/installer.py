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
		subprocess.check_call([sys.executable, "-m", "pip", "install",
							   "--quiet", "imageio-ffmpeg"])
		import imageio_ffmpeg  # type: ignore
		return imageio_ffmpeg.get_ffmpeg_exe()
	except Exception as e:  # noqa: BLE001
		log.warning("imageio-ffmpeg install failed: %s", e)
		raise RuntimeError("Could not install ffmpeg automatically.") from e


# -------- analyzer environments --------

def _venv_for(name: str) -> Path:
	return analyzers_root() / name / "venv"


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
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
							text=True)
	assert proc.stdout
	for line in proc.stdout:
		log.debug("[pip] %s", line.rstrip())
	if proc.wait() != 0:
		raise RuntimeError(f"pip install failed for {packages}")


def install_birdnet(cb: ProgressCb = None) -> Path:
	env_dir = _ensure_venv("birdnet", cb)
	_pip_install(env_dir, ["birdnet-analyzer"], cb)
	_emit(cb, "BirdNET installed.", 1.0)
	return _venv_python(env_dir)


def install_nighthawk(cb: ProgressCb = None) -> Path:
	try:
		env_dir = _ensure_venv("nighthawk", cb)
		_pip_install(env_dir, ["nighthawk"], cb)
		_emit(cb, "Nighthawk installed (pip).", 1.0)
		return _venv_python(env_dir)
	except Exception as e:  # noqa: BLE001
		log.warning("pip install of nighthawk failed (%s); falling back to micromamba", e)

	micromamba = _ensure_micromamba(cb)
	env_dir = analyzers_root() / "nighthawk" / "mamba"
	env_dir.mkdir(parents=True, exist_ok=True)
	_emit(cb, "Creating Nighthawk environment via micromamba (this may take a few minutes)...")
	subprocess.check_call([
		str(micromamba), "create", "-y", "-p", str(env_dir),
		"-c", "conda-forge", "python=3.10", "pip",
	])
	py = env_dir / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
	subprocess.check_call([str(py), "-m", "pip", "install", "nighthawk"])
	_emit(cb, "Nighthawk installed (micromamba).", 1.0)
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
	for name in ("birdnet", "nighthawk"):
		py = _venv_python(_venv_for(name))
		if py.exists():
			out[name] = {"installed": True, "python": str(py)}
		else:
			mamba_py = (analyzers_root() / name / "mamba" /
						("Scripts/python.exe" if platform.system() == "Windows" else "bin/python"))
			if mamba_py.exists():
				out[name] = {"installed": True, "python": str(mamba_py)}
			else:
				out[name] = {"installed": False, "python": None}
	return out
