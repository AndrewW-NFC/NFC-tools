"""Diagnose the user-defined robin development split; never open faint audio.

Run from the repository root with the project Python environment.
Source audio stays in the supplied archive; output contains measurements only.
"""

import argparse, io, json, hashlib, subprocess, tempfile, zipfile
from pathlib import Path
from dataclasses import asdict
from collections import Counter
from nfc_tools.analyzers import wingbeats as w
from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeat_frames import FrameCache
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--layout", choices=("training", "additional"), default="training")
args = parser.parse_args()
out = args.output
out.mkdir(parents=True, exist_ok=True)
z = zipfile.ZipFile(args.archive)
provenance = dict(
    source_archive=args.archive.name,
    archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
    revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    sample_rate=24000,
    evaluation_role="development"
    if args.layout == "training"
    else "additional_baseline",
    candidate_rule_tested=False,
)
results = []
excluded = []
for name in sorted(z.namelist()):
    p = Path(name)
    if p.suffix.lower() != ".wav" or "__MACOSX" in p.parts:
        continue
    if "faint" in p.name.lower():
        excluded.append(p.name)
        continue
    group = "varied" if p.name.startswith("WING (review required)") else "diagnosis"
    if args.layout == "additional":
        if p.parent.name == "Robin mis-ID as WING":
            group = "robin"
        elif p.parent.name == "Neither robin nor WING":
            group = "likely_footsteps"
        else:
            raise ValueError(f"Unrecognized additional-set directory: {p.parent}")
    data = z.read(name)
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "input.wav"
        wav.write_bytes(data)
        raw = subprocess.check_output(
            [
                ensure_ffmpeg(),
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(wav),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-f",
                "f32le",
                "-",
            ]
        )
    caches = (
        FrameCache(768, 240, w.broadband_frames),
        FrameCache(1024, 240, a.accompaniment_frames),
    )
    accepted = []
    for start, samples, kind in w.analysis_windows(io.BytesIO(raw), 24000):
        offset = round(start * 24000)
        score = w.screen_window(
            samples, 24000, pass_kind=kind, frame_caches=caches, offset=offset
        )
        if score is None:
            continue
        broad = w.window_features(samples, 24000, frame_cache=caches[0], offset=offset)
        broad_ok = (
            kind not in ("brief", "accompaniment")
            and broad
            and (
                broad.peak_envelope >= 1e-4
                and broad.spectral_flatness >= 0.12
                and broad.modulation >= 0.25
                and broad.periodicity >= 0.6
                and broad.repeat_periodicity >= 0.35
                and broad.pulse_count >= 4
                and broad.coherent_bands >= 3
                and broad.low_band_fraction >= a.MIN_LOW_BAND_FRACTION
                and broad.band_energy_fraction >= 1e-4
            )
        )
        features = a.accompaniment_features(
            samples, frame_cache=caches[1], offset=offset
        )
        selected = []
        for f in features:
            if (
                a.screen_accompaniment(
                    [f], allow_near_miss=kind in ("long", "accompaniment")
                )
                is not None
            ):
                selected.append(
                    dict(
                        **asdict(f),
                        spectral_route=a.accompaniment_spectral_support(f),
                        localized_route=a.localized_pulse_support(f),
                        regular_rhythm=a.accompaniment_rhythm_passes(
                            f, allow_near_miss=kind in ("long", "accompaniment")
                        ),
                        irregular_rhythm=a.supported_irregular_rhythm(f),
                    )
                )
        accepted.append(
            dict(
                pcm_sha256=hashlib.sha256(samples.tobytes()).hexdigest(),
                start=start,
                end=start + len(samples) / 24000,
                kind=kind,
                broadband=bool(broad_ok),
                broadband_features=asdict(broad) if broad else None,
                accompaniment=selected,
            )
        )
    intervals = [asdict(c) for c in w.detect_stream(io.BytesIO(raw), 24000)]
    row = dict(
        file=str(p.relative_to(p.parts[0])) if args.layout == "additional" else p.name,
        group=group,
        sha256=hashlib.sha256(data).hexdigest(),
        seconds=len(raw) / 4 / 24000,
        intervals=intervals,
        accepted_windows=accepted,
    )
    results.append(row)
    print(
        group,
        p.name,
        "seconds",
        round(row["seconds"], 2),
        "windows",
        len(accepted),
        "broad",
        sum(x["broadband"] for x in accepted),
        "bands",
        dict(Counter(f["lower_hz"] for x in accepted for f in x["accompaniment"])),
        flush=True,
    )
    (out / "results.json").write_text(
        json.dumps(
            dict(provenance=provenance, recordings=results, excluded=excluded), indent=2
        )
        + "\n"
    )
print("DONE", flush=True)

# Verify diagnostic coverage against the authoritative streaming output and
# record exact overlapping PCM without treating it as independent evidence.
from collections import defaultdict
import csv

matches = defaultdict(list)
for row in results:
    merged = []
    for window in row["accepted_windows"]:
        matches[window["pcm_sha256"]].append(
            dict(
                file=row["file"],
                start=window["start"],
                end=window["end"],
                group=row["group"],
            )
        )
        if merged and window["start"] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], window["end"])
        else:
            merged.append([window["start"], window["end"]])
    assert merged == [[x["start"], x["end"]] for x in row["intervals"]]
shared = [v for v in matches.values() if len({x["file"] for x in v}) > 1]
(out / "results.json").write_text(
    json.dumps(
        dict(
            provenance=provenance,
            recordings=results,
            excluded=excluded,
            identical_accepted_audio_windows=shared,
        ),
        indent=2,
    )
    + "\n"
)
with (out / "clips.csv").open("w", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(
        ["file", "group", "seconds", "detected_intervals", "accepted_windows", "sha256"]
    )
    for row in results:
        writer.writerow(
            [
                row["file"],
                row["group"],
                row["seconds"],
                "; ".join(f"{c['start']:.3f}-{c['end']:.3f}" for c in row["intervals"]),
                len(row["accepted_windows"]),
                row["sha256"],
            ]
        )
