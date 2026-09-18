#!/usr/bin/env python3
"""Finish remaining copper: current-rated power to In1/In2 planes + signal vias.

Does not wipe existing tracks. Run with KiCad's Python:

    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" finish_route.py
"""
from __future__ import annotations

import math
import sys
import subprocess
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"

# Board origin 50,50  180×120. Copper ≥2 mm from Edge.Cuts (PCB_REVIEW A12).
OX, OY, BW, BH = 50.0, 50.0, 180.0, 120.0
EDGE_MM = 2.0
X0, Y0, X1, Y1 = OX + EDGE_MM, OY + EDGE_MM, OX + BW - EDGE_MM, OY + BH - EDGE_MM
# In2 split — same polygons as the live zones (outer inset 2 mm, split unmoved).
PLUS5 = (52.0, 52.0, 153.744, 107.014)
PLUS3 = (154.944, 52.0, 228.0, 107.014)
PLUS24 = (52.0, 108.214, 228.0, 168.0)

# IPC-2221 1 oz, 10 °C rise. See verify_track_width.py.
WIDTH_MM = {
    "GND": 1.00,
    "+24V": 1.00,
    "+24V_RAW": 1.00,
    "+24V_PRE": 1.00,
    "+24V_MOT": 0.50,
    "+24V_MOT2": 0.50,
    "+5V": 0.50,
    "+3V3": 0.35,
    "+24V_SNS": 0.25,
    "+24V_SNS_PRE": 0.25,
}
PLANE_NETS = ("GND", "+24V", "+5V", "+3V3", "+24V_PRE", "+24V_RAW")
VIA_D, VIA_DRILL = 0.8, 0.4
VIA_R = VIA_D * 0.5
VIA_PAD_GAP_MM = 1.0  # A11 copper-to-copper
CLEAR_MM = 0.50  # router floor (PCB_REVIEW R) — power / vias
SIGNAL_CLEAR_MM = 0.22  # signal track-to-track (netclass 0.20 + hair)
SIGNAL_W = 0.25
FANOUT_XY = (
    (2.4, 0), (-2.4, 0), (0, 2.4), (0, -2.4),
    (2.2, 2.2), (-2.2, 2.2), (2.2, -2.2), (-2.2, -2.2),
    (3.0, 0), (-3.0, 0), (0, 3.0), (0, -3.0),
    (3.2, 1.6), (-3.2, 1.6), (3.2, -1.6), (-3.2, -1.6),
    (4.0, 0), (0, 4.0), (-4.0, 0), (0, -4.0),
    (4.5, 0), (0, 4.5), (-4.5, 0), (0, -4.5),
    (5.5, 0), (0, 5.5), (-5.5, 0), (0, -5.5),
    (6.0, 2.0), (-6.0, 2.0), (6.0, -2.0), (-6.0, -2.0),
)


def _ign(ignore_ref) -> set[str]:
    if not ignore_ref:
        return set()
    if isinstance(ignore_ref, str):
        return {ignore_ref}
    return set(ignore_ref)


def mm(v) -> float:
    return pcbnew.ToMM(v)


def iu(v_mm: float) -> int:
    return pcbnew.FromMM(v_mm)


def width_for(name: str) -> float:
    if name in WIDTH_MM:
        return WIDTH_MM[name]
    if name.startswith("/Mot"):
        return 0.50
    return SIGNAL_W


def plane_rect(net: str) -> tuple[float, float, float, float] | None:
    if net == "GND":
        return (X0, Y0, X1, Y1)
    if net in ("+24V", "+24V_PRE", "+24V_RAW"):
        return PLUS24
    if net == "+5V":
        return PLUS5
    if net == "+3V3":
        return PLUS3
    return None


def clamp_to_rect(x: float, y: float, rect) -> tuple[float, float]:
    xa, ya, xb, yb = rect
    return min(max(x, xa), xb), min(max(y, ya), yb)


def in_rect(x: float, y: float, rect) -> bool:
    xa, ya, xb, yb = rect
    return xa <= x <= xb and ya <= y <= yb


def _orient(ax, ay, bx, by, cx, cy) -> int:
    v = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
    if abs(v) < 1e-9:
        return 0
    return 1 if v > 0 else 2


def _on_seg(ax, ay, bx, by, cx, cy) -> bool:
    return (min(ax, bx) - 1e-9 <= cx <= max(ax, bx) + 1e-9
            and min(ay, by) - 1e-9 <= cy <= max(ay, by) + 1e-9)


