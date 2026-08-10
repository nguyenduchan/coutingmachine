import sys, json, math
from pathlib import Path
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None

out = {"checks": {}, "sweep": [], "mesh_samples": []}
math_v = w.verify_dwell_jump_math()
out["checks"]["math"] = {
    "pass": math_v["pass"],
    "phases": {k: [round(a,2), round(b,2)] for k,(a,b) in math_v.get("phases", {}).items()} if isinstance(math_v.get("phases"), dict) else math_v.get("phases"),
    "key": {k: math_v["checks"].get(k) for k in (
        "dwell_stand_still", "jumps_at_5_and_9", "g2_opposite_same_speed",
        "sliders_coplanar", "slider2_above_slider1", "sealed_at_0",
        "no_aperture_motion_outside_gear1", "no_cassette_motion_outside_gear2",
    )},
}

r = w.gear_math()["pitch_radius"]
rows = []
n = 33
for i in range(n):
    q = w.TRAVEL_MAX * i / (n - 1)
    st = w.selector_state(q)
    th1 = st["gear1_angle_deg"]
    th_exp = -(q / r) * (180.0 / math.pi)
    rows.append({
        "q_mm": round(q, 3),
        "knob_deg": round(st["knob_angle_deg"], 3),
        "gear1_deg": round(th1, 3),
        "gear2_deg": round(st["gear2_angle_deg"], 3),
        "slider1_aperture_mm": st["aperture_mm"],
        "slider2_cassette_dy_mm": st["slider2_mm"],
        "chute": st["chute_name"],
        "g1_active": st["gear1_active"],
        "g2_active": st["gear2_active"],
        "theta_err_deg": round(abs(th1 - th_exp), 6),
        "reverse_err_deg": round(abs(st["gear2_angle_deg"] + th1), 6),
    })

rev_ok = True
b = w.drive_phase_bounds()
for q in (w.TRAVEL_MAX, 0.0):
    st = w.selector_state(q)
    if q >= b["gear2_2"][0] and st["chute_index"] != 2:
        rev_ok = False
    if q < 1e-9 and (st["aperture_mm"] > 1e-9 or st["chute_index"] != 0):
        rev_ok = False

theta_ok = all(rr["theta_err_deg"] < 1e-4 and rr["reverse_err_deg"] < 1e-4 for rr in rows)
ap_freeze_ok = True
cass_freeze_ok = True
ap_increases_on_g1 = True
prev = rows[0]
for rr in rows[1:]:
    dap = rr["slider1_aperture_mm"] - prev["slider1_aperture_mm"]
    dcy = rr["slider2_cassette_dy_mm"] - prev["slider2_cassette_dy_mm"]
    mid_q = 0.5 * (rr["q_mm"] + prev["q_mm"])
    if w.gear1_active(mid_q):
        if dap < -1e-6:
            ap_increases_on_g1 = False
    elif abs(dap) > 1e-6:
        ap_freeze_ok = False
    if (not w.gear2_active(mid_q)) and abs(dcy) > 1e-6:
        cass_freeze_ok = False
    prev = rr

for q in (1.0, 0.5 * sum(b["gear1_b"]), 0.5 * sum(b["gear2_1"])):
    m = w.verify_gear_mesh(q)
    out["mesh_samples"].append({"q": round(q, 3), "pass": m["pass"],
        "g1": None if not m.get("gear1") else {"pass": m["gear1"].get("pass"), "ov": m["gear1"].get("overlap_mm3")},
        "g2": None if not m.get("gear2") else {"pass": m["gear2"].get("pass"), "ov": m["gear2"].get("overlap_mm3"), "skip": m["gear2"].get("skipped")}})

jam = w.verify_no_jam_sweep(n_steps=7)
flow = w.verify_flow_path_geometry(n_steps=7)
seal = w.verify_gate_seal_no_gaps(n_steps=7)

out["checks"]["knob_gear_angle"] = {"pass": theta_ok}
out["checks"]["slider1_freeze_when_g1_blank"] = {"pass": ap_freeze_ok}
out["checks"]["slider2_freeze_when_g2_blank"] = {"pass": cass_freeze_ok}
out["checks"]["slider1_opens_on_g1"] = {"pass": ap_increases_on_g1}
out["checks"]["reverse_landmarks"] = {"pass": rev_ok}
out["checks"]["jam"] = {"pass": jam["pass"], "hits": jam["jam_hits"], "worst": jam.get("worst")}
out["checks"]["flow"] = {"pass": flow["pass"]}
out["checks"]["seal"] = {"pass": seal["pass"], "sealed_at_0": seal.get("sealed_at_0_blocks_junction")}
out["sweep"] = rows
out["summary"] = {
    "TRAVEL_MAX_mm": w.TRAVEL_MAX,
    "pitch_radius_mm": r,
    "knob_deg_range": [rows[0]["knob_deg"], rows[-1]["knob_deg"]],
    "slider1_aperture_mm": [rows[0]["slider1_aperture_mm"], rows[-1]["slider1_aperture_mm"]],
    "slider2_cassette_dy_mm": [rows[0]["slider2_cassette_dy_mm"], rows[-1]["slider2_cassette_dy_mm"]],
    "phases": out["checks"]["math"]["phases"],
}
flags = [
    out["checks"]["math"]["pass"], theta_ok, ap_freeze_ok, cass_freeze_ok,
    ap_increases_on_g1, rev_ok, jam["pass"], flow["pass"], seal["pass"],
    all(m["pass"] for m in out["mesh_samples"]),
]
out["pass"] = all(flags)
Path(r"d:\Project\coutingmachine\3d_model\freecad\out\width_chute_slider_motion_verify.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("PASS" if out["pass"] else "FAIL")
print("SUMMARY", json.dumps(out["summary"], indent=2))
print("CHECKS", json.dumps(out["checks"], indent=2))
print("MESH", json.dumps(out["mesh_samples"], indent=2))
print("--- motion landmarks ---")
for rr in rows:
    q = rr["q_mm"]
    if (q < 0.01 or abs(q-5)<0.15 or abs(q-11)<0.25 or abs(q-15)<0.25
            or abs(q-25)<0.25 or abs(q-w.TRAVEL_MAX)<0.15):
        print("q=%5.1f  θ1=%7.1f° θ2=%+7.1f°  ap=%5.1f  cass_dy=%6.1f  g1=%-5s g2=%-5s  chute=%s" % (
            q, rr["gear1_deg"], rr["gear2_deg"], rr["slider1_aperture_mm"],
            rr["slider2_cassette_dy_mm"], rr["g1_active"], rr["g2_active"], rr["chute"]))
