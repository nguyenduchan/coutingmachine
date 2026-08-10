import sys
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
from rotary_linear import make_involute_pinion_local, verify_rack_pinion_mesh
import FreeCAD as App
g = w.gear_math()
print("m=%.6f z=%d p=%.6f r=%.4f" % (g["module"], g["teeth"], g["circular_pitch"], g["pitch_radius"]))
for q in (1.0, 5.0, 8.0, 11.0, 13.0, 15.0, 20.0, 25.0):
    full = make_involute_pinion_local(module=w.GEAR_M, teeth=w.GEAR_Z, face_w=w.FACE_2, bore=0.0,
        alpha_deg=w.ALPHA_DEG, tooth_clear=w.TOOTH_CLEAR)
    full.rotate(App.Vector(0,0,0), App.Vector(0,0,1), w.knob_angle_deg(q))
    full.translate(App.Vector(w.AX, w.AY, w.Z_GEAR2))
    rack = w._slider2_rack_at(q)
    mf = verify_rack_pinion_mesh(full, rack)
    print("q=%.1f full_ov=%.3f pass=%s g2=%s cy=%.2f" % (q, mf["overlap_mm3"], mf["pass"], w.gear2_active(q), w.cassette_y_for_travel(q)))
    if w.gear1_active(q):
        m1 = verify_rack_pinion_mesh(w.make_gear1(q), w._slider1_rack_at(q))
        print("  g1 mesh", m1["pass"], round(m1["overlap_mm3"],3))
