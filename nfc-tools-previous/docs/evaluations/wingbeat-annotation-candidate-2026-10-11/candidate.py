"""Research candidate only: shorter windows and capped residual contrast.

Not enabled in the production detector. Thresholds are empirical, not biological
limits. The standard spectral route is capped; the existing localized route
remains available on the original schedule.
"""
from dataclasses import replace
from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers import wingbeats as w

MAX_CONTRAST = .75


def screen_features(features, *, allow_near_miss=False, short=False):
    selected = []
    for item in features:
        if item.noise_contrast > MAX_CONTRAST:
            if short:
                continue
            # Disable only standard spectral support; preserve localized lobes.
            item = replace(item, pulse_excess_flatness=0.)
        selected.append(item)
    return a.screen_accompaniment(selected, allow_near_miss=allow_near_miss)


def analysis_windows(stream, sample_rate=a.ANALYSIS_RATE):
    for start, samples, kind in w.analysis_windows(stream, sample_rate):
        # Reproduce the pre-experiment schedule after the brief pass is added.
        if kind == 'brief':
            continue
        yield start, samples, kind
        if sample_rate == a.ANALYSIS_RATE and kind != 'standard':
            yield start, samples[:sample_rate], 'short'


def screen_window(samples, sample_rate=w.SAMPLE_RATE, *, pass_kind='standard'):
    if sample_rate != a.ANALYSIS_RATE:
        return w.screen_window(samples, sample_rate, pass_kind=pass_kind)
    if pass_kind not in {'standard', 'long', 'accompaniment', 'short'}:
        raise ValueError(f'Unknown WING analysis pass: {pass_kind}')
    if pass_kind not in {'accompaniment', 'short'}:
        f = w.window_features(samples, sample_rate)
        if f is None:
            return None
        if (f.peak_envelope >= 1e-4 and f.spectral_flatness >= .12
                and f.modulation >= .25 and f.periodicity >= .6
                and f.repeat_periodicity >= .35 and f.pulse_count >= 4
                and f.coherent_bands >= 3 and f.low_band_fraction >= .005
                and f.band_energy_fraction >= 1e-4):
            return f.periodicity
    return screen_features(a.accompaniment_features(samples),
                           allow_near_miss=pass_kind in {'long', 'accompaniment'},
                           short=pass_kind == 'short')
