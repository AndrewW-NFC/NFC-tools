import csv
import wave
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from nfc_tools.ebird_export import (
    EBIRD_RECORD_FIELDS,
    EbirdExportOptions,
    _boundary_comments,
    _nighthawk_broad_labels,
    _nighthawk_species_taxonomy,
    prepare_record_export,
)
from nfc_tools.ephemeris import sun_times


def write_wav(path, seconds=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 8000 * seconds)


@pytest.mark.parametrize("boundary", ["civil_dusk", "civil_dawn", "astronomical_dusk", "astronomical_dawn", "midnight"])
@pytest.mark.parametrize("offset", [-1, 0, 1, 10])
def test_boundary_notes_precede_weather_in_session_and_night_exports(tmp_path, boundary, offset):
    options = EbirdExportOptions("Recorder", 42, -71, "MA", timezone="America/New_York",
                                 submission_comments="Observer note")
    sun = sun_times(date(2026, 8, 26), 42, -71, options.timezone)
    endpoint = (datetime(2026, 8, 27, tzinfo=ZoneInfo(options.timezone)) if boundary == "midnight"
                else getattr(sun, boundary))
    start = endpoint.replace(microsecond=0) - timedelta(seconds=30) + timedelta(seconds=offset)
    recording = f"001_NFC_{start:%Y-%m-%d_%H-%M-%S}.wav"
    write_wav(tmp_path / "audio" / recording, seconds=30)
    result_dir = tmp_path / "results" / "nighthawk" / recording[:-4]
    result_dir.mkdir(parents=True)
    (result_dir / f"{recording[:-4]}_detections.csv").write_text(
        "start_sec,end_sec,predicted_category,prob\n1,2,amered,0.91\n", encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "environmental_conditions.csv").write_text(
        f"hour_date,hour_time,surface_temp_f,available\n{start:%Y-%m-%d},{start:%H-%M-%S},63,True\n",
        encoding="utf-8")
    kind = "midnight" if boundary == "midnight" else boundary.split("_")[0] + " twilight"
    note = f"Ending at {kind}"
    for _ in range(2):
        result = prepare_record_export(tmp_path, options)
        for path in (result["import_path"], result["combined_import_path"]):
            with path.open(newline="", encoding="utf-8") as handle:
                comments = next(csv.reader(handle))[18]
            if offset == 10:
                assert "Ending at" not in comments
            else:
                assert f"Observer note | {note} | Temperature" in comments
                assert comments.count(note) == 1


def test_boundary_notes_use_elapsed_duration_and_do_not_invent_missing_audio(tmp_path, monkeypatch):
    options = EbirdExportOptions("Recorder", 42, -71, "MA", timezone="America/New_York")
    recording = "001_NFC_2026-11-01_00-00-00.wav"
    assert _boundary_comments(tmp_path, recording, options) == []
    monkeypatch.setattr("nfc_tools.ebird_export._wav_duration_seconds", lambda path: 25 * 3600)
    assert _boundary_comments(tmp_path, recording, options) == ["Ending at midnight"]


@pytest.mark.parametrize("boundary", ["civil_dusk", "civil_dawn"])
def test_civil_endpoint_notes_preserve_existing_comments_without_duplicates(tmp_path, monkeypatch, boundary):
    from nfc_tools.ebird_export import _submission_comments

    options = EbirdExportOptions("Recorder", 42, -71, "MA", timezone="America/New_York",
                                 submission_comments="Observer note | Starting at civil twilight")
    sun = sun_times(date(2026, 8, 26), 42, -71, options.timezone)
    start = getattr(sun, boundary).replace(microsecond=0)
    end = sun.civil_dusk if boundary == "civil_dawn" else sun_times(
        start.date() + timedelta(days=1), 42, -71, options.timezone).civil_dawn
    recording = f"001_NFC_{start:%Y-%m-%d_%H-%M-%S}.wav"
    monkeypatch.setattr("nfc_tools.ebird_export._wav_duration_seconds", lambda path: (end - start).total_seconds())
    comments = _submission_comments(tmp_path, recording, options)
    assert "Observer note | Starting at civil twilight | Ending at civil twilight | Acoustic" in comments
    assert comments.count("Starting at civil twilight") == 1


