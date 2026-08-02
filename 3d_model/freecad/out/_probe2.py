import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
ex, hy, z_ear0 = -9.0, -18.85 + 4.25, 88.0 - 5.0
z_mid = z_ear0 + 0.35 * 10.0
print("nsol", len(list(rail.Solids)), "XMin", rail.BoundBox.XMin)
for x in (-33.0, -25.0, -18.0, -12.0, -10.0, -9.0):
    print("x=%.1f z=%.1f solid=%s" % (x, z_mid, rail.isInside(App.Vector(x, hy, z_mid), 0.08, True)))
App.closeDocument(doc.Name)
