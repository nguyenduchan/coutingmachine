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
    "note": "Outer_Guide_Arc — fixed bowl wall around disc",
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
# =============================================================================
LID = {
    # --- stack (Z) ---
    # Underside of lid + walls over disc = disc top + this gap (disc can spin free)
    "disc_clear": 0.5,
    "top_thickness": 3.0,  # flat continuous top face
    "wall_thickness": 2.0,
    "wall_height": 27.0,  # from underside up to under top plate (−1 cm from 37)
    "stack_height": 30.0,  # wall_height + top_thickness (overall lid H)
    # --- adjusters ---
    "width_bar": {
        "role": "lane width adjust",
        "shape": "parallelogram_prism",
        "height": 40.0,
        "width": 20.0,  # distance between long edges
        "long_edge_angle_deg": 135.0,  # from +X CCW
        "short_edge": "parallel_to_chute",  # vertical in plan (= chute // -Y)
        # cạnh phải bar = cạnh trái máng thẳng (x_outer)
        "short_edge_placement": "chute_left",
        # chiều dài dọc 135° tới gần tường vuông trái
        "long_length": "to_square_left",
        "long_end_inset": 0.0,  # mm inward from square left wall
    },
    "height_bar": {
        "role": "stack height limit",
        "shape": "box_prism",
        "height": 10.0,  # 1 cm
        "thickness": 2.0,  # plan thickness
        "length": 32.0,
        "angle_deg": 0.0,  # horizontal
        "at": "narrow_mouth",
    },
    # --- plan (XY) ---
    "plan": {
        "wide_mouth": {
            "at_clock": 3,
            "shape": "radial_segment",
            "width": 75.0,  # hub→rim ≈ full annulus
            "inset_from_hub_rim": 2.5,  # margin inside disc
        },
        "narrow_mouth": {
            "at_clock": 9,
            "shape": "horizontal_segment",  # perpendicular to chute
            "width": 20.0,
            # center radius = mid_annulus + outward_offset
            "mid_annulus_offset": 10.0,  # +1 cm toward rim from mid
            "y_offset": 8.0,  # slight +Y so arcs stay upper
        },
        "funnel_walls": {
            "shape": "two_circular_arcs",
            "inner": "w_in -> n_in (hub side)",
            "outer": "w_out -> n_out (rim side)",
            "must_stay_inside_disc": True,
            "non_crossing": True,
        },
        # Khoang phễu (cửa rộng → cửa hẹp): có được nắp trên che kín không
        "funnel_chamber": {
            "shape": "wide_mouth -> arcs -> narrow_mouth",
            # True  = khoang bị khép bởi Lid_Top (thêm Lid_Top_Funnel_Roof)
            # False = để hở xuyên nắp (chỉ tường + không có mái)
            "roofed_by_lid_top": True,
            # True  = máng đỏ sau cửa hẹp cũng có mái; False = máng hở trên
            "roof_chute": False,
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
        },
        "chute": {
            "shape": "two_parallel_walls",
            "color_ref": "red_in_2d",
            "direction": "-Y",  # top→bottom in 2D image
            "width": 20.0,
            # end flush with farthest disc rim in -Y (= y = -disc_radius)
            "end": "disc_far_rim",
            "end_y": "-(DISC.diameter/2)",
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
                "Lid_Top_Out_SW",
                # Over disc — split at funnel / rim / mouth / chute walls
                "Lid_Top_Funnel_Roof",
                "Lid_Top_Rim_Pocket",
                "Lid_Top_Chute_Roof",
                "Lid_Top_Deck_N",
                "Lid_Top_Deck_S_Hub",
                "Lid_Top_Deck_S_Rim",
            ],
            "build": "continuous_plate_split_at_walls",
        },
        # Mặt dưới: Z = mặt đĩa + disc_clear (0.5); hở hình trụ đĩa
        "bottom_plate": {
            "enabled": True,
            "thickness": 3.0,
            "open_over_disc": True,
            "disc_clearance": 0.5,  # XY hole Ø = disc + this
            "z": "disc_top + LID.disc_clear",  # underside flush plane
            "children": ["Lid_Bottom_Floor"],
            "note": "bottom face at disc height + 0.5mm; walls over disc same Z",
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
    bar_short = bar_w * math.sqrt(2.0)
    ang = math.radians(float(wb["long_edge_angle_deg"]))
    ux, uy = math.cos(ang), math.sin(ang)
    # Short edge X: right edge of bar
    place = str(wb.get("short_edge_placement", "chute_left"))
    if place in ("chute_left", "x_outer"):
        xc = x_outer  # trùng cạnh trái máng thẳng
    elif place in ("chute_right", "x_inner"):
        xc = x_inner
    else:
        xc = 0.5 * (x_inner + x_outer)  # centered_in_chute
    yc = 0.5 * (y_mouth + y_exit)
    # Long length along 135°
    ll = wb.get("long_length", "to_square_left")
    if ll == "to_square_left" or ll is None:
        inset = float(wb.get("long_end_inset", 0.0))
        # xc + bar_long*ux = box_xl + inset  (ux < 0)
        bar_long = (box_xl + inset - xc) / ux if abs(ux) > 1e-9 else 40.0
        bar_long = abs(float(bar_long))
    else:
        bar_long = float(ll)
    b0 = (xc, yc - bar_short / 2.0)
    b1 = (xc, yc + bar_short / 2.0)
    b2 = (b1[0] + bar_long * ux, b1[1] + bar_long * uy)
    b3 = (b0[0] + bar_long * ux, b0[1] + bar_long * uy)
    ht = float(LID["height_bar"]["thickness"])
    hl = float(LID["height_bar"]["length"])
    height_bar = [
        (xc - hl / 2.0, y_mouth - ht / 2.0),
        (xc + hl / 2.0, y_mouth - ht / 2.0),
        (xc + hl / 2.0, y_mouth + ht / 2.0),
        (xc - hl / 2.0, y_mouth + ht / 2.0),
    ]
    return {
        "w_in": w_in,
        "w_out": w_out,
        "n_in": n_in,
        "n_out": n_out,
        "e_in": e_in,
        "e_out": e_out,
        "box": box,
        "width_bar": [b0, b1, b2, b3],
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
    }


def lid_funnel_arcs(
    w_in: tuple[float, float],
    w_out: tuple[float, float],
    n_in: tuple[float, float],
    n_out: tuple[float, float],
    r_hub: float | None = None,
    r_disc: float | None = None,
    n: int = 48,
) -> tuple[list, list]:
    """Two non-crossing circular arcs inside the disc (shared by CAD + 2D)."""
    import math

    if r_hub is None:
        r_hub = hub_radius()
    if r_disc is None:
        r_disc = disc_radius()

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
                math.hypot(x, y) < r_hub + 0.3 or math.hypot(x, y) > r_disc - 0.3
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

    cins = collect(w_in, n_in, r_hub + 14)
    couts = collect(w_out, n_out, r_disc - 14)
    for hug_i, ai, ci, ri in cins:
        for hug_o, ao, co, ro in couts:
            if cross(ai, ao):
                continue
            if math.hypot(*ao[len(ao) // 2]) < math.hypot(*ai[len(ai) // 2]) + 3:
                continue
            return ai, ao, {"c_in": ci, "r_in": ri, "c_out": co, "r_out": ro}
    return [w_in, n_in], [w_out, n_out], {"c_in": None, "r_in": None, "c_out": None, "r_out": None}


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
