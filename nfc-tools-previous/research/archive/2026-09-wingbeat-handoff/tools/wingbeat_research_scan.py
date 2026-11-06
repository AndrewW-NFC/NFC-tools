from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np

from nfc_tools.analyzers.wingbeats import (
    PULSE_BANDS, WINDOW_SECONDS, HOP_SECONDS, window_features, screen_window, detect_stream,
)
from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE, SEARCH_BANDS, accompaniment_features, screen_accompaniment,
    AccompanimentFeatures, distinct_pulses, _correlation, _smooth,
)

EPS = 1e-20

# Exact accelerator for the 21-bin local spectral median used by the current
# accompaniment route. The edge handling and odd-window median are identical to
# np.pad(..., mode="edge") + sliding_window_view(..., 21) + median.
try:
    from numba import njit
    @njit(cache=True)
    def _median21_rows(power):
        n, m = power.shape
        out = np.empty_like(power)
        for i in range(n):
            vals = np.empty(21, dtype=power.dtype)
            for j in range(m):
                for k in range(21):
                    q = j + k - 10
                    if q < 0:
                        q = 0
                    elif q >= m:
                        q = m - 1
                    vals[k] = power[i, q]
                for k in range(1, 21):
                    v = vals[k]
                    l = k - 1
                    while l >= 0 and vals[l] > v:
                        vals[l + 1] = vals[l]
                        l -= 1
                    vals[l + 1] = v
                out[i, j] = vals[10]
        return out
    _HAVE_NUMBA = True
except Exception:
    _HAVE_NUMBA = False
    def _median21_rows(power):
        neighborhoods = np.lib.stride_tricks.sliding_window_view(
            np.pad(power, ((0, 0), (10, 10)), mode="edge"), 21, axis=1
        )
        return np.median(neighborhoods, axis=-1)


def _current_broadband_pass(features) -> bool:
    """Mirror the current production broadband gates for route labeling only."""
    if features is None:
        return False
    return not (features.peak_envelope < 1e-4 or features.spectral_flatness < 0.12
                or features.modulation < 0.25 or features.periodicity < 0.6
                or features.repeat_periodicity < 0.35 or features.pulse_count < 4
                or features.coherent_bands < 3 or features.band_energy_fraction < 1e-4)


