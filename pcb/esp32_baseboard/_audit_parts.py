#!/usr/bin/env python3
"""Audit carrier PCB for redundant / duplicate-function parts."""
from __future__ import annotations
import re
from pathlib import Path

PCB = Path(__file__).resolve().parent / "esp32_baseboard.kicad_pcb"
text = PCB.read_text(encoding="utf-8")

parts = []
for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
    # find block end roughly via next footprint or zone
    start = m.start() + 1
    nxt = text.find("\n\t(footprint ", start + 10)
    if nxt < 0:
        nxt = text.find("\n\t(zone", start)
    blk = text[start:nxt if nxt > 0 else start + 5000]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
    val = re.search(r'\(property "Value" "([^"]+)"', blk)
    if not ref:
        continue
    parts.append((ref.group(1), val.group(1) if val else "?", m.group(1).split(":")[-1]))

print(f"{'REF':6} {'VALUE':22} FOOTPRINT")
print("-" * 60)
for r, v, f in sorted(parts, key=lambda x: (re.sub(r"\d+", "", x[0]), int(re.sub(r"\D", "", x[0]) or 0))):
    print(f"{r:6} {v:22} {f}")
print(f"\nTotal footprints: {len(parts)}")
print("segments", text.count("(segment"))
print("vias", len(re.findall(r"\n\t\(via\b", text)))
