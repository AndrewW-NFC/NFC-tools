from types import SimpleNamespace

import pytest

from nfc_tools.analyzers import birdnet
from nfc_tools.config import Config


@pytest.mark.parametrize('date,week', [('2026-01-01', 1), ('2026-01-31', 4), ('2026-02-01', 5),
                                     ('2024-02-29', 8), ('2026-08-09', 30), ('2026-12-31', 48)])
def test_birdnet_uses_recording_date_in_48_week_calendar(tmp_path, monkeypatch, date, week):
    calls = []
    plugin = birdnet.BirdNETPlugin()
    monkeypatch.setattr(plugin, '_python', lambda: 'python')
    monkeypatch.setattr(birdnet.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0))
    cfg = Config()
    wav = tmp_path / f'001_NFC_{date}_03-30-00.wav'
    wav.write_bytes(b'audio')
    assert plugin.run(wav, tmp_path / 'results', cfg).success
    cmd = calls[0]
    assert cmd[cmd.index('--week') + 1] == str(week)
    assert cmd[cmd.index('--lat') + 1] == str(cfg.site.latitude)
    assert cmd[cmd.index('--lon') + 1] == str(cfg.site.longitude)
    assert cmd[cmd.index('--min_conf') + 1] == '0.5'


def test_year_round_retains_location_filter(tmp_path, monkeypatch):
    calls = []
    plugin = birdnet.BirdNETPlugin()
    monkeypatch.setattr(plugin, '_python', lambda: 'python')
    monkeypatch.setattr(birdnet.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0))
    cfg = Config()
    cfg.analyzers.birdnet_year_round = True
    wav = tmp_path / '001_NFC_2026-08-09_03-30-00.wav'
    wav.write_bytes(b'audio')
    plugin.run(wav, tmp_path / 'results', cfg)
    cmd = calls[0]
    assert cmd[cmd.index('--week') + 1] == '-1'
    assert cmd[cmd.index('--lat') + 1] == str(cfg.site.latitude)
