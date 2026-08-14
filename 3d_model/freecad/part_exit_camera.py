# -*- coding: utf-8 -*-
"""
Cụm thị giác đếm viên tại cửa ra Tube_L_Exit_Gate.

TẠI SAO ĐẶT Ở ĐÂY (không phải "nhìn vào máng"):
  Exit_Track bịt viên 3 phía — nóc (z≈GAP0+H+0.3), 2 vách (z=GAP0..GAP0+H+6),
  và mặt ĐĨA làm sàn. Máng KHÔNG có đáy: đĩa chính là sàn. Nên viên chỉ lộ ra
  đúng lúc tâm nó vượt mép đĩa (r = DISC_R) và rơi qua đáy hở. Đó là chỗ DUY
  NHẤT camera thấy được viên.

TẠI SAO ĐẾM Ở MÉP ĐĨA LÀ ĐÚNG:
  Trong máng s_dot = ω·r·(sinβ − μ_wall·cosβ) — TỈ LỆ THUẬN với ω. Cho ω = 0
  thì mọi viên còn trên đĩa đứng yên tại chỗ. Chỉ viên đã qua mép đĩa là không
  giữ lại được (đang rơi tự do). Vậy đặt vạch đếm ngay mép đĩa ⇒ "đếm được" =
  "đã cam kết", không có viên nào đang bay mà chưa đếm. Sai số còn lại chỉ do
  đĩa giảm tốc: viên tiến thêm ~0.5·s_dot·t_stop. Vì s_dot ∝ ω, chạy chậm ở
  vài viên cuối là giảm sai số theo đúng tỉ lệ đó.

BỐ TRÍ:
  Exit_Camera        — global shutter + ống kính C-mount, trục quang NẰM NGANG
                       ở z = CAM_AXIS_Z, vuông góc mặt phẳng rơi
  Backlight_Panel    — tấm tán sáng ĐỐI DIỆN camera ⇒ viên hiện thành bóng đen
                       (không phụ thuộc màu/chữ in trên viên)
  Collection_Funnel  — hứng viên sau khi qua vùng nhìn, gom xuống ngăn chứa
  Camera_Mount / Backlight_Mount — trụ đứng từ đế máy (z = MOUNT_BASE_Z)

Mặt phẳng rơi = mặt phẳng đứng chứa hướng máng (θ_exit + β). Trục quang đặt
VUÔNG GÓC mặt phẳng đó nên toàn bộ độ dạt ngang của viên nằm trong ảnh, chiều
sâu gần như không đổi.
"""
from __future__ import annotations

import math

import Part

from mech_common import *  # noqa: F401,F403

G_MM_S2 = 9810.0  # gia tốc trọng trường, mm/s²

# --- Camera: global shutter machine-vision + C-mount, nối PC qua USB3 --------
CAM_BODY = (29.0, 29.0, 30.0)  # thân (dọc trục quang, ngang, cao)
CAM_LENS_D = 30.0
CAM_LENS_LEN = 35.0
CAM_SENSOR = (4.97, 3.73)  # 1/2.9" — 1440×1080, 3.45 µm
CAM_PIX = (1440, 1080)
CAM_FOCAL = 12.0  # mm
CAM_PORTRAIT = True  # xoay 90°: cạnh dài của cảm biến theo phương RƠI
CAM_WD = 170.0  # mặt trước ống kính → mặt phẳng rơi
CAM_AXIS_Z = -26.0  # cao độ trục quang (dưới mặt đĩa)

# Dải đếm: KHÔNG bắt đầu từ z=0. Trục quang gần phương tiếp tuyến nên tia từ
# viên ở ngang mặt đĩa trượt dọc r≈DISC_R và xuyên vào mép đĩa trước khi kịp
# hạ xuống dưới đáy đĩa (z=-DISC_T). Viên chỉ lộ ra sau khi rơi khỏi bóng đĩa.
# Điều đó KHÔNG ảnh hưởng độ chính xác đếm: viên đã qua mép đĩa là rơi tự do,
# không quay lại được, nên thấy nó muộn vài mm vẫn là "đã cam kết = đã đếm".
# verify_exit_camera.py dò z lộ ra thật rồi kiểm dải đếm nằm gọn trong khung.
COUNT_BAND_MM = 36.0  # chiều cao dải đếm, tính từ chỗ viên lộ ra