def _segs_cross(x1, y1, x2, y2, x3, y3, x4, y4) -> bool:
    o1 = _orient(x1, y1, x2, y2, x3, y3)
    o2 = _orient(x1, y1, x2, y2, x4, y4)
    o3 = _orient(x3, y3, x4, y4, x1, y1)
    o4 = _orient(x3, y3, x4, y4, x2, y2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_seg(x1, y1, x2, y2, x3, y3):
        return True
    if o2 == 0 and _on_seg(x1, y1, x2, y2, x4, y4):
        return True
    if o3 == 0 and _on_seg(x3, y3, x4, y4, x1, y1):
        return True
    if o4 == 0 and _on_seg(x3, y3, x4, y4, x2, y2):
        return True
    return False


def dist_point_seg(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _seg_hits_rect(x1, y1, x2, y2, half_w, rect) -> bool:
    xa, ya, xb, yb = rect
    xa, xb = min(xa, xb) - half_w, max(xa, xb) + half_w
    ya, yb = min(ya, yb) - half_w, max(ya, yb) + half_w
    sx0, sx1 = min(x1, x2), max(x1, x2)
    sy0, sy1 = min(y1, y2), max(y1, y2)
    return not (sx1 < xa or sx0 > xb or sy1 < ya or sy0 > yb)


class Occupancy:
    def __init__(self, board):
        self.board = board
        self.pads = []
        for fp in board.GetFootprints():
            href = str(fp.GetReference()).startswith("H")
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                p = pad.GetPosition()
                sz = pad.GetSize()
                r = 0.5 * mm(max(sz.x, sz.y))
                self.pads.append((mm(p.x), mm(p.y), r, pad.GetNetCode(), pad, fp, href))
        from pin_row_keepout import pin_row_rects
        self.pin_rects = [b[:4] for b in pin_row_rects(PCB.read_text(encoding="utf-8"))]
        self.track_objs = []
        for t in board.GetTracks():
            self.track_objs.append(t)
        self.tracks = []
        self.vias = []
        self.rebuild_geom()

    def rebuild_geom(self):
        self.tracks = []
        self.vias = []
        for t in self.track_objs:
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                self.vias.append((mm(p.x), mm(p.y), VIA_D * 0.5, t.GetNetCode()))
            elif t.Type() == pcbnew.PCB_TRACE_T:
                a, b = t.GetStart(), t.GetEnd()
                self.tracks.append((
                    mm(a.x), mm(a.y), mm(b.x), mm(b.y),
                    mm(t.GetWidth()) * 0.5, t.GetLayer(), t.GetNetCode(),
                ))

    def refresh(self):
        self.rebuild_geom()

    def track_ok(self, x1, y1, x2, y2, layer, net, half_w, clear=None, ignore_ref=None) -> bool:
        if clear is None:
            clear = CLEAR_MM
        need = half_w + clear
        for x, y in ((x1, y1), (x2, y2)):
            if not (X0 + half_w <= x <= X1 - half_w and Y0 + half_w <= y <= Y1 - half_w):
                return False
        near_own = False
        for px, py, r, ncode, _pad, _fp, _h in self.pads:
            if ncode == net and (
                math.hypot(x1 - px, y1 - py) < 0.55 or math.hypot(x2 - px, y2 - py) < 0.55
            ):
                near_own = True
                break
        if not near_own:
            for vx, vy, vr, ncode in self.vias:
                if ncode == net and (
                    math.hypot(x1 - vx, y1 - vy) < 0.55 or math.hypot(x2 - vx, y2 - vy) < 0.55
                ):
                    near_own = True
                    break
        if not near_own:
            for ax, ay, bx, by, _hw, _ly, ncode in self.tracks:
                if ncode != net:
                    continue
                if min(
                    math.hypot(x1 - ax, y1 - ay), math.hypot(x1 - bx, y1 - by),
                    math.hypot(x2 - ax, y2 - ay), math.hypot(x2 - bx, y2 - by),
                ) < 0.55:
                    near_own = True
                    break
        if not near_own:
            for rect in self.pin_rects:
                if _seg_hits_rect(x1, y1, x2, y2, half_w, rect):
                    return False
        ign = _ign(ignore_ref)
        for px, py, r, ncode, _pad, fp, _h in self.pads:
            if ncode == net:
                continue
            if str(fp.GetReference()) in ign:
                continue
            if dist_point_seg(px, py, x1, y1, x2, y2) < r + need:
                return False
        for vx, vy, vr, ncode in self.vias:
            if ncode == net:
                continue
            if dist_point_seg(vx, vy, x1, y1, x2, y2) < vr + need:
                return False
        for ax, ay, bx, by, hw, ly, ncode in self.tracks:
            if ncode == net or ly != layer:
                continue
            if _segs_cross(x1, y1, x2, y2, ax, ay, bx, by):
                return False
            if dist_point_seg(ax, ay, x1, y1, x2, y2) < hw + need:
                return False
            if dist_point_seg(bx, by, x1, y1, x2, y2) < hw + need:
                return False
            if dist_point_seg(x1, y1, ax, ay, bx, by) < hw + need:
                return False
            if dist_point_seg(x2, y2, ax, ay, bx, by) < hw + need:
                return False
        return True

    def via_ok(self, x, y, net, ignore_ref=None) -> bool:
        if not (X0 + VIA_R <= x <= X1 - VIA_R and Y0 + VIA_R <= y <= Y1 - VIA_R):
            return False
        for px, py, r, ncode, _pad, fp, href in self.pads:
            if href:
                continue
            if str(fp.GetReference()) in _ign(ignore_ref):
                continue
            if math.hypot(x - px, y - py) < r + VIA_R + VIA_PAD_GAP_MM:
                return False
        for vx, vy, vr, ncode in self.vias:
            if math.hypot(x - vx, y - vy) < VIA_R + vr + CLEAR_MM:
                return False
        for ax, ay, bx, by, hw, _ly, ncode in self.tracks:
            if ncode == net:
                continue
            if dist_point_seg(x, y, ax, ay, bx, by) < VIA_R + hw + CLEAR_MM:
                return False
        return True


def add_track(board, occ, x1, y1, x2, y2, layer, net, w_mm, clear=None, ignore_ref=None) -> bool:
    if abs(x1 - x2) < 0.02 and abs(y1 - y2) < 0.02:
        return True
    if not occ.track_ok(x1, y1, x2, y2, layer, net, w_mm * 0.5, clear, ignore_ref):
        return False
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(iu(x1), iu(y1)))
    tr.SetEnd(pcbnew.VECTOR2I(iu(x2), iu(y2)))
    tr.SetWidth(iu(w_mm))
    tr.SetLayer(layer)
    tr.SetNetCode(net)
    board.Add(tr)
    occ.track_objs.append(tr)
    occ.tracks.append((x1, y1, x2, y2, w_mm * 0.5, layer, net))
    return True


def add_via(board, occ, x, y, net, ignore_ref=None) -> bool:
    if not occ.via_ok(x, y, net, ignore_ref):
        return False
    via = pcbnew.PCB_VIA(board)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(iu(VIA_D))
    via.SetDrill(iu(VIA_DRILL))
    via.SetNetCode(net)
    via.SetPosition(pcbnew.VECTOR2I(iu(x), iu(y)))
    board.Add(via)
    occ.track_objs.append(via)
    occ.vias.append((x, y, VIA_D * 0.5, net))
    return True


def route_l(board, occ, ax, ay, bx, by, layer, net, w, clear=None, ignore_ref=None) -> bool:
    half = w * 0.5
    hv = occ.track_ok(ax, ay, bx, ay, layer, net, half, clear, ignore_ref) and occ.track_ok(
        bx, ay, bx, by, layer, net, half, clear, ignore_ref
    )
    if hv:
        add_track(board, occ, ax, ay, bx, ay, layer, net, w, clear, ignore_ref)
        add_track(board, occ, bx, ay, bx, by, layer, net, w, clear, ignore_ref)
        return True
    vh = occ.track_ok(ax, ay, ax, by, layer, net, half, clear, ignore_ref) and occ.track_ok(
        ax, by, bx, by, layer, net, half, clear, ignore_ref
    )
    if vh:
        add_track(board, occ, ax, ay, ax, by, layer, net, w, clear, ignore_ref)
        add_track(board, occ, ax, by, bx, by, layer, net, w, clear, ignore_ref)
        return True
    return False


def route_dogleg(board, occ, ax, ay, bx, by, layer, net, w, clear=None, ignore_ref=None) -> bool:
    """3-segment Manhattan with a parallel offset if a plain L is blocked."""
    if route_l(board, occ, ax, ay, bx, by, layer, net, w, clear, ignore_ref):
        return True
    half = w * 0.5
    mids = []
    offsets = (2.0, -2.0, 3.5, -3.5, 5.5, -5.5, 8.0, -8.0, 11.0, -11.0, 15.0, -15.0, 20.0, -20.0)
    for off in offsets:
        mids.append((ax, ay + off, bx, ay + off))
        mids.append((ax + off, ay, ax + off, by))
    for y in (57.5, 61.2, 66.0, 70.0, 74.0, 82.0, 90.0, 98.0, 112.0, 128.0, 142.0, 155.0):
        mids.append((ax, y, bx, y))
    for x in (64.0, 90.0, 110.0, 140.0, 160.0, 164.0, 190.0, 196.0, 210.0, 222.0):
        mids.append((x, ay, x, by))
    for mx1, my1, mx2, my2 in mids:
        if not (X0 <= mx1 <= X1 and Y0 <= my1 <= Y1 and X0 <= mx2 <= X1 and Y0 <= my2 <= Y1):
            continue
        if not occ.track_ok(ax, ay, mx1, my1, layer, net, half, clear, ignore_ref):
            continue
        if not occ.track_ok(mx1, my1, mx2, my2, layer, net, half, clear, ignore_ref):
            continue
        if not occ.track_ok(mx2, my2, bx, by, layer, net, half, clear, ignore_ref):
            continue
        add_track(board, occ, ax, ay, mx1, my1, layer, net, w, clear, ignore_ref)
        add_track(board, occ, mx1, my1, mx2, my2, layer, net, w, clear, ignore_ref)
        add_track(board, occ, mx2, my2, bx, by, layer, net, w, clear, ignore_ref)
        return True
    return False


def spiral_xy(max_r: float = 10.0, step: float = 0.7):
    r = 2.2
    while r <= max_r:
        n = max(8, int(2 * math.pi * r / 1.2))
        for i in range(n):
            a = i * 2 * math.pi / n
            yield r * math.cos(a), r * math.sin(a)
        r += step


def place_via_near(board, occ, x, y, net, max_r: float = 10.0, ignore_ref=None):
    if occ.via_ok(x, y, net, ignore_ref) and add_via(board, occ, x, y, net, ignore_ref):
        return x, y
    for dx, dy in spiral_xy(max_r):
        vx, vy = x + dx, y + dy
        if add_via(board, occ, vx, vy, net, ignore_ref):
            return vx, vy
    return None


def pad_xy(pad) -> tuple[float, float]:
    p = pad.GetPosition()
    return mm(p.x), mm(p.y)


def strip_drc_faults(board) -> int:
    """Delete tracks/vias named in the last DRC short/crossing report."""
    import json
    path = HERE / "out" / "drc_now.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    doomed = set()
    for v in data.get("violations") or []:
        if v.get("type") not in (
            "shorting_items", "tracks_crossing", "hole_clearance", "hole_to_hole",
            "copper_edge_clearance", "clearance",
        ):
            continue
        for it in v.get("items") or []:
            desc = it.get("description") or ""
            if "Track" in desc or "Via" in desc:
                doomed.add(it.get("uuid"))
    n = 0
    for t in list(board.GetTracks()):
        try:
            uid = t.m_Uuid.AsString()
        except Exception:
            continue
        if uid in doomed:
            try:
                board.Remove(t)
                n += 1
            except Exception:
                pass
    if n:
        print(f"  stripped {n} short/crossing copper item(s)", flush=True)
    return n


def pad_has_track(occ, px, py, net) -> bool:
    for ax, ay, bx, by, _hw, _ly, ncode in occ.tracks:
        if ncode != net:
            continue
        if math.hypot(ax - px, ay - py) < 0.40 or math.hypot(bx - px, by - py) < 0.40:
            return True
    return False


def fanout_power(board, occ) -> int:
    added = 0
    for px, py, pr, net, pad, fp, href in occ.pads:
        if href:
            continue
        name = pad.GetNetname()
        rect = plane_rect(name)
        if rect is None:
            continue
        w = width_for(name)
        tht = pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        if tht and in_rect(px, py, rect):
            continue  # through-pad already pierces the inner plane
        if pad_has_track(occ, px, py, net):
            continue
        href_ref = str(fp.GetReference())
        tx, ty = clamp_to_rect(px, py, rect)
        if in_rect(px, py, rect):
            placed = False
            for dx, dy in FANOUT_XY:
                vx, vy = px + dx, py + dy
                if not in_rect(vx, vy, rect):
                    continue
                if not occ.via_ok(vx, vy, net, href_ref):
                    continue
                if not occ.track_ok(
                    px, py, vx, vy, pcbnew.F_Cu, net, w * 0.5, SIGNAL_CLEAR_MM, href_ref
                ):
                    continue
                if add_via(board, occ, vx, vy, net, href_ref) and add_track(
                    board, occ, px, py, vx, vy, pcbnew.F_Cu, net, w, SIGNAL_CLEAR_MM, href_ref
                ):
                    added += 1
                    placed = True
                    break
            if not placed:
                print(f"  fanout skip {fp.GetReference()}.{pad.GetNumber()} {name} @ {px:.1f},{py:.1f}")
            continue
        placed = False
        tw = min(w, 0.35)
        for dx, dy in FANOUT_XY:
            vx, vy = tx + dx, ty + dy
            if not in_rect(vx, vy, rect):
                vx, vy = clamp_to_rect(tx + dx, ty + dy, rect)
            if not occ.via_ok(vx, vy, net):
                continue
            if not add_via(board, occ, vx, vy, net):
                continue
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if route_dogleg(
                    board, occ, px, py, vx, vy, layer, net, tw, SIGNAL_CLEAR_MM, href_ref
                ):
                    added += 1
                    placed = True
                    break
            if placed:
                break
        if not placed:
            print(f"  plane-run skip {fp.GetReference()}.{pad.GetNumber()} {name} -> {tx:.1f},{ty:.1f}")
    return added


def tie_pads_to_vias(board, occ) -> int:
    """SMD power pads that failed local fanout: stub to an existing same-net via."""
    added = 0
    for px, py, _pr, net, pad, fp, href in occ.pads:
        if href:
            continue
        name = pad.GetNetname()
        rect = plane_rect(name)
        if rect is None:
            continue
        w = width_for(name)
        if pad_has_track(occ, px, py, net):
            continue
        href_ref = str(fp.GetReference())
        cands = sorted(
            ((math.hypot(vx - px, vy - py), vx, vy)
             for vx, vy, _vr, ncode in occ.vias
             if ncode == net and in_rect(vx, vy, rect)),
        )
        placed = False
        for dist, vx, vy in cands[:12]:
            if dist > 14:
                break
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if route_dogleg(
                    board, occ, px, py, vx, vy, layer, net, min(w, 0.25), SIGNAL_CLEAR_MM
                ) or add_track(
                    board, occ, px, py, vx, vy, layer, net, min(w, 0.25), SIGNAL_CLEAR_MM, href_ref
                ):
                    added += 1
                    placed = True
                    break
            if placed:
                break
        if not placed and cands:
            print(f"  tie-via skip {fp.GetReference()}.{pad.GetNumber()} {name}")
    return added


def add_power_spines(board, occ) -> int:
    """B.Cu collector buses so south/west loads reach the correct In2 region."""
    added = 0
    spines = (
        ("+3V3", 221.0, 56.0, 166.0, (85.0, 100.0, 130.0, 158.0), 0.35),
        ("+5V", 59.0, 56.0, 105.0, (85.0, 98.0), 0.50),
        ("+24V", 59.0, 112.0, 166.0, (125.0, 140.0, 160.0), 1.00),
        ("GND", 221.0, 56.0, 166.0, (85.0, 115.0, 140.0), 1.00),
    )
    for name, x, y0, y1, via_ys, w in spines:
        netobj = board.FindNet(name)
        if netobj is None:
            continue
        net = netobj.GetNetCode()
        if add_track(board, occ, x, y0, x, y1, pcbnew.B_Cu, net, w):
            added += 1
        for y in via_ys:
            if add_via(board, occ, x, y, net):
                added += 1
    return added


def nudge_j_key(board) -> int:
    """Keep J_KEY clear of J_CNT5. Do not auto-slide into courtyard overlap."""
    return 0


def thicken_power(occ) -> int:
    n = 0
    for t in occ.track_objs:
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        name = t.GetNetname()
        want = width_for(name)
        if name not in WIDTH_MM and not name.startswith("/Mot"):
            continue
        cur = mm(t.GetWidth())
        if cur + 0.02 < want:
            t.SetWidth(iu(want))
            n += 1
    occ.rebuild_geom()
    return n


def fix_en_tmc(board, occ) -> int:
    """Pull /EN_TMC off U1 pad 14 /BUP (0.073 mm actual vs 0.15 need)."""
    bup = None
    for _px, _py, _r, _net, pad, fp, _h in occ.pads:
        if fp.GetReference() == "U1" and pad.GetNumber() == "14":
            bup = pad
            break
    if bup is None:
        return 0
    bx, by = pad_xy(bup)
    removed = 0
    keep = []
    for t in occ.track_objs:
        if t.Type() != pcbnew.PCB_TRACE_T or t.GetNetname() != "/EN_TMC":
            keep.append(t)
            continue
        a, b = t.GetStart(), t.GetEnd()
        d = dist_point_seg(bx, by, mm(a.x), mm(a.y), mm(b.x), mm(b.y))
        if d < 0.40:
            board.Remove(t)
            removed += 1
        else:
            keep.append(t)
    occ.track_objs = keep
    occ.rebuild_geom()
    return removed


def u1_escape(pad, fp) -> tuple[float, float]:
    p = pad.GetPosition()
    c = fp.GetPosition()
    px, py = mm(p.x), mm(p.y)
    cx, cy = mm(c.x), mm(c.y)
    dx, dy = px - cx, py - cy
    if abs(dx) >= abs(dy):
        return px + (2.4 if dx >= 0 else -2.4), py
    return px, py + (2.4 if dy >= 0 else -2.4)


def load_unconnected_pairs() -> list[tuple[str, float, float, float, float]]:
    """(net, x1, y1, x2, y2) from last KiCad DRC JSON."""
    path = HERE / "out" / "drc_now.json"
    if not path.exists():
        path = HERE / "out" / "drc_fab.json"
    import json, re
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = []
    for v in data.get("unconnected_items") or []:
        items = v.get("items") or []
        if len(items) < 2:
            continue
        net = None
        pts = []
        for it in items:
            desc = it.get("description") or ""
            m = re.search(r"\[([^\]]+)\]", desc)
            if m:
                net = m.group(1)
            pos = it.get("pos") or {}
            if "x" in pos:
                pts.append((float(pos["x"]), float(pos["y"])))
        if net and len(pts) >= 2:
            pairs.append((net, pts[0][0], pts[0][1], pts[1][0], pts[1][1]))
    return pairs


def nearest_pad(occ, x, y, netname):
    best = None
    best_fp = None
    best_d = 9e9
    for px, py, _r, _net, pad, fp, _h in occ.pads:
        if pad.GetNetname() != netname:
            continue
        d = (px - x) ** 2 + (py - y) ** 2
        if d < best_d:
            best_d, best, best_fp = d, pad, fp
    return best, best_fp


def nearest_same_net_via(occ, x, y, net, min_d=1.4):
    best = None
    best_d = 9e9
    for vx, vy, _vr, ncode in occ.vias:
        if ncode != net:
            continue
        d = math.hypot(vx - x, vy - y)
        if min_d <= d < best_d:
            best_d, best = d, (vx, vy)
    return best


def connect_one(board, occ, ax, ay, bx, by, net, w, clear, ignore_ref=None) -> bool:
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if add_track(board, occ, ax, ay, bx, by, layer, net, w, clear, ignore_ref):
            return True
        if route_dogleg(board, occ, ax, ay, bx, by, layer, net, w, clear, ignore_ref):
            return True
    pa = place_via_near(board, occ, ax, ay, net)
    pb = place_via_near(board, occ, bx, by, net)
    if pa is None or pb is None:
        return False
    add_track(board, occ, ax, ay, pa[0], pa[1], pcbnew.F_Cu, net, w, clear, ignore_ref)
    add_track(board, occ, bx, by, pb[0], pb[1], pcbnew.F_Cu, net, w, clear, ignore_ref)
    return route_dogleg(
        board, occ, pa[0], pa[1], pb[0], pb[1], pcbnew.B_Cu, net, w, clear, ignore_ref
    )


def _in_alleys(x, y, alleys) -> bool:
    return any(xa <= x <= xb and ya <= y <= yb for xa, ya, xb, yb in alleys)


def clear_signal_alleys(board, aggressive: bool = False) -> int:
    """Drop vias that clog the KEY corridor so B.Cu buses can run."""
    alleys = (
        (166.0, 55.5, 190.0, 77.0),
    )
    stitch = {"GND", "+3V3", "+5V", "+24V"}
    doomed_vias = []
    via_pts: list[tuple[float, float, int]] = []
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T:
            continue
        p = t.GetPosition()
        x, y = mm(p.x), mm(p.y)
        if not _in_alleys(x, y, alleys):
            continue
        name = t.GetNetname()
        if aggressive or name in stitch:
            doomed_vias.append(t)
            via_pts.append((x, y, t.GetNetCode()))
    doomed_tracks = []
    if aggressive:
        for tr in board.GetTracks():
            if tr.Type() != pcbnew.PCB_TRACE_T:
                continue
            a, b = tr.GetStart(), tr.GetEnd()
            ax, ay, bx, by = mm(a.x), mm(a.y), mm(b.x), mm(b.y)
            net = tr.GetNetCode()
            if any(
                ncode == net and (
                    math.hypot(ax - vx, ay - vy) < 0.50
                    or math.hypot(bx - vx, by - vy) < 0.50
                )
                for vx, vy, ncode in via_pts
            ):
                doomed_tracks.append(tr)
                continue
            if (
                tr.GetLayer() == pcbnew.B_Cu
                and not (tr.GetNetname() or "").startswith("/KEY")
                and _seg_hits_rect(ax, ay, bx, by, 0.20, (166.0, 56.0, 190.0, 77.0))
            ):
                doomed_tracks.append(tr)
    n = 0
    for t in doomed_tracks + doomed_vias:
        try:
            board.Remove(t)
            n += 1
        except Exception:
            pass
    if n:
        print(f"  cleared {n} alley via/track item(s)", flush=True)
    return n


def rip_corridor_blockers(board) -> int:
    """Remove foreign B.Cu that walls the KEY alley (e.g. /IN2 at y=67.9)."""
    box = (166.0, 56.0, 190.0, 77.0)
    n = 0
    for t in list(board.GetTracks()):
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        if t.GetLayer() != pcbnew.B_Cu:
            continue
        name = t.GetNetname()
        if name.startswith("/KEY"):
            continue
        a, b = t.GetStart(), t.GetEnd()
        if _seg_hits_rect(mm(a.x), mm(a.y), mm(b.x), mm(b.y), 0.20, box):
            try:
                board.Remove(t)
                n += 1
            except Exception:
                pass
    if n:
        print(f"  ripped {n} B.Cu blocker(s) from KEY corridor", flush=True)
    return n


def probe_via(occ, x, y, net, ignore_ref=None, max_r: float = 5.0):
    if occ.via_ok(x, y, net, ignore_ref):
        return x, y
    for dx, dy in spiral_xy(max_r, 0.55):
        vx, vy = x + dx, y + dy
        if occ.via_ok(vx, vy, net, ignore_ref):
            return vx, vy
    return None


def escape_to_b(board, occ, x, y, net, w, clear, ignore_ref=None):
    """Return a B.Cu point for this island; add one via + F stub if needed."""
    if pcbnew.B_Cu in endpoint_layers(occ, x, y, net):
        return x, y
    placed = place_via_near(board, occ, x, y, net, max_r=6.0, ignore_ref=ignore_ref)
    if placed is None:
        ex, ey = x, y + 2.6
        placed = place_via_near(board, occ, ex, ey, net, max_r=5.0, ignore_ref=ignore_ref)
    if placed is None:
        return None
    add_track(
        board, occ, x, y, placed[0], placed[1], pcbnew.F_Cu, net, w, clear, ignore_ref
    )
    return placed


def route_key_bus(board, occ) -> int:
    """KEY_R/C: J_KEY is THT so B.Cu starts on the pad; via only at U1."""
    added = 0
    keys: dict[str, dict[str, tuple]] = {}
    for px, py, _r, ncode, pad, fp, _h in occ.pads:
        ref = str(fp.GetReference())
        name = pad.GetNetname()
        if not name.startswith("/KEY"):
            continue
        keys.setdefault(name, {})[ref] = (px, py, ncode)
    clear, w = SIGNAL_CLEAR_MM, SIGNAL_W
    ordered = sorted(
        ((n, d) for n, d in keys.items() if "J_KEY" in d and "U1" in d),
        key=lambda kv: kv[1]["J_KEY"][0],
    )
    for i, (name, d) in enumerate(ordered):
        jx, jy, net = d["J_KEY"]
        ux, uy, _ = d["U1"]
        if pad_has_track(occ, jx, jy, net) and pad_has_track(occ, ux, uy, net):
            if copper_reachable(occ, jx, jy, ux, uy, net):
                continue
        lane_y = 59.0 + i * 0.50
        if not add_track(board, occ, jx, jy, jx, lane_y, pcbnew.B_Cu, net, w, clear, "J_KEY"):
            if not route_l(board, occ, jx, jy, jx, lane_y, pcbnew.B_Cu, net, w, clear, "J_KEY"):
                print(f"  KEY drop skip {name}")
                continue
        if abs(uy - 79.16) < 1.2:
            cand = probe_via(occ, ux, uy - 2.8, net, None, 3.5) or probe_via(
                occ, ux, uy - 2.8, net, "U1", 3.5
            )
        else:
            cand = probe_via(occ, ux + 2.8, uy, net, None, 3.5) or probe_via(
                occ, ux + 2.8, uy, net, "U1", 3.5
            )
        if cand is None:
            print(f"  KEY via-U skip {name}")
            continue
        vx, vy = cand
        path_ok = route_l(
            board, occ, jx, lane_y, vx, vy, pcbnew.B_Cu, net, w, clear, "J_KEY"
        ) or route_dogleg(
            board, occ, jx, lane_y, vx, vy, pcbnew.B_Cu, net, w, clear, "J_KEY"
        ) or astar_connect(
            board, occ, jx, lane_y, vx, vy, net, w, clear, None
        )
        if not path_ok:
            print(f"  KEY bus skip {name}")
            continue
        if not add_via(board, occ, vx, vy, net, "U1"):
            print(f"  KEY via add skip {name}")
            continue
        add_track(board, occ, ux, uy, vx, vy, pcbnew.F_Cu, net, w, clear, "U1")
        added += 1
        print(f"  KEY bus {name}", flush=True)
    return added


def nearest_fp_ref(occ, x, y) -> str | None:
    best, bd = None, 9e9
    for px, py, _r, _n, _pad, fp, _h in occ.pads:
        d = (px - x) ** 2 + (py - y) ** 2
        if d < bd:
            bd, best = d, str(fp.GetReference())
    return best


def _pair_width(name: str) -> float:
    if name.startswith("/Mot"):
        return 0.50
    if name in WIDTH_MM:
        return min(WIDTH_MM[name], 0.35)
    return SIGNAL_W


def copper_reachable(occ, ax, ay, bx, by, net, tol: float = 0.55) -> bool:
    """True if two points already share a same-net track/via island."""
    nodes: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def key(x, y):
        return (round(x * 20), round(y * 20))

    def add_edge(x1, y1, x2, y2):
        a, b = key(x1, y1), key(x2, y2)
        nodes.setdefault(a, []).append(b)
        nodes.setdefault(b, []).append(a)

    for x1, y1, x2, y2, _hw, _ly, ncode in occ.tracks:
        if ncode == net:
            add_edge(x1, y1, x2, y2)
    for vx, vy, _vr, ncode in occ.vias:
        if ncode == net:
            add_edge(vx, vy, vx, vy)
    start = key(ax, ay)
    goal = key(bx, by)
    if start not in nodes and goal not in nodes:
        return math.hypot(ax - bx, ay - by) < tol
    # Snap to nearest graph node.
    def snap(x, y):
        k0 = key(x, y)
        if k0 in nodes:
            return k0
        best, bd = None, tol * 20
        for k in nodes:
            d = abs(k[0] - k0[0]) + abs(k[1] - k0[1])
            if d < bd:
                bd, best = d, k
        return best

    s, g = snap(ax, ay), snap(bx, by)
    if s is None or g is None:
        return False
    seen = {s}
    q = [s]
    while q:
        cur = q.pop()
        if cur == g:
            return True
        for nxt in nodes.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return False


def endpoint_layers(occ, x, y, net) -> set[int]:
    layers: set[int] = set()
    for ax, ay, bx, by, _hw, ly, ncode in occ.tracks:
        if ncode != net:
            continue
        if math.hypot(ax - x, ay - y) < 0.50 or math.hypot(bx - x, by - y) < 0.50:
            layers.add(ly)
    for vx, vy, _vr, ncode in occ.vias:
        if ncode == net and math.hypot(vx - x, vy - y) < 0.50:
            layers.update((pcbnew.F_Cu, pcbnew.B_Cu))
    for px, py, _r, ncode, pad, _fp, _h in occ.pads:
        if ncode != net:
            continue
        if math.hypot(px - x, py - y) < 0.50:
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                layers.update((pcbnew.F_Cu, pcbnew.B_Cu))
            elif pad.IsOnLayer(pcbnew.B_Cu):
                layers.add(pcbnew.B_Cu)
            else:
                layers.add(pcbnew.F_Cu)
    return layers or {pcbnew.F_Cu}


class _GridMap:
    """Binary occupancy for leftover A* (F.Cu / B.Cu only)."""

    G = 0.50

    def __init__(self, occ: Occupancy, net: int, half_w: float, clear: float, ignore_ref, ax, ay, bx, by):
        self.occ = occ
        self.net = net
        self.g = self.G
        self.x0, self.y0 = X0, Y0
        self.nx = int((X1 - X0) / self.g) + 1
        self.ny = int((Y1 - Y0) / self.g) + 1
        self.blocked = {
            pcbnew.F_Cu: bytearray(self.nx * self.ny),
            pcbnew.B_Cu: bytearray(self.nx * self.ny),
        }
        need = half_w + clear
        ign = _ign(ignore_ref)
        ends = ((ax, ay), (bx, by))

        def near_end(px, py) -> bool:
            return any(math.hypot(px - ex, py - ey) < 0.80 for ex, ey in ends)

        for px, py, r, ncode, pad, fp, href in occ.pads:
            if href or ncode == net or str(fp.GetReference()) in ign:
                continue
            rad = r + need
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                lys = (pcbnew.F_Cu, pcbnew.B_Cu)
            elif pad.IsOnLayer(pcbnew.B_Cu) and not pad.IsOnLayer(pcbnew.F_Cu):
                lys = (pcbnew.B_Cu,)
            else:
                lys = (pcbnew.F_Cu,)
            for ly in lys:
                self._disk(ly, px, py, rad)
        for vx, vy, vr, ncode in occ.vias:
            if ncode == net:
                continue
            rad = vr + need
            self._disk(pcbnew.F_Cu, vx, vy, rad)
            self._disk(pcbnew.B_Cu, vx, vy, rad)
        for x1, y1, x2, y2, hw, ly, ncode in occ.tracks:
            if ncode == net or ly not in self.blocked:
                continue
            self._seg(ly, x1, y1, x2, y2, hw + need)
        for rect in occ.pin_rects:
            xa, ya, xb, yb = rect
            if near_end(xa, ya) or near_end(xb, yb) or near_end((xa + xb) * 0.5, (ya + yb) * 0.5):
                continue
            self._rect(pcbnew.F_Cu, xa, ya, xb, yb)
            self._rect(pcbnew.B_Cu, xa, ya, xb, yb)

    def _clamp_i(self, ix, iy):
        return 0 <= ix < self.nx and 0 <= iy < self.ny

    def _mark(self, ly, ix, iy):
        if self._clamp_i(ix, iy):
            self.blocked[ly][iy * self.nx + ix] = 1

    def _disk(self, ly, x, y, r):
        g = self.g
        i0 = int((x - r - self.x0) / g)
        i1 = int((x + r - self.x0) / g) + 1
        j0 = int((y - r - self.y0) / g)
        j1 = int((y + r - self.y0) / g) + 1
        r2 = r * r
        for iy in range(j0, j1 + 1):
            for ix in range(i0, i1 + 1):
                cx = self.x0 + ix * g
                cy = self.y0 + iy * g
                if (cx - x) ** 2 + (cy - y) ** 2 <= r2:
                    self._mark(ly, ix, iy)

    def _seg(self, ly, x1, y1, x2, y2, r):
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(length / (self.g * 0.5)))
        for i in range(n + 1):
            t = i / n
            self._disk(ly, x1 + t * (x2 - x1), y1 + t * (y2 - y1), r)

    def _rect(self, ly, xa, ya, xb, yb):
        g = self.g
        i0 = int((min(xa, xb) - self.x0) / g)
        i1 = int((max(xa, xb) - self.x0) / g) + 1
        j0 = int((min(ya, yb) - self.y0) / g)
        j1 = int((max(ya, yb) - self.y0) / g) + 1
        for iy in range(j0, j1 + 1):
            for ix in range(i0, i1 + 1):
                self._mark(ly, ix, iy)

    def cell(self, x, y) -> tuple[int, int]:
        return (
            max(0, min(self.nx - 1, int(round((x - self.x0) / self.g)))),
            max(0, min(self.ny - 1, int(round((y - self.y0) / self.g)))),
        )

    def xy(self, ix, iy) -> tuple[float, float]:
        return self.x0 + ix * self.g, self.y0 + iy * self.g

    def free(self, ly, ix, iy) -> bool:
        return self._clamp_i(ix, iy) and self.blocked[ly][iy * self.nx + ix] == 0


