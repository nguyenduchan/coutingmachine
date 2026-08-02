import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
import FreeCAD as App
import Part
import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, _as_one_solid

# Monkey: rebuild internals by copying key geometry via a slim probe
# Re-run only the rail fuse path by importing module functions after build prints dims
import height_adjust_z as HA

drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
hb = BX.LID.get("height_bar", {})
drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
drv["include_bottom_stop"] = False
drv["include_scale"] = False

# Instrument: wrap _as_one_solid to dump when called from finish - easier to rebuild pieces
# Instead: open saved FCStd and inspect Rail_S solids
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
obj = doc.getObject("HA_Bearing_Rail_S")
sh = obj.Shape
sols = list(sh.Solids)
print("Rail_S nsol", len(sols), "vol", float(sh.Volume))
for i, s in enumerate(sols):
    bb = s.BoundBox
    print("sol%d V=%.1f X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f]" % (
        i, float(s.Volume), bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
# Distances between solids
if len(sols) >= 2:
    for i in range(len(sols)):
        for j in range(i+1, len(sols)):
            d = sols[i].distToShape(sols[j])[0]
            print("dist sol%d-sol%d = %.4f" % (i, j, d))
App.closeDocument(doc.Name)
