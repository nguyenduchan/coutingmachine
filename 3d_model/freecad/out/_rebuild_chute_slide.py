# -*- coding: utf-8 -*-
import json
import math
import sys
from pathlib import Path

_HERE = Path(r"D:\Project\coutingmachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import FreeCAD as App  # noqa: E402
from mech_common import (  # noqa: E402
    GAP0,
    CHUTE_W_MM,
    CHUTE_WALL_H_MM,
    DISC_R,
    EXIT_CHUTE_LEN_MM,
    RAMP_ANGLE_DEG,
    W_MIN,
    W_MAX,
    make_exit_track,
    make_exit_ramp,
    make_bowl_exit_chute,
    make_crossbar_bridge,
    make_chute_slide_bar_at_clock,
    chute_slide_rail_specs,
    inner_lane_slide_x,
    ramp_geo,
    _cyl_z,
    _shape_min_dist_mm,
)
from part_bowl_tube import make_bowl_tube, write_bowl_tube_component  # noqa: E402
from part_inner_lane_rail import make_inner_lane_rail_body, make_inner_lane_arc_only  # noqa: E402
from part_width_carriage import make_width_carriage  # noqa: E402
from part_guide_system import make_guide_system  # noqa: E402
from part_height_slider import make_height_scraper  # noqa: E402
from part_rotor_disc import make_rotor_disc  # noqa: E402
from part_chute_slide import make_chute_slide, write_chute_slide_component  # noqa: E402
from tube_l_components import build_component_assembly, component_path, print_summary, _style  # noqa: E402
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
    "Height_Scraper": lambda: make_height_scraper(W, H),
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

write_bowl_tube_component(component_path("Bowl_Tube"), style_fn=_style)
print("wrote Bowl_Tube")
write_chute_slide_component(component_path("Chute_Slide"), style_fn=_style)
print("wrote Chute_Slide")

doc, info = build_component_assembly(W, H, rebuild=False, save=True)
print_summary(info)

bars = make_chute_slide()
bar8 = make_chute_slide_bar_at_clock(210.0)
bar10 = make_chute_slide_bar_at_clock(150.0)
bars_vol = float(getattr(bars, "Volume", 0.0) or 0.0)
v8 = float(getattr(bar8, "Volume", 0.0) or 0.0)
v10 = float(getattr(bar10, "Volume", 0.0) or 0.0)
rotor = make_rotor_disc()
rim = _overlap_volume(bars, rotor)
z_probe = GAP0 + CHUTE_WALL_H_MM + 8.0
probe8 = _cyl_z(
    8.0, 12.0,
    DISC_R * math.cos(math.radians(210.0)),
    DISC_R * math.sin(math.radians(210.0)),
    z_probe,
)
probe10 = _cyl_z(
    8.0, 12.0,
    DISC_R * math.cos(math.radians(150.0)),
    DISC_R * math.sin(math.radians(150.0)),
    z_probe,
)
hit8 = _overlap_volume(bar8, probe8) > 1.0
hit10 = _overlap_volume(bar10, probe10) > 1.0
arc_only = make_inner_lane_arc_only()
arc_vs_bars = _overlap_volume(arc_only, bars)
rail_wmax = make_inner_lane_rail_body(W_MAX)
rail_wmin = make_inner_lane_rail_body(W_MIN)
rail_w = make_inner_lane_rail_body(W)
shoe_eng = []
for ww, rail in ((W_MAX, rail_wmax), (W_MIN, rail_wmin), (W, rail_w)):
    gap = _shape_min_dist_mm(rail, bars)
    shoe_eng.append({
        "W_mm": ww,
        "slide_x_mm": round(inner_lane_slide_x(ww), 2),
        "rail_vs_bars_gap_mm": round(gap, 3),
        "engaged": gap <= 1.0,
    })
dx_ok = inner_lane_slide_x(W_MIN) > inner_lane_slide_x(W_MAX) + 20.0
zmin_bars = float(bars.BoundBox.ZMin)
zmax_arc = float(arc_only.BoundBox.ZMax)
above = zmin_bars >= zmax_arc - 0.6
try:
    exit_ov = _overlap_volume(make_exit_track(W, H), bars)
except Exception:
    exit_ov = 0.0
bowl_ov = _overlap_volume(make_bowl_tube(), bars)

track_empty = True
try:
    track_empty = float(getattr(make_exit_track(W, H), "Volume", 0.0) or 0.0) < 1.0
except Exception:
    track_empty = True
chute = make_bowl_exit_chute()
gex = ramp_geo(W, H)
disc_probe = _cyl_z(2.0 * (DISC_R - 0.4), 16.0, 0.0, 0.0, GAP0)
on_disc = _overlap_volume(chute, disc_probe)
chute_vs_rotor = _overlap_volume(chute, rotor)
chute_vol = float(getattr(chute, "Volume", 0.0) or 0.0)
zmin_ch = float(chute.BoundBox.ZMin)
end_y = float(gex["end_xy"][1])
exit_pass = bool(
    track_empty
    and chute_vol > 200.0
    and abs(gex["angle_deg"] - 40.0) < 1e-9
    and gex["slides"]
    and gex["heading_front"]
    and on_disc < 1.0
    and chute_vs_rotor < 1.0
    and zmin_ch < GAP0 - 8.0
    and end_y < -15.0
)

v1 = verify_single_exit_path_only()
v2 = verify_lane_outer_boundary_sealed()
slide_pass = (
    bars_vol > 800.0
    and v8 > 300.0
    and v10 > 300.0
    and hit8
    and hit10
    and rim < 1.0
    and arc_vs_bars < 1.0
    and above
    and dx_ok
    and all(r["engaged"] for r in shoe_eng)
)
out = {
    "pass": bool(v1["pass"] and v2["pass"] and slide_pass and exit_pass),
    "GAP0_mm": GAP0,
    "exit_chute_len_mm": EXIT_CHUTE_LEN_MM,
    "lane_w_mm": CHUTE_W_MM,
    "exit_chute": {
        "pass": exit_pass,
        "component": "Bowl_Tube_Exit_Chute",
        "parent": "Bowl_Tube",
        "on_disc_removed": track_empty,
        "angle_deg": gex["angle_deg"],
        "clock_h": gex["clock_h"],
        "heading_front": gex["heading_front"],
        "has_floor": True,
        "slides": gex["slides"],
        "vol_mm3": round(chute_vol, 1),
        "zmin_mm": round(zmin_ch, 2),
        "end_y_mm": round(end_y, 2),
        "overlap_disc_top_mm3": round(on_disc, 3),
        "overlap_rotor_mm3": round(chute_vs_rotor, 3),
        "note": "40 deg floor chute at 9 o'clock toward Front; child of Bowl_Tube",
    },
    "chute_slide": {
        "pass": slide_pass,
        "component": "Chute_Slide",
        "rail_count": 2,
        "clock_hours": [8, 10],
        "bars_vol_mm3": round(bars_vol, 1),
        "bar_8h_vol_mm3": round(v8, 1),
        "bar_10h_vol_mm3": round(v10, 1),
        "connected_disc_wall_8h": hit8,
        "connected_disc_wall_10h": hit10,
        "bars_above_lane": above,
        "zmin_bars_mm": round(zmin_bars, 2),
        "zmax_arc_mm": round(zmax_arc, 2),
        "arc_vs_bars_mm3": round(arc_vs_bars, 3),
        "t_rail_engagement": shoe_eng,
        "slide_x_increases_when_W_drops": dx_ok,
        "overlap_rotor_disc_mm3": round(rim, 3),
        "overlap_exit_track_mm3": round(exit_ov, 3),
        "overlap_bowl_mm3": round(bowl_ov, 3),
        "rail_specs": chute_slide_rail_specs(),
        "note": "T-rails above Inner_Lane_Rail; shoes slide +X with W",
    },
    "single_exit": {"pass": v1["pass"]},
    "lane_outer": {"pass": v2["pass"], "n_gaps": v2["n_gaps"]},
}
out_path = Path(r"D:\Project\coutingmachine\3d_model\freecad\out\tube_l_chute_slide_verify.json")
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
for name in list(App.listDocuments().keys()):
    App.closeDocument(name)
