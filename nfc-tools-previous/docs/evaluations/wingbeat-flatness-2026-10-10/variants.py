import json,sys
from pathlib import Path
import numpy as np
from run import task,merge,MODES
root=Path('/tmp/nfc-wingbeat-validation')
x=np.load(root/'audio-22.npy',mmap_mode='r')[3184*24000:3208*24000].copy()
results=[]
for gain in [.1,1,3]:
 for padding in [0,.25,.5,.75]:
  samples=np.r_[np.zeros(int(padding*24000),dtype='<f4'),x*gain].astype('<f4')
  p=root/'variant.npy';np.save(p,samples)
  r=task(('variant',str(p),0,len(samples)/24000));d={'gain':gain,'padding':padding}
  for m in MODES:d[m]=[[s-padding+3184,e-padding+3184] for s,e in merge(r['accepted'][m])]
  results.append(d)
  print(gain,padding,{m:bool(d[m]) for m in MODES},flush=True)
(root/'variants.json').write_text(json.dumps(results,indent=2))
