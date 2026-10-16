"""Read-only feature experiment. Candidates are not production detector changes."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile
import sys
import numpy as np
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.ffmpeg_locator import ensure_ffmpeg
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
from wingbeat_research_scan import _current_broadband_pass

VARIANTS=['baseline','brief_broadband','broadband_rhythm','spectral_flatness','three_pulses','lower_localized']

def merge(intervals):
    result=[]
    for start,end in sorted(intervals):
        if result and start<=result[-1][1]:result[-1][1]=max(end,result[-1][1])
        else:result.append([start,end])
    return result

def gates(b):
    limits={'peak_envelope':1e-4,'spectral_flatness':.12,'modulation':.25,'periodicity':.6,'repeat_periodicity':.35,'pulse_count':4,'coherent_bands':3,'band_energy_fraction':1e-4,'low_band_fraction':.005}
    return [k for k,v in limits.items() if b[k]<v]

def accepted(row, variant):
    b=w.WindowFeatures(**row['broad']); fs=[a.AccompanimentFeatures(**f) for f in row['accompaniment']]
    kind=row['kind']; near=kind in {'long','accompaniment'}
    baseline=(kind not in {'brief','accompaniment'} and _current_broadband_pass(b)) or a.screen_accompaniment(fs,allow_near_miss=near) is not None
    if baseline or variant=='baseline':return baseline
    if variant=='brief_broadband':return kind=='brief' and _current_broadband_pass(b)
    if variant=='broadband_rhythm':
        return kind not in {'brief','accompaniment'} and b.periodicity>=.5 and b.repeat_periodicity>=.25 and _current_broadband_pass(replace(b,periodicity=max(.6,b.periodicity),repeat_periodicity=max(.35,b.repeat_periodicity)))
    if variant=='spectral_flatness':
        fs=[replace(f,pulse_excess_flatness=max(.3,f.pulse_excess_flatness)) if f.pulse_excess_flatness>=.2 else f for f in fs]
    elif variant=='three_pulses':
        fs=[replace(f,pulse_count=4) if f.pulse_count==3 else f for f in fs]
    elif variant=='lower_localized':
        # Test applying the existing localized lobe support to lower search bands.
        fs=[replace(f,lower_hz=3500) if f.lower_hz<3500 else f for f in fs]
    return a.screen_accompaniment(fs,allow_near_miss=near) is not None

def work(job):
    raw=subprocess.check_output([ensure_ffmpeg(),'-v','error','-nostdin','-i',job['path'],'-map','0:a:0','-ac','1','-ar','24000','-f','f32le','-'])
    x=np.frombuffer(raw,dtype='<f4')
    if 'crop' in job:
        start,end=job['crop']; x=x[round(start*24000):round(end*24000)];raw=x.tobytes()
    rows=[]
    for start,samples,kind in w.analysis_windows(io.BytesIO(raw),24000):
        rows.append({'start':start,'end':start+len(samples)/24000,'kind':kind,
                     'broad':asdict(w.window_features(samples,24000)),
                     'accompaniment':[asdict(f) for f in a.accompaniment_features(samples)]})
    output={v:merge([[r['start'],r['end']] for r in rows if accepted(r,v)]) for v in VARIANTS}
    return dict(job,pcm_sha256=hashlib.sha256(raw).hexdigest(),duration=len(x)/24000,windows=rows,outputs=output)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['pilot','controls']);p.add_argument('output',type=Path);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    root=Path('/Volumes/T7/Wingbeats detector')
    snap=json.loads((root/'analysis-results/2026-10-16-waterfowl-pilot-detector/review-snapshot.json').read_text())
    jobs=[]
    with tempfile.TemporaryDirectory() as temp:
        if args.mode=='pilot':
            with tarfile.open(root/snap['batch']['records'][0]['source_archive']) as archive:
                for r in snap['batch']['records']:
                    review=snap['reviews'][r['id']]
                    if r['id'] in {'ml-435689831','ml-179948131'}:continue
                    raw=archive.extractfile(r['source_member']).read()
                    assert hashlib.sha256(raw).hexdigest()==r['source_sha256']
                    path=Path(temp)/(r['id']+'.wav');path.write_bytes(raw)
                    jobs.append({'id':r['id'],'dataset':'pilot','path':str(path),'species':r['species'],'review':review})
        else:
            prior=json.loads((root/'analysis-results/2026-10-13-insect-filter/results.json').read_text())
            for r in prior:
                if r['dataset'] in {'xc','fsd','reference'} or (r['dataset'] in {'insect','field'} and r.get('gain')==1 and r.get('padding')==0):
                    jobs.append({k:v for k,v in r.items() if k in {'id','dataset','path','label','target','crop','pcm_sha256','after'}})
            with zipfile.ZipFile(root/'audio-library/reference-recordings/suspected-false-positives/wav files with false positive WING sounds.zip') as z:
                for r in prior:
                    if r['dataset']=='discrete':
                        path=Path(temp)/('discrete-'+str(len(jobs))+'.wav');path.write_bytes(z.read(r['id']))
                        jobs.append(dict(id=r['id'],dataset='discrete',label='no',path=str(path),pcm_sha256=r['pcm_sha256'],after=r['after']))
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(work,j) for j in jobs]
            for n,f in enumerate(as_completed(futures),1):
                r=f.result()
                if 'after' in r:assert r['outputs']['baseline']==r['after'],r['id']
                expected=next(j.get('pcm_sha256') for j in jobs if j['id']==r['id'])
                if expected:assert r['pcm_sha256']==expected,r['id']
                (args.output/(args.mode+'-'+r['id'].replace('/','_')+'.json')).write_text(json.dumps(r))
                print(args.mode,n,'/',len(jobs),r['id'],flush=True)
if __name__=='__main__':main()
