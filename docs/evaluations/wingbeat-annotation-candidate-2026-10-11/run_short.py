"""Compute only added short-window intervals; merge with hashed saved baseline.

Use the same CLI as run.py. The output 'after' contains ONLY new-pass hits;
combine it with the saved production intervals after checking PCM hashes.
"""
import numpy as np
import run
from nfc_tools.analyzers import wingbeat_accompaniment as a


def task(job):
    key,path,start,stop=job
    x=np.load(path,mmap_mode='r');accepted=[];checks=0
    for offset in range(int(start*24000),min(int(stop*24000),len(x)-24000+1),6000):
        samples=x[offset:offset+24000]
        if a.screen_accompaniment(a.accompaniment_features(samples)) is not None:
            accepted.append([offset/24000,offset/24000+1])
        checks+=1
    return dict(key=key,start=start,checks=checks,before=[],after=accepted,recovered=[])


if __name__=='__main__':
    run.task=task
    run.main()