# --- Đèn nền ---------------------------------------------------------------
BL_PANEL = (80.0, 70.0, 6.0)  # rộng × cao × dày
BL_DIST = 100.0  # mặt phẳng rơi → mặt đèn

# --- Phễu hứng -------------------------------------------------------------
FUNNEL_TOP_Z = -64.0  # nằm DƯỚI đáy dải đếm để không che viên đang được đếm
FUNNEL_MOUTH = (70.0, 70.0)
FUNNEL_OUT_Z = -95.0
FUNNEL_OUT = (26.0, 26.0)
FUNNEL_T = 2.4

MOUNT_BASE_Z = -100.0  # mặt đế máy
MOUNT_POST = (18.0, 18.0)
MOUNT_T = 4.0

COLOR_CAM = (0.10, 0.10, 0.12)
COLOR_LENS = (0.20, 0.22, 0.26)
COLOR_BL = (1.00, 0.97, 0.80)
COLOR_MOUNT = (0.45, 0.48, 0.55)
COLOR_FUNNEL = (0.30, 0.52, 0.62)


# ---------------------------------------------------------------------------
# Hình học rơi
# ---------------------------------------------------------------------------
def exit_drift_dir() -> tuple[float, float]:
    """Hướng ngang của viên lúc rời mép đĩa = hướng máng (θ_exit + β)."""
    h = math.radians(THETA_EXIT_DEG + EXIT_FROM_RADIAL_DEG)
    return math.cos(h), math.sin(h)


def view_dir() -> tuple[float, float]:
    """Trục quang: vuông góc mặt phẳng rơi, hướng TỪ camera TỚI viên."""
    dx, dy = exit_drift_dir()
    return dy, -dx


def exit_speed(omega: float = OMEGA_DISC) -> float:
    """Tốc độ dọc máng tại mép đĩa (mm/s)."""
    return omega * DISC_R * exit_wall_friction_beta()["drive_net"]


def drop_point(D: float) -> tuple[float, float, float]:
    """Điểm tâm viên cắt r = DISC_R (bắt đầu rơi), theo cỡ viên."""
    gap = recommend_gap_mm(D, max(1.0, 0.5 * D))
    ap = aperture_from_opens(gap["W"], gap["H"])
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    cb = math.cos(math.radians(EXIT_FROM_RADIAL_DEG))
    sb = math.sin(math.radians(EXIT_FROM_RADIAL_DEG))
    # |(-r_lane,0) + s*(-cos b,-sin b)| = DISC_R
    b = 2.0 * r_lane * cb
    c = r_lane ** 2 - DISC_R ** 2
    s = (-b + math.sqrt(max(0.0, b * b - 4.0 * c))) / 2.0
    return -r_lane - s * cb, -s * sb, 0.0


def fall_xyz(D: float, z: float, omega: float = OMEGA_DISC) -> tuple[float, float]:
    """Vị trí ngang của tâm viên khi đã rơi xuống cao độ z (z ≤ 0)."""
    x0, y0, _ = drop_point(D)
    t = math.sqrt(max(0.0, -2.0 * z / G_MM_S2))
    dx, dy = exit_drift_dir()
    v = exit_speed(omega)
    return x0 + v * dx * t, y0 + v * dy * t


def camera_fov(wd: float = CAM_WD) -> tuple[float, float]:
    """Bề rộng × chiều cao khung hình tại mặt phẳng rơi (mm)."""
    sw, sh = CAM_SENSOR
    if CAM_PORTRAIT:
        sw, sh = sh, sw
    return sw * wd / CAM_FOCAL, sh * wd / CAM_FOCAL


def _view_anchor(omega: float = OMEGA_DISC) -> tuple[float, float]:
    """Giao của mặt phẳng rơi với cao độ trục quang (lấy cỡ viên giữa dải)."""
    return fall_xyz(0.5 * (W_MIN + W_MAX - 2.0), CAM_AXIS_Z, omega)


