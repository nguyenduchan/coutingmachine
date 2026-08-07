"""
Counting machine — geometric settings (mm, degrees unless noted).

Edit THIS file to change size and shape. Rebuild:
  - 2D lid:  python 3d_model/freecad/out/_gen_lid_2d.py
  - 3D CAD:  freecad 3d_model/freecad/show_jgb37_gui.py

Convention (top view / FreeCAD XY):
  +X = 3 o'clock (wide mouth), +Y = 12 o'clock, -X = 9 o'clock, -Y = 6 o'clock.
  Disc / hub axis at world origin (0, 0).

Shape notes use short tags:
  cyl = cylinder, box = rectangular prism, arc = circular-arc wall,
  poly = polygonal extrusion, annulus = ring sector.
"""

from __future__ import annotations

# =============================================================================
# DISC + HUB (rotating) — not part of the lid
# =============================================================================
DISC = {
    "shape": "cyl",
    "diameter": 200.0,
    "thickness": 5.0,
    "shaft_bore": 6.1,  # clearance on Ø6 shaft
    "note": "Turntable_Disc — rotating plate",
}
HUB = {
    "shape": "cyl",
    "diameter": 50.0,  # Ø5 cm
    "height": 20.0,  # 2 cm
    "note": "Center_Hub on disc; rotates with disc",
}

# =============================================================================
# HOUSING / OUTER GUIDE
# =============================================================================
GUIDE = {
    "shape": "annulus_floor + wall_sectors",
    "wall_radial_thickness": 12.0,
    "bore_clearance_on_disc": 0.5,  # bore = disc_d + this
    "wall_sector_step_deg": 10.0,
    # Khoét thủng vách vành nơi máng thẳng (lid chute) cắt qua
    "cut_straight_chute": True,
    "chute_cut_pad": 1.0,  # mm expand cut beyond chute polygon
    "note": "Outer_Guide_Arc — fixed bowl wall around disc; open where straight chute crosses",
}
HOUSING = {
    "shape": "box_shell",
    "wall_thickness": 4.0,
    # Outer footprint of Housing_Shell (mm) — width × depth
    "outer_width": 220.0,  # 22 cm
    "outer_depth": 220.0,  # 22 cm
    "pad_around_guide": 6.0,  # legacy; unused when outer_width/depth set
    "lid": {
        "shape": "closed_square",  # full square — no disc hole / notch
        "thickness": "wall_thickness",
    },
    "note": "Housing_Shell outer = 220×220 mm (22×22 cm); Housing_Lid = full square",
}

# =============================================================================
# MOTOR + MOUNT (FROZEN — do not change pose without explicit user request)
# =============================================================================
MOTOR = {
    "frozen": True,
    "shape": "jgb37_assembly",
    "gearbox_od": 37.0,
    "gearbox_length": 26.5,
    "mount_pcd": 31.0,
    "shaft_offset": 7.0,
    "boss_od": 12.0,
    "boss_height": 6.0,
    "shaft_od": 6.0,
    "note": "JGB37_520_Motor + L_Bracket_Mount_Frame — see jgb37-mount-freeze",
}
DRIVE = {
    "shape": "cyl",
    "bearing_od": 19.0,
    "bearing_id": 6.0,
    "bearing_height": 6.0,
    "coupler_od": 18.0,
    "coupler_length": 25.0,
    "note": "Bearings 626ZZ + flexible coupler + disc shaft",
}

# =============================================================================
# EXIT TRAY + GAP (lining-up) — Placement restored from FCStd App::Part
# =============================================================================
EXIT_TRAY = {
    "shape": "floor + walls (straight + quarter arc)",
    "arc_diameter": 100.0,
    "channel_width": 12.0,
    "straight_length": 65.0,
    "wall_height": 20.0,
    "floor_thickness": 2.5,
    "wall_thickness": 3.0,
    "floor_side_pad": 20.0,
    "wall_front_clear": 30.0,
    "arc_cx_local": -50.0,
    "arc_cy_local": 50.0,
    "arc_a0_deg": 130.0,
    "arc_a1_deg": 180.0,
    "recycle_gap": 14.0,
    "disc_clear": 1.2,
    "note": "Exit_Guide_Tray — move only via App::Part Placement",
}
GAP = {
    "shape": "annular_sector_guard + rack_pinion",
    "curve_thickness": 4.0,
    "curve_a0_deg": 95.0,
    "curve_a1_deg": 175.0,
    "stroke_max": 20.0,
    "rack_module": 1.5,
    "pinion_teeth": 16,
    "note": "Gap_Lining_Up — Placement from FCStd",
}
GATE = {
    "nominal_gap": 11.0,
    "gap_max": 20.0,
    "exit_y": 55.0,
    "note": "Legacy gate throat reference",
}
PRESS = {
    "shape": "finger + bypass rail",
    "finger_height": 9.0,
    "finger_thickness": 2.2,
    "tip_radius": 3.5,
    "bypass_dr": 14.0,
    "note": "Exit_Press_Guide",
}

