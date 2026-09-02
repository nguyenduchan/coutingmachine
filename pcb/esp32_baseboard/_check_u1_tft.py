"""Check U1 vs MCU cluster and TFT silk order on PCB."""
import math
import re
from pathlib import Path

src = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")

def fp_block(ref: str) -> str:
    key = f'(property "Reference" "{ref}"'
    i = src.find(key)
    if i < 0:
        raise SystemExit(f"missing {ref}")
    # walk back to footprint start
    st = src.rfind("\n\t(footprint ", 0, i)
    d = 0
    j = st + 1
    while j < len(src):
        if src[j] == "(":
            d += 1
        elif src[j] == ")":
            d -= 1
            if d == 0:
                return src[st + 1 : j + 1]
        j += 1
    raise SystemExit("unbalanced")

for ref in ("U1", "J17", "J23"):
    blk = fp_block(ref)
    at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
    ax, ay, ar = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    layer = re.search(r'\n\t\t\(layer "(F|B)\.Cu"\)', blk).group(1)
    print(f"\n{ref} at=({ax},{ay}) rot={ar} layer={layer}.Cu")
    labels = re.findall(r'\(fp_text user "([^"]+)"\s*\n\s*\(at ([-\d.]+) ([-\d.]+)', blk)
    pads = []
    for pm in re.finditer(
        r'\(pad "(\d+)"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)\)[\s\S]*?(?:\(net \d+ "([^"]+)"\))?',
        blk,
    ):
        pads.append((pm.group(1), float(pm.group(2)), float(pm.group(3)), pm.group(4)))
    if labels:
        print("  silk local:", [(n, float(x), float(y)) for n, x, y in labels])
    # world Y of each pad (rot 180: wy = ay - ly)
    th = math.radians(ar)
    world = []
    for num, lx, ly, net in pads:
        wx = ax + lx * math.cos(th) - ly * math.sin(th)
        wy = ay + lx * math.sin(th) + ly * math.cos(th)
        world.append((num, wx, wy, net))
    world.sort(key=lambda t: t[2])  # north to south by Y
    print("  pads N→S (world Y):")
    for num, wx, wy, net in world[:20]:
        print(f"    pad{num:3s} y={wy:7.2f} net={net}")
    if ref == "U1":
        xs = [w[1] for w in world]
        ys = [w[2] for w in world]
        print(f"  pad bbox x={min(xs):.1f}..{max(xs):.1f} y={min(ys):.1f}..{max(ys):.1f}")
        print(f"  pad center=({(min(xs)+max(xs))/2:.1f},{(min(ys)+max(ys))/2:.1f})")

# MCU cluster rect
print("\nMCU Eco2 rects:")
for part in re.split(r"\n\t\(gr_rect\n", src)[1:]:
    blk = part.split("\n\t(gr_", 1)[0]
    if "Eco2.User" not in blk:
        continue
    st = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", blk)
    en = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", blk)
    x0, y0, x1, y1 = map(float, (st.group(1), st.group(2), en.group(1), en.group(2)))
    # find following text within next 400 chars of original - approximate by center
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    print(f"  box ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) ctr=({cx:.1f},{cy:.1f})")

expect_lcd = ["VCC", "GND", "CS", "RESET", "DC", "SDI", "SCK", "LED", "SDO"]
expect_tp = ["T_CLK", "T_CS", "T_DIN", "T_DO", "T_IRQ"]
print("\nMSP3520 expect LCD:", expect_lcd)
print("MSP3520 expect TP :", expect_tp)
