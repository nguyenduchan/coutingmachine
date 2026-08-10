import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
from rotary_linear import verify_rack_pinion_mesh
g = w.gear_math()
print("root", g["root_radius"], "tip", g["tip_radius"], "pitch", g["pitch_radius"])
for q in (1.0, 5.5, 8.0, 12.0, 18.0):
    g1, s1 = w.make_gear1(q), w.make_slider1_with_rack(q)
    g2, s2 = w.make_gear2(q), w.make_slider2_with_rack(q)
    print("q=%.1f g1=%s g2=%s mate1=%.2f mate2=%.2f" % (
        q, w.gear1_active(q), w.gear2_active(q),
        w.common_volume(g1,s1), w.common_volume(g2,s2)))
    if w.gear2_active(q):
        m = verify_rack_pinion_mesh(g2, s2)
        print("  mesh2", m)