def _astar_cells(grid: _GridMap, sx, sy, gx, gy, start_layers, goal_layers, allow_via, ignore_ref, net):
    import heapq
    si, sj = grid.cell(sx, sy)
    gi, gj = grid.cell(gx, gy)
    starts = []
    for ly in start_layers:
        if grid.free(ly, si, sj) or True:
            starts.append((si, sj, ly))
    goals = set()
    for ly in goal_layers:
        goals.add((gi, gj, ly))
        for d in range(1, 3):
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                goals.add((gi + dx, gj + dy, ly))
    VIA_COST = 12
    heap = []
    dist = {}
    prev = {}
    for st in starts:
        heapq.heappush(heap, (0, st))
        dist[st] = 0
    expanded = 0
    max_expand = 90000
    found = None
    while heap and expanded < max_expand:
        cost, (ix, iy, ly) = heapq.heappop(heap)
        if cost != dist.get((ix, iy, ly), 1e18):
            continue
        expanded += 1
        if (ix, iy, ly) in goals and grid.free(ly, ix, iy):
            found = (ix, iy, ly)
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = ix + dx, iy + dy
            if not grid.free(ly, nx, ny):
                continue
            ncost = cost + 1
            st = (nx, ny, ly)
            if ncost < dist.get(st, 1e18):
                dist[st] = ncost
                prev[st] = (ix, iy, ly)
                heapq.heappush(heap, (ncost + abs(nx - gi) + abs(ny - gj), st))
        if allow_via:
            other = pcbnew.B_Cu if ly == pcbnew.F_Cu else pcbnew.F_Cu
            if grid.free(other, ix, iy):
                vx, vy = grid.xy(ix, iy)
                if grid.occ.via_ok(vx, vy, net, ignore_ref):
                    ncost = cost + VIA_COST
                    st = (ix, iy, other)
                    if ncost < dist.get(st, 1e18):
                        dist[st] = ncost
                        prev[st] = (ix, iy, ly)
                        heapq.heappush(heap, (ncost + abs(ix - gi) + abs(iy - gj), st))
    if found is None:
        return None
    path = [found]
    cur = found
    while cur in prev:
        cur = prev[cur]
        path.append(cur)
    path.reverse()
    return path


