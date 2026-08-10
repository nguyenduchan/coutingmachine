import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
from width_chute_selector import verify_dwell_jump_math, verify_no_jam_sweep, verify_flow_path_geometry, verify_gate_seal_no_gaps
m = verify_dwell_jump_math()
print("MATH pass", m["pass"])
print("checks", json.dumps(m["checks"], indent=2))
if not m["pass"]:
    for k in ("jump_bands","tooth_bands","dwell_bands","landmarks"):
        print("---", k)
        print(json.dumps(m.get(k), indent=2)[:3000])
