import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
cap = doc.getObject("HA_Bearing_Cap_S").Shape
print("Rail Z", round(rail.BoundBox.ZMin,2), round(rail.BoundBox.ZMax,2))
print("Cap  Z", round(cap.BoundBox.ZMin,2), round(cap.BoundBox.ZMax,2))
try:
    common = rail.common(cap)
    print("common null", common.isNull(), "vol", round(float(common.Volume),2) if not common.isNull() else 0)
    if not common.isNull():
        bb = common.BoundBox
        print("common BB X", round(bb.XMin,2), round(bb.XMax,2), "Y", round(bb.YMin,2), round(bb.YMax,2), "Z", round(bb.ZMin,2), round(bb.ZMax,2))
except Exception as e:
    print("common err", e)
App.closeDocument(doc.Name)
