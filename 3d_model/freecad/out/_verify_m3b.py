import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
cap = doc.getObject("HA_Bearing_Cap_S").Shape
bridge = doc.getObject("HA_Rail_Bridge").Shape
ex, hy, z_pin = -9.0, -14.60, 87.96
z_ear0, z_ear1 = z_pin - 5.0, z_pin + 5.0

def void(sh,x,y,z):
    return not sh.isInside(App.Vector(x,y,z), 0.08, True)

print("Bridge BB", bridge.BoundBox.XMin, bridge.BoundBox.XMax, bridge.BoundBox.YMin, bridge.BoundBox.YMax, bridge.BoundBox.ZMin, bridge.BoundBox.ZMax)
print("\n=== Bridge blocks -X approach to hole? ===")
# approach from x=-40 toward rail at ear height
for x in (-40, -37, -35, -34, -33):
    print("bridge x=%.1f void=%s | rail void=%s" % (x, void(bridge,x,hy,z_ear0+2), void(rail,x,hy,z_ear0+2)))

print("\n=== Cap bolt entry from +Z ===")
for z in [98.5, 96, 94, 93, 92, 91, 90, 89]:
    print("cap z=%.1f void=%s" % (z, void(cap, ex, hy, z)))

print("\n=== Combined Rail+Bridge at approach ===")
# compound check: is path blocked by either
for x in (-40, -37, -35, -33.2, -25, -15, -9):
    br = not void(bridge, x, hy, z_ear0+2)
    rr = not void(rail, x, hy, z_ear0+2)
    print("x=%6.1f blocked_by_bridge=%s blocked_by_rail=%s" % (x, br, rr))

print("\n=== Nut AF corridor through bridge+rail ===")
af = 2.8
z_n = z_ear0 + 1.4
for x in (-40, -37, -35, -33, -20, -12, -9):
    blocked = False
    for dx in (-af, 0, af):
        for dy in (-af, 0, af):
            p = App.Vector(x, hy+dy, z_n) if abs(dx)<0.1 else App.Vector(x, hy+dy, z_n)
            # only check yz cross-section near pocket; for approach check centerline + AF at hy
            if bridge.isInside(App.Vector(x, hy+dy, z_n), 0.05, True) or rail.isInside(App.Vector(x, hy+dy, z_n), 0.05, True):
                # for far approach, only care bridge+rail at (x,hy,*)
                pass
    bmid = bridge.isInside(App.Vector(x, hy, z_n), 0.05, True)
    rmid = rail.isInside(App.Vector(x, hy, z_n), 0.05, True)
    # AF extent in Y
    baf = any(bridge.isInside(App.Vector(x, hy+dy, z_n), 0.05, True) for dy in (-af,0,af))
    raf = any(rail.isInside(App.Vector(x, hy+dy, z_n), 0.05, True) for dy in (-af,0,af))
    print("x=%6.1f mid_blocked=%s afY_blocked=%s" % (x, bmid or rmid, baf or raf))

App.closeDocument(doc.Name)
