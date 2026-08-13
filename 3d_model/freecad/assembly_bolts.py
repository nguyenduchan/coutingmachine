"""
Shared M3 fastener HOLES only — never model bolt/nut solids.

Cut clearance Ø3.6 (+ optional head CB / nut pocket) into printed parts.
The same makers feed Disc_Access_Lid, Rotary_Linear (via lid height drive),
and the combined disc machine (show_jgb37_gui.py).

Hardware (not drawn): M3 ISO hex + M3 nut (AF 5.5).
  Through plate: clearance cylinder Ø3.6
  Head side: counterbore Ø6.5 × 2.2 (recess in the part, not a bolt)
  Nut side: square pocket AF 6.0 × 2.8 (recess, not a nut solid)

Patterns are world-XY (mm) unless noted local-to-parent.
"""
from __future__ import annotations

import math
from typing import Iterable

import FreeCAD as App
import Part

import box_settings as BX

_F = BX.FASTENER
M3_CLEAR = float(_F["clear_d"])
M3_HEAD_CB_D = float(_F["head_cb_d"])
M3_HEAD_CB_H = float(_F["head_cb_h"])
M3_NUT_POCKET_AF = float(_F["nut_pocket_af"])
M3_NUT_POCKET_H = float(_F["nut_pocket_h"])
M3_BOLT_L = float(_F["default_len"])
FASTENER_SPEC = str(_F["spec"])
LID_CORNER_INSET = float(_F["lid_corner_inset"])
HUB_PCD = float(_F["hub_pcd"])
HUB_CLAMP_T = float(_F.get("hub_clamp_t", 6.0))
GUIDE_WALL_HOLE_H = float(_F.get("guide_wall_hole_h", 6.0))


def _as_solid(shape: Part.Shape) -> Part.Shape:
    if shape is None or getattr(shape, "isNull", lambda: False)():
        return shape
    try:
        out = shape.removeSplitter()
        if out is not None and not out.isNull() and out.Solids:
            return out
    except Exception:
        pass
    return shape


