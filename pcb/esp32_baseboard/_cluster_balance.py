"""Analyze TOP/BOTTOM module-cluster balance on esp32_baseboard.kicad_pcb."""
from __future__ import annotations

import math
import re
from pathlib import Path

PCB = Path(__file__).with_name("esp32_baseboard.kicad_pcb")
src = PCB.read_text(encoding="utf-8")

bx0 = by0 = bx1 = by1 = None
for chunk in src.split("(gr_rect")[1:]:
    chunk = chunk.split("(gr_", 1)[0]
    if '"Edge.Cuts"' not in chunk:
        continue
    st = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", chunk)
    en = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", chunk)
    if st and en:
        bx0, by0 = float(st.group(1)), float(st.group(2))
        bx1, by1 = float(en.group(1)), float(en.group(2))
        break
assert bx0 is not None
bw, bh = bx1 - bx0, by1 - by0
bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
board_a = bw * bh

print(f"BOARD {bw:.0f}x{bh:.0f} mm  origin=({bx0:.0f},{by0:.0f})  center=({bcx:.1f},{bcy:.1f})")
print(f"  area={board_a:.0f} mm2")

clusters: list[dict] = []
for part in re.split(r"\n\t\(gr_rect\n", src)[1:]:
    blk = part.split("\n\t(gr_", 1)[0]
    if "Eco1.User" not in blk and "Eco2.User" not in blk:
        continue
    st = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", blk)
    en = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", blk)
    face = "TOP" if "Eco1.User" in blk else "BOT"
    x0, y0 = float(st.group(1)), float(st.group(2))
    x1, y1 = float(en.group(1)), float(en.group(2))
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    clusters.append({"face": face, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "label": "?"})

for m in re.finditer(
    r'\(gr_text "([^"]+)"\s*\n\s*\(at ([\d.-]+) ([\d.-]+)', src
):
    label, lx, ly = m.group(1), float(m.group(2)), float(m.group(3))
    tail = src[m.end() : m.end() + 220]
    if "Eco1.User" in tail:
        face = "TOP"
    elif "Eco2.User" in tail:
        face = "BOT"
    else:
        continue
    best = None
    bd = 1e18
    for c in clusters:
        if c["face"] != face:
            continue
        cx = (c["x0"] + c["x1"]) / 2
        cy = (c["y0"] + c["y1"]) / 2
        d = (lx - cx) ** 2 + (ly - cy) ** 2
        if c["x0"] - 2 <= lx <= c["x1"] + 2 and c["y0"] - 2 <= ly <= c["y1"] + 2:
            d *= 0.01
        if d < bd:
            bd = d
            best = c
    if best is not None and best["label"] == "?":
        best["label"] = label

fps: list[dict] = []
for m in re.finditer(r'\n\t\(footprint "([^"]+)"', src):
    st = m.start() + 1
    d = 0
    i = st
    while True:
        ch = src[i]
        if ch == "(":
            d += 1
        elif ch == ")":
            d -= 1
            if d == 0:
                break
        i += 1
    blk = src[st : i + 1]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    lm = re.search(r'\n\t\t\(layer "(F|B)\.Cu"\)', blk)
    face = "TOP" if lm and lm.group(1) == "F" else "BOT"
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
    for p in re.finditer(
        r'\(pad "[^"]*" \S+ \S+\s*\n\s*\(at ([-\d.]+) ([-\d.]+)', blk
    ):
        lx, ly = float(p.group(1)), float(p.group(2))
        th = math.radians(ar)
        wx = ax + lx * math.cos(th) - ly * math.sin(th)
        wy = ay + lx * math.sin(th) + ly * math.cos(th)
        xs += [wx - 1, wx + 1]
        ys += [wy - 1, wy + 1]
    if xs:
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        fps.append(
            {
                "ref": ref,
                "face": face,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "a": (x1 - x0) * (y1 - y0),
            }
        )


