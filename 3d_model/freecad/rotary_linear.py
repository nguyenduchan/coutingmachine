"""
Rotary_Linear — ISO/SolidWorks involute spur rack & pinion.

Build frame: pinion axis Y ⊥ rack travel Z; then whole assembly is rotated
+90° about Y so travel lies horizontal along +X (follower bar ngang).

Print / assembly (serviceable):
  RL_Pinion_Shaft — pinion + shaft fused (one 3D print)
  RL_Bearing_Rail_S/N — lower saddle + rail; M3 nut pockets
  RL_Bearing_Cap_S/N — upper half; M3×16 hex bolt + head counterbore
  RL_Knob — blind bore on shaft tip + short M3 (shaft does not pass through)
  RL_Follower — rack + slide (travel horizontal after orient); optional detent pockets
  RL_Rail_Bridge — flat plate // follower, joins Rail_S ↔ Rail_N; optional detent bore
  RL_Detent — ball + spring + set screw (include_ball_detent)

Hardware: M3×16 ISO hex bolt + M3 hex nut (AF 5.5). Clearance Ø3.6.
Drop pinion-shaft into open saddles → bolt caps → fit washer/knob.
"""
from __future__ import annotations

import math
import sys
from typing import Callable

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part


ACTIVE_RL_PARTS = frozenset(
    {
        "RL_Pinion_Shaft",
        "RL_Bearing_Rail_S",
        "RL_Bearing_Cap_S",
        "RL_Bearing_Rail_N",
        "RL_Bearing_Cap_N",
        "RL_Rail_Bridge",
        "RL_Knob",
        "RL_Friction_Washer",
        "RL_Follower",
        # Ball detent (include_ball_detent): bi lò xo sập vào rãnh khi dừng xoay
        "RL_Detent",
        "RL_Cam_Sleeve",
        "RL_Cam_StopPin",
    }
)

# ---------------------------------------------------------------------------
# Fastener (bearing caps + knob): ISO hex bolt M3×16 + hex nut M3
#   wrench / AF = 5.5 mm; nut height ≈ 2.4 mm; head height ≈ 2.0 mm
#   FDM clearance hole Ø3.6 (ISO 273 medium + print margin)
#   Cap: Ø6.5 × 2.2 counterbore for hex head
#   Rail: 6.0 AF × 2.8 deep square nut pocket (traps M3 nut)
#   Grip = CAP_CLAMP_T + RAIL_CLAMP_T ≈ 10 mm → fits M3×16 + nut
# ---------------------------------------------------------------------------
FASTENER_SPEC = "M3x16 ISO hex bolt + M3 hex nut (AF 5.5)"
M3_CLEAR = 3.6
M3_HEAD_CB_D = 6.5
M3_HEAD_CB_H = 2.2
M3_NUT_POCKET_AF = 6.0
M3_NUT_POCKET_H = 2.8
M3_BOLT_L = 16.0
M3_NUT_H = 2.4
M3_CAP_CLAMP_T = 5.0  # Cap ear thickness along bolt (X)
M3_RAIL_CLAMP_T = 5.0  # Rail ear thickness along bolt (X)
BOLT_EAR = 10.0  # ear pad in YZ — fits nut pocket + margins
# Tool cavity outside Rail nut face (not part of bolt grip)
M3_RAIL_UNDER = 5.0
M3_UNDER_CAVITY_D = 11.0  # Ø cavity under hole (wrench / fingers)


def _refine(shape: Part.Shape) -> Part.Shape:
    try:
        out = shape.removeSplitter()
        return shape if out is None or out.isNull() else out
    except Exception:
        return shape


def _as_one_solid(shape: Part.Shape) -> Part.Shape:
    shape = _refine(shape)
    if shape is None or getattr(shape, "isNull", lambda: False)():
        return shape
    sols = list(getattr(shape, "Solids", []) or [])
    if len(sols) <= 1:
        return shape
    out = sols[0]
    for s in sols[1:]:
        try:
            out = out.fuse(s)
        except Exception:
            pass
    out = _refine(out)
    sols2 = list(getattr(out, "Solids", []) or [])
    return out if len(sols2) <= 1 else Part.makeCompound(sols2)


def _keep_largest_solid(shape: Part.Shape) -> Part.Shape:
    """Drop detached scraps; keep the single largest solid."""
    shape = _refine(shape)
    sols = list(getattr(shape, "Solids", []) or [])
    if not sols:
        return shape
    if len(sols) == 1:
        return sols[0]
    best = max(sols, key=lambda s: float(s.Volume))
    return _refine(best)


def _cyl_y(d: float, length: float, x: float, y0: float, z: float) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, length)
    c.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
    c.translate(App.Vector(x, y0, z))
    return c


def _m3_hole_z(x: float, y: float, z0: float, h: float) -> Part.Shape:
    c = Part.makeCylinder(M3_CLEAR / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _m3_head_cbore_z(x: float, y: float, z_top: float) -> Part.Shape:
    """Counterbore from z_top downward for M3 hex head."""
    c = Part.makeCylinder(M3_HEAD_CB_D / 2.0, M3_HEAD_CB_H + 0.2)
    c.translate(App.Vector(x, y, z_top - M3_HEAD_CB_H - 0.2))
    return c


def _m3_nut_pocket_z(x: float, y: float, z_bottom: float) -> Part.Shape:
    """Square pocket from z_bottom upward — traps M3 hex nut (AF 5.5)."""
    af = M3_NUT_POCKET_AF
    box = Part.makeBox(af, af, M3_NUT_POCKET_H + 0.2)
    box.translate(App.Vector(x - 0.5 * af, y - 0.5 * af, z_bottom - 0.05))
    return box


def _cyl_axis_x(d: float, length: float, x0: float, y: float, z: float) -> Part.Shape:
    """Cylinder along +X from x0 (default Part cyl is +Z)."""
    c = Part.makeCylinder(d / 2.0, length)
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
    c.translate(App.Vector(x0, y, z))
    return c


def _sphere(r: float, x: float, y: float, z: float) -> Part.Shape:
    s = Part.makeSphere(r)
    s.translate(App.Vector(x, y, z))
    return s


def _m3_hole_x(x0: float, y: float, z: float, h: float) -> Part.Shape:
    return _cyl_axis_x(M3_CLEAR, h, x0, y, z)


def _m3_head_cbore_x(x_outer: float, y: float, z: float) -> Part.Shape:
    """Counterbore from +X face inward (−X) for M3 hex head (top after orient)."""
    h = M3_HEAD_CB_H + 0.2
    return _cyl_axis_x(M3_HEAD_CB_D, h, x_outer - h, y, z)


def _m3_nut_pocket_x(x_face: float, y: float, z: float) -> Part.Shape:
    """Square pocket from −X face inward (+X) — traps M3 hex nut."""
    af = M3_NUT_POCKET_AF
    box = Part.makeBox(M3_NUT_POCKET_H + 0.2, af, af)
    box.translate(App.Vector(x_face - 0.05, y - 0.5 * af, z - 0.5 * af))
    return box


def _cut_keep_x_le(shape: Part.Shape, x_cut: float) -> Part.Shape:
    """Keep material with X <= x_cut (Rail / bottom after orient)."""
    bb = shape.BoundBox
    box = Part.makeBox(
        bb.XLength + 40.0,
        bb.YLength + 20.0,
        bb.ZLength + 20.0,
    )
    box.translate(App.Vector(x_cut, bb.YMin - 10.0, bb.ZMin - 10.0))
    try:
        return _as_one_solid(shape.cut(box))
    except Exception:
        return shape


def _cut_keep_x_ge(shape: Part.Shape, x_cut: float) -> Part.Shape:
    """Keep material with X >= x_cut (Cap / top after orient)."""
    bb = shape.BoundBox
    box = Part.makeBox(
        bb.XLength + 40.0,
        bb.YLength + 20.0,
        bb.ZLength + 20.0,
    )
    box.translate(
        App.Vector(x_cut - (bb.XLength + 40.0), bb.YMin - 10.0, bb.ZMin - 10.0)
    )
    try:
        return _as_one_solid(shape.cut(box))
    except Exception:
        return shape


def _cut_above_z(shape: Part.Shape, z_cut: float) -> Part.Shape:
    """Keep material with Z <= z_cut (lower half)."""
    bb = shape.BoundBox
    box = Part.makeBox(
        bb.XLength + 20.0,
        bb.YLength + 20.0,
        bb.ZLength + 40.0,
    )
    box.translate(App.Vector(bb.XMin - 10.0, bb.YMin - 10.0, z_cut))
    try:
        return _as_one_solid(shape.cut(box))
    except Exception:
        return shape


def _cut_below_z(shape: Part.Shape, z_cut: float) -> Part.Shape:
    """Keep material with Z >= z_cut (upper half)."""
    bb = shape.BoundBox
    box = Part.makeBox(
        bb.XLength + 20.0,
        bb.YLength + 20.0,
        bb.ZLength + 40.0,
    )
    box.translate(
        App.Vector(bb.XMin - 10.0, bb.YMin - 10.0, z_cut - (bb.ZLength + 40.0))
    )
    try:
        return _as_one_solid(shape.cut(box))
    except Exception:
        return shape


def spur_gear_math(
    module: float,
    teeth: int,
    *,
    alpha_deg: float = 20.0,
    tooth_clear: float = 0.40,
) -> dict:
    """
    Shared ISO/SolidWorks full-depth spur math for pinion AND rack.
    Both must use identical m, α, p, s, e, ha, hf.
    """
    z = max(18, int(teeth))
    m = max(1.0, float(module))
    alpha = math.radians(alpha_deg)
    p = math.pi * m
    r = 0.5 * m * z
    ra = 0.5 * m * (z + 2.0)
    rf = 0.5 * m * (z - 2.5)
    ha = 1.0 * m
    hf = 1.25 * m
    s = 0.5 * p - 0.5 * tooth_clear  # tooth thickness at pitch
    e = p - s  # space at pitch
    tan_a = math.tan(alpha)
    z_min = 2.0 / (math.sin(alpha) ** 2)

    def tooth_half_w(depth_from_pitch: float) -> float:
        """Half tooth width; depth_from_pitch >0 toward tip, <0 toward root."""
        return max(0.25, 0.5 * s - depth_from_pitch * tan_a)

    return {
        "module": m,
        "teeth": z,
        "alpha_deg": alpha_deg,
        "alpha_rad": alpha,
        "circular_pitch": p,
        "pitch_radius": r,
        "tip_radius": ra,
        "root_radius": rf,
        "addendum": ha,
        "dedendum": hf,
        "tooth_thickness": s,
        "space_width": e,
        "tooth_clear": tooth_clear,
        "tan_alpha": tan_a,
        "z_min_no_undercut": z_min,
        "travel_per_turn": math.pi * m * z,
        "tooth_half_w": tooth_half_w,
    }


def _rack_params(cfg: dict) -> dict:
    r = dict(cfg.get("rack") or {})
    stroke = float(r.get("stroke", cfg.get("rail_stroke", 20.0)))
    module = float(r.get("module", cfg.get("gear_module", 2.0)))
    teeth = max(18, int(r.get("pinion_teeth", cfg.get("pinion_teeth", 18))))
    alpha = float(r.get("pressure_angle_deg", cfg.get("pressure_angle_deg", 20.0)))
    clear = float(r.get("tooth_clear", cfg.get("tooth_clear", 0.40)))
    g = spur_gear_math(module, teeth, alpha_deg=alpha, tooth_clear=clear)
    return {
        "stroke": stroke,
        "module": g["module"],
        "pinion_teeth": g["teeth"],
        "pitch_d": 2.0 * g["pitch_radius"],
        "travel_per_turn": g["travel_per_turn"],
        "face_w": float(r.get("face_w", cfg.get("pinion_face_w", 12.0))),
        "pressure_angle_deg": alpha,
        "tooth_clear": clear,
        "center_backlash": float(
            r.get("center_backlash", cfg.get("center_backlash", 0.25))
        ),
        "gear": g,
    }


def make_one_pinion_tooth(
    g: dict,
    *,
    face_w: float,
) -> Part.Shape:
    """
    Single tooth on +X centerline — identical template for polar copy.
    Root WIDER than tip (α flanks). Same s/α/ha/hf as rack.
    """
    rf = g["root_radius"]
    ra = g["tip_radius"]
    r = g["pitch_radius"]
    th = g["tooth_half_w"]
    h_root = th(-(r - rf))  # toward root
    h_tip = th(+(ra - r))  # toward tip
    if h_root <= h_tip:
        h_root = h_tip + 0.5
    pts = [
        App.Vector(rf, -h_root, 0.0),
        App.Vector(ra, -h_tip, 0.0),
        App.Vector(ra, h_tip, 0.0),
        App.Vector(rf, h_root, 0.0),
        App.Vector(rf, -h_root, 0.0),
    ]
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(App.Vector(0, 0, face_w))


def make_involute_pinion_local(
    *,
    module: float,
    teeth: int,
    face_w: float,
    bore: float,
    alpha_deg: float = 20.0,
    tooth_clear: float = 0.40,
) -> Part.Shape:
    """
    Uniform spur pinion: ONE tooth template polar-copied z times.
    Guarantees every tooth is identical size/shape.
    """
    g = spur_gear_math(module, teeth, alpha_deg=alpha_deg, tooth_clear=tooth_clear)
    z = g["teeth"]
    rf = g["root_radius"] if bore <= 0.5 else max(g["root_radius"], bore / 2.0 + 0.8)
    # Rebuild g root if bore forces larger hub (tooth still uses ISO rf for profile)
    tooth0 = make_one_pinion_tooth(g, face_w=face_w)

    solid = None
    for i in range(z):
        tooth = tooth0.copy()
        tooth.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / z)
        solid = tooth if solid is None else solid.fuse(tooth)

    hub = Part.makeCylinder(rf, face_w)
    solid = _as_one_solid(hub.fuse(solid))

    if bore > 0.5:
        hole = Part.makeCylinder(bore / 2.0, face_w + 2.0)
        hole.translate(App.Vector(0, 0, -1.0))
        try:
            solid = _as_one_solid(solid.cut(hole))
        except Exception:
            pass
        flat = Part.makeBox(bore + 1.5, 1.2, face_w + 0.4)
        flat.translate(App.Vector(-(bore + 1.5) / 2.0, -0.6, -0.2))
        try:
            keep = Part.makeCylinder(max(bore / 2.0 + 1.0, rf - 0.5), face_w + 2.0)
            keep.translate(App.Vector(0, 0, -1.0))
            flat = flat.common(keep)
            solid = _as_one_solid(solid.cut(flat))
        except Exception:
            pass
        try:
            ss = Part.makeCylinder(1.55, rf + 2.0)
            ss.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
            ss.translate(App.Vector(0.0, -(rf + 0.5), 0.5 * face_w))
            solid = _as_one_solid(solid.cut(ss))
        except Exception:
            pass
    return _as_one_solid(solid)


