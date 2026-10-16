#!/usr/bin/env python3
"""Resolve historical paths through the collection migration table."""
import argparse,csv,os
from pathlib import Path

def resolve_path(value,root):
    archive,sep,member=value.partition('!')
    with (root/'catalogs/path-migrations.csv').open(newline='') as f:maps=list(csv.DictReader(f))
    for row in sorted(maps,key=lambda r:len(r['old_path']),reverse=True):
        old=row['old_path']
        if archive==old or archive.startswith(old+'/'):
            archive=row['new_path']+archive[len(old):];break
    return archive+(sep+member if sep else '')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('path');ap.add_argument('--root',type=Path,default=Path(os.environ.get('WINGBEAT_DATA_ROOT',Path(__file__).resolve().parents[2])));a=ap.parse_args()
    print(resolve_path(a.path,a.root))
