import csv
import wave

from nfc_tools.ebird_export import EBIRD_RECORD_FIELDS, EbirdExportOptions, prepare_record_export


def write_wav(path, seconds=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 8000 * seconds)


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
        "10.0,11.0,Passeriformes,0.96\n",
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

    assert result["observations"] == 4
    assert result["review_rows"] == 5
    assert result["unmapped"] == 0
    assert result["import_path"].parent == night / "eBird checklists"
    assert result["import_path"].name == "ebird_record_import_2026-08-27_02-00.csv"
    assert result["review_path"].name == "ebird_review_2026-08-27_02-00.csv"

    assert result["import_path"].read_bytes().startswith(b"\xef\xbb\xbf")
    with result["import_path"].open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 4
    by_common = {row[0]: row for row in rows}
    assert by_common["Barred Owl"] == [
        "Barred Owl",
        "",
        "Strix varia",
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
        "Awaiting manual review",
    ]
    assert any(
        row[0] == "new world warbler sp."
        and row[4] == "NFC 2 | Parulidae 1 | SBUF 1"
        for row in rows
    )
    assert by_common["American Redstart"][4] == "NFC 1"
    assert by_common["passerine sp."][4] == "NFC 1 | Passeriformes 1"
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


def test_record_export_weather_comments_are_utf8_and_timestamp_free(tmp_path):
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
    (logs / "environmental_conditions.csv").write_text(
        "hour_date,hour_time,surface_temp_f,surface_wind_mph,surface_wind_dir_deg,"
        "wind_950hpa_mph,wind_950hpa_dir_deg,cloud_cover_pct\n"
        "2026-08-27,02-00-30,63.4,4.8,210,11.2,235,18\n",
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
    assert "Wind direction: 210°" in comments
    assert "Date:" not in comments
    assert "Time:" not in comments
    assert b"\xc2\xb0" in result["import_path"].read_bytes()


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
