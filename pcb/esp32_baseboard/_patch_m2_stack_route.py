from pathlib import Path

p = Path(__file__).with_name("gen_submodules.py")
t = p.read_text(encoding="utf-8")
# bump size for side rails
t = t.replace("M2_W, M2_H = 34.0, 100.0", "M2_W, M2_H = 36.0, 105.0")
t = t.replace("M2_W, M2_H = 30.0, 100.0", "M2_W, M2_H = 36.0, 105.0")
start = t.index("        # IN: B to y_end")
end = t.index('    _silk(a, "stack S of P2"')
new = r'''        # IN: B to y_end; F south; via; B east to 2k2
        x_iw = x_west + i * 1.15
        y_end = hy_out + 7.5
        _via(a, pin_x, hy_in + 0.6, iid)
        _seg(a, pin_x, hy_in, pin_x, hy_in + 0.6, iid, w=0.35)
        _seg(a, pin_x, hy_in + 0.6, x_iw, hy_in + 0.6, iid, layer="B.Cu", w=0.35)
        _seg(a, x_iw, hy_in + 0.6, x_iw, y_end, iid, layer="B.Cu", w=0.35)
        _via(a, x_iw, y_end, iid)
        _seg(a, x_iw, y_end, x_iw, rin_n, iid, w=0.35)
        _via(a, x_iw, rin_n, iid)
        _seg(a, x_iw, rin_n, rx, rin_n, iid, layer="B.Cu", w=0.35)
        _via(a, rx, rin_n, iid)
        _seg(a, rx, rin_s, rx, ay, aid, w=0.35)
        _seg(a, rx, ay, ax, ay, aid, w=0.35)

        # OUT: F local; B east to y_end; F header (ordered y_on)
        _seg(a, cx_pad, cy_pad, out_x, cy_pad, oid, w=0.35)
        _seg(a, out_x, cy_pad, out_x, rout_out, oid, w=0.35)
        x_oe = x_east - i * 1.15
        _seg(a, out_x, rout_out, x_oe, rout_out, oid, w=0.35)
        _via(a, x_oe, rout_out, oid)
        y_on = hy_out + 1.8 + i * 1.25
        _seg(a, x_oe, rout_out, x_oe, y_end, oid, layer="B.Cu", w=0.35)
        _via(a, x_oe, y_end, oid)
        _seg(a, x_oe, y_end, x_oe, y_on, oid, w=0.35)
        _seg(a, x_oe, y_on, pin_x, y_on, oid, w=0.35)
        _seg(a, pin_x, y_on, pin_x, hy_out, oid, w=0.35)

        # GND: E-K; via; B south to bottom bus (below all chips)
        _seg(a, ex, ey, kx, ky, 6, w=0.35)
        _via(a, kx, ky, 6)
        y_gbot = chip_ys[-1] + 8.0
        _seg(a, kx, ky, kx, y_gbot, 6, layer="B.Cu", w=0.4)
        # 3V3 stub east on F
        _seg(a, out_x, rout_3v, x_east - 0.5, rout_3v, 11, w=0.4)

    # GND bottom bus → west rail → IN GND
    y_gbot = chip_ys[-1] + 8.0
    kxs = [cx - 1.27] * 4
    # connect K columns on bottom bus
    _seg(a, cx - 1.27, y_gbot, x_west, y_gbot, 6, layer="B.Cu", w=0.5)
    _seg(a, x_west, y_gbot, x_west, gnd_by, 6, layer="B.Cu", w=0.45)
    _seg(a, x_west, gnd_by, gnd_pin_x, gnd_by, 6, layer="B.Cu", w=0.45)
    _via(a, gnd_pin_x, gnd_by, 6)
    _seg(a, gnd_pin_x, gnd_by, gnd_pin_x, hy_in, 6, w=0.45)

    # +3V3 F daisy; B far-east above y_end
    y3s = [cy + 3.75 for cy in chip_ys]
    x_3d = x_east - 0.5
    y_end = hy_out + 7.5
    for i in range(3):
        _seg(a, x_3d, y3s[i], x_3d, y3s[i + 1], 11, w=0.4)
    _via(a, x_3d, y3s[0], 11)
    y_3n = hy_out + 0.9
    x_3v_rail = ox + w - 1.2
    _seg(a, x_3d, y3s[0], x_3d, y_end, 11, layer="B.Cu", w=0.4)
    _seg(a, x_3d, y_end, x_3v_rail, y_end, 11, layer="B.Cu", w=0.4)
    _seg(a, x_3v_rail, y_end, x_3v_rail, y_3n, 11, layer="B.Cu", w=0.4)
    _seg(a, x_3v_rail, y_3n, v3_pin_x, y_3n, 11, layer="B.Cu", w=0.4)
    _via(a, v3_pin_x, y_3n, 11)
    _seg(a, v3_pin_x, y_3n, v3_pin_x, hy_out, 11, w=0.45)

'''
t = t[:start] + new + t[end:]
for a, b in [
    ("**34×100 mm**", "**36×105 mm**"),
    ("**30×100 mm**", "**36×105 mm**"),
    ("(34x100 mm, stacked)", "(36x105 mm, stacked)"),
    ("(30x100 mm, stacked)", "(36x105 mm, stacked)"),
    ("| **34×100** |", "| **36×105** |"),
    ("| **30×100** |", "| **36×105** |"),
]:
    t = t.replace(a, b)
p.write_text(t, encoding="utf-8")
print("ok")
