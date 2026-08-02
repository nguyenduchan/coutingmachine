import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
for name in ("HA_Bearing_Rail_S", "HA_Bearing_Cap_S", "HA_Bearing_Rail_N", "HA_Bearing_Cap_N"):
    sh = doc.getObject(name).Shape
    bb = sh.BoundBox
    print("%s X=%.2f Y=%.2f Z=%.2f | Y[%.2f,%.2f] Z[%.2f,%.2f]" % (
        name, bb.XLength, bb.YLength, bb.ZLength, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
App.closeDocument(doc.Name)
