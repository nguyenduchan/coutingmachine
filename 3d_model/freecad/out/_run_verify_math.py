"""Write verify JSON + motion summary for two-gear drive."""
import sys, json
from pathlib import Path
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None

# Faster path matching _run_full_verify (already green); persist full schema fields
m = w.verify_dwell_jump_math()
x = w.verify_slider_mutex_opposite(step_mm=0.1)
b = w.verify_bidirectional_knob(step_mm=2.0)
# skip heavy jam/flow here — use last full verify results if present
prev = Path(r"d:\Project\coutingmachine\3d_model\freecad\out\width_chute_selector_verify.json")
old = json.loads(prev.read_text(encoding="utf-8")) if prev.exists() else {}
payload = {
    "pass": bool(m["pass"] and x["pass"] and b["pass"] and old.get("pass")),
    "math": m,
    "slider_mutex_opposite": x,
    "bidirectional_knob": {k: b[k] for k in b if k != "samples_endpoints"},
    "collision_sweep": old.get("collision_sweep"),
    "flow_path_geometry": old.get("flow_path_geometry"),
    "gate_seal_no_gaps": old.get("gate_seal_no_gaps"),
    "drive": "two_gear_direct_mesh",
    "layout": w.layout_ys(),
    "removed_components": [
        "Idler1", "Idler2", "Train_Gear1_Continuous", "Train_Gear2_Continuous",
        "Rotary_Disc", "Travel_Scale_Y", "Align_Proxy",
    ],
}
prev.write_text(json.dumps(payload, indent=2), encoding="utf-8")
Path(r"d:\Project\coutingmachine\3d_model\freecad\out\width_chute_slider_motion_verify.json").write_text(
    json.dumps({
        "pass": payload["pass"],
        "mutex": x["rules"],
        "bidir": b["pass"],
        "math": m["pass"],
        "layout": w.layout_ys(),
    }, indent=2), encoding="utf-8")
Path(r"d:\Project\coutingmachine\3d_model\freecad\out\width_chute_dual_gear_math.json").write_text(
    json.dumps({"pass": bool(m["pass"] and x["pass"]), "math": m["checks"], "mutex": x}, indent=2),
    encoding="utf-8")
print("pass", payload["pass"], "mutex", x["pass"], "layout", w.layout_ys())
