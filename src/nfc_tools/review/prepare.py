"""Prepare a deterministic, metadata-only pilot without modifying source audio."""
import csv
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
import wave
from collections import Counter
from pathlib import Path

import numpy as np
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def prepare(root: Path, batch_id: str):
    batch = root / 'reviews' / batch_id
    if batch.exists():
        raise ValueError(f'Batch already exists; refusing to overwrite: {batch}')
    with (root / 'catalogs/waterfowl-recordings.csv').open(newline='') as f:
        catalog = list(csv.DictReader(f))
    eligible, unsupported = [], 0
    pattern = re.compile(r'wing[ -]?beats?|flapp|wing (?:sounds?|noise)|wings (?:can be|are) heard|wings beat', re.I)
    archive = root / catalog[0]['archive_path']
    with tarfile.open(archive, 'r:') as source:
        for row in catalog:
            if not row['archive_member'].endswith('.wav'):
                continue
            try:
                with wave.open(source.extractfile(row['archive_member'])) as audio:
                    duration = audio.getnframes() / audio.getframerate()
            except (wave.Error, EOFError):
                unsupported += 1
                continue
            if 8 <= duration <= 100:
                eligible.append(dict(row, duration=duration, explicit=bool(pattern.search(row['media_notes']))))
        chosen, species, recordists = [], Counter(), Counter()
        for explicit, count in [(True, 15), (False, 5)]:
            pool = [r for r in eligible if r['explicit'] == explicit and r['recordist'] not in recordists]
            for _ in range(count):
                if not pool:
                    raise ValueError('Insufficient distinct-recordist candidates for the pilot')
                row = min(pool, key=lambda r: (species[r['common_name']], abs(r['duration'] - 35), r['recording_id']))
                chosen.append(row)
                species[row['common_name']] += 1
                recordists[row['recordist']] += 1
                pool = [r for r in pool if r['recordist'] != row['recordist']]
        # Interleave the ambiguous examples, without exposing selection flags in the queue.
        positives, ambiguous = chosen[:15], chosen[15:]
        chosen = [r for i in range(5) for r in positives[i*3:i*3+3] + [ambiguous[i]]]
        preview_dir = root / 'audio-library/macaulay/review-previews' / batch_id
        if preview_dir.exists():
            raise ValueError(f'Preview folder already exists: {preview_dir}')
        preview_dir.mkdir(parents=True)
        records = []
        for row in chosen:
            member = source.getmember(row['archive_member'])
            with tempfile.TemporaryDirectory(prefix='wingbeat-review-prepare-') as tmp:
                original = Path(tmp) / 'source.wav'
                digest = hashlib.sha256()
                with source.extractfile(member) as src, original.open('wb') as dst:
                    for block in iter(lambda: src.read(4 * 1024 * 1024), b''):
                        digest.update(block)
                        dst.write(block)
                if digest.hexdigest() != row['sha256']:
                    raise ValueError(f'Source checksum failed: {row["recording_id"]}')
                preview = preview_dir / (row['recording_id'] + '.wav')
                subprocess.run([ensure_ffmpeg(), '-nostdin', '-v', 'error', '-i', str(original),
                                '-map_metadata', '-1', '-ar', '48000', '-c:a', 'pcm_s16le', str(preview)], check=True)
            with wave.open(str(preview)) as audio:
                rate, channels = audio.getframerate(), audio.getnchannels()
                samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').reshape(-1, channels)
                duration = len(samples) / rate
            peaks = [round(float(np.max(np.abs(chunk.astype(np.int32)))) / 32768, 5)
                     for chunk in np.array_split(samples, min(2400, len(samples))) if len(chunk)]
            records.append({
                'id': row['recording_id'], 'catalog_number': row['catalog_number'],
                'species': row['common_name'], 'recordist': row['recordist'], 'source_notes': row['media_notes'],
                'duration': duration, 'source_duration': row['duration'], 'channels': channels,
                'source_sha256': row['sha256'], 'source_archive': row['archive_path'],
                'source_member': row['archive_member'], 'audio_path': str(preview.relative_to(root)),
                'preview_sha256': hashlib.sha256(preview.read_bytes()).hexdigest(), 'peaks': peaks,
                'selection_basis': 'explicit wing-sound notes' if row['explicit'] else 'less explicit metadata',
            })
            print('Prepared', row['recording_id'], row['common_name'], round(duration, 1), flush=True)
    batch.mkdir(parents=True)
    manifest = {'batch_id': batch_id, 'title': 'Waterfowl listening pilot', 'created_date': '2026-10-16',
                'purpose': 'Development pilot; do not use as an untouched evaluation set.',
                'selection': {'explicit_notes': 15, 'less_explicit': 5, 'duration_range_seconds': [8, 100],
                              'unique_recordists': len(recordists), 'species': len(species),
                              'eligible_records': len(eligible), 'unreadable_pcm_headers_excluded': unsupported,
                              'limitations': 'Convenience pilot limited to WAV files readable by Python wave, 8–100 seconds; not a representative evaluation sample. No detector scores used.'},
                'preview': '48 kHz PCM16 WAV, original channel count, no trimming or normalization. Timestamps are seconds from the start of the original recording.',
                'records': records}
    (batch / 'batch.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    fields = ['id', 'catalog_number', 'species', 'recordist', 'duration', 'source_sha256', 'source_archive', 'source_member', 'audio_path', 'preview_sha256', 'selection_basis']
    with (batch / 'recording-list.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        w.writerows({k: r[k] for k in fields} for r in records)
    print(json.dumps({'batch': str(batch), 'recordings': len(records), 'minutes': sum(r['duration'] for r in records)/60, 'species': len(species), 'recordists': len(recordists)}))
    return batch
