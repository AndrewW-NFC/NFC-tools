from types import SimpleNamespace

import pytest

from nfc_tools import folder_picker


@pytest.mark.parametrize('system,stdout', [
    ('Darwin', '/recordings/a b.wav\0/recordings/c.wav\0\n'),
    ('Windows', '["/recordings/a b.wav", "/recordings/c.wav"]'),
    ('Linux', '/recordings/a b.wav\n/recordings/c.wav\n'),
])
def test_multiple_file_picker_results(monkeypatch, tmp_path, system, stdout):
    monkeypatch.setattr(folder_picker.platform, 'system', lambda: system)
    monkeypatch.setattr(folder_picker.shutil, 'which', lambda name: name)
    monkeypatch.setattr(folder_picker.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=stdout, stderr=''))
    assert folder_picker.choose_files(str(tmp_path)) == ['/recordings/a b.wav', '/recordings/c.wav']


@pytest.mark.parametrize('system,code,error', [
    ('Darwin', 1, 'User canceled'), ('Windows', 2, ''), ('Linux', 1, ''),
])
def test_file_picker_cancel(monkeypatch, tmp_path, system, code, error):
    monkeypatch.setattr(folder_picker.platform, 'system', lambda: system)
    monkeypatch.setattr(folder_picker.shutil, 'which', lambda name: name)
    monkeypatch.setattr(folder_picker.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        returncode=code, stdout='', stderr=error))
    assert folder_picker.choose_files(str(tmp_path)) is None


def test_folder_picker_starts_in_parent_of_selected_file(tmp_path):
    source = tmp_path / 'recording.wav'
    source.write_bytes(b'')
    assert folder_picker._initial_directory(str(source)) == tmp_path
