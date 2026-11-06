"""Verify shipped detector on original audio, frozen controls and gain/offset variants."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile

import numpy as np
from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.ffmpeg_locator import ensure_ffmpeg
from experiment import merge

ROOT=Path('/Volumes/T7/Wingbeats detector')
OUT=ROOT/'analysis-results/2026-10-16-waterfowl-release'
FEATURES=ROOT/'analysis-results/2026-10-16-waterfowl-diagnostics/features'

def expected(row):
    hits=[]
    for win in row['windows']:
        fs=[a.AccompanimentFeatures(**f) for f in win['accompaniment']]
        from wingbeat_research_scan import _current_broadband_pass
        broad=win['kind'] not in {'brief','accompaniment'} and _current_broadband_pass(w.WindowFeatures(**win['broad']))
        if broad or a.screen_accompaniment(fs,allow_near_miss=win['kind'] in {'long','accompaniment'}) is not None:
            hits.append([win['start'],win['end']])
    return merge(hits)

def run(job):
    raw=subprocess.check_output([ensure_ffmpeg(),'-v','error','-nostdin','-i',job['path'],'-map','0:a:0','-ac','1','-ar','24000','-f','f32le','-'])
    x=np.frombuffer(raw,dtype='<f4')
    if 'crop' in job:
        start,end=job['crop'];x=x[round(start*24000):round(end*24000)]
    assert hashlib.sha256(x.tobytes()).hexdigest()==job['pcm_sha256'],job['id']
    padding=job.get('padding',0);gain=job.get('gain',1)
    x=np.r_[np.zeros(round(padding*24000)),x*gain].astype('<f4')
    after=[[d.start,d.end] for d in w.detect_stream(io.BytesIO(x.tobytes()),24000)]
    if 'expected' in job:assert after==job['expected'],job['id']
    return dict(job,after=after,variant_pcm_sha256=hashlib.sha256(x.tobytes()).hexdigest())

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    snapshot=json.loads((ROOT/'analysis-results/2026-10-16-waterfowl-pilot-detector/review-snapshot.json').read_text())
    jobs=[]
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(ROOT/snapshot['batch']['records'][0]['source_archive']) as archive:
            for r in snapshot['batch']['records']:
                if r['id'] in {'ml-435689831','ml-179948131'}:continue
                raw=archive.extractfile(r['source_member']).read();assert hashlib.sha256(raw).hexdigest()==r['source_sha256']
                path=Path(tmp)/(r['id']+'.wav');path.write_bytes(raw)
        with zipfile.ZipFile(ROOT/'audio-library/reference-recordings/suspected-false-positives/wav files with false positive WING sounds.zip') as z:
            for feature in sorted(FEATURES.glob('*.json')):
                row=json.loads(feature.read_text());job={k:row[k] for k in ['id','dataset','path','pcm_sha256']}
                job.update(before=row['outputs']['baseline'],expected=expected(row))
                for k in ['crop','target','label','review','species']:
                    if k in row:job[k]=row[k]
                if row['dataset']=='pilot':job['path']=str(Path(tmp)/(row['id']+'.wav'))
                if row['dataset']=='discrete':
                    path=Path(tmp)/('discrete-'+str(len(jobs))+'.wav');path.write_bytes(z.read(row['id']));job['path']=str(path)
                jobs.append(job)
            for base in list(jobs):
                if base['id'] not in {'ml-211014411','ml-645008811'} and base['dataset'] not in {'insect','field'}:continue
                for gain in [.1,1,3]:
                    for padding in [0,.25,.5,.75]:
                        if gain==1 and padding==0:continue
                        job=dict(base,id=f"{base['id']}@{gain}x+{padding}",original_id=base['id'],gain=gain,padding=padding)
                        job.pop('expected');job.pop('before');jobs.append(job)
            results=[]
            with ProcessPoolExecutor(max_workers=4) as pool:
                for n,future in enumerate(as_completed([pool.submit(run,j) for j in jobs]),1):
                    result=future.result();results.append(result)
                    if n%10==0:print(n,'/',len(jobs),flush=True)
            results.sort(key=lambda r:r['id'])
            (OUT/'verified-results.json').write_text(json.dumps(results,indent=2)+'\n')
            print('Verified',len(results),'real streaming runs',flush=True)
if __name__=='__main__':main()