def place_pinion_axis_y(local, *, face_w, x, y, z):
    sh = local.copy()
    sh.translate(App.Vector(0, 0, -0.5 * face_w))
    sh.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
    sh.translate(App.Vector(x, y, z))
    return sh


def make_involute_rack(
    *,
    module: float,
    length_z: float,
    face_y: float,
    body_t: float,
    x_pitch: float,
    y0: float,
    z0: float,
    mesh_z: float,
    alpha_deg: float = 20.0,
    tooth_clear: float = 0.40,
    pinion_teeth: int = 18,
) -> Part.Shape:
    """
    Rack teeth from SAME spur_gear_math as pinion (identical m, α, p, s).
    One tooth template along Z by k·p.

    Phase: SPACE centered at mesh_z so a pinion tooth on −X seats in the
    gap (not tooth-on-tooth). Tooth centers = mesh_z + (i + ½)·p.
    """
    g = spur_gear_math(
        module, pinion_teeth, alpha_deg=alpha_deg, tooth_clear=tooth_clear
    )
    p = g["circular_pitch"]
    ha, hf = g["addendum"], g["dedendum"]
    th = g["tooth_half_w"]
    # Teeth point +X (toward pinion). Pitch line at x_pitch.
    x_tip = x_pitch + ha
    x_root = x_pitch - hf
    h_tip = th(+ha)
    h_root = th(-hf)
    if h_root <= h_tip:
        h_root = h_tip + 0.5
    # Body optional — body_t=0 means teeth sit on external rail face
    body_t = max(0.0, float(body_t))
    x_back = x_root - body_t
    solid = None
    if body_t > 0.05:
        body = Part.makeBox(max(0.5, x_root - x_back), face_y, length_z)
        body.translate(App.Vector(x_back, y0, z0))
        solid = body

    pts = [
        App.Vector(x_root, 0.0, -h_root),
        App.Vector(x_tip, 0.0, -h_tip),
        App.Vector(x_tip, 0.0, h_tip),
        App.Vector(x_root, 0.0, h_root),
        App.Vector(x_root, 0.0, -h_root),
    ]
    tooth0 = Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, face_y, 0))
    tooth0.translate(App.Vector(0, y0, 0))

    i0 = int(math.floor((z0 - mesh_z) / p)) - 2
    i1 = int(math.ceil((z0 + length_z - mesh_z) / p)) + 2
    for i in range(i0, i1 + 1):
        # Half-pitch offset ⇒ space at mesh_z + k·p
        zc = mesh_z + (i + 0.5) * p
        # Keep only teeth that sit on the bar (no floating overhang teeth)
        if zc - h_root < z0 - 0.02 or zc + h_root > z0 + length_z + 0.02:
            continue
        tooth = tooth0.copy()
        tooth.translate(App.Vector(0, 0, zc))
        if solid is None:
            solid = tooth
        else:
            solid = solid.fuse(tooth)
    if solid is None:
        solid = Part.makeBox(0.5, face_y, length_z)
        solid.translate(App.Vector(x_root - 0.5, y0, z0))
    return _as_one_solid(solid)


def verify_rack_pinion_mesh(
    pinion: Part.Shape,
    rack: Part.Shape,
    *,
    max_overlap_mm3: float = 8.0,
) -> dict:
    """True mesh may have tiny numeric overlap; deep collision = fail."""
    try:
        common = pinion.common(rack)
        vol = float(common.Volume) if common is not None and not common.isNull() else 0.0
    except Exception as ex:
        return {"pass": False, "overlap_mm3": None, "reason": str(ex)}
    return {
        "pass": vol <= max_overlap_mm3,
        "overlap_mm3": vol,
        "max_overlap_mm3": max_overlap_mm3,
    }


def verify_pinion_teeth_uniform(
    pinion_local: Part.Shape,
    g: dict,
    *,
    face_w: float,
    tol_vol_frac: float = 0.02,
) -> dict:
    """
    Enforce: every tooth identical (polar sectors have equal volume).
    Returns report with pass/fail.
    """
    z = g["teeth"]
    ra = g["tip_radius"]
    rf = g["root_radius"]
    vols = []
    for i in range(z):
        a0 = 360.0 * i / z - 180.0 / z
        a1 = 360.0 * i / z + 180.0 / z
        # Sector wedge from origin
        n = 8
        pts = [App.Vector(0, 0, -1)]
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            pts.append(App.Vector(ra * 1.05 * math.cos(a), ra * 1.05 * math.sin(a), -1))
        pts.append(App.Vector(0, 0, -1))
        try:
            wedge = Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, 0, face_w + 2))
            # Tooth material outside hub
            ring = Part.makeCylinder(ra * 1.02, face_w).cut(
                Part.makeCylinder(rf * 0.98, face_w + 0.2)
            )
            piece = pinion_local.common(wedge).common(ring)
            vols.append(float(piece.Volume))
        except Exception:
            vols.append(0.0)
    mean = sum(vols) / max(len(vols), 1)
    if mean < 1e-6:
        return {"pass": False, "reason": "zero_tooth_volume", "volumes": vols}
    rel = [abs(v - mean) / mean for v in vols]
    ok = max(rel) <= tol_vol_frac
    return {
        "pass": ok,
        "n_teeth": z,
        "volumes_mm3": vols,
        "mean_mm3": mean,
        "max_rel_dev": max(rel) if rel else 0.0,
        "tol_vol_frac": tol_vol_frac,
        "math": {
            "module": g["module"],
            "circular_pitch": g["circular_pitch"],
            "tooth_thickness": g["tooth_thickness"],
            "space_width": g["space_width"],
            "alpha_deg": g["alpha_deg"],
        },
    }