def exit_view_geometry(omega: float = OMEGA_DISC) -> dict:
    """Mọi số liệu dẫn xuất — dùng cho verify và cho phần mềm đếm trên PC."""
    vx, vy = view_dir()
    ax, ay = _view_anchor(omega)
    fov_w, fov_h = camera_fov()
    v = exit_speed(omega)
    px = (CAM_PIX[1] if CAM_PORTRAIT else CAM_PIX[0]) / fov_w
    z_top, z_bot = CAM_AXIS_Z + 0.5 * fov_h, CAM_AXIS_Z - 0.5 * fov_h

    sizes = []
    for D in (W_MIN, 5.0, 8.0, 12.0, 18.0, W_MAX - 1.0):
        x0, y0, _ = drop_point(D)
        xb, yb = fall_xyz(D, FUNNEL_TOP_Z, omega)
        sizes.append({
            "D_mm": D,
            "drop_xy": (x0, y0),
            "at_funnel_xy": (xb, yb),
            "t_visible_s": (fov_h + D) / v,
        })

    return {
        "omega_rad_s": omega,
        "speed_at_rim_mm_s": v,
        "drift_dir": exit_drift_dir(),
        "view_dir": (vx, vy),
        "view_angle_deg": math.degrees(math.atan2(vy, vx)),
        "axis_z_mm": CAM_AXIS_Z,
        "axis_anchor_xy": (ax, ay),
        "camera_front_xy": (ax - CAM_WD * vx, ay - CAM_WD * vy),
        "backlight_xy": (ax + BL_DIST * vx, ay + BL_DIST * vy),
        "working_distance_mm": CAM_WD,
        "fov_mm": (fov_w, fov_h),
        "fov_z_range": (z_bot, z_top),
        "px_per_mm": px,
        "sees_rim": z_top >= 0.0,
        "funnel_top_z": FUNNEL_TOP_Z,
        "funnel_below_fov": FUNNEL_TOP_Z < z_bot,
        "sizes": sizes,
    }


def stop_slip_mm(t_stop_s: float, omega: float = OMEGA_DISC) -> float:
    """Quãng viên còn tiến thêm khi đĩa giảm tốc tuyến tính về 0."""
    return 0.5 * exit_speed(omega) * float(t_stop_s)


# ---------------------------------------------------------------------------
# Dựng hình
# ---------------------------------------------------------------------------
def _place_view(shape: Part.Shape, x: float, y: float, z: float) -> Part.Shape:
    """Local +x = hướng trục quang; quay quanh Z rồi tịnh tiến."""
    vx, vy = view_dir()
    shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1),
                 math.degrees(math.atan2(vy, vx)))
    shape.translate(App.Vector(x, y, z))
    return shape


def _rect_wire(w: float, h: float, x: float, y: float, z: float) -> Part.Wire:
    hw, hh = 0.5 * w, 0.5 * h
    pts = [
        App.Vector(x - hw, y - hh, z), App.Vector(x + hw, y - hh, z),
        App.Vector(x + hw, y + hh, z), App.Vector(x - hw, y + hh, z),
    ]
    return Part.makePolygon(pts + [pts[0]])


def make_exit_camera() -> Part.Shape:
    """Thân + ống kính (vật mua sẵn — chỉ để kiểm tầm nhìn và va chạm)."""
    bd, bw, bh = CAM_BODY
    body = _box(bd, bw, bh, -CAM_LENS_LEN - bd, -0.5 * bw, -0.5 * bh)
    lens = Part.makeCylinder(0.5 * CAM_LENS_D, CAM_LENS_LEN,
                             App.Vector(-CAM_LENS_LEN, 0, 0), App.Vector(1, 0, 0))
    shape = body.fuse(lens)
    ax, ay = _view_anchor()
    vx, vy = view_dir()
    return _refine(_place_view(shape, ax - CAM_WD * vx, ay - CAM_WD * vy, CAM_AXIS_Z))


def make_backlight_panel() -> Part.Shape:
    """Tấm tán sáng — viên đi qua thành bóng đen trên nền sáng đều."""
    w, h, t = BL_PANEL
    panel = _box(t, w, h, 0.0, -0.5 * w, -0.5 * h)
    ax, ay = _view_anchor()
    vx, vy = view_dir()
    return _refine(_place_view(panel, ax + BL_DIST * vx, ay + BL_DIST * vy, CAM_AXIS_Z))


