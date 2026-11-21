"""Recheck supplied clips and controls; keep original audio unchanged.

Run from the repository root with --output pointing to a fresh JSON file.
Inputs and source hashes are recorded in baseline-features.json beside this file.
"""
import argparse
import hashlib
import io
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

import numpy as np

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def previous_rule(item):
    return (item.low_band_fraction < .0005
            and item.pulse_centroid_range_hz >= 700
            and item.pulse_width_ratio <= .80)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output file; historical results are not overwritten.')
    inputs = json.loads(Path(__file__).with_name('baseline-features.json').read_text())
    current_rule = a.swept_call_interference
    results = []
    for row in inputs:
        path = Path(row['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], path
        raw = subprocess.check_output([
            ensure_ffmpeg(), '-v', 'error', '-i', str(path), '-ac', '1',
            '-ar', '24000', '-f', 'f32le', '-',
        ])
        samples = np.frombuffer(raw, dtype='<f4')
        variants = []
        for gain in (.1, 1, 3):
            for padding in (0, .125, .5, .75):
                pcm = np.r_[np.zeros(round(padding * 24000)), samples * gain].astype('<f4').tobytes()
                try:
                    a.swept_call_interference = previous_rule
                    before = [asdict(c) for c in detect_stream(io.BytesIO(pcm), 24000)]
                finally:
                    a.swept_call_interference = current_rule
                after = [asdict(c) for c in detect_stream(io.BytesIO(pcm), 24000)]
                variants.append(dict(gain=gain, padding=padding, before=before, after=after))
        results.append(dict(path=str(path), sha256=row['sha256'], variants=variants))
        print(path.name, sum(bool(v['before']) for v in variants),
              sum(bool(v['after']) for v in variants), flush=True)
    args.output.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
