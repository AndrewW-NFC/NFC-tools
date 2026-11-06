"""Bounded reuse of frame-local calculations within one decoded audio stream."""
from __future__ import annotations

import numpy as np


class FrameCache:
    """Keep only overlapping frames; never cache window-dependent statistics.

    Callers supply monotonically increasing, hop-aligned sample offsets from
    one stream. Several window lengths may share the same offset. Each returned
    array has frames on axis zero, and must be treated as read-only.
    """

    def __init__(self, frame_size, hop, transform):
        self.frame_size = frame_size
        self.hop = hop
        self.transform = transform
        self.start = 0
        self.arrays = None

    def get(self, samples, offset):
        count = max(0, (len(samples) - self.frame_size) // self.hop + 1)
        delta = offset - self.start
        if (self.arrays is None or delta < 0 or delta % self.hop
                or delta // self.hop >= len(self.arrays[0])):
            self.arrays = None
        else:
            skip = delta // self.hop
            # Copy to release frames preceding the current window, even at EOF.
            if skip:
                self.arrays = tuple(a[skip:].copy() for a in self.arrays)
        self.start = offset
        kept = 0 if self.arrays is None else len(self.arrays[0])
        if count > kept:
            frames = np.lib.stride_tricks.sliding_window_view(
                samples[kept * self.hop:], self.frame_size,
            )[::self.hop]
            new = self.transform(frames)
            self.arrays = (new if self.arrays is None else
                           tuple(np.concatenate((old, extra))
                                 for old, extra in zip(self.arrays, new)))
        return tuple(a[:count] for a in self.arrays)
