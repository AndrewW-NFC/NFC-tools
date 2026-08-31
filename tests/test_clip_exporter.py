import wave
from pathlib import Path

from nfc_tools import clip_exporter
from nfc_tools.config import Config


def _write_wav(path: Path, seconds: float = 120.0, sample_rate: int = 8000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\0\0" * frames)


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
    _write_wav(wav)
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
    assert calls[0][calls[0].index("-ss") + 1] == "8.340000"
    assert calls[0][calls[0].index("-t") + 1] == "9.000000"


def test_exports_birdnet_table_rows_at_configured_confidence(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    cfg = Config()
    cfg.analyzers.birdnet_min_conf = 0.75
    wav = tmp_path / "2026-06-17" / "audio" / "002_NFC_2026-06-18_00-00-00.wav"
    wav.parent.mkdir(parents=True)
    _write_wav(wav)
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
    assert calls[0][calls[0].index("-ss") + 1] == "40.000000"
    assert calls[0][calls[0].index("-t") + 1] == "11.000000"


def test_duplicate_clip_names_get_numbered(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    wav = tmp_path / "2026-06-17" / "audio" / "001_NFC_2026-06-17_22-00-00.wav"
    wav.parent.mkdir(parents=True)
    _write_wav(wav)
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


def test_review_clip_window_clamps_to_source_wav(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    wav = tmp_path / "2026-06-17" / "audio" / "001_NFC_2026-06-17_22-00-00.wav"
    wav.parent.mkdir(parents=True)
    _write_wav(wav, seconds=10.0)
    out = tmp_path / "results" / "nighthawk" / wav.stem
    out.mkdir(parents=True)
    (out / f"{wav.stem}_audacity.txt").write_text(
        "1\t2\tearly (0.900)\n"
        "8\t9\tlate (0.900)\n"
    )

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "clips", Config())

    assert count == 2
    assert calls[0][calls[0].index("-ss") + 1] == "0.000000"
    assert calls[0][calls[0].index("-t") + 1] == "6.000000"
    assert calls[1][calls[1].index("-ss") + 1] == "4.000000"
    assert calls[1][calls[1].index("-t") + 1] == "6.000000"


def test_review_clip_window_does_not_rescue_invalid_label_rows(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _fake_ffmpeg(monkeypatch, calls)

    wav = tmp_path / "2026-06-17" / "audio" / "001_NFC_2026-06-17_22-00-00.wav"
    wav.parent.mkdir(parents=True)
    _write_wav(wav)
    out = tmp_path / "results" / "nighthawk" / wav.stem
    out.mkdir(parents=True)
    (out / f"{wav.stem}_audacity.txt").write_text("8\t7\tinvalid (0.900)\n")

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "clips", Config())

    assert count == 0
    assert calls == []
