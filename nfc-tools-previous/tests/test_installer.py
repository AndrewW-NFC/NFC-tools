from types import SimpleNamespace

import pytest

from nfc_tools import installer


@pytest.fixture
def install_commands(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(installer, "_venv_for", lambda name: tmp_path / name / "venv")
    monkeypatch.setattr(installer, "_mamba_for", lambda name: tmp_path / name / "mamba")
    monkeypatch.setattr(installer, "_ensure_venv", lambda name, cb: installer._venv_for(name))
    monkeypatch.setattr(installer, "_ensure_micromamba", lambda cb: tmp_path / "micromamba")
    monkeypatch.setattr(installer, "_run_command", lambda cmd, cb, **kwargs: commands.append(cmd))
    return commands


@pytest.mark.parametrize("python_version", [(3, 10), (3, 11), (3, 14)])
def test_birdnet_installs_private_python(monkeypatch, install_commands, python_version):
    monkeypatch.setattr(installer, "sys", SimpleNamespace(version_info=python_version))
    monkeypatch.setattr(installer, "_working_birdnet_python", lambda: None)
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: None)
    monkeypatch.setattr(installer, "_python_version_tuple", lambda py: None)
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: True)

    py = installer.install_birdnet()

    assert "python=3.11" in install_commands[0]
    assert install_commands[-1] == [
        str(py), "-m", "pip", "install", "--upgrade", "birdnet-analyzer==2.4.0"
    ]
    assert py == installer._mamba_python(installer._mamba_for("birdnet"))


@pytest.mark.parametrize("kind", ["venv", "mamba"])
def test_birdnet_preserves_working_install(monkeypatch, install_commands, kind):
    expected = (installer._venv_python(installer._venv_for("birdnet")) if kind == "venv"
                else installer._mamba_python(installer._mamba_for("birdnet")))
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: py == expected)
    # A working install is retained even on an otherwise unsupported platform.
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: "Unsupported")
    assert installer.install_birdnet() == expected
    assert not install_commands


def test_birdnet_retries_packages_without_recreating_python(monkeypatch, install_commands):
    monkeypatch.setattr(installer, "_working_birdnet_python", lambda: None)
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: None)
    monkeypatch.setattr(installer, "_python_version_tuple", lambda py: (3, 11))
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: True)
    installer.install_birdnet()
    assert len(install_commands) == 2
    assert all("create" not in cmd for cmd in install_commands)


def test_birdnet_rebuilds_wrong_python_and_preserves_old_venv(monkeypatch, install_commands):
    monkeypatch.setattr(installer, "_working_birdnet_python", lambda: None)
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: None)
    monkeypatch.setattr(installer, "_python_version_tuple", lambda py: (3, 10))
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: True)
    env = installer._mamba_for("birdnet")
    env.mkdir(parents=True)
    stale = env / "stale"
    stale.touch()
    old = installer._venv_for("birdnet")
    old.mkdir()
    installer.install_birdnet()
    assert not stale.exists()
    assert old.exists()
    assert "create" in install_commands[0]


def test_birdnet_failed_import_is_not_success(monkeypatch, install_commands):
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: None)
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: False)
    monkeypatch.setattr(installer, "_python_version_tuple", lambda py: (3, 11))
    with pytest.raises(RuntimeError, match="could not be started"):
        installer.install_birdnet()


@pytest.mark.parametrize("system,arch,supported", [
    ("Darwin", "arm64", True), ("Darwin", "x86_64", False),
    ("Windows", "AMD64", True), ("Windows", "ARM64", False),
    ("Linux", "x86_64", True), ("Linux", "aarch64", True),
    ("Linux", "armv7l", False),
])
def test_birdnet_platform_preflight(monkeypatch, install_commands, system, arch, supported):
    monkeypatch.setattr(installer.platform, "system", lambda: system)
    monkeypatch.setattr(installer.platform, "machine", lambda: arch)
    assert (installer._birdnet_platform_error() is None) == supported
    if not supported:
        monkeypatch.setattr(installer, "_working_birdnet_python", lambda: None)
        def unexpected_download(cb):
            pytest.fail("Unsupported platforms must not download Python")
        monkeypatch.setattr(installer, "_ensure_micromamba", unexpected_download)
        with pytest.raises(RuntimeError):
            installer.install_birdnet()
        assert not install_commands


def test_windows_conda_python_is_at_environment_root(monkeypatch, tmp_path):
    monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
    assert installer._mamba_python(tmp_path) == tmp_path / "python.exe"
    assert installer._venv_python(tmp_path) == tmp_path / "Scripts" / "python.exe"


@pytest.mark.parametrize("working", ["mamba", "venv", None])
def test_status_selects_working_birdnet(monkeypatch, install_commands, working):
    from nfc_tools import ffmpeg_locator
    monkeypatch.setattr(ffmpeg_locator, "find_ffmpeg", lambda: None)
    mamba = installer._mamba_python(installer._mamba_for("birdnet"))
    venv = installer._venv_python(installer._venv_for("birdnet"))
    expected = {"mamba": mamba, "venv": venv, None: None}[working]
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: py == expected)
    monkeypatch.setattr(installer, "_birdnet_platform_error", lambda: "Unsupported")
    status = installer.status()["birdnet"]
    assert status["installed"] == (working is not None)
    assert status["python"] == (str(expected) if expected else None)
    assert status["setup_error"] == (None if expected else "Unsupported")


@pytest.mark.parametrize("python_version", [(3, 10), (3, 13)])
def test_nighthawk_install_commands_are_pinned(monkeypatch, install_commands, python_version):
    monkeypatch.setattr(installer, "sys", SimpleNamespace(version_info=python_version))
    valid = iter([False, True])  # No pre-existing mamba install; final import succeeds.
    monkeypatch.setattr(installer, "_valid_nighthawk_python", lambda py: next(valid))

    py = installer.install_nighthawk()

    assert install_commands[-1] == [
        str(py), "-m", "pip", "install", "--upgrade", "nighthawk==0.3.1"
    ]
    assert len(install_commands) == (1 if python_version == (3, 10) else 3)
