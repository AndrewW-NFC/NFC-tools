from nfc_tools.config import Config
from nfc_tools.detections import Detection
from nfc_tools.exporters import to_rich_csv, to_ebird_csv


def _det(**kw):
	base = dict(session_date="2026-05-10", filename="x.wav", analyzer="birdnet",
				species="Catharus ustulatus", common_name="Swainson's Thrush",
				start_seconds=10.0, end_seconds=13.0, confidence=0.9,
				timestamp="2026-05-11T01:00:10")
	base.update(kw)
	return Detection(**base)


def test_rich_csv_has_header_and_rows():
	body = to_rich_csv([_det(), _det(confidence=0.4)])
	lines = body.strip().splitlines()
	assert lines[0].startswith("session_date,timestamp")
	assert len(lines) == 3


def test_ebird_csv_filters_low_conf_and_groups():
	rows = [_det(),
			_det(confidence=0.95, start_seconds=20.0),
			_det(common_name="White-throated Sparrow",
				 species="Zonotrichia albicollis")]
	body = to_ebird_csv(rows, Config(), min_confidence=0.7)
	assert "Common Name" in body.splitlines()[0]
	assert "Swainson's Thrush" in body
	assert "White-throated Sparrow" in body
