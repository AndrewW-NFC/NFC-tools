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


def test_birdnet_install_command_is_pinned(monkeypatch, install_commands):
    monkeypatch.setattr(installer, "_python_imports", lambda py, module: True)

    py = installer.install_birdnet()

    assert install_commands == [
        [str(py), "-m", "pip", "install", "--upgrade", "birdnet-analyzer==2.4.0"]
    ]


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
