"""Compare the original, cross-band and current screens on labeled audio clips.

Accepts a ZIP or directory. Reads recordings without modifying them; reports are
written only to the explicit output directory. Clip-level labels need no species
annotations. WAV and MP3 are supported; this also accepts known positives. These tuning-set counts do not estimate field accuracy.
"""
import argparse
import csv
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

import numpy as np

from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE,
    accompaniment_features,
    screen_accompaniment,
)
from nfc_tools.analyzers.wingbeats import (
    HOP_SECONDS,
    SAMPLE_RATE,
    WINDOW_SECONDS,
    detect_stream,
    window_features,
)
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def previous_screen(features):
    """Frozen gates from before the September 2026 cross-band refinement."""
    return features is not None and (
        features.peak_envelope >= 1e-4 and features.spectral_flatness >= 0.12
        and features.modulation >= 0.25 and features.periodicity >= 0.6
        and features.repeat_periodicity >= 0.35 and features.pulse_count >= 4
    )


def recordings(source):
    if source.is_dir():
        for path in sorted(source.rglob('*')):
            if path.suffix.lower() in {'.wav', '.mp3'} and not path.name.startswith('._'):
                yield str(path.relative_to(source)), path.read_bytes()
    else:
        with zipfile.ZipFile(source) as archive:
            for info in sorted(archive.infolist(), key=lambda item: item.filename):
                path = Path(info.filename)
                if path.suffix.lower() in {'.wav', '.mp3'} and '__MACOSX' not in path.parts and not path.name.startswith('._'):
                    yield info.filename, archive.read(info)


def evaluate(name, data):
    # A fixed temporary filename avoids trusting paths supplied by the archive.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.wav'
        path.write_bytes(data)
        command = [
            ensure_ffmpeg(), '-v', 'error', '-nostdin', '-i', str(path),
            '-map', '0:a:0', '-ac', '1', '-ar', str(SAMPLE_RATE), '-f', 'f32le', '-',
        ]
        raw = subprocess.check_output(command)
        command[command.index('-ar') + 1] = str(ANALYSIS_RATE)
        wide_raw = subprocess.check_output(command)
    samples = np.frombuffer(raw, dtype='<f4')
    baseline = []
    windows = []
    for start in range(0, len(samples), SAMPLE_RATE * HOP_SECONDS):
        window = samples[start:start + SAMPLE_RATE * WINDOW_SECONDS]
        features = window_features(window)
        if features is None:
            continue
        accepted = previous_screen(features)
        windows.append(dict(start_sec=start / SAMPLE_RATE, baseline=accepted, **asdict(features)))
        if accepted:
            left, right = start / SAMPLE_RATE, (start + len(window)) / SAMPLE_RATE
            if baseline and left <= baseline[-1][1]:
                baseline[-1][1] = right
            else:
                baseline.append([left, right])
    cross_band = [asdict(candidate) for candidate in detect_stream(io.BytesIO(raw))]
    current = [asdict(candidate) for candidate in detect_stream(io.BytesIO(wide_raw), ANALYSIS_RATE)]
    wide_samples = np.frombuffer(wide_raw, dtype='<f4')
    accompaniment = []
    for start in range(0, len(wide_samples), ANALYSIS_RATE * HOP_SECONDS):
        features = accompaniment_features(wide_samples[start:start + ANALYSIS_RATE * WINDOW_SECONDS])
        accompaniment.append({'start_sec': start / ANALYSIS_RATE,
                              'accepted': screen_accompaniment(features) is not None,
                              'features': [asdict(item) for item in features]})
    return {'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'seconds': len(samples) / SAMPLE_RATE,
                'baseline_intervals': baseline, 'cross_band_intervals': cross_band,
                'current_intervals': current, 'windows': windows, 'accompaniment': accompaniment}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    results = [evaluate(name, data) for name, data in recordings(args.source)]
    if not results:
        parser.error('No WAV or MP3 recordings found')
    summary = {'recordings': len(results), 'seconds': sum(row['seconds'] for row in results),
                   'baseline_flagged': sum(bool(row['baseline_intervals']) for row in results),
                   'cross_band_flagged': sum(bool(row['cross_band_intervals']) for row in results),
                   'current_flagged': sum(bool(row['current_intervals']) for row in results)}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'results.json').write_text(json.dumps({'summary': summary, 'recordings': results}, indent=2) + '\n')
    with (args.output / 'results.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['file', 'sha256', 'seconds', 'baseline_intervals', 'cross_band_intervals', 'current_intervals', 'suppressed'])
        for row in results:
            writer.writerow([row['file'], row['sha256'], row['seconds'], json.dumps(row['baseline_intervals']), json.dumps(row['cross_band_intervals']),
                             json.dumps(row['current_intervals']), bool(row['baseline_intervals']) and not row['current_intervals']])
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
