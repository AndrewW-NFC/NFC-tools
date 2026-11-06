"""Fresh supplied-clip and positive-control gain/alignment comparisons.

Variants are correlated robustness checks, not independent field examples.
Run from the repository root; originals are never modified.
"""

import json, io, subprocess, hashlib, tempfile, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream
from nfc_tools.ffmpeg_locator import ensure_ffmpeg


def work(job):
    if job.get("archive"):
        with zipfile.ZipFile(job["archive"]) as z:
            data = z.read(job["member"])
    else:
        data = Path(job["path"]).read_bytes()
    if "expected_sha256" in job:
        assert hashlib.sha256(data).hexdigest() == job["expected_sha256"], job["file"]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "input.wav"
        p.write_bytes(data)
        raw = subprocess.check_output(
            [
                ensure_ffmpeg(),
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(p),
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
    if "crop" in job:
        x = x[round(job["crop"][0] * 24000) : round(job["crop"][1] * 24000)]
    variants = [(1, 0)]
    if job["group"] in ("diagnosis", "robin", "field", "mute_swan"):
        variants = [(g, p) for g in (0.1, 1, 3) for p in (0, 0.125, 0.5, 0.75)]
    results = []
    for gain, padding in variants:
        xx = np.r_[np.zeros(round(padding * 24000)), x * gain].astype("<f4")
        saved = a.swept_call_interference
        a.swept_call_interference = lambda item: False
        try:
            before = [
                [c.start, c.end] for c in detect_stream(io.BytesIO(xx.tobytes()), 24000)
            ]
        finally:
            a.swept_call_interference = saved
        after = [
            [c.start, c.end] for c in detect_stream(io.BytesIO(xx.tobytes()), 24000)
        ]
        assert all(any(bs <= s and e <= be for bs, be in before) for s, e in after)
        results.append(dict(gain=gain, padding=padding, before=before, after=after))
    return dict(
        **job,
        sha256=hashlib.sha256(data).hexdigest(),
        pcm_sha256=hashlib.sha256(x.tobytes()).hexdigest(),
        variants=results,
    )


def supplied_jobs(audio_directory):
    """Resolve the moved, extracted T7 files, retaining original ZIP support."""
    base = Path("docs/evaluations/wingbeat-robin-2026-11-06")
    jobs = []
    for report, archive, prefix, folder in (
        (base / "results.json", "robin training.zip", "robin training/", ""),
        (
            base / "additional/results.json",
            "Test against.zip",
            "Test against/",
            "Test against",
        ),
    ):
        for r in json.loads(report.read_text())["recordings"]:
            job = dict(file=r["file"], group=r["group"], expected_sha256=r["sha256"])
            extracted = audio_directory / folder / r["file"]
            if extracted.is_file():
                job["path"] = str(extracted)
            else:
                job.update(
                    archive=str(audio_directory / archive), member=prefix + r["file"]
                )
            jobs.append(job)
    return jobs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--field-results", type=Path, required=True)
    args = parser.parse_args()
    jobs = supplied_jobs(args.audio_directory)
    jobs.append(
        dict(
            file="mute-swan-wings.wav",
            group="mute_swan",
            path="tests/fixtures/mute-swan-wings.wav",
        )
    )
    for p in args.field_results.glob("*.json"):
        r = json.loads(p.read_text())
        if r["dataset"] == "field":
            jobs.append(
                dict(file=r["id"], group="field", path=r["path"], crop=r["crop"])
            )
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(work, j) for j in jobs]
        for n, f in enumerate(as_completed(futures), 1):
            r = f.result()
            (out / (str(n) + ".json")).write_text(json.dumps(r))
            print(
                n,
                "/",
                len(jobs),
                r["group"],
                r["file"],
                sum(bool(x["before"]) for x in r["variants"]),
                sum(bool(x["after"]) for x in r["variants"]),
                flush=True,
            )
