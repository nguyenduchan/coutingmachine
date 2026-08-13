"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Module rieng: VACH DIEU CHINH DO CAO (lưỡi Height_Scraper — 2mm sát miệng lane
tại θ_mouth, giới hạn chiều cao vật đi qua = H). Tach tu make_height_scraper()
goc (xem git log) — phan "blade+lip" (khong bao gom "thanh tinh tien doc",
xem part_height_slider.py). Ghep lai thanh Height_Scraper hoan chinh trong
part_height_slider.py::make_height_scraper().
"""
from __future__ import annotations

import math

import FreeCAD as App
import Part

from mech_common import *  # noqa: F401,F403
from part_width_carriage import make_width_carriage

SCRAPER_RAMP_LEN = 10.0  # dốc nghiêng trước lưỡi — ép vật cao/chồng xuống ≤H
# thay vì chỉ chặn cứng (rủi ro kẹt khi vật lăn/đứng chạm mép lưỡi phẳng —
# xem 3d_model/sim/tube_l_height_scraper_pybullet.py: lưỡi phẳng có thể ghim
# viên "đứng" tại chỗ thay vì lật nằm; dốc nghiêng biến lực đẩy ngang thành
# lực ép xuống, đảm bảo hạ được trước khi tới mép lưỡi).


def _height_ramp_local(blade_len: float, z1: float) -> Part.Shape:
    """Nêm nghiêng LOCAL (trước khi rotate/translate như blade/lip): đáy dốc
    từ cao (không chặn, y=-RAMP_LEN) xuống z1 (=H, khớp đáy lưỡi tại y=0)."""
    half = 0.5 * blade_len
    z_top = z1 + H_MAX + 4.0
    pts = [
        App.Vector(-half, -SCRAPER_RAMP_LEN, z_top),
        App.Vector(-half, 0.0, z_top),
        App.Vector(-half, 0.0, z1),
        App.Vector(-half, -SCRAPER_RAMP_LEN, z_top),
    ]
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(App.Vector(blade_len, 0, 0))


def make_height_wall(width_open: float, height_open: float) -> Part.Shape:
    """
    Vách điều chỉnh độ cao (lưỡi Height_Scraper): thanh ngang 2 mm sát mặt
    miệng lane (θ_mouth), phủ W. Không phủ cả cung tới cửa ra. Thành L ngắn
    phía tâm, trong lane.
    """
    ap = aperture_from_opens(width_open, height_open)
    z1 = ap["z1"]
    r_i, r_o = ap["r_inner"], ap["r_outer"]
    r_join = r_o - 0.4
    r_blade_in = min(r_i + 0.6, r_join - 0.5)
    blade_len = max(2.0, r_join - r_blade_in)
    r_mid = 0.5 * (r_blade_in + r_join)
    th_m = _deg2rad(THETA_MOUTH_DEG)
    # local +X = xuyên tâm, +Y = +θ vào lane; Y=0 tại mặt miệng
    blade = _box(
        blade_len, SCRAPER_BLADE_ALONG, SCRAPER_T,
        -0.5 * blade_len, 0.0, z1,
    )
    blade.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), THETA_MOUTH_DEG)
    blade.translate(App.Vector(r_mid * math.cos(th_m), r_mid * math.sin(th_m), 0))
    blade = _refine(blade)
    ramp = _height_ramp_local(blade_len, z1)
    ramp.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), THETA_MOUTH_DEG)
    ramp.translate(App.Vector(r_mid * math.cos(th_m), r_mid * math.sin(th_m), 0))
    ramp = _refine(ramp)
    blade = _refine(blade.fuse(ramp))
    # Thành L đứng trên mép trong lưỡi — không đâm vào đĩa / rail
    lip = _box(
        SCRAPER_ENTRY_T, SCRAPER_BLADE_ALONG, SCRAPER_ENTRY_H,
        -0.5 * blade_len, 0.0, z1,
    )
    lip.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), THETA_MOUTH_DEG)
    lip.translate(App.Vector(r_mid * math.cos(th_m), r_mid * math.sin(th_m), 0))
    lip = _refine(lip)
    body = blade.fuse(lip)
    try:
        body = _refine(body.cut(make_crossbar_bridge()))
    except Exception:
        pass
    try:
        body = _refine(body.cut(make_width_carriage(width_open)))
    except Exception:
        pass
    return _refine(body)
