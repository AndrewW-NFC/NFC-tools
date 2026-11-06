"""Offline sensitivity test; never changes production thresholds or results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from nfc_tools.analyzers import wingbeat_accompaniment as acc
from nfc_tools.analyzers import wingbeats as wing
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

PROFILE = {
    'broadband': {'spectral_flatness': .09, 'modulation': .18, 'periodicity': .45,
                  'repeat_periodicity': .20, 'pulse_count': 3, 'coherent_bands': 2},
    'accompaniment': {'modulation': .18, 'periodicity': .45, 'repeat_periodicity': .20,
                      'pulse_count': 3, 'noise_coherence': .30, 'noise_contrast': .10},
}


def broadband_pass(f, relaxed=False):
    if f is None:
        return False
    limits = PROFILE['broadband'] if relaxed else {
        'spectral_flatness': .12, 'modulation': .25, 'periodicity': .60,
        'repeat_periodicity': .35, 'pulse_count': 4, 'coherent_bands': 3}
    return (all(getattr(f, key) >= value for key, value in limits.items())
            and f.peak_envelope >= 1e-4 and f.band_energy_fraction >= 1e-4
            and f.low_band_fraction >= acc.MIN_LOW_BAND_FRACTION)


def scores(samples, kind):
    f = wing.window_features(samples, acc.ANALYSIS_RATE) if kind not in {'brief', 'accompaniment'} else None
    baseline = f.periodicity if broadband_pass(f) else None
    relaxed = f.periodicity if broadband_pass(f, True) else None
    # Production returns on broadband acceptance; otherwise use the same measured features.
    if baseline is None:
        features = acc.accompaniment_features(samples)
        baseline = acc.screen_accompaniment(features, allow_near_miss=kind in {'long', 'accompaniment'})
        for item in features:
            if (all(getattr(item, key) >= value for key, value in PROFILE['accompaniment'].items())
                    and item.peak_envelope >= 1e-4 and item.noise_ratio >= .005
                    and item.ridge_share >= .001 and item.residual_bins >= 20
                    and (acc.accompaniment_spectral_support(item) or acc.localized_pulse_support(item))):
                relaxed = max(relaxed or 0., item.periodicity)
    if baseline is not None:
        relaxed = max(relaxed or 0., baseline)
    return baseline, relaxed


def merge(items, start, end, score):
    if score is None:
        return
    if items and start <= items[-1]['end']:
        items[-1]['end'] = max(end, items[-1]['end'])
        items[-1]['periodicity'] = max(score, items[-1]['periodicity'])
    else:
        items.append({'start': start, 'end': end, 'periodicity': score})


def atomic_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def process_file(source, out):
    source, out = Path(source), Path(out)
    start_time = time.monotonic()
    candidates = {'baseline': [], 'relaxed': []}
    windows = 0
    end = 0.
    next_progress = 60.
    with tempfile.TemporaryFile() as errors:  # noqa: SIM117
        with subprocess.Popen([ensure_ffmpeg(), '-v', 'error', '-nostdin', '-i', str(source),
                               '-map', '0:a:0', '-ac', '1', '-ar', str(acc.ANALYSIS_RATE),
                               '-f', 'f32le', 'pipe:1'], stdout=subprocess.PIPE, stderr=errors) as proc:
            try:
                for offset, samples, kind in wing.analysis_windows(proc.stdout, acc.ANALYSIS_RATE):
                    end = max(end, offset + len(samples) / acc.ANALYSIS_RATE)
                    baseline, relaxed = scores(samples, kind)
                    for name, score in [('baseline', baseline), ('relaxed', relaxed)]:
                        merge(candidates[name], offset, offset + len(samples) / acc.ANALYSIS_RATE, score)
                    windows += 1
                    if end >= next_progress:
                        atomic_json(out / 'progress' / (source.stem + '.json'), {
                            'file': source.name, 'seconds_processed': end, 'windows': windows,
                            'baseline': len(candidates['baseline']), 'relaxed': len(candidates['relaxed']),
                            'elapsed': time.monotonic() - start_time})
                        next_progress += 60.
            except BaseException:
                proc.kill()
                raise
            if proc.wait():
                errors.seek(0)
                raise RuntimeError(errors.read().decode())
    result = {'file': source.name, 'source': str(source), 'duration_sec': end,
              'windows': windows, 'elapsed': time.monotonic() - start_time, **candidates}
    atomic_json(out / 'per_file' / (source.stem + '.json'), result)
    return result


def write_csv(path, rows, fields):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    exts = {'.wav', '.flac', '.mp3', '.m4a', '.aif', '.aiff', '.ogg'}
    files = []
    for root, dirs, names in os.walk(args.source):
        dirs[:] = [d for d in dirs if d.lower() != 'clips' and (Path(root) / d).resolve() != args.out.resolve()]
        files += [Path(root) / n for n in names if Path(n).suffix.lower() in exts and not n.startswith('._')]
    files.sort()
    if not files or len({p.stem for p in files}) != len(files):
        raise ValueError('No audio or duplicate stems')
    args.out.mkdir(parents=True, exist_ok=False)
    for directory in ('per_file', 'progress', 'labels', 'review_audio'):
        (args.out / directory).mkdir()
    manifest = {'profile': PROFILE, 'excluded_directory_names': ['clips'],
                'spectral_checks': 'unchanged; baseline accepted windows always retained',
                'inputs': [{'path': str(p), 'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns} for p in files],
                'code_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                [Path(__file__), Path(wing.__file__), Path(acc.__file__)]}}
    atomic_json(args.out / 'manifest.json', manifest)
    print(f'Scanning {len(files)} files with {args.workers} workers; clips excluded', flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(process_file, str(p), str(args.out)): p for p in files}
        for future in as_completed(jobs):
            result = future.result()
            results.append(result)
            print(f"Completed {result['file']}: baseline={len(result['baseline'])}, relaxed={len(result['relaxed'])}", flush=True)
    finalize(args, results)


def finalize(args, results):
    results.sort(key=lambda r: r['file'])
    rows, mismatches = [], []
    for result in results:
        source = Path(result['source'])
        old_path = args.source / 'results' / 'wingbeats' / source.stem / (source.stem + '_wingbeats.csv')
        if old_path.exists():
            with old_path.open() as f:
                old = list(csv.DictReader(f))
            actual = result['baseline']
            if len(old) != len(actual) or any(abs(float(a['start_sec']) - b['start']) > .001 or abs(float(a['end_sec']) - b['end']) > .001 for a, b in zip(old, actual)):
                mismatches.append(source.name)
        try:
            origin = datetime.strptime(source.stem[-19:], '%Y-%m-%d_%H-%M-%S').replace(tzinfo=ZoneInfo('America/New_York'))
        except ValueError:
            origin = None
        labels = []
        for c in result['relaxed']:
            cid = f'{len(rows)+1:04d}'
            existing = any(c['start'] <= b['end'] and c['end'] >= b['start'] for b in result['baseline'])
            clip_start = max(0, c['start'] - 3)
            clip_end = min(result['duration_sec'], c['end'] + 3)
            clip = args.out / 'review_audio' / f'{cid}_{source.stem}_{c["start"]:.2f}s.wav'
            subprocess.run([ensure_ffmpeg(), '-y', '-v', 'error', '-nostdin', '-ss', str(clip_start),
                            '-i', str(source), '-t', str(clip_end - clip_start), '-acodec', 'pcm_s16le', str(clip)], check=True)
            rows.append({'id': cid, 'filename': source.name, 'start_sec': c['start'], 'end_sec': c['end'],
                         'local_time': (origin + timedelta(seconds=c['start'])).isoformat(sep=' ', timespec='milliseconds') if origin else '',
                         'periodicity': c['periodicity'], 'overlaps_baseline': existing,
                         'clip': str(clip), 'clip_start_sec': clip_start, 'review': ''})
            labels.append(f"{c['start']:.3f}\t{c['end']:.3f}\tWING relaxed {cid}\n")
        (args.out / 'labels' / (source.stem + '_audacity.txt')).write_text(''.join(labels))
    fields = ['id', 'filename', 'start_sec', 'end_sec', 'local_time', 'periodicity', 'overlaps_baseline', 'clip', 'clip_start_sec', 'review']
    write_csv(args.out / 'candidates.csv', rows, fields)
    summary = {'files': len(results), 'hours': sum(r['duration_sec'] for r in results)/3600,
               'baseline_candidates': sum(len(r['baseline']) for r in results), 'relaxed_candidates': len(rows),
               'new_candidates': sum(not r['overlaps_baseline'] for r in rows), 'baseline_mismatches': mismatches}
    atomic_json(args.out / 'summary.json', summary)
    cards = []
    for row in rows:
        clip = Path(row['clip']).relative_to(args.out).as_posix()
        status = 'Original detection' if row['overlaps_baseline'] else 'New candidate'
        cards.append(f"<article><h2>{row['id']} · {row['local_time']} · {status}</h2>"
                     f"<p>{html.escape(row['filename'])}<br>Offset {row['start_sec']:.2f}–{row['end_sec']:.2f} s</p>"
                     f'<audio controls preload="none" src="{html.escape(clip)}"></audio></article>')
    (args.out / 'review.html').write_text(
        '<!doctype html><html><meta charset="utf-8"><title>Relaxed wingbeat test</title>'
        '<style>body{font:16px system-ui;max-width:900px;margin:40px auto;background:#f5f6f8;color:#17212b}'
        'article{padding:20px;margin:16px 0;background:white;border-radius:12px}h2{font-size:18px}audio{width:100%}</style>'
        f"<h1>Relaxed wingbeat test · October 17–18, 2026</h1><p>{len(rows)} candidates; "
        f"{summary['new_candidates']} additional candidates. These require listening review.</p>"
        '<p>Clips include three seconds of context on each side. Times are local recording times (America/New_York), inferred from filenames.</p>'
        + ''.join(cards) + '</html>')
    (args.out / 'README.md').write_text(
        '# Relaxed wingbeat sensitivity test\n\n'
        f"Processed {summary['files']} audio files ({summary['hours']:.3f} hours), excluding every clips directory. "
        'Inputs include 16 overnight recordings and one microphone-readiness diagnostic.\n\n'
        f"Baseline: {summary['baseline_candidates']} events. Relaxed: {summary['relaxed_candidates']} events; "
        f"{summary['new_candidates']} additional candidates. Baseline mismatches versus saved overnight results: {mismatches}.\n\n"
        'Open review.html to listen; candidates.csv records offsets, local times, baseline overlap, and clip paths. '
        'labels/ contains Audacity labels relative to each original file. review_audio/ contains 16-bit PCM excerpts with three seconds of context on each side. '
        'Candidate status is not a confirmation of wingbeats. Periodicity is not a probability.\n\n'
        'Test-only thresholds: broadband periodicity 0.60→0.45, repeat periodicity 0.35→0.20, modulation 0.25→0.18, '
        'flatness 0.12→0.09, pulse count 4→3, coherent bands 3→2. Accompaniment periodicity 0.60→0.45, '
        'repeat periodicity 0.35→0.20, modulation 0.25→0.18, pulse count 4→3, noise coherence 0.40→0.30, '
        'noise contrast 0.15→0.10. Spectral support and upper-band interference checks remain unchanged. '
        'All baseline-accepted windows are retained. Production code and existing results are unchanged.\n\n'
        'manifest.json records selected files and detector code hashes; per_file/ records all merged baseline and relaxed events.\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
