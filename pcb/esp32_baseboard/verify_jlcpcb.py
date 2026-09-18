#!/usr/bin/env python3
"""JLCPCB DFM / DFA gates for the STM32 compact carrier.

Does *not* invent a pass: 0 tracks, overlapping pads, illegal holes, or
nets that exist only as names (no copper) fail. Run:

  python verify_jlcpcb.py
  python verify_pre_fab.py

Limits: jlcpcb_limits.py (JLCPCB capabilities + house 24 V / plug gap).
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import jlcpcb_limits as JLC
from pcb_parse import NetTable, pad_net

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
OUT = ROOT / "out" / "jlcpcb_verify.json"

HV_NETS = JLC.HV_NET_PREFIXES
FIELD = set(JLC.NORTH_JACKS) | set(JLC.SOUTH_JACKS)


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def _rot(fx: float, fy: float, deg: float, lx: float, ly: float) -> tuple[float, float]:
    """KiCad footprint angle is clockwise in the Y-down canvas.

    +90° maps local +Y to world +X (confirmed vs pcbnew pad coordinates).
    """
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return fx + lx * c + ly * s, fy - lx * s + ly * c


def _aabb_corners(fx: float, fy: float, fr: float, x0: float, y0: float, x1: float, y1: float):
    xs, ys = [], []
    for lx in (x0, x1):
        for ly in (y0, y1):
            wx, wy = _rot(fx, fy, fr, lx, ly)
            xs.append(wx)
            ys.append(wy)
    return min(xs), min(ys), max(xs), max(ys)


def _layer_rect(blk: str, layer: str):
    for m in re.finditer(r"\(fp_rect\s+", blk):
        rblk = _block(blk, m.start())
        if layer not in rblk:
            continue
        sm = re.search(r"\(start\s+([-\d.]+)\s+([-\d.]+)\)", rblk)
        em = re.search(r"\(end\s+([-\d.]+)\s+([-\d.]+)\)", rblk)
        if sm and em:
            return tuple(map(float, sm.groups() + em.groups()))
    return None


def aabb_gap(a, b) -> float:
    """Edge-to-edge gap; negative = overlap depth."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    gx = max(ax0, bx0) - min(ax1, bx1)  # <0 overlap in x
    gy = max(ay0, by0) - min(ay1, by1)
    if gx < 0 and gy < 0:
        return max(gx, gy)  # less-negative = shallower overlap
    if gx < 0:
        return gy
    if gy < 0:
        return gx
    return math.hypot(gx, gy)


def is_hv(net: str) -> bool:
    return any(net == p or net.startswith(p + "_") or net.startswith(p) for p in HV_NETS)


def parse_board(text: str) -> dict:
    em = re.search(
        r"\(gr_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)"
        r"[\s\S]*?Edge\.Cuts",
        text,
    )
    if not em:
        raise SystemExit("FAIL: no Edge.Cuts rect")
    x0, y0, x1, y1 = map(float, em.groups())
    th = float(re.search(r"\(thickness\s+([\d.]+)\)", text).group(1))
    layers = re.findall(r'\(\d+\s+"(F\.Cu|B\.Cu|In\d+\.Cu)"', text)
    return {
        "x0": x0, "y0": y0, "x1": x1, "y1": y1,
        "w": x1 - x0, "h": y1 - y0, "th": th,
        "cu_layers": len({*layers}),
    }


