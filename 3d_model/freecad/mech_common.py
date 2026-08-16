"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Entry_Gate_*        — cửa chỉnh chiều cao ở đầu máng vào (trụ + trượt + barrier)
  Inner_Lane_Rail     — tường liên tục + Reject_Wiper dính đầu (cùng dịch W)
  Entry_Gate_Barrier  — barrier chữ L (trần 20 mm + tấm đứng 10 mm); H 2–26 mm
  Funnel_Guide        — (cũ) → Center_Director: lưỡi cày TÂM đĩa, ép vật ra vành
  Outer_Rim_Funnel    — cánh ngoài thu hẹp vào lane
  Bowl_Tube_Exit_Chute — máng dốc 40° tại 9 giờ, đổ −Y ra Front; cạnh TRÁI của
                        lòng máng trùng mép đĩa (x = −DISC_R), thân máng luồn
                        dưới đĩa để hứng viên vừa rời vành

THAO TÁC CHỈNH (tay với từ trên — giống video):
  W: kéo Inner_Lane_Rail trượt xuyên tâm trên 2 ray T của Chute_Slide
     vào tâm = W↑ | ra vành = W↓ | 1 mm = 1 mm W
  H: nới Screw_Gate_H → nâng/hạ cụm barrier trên ray T đứng ở đầu máng vào
     lên = H↑ | xuống = H↓ | 1 mm = 1 mm H
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

# ---------------------------------------------------------------------------
# Layout (mm). Disc top Z=0. CCW: at +X velocity ≈ +Y.
# Ref: SchanerDesigns rotary table + slotted crossbar + open-bottom guides.
# ---------------------------------------------------------------------------

DISC_D = 200.0
DISC_T = 5.0
DISC_R = 0.5 * DISC_D
HUB_D = 28.0
HUB_H = 10.0
SHAFT_D = 8.0

DISC_RADIAL_CLEAR = 0.8
WALL_T = 4.0
BOWL_ID = DISC_D + 2.0 * DISC_RADIAL_CLEAR
BOWL_OD = BOWL_ID + 2.0 * WALL_T
BOWL_IR = 0.5 * BOWL_ID
BOWL_OR = 0.5 * BOWL_OD
BOWL_H = 40.0
BOWL_Z0 = 0.0

# Đĩa: mặt trên Z=0. Mọi máng/guide đáy HỞ tại GAP0 — KHÔNG chạm đĩa.
DISC_TOP_Z = 0.0
GAP0 = 0.5  # khe đáy mở phía trên mặt đĩa (bắt buộc 0.5 mm)

# Lane → exit trên mặt FreeCAD Front (camera nhìn theo +Y).
# θ_exit = 180° (−X, bên TRÁI màn Front): tiếp tuyến CCW = (0,−1) = đổ RA ngoài về phía người nhìn.
# Lane CCW: miệng vào θ=90° (+Y) → cửa ra θ=180°.
THETA_MOUTH_DEG = 90.0
THETA_EXIT_DEG = 180.0
CHUTE_ARC_DEG = THETA_EXIT_DEG - THETA_MOUTH_DEG
# Inner_Lane_Rail: cung trên vòng DISC_D (Ø20 cm = thành đĩa), 7 giờ → 11 giờ.
INNER_LANE_CLOCK_TH0_DEG = 240.0  # 7 giờ
INNER_LANE_CLOCK_TH1_DEG = 120.0  # 11 giờ
INNER_LANE_ARC_R = DISC_R

W_MAX = 26.0  # họng vào + trượt máng (H chỉnh scraper)
H_MAX = 26.0  # chỉnh H: 2–26 mm
W_MIN = 2.0  # dải chỉnh W: 2–26 mm
H_MIN = 2.0
# Máng lane + exit: rộng cố định, một thành trong cao 30 mm (ngoài = vành bát).
CHUTE_W_MM = 30.0
CHUTE_WALL_H_MM = 30.0
# Outer of free lane = inner face of bowl rim (video: white ring)
CHANNEL_R_OUTER = BOWL_IR
# Máng trượt: 2 thanh T nằm TRÊN Inner_Lane_Rail (8h / 10h), nối thành đĩa.
CHUTE_SLIDE_THETA_DEG = 0.5 * (THETA_MOUTH_DEG + THETA_EXIT_DEG)
CHUTE_SLIDE_RAIL_W = 6.0
CHUTE_SLIDE_RAIL_H = 5.0
CHUTE_SLIDE_HORIZ_LEN = 70.0
CHUTE_SLIDE_T_BODY_Z0 = GAP0 + CHUTE_WALL_H_MM + 11.5  # 42.0 — trên đỉnh máng
CHUTE_SLIDE_T_NECK_W = 4.0
CHUTE_SLIDE_T_NECK_H = 3.2
CHUTE_SLIDE_T_FLANGE_W = 9.0
CHUTE_SLIDE_T_FLANGE_H = 2.4
CHUTE_SLIDE_SHOE_LEN = 18.0
CHUTE_SLIDE_SHOE_FIT = 0.35
CHUTE_SLIDE_RAIL_Z0 = CHUTE_SLIDE_T_BODY_Z0
CHUTE_SLIDE_RAIL_LEN = (W_MAX - W_MIN) + 14.0
CHUTE_SLIDE_R_IN = DISC_R - CHUTE_W_MM - (W_MAX - W_MIN) - 4.0
CHUTE_SLIDE_R_OUT = DISC_R - 1.0
CHUTE_SLIDE_BAR_LEN = 22.0
CHUTE_SLIDE_BAR_W = 4.0
CHUTE_DISC_GUIDE_CLEAR = 0.35
# Cơ cấu W: chỉnh độ hẹp họng đầu vào + vị trí trượt máng.
INLET_DEFLECTOR_ALONG = 14.0
INLET_DEFLECTOR_UPSTREAM = 4.0
INLET_DEFLECTOR_BEVEL_DEG = 38.0
INLET_WING_R_GAP = 0.8
RAIL_T = 3.0
RAIL_H = H_MAX + 10.0  # tường đủ cao hơn H_MAX

TH_ADJ_DEG = THETA_MOUTH_DEG  # tham chiếu cũ (cụm Crossbar 12h đã bỏ)
# M3 printed-part fastener — holes only (never model bolt/nut solids)
M3_CLEAR = 3.6  # ISO 273 medium + FDM margin
M3_HEAD_CB_D = 6.5
M3_HEAD_CB_H = 2.2
M3_NUT_POCKET_AF = 6.0
M3_NUT_POCKET_H = 2.8
M3_BOLT_L = 16.0  # grip ≤ ~12 mm + nut 2.4
HUB_M3_PCD = 18.0
HUB_CLAMP_T = 6.0
SCREW_D = M3_CLEAR  # clamp / assembly holes = M3 clearance
SCRAPER_T = 2.4  # FDM 6 perimeters @ 0.4 mm (was 2.0)
STEM_FIT = 0.25
KNOB_D = 11.0
KNOB_L = 5.0

W_TRAVEL = W_MAX - W_MIN
H_TRAVEL = H_MAX - H_MIN

# ---------------------------------------------------------------------------
# CỬA CHỈNH CHIỀU CAO tại ĐẦU MÁNG (11 giờ) — Entry_Gate_*
# ---------------------------------------------------------------------------
# Thay cụm Crossbar_Bridge / Width_Carriage / Height_Scraper ở 12 giờ (đã bỏ).
#
#   Entry_Gate_Post    — trụ CỐ ĐỊNH bắt vào vành Bowl_Tube tại 11h, mang ray T đứng
#   Entry_Gate_Slider  — con trượt TỊNH TIẾN ĐỨNG ôm ray T + tay với vào trong đĩa
#   Entry_Gate_Barrier — barrier chữ L treo dưới con trượt
#
# Barrier nhìn DỌC DÒNG CHẢY = chữ L: tấm ngang 20 mm làm TRẦN, tấm đứng 10 mm
# dựng LÊN ở mép đón vật. Nhìn từ TRÊN: rộng 30 mm (đúng bề rộng lane), cạnh
# ngoài ôm cung mép đĩa. Khe hở dưới trần = H = chiều cao tối đa vật vào máng.
#
# Vì sao khớp trượt nằm NGOÀI vành bát: mọi thứ cố định treo trong lòng lane mà
# thấp hơn GAP0+H_MAX (26.5) sẽ chặn vật khi mở H lớn. Đưa ray ra ngoài bát, chỉ
# tay với (đi theo con trượt) bắc qua vành ⇒ lane trống suốt dải H 2–26.
# VỊ TRÍ GÓC — vì sao KHÔNG đặt đúng 120°:
#   Inner_Lane_Rail dịch +X theo W (dx = W_MAX − W, tới 24 mm) nên ĐẦU cung rail
#   lùi từ 120° (dx=0) xuống 106.5° (dx=24), và tại 110–131° thân rail nằm ở
#   r = 81–98 mm — tức là NGAY TRONG dải 30 mm của barrier. Tường rail cao 30 mm
#   nên trần barrier (z ≤ GAP0+26) không thể đi qua nó.
#   ⇒ đặt cửa NGAY TRƯỚC đầu rail ở mọi W: mép SAU (hạ lưu) của trần = góc lùi
#   xa nhất của đầu rail trừ biên; trần trải 20 mm ngược dòng. Ở đó mặt đĩa
#   trống suốt 30 mm nên giữ đúng kích thước barrier người dùng yêu cầu.
_RAIL_TIP_R = INNER_LANE_ARC_R - 0.5 * RAIL_T
_RAIL_TIP_X = _RAIL_TIP_R * math.cos(math.radians(INNER_LANE_CLOCK_TH1_DEG)) + (W_MAX - W_MIN)
_RAIL_TIP_Y = _RAIL_TIP_R * math.sin(math.radians(INNER_LANE_CLOCK_TH1_DEG))
_RAIL_TIP_TH_DEG = math.degrees(math.atan2(_RAIL_TIP_Y, _RAIL_TIP_X)) - math.degrees(
    0.5 * RAIL_T / math.hypot(_RAIL_TIP_X, _RAIL_TIP_Y)
)
GATE_MARGIN_DEG = 1.5
GATE_TH_DEG = _RAIL_TIP_TH_DEG - GATE_MARGIN_DEG  # mép SAU của trần (~104°)
GATE_R_OUT = DISC_R - CHUTE_DISC_GUIDE_CLEAR  # cạnh ngoài ôm sát mép đĩa
GATE_W_MM = CHUTE_W_MM  # 30 mm nhìn từ trên
GATE_R_IN = GATE_R_OUT - GATE_W_MM
GATE_ROOF_ALONG_MM = 20.0  # tấm ngang (dọc dòng chảy)
GATE_ROOF_T = SCRAPER_T
GATE_WALL_H_MM = 10.0  # tấm đứng
GATE_WALL_T = SCRAPER_T
GATE_ARM_CLEAR_Z = BOWL_H + 4.0  # bụng tay với tại H_MIN — vượt vành bát
GATE_ARM_T = 8.0
GATE_ARM_W = 12.0
GATE_STEM_W = 10.0  # cột nối trần → tay với: bề radial
GATE_STEM_ALONG = 8.0  # dọc dòng chảy (đế cột đặt trên trần, sau tấm đứng)
GATE_STEM_FOOT_T = 3.0
GATE_RAIL_R0 = BOWL_OR + 0.8  # mặt trong bích ray T (ngoài vành bát)
GATE_RAIL_FLANGE_T = 3.5
GATE_RAIL_FLANGE_W = 16.0
GATE_RAIL_NECK_T = 4.5
GATE_RAIL_NECK_W = 7.0
GATE_RAIL_SPINE_T = 8.0
GATE_RAIL_SPINE_W = 16.0
GATE_COLLAR_H = 14.0
GATE_COLLAR_WALL = 4.0
GATE_FIT = STEM_FIT
GATE_FOOT_Z0 = GAP0 + H_MAX + 0.5  # 27.0 — chân bắt bát, TRÊN vùng vật đi
GATE_FOOT_T = 4.0
GATE_FOOT_W = 20.0
GATE_ROOF_DEG = math.degrees(GATE_ROOF_ALONG_MM / GATE_R_OUT)
# Khung cục bộ của cụm cửa: gốc góc = mép ĐÓN VẬT của trần; local +x = xuyên
# tâm, +y = xuôi dòng (mm cung), +z = lên.
GATE_FRAME_TH_DEG = GATE_TH_DEG - GATE_ROOF_DEG

# Guide_System cố định — xoắn hub→vành; HỌNG LANE mở theo CCW (lực tiếp tuyến)
# Tip Guide DỪNG trước θ_mouth → khe góc + khe bán kính với Bowl = lối vào nhìn thấy
ENTRANCE_W = 26.0  # họng Guide↔Bowl = W_MAX — nhận vật 2–26 mm
# Dung sai "bắt được tường" trong simulate_pill_mechanics (viên phải nằm cách
# tường không quá clear+TOL để coi là chạm). 0.35mm cũ để lại một dải chết hẹp
# ~1.2mm sát trục cho viên rất nhỏ (D=2mm): r0 ∈ [hub-touch, GUIDE_R0-clear)
# không bao giờ được xoắn Guide "vợt" vào — viên quay mãi không thoát (đã phát
# hiện bằng quét toàn dải bán kính, xem verify_recirculation_full_sweep).
# 2.0mm đủ đóng dải chết ở mọi D 2–25mm (đã verify), vẫn nhỏ so R0=20mm nên
# không đổi hành vi bắt/không-bắt ở các vị trí xa tường khác.
WALL_CAPTURE_TOL_MM = 2.0
GUIDE_R0 = 0.5 * HUB_D + 6.0
GUIDE_R1 = CHANNEL_R_OUTER - ENTRANCE_W
GUIDE_TH0 = THETA_MOUTH_DEG - 200.0
GUIDE_TH1 = THETA_MOUTH_DEG - 18.0  # trước miệng — không bịt lối vào
GUIDE_T = 4.5
GUIDE_FLANGE_W = 10.0
GUIDE_FLANGE_T = 3.5
GUIDE_H = H_MAX + 8.0
DIR_CLAMP_S = 0.0
DIR_CLAMP_L = 36.0
DIR_CLAMP_W = 22.0
DIR_CLAMP_H = 14.0
DIR_SCREW_SPAN = 16.0
DIR_STEM = 12.0
DIR_HUB_D = 38.0
_GUIDE_SPAN_R = GUIDE_R1 - GUIDE_R0
_GUIDE_SPAN_TH = GUIDE_TH1 - GUIDE_TH0
_GUIDE_U_MID = 0.38
DIR_R0 = GUIDE_R0
DIR_R1 = GUIDE_R0 + _GUIDE_U_MID * _GUIDE_SPAN_R
DIR_TH0 = GUIDE_TH0
DIR_TH1 = GUIDE_TH0 + _GUIDE_U_MID * _GUIDE_SPAN_TH
DIR_T = GUIDE_T
DIR_FLANGE_W = GUIDE_FLANGE_W
DIR_FLANGE_T = GUIDE_FLANGE_T
DIR_H = GUIDE_H
FUNNEL_R0 = DIR_R1
FUNNEL_R1 = GUIDE_R1
FUNNEL_TH0 = DIR_TH1
FUNNEL_TH1 = GUIDE_TH1
FUNNEL_T = GUIDE_T
FUNNEL_FLANGE_W = GUIDE_FLANGE_W
FUNNEL_FLANGE_T = GUIDE_FLANGE_T
FUNNEL_H = GUIDE_H
FUNNEL_N_FEET = 0
GUIDE_N_FEET = 0
GUIDE_HANDOFF_R = GUIDE_R1 - RAIL_T - 2.0
REJECT_LEN = 8.0  # chỉ bịt khe tip Guide↔rail — không quét đĩa
REJECT_T = RAIL_T
REJECT_ANGLE_DEG = 55.0
REJECT_R_CLEAR = 1.5
# Cửa vào (góc): từ tip Guide → θ_mouth — trống để thấy họng
ENTRANCE_TH0 = GUIDE_TH1
ENTRANCE_TH1 = THETA_MOUTH_DEG + 10.0

