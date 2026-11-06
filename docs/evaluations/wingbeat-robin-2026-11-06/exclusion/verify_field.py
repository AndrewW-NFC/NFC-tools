"""Compare the current detector with and without the call veto on T7 controls.

Read-only source access; exact decoded-PCM hashes must match prior provenance.
Older cached predictions are diagnostic only; fresh streams are authoritative.
Run from the repository root.
"""

import json, sys, io, subprocess, hashlib, tarfile, zipfile, tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from nfc_tools.ffmpeg_locator import ensure_ffmpeg
from nfc_tools.analyzers import wingbeat_accompaniment as a

sys.path.insert(0, str(Path.cwd() / "tools"))
from wingbeat_research_scan import _current_broadband_pass
from nfc_tools.analyzers.wingbeats import WindowFeatures, detect_stream
from motion import metrics


def veto(m):
    return (
        m["old"]["low_band_fraction"] < 0.0005
        and m["centroid_range"] >= 700
        and m["width_ratio"] <= 0.8
    )


ROOT = Path("/Volumes/T7/Wingbeats detector")
FEATURES = ROOT / "analysis-results/2026-10-16-waterfowl-diagnostics/features"


def merge(seq):
    out = []
    for start, end in sorted(seq):
        if out and start <= out[-1][1]:
            out[-1][1] = max(end, out[-1][1])
        else:
            out.append([start, end])
    return out


def work(path):
    r = json.loads(Path(path).read_text())
    wins = []
    for win in r["windows"]:
        broad = win["kind"] not in (
            "brief",
            "accompaniment",
        ) and _current_broadband_pass(WindowFeatures(**win["broad"]))
        fs = [
            f
            for f in win["accompaniment"]
            if a.screen_accompaniment(
                [a.AccompanimentFeatures(**f)],
                allow_near_miss=win["kind"] in ("long", "accompaniment"),
            )
            is not None
        ]
        if broad or fs:
            wins.append((win, broad, fs))
    result = {k: v for k, v in r.items() if k not in ("windows", "outputs", "after")}
    result["baseline"] = merge([[win["start"], win["end"]] for win, broad, fs in wins])
    result["measurements"] = []
    with tempfile.TemporaryDirectory() as td:
        source = Path(r["path"])
        if not source.exists():
            source = Path(td) / "source.wav"
            if r["dataset"] == "pilot":
                snap = json.loads(
                    (
                        ROOT
                        / "analysis-results/2026-10-16-waterfowl-pilot-detector/review-snapshot.json"
                    ).read_text()
                )
                rec = next(x for x in snap["batch"]["records"] if x["id"] == r["id"])
                with tarfile.open(ROOT / rec["source_archive"]) as archive:
                    data = archive.extractfile(rec["source_member"]).read()
                assert hashlib.sha256(data).hexdigest() == rec["source_sha256"]
            elif r["dataset"] == "discrete":
                with zipfile.ZipFile(
                    ROOT
                    / "audio-library/reference-recordings/suspected-false-positives/wav files with false positive WING sounds.zip"
                ) as z:
                    data = z.read(r["id"])
            else:
                raise FileNotFoundError(r["path"])
            source.write_bytes(data)
        raw = subprocess.check_output(
            [
                ensure_ffmpeg(),
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-f",
                "f32le",
                "-",
            ]
        )
    x = np.frombuffer(raw, dtype="<f4")
    if "crop" in r:
        x = x[round(r["crop"][0] * 24000) : round(r["crop"][1] * 24000)]
    assert hashlib.sha256(x.tobytes()).hexdigest() == r["pcm_sha256"], r["id"]
    saved_veto = a.swept_call_interference
    a.swept_call_interference = lambda item: False
    try:
        baseline_current = [
            [c.start, c.end] for c in detect_stream(io.BytesIO(x.tobytes()), 24000)
        ]
    finally:
        a.swept_call_interference = saved_veto
    fresh = [[c.start, c.end] for c in detect_stream(io.BytesIO(x.tobytes()), 24000)]
    for win, broad, fs in wins:
        chunk = x[round(win["start"] * 24000) : round(win["end"] * 24000)]
        mm = [dict(old=f, **metrics(chunk, f)) for f in fs] if not broad else []
        result["measurements"].append(
            dict(
                start=win["start"],
                end=win["end"],
                kind=win["kind"],
                broadband=broad,
                features=mm,
            )
        )
    result["candidate"] = merge(
        [
            [w["start"], w["end"]]
            for w in result["measurements"]
            if w["broadband"] or any(not veto(m) for m in w["features"])
        ]
    )
    result["cached_baseline"] = result["baseline"]
    result["cached_candidate"] = result["candidate"]
    result["baseline"] = baseline_current
    result["candidate"] = fresh
    assert all(
        any(bs <= s and e <= be for bs, be in baseline_current) for s, e in fresh
    ), r["id"]
    result["fresh_stream_verified"] = True
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(work, p): p for p in sorted(FEATURES.glob("*.json"))}
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            (out / (futs[f].name)).write_text(json.dumps(r))
            if r["baseline"] != r["candidate"]:
                print(
                    "CHANGED",
                    r["dataset"],
                    r["id"],
                    r.get("label"),
                    r["baseline"],
                    r["candidate"],
                    flush=True,
                )
            if n % 30 == 0:
                print("progress", n, "/", len(futs), flush=True)
