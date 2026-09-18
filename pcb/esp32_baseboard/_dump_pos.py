#!/usr/bin/env python3
import re
from pathlib import Path

text = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")


def block(s, start):
    d, i = 0, start
    while i < len(s):
        if s[i] == "(":
            d += 1
        elif s[i] == ")":
            d -= 1
            if d == 0:
                return s[start : i + 1]
        i += 1
    raise ValueError()


rows = []
for m in re.finditer(r"\n\t\(footprint \"([^\"]+)\"", text):
    blk = block(text, m.start() + 1)
    rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
    at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
    if rm and at:
        rows.append(
            (
                rm.group(1),
                float(at.group(1)),
                float(at.group(2)),
                float(at.group(3) or 0),
                m.group(1).split(":")[-1],
            )
        )
for r in sorted(rows, key=lambda t: (t[2], t[1])):
    print(f"{r[0]:12s} {r[1]:8.3f} {r[2]:8.3f} r={r[3]:6.1f}  {r[4]}")
print("count", len(rows))