def _emit_astar(board, occ, path, grid, ax, ay, bx, by, net, w, clear, ignore_ref) -> bool:
    if not path:
        return False
    pts = [(grid.xy(ix, iy)[0], grid.xy(ix, iy)[1], ly) for ix, iy, ly in path]
    pts[0] = (ax, ay, pts[0][2])
    pts[-1] = (bx, by, pts[-1][2])
    # Merge collinear same-layer runs; drop a via wherever layer changes.
    segs = []
    vias = []
    x0, y0, ly0 = pts[0]
    for x1, y1, ly1 in pts[1:]:
        if ly1 != ly0:
            if abs(x1 - x0) > 0.02 or abs(y1 - y0) > 0.02:
                segs.append((x0, y0, x1, y1, ly0))
            vias.append((x1, y1))
            x0, y0, ly0 = x1, y1, ly1
            continue
        segs.append((x0, y0, x1, y1, ly0))
        x0, y0, ly0 = x1, y1, ly1
    # Collapse collinear stubs
    merged = []
    for seg in segs:
        if abs(seg[0] - seg[2]) < 0.02 and abs(seg[1] - seg[3]) < 0.02:
            continue
        if not merged:
            merged.append(list(seg))
            continue
        p = merged[-1]
        if p[4] != seg[4]:
            merged.append(list(seg))
            continue
        if abs(p[2] - seg[0]) > 0.05 or abs(p[3] - seg[1]) > 0.05:
            merged.append(list(seg))
            continue
        same_h = abs(p[1] - p[3]) < 0.05 and abs(seg[1] - seg[3]) < 0.05 and abs(p[1] - seg[1]) < 0.05
        same_v = abs(p[0] - p[2]) < 0.05 and abs(seg[0] - seg[2]) < 0.05 and abs(p[0] - seg[0]) < 0.05
        if same_h or same_v:
            p[2], p[3] = seg[2], seg[3]
        else:
            merged.append(list(seg))
    for vx, vy in vias:
        if not add_via(board, occ, vx, vy, net, ignore_ref):
            return False
    for x1, y1, x2, y2, ly in merged:
        if not add_track(board, occ, x1, y1, x2, y2, ly, net, w, clear, ignore_ref):
            # Fallback: L-route this hop
            if not route_l(board, occ, x1, y1, x2, y2, ly, net, w, clear, ignore_ref):
                return False
    return True


