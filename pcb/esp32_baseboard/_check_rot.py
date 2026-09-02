"""Allowlisted non-zero rotations (uncross nets). Other parts must stay 0°."""
import re
from pathlib import Path

# ref -> expected rotation (deg)
ALLOW = {
    "J1": 90,
    "U3": 270,
    "J18": 180,
    "U5": 180,
    "U6": 180,
    "U7": 180,
    "J5": 180,
    "J6": 180,
    "J7": 180,
}

src = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
bad = []
for m in re.finditer(r"\n\t\(footprint ", src):
    st = m.start() + 1
    d = 0
    i = st
    while True:
        c = src[i]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                break
        i += 1
    blk = src[st : i + 1]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    if ref.startswith("H"):
        continue
    at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
    rot = float(at.group(3) or 0) % 360
    expect = float(ALLOW.get(ref, 0)) % 360
    if abs(rot - expect) > 0.01 and abs(rot - expect) < 359.99:
        bad.append((ref, rot, expect))
if bad:
    print(f"FAIL {len(bad)} parts wrong rotation:")
    for r, rot, exp in bad:
        print(f"  {r} rot={rot} expected={exp}")
else:
    print(f"OK rotations (allowlist {len(ALLOW)} non-zero + rest 0°)")