def _post_to_base(x: float, y: float, z_top: float, top_pad: tuple) -> Part.Shape:
    """Trụ vuông từ đế máy lên tới z_top + bàn đỡ + chân đế."""
    pw, pd = MOUNT_POST
    h = z_top - MOUNT_BASE_Z
    post = _box(pw, pd, h, x - 0.5 * pw, y - 0.5 * pd, MOUNT_BASE_Z)
    foot = _box(pw + 26.0, pd + 26.0, MOUNT_T,
                x - 0.5 * pw - 13.0, y - 0.5 * pd - 13.0, MOUNT_BASE_Z)
    tw, td = top_pad
    pad = _box(tw, td, MOUNT_T, x - 0.5 * tw, y - 0.5 * td, z_top)
    body = post.fuse(foot).fuse(pad)
    holes = [
        (x - 0.5 * pw - 7.0, y), (x + 0.5 * pw + 7.0, y),
        (x, y - 0.5 * pd - 7.0), (x, y + 0.5 * pd + 7.0),
    ]
    body = _cut_m3_z(body, holes, MOUNT_BASE_Z - 1.0, MOUNT_T + 2.0)
    return _refine(body)


def make_camera_mount() -> Part.Shape:
    """Trụ đỡ camera — bàn đỡ ngay dưới thân máy, bắt vít 1/4-20 lên trên."""
    ax, ay = _view_anchor()
    vx, vy = view_dir()
    bd, bw, bh = CAM_BODY
    cx = ax - (CAM_WD + CAM_LENS_LEN + 0.5 * bd) * vx
    cy = ay - (CAM_WD + CAM_LENS_LEN + 0.5 * bd) * vy
    z_top = CAM_AXIS_Z - 0.5 * bh - MOUNT_T
    mount = _post_to_base(cx, cy, z_top, (bd + 10.0, bw + 10.0))
    tripod = _cyl_z(6.4, MOUNT_T + 2.0, cx, cy, z_top - 1.0)  # 1/4"-20 clearance
    return _refine(mount.cut(tripod))


def make_backlight_mount() -> Part.Shape:
    """Trụ đỡ đèn nền, đối diện camera qua mặt phẳng rơi."""
    ax, ay = _view_anchor()
    vx, vy = view_dir()
    w, h, t = BL_PANEL
    bx = ax + (BL_DIST + 0.5 * t) * vx
    by = ay + (BL_DIST + 0.5 * t) * vy
    return _post_to_base(bx, by, CAM_AXIS_Z - 0.5 * h - MOUNT_T, (w * 0.5, 24.0))


def make_collection_funnel() -> Part.Shape:
    """Phễu hứng — miệng dưới khung hình, thu về cửa ra vuông."""
    mx, my = fall_xyz(8.0, FUNNEL_TOP_Z)
    mw, mh = FUNNEL_MOUTH
    ow, oh = FUNNEL_OUT
    outer = Part.makeLoft(
        [_rect_wire(mw, mh, mx, my, FUNNEL_TOP_Z),
         _rect_wire(ow, oh, mx, my, FUNNEL_OUT_Z)], True)
    inner = Part.makeLoft(
        [_rect_wire(mw - 2 * FUNNEL_T, mh - 2 * FUNNEL_T, mx, my, FUNNEL_TOP_Z + 0.01),
         _rect_wire(ow - 2 * FUNNEL_T, oh - 2 * FUNNEL_T, mx, my, FUNNEL_OUT_Z - 0.01)],
        True)
    return _refine(outer.cut(inner))


def build_exit_camera_parts() -> list[tuple]:
    """(name, shape, color) — ghép vào assembly Tube_L_Exit_Gate."""
    return [
        ("Exit_Camera", make_exit_camera(), COLOR_CAM),
        ("Camera_Mount", make_camera_mount(), COLOR_MOUNT),
        ("Backlight_Panel", make_backlight_panel(), COLOR_BL),
        ("Backlight_Mount", make_backlight_mount(), COLOR_MOUNT),
        ("Collection_Funnel", make_collection_funnel(), COLOR_FUNNEL),
    ]