# Cuối Inner_Lane_Rail: bóc theo máng. Không hàng rào phía tâm (chặn vật quay vòng vào lane).
EXIT_GUARD_INBOARD = 0.0
EXIT_GUARD_ALONG = 22.0
EXIT_GUARD_T = RAIL_T
EXIT_GUARD_H = RAIL_H
EXIT_PEEL_PAST_RIM = 20.0  # tường trong máng nhô quá mép đĩa (máng ngắn 50 mm)

# Máng thoát ngắn 50 mm (phần nhô ngoài mép đĩa / chiều dài dốc).
EXIT_CHUTE_LEN_MM = 50.0
EXIT_TRACK_LEN = DISC_R + EXIT_CHUTE_LEN_MM  # envelope dựng tường tới chỗ cắt vành + stub
EXIT_TRACK_WALL = 3.0  # FDM chute wall (was 2.5)
# Ma sát thành máng (Coulomb): tường CCW tự hãm nếu tan(β) ≤ μ_wall.
# F_đĩa = F ê_θ; N_tường = F cos β; F_dọc máng = F (sin β − μ cos β).
# Đẩy ra được ⇔ tan β > μ  ⇔  β > arctan(μ).
# PETG in / viên khô: μ_s ≈ 0.30–0.40; lấy 0.35 + biên 5° (tĩnh + nhám lớp in).
MU_WALL = 0.35
MU_DISC = 0.40
EXIT_FRICTION_MARGIN_DEG = 5.0


def exit_wall_friction_beta(
    mu_wall: float = MU_WALL,
    margin_deg: float = EXIT_FRICTION_MARGIN_DEG,
    beta_deg: float | None = None,
) -> dict:
    """β tối thiểu để đĩa đẩy viên dọc máng khi thành máng có ma sát.

    beta_deg=None → trả về β TỐI THIỂU (arctan μ + biên). Truyền beta_deg để
    tính drive_net tại góc máng thực tế đang dùng (EXIT_FROM_RADIAL_DEG).
    """
    beta_lock_deg = math.degrees(math.atan(mu_wall))
    if beta_deg is None:
        beta_deg = beta_lock_deg + float(margin_deg)
    beta_deg = float(beta_deg)
    br = math.radians(beta_deg)
    sin_b, cos_b = math.sin(br), math.cos(br)
    drive_raw = sin_b
    drive_net = sin_b - mu_wall * cos_b
    return {
        "mu_wall": float(mu_wall),
        "mu_disc": MU_DISC,
        "beta_lock_deg": beta_lock_deg,
        "margin_deg": float(margin_deg),
        "beta_deg": beta_deg,
        "drive_raw": drive_raw,
        "drive_net": drive_net,
        "unlock": drive_net > 1e-9 and beta_deg > beta_lock_deg + 1e-9,
        "eq": "F_along = F*(sin(beta)-mu*cos(beta)); tan(beta)>mu",
    }


_EXIT_FRIC = exit_wall_friction_beta()
# Máng ra đi theo phương TIẾP TUYẾN (β = 90° tính từ xuyên tâm) — viên rời lane
# đúng hướng nó đang chạy, không bị bẻ ra ngoài. Ma sát thành: drive_net =
# sin90 − μ·cos90 = 1.0, xa ngưỡng tự hãm arctan(μ)=19.3° nên đĩa luôn đẩy được.
# Đánh đổi: đường tiếp tuyến rời đĩa rất từ từ (r=√(r_lane²+s²)), điểm cắt vành
# chạy từ s≈12 mm (lane hẹp) tới s≈48 mm (lane rộng) — Exit_Ramp có ĐÁY nhận
# viên ngay tại chỗ cắt vành đó nên đường đi sau khi rời đĩa không còn phụ
# thuộc cỡ viên.
EXIT_FROM_RADIAL_DEG = 90.0

# Dốc thoát sau khi rời đĩa: có ĐÁY, nghiêng xuống RAMP_ANGLE_DEG.
# Trượt được ⇔ tan(40°)=0.839 > μ_wall=0.35 (góc tự hãm 19.3°) — dư biên.
#
# ĐẶT MÁNG (quan trọng — trước đây SAI): viên đi tiếp tuyến từ θ_exit nên nó
# luôn ở PHÍA TRONG đường tiếp tuyến x = −DISC_R (x_tâm = −r_lane ≥ −DISC_R),
# rời đĩa khi vành đĩa lùi khỏi nó chứ không bao giờ văng ra ngoài tiếp tuyến.
# Vậy lòng máng phải nằm PHÍA TRONG: cạnh TRÁI (nhìn Front) của lòng máng trùng
# đúng mép đĩa x = −DISC_R, phần còn lại luồn DƯỚI đĩa. Máng cũ nằm hẳn ngoài
# tiếp tuyến (x ∈ [−130, −103]) nên không hứng được viên nào.
RAMP_ANGLE_DEG = 40.0
RAMP_FLOOR_T = 3.0
RAMP_WALL_T = 3.0
RAMP_DISC_GAP = 1.0  # khe đáy đĩa → mặt máng (đĩa quay, máng đứng yên)
RAMP_CATCH_MARGIN = 8.0  # phủ thêm sau điểm rời đĩa xa nhất (lane rộng nhất)
RAMP_START_DROP = 0.0
RAMP_SIDE_CLEAR = 0.6
RAMP_TAKEOVER_OVERLAP = 6.0  # máng phẳng chồng đầu dốc chừng này rồi mới hết

# Mức chồng CỐ Ý giữa Inner_Lane_Rail và Exit_Track tại mối nối (seal key +
# rail bám đường máng). Đo được ~2850–3010 mm³ ở cả β=24.29° lẫn β=90°.
RAIL_EXIT_SHARED_MAX = 3600.0
# Máng ra = khẩu độ chỉnh (W×H); khi set pill: W=D+1, H=T+1
# EXIT_TRACK_W giữ alias legacy — kích thước thật của máng = CHUTE_W_MM
EXIT_TRACK_W = CHUTE_W_MM
# Mép vào máng sát mặt phẳng θ_exit của lane (không lệch ra BOWL_OR)
EXIT_X0_ALONG = 0.0
# Nối lane → máng ra: Hermite G1 (không góc gãy a2/b2)
JOIN_BLEND_S = 20.0
JOIN_HANDLE_FRAC = 0.40
JOIN_N = 28
JOIN_MAX_TURN_DEG = 45.0  # cũ a2/b2 ~90°; nối mới <45°/mẫu
JOIN_BLEND_TH0 = THETA_EXIT_DEG - 12.0
JOIN_SEAL_OVERLAP_MM = 8.0  # rail xuyên miệng chồng Exit_Track
JOIN_MAX_GAP_MM = 0.35  # không khe hở vách W ↔ máng ra

WIDTH_MIN, WIDTH_MAX = W_MIN, W_MAX
HEIGHT_MIN, HEIGHT_MAX = H_MIN, H_MAX

# Máng / khe: rộng hơn và cao hơn vật đúng 1 mm
PILL_CLEAR_XY = 1.0
PILL_CLEAR_Z = 1.0

PILL_DATASETS: list[dict] = [
    {"id": "tiny_5x2.5", "D": 5.0, "T": 2.5, "shape": "tablet"},
    {"id": "small_6x3", "D": 6.0, "T": 3.0, "shape": "tablet"},
    {"id": "medium_8x4", "D": 8.0, "T": 4.0, "shape": "tablet"},
    {"id": "large_10x5", "D": 10.0, "T": 5.0, "shape": "tablet"},
    {"id": "xl_12x6", "D": 12.0, "T": 6.0, "shape": "tablet"},
    {"id": "softgel_9", "D": 9.0, "T": 9.0, "shape": "ball"},
    {"id": "caplet_eq_7x4", "D": 7.0, "T": 4.0, "shape": "tablet"},
    {"id": "thick_8x7", "D": 8.0, "T": 7.0, "shape": "tablet"},
    {"id": "mini_4x2", "D": 4.0, "T": 2.0, "shape": "tablet"},
    {"id": "oblong_11x5", "D": 11.0, "T": 5.0, "shape": "tablet"},
    {"id": "softgel_7", "D": 7.0, "T": 7.0, "shape": "ball"},
    {"id": "flat_9x3", "D": 9.0, "T": 3.0, "shape": "tablet"},
]

COLORS = {
    "disc": (0.22, 0.22, 0.24),
    "bowl": (0.92, 0.92, 0.94),
    "bar": (0.72, 0.74, 0.78),
    "clamp": (0.18, 0.18, 0.22),
    "slide": (0.45, 0.48, 0.55),
    "rail": (0.85, 0.55, 0.20),
    "height": (0.30, 0.55, 0.90),
    "funnel": (0.30, 0.52, 0.62),
    "director": (0.30, 0.52, 0.62),
    "guide": (0.30, 0.52, 0.62),
    "reject": (0.90, 0.25, 0.25),
    "exit": (0.12, 0.12, 0.12),
    "mouth": (0.95, 0.25, 0.55),
    "screw": (0.35, 0.35, 0.38),
}


def _refine(shape: Part.Shape) -> Part.Shape:
    try:
        out = shape.removeSplitter()
        return shape if out is None or out.isNull() else out
    except Exception:
        return shape


def _shape_ok(shape: Part.Shape, min_vol: float = 2.0) -> bool:
    try:
        if shape is None or shape.isNull():
            return False
        return float(getattr(shape, "Volume", 0.0) or 0.0) >= min_vol
    except Exception:
        return False


