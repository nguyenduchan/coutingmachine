import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
cap = doc.getObject("HA_Bearing_Cap_S").Shape
rail = doc.getObject("HA_Bearing_Rail_S").Shape
print("Cap BB", [round(x,2) for x in (cap.BoundBox.XMin,cap.BoundBox.XMax,cap.BoundBox.YMin,cap.BoundBox.YMax,cap.BoundBox.ZMin,cap.BoundBox.ZMax)])
print("Rail BB", [round(x,2) for x in (rail.BoundBox.XMin,rail.BoundBox.XMax,rail.BoundBox.YMin,rail.BoundBox.YMax,rail.BoundBox.ZMin,rail.BoundBox.ZMax)])
# find hole centers by scanning void columns
hy = -14.60
z_pin = 87.96
for name, sh, z in [("cap", cap, z_pin+3), ("rail", rail, z_pin-2)]:
  voids = []
  x = -20
  while x <= 20:
    if not sh.isInside(App.Vector(x, hy, z), 0.08, True):
      # check it's a hole-ish (neighbors)
      voids.append(round(x,1))
    x += 0.5
  # cluster
  print(name, "void xs sample", voids[:5], "...", voids[-5:] if len(voids)>5 else voids, "n", len(voids))
App.closeDocument(doc.Name)
