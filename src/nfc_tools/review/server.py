"""Loopback-only review server with validated annotations and durable revisions."""
from __future__ import annotations
import csv
import io
import json
import math
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


class Passage(BaseModel):
    start: float
    end: float
    confidence: str = 'clear'
    note: str = Field(default='', max_length=2000)


class Review(BaseModel):
    revision: int = 0
    reviewer: str = Field(min_length=1, max_length=150)
    status: str = 'in_progress'
    outcome: str = 'unreviewed'
    intervals: list[Passage] = Field(default_factory=list, max_length=200)
    listened: list[list[float]] = Field(default_factory=list, max_length=10000)
    full_listen_confirmed: bool = False
    interference: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default='', max_length=10000)


def merge_ranges(ranges, duration):
    valid = []
    for pair in ranges:
        if len(pair) != 2 or not all(math.isfinite(x) for x in pair):
            raise ValueError('Invalid listened range')
        start, end = pair
        if not 0 <= start < end <= duration + .05:
            raise ValueError('Listened ranges must lie inside the recording')
        valid.append([start, min(end, duration)])
    merged = []
    for start, end in sorted(valid):
        if merged and start <= merged[-1][1] + .05:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def validate(review, duration):
    if review.status not in {'in_progress', 'complete', 'needs_another_listen'}:
        raise ValueError('Choose a review status')
    if review.outcome not in {'unreviewed', 'present', 'absent', 'uncertain'}:
        raise ValueError('Invalid outcome')
    if not review.reviewer.strip():
        raise ValueError('Enter your reviewer name')
    for event in review.intervals:
        if not all(math.isfinite(x) for x in [event.start, event.end]) or not 0 <= event.start < event.end <= duration:
            raise ValueError('Passages must have start < end within this recording')
        if event.confidence not in {'clear', 'faint', 'uncertain'}:
            raise ValueError('Invalid passage confidence')
    if review.outcome == 'absent' and review.intervals:
        raise ValueError('A “none heard” label cannot contain wingbeat passages')
    ranges = merge_ranges(review.listened, duration)
    coverage = duration if review.full_listen_confirmed else sum(end - start for start, end in ranges)
    if review.status == 'complete':
        if review.outcome not in {'present', 'absent'}:
            raise ValueError('Choose wingbeats present or none heard, or save as needs another listen')
        if review.outcome == 'present' and not review.intervals:
            raise ValueError('Mark at least one wingbeat passage')
        if coverage < duration - .15:
            raise ValueError('Review the whole recording before marking complete; save partial work as in progress')
    return dict(review.model_dump(), listened=ranges, reviewed_seconds=coverage)


