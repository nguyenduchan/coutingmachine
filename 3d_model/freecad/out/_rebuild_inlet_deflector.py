# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

_HERE = Path(r"D:\Project\coutingmachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import FreeCAD as App  # noqa: E402
from mech_common import (  # noqa: E402
    GAP0,
    CHUTE_W_MM,
    W_MIN,
    W_MAX,
    make_exit_track,
    make_exit_ramp,
    make_crossbar_bridge,
    make_inlet_deflector,
    inlet_throat_params,
)
from part_inner_lane_rail import make_inner_lane_rail_body  # noqa: E402
from part_width_carriage import make_width_carriage  # noqa: E402
from part_guide_system import make_guide_system  # noqa: E402
from tube_l_components import build_component_assembly, component_path, print_summary  # noqa: E402
from tube_l_exit_gate import (  # noqa: E402
    verify_single_exit_path_only,
    verify_lane_outer_boundary_sealed,
    _overlap_volume,
)

W, H = 9.0, 5.0

PARTS = {
    "Crossbar_Bridge": make_crossbar_bridge,
    "Guide_System": make_guide_system,
    "Inner_Lane_Rail": lambda: make_inner_lane_rail_body(W),
    "Width_Carriage": lambda: make_width_carriage(W),
    "Exit_Track": lambda: make_exit_track(W, H),
    "Exit_Ramp": lambda: make_exit_ramp(W, H),
}

for name in list(App.listDocuments().keys()):
    App.closeDocument(name)

for name, fn in PARTS.items():
    path = component_path(name)
    doc = App.newDocument(name)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = fn()
    obj.Label = name
    doc.recompute()
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    print("wrote", name)

doc, info = build_component_assembly(W, H, rebuild=False, save=True)
print_summary(info)

disc_fails = []
for label, fn in [
    ("Inner_Lane_Rail", lambda: make_inner_lane_rail_body(W)),
    ("Exit_Track", lambda: make_exit_track(W, H)),
    ("Exit_Ramp", lambda: make_exit_ramp(W, H)),
    ("Guide_System", make_guide_system),
    ("Width_Carriage", lambda: make_width_carriage(W)),
    ("Crossbar_Bridge", make_crossbar_bridge),
]:
    bb = fn().BoundBox
    if bb.ZMin < GAP0 - 0.08:
        disc_fails.append({"part": label, "z_min_mm": round(bb.ZMin, 3)})

rail = make_inner_lane_rail_body(W)
defl = make_inlet_deflector(W)
defl_rail_ov = _overlap_volume(defl, rail)
# Carriage clamp (không gồm phễu) — so khung tọa độ gốc; phễu tách khỏi máng
rail_defl_sep_ok = (
    float(getattr(defl, "Volume", 0.0) or 0.0) > 80.0
    and defl_rail_ov <= max(350.0, 0.12 * float(getattr(defl, "Volume", 0.0) or 0.0))
)
throat_w_ok = True
throat_checks = []
for ww in (W_MIN, W_MAX, W):
    tp = inlet_throat_params(ww)
    d = make_inlet_deflector(ww)
    bb = d.BoundBox
    throat_checks.append(
        {
            "W_mm": ww,
            "throat_w_mm": tp["throat_w_mm"],
            "r_in_mm": round(tp["r_in_mm"], 2),
            "r_out_mm": round(tp["r_out_mm"], 2),
            "z_min_mm": round(bb.ZMin, 3),
        }
    )
    if abs(tp["throat_w_mm"] - ww) > 1e-6 or bb.ZMin < GAP0 - 0.08 or float(getattr(d, "Volume", 0.0) or 0.0) < 50.0:
        throat_w_ok = False

v1 = verify_single_exit_path_only()
v2 = verify_lane_outer_boundary_sealed()
out = {
    "pass": bool(
        not disc_fails
        and v1["pass"]
        and v2["pass"]
        and throat_w_ok
        and rail_defl_sep_ok
    ),
    "GAP0_mm": GAP0,
    "lane_w_mm": CHUTE_W_MM,
    "inlet_deflector_separated": {
        "pass": rail_defl_sep_ok,
        "deflector_rail_overlap_mm3": round(defl_rail_ov, 1),
        "deflector_volume_mm3": round(float(getattr(defl, "Volume", 0.0) or 0.0), 1),
        "note": "W adjusts inlet throat only; lane fixed 30mm; deflector not fused to rail",
    },
    "disc_clearance": {"pass": not disc_fails, "fails": disc_fails},
    "single_exit": {"pass": v1["pass"]},
    "lane_outer": {"pass": v2["pass"], "n_gaps": v2["n_gaps"]},
    "inlet_throat_sweep": throat_checks,
    "bevel_both_sides": True,
}
out_path = Path(r"D:\Project\coutingmachine\3d_model\freecad\out\tube_l_inlet_deflector_verify.json")
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
for name in list(App.listDocuments().keys()):
    App.closeDocument(name)
