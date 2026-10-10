from __future__ import annotations
import csv,hashlib,io,json,subprocess,zipfile,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict,replace
import numpy as np
import nfc_tools.analyzers.wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import analysis_windows,window_features,screen_window
from nfc_tools.ffmpeg_locator import ensure_ffmpeg
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from wingbeat_research_scan import _current_broadband_pass
OUT=Path('/tmp/nfc-wingbeat-validation')
MODES=['current','flat_013','flat_010','conditional_013']

def decode(path):
 b=subprocess.check_output([ensure_ffmpeg(),'-v','error','-nostdin','-i',str(path),'-ac','1','-ar','24000','-f','f32le','-'])
 return np.frombuffer(b,dtype='<f4')

def merge(windows):
 out=[]
 for st,en in sorted(windows):
  if out and st<=out[-1][1]:out[-1][1]=max(out[-1][1],en)
  else:out.append([st,en])
 return out

def task(job):
 key,path,start,stop=job
 x=np.load(path,mmap_mode='r');n=len(x)
 # Include lookahead but yield only starts within the owned range; preserve end-of-file tails.
 samples=x[int(start*24000):min(n,int((stop+2)*24000))]
 accepted={m:[] for m in MODES};fallback=[];checked=0;count=0
 for local,s,k in analysis_windows(io.BytesIO(samples.astype('<f4').tobytes()),24000):
  st=start+local
  if st>=stop:break
  count+=1;en=st+len(s)/24000
  broad=k!='accompaniment' and _current_broadband_pass(window_features(s,24000))
  fs=a.accompaniment_features(s);near=k!='standard'
  base=a.screen_accompaniment(fs,allow_near_miss=near) is not None
  # Use the authoritative screen with only the flatness value substituted:
  # changing value by ratio is equivalent to changing cutoff 0.30 -> 0.13/0.10.
  f13=a.screen_accompaniment([replace(f,pulse_excess_flatness=f.pulse_excess_flatness*.30/.13) for f in fs],allow_near_miss=near) is not None
  f10=a.screen_accompaniment([replace(f,pulse_excess_flatness=f.pulse_excess_flatness*3) for f in fs],allow_near_miss=near) is not None
  cond=a.screen_accompaniment([replace(f,pulse_excess_flatness=f.pulse_excess_flatness*.30/.13) for f in fs if f.periodicity>=.70 and f.repeat_periodicity>=.65 and f.ridge_prominence>=16],allow_near_miss=near) is not None
  decisions=[broad or base,broad or f13,broad or f10,broad or base or cond]
  for m,yes in zip(MODES,decisions):
   if yes:accepted[m].append([st,en])
  if cond and not (broad or base):fallback.append([st,en])
  if count<=2:
   assert (screen_window(s,24000,pass_kind=k) is not None)==decisions[0]
   checked+=1
 return dict(key=key,start=start,stop=stop,windows=count,checks=checked,accepted=accepted,fallback=fallback)

def main():
 OUT.mkdir(parents=True, exist_ok=True)
 fixtures=[]
 for p in sorted(Path('/Volumes/T7/Wingbeats detector/Confirmed species wing sounds').glob('*.mp3')):fixtures.append(('positive',p))
 with zipfile.ZipFile('/Volumes/T7/Wingbeats detector/wav files with false positive WING sounds.zip') as z:
  for name in z.namelist():
   if name.startswith('__MACOSX') or not name.lower().endswith('.wav'):continue
   p=OUT/'discrete'/Path(name).name;p.parent.mkdir(exist_ok=True);p.write_bytes(z.read(name));fixtures.append(('discrete-negative',p))
 fixtures.append(('site-hour',Path('/Volumes/T7/NFC recordings/2026-10-09/audio/Wingbeats/015_NFC_CIVIL_MORNING_2026-10-10_05-18-13.wav')))
 manifest=[];jobs=[]
 for idx,(group,p) in enumerate(fixtures):
  x=decode(p);cache=OUT/f'audio-{idx}.npy';np.save(cache,x)
  key=f'{idx:02d}';seconds=len(x)/24000
  manifest.append(dict(key=key,group=group,path=str(p),seconds=seconds,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pcm_sha256=hashlib.sha256(x.tobytes()).hexdigest()))
  if group=='site-hour':
   for start in range(0,int(np.ceil(seconds)),60):jobs.append((key,str(cache),start,min(start+60,seconds)))
  else:jobs.append((key,str(cache),0,seconds))
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
 results=[]
 with ProcessPoolExecutor(max_workers=4) as pool:
  future={pool.submit(task,j):j for j in jobs}
  with (OUT/'progress.jsonl').open('w') as log:
   for fut in as_completed(future):
    r=fut.result();results.append(r);log.write(json.dumps(r)+'\n');log.flush()
    print(f"completed {len(results)}/{len(jobs)}: {r['key']} {r['start']:.0f}s",flush=True)
 output=[]
 for f in manifest:
  rr=[r for r in results if r['key']==f['key']]
  d=dict(f)
  for m in MODES:d[m]=merge([v for r in rr for v in r['accepted'][m]])
  d['conditional_extra_windows']=sorted([v for r in rr for v in r['fallback']]);output.append(d)
 (OUT/'results.json').write_text(json.dumps(output,indent=2))
 print(json.dumps([{k:v for k,v in d.items() if k in ['group','path']+MODES} for d in output],indent=2),flush=True)
if __name__=='__main__':main()
