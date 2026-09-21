#!/usr/bin/env python3
"""Estimate 74HC595-24 module pin geometry from product photo."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
import numpy as np

p = Path(__file__).resolve().parent / "_595mod_scrape" / "full_0.png"
im = Image.open(p).convert("RGB")
arr = np.asarray(im)
h, w, _ = arr.shape
print("size", w, h)

# Gold pads are yellowish; find bright yellow-ish pixels
r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
mask = (r > 160) & (g > 120) & (b < 100) & (r > g) & (g > b + 20)
ys, xs = np.where(mask)
print("gold pixels", len(xs))
if len(xs) < 10:
    # try broader
    mask = (r > 140) & (g > 100) & (b < 120) & (r > b + 40)
    ys, xs = np.where(mask)
    print("gold pixels2", len(xs))

# cluster by x for bottom row (high y)
bottom = ys > h * 0.55
bx, by = xs[bottom], ys[bottom]
print("bottom gold", len(bx), "y range", by.min() if len(by) else None, by.max() if len(by) else None)

# histogram of x
if len(bx):
    hist = np.bincount(bx)
    # peaks
    peaks = []
    for i in range(2, len(hist) - 2):
        if hist[i] >= hist[i - 1] and hist[i] >= hist[i + 1] and hist[i] > 5:
            if not peaks or i - peaks[-1] > 8:
                peaks.append(i)
            elif hist[i] > hist[peaks[-1]]:
                peaks[-1] = i
    print("x peaks", len(peaks), peaks[:30], "..." if len(peaks) > 30 else "")
    if len(peaks) >= 2:
        gaps = np.diff(peaks)
        print("median gap px", float(np.median(gaps)), "gaps", gaps[:24])

# left/right short headers: x near edges
left = xs < w * 0.18
right = xs > w * 0.82
for name, sel in ("left", left), ("right", right):
    lx, ly = xs[sel], ys[sel]
    if len(ly) < 5:
        print(name, "few")
        continue
    # y peaks
    hist = np.bincount(ly)
    peaks = []
    for i in range(2, len(hist) - 2):
        if hist[i] >= hist[i - 1] and hist[i] >= hist[i + 1] and hist[i] > 3:
            if not peaks or i - peaks[-1] > 6:
                peaks.append(i)
            elif hist[i] > hist[peaks[-1]]:
                peaks[-1] = i
    print(name, "y peaks", len(peaks), peaks)
    if len(peaks) >= 2:
        print(name, "median gap", float(np.median(np.diff(peaks))))
