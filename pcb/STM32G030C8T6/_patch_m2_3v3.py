from pathlib import Path

p = Path(__file__).with_name("gen_submodules.py")
t = p.read_text(encoding="utf-8")
start = t.index("        # 3V3 F stub east of 10k")
end = t.index("    _silk(a, \"IN=N  OUT=S  SNS=P1.5\"")
new = '''        # 3V3 via east of 10k → B bus (OUT stays on F — A5)
        _via(a, out_x + 2.5, rout_s, 11)
        _seg(a, out_x + 2.5, rout_s, chip_xs[-1] + 7.5, rout_s, 11, layer="B.Cu", w=0.4)

    gnd_rail_x = ox + 2.2
    y_gw = chip_y + 1.27 + 0.9
    _seg(a, gnd_rail_x, y_gw, gnd_rail_x, gnd_by, 6, layer="B.Cu", w=0.45)
    _seg(a, gnd_rail_x, gnd_by, gnd_pin_x, gnd_by, 6, layer="B.Cu", w=0.45)
    _via(a, gnd_pin_x, gnd_by, 6)
    _seg(a, gnd_pin_x, gnd_by, gnd_pin_x, hy_in, 6, w=0.45)

    v3_spine = chip_xs[-1] + 7.5
    rout_s0 = chip_y + 1.0 + 3.75
    _via(a, v3_spine, rout_s0, 11)
    _seg(a, v3_spine, rout_s0, v3_spine, hy_out - 0.5, 11, layer="B.Cu", w=0.4)
    _seg(a, v3_spine, hy_out - 0.5, v3_pin_x, hy_out - 0.5, 11, layer="B.Cu", w=0.4)
    _via(a, v3_pin_x, hy_out - 0.5, 11)
    _seg(a, v3_pin_x, hy_out - 0.5, v3_pin_x, hy_out, 11, w=0.45)

'''
# Also remove duplicate gnd block if patch left both - find from 3V3 stub only
if start < 0:
    raise SystemExit('start not found')
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("ok")
