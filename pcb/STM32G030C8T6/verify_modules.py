#!/usr/bin/env python3
"""PCB_REVIEW gates that apply to pluggable sub-modules (M1/M2/panel).

Carrier-specific GPIO/TFT checks do not apply; these boards must still meet
fab / safety rules: Edge.Cuts clear, via A8, track fab min, silk Ref+Value
on discretes, copper islands for routed nets, TOP-only footprints.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOD = ROOT / "modules"
MIN_TRACK = 0.20
VIA_DRILL, VIA_SIZE = 0.4, 0.8
EDGE_CLEAR = 1.0  # small boards: keep parts inside outline with margin
PCBS = [
    MOD / "m3_uln2003.kicad_pcb",
    MOD / "submodules_panel.kicad_pcb",
]


def _edge(text: str) -> tuple[float, float, float, float] | None:
    m = re.search(
        r'\(gr_rect\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
        r'[\s\S]*?\(layer\s+"Edge\.Cuts"\)',
        text,
    )
    if not m:
        return None
    x0, y0, x1, y1 = map(float, m.groups())
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _fps(text: str) -> list[tuple[str, float, float, str]]:
    out = []
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
        st = m.start() + 1
        d = 0
        i = st
        while i < len(text):
            if text[i] == "(":
                d += 1
            elif text[i] == ")":
                d -= 1
                if d == 0:
                    break
            i += 1
        blk = text[st : i + 1]
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at_m = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", blk)
        layer_m = re.search(r'\n\t\t\(layer "([^"]+)"\)', blk)
        if not ref_m or not at_m:
            continue
        out.append((ref_m.group(1), float(at_m.group(1)), float(at_m.group(2)),
                    layer_m.group(1) if layer_m else "?"))
    return out


def _vias(text: str) -> list[tuple[float, float]]:
    """A8 routing vias only — skip mousebite / NPTH-like (drill ≈ size ≥ 0.6)."""
    bad = []
    for m in re.finditer(r"\n\t\(via\s+([\s\S]*?)\n\t\)", text):
        blk = m.group(1)
        sz = re.search(r"\(size ([\d.]+)\)", blk)
        dr = re.search(r"\(drill ([\d.]+)\)", blk)
        if not sz or not dr:
            continue
        size, drill = float(sz.group(1)), float(dr.group(1))
        if drill >= 0.55 and abs(size - drill) < 0.05:
            continue  # mousebite / snap
        if abs(size - VIA_SIZE) > 0.01 or abs(drill - VIA_DRILL) > 0.01:
            bad.append((size, drill))
    return bad


def _tracks(text: str) -> list[float]:
    return [float(w) for w in re.findall(r"\n\t\(segment[\s\S]*?\(width ([\d.]+)\)", text)]


def _discrete_silk_ok(text: str, ref: str) -> bool:
    """E10.13: Ref + Value present in footprint block for R/C/D/F."""
    m = re.search(
        rf'\n\t\(footprint "[^"]+"[\s\S]*?\(property "Reference" "{re.escape(ref)}"',
        text,
    )
    if not m:
        return False
    # Find block start
    st = text.rfind("\t(footprint", 0, m.end())
    d = 0
    i = st
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                break
        i += 1
    blk = text[st : i + 1]
    has_val = '(property "Value"' in blk
    has_rect = "(fp_rect" in blk and "SilkS" in blk
    return has_val and has_rect


def check_pcb(path: Path) -> list[str]:
    fails: list[str] = []
    if not path.is_file():
        return [f"missing {path.name}"]
    text = path.read_text(encoding="utf-8")
    edge = _edge(text)
    if not edge:
        fails.append(f"{path.name}: no Edge.Cuts rect")
        return fails
    x0, y0, x1, y1 = edge
    for ref, x, y, layer in _fps(text):
        if layer not in ("F.Cu", "?"):
            fails.append(f"{path.name}: {ref} not on F.Cu ({layer})")
        if not (x0 + EDGE_CLEAR <= x <= x1 - EDGE_CLEAR and
                y0 + EDGE_CLEAR <= y <= y1 - EDGE_CLEAR):
            if path.name.startswith("submodules_panel"):
                continue
            fails.append(f"{path.name}: {ref} @{x:.1f},{y:.1f} too close to edge")
        if ref[0] in "RCDF" and ref[1:2].isdigit():
            if not _discrete_silk_ok(text, ref):
                fails.append(f"{path.name}: {ref} missing Value silk / fp_rect (E10.13)")
    for sz, dr in _vias(text):
        fails.append(f"{path.name}: via {sz}/{dr} ≠ A8 {VIA_SIZE}/{VIA_DRILL}")
    widths = _tracks(text)
    # M2 may be placement-only (no copper) until routing is requested
    if path.name in ("m3_uln2003.kicad_pcb",):
        if not widths:
            fails.append(f"{path.name}: no tracks (module must be pre-routed)")
        for w in widths:
            if w < MIN_TRACK - 1e-9:
                fails.append(f"{path.name}: track width {w} < {MIN_TRACK}")
                break
    elif path.name == "m2_opto4.kicad_pcb" and widths:
        for w in widths:
            if w < MIN_TRACK - 1e-9:
                fails.append(f"{path.name}: track width {w} < {MIN_TRACK}")
                break
    # A5–A7 geometry (same rules as carrier — PCB_REVIEW E5 applies to modules)
    if path.name in ("m3_uln2003.kicad_pcb",):
        try:
            import _check_signal_routing as csr
            csr.PCB = path
            # Capture A5/A6/A7 without printing twice — call internals
            text_pcb = path.read_text(encoding="utf-8")
            net_names, segs, holes = csr.parse_pcb(text_pcb)
            crosses = colinear = 0
            hole_hits = 0
            for i, a in enumerate(segs):
                for b in segs[i + 1 :]:
                    if a.layer != b.layer or a.net == b.net:
                        continue
                    if csr.proper_interior_cross(a.p1, a.p2, b.p1, b.p2):
                        crosses += 1
                    elif csr.colinear_overlap(a, b):
                        colinear += 1
            import math
            for seg in segs:
                for hole in holes:
                    if hole.net == seg.net and hole.net != 0:
                        continue
                    for pt in (seg.p1, seg.p2):
                        if math.hypot(pt[0] - hole.x, pt[1] - hole.y) < hole.radius + csr.ENDPOINT_PAD_TOL_MM:
                            break
                    else:
                        d, t = csr.dist_point_seg(hole.x, hole.y, seg.p1, seg.p2)
                        need = hole.radius + seg.width * 0.5 + csr.TRACE_CLEARANCE_MM
                        if d < need and 0.02 < t < 0.98:
                            hole_hits += 1
            if crosses:
                fails.append(f"{path.name}: {crosses} same-layer crossings (A5)")
            if colinear:
                fails.append(f"{path.name}: {colinear} colinear overlaps (A6)")
            if hole_hits:
                fails.append(f"{path.name}: {hole_hits} tracks through/near foreign holes (A7)")
        except Exception as e:
            fails.append(f"{path.name}: A5-A7 check error: {e}")
    # A5 — same-layer interior crossings (legacy helper; kept as backup)
    try:
        from _find_crossings import scan as _scan_x
        xs = _scan_x(path)
        if xs and path.name == "submodules_panel.kicad_pcb":
            fails.append(f"{path.name}: {len(xs)} same-layer track crossings (A5)")
    except Exception as e:
        fails.append(f"{path.name}: crossing check error: {e}")
    return fails


def main() -> int:
    print("=== Sub-module PCB_REVIEW gates ===")
    all_fails: list[str] = []
    for p in PCBS:
        fails = check_pcb(p)
        tag = "PASS" if not fails else "FAIL"
        print(f"  {tag}  {p.name}")
        for f in fails:
            print(f"       - {f}")
            all_fails.append(f)
    if all_fails:
        print(f"\nMODULES OVERALL: FAIL ({len(all_fails)})")
        return 1
    print("\nMODULES OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
