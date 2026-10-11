"""Exercise the candidate on existing audio controls without changing tests."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
import candidate
from test_wingbeat_accompaniment import whistle
from test_wingbeat_localized_pulses import localized_noise
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.analyzers.wingbeat_accompaniment import ANALYSIS_RATE

rows=[]
for frequency in [1532.1,2732.1,5432.1,7832.1]:
    for seed in range(5):
        for kind in ['accompanied','tone','stationary','harmonics','sweep']:
            x=whistle(seed,frequency,kind)
            rows.append(dict(group=kind,frequency=frequency,seed=seed,
                baseline=w.screen_window(x,ANALYSIS_RATE) is not None,
                candidate=candidate.screen_window(x,ANALYSIS_RATE) is not None))
for center in [4000,5000,7200]:
    for seed in range(5):
        x=localized_noise(seed,center)
        rows.append(dict(group='localized',center=center,seed=seed,
            baseline=w.screen_window(x,ANALYSIS_RATE) is not None,
            candidate=candidate.screen_window(x,ANALYSIS_RATE) is not None))
Path(sys.argv[1]).write_text(json.dumps(rows,indent=2))
for group in sorted({r['group'] for r in rows}):
    selected=[r for r in rows if r['group']==group]
    print(group,len(selected),sum(r['baseline'] for r in selected),sum(r['candidate'] for r in selected))
