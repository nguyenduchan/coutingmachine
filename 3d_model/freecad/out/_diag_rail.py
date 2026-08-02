import sys
from pathlib import Path
sys.path.insert(0, r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts

drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
hb = BX.LID.get("height_bar", {})
drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
drv["include_bottom_stop"] = False
drv["include_scale"] = False
parts = build_height_adjust_z_parts(cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False)
for name, sh, _ in parts:
    if "Rail_" not in name:
        continue
    sols = list(getattr(sh, "Solids", []) or [])
    print("===", name, "nsol=", len(sols), "vol=", round(float(sh.Volume),1))
    for i, s in enumerate(sols):
        bb = s.BoundBox
        print(
            "  sol%d V=%.1f X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
            % (i, float(s.Volume), bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)
        )
