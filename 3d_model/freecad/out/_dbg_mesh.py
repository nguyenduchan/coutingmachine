import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
log = open(r"d:\Project\coutingmachine\3d_model\freecad\out\_mesh_dbg.txt","w",encoding="utf-8")
for q in (1.0, 2.5, 11.5, 13.0, 26.0):
    m = w.verify_gear_mesh(q)
    log.write("q=%s teeth=%s pass=%s\n" % (q, w.teeth_active(q), m.get("pass")))
    log.write("  %s\n" % json.dumps(m, default=str)[:800])
# fork clearance samples
for q in (0, 2, 6, 12.4, 18, 26):
    gear = w.make_drive_gear(q)
    forks = w.make_cassette_forks(q)
    ov = w.common_volume(gear, forks)
    g = w.gear_math()
    log.write("fork_ov q=%.1f ov=%.3f tip=%.2f hub_root=%.2f sector=%s teeth=%s\n" % (
        q, ov, g["tip_radius"], g["root_radius"], w.sector_active(q), w.teeth_active(q)))
log.close()
print("wrote dbg")