def test_prepare_record_export_maps_nighthawk_and_birdnet_rows(tmp_path):
    night = tmp_path / "2026-08-26"
    recording = "009_NFC_2026-08-27_02-00-30.wav"
    stem = recording[:-4]
    write_wav(night / "audio" / recording)
    nighthawk = night / "results" / "nighthawk" / stem
    nighthawk.mkdir(parents=True)
    (nighthawk / f"{stem}_detections.csv").write_text(
        "start_sec,end_sec,predicted_category,prob\n"
        "1.0,2.0,amered,0.91\n"
        "4.0,5.0,SBUF,0.93\n"
        "7.0,8.0,Parulidae,0.94\n"
        "10.0,11.0,Passeriformes,0.96\n"
        "13.0,14.0,Charadriiformes,0.97\n"
        "16.0,17.0,Cuculidae,0.98\n"
        "19.0,20.0,Cuculiformes,0.99\n",
        encoding="utf-8",
    )
    birdnet = night / "results" / "birdnet" / stem
    birdnet.mkdir(parents=True)
    (birdnet / f"{stem}.BirdNET.results.csv").write_text(
        "Start (s),End (s),Scientific name,Common name,Confidence,File\n"
        "20.0,23.0,Strix varia,Barred Owl,0.42,file.wav\n",
        encoding="utf-8",
    )
    (birdnet / f"{stem}.BirdNET.selection.table.txt").write_text(
        "Begin Time (s)\tEnd Time (s)\tCommon Name\tSpecies Code\tConfidence\n"
        "20.0\t23.0\tBarred Owl\tbrdowl\t0.42\n",
        encoding="utf-8",
    )

    result = prepare_record_export(
        night,
        EbirdExportOptions(
            location_name="Merrill test site",
            latitude=42.123456789,
            longitude=-71.987654321,
            state_province="US-MA",
            ebird_hotspot="https://ebird.org/hotspot/L5129545",
        ),
    )

    assert result["observations"] == 6
    assert result["review_rows"] == 8
    assert result["unmapped"] == 0
    assert result["import_path"].parent == night / "eBird checklists"
    assert result["import_path"].name == "ebird_record_import_2026-08-27_02-00.csv"
    assert result["review_path"].name == "ebird_review_2026-08-27_02-00.csv"
    assert result["combined_import_path"].name == "ebird_record_import_night_2026-08-26.csv"
    assert result["combined_review_path"].name == "ebird_review_night_2026-08-26.csv"

    assert not result["import_path"].read_bytes().startswith(b"\xef\xbb\xbf")
    assert not result["combined_import_path"].read_bytes().startswith(b"\xef\xbb\xbf")
    assert result["review_path"].read_bytes().startswith(b"\xef\xbb\xbf")
    assert result["combined_review_path"].read_bytes().startswith(b"\xef\xbb\xbf")
    with result["import_path"].open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 6
    by_common = {row[0]: row for row in rows}
    assert by_common["Barred Owl"] == [
        "Barred Owl",
        "",
        "",
        "X",
        "BirdNET detections 1",
        "Merrill test site",
        "42.1234568",
        "-71.9876543",
        "8/27/2026",
        "02:00",
        "MA",
        "US",
        "P54",
        "1",
        "1",
        "N",
        "",
        "",
        "Awaiting manual review | Acoustic conditions: unavailable | "
        "Acoustic scoring: https://andreww-nfc.github.io/nfc-acoustic-environment-forecast/",
    ]
    assert by_common["American Redstart"][:5] == [
        "American Redstart",
        "",
        "",
        "X",
        "NFC 1",
    ]
    assert by_common["new world warbler sp."][:5] == [
        "new world warbler sp.",
        "",
        "",
        "X",
        "NFC 2 | Parulidae 1 | SBUF 1",
    ]
    assert by_common["passerine sp."][:5] == [
        "passerine sp.",
        "",
        "",
        "X",
        "NFC 1 | Passeriformes 1",
    ]
    assert by_common["shorebird sp."][:5] == [
        "shorebird sp.",
        "",
        "",
        "X",
        "NFC 1 | Charadriiformes 1",
    ]
    assert by_common["cuckoo sp. (Cuculidae sp.)"][:5] == [
        "cuckoo sp. (Cuculidae sp.)",
        "",
        "",
        "X",
        "NFC 2 | Cuculidae 1 | Cuculiformes 1",
    ]
    import_text = result["import_path"].read_text(encoding="utf-8")
    assert '"' not in import_text
    assert "Nighthawk" not in import_text
    assert "| BirdNET" not in import_text
    assert "BirdNET |" not in import_text
    assert "brdowl" not in import_text
    assert "AMRE" not in import_text
    assert "BTBW" not in import_text
    assert "Recorded overnight with NFC Tools" not in import_text

    with result["review_path"].open(newline="", encoding="utf-8") as handle:
        review = list(csv.DictReader(handle))
    assert "mapping_status" not in review[0]
    assert any(row["source_label"] == "Passeriformes" and row["common_name"] == "passerine sp." for row in review)
    assert all(row["ebird_hotspot_id"] == "L5129545" for row in review)
    assert all(row["ebird_hotspot_url"] == "https://ebird.org/hotspot/L5129545" for row in review)


