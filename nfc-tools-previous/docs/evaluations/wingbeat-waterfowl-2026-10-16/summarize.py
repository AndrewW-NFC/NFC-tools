"""Summarize cached candidate experiments without touching annotations."""
import json
from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experiment import gates,VARIANTS
from rescore import EXTRA
VARIANTS = VARIANTS + EXTRA
from nfc_tools.analyzers import wingbeat_accompaniment as a
ROOT=Path('/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-diagnostics')

def overlap(ds, intervals):
 return sum(max(0,min(end,i['end'])-max(start,i['start'])) for start,end in ds for i in intervals)

def failed(f,kind):
 x=a.AccompanimentFeatures(**f)
 checks={'amplitude':x.peak_envelope>=1e-4,'pulse_count':x.pulse_count>=4,'rhythm':a.accompaniment_rhythm_passes(x,allow_near_miss=kind in {'long','accompaniment'}),'modulation':x.modulation>=.25,'noise_coherence':x.noise_coherence>=.4,'noise_contrast':x.noise_contrast>=.15,'noise_ratio':x.noise_ratio>=.005,'ridge_share':x.ridge_share>=.001,'residual_bins':x.residual_bins>=20,'spectral_support':a.accompaniment_spectral_support(x) or a.localized_pulse_support(x)}
 return [k for k,v in checks.items() if not v]

def main():
 rows=[json.loads(p.read_text()) for p in sorted((ROOT/'features').glob('*.json'))]
 pilot=[r for r in rows if r['dataset']=='pilot']
 out={}
 for v in VARIANTS:
  ps=[r for r in pilot if r['review']['outcome']=='present']
  out[v]={'pilot_hits':sum(overlap(r['outputs'][v],[i for i in r['review']['intervals'] if i['confidence']=='clear'])>0 for r in ps),'pilot_covered_seconds':sum(overlap(r['outputs'][v],[i for i in r['review']['intervals'] if i['confidence']=='clear']) for r in ps),'controls':{}}
  for dataset in sorted({r['dataset'] for r in rows if r['dataset']!='pilot'}):
   rs=[r for r in rows if r['dataset']==dataset]
   out[v]['controls'][dataset]={'files':len(rs),'flagged':sum(bool(r['outputs'][v]) for r in rs),'changed':sum(r['outputs'][v]!=r['outputs']['baseline'] for r in rs),'newly_flagged':sum(bool(r['outputs'][v]) and not r['outputs']['baseline'] for r in rs),'added_seconds':sum(sum(b-a for a,b in r['outputs'][v])-sum(b-a for a,b in r['outputs']['baseline']) for r in rs),'changed_ids':[r['id'] for r in rs if r['outputs'][v]!=r['outputs']['baseline']]}
  for label in ['yes','no']:
   rs=[r for r in rows if r['dataset']=='xc' and r['label']==label]
   out[v]['controls']['xc_'+label]={'files':len(rs),'flagged':sum(bool(r['outputs'][v]) for r in rs),'newly_flagged':sum(bool(r['outputs'][v]) and not r['outputs']['baseline'] for r in rs),'added_seconds':sum(sum(b-a for a,b in r['outputs'][v])-sum(b-a for a,b in r['outputs']['baseline']) for r in rs),'changed_ids':[r['id'] for r in rs if r['outputs'][v]!=r['outputs']['baseline']]}
   if label=='yes':
    out[v]['controls']['xc_yes']['passages_hit']=sum(overlap(r['outputs'][v],[{'start':r['target'][0],'end':r['target'][1]}])>0 for r in rs)
    out[v]['controls']['xc_yes']['covered_seconds']=sum(overlap(r['outputs'][v],[{'start':r['target'][0],'end':r['target'][1]}]) for r in rs)
  out[v]['pilot']=[{'id':r['id'],'species':r['species'],'intervals':r['outputs'][v],'coverage':overlap(r['outputs'][v],[i for i in r['review']['intervals'] if i['confidence']=='clear'])} for r in pilot]
 diagnostics=[]
 for r in pilot:
  intervals=[i for i in r['review']['intervals'] if i['confidence']=='clear']
  if not intervals or overlap(r['outputs']['baseline'],intervals)>0:continue
  windows=[w for w in r['windows'] if overlap([[w['start'],w['end']]],intervals)>=(w['end']-w['start'])*.5]
  nearest=[]
  for w in windows:
   for f in w['accompaniment']:
    errors=failed(f,w['kind']);nearest.append({'start':w['start'],'end':w['end'],'kind':w['kind'],'failed':errors,'features':f})
  nearest.sort(key=lambda x:(len(x['failed']),-x['features']['periodicity']))
  broad=sorted([{'start':w['start'],'end':w['end'],'failed':gates(w['broad']),'features':w['broad']} for w in windows if w['kind'] not in {'brief','accompaniment'}],key=lambda x:(len(x['failed']),-x['features']['periodicity']))
  diagnostics.append({'id':r['id'],'species':r['species'],'intervals':intervals,'nearest_accompaniment':nearest[:3],'nearest_broadband':broad[:3], 'accompaniment_failures':dict(Counter(k for w in windows for f in w['accompaniment'] for k in failed(f,w['kind'])))})
 (ROOT/'candidate-results.json').write_text(json.dumps(out,indent=2)+'\n')
 (ROOT/'miss-diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
 print(json.dumps({k:{'hits':v['pilot_hits'],'covered':v['pilot_covered_seconds'],'controls':v['controls']} for k,v in out.items()},indent=2))
 for d in diagnostics:
  n=d['nearest_accompaniment'][0];print(d['species'],n['start'],n['end'],n['failed'],{k:round(n['features'][k],3) for k in ['periodicity','repeat_periodicity','pulse_count','pulse_excess_flatness','noise_coherence','ridge_prominence','low_band_fraction']})
if __name__=='__main__':main()