# =============================================================================
# DISC ACCESS LID (everything except rotating disc/hub)
# Standalone: show_disc_access_lid_gui.py → out/disc_access_lid.FCStd
# (same make_lid_* as show_jgb37_gui — rebuild either file to update both)
# =============================================================================
LID = {
    # --- stack (Z) ---
    # Underside of lid + walls over disc = disc top + this gap (disc can spin free)
    # Enforced: Disc_Access_Lid parent Placement Pz = 0 (do not sink the group)
    "disc_clear": 0.5,
    "top_thickness": 3.0,  # flat continuous top face
    "wall_thickness": 2.0,
    "wall_height": 27.0,  # from underside up to under top plate (−1 cm from 37)
    "stack_height": 30.0,  # wall_height + top_thickness (overall lid H)
    # --- adjusters ---
    "width_bar": {
        "role": "lane width adjust",
        "shape": "box_prism",
        "height": 12.0,  # thap — chay trong ray duoi nap
        "width": 10.0,  # 1 cm
        "long_edge_angle_deg": 90.0,
        "short_edge": "perpendicular_to_chute",
        "short_edge_placement": "chute_right_inward",
        "long_length": "chute_span",
        "long_end_inset": 0.0,
        "offset_x": -12.0,  # dich Drive+Bar sang trai (−X), khong canh phai mang
        "offset_y": 138.0,
        "clip_to_lid_box": True,
        # Num dong truc voi chieu tinh tien (// Y) — ren in duoc + giu num vao nap
        "drive": {
            "enabled": True,
            "mechanism": "coaxial_leadscrew",
            "note": "knob+screw // Y; FDM helix; bar+rail shifted left of chute right wall",
            "offset_x": 0.0,  # extra drive-axis shift vs bar center (usually 0)
            "knob_od": 28.0,
            "knob_h": 14.0,
            "knob_grip_od": 22.0,
            "leadscrew_od": 8.0,
            "leadscrew_pitch": 3.0,
            "leadscrew_len": 90.0,
            "thread_depth": 1.1,  # radial major→minor
            "thread_clear_r": 0.40,  # FDM radial clearance nut vs screw
            "segs_per_turn": 20,
            "nut_l": 18.0,  # ≥ ~6×pitch engagement
            "nut_w": 14.0,
            "nut_h": 12.0,
            "rail_wall": 2.0,
            "rail_clear": 0.4,
            "rail_overhang": 3.0,
            # Axial lock: flange on screw trapped by retainer bolted to lid underside
            "collar_od": 16.0,
            "collar_t": 2.8,
            "journal_od": 8.0,
            "retainer_wall": 3.0,
            "retainer_pad_t": 4.0,  # pad against Lid_Top underside
            "retainer_screw_d": 3.2,  # M3 clearance in pad+cap
            "retainer_screw_span": 22.0,
        },
    },
    "height_bar": {
        "role": "stack height limit — cam follower / green scraper // Y beside Width",
        "shape": "box_prism",
        "height": 12.0,  # scraper body Z (ridge adds +nut_ridge_h)
        "thickness": 10.0,  # plan X
        "at": "width_bar_right",
        "gap": 0.0,
        "long_length": "match_width_bar",
        # Spur rack–pinion: pinion axis Y ⊥ rack travel Z; ~75 mm/turn; friction hold
        "drive": {
            "enabled": True,
            "mechanism": "rack_pinion",
            "note": "Y-pinion+Z-rack; stiffened rails/follower/shaft; fused pinion-shaft; M3 caps+knob",
            "include_bottom_stop": False,
            "include_scale": False,
            "knob_od": 28.0,
            "knob_h": 14.0,
            "knob_grip_od": 22.0,
            "knob_seat_depth": 8.0,
            "shaft_tip_hole_len": 6.0,
            "knob_clear_from_rail_n": 20.0,
            "rack": {
                "stroke": 20.0,
                "module": 2.0,
                "pinion_teeth": 18,
                "face_w": 12.0,
                "pressure_angle_deg": 20.0,
                "tooth_clear": 0.55,
                "center_backlash": 0.50,
            },
            "gear_module": 2.0,
            "pinion_teeth": 18,
            "pinion_face_w": 10.0,
            "pressure_angle_deg": 20.0,
            "tooth_clear": 0.55,
            "center_backlash": 0.50,
            "friction_washer_t": 2.0,
            "friction_washer_od": 18.0,
            "bearing_t": 8.5,
            "bearing_h": 22.0,
            "bearing_w": 20.0,
            "nut_l": 12.0,
            "nut_w": 16.0,
            "nut_h": 12.0,
            "bar_thickness": 8.0,
            "bar_length_y": 24.0,
            "bar_height": 14.0,
            "rack_body_t": 0.0,
            "nut_ridge_h": 10.0,
            "nut_ridge_t": 4.5,
            "nut_ridge_side": "right",
            "rail_wall": 4.5,
            "rail_clear": 0.35,
            "rail_extend_down": 8.0,
            "rail_s_extend_down": 8.0,
            "rail_bridge_t": 5.0,
            "rail_stroke": 20.0,
            "scale_max": 20.0,
            "bottom_stop_h": 3.0,
            "journal_od": 8.0,
            "groove_od": 6.5,
            "groove_w": 2.2,
            "collar_od": 14.0,
            "collar_flange_t": 1.5,
            "block_xy": 36.0,
            "block_h": 8.0,
            "retainer_screw_d": 3.2,
            "retainer_screw_span": 22.0,
            "at": "bar_center",
            "axis_inset": 0.0,
        },
    },
    # --- plan (XY) ---
    "plan": {
        "wide_mouth": {
            "at_clock": 3,
            "shape": "radial_segment",
            "width": 75.0,  # hub→rim ≈ full annulus
            "inset_from_hub_rim": 2.5,  # margin inside disc (w_in / w_out plan)
        },
        "narrow_mouth": {
            "at_clock": 9,
            "shape": "horizontal_segment",  # perpendicular to chute
            "width": 20.0,
            # center radius = mid_annulus + outward_offset
            "mid_annulus_offset": 20.0,  # +2 cm toward rim from mid (−1 cm closer to disc rim)
            "y_offset": 8.0,  # slight +Y so arcs stay upper
        },
        "funnel_walls": {
            "shape": "two_circular_arcs",
            "inner": "w_in -> n_in (hub side)",
            "outer": "w_out -> n_out (rim side)",
            "must_stay_inside_disc": True,
            "non_crossing": True,
            # Mép trong cửa rộng: đi thẳng vào phễu rồi mới cung tròn
            # (tránh cung cắt hub Ø5 cm — kể cả nửa bề dày tường)
            "inner_lead_mm": 15.0,
            "inner_hub_clear": 1.0,  # extra mm beyond hub + wall/2
            # Chỉ mép Arc_Out tại cửa rộng dịch +X (sát vành); cung giữ nguyên
            "arc_out_wide_tip_inset": 0.5,  # tip at r = disc_r − this
        },
        # Khoang phễu (cửa rộng → cửa hẹp): có được nắp trên che kín không
        "funnel_chamber": {
            "shape": "wide_mouth -> arcs -> narrow_mouth",
            # True  = khoang bị khép bởi Lid_Top (thêm Lid_Top_Funnel_Roof)
            # False = để hở xuyên nắp (chỉ tường + không có mái)
            "roofed_by_lid_top": True,
            # True  = máng đỏ sau cửa hẹp cũng có mái (mặt trên kín)
            # False = máng hở trên
            "roof_chute": True,
            # Vùng giữa cung ngoài phễu và vành đĩa (vùng vàng trên sơ đồ) — kín bằng nắp
            "roof_rim_pocket": True,
            # Kéo Rim_Pocket xuống quá miệng hẹp (°) để kín khe dưới với Deck_S_Rim
            "rim_pocket_south_extra_deg": 22.0,
            # Túi bé chấm đỏ (~9h): cung đĩa (phải) × góc vuông khung (trái+dưới)
            "roof_arc_corner": True,
            "arc_corner": {
                # └ góc khung trái: tường đứng = box_xl; ngang = corner_y;
                # túi = bên phải + phía trên góc, trừ phần trong đĩa
                "corner_x": "box_xl",  # -110 (Lid_Wall_Sq_W)
                "corner_y": -50.0,
                "span": 35.0,
                "orient": "right_above",  # +X,+Y from corner
            },
            # Thành kín dọc vành đĩa (ngoài Ø20cm), CUNG PHÍA DƯỚI (−Y):
            # bắt đầu cạnh phải máng thẳng ∩ đường tròn → mép ngoài cửa rộng (3h)
            "rim_seal_wall": {
                "enabled": True,
                "thickness": 2.0,  # radial wall T (mm)
                "disc_clear_radial": 0.25,  # r_in = disc_r + this
                "from": "chute_in_rim_south",  # cạnh phải máng (x_inner) ∩ rim, nhánh −Y
                "to": "wide_mouth_out",  # mép ngoài cửa rộng (+X / 3h)
                "via": "south",  # cung dưới (không qua 12h)
                "name": "Lid_Wall_Rim_Arc",
            },
        },
        "chute": {
            "shape": "two_parallel_walls",
            "color_ref": "red_in_2d",
            "direction": "-Y",  # top→bottom in 2D image
            "width": 20.0,
            # end flush with farthest disc rim in -Y (= y = -disc_radius)
            "end": "disc_far_rim",
            "end_y": "-(DISC.diameter/2)",
            # Vách đứng tại cạnh ngang cuối máng: từ mặt dưới → mặt trên nắp
            "end_barrier": True,
            "end_barrier_height": "stack_height",  # full lid H
            # Mặt dưới nắp: khoét thủng theo polygon máng (cộng với lỗ đĩa)
            "open_bottom": True,
        },
        # Outer lid = closed square; bottom edge = disc + bottom_extra (1 cm past rim)
        "frame": {
            "shape": "closed_square",
            "bottom_extra": 10.0,  # cạnh dưới rộng thêm 1 cm so với đĩa
            # side length = disc_diameter + 2*bottom_extra (vuông kín, tâm = gốc đĩa)
            "note": "square centered on disc; fills missing edges into full square",
        },
        "top_plate": {
            "shape": "closed_square covering frame",
            "cut_hub": True,
            # Outside disc = square − disc cylinder (no AABB gaps)
            "children": [
                # Outside disc — split at square mid / mouth / chute-out walls
                "Lid_Top_Out_NE",
                "Lid_Top_Out_SE",
                "Lid_Top_Out_W",
                "Lid_Top_Out_NW",
                "Lid_Top_Out_NWm",
                "Lid_Top_Out_SW",  # parent
                "Lid_Top_Out_SW_Chute",  # parent: Above + Below (split at Chute_End)
                "Lid_Top_Out_SW_Chute_Above",
                "Lid_Top_Out_SW_Chute_Below",
                "Lid_Top_Out_SW_Rest",
                # Over disc — split at funnel / rim / mouth / chute walls
                "Lid_Top_Funnel_Roof",
                "Lid_Top_Rim_Pocket",
                "Lid_Top_Chute_Roof",  # máng đỏ — mặt trên kín
                "Lid_Top_Deck_N",
                "Lid_Top_Deck_S_Hub",  # parent: Hub_L + Hub_R
                "Lid_Top_Deck_S_Hub_L",
                "Lid_Top_Deck_S_Hub_R",
                "Lid_Top_Deck_S_Rim",
            ],
            "build": "continuous_plate_split_at_walls",
        },
        # Mặt dưới: Z = mặt đĩa + disc_clear (0.5); hở hình trụ đĩa + máng thẳng
        # nhưng kín dưới Rim_Pocket + Deck_S_Rim (cùng XY với mặt trên)
        "bottom_plate": {
            "enabled": True,
            "thickness": 3.0,
            "open_over_disc": True,
            "open_over_chute": True,  # khoét thêm polygon máng thẳng
            "disc_clearance": 0.5,  # XY hole Ø = disc + this
            "z": "disc_top + LID.disc_clear",  # underside flush plane
            "seal_under": [
                "Lid_Top_Rim_Pocket",
                "Lid_Top_Deck_S_Rim",
            ],
            "children": [
                "Lid_Bottom_Floor",
                "Lid_Bottom_Rim_Pocket",
                "Lid_Bottom_Deck_S_Rim",
            ],
            "note": "bottom open over disc/chute except sealed under Rim_Pocket + Deck_S_Rim",
        },
        # Đặc phần giữa vành đĩa ↔ cạnh vuông (đầy tường, không để rỗng)
        "annulus_fill": {
            "enabled": True,
            "shape": "square_prism - disc_cylinder",
            "height": "wall_height - bottom_thickness",  # sits on bottom plate
            "children": ["Lid_Fill_Outside"],
            "note": "solid fill so disc↔square margin is fully enclosed",
        },
    },
}