def _box(dx, dy, dz, x0, y0, z0) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def _cyl_z(d, h, x=0.0, y=0.0, z0=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _unit3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.hypot(v[0], v[1], v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cyl_axis(d: float, h: float, origin, axis) -> Part.Shape:
    o = App.Vector(float(origin[0]), float(origin[1]), float(origin[2]))
    a = _unit3(axis)
    return Part.makeCylinder(d / 2.0, h, o, App.Vector(a[0], a[1], a[2]))


def hub_m3_xy() -> list[tuple[float, float]]:
    r = 0.5 * HUB_M3_PCD
    out = []
    for i in range(4):
        a = math.radians(45.0 + i * 90.0)
        out.append((r * math.cos(a), r * math.sin(a)))
    return out


def _m3_nut_pocket_z(x: float, y: float, z_bottom: float) -> Part.Shape:
    af = M3_NUT_POCKET_AF
    box = Part.makeBox(af, af, M3_NUT_POCKET_H + 0.2)
    box.translate(App.Vector(x - af / 2.0, y - af / 2.0, z_bottom - 0.1))
    return box


def _m3_cbore_z(x: float, y: float, z_top: float) -> Part.Shape:
    c = Part.makeCylinder(M3_HEAD_CB_D / 2.0, M3_HEAD_CB_H + 0.2)
    c.translate(App.Vector(x, y, z_top - M3_HEAD_CB_H - 0.2))
    return c


def _cut_m3_z(
    shape: Part.Shape,
    xy: list[tuple[float, float]],
    z0: float,
    h: float,
    *,
    cbore_top: float | None = None,
    nut_bottom: float | None = None,
) -> Part.Shape:
    out = shape
    for x, y in xy:
        try:
            nxt = out.cut(_cyl_z(M3_CLEAR, h, x, y, z0))
            if nxt is not None and getattr(nxt, "Solids", None):
                out = nxt
        except Exception:
            continue
        if cbore_top is not None:
            try:
                nxt = out.cut(_m3_cbore_z(x, y, cbore_top))
                if nxt is not None and getattr(nxt, "Solids", None):
                    out = nxt
            except Exception:
                pass
        if nut_bottom is not None:
            try:
                nxt = out.cut(_m3_nut_pocket_z(x, y, nut_bottom))
                if nxt is not None and getattr(nxt, "Solids", None):
                    out = nxt
            except Exception:
                pass
    return out


def guide_mount_sites() -> list[dict]:
    """Radial M3 through Guide feet into Bowl_Tube (above H_MAX)."""
    mount_z0 = GAP0 + H_MAX + 2.0
    mount_h = (GAP0 + GUIDE_H) - mount_z0
    z = mount_z0 + 0.5 * max(2.0, mount_h)
    out = []
    for u_ft in (0.30, 0.70):
        th_ft = GUIDE_TH0 + (GUIDE_TH1 - GUIDE_TH0) * u_ft
        r_wall = GUIDE_R0 + (GUIDE_R1 - GUIDE_R0) * u_ft
        c, s = math.cos(_deg2rad(th_ft)), math.sin(_deg2rad(th_ft))
        r0 = r_wall - 2.0
        out.append(
            {
                "origin": (r0 * c, r0 * s, z),
                "axis": (c, s, 0.0),
                "h": (BOWL_OR - r0) + 6.0,
                "th_deg": th_ft,
            }
        )
    return out


def _cut_m3_sites(shape: Part.Shape, sites: list[dict]) -> Part.Shape:
    out = shape
    for site in sites:
        try:
            nxt = out.cut(_cyl_axis(M3_CLEAR, float(site["h"]), site["origin"], site["axis"]))
            if nxt is not None and getattr(nxt, "Solids", None):
                out = nxt
        except Exception:
            continue
    return out


def hole_is_empty(shape: Part.Shape, x: float, y: float, z: float, tol: float = 0.5) -> bool:
    if shape is None or not getattr(shape, "Solids", None):
        return False
    try:
        return not bool(shape.isInside(App.Vector(x, y, z), tol, True))
    except Exception:
        return False


def _knob_bolt_along(origin, axis, shank_len: float) -> Part.Shape:
    """Bu-lông núm vặn lớn: núm (KNOB_D×KNOB_L) tại origin, thân ren (SCREW_D) dài
    shank_len tiếp theo cùng huống axis — dùng cho ca kep W va H (thay lo xo)."""
    ax = _unit3(axis)
    knob = _cyl_axis(KNOB_D, KNOB_L, origin, ax)
    shank_origin = (
        origin[0] + KNOB_L * ax[0],
        origin[1] + KNOB_L * ax[1],
        origin[2] + KNOB_L * ax[2],
    )
    shank = _cyl_axis(SCREW_D, shank_len, shank_origin, ax)
    return _refine(knob.fuse(shank))


def gate_mount_sites() -> list[dict]:
    """2 bu-lông M3 xuyên tâm bắt chân Entry_Gate_Post vào vành Bowl_Tube tại 11h.

    Đặt CAO hơn GAP0+H_MAX để lỗ xuyên vành không thành đường vật lọt ra."""
    out = []
    th = GATE_TH_DEG - 0.5 * GATE_ROOF_DEG  # giữa cửa
    c, s_ = math.cos(_deg2rad(th)), math.sin(_deg2rad(th))
    r0 = BOWL_IR - 2.0
    for z in (GATE_FOOT_Z0 + 4.0, GATE_FOOT_Z0 + 11.0):
        out.append({
            "origin": (r0 * c, r0 * s_, z),
            "axis": (c, s_, 0.0),
            "h": (GATE_RAIL_R0 + GATE_FOOT_T + 4.0) - r0,
            "th_deg": th,
            "z": z,
        })
    return out


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _deg2rad(d: float) -> float:
    return d * math.pi / 180.0


def _annular_sector(
    r_in: float,
    r_out: float,
    th0_deg: float,
    th1_deg: float,
    z0: float,
    h: float,
    n: int = 36,
) -> Part.Shape:
    if r_out <= r_in + 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    th0, th1 = _deg2rad(th0_deg), _deg2rad(th1_deg)
    if th1 < th0:
        th0, th1 = th1, th0
    n = max(8, int(n))
    pts_out, pts_in = [], []
    for i in range(n + 1):
        t = th0 + (th1 - th0) * (i / n)
        pts_out.append(App.Vector(r_out * math.cos(t), r_out * math.sin(t), z0))
        pts_in.append(App.Vector(r_in * math.cos(t), r_in * math.sin(t), z0))
    wire = pts_out + list(reversed(pts_in))
    wire.append(wire[0])
    face = Part.Face(Part.makePolygon(wire))
    return _refine(face.extrude(App.Vector(0, 0, h)))


def _place_oriented_box(
    length, thick, height, cx, cy, z0, heading_deg
) -> Part.Shape:
    b = _box(length, thick, height, -0.5 * length, -0.5 * thick, z0)
    b.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading_deg)
    b.translate(App.Vector(cx, cy, 0))
    return _refine(b)


def exit_tangent_pose(width_open: float, height_open: float) -> dict:
    """
    Cửa ra: neo tại tâm lane; hướng GẦN XUYÊN TÂM + lệch CCW β.
    β = arctan(μ_wall) + biên — đủ lớn để F_dọc = F(sinβ − μ cosβ) > 0
    (thành máng ma sát không tự hãm; đĩa chậm vẫn đẩy). Đáy hở tới r > DISC_R.
    """
    ap = chute_slide_aperture(width_open)
    th_deg = THETA_EXIT_DEG
    th = _deg2rad(th_deg)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    r_anchor = r_lane
    tx, ty = -math.sin(th), math.cos(th)
    nx, ny = math.cos(th), math.sin(th)
    fric = exit_wall_friction_beta(beta_deg=EXIT_FROM_RADIAL_DEG)
    beta = fric["beta_deg"]
    heading = th_deg + beta  # 0=radial out, 90=tangent CCW
    hx, hy = math.cos(_deg2rad(heading)), math.sin(_deg2rad(heading))
    x0_along = EXIT_X0_ALONG
    return {
        "theta_deg": th_deg,
        "heading_tangent_deg": heading,
        "heading_chute_deg": heading,
        "from_radial_deg": beta,
        "r_center_mm": r_anchor,
        "r_lane_mm": r_lane,
        "r_anchor_mm": r_anchor,
        "x0_along_mm": x0_along,
        "anchor_xy": (r_anchor * math.cos(th), r_anchor * math.sin(th)),
        "lane_center_xy": (r_lane * math.cos(th), r_lane * math.sin(th)),
        "tangent": (tx, ty),
        "radial_out": (nx, ny),
        "chute_dir": (hx, hy),
        "drive_along_chute": fric["drive_raw"],
        "drive_net_friction": fric["drive_net"],
        "mu_wall": fric["mu_wall"],
        "mu_disc": fric["mu_disc"],
        "beta_lock_deg": fric["beta_lock_deg"],
        "friction_unlock": fric["unlock"],
        "exit_track_w_mm": ap["width_mm"],
        "W": ap["width_mm"],
        "H": ap["height_mm"],
        "matched_to_lane": abs(r_anchor - r_lane) < 1e-9,
        "flush_to_lane": abs(x0_along) < 1e-9,
        "open_bottom_on_disc": True,
    }


def _place_tangent_exit(shape: Part.Shape, width_open: float, height_open: float) -> Part.Shape:
    pose = exit_tangent_pose(width_open, height_open)
    ax, ay = pose["anchor_xy"]
    shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), pose["heading_tangent_deg"])
    shape.translate(App.Vector(ax, ay, 0))
    return _refine(shape)


def chute_slide_aperture(width_open: float) -> dict:
    """Máng 30 mm trượt: 1 ray bát (trong) + mép đĩa DISC_R (ngoài)."""
    w_cmd = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    slide = W_MAX - w_cmd
    r_disc = DISC_R - CHUTE_DISC_GUIDE_CLEAR
    r_outer = r_disc
    r_inner = r_outer - CHUTE_W_MM - slide
    h = CHUTE_WALL_H_MM
    return {
        "width_mm": CHUTE_W_MM,
        "width_cmd_mm": w_cmd,
        "slide_mm": slide,
        "height_mm": h,
        "r_inner": r_inner,
        "r_outer": r_outer,
        "disc_guide_r_mm": r_disc,
        "z0": GAP0,
        "z1": GAP0 + h,
        "theta_mouth_deg": THETA_MOUTH_DEG,
        "theta_exit_deg": THETA_EXIT_DEG,
        "arc_deg": CHUTE_ARC_DEG,
        "slide_theta_deg": CHUTE_SLIDE_THETA_DEG,
    }


def chute_aperture(width_open: float | None = None) -> dict:
    """Máng lane + exit. Truyền width_open để lấy vị trí trượt; None = W_MAX."""
    if width_open is None:
        return chute_slide_aperture(W_MAX)
    return chute_slide_aperture(width_open)


def aperture_from_opens(width_open: float, height_open: float) -> dict:
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    r_outer = CHANNEL_R_OUTER
    r_inner = r_outer - w
    return {
        "width_mm": w,
        "height_mm": h,
        "r_inner": r_inner,
        "r_outer": r_outer,
        "z0": GAP0,
        "z1": GAP0 + h,
        "theta_mouth_deg": THETA_MOUTH_DEG,
        "theta_exit_deg": THETA_EXIT_DEG,
        "arc_deg": CHUTE_ARC_DEG,
    }


def _radial_slide_bar(
    r0: float, r1: float, th_deg: float, z0: float, h: float, thick: float,
) -> Part.Shape:
    r_lo, r_hi = min(r0, r1), max(r0, r1)
    ln = r_hi - r_lo
    if ln < 1.0:
        return Part.Shape()
    r_mid = 0.5 * (r_lo + r_hi)
    return _place_oriented_box(
        ln, thick, h,
        r_mid * math.cos(_deg2rad(th_deg)),
        r_mid * math.sin(_deg2rad(th_deg)),
        z0, th_deg,
    )


def chute_slide_rail_specs() -> dict:
    """Hai thanh T treo trên Inner_Lane_Rail; máng trượt bằng 2 con trượt."""
    z_flange = CHUTE_SLIDE_T_BODY_Z0 - CHUTE_SLIDE_T_NECK_H - CHUTE_SLIDE_T_FLANGE_H
    return {
        "clock_8h_deg": 210.0,
        "clock_10h_deg": 150.0,
        "r_mm": DISC_R,
        "length_mm": CHUTE_SLIDE_HORIZ_LEN,
        "z0_mm": z_flange,
        "z_body_mm": CHUTE_SLIDE_T_BODY_Z0,
        "rail_w_mm": CHUTE_SLIDE_RAIL_W,
        "t_flange_w_mm": CHUTE_SLIDE_T_FLANGE_W,
        "above_lane_mm": round(z_flange - (GAP0 + CHUTE_WALL_H_MM), 2),
        "disc_guide_r_mm": DISC_R,
        "travel_mm": W_TRAVEL,
        "rail_count": 2,
        "axis": "+X T-rail over Inner_Lane_Rail",
    }


def inner_lane_slide_x(width_open: float) -> float:
    """Dịch Inner_Lane_Rail dọc +X trên 2 thanh T (W↓ → vào tâm)."""
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    return W_MAX - w


def make_bowl_chute_slide_rail() -> Part.Shape:
    """1 thanh ray radial gắn cố định vào thành bát (máng trượt phía trong)."""
    th = CHUTE_SLIDE_THETA_DEG
    body = _radial_slide_bar(
        CHUTE_SLIDE_R_IN, CHUTE_SLIDE_R_OUT, th,
        CHUTE_SLIDE_RAIL_Z0, CHUTE_SLIDE_RAIL_H, CHUTE_SLIDE_RAIL_W,
    )
    return _refine(_enforce_disc_clearance(body))


def make_bowl_chute_slide_rails() -> Part.Shape:
    """Alias — chỉ 1 thanh trên Bowl_Tube."""
    return make_bowl_chute_slide_rail()


def make_chute_disc_guide(width_open: float) -> Part.Shape:
    """Vách ngoài máng bám mép đĩa (r = DISC_R) — giữ cho verify cũ."""
    ap = chute_slide_aperture(width_open)
    th0 = THETA_MOUTH_DEG - 1.0
    th1 = THETA_EXIT_DEG + 10.0
    r_out = DISC_R + 0.15
    r_in = ap["r_outer"] - RAIL_T - 0.5
    if r_out <= r_in + 0.4:
        return Part.Shape()
    h = min(CHUTE_WALL_H_MM - 2.0, 24.0)
    shoe = _annular_sector(r_in, r_out, th0, th1, GAP0, h, n=22)
    return _refine(_enforce_disc_clearance(shoe))


def make_chute_slide_bar_at_clock(th_deg: float) -> Part.Shape:
    """Thanh T treo (nằm trên máng): thân + cổ + bích, đế cao ôm thành đĩa."""
    th = _deg2rad(th_deg)
    x_rim = DISC_R * math.cos(th)
    y_rim = DISC_R * math.sin(th)
    ln = CHUTE_SLIDE_HORIZ_LEN
    cx = x_rim + 0.5 * ln
    z_body = CHUTE_SLIDE_T_BODY_Z0
    body_h = CHUTE_SLIDE_RAIL_H
    z_neck = z_body - CHUTE_SLIDE_T_NECK_H
    z_flange = z_neck - CHUTE_SLIDE_T_FLANGE_H
    body = _place_oriented_box(ln, CHUTE_SLIDE_RAIL_W, body_h, cx, y_rim, z_body, 0.0)
    neck = _place_oriented_box(
        ln, CHUTE_SLIDE_T_NECK_W, CHUTE_SLIDE_T_NECK_H, cx, y_rim, z_neck, 0.0,
    )
    flange = _place_oriented_box(
        ln, CHUTE_SLIDE_T_FLANGE_W, CHUTE_SLIDE_T_FLANGE_H, cx, y_rim, z_flange, 0.0,
    )
    pad = _annular_sector(
        DISC_R - 7.0, DISC_R + 0.12,
        th_deg - 7.0, th_deg + 7.0,
        z_flange, (z_body + body_h) - z_flange, n=16,
    )
    body_all = body
    for extra in (neck, flange, pad):
        try:
            fused = body_all.fuse(extra)
            if _shape_ok(fused, 0.5 * float(getattr(body_all, "Volume", 1.0) or 1.0)):
                body_all = fused
        except Exception:
            continue
    return _refine(_enforce_disc_clearance(body_all))


def make_chute_slide_shoe_at_clock(th_deg: float) -> Part.Shape:
    """Con trượt T-slot ôm bích treo — gắn lên Inner_Lane_Rail tại 8h/10h."""
    th = _deg2rad(th_deg)
    x_rim = DISC_R * math.cos(th)
    y_rim = DISC_R * math.sin(th)
    z_lane_top = GAP0 + CHUTE_WALL_H_MM
    z_neck = CHUTE_SLIDE_T_BODY_Z0 - CHUTE_SLIDE_T_NECK_H
    z_flange = z_neck - CHUTE_SLIDE_T_FLANGE_H
    fit = CHUTE_SLIDE_SHOE_FIT
    shoe_len = CHUTE_SLIDE_SHOE_LEN
    shoe_w = CHUTE_SLIDE_T_FLANGE_W + 4.0
    # Đế + thành U từ đỉnh máng lên ôm bích T (khe FIT, trượt dọc +X).
    z0 = z_lane_top - 0.4
    h_total = (z_neck + 0.6) - z0
    cx = x_rim + 0.5 * shoe_len
    outer = _place_oriented_box(shoe_len, shoe_w, h_total, cx, y_rim, z0, 0.0)
    pocket = _place_oriented_box(
        shoe_len + 2.0,
        CHUTE_SLIDE_T_FLANGE_W + 2.0 * fit,
        CHUTE_SLIDE_T_FLANGE_H + 2.0 * fit,
        cx, y_rim, z_flange - fit, 0.0,
    )
    neck_cut = _place_oriented_box(
        shoe_len + 2.0,
        CHUTE_SLIDE_T_NECK_W + 2.0 * fit,
        CHUTE_SLIDE_T_NECK_H + 8.0,
        cx, y_rim, z_neck - fit, 0.0,
    )
    try:
        shoe = outer.cut(pocket).cut(neck_cut)
    except Exception:
        shoe = outer
    stem = _place_oriented_box(
        8.0, RAIL_T + 1.0, max(2.0, z0 + 2.0 - (z_lane_top - 2.0)),
        x_rim + 0.5 * shoe_len, y_rim, z_lane_top - 2.0, 0.0,
    )
    try:
        fused = shoe.fuse(stem)
        if _shape_ok(fused, 0.4 * float(getattr(shoe, "Volume", 1.0) or 1.0)):
            shoe = fused
    except Exception:
        pass
    return _refine(_enforce_disc_clearance(shoe))


def make_chute_slide_bars(width_open: float | None = None) -> Part.Shape:
    """2 thanh ngang cố định: 8 giờ + 10 giờ, nối thành đĩa (component Chute_Slide)."""
    _ = width_open
    a = make_chute_slide_bar_at_clock(210.0)
    b = make_chute_slide_bar_at_clock(150.0)
    try:
        fused = a.fuse(b)
        if _shape_ok(fused, 0.5 * (float(a.Volume) + float(b.Volume))):
            return _refine(fused)
    except Exception:
        pass
    return _refine(a)


def inlet_throat_params(width_open: float) -> dict:
    """Họng đầu vào — W chỉnh độ hẹp; máng trượt CHUTE_W_MM trên ray bát."""
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    ap = chute_slide_aperture(width_open)
    r_c = 0.5 * (ap["r_inner"] + ap["r_outer"])
    half = 0.5 * w
    return {
        "throat_w_mm": w,
        "r_center_mm": r_c,
        "r_in_mm": r_c - half,
        "r_out_mm": r_c + half,
        "r_lane_in": ap["r_inner"],
        "r_lane_out": ap["r_outer"],
        "lane_w_mm": CHUTE_W_MM,
        "theta_mouth_deg": THETA_MOUTH_DEG,
    }


