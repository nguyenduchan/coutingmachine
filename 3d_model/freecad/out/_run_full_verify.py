"""Two-gear verify: math, mutex, jam(7), flow/seal."""
import sys, json, traceback
from pathlib import Path
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
log = Path(r"d:\Project\coutingmachine\3d_model\freecad\out\_verify_log.txt").open("w", encoding="utf-8")
try:
    import importlib, width_chute_selector as w
    importlib.reload(w)
    w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None
    ly = w.layout_ys()
    log.write("layout %s axes=%s\n" % (ly, [s["name"] for s in w.gear_axis_stations()])); log.flush()
    m = w.verify_dwell_jump_math()
    log.write("MATH %s\n" % m["pass"]); log.flush()
    x = w.verify_slider_mutex_opposite(step_mm=0.1)
    log.write("MUTEX %s %s\n" % (x["pass"], x["rules"])); log.flush()
    # continuous mesh presence
    ov = w.common_volume(w.make_train_gear1(0.0), w.make_train_gear2(0.0))
    log.write("train_mesh_ov=%.3f\n" % ov); log.flush()
    jam = w.verify_no_jam_sweep(n_steps=7)
    log.write("JAM %s hits=%s worst=%s\n" % (jam["pass"], jam["jam_hits"], jam.get("worst"))); log.flush()
    flow = w.verify_flow_path_geometry(n_steps=7)
    seal = w.verify_gate_seal_no_gaps(n_steps=7)
    log.write("flow=%s seal=%s\n" % (flow["pass"], seal["pass"]))
    ok = bool(m["pass"] and x["pass"] and jam["pass"] and flow["pass"] and seal["pass"])
    Path(r"d:\Project\coutingmachine\3d_model\freecad\out\width_chute_selector_verify.json").write_text(
        json.dumps({
            "pass": ok, "math": m, "slider_mutex_opposite": x,
            "collision_sweep": jam, "flow_path_geometry": flow, "gate_seal_no_gaps": seal,
            "drive": "two_gear_direct_mesh", "train_mesh_ov_mm3": ov,
            "layout": ly,
        }, indent=2), encoding="utf-8")
    log.write("FULL %s\n" % ok)
    print("FULL", ok, "jam", jam["jam_hits"], "worst", jam.get("worst"), "train_ov", round(ov, 2))
    if not ok:
        raise SystemExit(1)
except Exception:
    log.write(traceback.format_exc())
    raise
finally:
    log.close()