def test_prepare_record_export_uses_common_name_only_like_ebird_record_sample(tmp_path):
    night = tmp_path / "2026-08-26"
    recording = "009_NFC_2026-08-27_02-00-30.wav"
    stem = recording[:-4]
    write_wav(night / "audio" / recording)
    nighthawk = night / "results" / "nighthawk" / stem
    nighthawk.mkdir(parents=True)
    (nighthawk / f"{stem}_detections.csv").write_text(
        "start_sec,end_sec,predicted_category,prob\n"
        "1.0,2.0,mouwar,0.91\n",
        encoding="utf-8",
    )

    result = prepare_record_export(
        night,
        EbirdExportOptions(
            location_name="Merrill test site",
            latitude=42.123456789,
            longitude=-71.987654321,
            state_province="MA",
        ),
    )

    with result["import_path"].open(newline="", encoding="utf-8-sig") as handle:
        row = next(csv.reader(handle))

    assert row[:5] == [
        "Mourning Warbler",
        "",
        "",
        "X",
        "NFC 1",
    ]


def test_packaged_nighthawk_taxonomy_contains_full_reference_mapping(monkeypatch):
    monkeypatch.setattr("nfc_tools.ebird_export._nighthawk_taxonomy_path", lambda: None)

    taxonomy = _nighthawk_species_taxonomy()
    broad = _nighthawk_broad_labels()

    assert len(taxonomy) == 130
    assert taxonomy["mouwar"].common_name == "Mourning Warbler"
    assert taxonomy["yelwar"].common_name == "Northern/Mangrove Yellow Warbler"
    assert taxonomy["whimbr"].common_name == "Hudsonian/Eurasian Whimbrel"
    assert broad["ZEEP"].common_name == "new world warbler sp."
    assert broad["Passerellidae"].common_name == "new world sparrow sp."
    assert broad["Charadriiformes"].common_name == "shorebird sp."
    assert broad["Cuculiformes"].common_name == "cuckoo sp. (Cuculidae sp.)"


