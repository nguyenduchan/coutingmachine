import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
import Part
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
# Probe left M3 at ex~-9, hy~ y_brg + bearing_t/2
# Sample points: hole axis and -X face opening
ex, hy, z_pin = -9.0, -18.85 + 4.25, 88.0
z_ear0 = z_pin - 5.0
# Is material at hole center (should be VOID)?
def inside(sh, x,y,z):
    return sh.isInside(App.Vector(x,y,z), 0.05, True)
print("nsol", len(list(rail.Solids)))
bb = rail.BoundBox
print("XMin", bb.XMin)
# Along hole axis at mid ear
for z in (z_ear0+1, z_ear0+2.5, z_ear0+4):
    print("axis(%.1f,%.1f,%.1f) solid=%s" % (ex, hy, z, inside(rail, ex, hy, z)))
# At -X face toward hole
for x in (bb.XMin+0.2, bb.XMin+1.0, ex-3, ex-1, ex):
    print("face_x=%.2f y=%.1f z=%.1f solid=%s" % (x, hy, z_ear0+1.5, inside(rail, x, hy, z_ear0+1.5)))
# Cap too
cap = doc.getObject("HA_Bearing_Cap_S").Shape
print("Cap nsol", len(list(cap.Solids)), "XMin", cap.BoundBox.XMin)
for z in (z_pin+1, z_pin+3):
    print("cap axis(%.1f,%.1f,%.1f) solid=%s" % (ex, hy, z, inside(cap, ex, hy, z)))
App.closeDocument(doc.Name)
