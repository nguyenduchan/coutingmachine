import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
from rotary_linear import make_involute_pinion_local, verify_rack_pinion_mesh
import FreeCAD as App, Part

g = w.gear_math()
# full continuous pinion at q=0 pose
local = make_involute_pinion_local(module=w.GEAR_M, teeth=w.GEAR_Z, face_w=w.FACE_W, bore=0.0,
    alpha_deg=w.ALPHA_DEG, tooth_clear=w.TOOTH_CLEAR)
local.rotate(App.Vector(0,0,0), App.Vector(0,0,1), w.knob_angle_deg(1.0))
local.translate(App.Vector(w.AX, w.AY, w.Z_GEAR))
r = g["pitch_radius"]
x_pitch = w.AX - r - w.CENTER_BL
ry0 = max(w.AY - g["tip_radius"] - w.APERTURE_MAX - 2.0, w.RACK_Y0_MIN)
ry1 = w.AY + g["tip_radius"] + w.APERTURE_MAX + 2.0
rack = w._rack_along_y(g, x_pitch=x_pitch, dirx=+1.0, y0=ry0, y1=ry1, z0=w.Z_GEAR, face_z=w.FACE_W, body_t=4.0, mesh_y=w.AY)
rack.translate(App.Vector(0, w.aperture_mm(1.0), 0))
m_full = verify_rack_pinion_mesh(local, rack)
print("full continuous mesh", m_full)

# discontinuous without lugs
w._GEAR_LOCAL = None
# monkeypatch lug angles empty
w._lug_local_angles_deg = lambda: []
disc = w._drive_gear_local()
disc.rotate(App.Vector(0,0,0), App.Vector(0,0,1), w.knob_angle_deg(1.0))
disc.translate(App.Vector(w.AX, w.AY, w.Z_GEAR))
m_disc = verify_rack_pinion_mesh(disc, rack)
print("disc no lug mesh", m_disc)
print("windows", w._tooth_keep_windows_deg())
