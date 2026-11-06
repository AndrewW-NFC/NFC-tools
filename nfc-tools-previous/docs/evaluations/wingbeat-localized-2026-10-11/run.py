"""Reproduce the localized-pulse field comparison; audio is never modified.

Run from the repository root with the editable package installed. Example paths
and measured outcomes are in report.md. Temporary decoded PCM is removed on exit.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import numpy as np

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from wingbeat_research_scan import _current_broadband_pass  # noqa: E402


def decode(path):
    raw = subprocess.check_output([
        ensure_ffmpeg(), '-v', 'error', '-nostdin', '-i', str(path),
        '-map', '0:a:0', '-ac', '1', '-ar', '24000', '-f', 'f32le', '-',
    ])
    return np.frombuffer(raw, dtype='<f4')


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def task(job):
    key, path, start, stop = job
    x = np.load(path, mmap_mode='r')
    samples = x[int(start * 24000):min(len(x), int((stop + 2) * 24000))]
    accepted = {'before': [], 'after': []}
    recovered = []
    checks = 0
    for local, samples, kind in w.analysis_windows(io.BytesIO(samples.tobytes()), 24000):
        if kind == 'brief':  # Keep this historical experiment's original schedule.
            continue
        offset = start + local
        if offset >= stop:
            break
        end = offset + len(samples) / 24000
        broad = kind != 'accompaniment' and _current_broadband_pass(w.window_features(samples, 24000))
        features = a.accompaniment_features(samples)
        # Zero only the new measurements to reproduce the unchanged old gates.
        original = [replace(f, pulse_lobe_width_hz=0., pulse_lobe_effective_width_hz=0.)
                    for f in features]
        near = kind != 'standard'
        before = broad or a.screen_accompaniment(original, allow_near_miss=near) is not None
        after = broad or a.screen_accompaniment(features, allow_near_miss=near) is not None
        assert not before or after
        if checks < 2:
            assert after == (w.screen_window(samples, 24000, pass_kind=kind) is not None)
            checks += 1
        for mode, decision in [('before', before), ('after', after)]:
            if decision:
                accepted[mode].append([offset, end])
        if after and not before:
            recovered.append({'start': offset, 'end': end, 'features': [
                asdict(f) for f in features if a.localized_pulse_support(f)
                and a.screen_accompaniment([f], allow_near_miss=near) is not None]})
    return dict(key=key, start=start, checks=checks, **accepted, recovered=recovered)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--positives', type=Path)
    parser.add_argument('--negatives', type=Path, help='ZIP of labeled negative WAV clips')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest, jobs = [], []
    with tempfile.TemporaryDirectory(prefix='nfc-localized-') as directory:
        cache = Path(directory)

        def add(key, group, samples, source=None, **metadata):
            path = cache / f'{key}.npy'
            np.save(path, samples)
            duration = len(samples) / 24000
            manifest.append(dict(key=key, group=group, source=str(source) if source else None,
                                 seconds=duration, pcm_sha256=hashlib.sha256(samples.tobytes()).hexdigest(),
                                 **metadata))
            for start in range(0, int(np.ceil(duration)), 60):
                jobs.append((key, str(path), start, min(start + 60, duration)))

        x = decode(args.recording)
        add('hour', 'site-hour', x, args.recording)
        for name, start, end in [('1758', 1072, 1096), ('2448', 1482, 1506), ('4200', 2514, 2538)]:
            for gain in (.1, 1, 3):
                for padding in (0, .25, .5, .75):
                    samples = np.r_[np.zeros(int(padding * 24000), dtype='<f4'),
                                    x[start * 24000:end * 24000] * gain].astype('<f4')
                    add(f'{name}-{gain}-{padding}', 'variant', samples, args.recording,
                        event=name, crop_start=start, gain=gain, padding=padding)
        if args.positives:
            for i, path in enumerate(sorted(args.positives.glob('*.mp3'))):
                add(f'positive-{i}', 'positive', decode(path), path,
                    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if args.negatives:
            with zipfile.ZipFile(args.negatives) as archive:
                for i, name in enumerate(archive.namelist()):
                    if name.startswith('__MACOSX') or not name.lower().endswith('.wav'):
                        continue
                    data = archive.read(name)
                    path = cache / 'negative.wav'
                    path.write_bytes(data)
                    add(f'negative-{i}', 'discrete-negative', decode(path), f'{args.negatives}!{name}',
                        source_sha256=hashlib.sha256(data).hexdigest())
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        results = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(task, job) for job in jobs]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(f"Completed {len(results)}/{len(jobs)}: {result['key']} at {result['start']}s", flush=True)
        output = []
        for item in manifest:
            matching = [result for result in results if result['key'] == item['key']]
            output.append(dict(item, **{mode: merge([interval for result in matching for interval in result[mode]])
                                       for mode in ('before', 'after')},
                               recovered=[window for result in matching for window in result['recovered']]))
        (args.output / 'results.json').write_text(json.dumps(output, indent=2) + '\n')
        print(json.dumps({'checks': sum(r['checks'] for r in results), 'files': len(output)}))


if __name__ == '__main__':
    main()