def height_scraper_z(height_open: float) -> float:
    """Bottom face Z of height scraper."""
    return GAP0 + _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)


def entry_gate_geo(height_open: float) -> dict:
    """Toạ độ then chốt của cụm cửa chỉnh chiều cao 11h (nguồn sự thật cho CAD
    lẫn verify). H = khe hở dưới TRẦN barrier = chiều cao vật lọt vào máng."""
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    z_roof0 = height_scraper_z(h)  # đáy trần
    z_roof1 = z_roof0 + GATE_ROOF_T
    z_wall1 = z_roof1 + GATE_WALL_H_MM
    # Cột nối dài CỐ ĐỊNH: chọn theo H_MIN để bụng tay với luôn vượt vành bát.
    stem_len = GATE_ARM_CLEAR_Z - (height_scraper_z(HEIGHT_MIN) + GATE_ROOF_T)
    z_arm0 = z_roof1 + stem_len
    r_mid = 0.5 * (GATE_R_IN + GATE_R_OUT)
    d_roof = math.degrees(GATE_ROOF_ALONG_MM / GATE_R_OUT)
    d_wall = math.degrees(GATE_WALL_T / GATE_R_OUT)
    d_stem = math.degrees(GATE_STEM_ALONG / GATE_R_OUT)
    th1 = GATE_TH_DEG            # mép SAU (hạ lưu) — sát đầu Inner_Lane_Rail
    th0 = th1 - d_roof           # mép ĐÓN vật (thượng lưu) — chỗ tấm đứng
    return {
        "H": h,
        "th_gate_deg": GATE_TH_DEG,
        "th_roof0_deg": th0,
        "th_roof1_deg": th1,
        "th_wall1_deg": th0 + d_wall,
        "th_stem0_deg": th0 + d_wall,
        "th_stem1_deg": th0 + d_wall + d_stem,
        "th_center_deg": 0.5 * (th0 + th1),
        "rail_tip_min_deg": _RAIL_TIP_TH_DEG,
        "r_in_mm": GATE_R_IN,
        "r_out_mm": GATE_R_OUT,
        "r_mid_mm": r_mid,
        "top_view_w_mm": GATE_W_MM,
        "roof_along_mm": GATE_ROOF_ALONG_MM,
        "roof_deg": d_roof,
        "wall_deg": d_wall,
        "stem_deg": d_stem,
        "z_roof0_mm": z_roof0,
        "z_roof1_mm": z_roof1,
        "z_wall1_mm": z_wall1,
        "z_arm0_mm": z_arm0,
        "z_arm1_mm": z_arm0 + GATE_ARM_T,
        "z_collar0_mm": z_arm0 - 0.5 * (GATE_COLLAR_H - GATE_ARM_T),
        "z_collar1_mm": z_arm0 + 0.5 * (GATE_COLLAR_H + GATE_ARM_T),
        "stem_len_mm": stem_len,
        "travel_mm": H_TRAVEL,
        "clear_h_mm": z_roof0 - DISC_TOP_Z,
        "eq_H": "H = z_roof0 - GAP0 (khe dưới trần)",
        "check_H_from_z": abs((z_roof0 - GAP0) - h) < 1e-9,
        "check_outer_edge_on_rim": abs(GATE_R_OUT - (DISC_R - CHUTE_DISC_GUIDE_CLEAR)) < 1e-9,
        "check_top_view_w": abs((GATE_R_OUT - GATE_R_IN) - GATE_W_MM) < 1e-9,
        "collar_above_bowl": (z_arm0 - 0.5 * (GATE_COLLAR_H - GATE_ARM_T)) > BOWL_Z0 + BOWL_H,
    }


def adjust_pose_math(width_open: float, height_open: float) -> dict:
    """Closed-form pose — nguồn sự thật cho CAD + verify.

    W: kéo Inner_Lane_Rail xuyên tâm trên 2 ray T của Chute_Slide (1 mm = 1 mm).
    H: hạ/nâng Entry_Gate_Slider trên ray T đứng ở 11h (1 mm = 1 mm)."""
    ap = chute_slide_aperture(width_open)
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    g = entry_gate_geo(h)
    s = inner_lane_slide_x(w)
    z1 = g["z_roof0_mm"]
    return {
        "W": w,
        "H": h,
        "lane_w_mm": ap["width_mm"],
        "chute_slide_mm": ap["slide_mm"],
        "s_mm": round(s, 6),
        "r_inner_mm": ap["r_inner"],
        "r_outer_mm": ap["r_outer"],
        "z_gate_roof_mm": round(z1, 6),
        "z_gate_arm_mm": round(g["z_arm0_mm"], 6),
        "theta_gate_deg": GATE_TH_DEG,
        "eq_W": "s = W_MAX - W (rail truot tren ray T Chute_Slide)",
        "eq_H": "H = z_roof0 - GAP0 (khe duoi tran barrier)",
        "check_W_from_s": abs((W_MAX - s) - w) < 1e-9,
        "check_H_from_z": abs((z1 - GAP0) - h) < 1e-9,
        "check_chute_slides": abs(ap["slide_mm"] - (W_MAX - w)) < 1e-9,
    }


def mouth_geometry() -> dict:
    th_m = _deg2rad(THETA_MOUTH_DEG)
    r_m = CHANNEL_R_OUTER - 0.5 * W_MAX
    tx_m, ty_m = -math.sin(th_m), math.cos(th_m)
    nx_m, ny_m = math.cos(th_m), math.sin(th_m)
    ex = exit_tangent_pose(W_MAX, H_MAX)
    tx, ty = ex["tangent"]
    nx, ny = ex["radial_out"]
    # exit local +X after rotate(heading) = chute axis (near radial)
    h = _deg2rad(ex["heading_tangent_deg"])
    exit_dir = (math.cos(h), math.sin(h))
    dot_t = exit_dir[0] * tx + exit_dir[1] * ty
    dot_r = exit_dir[0] * nx + exit_dir[1] * ny
    ang_vs_radial_deg = abs(math.degrees(math.atan2(dot_t, dot_r)))
    return {
        "mouth_xy_mm": (round(r_m * math.cos(th_m), 3), round(r_m * math.sin(th_m), 3)),
        "tangent_flow": (round(tx_m, 5), round(ty_m, 5)),
        "radial_out": (round(nx_m, 5), round(ny_m, 5)),
        "mouth_open_vs_flow_deg": 0.0,
        "bad_perpendicular_mouth_deg": 90.0,
        "mouth_is_along_flow": True,
        "entrance_throat": {
            "width_mm": ENTRANCE_W,
            "r_inner_guide_mm": GUIDE_R1,
            "r_outer_bowl_mm": CHANNEL_R_OUTER,
            "theta_open_deg": [ENTRANCE_TH0, ENTRANCE_TH1],
            "opens_into_ccw_flow": True,
            "guide_fixed": True,
            "guide_stops_before_mouth": GUIDE_TH1 < THETA_MOUTH_DEG - 5.0,
            "force_model": "tangential_only_on_disc",
            "visible_gap_mm": round(CHANNEL_R_OUTER - GUIDE_R1, 2),
        },
        "exit_tangent": {
            "theta_exit_deg": THETA_EXIT_DEG,
            "heading_deg": ex["heading_tangent_deg"],
            "from_radial_deg": round(EXIT_FROM_RADIAL_DEG, 3),
            "mu_wall": ex["mu_wall"],
            "mu_disc": ex["mu_disc"],
            "beta_lock_deg": round(ex["beta_lock_deg"], 3),
            "drive_raw": round(ex["drive_along_chute"], 6),
            "drive_net_friction": round(ex["drive_net_friction"], 6),
            "wall_friction_unlock": bool(ex["friction_unlock"]),
            "anchor_xy": (round(ex["anchor_xy"][0], 3), round(ex["anchor_xy"][1], 3)),
            "exit_dir": (round(exit_dir[0], 5), round(exit_dir[1], 5)),
            "tangent": (round(tx, 5), round(ty, 5)),
            "dot_exit_tangent": round(dot_t, 6),
            "dot_exit_radial": round(dot_r, 6),
            "angle_vs_radial_deg": round(ang_vs_radial_deg, 3),
            "nearly_radial": (
                dot_r > 0.88
                and ang_vs_radial_deg <= EXIT_FROM_RADIAL_DEG + 0.5
            ),
            "aligned_with_tangent": False,
            "slow_omega_drive": bool(ex["friction_unlock"]) and float(ex["drive_net_friction"]) > 0.05,
            "flows_toward_front_left": exit_dir[0] < -0.82,
            "mouth_on_front_left": ex["anchor_xy"][0] < -0.5 * BOWL_OR and abs(ex["anchor_xy"][1]) < 0.35 * BOWL_OR,
            "open_bottom_until_off_disc": True,
            "view_note": (
                f"θ_exit=180°; máng lệch CCW {EXIT_FROM_RADIAL_DEG:.1f}° "
                f"(β>arctan(μ={MU_WALL:g})={ex['beta_lock_deg']:.1f}°) để thắng ma sát thành"
            ),
        },
        "rotation": "CCW",
        "ref": "SchanerDesigns shorts ju5vIg66NNk",
    }


def _enforce_disc_clearance(shape: Part.Shape, z_min: float = GAP0) -> Part.Shape:
    """Cắt mọi vật liệu z < z_min — máng/guide không tiếp xúc mặt đĩa (z=0)."""
    if shape is None or getattr(shape, "isNull", lambda: True)():
        return shape
    cutter = _box(500.0, 500.0, z_min + 80.0, -250.0, -250.0, -80.0)
    try:
        cut = shape.cut(cutter)
        if _shape_ok(cut, 0.5):
            return cut
    except Exception:
        pass
    return shape


def _to_gate_frame(shape: Part.Shape) -> Part.Shape:
    """Local: +x = xuyên tâm, +y = xuôi dòng (CCW) → đặt về mép đón vật của cửa."""
    shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), GATE_FRAME_TH_DEG)
    return _refine(shape)


# Cửa bát: chỉ hở đúng quỹ đạo máng thoát (θ_exit + peel), thành còn lại liền quanh đĩa.
# BEFORE nhỏ để θ≈179° vẫn có thành (lane_outer); AFTER đủ W_MAX xuyên vành.
BOWL_SLOT_BEFORE_EXIT_DEG = 0.8
_R_LANE_WMAX = CHANNEL_R_OUTER - 0.5 * CHUTE_W_MM
_S_BOWL_EXIT = math.sqrt(max(0.0, BOWL_OR ** 2 - _R_LANE_WMAX ** 2))
BOWL_SLOT_AFTER_EXIT_DEG = math.degrees(math.atan2(_S_BOWL_EXIT, max(1.0, _R_LANE_WMAX))) + 4.0


BOWL_SLOT_TH0_DEG = THETA_EXIT_DEG - BOWL_SLOT_BEFORE_EXIT_DEG
BOWL_SLOT_TH1_DEG = THETA_EXIT_DEG + BOWL_SLOT_AFTER_EXIT_DEG


def _dedupe_xy(pts_xy: list[tuple[float, float]], eps: float = 0.12) -> list[tuple[float, float]]:
    if not pts_xy:
        return []
    out = [pts_xy[0]]
    for p in pts_xy[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= eps:
            out.append(p)
    return out


def _path_len_mm(pts_xy: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(pts_xy[i][0] - pts_xy[i - 1][0], pts_xy[i][1] - pts_xy[i - 1][1])
        for i in range(1, len(pts_xy))
    )


def _take_path_len(
    pts_xy: list[tuple[float, float]], length: float
) -> list[tuple[float, float]]:
    if not pts_xy or length <= 1e-9:
        return list(pts_xy[:1])
    out = [pts_xy[0]]
    acc = 0.0
    for p in pts_xy[1:]:
        dx, dy = p[0] - out[-1][0], p[1] - out[-1][1]
        d = math.hypot(dx, dy)
        if d < 1e-9:
            continue
        if acc + d >= length:
            u = (length - acc) / d
            out.append((out[-1][0] + u * dx, out[-1][1] + u * dy))
            return out
        out.append(p)
        acc += d
    return out


def _downsample_xy(pts_xy: list[tuple[float, float]], n_max: int = 12) -> list[tuple[float, float]]:
    if len(pts_xy) <= n_max:
        return list(pts_xy)
    out = [pts_xy[0]]
    step = (len(pts_xy) - 1) / float(n_max - 1)
    for i in range(1, n_max - 1):
        out.append(pts_xy[int(round(i * step))])
    out.append(pts_xy[-1])
    return _dedupe_xy(out)


def _wall_from_segments(
    pts_xy: list[tuple[float, float]],
    thick: float,
    z0: float,
    h: float,
) -> Part.Shape:
    """Tường vững boolean: ít hộp theo polyline rút gọn — không Face tự cắt."""
    pts = _downsample_xy(_dedupe_xy(pts_xy), 10)
    if len(pts) < 2 or thick <= 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    body = None
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 0.08:
            continue
        heading = math.degrees(math.atan2(y1 - y0, x1 - x0))
        seg = _box(ln + 0.55, thick, h, -0.28, -0.5 * thick, z0)
        seg.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
        seg.translate(App.Vector(x0, y0, 0))
        body = seg if body is None else body.fuse(seg)
    for x, y in (pts[0], pts[-1]):
        cap = _cyl_z(thick, h, x, y, z0)
        body = cap if body is None else body.fuse(cap)
    return _refine(body) if body is not None else _box(0.1, 0.1, 0.1, 0, 0, z0)


def _thickened_path_wall(
    pts_xy: list[tuple[float, float]],
    thick: float,
    z0: float,
    h: float,
) -> Part.Shape:
    """Tường đứng theo polyline tâm. Face mượt nếu vững; không thì ghép đoạn."""
    pts = _dedupe_xy(pts_xy)
    if len(pts) < 2 or thick <= 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    want = _path_len_mm(pts) * thick * h * 0.45
    half = 0.5 * thick
    left, right = [], []
    n = len(pts)
    for i in range(n):
        if i == 0:
            dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx, dy = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dy = pts[i + 1][1] - pts[i - 1][1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        x, y = pts[i]
        left.append(App.Vector(x + half * nx, y + half * ny, z0))
        right.append(App.Vector(x - half * nx, y - half * ny, z0))
    wire = left + list(reversed(right))
    wire.append(wire[0])
    try:
        face = Part.Face(Part.makePolygon(wire))
        wall = _refine(face.extrude(App.Vector(0, 0, h)))
        vol = float(getattr(wall, "Volume", 0.0) or 0.0)
        if vol >= max(1.0, want) and _shape_ok(wall, max(1.0, want)):
            return wall
    except Exception:
        pass
    return _wall_from_segments(pts, thick, z0, h)


def _join_seal_key(width_open: float, thick: float, h: float) -> Part.Shape:
    """Khối khóa miệng: hộp trên dây tâm, lệch vào trong tường (không lấn lòng lane)."""
    geo = lane_exit_join_geo(width_open)
    pts = _take_path_len(geo["exit_inner_pts"], JOIN_SEAL_OVERLAP_MM + 12.0)
    if len(pts) < 2:
        p = geo["exit_inner_pts"][0]
        return _cyl_z(thick, h, p[0], p[1], GAP0)
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    heading = math.degrees(math.atan2(y1 - y0, x1 - x0))
    tw = max(2.2, thick - 0.15)
    # lệch về tâm (phía đặc tường) — hộp dây cung không cắt lòng lane.
    # 0.45 mm cũ không đủ ở W lớn (viên tại θ_exit vẫn chạm cap0/bar — xem
    # verify_single_file_multi / verify_single_file_size_sweep jam_pill_vs_L);
    # 4 mm còn kẹt sát ngay tại θ_exit khi W→26 (D→25 mm, biên <0.5 mm theo mô
    # hình capsule đơn giản — CAD 3D thật vẫn chạm). 7 mm cho biên ~2 mm dư mọi W.
    SEAL_KEY_INBOARD_MM = 7.0
    ux_in, uy_in = _unit2(-x0, -y0)
    ox, oy = x0 + SEAL_KEY_INBOARD_MM * ux_in, y0 + SEAL_KEY_INBOARD_MM * uy_in
    bar = _box(ln + 2.4, tw, h, -1.2, -0.5 * tw, GAP0)
    bar.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
    bar.translate(App.Vector(ox, oy, 0))
    cap0 = _cyl_z(tw, h, ox, oy, GAP0)
    cap1 = _cyl_z(tw, h, x1 + SEAL_KEY_INBOARD_MM * ux_in, y1 + SEAL_KEY_INBOARD_MM * uy_in, GAP0)
    return _refine(bar.fuse(cap0).fuse(cap1))


def _funnel_params(width_open: float) -> dict | None:
    """Phễu tiếp xúc: tip Guide → tường trong lane (đẩy +r khi W < ENTRANCE_W)."""
    r_i = CHANNEL_R_OUTER - _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    r_cline = r_i - 0.5 * RAIL_T
    r0 = GUIDE_R1 + 1.2
    th0 = GUIDE_TH1 + 2.5
    # Dừng trước cửa chỉnh chiều cao — không cắt Entry_Gate_*
    th1 = THETA_MOUTH_DEG - 8.5
    if r_cline <= r0 + 0.8 or th1 <= th0 + 0.5:
        return None
    return {"r0": r0, "r1": r_cline, "th0": th0, "th1": th1}


def _inner_wall_r(th_deg: float, width_open: float) -> float | None:
    """Tâm tường đẩy +r tại θ: xoắn Guide, phễu họng, rồi rail lane. None = không tường."""
    rg = _spiral_r_at_theta(GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th_deg)
    if rg is not None:
        return rg
    fun = _funnel_params(width_open)
    if fun is not None and _ang_between(th_deg, fun["th0"], fun["th1"]):
        span = fun["th1"] - fun["th0"]
        th = th_deg
        if th < fun["th0"] - 1.0:
            th += 360.0
        u = _clamp((th - fun["th0"]) / span, 0.0, 1.0)
        return fun["r0"] + u * (fun["r1"] - fun["r0"])
    r_i = CHANNEL_R_OUTER - _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    if _ang_between(th_deg, THETA_MOUTH_DEG - 0.5, THETA_EXIT_DEG):
        return r_i - 0.5 * RAIL_T
    return None


def _unit2(x: float, y: float) -> tuple[float, float]:
    n = math.hypot(x, y) or 1.0
    return (x / n, y / n)


def _ang_diff_deg(a: float, b: float) -> float:
    return (b - a + 180.0) % 360.0 - 180.0


def _path_heading_deg(p: tuple[float, float], q: tuple[float, float]) -> float:
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))


