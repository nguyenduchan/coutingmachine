# -*- coding: utf-8 -*-
"""
Export Height_Adjust FreeCAD solids → STL for physics sim (exact CAD).

Run:
  freecadcmd 3d_model/freecad/export_height_adjust_meshes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import MeshPart

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
OUT = _HERE.parent / "sim" / "meshes" / "height_adjust"
OUT.mkdir(parents=True, exist_ok=True)

import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, _rack_params


def shape_to_stl(shape, path: Path, linear_deflection: float = 0.15) -> dict:
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=linear_deflection,
        AngularDeflection=0.1,
        Relative=False,
    )
    mesh.write(str(path))
    bb = shape.BoundBox
    return {
        "file": path.name,
        "volume_mm3": float(shape.Volume),
        "bbox_mm": {
            "xmin": float(bb.XMin),
            "xmax": float(bb.XMax),
            "ymin": float(bb.YMin),
            "ymax": float(bb.YMax),
            "zmin": float(bb.ZMin),
            "zmax": float(bb.ZMax),
        },
    }


def main() -> None:
    for old in OUT.glob("*.stl"):
        old.unlink()

    drv = dict(BX.LID["height_bar"]["drive"])
    drv["bar_length_y"] = float(drv.get("bar_length_y", 40.0))
    drv["bar_thickness"] = float(BX.LID["height_bar"].get("thickness", 10.0))
    drv["bar_height"] = float(BX.LID["height_bar"].get("height", 12.0))
    rack_p = _rack_params(drv)

    parts = build_height_adjust_z_parts(
        cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False
    )

    want = {
        "HA_Pinion_Shaft",
        "HA_Knob",
        "HA_Friction_Washer",
        "HA_Follower",
        "HA_Bearing_Rail_S",
        "HA_Bearing_Cap_S",
        "HA_Bearing_Rail_N",
        "HA_Bearing_Cap_N",
        "HA_Rail_Bridge",
    }

    manifest = {
        "unit": "mm",
        "source": "height_adjust_z.build_height_adjust_z_parts",
        "mechanism": "rack_pinion",
        "kinematics": {
            "pinion_axis": "Y",
            "rack_travel": "Z",
            "note": "spur: rotation axis perpendicular to translation",
        },
        "rack": rack_p,
        "rail_stroke_mm": float(drv.get("rail_stroke", 20.0)),
        "parts": {},
        "roles": {
            "actuator": ["HA_Pinion_Shaft", "HA_Knob"],
            "follower": ["HA_Follower"],
            "static": [
                "HA_Bearing_Rail_S",
                "HA_Bearing_Cap_S",
                "HA_Bearing_Rail_N",
                "HA_Bearing_Cap_N",
                "HA_Rail_Bridge",
                "HA_Friction_Washer",
            ],
        },
    }

    by = {n: sh for n, sh, _ in parts}
    for name in sorted(want):
        if name not in by:
            print("skip missing", name)
            continue
        path = OUT / f"{name}.stl"
        info = shape_to_stl(by[name], path)
        manifest["parts"][name] = info
        print("Wrote", path, "vol=%.0f" % info["volume_mm3"])

    # Pivot for sim: pinion axis // Y through bbox center
    pin_bb = manifest["parts"].get("HA_Pinion_Shaft", {}).get("bbox_mm", {})
    if pin_bb:
        zc = 0.5 * (pin_bb["zmin"] + pin_bb["zmax"])
        xc = 0.5 * (pin_bb["xmin"] + pin_bb["xmax"])
        manifest["kinematics"]["axis_pivot_mm"] = [xc, 0.0, zc]
        manifest["kinematics"]["axis_pivot_m"] = [xc * 0.001, 0.0, zc * 0.001]

    man_path = OUT / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote", man_path)
    print("OK export", len(manifest["parts"]), "meshes")


main()
