import sys
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
import FreeCAD as App, Part
importlib.reload(w)
q=31.0
ap=w.aperture_mm(q)
r=min(1.2, 0.45*min(ap, w.active_lane_width(q)))
y_c=w.flow_center_y(q)
z_c=w.DISC_Z_TOP+r+0.05
print("ap",ap,"r",r,"yc",y_c,"zc",z_c,"jaw",w.bar_y0(q))
obs=w._flow_obstacles(q)
# split obstacles
parts=[("inlet",w.make_inlet_chute()),("gate",w.make_width_gate_fixed(q)),
       ("s1",w.make_slider1_with_rack(q)),("rails",w.make_slider1_y_rails()),
       ("cass",w._fuse_shapes([sh for n,sh,c in w.make_cassette_chutes(q)]))]
x_mid=w.INLET_L+0.5*w.GATE_L
ball=Part.makeSphere(r); ball.translate(App.Vector(x_mid,y_c,z_c))
print("vs all", w.common_volume(ball, obs))
for n,sh in parts:
    print(n, w.common_volume(ball, sh))
# also check gate pieces conceptually - lip_p