def _path_max_turn_deg(pts: list[tuple[float, float]]) -> float:
    mx = 0.0
    for i in range(1, len(pts) - 1):
        a = _path_heading_deg(pts[i - 1], pts[i])
        b = _path_heading_deg(pts[i], pts[i + 1])
        mx = max(mx, abs(_ang_diff_deg(a, b)))
    return mx


def _hermite_poly(
    p0: tuple[float, float],
    t0: tuple[float, float],
    p3: tuple[float, float],
    t3: tuple[float, float],
    n: int,
    l0: float | None = None,
    l3: float | None = None,
) -> list[tuple[float, float]]:
    ux0, uy0 = _unit2(*t0)
    ux3, uy3 = _unit2(*t3)
    chord = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
    h0 = float(l0 if l0 is not None else JOIN_HANDLE_FRAC * chord)
    h3 = float(l3 if l3 is not None else JOIN_HANDLE_FRAC * chord)
    p1 = (p0[0] + h0 * ux0, p0[1] + h0 * uy0)
    p2 = (p3[0] - h3 * ux3, p3[1] - h3 * uy3)
    pts: list[tuple[float, float]] = []
    for i in range(max(4, n) + 1):
        tt = i / max(4, n)
        u = 1.0 - tt
        b0, b1, b2, b3 = u ** 3, 3.0 * u * u * tt, 3.0 * u * tt * tt, tt ** 3
        pts.append(
            (
                b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0],
                b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1],
            )
        )
    return pts


def lane_exit_join_geo(width_open: float) -> dict:
    """Cung lane → Hermite G1 → máng 50 mm (trượt radial theo W trên ray bát)."""
    ap = chute_slide_aperture(width_open)
    r_i = ap["r_inner"]
    r_c = 0.5 * (ap["r_inner"] + ap["r_outer"])
    r_cline = r_i - 0.5 * RAIL_T
    r_cline_outer = ap["r_outer"] - 0.5 * RAIL_T  # vách ngoài sát thành bát
    pose = exit_tangent_pose(width_open, CHUTE_WALL_H_MM)
    ux, uy = pose["chute_dir"]
    ax, ay = pose["anchor_xy"]
    nx_i, ny_i = -uy, ux
    if ax * nx_i + ay * ny_i > 0.0:
        nx_i, ny_i = -nx_i, -ny_i
    nx_o, ny_o = -nx_i, -ny_i
    delta = r_c - r_cline
    th_b = _deg2rad(JOIN_BLEND_TH0)
    th_e = _deg2rad(THETA_EXIT_DEG)
    p0 = (r_cline * math.cos(th_e), r_cline * math.sin(th_e))
    t0 = (-math.sin(th_e), math.cos(th_e))
    # p3 = điểm offset delta*nx_i tại s=0 (đầu đường thẳng máng ra) — KHÔNG cộng
    # thêm JOIN_BLEND_S*u trước khi offset, tránh Bezier phải vươn xa (25 mm+)
    # rồi vọt lố bán kính qua r_c (tường cắt viên tại khuỷu θ_exit, xem
    # verify_single_file_multi jam_pill_vs_L). Đường thẳng offset (song song
    # trục máng, cách đều delta) tự nó luôn đúng khoảng cách — không cần Bezier
    # vươn dài; chỉ cần Bezier NGẮN nối góc cung → điểm đầu đường thẳng.
    p3 = (ax + delta * nx_i, ay + delta * ny_i)
    # Không xoắn lõm vào tâm (túi chết). Uốn G1 tại miệng: ê_θ → û, lệch nhẹ n_in.
    t_mix = _unit2(0.55 * t0[0] + 0.45 * ux + 0.20 * nx_i, 0.55 * t0[1] + 0.45 * uy + 0.20 * ny_i)
    # Handle theo JOIN_HANDLE_FRAC * chord (chord ngắn hẳn nay p3 ở s=0) —
    # không còn hằng số tuyệt đối 10/12 mm (từng dài hơn chord mới → vọt lố).
    herm = _hermite_poly(p0, t_mix, p3, (ux, uy), JOIN_N, l0=None, l3=None)
    # Cung tới θ_exit rồi nối — không túi r↓
    pre: list[tuple[float, float]] = []
    n_pre = 8
    for i in range(n_pre):
        u = i / n_pre
        th = _deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * u)
        pre.append((r_cline * math.cos(th), r_cline * math.sin(th)))
    blend = pre + herm
    # p3 nay ở s=0 (không còn "dùng hết" JOIN_BLEND_S bên trong Bezier) — đường
    # thẳng phải chạy đủ EXIT_TRACK_LEN từ p3.
    extra = max(12.0, EXIT_TRACK_LEN)
    straight: list[tuple[float, float]] = []
    for i in range(1, 17):
        s = extra * (i / 16.0)
        straight.append((p3[0] + s * ux, p3[1] + s * uy))
    arc: list[tuple[float, float]] = []
    outer_arc: list[tuple[float, float]] = []
    n_arc = 40
    for i in range(n_arc + 1):
        u = i / n_arc
        th = _deg2rad(THETA_MOUTH_DEG + (JOIN_BLEND_TH0 - THETA_MOUTH_DEG) * u)
        arc.append((r_cline * math.cos(th), r_cline * math.sin(th)))
        outer_arc.append((r_cline_outer * math.cos(th), r_cline_outer * math.sin(th)))
    rail_pts = arc[:-1] + blend + straight[:10]
    # Exit bắt đầu trước miệng (chồng rail ≥ JOIN_SEAL_OVERLAP)
    exit_inner = herm + straight
    wall_span = ap["width_mm"] + 0.5 * RAIL_T + 0.5 * EXIT_TRACK_WALL

    def _offset_poly(pts: list[tuple[float, float]], off: float) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        n = len(pts)
        for i in range(n):
            if i == 0:
                dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
            elif i == n - 1:
                dx, dy = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
            else:
                dx = pts[i + 1][0] - pts[i - 1][0]
                dy = pts[i + 1][1] - pts[i - 1][1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            if nx * nx_o + ny * ny_o < 0.0:
                nx, ny = -nx, -ny
            out.append((pts[i][0] + off * nx, pts[i][1] + off * ny))
        return out

    exit_outer = _offset_poly(exit_inner, wall_span)
    turn = _path_max_turn_deg(arc[-4:] + blend[1:])
    h_u = math.degrees(math.atan2(uy, ux))
    t0 = (-math.sin(th_b), math.cos(th_b))
    t_pre = (-math.sin(th_b), math.cos(th_b))
    h_t = math.degrees(math.atan2(t_pre[1], t_pre[0]))
    g1_end = abs(_ang_diff_deg(_path_heading_deg(blend[-2], blend[-1]), h_u)) < 8.0
    g1_start = abs(_ang_diff_deg(_path_heading_deg(blend[0], blend[1]), h_t)) < 20.0
    r_lane_pts = []
    for x, y in blend:
        s_ch = (x - ax) * ux + (y - ay) * uy
        if s_ch < 2.0 and math.hypot(x, y) < BOWL_IR + 0.5:
            r_lane_pts.append(math.hypot(x, y))
    r_blend_max = max(r_lane_pts) if r_lane_pts else 0.0
    inboard_ok = r_blend_max <= r_cline + 5.0
    return {
        "r_cline": r_cline,
        "r_center": r_c,
        "arc_pts": arc,
        "outer_arc_pts": outer_arc,
        "blend_pts": blend,
        "straight_pts": straight,
        "rail_pts": rail_pts,
        "exit_inner_pts": exit_inner,
        "exit_outer_pts": exit_outer,
        "max_turn_deg": round(turn, 3),
        "g1_start": g1_start,
        "g1_end": g1_end,
        "smooth": bool(turn <= JOIN_MAX_TURN_DEG and g1_end and g1_start and inboard_ok),
        "inboard_ok": inboard_ok,
        "r_blend_max": round(r_blend_max, 3),
        "blend_s_mm": JOIN_BLEND_S,
    }


def _rail_pill_clearance_cut(width_open: float) -> Part.Shape:
    """
    Bao an toàn quanh ĐƯỜNG ĐI THẬT của viên tại khuỷu lane→Exit_Track — cắt
    trực tiếp khỏi Inner_Lane_Rail, không phụ thuộc hình Hermite của tường
    (đường cong nối G1 không giữ khoảng-cách-vuông-góc hằng số tới viên, có
    thể phình vào đúng chỗ viên đi qua ở W lớn — xem verify_single_file_*
    jam_pill_vs_L). Chỉ cắt QUANH khuỷu (θ∈[JOIN_BLEND_TH0, θ_exit] + đoạn
    đầu máng ra), KHÔNG đụng phần cung chính (mouth→JOIN_BLEND_TH0) vẫn cần
    tường để dẫn hướng viên.
      (a) cung bán kính r_c (tâm viên thật) từ JOIN_BLEND_TH0 → θ_exit
      (b) đoạn thẳng dọc trục máng (tâm viên thật khi đã vào máng) s∈[0,30] mm
    """
    ap = chute_slide_aperture(width_open)
    r_c = 0.5 * (ap["r_inner"] + ap["r_outer"])
    D_est = max(0.5, CHUTE_W_MM - PILL_CLEAR_XY)
    clear_d = D_est + RAIL_T + 1.0
    n = 16
    arc_pts = [
        (
            r_c * math.cos(_deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * (i / n))),
            r_c * math.sin(_deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * (i / n))),
        )
        for i in range(n + 1)
    ]
    cut_arc = _wall_from_segments(arc_pts, clear_d, GAP0, CHUTE_WALL_H_MM)
    pose = exit_tangent_pose(width_open, CHUTE_WALL_H_MM)
    ax, ay = pose["anchor_xy"]
    ux, uy = pose["chute_dir"]
    line_pts = [(ax + s * ux, ay + s * uy) for s in (0.0, 10.0, 20.0, 30.0)]
    cut_line = _wall_from_segments(line_pts, clear_d, GAP0, CHUTE_WALL_H_MM)
    return _refine(cut_arc.fuse(cut_line))


def make_lane_entrance_marker() -> Part.Shape:
    """
    Khung hồng — HỌNG VÀO lane nhìn từ Top.
    Không có sàn — viên luôn tiếp xúc đĩa; chỉ mép + mũi tên treo.
    """
    th0 = ENTRANCE_TH0
    th1 = ENTRANCE_TH1
    r_in = GUIDE_R1 + 0.5 * GUIDE_T + 0.3
    r_out = CHANNEL_R_OUTER - 0.3
    # Marker treo trên H_MAX — không đứng trên đĩa (trước đây môi GAP0 chặn họng)
    z_mark = GAP0 + H_MAX + 4.0
    th_lip = th0 + 3.0
    lip_in = _place_oriented_box(
        5.0, 3.5, 4.0,
        (r_in + 2.0) * math.cos(_deg2rad(th_lip)),
        (r_in + 2.0) * math.sin(_deg2rad(th_lip)),
        z_mark,
        th_lip,
    )
    lip_out = _place_oriented_box(
        5.0, 3.5, 4.0,
        (r_out - 2.0) * math.cos(_deg2rad(th_lip)),
        (r_out - 2.0) * math.sin(_deg2rad(th_lip)),
        z_mark,
        th_lip,
    )
    th_c = 0.5 * (th0 + THETA_MOUTH_DEG)
    r_c = 0.5 * (r_in + r_out)
    arrow = _place_oriented_box(
        16.0, 4.0, 2.2,
        r_c * math.cos(_deg2rad(th_c)),
        r_c * math.sin(_deg2rad(th_c)),
        z_mark + 2.0,
        th_c + 90.0,
    )
    return _refine(lip_in.fuse(lip_out).fuse(arrow))


