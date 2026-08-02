import sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import FreeCAD as App
doc = App.open(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\height_adjust_z.FCStd")
rail = doc.getObject("HA_Bearing_Rail_S").Shape
cap = doc.getObject("HA_Bearing_Cap_S").Shape
exL, exR = -9.0, 15.0
hy = -14.60
z_pin = 87.96
BOLT_EAR = 10.0
M3_CLEAR = 3.6

def void(sh,x,y,z,t=0.06):
    return not sh.isInside(App.Vector(x,y,z), t, True)

def hole_z_span(sh, ex, hy, z_lo, z_hi, step=0.25):
    """Return (first_void_z, last_void_z) along axis."""
    zs = []
    z = z_lo
    while z <= z_hi + 1e-9:
        if void(sh, ex, hy, z):
            zs.append(z)
        z += step
    if not zs:
        return None, None, 0.0
    return zs[0], zs[-1], zs[-1] - zs[0]

def ring_complete(sh, ex, hy, z, r=1.6):
    """True if all 8 compass dirs have solid just outside clear radius."""
    ok = True
    misses = []
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        # just outside bore
        x = ex + 2.2 * math.cos(a)
        y = hy + 2.2 * math.sin(a)
        if void(sh, x, y, z):
            ok = False
            misses.append(ang)
    return ok, misses

print("=== RAIL hole depth L vs R ===")
for name, ex in [("L", exL), ("R", exR)]:
    a,b,d = hole_z_span(rail, ex, hy, z_pin-12, z_pin+2)
    print("RAIL %s void_z[%.2f, %.2f] depth=%.2f" % (name, a or -1, b or -1, d))

print("\n=== CAP hole depth L vs R ===")
for name, ex in [("L", exL), ("R", exR)]:
    a,b,d = hole_z_span(cap, ex, hy, z_pin-1, cap.BoundBox.ZMax+1)
    print("CAP  %s void_z[%.2f, %.2f] depth=%.2f ZMax=%.2f" % (name, a or -1, b or -1, d, cap.BoundBox.ZMax))

print("\n=== Ring completeness mid-ear ===")
z_rail_mid = z_pin - 0.5*BOLT_EAR + 2.5
z_cap_mid = z_pin + 2.5
for name, sh, z in [("RAIL", rail, z_rail_mid), ("CAP", cap, z_cap_mid)]:
    for side, ex in [("L", exL), ("R", exR)]:
        ok, miss = ring_complete(sh, ex, hy, z)
        print("%s %s z=%.1f ring_ok=%s miss_ang=%s" % (name, side, z, ok, miss))

print("\n=== Under-hole clearance (nut/tool space) ===")
# below ear bottom z_ear0 = z_pin-5
z_ear0 = z_pin - 0.5*BOLT_EAR
for side, ex in [("L", exL), ("R", exR)]:
    print("--- RAIL under %s ---" % side)
    for dz in [0.5, 1.5, 2.5, 3.5, 5.0, 7.0]:
        z = z_ear0 - dz
        # center + AF corners
        pts = [(0,0),(2.5,2.5),(2.5,-2.5),(-2.5,2.5),(-2.5,-2.5)]
        nvoid = sum(1 for dx,dy in pts if void(rail, ex+dx, hy+dy, z))
        print("  z_ear0-%.1f: void_pts=%d/5" % (dz, nvoid))

print("\n=== Cap under CB / above split (should be void on axis) ===")
for side, ex in [("L", exL), ("R", exR)]:
    for z in [z_pin+0.5, z_pin+3, z_pin+5, cap.BoundBox.ZMax-1]:
        print("CAP %s z=%.1f void=%s" % (side, z, void(cap, ex, hy, z)))

# Compare ear pad presence: volume of solid in ear box L vs R
print("\n=== Ear pad solid sample (should match L/R) ===")
for sh_name, sh, z0, z1 in [
    ("RAIL", rail, z_pin-5, z_pin),
    ("CAP", cap, z_pin, z_pin+5),
]:
    for side, ex in [("L", exL), ("R", exR)]:
        solid_n = 0
        tot = 0
        for ix in range(-4, 5):
            for iy in range(-3, 4):
                for iz in range(0, 5):
                    x = ex + ix * 1.0
                    y = hy + iy * 1.0
                    z = z0 + iz * 1.0
                    # skip hole interior
                    if (x-ex)**2 + (y-hy)**2 < (M3_CLEAR/2)**2:
                        continue
                    tot += 1
                    if not void(sh, x, y, z):
                        solid_n += 1
        print("%s %s ear_solid_samples=%d/%d" % (sh_name, side, solid_n, tot))

App.closeDocument(doc.Name)