def analyze(face: str, items: list[dict], kind: str) -> dict:
    print(f"\n======== {face} — {kind} ({len(items)}) ========")
    out: dict = {"face": face, "kind": kind, "n": len(items)}
    if not items:
        return out
    q = {"NW": 0.0, "NE": 0.0, "SW": 0.0, "SE": 0.0}
    ax = ay = at = 0.0
    rows = []
    for it in items:
        a = it.get("a") or (it["x1"] - it["x0"]) * (it["y1"] - it["y0"])
        cx = (it["x0"] + it["x1"]) / 2
        cy = (it["y0"] + it["y1"]) / 2
        ax += cx * a
        ay += cy * a
        at += a
        qn = ("N" if cy < bcy else "S") + ("W" if cx < bcx else "E")
        q[qn] += a
        w, h = it["x1"] - it["x0"], it["y1"] - it["y0"]
        name = it.get("label") or it.get("ref") or "?"
        rows.append(
            {
                "name": name,
                "w": w,
                "h": h,
                "a": a,
                "cx": cx,
                "cy": cy,
                "dx": cx - bcx,
                "dy": cy - bcy,
                "q": qn,
            }
        )
        print(
            f"  {name[:48]:48s} box={w:5.1f}x{h:5.1f} a={a:6.0f} "
            f"ctr=({cx:6.1f},{cy:6.1f}) d=({cx - bcx:+5.1f},{cy - bcy:+5.1f}) {qn}"
        )
    comx, comy = ax / at, ay / at
    vals = list(q.values())
    mean = sum(vals) / 4
    cv = (sum((v - mean) ** 2 for v in vals) / 4) ** 0.5 / mean if mean else 0
    cxs = [(it["x0"] + it["x1"]) / 2 for it in items]
    cys = [(it["y0"] + it["y1"]) / 2 for it in items]
    print(f"  Σ area={at:.0f} mm2  coverage={100 * at / board_a:.1f}% (AABB sum)")
    print(
        f"  area COM=({comx:.1f},{comy:.1f})  offset=({comx - bcx:+.1f},{comy - bcy:+.1f}) mm"
    )
    print(
        f"  quadrant NW={q['NW']:.0f} NE={q['NE']:.0f} SW={q['SW']:.0f} SE={q['SE']:.0f}  CV={cv:.2f}"
    )
    print(
        f"  center span X={max(cxs) - min(cxs):.0f}/{bw:.0f}  Y={max(cys) - min(cys):.0f}/{bh:.0f}"
    )
    grid = []
    nx, ny = 4, 3
    print("  grid occupancy:")
    for j in range(ny):
        row = []
        for i in range(nx):
            gx0 = bx0 + i * bw / nx
            gx1 = bx0 + (i + 1) * bw / nx
            gy0 = by0 + j * bh / ny
            gy1 = by0 + (j + 1) * bh / ny
            hit = any(
                min(it["x1"], gx1) > max(it["x0"], gx0)
                and min(it["y1"], gy1) > max(it["y0"], gy0)
                for it in items
            )
            row.append(1 if hit else 0)
        grid.append(row)
        print(
            "   ",
            " ".join("##" if h else ".." for h in row),
            f"  y={by0 + j * bh / ny:.0f}..{by0 + (j + 1) * bh / ny:.0f}",
        )
    out.update(
        {
            "area": at,
            "coverage_pct": 100 * at / board_a,
            "com": (comx, comy),
            "offset": (comx - bcx, comy - bcy),
            "q": q,
            "cv": cv,
            "span": (max(cxs) - min(cxs), max(cys) - min(cys)),
            "rows": rows,
            "grid": grid,
        }
    )
    return out


stats = []
for face in ("TOP", "BOT"):
    stats.append(analyze(face, [c for c in clusters if c["face"] == face], "clusters"))
for face in ("TOP", "BOT"):
    stats.append(analyze(face, [f for f in fps if f["face"] == face], "footprints"))

print("\n======== same-face cluster AABB overlaps ========")
for face in ("TOP", "BOT"):
    cs = [c for c in clusters if c["face"] == face]
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            a, b = cs[i], cs[j]
            ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            if ox > 0 and oy > 0:
                print(
                    f"  {face} OVERLAP {a['label'][:32]} x {b['label'][:32]}: "
                    f"{ox:.1f}x{oy:.1f}"
                )

# Verdict helpers
print("\n======== VERDICT ========")
for s in stats:
    if s["kind"] != "clusters":
        continue
    face = s["face"]
    dx, dy = s["offset"]
    cv = s["cv"]
    empty = sum(1 for row in s["grid"] for v in row if not v)
    issues = []
    if abs(dx) > bw * 0.12:
        issues.append(f"COM lech X {dx:+.0f} mm (>12% ban board)")
    if abs(dy) > bh * 0.15:
        issues.append(f"COM lech Y {dy:+.0f} mm")
    if cv > 0.55:
        issues.append(f"quadrant CV={cv:.2f} (lech manh)")
    elif cv > 0.35:
        issues.append(f"quadrant CV={cv:.2f} (lech vua)")
    if empty >= 4:
        issues.append(f"{empty}/12 o luoi trong")
    if not issues:
        print(f"  {face} clusters: OK - phan bo tuong doi deu")
    else:
        print(f"  {face} clusters: " + "; ".join(issues))

# JSON for canvas / docs
import json

payload = {
    "board": {"w": bw, "h": bh, "ox": bx0, "oy": by0, "cx": bcx, "cy": bcy},
    "stats": [
        {
            k: (list(v) if isinstance(v, tuple) else v)
            for k, v in s.items()
            if k != "rows" or True
        }
        for s in stats
    ],
}
# Make JSON-serializable
def _ser(o):
    if isinstance(o, dict):
        return {k: _ser(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_ser(x) for x in o]
    return o

Path(__file__).with_name("_cluster_balance.json").write_text(
    json.dumps(_ser(payload), indent=2), encoding="utf-8"
)
print("wrote _cluster_balance.json")