def make_exit_track(width_open: float, height_open: float) -> Part.Shape:
    """Không còn máng exit trên đĩa."""
    _ = width_open, height_open
    return Part.Shape()


def rim_leave_y_mm(width_open: float) -> float:
    """|y| chỗ tâm viên rời đĩa: đi tiếp tuyến từ (−r_lane, 0) tới r = DISC_R."""
    ap = aperture_from_opens(width_open, H_MAX)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    return math.sqrt(max(0.0, DISC_R ** 2 - r_lane ** 2))


def ramp_catch_run_mm() -> float:
    """Máng phải chạy đủ xa theo −Y để hứng cả viên rời đĩa muộn nhất (W lớn)."""
    return rim_leave_y_mm(W_MAX) + RAMP_CATCH_MARGIN


def ramp_geo(width_open: float, height_open: float) -> dict:
    """Máng nghiêng 40°, đổ −Y (ra Front), có đáy.

    Cạnh TRÁI của lòng máng = đường tiếp tuyến mép đĩa tại 9 giờ (x = −DISC_R);
    lòng máng rộng CHUTE_W_MM chạy vào PHÍA TRONG (luồn dưới đĩa, cách đáy đĩa
    RAMP_DISC_GAP). Viên rời đĩa ở x ∈ [−DISC_R, −r_lane_min] nên rơi thẳng
    xuống lòng máng.
    """
    _ = width_open, height_open
    ux, uy = 0.0, -1.0
    x0, y0 = -DISC_R, 0.0  # cạnh trái lòng máng, ngay mép đĩa
    a = _deg2rad(RAMP_ANGLE_DEG)
    run = ramp_catch_run_mm()
    L = run / math.cos(a)
    drop = L * math.sin(a)
    w = CHUTE_W_MM
    z0 = DISC_TOP_Z - DISC_T - RAMP_DISC_GAP  # luồn dưới đĩa
    return {
        "s_cross_mm": 0.0,
        "start_xy": (x0, y0),
        "start_z": z0,
        "center_xy": (x0 + 0.5 * w, y0),  # tâm lòng máng (đo bề rộng ở đây)
        "end_xy": (x0 + run * ux, y0 + run * uy),
        "end_z": z0 - drop,
        "dir_xy": (ux, uy),
        "run_mm": run,
        "len_mm": L,
        "drop_mm": drop,
        "angle_deg": RAMP_ANGLE_DEG,
        "lumen_w_mm": w,
        "lumen_x_mm": (x0, x0 + w),
        "left_edge_x_mm": x0,
        "left_edge_on_rim": abs(x0 + DISC_R) < 1e-9,
        "rim_leave_y_mm": (rim_leave_y_mm(W_MIN), rim_leave_y_mm(W_MAX)),
        "under_disc_gap_mm": RAMP_DISC_GAP,
        "wall_h_mm": CHUTE_WALL_H_MM,
        "slides": math.tan(a) > MU_WALL,
        "self_lock_deg": math.degrees(math.atan(MU_WALL)),
        "on_disc": False,
        "clock_h": 9,
        "heading_front": True,
    }


def make_bowl_exit_chute(_width_open: float | None = None, _height_open: float | None = None) -> Part.Shape:
    """Máng nghiêng 40° có đáy — child của Bowl_Tube, cạnh trái trùng mép đĩa 9h.

    Dựng ở gốc: +x = dọc máng (chưa nghiêng), +y = hướng vào TÂM đĩa sau khi
    quay. Lòng máng y ∈ [0, w]; vách trái (ngoài mép đĩa) y ∈ [−t, 0] nên MẶT
    TRONG của nó nằm đúng x = −DISC_R sau khi đặt.
    """
    g = ramp_geo(W_MAX, CHUTE_WALL_H_MM)
    w = g["lumen_w_mm"]
    t = RAMP_WALL_T
    ft = RAMP_FLOOR_T
    h = g["wall_h_mm"]
    L = g["len_mm"]
    floor = _box(L, w + 2.0 * t, ft, 0.0, -t, -ft)
    wall_left = _box(L, t, h, 0.0, -t, 0.0)  # phía ngoài mép đĩa
    wall_right = _box(L, t, h, 0.0, w, 0.0)  # phía tâm đĩa
    body = floor.fuse(wall_left).fuse(wall_right)
    body.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), RAMP_ANGLE_DEG)
    body.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -90.0)
    x0, y0 = g["start_xy"]
    body.translate(App.Vector(x0, y0, g["start_z"]))
    # Keep-out = BAO ĐĨA (không phải cả trụ vô hạn như trước): máng được phép
    # luồn DƯỚI đĩa, chỉ không được chạm đĩa. Đáy keep-out = mặt máng tại 9h nên
    # sàn máng không bị cắt; phần vách nhô lên trong lòng đĩa thì bị gọt đi.
    keep_out = _cyl_z(
        2.0 * (DISC_R + DISC_RADIAL_CLEAR), 400.0, 0.0, 0.0, g["start_z"],
    )
    try:
        cut = body.cut(keep_out)
        if _shape_ok(cut, 200.0):
            body = cut
    except Exception:
        pass
    return _refine(body)


def make_exit_ramp(width_open: float, height_open: float) -> Part.Shape:
    """Alias — Bowl_Tube_Exit_Chute."""
    return make_bowl_exit_chute(width_open, height_open)


def make_exit_mouth_marker(width_open: float, height_open: float) -> Part.Shape:
    """
    Khung hồng đánh dấu miệng máng — chỉ 2 trụ + xà trên cao.
    Lòng kênh (W × H) hoàn toàn trống — không chặn viên ra.
    """
    ap = aperture_from_opens(width_open, height_open)
    W = ap["width_mm"]
    H = ap["height_mm"]
    pose = exit_tangent_pose(width_open, height_open)
    x0 = pose["x0_along_mm"]
    clear_z = 2.0
    post_w = 3.0
    post_t = 3.0
    post_l = _box(
        post_t, post_w, H + 8.0,
        x0 - 0.5, -0.5 * W - post_w - 0.5, GAP0,
    )
    post_r = _box(
        post_t, post_w, H + 8.0,
        x0 - 0.5, 0.5 * W + 0.5, GAP0,
    )
    lintel = _box(
        post_t, W + 2.0 * post_w + 1.0, 2.5,
        x0 - 0.5, -0.5 * W - post_w - 0.5, GAP0 + H + clear_z,
    )
    return _place_tangent_exit(_refine(post_l.fuse(post_r).fuse(lintel)), width_open, height_open)


def _overlap_volume(a: Part.Shape, b: Part.Shape) -> float:
    try:
        return float(getattr(a.common(b), "Volume", 0.0) or 0.0)
    except Exception:
        return 0.0


def _to_mesh(shape: Part.Shape, deflection: float = 0.75):
    """Tessellate BREP → triangle mesh for surface collision."""
    import MeshPart

    return MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=float(deflection),
        AngularDeflection=0.5,
    )


def _mesh_intersect_facets(a: Part.Shape, b: Part.Shape, deflection: float = 0.75) -> int:
    """Number of intersection facets between two tessellated surfaces (0 = clear)."""
    try:
        ma = _to_mesh(a, deflection)
        mb = _to_mesh(b, deflection)
        hit = ma.intersect(mb)
        return int(getattr(hit, "CountFacets", 0) or 0)
    except Exception:
        # Fallback: solid volume overlap counts as jam
        return 1 if _overlap_volume(a, b) > 1e-2 else 0


def _mesh_jam(
    a: Part.Shape,
    b: Part.Shape,
    deflection: float = 0.85,
    solid_thr: float = 0.05,
) -> tuple[bool, int, float]:
    """
    Mesh surface collision + solid confirm.
    Near-touch tessellation can yield a few facets with Volume≈0 — not a jam.
    """
    fac = _mesh_intersect_facets(a, b, deflection)
    if fac <= 0:
        return False, 0, 0.0
    vol = _overlap_volume(a, b)
    return (vol > solid_thr), fac, vol


def _grid(lo: float, hi: float, step: float) -> list[float]:
    vals, v = [], lo
    while v <= hi + 1e-9:
        vals.append(round(v, 6))
        v += step
    if vals[-1] < hi - 1e-9:
        vals.append(hi)
    return vals


def recommend_gap_mm(D, T, clear_xy=PILL_CLEAR_XY, clear_z=PILL_CLEAR_Z) -> dict:
    """
    Máng / khe: rộng & cao hơn vật 1 mm, kẹp trong dải chỉnh 2–26 (W) / 2–26 (H).
    Vật kích thước 2–26 mm luôn có khẩu độ khả thi (tại max: clear có thể < 1 mm).
    """
    w_want = float(D) + float(clear_xy)
    h_want = float(T) + float(clear_z)
    notes = []
    w = w_want
    h = h_want
    if w < WIDTH_MIN and WIDTH_MIN < 2.0 * D:
        w = WIDTH_MIN
        notes.append("W_bumped_to_W_MIN")
    if h < HEIGHT_MIN and HEIGHT_MIN < 2.0 * T:
        h = HEIGHT_MIN
        notes.append("H_bumped_to_H_MIN")
    if w > WIDTH_MAX:
        w = WIDTH_MAX
        notes.append("W_clamped_to_W_MAX")
    if h > HEIGHT_MAX:
        h = HEIGHT_MAX
        notes.append("H_clamped_to_H_MAX")
    obj_in = (WIDTH_MIN - 1e-9) <= float(D) <= (WIDTH_MAX + 1e-9) and (
        HEIGHT_MIN - 1e-9
    ) <= float(T) <= (HEIGHT_MAX + 1e-9)
    fit = w + 1e-9 >= float(D) and h + 1e-9 >= float(T)
    return {
        "W": round(w, 3),
        "H": round(h, 3),
        "W_want": round(w_want, 3),
        "H_want": round(h_want, 3),
        "in_adjust_range": bool(obj_in and fit),
        "notes": notes,
        "clear_xy": clear_xy,
        "clear_z": clear_z,
    }


def _pill_channel_fit(D, T, W, H) -> dict:
    pass_one_w, pass_one_h = W >= D - 1e-9, H >= T - 1e-9
    block_dw, block_dh = W < 2 * D - 1e-9, H < 2 * T - 1e-9
    r_o, r_i = CHANNEL_R_OUTER, CHANNEL_R_OUTER - W
    r_c = 0.5 * (r_i + r_o)
    sits = (r_c - 0.5 * D) >= r_i - 1e-6 and (r_c + 0.5 * D) <= r_o + 1e-6
    return {
        "pass_one_w": pass_one_w,
        "pass_one_h": pass_one_h,
        "block_double_w": block_dw,
        "block_double_h": block_dh,
        "single_file": pass_one_w and pass_one_h and block_dw and block_dh,
        "r_center_mm": round(r_c, 3),
        "sits_in_channel": sits,
        "two_abreast_would_fit": W >= 2 * D,
        "radial_clear_in_mm": round((r_c - 0.5 * D) - r_i, 3),
        "radial_clear_out_mm": round(r_o - (r_c + 0.5 * D), 3),
    }


def min_angular_pitch_deg(D: float, W: float, margin_mm: float = 1.0) -> float:
    """
    Δθ tối thiểu giữa 2 viên (thả cùng lúc, cùng cỡ) để KHÔNG va khi CẢ HAI
    cùng đi qua nút thắt cổ chai: MIỆNG MÁNG RA (Exit_Track).

    Trên đĩa (chưa vào máng): θ̇=ω chung cho mọi viên, không lực viên-viên
    ⇒ Δθ_ij = θ0_i−θ0_j giữ NGUYÊN (mod 360) suốt pha này — tưởng như cứ
    Δθ>0 là an toàn. NHƯNG khi viên trước (i) cắt θ_exit và bắt đầu vào máng,
    tốc độ dọc máng bị ma sát ghìm rất chậm lúc mới vào:
      s_dot = ω·r·drive_net,  drive_net = sinβ − μ_wall·cosβ  (β chỉ vừa đủ
      thắng khóa ma sát — drive_net ≪ 1 theo thiết kế, xem exit_wall_friction_beta).
    Viên sau (j) tới θ_exit trễ hơn Δt = Δθ_rad/ω; lúc đó viên i mới đi được
      s_i(Δt) ≈ ω·r_lane·drive_net·Δt = r_lane·drive_net·Δθ_rad
    (ω triệt tiêu — khoảng cách dọc máng lúc viên sau bắt đầu vào KHÔNG phụ
    thuộc ω, chỉ phụ thuộc Δθ và drive_net). Vì drive_net nhỏ (~0.09 với
    μ_wall=0.35, margin 5°), khoảng cách "hội tụ" tại miệng máng bị NÉN theo
    hệ số drive_net so với khoảng cách hình học Δθ·r_lane ngây thơ — đây là
    nút thắt cổ chai thật của cơ cấu (máng phải giữ β nhỏ để tự hãm khi đĩa
    dừng, nên vào máng luôn chậm). Sau khi viên sau cũng đã vào máng, khoảng
    cách hai viên KHÔNG giảm thêm (s_dot tăng theo r, viên trước luôn nhanh
    hơn hoặc bằng) ⇒ đây là khoảng cách NHỎ NHẤT suốt hành trình.
      Δθ_min = (D + margin) / (r_lane · drive_net)   [rad]
    """
    ap = aperture_from_opens(W, H_MIN)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    drive_net = max(1e-6, float(exit_wall_friction_beta()["drive_net"]))
    return math.degrees((float(D) + float(margin_mm)) / (r_lane * drive_net))


def _place_n_pills_no_overlap(
    n: int,
    D: float,
    T: float,
    shape: str,
    seed: int,
    pitch_min: float,
    dtheta_min_deg: float = 0.0,
) -> list[tuple[float, float]]:
    """
    Rớt n viên cùng lúc, vị trí ngẫu nhiên, không chồng nhau lúc thả (rejection
    sampling). Ngoài khoảng cách Euclid ≥ pitch_min, còn ép Δθ ≥ dtheta_min_deg
    (xem min_angular_pitch_deg) — nếu không, 2 viên ở bán kính khác nhau nhưng
    θ gần nhau có thể va khi CÙNG hội tụ vào lane (khoảng cách kính không giúp
    được nữa một khi cả hai bị ép về cùng bán kính lane).
    """
    rng = random.Random(seed)
    half = 0.5 * D
    r_lo = 0.5 * HUB_D + half + 2.0
    r_hi = CHANNEL_R_OUTER - half - 1.0
    placed_xy: list[tuple[float, float]] = []
    placed_rth: list[tuple[float, float]] = []
    max_attempts = max(4000, n * 800)
    attempts = 0
    while len(placed_rth) < n and attempts < max_attempts:
        attempts += 1
        r = rng.uniform(r_lo, r_hi)
        th = rng.uniform(0.0, 360.0)
        x = r * math.cos(_deg2rad(th))
        y = r * math.sin(_deg2rad(th))
        ok = True
        for (pr, pth), (px, py) in zip(placed_rth, placed_xy):
            if math.hypot(x - px, y - py) < pitch_min:
                ok = False
                break
            if dtheta_min_deg > 0.0:
                dth = abs(((th - pth + 180.0) % 360.0) - 180.0)
                if dth < dtheta_min_deg:
                    ok = False
                    break
        if ok:
            placed_xy.append((x, y))
            placed_rth.append((r, th))
    return placed_rth


