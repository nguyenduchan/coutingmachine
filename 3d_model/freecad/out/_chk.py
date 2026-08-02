import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
for name in ("HA_Bearing_Rail_S", "HA_Bearing_Rail_N"):
    sh = doc.getObject(name).Shape
    print("%s nsol=%d vol=%.1f" % (name, len(list(sh.Solids)), float(sh.Volume)))
App.closeDocument(doc.Name)
