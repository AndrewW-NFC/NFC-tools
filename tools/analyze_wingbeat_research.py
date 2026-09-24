"""Descriptive research comparison; no classifier, threshold fitting or production writes.

Requires pandas and NumPy. Input scans must be complete and reference-validated.
One recording's median over accepted windows is the primary analysis unit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def cliffs_delta(x, y):
    """P(X>Y)-P(X<Y), with ties contributing zero; no parametric assumptions."""
    x, y = np.asarray(x), np.sort(np.asarray(y))
    if not len(x) or not len(y):
        return np.nan
    less = np.searchsorted(y, x, side='left')
    more = len(y) - np.searchsorted(y, x, side='right')
    return float(np.sum(less - more) / (len(x) * len(y)))


def compare(frame, features, contrast):
    out = []
    xc = frame[frame.source == 'xc_positive']
    fsd = frame[frame.source == 'fsd_hard_negative']
    for name in features:
        x, y = xc[name].dropna().to_numpy(), fsd[name].dropna().to_numpy()
        if min(len(x), len(y)) < 5:
            continue
        qx, qy = np.quantile(x, [.1, .25, .5, .75, .9]), np.quantile(y, [.1, .25, .5, .75, .9])
        bins = np.unique(np.quantile(np.r_[x, y], np.linspace(0, 1, 21)))
        overlap = 1. if len(bins) < 2 else float(np.minimum(np.histogram(x, bins)[0] / len(x), np.histogram(y, bins)[0] / len(y)).sum())
        row = {'contrast': contrast, 'feature': name, 'xc_n': len(x), 'fsd_n': len(y),
                   'cliffs_delta_xc_minus_fsd': cliffs_delta(x, y), 'histogram_overlap': overlap,
                   'xc_fraction_in_fsd_p10_p90': float(np.mean((x >= qy[0]) & (x <= qy[-1])))}
        row.update({f'{group}_{q}': val for group, arr in [('xc', qx), ('fsd', qy)]
                    for q, val in zip(['p10', 'p25', 'median', 'p75', 'p90'], arr)})
        out.append(row)
    return out


def recording_summary(windows, features):
    return windows.groupby(['source', 'file_id'], sort=False)[features].median().reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fsd', type=Path, required=True)
    parser.add_argument('--xc', type=Path, required=True)
    parser.add_argument('--xc-metadata', type=Path, required=True)
    parser.add_argument('--fsd-metadata', type=Path, required=True)
    parser.add_argument('--bundle-data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tables, file_tables, summaries = [], [], {}
    for source, root, expected in [('fsd_hard_negative', args.fsd, 3343), ('xc_positive', args.xc, 958)]:
        summary = json.loads((root / 'summary.json').read_text())
        if (summary['processed'] != expected or summary['selected'] != expected or
                summary['errors'] or summary['validation_mismatches'] or not summary['validated_files']):
            raise RuntimeError(f'Incomplete or unvalidated input: {root}')
        summaries[source] = summary
        tables.append(pd.read_csv(root / 'windows.csv', low_memory=False, dtype={'file_id': str}, float_precision='round_trip'))
        file_tables.append(pd.read_csv(root / 'files.csv', dtype={'file_id': str}))
    windows = pd.concat(tables, ignore_index=True)
    files = pd.concat(file_tables, ignore_index=True)
    if windows.duplicated(['source', 'file_id', 'window_start_sec']).any():
        raise RuntimeError('Duplicate windows')
    if (windows.reference_validation_match.dropna() != 1).any():
        raise RuntimeError('Reference mismatch in input rows')
    source_meta = pd.read_csv(args.xc_metadata, dtype=str, encoding='utf-8-sig').fillna('')
    source_meta['file_id'] = 'XC' + source_meta.id
    source_meta = source_meta.set_index('file_id')
    fsd_meta = json.loads(args.fsd_metadata.read_text())
    files['format'] = files.filename.map(lambda x: Path(x).suffix.lower())
    files['uploader'] = [source_meta.loc[r.file_id, 'rec'] if r.source == 'xc_positive'
                         else fsd_meta.get(r.file_id, {}).get('uploader', '') for r in files.itertuples()]
    files['uploader'] = files.uploader.fillna('').replace('', 'unknown')
    files['declared_source_rate'] = [source_meta.loc[r.file_id, 'smp'] if r.source == 'xc_positive'
                                    else str(getattr(r, 'meta_source_rate', '')) for r in files.itertuples()]
    files['declared_source_rate_numeric'] = pd.to_numeric(files.declared_source_rate, errors='coerce')
    files['recording_device'] = [source_meta.loc[r.file_id, 'dvc'] if r.source == 'xc_positive' else '' for r in files.itertuples()]
    files['microphone'] = [source_meta.loc[r.file_id, 'mic'] if r.source == 'xc_positive' else '' for r in files.itertuples()]
    files['wingbeats_only_type'] = files.meta_type.fillna('').str.strip().str.lower().eq('wingbeats')
    files.to_csv(args.out / 'file_provenance.csv', index=False)
    metadata_columns = ['source', 'file_id', 'format', 'uploader', 'declared_source_rate', 'declared_source_rate_numeric', 'duration_sec',
                        'wingbeats_only_type', 'meta_labels', 'meta_type', 'meta_en', 'meta_url', 'meta_rmk']
    metadata = files[metadata_columns]
    # Select the highest-scoring passing accompaniment band; this respects production selection.
    bands = ['700_2200', '1800_4000', '3500_6500', '6000_9500']
    passes = []
    limits = {'peak_envelope': 1e-4, 'pulse_count': 4, 'periodicity': .60, 'repeat_periodicity': .35,
                  'modulation': .25, 'noise_coherence': .40, 'noise_contrast': .15, 'noise_ratio': .005,
                  'ridge_share': .001, 'residual_bins': 20}
    for band in bands:
        mask = pd.Series(True, index=windows.index)
        for feature, threshold in limits.items():
            mask &= windows[f'acc_{band}_{feature}'] >= threshold
        passes.append(windows[f'acc_{band}_periodicity'].where(mask, -np.inf))
    scores = np.column_stack(passes)
    winners = np.argmax(scores, axis=1)
    has_winner = np.isfinite(scores.max(axis=1))
    for field in ['periodicity', 'repeat_periodicity', 'modulation', 'noise_coherence', 'noise_contrast',
                  'noise_ratio', 'ridge_share', 'residual_bins', 'pulse_count', 'noise_center_hz']:
        arr = np.column_stack([windows[f'acc_{b}_{field}'] for b in bands])
        windows['selected_acc_' + field] = np.where(has_winner, arr[np.arange(len(windows)), winners], np.nan)
    excluded = {'pulse_times_sec'}
    prefixes = ('wing_', 'beat_', 'ipi_', 'pulse_', 'band', 'spectral_', 'selected_acc_')
    features = [c for c in windows if (c.startswith(prefixes) or c in ['rms', 'peak_abs', 'crest_factor', 'waveform_kurtosis', 'zero_cross_rate'])
                and c not in excluded and pd.api.types.is_numeric_dtype(windows[c])]
    windows[features] = windows[features].replace([np.inf, -np.inf], np.nan)
    accepted = windows[windows.current_detect == 1].copy()
    events = []
    for (source, file_id), group in accepted.groupby(['source', 'file_id'], sort=False):
        current = None
        for row in group.sort_values('window_start_sec').itertuples():
            if current is None or row.window_start_sec > current['end_sec']:
                if current is not None:
                    current['routes'] = ';'.join(sorted(current['routes']))
                    events.append(current)
                current = {'source': source, 'file_id': file_id, 'start_sec': row.window_start_sec,
                           'end_sec': row.window_end_sec, 'periodicity': row.current_score,
                           'accepted_windows': 1, 'routes': {row.current_route}}
            else:
                current['end_sec'] = row.window_end_sec
                current['periodicity'] = max(current['periodicity'], row.current_score)
                current['accepted_windows'] += 1
                current['routes'].add(row.current_route)
        if current is not None:
            current['routes'] = ';'.join(sorted(current['routes']))
            events.append(current)
    event_table = pd.DataFrame(events)
    event_table.to_csv(args.out / 'candidate_events.csv', index=False)
    prior_rows = pd.read_csv(args.bundle_data / 'fsd50k_wing_scan_dev.csv', dtype={'fname': str}).set_index('fname')
    historical_checks = []
    for file_id, group in event_table[event_table.source == 'fsd_hard_negative'].groupby('file_id'):
        reconstructed = [{field: round(float(getattr(row, field)), 3)
                          for field in ['start_sec', 'end_sec', 'periodicity']}
                         for row in group.itertuples()]
        original = json.loads(prior_rows.loc[file_id, 'detections_json'])
        historical_checks.append({'file_id': file_id, 'rounded_prior_candidate_list_match': reconstructed == original})
    historical_checks = pd.DataFrame(historical_checks)
    historical_checks.to_csv(args.out / 'fsd_prior_candidate_validation.csv', index=False)
    if len(historical_checks) != 3343 or not historical_checks.rounded_prior_candidate_list_match.all():
        raise RuntimeError('Prior candidate list disagreement: diagnose before interpreting comparisons')
    primary = recording_summary(accepted, features).merge(metadata, on=['source', 'file_id'], validate='one_to_one')
    primary.to_csv(args.out / 'candidate_recording_summaries.csv', index=False)
    contrasts = compare(primary, features, 'all_candidate_recordings')
    for route in ['broadband', 'accompaniment']:
        subset = recording_summary(accepted[accepted.current_route == route], features).merge(metadata, on=['source', 'file_id'])
        contrasts.extend(compare(subset, features, route + '_only'))
    contrasts.extend(compare(primary[primary.format == '.wav'], features, 'wav_only'))
    matched_rate = primary[(primary.format == '.wav') & (primary.declared_source_rate_numeric == 44100)]
    contrasts.extend(compare(matched_rate, features, 'wav_44100_only'))
    pure = primary[(primary.source == 'fsd_hard_negative') | (primary.wingbeats_only_type & (primary.duration_sec <= 15))]
    contrasts.extend(compare(pure, features, 'xc_wingbeats_only_type_le15s'))
    creators = primary[primary.uploader != 'unknown'].groupby(['source', 'uploader'])[features].median().reset_index()
    contrasts.extend(compare(creators, features, 'uploader_medians'))
    comparisons = pd.DataFrame(contrasts)
    comparisons['abs_delta'] = comparisons.cliffs_delta_xc_minus_fsd.abs()
    comparisons = comparisons.sort_values(['contrast', 'abs_delta'], ascending=[True, False])
    comparisons.to_csv(args.out / 'feature_comparison.csv', index=False)
    # Subtype labels are non-exclusive recording labels, not temporal annotations.
    categories = {
        'footsteps_running': {'Run', 'Walk_and_footsteps'},
        'applause': {'Clapping', 'Applause'},
        'clocks': {'Clock', 'Tick-tock', 'Tick'},
        'machinery': {'Mechanisms', 'Engine', 'Engine_starting', 'Motor_vehicle_(road)', 'Vehicle',
                      'Tools', 'Power_tool', 'Drill', 'Mechanical_fan', 'Motorcycle', 'Train', 'Boat_and_Water_vehicle'},
        'rain_wind': {'Rain', 'Raindrop', 'Wind', 'Thunder', 'Thunderstorm'},
        'music_instruments': {'Music', 'Musical_instrument'},
        'voice_laughter': {'Human_voice', 'Laughter'},
    }
    label_sets = primary.meta_labels.fillna('').map(lambda s: set(s.split(',')))
    subtype = []
    subtype_counts = []
    for category, labels in categories.items():
        mask = label_sets.map(lambda values, labels=labels: bool(values & labels))
        group = primary[(primary.source == 'xc_positive') | mask]
        subtype.extend(compare(group, features, category))
        subtype_counts.append({'category': category, 'candidate_recordings': int(mask.sum())})
    pd.DataFrame(subtype).to_csv(args.out / 'confounder_comparison.csv', index=False)
    pd.DataFrame(subtype_counts).to_csv(args.out / 'confounder_counts.csv', index=False)
    # Per-recording pass fractions prevent long recordings dominating gate rates.
    broad_limits = {'peak_envelope': 1e-4, 'spectral_flatness': .12, 'modulation': .25, 'periodicity': .60,
                        'repeat_periodicity': .35, 'pulse_count': 4, 'coherent_bands': 3, 'band_energy_fraction': 1e-4}
    gates = []
    for selection, ww in [('all_windows_in_selected_files', windows), ('accepted_windows', accepted)]:
        for name, threshold in broad_limits.items():
            valid = ww['wing_' + name].notna()
            tmp = ww.loc[valid, ['source', 'file_id']].copy()
            tmp['pass'] = (ww.loc[valid, 'wing_' + name] >= threshold).astype(float)
            per_file = tmp.groupby(['source', 'file_id'])['pass'].mean().reset_index()
            for source, group in per_file.groupby('source'):
                gates.append({'selection': selection, 'source': source, 'gate': name, 'n_recordings': len(group),
                                  'mean_recording_pass_fraction': group['pass'].mean(), 'median_recording_pass_fraction': group['pass'].median()})
    pd.DataFrame(gates).to_csv(args.out / 'gate_pass_rates.csv', index=False)
    accepted.groupby(['source', 'current_route']).size().rename('windows').reset_index().to_csv(args.out / 'route_counts.csv', index=False)
    # Curation proposals, never promoted to ground-truth positives automatically.
    curation = files[files.source == 'xc_positive'].copy()
    curation['remarks_has_timestamp'] = curation.meta_rmk.fillna('').str.contains(r'\b\d{1,2}:\d{2}\b|\b\d+(?:\.\d+)?\s*(?:seconds?|secs?|s)\b', case=False, regex=True)
    curation['review_priority'] = np.where(curation.wingbeats_only_type & (curation.duration_sec <= 15), '1_short_wingbeats_only',
                                         np.where(curation.remarks_has_timestamp, '2_timestamp_remark',
                                                  np.where(curation.wingbeats_only_type, '3_wingbeats_only', '4_mixed_recording')))
    curation['localization_status'] = 'unverified_requires_listening_and_temporal_annotation'
    curation.sort_values(['review_priority', 'duration_sec']).to_csv(args.out / 'xc_curation_proposals.csv', index=False)
    # Historical table changes: don't infer detector changes from corrected scanner counts.
    old = pd.read_csv(args.bundle_data / 'xc_wingbeat_research_files.csv', dtype={'file_id': str})
    changes = files[files.source == 'xc_positive'][['file_id', 'windows', 'detected_windows', 'merged_candidates']].merge(
        old[['file_id', 'windows', 'detected_windows', 'merged_candidates']], on='file_id', suffixes=('_corrected', '_bundle'), validate='one_to_one')
    for name in ['windows', 'detected_windows', 'merged_candidates']:
        changes[name + '_difference'] = changes[name + '_corrected'] - changes[name + '_bundle']
    changes.to_csv(args.out / 'xc_historical_count_changes.csv', index=False)
    old_windows = pd.read_csv(args.bundle_data / 'xc_wingbeat_research_windows.csv.gz',
                              usecols=['file_id', 'window_start_sec', 'current_detect', 'current_score', 'current_route'],
                              dtype={'file_id': str})
    common = windows[windows.source == 'xc_positive'][old_windows.columns].merge(
        old_windows, on=['file_id', 'window_start_sec'], suffixes=('_corrected', '_bundle'), how='outer', indicator=True,
        validate='one_to_one')
    common['decision_disagreement'] = ((common._merge == 'both') &
        (common.current_detect_corrected != common.current_detect_bundle))
    common['route_disagreement'] = ((common._merge == 'both') &
        (common.current_route_corrected != common.current_route_bundle))
    common['absolute_score_difference'] = (common.current_score_corrected - common.current_score_bundle).abs()
    common['added_window'] = common._merge == 'left_only'
    common['removed_window'] = common._merge == 'right_only'
    historical_window_audit = common.groupby('file_id').agg(
        added_windows=('added_window', 'sum'), removed_windows=('removed_window', 'sum'),
        decision_disagreements=('decision_disagreement', 'sum'), route_disagreements=('route_disagreement', 'sum'),
        maximum_absolute_score_difference=('absolute_score_difference', 'max'))
    historical_window_audit.to_csv(args.out / 'xc_historical_window_audit.csv')
    prior = pd.read_csv(args.bundle_data / 'fsd50k_wing_scan_dev.csv', dtype={'fname': str})
    prior = prior.rename(columns={'fname': 'file_id', 'candidate_count': 'prior_candidate_count'})
    fsd_changes = files[files.source == 'fsd_hard_negative'][['file_id', 'merged_candidates']].merge(prior[['file_id', 'prior_candidate_count']], on='file_id', validate='one_to_one')
    fsd_changes['difference'] = fsd_changes.merged_candidates - fsd_changes.prior_candidate_count
    fsd_changes.to_csv(args.out / 'fsd_prior_count_changes.csv', index=False)
    # Source and uploader concentration diagnostics.
    files.groupby(['source', 'format', 'declared_source_rate'], dropna=False).size().rename('recordings').reset_index().to_csv(args.out / 'source_format_rates.csv', index=False)
    primary.groupby(['source', 'uploader']).size().rename('candidate_recordings').reset_index().sort_values('candidate_recordings', ascending=False).to_csv(args.out / 'uploader_concentration.csv', index=False)
    missing = accepted.groupby('source')[features].agg(lambda x: x.isna().mean()).T
    missing.to_csv(args.out / 'candidate_feature_missing_fractions.csv')
    # ECDF coordinates allow plotting without a plotting dependency.
    ecdfs = []
    headline = ['band1_150_600_modulation', 'selected_acc_noise_contrast', 'spectral_flux_cv', 'beat_rate_hz', 'ipi_cv', 'ipi_npvi', 'pulse_amp_cv', 'pulse_fwhm_ms_median',
                'pulse_above_threshold_duty_fraction', 'band_sync_lag_spread_ms', 'crest_factor',
                'spectral_entropy', 'spectral_centroid_hz', 'spectral_flux_mean', 'spectral_comb_score',
                'wing_periodicity', 'wing_modulation', 'wing_spectral_flatness', 'rms']
    for feature in headline:
        for source, group in primary.groupby('source'):
            arr = np.sort(group[feature].dropna().to_numpy())
            for i, value in enumerate(arr):
                ecdfs.append({'feature': feature, 'source': source, 'value': value, 'cumulative_fraction': (i+1)/len(arr)})
    pd.DataFrame(ecdfs).to_csv(args.out / 'feature_ecdfs.csv', index=False)
    detail = {'scan_summaries': summaries, 'candidate_recordings': primary.groupby('source').size().to_dict(),
                  'curation_counts': curation.review_priority.value_counts().to_dict(),
                  'historical_xc_differences': {k: int(changes[k + '_difference'].sum()) for k in ['windows', 'detected_windows', 'merged_candidates']},
                  'fsd_prior_candidate_mismatch_files': int((fsd_changes.difference != 0).sum()),
                  'analysis_unit': 'one recording median over accepted windows; uploader contrast uses medians of these recording medians',
                  'cliffs_delta': 'P(XC > FSD) - P(XC < FSD); ties zero; range -1 to 1; descriptive, not predictive accuracy',
                  'histogram_overlap': 'Sum of minimum probability mass in 20 pooled quantile bins; 1 means full histogram overlap',
                  'no_models_or_threshold_tuning': True}
    (args.out / 'analysis_summary.json').write_text(json.dumps(detail, indent=2))
    inputs = [args.fsd/'windows.csv', args.xc/'windows.csv', args.xc_metadata, args.fsd_metadata, Path(__file__)]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    (args.out / 'analysis_provenance.json').write_text(json.dumps({'input_sha256': hashes, 'numpy': np.__version__, 'pandas': pd.__version__}, indent=2))
    print(json.dumps(detail, indent=2))
    print(comparisons[comparisons.contrast == 'all_candidate_recordings'].head(20).to_string(index=False))


if __name__ == '__main__':
    main()
