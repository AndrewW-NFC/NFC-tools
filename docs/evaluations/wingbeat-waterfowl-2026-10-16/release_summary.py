"""Assert release acceptance and publish compact results without source audio."""
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT=Path('/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-release')
DEST=Path(__file__).resolve().parent


def overlap(detections,targets):
    return sum(max(0,min(b,d)-max(a,c)) for a,b in detections for c,d in targets)


def main():
    rows=json.loads((ROOT/'verified-results.json').read_text())
    assert len(rows)==309
    base=[r for r in rows if 'original_id' not in r]
    assert len(base)==243
    for r in base:
        assert all(abs(overlap(r['after'],[[s,e]])-(e-s))<1e-6 for s,e in r['before']),r['id']
    targets={'ml-211014411':[22,24],'ml-645008811':[28,30]}
    variants={}
    for id,target in targets.items():
        selected=[r for r in rows if r.get('original_id',r['id'])==id]
        assert len(selected)==12
        coverages=[overlap(r['after'],[[target[0]+r.get('padding',0),target[1]+r.get('padding',0)]]) for r in selected]
        assert all(c>0 for c in coverages),(id,coverages)
        variants[id]={'variants':12,'passes':12,'minimum_overlap_seconds':min(coverages)}
    insect=[r for r in rows if r['dataset']=='insect'];assert len(insect)==12 and not any(r['after'] for r in insect)
    field=[r for r in rows if r['dataset']=='field'];assert len(field)==36 and all(r['after'] for r in field)
    pilot=[r for r in base if r['dataset']=='pilot']
    assert not any(r['after'] for r in pilot if r['id'] in {'ml-219909091','ml-643020090','ml-611676676'})
    p=[]
    for r in pilot:
        clear=[[i['start'],i['end']] for i in r['review']['intervals'] if i['confidence']=='clear']
        p.append(dict(id=r['id'],species=r['species'],clear_intervals=clear,before=r['before'],after=r['after'],covered_before=overlap(r['before'],clear),covered_after=overlap(r['after'],clear)))
    controls={}
    for group in ['xc_yes','xc_no','fsd','discrete','reference','insect','field']:
        rs=[r for r in base if (r['dataset']=='xc' and r['label']==group[3:]) or r['dataset']==group]
        controls[group]={'recordings':len(rs),'flagged_before':sum(bool(r['before']) for r in rs),'flagged_after':sum(bool(r['after']) for r in rs),'additional_detection_seconds':sum(sum(b-a for a,b in r['after'])-sum(b-a for a,b in r['before']) for r in rs),'newly_flagged_ids':[r['id'] for r in rs if r['after'] and not r['before']]}
        if group=='xc_yes':
            controls[group]['passages_before']=sum(overlap(r['before'],[r['target']])>0 for r in rs)
            controls[group]['passages_after']=sum(overlap(r['after'],[r['target']])>0 for r in rs)
    summary={'actual_streaming_runs':309,'base_dataset_counts':dict(Counter(r['dataset'] for r in base)),'requested_sample_variants':variants,'insect_variants_rejected':12,'field_variants_retained':36,'pilot_passages_before':sum(r['covered_before']>0 for r in p),'pilot_passages_after':sum(r['covered_after']>0 for r in p),'pilot_seconds_before':sum(r['covered_before'] for r in p),'pilot_seconds_after':sum(r['covered_after'] for r in p),'pilot_annotated_seconds':74,'controls':controls,'pilot':p}
    sources=[Path('src/nfc_tools/analyzers/wingbeats.py'),Path('src/nfc_tools/analyzers/wingbeat_accompaniment.py'),Path('tools/wingbeat_research_scan.py')]
    summary['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (DEST/'release-results.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'pilot','source_sha256'}},indent=2))

if __name__=='__main__':main()