@pytest.mark.parametrize(
    ("precipitation", "expected"),
    [("1.2", "1.2 mm"), ("0", "0 mm"), ("", "unavailable"), (None, "unavailable")],
)
def test_record_export_weather_comments_are_utf8_and_timestamp_free(tmp_path, precipitation, expected):
    night = tmp_path / "2026-08-26"
    recording = "009_NFC_2026-08-27_02-00-30.wav"
    stem = recording[:-4]
    write_wav(night / "audio" / recording)
    result_dir = night / "results" / "nighthawk" / stem
    result_dir.mkdir(parents=True)
    (result_dir / f"{stem}_detections.csv").write_text(
        "start_sec,end_sec,predicted_category,prob\n1.0,2.0,amered,0.91\n",
        encoding="utf-8",
    )
    logs = night / "logs"
    logs.mkdir()
    precipitation_header = ",precipitation_mm" if precipitation is not None else ""
    precipitation_value = f",{precipitation}" if precipitation is not None else ""
    (logs / "environmental_conditions.csv").write_text(
        "hour_date,hour_time,surface_temp_f,surface_wind_mph,surface_wind_dir_deg,"
        f"wind_950hpa_mph,wind_950hpa_dir_deg,cloud_cover_pct,available{precipitation_header}\n"
        f"2026-08-27,02-00-30,,,,,,,False{precipitation_value}\n"
        f"2026-08-27,02-00-30,63.4,4.8,210,11.2,235,18,True{precipitation_value}\n",
        encoding="utf-8",
    )

    result = prepare_record_export(
        night,
        EbirdExportOptions(
            location_name="Merrill test site",
            latitude=42.123456789,
            longitude=-71.987654321,
            state_province="MA",
        ),
    )

    with result["import_path"].open(newline="", encoding="utf-8-sig") as handle:
        row = next(csv.reader(handle))
    comments = row[18]
    assert "Awaiting manual review | Temperature (F): 63.4°" in comments
    assert f"Precipitation: {expected}" in comments
    assert "Wind direction: 210°" in comments
    assert "Date:" not in comments
    assert "Time:" not in comments
    assert b"\xc2\xb0" in result["import_path"].read_bytes()
    assert not result["import_path"].read_bytes().startswith(b"\xef\xbb\xbf")


def test_record_export_writes_one_pair_per_recording_session(tmp_path):
    night = tmp_path / "2026-08-26"
    recordings = [
        "001_NFC_2026-08-27_01-00-00.wav",
        "002_NFC_2026-08-27_02-00-30.wav",
    ]
    for recording in recordings:
        stem = recording[:-4]
        write_wav(night / "audio" / recording)
        result_dir = night / "results" / "nighthawk" / stem
        result_dir.mkdir(parents=True)
        (result_dir / f"{stem}_detections.csv").write_text(
            "start_sec,end_sec,predicted_category,prob\n1.0,2.0,amered,0.91\n",
            encoding="utf-8",
        )

    result = prepare_record_export(
        night,
        EbirdExportOptions(
            location_name="Merrill test site",
            latitude=42.123456789,
            longitude=-71.987654321,
            state_province="MA",
        ),
    )

    assert result["import_path"] is None
    assert result["review_path"] is None
    assert [path.name for path in result["import_paths"]] == [
        "ebird_record_import_2026-08-27_01-00.csv",
        "ebird_record_import_2026-08-27_02-00.csv",
    ]
    assert [path.name for path in result["review_paths"]] == [
        "ebird_review_2026-08-27_01-00.csv",
        "ebird_review_2026-08-27_02-00.csv",
    ]
    assert result["combined_import_path"].name == "ebird_record_import_night_2026-08-26.csv"
    assert result["combined_review_path"].name == "ebird_review_night_2026-08-26.csv"

    with result["combined_import_path"].open(newline="", encoding="utf-8-sig") as handle:
        combined_rows = list(csv.reader(handle))
    assert len(combined_rows) == 2
    assert [row[8:15] for row in combined_rows] == [
        ["8/27/2026", "01:00", "MA", "US", "P54", "1", "1"],
        ["8/27/2026", "02:00", "MA", "US", "P54", "1", "1"],
    ]

    with result["combined_review_path"].open(newline="", encoding="utf-8-sig") as handle:
        review_rows = list(csv.DictReader(handle))
    assert [row["recording"] for row in review_rows] == recordings


def test_record_export_field_order_matches_official_template():
    assert EBIRD_RECORD_FIELDS == [
        "Common Name",
        "Genus",
        "Species",
        "Number",
        "Species Comments",
        "Location Name",
        "Latitude",
        "Longitude",
        "Date",
        "Start Time",
        "State/Province",
        "Country Code",
        "Protocol",
        "Number of Observers",
        "Duration",
        "All observations reported?",
        "Effort Distance Miles",
        "Effort area acres",
        "Submission Comments",
    ]