def astar_connect(board, occ, ax, ay, bx, by, net, w, clear, ignore_ref) -> bool:
    """B.Cu A* with at most one via at each end (A0). No mid-route vias."""
    pa = escape_to_b(board, occ, ax, ay, net, w, clear, ignore_ref)
    pb = escape_to_b(board, occ, bx, by, net, w, clear, ignore_ref)
    if pa is None or pb is None:
        return False
    ax, ay = pa
    bx, by = pb
    grid = _GridMap(occ, net, w * 0.5, clear, None, ax, ay, bx, by)
    sl = gl = {pcbnew.B_Cu}
    path = _astar_cells(grid, ax, ay, bx, by, sl, gl, False, None, net)
    if path and _emit_astar(board, occ, path, grid, ax, ay, bx, by, net, w, clear, None):
        return True
    path = _astar_cells(grid, bx, by, ax, ay, gl, sl, False, None, net)
    if path and _emit_astar(board, occ, path, grid, bx, by, ax, ay, net, w, clear, None):
        return True
    return False


def close_short_hops(board, occ, max_d: float = 10.0, clear: float = 0.30) -> int:
    """Connect nearby DRC endpoints without new vias (avoids A11 pile-up)."""
    added = 0
    for name, x1, y1, x2, y2 in load_unconnected_pairs():
        if math.hypot(x2 - x1, y2 - y1) > max_d:
            continue
        netobj = board.FindNet(name)
        if netobj is None:
            continue
        net = netobj.GetNetCode()
        w = _pair_width(name)
        ign = None
        ok = False
        for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
            if add_track(board, occ, x1, y1, x2, y2, layer, net, w, clear, ign):
                ok = True
                break
            if route_l(board, occ, x1, y1, x2, y2, layer, net, w, clear, ign):
                ok = True
                break
            if route_dogleg(board, occ, x1, y1, x2, y2, layer, net, w, clear, ign):
                ok = True
                break
        if ok:
            added += 1
            print(f"  hop {name} {math.hypot(x2-x1,y2-y1):.1f}mm", flush=True)
        else:
            print(f"  hop skip {name} {math.hypot(x2-x1,y2-y1):.1f}mm", flush=True)
    return added


