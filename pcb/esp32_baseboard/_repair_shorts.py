#!/usr/bin/env python3
"""Repair shorts / opens introduced by clearance nudges."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

PCB = Path("esp32_baseboard.kicad_pcb")
text = PCB.read_text(encoding="utf-8")


def del_uuid(uid: str) -> bool:
    global text
    for kind in ("segment", "via"):
        for m in re.finditer(rf"\n\t\({kind}\b[\s\S]*?\n\t\)", text):
            if uid in m.group(0):
                text = text[: m.start()] + text[m.end() :]
                print("del", uid[:8])
                return True
    print("miss", uid[:8])
    return False


def add_seg(x1, y1, x2, y2, w, layer, net) -> None:
    global text
    uid = str(uuid.uuid4())
    block = (
        f"\n\t(segment\n"
        f"\t\t(start {x1:g} {y1:g})\n"
        f"\t\t(end {x2:g} {y2:g})\n"
        f"\t\t(width {w:g})\n"
        f'\t\t(layer "{layer}")\n'
        f'\t\t(net "{net}")\n'
        f'\t\t(uuid "{uid}")\n'
        f"\t)"
    )
    # Insert before the final closing paren of the pcb file
    idx = text.rfind("\n)")
    text = text[:idx] + block + text[idx:]
    print(f"add {net} ({x1:g},{y1:g})-({x2:g},{y2:g})")


# 1) Restore +24V near PTC
text = text.replace(
    "(start 77.5 99.6)\n\t\t(end 75.4 97.5)\n\t\t(width 0.7)\n"
    '\t\t(layer "F.Cu")\n\t\t(net "+24V")',
    "(start 76.8242 98.8812)\n\t\t(end 74.743 96.8)\n\t\t(width 0.7)\n"
    '\t\t(layer "F.Cu")\n\t\t(net "+24V")',
)
for a, b in (
    ("(end 77.5 99.6)", "(end 76.8242 98.8812)"),
    ("(start 77.5 99.6)", "(start 76.8242 98.8812)"),
    ("(end 75.4 97.5)", "(end 74.743 96.8)"),
    ("(start 75.4 97.5)", "(start 74.743 96.8)"),
):
    text = text.replace(a, b)
print("restored +24V PTC run")

# 2) +3V3 U1 pad connection: vertical stub from pad then west
# Current broken: start 153.175 64.8 end 150 64.8 — replace with elbow from pad
if "(start 153.175 64.8)\n\t\t(end 150 64.8)" in text:
    text = text.replace(
        "(start 153.175 64.8)\n\t\t(end 150 64.8)",
        "(start 153.175 65.5)\n\t\t(end 153.175 64.7)",
    )
    add_seg(153.175, 64.7, 150, 64.7, 0.35, "F.Cu", "+3V3")
elif "(start 153.175 65.5)\n\t\t(end 150 65.5)" in text:
    text = text.replace(
        "(start 153.175 65.5)\n\t\t(end 150 65.5)",
        "(start 153.175 65.5)\n\t\t(end 153.175 64.7)",
    )
    add_seg(153.175, 64.7, 150, 64.7, 0.35, "F.Cu", "+3V3")
else:
    print("warn: U1 +3V3 fanout pattern not found")
# Fix continuation that still says 150 64.8
text = text.replace("(start 150 64.8)", "(start 150 64.7)")
text = text.replace("(end 150 64.8)", "(end 150 64.7)")

# 3) Kill +3V3 spur into U_PWR1
del_uuid("ec3b27c1-d2e6-4587-9103-fd157325593a")
text = text.replace(
    "(start 146.590299 133)\n\t\t(end 139.0 140.59)",
    "(start 146.590299 133)\n\t\t(end 146.590299 136)",
)
text = text.replace("(start 139.0 140.59)", "(start 146.590299 136)")
text = text.replace("(end 139.0 140.59)", "(end 146.590299 136)")
print("trimmed +3V3 south spur")

# 4) GND around Cc — delete diagonal, add L west of pad
del_uuid("804c2f73-bd83-4baa-a43b-b7e539390038")
add_seg(89.6, 97.15, 87.0, 97.15, 1.0, "F.Cu", "GND")
add_seg(87.0, 97.15, 87.0, 102.5, 1.0, "F.Cu", "GND")
add_seg(87.0, 102.5, 93.6, 102.5, 1.0, "F.Cu", "GND")
add_seg(93.6, 102.5, 93.6, 102.0, 1.0, "F.Cu", "GND")

PCB.write_text(text, encoding="utf-8")
print("written ok")