def disc_radius() -> float:
    return DISC["diameter"] / 2.0


def hub_radius() -> float:
    return HUB["diameter"] / 2.0


def lid_mouth_radius() -> float:
    """Narrow-mouth center radius (toward rim from mid-annulus)."""
    mid = (hub_radius() + disc_radius()) / 2.0
    return mid + float(LID["plan"]["narrow_mouth"]["mid_annulus_offset"])


def lid_rim_seal_angles(plan: dict | None = None) -> tuple[float, float, float, float]:
    """
    Angles (deg, CCW from +X) and radii for Lid_Wall_Rim_Arc — SOUTHERN arc.

    Starts at the right edge of the straight chute (x_inner / Chute_In) where it
    intersects the disc circle on the −Y side, then goes CCW along the lower rim
    to the wide-mouth outer at +X (3h). Wall stays outside Ø20 cm disc.

    Returns (deg0, deg1, r_in, r_out) for CCW annular sector deg0→deg1.
    """
    import math

    if plan is None:
        plan = lid_plan_full()
    cfg = LID["plan"]["funnel_chamber"].get("rim_seal_wall", {})
    r_disc = float(plan["r_disc"])
    clear = float(cfg.get("disc_clear_radial", 0.25))
    thick = float(cfg.get("thickness", LID["wall_thickness"]))
    r_in = r_disc + clear
    r_out = r_in + thick

    # Wide-mouth outer → rim at +X (3h) ≈ 0° / 360°
    w_out = plan["w_out"]
    deg_wide = math.degrees(math.atan2(float(w_out[1]), float(w_out[0]))) % 360.0
    if deg_wide < 1e-6:
        deg_wide = 360.0  # CCW end of southern sweep

    # Right edge of chute = x_inner (Chute_In); south intersection with disc
    x_in = float(plan["x_inner"])
    half = max(r_disc * r_disc - x_in * x_in, 1e-6) ** 0.5
    chute_rim_s = (x_in, -half)
    deg_chute = math.degrees(math.atan2(chute_rim_s[1], chute_rim_s[0])) % 360.0

    # Southern arc: CCW from chute-right-south (~223°) → wide mouth (360°)
    return deg_chute, deg_wide, r_in, r_out


