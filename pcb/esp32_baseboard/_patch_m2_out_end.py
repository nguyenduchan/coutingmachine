from pathlib import Path

p = Path(__file__).with_name("gen_submodules.py")
t = p.read_text(encoding="utf-8")
old = """        y_on = hy_out + 1.8 + i * 1.25
        _seg(a, x_oe, rout_out, x_oe, y_end, oid, layer=\"B.Cu\", w=0.35)
        _via(a, x_oe, y_end, oid)
        _seg(a, x_oe, y_end, x_oe, y_on, oid, w=0.35)
        _seg(a, x_oe, y_on, pin_x, y_on, oid, w=0.35)
        _seg(a, pin_x, y_on, pin_x, hy_out, oid, w=0.35)
"""
# fix escapes - read actual file content
idx = t.index("        y_on = hy_out + 1.8 + i * 1.25")
idx2 = t.index("        # GND: E-K; via; B south to bottom bus", idx)
new = """        y_on = hy_out + 1.8 + i * 1.25
        _seg(a, x_oe, rout_out, x_oe, y_end, oid, layer=\"B.Cu\", w=0.35)
        _via(a, x_oe, y_end, oid)
        _seg(a, x_oe, y_end, x_oe, y_on, oid, w=0.35)
        _seg(a, x_oe, y_on, pin_x, y_on, oid, w=0.35)
        _via(a, pin_x, y_on, oid)
        _seg(a, pin_x, y_on, pin_x, hy_out + 0.55, oid, layer=\"B.Cu\", w=0.35)
        _via(a, pin_x, hy_out + 0.55, oid)
        _seg(a, pin_x, hy_out + 0.55, pin_x, hy_out, oid, w=0.35)
"""
# The file uses normal quotes not escaped
new = """        y_on = hy_out + 1.8 + i * 1.25
        _seg(a, x_oe, rout_out, x_oe, y_end, oid, layer="B.Cu", w=0.35)
        _via(a, x_oe, y_end, oid)
        _seg(a, x_oe, y_end, x_oe, y_on, oid, w=0.35)
        _seg(a, x_oe, y_on, pin_x, y_on, oid, w=0.35)
        _via(a, pin_x, y_on, oid)
        _seg(a, pin_x, y_on, pin_x, hy_out + 0.55, oid, layer="B.Cu", w=0.35)
        _via(a, pin_x, hy_out + 0.55, oid)
        _seg(a, pin_x, hy_out + 0.55, pin_x, hy_out, oid, w=0.35)
"""
t = t[:idx] + new + t[idx2:]

# GND A7: don't run B down through anode — jog west first
t2 = """        _via(a, kx, ky, 6)
        y_gbot = chip_ys[-1] + 8.0
        _seg(a, kx, ky, cx - 6.5, ky, 6, layer="B.Cu", w=0.4)
        _seg(a, cx - 6.5, ky, cx - 6.5, y_gbot, 6, layer="B.Cu", w=0.4)
"""
old_g = """        _via(a, kx, ky, 6)
        y_gbot = chip_ys[-1] + 8.0
        _seg(a, kx, ky, kx, y_gbot, 6, layer="B.Cu", w=0.4)
"""
if old_g not in t:
    raise SystemExit('gnd block not found')
t = t.replace(old_g, t2)
# bottom bus from daisy x
t = t.replace(
    "    _seg(a, cx - 1.27, y_gbot, x_west, y_gbot, 6, layer=\"B.Cu\", w=0.5)\n",
    "    _seg(a, cx - 6.5, y_gbot, x_west, y_gbot, 6, layer=\"B.Cu\", w=0.5)\n",
)
p.write_text(t, encoding="utf-8")
print("ok")
