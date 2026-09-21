from placement_floorplan import compact_placement_170x150

p = compact_placement_170x150(35, 30, 170, 150)
boxes = p["boxes"]
for k, v in boxes.items():
    print(f"{k:7s} {v}")
print("jx", p["jx"], "j30", p["j30x"], p["j30y"], "tx", p["tx"], p["ty"])
print("u10", p["u10_ctrl_x"], p["u10_q_x"], p["u10_y0"], "r4", p["r4x"], p["r4y"])
print("j3/j18", p["j3x"], p["j18x"], "j16", p["j16x"], "j31a", p["j31ax"], p["j31ay"])