def _rim_arc_cw(
    radius: float, a_start: float, a_end: float, steps: int = 36
) -> list[tuple[float, float]]:
    """Clockwise arc on circle radius from a_start → a_end (radians)."""
    import math

    s = math.degrees(a_start) % 360
    e = math.degrees(a_end) % 360
    total = (s - e) % 360
    if total < 1:
        total = 360.0
    return [
        (
            radius * math.cos(math.radians((s - total * i / steps) % 360)),
            radius * math.sin(math.radians((s - total * i / steps) % 360)),
        )
        for i in range(steps + 1)
    ]


def lid_rim_pocket_xy(plan: dict | None = None) -> list[tuple[float, float]]:
    """
    Polygon: outer funnel arc → disc rim (via 12h) → back.
    Vùng giữa cung ngoài và vành đĩa (vùng vàng trên sơ đồ).

    Extends a few mm south of n_out / mouth so no seam gap with Deck_S_Rim.
    """
    import math

    if plan is None:
        plan = lid_plan_full()
    arc_out = list(plan["arc_out"])
    w_out = plan["w_out"]
    n_out = plan["n_out"]
    r = float(plan["r_disc"]) - 0.05  # almost to rim (was -0.2 → thin edge gap)
    a0 = math.atan2(w_out[1], w_out[0])
    a1 = math.atan2(n_out[1], n_out[0])
    # South of mouth along west rim (~20° past n_out toward -Y) — closes bottom seam
    south_extra_deg = float(
        LID["plan"]["funnel_chamber"].get("rim_pocket_south_extra_deg", 22.0)
    )
    a_south = a1 + math.radians(south_extra_deg)  # CCW from n_out → toward 180°/-Y
    # Build: arc_out → n_out → short chord south → rim from a_south CW via north to w_out
    y_south = r * math.sin(a_south)
    x_south = r * math.cos(a_south)
    # Also drop slightly south of n_out along outer wall for overlap with Deck_S_Rim
    n_out_south = (float(n_out[0]), float(n_out[1]) - 8.0)
    return (
        arc_out
        + [n_out_south, (x_south, y_south)]
        + _rim_arc_cw(r, a_south, a0, steps=40)
    )


