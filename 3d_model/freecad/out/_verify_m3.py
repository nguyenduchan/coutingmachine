import sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
import FreeCAD as App
import Part
import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, M3_CLEAR, M3_NUT_POCKET_AF, M3_NUT_POCKET_H, BOLT_EAR

drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
hb = BX.LID.get("height_bar", {})
drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
drv["include_bottom_stop"] = False
drv["include_scale"] = False
parts = {n: sh for n, sh, _ in build_height_adjust_z_parts(cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False)}

rail = parts["HA_Bearing_Rail_S"]
cap = parts["HA_Bearing_Cap_S"]
# dims from prints / known
# re-derive clamp from rail BB and typical
# Find hole by scanning for void cylinder near bearing
bb = rail.BoundBox
print("Rail BB X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f] nsol=%d" % (
    bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax, len(list(rail.Solids))))
capbb = cap.BoundBox
print("Cap  BB X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f]" % (
    capbb.XMin, capbb.XMax, capbb.YMin, capbb.YMax, capbb.ZMin, capbb.ZMax))

# From last build: ex=-9, y_brg=-18.85, bearing_t=8.5, z_pin=88
ex = -9.0
y0 = bb.YMin  # should be y_brg
bearing_t = 8.5
hy = y0 + 0.5 * bearing_t
z_pin = 0.5 * (bb.ZMin + bb.ZMax)  # approx mid if rail full length
# better: cap/rail split
z_pin = capbb.ZMin  # cap starts at z_pin typically
print("assumed y0=%.2f hy=%.2f z_pin=%.2f ex=%.1f" % (y0, hy, z_pin, ex))

def void(sh, x,y,z, tol=0.05):
    return not sh.isInside(App.Vector(x,y,z), tol, True)

# 1) Bolt path: continuous void along Z through cap+rail at (ex,hy)
print("\n=== BOLT AXIS void (need True=empty) ===")
for z in [z_pin - 4, z_pin - 2, z_pin - 0.5, z_pin + 0.5, z_pin + 2, z_pin + 4]:
    vr = void(rail, ex, hy, z)
    vc = void(cap, ex, hy, z)
    print("z=%6.1f rail_void=%s cap_void=%s" % (z, vr, vc))

# 2) Nut body AF box under ear must be empty
z_ear0 = z_pin - 0.5 * BOLT_EAR
print("\n=== NUT POCKET (AF box) z_ear0=%.2f ===" % z_ear0)
hits = 0
samples = 0
for dx in (-2.5, -1.0, 0, 1.0, 2.5):
    for dy in (-2.5, -1.0, 0, 1.0, 2.5):
        for dz in (0.3, 1.4, 2.5):
            samples += 1
            if not void(rail, ex+dx, hy+dy, z_ear0+dz):
                hits += 1
print("nut pocket solid hits %d / %d (want 0)" % (hits, samples))

# 3) Nut INSERTION path from -X: can we slide nut to pocket?
# Nut needs ~AF path; check corridor from XMin to ex at nut Z
print("\n=== NUT INSERT from -X (corridor) ===")
z_nut = z_ear0 + 0.5 * M3_NUT_POCKET_H
blocked = []
for x in [bb.XMin + 1, -28, -22, -16, -12, -10, ex]:
    # center and 4 corners of nut AF
    ok = True
    for dx,dy in [(0,0),(2.8,2.8),(2.8,-2.8),(-2.8,2.8),(-2.8,-2.8)]:
        if not void(rail, x+dx*0, hy+dy*0 if dx==0 and dy==0 else hy, z_nut) and dx==0:
            pass
        if dx==0 and dy==0:
            if not void(rail, x, hy, z_nut):
                ok = False
        else:
            # check offset at fixed x toward pocket - only near ex matter for corners
            if abs(x - ex) < 4:
                if not void(rail, ex+dx*0.5, hy+dy*0.5, z_nut):
                    ok = False
    if not void(rail, x, hy, z_nut):
        ok = False
        blocked.append(x)
    print("x=%6.1f mid_void=%s" % (x, void(rail, x, hy, z_nut)))

# Wrench: need space under ear for hex ~7mm across flats turn
print("\n=== WRENCH swing under ear (r=5 around hy) ===")
for ang in range(0, 360, 45):
    rad = math.radians(ang)
    x = ex + 5.0 * math.cos(rad)
    y = hy + 5.0 * math.sin(rad)
    z = z_ear0 - 1.0
    print("ang=%3d void=%s @ (%.1f,%.1f,%.1f)" % (ang, void(rail, x,y,z), x,y,z))

# Hex head access from +Z on cap
print("\n=== HEAD CBORE on cap ===")
for z in [capbb.ZMax - 0.5, capbb.ZMax - 1.5, capbb.ZMax - 2.5]:
    print("z=%.1f void=%s" % (z, void(cap, ex, hy, z)))

# Is ear -X face exposed or still wall at ear height?
print("\n=== VIEW from -X at ear mid-Z ===")
z_mid = z_ear0 + 0.4 * BOLT_EAR
for x in [bb.XMin+0.5, -30, -20, -14, -11, -9]:
    print("x=%6.1f void=%s" % (x, void(rail, x, hy, z_mid)))

# Distance from rail XMin to ex - how deep is buried
print("\ndepth rail_x0 to ex = %.1f mm" % (ex - bb.XMin))
print("bearing_t=%.1f BOLT_EAR=%.1f nut_AF=%.1f" % (bearing_t, BOLT_EAR, M3_NUT_POCKET_AF))
