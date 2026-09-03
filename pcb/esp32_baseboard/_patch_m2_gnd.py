from pathlib import Path

p = Path(__file__).with_name("gen_submodules.py")
t = p.read_text(encoding="utf-8")
start = t.index("        # GND: E")
end = t.index("    _silk(a, \"IN=N  OUT=S  SNS=P1.5\"")
new = '''        # GND: E-K on F; B to west rail at ky+0.9 (A5/A7)
        _seg(a, ex, ey, kx, ky, 6, w=0.35)
        _via(a, kx, ky, 6)
        x_g = cx - 5.5
        y_gw = ky + 0.9
        _seg(a, kx, ky, x_g, ky, 6, layer="B.Cu", w=0.4)
        _seg(a, x_g, ky, x_g, y_gw, 6, layer="B.Cu", w=0.4)
        _seg(a, x_g, y_gw, ox + 2.2, y_gw, 6, layer="B.Cu", w=0.4)
        # 3V3 F stub east of 10k
        _seg(a, out_x, rout_s, out_x + 2.5, rout_s, 11, w=0.4)

    gnd_rail_x = ox + 2.2
    y_gw = chip_y + 1.27 + 0.9
    _seg(a, gnd_rail_x, y_gw, gnd_rail_x, gnd_by, 6, layer="B.Cu", w=0.45)
    _seg(a, gnd_rail_x, gnd_by, gnd_pin_x, gnd_by, 6, layer="B.Cu", w=0.45)
    _via(a, gnd_pin_x, gnd_by, 6)
    _seg(a, gnd_pin_x, gnd_by, gnd_pin_x, hy_in, 6, w=0.45)

    v3_spine = chip_xs[-1] + 7.5
    rout_s0 = chip_y + 1.0 + 3.75
    for cx in chip_xs:
        _seg(a, cx + 7.5, rout_s0, v3_spine, rout_s0, 11, w=0.4)
    _seg(a, v3_spine, rout_s0, v3_spine, hy_out - 0.5, 11, w=0.4)
    _seg(a, v3_spine, hy_out - 0.5, v3_pin_x, hy_out - 0.5, 11, w=0.4)
    _seg(a, v3_pin_x, hy_out - 0.5, v3_pin_x, hy_out, 11, w=0.45)

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched", start, end)
