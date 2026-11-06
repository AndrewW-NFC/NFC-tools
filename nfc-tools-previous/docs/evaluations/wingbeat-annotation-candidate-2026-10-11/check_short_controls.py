"""Check new short windows on deterministic existing synthetic negatives."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_wingbeat_accompaniment import whistle, shaped_background
from test_wingbeat_localized_pulses import localized_noise
from nfc_tools.analyzers.wingbeat_accompaniment import accompaniment_features,screen_accompaniment,ANALYSIS_RATE
import numpy as np

def check(x):
    return [offset / ANALYSIS_RATE for offset in range(0,len(x)-ANALYSIS_RATE+1,6000)
            if screen_accompaniment(accompaniment_features(x[offset:offset+ANALYSIS_RATE])) is not None]
rows=[]
for frequency in [1532.1,2732.1,5432.1,7832.1]:
    for seed in range(5):
        for kind in ['tone','stationary','harmonics','sweep']:
            rows.append(dict(kind=kind,frequency=frequency,seed=seed,hits=check(whistle(seed,frequency,kind))))
for center in [4000,5000,7200]:
    for seed in range(5):
        rows.append(dict(kind='stationary-localized',center=center,seed=seed,hits=check(localized_noise(seed,center,pulsed=False))))
for center in [5400,6800]:
    for amp in [.03,.06,.1]:
        for seed in range(5):
            t=np.arange(2*ANALYSIS_RATE)/ANALYSIS_RATE
            x=.2*np.sin(2*np.pi*6100*t)*(.02+np.maximum(0,np.sin(2*np.pi*7*t))**4)+amp*shaped_background(seed,center,len(t))
            rows.append(dict(kind='stationary-shaped',center=center,amplitude=amp,seed=seed,hits=check(x)))
Path(sys.argv[1]).write_text(json.dumps(rows,indent=2))
print('Negative signals',len(rows),'flagged',sum(bool(r['hits']) for r in rows))
for r in rows:
    if r['hits']:print(r)