PILL_POSES = ("flat", "stand")  # stand = viên dựng (cao = D); ball bỏ qua stand


def _pill_extents(D: float, T: float, pose: str, shape: str) -> tuple[float, float]:
    """(xy_span, z_height) của viên trên đĩa."""
    if shape == "ball" or abs(D - T) < 1e-9:
        return float(D), float(D)
    if pose == "stand":
        return float(T), float(D)  # dựng trên cạnh: đáy hẹp T, cao D
    return float(D), float(T)


def _spiral_r_at_theta(r0, r1, th0_deg, th1_deg, th_deg: float) -> float | None:
    """Bán kính lưỡi xoắn tại θ (hỗ trợ θ bọc 0..360 vs th0 âm)."""
    span = th1_deg - th0_deg
    if abs(span) < 1e-9:
        return None
    u_hit = None
    for k in (-1, 0, 1):
        u = (th_deg + 360.0 * k - th0_deg) / span
        if -0.02 <= u <= 1.02:
            u_hit = _clamp(u, 0.0, 1.0)
            break
    if u_hit is None:
        return None
    return r0 + (r1 - r0) * u_hit


def _ang_between(th_deg: float, a_deg: float, b_deg: float) -> bool:
    """θ ∈ [a,b] trên vòng tròn (a→b theo +θ, có thể bọc)."""
    th = th_deg % 360.0
    a = a_deg % 360.0
    b = b_deg % 360.0
    if a <= b:
        return a - 1e-9 <= th <= b + 1e-9
    return th >= a - 1e-9 or th <= b + 1e-9


def _trace_pill_egress(
    D: float,
    T: float,
    W: float,
    H: float,
    r0: float,
    th0: float,
    pose0: str,
    shape: str = "tablet",
    steps_per_rev: int = 48,
    max_revs: float = 5.0,
) -> dict:
    """
    Quỹ đạo rời rạc trên đĩa. Guide đẩy ra; lane kẹp r; scraper hạ stand→flat;
    thoát Exit_Track. Không xuyên tường: PyBullet tube_l_egress_pybullet.py.
    """
    ap = aperture_from_opens(W, H)
    r_i, r_o = ap["r_inner"], ap["r_outer"]
    r_c = 0.5 * (r_i + r_o)
    r_hub = DIR_R0 - 2.0
    r_max = CHANNEL_R_OUTER - 0.4
    pose = "flat" if shape == "ball" else pose0
    r = float(_clamp(r0, r_hub, r_max))
    th = float(th0)
    knocked = False
    entered_lane = False
    dth = 360.0 / steps_per_rev
    n_max = int(max_revs * steps_per_rev)
    path_pts: list[tuple[float, float, str]] = []

    for step in range(n_max):
        th = (th + dth) % 360.0
        xy_span, z_h = _pill_extents(D, T, pose, shape)

        in_lane_ang = THETA_MOUTH_DEG - 2.0 <= th <= THETA_EXIT_DEG + dth + 2.0
        in_lane_r = (r + 0.5 * xy_span) >= r_i - 0.5 and (r - 0.5 * xy_span) <= r_o + 0.5
        if in_lane_ang and in_lane_r:
            entered_lane = True
            if pose == "stand" and z_h > H - 0.05:
                # scraper / nóc máng: dựng sát H cũng bị quệt → nằm
                pose = "flat"
                knocked = True
                xy_span, z_h = _pill_extents(D, T, pose, shape)
            r = 0.85 * r + 0.15 * r_c
            r = _clamp(r, r_i + 0.5 * xy_span, r_o - 0.5 * xy_span)

            # thoát khi qua θ_exit và chiều cao vừa máng (H = T+1 mm)
            if z_h <= H + 0.25 and th >= THETA_EXIT_DEG - dth:
                return {
                    "exited": True,
                    "pose_exit": "flat" if pose == "flat" or z_h <= T + PILL_CLEAR_Z else pose,
                    "knocked_down": knocked,
                    "entered_lane": True,
                    "steps": step + 1,
                    "revs": round((step + 1) / steps_per_rev, 3),
                    "r_end": round(r, 2),
                    "th_end": round(th, 2),
                    "path": path_pts,
                }
        if step % 3 == 0:
            path_pts.append((round(r, 2), round(th, 2), pose))

        rg = _spiral_r_at_theta(GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th)
        if rg is not None and r <= rg + 0.5 * GUIDE_T + 0.55 * xy_span + 1.5:
            r = max(r, min(r_max, rg + 0.5 * GUIDE_T + 0.45 * xy_span))

        # Họng → lane (W=pill+1): drift về tâm kênh
        if _ang_between(th, ENTRANCE_TH0 - 2.0, THETA_EXIT_DEG + 2.0):
            if r >= GUIDE_R1 - 4.0:
                r = 0.65 * r + 0.35 * r_c
                r = _clamp(r, GUIDE_R1 + 0.2 * xy_span, r_max - 0.05)

        if r + 0.5 * xy_span > r_max:
            r = r_max - 0.5 * xy_span
        if (
            _ang_between(th, GUIDE_TH1 - 8.0, GUIDE_TH1 + 5.0)
            and r + 0.5 * xy_span < GUIDE_R1 - 0.5
        ):
            r = max(r_hub, r - 1.2)

    return {
        "exited": False,
        "pose_exit": pose,
        "knocked_down": knocked,
        "entered_lane": entered_lane,
        "steps": n_max,
        "revs": max_revs,
        "r_end": round(r, 2),
        "th_end": round(th, 2),
        "trapped": True,
        "path": path_pts,
    }


def _egress_start_grid(D: float) -> list[tuple[float, float]]:
    """Lưới (r, θ) phủ đĩa (tránh hub / ngoài bowl)."""
    r_lo = DIR_R0 + 0.5 * D + 1.0
    r_hi = CHANNEL_R_OUTER - 0.5 * D - 1.0
    rs = [
        r_lo,
        0.35 * r_lo + 0.65 * DIR_R1,
        0.5 * (DIR_R1 + FUNNEL_R1),
        0.55 * FUNNEL_R1 + 0.45 * r_hi,
        r_hi,
    ]
    ths = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]
    return [(r, th) for r in rs for th in ths]


def _pill_tunnel_hits_along_path(
    D: float,
    T: float,
    W: float,
    H: float,
    path: list,
    shape: str,
    guide,
    rail,
    bowl,
    exit_track,
) -> int:
    """Đếm mẫu tâm viên nằm sâu trong tường (xuyên component)."""
    hits = 0
    for r, th, pose in path[::3]:
        xy_span, z_h = _pill_extents(D, T, pose, shape)
        z_h = min(z_h, H + 0.2)
        cx = r * math.cos(_deg2rad(th))
        cy = r * math.sin(_deg2rad(th))
        # probe nhỏ — chỉ bắt xuyên sâu, không đếm tiếp xúc bề mặt
        rad = max(0.25, 0.15 * xy_span)
        probe = _cyl_z(rad, max(0.3, 0.35 * z_h), cx, cy, DISC_TOP_Z + 0.05)
        thr = 6.0
        if _overlap_volume(probe, guide) > thr or _overlap_volume(probe, rail) > thr:
            hits += 1
            continue
        # gần vành: tiếp xúc bowl bình thường — chỉ fail nếu tâm sâu trong tường
        if r < CHANNEL_R_OUTER - 0.55 * xy_span - 1.0:
            if _overlap_volume(probe, bowl) > thr:
                hits += 1
                continue
        if th >= THETA_EXIT_DEG + 2.0 and r >= CHANNEL_R_OUTER - 0.5 * W - 1.0:
            if _overlap_volume(probe, exit_track) > thr:
                hits += 1
    return hits


SIZE_SWEEP_MM = [2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 20, 22, 24, 26]


def make_size_range_datasets() -> list[dict]:
    """Ball (D=T=s) + tablet (D=s, T=max(2, s/2)) cho mỗi s ∈ 2..26."""
    out = []
    for s in SIZE_SWEEP_MM:
        sf = float(s)
        out.append({"id": f"size_ball_{s:g}", "D": sf, "T": sf, "shape": "ball"})
        t = max(2.0, round(0.5 * sf, 2))
        if abs(t - sf) > 0.05:
            out.append(
                {"id": f"size_tab_{s:g}x{t:g}", "D": sf, "T": float(t), "shape": "tablet"}
            )
    return out


OMEGA_DISC = 2.0 * math.pi  # rad/s — 1 vòng/s (chuẩn hoá; tỉ lệ thời gian)
SANITY_SEED = 20260811
SANITY_N = 100


def _crossed_unwrapped(th0_deg: float, th1_deg: float, target_deg: float) -> bool:
    """True nếu góc bung [th0, th1] cắt target + 360k."""
    lo = min(th0_deg, th1_deg) - 360.0
    hi = max(th0_deg, th1_deg) + 360.0
    k0 = int(math.floor(lo / 360.0)) - 1
    k1 = int(math.floor(hi / 360.0)) + 2
    for k in range(k0, k1 + 1):
        t = target_deg + 360.0 * k
        if th0_deg < t <= th1_deg:
            return True
    return False


