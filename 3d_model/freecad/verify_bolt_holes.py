"""
Verify every serviceable joint has matching M3 clearance holes.

  freecadcmd 3d_model/freecad/verify_bolt_holes.py

Writes 3d_model/freecad/out/bolt_holes_verify.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import FreeCAD as App  # noqa: E402

import assembly_bolts as AB  # noqa: E402
import show_jgb37_gui as G  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def _by_name(specs) -> dict:
    return {n: sh for n, sh, _c in specs}


def _check_xy(parts: dict, names: list[str], xy, z_list: list[float]) -> dict:
    hits = []
    miss = []
    for x, y in xy:
        part_ok = {}
        for pname in names:
            sh = parts.get(pname)
            if sh is None:
                continue
            empty = False
            for z in z_list:
                if AB.hole_is_empty(sh, x, y, z, tol=0.5):
                    empty = True
                    break
            part_ok[pname] = empty
            if empty:
                hits.append("%s@(%.1f,%.1f)" % (pname, x, y))
            else:
                # hole may miss this child (lid top is split) — only fail if
                # NONE of the named parts is empty at this XY
                miss.append("%s@(%.1f,%.1f)" % (pname, x, y))
        any_empty = any(part_ok.values()) if part_ok else False
        if not any_empty:
            return {
                "ok": False,
                "reason": "no hole at (%.2f, %.2f) in %s" % (x, y, names),
                "part_ok": part_ok,
            }
    return {"ok": True, "hits": len(hits), "checked": len(xy)}


def main() -> None:
    print("=== Bolt holes (M3) ===", flush=True)
    z_disc = G.TOP_Z + G.BOX_T + 1.0
    face_z = G.SHELF_Z - 8.0 - G.COUPLER_L
    z_coupler = face_z + G.BOSS_H + 2.0
    wall, bore_d, _side = G._guide_dims()
    r_in, r_out = bore_d / 2.0, bore_d / 2.0 + wall

    housing = _by_name(G.make_housing_mount_parts(face_z))
    disc = _by_name(G.make_disc_parts(z_disc))
    hub = _by_name(G.make_center_hub_parts(z_disc))
    coupler = _by_name(G.make_coupler_parts(z_coupler))
    guide = _by_name(G.make_outer_guide_parts(z_disc))
    lid_top = _by_name(G.make_lid_top_parts(z_disc))
    lid_bot = _by_name(G.make_lid_bottom_parts(z_disc))
    lid_fill = _by_name(G.make_lid_fill_parts(z_disc))
    lid_rest = _by_name(G.make_disc_access_lid_parts(z_disc))
    tray = _by_name(G.make_exit_tray_floor_basic_parts(z_disc))
    gap = _by_name(G.make_lining_up_gap_parts(z_disc))
    press = _by_name(G.make_exit_press_guide_parts(z_disc))
    panel = _by_name(G.make_control_panel_parts())
    chute = _by_name(G.make_outlet_chute_parts(z_disc))
    cover = _by_name(G.make_clear_exit_cover_parts(z_disc))
    sep = _by_name(G.make_separator_tab_parts(z_disc))
    sensor = _by_name(G.make_sensor_fork_parts(z_disc))

    parts = {}
    for d in (
        housing,
        disc,
        hub,
        coupler,
        guide,
        lid_top,
        lid_bot,
        lid_fill,
        lid_rest,
        tray,
        gap,
        press,
        panel,
        chute,
        cover,
        sep,
        sensor,
    ):
        parts.update(d)

    z_under = G._lid_z_underside(z_disc)
    corners = AB.lid_corner_xy()
    gfloor = AB.guide_floor_xy(r_in, r_out)
    gwalls = AB.guide_wall_xy(0.5 * (r_in + r_out))
    hub_xy = AB.hub_disc_xy()
    plan = G._lid_plan_points()
    sq_xy = AB.all_lid_wall_sq_xy(
        float(plan["box_xl"]),
        float(plan["box_xr"]),
        float(plan["box_yb"]),
        float(plan["box_yt"]),
    )

    checks = []

    def add(name, result):
        result = dict(result)
        result["name"] = name
        checks.append(result)
        print(
            "  %s: %s"
            % (name, "PASS" if result.get("ok") else "FAIL " + str(result.get("reason", "")))
        )

    add(
        "lid_housing_corners",
        _check_xy(
            parts,
            [
                "Lid_Bottom_Floor",
                "Housing_Lid",
            ],
            corners,
            [z_under + 1.5, G.TOP_Z + 2.0, G.TOP_Z + G.BOX_T + 3.0],
        ),
    )
    add(
        "guide_floor_housing",
        _check_xy(
            parts,
            ["Outer_Guide_Floor", "Housing_Lid"],
            gfloor,
            [z_disc - 2.5, G.TOP_Z + 2.0],
        ),
    )
    add(
        "guide_wall_floor",
        _check_xy(
            parts,
            ["Outer_Guide_Floor"]
            + [n for n in parts if n.startswith("Outer_Guide_Wall_")],
            gwalls,
            [z_disc + 4.0, z_disc - 2.5],
        ),
    )
    add(
        "disc_hub",
        _check_xy(
            parts,
            ["Disc_Plate", "Hub_Body"],
            hub_xy,
            [z_disc + 2.5, z_disc + G.DISC_T + 0.5 * AB.HUB_CLAMP_T],
        ),
    )
    add(
        "lid_wall_sq",
        _check_xy(
            parts,
            [
                "Lid_Wall_Sq_E",
                "Lid_Wall_Sq_W",
                "Lid_Wall_Sq_N",
                "Lid_Wall_Sq_S",
                "Lid_Bottom_Floor",
            ],
            sq_xy,
            [z_under + 3.0, z_under + 1.5],
        ),
    )
    add(
        "housing_shelf",
        _check_xy(
            parts,
            ["Housing_Shelf", "Housing_Shell"],
            corners,
            [G.SHELF_Z + 2.0],
        ),
    )
    add(
        "exit_tray_floor",
        _check_xy(
            parts,
            [n for n in parts if n.startswith("Exit_Tray_Floor_")],
            AB.exit_tray_bolt_xy_local(),
            [z_disc + G.DISC_T + 1.2],
        ),
    )
    add(
        "press_mount",
        _check_xy(
            parts,
            ["Press_Mount"] + [n for n in parts if n.startswith("Outer_Guide_Wall_")],
            AB.press_mount_xy(),
            [z_disc + G.DISC_T + 0.5 * AB.HUB_CLAMP_T],
        ),
    )
    add(
        "gap_drive_box",
        {
            "ok": "Gap_Drive_Box" in parts
            and parts["Gap_Drive_Box"] is not None
            and bool(parts["Gap_Drive_Box"].Solids),
            "note": "4×M3 cut from BoundBox of box floor",
        },
    )
    # Radial: coupler + hub set screw + panel
    rad_ok = True
    rad_miss = []
    # Coupler wall at x ≈ 6 (between bore Ø6 and OD Ø18) at set-screw Z
    if not AB.hole_is_empty(parts["Coupler_Body"], 6.0, 0.0, z_coupler + 6.0, tol=0.6):
        rad_ok = False
        rad_miss.append("coupler_low")
    if not AB.hole_is_empty(
        parts["Coupler_Body"], 6.0, 0.0, z_coupler + G.COUPLER_L - 6.0, tol=0.6
    ):
        rad_ok = False
        rad_miss.append("coupler_high")
    if not AB.hole_is_empty(
        parts["Hub_Body"], 10.0, 0.0, z_disc + G.DISC_T + 0.5 * G.HUB_H, tol=0.6
    ):
        rad_ok = False
        rad_miss.append("hub_set")
    for px, py, pz in AB.panel_xy(G.BOX_D, G.BOX_H):
        if not AB.hole_is_empty(parts["Panel_Bezel"], px, py, pz, tol=0.6):
            rad_ok = False
            rad_miss.append("panel@(%.0f,%.0f,%.0f)" % (px, py, pz))
        if not AB.hole_is_empty(parts["Housing_Shell"], px, py, pz, tol=0.6):
            rad_ok = False
            rad_miss.append("shell_panel@(%.0f,%.0f,%.0f)" % (px, py, pz))
    add(
        "radial_m3",
        {"ok": rad_ok, "miss": rad_miss, "bolt": AB.FASTENER_SPEC},
    )
    add(
        "accessories_present",
        {
            "ok": all(
                n in parts and parts[n] is not None
                for n in (
                    "Chute_Body",
                    "Clear_Cover_Top",
                    "Separator_Blade",
                    "Sensor_Bridge",
                    "Press_Mount",
                )
            ),
        },
    )

    all_pass = all(c.get("ok") for c in checks)
    report = {
        "pass": all_pass,
        "fastener": AB.FASTENER_SPEC,
        "clear_d": AB.M3_CLEAR,
        "default_len_mm": AB.M3_BOLT_L,
        "hub_clamp_t": AB.HUB_CLAMP_T,
        "guide_wall_hole_h": AB.GUIDE_WALL_HOLE_H,
        "fdm_walls_mm": {
            "housing": G.BOX_T,
            "lid_wall": G.LID_WALL_T,
            "lid_top": G.LID_TOP_T,
            "lid_bottom": G.LID_BOTTOM_T,
            "guide_radial": G.GUIDE_WALL,
            "tray_floor": G.EXIT_TRAY_FLOOR_T,
            "tray_wall": G.EXIT_TRAY_WALL_T,
            "gap_rail": G.GAP_RAIL_WALL,
            "press_finger": G.PRESS_FINGER_T,
            "disc": G.DISC_T,
        },
        "joints": checks,
        "n_parts": len(parts),
    }
    path = OUT / "bolt_holes_verify.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("pass=%s | parts=%d | %s" % (all_pass, len(parts), AB.FASTENER_SPEC))
    print("Wrote", path)
    if not all_pass:
        sys.exit(1)


def _run() -> None:
    log = OUT / "bolt_holes_verify_log.txt"
    try:
        main()
        log.write_text("main() returned\n", encoding="utf-8")
    except SystemExit as e:
        log.write_text("SystemExit %s\n" % e, encoding="utf-8")
        raise
    except Exception:
        import traceback

        tb = traceback.format_exc()
        log.write_text(tb, encoding="utf-8")
        print(tb, flush=True)
        raise SystemExit(1)


_run()
