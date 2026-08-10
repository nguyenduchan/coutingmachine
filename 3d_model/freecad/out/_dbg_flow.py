import sys, json
sys.path.insert(0, r"d:\Project\coutingmachine\3d_model\freecad")
import importlib, width_chute_selector as w
importlib.reload(w)
w._GEAR1_LOCAL = w._GEAR2_LOCAL = w._TRAIN_G_LOCAL = w._IDLER_LOCAL = None
flow = w.verify_flow_path_geometry(n_steps=9)
print(json.dumps(flow, indent=2)[:2500])