def lid_north_cap_xy(plan: dict | None = None) -> list[tuple[float, float]]:
    """2D AABB of Lid_Top_Arc_Corner (schematic only)."""
    x_v, y_h, span, orient = lid_arc_corner_params(plan)
    if orient == "right_above":
        return [
            (x_v, y_h),
            (x_v + span, y_h),
            (x_v + span, y_h + span),
            (x_v, y_h + span),
        ]
    return [
        (x_v - span, y_h - span),
        (x_v, y_h - span),
        (x_v, y_h),
        (x_v - span, y_h),
    ]


def lid_arc_corner_params(
    plan: dict | None = None,
) -> tuple[float, float, float, str]:
    """
    (corner_x, corner_y, span, orient) for tiny disc-arc × right-angle pocket.

    Chấm đỏ (~9h): between square left wall and disc rim (arc on the right
    of the pocket; right-angle = frame left + bottom).
    """
    if plan is None:
        plan = lid_plan_full()
    ac = LID["plan"]["funnel_chamber"].get("arc_corner", {})
    cx = ac.get("corner_x", "box_xl")
    if cx == "box_xl":
        x_v = float(plan["box_xl"])
    elif cx == "x_outer":
        x_v = float(plan["x_outer"])
    else:
        x_v = float(cx)
    y_h = float(ac.get("corner_y", -50.0))
    span = float(ac.get("span", 35.0))
    orient = str(ac.get("orient", "right_above"))
    return x_v, y_h, span, orient


def lid_deck_s_rim_xy(plan: dict | None = None) -> list[tuple[float, float]]:
    """
    Top-lid west cover (vùng đỏ): square left ↔ disc (−X),
    plus finger over Chute_Out. Outside-disc area included (no disc-only clip).
    """
    if plan is None:
        plan = lid_plan_full()
    n_out = plan["n_out"]
    xl = float(plan["box_xl"])
    yb = float(plan["box_yb"])
    yt = float(plan["box_yt"])
    r_disc = float(plan["r_disc"])
    wt = float(LID["wall_thickness"])
    x_rim = -r_disc  # disc left AABB / rim plane
    x_cap = float(n_out[0]) + wt / 2.0
    y_mouth = float(n_out[1])
    y_f0 = max(yb + 1.0, y_mouth - 40.0)
    y_f1 = min(yt - 1.0, y_mouth + 40.0)
    # West rectangle + bay over chute wall
    return [
        (xl, yb + 0.5),
        (x_rim, yb + 0.5),
        (x_rim, y_f0),
        (x_cap, y_f0),
        (x_cap, y_f1),
        (x_rim, y_f1),
        (x_rim, yt - 0.5),
        (xl, yt - 0.5),
    ]


def lid_square_half() -> float:
    """Half side of closed square lid (mm). Side = disc_d + 2*bottom_extra."""
    extra = float(LID["plan"]["frame"]["bottom_extra"])
    return disc_radius() + extra


def lid_chute_end_y() -> float:
    """Y of red chute end — farthest disc rim in -Y (inside square)."""
    end = LID["plan"]["chute"]["end"]
    if end == "disc_far_rim":
        return -disc_radius()
    if end == "square_bottom":
        return -lid_square_half()
    # legacy: past local rim at mouth radius
    r_m = lid_mouth_radius()
    y_rim = -(max(disc_radius() ** 2 - r_m**2, 1.0) ** 0.5)
    return y_rim - 18.0


def height_drive_xy(
    height_bar: list,
    drv: dict | None = None,
) -> tuple[float, float]:
    """
    XY of Rotary_Linear (height_bar) knob/screw axis.
    Default: left end of bar (−X) so the knob is not centered on the chute.
    """
    drv = drv or {}
    xs = [float(p[0]) for p in height_bar]
    ys = [float(p[1]) for p in height_bar]
    x_a, x_b = min(xs), max(xs)
    y_a, y_b = min(ys), max(ys)
    cy = 0.5 * (y_a + y_b)
    inset = float(drv.get("axis_inset", 7.0))
    place = str(drv.get("at", "bar_left"))
    if place in ("bar_left", "left", "-x", "outer"):
        cx = x_a + inset
    elif place in ("bar_right", "right", "+x", "inner"):
        cx = x_b - inset
    else:
        cx = 0.5 * (x_a + x_b) + float(drv.get("offset_x", 0.0))
        cy = cy + float(drv.get("offset_y", 0.0))
        return (cx, cy)
    cx += float(drv.get("offset_x", 0.0))
    cy += float(drv.get("offset_y", 0.0))
    return (cx, cy)


