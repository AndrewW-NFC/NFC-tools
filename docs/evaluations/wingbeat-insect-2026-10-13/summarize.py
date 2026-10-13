"""Verify the historical baseline and publish compact reviewable measurements."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def coverage(row, mode):
    start, end = row['target']
    return sum(max(0, min(end, stop) - max(start, begin)) for begin, stop in row[mode])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('historical', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = json.loads(args.results.read_text())
    historical = {r['id']: r for r in json.loads(args.historical.read_text())}
    checked = 0
    for row in rows:
        if row['dataset'] in {'xc', 'fsd'}:
            assert row['before'] == historical[row['id']]['intervals'], row['id']
            assert row['pcm_sha256'] == historical[row['id']]['pcm_sha256'], row['id']
            checked += 1
    assert checked == len(historical)
    summary = {}
    for dataset in sorted({r['dataset'] for r in rows}):
        for label in ('yes', 'no'):
            selected = [r for r in rows if r['dataset'] == dataset and r['label'] == label]
            if not selected:
                continue
            result = {
                'files': len(selected),
                'before_flagged': sum(bool(r['before']) for r in selected),
                'after_flagged': sum(bool(r['after']) for r in selected),
                'changed_files': sum(r['before'] != r['after'] for r in selected),
                'before_seconds': sum(e - s for r in selected for s, e in r['before']),
                'after_seconds': sum(e - s for r in selected for s, e in r['after']),
            }
            if dataset == 'xc' and label == 'yes':
                for mode in ('before', 'after'):
                    result[mode + '_passages'] = sum(coverage(r, mode) > 0 for r in selected)
                    result[mode + '_coverage'] = sum(coverage(r, mode) for r in selected)
            summary[dataset + '_' + label] = result
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    fields = ['id', 'dataset', 'label', 'pcm_sha256', 'before', 'after']
    with (args.output / 'recordings.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row[k]) if isinstance(row[k], list) else row[k] for k in fields})
    repository = Path(__file__).resolve().parents[3]
    sources = ['src/nfc_tools/analyzers/wingbeat_accompaniment.py',
               'src/nfc_tools/analyzers/wingbeats.py',
               'docs/evaluations/wingbeat-insect-2026-10-13/evaluate.py',
               'docs/evaluations/wingbeat-insect-2026-10-13/summarize.py']
    provenance = {
        'baseline_git': 'dd15bcf',
        'prior_production_comparisons': checked,
        'comparison_jobs': len(rows),
        'source_sha256': {p: hashlib.sha256((repository / p).read_bytes()).hexdigest() for p in sources},
        'results_sha256': hashlib.sha256(args.results.read_bytes()).hexdigest(),
    }
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    print('Changed non-insect recordings:', [r['id'] for r in rows
                                             if r['dataset'] != 'insect' and r['before'] != r['after']])


if __name__ == '__main__':
    main()
