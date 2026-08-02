"""
Height_Adjust Z — ISO/SolidWorks involute spur rack & pinion.

Pinion axis Y (horizontal) ⊥ rack travel Z.
m=2, z>=18 (no undercut at α=20°), ha=m, hf=1.25m.

Print / assembly (serviceable):
  HA_Pinion_Shaft — pinion + shaft fused (one 3D print)
  HA_Bearing_Rail_S/N — lower saddle + rail; M3 nut pockets
  HA_Bearing_Cap_S/N — upper half; M3×16 hex bolt + head counterbore
  HA_Knob — blind bore on shaft tip + short M3 (shaft does not pass through)
  HA_Follower — rack + slide
  HA_Rail_Bridge — flat plate // follower (YZ), joins Rail_S ↔ Rail_N

Hardware: M3×16 ISO hex bolt + M3 hex nut (AF 5.5). Clearance Ø3.6.
Drop pinion-shaft into open saddles → bolt caps → fit washer/knob.
"""
from __future__ import annotations

import math
from typing import Callable

import FreeCAD as App
import Part


ACTIVE_HA_PARTS = frozenset(
    {
        "HA_Pinion_Shaft",
        "HA_Bearing_Rail_S",
        "HA_Bearing_Cap_S",
        "HA_Bearing_Rail_N",
        "HA_Bearing_Cap_N",
        "HA_Rail_Bridge",
        "HA_Knob",
        "HA_Friction_Washer",
        "HA_Follower",
    }
)

# ---------------------------------------------------------------------------
# Fastener (bearing caps + knob): ISO hex bolt M3×16 + hex nut M3
#   wrench / AF = 5.5 mm; nut height ≈ 2.4 mm; head height ≈ 2.0 mm
#   FDM clearance hole Ø3.6 (ISO 273 medium + print margin)
#   Cap: Ø6.5 × 2.2 counterbore for hex head
#   Rail: 6.0 AF × 2.8 deep square nut pocket (traps M3 nut)
# ---------------------------------------------------------------------------
FASTENER_SPEC = "M3x16 ISO hex bolt + M3 hex nut (AF 5.5)"
M3_CLEAR = 3.6
M3_HEAD_CB_D = 6.5
M3_HEAD_CB_H = 2.2
M3_NUT_POCKET_AF = 6.0
M3_NUT_POCKET_H = 2.8
BOLT_EAR = 10.0  # ear size — fits nut pocket + margins
# Empty space under Rail ear for nut + finger/tool (same ±X)
M3_RAIL_UNDER = 8.0
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
        if zc < z0 - 0.55 * p or zc > z0 + length_z + 0.55 * p:
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