def build_rotary_linear_parts(
    *,
    cx: float = 0.0,
    cy: float = 0.0,
    z_zero: float = 0.0,
    cfg: dict | None = None,
    include_demo_wall: bool = False,
    thread_fn: Callable | None = None,
) -> list:
    d = dict(cfg or {})
    # Ball detent: bi + lò xo qua cầu ray → rãnh cầu trên thanh (2 chiều, sạch)
    ball_detent = bool(d.get("include_ball_detent", False))
    active_cam = bool(d.get("include_active_cam", False))
    rp = _rack_params(d)
    stroke = float(d.get("rail_stroke", rp["stroke"]))
    module = rp["module"]
    teeth = rp["pinion_teeth"]
    pitch_d = rp["pitch_d"]
    pitch_r = 0.5 * pitch_d
    face_w = rp["face_w"]
    travel = rp["travel_per_turn"]
    tip_r = 0.5 * module * (teeth + 2.0)
    alpha_deg = rp["pressure_angle_deg"]
    tooth_clear = rp["tooth_clear"]
    center_bl = rp["center_backlash"]

    knob_od = float(d.get("knob_od", 28.0))
    knob_h = float(d.get("knob_h", 14.0))
    grip_od = float(d.get("knob_grip_od", 22.0))
    bar_x = float(d.get("bar_thickness", 10.0))
    bar_y = float(d.get("bar_length_y", 40.0))
    bar_z = float(d.get("bar_height", 12.0))
    ridge_h = float(d.get("nut_ridge_h", 8.0))
    ridge_t = float(d.get("nut_ridge_t", 3.0))
    journal_od = float(d.get("journal_od", 8.0))
    rail_wall = float(d.get("rail_wall", 2.5))
    rail_clear = float(d.get("rail_clear", 0.35))
    scale_max = float(d.get("scale_max", stroke))
    stop_h = float(d.get("bottom_stop_h", 3.0))
    friction_t = float(d.get("friction_washer_t", 2.0))
    friction_od = float(d.get("friction_washer_od", 18.0))
    bearing_t = float(d.get("bearing_t", 6.0))
    bearing_h = float(d.get("bearing_h", max(22.0, 2.0 * tip_r + 6.0)))
    bearing_w = float(d.get("bearing_w", 20.0))
    j_od = max(journal_od, 8.0)
    pitch = math.pi * module

    z_nut0 = z_zero
    # Pitch line left of pinion: CD = pitch_r + backlash (print clearance)
    x_pitch = cx - pitch_r - center_bl
    # Slim follower: ONE slide rail + rack teeth on its +X face (no stacked flats)
    rack_body_t = 0.0
    x_root = x_pitch - 1.25 * module
    bar_cx = x_root - 0.5 * bar_x
    # --- Z layout: pinion at mid-rail; follower = ½ rail length ---
    # Follower (thanh) must cover stroke + mesh margins; rails are 2× that
    follower_len = stroke + 2.0 * tip_r + 2.0 * pitch + 8.0
    n_pitch = max(4, int(math.ceil(follower_len / pitch)))
    if n_pitch % 2:
        n_pitch += 1
    follower_len = n_pitch * pitch  # plate_h / rack span
    rail_len = 2.0 * follower_len  # guide rails S/N (+ bridge)
    # Optional extra rail beyond 2×follower (still keep pinion centered)
    rail_len = max(rail_len, float(d.get("rail_length_z", rail_len)))
    if rail_len < 2.0 * follower_len:
        rail_len = 2.0 * follower_len
    # Center pinion on guide rails
    z_rail_bot = z_nut0
    z_rail_top = z_rail_bot + rail_len
    z_pin = 0.5 * (z_rail_bot + z_rail_top)
    # Follower centered on pinion at mid-stroke rest pose
    z_fol0 = z_pin - 0.5 * follower_len
    rack_len = follower_len
    rack_z0 = z_fol0
    plate_h = follower_len
    print(
        "RL_Z_layout: rail_len=%.1f follower=%.1f (=1/2 rail) z_pin=%.1f "
        "(centered) stroke=%.1f"
        % (rail_len, follower_len, z_pin, stroke)
    )
    # Gear face width locked to pinion; follower Y may be tighter around it
    rack_face_y = face_w
    rack_y0 = cy - 0.5 * rack_face_y
    # Deeper tongue/groove → stiffer lateral guide (same kinematic slot role)
    slot_w, slot_d = 3.6, 3.0
    bar_y = max(bar_y, rack_face_y + 2.0 * slot_d + 4.0)

    y_pin_lo = cy - 0.5 * face_w
    y_pin_hi = cy + 0.5 * face_w
    # Shared Y thickness: Cap == Rail (guide band + tongue tip)
    # bearing_t already from cfg; size rail band so band + tongue = bearing_t
    tong_overlap = 1.2
    tong_stick = rail_clear + (slot_d - 0.45)
    rail_t = max(3.0, float(bearing_t) - tong_stick)
    tong_stick = float(bearing_t) - rail_t  # exact: Rail YLength == Cap YLength
    y_s_plane = cy - (0.5 * bar_y + rail_clear + rail_t)  # −Y outer
    y_n_plane = cy + (0.5 * bar_y + rail_clear + rail_t)  # +Y outer
    y_brg_l = y_s_plane  # Bearing_L outer (−Y) == Rail_S outer
    y_brg_r = y_n_plane - bearing_t  # Cap_N / Rail_N share same Y span
    print(
        "RL_thickness: Cap=Rail=%.2f mm (rail_t=%.2f + tongue_stick=%.2f)"
        % (bearing_t, rail_t, tong_stick)
    )
    # Knob face 20 mm beyond Rail_N outer (+Y); shaft lengthens with it
    knob_clear_n = float(d.get("knob_clear_from_rail_n", 20.0))
    y_knob = y_n_plane + knob_clear_n
    # Friction washer stays on Rail_N outer face
    y_fric = y_brg_r + bearing_t + 0.2
    # Shaft seats in blind knob bore — does NOT pass through outer face
    knob_seat = float(d.get("knob_seat_depth", 8.0))
    knob_seat = max(5.0, min(knob_seat, knob_h - 3.0))  # >=3 mm solid outer wall
    tip_hole_len = float(d.get("shaft_tip_hole_len", 6.0))  # short M3 + D-flat zone
    tip_hole_len = max(4.0, min(tip_hole_len, knob_seat))
    y_shaft0 = y_brg_l - 2.0
    y_shaft_end = y_knob + knob_seat
    shaft_len = y_shaft_end - y_shaft0
    print(
        "RL_shaft->knob: clear_N=%.1f y_knob=%.1f seat=%.1f end=%.1f (len=%.1f) blind"
        % (knob_clear_n, y_knob, knob_seat, y_shaft_end, shaft_len)
    )
    print(
        "RL_plane_S: y=%.3f | RL_plane_N: y=%.3f (bearing outer = rail outer)"
        % (y_s_plane, y_n_plane)
    )

    cols = {
        "pinion": (1.0, 0.45, 0.05),
        "knob": (0.45, 0.25, 0.55),
        "fric": (0.35, 0.35, 0.38),
        "brg": (0.30, 0.50, 0.75),
        "cap": (0.40, 0.60, 0.85),
        "fol": (0.25, 0.72, 0.35),
        "bridge": (0.45, 0.55, 0.62),
        "scale": (0.85, 0.85, 0.20),
        "stop": (0.75, 0.25, 0.25),
        "wall": (0.70, 0.70, 0.72),
    }
    parts = []
    bush = j_od + 0.35  # print clearance in bearing bore

    # --- RL_Pinion_Shaft: solid pinion fused with shaft (one print) ---
    local = make_involute_pinion_local(
        module=module,
        teeth=teeth,
        face_w=face_w,
        bore=0.0,
        alpha_deg=alpha_deg,
        tooth_clear=tooth_clear,
    )
    g_math = rp["gear"]
    uni = verify_pinion_teeth_uniform(local, g_math, face_w=face_w)
    print(
        "RL_Pinion tooth_uniform: %s — max_rel_dev=%.4f mean_vol=%.2f"
        % (
            "PASS" if uni["pass"] else "FAIL",
            float(uni.get("max_rel_dev", 0.0)),
            float(uni.get("mean_mm3", 0.0)),
        )
    )
    if not uni["pass"]:
        raise RuntimeError(
            "RL_Pinion teeth not identical: %s" % uni.get("reason", uni)
        )
    local.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0)
    pinion = place_pinion_axis_y(local, face_w=face_w, x=cx, y=cy, z=z_pin)

    shaft = _cyl_y(j_od, shaft_len, cx, y_shaft0, z_pin)
    sh_s = _cyl_y(j_od + 3.0, 2.0, cx, y_brg_l + bearing_t + 0.3, z_pin)
    sh_n = _cyl_y(j_od + 3.0, 2.0, cx, y_brg_r - 2.3, z_pin)
    # Mid-span thickeners (OD > journal) — stiffen plastic shaft without changing bore
    stiff_od = j_od + 2.8
    span_s0 = y_brg_l + bearing_t + 2.5
    span_s1 = y_pin_lo - 0.8
    span_n0 = y_pin_hi + 0.8
    span_n1 = y_brg_r - 0.8
    pinion_shaft = _as_one_solid(pinion.fuse(shaft).fuse(sh_s).fuse(sh_n))
    if span_s1 > span_s0 + 1.0:
        pinion_shaft = _as_one_solid(
            pinion_shaft.fuse(_cyl_y(stiff_od, span_s1 - span_s0, cx, span_s0, z_pin))
        )
    if span_n1 > span_n0 + 1.0:
        pinion_shaft = _as_one_solid(
            pinion_shaft.fuse(_cyl_y(stiff_od, span_n1 - span_n0, cx, span_n0, z_pin))
        )
    # Stiffen exposed shaft between washer and knob (skip washer Y)
    gap0 = y_fric + friction_t + 0.5
    gap1 = y_knob - 0.8
    if gap1 > gap0 + 1.0 and not active_cam:
        pinion_shaft = _as_one_solid(
            pinion_shaft.fuse(_cyl_y(stiff_od, gap1 - gap0, cx, gap0, z_pin))
        )
    if active_cam:
        # D-flat dài cho ống cam: quay cùng trục nhưng trượt dọc Y
        cam_flat_x0 = cx + 0.5 * j_od - 1.15
        cam_flat_y0 = y_fric + 0.2
        cam_flat = Part.makeBox(
            2.0,
            (y_knob + 1.0) - cam_flat_y0,
            j_od + 1.0,
        )
        cam_flat.translate(
            App.Vector(cam_flat_x0, cam_flat_y0, z_pin - 0.5 * (j_od + 1.0))
        )
        try:
            pinion_shaft = _as_one_solid(pinion_shaft.cut(cam_flat))
        except Exception:
            pass
    # Short D-flat + M3 cross hole only near tip (knob seat) — not full shaft
    y_tip0 = y_shaft_end - tip_hole_len
    flat_depth = 0.9
    flat_x0 = cx + 0.5 * j_od - flat_depth
    flat = Part.makeBox(flat_depth + 1.0, tip_hole_len + 0.8, j_od + 1.0)
    flat.translate(
        App.Vector(flat_x0, y_tip0 - 0.2, z_pin - 0.5 * (j_od + 1.0))
    )
    try:
        pinion_shaft = _as_one_solid(pinion_shaft.cut(flat))
    except Exception:
        pass
    try:
        y_hs = y_tip0 + 0.5 * tip_hole_len
        pinion_shaft = _as_one_solid(
            pinion_shaft.cut(
                _m3_hole_x(cx - 0.5 * j_od - 2.0, y_hs, z_pin, j_od + 4.0)
            )
        )
    except Exception:
        pass
    parts.append(("RL_Pinion_Shaft", pinion_shaft, cols["pinion"]))
    print(
        "RL_Pinion_Shaft: fused print | tip M3+flat len=%.1f | m=%.1f z=%d"
        % (tip_hole_len, module, teeth)
    )
    tip_to_root_clear = (cx - (pitch_r + module)) - (x_pitch - 1.25 * module)
    print(
        "RL_mesh: x_pitch=%.2f pitch_r=%.2f bl=%.2f tip_to_rack_root=%.2f"
        % (x_pitch, pitch_r, center_bl, tip_to_root_clear)
    )

    def _m3_clamp_z(sz: float) -> float:
        """+/-Z hole centers — ears fully outside journal block (thin clamp stack)."""
        # Outside bearing_h so bolt only goes through thin ears (not half bearing_w)
        half = 0.5 * bearing_h + 0.5 * BOLT_EAR + 1.5
        half = max(half, 0.5 * bush + 0.5 * M3_CLEAR + 5.0)
        return z_pin + sz * half

    print(
        "RL_M3_pitch: ez half=%.1f | c-c=%.1f | bush=%.1f (clear of shaft)"
        % (
            abs(_m3_clamp_z(1.0) - z_pin),
            abs(_m3_clamp_z(1.0) - _m3_clamp_z(-1.0)),
            bush,
        )
    )
    _grip = M3_CAP_CLAMP_T + M3_RAIL_CLAMP_T
    print(
        "RL_M3_grip: Cap=%.1f + Rail=%.1f = %.1f mm | bolt=%.0f nut~%.1f "
        "(need grip+nut <= bolt) %s"
        % (
            M3_CAP_CLAMP_T,
            M3_RAIL_CLAMP_T,
            _grip,
            M3_BOLT_L,
            M3_NUT_H,
            "OK" if (_grip + M3_NUT_H) <= M3_BOLT_L + 0.5 else "TOO_LONG",
        )
    )

    def _add_clamp_ears_m3(
        solid: Part.Shape,
        y0: float,
        *,
        for_cap: bool,
    ) -> Part.Shape:
        """
        Thin clamp plate at X=cx spanning both +/-Z holes (fits M3x16):
          Cap  -- +X pad CAP_CLAMP_T + CB
          Rail -- -X pad RAIL_CLAMP_T + nut pocket
        One plate fuses to journal half (C1), holes only through thin stack.
        """
        hy = y0 + 0.5 * bearing_t
        eps = 0.05
        x_cap_out = cx + M3_CAP_CLAMP_T
        x_rail_out = cx - M3_RAIL_CLAMP_T
        ez_lo = _m3_clamp_z(-1.0)
        ez_hi = _m3_clamp_z(1.0)
        z0_pad = ez_lo - 0.5 * BOLT_EAR
        z_span = (ez_hi + 0.5 * BOLT_EAR) - z0_pad
        if for_cap:
            pad = Part.makeBox(M3_CAP_CLAMP_T + eps, bearing_t, z_span)
            pad.translate(App.Vector(cx - eps, y0, z0_pad))
            solid = _as_one_solid(solid.fuse(pad))
            # Pad spans journal Z — keep shaft bore open
            try:
                solid = _as_one_solid(
                    solid.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
                )
            except Exception:
                pass
            for ez in (ez_lo, ez_hi):
                try:
                    solid = _as_one_solid(
                        solid.cut(
                            _m3_hole_x(
                                cx - eps, hy, ez, M3_CAP_CLAMP_T + 2.0 * eps + 0.4
                            )
                        )
                    )
                except Exception:
                    pass
                try:
                    solid = _as_one_solid(
                        solid.cut(_m3_head_cbore_x(x_cap_out, hy, ez))
                    )
                except Exception:
                    pass
        else:
            pad = Part.makeBox(M3_RAIL_CLAMP_T + eps, bearing_t, z_span)
            pad.translate(App.Vector(x_rail_out, y0, z0_pad))
            solid = _as_one_solid(solid.fuse(pad))
            try:
                solid = _as_one_solid(
                    solid.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
                )
            except Exception:
                pass
            for ez in (ez_lo, ez_hi):
                try:
                    solid = _as_one_solid(
                        solid.cut(
                            _m3_hole_x(
                                x_rail_out - 0.2, hy, ez, M3_RAIL_CLAMP_T + eps + 0.6
                            )
                        )
                    )
                except Exception:
                    pass
                try:
                    solid = _as_one_solid(
                        solid.cut(_m3_nut_pocket_x(x_rail_out, hy, ez))
                    )
                except Exception:
                    pass
        return solid

    def _bearing_block(y0: float, *, for_cap: bool) -> Part.Shape:
        """
        Full journal block; Cap = +X half, Rail = -X half + foot.
        M3 ears applied after X-split.
        """
        block = Part.makeBox(bearing_w, bearing_t, bearing_h)
        block.translate(App.Vector(cx - 0.5 * bearing_w, y0, z_pin - 0.5 * bearing_h))
        solid = _as_one_solid(
            block.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
        )
        if not for_cap:
            # Foot pads both sides of journal (symmetric about z_pin / travel mid)
            foot_h_local = 5.5
            for z_foot0 in (
                z_pin - 0.5 * bearing_h - foot_h_local,
                z_pin + 0.5 * bearing_h,
            ):
                foot = Part.makeBox(bearing_w + 8.0, bearing_t, foot_h_local)
                foot.translate(
                    App.Vector(
                        cx - 0.5 * (bearing_w + 8.0),
                        y0,
                        z_foot0,
                    )
                )
                solid = _as_one_solid(solid.fuse(foot))
        return solid

    print(
        "RL_fastener: %s | clear=D%.1f | clamp=+/-Z bolt//X (top-down after orient)"
        % (FASTENER_SPEC, M3_CLEAR)
    )

    # Split at shaft X=cx (Rail_S / Cap_S); N = mirror later
    brg_l_lo = _add_clamp_ears_m3(
        _cut_keep_x_le(_bearing_block(y_brg_l, for_cap=False), cx + 0.05),
        y_brg_l,
        for_cap=False,
    )
    brg_l_hi = _add_clamp_ears_m3(
        _cut_keep_x_ge(_bearing_block(y_brg_l, for_cap=True), cx - 0.05),
        y_brg_l,
        for_cap=True,
    )

    washer = _cyl_y(friction_od, friction_t, cx, y_fric, z_pin)
    washer = washer.cut(_cyl_y(j_od + 0.5, friction_t + 2.0, cx, y_fric - 1.0, z_pin))
    parts.append(("RL_Friction_Washer", _as_one_solid(washer), cols["fric"]))

    # RL_Knob — blind socket; body of revolution (+ optional set-screw)
    # Keep 8-fold / axial symmetry about shaft (Y); no one-sided gouges.
    knob = _cyl_y(knob_od, knob_h * 0.35, cx, y_knob, z_pin).fuse(
        _cyl_y(grip_od, knob_h, cx, y_knob, z_pin)
    )
    # Knurl flutes — axes on circle, full height, centered on knob Y
    for i in range(8):
        a = math.radians(i * 45.0)
        fr = grip_od / 2.0 - 0.5
        knob = knob.cut(
            _cyl_y(
                4.4,
                knob_h + 0.6,
                cx + fr * math.cos(a),
                y_knob - 0.3,
                z_pin + fr * math.sin(a),
            )
        )
    # Blind bore from washer face — coaxial, stops before outer face
    socket = _cyl_y(j_od + 0.35, knob_seat + 0.6, cx, y_knob - 0.3, z_pin)
    try:
        knob = knob.cut(socket)
    except Exception:
        pass
    y_hs = y_tip0 + 0.5 * tip_hole_len
    if not active_cam:
        # Internal D-flat (match shaft) — only +X side of bore, stays inside grip
        flat_depth = 0.9
        flat_x0 = cx + 0.5 * j_od - flat_depth
        kflat = Part.makeBox(flat_depth + 1.0, tip_hole_len + 0.8, j_od + 1.0)
        kflat.translate(
            App.Vector(
                flat_x0,
                y_tip0 - 0.2,
                z_pin - 0.5 * (j_od + 1.0),
            )
        )
        try:
            knob = knob.cut(kflat)
        except Exception:
            pass
        # M3 set-screw through axis (// X), centered on z_pin — not a +Z-only gouge
        try:
            knob = knob.cut(
                _m3_hole_x(cx - 0.5 * j_od - 2.0, y_hs, z_pin, j_od + 4.0)
            )
        except Exception:
            pass
    else:
        # Knob free-play ±40°: rãnh cung quanh stop-pin + FACE CAM theo góc.
        # (Ramp XY phẳng đùn //Z KHÔNG đổi Y khi xoay quanh Y — đã fail rotate-check.)
        # rise(|θ|): 0 @ nghỉ → ~3 mm @ ±40° → đẩy ống cam −Y trước khi chốt kéo pinion.
        ring = _cyl_y(15.2, 4.0, cx, y_hs - 2.0, z_pin).cut(
            _cyl_y(7.8, 4.4, cx, y_hs - 2.2, z_pin)
        )
        for a_center in (0.0, 180.0):
            wpts = [App.Vector(cx, y_hs - 2.2, z_pin)]
            for k in range(9):
                a = math.radians(a_center - 54.0 + 108.0 * k / 8.0)
                wpts.append(
                    App.Vector(
                        cx + 9.0 * math.cos(a), y_hs - 2.2, z_pin - 9.0 * math.sin(a)
                    )
                )
            wpts.append(App.Vector(cx, y_hs - 2.2, z_pin))
            wedge = Part.Face(Part.makePolygon(wpts)).extrude(App.Vector(0, 4.4, 0))
            try:
                knob = knob.cut(ring.common(wedge))
            except Exception:
                pass
        # Face-cam: gắn NGẬP vào thân núm (y_knob+embed) rồi nhô −Y,
        # tránh _keep_largest_solid nuốt mất lobe (chỉ chạm mặt phẳng thì fuse rời).
        cam_rise = float(d.get("cam_face_rise", 3.0))
        cam_ang = float(d.get("cam_face_angle_deg", 42.0))
        cam_dead = float(d.get("cam_face_dead_deg", 12.0))
        r_cam0, r_cam1 = 6.2, 10.2
        n_seg = 24
        embed = 1.2
        face_y0 = y_knob + embed
        cam_vol = 0.0
        for lobe in (90.0, 270.0):
            for i in range(n_seg):
                a0 = -cam_ang + (2.0 * cam_ang) * i / (n_seg - 1)
                a1 = -cam_ang + (2.0 * cam_ang) * (i + 1) / (n_seg - 1)
                if i == n_seg - 1:
                    a1 = cam_ang
                a_mid = 0.5 * (a0 + a1)
                aa = abs(a_mid)
                if aa <= cam_dead:
                    continue
                rise = cam_rise * min(1.0, (aa - cam_dead) / max(1.0, 40.0 - cam_dead))
                if rise < 0.15:
                    continue
                da = math.radians(max(1.2, abs(a1 - a0) * 1.08))
                am = math.radians(lobe + a_mid)
                p0 = App.Vector(
                    cx + r_cam0 * math.cos(am - 0.5 * da),
                    face_y0,
                    z_pin + r_cam0 * math.sin(am - 0.5 * da),
                )
                p1 = App.Vector(
                    cx + r_cam1 * math.cos(am - 0.5 * da),
                    face_y0,
                    z_pin + r_cam1 * math.sin(am - 0.5 * da),
                )
                p2 = App.Vector(
                    cx + r_cam1 * math.cos(am + 0.5 * da),
                    face_y0,
                    z_pin + r_cam1 * math.sin(am + 0.5 * da),
                )
                p3 = App.Vector(
                    cx + r_cam0 * math.cos(am + 0.5 * da),
                    face_y0,
                    z_pin + r_cam0 * math.sin(am + 0.5 * da),
                )
                try:
                    face = Part.Face(Part.makePolygon([p0, p1, p2, p3, p0]))
                    seg = face.extrude(App.Vector(0, -(rise + embed), 0))
                    knob = knob.fuse(seg)
                    cam_vol += float(seg.Volume)
                except Exception:
                    pass
        knob = _as_one_solid(knob)
        # Không dùng _keep_largest_solid sau face-cam — giữ mọi solid đã fuse.
        print(
            "RL_active_cam_knob: free ±40° | FACE-CAM rise=%.1f mm dead=±%.0f° "
            "to ±%.0f° | cam_seg_vol≈%.1f | slot @ y=%.2f"
            % (cam_rise, cam_dead, cam_ang, cam_vol, y_hs)
        )
    parts.append(("RL_Knob", _as_one_solid(knob), cols["knob"]))
    if active_cam:
        # Giữ face-cam: không _keep_largest_solid (sẽ cắt lobe rời)
        pass
    else:
        parts[-1] = (
            "RL_Knob",
            _keep_largest_solid(_as_one_solid(knob)),
            cols["knob"],
        )
    print(
        "RL_Knob: blind seat=%.1f mm | outer wall~%.1f | 8-flute sym | no through-shaft"
        % (knob_seat, knob_h - knob_seat)
    )
    # RL_Follower: single slide + teeth; length = ½ guide rail (centered on pinion)
    slide = Part.makeBox(bar_x, bar_y, plate_h)
    slide.translate(App.Vector(bar_cx - 0.5 * bar_x, cy - 0.5 * bar_y, z_fol0))
    rack = make_involute_rack(
        module=module,
        length_z=rack_len,
        face_y=rack_face_y,
        body_t=0.0,
        x_pitch=x_pitch,
        y0=rack_y0,
        z0=rack_z0,
        mesh_z=z_pin,
        alpha_deg=alpha_deg,
        tooth_clear=tooth_clear,
        pinion_teeth=teeth,
    )
    mesh = verify_rack_pinion_mesh(pinion, rack)
    ov = mesh.get("overlap_mm3")
    print(
        "RL_mesh_collision: %s — overlap=%.2f mm3 (max %.2f)"
        % (
            "PASS" if mesh["pass"] else "FAIL",
            float(ov) if ov is not None else -1.0,
            float(mesh.get("max_overlap_mm3") or 0.0),
        )
    )
    if not mesh["pass"]:
        raise RuntimeError(
            "HA rack/pinion collide (tooth phase or center distance): %s" % mesh
        )
    # Conjugate spot-check: rotate pinion + translate rack by r*θ (jam detection)
    max_ov_m = float(ov or 0.0)
    for _ang in (0.5 * 360.0 / teeth,):
        _loc = make_involute_pinion_local(
            module=module,
            teeth=teeth,
            face_w=face_w,
            bore=0.0,
            alpha_deg=alpha_deg,
            tooth_clear=tooth_clear,
        )
        _loc.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0 + _ang)
        _pin = place_pinion_axis_y(_loc, face_w=face_w, x=cx, y=cy, z=z_pin)
        _rk = rack.copy()
        _rk.translate(App.Vector(0, 0, pitch_r * math.radians(_ang)))
        _m = verify_rack_pinion_mesh(_pin, _rk)
        max_ov_m = max(max_ov_m, float(_m.get("overlap_mm3") or 0.0))
        if not _m["pass"]:
            raise RuntimeError(
                "HA rack/pinion jam under conjugate motion θ=%.1f°: %s" % (_ang, _m)
            )
    print(
        "RL_mesh_conjugate: PASS - worst_overlap=%.2f mm3 | clear=%.2f bl=%.2f p=%.4f"
        % (max_ov_m, tooth_clear, center_bl, pitch)
    )
    print(
        "RL_gear_math: m=%.1f z=%d a=%.0f s=%.3f e=%.3f tip_root_clr=%.2f"
        % (
            module,
            teeth,
            alpha_deg,
            g_math["tooth_thickness"],
            g_math["space_width"],
            tip_to_root_clear,
        )
    )
    scraper = _as_one_solid(slide.fuse(rack))
    # Overlap teeth into slide (−X) so fuse is one solid; drop any loose teeth
    try:
        rack_ol = rack.copy()
        rack_ol.translate(App.Vector(-1.0, 0, 0))
        fused = slide.fuse(rack_ol)
    except Exception:
        fused = scraper
    n_pre = len(list(getattr(fused, "Solids", []) or []))
    scraper = _keep_largest_solid(_as_one_solid(fused))
    n_post = len(list(getattr(scraper, "Solids", []) or []))
    print(
        "RL_Follower fuse: solids %d -> %d (drop detached teeth; overlap 1.0 into slide)"
        % (n_pre, n_post)
    )
    try:
        scraper = scraper.cut(
            _cyl_y(j_od + 2.0, face_w + 20.0, cx, y_pin_lo - 8.0, z_pin)
        )
    except Exception:
        pass
    for sign in (-1.0, 1.0):
        sy = cy + sign * (0.5 * bar_y - 0.5 * slot_d)
        gcut = Part.makeBox(slot_w + 0.3, slot_d + 0.4, plate_h + 2)
        gcut.translate(
            App.Vector(
                bar_cx - 0.5 * (slot_w + 0.3),
                sy - 0.5 * (slot_d + 0.4),
                z_fol0 - 0.5,
            )
        )
        try:
            nxt = scraper.cut(gcut)
            if nxt is not None and float(nxt.Volume) >= float(scraper.Volume) * 0.55:
                scraper = nxt
        except Exception:
            pass
    scraper = _keep_largest_solid(_as_one_solid(scraper))
    # Ball detent: nấc ĐỘC LẬP với bước răng — răng giữ m lớn (dễ in 3D),
    # bi lò xo tạo độ phân giải mịn (mặc định 0.5 mm). Bi nhỏ Ø1.5 hợp nấc mịn.
    #
    # KHÔNG có cơ cấu riêng từ núm → bi. Chuỗi lực:
    #   xoay núm → pinion → thanh trượt → MÉP RÃNH trên thanh đẩy bi nén lò xo
    #   (cam thụ động bởi mặt cầu). Dừng xoay → lò xo ép bi sập nấc kế.
    det_pitch = float(d.get("detent_pitch", 0.5))
    det_ball_r = float(d.get("detent_ball_r", 0.75))  # Ø1.5
    # Nấc 0.5 mm + bi Ø1.5: dimple cầu sẽ chồng miệng → dùng rãnh V (còn gờ).
    det_off = float(d.get("detent_off", 0.20))
    x_fol_back = bar_cx - 0.5 * bar_x
    if ball_detent:
        v_width = min(0.40, 0.82 * det_pitch)  # miệng < pitch → còn gờ
        v_depth = float(d.get("detent_v_depth", 0.35))
        n_det = max(3, int(math.ceil(0.5 * stroke / det_pitch)) + 1)
        n_cut = 0
        for k in range(-n_det, n_det + 1):
            zc = z_pin + k * det_pitch
            if zc < z_fol0 + 3.0 or zc > z_fol0 + follower_len - 3.0:
                continue
            try:
                # Tam giác V trong mặt XZ, đùn // Y — khắc vào lưng thanh (−X)
                hw = 0.5 * v_width
                pts = [
                    App.Vector(x_fol_back + 0.02, 0.0, zc - hw),
                    App.Vector(x_fol_back - v_depth, 0.0, zc),
                    App.Vector(x_fol_back + 0.02, 0.0, zc + hw),
                    App.Vector(x_fol_back + 0.02, 0.0, zc - hw),
                ]
                wedge = Part.Face(Part.makePolygon(pts)).extrude(
                    App.Vector(0, 4.0, 0)
                )
                wedge.translate(App.Vector(0, cy - 2.0, 0))
                nxt = scraper.cut(wedge)
                if len(list(getattr(nxt, "Solids", []) or [])) == 1:
                    scraper = nxt
                    n_cut += 1
            except Exception:
                pass
        scraper = _keep_largest_solid(_as_one_solid(scraper))
        print(
            "RL_detent_pockets: V-groove nấc=%.2f mm | w=%.2f d=%.2f | "
            "ball Ø%.1f | %d rãnh | gờ giữa nấc | pitch răng=%.2f"
            % (det_pitch, v_width, v_depth, 2.0 * det_ball_r, n_cut, pitch)
        )
        print(
            "RL_detent_kinematics: CAM nhấc bi rồi mới kéo | "
            "khóa: bi sập V mỗi %.2f mm"
            % det_pitch
        )
    parts.append(("RL_Follower", scraper, cols["fol"]))
    print(
        "RL_Follower: slide+teeth | len=%.1f (=1/2 rail %.1f) z[%.1f,%.1f] solids=%d"
        % (
            follower_len,
            rail_len,
            z_fol0,
            z_fol0 + follower_len,
            len(list(getattr(scraper, "Solids", []) or [])),
        )
    )
    print(
        "RL_stiffen: bar_x=%.1f rail_wall=%.1f bearing_t=%.1f "
        "slot=%.1fx%.1f shaft_mid_od=%.1f (kinematics unchanged)"
        % (bar_x, rail_wall, bearing_t, slot_w, slot_d, j_od + 2.8)
    )

    # Guide rails: full rail_len, pinion at geometric center (z_pin)
    rail_h = rail_len
    z_rail0 = z_rail_bot

    def _make_rail(sign: float, *, z0: float | None = None, h: float | None = None) -> Part.Shape:
        z0u = z_rail0 if z0 is None else float(z0)
        hu = rail_h if h is None else float(h)
        ry = cy + sign * (0.5 * bar_y + rail_clear + 0.5 * rail_t)
        rail = Part.makeBox(bar_x + 2 * rail_wall, rail_t, hu)
        rail.translate(
            App.Vector(
                bar_cx - 0.5 * (bar_x + 2 * rail_wall), ry - 0.5 * rail_t, z0u
            )
        )
        # Tongue must OVERLAP the rail body (C1); tip flush with Cap inner face
        tongue_h = max(4.0, hu - 4.0)
        tong_w = slot_w - 0.5
        overlap = tong_overlap
        stick = tong_stick
        tong_dy = overlap + stick
        if sign < 0.0:
            y_inner = y_s_plane + rail_t
            y_tong0 = y_inner - overlap
        else:
            y_inner = y_n_plane - rail_t
            y_tong0 = y_inner - stick
        tongue = Part.makeBox(tong_w, tong_dy, tongue_h)
        tongue.translate(
            App.Vector(
                bar_cx - 0.5 * tong_w,
                y_tong0,
                z0u + 2,
            )
        )
        return _as_one_solid(rail.fuse(tongue))

    rail_s = _make_rail(-1.0, z0=z_rail_bot, h=rail_h)
    print(
        "RL_Bearing_Rail S: len=%.1f z[%.1f,%.1f] pinion_mid=%.1f | N=mirror(S)"
        % (rail_h, z_rail_bot, z_rail_bot + rail_h, z_pin)
    )

    # -------------------------------------------------------------------------
    # RL_Bearing_Rail — see .cursor/rules/ha-bearing-rail.mdc
    #   C1 one solid | C2 tongue | C3 web band (sym about cx) | C10 journal
    #   Clamp: split @ X=cx, bolt // X (+/-Z ears) -> top-down after orient
    # -------------------------------------------------------------------------
    rail_x0 = bar_cx - 0.5 * (bar_x + 2 * rail_wall)
    rail_x1 = bar_cx + 0.5 * (bar_x + 2 * rail_wall)
    brg_x0 = cx - 0.5 * (bearing_w + 8.0)
    brg_x1 = cx + 0.5 * (bearing_w + 8.0)
    # Full web into bearing foot (C1) — stop before journal at cx (no saddle fill)
    # −X face flush with rail outer (no link_x0 overhang / stepped left wall)
    link_x0 = rail_x0
    link_x1 = min(brg_x0 + 8.0, cx - 0.5 * bush - 2.0)
    if link_x1 < link_x0 + 4.0:
        link_x1 = link_x0 + 4.0
    # Web thickness = rail band only — must NOT invade follower Y corridor
    link_t = rail_t
    foot_h = 5.5
    link_z0 = z_pin - 0.5 * bearing_h - foot_h
    link_z1 = z_pin
    y_fol_s = cy - 0.5 * bar_y - rail_clear
    y_fol_n = cy + 0.5 * bar_y + rail_clear
    print(
        "RL_web: X[%.1f,%.1f] t=%.1f (stops before journal)"
        % (link_x0, link_x1, link_t)
    )
    print(
        "RL_rail_thick: wall=%.1f rail_t=%.1f bearing_t=%.1f foot_h=%.1f"
        % (rail_wall, rail_t, bearing_t, foot_h)
    )

    def _stiff_web(y0_plane: float, *, z_bot: float | None = None) -> Part.Shape:
        """
        Full-length stiffener, mirror-symmetric about rail centerline (axis // Z)
        and about mid-travel z_pin.
        """
        z0 = float(z_bot) if z_bot is not None else z_rail0
        z1 = z0 + rail_h
        # Mirror link span about rail mid-X → symmetric about long axis // Z
        xc = 0.5 * (rail_x0 + rail_x1)
        x0 = min(link_x0, 2.0 * xc - link_x1)
        x1 = max(link_x1, 2.0 * xc - link_x0)
        # Keep clear of journal / Cap (+X of cx)
        x1 = min(x1, cx - 0.5 * bush - 2.0)
        dx = max(1.0, x1 - x0)
        rib_w = 6.0
        hz = max(1.0, z1 - z0)
        spine = Part.makeBox(dx, link_t, hz)
        spine.translate(App.Vector(x0, y0_plane, z0))
        pieces = [spine]
        for x_rib in (x0, x1 - rib_w):
            if x_rib < x0 - 0.01 or x_rib > x1 - 0.5:
                continue
            rib = Part.makeBox(rib_w, link_t, hz)
            rib.translate(App.Vector(x_rib, y0_plane, z0))
            pieces.append(rib)
        # Flange full length, same X span (symmetric about Z-axis of rail)
        flange = Part.makeBox(dx, link_t, hz)
        flange.translate(App.Vector(x0, y0_plane, z0))
        pieces.append(flange)
        # Chords symmetric about z_pin
        band = 5.5
        for z_b in (z_pin - band, z_pin):
            chord = Part.makeBox(dx, link_t, band)
            chord.translate(App.Vector(x0, y0_plane, z_b))
            pieces.append(chord)
        out = pieces[0]
        for p in pieces[1:]:
            try:
                out = out.fuse(p)
            except Exception:
                pass
        print(
            "RL_web_symZ: X[%.1f,%.1f] mid=%.1f (rail xc=%.1f) full Z[%.1f,%.1f]"
            % (x0, x1, 0.5 * (x0 + x1), xc, z0, z1)
        )
        return _as_one_solid(out)

    def _nsol(shape: Part.Shape) -> int:
        return len(list(getattr(shape, "Solids", []) or []))

    def _cut_keep_one(solid: Part.Shape, tool: Part.Shape) -> Part.Shape:
        """Boolean cut that refuses to split C1 (rolls back if multi-solid)."""
        try:
            nxt = _as_one_solid(solid.cut(tool))
        except Exception:
            return solid
        if nxt is None or getattr(nxt, "isNull", lambda: False)():
            return solid
        if _nsol(nxt) > 1:
            return solid
        return nxt

    def _under_cavity_x(x_face: float, hy: float, ez: float) -> Part.Shape:
        """Identical cavity outside -X nut face (tool space), both +/-Z holes."""
        h = M3_RAIL_UNDER
        return _cyl_axis_x(M3_UNDER_CAVITY_D, h, x_face - h, hy, ez)

    def _apply_rail_m3_both_sides(solid: Part.Shape, y0: float) -> Part.Shape:
        """Re-cut thin Rail clamp plate holes + nut + under (C8)."""
        hy = y0 + 0.5 * bearing_t
        eps = 0.05
        x_rail_out = cx - M3_RAIL_CLAMP_T
        hole_x0 = x_rail_out - 0.2
        hole_h = M3_RAIL_CLAMP_T + eps + 0.6
        ez_lo = _m3_clamp_z(-1.0)
        ez_hi = _m3_clamp_z(1.0)
        z0_pad = ez_lo - 0.5 * BOLT_EAR
        z_span = (ez_hi + 0.5 * BOLT_EAR) - z0_pad
        pad = Part.makeBox(M3_RAIL_CLAMP_T + eps, bearing_t, z_span)
        pad.translate(App.Vector(x_rail_out, y0, z0_pad))
        try:
            solid = _as_one_solid(solid.fuse(pad))
        except Exception:
            pass
        try:
            solid = _as_one_solid(
                solid.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
            )
        except Exception:
            pass
        for ez in (ez_lo, ez_hi):
            solid = _cut_keep_one(solid, _m3_hole_x(hole_x0, hy, ez, hole_h))
            solid = _cut_keep_one(solid, _m3_nut_pocket_x(x_rail_out, hy, ez))
            solid = _cut_keep_one(solid, _under_cavity_x(x_rail_out, hy, ez))
        for ez in (ez_lo, ez_hi):
            solid = _cut_keep_one(solid, _m3_hole_x(hole_x0, hy, ez, hole_h))
            solid = _cut_keep_one(solid, _m3_nut_pocket_x(x_rail_out, hy, ez))
        return solid

    def _finish_rail_one_solid(
        brg_lo: Part.Shape,
        rail: Part.Shape,
        y0: float,
        y_plane: float,
        *,
        z_bot: float | None = None,
    ) -> Part.Shape:
        """Fuse to one solid (C1); apply identical +/-Z round M3 + under space."""
        web = _stiff_web(y_plane, z_bot=z_bot)
        solid = brg_lo
        for piece in (rail, web):
            try:
                solid = _as_one_solid(solid.fuse(piece))
            except Exception:
                pass
        if _nsol(solid) > 1:
            print(
                "RL_Bearing_Rail y0=%.1f: WARN fuse pre-cut solids=%d"
                % (y0, _nsol(solid))
            )
        solid = _apply_rail_m3_both_sides(solid, y0)
        nsol = _nsol(solid)
        print(
            "RL_Bearing_Rail y0=%.1f: solids=%d (want 1) | +/-Z equal depth+under"
            % (y0, nsol)
        )
        if nsol != 1:
            print("RL_Bearing_Rail FAIL C1: still multi-solid after clamp cuts")
        return solid

    rail_s_assy = _finish_rail_one_solid(
        brg_l_lo, rail_s, y_brg_l, y_s_plane, z_bot=z_rail_bot
    )
    # Rail_N built later as mirror of Rail_S (same Z-axis symmetry)

    def _hole_depth_x(sh: Part.Shape, ez: float, hy: float, *, is_cap: bool) -> float:
        """Depth of clearance bore along X (clamp pad only)."""
        if is_cap:
            x0 = cx - 0.05
            x1 = cx + M3_CAP_CLAMP_T + 0.05
        else:
            x0 = cx - M3_RAIL_CLAMP_T - 0.05
            x1 = cx + 0.05
        first = last = None
        x = x0
        while x <= x1 + 1e-9:
            try:
                empty = not sh.isInside(App.Vector(x, hy, ez), 0.06, True)
            except Exception:
                empty = False
            if empty:
                if first is None:
                    first = x
                last = x
            x += 0.25
        if first is None or last is None:
            return -1.0
        return float(last - first)

    def _ring_closed_yz(sh: Part.Shape, x: float, hy: float, ez: float) -> bool:
        """Material around bore in YZ at r=2.5."""
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            y = hy + 2.5 * math.cos(a)
            z = ez + 2.5 * math.sin(a)
            try:
                if not sh.isInside(App.Vector(x, y, z), 0.08, True):
                    return False
            except Exception:
                return False
        return True

    # C8: re-apply identical +/-Z features after fuse (Rail_S only; N = mirror)
    rail_s_assy = _apply_rail_m3_both_sides(rail_s_assy, y_brg_l)

    def _recut_cap_m3_through(solid: Part.Shape, y0: float) -> Part.Shape:
        hy = y0 + 0.5 * bearing_t
        x_cap_out = cx + M3_CAP_CLAMP_T
        ez_lo = _m3_clamp_z(-1.0)
        ez_hi = _m3_clamp_z(1.0)
        z0_pad = ez_lo - 0.5 * BOLT_EAR
        z_span = (ez_hi + 0.5 * BOLT_EAR) - z0_pad
        pad = Part.makeBox(M3_CAP_CLAMP_T + 0.05, bearing_t, z_span)
        pad.translate(App.Vector(cx - 0.05, y0, z0_pad))
        try:
            solid = _as_one_solid(solid.fuse(pad))
        except Exception:
            pass
        try:
            solid = _as_one_solid(
                solid.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
            )
        except Exception:
            pass
        for ez in (ez_lo, ez_hi):
            try:
                solid = _as_one_solid(
                    solid.cut(_m3_hole_x(cx - 0.15, hy, ez, M3_CAP_CLAMP_T + 0.5))
                )
            except Exception:
                pass
            try:
                solid = _as_one_solid(
                    solid.cut(_m3_head_cbore_x(x_cap_out, hy, ez))
                )
            except Exception:
                pass
        return solid

    brg_l_hi = _recut_cap_m3_through(brg_l_hi, y_brg_l)

    def _verify_m3_pair(
        label: str, sh: Part.Shape, y0: float, *, is_cap: bool
    ) -> bool:
        hy = y0 + 0.5 * bearing_t
        ez_l, ez_r = _m3_clamp_z(-1.0), _m3_clamp_z(1.0)
        d_l = _hole_depth_x(sh, ez_l, hy, is_cap=is_cap)
        d_r = _hole_depth_x(sh, ez_r, hy, is_cap=is_cap)
        half_w = 0.5 * BOLT_EAR
        if is_cap:
            x_mid = cx + 0.5 * M3_CAP_CLAMP_T
        else:
            # Past nut pocket (near split) so AF cut does not fail ring check
            x_mid = cx - 1.0
        ring_l = _ring_closed_yz(sh, x_mid, hy, ez_l)
        ring_r = _ring_closed_yz(sh, x_mid, hy, ez_r)
        under_ok = True
        under_s = "n/a"
        if not is_cap:
            x_rail_out = cx - M3_RAIL_CLAMP_T
            x_u = x_rail_out - 0.5 * M3_RAIL_UNDER
            for ez in (ez_l, ez_r):
                try:
                    if sh.isInside(App.Vector(x_u, hy, ez), 0.08, True):
                        under_ok = False
                except Exception:
                    under_ok = False
            under_s = "yes" if under_ok else "NO"
        depth_ok = abs(d_l - d_r) <= 0.35 and d_l > 0 and d_r > 0
        # Cap/Rail hole depth should match thin clamp pads (~5 mm), not half bearing
        want = M3_CAP_CLAMP_T if is_cap else M3_RAIL_CLAMP_T
        len_ok = abs(d_l - want) <= 1.5 and abs(d_r - want) <= 1.5
        ok = depth_ok and ring_l and ring_r and under_ok and len_ok
        print(
            "RL_M3_verify %s: depth Lo=%.2f Hi=%.2f want~%.1f equal=%s "
            "ring_Lo=%s ring_Hi=%s under=%s -> %s"
            % (
                label,
                d_l,
                d_r,
                want,
                "yes" if depth_ok else "NO",
                "yes" if ring_l else "NO",
                "yes" if ring_r else "NO",
                under_s,
                "PASS" if ok else "FAIL",
            )
        )
        return ok

    brg_l_hi = _as_one_solid(brg_l_hi)

    def _cut_rail_where_cap(
        rail: Part.Shape, cap: Part.Shape, label: str
    ) -> Part.Shape:
        """Remove Rail material that intersects Cap (split at X=cx)."""
        vol = 0.0
        try:
            common = rail.common(cap)
            if common is not None and not common.isNull():
                vol = float(common.Volume)
        except Exception:
            vol = 0.0
        if vol > 0.05:
            try:
                rail = _keep_largest_solid(rail.cut(cap))
            except Exception:
                pass
            try:
                left = rail.common(cap)
                left_v = (
                    float(left.Volume)
                    if left is not None and not left.isNull()
                    else 0.0
                )
            except Exception:
                left_v = -1.0
            print(
                "RL_cut_Rail_Cap_%s: removed_vol=%.1f remain=%.2f solids=%d"
                % (label, vol, left_v, _nsol(rail))
            )
        else:
            print("RL_cut_Rail_Cap_%s: no overlap" % label)
        return rail

    rail_s_assy = _cut_rail_where_cap(rail_s_assy, brg_l_hi, "S")
    rail_s_assy = _apply_rail_m3_both_sides(rail_s_assy, y_brg_l)
    brg_l_hi = _recut_cap_m3_through(brg_l_hi, y_brg_l)

    def _mirror_y(sh: Part.Shape) -> Part.Shape:
        """Mirror about Y=cy → Rail_N / Cap_N from S (same Z-symmetric structure)."""
        try:
            out = sh.mirror(App.Vector(0.0, cy, 0.0), App.Vector(0.0, 1.0, 0.0))
            return _keep_largest_solid(_as_one_solid(out))
        except Exception:
            return sh

    rail_n_assy = _mirror_y(rail_s_assy)
    brg_r_hi = _mirror_y(brg_l_hi)
    print(
        "RL_Bearing_Rail_N: mirror of S about Y=%.3f | solids=%d"
        % (cy, _nsol(rail_n_assy))
    )

    parts.append(("RL_Bearing_Rail_S", rail_s_assy, cols["brg"]))
    parts.append(("RL_Bearing_Rail_N", rail_n_assy, cols["brg"]))
    parts.append(("RL_Bearing_Cap_S", brg_l_hi, cols["cap"]))
    parts.append(("RL_Bearing_Cap_N", brg_r_hi, cols["cap"]))
    _verify_m3_pair("Rail_S", rail_s_assy, y_brg_l, is_cap=False)
    _verify_m3_pair("Rail_N", rail_n_assy, y_brg_r, is_cap=False)
    _verify_m3_pair("Cap_S", brg_l_hi, y_brg_l, is_cap=True)
    _verify_m3_pair("Cap_N", brg_r_hi, y_brg_r, is_cap=True)
    print("RL_Bearing_Rail: C1 one-solid + Z-sym web; N=mirror(S)")
    print(
        "RL_M3_split: Cap=%.0fmm+CB | Rail=%.0fmm+nut | grip=%.0f | M3x%.0f %s"
        % (
            M3_CAP_CLAMP_T,
            M3_RAIL_CLAMP_T,
            M3_CAP_CLAMP_T + M3_RAIL_CLAMP_T,
            M3_BOLT_L,
            "OK" if (M3_CAP_CLAMP_T + M3_RAIL_CLAMP_T + M3_NUT_H) <= M3_BOLT_L + 0.5 else "CHECK",
        )
    )

    # Flat plate // follower (YZ plane, normal X) — bridges Rail_S ↔ Rail_N
    bridge_t = max(2.0, float(d.get("rail_bridge_t", 4.0)))
    bridge_z0 = z_rail_bot
    bridge_h = rail_h
    bridge_y0 = y_s_plane
    bridge_dy = y_n_plane - y_s_plane
    bridge = Part.makeBox(bridge_t, bridge_dy, bridge_h)
    bridge.translate(App.Vector(rail_x0 - bridge_t, bridge_y0, bridge_z0))
    # Ball detent plunger bore (// X) through bridge at mid-travel z_pin
    if ball_detent:
        bore_d = 2.0 * det_ball_r + 0.35  # clear cho bi Ø1.5
        try:
            bridge = _as_one_solid(
                bridge.cut(
                    _cyl_axis_x(
                        bore_d,
                        bridge_t + rail_wall + 2.0,
                        rail_x0 - bridge_t - 1.0,
                        cy,
                        z_pin,
                    )
                )
            )
        except Exception:
            pass
        # Counterbore ngoài cầu cho vành Ø11 + đầu ốc Ø8
        try:
            bridge = _as_one_solid(
                bridge.cut(
                    _cyl_axis_x(
                        11.2,
                        1.4,
                        rail_x0 - bridge_t - 0.1,
                        cy,
                        z_pin,
                    )
                )
            )
        except Exception:
            pass
        # Cửa sổ nhìn cạnh (+Y): thấy bi tì vào rãnh trên lưng thanh
        # (chứng minh: mép rãnh đẩy bi khi thanh chạy — không có cam từ núm)
        try:
            side_win = Part.makeBox(
                bridge_t + rail_wall + 1.5,
                14.0,
                20.0,
            )
            side_win.translate(
                App.Vector(
                    rail_x0 - bridge_t - 0.5,
                    cy + 1.5,
                    z_pin - 10.0,
                )
            )
            nxt = _as_one_solid(bridge.cut(side_win))
            if len(list(getattr(nxt, "Solids", []) or [])) == 1:
                bridge = nxt
        except Exception:
            pass
        print(
            "RL_detent_bridge: bore Ø%.1f // X @ z_pin=%.1f | "
            "cửa sổ +Y nhìn bi↔rãnh thanh"
            % (bore_d, z_pin)
        )
    # No side windows: M3 is top-down (windows looked like deep side notches)
    n_br = len(list(getattr(bridge, "Solids", []) or []))
    parts.append(("RL_Rail_Bridge", _as_one_solid(bridge), cols["bridge"]))
    print(
        "RL_Rail_Bridge: t=%.1f Y-span=%.1f H=%.1f @ x=%.1f solids=%d"
        % (bridge_t, bridge_dy, bridge_h, rail_x0 - 0.5 * bridge_t, n_br)
    )

    # ------------------------------------------------------------------
    # BALL DETENT — chủ động bằng CAM:
    #   đoạn xoay đầu của núm đi vào cam dốc → đẩy ống cam trượt dọc Y.
    #   Ống cam có mặt côn tác động lên tay đẩy của cụm bi, RÚT bi ra
    #   khỏi rãnh trước khi pinion kéo follower trượt.
    #   Hết hành trình rơ ±40° thì chốt chạm đầu rãnh cung và mới bắt đầu
    #   kéo pinion. Nhả tay → lò xo detent đẩy bi về, đồng thời hồi cam.
    # ------------------------------------------------------------------
    if ball_detent:
        if active_cam:
            sl_face = y_knob - 0.3
            sl_col0 = y_knob - 7.45
            sl_cone0 = y_knob - 13.25
            cone = Part.makeCone(7.2, 13.0, sl_col0 - sl_cone0)
            cone.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
            cone.translate(App.Vector(cx, sl_cone0, z_pin))
            collar_cam = _cyl_y(21.4, sl_face - sl_col0, cx, sl_col0, z_pin)
            cam_sleeve = _as_one_solid(cone.fuse(collar_cam))
            # Mặt ống lõm sâu hơn cam_rise + 2 pad tì tại ±Z (khớp lobe núm).
            cam_rise_ref = float(d.get("cam_face_rise", 3.0))
            try:
                recess = _cyl_y(
                    22.0,  # rộng hơn r_cam1
                    cam_rise_ref + 1.2,
                    cx,
                    sl_face - (cam_rise_ref + 0.6),
                    z_pin,
                )
                cam_sleeve = _as_one_solid(cam_sleeve.cut(recess))
            except Exception:
                pass
            # Pad thấp: đỉnh dưới mặt núm một khe nghỉ (~0.35 mm)
            pad_h = 0.40
            pad_r0, pad_r1 = 6.4, 10.0
            for lobe in (90.0, 270.0):
                am = math.radians(lobe)
                da = math.radians(16.0)
                q0 = App.Vector(
                    cx + pad_r0 * math.cos(am - 0.5 * da),
                    sl_face - pad_h,
                    z_pin + pad_r0 * math.sin(am - 0.5 * da),
                )
                q1 = App.Vector(
                    cx + pad_r1 * math.cos(am - 0.5 * da),
                    sl_face - pad_h,
                    z_pin + pad_r1 * math.sin(am - 0.5 * da),
                )
                q2 = App.Vector(
                    cx + pad_r1 * math.cos(am + 0.5 * da),
                    sl_face - pad_h,
                    z_pin + pad_r1 * math.sin(am + 0.5 * da),
                )
                q3 = App.Vector(
                    cx + pad_r0 * math.cos(am + 0.5 * da),
                    sl_face - pad_h,
                    z_pin + pad_r0 * math.sin(am + 0.5 * da),
                )
                try:
                    pad = Part.Face(Part.makePolygon([q0, q1, q2, q3, q0])).extrude(
                        App.Vector(0, pad_h, 0)
                    )
                    cam_sleeve = cam_sleeve.fuse(pad)
                except Exception:
                    pass
            cam_sleeve = _as_one_solid(cam_sleeve)
            cam_sleeve = _as_one_solid(
                cam_sleeve.cut(
                    _cyl_y(j_od + 0.4, (sl_face - sl_cone0) + 2.0, cx, sl_cone0 - 1.0, z_pin)
                )
            )
            ridge = Part.makeBox(1.45, (sl_face - 0.05) - (sl_cone0 + 0.05), 5.8)
            ridge.translate(App.Vector(cx + 2.95, sl_cone0 + 0.05, z_pin - 2.9))
            cam_sleeve = _as_one_solid(cam_sleeve.fuse(ridge))
            stop_pin = _cyl_axis_x(3.4, 14.0, cx - 7.0, y_hs, z_pin)
            parts.append(("RL_Cam_Sleeve", cam_sleeve, (0.95, 0.45, 0.10)))
            parts.append(("RL_Cam_StopPin", _as_one_solid(stop_pin), (0.22, 0.22, 0.25)))
            print(
                "RL_active_cam: face-cam pads @ ±Z | sleeve y[%.1f,%.1f] | "
                "θ→push −Y before drive"
                % (sl_cone0, sl_col0)
            )
        xb = x_fol_back - det_off  # tâm bi khi sập vào rãnh (đúng nấc mid)
        ball = _sphere(det_ball_r, xb, cy, z_pin)
        spring_x0 = rail_x0 - bridge_t + 2.6
        spring_x1 = xb - det_ball_r + 0.2
        spring = _cyl_axis_x(
            max(1.0, 2.0 * det_ball_r - 0.3),
            max(1.0, spring_x1 - spring_x0),
            spring_x0,
            cy,
            z_pin,
        )
        shank = _cyl_axis_x(1.6, 3.0, rail_x0 - bridge_t + 0.2, cy, z_pin)
        head = _cyl_axis_x(8.0, 4.0, rail_x0 - bridge_t - 4.0, cy, z_pin)
        collar = _cyl_axis_x(11.0, 1.2, rail_x0 - bridge_t - 1.2, cy, z_pin)
        detent = ball.fuse(spring).fuse(shank).fuse(head).fuse(collar)
        if active_cam:
            # Chân tì côn −X. Đòn bên ngoài web ray (x < web_x_lo) chạy +Y
            # tới cam rồi bắt ngang — tránh Rail_N web / bridge / pinion.
            cone_len = sl_col0 - sl_cone0
            cone_r0, cone_r1 = 7.2, 13.0
            cam_gap = 0.30
            y_f0, y_f1 = sl_cone0 + 0.8, sl_cone0 + 3.5
            r_f0 = cone_r0 + (cone_r1 - cone_r0) * ((y_f0 - sl_cone0) / cone_len)
            r_f1 = cone_r0 + (cone_r1 - cone_r0) * ((y_f1 - sl_cone0) / cone_len)
            x_touch0 = cx - (r_f0 + cam_gap)
            x_touch1 = cx - (r_f1 + cam_gap)
            x_safe = cx - (cone_r1 + cam_gap + 0.5)
            xc_rail = 0.5 * (rail_x0 + rail_x1)
            web_x_lo = min(link_x0, 2.0 * xc_rail - link_x1)
            lever_w = 5.0
            # Toàn bộ đòn nằm ngoài web (và ngoài cầu)
            x_ext = web_x_lo - 5.0
            lever = Part.makeBox(lever_w, (y_f1 + 1.0) - (cy - 4.0), 6.0)
            lever.translate(
                App.Vector(x_ext - 0.5 * lever_w, cy - 4.0, z_pin - 3.0)
            )
            # Nối đòn → đầu ốc/collar (đã có sẵn phía ngoài cầu)
            x_head0 = rail_x0 - bridge_t - 4.0
            x_lever_hi = x_ext + 0.5 * lever_w
            if x_head0 > x_lever_hi + 0.5:
                conn = Part.makeBox(x_head0 - x_lever_hi, 6.0, 6.0)
                conn.translate(App.Vector(x_lever_hi, cy - 3.0, z_pin - 3.0))
                detent = detent.fuse(conn)
            cross = Part.makeBox(
                x_safe - (x_ext - 0.5 * lever_w),
                y_f1 - y_f0,
                6.0,
            )
            cross.translate(
                App.Vector(x_ext - 0.5 * lever_w, y_f0, z_pin - 3.0)
            )
            fpts = [
                App.Vector(x_touch0, y_f0, 0.0),
                App.Vector(x_touch1, y_f1, 0.0),
                App.Vector(x_safe, y_f1, 0.0),
                App.Vector(x_safe, y_f0, 0.0),
                App.Vector(x_touch0, y_f0, 0.0),
            ]
            foot = Part.Face(Part.makePolygon(fpts)).extrude(App.Vector(0, 0, 7.0))
            foot.translate(App.Vector(0, 0, z_pin - 3.5))
            detent = detent.fuse(lever).fuse(cross).fuse(foot)
            try:
                cone_keep = Part.makeCone(
                    cone_r0 + cam_gap, cone_r1 + cam_gap, cone_len
                )
                cone_keep.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
                cone_keep.translate(App.Vector(cx, sl_cone0, z_pin))
                col_keep = _cyl_y(
                    21.4 + 2.0 * cam_gap,
                    sl_face - sl_col0 + 0.5,
                    cx,
                    sl_col0 - 0.25,
                    z_pin,
                )
                detent = _as_one_solid(detent.cut(cone_keep.fuse(col_keep)))
            except Exception:
                pass
            print(
                "RL_active_cam_wedge: lever outside web (x_ext=%.1f web_lo=%.1f) | "
                "foot −X gap=%.2f R≈%.1f→%.1f"
                % (x_ext, web_x_lo, cam_gap, r_f0, r_f1)
            )
        detent = _as_one_solid(detent)
        # Bi chrome nổi — phần ĐƯỢC mép rãnh thanh đẩy khi xoay núm
        parts.append(("RL_Detent", detent, (0.85, 0.88, 0.92)))
        print(
            "RL_detent: bi Ø%.1f + lò xo + ốc | nấc=%.2f mm | stroke=%.0f→~%.0f "
            "nấc | %s"
            % (
                2.0 * det_ball_r,
                det_pitch,
                stroke,
                stroke / det_pitch,
                "CAM chủ động nhấc bi trước khi kéo thanh" if active_cam
                else "ĐẨY BI = mép rãnh THANH (không phải núm/cam riêng)",
            )
        )
        knob_sh = parts[[n for n, _, _ in parts].index("RL_Knob")][1]
        det_pairs = [
            ("Detent", detent, "Rail_Bridge", bridge, 0.05),
            ("Detent", detent, "Follower", scraper, 15.0),
            ("Detent", detent, "Bearing_Rail_S", rail_s_assy, 0.05),
            ("Detent", detent, "Bearing_Rail_N", rail_n_assy, 0.05),
            ("Detent", detent, "Pinion_Shaft", pinion_shaft, 0.05),
            ("Detent", detent, "Knob", knob_sh, 0.05),
        ]
        if active_cam:
            det_pairs.extend(
                [
                    ("Cam_Sleeve", cam_sleeve, "Detent", detent, 0.05),
                    ("Cam_Sleeve", cam_sleeve, "Pinion_Shaft", pinion_shaft, 0.05),
                    ("Cam_Sleeve", cam_sleeve, "Knob", knob_sh, 0.05),
                    ("Cam_StopPin", stop_pin, "Knob", knob_sh, 0.05),
                    ("Cam_StopPin", stop_pin, "Pinion_Shaft", pinion_shaft, 0.05),
                ]
            )
        det_bad = []
        for na, sa, nb, sb, mx in det_pairs:
            try:
                com = sa.common(sb)
                vol = (
                    float(com.Volume)
                    if com is not None and not com.isNull()
                    else 0.0
                )
            except Exception:
                vol = -1.0
            ok = 0.0 <= vol <= mx
            print(
                "RL_detent_clear %s vs %s: overlap=%.3f mm3 (max %.2f) -> %s"
                % (na, nb, vol, mx, "PASS" if ok else "FAIL")
            )
            if not ok:
                det_bad.append((na, nb, vol))
        if det_bad:
            raise RuntimeError("RL ball-detent collision: %s" % det_bad)

    include_bottom_stop = bool(d.get("include_bottom_stop", False))
    include_scale = bool(d.get("include_scale", False))

    if include_bottom_stop:
        stop_w = abs(cx - bar_cx) + max(bar_x, 2 * tip_r) + 12
        stop = Part.makeBox(stop_w, bar_y + 8, stop_h)
        stop.translate(
            App.Vector(
                0.5 * (bar_cx + cx) - 0.5 * stop_w,
                cy - 0.5 * (bar_y + 8),
                z_nut0 - stop_h - 1,
            )
        )
        parts.append(("RL_Bottom_Stop", _as_one_solid(stop), cols["stop"]))

    if include_scale:
        sx0 = bar_cx - 0.5 * bar_x - rail_wall - 5
        for i in range(int(scale_max) + 1):
            L = 4.0 if i % 5 == 0 else 2.2
            mk = Part.makeBox(L, 0.6, 1.2)
            mk.translate(App.Vector(sx0, cy - 0.3, z_nut0 + float(i)))
            parts.append(("RL_Scale_%02d" % i, mk, cols["scale"]))

    if include_demo_wall:
        z0w = z_rail0 - 2
        wall = Part.makeBox(60, 4, z_pin + tip_r + bearing_h - z0w)
        wall.translate(App.Vector(cx - 30, y_n_plane + 8, z0w))
        parts.append(("RL_Demo_Wall_U", _as_one_solid(wall), cols["wall"]))

    print(
        "Rotary_Linear involute | z=%d alpha=%.0f | stroke=%.0f | %.2f turn (%.0f mm/turn)"
        % (teeth, alpha_deg, stroke, stroke / travel, travel)
    )
    print("RL_active_parts: %s" % ", ".join(n for n, _, _ in parts))

    # Orient: travel horizontal (+X); pinion/gear on top (+Z)
    def _orient_travel_horizontal(
        items: list,
    ) -> list:
        out = []
        for name, sh, col in items:
            try:
                s = sh.copy()
            except Exception:
                s = sh
            try:
                # Build frame: travel // +Z, pinion beside rack in X
                s.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
                # Flip so pinion sits above follower (gear on top)
                s.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180.0)
                s = _as_one_solid(s)
            except Exception:
                pass
            out.append((name, s, col))
        print(
            "RL_orient: +90°Y then +180°X | travel // +X, pinion on top (+Z)"
        )
        return out

    return _orient_travel_horizontal(parts)
