import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
cap = doc.getObject("HA_Bearing_Cap_S").Shape
hy = -14.60
z_top = cap.BoundBox.ZMax - 0.4
# Main block top is roughly X in [-10,10]; hole should be left of that
# Find left hole center: void on axis near expected
for ex in [-16, -15.5, -15, -14.5, -14, -13, -12, -11, -10, -9]:
  void = not cap.isInside(App.Vector(ex, hy, z_top), 0.08, True)
  # also mid height
  void2 = not cap.isInside(App.Vector(ex, hy, 90.0), 0.08, True)
  print("ex=%.1f top_void=%s mid_void=%s" % (ex, void, void2))
# Is main roof at x=-5 still solid (not drilled)?
print("roof x=-5 top solid?", cap.isInside(App.Vector(-5, hy, z_top), 0.08, True))
print("roof x=-8 top solid?", cap.isInside(App.Vector(-8, hy, z_top), 0.08, True))
print("Cap XMin", cap.BoundBox.XMin)
App.closeDocument(doc.Name)
