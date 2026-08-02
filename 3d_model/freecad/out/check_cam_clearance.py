# -*- coding: utf-8 -*-
"""Clearance check: rotate face cam, lift follower; report interferences."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

_HERE = Path(__file__).resolve().parent
_FC = _HERE.parent if _HERE.name == "out" else _HERE
sys.path.insert(0, str(_FC))
OUT = _FC / "out"
OUT.mkdir(parents=True, exist_ok=True)

import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, _cam_params


def _common_vol(a: Part.Shape, b: Part.Shape) -> float:
    try:
        c = a.common(b)
        if c is None or c.isNull():
            return 0.0
        return abs(float(c.Volume))
    except Exception:
        return -1.0


def main() -> None:
    drv = dict(BX.LID["height_bar"]["drive"])
    drv["bar_length_y"] = 40.0
    cam_p = _cam_params(drv)
    stroke = cam_p["stroke"]
    base_t = cam_p["base_t"]

    parts = {
        n: sh
        for n, sh, _ in build_height_adjust_z_parts(
            cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False
        )
    }
    cam0 = parts["HA_Cam"]
    fol0 = parts["HA_Follower"]
    shaft = parts["HA_Shaft"]
    block = parts["HA_Bearing_Block"]
    rails = [parts[k] for k in ("HA_Bearing_Rail_N", "HA_Bearing_Rail_S") if k in parts]

    # Contact pad may share a little volume with cam face — allow small budget
    contact_budget = 120.0  # mm^3 — pad sitting on cam face
    errors = []
    samples = []

    for deg in range(0, 360, 15):
        th = math.radians(deg)
        # CW cam rotation → rise: dz = stroke * th/(2π)
        dz = stroke * (th / (2.0 * math.pi))
        cam = cam0.copy()
        cam.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -deg)  # CW
        fol = fol0.copy()
        fol.translate(App.Vector(0, 0, dz))

        v_cf = _common_vol(cam, fol)
        v_sf = _common_vol(shaft, fol)
        v_cb = _common_vol(cam, block)
        v_cr = sum(_common_vol(cam, r) for r in rails)

        # Strip "contact" : common near pad — if total common >> budget → clash
        clash_fol = v_cf > contact_budget
        clash_shaft = v_sf > 1.0
        clash_block = v_cb > 1.0
        clash_rail = v_cr > 1.0
        ok = not (clash_fol or clash_shaft or clash_block or clash_rail)
        samples.append(
            {
                "deg": deg,
                "dz_mm": dz,
                "cam_fol_mm3": v_cf,
                "shaft_fol_mm3": v_sf,
                "cam_block_mm3": v_cb,
                "cam_rail_mm3": v_cr,
                "ok": ok,
            }
        )
        print(
            "θ=%3d° dz=%5.1f  cam∩fol=%.1f  shaft∩fol=%.1f  ok=%s"
            % (deg, dz, v_cf, v_sf, ok)
        )
        if not ok:
            errors.append(
                "clash at %d deg: cam∩fol=%.1f shaft∩fol=%.1f cam∩block=%.1f cam∩rail=%.1f"
                % (deg, v_cf, v_sf, v_cb, v_cr)
            )

    # Full turn travel check
    if abs(stroke - 20.0) > 0.05:
        errors.append("stroke setting %.1f != 20" % stroke)

    report = {
        "mechanism": "face_cam_follower",
        "stroke_mm": stroke,
        "base_t_mm": base_t,
        "contact_budget_mm3": contact_budget,
        "samples": samples,
        "pass": len(errors) == 0,
        "errors": errors,
    }
    out = OUT / "height_cam_clearance.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("=" * 50)
    print("RESULT:", "PASS" if report["pass"] else "FAIL")
    for e in errors:
        print(" -", e)
    print("Wrote", out)
    if not report["pass"]:
        sys.exit(1)


main()
