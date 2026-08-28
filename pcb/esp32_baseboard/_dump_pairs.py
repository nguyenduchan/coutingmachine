"""Print top conflict segment pairs with geometry."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
nets = {int(a): b for a, b in re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)}
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


def overlap_1d(a0, a1, b0, b1, eps=0.05):
    lo = max(min(a0, a1), min(b0, b1))
    hi = min(max(a0, a1), max(b0, b1))
    return hi - lo > eps


colo = []
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        if abs(a[0][1] - a[1][1]) < 1e-4 and abs(b[0][1] - b[1][1]) < 1e-4:
            if abs(a[0][1] - b[0][1]) > (a[2] + b[2]) / 2 + 0.05:
                continue
            if overlap_1d(a[0][0], a[1][0], b[0][0], b[1][0]):
                colo.append(("H", a, b))
        if abs(a[0][0] - a[1][0]) < 1e-4 and abs(b[0][0] - b[1][0]) < 1e-4:
            if abs(a[0][0] - b[0][0]) > (a[2] + b[2]) / 2 + 0.05:
                continue
            if overlap_1d(a[0][1], a[1][1], b[0][1], b[1][1]):
                colo.append(("V", a, b))

want = {
    ("+3V3", "/MotA1"),
    ("+3V3", "/OPTO_IN4"),
    ("+12V_SNS", "/MotDC1_A"),
    ("+12V", "/DC3_IN1"),
    ("GND", "+12V"),
    ("/OPTO_IN1", "+5V"),
    ("/BLOWER", "GND"),
}
for kind, a, b in colo:
    pair = tuple(sorted((nets[a[4]], nets[b[4]])))
    if pair in want or tuple(reversed(pair)) in want:
        print(f"{kind} {nets[a[4]]} {a[0]}->{a[1]} w={a[2]}")
        print(f"   {nets[b[4]]} {b[0]}->{b[1]} w={b[2]} {a[3]}")
        print()
