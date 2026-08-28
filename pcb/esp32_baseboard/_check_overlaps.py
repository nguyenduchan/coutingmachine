"""Detect same-layer track/pad shorts and footprint collisions."""
from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from pathlib import Path

PCB = Path(__file__).with_name("esp32_baseboard.kicad_pcb")
text = PCB.read_text(encoding="utf-8")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def seg_seg_dist(p1, p2, p3, p4) -> float:
    """Minimum distance between two finite segments (sampled)."""
    best = 1e9
    for i in range(21):
        t = i / 20
        ax, ay = p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])
        for j in range(21):
            u = j / 20
            bx, by = p3[0] + u * (p4[0] - p3[0]), p3[1] + u * (p4[1] - p3[1])
            best = min(best, math.hypot(ax - bx, ay - by))
    return best


def copper_short(d: float, w1: float, w2: float, clearance: float = 0.2) -> bool:
    """True if segment copper + clearance rules overlap (different nets)."""
    return d < (w1 + w2) * 0.5 + clearance - 1e-6


# --- outline ---
edges = re.findall(
    r'\(gr_line\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
    r'[\s\S]*?\(layer\s+"Edge\.Cuts"\)',
    text,
)
xs = [float(a) for a, b, c, d in edges] + [float(c) for a, b, c, d in edges]
ys = [float(b) for a, b, c, d in edges] + [float(d) for a, b, c, d in edges]
if xs:
    print(
        f"outline: {min(xs):.1f},{min(ys):.1f} -> {max(xs):.1f},{max(ys):.1f} "
        f"= {max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} mm"
    )

# --- segments ---
segs = []
for m in re.finditer(
    r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
    r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
    text,
):
    x1, y1, x2, y2, w, layer, net = m.groups()
    segs.append(
        {
            "p1": (float(x1), float(y1)),
            "p2": (float(x2), float(y2)),
            "w": float(w),
            "layer": layer,
            "net": int(net),
        }
    )
print(f"segments: {len(segs)}")
by_layer = defaultdict(int)
for s in segs:
    by_layer[s["layer"]] += 1
print("by layer:", dict(by_layer))

# Clearance rule (mm) — copper to copper different nets
CLEAR = 0.2

conflicts = []
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a["layer"] != b["layer"]:
            continue
        if a["net"] == b["net"]:
            continue
        d = seg_seg_dist(a["p1"], a["p2"], b["p1"], b["p2"])
        need = (a["w"] + b["w"]) / 2 + CLEAR
        if copper_short(d, a["w"], b["w"], CLEAR):
            mid = (
                (a["p1"][0] + a["p2"][0]) / 2,
                (a["p1"][1] + a["p2"][1]) / 2,
            )
            conflicts.append((d, need, a, b, mid))

conflicts.sort(key=lambda t: t[0])
print(f"\ntrack-track same-layer clearance violations: {len(conflicts)}")
# group by net pairs
pairs = defaultdict(int)
for d, need, a, b, mid in conflicts:
    key = tuple(sorted((a["net"], b["net"])))
    pairs[key] += 1
print("top net-pair hits:")
for (n1, n2), c in sorted(pairs.items(), key=lambda x: -x[1])[:25]:
    print(f"  net{n1} vs net{n2}: {c}")

print("\nsample conflicts (first 30):")
for d, need, a, b, mid in conflicts[:30]:
    print(
        f"  d={d:.3f} need={need:.3f} layer={a['layer']} "
        f"nets {a['net']}/{b['net']} near ({mid[0]:.1f},{mid[1]:.1f}) "
        f"w={a['w']:.2f}/{b['w']:.2f}"
    )

touch = [c for c in conflicts if c[0] < (c[2]["w"] + c[3]["w"]) * 0.5 - 0.02]
print(f"\ncross-net copper overlap (heuristic): {len(touch)}")
if touch:
    print("FAIL — review in KiCad DRC; regen if generator overlap")
else:
    print("PASS — no cross-net copper overlap (heuristic)")
print(f"clearance violations (incl. near-miss < {CLEAR} mm): {len(conflicts)}")

# --- net names ---
net_names = {}
for m in re.finditer(r'\(net\s+(\d+)\s+"([^"]*)"\)', text):
    net_names[int(m.group(1))] = m.group(2)
print("\nnet names for top conflicts:")
shown = set()
for d, need, a, b, mid in conflicts[:40]:
    for n in (a["net"], b["net"]):
        if n not in shown:
            print(f"  {n}: {net_names.get(n, '?')}")
            shown.add(n)

# --- footprint refs ---
# Split by footprint blocks
fps = []
for m in re.finditer(r'\(footprint\s+"([^"]+)"([\s\S]*?)\n\t\)', text):
    block = m.group(2)
    at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", block)
    ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    if at and ref:
        fps.append(
            {
                "fp": m.group(1),
                "ref": ref.group(1),
                "x": float(at.group(1)),
                "y": float(at.group(2)),
                "rot": float(at.group(3) or 0),
            }
        )
print(f"\nfootprints: {len(fps)}")
for f in sorted(fps, key=lambda z: z["ref"]):
    print(f"  {f['ref']:6s} @ {f['x']:7.2f},{f['y']:7.2f}  {f['fp'][:40]}")

# crude footprint center proximity (< 8 mm for module-sized parts)
print("\nclose footprint centers (<10 mm):")
for i, a in enumerate(fps):
    for b in fps[i + 1 :]:
        d = dist((a["x"], a["y"]), (b["x"], b["y"]))
        if d < 10 and a["ref"][0] == "U" and b["ref"][0] == "U":
            print(f"  {a['ref']}-{b['ref']}: {d:.1f} mm")
        elif d < 6:
            print(f"  {a['ref']}-{b['ref']}: {d:.1f} mm")

if touch:
    raise SystemExit(1)
raise SystemExit(0)
