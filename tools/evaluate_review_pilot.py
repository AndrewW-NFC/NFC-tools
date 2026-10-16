"""Evaluate the current wingbeat detector on a frozen listening-review snapshot."""
import argparse
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timezone

from nfc_tools.analyzers.wingbeats import detect_stream
from nfc_tools.analyzers.wingbeat_accompaniment import ANALYSIS_RATE
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    batch_path = args.root / 'reviews' / args.batch
    batch = json.loads((batch_path / 'batch.json').read_text())
    with sqlite3.connect(f'file:{batch_path / "annotations.sqlite"}?mode=ro', uri=True) as db:
        reviews = {r['recording_id']: r for (body,) in db.execute('SELECT body FROM reviews')
                   for r in [json.loads(body)]}
    snapshot = {'batch': batch, 'reviews': reviews}
    (args.output / 'review-snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n')
    repo = Path(__file__).resolve().parents[1]
    source_paths = [Path(__file__), repo/'src/nfc_tools/analyzers/wingbeats.py',
                    repo/'src/nfc_tools/analyzers/wingbeat_accompaniment.py']
    provenance = {'created_at': datetime.now(timezone.utc).isoformat(),
                  'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                  'source_sha256': {str(p.relative_to(repo)):sha(p.read_bytes()) for p in source_paths},
                  'analysis_rate': ANALYSIS_RATE,
                  'ffmpeg': subprocess.check_output([ensure_ffmpeg(),'-version'],text=True).splitlines()[0],
                  'method': 'Full original archive members, hash verified; ffmpeg first audio stream, mono f32le at production analysis rate; unmodified detect_stream; strict positive-duration overlap, no timing tolerance.',
                  'interpretation': 'None heard is a listener label, not verified biological absence. Detections in those recordings are unresolved disagreements, not confirmed false positives.'}
    results=[]
    archives={}
    try:
        for item in batch['records']:
            review=reviews.get(item['id'],{})
            clear=[i for i in review.get('intervals',[]) if i['confidence']=='clear']
            if review.get('status')!='complete' or not (clear or review.get('outcome')=='absent'):
                continue
            archive=item['source_archive']
            if archive not in archives:
                archives[archive]=tarfile.open(args.root/archive)
            with archives[archive].extractfile(item['source_member']) as f:
                original=f.read()
            assert sha(original)==item['source_sha256']==review['source_sha256'], item['id']
            raw=subprocess.run([ensure_ffmpeg(),'-hide_banner','-loglevel','error','-nostdin',
                                '-i','pipe:0','-map','0:a:0','-ac','1','-ar',str(ANALYSIS_RATE),
                                '-f','f32le','pipe:1'],input=original,capture_output=True,check=True).stdout
            duration=len(raw)/4/ANALYSIS_RATE
            assert abs(duration-item['source_duration'])<0.01
            detections=[asdict(d) for d in detect_stream(io.BytesIO(raw),ANALYSIS_RATE)]
            passages=[]
            for i in clear:
                covered=sum(max(0,min(i['end'],d['end'])-max(i['start'],d['start'])) for d in detections)
                passages.append(dict(i,covered_seconds=covered,hit=covered>0))
            result={'id':item['id'],'species':item['species'],'review_revision':review['revision'],
                    'label':review['outcome'],'duration':duration,'source_sha256':sha(original),
                    'decoded_pcm_sha256':sha(raw),'detections':detections,'clear_passages':passages,
                    'detected_seconds':sum(d['end']-d['start'] for d in detections)}
            results.append(result)
            print(item['id'],item['species'],len(detections),'detections',flush=True)
    finally:
        for archive in archives.values(): archive.close()
    positives=[r for r in results if r['label']=='present']
    negatives=[r for r in results if r['label']=='absent']
    passages=[p for r in positives for p in r['clear_passages']]
    summary={'clear_passages':len(passages),'passages_hit':sum(p['hit'] for p in passages),
             'annotated_seconds':sum(p['end']-p['start'] for p in passages),
             'annotated_seconds_covered':sum(p['covered_seconds'] for p in passages),
             'none_heard_recordings':len(negatives),'none_heard_flagged':sum(bool(r['detections']) for r in negatives),
             'none_heard_seconds':sum(r['duration'] for r in negatives),
             'none_heard_detected_seconds':sum(r['detected_seconds'] for r in negatives)}
    (args.output/'results.json').write_text(json.dumps(dict(provenance=provenance,summary=summary,recordings=results),indent=2)+'\n')
    lines=['# Current detector against the completed waterfowl pilot','',
           f"Clear passages overlapped: **{summary['passages_hit']}/{len(passages)}**. Annotated audio covered: **{summary['annotated_seconds_covered']:.2f}/{summary['annotated_seconds']:.2f} seconds**.",'',
           f"Listener-negative recordings flagged: **{summary['none_heard_flagged']}/{len(negatives)}**; {summary['none_heard_detected_seconds']:.2f} detected seconds in {summary['none_heard_seconds']:.2f} seconds reviewed.",'',
           provenance['interpretation'],'',
           '## Per-recording comparison','',
           '| Recording | Human label / clear passage | Detector intervals (seconds) | Passage overlap |','|---|---|---|---|']
    for r in results:
        labels=', '.join(f"{p['start']:g}–{p['end']:g}" for p in r['clear_passages']) or 'None heard'
        detections=', '.join(f"{d['start']:g}–{d['end']:g}" for d in r['detections']) or 'None'
        overlap=', '.join(f"{p['covered_seconds']:.2f} s" for p in r['clear_passages']) or 'Not applicable'
        lines.append(f"| {r['species']} ({r['id']}) | {labels} | {detections} | {overlap} |")
    lines+=['','## Interpretation and reproducibility','',provenance['method'],'',
            'Any positive overlap counts as a hit; it does not imply accurate boundaries or complete passage coverage. Unmarked portions of positive recordings are not scored as negatives. Scores are screening periodicity values, not probabilities of wingbeats.', '',
            'Lesser Scaup (2–7 s, uncertain) and White-cheeked Pintail (1–3 s, faint) are excluded. Reviews and source audio are unchanged. No training, threshold tuning, or detector changes were performed. This small, selected development pilot does not estimate general field accuracy.', '',
            'The frozen review-snapshot.json and results.json retain labels, revisions, source and decoded hashes, detector file hashes, and all outputs. Investigate listener-negative detections with focused replay and spectrogram inspection; retain an unresolved category if the sound cannot be identified. Do not automatically convert these into negative training labels.']
    (args.output/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
