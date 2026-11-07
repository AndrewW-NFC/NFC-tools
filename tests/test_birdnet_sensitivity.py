"""Regression tests for BirdNET sensitivity arguments and configuration."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Project/external imports:
# nfc_tools.analyzers.birdnet, nfc_tools.birdnet_policy, nfc_tools.clip_exporter,
# nfc_tools.config, pytest.

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nfc_tools.analyzers import birdnet
from nfc_tools.birdnet_policy import keep_detection
from nfc_tools.clip_exporter import _clip_specs
from nfc_tools.config import Config


@pytest.mark.parametrize('finches,owls', [(False, False), (True, False), (False, True), (True, True)])
def test_independent_thresholds(finches, owls):
    cfg = Config().analyzers
    cfg.birdnet_winter_finch_sensitivity = finches
    cfg.birdnet_owl_sensitivity = owls
    for scientific, common, enabled in [
        ('Spinus pinus', 'Pine Siskin', finches),
        ('Acanthis hornemanni', 'Hoary Redpoll', finches),
        ('Strix varia', 'Barred Owl', owls),
        ('Strix aluco', 'Tawny Owl', False),
        ('Turdus migratorius', 'American Robin', False),
    ]:
        for score, passes in [('0.01', False), ('0.04', False), ('0.2499', False), ('0.25', enabled), ('0.499', enabled), ('0.5', True), ('nan', False)]:
            assert keep_detection({'Scientific name': scientific, 'Common name': common, 'Confidence': score}, cfg) == passes
            assert keep_detection({'Common Name': common, 'Confidence': score}, cfg) == passes


def test_override_never_raises_lower_general_threshold():
    cfg = Config().analyzers
    cfg.birdnet_min_conf = 0.001
    cfg.birdnet_owl_sensitivity = True
    assert keep_detection({'Scientific name': 'Strix varia', 'Confidence': '0.005'}, cfg)


@pytest.mark.parametrize('year_round', [False, True])
def test_pipeline_expands_list_and_filters_both_outputs(tmp_path, monkeypatch, year_round):
    cfg = Config()
    cfg.analyzers.birdnet_winter_finch_sensitivity = True
    cfg.analyzers.birdnet_owl_sensitivity = True
    cfg.analyzers.birdnet_year_round = year_round
    wav = tmp_path / '001_NFC_2026-11-03_03-30-00.wav'
    wav.write_bytes(b'audio')
    out = tmp_path / 'results'
    calls = []
    plugin = birdnet.BirdNETPlugin()
    monkeypatch.setattr(plugin, '_python', lambda: 'python')

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if '-c' in cmd:
            assert cmd[-1] == ('-1' if year_round else '41')
            Path(cmd[3]).write_text('Turdus migratorius_American Robin\n')
            Path(cmd[4]).write_text(json.dumps([
                'Turdus migratorius_American Robin', 'Spinus pinus_Pine Siskin',
                'Strix varia_Barred Owl', 'Strix aluco_Tawny Owl',
            ]))
        else:
            assert '--lat' not in cmd and '--lon' not in cmd and '--week' not in cmd
            assert cmd[cmd.index('--min_conf') + 1] == '0.25'
            assert cmd[cmd.index('--birdnet') + 1] == '3.0'
            assert set(Path(cmd[cmd.index('--slist') + 1]).read_text().splitlines()) == {
                'Turdus migratorius_American Robin', 'Spinus pinus_Pine Siskin', 'Strix varia_Barred Owl',
            }
            (out / 'BirdNET_analysis_params.csv').write_text('Parameter,Value\nmin_conf,0.25\n')
            (out / 'test.csv').write_text(
                'Start (s),End (s),Scientific name,Common name,Confidence,File\n'
                '0,3,Spinus pinus,Pine Siskin,0.25,test.wav\n'
                '3,6,Strix varia,Barred Owl,0.3,test.wav\n'
                '6,9,Turdus migratorius,American Robin,0.04,test.wav\n'
                '9,12,Turdus migratorius,American Robin,0.5,test.wav\n'
                '12,15,Spinus pinus,Pine Siskin,0.009,test.wav\n'
            )
            (out / 'test.selection.table.txt').write_text(
                'Selection\tBegin Time (s)\tEnd Time (s)\tCommon Name\tSpecies Code\tConfidence\n'
                '1\t0\t3\tPine Siskin\t pinsis\t0.25\n'
                '2\t3\t6\tBarred Owl\tbrdowl\t0.3\n'
                '3\t6\t9\tAmerican Robin\tamerob\t0.04\n'
                '4\t9\t12\tAmerican Robin\tamerob\t0.5\n'
            )
        return SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setattr(birdnet.subprocess, 'run', fake_run)
    result = plugin.run(wav, out, cfg)
    assert result.success and result.detections_count == 3
    assert len(calls) == 2
    assert (out / "BirdNET_analysis_params.csv").read_text() == "Parameter,Value\nmin_conf,0.25\n"
    with (out / 'test.selection.table.txt').open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert [row['Selection'] for row in rows] == ['1', '2', '3']
    clips = _clip_specs('birdnet', out, cfg)
    assert [clip.score for clip in clips] == [0.25, 0.3, 0.5]
    (out / 'test.selection.table.txt').unlink()
    assert [clip.score for clip in _clip_specs('birdnet', out, cfg)] == [0.25, 0.3, 0.5]


def test_species_generation_failure_does_not_analyze(tmp_path, monkeypatch):
    cfg = Config()
    cfg.analyzers.birdnet_owl_sensitivity = True
    plugin = birdnet.BirdNETPlugin()
    monkeypatch.setattr(plugin, '_python', lambda: 'python')
    calls = []
    monkeypatch.setattr(birdnet.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=1, stderr='unavailable'))
    result = plugin.run(tmp_path / '001_NFC_2026-11-03_03-30-00.wav', tmp_path / 'out', cfg)
    assert not result.success
    assert 'species list failed' in result.message
    assert len(calls) == 1


def test_sensitivity_config_round_trip_and_legacy_defaults():
    cfg = Config(analyzers={'birdnet_winter_finch_sensitivity': True, 'birdnet_owl_sensitivity': True})
    restored = Config.model_validate_json(cfg.model_dump_json())
    assert restored.analyzers.birdnet_winter_finch_sensitivity
    assert restored.analyzers.birdnet_owl_sensitivity
    assert not Config(analyzers={'birdnet_min_conf': 0.5}).analyzers.birdnet_owl_sensitivity
