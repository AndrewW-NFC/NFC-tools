"""Prepare eBird spreadsheet-import CSVs from NFC Tools analysis results."""

from __future__ import annotations

import csv
import glob
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import filenames
from .clip_exporter import _wav_duration_seconds
from .config import normalize_ebird_state_province
from .paths import analyzers_root
from .weather import environment_conditions_text_line

EBIRD_RECORD_FIELDS = [
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

REVIEW_FIELDS = [
    "recording",
    "analyzer",
    "source_label",
    "common_name",
    "scientific_name",
    "count",
    "first_detection_seconds",
    "max_confidence",
    "species_comments",
    "ebird_hotspot_id",
    "ebird_hotspot_url",
]

DEFAULT_PROTOCOL = "P54"
DEFAULT_NUMBER = "X"
DEFAULT_CHECKLIST_COMMENT = "Awaiting manual review"


@dataclass(frozen=True)
class Taxon:
    common_name: str
    scientific_name: str = ""
    status: str = "mapped"


@dataclass(frozen=True)
class EbirdExportOptions:
    location_name: str
    latitude: float
    longitude: float
    state_province: str
    country_code: str = "US"
    protocol: str = DEFAULT_PROTOCOL
    number_of_observers: int = 1
    number: str = DEFAULT_NUMBER
    effort_distance_miles: str = ""
    effort_area_acres: str = ""
    submission_comments: str = ""
    ebird_hotspot: str = ""


@dataclass(frozen=True)
class Detection:
    recording: str
    analyzer: str
    source_label: str
    start_seconds: float
    end_seconds: float
    confidence: float | None
    taxon: Taxon

    @property
    def contributes_nfc_count(self) -> bool:
        return self.analyzer == "Nighthawk"


def prepare_record_export(night_path: Path, options: EbirdExportOptions) -> dict:
    """Write one eBird import/review CSV pair per recording session."""
    night_path = Path(night_path)
    state_province = normalize_ebird_state_province(options.state_province)
    country_code = str(options.country_code or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,3}", state_province):
        raise ValueError("eBird state/province must be a 1-3 character region code, such as MA.")
    if not re.fullmatch(r"[A-Z]{2}", country_code):
        raise ValueError("eBird country code must be exactly two letters, such as US.")
    detections = list(_night_detections(night_path))
    output_dir = night_path / "eBird checklists"
    output_dir.mkdir(parents=True, exist_ok=True)
    import_paths = []
    review_paths = []
    observation_count = 0
    review_row_count = 0
    unmapped_count = 0
    recordings = sorted(
        {detection.recording for detection in detections},
        key=lambda recording: (_parsed_recording(night_path, recording).recorded_at, recording),
    )
    for recording in recordings:
        session_detections = [detection for detection in detections if detection.recording == recording]
        review_aggregates = _aggregate_detections_for_review(session_detections)
        import_aggregates = _aggregate_detections_for_import(session_detections)
        rows = []
        review_rows = []
        for key in sorted(review_aggregates, key=lambda item: (item[1], item[2], item[3])):
            _, analyzer, source_label, common_name, scientific_name, _status = key
            values = review_aggregates[key]
            review_rows.append({
                "recording": recording,
                "analyzer": analyzer,
                "source_label": source_label,
                "common_name": common_name,
                "scientific_name": scientific_name,
                "count": len(values),
                "first_detection_seconds": _format_seconds(min(d.start_seconds for d in values)),
                "max_confidence": _format_probability(
                    max((d.confidence for d in values if d.confidence is not None), default=None)
                ),
                "species_comments": _species_comment(values),
                "ebird_hotspot_id": _ebird_hotspot_id(options.ebird_hotspot),
                "ebird_hotspot_url": _ebird_hotspot_url(options.ebird_hotspot),
            })
        parsed = _parsed_recording(night_path, recording)
        duration = _recording_duration_minutes(night_path, recording)
        for key in sorted(import_aggregates, key=lambda item: (item[1], item[2])):
            _, common_name, scientific_name = key
            values = import_aggregates[key]
            genus, species = _scientific_name_fields(scientific_name)
            rows.append({
                "Common Name": common_name,
                "Genus": genus,
                "Species": species,
                "Number": options.number,
                "Species Comments": _aggregate_species_comment(values),
                "Location Name": options.location_name,
                "Latitude": _format_coordinate(options.latitude),
                "Longitude": _format_coordinate(options.longitude),
                "Date": _ebird_date(parsed.recorded_at),
                "Start Time": parsed.recorded_at.strftime("%H:%M"),
                "State/Province": state_province,
                "Country Code": country_code,
                "Protocol": options.protocol,
                "Number of Observers": str(options.number_of_observers),
                "Duration": _format_duration_minutes(duration),
                "All observations reported?": "N",
                "Effort Distance Miles": options.effort_distance_miles,
                "Effort area acres": options.effort_area_acres,
                "Submission Comments": _submission_comments(night_path, recording, options),
            })
        stamp = _recording_session_stamp(night_path, recording)
        import_path = output_dir / f"ebird_record_import_{stamp}.csv"
        review_path = output_dir / f"ebird_review_{stamp}.csv"
        _write_csv(import_path, rows, EBIRD_RECORD_FIELDS, include_header=False)
        _write_csv(review_path, review_rows, REVIEW_FIELDS, include_header=True)
        import_paths.append(import_path)
        review_paths.append(review_path)
        observation_count += len(rows)
        review_row_count += len(review_rows)
        unmapped_count += sum(1 for row in review_rows if not row["common_name"])

    return {
        # Keep singular keys for callers handling a single recording session.
        "import_path": import_paths[0] if len(import_paths) == 1 else None,
        "review_path": review_paths[0] if len(review_paths) == 1 else None,
        "import_paths": import_paths,
        "review_paths": review_paths,
        "observations": observation_count,
        "review_rows": review_row_count,
        "unmapped": unmapped_count,
    }


def _night_detections(night_path: Path) -> list[Detection]:
    detections = []
    detections.extend(_birdnet_detections(night_path))
    detections.extend(_nighthawk_detections(night_path))
    return detections


def _birdnet_detections(night_path: Path) -> list[Detection]:
    detections = []
    species_codes = _birdnet_species_codes(night_path)
    for path in sorted((night_path / "results" / "birdnet").rglob("*.BirdNET.results.csv")):
        recording = _recording_name_from_result_dir(path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                common = (row.get("Common name") or row.get("Common Name") or "").strip()
                scientific = (row.get("Scientific name") or row.get("Scientific Name") or "").strip()
                if not common:
                    continue
                code = species_codes.get((recording, common)) or species_codes.get(("", common))
                detections.append(Detection(
                    recording=recording,
                    analyzer="BirdNET",
                    source_label=code or _safe_label(common),
                    start_seconds=_float(row.get("Start (s)")),
                    end_seconds=_float(row.get("End (s)")),
                    confidence=_optional_float(row.get("Confidence")),
                    taxon=Taxon(common, scientific),
                ))
    return detections


def _birdnet_species_codes(night_path: Path) -> dict[tuple[str, str], str]:
    codes = {}
    for path in sorted((night_path / "results" / "birdnet").rglob("*.selection.table.txt")):
        recording = _recording_name_from_result_dir(path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                common = (row.get("Common Name") or row.get("Common name") or "").strip()
                code = (row.get("Species Code") or "").strip()
                if common and code:
                    codes[(recording, common)] = code
                    codes[("", common)] = code
    return codes


def _nighthawk_detections(night_path: Path) -> list[Detection]:
    taxonomy = _nighthawk_species_taxonomy()
    detections = []
    for path in sorted((night_path / "results" / "nighthawk").rglob("*_detections.csv")):
        recording = _recording_name_from_result_dir(path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                label = (row.get("predicted_category") or "").strip()
                if not label:
                    continue
                detections.append(Detection(
                    recording=recording,
                    analyzer="Nighthawk",
                    source_label=label,
                    start_seconds=_float(row.get("start_sec")),
                    end_seconds=_float(row.get("end_sec")),
                    confidence=_optional_float(row.get("prob")),
                    taxon=_map_nighthawk_label(label, taxonomy),
                ))
    return detections


def _aggregate_detections_for_review(
    detections: list[Detection],
) -> dict[tuple[str, str, str, str, str, str], list[Detection]]:
    aggregates: dict[tuple[str, str, str, str, str, str], list[Detection]] = {}
    for detection in detections:
        key = (
            detection.recording,
            detection.analyzer,
            detection.source_label,
            detection.taxon.common_name,
            detection.taxon.scientific_name,
            detection.taxon.status,
        )
        aggregates.setdefault(key, []).append(detection)
    return aggregates


def _aggregate_detections_for_import(detections: list[Detection]) -> dict[tuple[str, str, str], list[Detection]]:
    aggregates: dict[tuple[str, str, str], list[Detection]] = {}
    for detection in detections:
        if detection.taxon.status != "mapped":
            continue
        key = (detection.recording, detection.taxon.common_name, detection.taxon.scientific_name)
        aggregates.setdefault(key, []).append(detection)
    return aggregates


def _map_nighthawk_label(label: str, taxonomy: dict[str, Taxon]) -> Taxon:
    lower = label.lower()
    if lower in taxonomy:
        return taxonomy[lower]
    if label in NIGHTHAWK_BROAD_LABELS:
        return NIGHTHAWK_BROAD_LABELS[label]
    return Taxon("", "", "unmapped")


NIGHTHAWK_BROAD_LABELS = {
    "Parulidae": Taxon("new world warbler sp.", "Parulidae sp."),
    "ZEEP": Taxon("new world warbler sp.", "Parulidae sp."),
    "SBUF": Taxon("new world warbler sp.", "Parulidae sp."),
    "DEWA": Taxon("new world warbler sp.", "Parulidae sp."),
    "DBUP": Taxon("new world warbler sp.", "Parulidae sp."),
    "BZWA": Taxon("new world warbler sp.", "Parulidae sp."),
    "MWAR": Taxon("new world warbler sp.", "Parulidae sp."),
    "Passerellidae": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "CUPS": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "SWLI": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "SFHS": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "HSSP": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "DESP": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "CCBRS": Taxon("new world sparrow sp.", "Passerellidae sp."),
    "Turdidae": Taxon("thrush sp.", "Turdidae sp."),
    "THSH": Taxon("thrush sp.", "Turdidae sp."),
    "GCBI": Taxon("thrush sp.", "Turdidae sp."),
    "WITH": Taxon("thrush sp.", "Turdidae sp."),
    "BUNT": Taxon("passerine sp.", "Passeriformes sp."),
    "GROS": Taxon("passerine sp.", "Passeriformes sp."),
    "TANA": Taxon("passerine sp.", "Passeriformes sp."),
    "Passeriformes": Taxon("passerine sp.", "Passeriformes sp."),
    "Ardeidae": Taxon("heron sp.", "Ardeidae sp."),
    "Charadriidae": Taxon("plover sp.", "Charadriidae sp."),
    "Scolopacidae": Taxon("Scolopacidae sp.", "Scolopacidae sp."),
    "Icteridae": Taxon("blackbird sp.", "Icteridae sp."),
    "Cuculidae": Taxon("cuckoo sp. (Cuculidae sp.)", "Cuculidae sp."),
    "Sittidae": Taxon("nuthatch sp.", "Sitta sp."),
    "Laridae": Taxon("gull/tern sp.", "Laridae sp."),
    "Corvidae": Taxon("corvid sp.", "Corvidae sp."),
    "Recurvirostridae": Taxon("stilt/avocet sp.", "Recurvirostridae sp."),
    "Alaudidae": Taxon("lark sp.", "Alaudidae sp."),
    "Haematopodidae": Taxon("oystercatcher sp.", "Haematopus sp."),
}

FALLBACK_NIGHTHAWK_SPECIES = {
    "amered": Taxon("American Redstart", "Setophaga ruticilla"),
    "amtspa": Taxon("American Tree Sparrow", "Spizelloides arborea"),
    "bawwar": Taxon("Black-and-white Warbler", "Mniotilta varia"),
    "btbwar": Taxon("Black-throated Blue Warbler", "Setophaga caerulescens"),
    "camwar": Taxon("Cape May Warbler", "Setophaga tigrina"),
    "chispa": Taxon("Chipping Sparrow", "Spizella passerina"),
    "chswar": Taxon("Chestnut-sided Warbler", "Setophaga pensylvanica"),
    "comyel": Taxon("Common Yellowthroat", "Geothlypis trichas"),
    "daejun": Taxon("Dark-eyed Junco", "Junco hyemalis"),
    "graspa": Taxon("Grasshopper Sparrow", "Ammodramus savannarum"),
    "gycthr": Taxon("Gray-cheeked Thrush", "Catharus minimus"),
    "herthr": Taxon("Hermit Thrush", "Catharus guttatus"),
    "norpar": Taxon("Northern Parula", "Setophaga americana"),
    "norwat": Taxon("Northern Waterthrush", "Parkesia noveboracensis"),
    "ovenbi1": Taxon("Ovenbird", "Seiurus aurocapilla"),
    "robgro": Taxon("Rose-breasted Grosbeak", "Pheucticus ludovicianus"),
    "swathr": Taxon("Swainson's Thrush", "Catharus ustulatus"),
    "veery": Taxon("Veery", "Catharus fuscescens"),
    "whcspa": Taxon("White-crowned Sparrow", "Zonotrichia leucophrys"),
    "whtspa": Taxon("White-throated Sparrow", "Zonotrichia albicollis"),
    "woothr": Taxon("Wood Thrush", "Hylocichla mustelina"),
}

BROAD_COMMENT_LABELS = set(NIGHTHAWK_BROAD_LABELS)


def _nighthawk_species_taxonomy() -> dict[str, Taxon]:
    taxonomy = dict(FALLBACK_NIGHTHAWK_SPECIES)
    path = _nighthawk_taxonomy_path()
    if not path:
        return taxonomy
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                code = (row.get("code") or "").strip().lower()
                common = (row.get("name") or "").strip()
                scientific = (row.get("sci_name") or "").strip()
                if code and common:
                    taxonomy[code] = Taxon(common, scientific)
    except OSError:
        pass
    return taxonomy


def _nighthawk_taxonomy_path() -> Path | None:
    root = analyzers_root() / "nighthawk"
    matches = sorted(
        glob.glob(str(root / "**" / "site-packages" / "nighthawk" / "taxonomy" / "ebird_taxonomy.csv"), recursive=True)
    )
    return Path(matches[0]) if matches else None


def _parsed_recording(night_path: Path, recording: str) -> filenames.ParsedName:
    parsed = filenames.parse(recording)
    if parsed:
        return parsed
    raise ValueError(f"Unrecognized recording filename for eBird export: {night_path / 'audio' / recording}")


def _recording_session_stamp(night_path: Path, recording: str) -> str:
    """Return the eBird export filename timestamp without seconds."""
    return _parsed_recording(night_path, recording).recorded_at.strftime("%Y-%m-%d_%H-%M")


def _scientific_name_fields(scientific_name: str) -> tuple[str, str]:
    parts = str(scientific_name or "").strip().split()
    if len(parts) < 2:
        return "", ""
    if any(part.lower() == "sp." for part in parts):
        return "", ""
    if not re.fullmatch(r"[A-Z][A-Za-z-]*", parts[0]):
        return "", ""
    if not all(re.fullmatch(r"[a-z][a-z.-]*", part) for part in parts[1:]):
        return "", ""
    return parts[0], " ".join(parts[1:])


def _recording_duration_minutes(night_path: Path, recording: str) -> float:
    path = night_path / "audio" / recording
    if not path.exists():
        return 60.0
    try:
        return max(1.0, _wav_duration_seconds(path) / 60.0)
    except Exception:  # noqa: BLE001
        return 60.0


def _recording_name_from_result_dir(path: Path) -> str:
    return path.parent.name + ".wav"


def _species_comment(detections: list[Detection]) -> str:
    return _aggregate_species_comment(detections)


def _aggregate_species_comment(detections: list[Detection]) -> str:
    nfc_count = sum(1 for detection in detections if detection.contributes_nfc_count)
    audio_detection_count = sum(1 for detection in detections if not detection.contributes_nfc_count)
    parts = []
    if nfc_count:
        parts.append(f"NFC {nfc_count}")
        broad_counts: dict[str, int] = {}
        for detection in detections:
            if detection.contributes_nfc_count and detection.source_label in BROAD_COMMENT_LABELS:
                broad_counts[detection.source_label] = broad_counts.get(detection.source_label, 0) + 1
        for label, count in sorted(broad_counts.items()):
            parts.append(f"{label} {count}")
    if audio_detection_count:
        parts.append(f"BirdNET detections {audio_detection_count}")
    return _sanitize_comment(" | ".join(parts))


def _submission_comments(night_path: Path, recording: str, options: EbirdExportOptions) -> str:
    parts = [DEFAULT_CHECKLIST_COMMENT]
    if options.submission_comments:
        parts.append(options.submission_comments)
    weather = _weather_comment(night_path, recording)
    if weather:
        parts.append(weather)
    return _sanitize_comment(" | ".join(parts))


def _weather_comment(night_path: Path, recording: str) -> str:
    path = night_path / "logs" / "environmental_conditions.csv"
    if not path.exists():
        return ""
    parsed = filenames.parse(recording)
    if not parsed:
        return ""
    target_date = parsed.recorded_at.strftime("%Y-%m-%d")
    target_time = parsed.recorded_at.strftime("%H-%M-%S")
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("hour_date") == target_date and row.get("hour_time") == target_time:
                    return environment_conditions_text_line(row)
    except OSError:
        return ""
    return ""


def _ebird_hotspot_id(value: str) -> str:
    match = re.search(r"\bL\d+\b", str(value or ""), flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _ebird_hotspot_url(value: str) -> str:
    hotspot_id = _ebird_hotspot_id(value)
    return f"https://ebird.org/hotspot/{hotspot_id}" if hotspot_id else ""


def _write_csv(path: Path, rows: list[dict], fields: list[str], *, include_header: bool) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL)
        if include_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({field: _sanitize_text(row.get(field, "")) for field in fields})


def _sanitize_text(value) -> str:
    text = str(value or "")
    text = text.replace('"', "")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = text.replace(",", " ")
    return re.sub(r"\s+", " ", text).strip()


def _sanitize_comment(value) -> str:
    """Keep pipe-delimited comments free of legacy date/time segments."""
    parts = []
    for part in _sanitize_text(value).split("|"):
        part = part.strip()
        if not part or re.match(r"^(?:Date|Time):\s*", part, flags=re.IGNORECASE):
            continue
        parts.append(part)
    return " | ".join(parts)


def _safe_label(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())


def _format_coordinate(value: float) -> str:
    return f"{float(value):.7f}".rstrip("0").rstrip(".")


def _ebird_date(value: datetime) -> str:
    return f"{value.month}/{value.day}/{value.year}"


def _format_duration_minutes(value: float) -> str:
    rounded = round(float(value), 1)
    return str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}"


def _format_seconds(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def _format_probability(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def _float(value) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else 0.0


def _optional_float(value) -> float | None:
    try:
        return float(str(value).strip())
    except Exception:  # noqa: BLE001
        return None
