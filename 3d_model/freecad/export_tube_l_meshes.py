# -*- coding: utf-8 -*-
"""
Export Tube_L_Exit_Gate solids → STL for PyBullet egress sim.

Run:
  freecadcmd 3d_model/freecad/export_tube_l_meshes.py
  freecadcmd 3d_model/freecad/export_tube_l_meshes.py --W 9 --H 5
"""
from __future__ import annotations

import argparse
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
OUT = _HERE.parent / "sim" / "meshes" / "tube_l_exit"
OUT.mkdir(parents=True, exist_ok=True)

from tube_l_exit_gate import (  # noqa: E402
    PILL_CLEAR_XY,
    PILL_CLEAR_Z,
    build_tube_l_exit_gate_parts,
    recommend_gap_mm,
)


def shape_to_stl(shape, path: Path, linear_deflection: float = 0.35) -> dict:
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=linear_deflection,
        AngularDeflection=0.25,
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
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--W", type=float, default=None)
    ap.add_argument("--H", type=float, default=None)
    ap.add_argument("--D", type=float, default=8.0)
    ap.add_argument("--T", type=float, default=4.0)
    args, _unknown = ap.parse_known_args(sys.argv[1:])
    if args.W is None or args.H is None:
        gap = recommend_gap_mm(args.D, args.T)
        W, H = gap["W"], gap["H"]
    else:
        W, H = float(args.W), float(args.H)

    for old in OUT.glob("*.stl"):
        old.unlink()

    # Export TAT CA cac phan (khong loc "want" nua) — dung cho mo phong PyBullet
    # hien thi giong het model FreeCAD (yeu cau: "model 3d trong mo phong vat ly
    # phai giong het trong freecad"). Truoc day chi export 6 phan chinh (bo qua
    # Entry_Gate_Post/Entry_Gate_Slider/screws).
    all_parts = build_tube_l_exit_gate_parts(W, H)
    manifest = {
        "units": "mm",
        "W_mm": W,
        "H_mm": H,
        "pill_clear_xy_mm": PILL_CLEAR_XY,
        "pill_clear_z_mm": PILL_CLEAR_Z,
        "note": "Exit_Track W×H = aperture (= pill + 1 mm clear)",
        "parts": {},
        "colors": {},
    }
    seen_names: dict[str, int] = {}
    for name, sh, color in all_parts:
        if name in seen_names:
            seen_names[name] += 1
            name = f"{name}_{seen_names[name]}"
        else:
            seen_names[name] = 0
        if sh is None or sh.isNull():
            continue
        defl = 0.55 if name in ("Bowl_Tube", "Guide_System") else 0.35
        info = shape_to_stl(sh, OUT / f"{name}.stl", linear_deflection=defl)
        manifest["parts"][name] = info
        manifest["colors"][name] = list(color)
        print("export", name, info["file"], flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("OK", len(manifest["parts"]), "meshes →", OUT, flush=True)


if __name__ == "__main__" or True:
    # freecadcmd may not set __name__ == "__main__"
    main()
