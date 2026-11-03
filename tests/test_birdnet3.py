import csv
import json
from types import SimpleNamespace

from nfc_tools.analyzers import birdnet
from nfc_tools.config import Config
from nfc_tools.clip_exporter import _birdnet_clip_specs


def test_v3_year_round_split_outputs_and_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(birdnet, 'IS_DEV', True)
    plugin = birdnet.BirdNETPlugin()
    monkeypatch.setattr(plugin, '_python', lambda: 'python')
    calls = []
    monkeypatch.setattr(birdnet.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0))
    cfg = Config()
    cfg.analyzers.birdnet_year_round = True
    wav = tmp_path / '001_NFC_2026-11-03_03-30-00.wav'
    wav.touch()
    output = tmp_path / 'results'
    assert plugin.run(wav, output, cfg).success
    cmd = calls[0]
    assert '--week' not in cmd
    assert '--lat' in cmd and '--lon' in cmd
    assert cmd[cmd.index('--birdnet') + 1] == '3.0'
    assert '--split_tables' in cmd
    assert json.loads((output / 'nfc_birdnet_policy.json').read_text())['model'] == '3.0'


def test_v3_filter_skips_parameters_and_preserves_clip_times(tmp_path):
    params = tmp_path / 'birdnet.analyze-params.csv'
    params.write_text('Parameter,Value\nmodel,3.0\n')
    table = tmp_path / 'audio.BirdNET.selection.table.txt'
    fields = ['Selection', 'Begin Time (s)', 'End Time (s)', 'Common Name', 'Scientific Name', 'Species Code', 'Confidence']
    with table.open('w') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(fields)
        writer.writerows([[1, 3, 6, 'Pine Siskin', 'Spinus pinus', 'pinsis', 0.25],
                          [2, 6, 9, 'Common Starling', 'Sturnus vulgaris', 'Sturnus vulgaris_Common Starling', 0.8],
                          [3, 9, 12, 'Other', 'Other', 'other', 0.1],
                          [4, 12, 15, 'Pine Siskin', 'Spinus pinus', 'pinsis', 0.2499]])
    cfg = Config()
    cfg.analyzers.birdnet_winter_finch_sensitivity = True
    birdnet._filter_results(tmp_path, cfg.analyzers)
    assert params.read_text() == 'Parameter,Value\nmodel,3.0\n'
    clips = _birdnet_clip_specs(tmp_path, 0.5, cfg.analyzers)
    assert len(clips) == 2
    assert clips[0].start_seconds == 3
    assert 'Common Starling' in clips[1].label
    assert 'Sturnus' not in clips[1].label


def test_development_installer_rejects_wrong_preview(tmp_path, monkeypatch):
    from nfc_tools import installer
    monkeypatch.setattr(installer, 'IS_DEV', True)
    monkeypatch.setattr(installer, '_mamba_for', lambda name: tmp_path / 'mamba')
    monkeypatch.setattr(installer, '_venv_for', lambda name: tmp_path / 'venv')
    monkeypatch.setattr(installer, '_python_imports', lambda *args: True)
    monkeypatch.setattr(installer, '_birdnet3_matches', lambda py: False)
    assert installer._working_birdnet_python() is None
    monkeypatch.setattr(installer, '_birdnet3_matches', lambda py: True)
    assert installer._working_birdnet_python() is not None
