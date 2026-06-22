from pathlib import Path

from nfc_tools import clip_exporter
from nfc_tools.config import Config


def _fake_ffmpeg(monkeypatch, calls: list[list[str]]) -> None:
    monkeypatch.setattr(clip_exporter, "ensure_ffmpeg", lambda: "ffmpeg")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"clip")

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(clip_exporter.subprocess, "run", fake_run)


def test_exports_nighthawk_audacity_labels_to_segment_start_folder(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    wav = (
        tmp_path
        / "2026-06-17"
        / "audio"
        / "001_NFC_CIVIL_EVENING_2026-06-17_21-50-02.wav"
    )
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"wav")
    out = tmp_path / "results" / "nighthawk" / wav.stem
    out.mkdir(parents=True)
    (out / f"{wav.stem}_audacity.txt").write_text(
        "12.34\t13.34\tswathr (0.943)\n"
        "20.00\t21.00\tzeepai (0.901)\n"
    )

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "clips", Config())

    assert count == 2
    assert (tmp_path / "clips" / "21-50-02" / "swathr (0.943)-Nighthawk.wav").exists()
    assert (tmp_path / "clips" / "21-50-02" / "zeepai (0.901)-Nighthawk.wav").exists()
    assert calls[0][-1].endswith("swathr (0.943)-Nighthawk.wav")
    assert calls[0][calls[0].index("-ss") + 1] == "12.340000"
    assert calls[0][calls[0].index("-t") + 1] == "1.000000"


def test_exports_birdnet_table_rows_at_configured_confidence(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    cfg = Config()
    cfg.analyzers.birdnet_min_conf = 0.75
    wav = tmp_path / "2026-06-17" / "audio" / "002_NFC_2026-06-18_00-00-00.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"wav")
    out = tmp_path / "results" / "birdnet" / wav.stem
    out.mkdir(parents=True)
    (out / f"{wav.stem}.BirdNET.selection.table.txt").write_text(
        "Selection\tView\tChannel\tBegin Time (s)\tEnd Time (s)\t"
        "Low Freq (Hz)\tHigh Freq (Hz)\t"
        "Common Name\tSpecies Code\tConfidence\tBegin Path\tFile Offset (s)\n"
        f"1\tSpectrogram 1\t1\t44\t47\t0\t12000\tSwainson's Thrush\tswathr\t0.8123\t{wav}\t44\n"
        f"2\tSpectrogram 1\t1\t50\t53\t0\t12000\tSora\tsora\t0.7000\t{wav}\t50\n"
    )
    (out / f"{wav.stem}.BirdNET.results.csv").write_text(
        "Start (s),End (s),Scientific name,Common name,Confidence,File\n"
        f"44,47,Catharus ustulatus,Swainson's Thrush,0.8123,{wav}\n"
    )

    count = clip_exporter.export_analyzer_clips(wav, "birdnet", out, tmp_path / "clips", cfg)

    assert count == 1
    assert (tmp_path / "clips" / "00-00-00" / "swathr (0.812)-BirdNET.wav").exists()
    assert not (tmp_path / "clips" / "00-00-00" / "sora (0.7)-BirdNET.wav").exists()


def test_duplicate_clip_names_get_numbered(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    wav = tmp_path / "2026-06-17" / "audio" / "001_NFC_2026-06-17_22-00-00.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"wav")
    out = tmp_path / "results" / "nighthawk" / wav.stem
    out.mkdir(parents=True)
    (out / f"{wav.stem}_audacity.txt").write_text(
        "1\t2\tswathr (0.943)\n"
        "3\t4\tswathr (0.943)\n"
    )

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "clips", Config())

    assert count == 2
    assert (tmp_path / "clips" / "22-00-00" / "swathr (0.943)-Nighthawk.wav").exists()
    assert (tmp_path / "clips" / "22-00-00" / "swathr (0.943)-Nighthawk 2.wav").exists()
