"""Additional single-gate diagnostics, scored on frozen feature measurements."""
import json
from dataclasses import replace
from pathlib import Path
from experiment import accepted,merge
from nfc_tools.analyzers import wingbeat_accompaniment as a

EXTRA=['accompaniment_rhythm','weak_ridge','tonal_support','supported_flatness']

def extra(row,variant):
 if accepted(row,'baseline'):return True
 fs=[a.AccompanimentFeatures(**f) for f in row['accompaniment']]
 if variant=='accompaniment_rhythm':
  # A moderate, explicit relaxation of both repeat thresholds; other gates stay.
  return any(f.periodicity>=.45 and f.repeat_periodicity>=.25
             and f.peak_envelope>=1e-4 and f.pulse_count>=4
             and f.modulation>=.25 and f.noise_coherence>=.40
             and f.noise_contrast>=.15 and f.noise_ratio>=.005
             and f.ridge_share>=.001 and f.residual_bins>=20
             and (a.accompaniment_spectral_support(f) or a.localized_pulse_support(f))
             for f in fs)
 elif variant=='weak_ridge':
  fs=[replace(f,ridge_share=.001) if .0005<=f.ridge_share<.001 else f for f in fs]
 elif variant=='supported_flatness':
  # Lower excess-flatness only with a prominent ridge, strong second repeat,
  # and synchronized residual energy; compare against unconditional lowering.
  fs=[replace(f,pulse_excess_flatness=max(.3,f.pulse_excess_flatness)) if f.pulse_excess_flatness>=.2 and f.ridge_prominence>=16 and f.repeat_periodicity>=.5 and f.noise_coherence>=.5 else f for f in fs]
 elif variant=='tonal_support':
  # Diagnostic for strong, repeating narrowband candidates: preserve amplitude,
  # rhythm, residual-energy and synchrony checks, plus require an actual ridge.
  fs=[replace(f,pulse_excess_flatness=max(.3,f.pulse_excess_flatness)) if f.ridge_prominence>=16 and f.periodicity>=.7 and f.repeat_periodicity>=.5 and f.noise_coherence>=.7 else f for f in fs]
 return a.screen_accompaniment(fs,allow_near_miss=row['kind'] in {'long','accompaniment'}) is not None

def main():
 root=Path('/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-diagnostics/features')
 for p in root.glob('*.json'):
  d=json.loads(p.read_text())
  for v in EXTRA:
   d['outputs'][v]=merge([[r['start'],r['end']] for r in d['windows'] if extra(r,v)])
  p.write_text(json.dumps(d))
if __name__=='__main__':main()
