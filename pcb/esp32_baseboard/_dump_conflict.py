"""Dump segments for known conflict nets."""
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


def show(name: str, pred):
    print(f"=== {name} ===")
    for a, b, w, layer, net in segs:
        if pred(nets[net], a, b, w, layer):
            print(f"  {nets[net]:12s} {layer} w={w} {a}->{b}")


show("OPTO_IN1", lambda n, a, b, w, l: n == "/OPTO_IN1")
show(
    "GND H ~42.54",
    lambda n, a, b, w, l: n == "GND"
    and abs(a[1] - b[1]) < 1e-3
    and abs(a[1] - 42.54) < 0.3,
)
show(
    "SNS V ~169",
    lambda n, a, b, w, l: n == "+12V_SNS"
    and abs(a[0] - b[0]) < 1e-3
    and abs(a[0] - 169) < 2,
)
show(
    "+3V3 H ~120",
    lambda n, a, b, w, l: n == "+3V3"
    and abs(a[1] - b[1]) < 1e-3
    and abs(a[1] - 120) < 0.5,
)
show(
    "GND H ~120",
    lambda n, a, b, w, l: n == "GND"
    and abs(a[1] - b[1]) < 1e-3
    and abs(a[1] - 120) < 0.5,
)
show(
    "OPTO_VCC_I",
    lambda n, a, b, w, l: n == "/OPTO_VCC_I",
)
