"""Verify real decoded production outputs against cached short-pass predictions."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import io
import json
from pathlib import Path
import subprocess

from nfc_tools.analyzers import wingbeats as w
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def task(job):
    raw = subprocess.check_output([ensure_ffmpeg(), '-v', 'error', '-nostdin', '-i', job['path'],
                                   '-map', '0:a:0', '-ac', '1', '-ar', '24000', '-f', 'f32le', '-'])
    hits = w.detect_stream(io.BytesIO(raw), 24000)
    return dict(id=job['id'], intervals=[[h.start, h.end] for h in hits],
                pcm_sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    args = parser.parse_args()
    jobs = json.loads((args.experiment / 'partition.json').read_text())
    predictions = json.loads((args.experiment / 'short_only_results.json').read_text())
    expected = {r['id']: r['intervals'] for p in predictions.values() for r in p['short']['rows']}
    results = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(task, j) for j in jobs]):
            row = future.result()
            assert row['intervals'] == expected[row['id']], row
            results.append(row)
            if len(results) % 20 == 0:
                print(f'Verified {len(results)}/{len(jobs)} files', flush=True)
    (args.experiment / 'production_verification.json').write_text(json.dumps(results, indent=2))
    print(f'PASS: {len(results)} production outputs exactly match predictions', flush=True)


if __name__ == '__main__':
    main()
