"""Diagnose slider1 vs bearings / deck / frame overlaps."""
import sys, json
from pathlib import Path
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None

out = []
ly = w.layout_ys()
g = w.gear_math()
out.append({"layout": ly, "tip": g["tip_radius"], "pitch_r": g["pitch_radius"],
            "AX1": w.AX1, "AY1": w.AY1, "Z_GEAR": w.Z_GEAR, "BEARING_OD": w.BEARING_OD})

brg = w.make_dual_bearing_supports()
deck = w.make_gear_deck()
frame = w.make_upper_bearing_frame()
stations = w.gear_axis_stations()

for q in (0.0, 5.0, 15.0, 25.0, 31.0):
    s1 = w.make_slider1_with_rack(q)
    s2 = w.make_slider2_with_rack(q)
    row = {"q": q, "s1_bb": [round(x, 2) for x in (s1.BoundBox.XMin, s1.BoundBox.XMax, s1.BoundBox.YMin, s1.BoundBox.YMax, s1.BoundBox.ZMin, s1.BoundBox.ZMax)],
           "s1_brg": round(w.common_volume(s1, brg), 3),
           "s1_deck": round(w.common_volume(s1, deck), 3),
           "s1_frame": round(w.common_volume(s1, frame), 3),
           "s2_brg": round(w.common_volume(s2, brg), 3),
           "s2_deck": round(w.common_volume(s2, deck), 3),
           "s2_frame": round(w.common_volume(s2, frame), 3)}
    # Probe each station with a cylinder approx
    for st in stations:
        cyl = __import__("Part").makeCylinder(w.BEARING_OD * 0.55, 40.0)
        cyl.translate(__import__("FreeCAD").Vector(st["ax"], st["ay"], w.POST_Z0 - 2))
        row["s1_" + st["name"]] = round(w.common_volume(s1, cyl), 3)
        row["s2_" + st["name"]] = round(w.common_volume(s2, cyl), 3)
    out.append(row)

Path(r"d:\Project\coutingmachine\3d_model\freecad\out\_dbg_s1_brg.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
