import re, math, sys
src = open('esp32_baseboard.kicad_pcb', encoding='utf-8').read()
res = []
for m in re.finditer(r'\n\t\(footprint "([^"]+)"', src):
    st = m.start() + 1; d = 0; i = st
    while True:
        c = src[i]
        if c == '(': d += 1
        elif c == ')':
            d -= 1
            if d == 0: break
        i += 1
    blk = src[st:i+1]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
    ax, ay, ar = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    xs = []; ys = []
    for r in re.finditer(r'\(fp_rect\s*\n\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\n\s*\(end ([-\d.]+) ([-\d.]+)\)', blk):
        for lx, ly in ((float(r.group(1)), float(r.group(2))), (float(r.group(3)), float(r.group(4)))):
            th = math.radians(ar)
            xs.append(ax + lx*math.cos(th) - ly*math.sin(th)); ys.append(ay + lx*math.sin(th) + ly*math.cos(th))
    for p in re.finditer(r'\(pad "[^"]*" \S+ \S+\s*\n\s*\(at ([-\d.]+) ([-\d.]+)', blk):
        lx, ly = float(p.group(1)), float(p.group(2)); th = math.radians(ar)
        wx = ax + lx*math.cos(th) - ly*math.sin(th); wy = ay + lx*math.sin(th) + ly*math.cos(th)
        xs += [wx-1.0, wx+1.0]; ys += [wy-1.0, wy+1.0]
    if xs: res.append((ref, min(xs), min(ys), max(xs), max(ys)))
res.sort()
n = 0
import sys
if "--boxes" in sys.argv:
    for r in res: print(f"{r[0]:6s} x {r[1]:7.1f}..{r[3]:7.1f}  y {r[2]:7.1f}..{r[4]:7.1f}")
for i in range(len(res)):
    for k in range(i+1, len(res)):
        a, b = res[i], res[k]
        ox_ = min(a[3], b[3]) - max(a[1], b[1]); oy_ = min(a[4], b[4]) - max(a[2], b[2])
        if ox_ > 0 and oy_ > 0:
            n += 1; print(f"  OVERLAP {a[0]} x {b[0]}: {ox_:.1f} x {oy_:.1f} mm")
# Must be the Edge.Cuts rectangle, not merely the first gr_rect in the file:
# the zone boxes are gr_rects too, and once one of them sorted ahead of the
# outline every footprint read as outside the board.
bx0 = by0 = bx1 = by1 = None
for chunk in src.split('(gr_rect')[1:]:
    chunk = chunk.split('(gr_', 1)[0]
    if '"Edge.Cuts"' not in chunk:
        continue
    st = re.search(r'\(start ([\d.-]+) ([\d.-]+)\)', chunk)
    en = re.search(r'\(end ([\d.-]+) ([\d.-]+)\)', chunk)
    if st and en:
        bx0, by0 = float(st.group(1)), float(st.group(2))
        bx1, by1 = float(en.group(1)), float(en.group(2))
        break
if bx0 is None:
    raise SystemExit('no Edge.Cuts rectangle found')
out = [r for r in res if r[1] < bx0 or r[2] < by0 or r[3] > bx1 or r[4] > by1]
print(f"board outline {bx0:.0f},{by0:.0f} .. {bx1:.0f},{by1:.0f}")
for r in out:
    print(f"  OUTSIDE {r[0]}: {r[1]:.1f},{r[2]:.1f} .. {r[3]:.1f},{r[4]:.1f}")
print(f"overlaps={n} outside={len(out)}")