def close_leftover(board, occ) -> int:
    """Close remaining DRC islands: dogleg, then B.Cu A*."""
    added = 0
    pairs = load_unconnected_pairs()
    pairs.sort(key=lambda p: math.hypot(p[3] - p[1], p[4] - p[2]))
    for name, x1, y1, x2, y2 in pairs:
        netobj = board.FindNet(name)
        if netobj is None:
            continue
        net = netobj.GetNetCode()
        if copper_reachable(occ, x1, y1, x2, y2, net):
            continue
        w = _pair_width(name)
        ign = None
        d = math.hypot(x2 - x1, y2 - y1)
        ok = False
        for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
            if add_track(board, occ, x1, y1, x2, y2, layer, net, w, SIGNAL_CLEAR_MM, ign):
                ok = True
                break
            if route_dogleg(board, occ, x1, y1, x2, y2, layer, net, w, SIGNAL_CLEAR_MM, ign):
                ok = True
                break
        if not ok:
            ok = astar_connect(board, occ, x1, y1, x2, y2, net, w, SIGNAL_CLEAR_MM, ign)
        if ok:
            added += 1
            print(f"  leftover {name} {d:.1f}mm", flush=True)
        else:
            print(f"  leftover skip {name} {d:.1f}mm ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})", flush=True)
    return added


