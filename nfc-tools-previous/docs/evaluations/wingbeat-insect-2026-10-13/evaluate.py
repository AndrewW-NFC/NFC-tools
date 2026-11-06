"""Compare the targeted filter with identical features and its veto disabled.

Sources are read-only. Output contains labels, hashes, intervals and changed
windows; no audio. Run with the previous experiment's partition.json and an
output directory. Process workers are independent recordings, not agents.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from wingbeat_research_scan import _current_broadband_pass


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def evaluate(job):
    command = [ensure_ffmpeg(), '-v', 'error', '-nostdin', '-i', job['path']]
    if 'crop' in job:
        start, end = job['crop']
        command += ['-ss', str(start), '-t', str(end - start)]
    raw = subprocess.check_output(command + ['-map', '0:a:0', '-ac', '1', '-ar', '24000', '-f', 'f32le', '-'])
    x = np.frombuffer(raw, dtype='<f4')
    gain, padding = job.get('gain', 1), job.get('padding', 0)
    x = np.r_[np.zeros(round(padding * 24000), dtype='<f4'), x * gain].astype('<f4')
    before, after, changes = [], [], []
    for start, samples, kind in w.analysis_windows(io.BytesIO(x.tobytes()), 24000):
        broad = kind not in {'brief', 'accompaniment'} and _current_broadband_pass(w.window_features(samples, 24000))
        fs = a.accompaniment_features(samples)
        previous = [replace(f, upper_pulse_dominance=0.) for f in fs]
        near = kind in {'long', 'accompaniment'}
        old = broad or a.screen_accompaniment(previous, allow_near_miss=near) is not None
        new = broad or a.screen_accompaniment(fs, allow_near_miss=near) is not None
        assert not new or old, job['id']
        end = start + len(samples) / 24000
        if old:
            before.append([start, end])
        if new:
            after.append([start, end])
        if old != new:
            changes.append({'start': start, 'end': end, 'kind': kind, 'features': [asdict(f) for f in fs if a.upper_pulse_interference(f)]})
    before, after = merge(before), merge(after)
    # Check real streaming intervals on each
    # changed file and the sample/field/reference regression groups.
    if changes or job['dataset'] not in {'xc', 'fsd'}:
        assert after == [[h.start, h.end] for h in w.detect_stream(io.BytesIO(x.tobytes()), 24000)], job['id']
    return dict(**job, pcm_sha256=hashlib.sha256(raw).hexdigest(),
                duration=len(x)/24000, before=before, after=after, changed_windows=changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('partition', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--sample', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--negatives', type=Path, required=True)
    parser.add_argument('--field', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(args.partition.read_text())
    for gain in [.1, 1, 3]:
        for padding in [0, .25, .5, .75]:
            jobs.append({'id': f'insect-{gain}-{padding}', 'dataset': 'insect', 'label': 'no', 'path': str(args.sample), 'gain': gain, 'padding': padding})
    for path in sorted(args.references.glob('*.mp3')):
        jobs.append({'id': path.stem, 'dataset': 'reference', 'label': 'yes', 'path': str(path)})
    for crop in [[1078, 1089], [1488, 1493], [2520, 2530]]:
        for gain in [.1, 1, 3]:
            for padding in [0, .25, .5, .75]:
                jobs.append({'id': f'field-{crop[0]}-{gain}-{padding}', 'dataset': 'field', 'label': 'yes', 'path': str(args.field), 'crop': crop, 'gain': gain, 'padding': padding})
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(args.negatives) as archive:
            for i, name in enumerate(archive.namelist()):
                if name.startswith('__MACOSX') or not name.lower().endswith('.wav'):
                    continue
                path = Path(temporary) / f'{i}.wav'
                path.write_bytes(archive.read(name))
                jobs.append({'id': name, 'dataset': 'discrete', 'label': 'no', 'path': str(path)})
        results = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(evaluate, job) for job in jobs]):
                row = future.result()
                results.append(row)
                if len(results) % 10 == 0:
                    print(f'{len(results)}/{len(jobs)}', flush=True)
        results.sort(key=lambda row: row['id'])
    # The earlier production run independently verifies the reconstructed
    # baseline and catches stale labels/audio or accidental changes to old gates.
    original = {row['id']: row for row in json.loads(
        (args.partition.parent / 'production_verification.json').read_text())}
    for row in results:
        if row['dataset'] in {'xc', 'fsd'}:
            assert row['before'] == original[row['id']]['intervals'], row['id']
            assert row['pcm_sha256'] == original[row['id']]['pcm_sha256'], row['id']
    (args.output / 'results.json').write_text(json.dumps(results, indent=2))
    summary = {}
    for dataset in sorted({r['dataset'] for r in results}):
        selected = [r for r in results if r['dataset'] == dataset]
        summary[dataset] = {'files': len(selected), 'before': sum(bool(r['before']) for r in selected), 'after': sum(bool(r['after']) for r in selected), 'changed': sum(r['before'] != r['after'] for r in selected)}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
