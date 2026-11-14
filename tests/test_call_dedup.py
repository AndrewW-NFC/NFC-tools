"""Regression cases for conservative grouping and persisted count review."""
import csv
from dataclasses import replace

import pytest

from nfc_tools.call_dedup import group_calls, read_reviews
from nfc_tools.ebird_export import Detection, Taxon, EbirdExportOptions, prepare_record_export


def detection(start, end, analyzer="Nighthawk", label="amered"):
    return Detection("001_NFC_2026-11-14_02-00-00.wav", analyzer, label, start, end, .9,
                     Taxon("American Redstart", "Setophaga ruticilla"))


@pytest.mark.parametrize("analyzers", [("Nighthawk", "BirdNET"), ("BirdNET", "BirdNET"), ("Nighthawk", "Nighthawk")])
def test_strong_overlap_counts_once_and_preserves_evidence(analyzers):
    values = [detection(1, 2, analyzers[0]), detection(1.1, 2.1, analyzers[1])]
    groups = group_calls(values)
    assert len(groups) == 1
    assert groups[0].count == 1
    assert not groups[0].unresolved
    assert len(groups[0].detections) == 2
    assert groups[0].group_id == group_calls(values[::-1])[0].group_id


@pytest.mark.parametrize("intervals", [
    [(0, 3), (.5, 1), (2, 2.5)],  # one broad window, two distinct calls
    [(0, 1), (1, 2)],  # boundary call or separate calls
    [(0, 3), (2, 5), (4, 7)],  # transitive overlap must not imply one call
    [(0, 1), (.5, 1.5)],
    [(2, 1)], [(float('nan'), 1)], [(0, float('inf'))],
])
def test_ambiguous_intervals_need_review(intervals):
    groups = group_calls([detection(*interval) for interval in intervals])
    assert all(group.unresolved for group in groups)


def test_separate_calls_and_different_broad_labels():
    assert sum(g.count for g in group_calls([detection(0, 1), detection(1.01, 2)])) == 2
    assert group_calls([detection(0, 1, label="SBUF"), detection(0, 1, label="Parulidae")])[0].unresolved
    assert group_calls([detection(0, 1, analyzer="Wingbeats")]) == []


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def set_count(path, count):
    rows = read_csv(path)
    rows[0]["reviewed_call_count"] = count
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_review_round_trip_exclusion_zero_and_changed_evidence(tmp_path, monkeypatch):
    values = [detection(0, 3), detection(2, 5, "BirdNET")]
    monkeypatch.setattr("nfc_tools.ebird_export._night_detections", lambda _: values)
    options = EbirdExportOptions("Test", 42, -71, "MA")
    result = prepare_record_export(tmp_path, options)
    assert result["observations"] == 0
    assert result["call_count_review_required"] == 1
    assert result["import_path"].read_text() == ""
    assert "count pending review" in read_csv(result["review_path"])[0]["species_comments"]
    review_path = result["call_count_review_path"]
    set_count(review_path, "2")
    for _ in range(2):
        result = prepare_record_export(tmp_path, options)
        assert result["observations"] == 1
        assert result["call_count_review_required"] == 0
        assert "NFC 2 | Nighthawk 1 | BirdNET 1" in result["import_path"].read_text()
        assert read_csv(review_path)[0]["status"] == "reviewed"
    set_count(review_path, "0")
    result = prepare_record_export(tmp_path, options)
    assert result["observations"] == 0
    assert result["combined_import_path"].read_text() == ""
    values[0] = replace(values[0], confidence=.95)
    result = prepare_record_export(tmp_path, options)
    assert result["call_count_review_required"] == 1
    assert list(review_path.parent.glob("call_count_review.previous-*.csv"))
    set_count(review_path, "1.5")
    before = result["import_path"].read_bytes()
    with pytest.raises(ValueError, match="nonnegative integer"):
        prepare_record_export(tmp_path, options)
    assert result["import_path"].read_bytes() == before


def test_separate_species_recordings_and_export_disabled(tmp_path, monkeypatch):
    values = [detection(0, 1), detection(0, 1, "BirdNET"),
              replace(detection(0, 1), recording="002_NFC_2026-11-14_03-00-00.wav"),
              replace(detection(0, 1), taxon=Taxon("Other species", "Other"))]
    monkeypatch.setattr("nfc_tools.ebird_export._night_detections", lambda _: values)
    result = prepare_record_export(tmp_path, EbirdExportOptions("Test", 42, -71, "MA", write_import=False))
    assert len(read_csv(result["call_count_review_path"])) == 3
    assert result["import_paths"] == []
    assert result["combined_import_path"] is None
    assert all(row["status"] == "automatic" for row in read_csv(result["call_count_review_path"]))


def test_duplicate_review_ids_rejected(tmp_path):
    path = tmp_path / "review.csv"
    path.write_text("group_id,reviewed_call_count\na,1\na,2\n")
    with pytest.raises(ValueError, match="duplicate"):
        read_reviews(path)


def test_duplicate_invalid_intervals_produce_one_reviewable_group(tmp_path, monkeypatch):
    values = [detection(2, 1), detection(2, 1)]
    monkeypatch.setattr("nfc_tools.ebird_export._night_detections", lambda _: values)
    options = EbirdExportOptions("Test", 42, -71, "MA")
    result = prepare_record_export(tmp_path, options)
    assert len(read_csv(result["call_count_review_path"])) == 1
    set_count(result["call_count_review_path"], "0")
    assert prepare_record_export(tmp_path, options)["call_count_review_required"] == 0
