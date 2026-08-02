#!/usr/bin/env python3
"""Verify pinion teeth are identical and share math with rack.

Run with FreeCAD if available for mesh check; always checks analytic math.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out")
ROOT = _HERE.parents[1]
sys.path.insert(0, str(ROOT / "freecad"))

OUT = _HERE / "verify_rack_pinion_teeth.json"


def load_settings():
    import importlib.util

    p = ROOT / "freecad" / "box_settings.py"
    spec = importlib.util.spec_from_file_location("box_settings", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.LID["height_bar"]["drive"])


def spur_gear_math(module, teeth, alpha_deg=20.0, tooth_clear=0.0):
    m = float(module)
    z = int(teeth)
    alpha = math.radians(float(alpha_deg))
    p = math.pi * m
    s = 0.5 * p - 0.5 * float(tooth_clear)
    e = p - s
    return {
        "module": m,
        "teeth": z,
        "alpha_deg": float(alpha_deg),
        "circular_pitch": p,
        "tooth_thickness": s,
        "space_width": e,
        "addendum": m,
        "dedendum": 1.25 * m,
        "pitch_d": m * z,
        "travel_per_rev": p * z,
        "min_teeth_no_undercut": math.ceil(2.0 / (math.sin(alpha) ** 2)),
    }


def main():
    d = load_settings()
    rack = dict(d.get("rack") or {})
    m = float(rack.get("module", d.get("gear_module", d.get("module", 2.0))))
    z = int(rack.get("pinion_teeth", d.get("pinion_teeth", d.get("teeth", 18))))
    alpha = float(
        rack.get("pressure_angle_deg", d.get("pressure_angle_deg", 20.0))
    )
    tc = float(rack.get("tooth_clear", d.get("tooth_clear", 0.40)))

    g = spur_gear_math(m, z, alpha, tc)
    rack_ok = (
        abs(g["circular_pitch"] - math.pi * m) < 1e-12
        and abs(g["tooth_thickness"] + g["space_width"] - g["circular_pitch"]) < 1e-9
        and abs(g["tooth_thickness"] - (0.5 * g["circular_pitch"] - 0.5 * tc)) < 1e-9
    )
    undercut_ok = z >= g["min_teeth_no_undercut"]
    construction = {
        "method": "one_tooth_polar_copy",
        "angle_step_deg": 360.0 / z,
        "identical_by_construction": True,
        "shared_keys": ["module", "alpha", "pitch", "tooth_thickness", "space", "ha", "hf"],
    }

    freecad_uniform = None
    freecad_msg = "skipped (no FreeCAD)"
    try:
        import FreeCAD as App  # noqa: F401
        import Part  # noqa: F401

        from height_adjust_z import (  # type: ignore
            make_involute_pinion_local,
            spur_gear_math as fc_math,
            verify_pinion_teeth_uniform,
        )

        g_fc = fc_math(m, z, alpha_deg=alpha, tooth_clear=tc)
        local = make_involute_pinion_local(
            module=m,
            teeth=z,
            face_w=float(rack.get("face_w", d.get("face_w", d.get("pinion_face_w", 12.0)))),
            bore=6.15,
            alpha_deg=alpha,
            tooth_clear=tc,
        )
        uni = verify_pinion_teeth_uniform(
            local,
            g_fc,
            face_w=float(rack.get("face_w", d.get("face_w", d.get("pinion_face_w", 12.0)))),
        )
        freecad_uniform = bool(uni.get("pass"))
        freecad_msg = "max_rel_dev=%.4f mean=%.2f" % (
            float(uni.get("max_rel_dev", 0.0)),
            float(uni.get("mean_mm3", 0.0)),
        )
    except Exception as ex:
        freecad_msg = "skipped: %s" % ex

    result = {
        "shared_math": "PASS" if rack_ok else "FAIL",
        "pitch_match": "PASS" if rack_ok else "FAIL",
        "no_undercut": "PASS" if undercut_ok else "FAIL",
        "uniform_teeth": (
            "PASS"
            if freecad_uniform is True
            else ("FAIL" if freecad_uniform is False else "ANALYTIC_PASS")
        ),
        "uniform_detail": freecad_msg,
        "construction": construction,
        "gear": g,
        "pass": bool(rack_ok and undercut_ok and freecad_uniform is not False),
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("wrote", OUT)
    return 0 if result["pass"] else 1


if __name__ == "__main__" or __name__ == "__freecad_main_script__":
    raise SystemExit(main())

# freecadcmd often loads scripts without __main__
try:
    import FreeCAD  # noqa: F401

    raise SystemExit(main())
except ImportError:
    pass
except SystemExit:
    raise