def create_app(root: Path, batch: Path):
    root, batch = root.resolve(), batch.resolve()
    if not batch.is_relative_to(root / 'reviews'):
        raise ValueError('Batch must be inside this collection’s reviews folder')
    manifest = json.loads((batch / 'batch.json').read_text())
    records = {r['id']: r for r in manifest['records']}
    db = batch / 'annotations.sqlite'
    backups = batch / 'backups'
    backups.mkdir(exist_ok=True)
    lock = threading.Lock()
    with sqlite3.connect(db) as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS revisions (id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(id,revision));''')
    app = FastAPI(title='Waterfowl listening pilot', docs_url=None, redoc_url=None)
    app.state.db = db
    assets = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=assets), name='static')

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        # Prevent websites or DNS-rebinding hosts from writing to the local app.
        if request.url.hostname not in {'127.0.0.1', 'localhost', 'testserver'}:
            return Response('Local access only', status_code=403)
        if request.method == 'POST':
            origin = request.headers.get('origin')
            if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}':
                return Response('Same-origin requests only', status_code=403)
            if request.headers.get('x-review-client') != 'local-review':
                return Response('Review client required', status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api') else 'no-cache'
        return response

    def states():
        with sqlite3.connect(db) as c:
            return {ident: json.loads(body) for ident, body in c.execute('SELECT id, body FROM reviews')}

    def get_record(ident):
        if ident not in records:
            raise HTTPException(404, 'Recording not in this batch')
        return records[ident]

    @app.get('/')
    def index():
        return FileResponse(assets / 'index.html')

    @app.get('/api/batch')
    def get_batch():
        return dict(manifest, reviews=states())

    @app.get('/audio/{ident}')
    def audio(ident: str):
        row = get_record(ident)
        path = (root / row['audio_path']).resolve()
        if not path.is_relative_to(root / 'audio-library') or not path.is_file():
            raise HTTPException(404, 'Audio unavailable; check that the T7 is mounted')
        return FileResponse(path, media_type='audio/wav')

    @app.post('/api/reviews/{ident}')
    def save(ident: str, review: Review):
        row = get_record(ident)
        try:
            data = validate(review, row['duration'])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with lock, sqlite3.connect(db) as c:
            c.execute('BEGIN IMMEDIATE')
            current = c.execute('SELECT revision FROM reviews WHERE id=?', (ident,)).fetchone()
            revision = current[0] if current else 0
            if revision != review.revision:
                raise HTTPException(409, 'This recording changed in another tab. Reload before editing; your local draft has not been discarded.')
            data.update(revision=revision + 1, updated_at=datetime.now(timezone.utc).isoformat(),
                        recording_id=ident, source_sha256=row['source_sha256'],
                        preview_sha256=row['preview_sha256'], batch_id=manifest['batch_id'])
            body = json.dumps(data, allow_nan=False)
            # Write an immutable backup before committing; errors roll back the save.
            backup_path = backups / f'{ident}-revision-{revision+1:05d}.json'
            with backup_path.open('w') as out:
                out.write(body + '\n')
                out.flush()
                import os
                os.fsync(out.fileno())
            c.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?)', (ident, revision + 1, body))
            c.execute('INSERT INTO revisions VALUES (?,?,?)', (ident, revision + 1, body))
            c.commit()
        return data

    @app.get('/api/export/{kind}')
    def export(kind: str):
        saved = states()
        if kind == 'json':
            payload = dict(batch=manifest, reviews=saved)
            return Response(json.dumps(payload, indent=2, ensure_ascii=False), media_type='application/json',
                            headers={'Content-Disposition': 'attachment; filename="waterfowl-review-backup.json"'})
        if kind not in {'recordings', 'passages', 'listened'}:
            raise HTTPException(404)
        fields = {'recordings': ['recording_id', 'catalog_number', 'species', 'status', 'outcome', 'reviewer', 'reviewed_seconds', 'duration_seconds', 'full_listen_confirmed', 'interference', 'notes', 'revision', 'updated_at', 'source_sha256', 'preview_sha256'],
                  'passages': ['recording_id', 'start_seconds', 'end_seconds', 'confidence', 'note', 'reviewer', 'revision', 'source_sha256'],
                  'listened': ['recording_id', 'start_seconds', 'end_seconds', 'full_listen_confirmed', 'reviewer', 'revision']}[kind]
        stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for row in records.values():
            state = saved.get(row['id'], {})
            common = dict(recording_id=row['id'], reviewer=state.get('reviewer', ''), revision=state.get('revision', 0))
            if kind == 'recordings':
                writer.writerow(dict(common, catalog_number=row['catalog_number'], species=row['species'],
                                     status=state.get('status', 'not_started'), outcome=state.get('outcome', 'unreviewed'),
                                     reviewed_seconds=state.get('reviewed_seconds', 0), duration_seconds=row['duration'],
                                     full_listen_confirmed=state.get('full_listen_confirmed', False),
                                     interference='; '.join(state.get('interference', [])), notes=state.get('notes', ''),
                                     updated_at=state.get('updated_at', ''), source_sha256=row['source_sha256'], preview_sha256=row['preview_sha256']))
            elif kind == 'passages':
                for event in state.get('intervals', []):
                    writer.writerow(dict(common, start_seconds=event['start'], end_seconds=event['end'], confidence=event['confidence'], note=event['note'], source_sha256=row['source_sha256']))
            else:
                for start, end in ([[0, row['duration']]] if state.get('full_listen_confirmed') else state.get('listened', [])):
                    writer.writerow(dict(common, start_seconds=start, end_seconds=end, full_listen_confirmed=state.get('full_listen_confirmed', False)))
        return Response(stream.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="waterfowl-{kind}.csv"'})
    return app
