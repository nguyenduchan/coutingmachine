"""Dump segments for current top conflict nets."""
from __future__ import annotations

import re
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

for name in ("/OPTO_IN7", "+12V", "+3V3", "GND", "/OPTO_IN1", "/OPTO_IN5"):
    print(f"=== {name} (sample) ===")
    n = 0
    for a, b, w, layer, net in segs:
        if nets[net] != name:
            continue
        # filter long / interesting
        length = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if length < 5 and name not in ("+3V3", "GND"):
            continue
        print(f"  {layer} w={w} {a}->{b}")
        n += 1
        if n >= 8:
            break
