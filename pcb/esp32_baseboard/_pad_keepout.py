"""Header/hole keepout: tracks must not cross foreign J*/H* pads."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
net_names = {int(a): b for a, b in re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)}

parts = re.split(r'(?=\t\(footprint )', text)
pads = []
for block in parts:
    if not block.lstrip().startswith("(footprint "):
        continue
    at = re.search(r'\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)', block)
    if not at:
        continue
    fx, fy = float(at.group(1)), float(at.group(2))
    rot = float(at.group(3) or 0)
    rad = math.radians(rot)
    c, s = math.cos(rad), math.sin(rad)
    ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    ref = ref_m.group(1) if ref_m else "?"
    # Focus: connectors + mounting holes
    if not (ref.startswith("J") or ref.startswith("H")):
        continue
    for pm in re.finditer(
        r'\(pad\s+"[^"]*"\s+(?:thru_hole|np_thru_hole)\s+\w+'
        r'[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+[\d.-]+)?\)'
        r'[\s\S]*?\(size\s+([\d.-]+)\s+([\d.-]+)\)'
        r'[\s\S]*?\(drill\s+([\d.-]+)\)',
        block,
    ):
        lx, ly = float(pm.group(1)), float(pm.group(2))
        sx, sy = float(pm.group(3)), float(pm.group(4))
        drill = float(pm.group(5))
        chunk = pm.group(0)
        nm = re.search(r'\(net\s+(\d+)\s+"', chunk)
        net = int(nm.group(1)) if nm else 0
        wx = fx + lx * c - ly * s
        wy = fy + lx * s + ly * c
        r = max(sx, sy, drill) / 2 + 0.25
        pads.append((wx, wy, r, net, ref))

segs = []
for m in re.finditer(
    r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
    r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
    text,
):
    x1, y1, x2, y2, w, layer, net = m.groups()
    segs.append(
        ((float(x1), float(y1)), (float(x2), float(y2)), float(w), layer, int(net))
    )


def dist_point_seg(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln2 = dx * dx + dy * dy or 1e-18
    t = max(0, min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / ln2))
    qx, qy = a[0] + t * dx, a[1] + t * dy
    return math.hypot(px - qx, py - qy), t


hits = []
for seg in segs:
    a, b, w, layer, net = seg
    for px, py, pr, pnet, ref in pads:
        if pnet == net and pnet != 0:
            continue
        # skip endpoint fanout to this pad
        if math.hypot(a[0] - px, a[1] - py) < pr + 1.0 or math.hypot(
            b[0] - px, b[1] - py
        ) < pr + 1.0:
            continue
        d, t = dist_point_seg(px, py, a, b)
        need = pr + w / 2 + 0.2
        if d < need:
            hits.append(
                (
                    need - d,
                    ref,
                    net_names.get(net, str(net)),
                    net_names.get(pnet, "NPTH" if pnet == 0 else str(pnet)),
                    a,
                    b,
                    (px, py),
                    layer,
                )
            )

hits.sort(reverse=True)
print(f"J*/H* pads: {len(pads)}")
print(f"track-through-foreign-header/hole: {len(hits)}")
by_ref = defaultdict(int)
for gap, ref, nseg, npad, a, b, p, layer in hits:
    by_ref[ref] += 1
print("by ref:")
for ref, c in sorted(by_ref.items(), key=lambda x: -x[1]):
    print(f"  {c:4d}  {ref}")
print("worst 25:")
for gap, ref, nseg, npad, a, b, p, layer in hits[:25]:
    print(
        f"  pen={gap:.2f}  {nseg} through {ref}/{npad} @({p[0]:.1f},{p[1]:.1f})"
        f"  {a}->{b} {layer}"
    )
