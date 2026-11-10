"""Compare the fixed-lobe route on 120 deterministic synthetic controls.

Run with the project Python environment. This is a development check, not a
field accuracy estimate. The baseline retains only the original ridge features.
"""

# Role: Reproduce synthetic-comparison.json without external audio dependencies.
# Dependencies: NumPy, the production detector, and scripts/evaluate_wingbeats.py.
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from evaluate_wingbeats import KINDS, synthetic_signal

from nfc_tools.analyzers import wingbeats as w


def detect(samples, *, fixed):
    original = w.accompaniment_features
    if not fixed:
        def ridge_only(*args, **kwargs):
            return [f for f in original(*args, **kwargs) if not f.fixed_lobe_envelope]
        w.accompaniment_features = ridge_only
    try:
        return [(hit.start, hit.end) for hit in w.detect_stream(
            io.BytesIO(samples.astype('<f4').tobytes()), 24000)]
    finally:
        w.accompaniment_features = original


def main():
    results = {}
    for kind in KINDS:
        rows = []
        for seed in range(10):
            samples = synthetic_signal(kind, seed)
            rows.append({'seed': seed, 'before': detect(samples, fixed=False),
                             'after': detect(samples, fixed=True)})
        results[kind] = rows
        print(kind, 'before', sum(bool(r['before']) for r in rows),
              'after', sum(bool(r['after']) for r in rows), flush=True)
    Path(__file__).with_name('synthetic-comparison.json').write_text(
        json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
