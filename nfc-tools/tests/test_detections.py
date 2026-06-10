from pathlib import Path
from datetime import datetime
from nfc_tools.detections import _parse_birdnet_csv, _parse_nighthawk_txt


def test_birdnet_parsing(tmp_path: Path):
	csv = tmp_path / "out.csv"
	csv.write_text(
		"Start (s),End (s),Scientific name,Common name,Confidence\n"
		"1.0,4.0,Catharus ustulatus,Swainson's Thrush,0.91\n"
		",,,,\n"
	)
	rows = list(_parse_birdnet_csv(csv, "x.wav", "2026-05-10",
								   datetime(2026, 5, 11, 1, 0, 0)))
	assert len(rows) == 1
	assert rows[0].common_name == "Swainson's Thrush"
	assert rows[0].confidence == 0.91
	assert rows[0].timestamp.startswith("2026-05-11T01:00:01")


def test_nighthawk_parsing(tmp_path: Path):
	f = tmp_path / "labels.txt"
	f.write_text("12.5\t13.0\tSWTH_0.873\n100.0\t100.5\tunknown\n")
	rows = list(_parse_nighthawk_txt(f, "x.wav", "2026-05-10", None))
	assert len(rows) == 2
	assert rows[0].species == "SWTH"
	assert abs(rows[0].confidence - 0.873) < 1e-6
	assert rows[1].species == "unknown"
