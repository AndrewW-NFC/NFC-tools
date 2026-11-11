"""Regression tests for review clip selection, audio boundaries, and embedded provenance."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Project/external imports: nfc_tools.clip_exporter,
# nfc_tools.clip_metadata, nfc_tools.config, nfc_tools.ffmpeg_locator, pytest. Audio
# decoding also requires ffmpeg.

import struct
import wave
from pathlib import Path

import pytest

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
        _write_wav(Path(cmd[-1]), seconds=1)

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

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "audio" / "clips", Config())

    assert count == 2
    assert (tmp_path / "audio" / "clips" / "21-50-02" / "swathr (0.943)-Nighthawk.wav").exists()
    assert (tmp_path / "audio" / "clips" / "21-50-02" / "zeepai (0.901)-Nighthawk.wav").exists()
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

    count = clip_exporter.export_analyzer_clips(wav, "birdnet", out, tmp_path / "audio" / "clips", cfg)

    assert count == 1
    assert (tmp_path / "audio" / "clips" / "00-00-00" / "swathr (0.812)-BirdNET.wav").exists()
    assert not (tmp_path / "audio" / "clips" / "00-00-00" / "sora (0.7)-BirdNET.wav").exists()
    assert calls[0][calls[0].index("-ss") + 1] == "40.000000"
    assert calls[0][calls[0].index("-t") + 1] == "11.000000"


@pytest.mark.parametrize(("code", "common", "expected"), [
    ("t-11044823", "Wood Frog", "Wood Frog"),
    ("t-11844438", "Fall Field Cricket", "Fall Field Cricket"),
    ("dogdog", "Dog", "Dog"),
    ("humvoc", "Human vocal", "Human vocal"),
    ("engine", "Engine", "Engine"),
    ("t-11044823", "", "t-11044823"),
    ("dogdog", "", "dogdog"),
    ("swathr", "Swainson's Thrush", "swathr"),
    ("nocall", "Noise", None),
])
def test_birdnet_non_avian_clip_filenames(tmp_path, monkeypatch, code, common, expected):
    _fake_ffmpeg(monkeypatch, [])
    wav = tmp_path / "001_NFC_2026-06-17_22-00-00.wav"
    _write_wav(wav, seconds=10)
    out = tmp_path / "results"
    out.mkdir()
    table = out / "sample.BirdNET.selection.table.txt"
    table.write_text(
        "Begin Time (s)\tEnd Time (s)\tCommon Name\tSpecies Code\tConfidence\n"
        f"1\t2\t{common}\t{code}\t0.812\n"
    )
    clips = tmp_path / "clips"
    count = clip_exporter.export_analyzer_clips(wav, "birdnet", out, clips, Config())
    if expected is None:
        assert count == 0
        assert not list(clips.rglob("*.wav"))
    else:
        assert count == 1
        assert (clips / "22-00-00" / f"{expected} (0.812)-BirdNET.wav").exists()
        specs = clip_exporter._birdnet_specs_from_file(table, 0.5)
        assert specs[0].identification == code


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

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "audio" / "clips", Config())

    assert count == 2
    assert (tmp_path / "audio" / "clips" / "22-00-00" / "swathr (0.943)-Nighthawk.wav").exists()
    assert (tmp_path / "audio" / "clips" / "22-00-00" / "swathr (0.943)-Nighthawk 2.wav").exists()


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

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "audio" / "clips", Config())

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

    count = clip_exporter.export_analyzer_clips(wav, "nighthawk", out, tmp_path / "audio" / "clips", Config())

    assert count == 0
    assert calls == []


def test_repeated_clip_export_does_not_duplicate_outputs(tmp_path, monkeypatch):
    calls = []
    _fake_ffmpeg(monkeypatch, calls)
    wav = tmp_path / '001_NFC_2026-09-17_22-00-00.wav'
    _write_wav(wav)
    out = tmp_path / 'results'
    out.mkdir()
    (out / 'audacity.txt').write_text('10\t11\tswathr\n20\t21\tswathr\n')
    for _ in range(2):
        assert clip_exporter.export_analyzer_clips(wav, 'nighthawk', out, tmp_path / 'audio' / 'clips', Config()) == 2
    assert len(list((tmp_path / 'audio' / 'clips').rglob('*.wav'))) == 2


def test_segment_folders_distinguish_fall_back_and_utc_date_rollover():
    from nfc_tools.clip_exporter import _segment_folder_name

    cases = {
        "001_NFC_2026-11-01_01-00-00_UTC-0400.wav": "01-00-00_UTC-05-00-00",
        "002_NFC_2026-11-01_01-00-00_UTC-0500.wav": "01-00-00_UTC-06-00-00",
        "003_NFC_2026-11-01_02-00-00_UTC-0500.wav": "02-00-00_UTC-07-00-00",
        "004_NFC_2026-11-01_23-00-00_UTC-0500.wav": "23-00-00_UTC-04-00-00",
        "001_NFC_2026-11-01_01-00-00.wav": "01-00-00",
        "unrecognized.wav": "unrecognized",
    }
    for name, expected in cases.items():
        assert _segment_folder_name(Path(name)) == expected


def test_embedded_metadata_preserves_audio_and_excludes_reviews(tmp_path):
    import json
    import struct

    from nfc_tools.clip_metadata import REPOSITORY, build_metadata, embed_metadata

    path = tmp_path / '001_NFC_2026-11-01_01-59-59_UTC-0400.wav'
    _write_wav(path, seconds=1)
    with wave.open(str(path)) as audio:
        before = audio.readframes(audio.getnframes())
    cfg = Config()
    cfg.site.name = 'Café marsh'
    spec = clip_exporter.ClipSpec(2, 3, 'swathr (0.943)', 'Nighthawk', 'swathr', .943)
    metadata = build_metadata(path, spec, 0, 7, cfg)
    embed_metadata(path, metadata)
    raw = path.read_bytes()
    assert struct.unpack('<I', raw[4:8])[0] == len(raw) - 8
    chunks = {}
    offset = 12
    while offset < len(raw):
        tag, size = struct.unpack('<4sI', raw[offset:offset + 8])
        chunks[tag] = raw[offset + 8:offset + 8 + size]
        offset += 8 + size + size % 2
    assert offset == len(raw)
    decoded = json.loads(chunks[b'nfct'])
    assert decoded == metadata
    assert "processing" not in decoded
    assert b"audio copied" not in chunks[b"LIST"]
    assert decoded['timing']['call_timestamp'] == '2026-11-01T02:00:01-04:00'
    assert decoded['timing']['call_start_in_clip_seconds'] == 2
    assert decoded['detection']['score'] == .943
    assert decoded['software']['repository'] == REPOSITORY
    assert 'Café marsh'.encode() in chunks[b'LIST']
    assert 'review' not in json.dumps(decoded).lower()
    with wave.open(str(path)) as audio:
        assert audio.readframes(audio.getnframes()) == before
    assert clip_exporter._wav_duration_seconds(path) == 1


def test_metadata_does_not_invent_timestamp_or_timezone(tmp_path):
    from nfc_tools.clip_metadata import build_metadata
    spec = clip_exporter.ClipSpec(1, 2, 'call', 'Nighthawk')
    for filename, expected in [
        ('unknown.wav', None),
        ('001_NFC_2026-06-17_22-00-00.wav', '2026-06-17T22:00:01'),
    ]:
        metadata = build_metadata(tmp_path / filename, spec, 0, 6, Config())
        assert metadata['timing']['call_timestamp'] == expected
        assert metadata['timing']['timezone_status'] == 'unknown'


def test_real_ffmpeg_export_contains_readable_and_structured_metadata(tmp_path):
    from nfc_tools.clip_metadata import build_metadata, embed_metadata
    from nfc_tools.ffmpeg_locator import ensure_ffmpeg

    source = tmp_path / 'source.wav'
    target = tmp_path / 'clip.wav'
    _write_wav(source, seconds=3)
    clip_exporter._export_clip(ensure_ffmpeg(), source, target, 1, 2)
    embed_metadata(target, build_metadata(
        source, clip_exporter.ClipSpec(1, 2, 'call', 'Nighthawk'), 1, 2, Config()
    ))
    assert b'Exported with NFC Tools' in target.read_bytes()
    assert b'nfct' in target.read_bytes()
    with wave.open(str(target)) as audio:
        assert audio.getframerate() == 8000
        assert audio.getsampwidth() == 2
        assert audio.getnchannels() == 1
        assert audio.getnframes() > 0


def test_nonfinite_detection_offsets_are_rejected():
    assert clip_exporter._float('nan') is None
    assert clip_exporter._float('inf') is None


@pytest.mark.parametrize('failure', ['empty', 'truncated'])
def test_invalid_export_preserves_existing_clip(tmp_path, monkeypatch, failure):
    _fake_ffmpeg(monkeypatch, [])
    source = tmp_path / 'source.wav'
    _write_wav(source)
    results = tmp_path / 'results'
    results.mkdir()
    (results / 'audacity.txt').write_text('10\t11\tcall\n')
    clips = tmp_path / 'clips'
    destination = clips / 'source'
    destination.mkdir(parents=True)
    existing = destination / 'call-Nighthawk.wav'
    _write_wav(existing, seconds=9)
    original = existing.read_bytes()

    def invalid_export(ffmpeg, wav_path, out_path, start, end):
        _write_wav(out_path, seconds=0 if failure == 'empty' else 9)
        if failure == 'truncated':
            out_path.write_bytes(out_path.read_bytes()[:44])

    monkeypatch.setattr(clip_exporter, '_export_clip', invalid_export)
    with pytest.raises(ValueError, match='Invalid review clip from source.wav at 6.000000-15.000000s'):
        clip_exporter.export_analyzer_clips(source, 'nighthawk', results, clips, Config())
    assert existing.read_bytes() == original
    assert list(destination.iterdir()) == [existing]


def test_real_ffmpeg_can_succeed_with_empty_clip(tmp_path):
    from nfc_tools.ffmpeg_locator import ensure_ffmpeg

    source = tmp_path / 'source.wav'
    target = tmp_path / 'empty.wav'
    _write_wav(source, seconds=1)
    # A zero process exit status is not sufficient evidence of usable audio.
    clip_exporter._export_clip(ensure_ffmpeg(), source, target, 10, 19)
    with pytest.raises(ValueError, match='missing or empty WAV data chunk'):
        clip_exporter._wav_duration_seconds(target)


def test_clip_duration_is_an_output_option(tmp_path, monkeypatch):
    calls = []
    _fake_ffmpeg(monkeypatch, calls)
    clip_exporter._export_clip('ffmpeg', tmp_path / 'source.wav', tmp_path / 'clip.wav', 436, 445.8)
    command = calls[0]
    assert command.index('-ss') < command.index('-i') < command.index('-t')
    assert command[command.index('-t') + 1] == '9.800000'


@pytest.mark.parametrize('sample_width', [2, 4])
def test_real_ffmpeg_exports_clip_far_into_recording(tmp_path, sample_width):
    from nfc_tools.ffmpeg_locator import ensure_ffmpeg

    source = tmp_path / 'source.wav'
    target = tmp_path / 'clip.wav'
    sample_rate = 48000
    sample = b'\x01' + b'\0' * (sample_width - 1)
    with wave.open(str(source), 'wb') as audio:
        audio.setparams((1, sample_width, sample_rate, 0, 'NONE', 'not compressed'))
        for _ in range(450):
            audio.writeframesraw(sample * sample_rate)
    # The reported clip should cover 436-445.8 seconds. FFmpeg 4.2.2
    # produces zero frames when -t is placed before -i with this seek.
    clip_exporter._export_clip(ensure_ffmpeg(), source, target, 436, 445.8)
    assert clip_exporter._wav_duration_seconds(target) == pytest.approx(9.8, abs=0.1)
    # Python's wave reader only supports WAVE_FORMAT_EXTENSIBLE from 3.12.
    # FFmpeg legitimately uses that header for 32-bit PCM. Inspect the RIFF
    # chunks directly so every supported Python verifies the exact same audio.
    raw = target.read_bytes()
    assert raw[:4] == b'RIFF' and raw[8:12] == b'WAVE'
    chunks = {}
    offset = 12
    while offset + 8 <= len(raw):
        chunk_id, size = struct.unpack_from('<4sI', raw, offset)
        offset += 8
        assert offset + size <= len(raw)
        chunks[chunk_id] = raw[offset:offset + size]
        offset += size + (size % 2)
    fmt = chunks[b'fmt ']
    format_tag, channels, rate, byte_rate, block_align, bits = struct.unpack_from('<HHIIHH', fmt)
    assert format_tag in (1, 0xfffe)
    if format_tag == 0xfffe:
        assert struct.unpack_from('<H', fmt, 16)[0] >= 22
        assert fmt[24:40] == bytes.fromhex('0100000000001000800000aa00389b71')  # PCM GUID
    assert (channels, rate, bits) == (1, sample_rate, sample_width * 8)
    assert block_align == sample_width
    assert byte_rate == sample_rate * sample_width
    payload = chunks[b'data']
    assert len(payload) % block_align == 0
    frames = len(payload) // block_align
    assert frames / sample_rate == pytest.approx(9.8, abs=0.1)
    assert payload == sample * frames