def lid_plan_xy() -> dict:
    """
    Compute all lid plan points (mm) for 2D SVG and 3D walls.
    Outer frame = closed square centered on disc; bottom = disc + bottom_extra.
    """
    import math

    r_disc = disc_radius()
    r_hub = hub_radius()
    m = float(LID["plan"]["wide_mouth"]["inset_from_hub_rim"])
    w_n = float(LID["plan"]["narrow_mouth"]["width"])
    w_in = (r_hub + m, 0.0)
    w_out = (r_disc - m, 0.0)
    r_mouth = lid_mouth_radius()
    x_inner = -(r_mouth - w_n / 2.0)
    x_outer = -(r_mouth + w_n / 2.0)
    y_mouth = float(LID["plan"]["narrow_mouth"]["y_offset"])
    n_in = (x_inner, y_mouth)
    n_out = (x_outer, y_mouth)
    y_exit = lid_chute_end_y()
    e_in = (x_inner, y_exit)
    e_out = (x_outer, y_exit)

    half = lid_square_half()
    box_xl, box_xr = -half, half
    box_yb, box_yt = -half, half
    # Closed square (CCW), first point repeated at end for wall polyline
    box = [
        (box_xr, box_yb),
        (box_xr, box_yt),
        (box_xl, box_yt),
        (box_xl, box_yb),
        (box_xr, box_yb),
    ]
    wb = LID["width_bar"]
    bar_w = float(wb["width"])
    place = str(wb.get("short_edge_placement", "chute_right"))
    ll = wb.get("long_length", "chute_span")
    ang_deg = float(wb.get("long_edge_angle_deg", 90.0))

    # Width bar: // chute (long along ±Y), same Y span
    if ll == "chute_span" or ang_deg in (90.0, -90.0, 270.0):
        # Long edges // máng (−Y); short = width along +X
        if place in ("in_chute", "centered_in_chute", "chute"):
            # Trùng đúng lòng máng thẳng
            x_a, x_b = min(x_outer, x_inner), max(x_outer, x_inner)
        elif place in ("chute_right_inward", "flush_right_inward"):
            # Cạnh phải cố định tại x_inner; rộng bar_w về −X (vào máng)
            x_b = x_inner
            x_a = x_inner - bar_w
        elif place in ("chute_right", "x_inner"):
            x_a, x_b = x_inner, x_inner + bar_w
        elif place in ("chute_left", "x_outer"):
            x_a, x_b = x_outer - bar_w, x_outer
        else:
            xm = 0.5 * (x_inner + x_outer)
            x_a, x_b = xm - bar_w / 2.0, xm + bar_w / 2.0
        y_lo, y_hi = min(y_exit, y_mouth), max(y_exit, y_mouth)
        ox = float(wb.get("offset_x", 0.0))
        oy = float(wb.get("offset_y", 0.0))
        x_a, x_b = x_a + ox, x_b + ox
        y_lo, y_hi = y_lo + oy, y_hi + oy
        # Clip to closed-square lid box (cut protrusion outside hộp)
        if bool(wb.get("clip_to_lid_box", True)):
            x_a = max(x_a, box_xl)
            x_b = min(x_b, box_xr)
            y_lo = max(y_lo, box_yb)
            y_hi = min(y_hi, box_yt)
        if x_b - x_a < 1e-6 or y_hi - y_lo < 1e-6:
            width_bar = [
                (x_inner + ox, y_mouth + oy),
                (x_outer + ox, y_mouth + oy),
                (x_outer + ox, y_mouth + oy),
                (x_inner + ox, y_mouth + oy),
            ]
        else:
            width_bar = [
                (x_a, y_lo),
                (x_b, y_lo),
                (x_b, y_hi),
                (x_a, y_hi),
            ]
    else:
        # legacy parallelogram (135° → square left)
        bar_short = bar_w * math.sqrt(2.0)
        ang = math.radians(ang_deg)
        ux, uy = math.cos(ang), math.sin(ang)
        if place in ("chute_left", "x_outer"):
            xc = x_outer
        elif place in ("chute_right", "x_inner"):
            xc = x_inner
        else:
            xc = 0.5 * (x_inner + x_outer)
        yc = 0.5 * (y_mouth + y_exit)
        if ll == "to_square_left" or ll is None:
            inset = float(wb.get("long_end_inset", 0.0))
            bar_long = (box_xl + inset - xc) / ux if abs(ux) > 1e-9 else 40.0
            bar_long = abs(float(bar_long))
        else:
            bar_long = float(ll)
        b0 = (xc, yc - bar_short / 2.0)
        b1 = (xc, yc + bar_short / 2.0)
        b2 = (b1[0] + bar_long * ux, b1[1] + bar_long * uy)
        b3 = (b0[0] + bar_long * ux, b0[1] + bar_long * uy)
        width_bar = [b0, b1, b2, b3]

    # Height bar: vertical strip // Y, flush to Width_Adjust right edge (+X)
    hb = LID["height_bar"]
    hb_at = str(hb.get("at", "width_bar_right"))
    hb_tx = float(hb.get("thickness", 10.0))  # X thickness
    wxs = [float(p[0]) for p in width_bar]
    wys = [float(p[1]) for p in width_bar]
    wr = max(wxs)
    wl = min(wxs)
    wy0, wy1 = min(wys), max(wys)
    if hb_at in ("width_bar_right", "flush_width_right", "width_right"):
        gap = float(hb.get("gap", 0.0))
        hx0 = wr + gap
        hx1 = hx0 + hb_tx
        hy0, hy1 = wy0, wy1
        if str(hb.get("long_length", "match_width_bar")) not in (
            "match_width_bar",
            "width_span",
            "same_y",
        ):
            try:
                half_l = 0.5 * float(hb["long_length"])
                yc = 0.5 * (wy0 + wy1)
                hy0, hy1 = yc - half_l, yc + half_l
            except (TypeError, ValueError, KeyError):
                pass
        height_bar = [
            (hx0, hy0),
            (hx1, hy0),
            (hx1, hy1),
            (hx0, hy1),
        ]
    elif hb_at in ("width_bar_left", "flush_width_left"):
        gap = float(hb.get("gap", 0.0))
        hx1 = wl - gap
        hx0 = hx1 - hb_tx
        height_bar = [
            (hx0, wy0),
            (hx1, wy0),
            (hx1, wy1),
            (hx0, wy1),
        ]
    else:
        # legacy: horizontal blade at narrow mouth
        ht = float(hb.get("thickness", 10.0))
        hl = float(hb.get("length", 32.0))
        hx = 0.5 * (x_inner + x_outer)
        height_bar = [
            (hx - hl / 2.0, y_mouth - ht / 2.0),
            (hx + hl / 2.0, y_mouth - ht / 2.0),
            (hx + hl / 2.0, y_mouth + ht / 2.0),
            (hx - hl / 2.0, y_mouth + ht / 2.0),
        ]

    return {
        "w_in": w_in,
        "w_out": w_out,
        "n_in": n_in,
        "n_out": n_out,
        "e_in": e_in,
        "e_out": e_out,
        "box": box,
        "width_bar": width_bar,
        "height_bar": height_bar,
        "box_xl": box_xl,
        "box_xr": box_xr,
        "box_yb": box_yb,
        "box_yt": box_yt,
        "y_exit": y_exit,
        "y_mouth": y_mouth,
        "r_disc": r_disc,
        "r_hub": r_hub,
        "r_mouth": r_mouth,
        "x_inner": x_inner,
        "x_outer": x_outer,
        "square_side": 2.0 * half,
        "square_half": half,
        "width_bar_center": (
            0.5 * (width_bar[0][0] + width_bar[2][0]),
            0.5 * (width_bar[0][1] + width_bar[2][1]),
        ),
        "height_bar_center": (
            0.5 * (height_bar[0][0] + height_bar[2][0]),
            0.5 * (height_bar[0][1] + height_bar[2][1]),
        ),
        "height_drive_xy": height_drive_xy(
            height_bar, LID.get("height_bar", {}).get("drive", {})
        ),
    }