def close_drc_pairs(board, occ) -> int:
    """Join the actual DRC island endpoints (pad/via/track), including power."""
    added = 0
    for name, x1, y1, x2, y2 in load_unconnected_pairs():
        netobj = board.FindNet(name)
        if netobj is None:
            continue
        net = netobj.GetNetCode()
        w = SIGNAL_W
        if name in WIDTH_MM:
            w = min(WIDTH_MM[name], 0.35)
        elif name.startswith("/Mot"):
            w = 0.50
        ign = {nearest_fp_ref(occ, x1, y1), nearest_fp_ref(occ, x2, y2)} - {None}
        if connect_one(board, occ, x1, y1, x2, y2, net, w, SIGNAL_CLEAR_MM, ign):
            added += 1
        else:
            print(f"  pair skip {name} ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})")
    return added


def move_pd_south(board) -> int:
    """Slide P9 pull-downs out of the KEY corridor, next to their south sockets."""
    dest = {
        "R_PD_PWM1": (152.5, 159.5, 0.0),
        "R_PD_EN1": (158.5, 159.5, 0.0),
        "R_PD_PWM2": (176.5, 159.5, 0.0),
        "R_PD_EN2": (182.5, 159.5, 0.0),
        "R_PD_VIB": (200.7, 159.5, 0.0),
    }
    old: list[tuple[float, float, int]] = []
    n = 0
    for fp in board.GetFootprints():
        ref = str(fp.GetReference())
        if ref not in dest:
            continue
        x, y, rot = dest[ref]
        p = fp.GetPosition()
        if abs(mm(p.x) - x) < 0.05 and abs(mm(p.y) - y) < 0.05:
            continue
        for pad in fp.Pads():
            pp = pad.GetPosition()
            old.append((mm(pp.x), mm(pp.y), pad.GetNetCode()))
        fp.SetPosition(pcbnew.VECTOR2I(iu(x), iu(y)))
        fp.SetOrientationDegrees(rot)
        n += 1
        print(f"  moved {ref} -> {x},{y} rot {rot}", flush=True)
    doomed = []
    for t in list(board.GetTracks()):
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        ax, ay = mm(t.GetStart().x), mm(t.GetStart().y)
        bx, by = mm(t.GetEnd().x), mm(t.GetEnd().y)
        for ox, oy, ncode in old:
            if t.GetNetCode() != ncode:
                continue
            if math.hypot(ax - ox, ay - oy) < 1.6 or math.hypot(bx - ox, by - oy) < 1.6:
                doomed.append(t)
                break
    for t in doomed:
        try:
            board.Remove(t)
        except Exception:
            pass
    if doomed:
        print(f"  dropped {len(doomed)} old PD stub(s)", flush=True)
    return n