def m3_hole_z(x: float, y: float, z0: float, h: float) -> Part.Shape:
    c = Part.makeCylinder(M3_CLEAR / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def m3_cbore_z(x: float, y: float, z_top: float) -> Part.Shape:
    c = Part.makeCylinder(M3_HEAD_CB_D / 2.0, M3_HEAD_CB_H + 0.2)
    c.translate(App.Vector(x, y, z_top - M3_HEAD_CB_H - 0.2))
    return c


def m3_well_z(x: float, y: float, z0: float, h: float, d: float = 7.0) -> Part.Shape:
    """Deep access well so M3×16 only clamps the remaining thin pad (hub)."""
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def m3_nut_pocket_z(x: float, y: float, z_bottom: float) -> Part.Shape:
    af = M3_NUT_POCKET_AF
    box = Part.makeBox(af, af, M3_NUT_POCKET_H + 0.2)
    box.translate(App.Vector(x - af / 2.0, y - af / 2.0, z_bottom - 0.1))
    return box


def m3_hole_x(x0: float, y: float, z: float, h: float) -> Part.Shape:
    c = Part.makeCylinder(M3_CLEAR / 2.0, h)
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
    c.translate(App.Vector(x0, y, z))
    return c


def m3_hole_y(x: float, y0: float, z: float, h: float) -> Part.Shape:
    c = Part.makeCylinder(M3_CLEAR / 2.0, h)
    c.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
    c.translate(App.Vector(x, y0, z))
    return c


def cut_holes_z(
    shape: Part.Shape,
    xy: Iterable[tuple[float, float]],
    z0: float,
    h: float,
    *,
    cbore_top: float | None = None,
    nut_bottom: float | None = None,
) -> Part.Shape:
    """Cut M3 through-holes; optional head CB from cbore_top, nut pocket at nut_bottom."""
    if shape is None or not getattr(shape, "Solids", None):
        return shape
    out = shape
    for x, y in xy:
        try:
            nxt = out.cut(m3_hole_z(x, y, z0, h))
            if nxt is not None and nxt.Solids:
                out = nxt
        except Exception:
            continue
        if cbore_top is not None:
            try:
                nxt = out.cut(m3_cbore_z(x, y, cbore_top))
                if nxt is not None and nxt.Solids:
                    out = nxt
            except Exception:
                pass
        if nut_bottom is not None:
            try:
                nxt = out.cut(m3_nut_pocket_z(x, y, nut_bottom))
                if nxt is not None and nxt.Solids:
                    out = nxt
            except Exception:
                pass
    return _as_solid(out)


def cut_radial_m3(
    shape: Part.Shape,
    *,
    axis: str,
    along0: float,
    a: float,
    b: float,
    h: float,
) -> Part.Shape:
    """axis='x': hole along +X from along0, center (a=y, b=z). axis='y': from along0 along +Y."""
    if shape is None or not getattr(shape, "Solids", None):
        return shape
    try:
        cutter = m3_hole_x(along0, a, b, h) if axis == "x" else m3_hole_y(a, along0, b, h)
        nxt = shape.cut(cutter)
        if nxt is not None and nxt.Solids:
            return _as_solid(nxt)
    except Exception:
        pass
    return shape


def pcd_xy(n: int, r: float, a0_deg: float = 45.0) -> list[tuple[float, float]]:
    out = []
    for i in range(n):
        a = math.radians(a0_deg + i * (360.0 / n))
        out.append((r * math.cos(a), r * math.sin(a)))
    return out


def lid_corner_xy(half: float | None = None, inset: float | None = None) -> list[tuple[float, float]]:
    """4 corners of the 220 mm square — lid sandwich + housing lid + shell bosses."""
    h = float(BX.lid_square_half() if half is None else half)
    ins = LID_CORNER_INSET if inset is None else float(inset)
    s = h - ins
    return [(s, s), (s, -s), (-s, s), (-s, -s)]


def guide_floor_xy(r_in: float, r_out: float, n: int | None = None) -> list[tuple[float, float]]:
    """Bolts through Outer_Guide_Floor annulus into Housing_Lid."""
    nn = int(_F.get("guide_n", 4) if n is None else n)
    r = 0.5 * (r_in + r_out)
    return pcd_xy(nn, r, a0_deg=45.0)


def guide_wall_xy(r_mid: float, step_deg: int = 10) -> list[tuple[float, float]]:
    """One M3 per 10° wall sector (mid-angle) into the floor."""
    out = []
    for i in range(0, 360, step_deg):
        a = math.radians(float(i) + 0.5 * step_deg)
        out.append((r_mid * math.cos(a), r_mid * math.sin(a)))
    return out


def hub_disc_xy(pcd: float | None = None) -> list[tuple[float, float]]:
    return pcd_xy(4, float(pcd or HUB_PCD) / 2.0, a0_deg=45.0)


def lid_wall_sq_xy(xl: float, xr: float, yb: float, yt: float) -> dict[str, list[tuple[float, float]]]:
    """2 holes per square lid wall, on inward flange (5 mm in from outer edge)."""
    inset = 5.0
    span = 55.0
    return {
        "Lid_Wall_Sq_E": [(xr - inset, span), (xr - inset, -span)],
        "Lid_Wall_Sq_W": [(xl + inset, span), (xl + inset, -span)],
        "Lid_Wall_Sq_N": [(span, yt - inset), (-span, yt - inset)],
        "Lid_Wall_Sq_S": [(span, yb + inset), (-span, yb + inset)],
    }


def all_lid_wall_sq_xy(xl: float, xr: float, yb: float, yt: float) -> list[tuple[float, float]]:
    d = lid_wall_sq_xy(xl, xr, yb, yt)
    acc: list[tuple[float, float]] = []
    for pts in d.values():
        acc.extend(pts)
    return acc


def exit_tray_bolt_xy_local() -> list[tuple[float, float]]:
    """4 M3 in Exit_Tray_Floor (local; add App::Part Placement for world)."""
    et = BX.EXIT_TRAY
    ra = float(et["arc_diameter"]) / 2.0
    ch = float(et["channel_width"])
    sl = float(et["straight_length"])
    wt = float(et["wall_thickness"])
    pad = float(et["floor_side_pad"])
    acx = float(et["arc_cx_local"])
    acy = float(et["arc_cy_local"])
    x_right = acx - ra
    x_left = x_right - ch - wt
    x0 = x_left - wt / 2.0 - pad
    x1 = x_right + wt + pad
    y_join = acy
    y_front = y_join - sl
    return [
        (x0 + 8.0, y_front + 6.0),
        (x1 - 8.0, y_front + 6.0),
        (x0 + 8.0, y_join - 12.0),
        (x1 - 8.0, y_join - 10.0),
    ]


def width_rail_bolt_xy() -> list[tuple[float, float]]:
    """4 M3 Width_Rail → Lid_Bottom (same XY as make_width_adjust_drive_parts)."""
    plan = BX.lid_plan_full()
    drv = BX.LID.get("width_bar", {}).get("drive", {})
    xs = [p[0] for p in plan["width_bar"]]
    ys = [p[1] for p in plan["width_bar"]]
    cx = 0.5 * (min(xs) + max(xs)) + float(drv.get("offset_x", 0.0))
    y_lo, y_hi = min(ys), max(ys)
    bar_w = max(xs) - min(xs)
    wall = float(drv.get("rail_wall", 2.0))
    clear = float(drv.get("rail_clear", 0.4))
    half = 0.5 * (bar_w + 2.0 * clear + 2.0 * wall)
    y0 = y_lo - 4.0
    y1 = y_hi + 4.0
    m = 5.0
    return [
        (cx - half + m, y0 + 8.0),
        (cx + half - m, y0 + 8.0),
        (cx - half + m, y1 - 8.0),
        (cx + half - m, y1 - 8.0),
    ]


def press_mount_xy() -> list[tuple[float, float]]:
    """2 M3 Press_Mount → Outer_Guide wall (same pose as make_exit_press_guide)."""
    disc_d = float(BX.DISC["diameter"])
    exit_y = float(BX.GATE["exit_y"])
    r_rim = (disc_d + 0.5) / 2.0
    a_mouth = math.degrees(math.atan2(float(exit_y), -r_rim))
    a_mount = a_mouth - 34.0
    r_m = r_rim + 1.5
    mx = r_m * math.cos(math.radians(a_mount))
    my = r_m * math.sin(math.radians(a_mount))
    tx = -math.sin(math.radians(a_mount))
    ty = math.cos(math.radians(a_mount))
    return [(mx + 5.0 * tx, my + 5.0 * ty), (mx - 5.0 * tx, my - 5.0 * ty)]


def panel_xy(box_d: float, box_h: float) -> list[tuple[float, float, float]]:
    """Control_Panel → Housing_Shell front (−Y). Returns (x, y, z) world."""
    y = -box_d / 2.0 + 2.0
    x0, z0 = 15.0, box_h - 75.0
    return [
        (x0 + 8.0, y, z0 + 8.0),
        (x0 + 87.0, y, z0 + 8.0),
        (x0 + 8.0, y, z0 + 62.0),
        (x0 + 87.0, y, z0 + 62.0),
    ]


def boss_box_z(
    x: float,
    y: float,
    z0: float,
    h: float,
    side: float = 12.0,
) -> Part.Shape:
    b = Part.makeBox(side, side, h)
    b.translate(App.Vector(x - side / 2.0, y - side / 2.0, z0))
    return b


def flange_box(
    x0: float,
    y0: float,
    z0: float,
    dx: float,
    dy: float,
    dz: float,
) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def hole_is_empty(shape: Part.Shape, x: float, y: float, z: float, tol: float = 0.4) -> bool:
    """True if (x,y,z) is not inside solid (a through-hole / pocket)."""
    if shape is None or not getattr(shape, "Solids", None):
        return False
    try:
        return not bool(shape.isInside(App.Vector(x, y, z), tol, True))
    except Exception:
        return False


def joint_catalog(
    *,
    z_disc: float,
    disc_t: float,
    hub_h: float,
    box_t: float,
    top_z: float,
    shelf_z: float,
    box_h: float,
    box_d: float,
    lid_disc_clear: float,
    lid_bottom_t: float,
    lid_wall_h: float,
    lid_top_t: float,
    r_guide_in: float,
    r_guide_out: float,
    coupler_z0: float,
    coupler_l: float,
    coupler_od: float,
    shaft_d: float,
    tray_pl: tuple[float, float] = (0.0, 0.0),
    gap_pl: tuple[float, float] = (0.0, 0.0),
) -> list[dict]:
    """Named joints for verify_bolt_holes.py (world XYZ of hole centers)."""
    z_under = z_disc + disc_t + lid_disc_clear
    z_top0 = z_under + lid_wall_h
    corners = lid_corner_xy()
    gfloor = guide_floor_xy(r_guide_in, r_guide_out)
    gwalls = guide_wall_xy(0.5 * (r_guide_in + r_guide_out))
    hub = hub_disc_xy()
    half = float(BX.lid_square_half())
    wall_xy = all_lid_wall_sq_xy(-half, half, -half, half)
    joints = [
        {
            "name": "lid_housing_corners",
            "bolt": FASTENER_SPEC,
            "xy": corners,
            "parts": [
                "Lid_Bottom_Floor",
                "Housing_Lid",
            ],
            "z_probe": [
                z_under + 0.5 * lid_bottom_t,
                top_z + 0.5 * box_t,
                top_z + box_t + 3.0,
            ],
        },
        {
            "name": "guide_floor_housing",
            "bolt": FASTENER_SPEC,
            "xy": gfloor,
            "parts": ["Outer_Guide_Floor", "Housing_Lid"],
            "z_probe": [z_disc - 0.5 * disc_t, top_z + 0.5 * box_t],
        },
        {
            "name": "guide_wall_floor",
            "bolt": FASTENER_SPEC,
            "xy": gwalls,
            "parts": ["Outer_Guide_Floor"],
            "z_probe": [z_disc + 2.0, z_disc - 0.5 * disc_t],
        },
        {
            "name": "disc_hub",
            "bolt": FASTENER_SPEC,
            "xy": hub,
            "parts": ["Disc_Plate", "Hub_Body"],
            "z_probe": [z_disc + 0.5 * disc_t, z_disc + disc_t + 0.5 * HUB_CLAMP_T],
        },
        {
            "name": "lid_wall_sq_bottom",
            "bolt": FASTENER_SPEC,
            "xy": wall_xy,
            "parts": [
                "Lid_Wall_Sq_E",
                "Lid_Wall_Sq_W",
                "Lid_Wall_Sq_N",
                "Lid_Wall_Sq_S",
                "Lid_Bottom_Floor",
            ],
            "z_probe": [z_under + 3.0, z_under + 0.5 * lid_bottom_t],
        },
        {
            "name": "housing_shelf",
            "bolt": FASTENER_SPEC,
            "xy": corners,
            "parts": ["Housing_Shelf", "Housing_Shell"],
            "z_probe": [shelf_z + 0.5 * box_t],
        },
        {
            "name": "control_panel",
            "bolt": FASTENER_SPEC,
            "xyz": panel_xy(box_d, box_h),
            "parts": ["Panel_Bezel", "Housing_Shell"],
        },
        {
            "name": "coupler_set_screws",
            "bolt": FASTENER_SPEC,
            "radial": [
                {
                    "axis": "x",
                    "x0": -coupler_od / 2.0 - 1.0,
                    "y": 0.0,
                    "z": coupler_z0 + 6.0,
                    "h": coupler_od + 2.0,
                },
                {
                    "axis": "x",
                    "x0": -coupler_od / 2.0 - 1.0,
                    "y": 0.0,
                    "z": coupler_z0 + coupler_l - 6.0,
                    "h": coupler_od + 2.0,
                },
            ],
            "parts": ["Coupler_Body"],
        },
        {
            "name": "hub_set_screw",
            "bolt": FASTENER_SPEC,
            "radial": [
                {
                    "axis": "x",
                    "x0": -25.0,
                    "y": 0.0,
                    "z": z_disc + disc_t + 0.5 * hub_h,
                    "h": 30.0,
                }
            ],
            "parts": ["Hub_Body"],
        },
    ]
    _ = (tray_pl, gap_pl, shaft_d)
    return joints
