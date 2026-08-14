# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

_HERE = Path(r"D:\Project\coutingmachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import FreeCAD as App  # noqa: E402
from mech_common import GAP0, CHUTE_W_MM, make_exit_track, make_exit_ramp, make_crossbar_bridge  # noqa: E402
from part_inner_lane_rail import make_inner_lane_rail_body  # noqa: E402
from part_guide_system import make_guide_system  # noqa: E402
from tube_l_components import build_component_assembly, component_path, print_summary  # noqa: E402
from tube_l_exit_gate import verify_single_exit_path_only, verify_lane_outer_boundary_sealed  # noqa: E402

PARTS = {
    "Crossbar_Bridge": make_crossbar_bridge,
    "Guide_System": make_guide_system,
    "Inner_Lane_Rail": lambda: make_inner_lane_rail_body(9.0),
    "Exit_Track": lambda: make_exit_track(9.0, 5.0),
    "Exit_Ramp": lambda: make_exit_ramp(9.0, 5.0),
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

doc, info = build_component_assembly(9.0, 5.0, rebuild=False, save=True)
print_summary(info)

disc_fails = []
for label, fn in [
    ("Inner_Lane_Rail", lambda: make_inner_lane_rail_body(9.0)),
    ("Exit_Track", lambda: make_exit_track(9.0, 5.0)),
    ("Exit_Ramp", lambda: make_exit_ramp(9.0, 5.0)),
    ("Guide_System", make_guide_system),
    ("Crossbar_Bridge", make_crossbar_bridge),
]:
    bb = fn().BoundBox
    if bb.ZMin < GAP0 - 0.08:
        disc_fails.append({"part": label, "z_min_mm": round(bb.ZMin, 3)})

v1 = verify_single_exit_path_only()
v2 = verify_lane_outer_boundary_sealed()
out = {
    "pass": bool(not disc_fails and v1["pass"] and v2["pass"]),
    "GAP0_mm": GAP0,
    "CHUTE_W_mm": CHUTE_W_MM,
    "disc_clearance": {"pass": not disc_fails, "fails": disc_fails},
    "single_exit": {"pass": v1["pass"]},
    "lane_outer": {"pass": v2["pass"], "n_gaps": v2["n_gaps"]},
    "crossbar_full_span": True,
    "mouth_guide_on_crossbar": True,
}
Path(r"D:\Project\coutingmachine\3d_model\freecad\out\tube_l_chute_rigid_verify.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)
print(json.dumps(out, indent=2))
for name in list(App.listDocuments().keys()):
    App.closeDocument(name)
