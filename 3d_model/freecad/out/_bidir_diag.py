import sys, json
from pathlib import Path
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None

# Expanded jam pairs at key poses
def jam_at(q):
    inlet=w.make_inlet_chute(); gate=w.make_width_gate_fixed(q)
    s1=w.make_slider1_with_rack(q); core=w.make_slider_bar_core(q)
    s2=w.make_slider2_with_rack(q)
    ch=w._fuse_shapes([sh for n,sh,c in w.make_cassette_chutes(q)])
    brg=w.make_dual_bearing_supports(); frame=w.make_upper_bearing_frame()
    deck=w.make_gear_deck()
    g1=w.make_gear1(q); g2=w.make_gear2(q)
    disc=w.make_rotary_disc(q)
    cy=w.cassette_y_for_travel(q)
    mouths={
      "in": w._box(-1, w.GATE_LEFT_INNER, w.CHUTE_Z0, 2, w.INLET_W, w.INLET_H),
      "gate": w._box(w.CHUTE_X0-1, w.GATE_LEFT_INNER, w.CHUTE_Z0, 2, w.INLET_W, w.INLET_H),
      "out": w._box(w.CHUTE_X1-1, cy+w.lane_bottoms_local()[w.chute_index_for_travel(q)], w.CHUTE_Z0, 2, w.CHUTE_WS[w.chute_index_for_travel(q)], w.CHUTE_H),
    }
    blockers=[("s1",s1),("s2",s2),("brg",brg),("frame",frame),("deck",deck),("g1",g1),("g2",g2),("disc",disc),("gate",gate)]
    bad=[]
    for mn,msh in mouths.items():
        for bn,bsh in blockers:
            ov=w.common_volume(msh,bsh)
            if ov>0.05:
                bad.append((mn,bn,round(ov,2)))
    # slider/cassette vs structure
    for name,a,b,thr in [
        ("s1_brg",s1,brg,2),("s2_brg",s2,brg,2),("s1_frame",s1,frame,2),("s2_frame",s2,frame,2),
        ("s1_deck",s1,deck,5),("s2_deck",s2,deck,5),("ch_brg",ch,brg,2),("ch_deck",ch,deck,2),
        ("s2_ch",s2,ch,50),("s1_ch",s1,ch,5),("s2_gate",s2,gate,2),
    ]:
        ov=w.common_volume(a,b)
        if ov>thr: bad.append((name,round(ov,2),thr))
    return bad

report={"fwd_rev":[], "jam_extra":{}}
# bidirectional kinematics
seq=list(range(0,32,2))+[31]+list(range(31,-1,-2))
prev=None
for q in seq:
    st=w.selector_state(float(q))
    report["fwd_rev"].append({"q":q,"ap":st["aperture_mm"],"cass":st["slider2_mm"],"th1":st["gear1_angle_deg"],"th2":st["gear2_angle_deg"],"chute":st["chute_name"]})
for q in (0,5,8,11,15,20,25,31):
    report["jam_extra"][str(q)]=jam_at(float(q))
Path(r"d:\Project\coutingmachine\3d_model\freecad\out\_bidir_diag.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("jam extras:")
for k,v in report["jam_extra"].items():
    if v: print(k,v)
print("clean poses", [k for k,v in report["jam_extra"].items() if not v])