def parse_fps(text: str) -> list[dict]:
    table = NetTable(text)
    fps = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if not rm or not at:
            continue
        fx, fy, fr = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        attr = re.search(r"\(attr ([^\n)]+)", blk)
        smd = bool(attr and "smd" in attr.group(1) and "through_hole" not in attr.group(1))
        pads = []
        starts = [p.start() for p in re.finditer(r'\(pad\s+"', blk)]
        for k, ps in enumerate(starts):
            chunk = blk[ps : (starts[k + 1] if k + 1 < len(starts) else len(blk))]
            hm = re.match(r'\(pad\s+"([^"]*)"\s+(\w+)\s+(\w+)', chunk)
            if not hm:
                continue
            num, ptype, shape = hm.group(1), hm.group(2), hm.group(3)
            am = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)", chunk)
            sm = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", chunk)
            dm = re.search(r"\(drill\s+([-\d.]+)\)", chunk)
            if not am or not sm:
                continue
            wx, wy = _rot(fx, fy, fr, float(am.group(1)), float(am.group(2)))
            sx, sy = float(sm.group(1)), float(sm.group(2))
            drill = float(dm.group(1)) if dm else None
            _nid, net = pad_net(chunk, table)
            pads.append({
                "num": num, "type": ptype, "shape": shape,
                "x": wx, "y": wy, "sx": sx, "sy": sy, "drill": drill, "net": net,
            })
        crt = _layer_rect(blk, "F.CrtYd")
        fab = _layer_rect(blk, "F.Fab")
        aabb = _aabb_corners(fx, fy, fr, *crt) if crt else None
        fab_bb = _aabb_corners(fx, fy, fr, *fab) if fab else aabb
        silk_h = [
            float(x)
            for x in re.findall(
                r'\(fp_text[\s\S]{0,200}?F\.SilkS[\s\S]{0,120}?\(font\s*\(size\s+([\d.]+)',
                blk,
            )
        ]
        fps.append({
            "ref": rm.group(1), "x": fx, "y": fy, "rot": fr,
            "smd": smd, "board_only": "board_only" in blk,
            "pads": pads, "aabb": aabb, "fab": fab_bb, "silk_h": silk_h,
            "fiducial": "fiducial" in blk.lower() or rm.group(1).startswith("FID"),
        })
    return fps


def parse_tracks(text: str) -> tuple[list, list]:
    segs = []
    for m in re.finditer(
        r"\(segment\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)"
        r"\s+\(width\s+([\d.]+)\)\s+\(layer\s+\"([^\"]+)\"\)",
        text,
    ):
        segs.append(tuple(float(m.group(i)) for i in range(1, 6)) + (m.group(6),))
    vias = []
    for m in re.finditer(r"\n\t\(via\s+", text):
        blk = _block(text, m.start() + 1)
        at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\)", blk)
        sz = re.search(r"\(size\s+([\d.]+)\)", blk)
        dr = re.search(r"\(drill\s+([\d.]+)\)", blk)
        if at and sz and dr:
            vias.append((float(at.group(1)), float(at.group(2)), float(sz.group(1)), float(dr.group(1))))
    return segs, vias


def edge_ok(x: float, y: float, b: dict, clear: float) -> bool:
    return (
        x >= b["x0"] + clear and x <= b["x1"] - clear
        and y >= b["y0"] + clear and y <= b["y1"] - clear
    )


def is_edge_jack(ref: str) -> bool:
    return ref in FIELD or ref.startswith("SW_")


def pad_box(p: dict) -> tuple[float, float, float, float]:
    return (p["x"] - p["sx"] / 2, p["y"] - p["sy"] / 2,
            p["x"] + p["sx"] / 2, p["y"] + p["sy"] / 2)


