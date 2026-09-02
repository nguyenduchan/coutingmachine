"""E11.14: every non-mount footprint must have all pads inside some Eco1 cluster."""
import math
import re
import sys
from pathlib import Path


def balanced_blocks(src: str, start_token: str):
    idx = 0
    while True:
        i = src.find(start_token, idx)
        if i < 0:
            return
        d = 0
        j = i
        while j < len(src):
            if src[j] == "(":
                d += 1
            elif src[j] == ")":
                d -= 1
                if d == 0:
                    j += 1
                    break
            j += 1
        yield src[i:j], j
        idx = j


src = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")

clusters = []
for blk, end in balanced_blocks(src, "(gr_rect"):
    if "Eco1.User" not in blk:
        continue
    st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
    en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
    x0, y0 = float(st.group(1)), float(st.group(2))
    x1, y1 = float(en.group(1)), float(en.group(2))
    t = re.match(r'\s*\(gr_text "([^"]+)"', src[end : end + 300])
    lab = t.group(1) if t else "?"
    clusters.append((lab, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

print(f"Eco1 clusters: {len(clusters)}")
for lab, *b in clusters:
    print(f"  {lab[:55]:55} ({b[0]:.1f},{b[1]:.1f})-({b[2]:.1f},{b[3]:.1f})")


def in_any(wx, wy, slack=0.15):
    for lab, x0, y0, x1, y1 in clusters:
        if x0 - slack <= wx <= x1 + slack and y0 - slack <= wy <= y1 + slack:
            return lab
    return None


outside = []
for blk, _ in balanced_blocks(src, "\n\t(footprint "):
    ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
    if not ref_m:
        continue
    ref = ref_m.group(1)
    if ref.startswith("H"):
        continue
    at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
    ax, ay = float(at.group(1)), float(at.group(2))
    rot = float(at.group(3) or 0)
    r = math.radians(rot)
    c, s = math.cos(r), math.sin(r)
    bad = []
    # footprint origin
    if not in_any(ax, ay):
        bad.append(("at", ax, ay))
    for pm in re.finditer(r'\(pad "[^"]+"[^\n]*\n\t\t\t\(at ([-\d.]+) ([-\d.]+)', blk):
        lx, ly = float(pm.group(1)), float(pm.group(2))
        wx = ax + lx * c + ly * s
        wy = ay - lx * s + ly * c
        if not in_any(wx, wy):
            bad.append((pm.group(0)[5:12], wx, wy))
    if bad:
        outside.append((ref, ax, ay, bad[:3]))

print(f"\nOUTSIDE (pad/at not in any Eco): {len(outside)}")
for ref, ax, ay, bad in sorted(outside, key=lambda t: t[0]):
    pts = ", ".join(f"{n}@({x:.1f},{y:.1f})" for n, x, y in bad)
    print(f"  {ref:6} @({ax:.1f},{ay:.1f})  {pts}")

sys.exit(1 if outside else 0)
