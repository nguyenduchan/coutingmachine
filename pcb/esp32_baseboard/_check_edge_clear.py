"""Check module footprints stay ≥ CLEAR mm inside Edge.Cuts (exclude mounting holes)."""
import math
import re
from pathlib import Path

CLEAR = 10.0
src = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
bx0 = by0 = bx1 = by1 = None
for chunk in src.split("(gr_rect")[1:]:
    if "Edge.Cuts" not in chunk.split("(gr_", 1)[0]:
        continue
    st = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", chunk)
    en = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", chunk)
    bx0, by0 = float(st.group(1)), float(st.group(2))
    bx1, by1 = float(en.group(1)), float(en.group(2))
    break
ix0, iy0, ix1, iy1 = bx0 + CLEAR, by0 + CLEAR, bx1 - CLEAR, by1 - CLEAR
print(f"board {bx1 - bx0:.0f}x{by1 - by0:.0f} usable ({ix0:.0f},{iy0:.0f})-({ix1:.0f},{iy1:.0f})")
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
    ax, ay, ar = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    xs: list[float] = []
    ys: list[float] = []
    for r in re.finditer(
        r"\(fp_rect\s*\n\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\n\s*\(end ([-\d.]+) ([-\d.]+)\)",
        blk,
    ):
        for lx, ly in (
            (float(r.group(1)), float(r.group(2))),
            (float(r.group(3)), float(r.group(4))),
        ):
            th = math.radians(ar)
            xs.append(ax + lx * math.cos(th) - ly * math.sin(th))
            ys.append(ay + lx * math.sin(th) + ly * math.cos(th))
    if not xs:
        continue
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if x0 < ix0 or y0 < iy0 or x1 > ix1 or y1 > iy1:
        bad.append((ref, x0, y0, x1, y1))
if bad:
    print(f"FAIL {len(bad)} footprints breach {CLEAR} mm edge clear:")
    for b in bad:
        print(f"  {b}")
else:
    print(f"OK all non-mount footprints ≥ {CLEAR} mm from Edge.Cuts")
