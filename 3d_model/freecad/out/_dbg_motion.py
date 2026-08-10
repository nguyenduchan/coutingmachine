import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
b = w.drive_phase_bounds()
print("phases:", {k: b[k] for k in b})
# Sample exact phase endpoints
qs = []
for k in ("gear1_a","gear2_1","gear1_b","gear2_2","gear1_c"):
    a,c = b[k]
    qs += [a, 0.5*(a+c), c]
qs = sorted(set(round(q,6) for q in qs))
print("q     ap    cass_dy  g1   g2   chute  θ1")
for q in qs:
    st = w.selector_state(q)
    print("%5.2f %5.2f %7.2f %-5s %-5s %4s %7.1f" % (
        q, st["aperture_mm"], st["slider2_mm"], st["gear1_active"], st["gear2_active"],
        st["chute_name"], st["gear1_angle_deg"]))
# Fine freeze audit (0.25mm) like math verify
ap_bad=[]; cass_bad=[]
step=0.25
n=int(round(w.TRAVEL_MAX/step))+1
xs=[min(w.TRAVEL_MAX,i*step) for i in range(n)]
aps=[w.aperture_mm(q) for q in xs]
cys=[w.cassette_y_for_travel(q) for q in xs]
for i in range(len(xs)-1):
    mid=0.5*(xs[i]+xs[i+1])
    if (not w.gear1_active(mid)) and abs(aps[i+1]-aps[i])>1e-6:
        ap_bad.append((xs[i],xs[i+1],aps[i],aps[i+1], mid, w.gear1_active(xs[i]), w.gear1_active(xs[i+1])))
    if (not w.gear2_active(mid)) and abs(cys[i+1]-cys[i])>1e-6:
        cass_bad.append((xs[i],xs[i+1],cys[i],cys[i+1]))
print("ap_freeze_violations", len(ap_bad), ap_bad[:5])
print("cass_freeze_violations", len(cass_bad), cass_bad[:5])
# pitch sync: during g1, dap ≈ dq; during g2, |dcy| ≈ dq
sync=[]
for i in range(len(xs)-1):
    mid=0.5*(xs[i]+xs[i+1])
    dq=xs[i+1]-xs[i]
    if w.gear1_active(mid):
        sync.append(("g1", dq, aps[i+1]-aps[i]))
    if w.gear2_active(mid):
        sync.append(("g2", dq, abs(cys[i+1]-cys[i])))
err1=max(abs(dq-dap) for t,dq,dap in sync if t=="g1")
err2=max(abs(dq-dcy) for t,dq,dcy in sync if t=="g2")
print("pitch_sync max|dap-dq| g1=%.6f g2=%.6f" % (err1, err2))
