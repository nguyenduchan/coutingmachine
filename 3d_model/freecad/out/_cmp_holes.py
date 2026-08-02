import sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
import Part
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
cap = doc.getObject("HA_Bearing_Cap_S").Shape
# known: ex_L=-9, ex_R=15, hy=-14.6, z_pin=87.96
exL, exR = -9.0, 15.0
hy = -14.60
z_pin = 87.96
z0 = z_pin - 5.0  # ear bottom
z1 = z_pin

def void(sh,x,y,z,t=0.05):
    return not sh.isInside(App.Vector(x,y,z), t, True)

print("=== Circular hole completeness at mid-ear Z ===")
z = z0 + 2.5
r_clear = 1.8  # M3_CLEAR/2
for name, ex in [("LEFT", exL), ("RIGHT", exR)]:
    # sample ring around hole
    inside_solid = 0
    void_n = 0
    for i in range(24):
        a = 2*math.pi*i/24
        x = ex + r_clear*0.85*math.cos(a)
        y = hy + r_clear*0.85*math.sin(a)
        if void(rail, x, y, z):
            void_n += 1
        else:
            inside_solid += 1
    # center
    print("%s center_void=%s ring_void=%d/24 solid=%d/24" % (
        name, void(rail, ex, hy, z), void_n, inside_solid))
    # radial scan from center at several angles - where does solid start?
    for ang_deg in [0, 45, 90, 135, 180, 225, 270, 315]:
        a = math.radians(ang_deg)
        hit = None
        for rr in [i*0.25 for i in range(0, 40)]:
            x = ex + rr*math.cos(a)
            y = hy + rr*math.sin(a)
            if not void(rail, x, y, z):
                hit = rr
                break
        print("  %s ang=%3d first_solid_r=%s" % (name, ang_deg, hit))

print("\n=== Along Z at hole center ===")
for name, ex in [("LEFT", exL), ("RIGHT", exR)]:
    zs = []
    for z in [z0-2, z0, z0+1, z0+2.5, z0+4, z1-0.2, z1+0.5]:
        zs.append((z, void(rail, ex, hy, z)))
    print(name, zs)

print("\n=== Cap comparison ===")
for name, ex in [("LEFT", exL), ("RIGHT", exR)]:
    print(name, "cap center mid", void(cap, ex, hy, z_pin+3))

# Ear material presence: is left ear a full cylinder bore through a boss?
print("\nRail BB", rail.BoundBox.XMin, rail.BoundBox.XMax)
App.closeDocument(doc.Name)