def _cad_theta_fences(W: float, H: float) -> list[dict]:
    """
    Tường gần-đứng (θ ≈ const) còn lại trên đĩa — vật ê_θ phải qua được.
    Sau khi xóa hàng rào thoát / thành 30 mm / môi họng: chỉ còn mấu scraper (z≥H)
    và reject ngắn tại tip (trượt +r vào họng, không kẹt θ).
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    r_i = CHANNEL_R_OUTER - W
    fences = [
        {
            "name": "scraper_entry_tab",
            "th_deg": THETA_MOUTH_DEG,
            "r_lo": r_i + 0.6,
            "r_hi": CHANNEL_R_OUTER - 0.4,
            "z_lo": GAP0 + H,
            "z_hi": GAP0 + H + SCRAPER_ENTRY_H,
            "on_hit": "knock",
        },
        {
            "name": "reject_tip",
            "th_deg": GUIDE_TH1,
            "r_lo": GUIDE_R1 - REJECT_LEN,
            "r_hi": GUIDE_R1 + 0.2,
            "z_lo": GAP0,
            "z_hi": GAP0 + GUIDE_H,
            "on_hit": "slide_out",
        },
    ]
    if EXIT_GUARD_INBOARD > 0.5:
        r_cline = r_i - 0.5 * RAIL_T
        fences.append(
            {
                "name": "exit_inboard_guard",
                "th_deg": THETA_EXIT_DEG,
                "r_lo": r_cline - EXIT_GUARD_INBOARD,
                "r_hi": r_cline + 0.5 * RAIL_T,
                "z_lo": GAP0,
                "z_hi": GAP0 + RAIL_H,
                "on_hit": "jam",
            }
        )
    return fences


def simulate_pill_mechanics(
    D: float,
    T: float,
    W: float,
    H: float,
    r0: float,
    th0: float,
    pose0: str,
    shape: str = "tablet",
    omega: float = OMEGA_DISC,
    dth_deg: float = 1.0,
    max_revs: float = 8.0,
    path_every: int = 8,
) -> dict:
    """
    Phương trình trên đĩa (cực):

      Không tiếp xúc máng (no-slip):
          ṙ = 0
          θ̇ = ω
          v = ω r ê_θ     (dính đĩa, không trượt xuyên tâm)

      Tiếp xúc tường Guide / phễu / rail / bowl (được trượt trên đĩa):
          r ← max(r, r_wall(θ) + half_t + half_pill)   # đẩy +r (inelastic)
          θ̇ = ω                                       # đĩa vẫn dẫn góc
          ṙ ≠ 0 chỉ tại bước có contact

      Scraper: nếu đứng và z > H → hạ flat (va lưỡi).
      Hàng rào θ (CAD): knock / trượt +r vào họng — không được kẹt θ.
      Thoát: cắt θ_exit khi đang trong lane và z ≤ H.

    Nhiều vòng được phép (max_revs).
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    xy0, _z0 = _pill_extents(D, T, "flat" if shape == "ball" else pose0, shape)
    r_hub = 0.5 * HUB_D + 0.5 * xy0 + 1.0
    r_rim = CHANNEL_R_OUTER - 0.5 * xy0 - 0.2
    pose = "flat" if shape == "ball" else pose0
    r = float(_clamp(r0, r_hub, r_rim))
    th_unw = float(th0)
    dt = math.radians(dth_deg) / max(omega, 1e-9)
    n_max = int(max_revs * 360.0 / dth_deg)
    r_i = CHANNEL_R_OUTER - W
    ep = exit_tangent_pose(W, H)
    ux, uy = ep["chute_dir"]
    ax, ay = ep["anchor_xy"]
    drive_net = float(ep["drive_net_friction"])
    in_chute = False
    s_chute = 0.0
    entered_lane = False
    blocked_by: str | None = None
    fences = _cad_theta_fences(W, H)

    knocked = False
    n_contact = n_free = illegal_slip = 0
    n_disc = n_disc_miss = 0
    max_free_dr = 0.0
    max_dth_err_deg = 0.0
    path: list[tuple] = []
    disc_miss_sample: list[dict] = []

    def _half():
        return 0.5 * _pill_extents(D, T, pose, shape)[0]

    def _zh():
        return _pill_extents(D, T, pose, shape)[1]

    def _in_lane(rr: float, half: float) -> bool:
        return (rr - half) >= (r_i - 1.2) and (rr + half) <= (CHANNEL_R_OUTER + 0.6)

    def _on_disc_face(rr: float, half: float) -> bool:
        """Tâm viên còn trên mặt vành đĩa (ngoài lỗ trục, trong Ø đĩa)."""
        r_hole = 0.5 * (SHAFT_D + 0.2) + 0.3
        return (rr - 0.45 * 2.0 * half) >= r_hole and (rr + 0.45 * 2.0 * half) <= (DISC_R + 0.5)

    for step in range(n_max):
        th_prev = th_unw
        r_prev = r
        th_unw = th_prev + dth_deg
        th = th_unw % 360.0
        dth_err = abs((th_unw - th_prev) - dth_deg)
        if dth_err > max_dth_err_deg:
            max_dth_err_deg = dth_err

        contact = False
        half = _half()
        z_h = _zh()

        if in_chute:
            # Trên máng: F_dọc = F(sinβ − μ_wall cosβ); ds = r·drive_net·dθ
            ds = r * max(0.0, drive_net) * math.radians(dth_deg)
            s_chute += max(0.0, ds)
            px = ax + s_chute * ux
            py = ay + s_chute * uy
            r = math.hypot(px, py)
            th = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            contact = True
            half = _half()
            z_h = _zh()
        else:
            # Bowl (tường ngoài cố định) — chỉ khi chưa vào máng
            r_bowl = CHANNEL_R_OUTER - half - 0.05
            if r > r_bowl + 1e-9:
                r = r_bowl
                contact = True

            # Tường mỏng: chỉ khi overlap (không dịch xuyên khoảng không)
            rw = _inner_wall_r(th, W)
            if rw is not None:
                on_spiral = _spiral_r_at_theta(
                    GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th
                ) is not None
                wall_t = GUIDE_T if on_spiral else RAIL_T
                clear = 0.5 * wall_t + half + 0.15
                if abs(r - rw) <= clear + WALL_CAPTURE_TOL_MM:
                    r_out = rw + 0.5 * wall_t + half + 0.15
                    if r < r_out:
                        r = min(r_out, r_bowl)
                        contact = True

            # Hub
            r_min = 0.5 * HUB_D + half + 0.8
            if r < r_min - 1e-9:
                r = r_min
                contact = True

            # Tường θ CAD: vật ê_θ cắt tường nếu chồng r và z
            for fn in fences:
                if not _crossed_unwrapped(th_prev, th_unw, fn["th_deg"]):
                    continue
                r_hit = (r + half) >= fn["r_lo"] - 0.2 and (r - half) <= fn["r_hi"] + 0.2
                z_hit = z_h > fn["z_lo"] + 1e-9
                if not (r_hit and z_hit):
                    continue
                contact = True
                if fn["on_hit"] == "knock" and pose == "stand" and z_h > H - 0.05:
                    pose = "flat"
                    knocked = True
                    half = _half()
                    z_h = _zh()
                    r = _clamp(r, 0.5 * HUB_D + half + 0.8, CHANNEL_R_OUTER - half - 0.05)
                    continue
                if fn["on_hit"] == "slide_out":
                    r = min(fn["r_hi"] + half + 0.2, CHANNEL_R_OUTER - half - 0.05)
                    continue
                if fn["on_hit"] == "jam":
                    blocked_by = fn["name"]
                    th_unw = th_prev
                    th = th_unw % 360.0
                    break

            # Scraper trong lane: hạ viên đứng nếu cao hơn khe H
            if (
                pose == "stand"
                and z_h > H - 0.05
                and _ang_between(th, THETA_MOUTH_DEG - 1.0, THETA_EXIT_DEG + 1.0)
                and _in_lane(r, half)
            ):
                pose = "flat"
                knocked = True
                contact = True
                half = _half()
                z_h = _zh()
                r = _clamp(r, 0.5 * HUB_D + half + 0.8, CHANNEL_R_OUTER - half - 0.05)

        if contact:
            n_contact += 1
        else:
            n_free += 1
            dr_free = abs(r - r_prev)
            if dr_free > max_free_dr:
                max_free_dr = dr_free
            if dr_free > 1e-6:
                illegal_slip += 1

        # Trên đĩa: đáy z = DISC_TOP_Z tới khi rơi khỏi mép (r > DISC_R)
        z_bottom = DISC_TOP_Z
        off_disc = r > (DISC_R + 0.2)
        # Trên máng: tiếp xúc tới khi tâm viên qua mép đĩa (được nhô vành)
        on_face = (r <= DISC_R + 0.2) if in_chute else _on_disc_face(r, half)
        guides_lift = GAP0 <= DISC_TOP_Z + 0.2
        if on_face and not off_disc:
            n_disc += 1
            if abs(z_bottom - DISC_TOP_Z) > 1e-12 or guides_lift:
                n_disc_miss += 1
                if len(disc_miss_sample) < 8:
                    disc_miss_sample.append(
                        {
                            "step": step + 1,
                            "r": round(r, 2),
                            "th": round(th, 2),
                            "z_bottom": z_bottom,
                            "reason": "lifted" if guides_lift else "z_off_disc",
                        }
                    )
        elif not (in_chute and off_disc):
            n_disc_miss += 1
            if len(disc_miss_sample) < 8:
                disc_miss_sample.append(
                    {
                        "step": step + 1,
                        "r": round(r, 2),
                        "th": round(th, 2),
                        "z_bottom": z_bottom,
                        "reason": "xy_off_disc_before_rim",
                    }
                )

        if step % max(1, path_every) == 0:
            path.append((round(r, 2), round(th, 2), pose, int(contact), z_bottom))

        if (not entered_lane) and _in_lane(r, half) and _ang_between(th, THETA_MOUTH_DEG - 1.0, THETA_EXIT_DEG + 1.0):
            entered_lane = True

        if (not in_chute) and _crossed_unwrapped(th_prev, th_unw, THETA_EXIT_DEG) and _in_lane(r, half) and z_h <= H + 0.25:
            in_chute = True
            s_chute = 0.0

        disc_ok = n_disc_miss == 0 and n_disc > 0
        if in_chute and off_disc:
            return {
                "exited": True,
                "pose_exit": pose,
                "knocked_down": knocked,
                "steps": step + 1,
                "revs": round((step + 1) * dth_deg / 360.0, 3),
                "t_s": round((step + 1) * dt, 4),
                "r_end": round(r, 2),
                "th_end": round(th, 2),
                "n_contact": n_contact,
                "n_free": n_free,
                "illegal_slip": illegal_slip,
                "max_free_dr_mm": round(max_free_dr, 6),
                "max_dth_err_deg": round(max_dth_err_deg, 9),
                "omega_rad_s": omega,
                "n_disc_steps": n_disc,
                "n_disc_miss": n_disc_miss,
                "disc_contact_every_step": disc_ok,
                "z_bottom_mm": DISC_TOP_Z,
                "off_disc": True,
                "s_chute_mm": round(s_chute, 2),
                "entered_lane": True,
                "blocked_by": blocked_by,
                "disc_miss_sample": disc_miss_sample,
                "eq": "chute: s_dot=(omega*r)*(sin(beta)-mu_wall*cos(beta)); z=0 until r>DISC_R",
                "path": path,
            }

    return {
        "exited": False,
        "pose_exit": pose,
        "knocked_down": knocked,
        "steps": n_max,
        "revs": max_revs,
        "t_s": round(n_max * dt, 4),
        "r_end": round(r, 2),
        "th_end": round(th_unw % 360.0, 2),
        "n_contact": n_contact,
        "n_free": n_free,
        "illegal_slip": illegal_slip,
        "max_free_dr_mm": round(max_free_dr, 6),
        "max_dth_err_deg": round(max_dth_err_deg, 9),
        "omega_rad_s": omega,
        "n_disc_steps": n_disc,
        "n_disc_miss": n_disc_miss,
        "disc_contact_every_step": n_disc_miss == 0 and n_disc > 0,
        "z_bottom_mm": DISC_TOP_Z,
        "disc_miss_sample": disc_miss_sample,
        "eq": "free: r_dot=0, th_dot=omega, z=DISC_TOP_Z; contact: r:=r_wall+clear",
        "entered_lane": entered_lane,
        "blocked_by": blocked_by,
        "trapped": True,
        "path": path,
    }


def _sanity_case_wh(D: float, T: float) -> tuple[float, float]:
    """W,H vận hành: từ 2 mm đến (kích thước vật + 1 mm), kẹp [2, 26]."""
    w = _clamp(float(D) + PILL_CLEAR_XY, W_MIN, W_MAX)
    h = _clamp(float(T) + PILL_CLEAR_Z, H_MIN, H_MAX)
    return round(w, 3), round(h, 3)


def make_sanity_100_cases(n: int = SANITY_N, seed: int = SANITY_SEED) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []
    sizes = [
        (2.0, 2.0, "ball"),
        (3.0, 2.0, "tablet"),
        (4.0, 4.0, "ball"),
        (5.0, 2.5, "tablet"),
        (6.0, 3.0, "tablet"),
        (8.0, 4.0, "tablet"),
        (9.0, 9.0, "ball"),
        (10.0, 5.0, "tablet"),
        (12.0, 6.0, "tablet"),
        (15.0, 7.0, "tablet"),
        (18.0, 8.0, "tablet"),
        (20.0, 10.0, "tablet"),
        (22.0, 12.0, "tablet"),
        (24.0, 8.0, "tablet"),
        (25.0, 25.0, "ball"),
    ]

    def _add(D, T, shape, r, th, pose, tag):
        W, H = _sanity_case_wh(D, T)
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        rr = float(_clamp(r, r_lo, r_hi))
        cases.append(
            {
                "id": f"s{len(cases):03d}_{tag}",
                "D": round(float(D), 3),
                "T": round(float(T), 3),
                "shape": shape,
                "W": W,
                "H": H,
                "W_range": [W_MIN, round(float(D) + PILL_CLEAR_XY, 3)],
                "H_range": [H_MIN, round(float(T) + PILL_CLEAR_Z, 3)],
                "r0": round(rr, 3),
                "th0": round(float(th) % 360.0, 3),
                "pose0": "flat" if shape == "ball" else pose,
            }
        )

    # 30: lưới r × θ, size xoay vòng — phủ đĩa + nhiều vòng
    for i in range(30):
        D, T, shape = sizes[i % len(sizes)]
        pose = "stand" if shape == "tablet" and (i % 3 == 1) else "flat"
        half = 0.5 * (T if pose == "stand" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        u = (i % 5) / 4.0
        r = r_lo + u * (r_hi - r_lo)
        th = (i * 37.0) % 360.0
        _add(D, T, shape, r, th, pose, "grid")

    # 20: sát hub — phải đi nhiều vòng theo xoắn
    for i in range(20):
        D, T, shape = sizes[(i + 3) % len(sizes)]
        pose = "flat" if shape == "ball" or i % 2 == 0 else "stand"
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r = 0.5 * HUB_D + half + 3.0 + (i % 4)
        th = (i * 18.0 + 11.0) % 360.0
        _add(D, T, shape, r, th, pose, "hub")

    # 50: ngẫu nhiên (seed cố định)
    while len(cases) < n:
        if rng.random() < 0.35:
            s = rng.uniform(2.0, 25.0)
            D = T = s
            shape = "ball"
        else:
            D = rng.uniform(2.0, 25.0)
            T = rng.uniform(2.0, max(2.0, D))
            shape = "tablet"
        pose = "flat" if shape == "ball" or rng.random() < 0.55 else "stand"
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        r = rng.uniform(r_lo, r_hi)
        th = rng.uniform(0.0, 360.0)
        _add(D, T, shape, r, th, pose, "rnd")
    return cases[:n]


def simulate_rest_in_lane(
    D: float,
    T: float,
    W: float,
    H: float,
    th0: float,
    r0: float | None = None,
    omega: float = OMEGA_DISC,
    dt: float = 0.002,
    t_max: float | None = None,
) -> dict:
    """
    Vật đứng yên trong máng xếp hàng (v=0 thế giới). Đĩa quay → ma sát μ_disc*mg
    tăng v_θ tới no-slip; cửa ra F_dọc = μ_disc*mg*(sinβ − μ_wall cosβ) > 0.
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    r_i = CHANNEL_R_OUTER - W
    r = float(r0 if r0 is not None else 0.5 * (r_i + CHANNEL_R_OUTER))
    half = 0.5 * D
    r = _clamp(r, r_i + half + 0.2, CHANNEL_R_OUTER - half - 0.2)
    th_unw = float(th0)
    v = 0.0
    g_mm = 9810.0
    ep = exit_tangent_pose(W, H)
    ux, uy = ep["chute_dir"]
    ax, ay = ep["anchor_xy"]
    drive_net = float(ep["drive_net_friction"])
    in_chute = th_unw >= THETA_EXIT_DEG - 0.2
    s_chute = 0.0
    t = 0.0
    n_slip = n_stick = 0
    r_end = r
    th_end = th_unw % 360.0
    span = max(15.0, THETA_EXIT_DEG - th_unw + 25.0)
    if t_max is None:
        t_max = math.radians(span) / max(omega, 1e-6) + 3.0
    while t < t_max:
        if in_chute:
            a = MU_DISC * g_mm * max(0.0, drive_net)
            v += a * dt
            s_chute += max(0.0, v) * dt
            px = ax + s_chute * ux
            py = ay + s_chute * uy
            r_end = math.hypot(px, py)
            th_end = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            if r_end > DISC_R + 0.2:
                t_stick = (omega * r) / max(MU_DISC * g_mm, 1e-9)
                return {
                    "exited": True,
                    "t_s": round(t + dt, 4),
                    "s_chute_mm": round(s_chute, 2),
                    "r_end": round(r_end, 2),
                    "th_end": round(th_end, 2),
                    "n_slip_steps": n_slip,
                    "n_stick_steps": n_stick,
                    "v_exit_mm_s": round(v, 2),
                    "drive_net": drive_net,
                    "t_stick_s": round(t_stick, 4),
                    "omega": omega,
                    "started_at_rest": True,
                    "th0": th0,
                    "r0": round(r, 2),
                    "eq": "rest: a=mu_disc*g; chute a=mu_disc*g*(sinβ-mu_wall*cosβ)",
                }
        else:
            v_disc = omega * r
            slip = v_disc - v
            if abs(slip) > 2.0:
                v += math.copysign(MU_DISC * g_mm * dt, slip)
                if (v - v_disc) * slip < 0.0:
                    v = v_disc
                n_slip += 1
            else:
                v = v_disc
                n_stick += 1
            th_unw += math.degrees((v / max(r, 1.0)) * dt)
            th_end = th_unw % 360.0
            r_end = r
            if th_unw >= THETA_EXIT_DEG:
                in_chute = True
                th_e = _deg2rad(THETA_EXIT_DEG)
                etx, ety = -math.sin(th_e), math.cos(th_e)
                v = max(0.0, v * (etx * ux + ety * uy))
                s_chute = 0.0
        t += dt
    return {
        "exited": False,
        "t_s": round(t_max, 4),
        "s_chute_mm": round(s_chute, 2),
        "r_end": round(r_end, 2),
        "th_end": round(th_end, 2),
        "n_slip_steps": n_slip,
        "n_stick_steps": n_stick,
        "drive_net": drive_net,
        "started_at_rest": True,
        "th0": th0,
        "r0": round(r, 2),
        "trapped": True,
    }


def _shape_min_dist_mm(a: Part.Shape, b: Part.Shape) -> float:
    if not _shape_ok(a, 0.05) or not _shape_ok(b, 0.05):
        return 99.0
    try:
        d, _p, _i = a.distToShape(b)
        return float(d)
    except Exception:
        ov = _overlap_volume(a, b)
        return 0.0 if ov > 1e-4 else 99.0


def make_exit_arc_outer():
    return _box(0.1, 0.1, 0.1, 0, 0, 0)


def width_carriage_x_local(w):
    return W_MAX - _clamp(w, W_MIN, W_MAX)


def height_carriage_z(h):
    return height_scraper_z(h)


# `from mech_common import *` mac dinh BO QUA moi ten bat dau bang "_" (quy uoc
# private cua Python) — nhieu helper hinh hoc dung chung o day (_box, _cyl_z,
# _refine, _cyl_axis, _deg2rad, _clamp, ...) can duoc cac module part_*.py va
# tube_l_exit_gate.py wildcard-import duoc, nen export TAT CA ten module-level
# (ke ca "_"), tru cac dunder (__name__, __file__, ...).
__all__ = [_n for _n in dir() if not _n.startswith("__")]


