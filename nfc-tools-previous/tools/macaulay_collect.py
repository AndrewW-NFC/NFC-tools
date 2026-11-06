"""Conservative, export-first Macaulay research collector (see docs/macaulay-collector.md)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_SEARCH = 'https://search.macaulaylibrary.org/catalog?tag=flying_flight,non_vocal&mediaType=audio'
DEFAULT_TERMS = ['wing', 'fly', 'fight', 'beat']


def now():
    return datetime.now(timezone.utc).isoformat()


def key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def field(row, *names):
    normalized = {key(k): v for k, v in row.items() if k is not None}
    return next((normalized[key(n)] for n in names if normalized.get(key(n))), '')


def asset_id(value):
    match = re.fullmatch(r'(?:ML\s*)?(\d+)', value.strip(), re.IGNORECASE)
    if not match:
        match = re.search(r'/asset/(\d+)(?:[/?.#]|$)', value)
    if not match:
        raise ValueError(f'Unrecognized catalog number: {value!r}')
    return match[1]


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


class Page(HTMLParser):
    """Preserve all source HTML separately; expose dt/dd, meta, JSON and visible text."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.audio, self.meta, self.structured = [], [], [], [], []
        self.fields = {}
        self.capture = None
        self.label = ''
        self.buffer = []
        self.script = None
        self.hidden = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            self.script = [attrs, []]
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('dt', 'dd'):
            self.capture, self.buffer = tag, []
        if tag == 'meta':
            self.meta.append(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs)
        if tag in ('audio', 'source') and attrs.get('src'):
            self.audio.append(attrs['src'])

    def handle_endtag(self, tag):
        if tag == self.capture:
            value = ' '.join(' '.join(self.buffer).split())
            if tag == 'dt':
                self.label = value
            elif self.label:
                self.fields.setdefault(self.label, []).append(value)
            self.capture = None
        if tag == 'script' and self.script:
            attrs, parts = self.script
            if 'json' in attrs.get('type', '') or attrs.get('id') == '__NEXT_DATA__':
                try:
                    self.structured.append(json.loads(''.join(parts)))
                except ValueError:
                    pass
            self.script = None
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if self.script:
            self.script[1].append(data)
        if not self.hidden:
            self.parts.append(data)
            if self.capture:
                self.buffer.append(data)

    @property
    def text(self):
        return '\n'.join(p.strip() for p in self.parts if p.strip())


def parse_page(html, ident):
    if any(s in html.casefold() for s in ('making sure you', 'anubis-challenge', 'cf-chl-')):
        raise RuntimeError('Bot verification page received; stopping without bypassing it.')
    p = Page(html)
    notes = '\n'.join(v for k, values in p.fields.items() if key(k) == 'medianotes' for v in values)
    row = {k: '\n'.join(v) for k, v in p.fields.items()}
    return {
        'media_notes': notes,
        'species': field(row, 'Species', 'Common name'),
        'recordist': field(row, 'Recordist', 'Contributor'),
        'location': field(row, 'Location', 'Locality'),
        'audio_url': next((u for u in p.audio if f'/asset/{ident}/' in u), ''),
        'page_fields': p.fields, 'page_meta': p.meta, 'page_json': p.structured,
        'page_text': p.text,
    }


def matches(notes, terms):
    result = []
    for term in terms:
        hits = list(re.finditer(re.escape(term), notes, re.IGNORECASE))
        if hits:
            result.append({'term': term, 'snippets': [notes[max(0, m.start()-65):m.end()+65] for m in hits]})
    return result


class PoliteClient:
    def __init__(self, contact, delay=10, client=None):
        self.delay = max(5, delay)
        self.agent = f'MacaulayWingbeatCollector/0.1 ({contact})'
        self.client = client or httpx.Client(timeout=60, headers={'User-Agent': self.agent})
        self.last = 0.0
        self.robots = {}

    def pause(self, minimum=0):
        time.sleep(max(0, self.last + max(self.delay, minimum) + random.uniform(0, 2) - time.monotonic()))
        self.last = time.monotonic()

    def request(self, url, stream=False, robots=True):
        # Re-check robots on redirects, including cross-host CDN redirects.
        for _ in range(6):
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Only HTTPS URLs without credentials are supported.')
            origin = f'{parsed.scheme}://{parsed.netloc}'
            if robots:
                if origin not in self.robots:
                    response = self.request(origin + '/robots.txt', robots=False)
                    rules = RobotFileParser()
                    if response.status_code == 404:
                        rules.parse([])
                    else:
                        response.raise_for_status()
                        if '<html' in response.text.casefold():
                            raise RuntimeError('robots.txt returned HTML; refusing to guess crawl rules.')
                        rules.parse(response.text.splitlines())
                    self.robots[origin] = rules
                rules = self.robots[origin]
                if not rules.can_fetch(self.agent, url):
                    raise RuntimeError(f'robots.txt disallows {url}. Use a CSV export or local saved pages.')
                self.delay = max(self.delay, rules.crawl_delay(self.agent) or 0)
            for attempt in range(4):
                self.pause()
                try:
                    response = self.client.send(self.client.build_request('GET', url), stream=stream)
                except httpx.TransportError:
                    if attempt == 3:
                        raise
                    self.pause(30 * 2**attempt)
                    continue
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
                retry = response.headers.get('Retry-After', '')
                response.close()
                if attempt == 3:
                    raise RuntimeError(f'Repeated HTTP {response.status_code}; stopped at {url}')
                try:
                    seconds = float(retry)
                except ValueError:
                    try:
                        seconds = parsedate_to_datetime(retry).timestamp() - time.time()
                    except (ValueError, TypeError, OverflowError):
                        seconds = 0
                self.pause(max(seconds, 30 * 2**attempt))
            if response.is_redirect:
                target = urljoin(url, response.headers['location'])
                response.close()
                url = target
                continue
            if response.status_code in (401, 403):
                response.close()
                raise RuntimeError(f'HTTP {response.status_code}: access denied at {url}; stopped.')
            if not (not robots and response.status_code == 404):
                response.raise_for_status()
            return response
        raise RuntimeError('Too many redirects')


