import sys
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
from rotary_linear import verify_rack_pinion_mesh
g = w.gear_math()
r = g["pitch_radius"]
x_pitch = w.AX - r - w.CENTER_BL
cy0 = w.cassette_y_targets()[0]
for q in (5.5, 8.0, 18.0):
    cy = w.cassette_y_for_travel(q)
    travel = abs(w.cassette_y_targets()[2] - cy0) + g["tip_radius"] + 8.0
    ry0 = w.AY - travel - 4.0
    ry1 = w.AY + g["tip_radius"] + 8.0
    rack = w._rack_along_y(g, x_pitch=x_pitch, dirx=+1.0, y0=ry0, y1=ry1,
        z0=w.Z_GEAR2, face_z=w.FACE_2, body_t=4.0, mesh_y=w.AY)
    rack.translate(__import__("FreeCAD").Vector(0, cy-cy0, 0))
    m = verify_rack_pinion_mesh(w.make_gear2(q), rack)
    print("q", q, "rack_only", m, "full", verify_rack_pinion_mesh(w.make_gear2(q), w.make_slider2_with_rack(q)))