def lid_funnel_arcs(
    w_in: tuple[float, float],
    w_out: tuple[float, float],
    n_in: tuple[float, float],
    n_out: tuple[float, float],
    r_hub: float | None = None,
    r_disc: float | None = None,
    n: int = 48,
) -> tuple[list, list, dict]:
    """
    Two non-crossing walls inside the disc (shared by CAD + 2D).

    Inner wall: short straight lead from w_in into the funnel (+Y), then a
    circular arc to n_in — keeps the wall clear of the hub circle (Ø5 cm).
    Outer wall: circular arc w_out → n_out.
    """
    import math

    if r_hub is None:
        r_hub = hub_radius()
    if r_disc is None:
        r_disc = disc_radius()

    fw = LID["plan"]["funnel_walls"]
    lead_mm = float(fw.get("inner_lead_mm", 15.0))
    hub_clear = float(fw.get("inner_hub_clear", 1.0))
    wall_t = float(LID.get("wall_thickness", 2.0))
    # Path is wall centerline → keep hub_r + wall/2 + clear so solid wall clears Ø5cm
    r_hub_keep = r_hub + wall_t / 2.0 + hub_clear

    # Straight lead: from wide-mouth inner tip into funnel (+Y at clock-3)
    # Also keep X far enough that the whole lead clears the hub circle
    x_lead = max(float(w_in[0]), r_hub_keep)
    lead_pt = (x_lead, float(w_in[1]) + lead_mm)
    if math.hypot(*lead_pt) < r_hub_keep:
        # push further +X if needed
        lead_pt = (r_hub_keep + 1.0, float(w_in[1]) + lead_mm)

    def sample_arc(c, r, p_a, p_b):
        a0 = math.atan2(p_a[1] - c[1], p_a[0] - c[0])
        a1 = math.atan2(p_b[1] - c[1], p_b[0] - c[0])
        d_ccw = (a1 - a0) % (2 * math.pi)
        d_cw = (a0 - a1) % (2 * math.pi)

        def pts(delta, sign):
            return [
                (
                    c[0] + r * math.cos(a0 + sign * delta * i / n),
                    c[1] + r * math.sin(a0 + sign * delta * i / n),
                )
                for i in range(n + 1)
            ]

        best = None
        for poly in (pts(d_ccw, +1), pts(d_cw, -1)):
            mid = poly[len(poly) // 2]
            if any(
                math.hypot(x, y) < r_hub_keep or math.hypot(x, y) > r_disc - 0.3
                for x, y in poly
            ):
                continue
            ang = math.degrees(math.atan2(mid[1], mid[0])) % 360
            sc = abs(ang - 90) + (0 if mid[1] > 0 else 50)
            if best is None or sc < best[0]:
                best = (sc, poly)
        return None if best is None else best[1]

    def collect(p1, p2, favor_r, k=10):
        mx = 0.5 * (p1[0] + p2[0])
        my = 0.5 * (p1[1] + p2[1])
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        nlen = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / nlen, dx / nlen
        cands = []
        for s in range(-400, 401, 2):
            c = (mx + s * nx, my + s * ny)
            r = math.hypot(p1[0] - c[0], p1[1] - c[1])
            if r < 15 or r > 450:
                continue
            poly = sample_arc(c, r, p1, p2)
            if poly is None:
                continue
            mid = poly[len(poly) // 2]
            hug = abs(math.hypot(mid[0], mid[1]) - favor_r)
            cands.append((hug, poly, c, r))
        cands.sort(key=lambda t: t[0])
        return cands[:k]

    def cross(a, b):
        def orient(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        def hit(p, q, r, s):
            return (orient(p, q, r) * orient(p, q, s) < 0) and (
                orient(r, s, p) * orient(r, s, q) < 0
            )

        for i in range(1, len(a) - 2):
            for j in range(1, len(b) - 2):
                if hit(a[i], a[i + 1], b[j], b[j + 1]):
                    return True
        return False

    # Arc starts after the straight lead (not from w_in directly)
    # Favor mid-radius that stays well outside hub (Ø5cm + wall)
    cins = collect(lead_pt, n_in, max(r_hub_keep + 12.0, r_hub + 18.0))
    couts = collect(w_out, n_out, r_disc - 14)
    for hug_i, ai, ci, ri in cins:
        for hug_o, ao, co, ro in couts:
            if cross(ai, ao):
                continue
            if math.hypot(*ao[len(ao) // 2]) < math.hypot(*ai[len(ai) // 2]) + 3:
                continue
            # Prepend straight lead: w_in → lead_pt → arc…
            arc_in = [tuple(w_in), lead_pt] + list(ai[1:])
            return (
                arc_in,
                ao,
                {
                    "c_in": ci,
                    "r_in": ri,
                    "c_out": co,
                    "r_out": ro,
                    "inner_lead_pt": lead_pt,
                },
            )
    # Fallback: straight lead + chord
    return (
        [tuple(w_in), lead_pt, tuple(n_in)],
        [tuple(w_out), tuple(n_out)],
        {
            "c_in": None,
            "r_in": None,
            "c_out": None,
            "r_out": None,
            "inner_lead_pt": lead_pt,
        },
    )


def lid_plan_full() -> dict:
    """Complete lid plan including funnel arcs (CAD + 2D source of truth)."""
    base = lid_plan_xy()
    arc_in, arc_out, meta = lid_funnel_arcs(
        base["w_in"],
        base["w_out"],
        base["n_in"],
        base["n_out"],
        base["r_hub"],
        base["r_disc"],
    )
    base["arc_in"] = arc_in
    base["arc_out"] = arc_out
    base.update(meta)
    return base


# =============================================================================
# OTHER ASSEMBLIES (shape + key sizes — Placement from FCStd when moved in GUI)
# =============================================================================
CLEAR_EXIT_COVER = {
    "shape": "box_shell_window",
    "outer_xy": (50.0, GATE["nominal_gap"] + 16.0),
    "height": 22.0,
    "wall_t": 3.0,
    "note": "Clear_Exit_Cover over gate throat",
}
SEPARATOR_TAB = {
    "shape": "thin_blade_box",
    "size": (18.0, 6.0, 12.0),
    "note": "Separator_Tab at disc rim",
}
OUTLET_CHUTE = {
    "shape": "hollow_box",
    "outer": (40.0, 28.0, 30.0),
    "inner_shrink": (6.0, 6.0, 2.0),
    "note": "Outlet_Chute below exit",
}
IR_SENSOR = {
    "shape": "U_fork",
    "body": (18.0, 12.0, 22.0),
    "slot_w": 8.0,
    "note": "IR_Sensor_Fork",
}
COLLECTION_DRAWER = {
    "shape": "open_box",
    "outer": (70.0, 55.0, 40.0),
    "wall_t": 4.0,
    "note": "Collection_Drawer",
}
CONTROL_PANEL = {
    "shape": "plate + buttons",
    "plate": (90.0, 8.0, 50.0),
    "note": "Control_Panel on housing front",
}


def as_flat_dict() -> dict:
    """Export all settings for tooling / docs."""
    return {
        "DISC": DISC,
        "HUB": HUB,
        "GUIDE": GUIDE,
        "HOUSING": HOUSING,
        "MOTOR": MOTOR,
        "DRIVE": DRIVE,
        "EXIT_TRAY": EXIT_TRAY,
        "GAP": GAP,
        "GATE": GATE,
        "PRESS": PRESS,
        "LID": LID,
        "CLEAR_EXIT_COVER": CLEAR_EXIT_COVER,
        "SEPARATOR_TAB": SEPARATOR_TAB,
        "OUTLET_CHUTE": OUTLET_CHUTE,
        "IR_SENSOR": IR_SENSOR,
        "COLLECTION_DRAWER": COLLECTION_DRAWER,
        "CONTROL_PANEL": CONTROL_PANEL,
        "derived": {
            "disc_r": disc_radius(),
            "hub_r": hub_radius(),
            "lid_chute_end_y": lid_chute_end_y(),
            "lid_mouth_r": lid_mouth_radius(),
        },
    }


if __name__ == "__main__":
    import pprint

    print("=== CountingMachine box_settings ===\n")
    pprint.pp(as_flat_dict(), width=100)
    plan = lid_plan_full()
    print(f"\nchute end Y = {plan['y_exit']:.3f} mm (disc far rim = {-disc_radius():.1f})")
    print(f"arcs: in={len(plan['arc_in'])} pts, out={len(plan['arc_out'])} pts")