def download(client, record, folder):
    destination = folder / f"ML{record['asset_id']}.mp3"
    previous = record.get('download', {})
    if destination.exists() and previous.get('sha256') == digest(destination):
        return
    response = client.request(record['audio_url'], stream=True)
    tmp = destination.with_suffix('.mp3.part')
    size, checksum = 0, hashlib.sha256()
    try:
        mime = response.headers.get('content-type', '').split(';')[0].strip().lower()
        if mime not in ('audio/mpeg', 'audio/mp3'):
            raise RuntimeError(f'Expected MP3, received {mime!r}; no audio saved.')
        with tmp.open('wb') as out:
            for chunk in response.iter_bytes():
                out.write(chunk)
                checksum.update(chunk)
                size += len(chunk)
        expected = response.headers.get('content-length')
        if size == 0 or (expected and not response.headers.get('content-encoding') and size != int(expected)):
            raise RuntimeError('Empty or incomplete audio download')
        with tmp.open('rb') as audio:
            prefix = audio.read(3)
        if not (prefix == b'ID3' or (len(prefix) >= 2 and prefix[0] == 255 and prefix[1] & 224 == 224)):
            raise RuntimeError('Response does not have an MP3 header; no audio saved.')
        tmp.replace(destination)
        record['download'] = {'path': str(destination), 'bytes': size, 'sha256': checksum.hexdigest(),
                              'retrieved_at': now(), 'final_url': str(response.url),
                              'headers': dict(response.headers)}
    finally:
        response.close()
        tmp.unlink(missing_ok=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_export(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for line, row in enumerate(reader, 2):
            value = field(row, 'ML Catalog Number', 'Catalog Number', 'ML Number', 'Asset ID', 'Asset URL')
            try:
                ident = asset_id(value)
            except ValueError as exc:
                raise ValueError(f'{path}:{line}: {exc}; columns: {reader.fieldnames}') from exc
            yield ident, row


def export_reports(root, records):
    columns = ['ML Catalog Number', 'species', 'recordist', 'location', 'media_notes',
               'asset_url', 'matched_terms', 'review_status', 'citation']
    for name, selected in [('index.csv', records), ('candidates.csv', [r for r in records if r['matches']])]:
        tmp = root / (name + '.tmp')
        with tmp.open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for r in selected:
                writer.writerow({**{k: r.get(k, '') for k in columns}, 'ML Catalog Number': 'ML'+r['asset_id'],
                                 'matched_terms': ', '.join(m['term'] for m in r['matches'])})
        tmp.replace(root / name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Official search-result metadata export')
    parser.add_argument('--html-dir', type=Path, help='Saved asset pages named ML123.html or 123.html')
    parser.add_argument('--search-url', help='Attempt HTML discovery; robots rules may block it')
    parser.add_argument('--fetch-pages', action='store_true', help='Enrich catalog entries over HTTP if allowed')
    parser.add_argument('--download', action='store_true', help='Download matching MP3s; use with permitted media')
    parser.add_argument('--contact', help='Email or project URL for descriptive User-Agent')
    parser.add_argument('--out', type=Path, default=Path('research/macaulay-collection'))
    parser.add_argument('--terms', nargs='+', default=DEFAULT_TERMS, help='Case-insensitive note substrings; replaces defaults')
    parser.add_argument('--delay', type=float, default=10, help='Seconds between requests, plus jitter; minimum 5')
    parser.add_argument('--limit', type=int, default=100, help='Maximum assets processed this run')
    args = parser.parse_args(argv)
    if not (args.csv or args.html_dir or args.search_url):
        parser.error('Provide --csv, --html-dir, or --search-url.')
    if args.limit < 1 or not all(t.strip() for t in args.terms):
        parser.error('Limit and search terms must be nonempty/positive.')
    if (args.fetch_pages or args.download or args.search_url) and not args.contact:
        parser.error('Network operations require --contact EMAIL_OR_PROJECT_URL.')
    root = args.out.resolve()
    for sub in ('metadata', 'pages', 'audio'):
        (root / sub).mkdir(parents=True, exist_ok=True)
    client = PoliteClient(args.contact, args.delay) if args.contact else None
    sources = {}
    if args.csv:
        for ident, row in read_export(args.csv):
            sources.setdefault(ident, []).append(row)
    local = {}
    if args.html_dir:
        for path in sorted(args.html_dir.glob('*.html')):
            ident = asset_id(path.stem)
            local[ident] = path
            sources.setdefault(ident, [])
    discovery = 'export_or_saved_pages'
    if args.search_url:
        response = client.request(args.search_url)
        html = response.text
        parse_page(html, '')  # Reject bot challenges before discovery.
        (root / 'search.html').write_text(html, encoding='utf-8')
        page = Page(html)
        for link in page.links:
            url = urljoin(args.search_url, link['href'])
            if urlsplit(url).hostname in ('macaulaylibrary.org', 'www.macaulaylibrary.org') and '/asset/' in url:
                sources.setdefault(asset_id(url), [])
        discovery = 'partial_html_only'
        print('Search HTML discovery is partial; export CSV for complete results/pagination.', file=sys.stderr)
        if not sources:
            raise RuntimeError('No asset links found; use the official CSV export.')
    atomic_json(root / 'run.json', {'started_at': now(), 'search_url': args.search_url or DEFAULT_SEARCH,
                                 'discovery': discovery, 'terms': args.terms, 'limit': args.limit,
                                 'source_count': len(sources), 'csv_source': str(args.csv) if args.csv else None})
    records = []
    completed = False
    try:
        for ident, rows in list(sources.items())[:args.limit]:
            target = root / 'metadata' / f'ML{ident}.json'
            record = json.loads(target.read_text()) if target.exists() else {'asset_id': ident, 'first_indexed_at': now()}
            record['asset_url'] = f'https://macaulaylibrary.org/asset/{ident}'
            record['source_search_url'] = args.search_url or DEFAULT_SEARCH
            if rows:
                record['export_rows'] = rows
                combined = {k: v for row in rows for k, v in row.items() if v}
                record.update(species=field(combined, 'Common Name', 'Species'),
                              scientific_name=field(combined, 'Scientific Name'),
                              recordist=field(combined, 'Recordist', 'Contributor', 'User Display Name'),
                              location=field(combined, 'Location', 'Locality'),
                              media_notes=field(combined, 'Media Notes', 'Media Comments'))
                record['audio_url'] = field(combined, 'Audio URL', 'Download URL') or record.get('audio_url', '')
            cached = root / 'pages' / f'ML{ident}.html'
            page_source = local.get(ident) or (cached if cached.exists() else None)
            if page_source:
                html = page_source.read_text(encoding='utf-8')
            elif args.fetch_pages:
                html = client.request(record['asset_url']).text
            else:
                html = None
            if html is not None:
                parsed = parse_page(html, ident)
                record.update({k: v for k, v in parsed.items() if v})
                cached.write_text(html, encoding='utf-8')
                record['saved_html'] = str(cached)
            record.setdefault('media_notes', '')
            record['notes_status'] = 'present' if record['media_notes'] else 'missing_or_empty_review_required'
            record['matches'] = matches(record['media_notes'], args.terms)
            record.setdefault('review_status', 'not_listened')
            species = record.get('scientific_name') or record.get('species') or '[species missing]'
            record['citation'] = f"{species} (ML{ident}); {record.get('recordist') or '[recordist missing]'}; Cornell Lab of Ornithology | Macaulay Library; {record['asset_url']}"
            record['indexed_at'] = now()
            # The user-provided endpoint convention is retained explicitly as unverified.
            if not record.get('audio_url'):
                record['audio_url'] = f'https://cdn.download.ams.birds.cornell.edu/api/v2/asset/{ident}/mp3'
                record['audio_url_source'] = 'user_provided_endpoint_pattern_unverified'
            else:
                record.setdefault('audio_url_source', 'export_or_saved_page')
            records.append(record)
            atomic_json(target, record)
            if args.download and record['matches']:
                download(client, record, root / 'audio')
                atomic_json(target, record)
        completed = True
    finally:
        export_reports(root, records)
        run = json.loads((root / 'run.json').read_text())
        run.update(finished_at=now(), status='completed' if completed else 'interrupted',
                   indexed_count=len(records), truncated=len(sources) > args.limit,
                   candidate_count=sum(bool(r['matches']) for r in records))
        atomic_json(root / 'run.json', run)
        if client:
            client.client.close()
    print(f'Indexed {len(records)}/{len(sources)} assets; {sum(bool(r["matches"]) for r in records)} candidates. Output: {root}')
    if len(sources) > args.limit:
        print('Limit reached. Raise --limit to include more assets; existing downloads are verified and skipped.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, httpx.HTTPError) as exc:
        print(f'Stopped: {exc}', file=sys.stderr)
        raise SystemExit(1)
