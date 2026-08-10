import sys
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None
s1 = w.make_slider1_with_rack(0.0)
s2 = w.make_slider2_with_rack(0.0)
b1, b2 = s1.BoundBox, s2.BoundBox
print("s1 vol=%.1f x=[%.1f,%.1f] y=[%.1f,%.1f] z=[%.1f,%.1f]" % (s1.Volume, b1.XMin,b1.XMax,b1.YMin,b1.YMax,b1.ZMin,b1.ZMax))
print("s2 vol=%.1f x=[%.1f,%.1f] y=[%.1f,%.1f] z=[%.1f,%.1f]" % (s2.Volume, b2.XMin,b2.XMax,b2.YMin,b2.YMax,b2.ZMin,b2.ZMax))
print("COL1", w.COL_SLIDER1, "COL2", w.COL_SLIDER2)
print("AY1", w.AY1, "AY2", w.AY2())
parts = w.build_width_chute_selector_parts(0.0)
print("names:", [n for n,_,_ in parts if "Slider" in n or "Gear" in n or "Idler" in n or "Train" in n])
