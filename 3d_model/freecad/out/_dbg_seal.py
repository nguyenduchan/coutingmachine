import sys
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
for q in (0.0, 1.0, 5.0, 9.0, 15.0, 31.0):
    st = w.selector_state(q)
    print("q=%.1f ap=%.2f sealed=%s bar_y0=%.2f bar_y1=%.2f gate=[%.1f,%.1f] g1=%s" % (
        q, st["aperture_mm"], st["sealed"], st["bar_y0"], st["bar_y1"],
        w.GATE_LEFT_INNER, w.GATE_RIGHT_INNER, st["gear1_active"]))
seal = w.verify_gate_seal_no_gaps(n_steps=5)
print("seal_pass", seal["pass"], "sealed_at_0 samples", [r for r in seal.get("samples", seal.get("rows", []))[:3]])
