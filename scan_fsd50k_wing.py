import csv
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from nfc_tools.analyzers.wingbeats import detect_stream
from nfc_tools.analyzers.wingbeat_accompaniment import ANALYSIS_RATE
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

ROOT = Path("/Volumes/T7/FSD50K")
AUDIO = ROOT / "FSD50K.dev_audio"
GROUND_TRUTH = ROOT / "FSD50K.ground_truth" / "dev.csv"
DB = ROOT / "fsd50k_wing_scan.sqlite"
CSV_OUT = ROOT / "fsd50k_wing_scan_dev.csv"

# Load FSD50K labels.
labels = {}
with GROUND_TRUTH.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        labels[row["fname"]] = {
            "labels": row["labels"],
            "split": row.get("split", ""),
        }

conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS files (
    fname TEXT PRIMARY KEY,
    labels TEXT,
    fsd_split TEXT,
    candidate_count INTEGER,
    detections_json TEXT,
    status TEXT,
    error TEXT
)
""")
conn.commit()

already_done = {
    row[0] for row in
    conn.execute("SELECT fname FROM files WHERE status = 'ok'")
}

wavs = sorted(AUDIO.glob("*.wav"))
total = len(wavs)

print(f"Found {total:,} development WAVs.")
print(f"Already completed: {len(already_done):,}")
print("Press Control-C at any time; completed files will remain saved.")
print()

for number, wav in enumerate(wavs, 1):
    fname = wav.stem

    if fname in already_done:
        continue

    info = labels.get(fname, {"labels": "", "split": ""})

    try:
        with tempfile.TemporaryFile() as errors:
            with subprocess.Popen(
                [
                    ensure_ffmpeg(),
                    "-hide_banner", "-loglevel", "error", "-nostdin",
                    "-i", str(wav),
                    "-map", "0:a:0",
                    "-ac", "1",
                    "-ar", str(ANALYSIS_RATE),
                    "-f", "f32le",
                    "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=errors,
            ) as process:
                candidates = detect_stream(process.stdout, ANALYSIS_RATE)

                if process.wait() != 0:
                    errors.seek(0)
                    raise RuntimeError(
                        errors.read(2000).decode(errors="replace")
                    )

        detections = [
            {
                "start_sec": round(c.start, 3),
                "end_sec": round(c.end, 3),
                "periodicity": round(c.periodicity, 3),
            }
            for c in candidates
        ]

        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files
                (fname, labels, fsd_split, candidate_count,
                 detections_json, status, error)
                VALUES (?, ?, ?, ?, ?, 'ok', '')
                """,
                (
                    fname,
                    info["labels"],
                    info["split"],
                    len(candidates),
                    json.dumps(detections),
                ),
            )

        if candidates:
            print(
                f"[{number:,}/{total:,}] {fname}.wav -> "
                f"{len(candidates)} WING candidate(s)  "
                f"{info['labels']}"
            )

        if number % 500 == 0:
            completed = conn.execute(
                "SELECT COUNT(*) FROM files WHERE status='ok'"
            ).fetchone()[0]
            hits = conn.execute(
                "SELECT COUNT(*) FROM files WHERE candidate_count > 0"
            ).fetchone()[0]
            print(
                f"--- {completed:,}/{total:,} analyzed; "
                f"{hits:,} files have triggered WING ---"
            )

    except KeyboardInterrupt:
        print("\nStopped. Progress has been saved.")
        break

    except Exception as exc:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files
                (fname, labels, fsd_split, candidate_count,
                 detections_json, status, error)
                VALUES (?, ?, ?, NULL, '[]', 'error', ?)
                """,
                (fname, info["labels"], info["split"], str(exc)),
            )
        print(f"ERROR: {fname}.wav: {exc}")

# Export the current database to an ordinary CSV.
with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "fname",
        "labels",
        "fsd_split",
        "candidate_count",
        "detections_json",
        "status",
        "error",
    ])
    for row in conn.execute("""
        SELECT fname, labels, fsd_split, candidate_count,
               detections_json, status, error
        FROM files
        ORDER BY CAST(fname AS INTEGER)
    """):
        writer.writerow(row)

completed = conn.execute(
    "SELECT COUNT(*) FROM files WHERE status='ok'"
).fetchone()[0]
hits = conn.execute(
    "SELECT COUNT(*) FROM files WHERE candidate_count > 0"
).fetchone()[0]
detections = conn.execute(
    "SELECT COALESCE(SUM(candidate_count), 0) FROM files"
).fetchone()[0]

print()
print(f"Completed: {completed:,} files")
print(f"Files triggering WING: {hits:,}")
print(f"Total WING intervals: {detections:,}")
print(f"Results: {CSV_OUT}")
print(f"Checkpoint database: {DB}")

conn.close()