def jack_row_gaps(fps: list[dict], refs: tuple[str, ...], need: float) -> list[str]:
    by = {fp["ref"]: fp for fp in fps}
    row = []
    for r in refs:
        fp = by.get(r)
        if not fp:
            return [f"missing {r}"]
        bb = fp["fab"] or fp["aabb"]
        if not bb:
            return [f"no housing {r}"]
        row.append((r, bb))
    row.sort(key=lambda t: t[1][0])
    bad = []
    for (ra, aa), (rb, bb) in zip(row, row[1:]):
        g = bb[0] - aa[2]
        if g + 1e-9 < need:
            bad.append(f"{ra}/{rb}={g:.2f}mm")
    return bad


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    b = parse_board(text)
    fps = parse_fps(text)
    segs, vias = parse_tracks(text)
    fails: list[str] = []
    warns: list[str] = []
    gates: list[dict] = []
    hole_hits: list[str] = []

    def gate(name: str, ok: bool, detail: str = "") -> None:
        gates.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            fails.append(f"{name}: {detail}" if detail else name)
        print(("  PASS " if ok else "  FAIL ") + name + (f"  {detail}" if detail else ""))

    def warn(name: str, detail: str) -> None:
        warns.append(f"{name}: {detail}")
        print(f"  WARN {name}  {detail}")

    print("=== JLCPCB DFM (bare PCB) ===")
    gate(
        "4-layer FR-4 1.6 mm (Sig/GND/PWR/Sig)",
        b["cu_layers"] == 4 and abs(b["th"] - JLC.THICKNESS_USED) < 0.05,
        f"layers={b['cu_layers']} th={b['th']}",
    )
    max_w, max_h = (JLC.BOARD_MAX_4L_MM if b["cu_layers"] >= 4 else JLC.BOARD_MAX_2L_MM)
    gate(
        "Board size in JLCPCB envelope",
        JLC.BOARD_MIN_MM <= b["w"] <= max_w
        and JLC.BOARD_MIN_MM <= b["h"] <= max_h,
        f"{b['w']:.0f}x{b['h']:.0f} mm {b['cu_layers']}L",
    )
    gate("Closed rectangular Edge.Cuts", b["w"] > 10 and b["h"] > 10)

    refs = [fp["ref"] for fp in fps]
    dup = [r for r, n in {r: refs.count(r) for r in refs}.items() if n > 1]
    gate("Unique footprint references", not dup, ",".join(dup) or "ok")

    drills = []
    pth_ann = []
    smd_min = 99.0
    for fp in fps:
        for p in fp["pads"]:
            if p["drill"]:
                drills.append((fp["ref"], p["num"], p["type"], p["drill"], p["sx"], p["sy"], p["x"], p["y"]))
                if p["type"] == "thru_hole":
                    pth_ann.append((min(p["sx"], p["sy"]) - p["drill"]) / 2)
            if p["type"] == "smd":
                smd_min = min(smd_min, p["sx"], p["sy"])

    bad_drill = [
        d for d in drills
        if (d[2] == "np_thru_hole" and d[3] < JLC.NPTH_MIN_MM)
        or (d[2] == "thru_hole" and not (JLC.DRILL_MIN_2L_MM <= d[3] <= JLC.DRILL_MAX_MM))
    ]
    gate("Drill diameters in JLCPCB range", not bad_drill, f"{len(bad_drill)} illegal")
    min_ann = min(pth_ann) if pth_ann else 1.0
    gate(
        f"PTH annular ≥ {JLC.PTH_ANNULAR_ABS_MM} mm (abs min)",
        min_ann + 1e-9 >= JLC.PTH_ANNULAR_ABS_MM,
        f"min={min_ann:.3f} mm",
    )
    if min_ann < JLC.PTH_ANNULAR_REC_MM:
        warn("PTH annular below recommended 0.20 mm", f"{min_ann:.3f}")
    gate(
        f"SMD pad ≥ {JLC.SMD_PAD_MIN_MM} mm",
        smd_min + 1e-9 >= JLC.SMD_PAD_MIN_MM,
        f"min={smd_min:.3f}",
    )

    hh_fail = 0
    holes = [(d[6], d[7], d[3], d[0], d[1]) for d in drills]
    for i, (x1, y1, d1, r1, n1) in enumerate(holes):
        for x2, y2, d2, r2, n2 in holes[i + 1 :]:
            gap = math.hypot(x1 - x2, y1 - y2) - (d1 + d2) / 2
            if gap + 1e-9 < JLC.HOLE_TO_HOLE_PAD_MM and r1 != r2:
                hh_fail += 1
                if len(hole_hits) < 8:
                    hole_hits.append(f"{r1}.{n1}↔{r2}.{n2}={gap:.3f}")
                    print(f"    hole {r1}.{n1}↔{r2}.{n2} gap={gap:.3f} mm")
    gate(
        f"Hole wall-to-wall ≥ {JLC.HOLE_TO_HOLE_PAD_MM} mm",
        hh_fail == 0,
        f"{hh_fail} pairs" + (": " + ", ".join(hole_hits) if hole_hits else ""),
    )

    npth = [d for d in drills if d[2] == "np_thru_hole"]
    gate("4× M3 NPTH mounting holes", len(npth) == JLC.NPTH_M3_COUNT, f"count={len(npth)}")
    odd_npth = [d for d in npth if abs(d[3] - JLC.NPTH_M3_MM) > 0.05]
    gate("NPTH drill is M3 Ø3.2 mm", not odd_npth, f"{len(odd_npth)} odd")

    edge_cu = []
    for fp in fps:
        for p in fp["pads"]:
            half = max(p["sx"], p["sy"]) / 2
            if p["drill"]:
                half = max(half, p["drill"] / 2)
            if not edge_ok(p["x"], p["y"], b, JLC.COPPER_TO_ROUTED_EDGE_MM + half):
                edge_cu.append(f"{fp['ref']}.{p['num']}")
    gate(
        f"Copper/hole ≥ {JLC.COPPER_TO_ROUTED_EDGE_MM} mm from routed edge",
        not edge_cu,
        ",".join(edge_cu[:8]) if edge_cu else "ok",
    )

    print("\n=== Pad-to-pad (shorts / 24 V) ===")
    pad_list = []
    for fp in fps:
        for p in fp["pads"]:
            if not p["net"]:
                continue
            pad_list.append((fp["ref"], p))
    shorts, hv_fail = [], []
    for i, (ra, pa) in enumerate(pad_list):
        ba = pad_box(pa)
        for rb, pb in pad_list[i + 1 :]:
            if ra == rb or pa["net"] == pb["net"]:
                continue
            g = aabb_gap(ba, pad_box(pb))
            need = JLC.HV_PAD_CLEAR_MM if (is_hv(pa["net"]) or is_hv(pb["net"])) else JLC.SPACE_HOUSE_MM
            if g + 1e-9 < 0:
                shorts.append(f"{ra}.{pa['num']}/{rb}.{pb['num']}")
            elif g + 1e-9 < need and (is_hv(pa["net"]) or is_hv(pb["net"])):
                hv_fail.append(f"{ra}.{pa['num']}/{rb}.{pb['num']}={g:.2f}")
            elif g + 1e-9 < need:
                shorts.append(f"{ra}.{pa['num']}/{rb}.{pb['num']}={g:.2f}")
    gate("Pads of different nets do not overlap", not shorts,
         f"{len(shorts)}: " + ", ".join(shorts[:8]) if shorts else "ok")
    gate(
        f"24 V pad clearance ≥ {JLC.HV_PAD_CLEAR_MM} mm",
        not hv_fail,
        f"{len(hv_fail)}: " + ", ".join(hv_fail[:8]) if hv_fail else "ok",
    )

    print("\n=== Tracks / vias ===")
    nseg, nvia = len(segs), len(vias)
    gate("Board is routed (tracks exist)", nseg > 0, f"segments={nseg} vias={nvia}")
    thin = [s[4] for s in segs if s[4] + 1e-9 < JLC.TRACK_HOUSE_MM]
    gate(
        f"Track width ≥ house {JLC.TRACK_HOUSE_MM} mm (JLC min {JLC.TRACK_MIN_MM})",
        not thin,
        f"{len(thin)} thinner" if thin else f"n={nseg}",
    )
    tiny_via = [v for v in vias if v[3] < JLC.VIA_HOLE_MIN_MM or v[2] < JLC.VIA_DIA_MIN_MM]
    gate("Via size ≥ JLC min (or no vias)", not tiny_via, f"{len(tiny_via)}")
    if nvia:
        odd = [v for v in vias if abs(v[3] - JLC.VIA_HOUSE[0]) > 0.02 or abs(v[2] - JLC.VIA_HOUSE[1]) > 0.02]
        if odd:
            warn("Via not 0.4/0.8 house size", f"{len(odd)} vias")
    if "blind" in text.lower() or "buried" in text.lower():
        gate("No blind/buried vias", False, "keyword found")
    else:
        gate("No blind/buried vias", True)

    by_net = defaultdict(int)
    for fp in fps:
        for p in fp["pads"]:
            if p["net"]:
                by_net[p["net"]] += 1
    multi = [n for n, c in by_net.items() if c >= 2 and n != ""]
    gate(
        "Every multi-pin net has copper (track/via/zone)",
        nseg > 0 or nvia > 0 or "(zone " in text,
        f"{len(multi)} nets need copper, segments={nseg}",
    )

    print("\n=== DFA / assembly ===")
    fids = [fp for fp in fps if fp["fiducial"]]
    if len(fids) < 3:
        warn("Fiducials", f"{len(fids)} (JLC can add rails+fiducials; or place 3× Ø1 mm)")
    smt_edge = []
    for fp in fps:
        if fp["board_only"] or is_edge_jack(fp["ref"]):
            continue
        if not fp["smd"] and not any(p["type"] == "smd" for p in fp["pads"]):
            continue
        aabb = fp["aabb"]
        if not aabb:
            continue
        x0, y0, x1, y1 = aabb
        need = JLC.ASSY_BODY_TO_EDGE_MM
        if x0 < b["x0"] + need or y0 < b["y0"] + need or x1 > b["x1"] - need or y1 > b["y1"] - need:
            smt_edge.append(fp["ref"])
    gate(
        f"SMT bodies ≥ {JLC.ASSY_BODY_TO_EDGE_MM} mm from edge (jacks excluded)",
        not smt_edge,
        ",".join(smt_edge[:10]) if smt_edge else "ok",
    )

    clashes = []
    bodies = [(fp["ref"], fp["aabb"], fp["smd"]) for fp in fps if fp["aabb"] and not fp["board_only"]]
    for i, (ra, aa, sa) in enumerate(bodies):
        ax0, ay0, ax1, ay1 = aa
        ax0 -= JLC.ASSY_COURTYARD_GAP_MM / 2
        ay0 -= JLC.ASSY_COURTYARD_GAP_MM / 2
        ax1 += JLC.ASSY_COURTYARD_GAP_MM / 2
        ay1 += JLC.ASSY_COURTYARD_GAP_MM / 2
        for rb, bb, sb in bodies[i + 1 :]:
            if not sa and not sb:
                continue  # THT↔THT: plug-gap gate below
            bx0, by0, bx1, by1 = bb
            if ax1 > bx0 and bx1 > ax0 and ay1 > by0 and by1 > ay0:
                clashes.append(f"{ra}/{rb}")
    gate(
        f"SMT courtyards do not overlap (+{JLC.ASSY_COURTYARD_GAP_MM} mm gap)",
        not clashes,
        f"{len(clashes)} pairs" + (": " + ", ".join(clashes[:8]) if clashes else ""),
    )

    n_gap = jack_row_gaps(fps, JLC.NORTH_JACKS, JLC.JACK_PLUG_GAP_MM)
    s_gap = jack_row_gaps(fps, JLC.SOUTH_JACKS, JLC.JACK_PLUG_GAP_MM)
    gate(
        f"North jack housing gap ≥ {JLC.JACK_PLUG_GAP_MM} mm",
        not n_gap,
        ", ".join(n_gap[:8]) if n_gap else "ok",
    )
    gate(
        f"South jack housing gap ≥ {JLC.JACK_PLUG_GAP_MM} mm",
        not s_gap,
        ", ".join(s_gap[:8]) if s_gap else "ok",
    )

    silk_small = 0
    for fp in fps:
        silk_small += sum(1 for h in fp["silk_h"] if h + 1e-9 < JLC.SILK_HEIGHT_MIN_MM)
    if silk_small:
        warn(
            f"Silkscreen text < {JLC.SILK_HEIGHT_MIN_MM} mm (JLC illegible)",
            f"{silk_small} texts — fab still etches copper",
        )

    print("\n=== Polarized / assembly-critical parts present ===")
    refset = {fp["ref"] for fp in fps}
    for need in JLC.POLARIZED_REFS + ("H1", "H2", "H3", "H4"):
        gate(f"Ref {need} on board", need in refset)

    overall = all(g["ok"] for g in gates)
    report = {
        "overall": "PASS" if overall else "FAIL",
        "board_mm": [b["w"], b["h"], b["th"]],
        "segments": nseg,
        "vias": nvia,
        "gates": gates,
        "fails": fails,
        "warns": warns,
        "courtyard_clashes": clashes[:40],
        "hole_hits": hole_hits,
        "source": "https://jlcpcb.com/capabilities/pcb-capabilities",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nOVERALL: {report['overall']}  ({len(fails)} fail, {len(warns)} warn)")
    print(f"Wrote {OUT}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
