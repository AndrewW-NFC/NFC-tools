"""Compare cached/uncached screening on identical decoded PCM without publishing results."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter

from nfc_tools.analyzers.wingbeats import detect_stream
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recordings', type=Path, nargs='+')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.seconds <= 0 or args.repeats < 1:
        parser.error('seconds and repeats must be positive')
    for path in args.recordings:
        pcm = subprocess.run([
            ensure_ffmpeg(), '-hide_banner', '-loglevel', 'error', '-nostdin',
            '-i', str(path), '-t', str(args.seconds), '-map', '0:a:0', '-ac', '1',
            '-ar', '24000', '-f', 'f32le', 'pipe:1',
        ], check=True, capture_output=True).stdout
        timings = {False: [], True: []}
        reference = None
        for repeat in range(args.repeats):
            # Alternate order to reduce warmup/order bias.
            for cached in ((False, True) if repeat % 2 == 0 else (True, False)):
                start = perf_counter()
                candidates = detect_stream(io.BytesIO(pcm), 24000, reuse_frames=cached)
                timings[cached].append(perf_counter() - start)
                if reference is None:
                    reference = candidates
                elif candidates != reference:
                    raise RuntimeError(f'Detections changed for {path}')
        baseline, optimized = median(timings[False]), median(timings[True])
        print(json.dumps(dict(
            recording=path.name, audio_seconds=len(pcm) / (24000 * 4),
            repeats=args.repeats, baseline_seconds=baseline,
            optimized_seconds=optimized, speedup=baseline / optimized,
            detections=len(reference), exact_match=True,
        )), flush=True)


if __name__ == '__main__':
    main()
