import sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
exL, exR = -9.0, 15.0
hy = -14.60
z_pin = 87.96
z_ear0 = z_pin - 5.0
for z in [z_ear0+0.5, z_ear0+1.5, z_ear0+2.5, z_ear0+4.0]:
  for name, ex in [("L", exL), ("R", exR)]:
    hits = []
    for ang in range(0,360,45):
      a = math.radians(ang)
      for r in (2.0, 2.5, 3.0, 3.5, 4.0):
        x = ex + r*math.cos(a); y = hy + r*math.sin(a)
        solid = rail.isInside(App.Vector(x,y,z), 0.05, True)
        if solid:
          hits.append((ang,r)); break
    print("z=%.1f %s first_solid_by_ang=%s" % (z, name, hits[:8]))
print("Rail ZMax at ear x", max(rail.BoundBox.ZMax,))
# bbox of solids near left ear
App.closeDocument(doc.Name)