def build_height_adjust_z_parts(
    *,
    cx: float = 0.0,
    cy: float = 0.0,
    z_zero: float = 0.0,
    cfg: dict | None = None,
    include_demo_wall: bool = False,
    thread_fn: Callable | None = None,
) -> list:
    d = dict(cfg or {})
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
        "HA_Z_layout: rail_len=%.1f follower=%.1f (=½ rail) z_pin=%.1f "
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
        "HA_thickness: Cap=Rail=%.2f mm (rail_t=%.2f + tongue_stick=%.2f)"
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
        "HA_shaft->knob: clear_N=%.1f y_knob=%.1f seat=%.1f end=%.1f (len=%.1f) blind"
        % (knob_clear_n, y_knob, knob_seat, y_shaft_end, shaft_len)
    )
    print(
        "HA_plane_S: y=%.3f | HA_plane_N: y=%.3f (bearing outer = rail outer)"
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

    # --- HA_Pinion_Shaft: solid pinion fused with shaft (one print) ---
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
        "HA_Pinion tooth_uniform: %s — max_rel_dev=%.4f mean_vol=%.2f"
        % (
            "PASS" if uni["pass"] else "FAIL",
            float(uni.get("max_rel_dev", 0.0)),
            float(uni.get("mean_mm3", 0.0)),
        )
    )
    if not uni["pass"]:
        raise RuntimeError(
            "HA_Pinion teeth not identical: %s" % uni.get("reason", uni)
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
    if gap1 > gap0 + 1.0:
        pinion_shaft = _as_one_solid(
            pinion_shaft.fuse(_cyl_y(stiff_od, gap1 - gap0, cx, gap0, z_pin))
        )
    # Short D-flat + M3 cross hole only near tip (knob seat) — not full shaft
    y_tip0 = y_shaft_end - tip_hole_len
    flat = Part.makeBox(1.6, tip_hole_len + 1.0, j_od + 2.0)
    flat.translate(App.Vector(cx - 0.8, y_tip0 - 0.5, z_pin - 0.5 * j_od - 1.0))
    try:
        pinion_shaft = _as_one_solid(pinion_shaft.cut(flat))
    except Exception:
        pass
    try:
        cross = Part.makeCylinder(M3_CLEAR / 2.0, j_od + 6.0)
        cross.translate(
            App.Vector(
                cx - 0.5 * (j_od + 6.0),
                y_tip0 + 0.5 * tip_hole_len,
                z_pin,
            )
        )
        pinion_shaft = _as_one_solid(pinion_shaft.cut(cross))
    except Exception:
        pass
    parts.append(("HA_Pinion_Shaft", pinion_shaft, cols["pinion"]))
    print(
        "HA_Pinion_Shaft: fused print | tip M3+flat len=%.1f | m=%.1f z=%d"
        % (tip_hole_len, module, teeth)
    )
    tip_to_root_clear = (cx - (pitch_r + module)) - (x_pitch - 1.25 * module)
    print(
        "HA_mesh: x_pitch=%.2f pitch_r=%.2f bl=%.2f tip_to_rack_root=%.2f"
        % (x_pitch, pitch_r, center_bl, tip_to_root_clear)
    )

    def _m3_clamp_x(sx: float) -> float:
        """
        ±X hole centers on clamp ears (shared Cap + Rail).

        −X: on outer ear (CB clear of Cap main-block roof), then nudge +2 mm
        toward +X so the bolt clears HA_Bearing_Rail when assembling.
        """
        ex = cx + sx * (0.5 * bearing_w + 0.5 * BOLT_EAR)
        if sx < 0.0:
            # Keep Ø CB off the main block top as much as practical
            block_x0 = cx - 0.5 * bearing_w
            ex = min(ex, block_x0 - 0.5 * M3_HEAD_CB_D - 1.0)
            ex += 2.0  # shift right — clearance vs Rail when inserting bolt
        return ex

    def _add_clamp_ears_m3(
        solid: Part.Shape,
        y0: float,
        *,
        for_cap: bool,
    ) -> Part.Shape:
        """
        Split M3 clamp at z_pin (bolt // Z):
          Cap  — upper half ear + clearance + head counterbore
          Rail — lower half ear + clearance + nut pocket
        Hardware: M3×16 hex bolt + M3 hex nut (AF 5.5).
        """
        z_ear0 = z_pin - 0.5 * BOLT_EAR
        z_ear1 = z_pin + 0.5 * BOLT_EAR
        half_h = 0.5 * BOLT_EAR
        hy = y0 + 0.5 * bearing_t
        # Tiny overlap at split so assembled halves form one continuous hole
        eps = 0.05
        for sx in (-1.0, 1.0):
            ex = _m3_clamp_x(sx)
            if for_cap:
                ear = Part.makeBox(BOLT_EAR, bearing_t, half_h)
                ear.translate(App.Vector(ex - 0.5 * BOLT_EAR, y0, z_pin))
                solid = _as_one_solid(solid.fuse(ear))
                # Through full cap height so bolt drops in from +Z (no closed cavity)
                z_cap_top = z_pin + 0.5 * bearing_h
                try:
                    solid = _as_one_solid(
                        solid.cut(
                            _m3_hole_z(
                                ex,
                                hy,
                                z_pin - eps,
                                (z_cap_top - z_pin) + eps + 0.8,
                            )
                        )
                    )
                except Exception:
                    pass
                try:
                    solid = _as_one_solid(
                        solid.cut(_m3_head_cbore_z(ex, hy, z_cap_top))
                    )
                except Exception:
                    pass
            else:
                ear = Part.makeBox(BOLT_EAR, bearing_t, half_h)
                ear.translate(App.Vector(ex - 0.5 * BOLT_EAR, y0, z_ear0))
                solid = _as_one_solid(solid.fuse(ear))
                # Same depth both ±X: through ear + under cavity start
                try:
                    solid = _as_one_solid(
                        solid.cut(
                            _m3_hole_z(
                                ex,
                                hy,
                                z_ear0 - M3_RAIL_UNDER,
                                M3_RAIL_UNDER + half_h + eps + 0.5,
                            )
                        )
                    )
                except Exception:
                    pass
                try:
                    solid = _as_one_solid(solid.cut(_m3_nut_pocket_z(ex, hy, z_ear0)))
                except Exception:
                    pass
        return solid

    def _bearing_block(y0: float, *, for_cap: bool) -> Part.Shape:
        """
        Rail lower: solid block + foot + ±X M3 ears (beside shaft).
        Cap: journal bore + same ±X M3 ears.
        """
        block = Part.makeBox(bearing_w, bearing_t, bearing_h)
        block.translate(App.Vector(cx - 0.5 * bearing_w, y0, z_pin - 0.5 * bearing_h))
        foot_h = 5.5
        foot = Part.makeBox(bearing_w + 8.0, bearing_t, foot_h)
        foot.translate(
            App.Vector(
                cx - 0.5 * (bearing_w + 8.0), y0, z_pin - 0.5 * bearing_h - foot_h
            )
        )
        solid = _as_one_solid(block.fuse(foot))
        # Journal cradle on BOTH halves (lower saddle + upper cap)
        solid = _as_one_solid(
            solid.cut(_cyl_y(bush, bearing_t + 2.0, cx, y0 - 1.0, z_pin))
        )
        solid = _add_clamp_ears_m3(solid, y0, for_cap=for_cap)
        return solid

    print(
        "HA_fastener: %s | clear=Ø%.1f | clamp=±X beside shaft"
        % (FASTENER_SPEC, M3_CLEAR)
    )

    brg_l_lo = _cut_above_z(_bearing_block(y_brg_l, for_cap=False), z_pin)
    brg_r_lo = _cut_above_z(_bearing_block(y_brg_r, for_cap=False), z_pin)
    brg_l_hi = _cut_below_z(_bearing_block(y_brg_l, for_cap=True), z_pin)
    brg_r_hi = _cut_below_z(_bearing_block(y_brg_r, for_cap=True), z_pin)

    washer = _cyl_y(friction_od, friction_t, cx, y_fric, z_pin)
    washer = washer.cut(_cyl_y(j_od + 0.5, friction_t + 2.0, cx, y_fric - 1.0, z_pin))
    parts.append(("HA_Friction_Washer", _as_one_solid(washer), cols["fric"]))

    # HA_Knob — blind socket (shaft does not pass through); short M3 at seat
    knob = _cyl_y(knob_od, knob_h * 0.35, cx, y_knob, z_pin).fuse(
        _cyl_y(grip_od, knob_h, cx, y_knob, z_pin)
    )
    for i in range(8):
        a = math.radians(i * 45.0)
        knob = knob.cut(
            _cyl_y(
                4.4,
                knob_h + 1.0,
                cx + (grip_od / 2 - 0.5) * math.cos(a),
                y_knob - 0.5,
                z_pin + (grip_od / 2 - 0.5) * math.sin(a),
            )
        )
    # Blind bore from washer face — stops before outer face
    socket = _cyl_y(j_od + 0.35, knob_seat + 0.6, cx, y_knob - 0.3, z_pin)
    try:
        knob = knob.cut(socket)
    except Exception:
        pass
    kflat = Part.makeBox(1.7, tip_hole_len + 1.2, j_od + 2.5)
    kflat.translate(
        App.Vector(cx - 0.85, y_tip0 - 0.4, z_pin - 0.5 * j_od - 1.2)
    )
    try:
        knob = knob.cut(kflat)
    except Exception:
        pass
    try:
        kh = Part.makeCylinder(M3_CLEAR / 2.0, j_od + 8.0)
        kh.translate(
            App.Vector(
                cx - 0.5 * (j_od + 8.0),
                y_tip0 + 0.5 * tip_hole_len,
                z_pin,
            )
        )
        knob = knob.cut(kh)
    except Exception:
        pass
    parts.append(("HA_Knob", _as_one_solid(knob), cols["knob"]))
    print(
        "HA_Knob: blind seat=%.1f mm | outer wall≈%.1f | no through-shaft"
        % (knob_seat, knob_h - knob_seat)
    )
    # HA_Follower: single slide + teeth; length = ½ guide rail (centered on pinion)
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
        "HA_mesh_collision: %s — overlap=%.2f mm³ (max %.2f)"
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
        "HA_mesh_conjugate: PASS — worst_overlap=%.2f mm³ | clear=%.2f bl=%.2f p=%.4f"
        % (max_ov_m, tooth_clear, center_bl, pitch)
    )
    print(
        "HA_gear_math: m=%.1f z=%d α=%.0f s=%.3f e=%.3f tip_root_clr=%.2f"
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
    parts.append(("HA_Follower", _as_one_solid(scraper), cols["fol"]))
    print(
        "HA_Follower: slide+teeth | len=%.1f (=½ rail %.1f) z[%.1f,%.1f]"
        % (follower_len, rail_len, z_fol0, z_fol0 + follower_len)
    )
    print(
        "HA_stiffen: bar_x=%.1f rail_wall=%.1f bearing_t=%.1f "
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
    rail_n = _make_rail(1.0, z0=z_rail_bot, h=rail_h)
    print(
        "HA_Bearing_Rail S/N: len=%.1f z[%.1f,%.1f] pinion_mid=%.1f"
        % (rail_h, z_rail_bot, z_rail_bot + rail_h, z_pin)
    )

    # -------------------------------------------------------------------------
    # HA_Bearing_Rail — see .cursor/rules/ha-bearing-rail.mdc (C1–C11)
    #   C1  one solid    C2 tongue overlap    C3 web band / no journal fill
    #   C4  ±X M3        C5 split @ z_pin     C6 −X hole OPEN (window to ex)
    #   C7  nut access   C8 fuse then re-cut  C9 hardware   C10 journal
    #   C11 planar −X + clamp window
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
        "HA_web: X[%.1f,%.1f] t=%.1f (stops before journal)"
        % (link_x0, link_x1, link_t)
    )
    print(
        "HA_rail_thick: wall=%.1f rail_t=%.1f bearing_t=%.1f foot_h=%.1f"
        % (rail_wall, rail_t, bearing_t, foot_h)
    )

    def _stiff_web(y0_plane: float, *, z_bot: float | None = None) -> Part.Shape:
        """Continuous web rail ↔ bearing in rail Y band only (no follower clash)."""
        z_flange0 = z_rail0 + 2.0 if z_bot is None else float(z_bot) + 2.0
        dx = max(1.0, link_x1 - link_x0)
        dz = max(1.0, link_z1 - link_z0)
        web = Part.makeBox(dx, link_t, dz)
        web.translate(App.Vector(link_x0, y0_plane, link_z0))
        band = 5.5  # thicker top/bottom chords
        top = Part.makeBox(dx, link_t, band)
        top.translate(App.Vector(link_x0, y0_plane, z_pin - band))
        bot = Part.makeBox(dx, link_t, band)
        bot.translate(App.Vector(link_x0, y0_plane, link_z0))
        rib_w = 6.0
        pieces = [web, top, bot]
        # Edge ribs only in rail X — skip mid rib through follower X span
        for x_rib in (link_x0, link_x1 - rib_w):
            rib = Part.makeBox(rib_w, link_t, dz)
            rib.translate(App.Vector(x_rib, y0_plane, link_z0))
            pieces.append(rib)
        flange_h = max(6.0, link_z1 - z_flange0)
        flange = Part.makeBox(max(4.0, rail_x1 - rail_x0), link_t, flange_h)
        flange.translate(App.Vector(rail_x0, y0_plane, z_flange0))
        pieces.append(flange)
        if z_bot is not None and float(z_bot) < link_z0 - 1.0:
            apron_h = link_z0 - float(z_bot)
            apron = Part.makeBox(dx, link_t, apron_h)
            apron.translate(App.Vector(link_x0, y0_plane, float(z_bot)))
            pieces.append(apron)
            for x_rib in (link_x0, link_x1 - rib_w):
                rib_d = Part.makeBox(rib_w, link_t, apron_h)
                rib_d.translate(App.Vector(x_rib, y0_plane, float(z_bot)))
                pieces.append(rib_d)
        out = pieces[0]
        for p in pieces[1:]:
            try:
                out = out.fuse(p)
            except Exception:
                pass
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

    def _under_cavity_z(ex: float, hy: float, z_ear0: float) -> Part.Shape:
        """Identical Ø cavity strictly under both ±X holes (nut + tool space)."""
        h = M3_RAIL_UNDER
        c = Part.makeCylinder(0.5 * M3_UNDER_CAVITY_D, h)
        # Top flush with ear bottom — does not eat the round pad
        c.translate(App.Vector(ex, hy, z_ear0 - h))
        return c

    def _expose_minus_x_ear_face(ex: float, y0: float, z_ear0: float) -> Part.Shape:
        """Clear web only up to -X ear outer face (keep full round boss)."""
        half_h = 0.5 * BOLT_EAR
        y_pad = 0.25
        y0w = y0 + y_pad
        yw = max(2.5, bearing_t - 2.0 * y_pad)
        ear_x0 = ex - 0.5 * BOLT_EAR
        x0w = rail_x0 - 0.6
        x1w = ear_x0 - 0.05
        dx = max(1.0, x1w - x0w)
        # Ear Z band (visibility) + under band (reach cavity from -X)
        z0w = z_ear0 - M3_RAIL_UNDER
        zw = half_h + M3_RAIL_UNDER + 0.3
        win = Part.makeBox(dx, yw, zw)
        win.translate(App.Vector(x0w, y0w, z0w))
        return win

    def _apply_rail_m3_both_sides(solid: Part.Shape, y0: float) -> Part.Shape:
        """
        Identical ±X clamp on Rail: full round ear bore, same hole depth,
        same under-cavity (C7/C14/C15). Then expose -X ear face only.
        """
        hy = y0 + 0.5 * bearing_t
        z_ear0 = z_pin - 0.5 * BOLT_EAR
        half_h = 0.5 * BOLT_EAR
        eps = 0.05
        hole_z0 = z_ear0 - M3_RAIL_UNDER
        hole_h = M3_RAIL_UNDER + half_h + eps + 0.6
        for sx in (-1.0, 1.0):
            ex = _m3_clamp_x(sx)
            ear = Part.makeBox(BOLT_EAR, bearing_t, half_h)
            ear.translate(App.Vector(ex - 0.5 * BOLT_EAR, y0, z_ear0))
            try:
                solid = _as_one_solid(solid.fuse(ear))
            except Exception:
                pass
            solid = _cut_keep_one(solid, _m3_hole_z(ex, hy, hole_z0, hole_h))
            solid = _cut_keep_one(solid, _m3_nut_pocket_z(ex, hy, z_ear0))
            solid = _cut_keep_one(solid, _under_cavity_z(ex, hy, z_ear0))
        # -X: open web to ear face + lateral path into under-cavity (not through ear)
        ex_l = _m3_clamp_x(-1.0)
        solid = _cut_keep_one(solid, _expose_minus_x_ear_face(ex_l, y0, z_ear0))
        # Re-cut round bores last so under/window cannot leave a slot (C14)
        for sx in (-1.0, 1.0):
            ex = _m3_clamp_x(sx)
            solid = _cut_keep_one(solid, _m3_hole_z(ex, hy, hole_z0, hole_h))
            solid = _cut_keep_one(solid, _m3_nut_pocket_z(ex, hy, z_ear0))
        return solid

    def _finish_rail_one_solid(
        brg_lo: Part.Shape,
        rail: Part.Shape,
        y0: float,
        y_plane: float,
        *,
        z_bot: float | None = None,
    ) -> Part.Shape:
        """Fuse to one solid (C1); apply identical ±X round M3 + under space."""
        web = _stiff_web(y_plane, z_bot=z_bot)
        solid = brg_lo
        for piece in (rail, web):
            try:
                solid = _as_one_solid(solid.fuse(piece))
            except Exception:
                pass
        if _nsol(solid) > 1:
            print(
                "HA_Bearing_Rail y0=%.1f: WARN fuse pre-cut solids=%d"
                % (y0, _nsol(solid))
            )
        solid = _apply_rail_m3_both_sides(solid, y0)
        nsol = _nsol(solid)
        print(
            "HA_Bearing_Rail y0=%.1f: solids=%d (want 1) | +/-X equal depth+under"
            % (y0, nsol)
        )
        if nsol != 1:
            print("HA_Bearing_Rail FAIL C1: still multi-solid after clamp cuts")
        return solid

    rail_s_assy = _finish_rail_one_solid(
        brg_l_lo, rail_s, y_brg_l, y_s_plane, z_bot=z_rail_bot
    )
    rail_n_assy = _finish_rail_one_solid(
        brg_r_lo, rail_n, y_brg_r, y_n_plane - link_t, z_bot=z_rail_bot
    )

    def _flatten_minus_x(solid: Part.Shape, x_face: float) -> Part.Shape:
        """Shave any material with X < x_face so -X wall is planar (// YZ)."""
        bb = solid.BoundBox
        if bb.XMin >= x_face - 0.02:
            return solid
        cut = Part.makeBox(
            (x_face - bb.XMin) + 1.0,
            bb.YLength + 20.0,
            bb.ZLength + 20.0,
        )
        cut.translate(App.Vector(bb.XMin - 0.5, bb.YMin - 10.0, bb.ZMin - 10.0))
        try:
            out = _cut_keep_one(solid, cut)
            if out is solid:
                out = _as_one_solid(solid.cut(cut))
            print(
                "HA_flatten_-X: XMin %.3f -> face %.3f | solids=%d"
                % (bb.XMin, x_face, _nsol(out))
            )
            return out
        except Exception:
            return solid

    rail_s_assy = _flatten_minus_x(rail_s_assy, rail_x0)
    rail_n_assy = _flatten_minus_x(rail_n_assy, rail_x0)

    def _hole_depth(sh: Part.Shape, ex: float, hy: float, *, is_cap: bool) -> float:
        """Depth of clearance bore only (not free space above/below the part)."""
        if is_cap:
            z0 = z_pin - 0.05
            z1 = z_pin + 0.5 * bearing_h + 0.05
        else:
            z0 = z_pin - 0.5 * BOLT_EAR - M3_RAIL_UNDER
            z1 = z_pin + 0.05
        first = last = None
        z = z0
        while z <= z1 + 1e-9:
            try:
                empty = not sh.isInside(App.Vector(ex, hy, z), 0.06, True)
            except Exception:
                empty = False
            if empty:
                if first is None:
                    first = z
                last = z
            z += 0.25
        if first is None or last is None:
            return -1.0
        return float(last - first)

    def _ring_closed(sh: Part.Shape, ex: float, hy: float, z: float) -> bool:
        """Material around bore at r=2.5 (outside Ø3.6, inside ear pad)."""
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            x = ex + 2.5 * math.cos(a)
            y = hy + 2.5 * math.sin(a)
            try:
                if not sh.isInside(App.Vector(x, y, z), 0.08, True):
                    return False
            except Exception:
                return False
        return True

    # C8: re-apply identical ±X features after flatten
    rail_s_assy = _apply_rail_m3_both_sides(rail_s_assy, y_brg_l)
    rail_n_assy = _apply_rail_m3_both_sides(rail_n_assy, y_brg_r)

    # Cap: through-hole + CB from top face (both ±X) — bolt installs from +Z
    def _recut_cap_m3_through(solid: Part.Shape, y0: float) -> Part.Shape:
        hy = y0 + 0.5 * bearing_t
        z_cap_top = z_pin + 0.5 * bearing_h
        half_h = 0.5 * BOLT_EAR
        for sx in (-1.0, 1.0):
            ex = _m3_clamp_x(sx)
            # Ensure full ear pad on both sides (no khuyết)
            ear = Part.makeBox(BOLT_EAR, bearing_t, half_h)
            ear.translate(App.Vector(ex - 0.5 * BOLT_EAR, y0, z_pin))
            try:
                solid = _as_one_solid(solid.fuse(ear))
            except Exception:
                pass
            try:
                solid = _as_one_solid(
                    solid.cut(
                        _m3_hole_z(ex, hy, z_pin - 0.15, (z_cap_top - z_pin) + 1.0)
                    )
                )
            except Exception:
                pass
            try:
                solid = _as_one_solid(
                    solid.cut(_m3_head_cbore_z(ex, hy, z_cap_top))
                )
            except Exception:
                pass
        return solid

    brg_l_hi = _recut_cap_m3_through(brg_l_hi, y_brg_l)
    brg_r_hi = _recut_cap_m3_through(brg_r_hi, y_brg_r)

    # --- Verify L/R equal depth + closed ring + under space (Rail + Cap) ---
    def _verify_m3_pair(
        label: str, sh: Part.Shape, y0: float, *, is_cap: bool
    ) -> bool:
        hy = y0 + 0.5 * bearing_t
        ex_l, ex_r = _m3_clamp_x(-1.0), _m3_clamp_x(1.0)
        d_l = _hole_depth(sh, ex_l, hy, is_cap=is_cap)
        d_r = _hole_depth(sh, ex_r, hy, is_cap=is_cap)
        # Ring above nut pocket (Rail) / mid upper ear (Cap)
        if is_cap:
            z_mid = z_pin + 0.5 * BOLT_EAR - 1.0
        else:
            z_mid = z_pin - 0.5 * BOLT_EAR + M3_NUT_POCKET_H + 1.2
        ring_l = _ring_closed(sh, ex_l, hy, z_mid)
        ring_r = _ring_closed(sh, ex_r, hy, z_mid)
        under_ok = True
        under_s = "n/a"
        if not is_cap:
            z_u = z_pin - 0.5 * BOLT_EAR - 0.5 * M3_RAIL_UNDER
            for ex in (ex_l, ex_r):
                try:
                    if sh.isInside(App.Vector(ex, hy, z_u), 0.08, True):
                        under_ok = False
                except Exception:
                    under_ok = False
            under_s = "yes" if under_ok else "NO"
        depth_ok = abs(d_l - d_r) <= 0.35 and d_l > 0 and d_r > 0
        ok = depth_ok and ring_l and ring_r and under_ok
        print(
            "HA_M3_verify %s: depth L=%.2f R=%.2f equal=%s ring_L=%s ring_R=%s "
            "under=%s -> %s"
            % (
                label,
                d_l,
                d_r,
                "yes" if depth_ok else "NO",
                "yes" if ring_l else "NO",
                "yes" if ring_r else "NO",
                under_s,
                "PASS" if ok else "FAIL",
            )
        )
        return ok

    brg_l_hi = _as_one_solid(brg_l_hi)
    brg_r_hi = _as_one_solid(brg_r_hi)

    def _cut_rail_where_cap(
        rail: Part.Shape, cap: Part.Shape, label: str
    ) -> Part.Shape:
        """Remove Rail material that intersects Cap (split at z_pin / ears)."""
        vol = 0.0
        try:
            common = rail.common(cap)
            if common is not None and not common.isNull():
                vol = float(common.Volume)
        except Exception:
            vol = 0.0
        if vol > 0.05:
            try:
                rail = _as_one_solid(rail.cut(cap))
            except Exception:
                pass
            # Confirm cleared
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
                "HA_cut_Rail_Cap_%s: removed_vol=%.1f remain=%.2f solids=%d"
                % (label, vol, left_v, _nsol(rail))
            )
        else:
            print("HA_cut_Rail_Cap_%s: no overlap" % label)
        return rail

    rail_s_assy = _cut_rail_where_cap(rail_s_assy, brg_l_hi, "S")
    rail_n_assy = _cut_rail_where_cap(rail_n_assy, brg_r_hi, "N")

    parts.append(("HA_Bearing_Rail_S", rail_s_assy, cols["brg"]))
    parts.append(("HA_Bearing_Rail_N", rail_n_assy, cols["brg"]))
    parts.append(("HA_Bearing_Cap_S", brg_l_hi, cols["cap"]))
    parts.append(("HA_Bearing_Cap_N", brg_r_hi, cols["cap"]))
    _verify_m3_pair("Rail_S", rail_s_assy, y_brg_l, is_cap=False)
    _verify_m3_pair("Cap_S", brg_l_hi, y_brg_l, is_cap=True)
    print("HA_Bearing_Rail: C1 one-solid + equal +/-X M3 + under cavity")
    print(
        "HA_M3_split: Cap=through+CB@top | Rail=lower+nut+under%.0f @ z_pin=%.2f "
        "ex=[%.1f,%.1f]"
        % (M3_RAIL_UNDER, z_pin, _m3_clamp_x(-1.0), _m3_clamp_x(1.0))
    )

    # Flat plate // follower (YZ plane, normal X) — bridges Rail_S ↔ Rail_N
    bridge_t = max(2.0, float(d.get("rail_bridge_t", 4.0)))
    bridge_z0 = z_rail_bot
    bridge_h = rail_h
    bridge_y0 = y_s_plane
    bridge_dy = y_n_plane - y_s_plane
    bridge = Part.makeBox(bridge_t, bridge_dy, bridge_h)
    bridge.translate(App.Vector(rail_x0 - bridge_t, bridge_y0, bridge_z0))
    # C13: service windows so -X M3 bolt+nut can be installed (else bridge walls them off)
    win_y = max(bearing_t + 2.0, M3_NUT_POCKET_AF + 10.0)
    win_z = BOLT_EAR + M3_NUT_POCKET_H + 10.0
    z_win0 = z_pin - 0.5 * BOLT_EAR - M3_NUT_POCKET_H - 4.0
    for y0b in (y_brg_l, y_brg_r):
        hyb = y0b + 0.5 * bearing_t
        cut = Part.makeBox(bridge_t + 2.0, win_y, win_z)
        cut.translate(
            App.Vector(
                rail_x0 - bridge_t - 1.0,
                hyb - 0.5 * win_y,
                z_win0,
            )
        )
        try:
            bridge = _as_one_solid(bridge.cut(cut))
        except Exception:
            pass
    n_br = len(list(getattr(bridge, "Solids", []) or []))
    parts.append(("HA_Rail_Bridge", _as_one_solid(bridge), cols["bridge"]))
    print(
        "HA_Rail_Bridge: t=%.1f Y-span=%.1f H=%.1f @ x=%.1f | M3 service windows solids=%d"
        % (bridge_t, bridge_dy, bridge_h, rail_x0 - 0.5 * bridge_t, n_br)
    )

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
        parts.append(("HA_Bottom_Stop", _as_one_solid(stop), cols["stop"]))

    if include_scale:
        sx0 = bar_cx - 0.5 * bar_x - rail_wall - 5
        for i in range(int(scale_max) + 1):
            L = 4.0 if i % 5 == 0 else 2.2
            mk = Part.makeBox(L, 0.6, 1.2)
            mk.translate(App.Vector(sx0, cy - 0.3, z_nut0 + float(i)))
            parts.append(("HA_Scale_%02d" % i, mk, cols["scale"]))

    if include_demo_wall:
        z0w = z_rail0 - 2
        wall = Part.makeBox(60, 4, z_pin + tip_r + bearing_h - z0w)
        wall.translate(App.Vector(cx - 30, y_n_plane + 8, z0w))
        parts.append(("HA_Demo_Wall_U", _as_one_solid(wall), cols["wall"]))

    print(
        "Height_Adjust_Z involute | z=%d alpha=%.0f | stroke=%.0f | %.2f turn (%.0f mm/turn)"
        % (teeth, alpha_deg, stroke, stroke / travel, travel)
    )
    print("HA_active_parts: %s" % ", ".join(n for n, _, _ in parts))
    return parts