def fast_accompaniment_features(samples: np.ndarray) -> list[AccompanimentFeatures]:
    """Numerically equivalent to current accompaniment_features; research scanner accelerator."""
    if len(samples) < ANALYSIS_RATE or not np.isfinite(samples).all():
        return []
    frames = np.lib.stride_tricks.sliding_window_view(samples, 1024)[::240]
    power = np.abs(np.fft.rfft(frames * np.hanning(1024), axis=1)) ** 2
    frequency = np.fft.rfftfreq(1024, 1 / ANALYSIS_RATE)
    local_median = _median21_rows(power)
    peaks = (power > 8 * local_median) & (power > power.max(axis=1, keepdims=True) * .001)
    masked = np.lib.stride_tricks.sliding_window_view(
        np.pad(peaks, ((0, 0), (6, 6)), mode="edge"), 13, axis=1,
    ).any(axis=-1)
    bins = np.arange(power.shape[1])[None, :]
    results = []
    for lower, upper in SEARCH_BANDS:
        in_band = (frequency >= lower) & (frequency < upper)
        ridge = np.argmax(power[:, in_band], axis=1) + np.flatnonzero(in_band)[0]
        distance = np.abs(bins - ridge[:, None])
        tone = _smooth(np.sqrt((power * (distance <= 2)).sum(axis=1)), 3)
        noise_center = int(np.median(ridge))
        residual_distance = np.abs(bins - noise_center)
        residual = ((residual_distance >= 9) & (residual_distance <= 45) & ~masked
                    & (frequency[None, :] >= 300) & (frequency[None, :] <= 10000))
        above = residual & (bins > noise_center)
        below = residual & ~above
        lower_power = (power * below).sum(axis=1) / np.maximum(1, below.sum(axis=1))
        upper_power = (power * above).sum(axis=1) / np.maximum(1, above.sum(axis=1))
        noise = _smooth(np.sqrt((lower_power + upper_power) / 2), 3)
        centered = tone - _smooth(tone, 51)
        noise_centered = noise - _smooth(noise, 51)
        correlations = [0.0] + [
            _correlation(centered[:-lag], centered[lag:])
            for lag in range(1, min(101, len(centered) // 2))
        ]
        lags = [lag for lag in range(5, min(51, len(centered) // 4))
                if correlations[lag] > correlations[lag - 1]
                and correlations[lag] >= correlations[lag + 1]]
        best = max(lags, key=lambda lag: correlations[lag], default=None)
        if best is None:
            continue
        on = centered >= np.percentile(centered, 75)
        off = centered <= np.percentile(centered, 25)
        contrast = (noise[on].mean() - noise[off].mean()) / (noise[on].mean() + 1e-20)
        low, high = np.percentile(tone, [10, 90])
        count = distinct_pulses(tone, low + .6 * (high - low), best)
        results.append(AccompanimentFeatures(
            lower, upper, correlations[best],
            _correlation(centered[:-2 * best], centered[2 * best:]),
            float((high - low) / (high + 1e-20)),
            _correlation(centered, noise_centered), float(contrast),
            float(np.median(noise) / (np.median(tone) + 1e-20)),
            float(np.median(power[np.arange(len(power)), ridge][on]
                            / (power.max(axis=1)[on] + 1e-20))),
            float(np.median(residual.sum(axis=1))), count, float(tone.max()),
            float(frequency[noise_center]),
        ))
    return results



def _float(x):
    try:
        v = float(x)
    except Exception:
        return ""
    return v if math.isfinite(v) else ""


def decode_audio(path: Path, sample_rate: int = ANALYSIS_RATE) -> np.ndarray:
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(sample_rate),
        "-f", "f32le", "pipe:1",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr[:2000].decode(errors="replace"))
    if len(p.stdout) % 4:
        raise ValueError("Truncated decoded audio")
    return np.frombuffer(p.stdout, dtype="<f4").copy()


def _smooth(values: np.ndarray, size: int) -> np.ndarray:
    return np.convolve(np.pad(values, size // 2, mode="symmetric"), np.ones(size) / size, mode="valid")


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    denom = np.linalg.norm(left) * np.linalg.norm(right)
    return float(np.dot(left, right) / denom) if denom else 0.0


def _select_pulse_peaks(envelope: np.ndarray, threshold: float, period: int | None) -> np.ndarray:
    if period is None or period <= 0 or len(envelope) == 0:
        return np.array([], dtype=int)
    above = np.r_[False, envelope > threshold, False]
    starts = np.flatnonzero(above[1:] & ~above[:-1])
    ends = np.flatnonzero(~above[1:] & above[:-1])
    candidates = np.array([
        start + int(np.argmax(envelope[start:end]))
        for start, end in zip(starts, ends) if end > start
    ], dtype=int)
    selected: list[int] = []
    if len(candidates):
        for peak in candidates[np.argsort(envelope[candidates])[::-1]]:
            if all(abs(int(peak) - other) >= .6 * period for other in selected):
                selected.append(int(peak))
    return np.array(sorted(selected), dtype=int)


def _lagged_corr(a: np.ndarray, b: np.ndarray, lag: int) -> float:
    if lag > 0:
        return _corr(a[:-lag], b[lag:]) if len(a) > lag else 0.0
    if lag < 0:
        lag = -lag
        return _corr(a[lag:], b[:-lag]) if len(a) > lag else 0.0
    return _corr(a, b)


def _broadband_detail(samples: np.ndarray, sample_rate: int = ANALYSIS_RATE) -> dict:
    out: dict[str, object] = {}
    if len(samples) < sample_rate or not np.isfinite(samples).all():
        return out
    frame_size = sample_rate * 32 // 1000
    hop = sample_rate // 100
    frames = np.lib.stride_tricks.sliding_window_view(samples, frame_size)[::hop]
    windowed = frames * np.hanning(frame_size)
    power = np.abs(np.fft.rfft(windowed, axis=1)) ** 2
    freq = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    main_mask = (freq >= 150) & (freq <= 3000)
    main = power[:, main_mask]
    envelope = np.sqrt(main.sum(axis=1))
    envelope = np.convolve(envelope, np.ones(3) / 3, mode="valid")
    centered = envelope - _smooth(envelope, 51)

    correlations = [0.0]
    for lag in range(1, min(102, len(centered) // 2)):
        correlations.append(_corr(centered[:-lag], centered[lag:]))
    lags = [lag for lag in range(5, min(51, len(centered) // 4))
            if correlations[lag] > correlations[lag - 1]
            and correlations[lag] >= correlations[lag + 1]]
    best = max(lags, key=lambda lag: correlations[lag], default=None)
    out["best_lag_frames"] = best if best is not None else ""
    out["beat_rate_hz"] = (100.0 / best) if best else ""  # envelope frames are 10 ms apart
    out["beat_period_ms"] = (10.0 * best) if best else ""

    low, high = np.percentile(envelope, [10, 90])
    threshold = low + .6 * (high - low)
    peaks = _select_pulse_peaks(envelope, threshold, best)
    times = peaks * 0.010 + 0.016  # approximate frame-center timing after smoothing
    out["pulse_times_sec"] = json.dumps([round(float(x), 4) for x in times])
    if len(times) >= 2:
        ipi = np.diff(times)
        out["ipi_mean_ms"] = float(np.mean(ipi) * 1000)
        out["ipi_sd_ms"] = float(np.std(ipi, ddof=1) * 1000) if len(ipi) > 1 else 0.0
        out["ipi_cv"] = float(np.std(ipi, ddof=1) / np.mean(ipi)) if len(ipi) > 1 and np.mean(ipi) else 0.0
        if len(ipi) >= 2:
            out["ipi_npvi"] = float(np.mean(200 * np.abs(np.diff(ipi)) / (ipi[:-1] + ipi[1:] + EPS)))
        else:
            out["ipi_npvi"] = ""
    else:
        out.update({"ipi_mean_ms":"", "ipi_sd_ms":"", "ipi_cv":"", "ipi_npvi":""})
    if len(peaks):
        amps = envelope[peaks]
        out["pulse_amp_cv"] = float(np.std(amps, ddof=1) / np.mean(amps)) if len(amps) > 1 and np.mean(amps) else 0.0
    else:
        out["pulse_amp_cv"] = ""

    # Pulse shape on the 10-ms envelope: half-height width and attack/decay.
    widths, attacks, decays = [], [], []
    for p in peaks:
        baseline = float(low)
        half = baseline + .5 * (float(envelope[p]) - baseline)
        left = int(p)
        while left > 0 and envelope[left] >= half:
            left -= 1
        right = int(p)
        while right + 1 < len(envelope) and envelope[right] >= half:
            right += 1
        widths.append((right - left) * 10.0)
        attacks.append((p - left) * 10.0)
        decays.append((right - p) * 10.0)
    out["pulse_fwhm_ms_median"] = float(np.median(widths)) if widths else ""
    out["pulse_attack_ms_median"] = float(np.median(attacks)) if attacks else ""
    out["pulse_decay_ms_median"] = float(np.median(decays)) if decays else ""
    out["pulse_attack_decay_ratio"] = (float(np.median(attacks)) / (float(np.median(decays)) + EPS)) if widths else ""

    # Cross-band details. These exactly parallel the detector's four pulse bands,
    # but record continuous values and timing offsets rather than only the pass count.
    band_lags = []
    for idx, (lower_hz, upper_hz) in enumerate(PULSE_BANDS, start=1):
        bm = (freq >= lower_hz) & (freq < upper_hz)
        benv = np.sqrt(power[:, bm].sum(axis=1))
        benv = np.convolve(benv, np.ones(3) / 3, mode="valid")
        blo, bhi = np.percentile(benv, [10, 90])
        bmod = float((bhi - blo) / (bhi + EPS))
        bc = benv - _smooth(benv, 51)
        coherence = _corr(bc, centered)
        repetition = _corr(bc[:-best], bc[best:]) if best and len(bc) > best else 0.0
        best_sync_lag = ""
        best_sync_corr = ""
        if len(bc) == len(centered) and len(bc) > 10:
            lag_scores = [(lag, _lagged_corr(centered, bc, lag)) for lag in range(-5, 6)]
            lag, val = max(lag_scores, key=lambda x: x[1])
            best_sync_lag = int(lag)
            best_sync_corr = float(val)
            band_lags.append(lag * 10.0)
        prefix = f"band{idx}_{lower_hz}_{upper_hz}"
        out[prefix + "_modulation"] = bmod
        out[prefix + "_coherence"] = coherence
        out[prefix + "_repetition"] = repetition
        out[prefix + "_sync_lag_ms"] = (best_sync_lag * 10.0) if best_sync_lag != "" else ""
        out[prefix + "_sync_corr"] = best_sync_corr
    out["band_sync_lag_spread_ms"] = float(np.ptp(band_lags)) if len(band_lags) >= 2 else ""

    # General waveform morphology. Polarity-independent biphasic balance is included
    # because bird-wing pressure impulses can flip sign with recording geometry.
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    peak_abs = float(np.max(np.abs(samples)))
    out["rms"] = rms
    out["peak_abs"] = peak_abs
    out["crest_factor"] = peak_abs / (rms + EPS)
    s2 = float(np.mean(samples.astype(np.float64) ** 2))
    s4 = float(np.mean(samples.astype(np.float64) ** 4))
    out["waveform_kurtosis"] = s4 / (s2 * s2 + EPS)
    out["zero_cross_rate"] = float(np.mean(np.signbit(samples[1:]) != np.signbit(samples[:-1]))) if len(samples) > 1 else ""

    biphasic, ptp = [], []
    radius = int(.05 * sample_rate)
    for t in times:
        c = int(t * sample_rate)
        a, b = max(0, c-radius), min(len(samples), c+radius)
        seg = samples[a:b]
        if len(seg):
            pos, neg = float(np.max(seg)), abs(float(np.min(seg)))
            hi, lo2 = max(pos, neg), min(pos, neg)
            biphasic.append(lo2 / (hi + EPS))
            ptp.append(pos + neg)
    out["pulse_biphasic_balance_median"] = float(np.median(biphasic)) if biphasic else ""
    out["pulse_peak_to_peak_median"] = float(np.median(ptp)) if ptp else ""

    # Spectral summaries from loud frames, 150 Hz to 10 kHz.
    wide_mask = (freq >= 150) & (freq <= min(10000, sample_rate/2))
    wide = power[:, wide_mask]
    wf = freq[wide_mask]
    raw_env = np.sqrt(main.sum(axis=1))
    loud_raw = raw_env >= np.percentile(raw_env, 75)
    spec = np.mean(wide[loud_raw], axis=0) if np.any(loud_raw) else np.mean(wide, axis=0)
    total = float(spec.sum()) + EPS
    p = spec / total
    centroid = float(np.sum(wf * p))
    out["spectral_centroid_hz"] = centroid
    out["spectral_bandwidth_hz"] = float(np.sqrt(np.sum(((wf-centroid)**2) * p)))
    cdf = np.cumsum(p)
    out["spectral_rolloff85_hz"] = float(wf[min(len(wf)-1, int(np.searchsorted(cdf, .85)))])
    nz = p[p > 0]
    out["spectral_entropy"] = float(-np.sum(nz * np.log(nz)) / np.log(len(p))) if len(p) > 1 else ""
    out["spectral_crest"] = float(np.max(spec) / (np.mean(spec) + EPS))

    # Frame-to-frame spectral flux.
    denom = wide.sum(axis=1, keepdims=True) + EPS
    norm = wide / denom
    if len(norm) > 1:
        flux = np.sqrt(np.sum(np.diff(norm, axis=0) ** 2, axis=1))
        out["spectral_flux_mean"] = float(np.mean(flux))
        out["spectral_flux_cv"] = float(np.std(flux, ddof=1)/(np.mean(flux)+EPS)) if len(flux) > 1 else 0.0
    else:
        out["spectral_flux_mean"] = out["spectral_flux_cv"] = ""

    # Spectral-comb diagnostic: strongest autocorrelation spacing of the log spectrum
    # corresponding to an 80-1000 Hz harmonic fundamental. Research only.
    logspec = np.log(spec + np.median(spec) * .01 + EPS)
    logspec = logspec - np.mean(logspec)
    bin_hz = float(wf[1] - wf[0]) if len(wf) > 1 else 0.0
    comb_candidates = []
    if bin_hz > 0:
        lo_lag = max(1, int(round(80/bin_hz)))
        hi_lag = min(len(logspec)//3, int(round(1000/bin_hz)))
        for lag in range(lo_lag, hi_lag+1):
            comb_candidates.append((lag, _corr(logspec[:-lag], logspec[lag:])))
    if comb_candidates:
        lag, val = max(comb_candidates, key=lambda x: x[1])
        out["spectral_comb_score"] = float(val)
        out["spectral_comb_spacing_hz"] = float(lag * bin_hz)
    else:
        out["spectral_comb_score"] = out["spectral_comb_spacing_hz"] = ""

    return out


def _gate_failures(features, acc) -> tuple[str, str, float | None, bool, bool]:
    if features is None:
        return "invalid_window", "", None, False, False
    failures = []
    checks = [
        ("peak_envelope", features.peak_envelope >= 1e-4),
        ("spectral_flatness", features.spectral_flatness >= .12),
        ("modulation", features.modulation >= .25),
        ("periodicity", features.periodicity >= .60),
        ("repeat_periodicity", features.repeat_periodicity >= .35),
        ("pulse_count", features.pulse_count >= 4),
        ("coherent_bands", features.coherent_bands >= 3),
        ("band_energy_fraction", features.band_energy_fraction >= 1e-4),
    ]
    failures = [name for name, ok in checks if not ok]
    bp = _current_broadband_pass(features)
    acc_score = screen_accompaniment(acc)
    ap = acc_score is not None
    acc_fail = ""
    if not ap and acc:
        # Summarize which accompaniment criteria fail in the best-periodicity band.
        item = max(acc, key=lambda x: x.periodicity)
        af = []
        ach = [
            ("peak_envelope", item.peak_envelope >= 1e-4), ("pulse_count", item.pulse_count >= 4),
            ("periodicity", item.periodicity >= .60), ("repeat_periodicity", item.repeat_periodicity >= .35),
            ("modulation", item.modulation >= .25), ("noise_coherence", item.noise_coherence >= .40),
            ("noise_contrast", item.noise_contrast >= .15), ("noise_ratio", item.noise_ratio >= .005),
            ("ridge_share", item.ridge_share >= .001), ("residual_bins", item.residual_bins >= 20),
        ]
        af = [n for n, ok in ach if not ok]
        acc_fail = ";".join(af)
    return ";".join(failures), acc_fail, acc_score, bp, ap


def instrument_window(samples: np.ndarray, start_sec: float) -> dict:
    # Authoritative decision: call the production WING screen unchanged. Nothing
    # measured below is allowed to feed back into this score.
    score = screen_window(samples, ANALYSIS_RATE)
    wf = window_features(samples, ANALYSIS_RATE)
    bp = _current_broadband_pass(wf)
    # Research-only accompaniment measurements are collected for every valid window,
    # including broadband-positive windows; the optional accelerator is exact and
    # falls back to NumPy if numba is absent.
    acc = fast_accompaniment_features(samples)
    acc_score = screen_accompaniment(acc)
    ap = (score is not None and not bp)
    broad_fail, acc_fail, _, _, _ = _gate_failures(wf, acc)
    row: dict[str, object] = {
        "window_start_sec": round(start_sec, 3),
        "window_end_sec": round(start_sec + len(samples)/ANALYSIS_RATE, 3),
        "window_duration_sec": round(len(samples)/ANALYSIS_RATE, 3),
        "current_detect": int(score is not None),
        "current_score": score if score is not None else "",
        "current_route": "broadband" if (score is not None and bp) else ("accompaniment" if ap else "none"),
        "broadband_pass": int(bp),
        "accompaniment_pass": int(acc_score is not None),
        "broadband_failed_gates": broad_fail,
        "accompaniment_failed_gates_best_band": acc_fail,
    }
    if wf:
        for k, v in asdict(wf).items():
            row["wing_" + k] = v
    else:
        for k in ("spectral_flatness","modulation","periodicity","repeat_periodicity","pulse_count","peak_envelope","coherent_bands","band_energy_fraction"):
            row["wing_"+k] = ""
    row.update(_broadband_detail(samples, ANALYSIS_RATE))
    amap = {a.lower_hz: a for a in acc}
    for lower, upper in SEARCH_BANDS:
        item = amap.get(lower)
        prefix = f"acc_{lower}_{upper}_"
        fields = ("periodicity","repeat_periodicity","modulation","noise_coherence","noise_contrast","noise_ratio","ridge_share","residual_bins","pulse_count","peak_envelope","noise_center_hz")
        for f in fields:
            row[prefix+f] = getattr(item, f) if item else ""
    return row


def window_slices(samples: np.ndarray):
    window = ANALYSIS_RATE * WINDOW_SECONDS
    hop = ANALYSIS_RATE * HOP_SECONDS
    offset = 0
    n = len(samples)
    while True:
        end = min(offset + window, n)
        yield offset / ANALYSIS_RATE, samples[offset:end]
        if end >= n:
            break
        offset += hop


def merged_from_rows(rows: list[dict]) -> list[tuple[float,float,float]]:
    cands: list[tuple[float,float,float]] = []
    for r in rows:
        try:
            detected = bool(int(r["current_detect"]))
        except Exception:
            detected = bool(r["current_detect"])
        if not detected:
            continue
        start, end, score = float(r["window_start_sec"]), float(r["window_end_sec"]), float(r["current_score"])
        if cands and start <= cands[-1][1]:
            old = cands.pop()
            cands.append((old[0], end, max(old[2], score)))
        else:
            cands.append((start, end, score))
    return cands


def compare_candidates(a, b, tol=5e-4) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a,b):
        xt = (x.start,x.end,x.periodicity) if hasattr(x,"start") else x
        yt = (y.start,y.end,y.periodicity) if hasattr(y,"start") else y
        if any(abs(float(i)-float(j)) > tol for i,j in zip(xt,yt)):
            return False
    return True


def load_xc_metadata(path: Path) -> dict[str, dict[str,str]]:
    if not path.exists():
        return {}
    wanted = ["id","en","gen","sp","ssp","type","q","rec","file-name","length","rmk","url"]
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = "XC" + str(r.get("id","")).strip()
            out[key] = {"meta_"+k.replace("-","_"): r.get(k,"") for k in wanted}
    return out


def load_fsd_scan(path: Path) -> dict[str, dict[str,str]]:
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                hits = int(float(r.get("candidate_count",0) or 0))
            except Exception:
                hits = 0
            labels = r.get("labels","")
            # Hard negatives: current WING hit and FSD label does not include Animal.
            if hits > 0 and "Animal" not in {x.strip() for x in labels.split(",")}:
                key = str(r["fname"]).strip()
                out[key] = {
                    "meta_labels": labels,
                    "meta_fsd_split": r.get("fsd_split", ""),
                    "meta_prior_candidate_count": r.get("candidate_count", ""),
                    "meta_prior_detections_json": r.get("detections_json", ""),
                }
    return out


def write_csv_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                fields.append(k); seen.add(k)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def consolidate(per_file: Path, out_csv: Path) -> None:
    files = sorted(per_file.glob("*.csv"))
    if not files:
        return
    header = None
    tmp = out_csv.with_suffix(out_csv.suffix+".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as dest:
        writer = None
        for p in files:
            with p.open(newline="", encoding="utf-8") as src:
                r = csv.DictReader(src)
                if writer is None:
                    header = r.fieldnames
                    writer = csv.DictWriter(dest, fieldnames=header)
                    writer.writeheader()
                for row in r:
                    writer.writerow(row)
    tmp.replace(out_csv)



def _process_one_file(path_s: str, out_file_s: str, m: dict[str,str], source: str, do_validate: bool) -> dict:
    path = Path(path_s); out_file = Path(out_file_s)
    # Long recordings can take longer than an interactive execution slice. Save
    # atomic 200-window chunks so an interrupted research run resumes rather than
    # redoing the file from the beginning.
    part_dir = out_file.parent / "_parts" / path.stem
    part_dir.mkdir(parents=True, exist_ok=True)
    existing_parts = sorted(part_dir.glob("part_*.csv"))
    skip_windows = len(existing_parts) * 200

    samples = decode_audio(path)
    chunk_rows = []
    total_windows = 0
    for widx, (start, chunk) in enumerate(window_slices(samples)):
        total_windows = widx + 1
        if widx < skip_windows:
            continue
        r = {"source": source, "file_id": path.stem, "filename": path.name, **m}
        r.update(instrument_window(chunk, start))
        r["reference_validation_match"] = ""
        chunk_rows.append(r)
        if len(chunk_rows) == 200:
            part_no = widx // 200
            write_csv_atomic(part_dir / f"part_{part_no:06d}.csv", chunk_rows)
            chunk_rows = []
    if chunk_rows:
        part_no = (total_windows - 1) // 200
        write_csv_atomic(part_dir / f"part_{part_no:06d}.csv", chunk_rows)

    # All windows are now checkpointed. Assemble the per-file table atomically.
    consolidate(part_dir, out_file)
    with out_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    reconstructed = merged_from_rows(rows)
    match = ""
    if do_validate:
        reference = detect_stream(io.BytesIO(samples.astype("<f4", copy=False).tobytes()), ANALYSIS_RATE)
        match = int(compare_candidates(reference, reconstructed))
        # Store reference validation in final per-file file without touching any
        # production WING result.
        for r in rows:
            r["reference_validation_match"] = match
        write_csv_atomic(out_file, rows)
    # Remove checkpoint pieces only after final file exists.
    for q in part_dir.glob("part_*.csv"):
        q.unlink()
    try:
        part_dir.rmdir()
    except OSError:
        pass
    return {
        "source":source,"file_id":path.stem,"filename":path.name,
        "duration_sec":round(len(samples)/ANALYSIS_RATE,3),"windows":len(rows),
        "detected_windows":sum(int(r["current_detect"]) for r in rows),
        "merged_candidates":len(reconstructed),"reference_validation_match":match,
        **m,
    }


def run_scan(audio_dir: Path, out_dir: Path, meta: dict[str,dict[str,str]], source: str, only_meta_keys: bool=False, workers: int=1, validate_reference: bool=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    per = out_dir / "per_file"
    per.mkdir(exist_ok=True)
    exts = {".wav",".mp3",".flac",".m4a",".aiff",".aif",".ogg"}
    files = sorted([p for p in audio_dir.iterdir() if p.is_file() and p.suffix.lower() in exts], key=lambda p: p.stat().st_size, reverse=True)
    if only_meta_keys:
        files = [p for p in files if p.stem in meta]
    total = len(files)
    pending=[]
    for idx,path in enumerate(files,1):
        out_file=per/f"{path.stem}.csv"
        if not out_file.exists():
            pending.append((idx,path,out_file,meta.get(path.stem,{}), validate_reference and (idx <= 5 or idx % 100 == 0)))
    print(f"{total} files selected; {len(pending)} pending; workers={workers}", flush=True)

    if workers <= 1:
        for idx,path,out_file,m,do_validate in pending:
            try:
                res=_process_one_file(str(path),str(out_file),m,source,do_validate)
                if do_validate and res.get("reference_validation_match") != 1:
                    print(f"WARNING decision mismatch: {path.name}", flush=True)
                if idx % 25 == 0 or res["merged_candidates"]:
                    print(f"[{idx}/{total}] {path.name}: {res['merged_candidates']} candidate(s)" + (f", validation={bool(res['reference_validation_match'])}" if do_validate else ""), flush=True)
            except Exception as e:
                print(f"ERROR {path}: {e}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs={pool.submit(_process_one_file,str(path),str(out_file),m,source,do_validate):(idx,path,do_validate) for idx,path,out_file,m,do_validate in pending}
            done=0
            for fut in as_completed(futs):
                idx,path,do_validate=futs[fut]; done+=1
                try:
                    res=fut.result()
                    if do_validate and res.get("reference_validation_match") != 1:
                        print(f"WARNING decision mismatch: {path.name}", flush=True)
                    if done % 25 == 0 or res["merged_candidates"] or do_validate:
                        print(f"[{done}/{len(pending)} completed; source index {idx}/{total}] {path.name}: {res['merged_candidates']} candidate(s)" + (f", validation={bool(res['reference_validation_match'])}" if do_validate else ""), flush=True)
                except Exception as e:
                    print(f"ERROR {path}: {e}", flush=True)

    # Rebuild manifest from atomic per-file outputs; this makes resumed runs complete.
    manifests=[]
    for p in sorted(per.glob("*.csv")):
        with p.open(newline="",encoding="utf-8") as f:
            rr=list(csv.DictReader(f))
        if not rr: continue
        first=rr[0]
        manifests.append({
            "source":first.get("source",""),"file_id":first.get("file_id",""),"filename":first.get("filename",""),
            "duration_sec":rr[-1].get("window_end_sec",""),"windows":len(rr),
            "detected_windows":sum(int(x.get("current_detect",0) or 0) for x in rr),
            "merged_candidates":len(merged_from_rows(rr)),
            "reference_validation_match":next((x.get("reference_validation_match","") for x in rr if x.get("reference_validation_match","") != ""),""),
            **{k:v for k,v in first.items() if k.startswith("meta_")},
        })
    write_csv_atomic(out_dir/"files.csv",manifests)
    consolidate(per,out_dir/"windows.csv")
    print(f"Done: {len(manifests)} files. Windows: {out_dir/'windows.csv'}", flush=True)

def main():
    ap=argparse.ArgumentParser(description="Research-only WING instrumentation. Production screen_window is authoritative and unchanged.")
    sub=ap.add_subparsers(dest="mode",required=True)
    x=sub.add_parser("xc")
    x.add_argument("--audio-dir",type=Path,required=True)
    x.add_argument("--metadata",type=Path,required=True)
    x.add_argument("--out",type=Path,required=True)
    x.add_argument("--workers",type=int,default=1)
    x.add_argument("--validate-reference",action="store_true")
    f=sub.add_parser("fsd-hard-negatives")
    f.add_argument("--audio-dir",type=Path,required=True)
    f.add_argument("--scan-csv",type=Path,required=True)
    f.add_argument("--out",type=Path,required=True)
    f.add_argument("--workers",type=int,default=1)
    f.add_argument("--validate-reference",action="store_true")
    args=ap.parse_args()
    if args.mode=="xc":
        run_scan(args.audio_dir,args.out,load_xc_metadata(args.metadata),"xc_positive",False,args.workers,args.validate_reference)
    else:
        meta=load_fsd_scan(args.scan_csv)
        print(f"Selected {len(meta)} non-Animal hard-negative files from scan CSV.", flush=True)
        run_scan(args.audio_dir,args.out,meta,"fsd_hard_negative",True,args.workers,args.validate_reference)

if __name__ == "__main__":
    main()
