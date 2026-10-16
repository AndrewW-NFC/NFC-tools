#!/usr/bin/env python3
"""List or selectively extract cataloged recordings; never unpack the whole tar implicitly."""
import argparse,collections,csv,hashlib,json,os,tarfile,tempfile
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('action',choices=['summary','list','extract'])
 ap.add_argument('--root',type=Path,default=Path(os.environ.get('WINGBEAT_DATA_ROOT',Path(__file__).resolve().parents[2])))
 ap.add_argument('--source');ap.add_argument('--group');ap.add_argument('--id',action='append',dest='ids');ap.add_argument('--output',type=Path)
 a=ap.parse_args()
 with (a.root/'catalogs/recordings.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
 ids=set(a.ids or [])
 selected=[r for r in rows if (not a.source or r['source']==a.source) and (not a.group or r['training_group']==a.group) and (not ids or r['recording_id'] in ids)]
 if ids-set(r['recording_id'] for r in selected):ap.error('One or more requested IDs do not match the catalog/filter')
 if a.action=='summary':
  print(json.dumps({'recordings':len(selected),'groups':dict(collections.Counter(r['training_group'] for r in selected)),'families':dict(collections.Counter(r['family'] or 'unresolved' for r in selected))},indent=2));return
 if a.action=='list':
  for r in selected:print(r['recording_id']+'\t'+r['archive_member'])
  return
 if not (a.group or ids):ap.error('Extraction requires --group or --id')
 if not a.output:ap.error('Extraction requires --output')
 if not selected:ap.error('No matching recordings')
 archives={};destinations=[]
 try:
  for r in selected:
   dest=(a.output/r['source']/r['archive_member']).resolve()
   if not dest.is_relative_to(a.output.resolve()):raise ValueError('Unsafe archive destination')
   if dest.exists():raise FileExistsError(dest)
   destinations.append((r,dest))
  for r,dest in destinations:
   path=(a.root/r['archive_path']).resolve()
   if path not in archives:archives[path]=tarfile.open(path,'r:')
   archive=archives[path];member=archive.getmember(r['archive_member']);assert member.isfile()
   dest.parent.mkdir(parents=True,exist_ok=True)
   fd,tmp=tempfile.mkstemp(prefix='.extract-',dir=dest.parent);h=hashlib.sha256();size=0
   try:
    with os.fdopen(fd,'wb') as out,archive.extractfile(member) as src:
     for b in iter(lambda:src.read(4*1024*1024),b''):out.write(b);h.update(b);size+=len(b)
    assert h.hexdigest()==r['sha256'] and size==int(r['size_bytes'])
    # Hard-link commits without overwriting a destination created concurrently.
    os.link(tmp,dest);print(str(dest))
   finally:
    Path(tmp).unlink(missing_ok=True)
 finally:
  for archive in archives.values():archive.close()

if __name__=='__main__':main()
