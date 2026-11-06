"""Independent frozen measurement implementation for the November 6 candidate."""

import numpy as np


def metrics(x, f):
    n = 512
    hop = 120
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    power = abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2
    freq = np.fft.rfftfreq(n, 1 / 24000)
    mask = (freq >= max(700, f["noise_center_hz"] - 1200)) & (
        freq <= min(9500, f["noise_center_hz"] + 1200)
    )
    p = power[:, mask]
    hz = freq[mask]
    p = np.maximum(0, p - np.percentile(p, 20, axis=0))
    energy = p.sum(axis=1)
    on = energy >= np.percentile(energy, 75)
    q = p / (energy[:, None] + 1e-20)
    centroid = q @ hz
    width = (p.sum(axis=1) ** 2 / (np.sum(p * p, axis=1) + 1e-20)) * 24000 / n
    agg = p[on].mean(axis=0)
    aggwidth = agg.sum() ** 2 / (np.sum(agg * agg) + 1e-20) * 24000 / n
    adjacent = on[1:] & on[:-1]
    dot = (np.sqrt(q[1:] * q[:-1])).sum(axis=1)
    return dict(
        width=float(np.median(width[on])),
        aggregate_width=float(aggwidth),
        width_ratio=float(np.median(width[on]) / aggwidth),
        centroid_range=float(
            np.percentile(centroid[on], 90) - np.percentile(centroid[on], 10)
        ),
        speed=float(np.median(abs(np.diff(centroid))[adjacent]))
        if adjacent.any()
        else 0,
        similarity=float(np.median(dot[adjacent])) if adjacent.any() else 1,
    )


def veto(m):
    return (
        m["old"]["low_band_fraction"] < 0.0005
        and m["centroid_range"] >= 700
        and m["width_ratio"] <= 0.8
    )
