import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
import FreeCAD as App
import box_settings as BX
from height_adjust_z import (
    build_height_adjust_z_parts, M3_NUT_POCKET_AF, M3_NUT_POCKET_H, BOLT_EAR
)

drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
hb = BX.LID.get("height_bar", {})
drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
drv["include_bottom_stop"] = False
drv["include_scale"] = False
parts = {n: sh for n, sh, _ in build_height_adjust_z_parts(cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False)}
rail, cap, bridge = parts["HA_Bearing_Rail_S"], parts["HA_Bearing_Cap_S"], parts["HA_Rail_Bridge"]
ex, hy, z_pin = -9.0, -14.60, 87.96
z_top = cap.BoundBox.ZMax
af = 0.5 * M3_NUT_POCKET_AF

def void(sh, x, y, z):
    return not sh.isInside(App.Vector(x, y, z), 0.08, True)

fails = []
# C1
if len(list(rail.Solids)) != 1:
    fails.append("C1 rail solids=%d" % len(list(rail.Solids)))
# C12 cap through to top
for z in [z_pin + 1, z_pin + 4, z_top - 1.0, z_top - 0.3]:
    if not void(cap, ex, hy, z):
        fails.append("C12 cap solid at z=%.1f" % z)
# C13 bridge window
for x in (-37.0, -35.0):
    if not void(bridge, x, hy, z_pin - 2):
        fails.append("C13 bridge blocks x=%.1f" % x)
# C6/C7 approach + nut AF
z_n = z_pin - 0.5 * BOLT_EAR + 0.5 * M3_NUT_POCKET_H
for x in (-40.0, -37.0, -35.0, -30.0, -20.0, -12.0, ex):
    for dy in (-af, 0.0, af):
        if not void(bridge, x, hy + dy, z_n) or not void(rail, x, hy + dy, z_n):
            # bridge only exists near -38..-33; rail window near ear
            if x <= -33.5:
                if not void(bridge, x, hy + dy, z_n):
                    fails.append("C7/C13 approach blocked bridge x=%.1f dy=%.1f" % (x, dy))
            else:
                if not void(rail, x, hy + dy, z_n):
                    fails.append("C7 approach blocked rail x=%.1f dy=%.1f" % (x, dy))
# bolt axis rail
for z in [z_pin - 3, z_pin - 1, z_pin + 1]:
    if z <= z_pin and not void(rail, ex, hy, z):
        fails.append("bolt axis rail z=%.1f" % z)
    if z >= z_pin and not void(cap, ex, hy, z):
        fails.append("bolt axis cap z=%.1f" % z)

print("VERIFY_M3_LEFT:", "PASS" if not fails else "FAIL")
for f in fails:
    print(" ", f)
print("cap ZMax=%.2f bridge solids=%d" % (z_top, len(list(bridge.Solids))))
