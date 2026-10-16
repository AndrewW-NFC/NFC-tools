"""Measured regression windows and counterexamples for waterfowl recovery."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
from nfc_tools.analyzers import wingbeat_accompaniment as a

ROWS = json.loads((Path(__file__).parent / 'fixtures/waterfowl-window-features.json').read_text())


@pytest.mark.parametrize('row', ROWS, ids=lambda row: row['species'])
def test_confirmed_passage_windows_are_accepted(row):
    f = a.AccompanimentFeatures(**row['features'])
    assert a.screen_accompaniment([f], allow_near_miss=row['kind'] in {'long', 'accompaniment'}) is not None


@pytest.mark.parametrize('row', ROWS[:2], ids=lambda row: row['species'])
@pytest.mark.parametrize('change', [
    {'noise_coherence': .64}, {'noise_contrast': .29}, {'noise_ratio': .09},
    {'pulse_excess_flatness': .69}, {'low_band_fraction': .004},
    {'lower_pulse_coherence': .29}, {'pulse_lobe_effective_width_hz': 299},
    {'ridge_prominence': 4.9}, {'periodicity': .44}, {'repeat_periodicity': .24},
    {'pulse_count': 3}, {'peak_envelope': 1e-5}, {'lower_hz': 1800},
])
def test_weak_rhythm_without_support_is_not_enough(row, change):
    f = replace(a.AccompanimentFeatures(**row['features']), **change)
    assert a.screen_accompaniment([f], allow_near_miss=row['kind'] in {'long', 'accompaniment'}) is None


@pytest.mark.parametrize('change', [
    {'ridge_prominence': 15.9}, {'repeat_periodicity': .49},
    {'noise_coherence': .49}, {'pulse_excess_flatness': .19},
])
def test_moderate_spectral_flatness_needs_support(change):
    f = replace(a.AccompanimentFeatures(**ROWS[2]['features']), **change)
    assert a.screen_accompaniment([f]) is None


def test_upper_interference_cannot_use_irregular_rhythm_alternative():
    f = replace(a.AccompanimentFeatures(**ROWS[0]['features']),
                upper_pulse_dominance=4., upper_pulse_coherence=.99,
                upper_pulse_contrast=.9, lower_pulse_coherence=.2)
    assert a.upper_pulse_interference(f)
    assert a.screen_accompaniment([f]) is None
