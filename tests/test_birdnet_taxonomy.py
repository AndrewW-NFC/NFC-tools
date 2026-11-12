"""Protect canonical export names, review-only candidates, and pinned provenance."""
# Role: Regression coverage for the versioned BirdNET/eBird crosswalk.
# Dependencies: pytest, packaged crosswalk, export implementation, maintenance builder.
import csv
import importlib.util
import json
from pathlib import Path

import pytest

from nfc_tools import birdnet_taxonomy
from nfc_tools.ebird_export import EbirdExportOptions, prepare_record_export


@pytest.mark.parametrize(('scientific', 'common'), [
    ('Megascops asio', 'Eastern Screech-Owl'),
    ('Aphelocoma coerulescens', 'Florida Scrub-Jay'),
    ('Catharus minimus', 'Gray-cheeked Thrush'),
    ('Strix varia', 'Barred Owl'),
])
def test_canonical_names(scientific, common):
    mapping = birdnet_taxonomy.resolve(scientific)
    assert mapping.status == 'mapped'
    assert mapping.common == common
    assert mapping.scientific == scientific
    assert mapping.version == 'birdnet3-ebird2026-r1'


@pytest.mark.parametrize('write_import', [True, False])
def test_export_corrects_names_and_retains_review_evidence(tmp_path, write_import):
    folder = tmp_path / 'results' / 'birdnet' / '009_NFC_2026-08-27_02-00-30'
    folder.mkdir(parents=True)
    (folder / 'test.BirdNET.results.csv').write_text(
        'Start (s),End (s),Scientific name,Common name,Confidence\n'
        '0,3,Megascops asio,Eastern Screech Owl,0.9\n'
        '3,6,Megascops asio,Eastern Screech-Owl,0.8\n'
        '6,9,Anas carolinensis,Green-winged Teal,0.9\n'
        '9,12,Apus nipalensis,House Swift,0.9\n'
        '12,15,Acanthis cabaret,Acanthis cabaret,0.9\n'
        '15,18,Unrecognized species,Eastern Screech Owl,0.9\n'
        '18,21,,Barred Owl,0.9\n'
        '21,24,Acheta domesticus,House Cricket,0.9\n', encoding='utf-8')
    result = prepare_record_export(tmp_path, EbirdExportOptions('Test', 42, -71, 'MA', write_import=write_import))
    assert result['taxonomy_review_required'] == 5
    for path in (result['review_path'], result['combined_review_path']):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 8
        mapped = [r for r in rows if r['taxonomy_status'] == 'mapped']
        assert {r['common_name'] for r in mapped} == {'Eastern Screech-Owl'}
        assert {r['original_common_name'] for r in mapped} == {'Eastern Screech Owl', 'Eastern Screech-Owl'}
        assert all(r['taxonomy_version'] == 'birdnet3-ebird2026-r1' for r in rows)
        teal = next(r for r in rows if r['original_scientific_name'] == 'Anas carolinensis')
        assert teal['taxonomy_status'] == 'review_required'
        assert teal['taxonomy_reason'] == 'common_name_only_review'
        assert teal['candidate_scientific_name'] == 'Anas crecca'
        assert teal['scientific_name'] == 'Anas carolinensis'
        assert next(r for r in rows if r['original_common_name'] == 'House Swift')['taxonomy_reason'] == 'cached_species_code_review'
        assert next(r for r in rows if r['original_common_name'] == 'House Cricket')['taxonomy_status'] == 'non_bird'
        assert sum(r['taxonomy_reason'] == 'unknown_scientific_name' for r in rows) == 2
    if write_import:
        for path in (result['import_path'], result['combined_import_path']):
            with path.open(newline='') as handle:
                uploads = list(csv.reader(handle))
            assert len(uploads) == 1
            assert uploads[0][0] == 'Eastern Screech-Owl'
            assert uploads[0][4] == 'NFC 2 | Nighthawk detections 0 | BirdNET detections 2'
    else:
        assert result['import_paths'] == []
        assert result['combined_import_path'] is None


def test_crosswalk_is_reproducible_and_all_accepted_rows_have_identity(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('builder', root / 'scripts/build_birdnet_ebird_crosswalk.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    name = birdnet_taxonomy.RESOURCE + '.csv'
    target = tmp_path / name
    builder.build(root / 'docs/evaluations/birdnet-ebird-taxonomy-2026-11-08/audit.json',
                  target, 'birdnet3-ebird2026-r1')
    data = root / 'src/nfc_tools/data'
    assert target.read_bytes() == (data / name).read_bytes()
    assert target.with_suffix('.json').read_bytes() == (data / name).with_suffix('.json').read_bytes()
    manifest = json.loads(target.with_suffix('.json').read_text())
    assert manifest['counts'] == {'mapped': 9561, 'review_required': 273, 'non_bird': 1726}
    with target.open(newline='') as handle:
        for row in csv.DictReader(handle):
            if row['status'] == 'mapped':
                assert row['birdnet_scientific'] == row['ebird_scientific']
                assert row['ebird_common'] and row['ebird_code']
