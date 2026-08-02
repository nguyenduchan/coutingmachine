# -*- coding: utf-8 -*-
"""Conjugate mesh: translate rack SOLID (teeth move with follower)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
OUT = HERE / "out" / "_ha_gear_math.txt"
sys.path.insert(0, str(HERE))

class Tee:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.old = sys.stdout
    def write(self, s):
        self.f.write(s)
        try:
            self.old.write(s)
        except Exception:
            pass
    def flush(self):
        self.f.flush()
    def close(self):
        self.f.close()

tee = Tee(OUT)
sys.stdout = tee
sys.stderr = tee

import FreeCAD as App
import box_settings as BX
from height_adjust_z import (
    _rack_params,
    make_involute_pinion_local,
    make_involute_rack,
    place_pinion_axis_y,
    verify_rack_pinion_mesh,
)

drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
rp = _rack_params(drv)
g = rp["gear"]
m, z, alpha = g["module"], g["teeth"], g["alpha_deg"]
p, r, ra = g["circular_pitch"], g["pitch_radius"], g["tip_radius"]
ha, hf = g["addendum"], g["dedendum"]
s, e, clear, bl = g["tooth_thickness"], g["space_width"], g["tooth_clear"], rp["center_backlash"]
cx = 0.0
x_pitch = cx - r - bl
face_w = float(rp["face_w"])
z_pin = 0.5 * rp["stroke"] + 0.5 * ra

print("=== MATH (current model) ===")
print(f"m={m} z={z} α={alpha}°  p=πm={p:.4f} mm")
print(f"d={2*r:.1f}  pitch_r={r:.1f}  tip_r={ra:.1f}  root_r={g['root_radius']:.1f}")
print(f"ha={ha} hf={hf}  whole_depth={ha+hf}")
print(f"s={s:.4f} e={e:.4f}  circ_backlash e-s={e-s:.4f} (=tooth_clear {clear})")
print(f"center_backlash={bl}  x_pitch={x_pitch:.3f}  CD={-x_pitch:.3f}")
print(f"tip→rack_root = {(cx-ra)-(x_pitch-hf):.3f} mm")
print(f"rack_tip→pin_root = {(cx-g['root_radius'])-(x_pitch+ha):.3f} mm")
print(f"travel/turn = {g['travel_per_turn']:.3f} mm")

n_pitch = max(4, int(math.ceil((rp["stroke"] + 2 * ra + 2 * p + 6) / p)))
if n_pitch % 2:
    n_pitch += 1
rack_len = n_pitch * p
rack_z0 = z_pin - 0.5 * rack_len

rack0 = make_involute_rack(
    module=m, length_z=rack_len, face_y=face_w, body_t=0.0,
    x_pitch=x_pitch, y0=-0.5 * face_w, z0=rack_z0, mesh_z=z_pin,
    alpha_deg=alpha, tooth_clear=clear, pinion_teeth=z,
)

print()
print("=== CONJUGATE MESH (pinion θ + rack.translate Z=r*θ) ===")
max_ov = 0.0
worst = 0.0
fails = 0
for ang in [i * (360.0 / z) / 6.0 for i in range(0, 7)]:
    loc = make_involute_pinion_local(
        module=m, teeth=z, face_w=face_w, bore=0.0,
        alpha_deg=alpha, tooth_clear=clear,
    )
    loc.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0 + ang)
    pin = place_pinion_axis_y(loc, face_w=face_w, x=cx, y=0.0, z=z_pin)
    dz = r * math.radians(ang)
    rack = rack0.copy()
    rack.translate(App.Vector(0, 0, dz))
    ov = float(verify_rack_pinion_mesh(pin, rack)["overlap_mm3"] or 0.0)
    ok = ov <= 8.0
    if not ok:
        fails += 1
    if ov > max_ov:
        max_ov, worst = ov, ang
    print(f"  θ={ang:6.2f}°  dz={dz:6.3f}  ov={ov:8.3f}  {'PASS' if ok else 'FAIL'}")

print(f"worst θ={worst:.2f} ov={max_ov:.3f} fails={fails}")
print(f"result: {'PASS' if max_ov <= 8.0 else 'FAIL — jam risk'}")

print()
print("=== VERDICT ===")
if max_ov <= 8.0:
    print("OK: pitch/module/backlash consistent; conjugate motion no deep collision.")
    if clear < 0.5:
        print("NOTE: tooth_clear=0.40 is modest for FDM — 0.50–0.60 safer for print tolerance.")
else:
    print("JAM: profiles collide under motion — increase tooth_clear / center_backlash.")

tee.close()
print("Wrote", OUT)
