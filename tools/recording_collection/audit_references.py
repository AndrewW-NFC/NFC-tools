#!/usr/bin/env python3
"""Read-only audit of stored local paths and HTML links in this collection/repo."""
import argparse,csv,json,os,zipfile
from resolve_path import resolve_path
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit

class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in {'src','href'} and v:self.links.append((tag,k,v))

def strings(o):
 if isinstance(o,str):yield o
 elif isinstance(o,dict):
  for v in o.values():yield from strings(v)
 elif isinstance(o,list):
  for v in o:yield from strings(v)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args()
 refs={};html=[];errors=[];files=0
 for scope in [a.root,a.repo]:
  for d,ds,fs in os.walk(scope):
   ds[:]=[n for n in ds if n not in {'.git','.venv','node_modules','__pycache__','migration-2026-10-16','taxonomy'} and not (Path(d)/n).is_symlink() and not (Path(d)/n).is_relative_to(a.root/'archive/change-history') and not (Path(d)/n).is_relative_to(a.root/'archive/reference-scripts')]
   for n in fs:
    p=Path(d)/n
    if p.name in {'reference-audit.json','path-migrations.csv'} or p.is_symlink() or p.suffix not in {'.json','.jsonl','.csv','.html'}:continue
    files+=1
    try:
     if p.suffix=='.html':
      parser=Links();parser.feed(p.read_text())
      for tag,attr,url in parser.links:
       u=urlsplit(url)
       if u.scheme not in {'','file'} or not u.path:continue
       if p.is_relative_to(a.repo/'src/nfc_tools/web/templates') and not u.scheme:continue
       target=Path(unquote(u.path)) if u.scheme=='file' else p.parent/unquote(u.path)
       html.append(dict(file=str(p),tag=tag,attribute=attr,url=url,target=str(target.resolve()),exists=target.exists()))
      continue
     if p.suffix=='.csv':
      with p.open(encoding='utf-8-sig',newline='') as f:
       for row in csv.reader(f):
        for s in row:
         if s.startswith(('/Volumes/T7/','/Users/andrewwhitacre/Desktop/ML__')):refs.setdefault(s,str(p))
     elif p.suffix=='.json':
      for s in strings(json.loads(p.read_text(encoding='utf-8-sig'))):
       if s.startswith(('/Volumes/T7/','/Users/andrewwhitacre/Desktop/ML__')):refs.setdefault(s,str(p))
     else:
      with p.open() as f:
       for line in f:
        for s in strings(json.loads(line)):
         if s.startswith(('/Volumes/T7/','/Users/andrewwhitacre/Desktop/ML__')):refs.setdefault(s,str(p))
    except (ValueError,UnicodeError) as e:errors.append(dict(file=str(p),error=str(e)))
 missing=[]; resolved=[]; archive_refs=0
 for p,f in refs.items():
  canonical=resolve_path(p,a.root);archive,sep,member=canonical.partition('!');exists=Path(archive).exists()
  if exists and sep:
   archive_refs+=1
   try:
    with zipfile.ZipFile(archive) as z:exists=member in z.namelist()
   except (ValueError,zipfile.BadZipFile):exists=False
  if not exists:missing.append(dict(path=p,resolved_path=canonical,first_reference=f))
  if canonical!=p:resolved.append(dict(path=p,resolved_path=canonical,exists=exists))
 report=dict(historical_path_resolutions=resolved,validated_archive_references=archive_refs,scanned_files=files,unique_absolute_paths=len(refs),missing_absolute_paths=missing,html_links=html,parse_errors=errors,scope=[str(a.root),str(a.repo)],notes='Checks complete absolute path values in CSV/JSON/JSONL and local HTML href/src targets. Uses migration mappings and validates zip!member references. Excludes migration artifacts and application web routes. Does not execute code or interpret free-text prose, binary databases, external applications or other repositories.')
 out=a.root/'catalogs/reference-audit.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(scanned_files=files,unique_absolute_paths=len(refs),missing_absolute_paths=len(missing),html_links=len(html),broken_html_links=sum(not r['exists'] for r in html),parse_errors=len(errors))))
 print(json.dumps(missing[:12],indent=2))
if __name__=='__main__':main()