def reduce_signal_vias(board) -> int:
    """Drop signal vias that do not actually hop F↔B (traditional: fewer holes)."""
    plane = {
        "GND", "+3V3", "+5V", "+24V", "+24V_PRE", "+24V_RAW",
        "+24V_MOT", "+24V_MOT2",
    }
    tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    removed = 0
    doomed_tracks = []
    for via in list(vias):
        name = via.GetNetname()
        if name in plane:
            continue
        vx, vy = mm(via.GetPosition().x), mm(via.GetPosition().y)
        hit_f = hit_b = 0
        stubs = []
        for t in tracks:
            if t.GetNetCode() != via.GetNetCode():
                continue
            ax, ay = mm(t.GetStart().x), mm(t.GetStart().y)
            bx, by = mm(t.GetEnd().x), mm(t.GetEnd().y)
            d = min(math.hypot(ax - vx, ay - vy), math.hypot(bx - vx, by - vy))
            if d > 0.20:
                continue
            ly = t.GetLayer()
            if ly == pcbnew.F_Cu:
                hit_f += 1
            elif ly == pcbnew.B_Cu:
                hit_b += 1
            stubs.append(t)
        if hit_f and hit_b:
            continue
        board.Remove(via)
        removed += 1
        for t in stubs:
            doomed_tracks.append(t)
    for t in doomed_tracks:
        try:
            board.Remove(t)
        except Exception:
            pass
    print(f"  reduced {removed} signal via(s) with no F↔B hop")
    return removed


def merge_colinear(board) -> int:
    """Join collinear same-net same-layer segments so FreeRouting combine() does not SO."""
    merged = 0
    for _ in range(40):
        tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
        ends = {}
        for t in tracks:
            a = (t.GetStart().x, t.GetStart().y, t.GetLayer(), t.GetNetCode())
            b = (t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetCode())
            ends.setdefault(a, []).append(t)
            ends.setdefault(b, []).append(t)
        did = False
        seen = set()
        for pts, lst in ends.items():
            if len(lst) < 2:
                continue
            for i, t1 in enumerate(lst):
                for t2 in lst[i + 1 :]:
                    if t1 is t2 or id(t1) in seen or id(t2) in seen:
                        continue
                    if t1.GetLayer() != t2.GetLayer() or t1.GetNetCode() != t2.GetNetCode():
                        continue
                    if abs(t1.GetWidth() - t2.GetWidth()) > pcbnew.FromMM(0.02):
                        continue
                    p1s, p1e = t1.GetStart(), t1.GetEnd()
                    p2s, p2e = t2.GetStart(), t2.GetEnd()
                    pts1 = [(p1s.x, p1s.y), (p1e.x, p1e.y)]
                    pts2 = [(p2s.x, p2s.y), (p2e.x, p2e.y)]
                    shared = set(pts1) & set(pts2)
                    if len(shared) != 1:
                        continue
                    sh = next(iter(shared))
                    a = pts1[0] if pts1[1] == sh else pts1[1]
                    b = pts2[0] if pts2[1] == sh else pts2[1]
                    dx1, dy1 = sh[0] - a[0], sh[1] - a[1]
                    dx2, dy2 = b[0] - sh[0], b[1] - sh[1]
                    cross = dx1 * dy2 - dy1 * dx2
                    dot = dx1 * dx2 + dy1 * dy2
                    if abs(cross) > 100 or dot <= 0:
                        continue
                    t1.SetStart(pcbnew.VECTOR2I(a[0], a[1]))
                    t1.SetEnd(pcbnew.VECTOR2I(b[0], b[1]))
                    board.Remove(t2)
                    seen.add(id(t1))
                    seen.add(id(t2))
                    merged += 1
                    did = True
                    break
                if did:
                    break
            if did:
                break
        if not did:
            break
    print(f"  merged {merged} collinear segment(s)", flush=True)
    return merged


def main() -> int:
    print("finish_route: load", flush=True)
    board = pcbnew.LoadBoard(str(PCB))
    if board is None:
        print("LoadBoard failed")
        return 1
    print("finish_route: loaded", flush=True)
    n_en = 0
    n_strip = 0
    if "--after-strip" not in sys.argv:
        n_strip = strip_drc_faults(board)
        print(f"finish_route: stripped {n_strip}", flush=True)
        if n_strip:
            pcbnew.SaveBoard(str(PCB), board)
            print("finish_route: re-exec after strip (fresh KiCad python)", flush=True)
            return subprocess.call(
                [sys.executable, str(HERE / "finish_route.py"), "--after-strip", *sys.argv[1:]]
            )
    if "--strip-only" in sys.argv:
        pcbnew.SaveBoard(str(PCB), board)
        print(f"finish_route: stripped {n_strip}, strip-only")
        return 0
    if "--merge" in sys.argv:
        n = merge_colinear(board)
        pcbnew.SaveBoard(str(PCB), board)
        print(f"finish_route: merged {n}")
        return 0
        n = reduce_signal_vias(board)
        pcbnew.SaveBoard(str(PCB), board)
        print(f"finish_route: reduced vias {n}")
        return 0
    if "--after-move" not in sys.argv:
        n_mv = move_pd_south(board)
        if n_mv:
            pcbnew.SaveBoard(str(PCB), board)
            print("finish_route: re-exec after PD move", flush=True)
            return subprocess.call(
                [sys.executable, str(HERE / "finish_route.py"),
                 "--after-move", "--after-strip", *sys.argv[1:]]
            )
    if "--short-hops" in sys.argv:
        occ = Occupancy(board)
        n = close_short_hops(board, occ)
        pcbnew.SaveBoard(str(PCB), board)
        print(f"finish_route: short hops {n}")
        return 0
    if "--leftover" in sys.argv or "--key-only" in sys.argv:
        if "--after-alley" not in sys.argv:
            n_al = clear_signal_alleys(board, aggressive=True)
            if n_al:
                pcbnew.SaveBoard(str(PCB), board)
                print("finish_route: re-exec after alley clear", flush=True)
                return subprocess.call(
                    [sys.executable, str(HERE / "finish_route.py"),
                     "--after-alley", "--after-move", "--after-strip", *sys.argv[1:]]
                )
        occ = Occupancy(board)
        n_key = route_key_bus(board, occ)
        if "--key-only" in sys.argv:
            pcbnew.SaveBoard(str(PCB), board)
            print(f"finish_route: KEY-only {n_key}")
            return 0
        n_hop = close_short_hops(board, occ, max_d=8.0, clear=0.30)
        n_left = close_leftover(board, occ)
        n_pwr = fanout_power(board, occ)
        n_tie = tie_pads_to_vias(board, occ)
        pcbnew.SaveBoard(str(PCB), board)
        print(
            f"finish_route: leftover KEY {n_key} hops {n_hop} astar {n_left} "
            f"fanout {n_pwr} tie {n_tie}"
        )
        return 0
    print("finish_route: occupancy", flush=True)
    occ = Occupancy(board)
    print("finish_route: thicken", flush=True)
    n_th = thicken_power(occ)
    print("finish_route: fanout", flush=True)
    n_pwr = fanout_power(board, occ)
    print("finish_route: spines", flush=True)
    n_spine = add_power_spines(board, occ)
    print("finish_route: tie", flush=True)
    n_tie = tie_pads_to_vias(board, occ)
    print("finish_route: close DRC pairs", flush=True)
    n_pair = close_drc_pairs(board, occ)
    print("finish_route: KEY bus", flush=True)
    n_key = route_key_bus(board, occ)
    print("finish_route: save", flush=True)
    pcbnew.SaveBoard(str(PCB), board)
    print(f"finish_route: power vias {n_pwr}, spines {n_spine}, pairs {n_pair}, "
          f"KEY {n_key}, tie {n_tie}, thickened {n_th}")
    print(f"saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
