"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Entry_Gate_*        — cửa chỉnh chiều cao ở đầu máng vào (trụ + trượt + barrier)
  Entry_Gate_Barrier  — barrier chữ L (trần 20 mm + tấm đứng 10 mm); H 2–26 mm
  Funnel_Guide        — (cũ) → Center_Director: lưỡi cày TÂM đĩa, ép vật ra vành
  Outer_Rim_Funnel    — cánh ngoài thu hẹp vào lane
  Bowl_Tube_Exit_Chute — máng dốc 40° tại 9 giờ, đổ −Y ra Front; cạnh TRÁI của
                        lòng máng trùng mép đĩa (x = −DISC_R), thân máng luồn
                        dưới đĩa để hứng viên vừa rời vành

THAO TÁC CHỈNH (tay với từ trên — giống video):
  W: KHÔNG chỉnh được — luồng cố định = họng ra Guide_System (ENTRANCE_W)
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
WALL_T = 2.0  # thành bát — theo yêu cầu, mọi vách kể cả thành bát đều 2 mm
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

# Cỡ vật lớn nhất máy nhận = họng ra Guide_System (ENTRANCE_W = 20 mm thông
# thuỷ tính từ mép đĩa). Lane KHÔNG còn chỉnh W (Inner_Lane_Rail/Chute_Slide đã
# bỏ) — W nay là bề rộng CỐ ĐỊNH của luồng, chỉ H còn chỉnh bằng Entry_Gate_*.
W_MAX = 20.0  # = ENTRANCE_W; bề rộng luồng cố định
H_MAX = 20.0  # chỉnh H: 2–20 mm
W_MIN = 2.0  # dải cỡ vật: 2–20 mm
H_MIN = 2.0
# Máng lane + exit: rộng cố định, một thành trong cao 30 mm (ngoài = vành bát).
CHUTE_W_MM = 30.0
CHUTE_WALL_H_MM = 30.0
# Outer of free lane = inner face of bowl rim (video: white ring)
CHANNEL_R_OUTER = BOWL_IR
CHUTE_DISC_GUIDE_CLEAR = 0.35
# Cơ cấu W: chỉnh độ hẹp họng đầu vào + vị trí trượt máng.
INLET_DEFLECTOR_ALONG = 14.0
INLET_DEFLECTOR_UPSTREAM = 4.0
INLET_DEFLECTOR_BEVEL_DEG = 38.0
INLET_WING_R_GAP = 0.8
# BỀ DÀY VÁCH CHUẨN — MỌI vách đều 2 mm: Guide (vách xoắn + vành tròn),
# Exit_Inner_Wall 1/2, barrier cửa H, thành máng thoát, và cả THÀNH BÁT
# (WALL_T ở trên). Đổi một chỗ này là đổi toàn bộ.
WALL_STD_T = 2.0
RAIL_T = WALL_STD_T
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
SCRAPER_T = WALL_STD_T  # tấm barrier cửa H
STEM_FIT = 0.25
KNOB_D = 11.0
KNOB_L = 5.0

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
# Hình học Exit_Inner_Wall — đặt SỚM vì góc cửa chỉnh H bám theo đầu vách này.
EXIT_WALL_OFFSET_MM = 20.0  # 2 cm, phương ngang, tính từ 9 giờ vào tâm
EXIT_WALL_X = -(DISC_R - EXIT_WALL_OFFSET_MM)  # −80.0 — mặt hướng luồng
EXIT_WALL_Y_RIM = -math.sqrt(max(0.0, DISC_R ** 2 - EXIT_WALL_X ** 2))   # −60.0
EXIT_WALL_Y_RIM_TOP = -EXIT_WALL_Y_RIM  # +60.0
# Đầu TRÊN của vách 1 nằm đúng trên mép đĩa — đó là chỗ vật đang bám vành bị
# hớt vào kênh, tức CỬA MÁNG do hai vách exit tạo ra.
EXIT_CHANNEL_MOUTH_TH_DEG = math.degrees(math.atan2(EXIT_WALL_Y_RIM_TOP, EXIT_WALL_X))  # 143.13°

# VỊ TRÍ GÓC: NGAY TRƯỚC cửa máng do Exit_Inner_Wall và Exit_Inner_Wall_2 tạo.
#   Vật bám vành bát chạy CCW; tới θ = 143.13° thì mặt ngoài vách 1 chạm đúng
#   mép đĩa nên đầu vách hớt vật vào kênh giữa hai vách. Cửa chỉnh H phải sàng
#   vật NGAY TRƯỚC đó: mép hạ lưu của trần đặt cách đầu vách GATE_MARGIN_DEG,
#   trần trải 20 mm (≈11.5°) ngược dòng — toàn bộ nằm ở θ < 143°, chỗ mặt đĩa
#   còn trống nên không đụng vách nào.
#   Biên 3° chứ không phải 1.5°: đầu vách 1 được cắt tới MẶT BÁT (r=100.8) nên
#   vật liệu của nó vươn ngược lên tận θ≈142.5°, sớm hơn mốc mép đĩa 143.13°;
#   thêm nữa barrier là TẤM THẲNG nên hai góc của nó nhô quá đường xuyên tâm.
GATE_MARGIN_DEG = 3.0
GATE_TH_DEG = EXIT_CHANNEL_MOUTH_TH_DEG - GATE_MARGIN_DEG  # ≈140.13° — mép SAU của trần
GATE_R_OUT = DISC_R - CHUTE_DISC_GUIDE_CLEAR  # cạnh ngoài ôm sát mép đĩa
GATE_W_MM = 40.0  # bề rộng XUYÊN TÂM (tâm → vành đĩa) nhìn từ trên
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
# Ray T ĐỨNG nằm ở MẶT TRONG thành bát: sống ray tì thẳng vào BOWL_IR, bích
# quay vào tâm. Trước đây ray nằm NGOÀI bát (BOWL_OR+0.8) và tay với phải bắc
# qua vành; nay tay với ngắn hẳn vì con trượt đã ở ngay trên lane.
GATE_RAIL_FLANGE_T = 3.5
GATE_RAIL_FLANGE_W = 16.0
GATE_RAIL_NECK_T = 4.5
GATE_RAIL_NECK_W = 7.0
GATE_RAIL_SPINE_T = 8.0
GATE_RAIL_SPINE_W = 16.0
GATE_RAIL_R0 = BOWL_IR - (GATE_RAIL_FLANGE_T + GATE_RAIL_NECK_T + GATE_RAIL_SPINE_T)  # 84.8
GATE_COLLAR_H = 14.0
GATE_COLLAR_WALL = 4.0
GATE_FIT = STEM_FIT
# Chân ray phải bắt đầu TRÊN đỉnh barrier ở H lớn nhất (GAP0+H_MAX+ROOF_T+
# WALL_H = 32.9), nếu không sống ray cắt vào chính barrier — hệ quả trực tiếp
# của việc đưa ray vào trong bát. Chỉ còn 33.9→BOWL_H = 6.1 mm để bắt bu-lông,
# nên 2 vít M3 phải nằm CẠNH NHAU theo chu vi thay vì chồng lên nhau.
GATE_FOOT_Z0 = GAP0 + H_MAX + GATE_ROOF_T + GATE_WALL_H_MM + 1.0  # 33.9
GATE_FOOT_T = 4.0
GATE_FOOT_W = 20.0
GATE_ROOF_DEG = math.degrees(GATE_ROOF_ALONG_MM / GATE_R_OUT)
# Khung cục bộ của cụm cửa: gốc góc = mép ĐÓN VẬT của trần; local +x = xuyên
# tâm, +y = xuôi dòng (mm cung), +z = lên.
GATE_FRAME_TH_DEG = GATE_TH_DEG - GATE_ROOF_DEG

# Guide_System cố định — xoắn hub→vành; HỌNG LANE mở theo CCW (lực tiếp tuyến)
# Tip Guide DỪNG trước θ_mouth → khe góc + khe bán kính với Bowl = lối vào nhìn thấy
# HỌNG RA Guide_System = khe THÔNG THUỶ 20 mm, đo từ MÉP ĐĨA (r = DISC_R) tới
# MẶT NGOÀI tường xoắn. Cách đo cũ (tâm tường → thành bát BOWL_IR) làm cửa danh
# nghĩa 26 mm nhưng lọt thật chỉ 23.75 mm vì tường dày GUIDE_T.
# Đây cũng là bề rộng luồng cố định sau khi bỏ Inner_Lane_Rail ⇒ ENTRANCE_W = W_MAX.
ENTRANCE_W = 20.0
# Dung sai "bắt được tường" trong simulate_pill_mechanics (viên phải nằm cách
# tường không quá clear+TOL để coi là chạm). 0.35mm cũ để lại một dải chết hẹp
# ~1.2mm sát trục cho viên rất nhỏ (D=2mm): r0 ∈ [hub-touch, GUIDE_R0-clear)
# không bao giờ được xoắn Guide "vợt" vào — viên quay mãi không thoát (đã phát
# hiện bằng quét toàn dải bán kính, hồi còn bộ verify).
# 2.0mm đủ đóng dải chết ở mọi D 2–25mm (đã verify), vẫn nhỏ so R0=20mm nên
# không đổi hành vi bắt/không-bắt ở các vị trí xa tường khác.
WALL_CAPTURE_TOL_MM = 2.0
GUIDE_T = WALL_STD_T  # bề dày vách xoắn
# ---------------------------------------------------------------------------
# Guide_System = (1) VÒNG TRÒN ở tâm, đường kính chuẩn hoá 35 mm
#                (2) VÁCH ĐỊNH HƯỚNG xoắn ARCHIMEDES (r tuyến tính theo θ)
#                    mọc từ đúng vòng tròn đó, quét ra tới khi ĐẦU RA cách mép
#                    đĩa đúng ENTRANCE_W = 20 mm (mặt ngoài ở r = 80).
# LƯU Ý: xoắn Archimedes KHÔNG tiếp tuyến với vòng tròn tại chỗ mọc — với
# r0=25, r1=79 trên 182° thì dr/dθ = 17.0 mm/rad nên vách rời vòng tròn dưới
# góc atan((dr/dθ)/r0) ≈ 34°. Muốn mọc đúng tiếp tuyến phải đổi luật xoắn
# (vd. r ~ u² để dr/dθ = 0 tại gốc), không còn là Archimedes nữa.
# ---------------------------------------------------------------------------
GUIDE_CIRCLE_D = 50.0                    # đường tròn tâm (5 cm) — ĐƯỜNG KÍNH NGOÀI
GUIDE_RING_T = GUIDE_T                   # 2.0 — vành tròn mỏng như vách
GUIDE_CIRCLE_ID = GUIDE_CIRCLE_D - 2.0 * GUIDE_RING_T   # 46.0 — lòng để trống
GUIDE_R_OUT = DISC_R - ENTRANCE_W        # 80.0 — bán kính LỚN NHẤT của đầu ra
GUIDE_R0 = 0.5 * GUIDE_CIRCLE_D          # 25.0 — vách mọc từ vòng tròn tâm
GUIDE_R1 = GUIDE_R_OUT - 0.5 * GUIDE_T   # 79.0 — tim vách tại đầu ra
GUIDE_TH0 = THETA_MOUTH_DEG - 200.0      # −110°
GUIDE_TH1 = THETA_MOUTH_DEG - 18.0       # 72° — góc đầu ra (giữ như cũ)
# KHÔNG bích chữ T: mặt trên vách rộng đúng bằng bề dày vách (GUIDE_T = 2 mm),
# nên vách là tấm phẳng đều từ đáy tới đỉnh. _spiral_tee_wall tự bỏ bích khi
# flange_w <= web_t + 0.5.
GUIDE_FLANGE_W = GUIDE_T
GUIDE_FLANGE_T = 0.0
GUIDE_H = H_MAX + 8.0
DIR_CLAMP_S = 0.0
DIR_CLAMP_L = 36.0
DIR_CLAMP_W = 22.0
DIR_CLAMP_H = 14.0
DIR_SCREW_SPAN = 16.0
DIR_STEM = 12.0
DIR_HUB_D = GUIDE_CIRCLE_D  # 35.0 — đường tròn tâm đã chuẩn hoá
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
# Cửa vào (góc): từ tip Guide → θ_mouth — trống để thấy họng
ENTRANCE_TH0 = GUIDE_TH1
ENTRANCE_TH1 = THETA_MOUTH_DEG + 10.0

# Cuối Inner_Lane_Rail: bóc theo máng. Không hàng rào phía tâm (chặn vật quay vòng vào lane).
EXIT_GUARD_INBOARD = 0.0
EXIT_GUARD_ALONG = 22.0
EXIT_GUARD_T = RAIL_T
EXIT_GUARD_H = RAIL_H
EXIT_PEEL_PAST_RIM = 20.0  # tường trong máng nhô quá mép đĩa (máng ngắn 50 mm)

# ---------------------------------------------------------------------------
# VÁCH TRONG CỬA RA (Exit_Inner_Wall) — nhìn từ TOP
# ---------------------------------------------------------------------------
# Bắt đầu tại 9 giờ (θ=180°, y=0), lùi vào TÂM 2 cm theo phương ngang:
#   x = −(DISC_R − EXIT_WALL_OFFSET) = −80  ← đúng bờ trong của luồng 20 mm
# rồi chạy XUỐNG (−Y, tức xuôi dòng CCW ra cửa) tới khi CHẠM VÀNH ĐĨA:
#   x² + y² = DISC_R²  →  y = −√(100² − 80²) = −60 mm
# Đầu vách được cắt bằng trụ BOWL_IR nên mặt cuối là cung ôm khít thành bát —
# đó cũng là chỗ duy nhất vách có điểm tựa để bắt/dán.
# Mặt hướng luồng nằm đúng x = −80, thân vách dày về phía TÂM (x ∈ [−80, −77])
# nên lòng luồng x ∈ [−100, −80] vẫn trống nguyên 20 mm.

# Vách kéo dài LÊN TRÊN (+Y) tới khi cắt vành đĩa phía trên: y = +60 (θ≈143.1°).
# Vậy vách là DÂY CUNG đầy đủ của đĩa tại x = −80, dài 120 mm giữa hai mép,
# hai đầu cắt bằng trụ BOWL_IR nên đều ôm khít thành bát.
EXIT_WALL_T = WALL_STD_T
EXIT_WALL_H = CHUTE_WALL_H_MM  # 30.0 — bằng các vách lane khác

# VÁCH THỨ 2 — song song vách trên, đỉnh cách đỉnh 2 cm (lùi tiếp vào tâm):
#   x = −60; chạy xuống tới vành đĩa tại y = −√(100² − 60²) = −80
#   rồi THÒ RA thêm 2 cm → y = −100 (r = 116.6, đã ra ngoài đĩa lẫn thành bát)
# Đoạn thò ra cắt qua vành bát tại θ ≈ 233–235°, NGOÀI khe thoát của bát
# ([179.2°, 219.0°]) — nên Bowl_Tube phải khoét một rãnh xuyên đúng tiết diện
# vách (xem bowl_wall2_slot_geo) thì vách mới đi qua được.
# ---------------------------------------------------------------------------
# CƠ CẤU TỊNH TIẾN CHỈNH BỀ RỘNG KÊNH EXIT
# ---------------------------------------------------------------------------
# Exit_Inner_Wall đứng yên; Exit_Inner_Wall_2 TRƯỢT theo +X trên 2 ray T nằm
# ngang (Exit_Slide) để đổi bề rộng thông thuỷ giữa hai vách:
#     gap = x2 − (EXIT_WALL_X + EXIT_WALL_T)      (x2 = mặt trong vách 2)
# Ray gắn vào mặt trong Bowl_Tube, chạy vào tâm theo +X, nằm CAO hơn đỉnh vách
# nên không cản vật; con trượt mọc từ đỉnh vách 2 lên ôm bích ray.
EXIT_GAP_MIN = 2.0
EXIT_GAP_MAX = 20.0          # = W_MAX — bằng họng ra Guide_System
EXIT_GAP_DEFAULT = 17.0      # vị trí hiện tại (x2 = −60)
EXIT_WALL2_PAST_RIM_MM = 20.0  # thò ra quá vành đĩa
EXIT_WALL2_X = EXIT_WALL_X + EXIT_WALL_T + EXIT_GAP_DEFAULT  # −60.0
EXIT_WALL2_Y_RIM = -math.sqrt(max(0.0, DISC_R ** 2 - EXIT_WALL2_X ** 2))  # −80.0
EXIT_WALL2_Y_END = EXIT_WALL2_Y_RIM - EXIT_WALL2_PAST_RIM_MM  # −100.0
EXIT_WALL2_SLOT_FIT = 0.4  # khe lắp mỗi bên khi khoét bát

# Bao trùm HÀNH TRÌNH: bát phải hở suốt dải vách 2 có thể tới
EXIT_WALL2_X_MIN = EXIT_WALL_X + EXIT_WALL_T + EXIT_GAP_MIN   # −75.0
EXIT_WALL2_X_MAX = EXIT_WALL_X + EXIT_WALL_T + EXIT_GAP_MAX   # −57.0

# 2 ray T nằm ngang (+X), neo vào mặt trong bát tại hai cao độ y này.
# Giới hạn |y|: ở gap NHỎ NHẤT con trượt lùi xa nhất tới x = −82.5; góc ngoài
# của nó phải còn trong lòng bát ⇒ |y_ray| + nửa bề rộng trượt (7.35) < 57.9,
# tức |y_ray| < 50.6. Lấy 45 để dư ~3 mm.
EXIT_SLIDE_Y = (-20.0, -45.0)
EXIT_SLIDE_X_IN = -45.0                            # đầu trong của ray
EXIT_SLIDE_T_BODY_Z0 = GAP0 + EXIT_WALL_H + 11.5   # 42.0 — trên đỉnh vách
EXIT_SLIDE_RAIL_W = 6.0
EXIT_SLIDE_RAIL_H = 5.0
EXIT_SLIDE_T_NECK_W = 4.0
EXIT_SLIDE_T_NECK_H = 3.2
EXIT_SLIDE_T_FLANGE_W = 9.0
EXIT_SLIDE_T_FLANGE_H = 2.4
EXIT_SLIDE_SHOE_LEN = 18.0
EXIT_SLIDE_FIT = 0.35                              # khe trượt mỗi bên
EXIT_SLIDE_BOWL_EMBED = 3.0                        # ray cắm vào bát để bắt chặt

# Máng thoát ngắn 50 mm (phần nhô ngoài mép đĩa / chiều dài dốc).
EXIT_CHUTE_LEN_MM = 50.0
EXIT_TRACK_LEN = DISC_R + EXIT_CHUTE_LEN_MM  # envelope dựng tường tới chỗ cắt vành + stub

# ---------------------------------------------------------------------------
# MÁNG THOÁT NẰM DƯỚI KÊNH GIỮA HAI VÁCH EXIT
# ---------------------------------------------------------------------------
# Vật KHÔNG còn rời đĩa ở mép 9 giờ nữa: nó chạy trong kênh hẹp giữa
# Exit_Inner_Wall (mặt trong x = −77) và Exit_Inner_Wall_2 (mặt trong x = −57…−75
# tuỳ gap) theo −Y, rời đĩa khi vành đĩa lùi khỏi nó. Vậy máng phải nằm ngay
# DƯỚI kênh đó, rộng đúng 2 cm = bề rộng kênh lớn nhất (EXIT_GAP_MAX):
#     lòng máng x ∈ [−77, −57]  ← trùng mặt trong vách 1 → hết hành trình vách 2
# Mép trái lòng máng thẳng hàng mặt trong vách 1 nên vật đi từ kênh xuống máng
# không vấp bậc.
EXIT_CHUTE_W_MM = 20.0                                    # 2 cm
EXIT_CHUTE_X0 = EXIT_WALL_X + EXIT_WALL_T                 # −77.0 — mép trái lòng máng
EXIT_CHUTE_X1 = EXIT_CHUTE_X0 + EXIT_CHUTE_W_MM           # −57.0 — mép phải lòng máng
# Bắt đầu hứng khi vật CÒN trên đĩa (máng luồn dưới đĩa) — sớm hơn điểm rời đĩa
# sớm nhất trong kênh (x = −77 → y = −63.7) một quãng.
EXIT_CHUTE_Y_START = -55.0
# Điểm rời đĩa MUỘN nhất trong kênh = mép phải lòng máng.
EXIT_CHUTE_Y_LEAVE = -math.sqrt(max(0.0, DISC_R ** 2 - EXIT_CHUTE_X1 ** 2))   # −82.2
# Chỗ máng chui khỏi vành bát ở mép phải (xa nhất theo −Y).
EXIT_CHUTE_Y_BOWL = -math.sqrt(max(0.0, BOWL_OR ** 2 - EXIT_CHUTE_X1 ** 2))   # −86.6
EXIT_CHUTE_PAST_BOWL_MM = 20.0  # nhô ra ngoài vành bát để đổ vào cụm hứng
EXIT_TRACK_WALL = WALL_STD_T
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
# ĐẶT MÁNG: từ khi có kênh exit (hai vách song song ở 9h), viên KHÔNG rời đĩa ở
# mép 9 giờ nữa mà chạy trong kênh theo −Y rồi rời đĩa ở y ≈ −64…−82. Lòng máng
# vì thế nằm ĐÚNG DƯỚI KÊNH — x ∈ [−77, −57], rộng 2 cm — chứ không còn bám mép
# đĩa x = −DISC_R (xem khối EXIT_CHUTE_* ở trên).
RAMP_ANGLE_DEG = 40.0
RAMP_FLOOR_T = WALL_STD_T
RAMP_WALL_T = WALL_STD_T
RAMP_DISC_GAP = 1.0  # khe đáy đĩa → mặt máng (đĩa quay, máng đứng yên)
RAMP_CATCH_MARGIN = 8.0  # phủ thêm sau điểm rời đĩa xa nhất (lane rộng nhất)
RAMP_START_DROP = 0.0
RAMP_SIDE_CLEAR = 0.6
RAMP_TAKEOVER_OVERLAP = 6.0  # máng phẳng chồng đầu dốc chừng này rồi mới hết

# Máng ra = khẩu độ chỉnh (W×H); khi set pill: W=D+1, H=T+1
# EXIT_TRACK_W giữ alias legacy — kích thước thật của máng = EXIT_CHUTE_W_MM
EXIT_TRACK_W = EXIT_CHUTE_W_MM
# Mép vào máng sát mặt phẳng θ_exit của lane (không lệch ra BOWL_OR)
EXIT_X0_ALONG = 0.0
# Nối lane → máng ra: Hermite G1 (không góc gãy a2/b2)

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
    for u_ft in (0.55, 0.95):
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
    th_c = GATE_TH_DEG - 0.5 * GATE_ROOF_DEG  # giữa cửa
    # Ray nay nam trong bat: chi con GATE_FOOT_Z0 -> dinh bat (~6 mm) de bat vit,
    # khong du xep 2 lo chong nhau => tach ra hai ben theo CHU VI.
    z = 0.5 * (GATE_FOOT_Z0 + (BOWL_Z0 + BOWL_H))
    d_half = math.degrees(0.5 * GATE_FOOT_W / BOWL_IR)
    r0 = GATE_RAIL_R0 + GATE_RAIL_FLANGE_T + GATE_RAIL_NECK_T - 2.0
    for dth in (-d_half, d_half):
        th = th_c + dth
        c, s_ = math.cos(_deg2rad(th)), math.sin(_deg2rad(th))
        out.append({
            "origin": (r0 * c, r0 * s_, z),
            "axis": (c, s_, 0.0),
            "h": (BOWL_OR + 4.0) - r0,
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
    ap = lane_aperture(width_open)
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


def lane_aperture(width_open: float | None = None) -> dict:
    """Luồng CỐ ĐỊNH bám mép đĩa, rộng đúng họng ra Guide_System.

    Không còn Inner_Lane_Rail/Chute_Slide nên không có vách trong vật lý và
    không trượt được: dải [DISC_R − ENTRANCE_W, DISC_R] chính là chỗ tường xoắn
    Guide thả vật ra, vật bị đĩa + ly tâm ép ra thành bát rồi chạy tới cửa ra.
    width_open chỉ còn là CỠ VẬT (kẹp 2–20) để các hàm cũ dùng chung chữ ký.
    """
    w_cmd = _clamp(W_MAX if width_open is None else width_open, WIDTH_MIN, WIDTH_MAX)
    r_outer = DISC_R
    r_inner = DISC_R - ENTRANCE_W
    h = CHUTE_WALL_H_MM
    return {
        "width_mm": ENTRANCE_W,
        "width_cmd_mm": w_cmd,
        "slide_mm": 0.0,
        "height_mm": h,
        "r_inner": r_inner,
        "r_outer": r_outer,
        "disc_guide_r_mm": DISC_R - CHUTE_DISC_GUIDE_CLEAR,
        "z0": GAP0,
        "z1": GAP0 + h,
        "theta_mouth_deg": THETA_MOUTH_DEG,
        "theta_exit_deg": THETA_EXIT_DEG,
        "arc_deg": CHUTE_ARC_DEG,
        "fixed": True,
    }


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
    th1 = GATE_TH_DEG            # mép SAU (hạ lưu) — đúng 11 giờ
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

    W: KHÔNG còn chỉnh được (Inner_Lane_Rail/Chute_Slide đã bỏ) — bề rộng luồng
    cố định = ENTRANCE_W, do họng ra Guide_System đặt.
    H: hạ/nâng Entry_Gate_Slider trên ray T đứng ở 11h (1 mm = 1 mm)."""
    ap = lane_aperture(width_open)
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    g = entry_gate_geo(h)
    z1 = g["z_roof0_mm"]
    return {
        "W": w,
        "H": h,
        "lane_w_mm": ap["width_mm"],
        "lane_fixed": True,
        "r_inner_mm": ap["r_inner"],
        "r_outer_mm": ap["r_outer"],
        "z_gate_roof_mm": round(z1, 6),
        "z_gate_arm_mm": round(g["z_arm0_mm"], 6),
        "theta_gate_deg": GATE_TH_DEG,
        "eq_W": "lane_w = ENTRANCE_W (co dinh, khong con co cau truot)",
        "eq_H": "H = z_roof0 - GAP0 (khe duoi tran barrier)",
        "check_lane_w": abs(ap["width_mm"] - ENTRANCE_W) < 1e-9,
        "check_H_from_z": abs((z1 - GAP0) - h) < 1e-9,
        "check_no_slide": abs(ap["slide_mm"]) < 1e-9,
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
            # Thông thuỷ THẬT: mặt ngoài tường xoắn → mép đĩa / thành bát
            "clear_to_disc_rim_mm": round(DISC_R - (GUIDE_R1 + 0.5 * GUIDE_T), 3),
            "clear_to_bowl_wall_mm": round(CHANNEL_R_OUTER - (GUIDE_R1 + 0.5 * GUIDE_T), 3),
            "visible_gap_mm": round(DISC_R - (GUIDE_R1 + 0.5 * GUIDE_T), 2),
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


def exit_wall2_x(gap_mm: float | None = None) -> float:
    """Mặt trong vách 2 ứng với bề rộng thông thuỷ gap."""
    g = EXIT_GAP_DEFAULT if gap_mm is None else _clamp(
        float(gap_mm), EXIT_GAP_MIN, EXIT_GAP_MAX)
    return EXIT_WALL_X + EXIT_WALL_T + g


def exit_wall2_geo(gap_mm: float | None = None) -> dict:
    """Toạ độ vách 2 theo bề rộng khe."""
    x2 = exit_wall2_x(gap_mm)
    y_rim = -math.sqrt(max(0.0, DISC_R ** 2 - x2 ** 2))
    return {
        "gap_mm": x2 - (EXIT_WALL_X + EXIT_WALL_T),
        "x_in": x2,
        "x_out": x2 + EXIT_WALL_T,
        "y_rim": y_rim,
        "y_end": y_rim - EXIT_WALL2_PAST_RIM_MM,
        "slide_mm": x2 - EXIT_WALL2_X,
    }


def exit_slide_rail_x_bowl(y_mm: float) -> float:
    """Mặt trong Bowl_Tube tại cao độ y — gốc neo của ray."""
    return -math.sqrt(max(1.0, BOWL_IR ** 2 - float(y_mm) ** 2))


def exit_channel_slot_geo() -> dict:
    """Cửa DUY NHẤT trên thành bát = đúng khoảng trống giữa hai vách exit.

    Thành bát được làm LIỀN toàn bộ (không còn khe cung cũ ở θ 179–219°); chỗ hở
    duy nhất là dải thẳng x ∈ [mặt trong vách 1, mặt ngoài vách 2] chạy theo −Y
    xuyên qua vành bát, tức đúng lòng kênh mà vật đi.
    """
    x_lo = EXIT_WALL_X + EXIT_WALL_T          # −77.0 — mặt trong vách 1
    x_hi = EXIT_WALL2_X_MAX + EXIT_WALL_T     # −54.0 — bao hết hành trình vách 2
    return {
        "x0": x_lo,
        "dx": x_hi - x_lo,             # 23.0 mm — phủ toàn dải chỉnh
        "y0": -(BOWL_OR + 10.0),
        "dy": BOWL_OR + 10.0,          # tới y = 0
        "z0": BOWL_Z0 - 1.0,
        "dz": (GAP0 + EXIT_WALL_H) - (BOWL_Z0 - 1.0),  # hở hết chiều cao kênh
    }


def make_exit_channel_slot_cutter() -> Part.Shape:
    g = exit_channel_slot_geo()
    return _box(g["dx"], g["dy"], g["dz"], g["x0"], g["y0"], g["z0"])


def exit_wall2_slot_geo() -> dict:
    """Rãnh xuyên trên Bowl_Tube để Exit_Inner_Wall_2 thò ra 2 cm quá vành đĩa.

    Đoạn thò ra nằm ở θ≈233–235°, ngoài khe thoát của bát, nên bát phải được
    khoét đúng tiết diện vách + khe lắp EXIT_WALL2_SLOT_FIT mỗi bên.
    """
    fit = EXIT_WALL2_SLOT_FIT
    return {
        "x0": EXIT_WALL2_X_MIN - fit,
        "dx": (EXIT_WALL2_X_MAX + EXIT_WALL_T) - EXIT_WALL2_X_MIN + 2.0 * fit,
        "z0": GAP0 - fit,
        "dz": EXIT_WALL_H + 2.0 * fit,
        "y_start": EXIT_WALL2_Y_RIM - 0.5,
        "dy": abs(EXIT_WALL2_Y_END - EXIT_WALL2_Y_RIM) + 30.0,
    }


def make_exit_wall2_slot_cutter() -> Part.Shape:
    g = exit_wall2_slot_geo()
    return _box(g["dx"], g["dy"], g["dz"], g["x0"], g["y_start"] - g["dy"], g["z0"])


def exit_wall2_travel_geo() -> dict:
    """Hộp bao TOÀN BỘ hành trình của vách 2 (mọi gap, kể cả đuôi thò quá vành).

    Dùng để gọt vách máng thoát: máng đứng yên còn vách 2 trượt ngang bên trên
    nó, nên chỗ nào máng cao lên tới cao độ vách thì phải khoét đi.
    """
    fit = EXIT_WALL2_SLOT_FIT
    # đuôi vách xa nhất theo −Y ứng với gap lớn nhất (x_in = EXIT_WALL2_X_MAX)
    y_far = -math.sqrt(max(0.0, DISC_R ** 2 - EXIT_WALL2_X_MAX ** 2)) \
        - EXIT_WALL2_PAST_RIM_MM
    return {
        "x0": EXIT_WALL2_X_MIN - fit,
        "dx": (EXIT_WALL2_X_MAX + EXIT_WALL_T) - EXIT_WALL2_X_MIN + 2.0 * fit,
        "y0": y_far - 5.0,
        "dy": abs(y_far - 5.0),          # tới y = 0
        "z0": GAP0 - fit,
        "dz": EXIT_WALL_H + 20.0,
    }


def make_exit_wall2_travel_cutter() -> Part.Shape:
    g = exit_wall2_travel_geo()
    return _box(g["dx"], g["dy"], g["dz"], g["x0"], g["y0"], g["z0"])


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


def _inner_wall_r(th_deg: float, width_open: float) -> float | None:
    """Tâm tường đẩy +r tại θ. Chỉ còn xoắn Guide_System.

    Sau tip Guide (θ > GUIDE_TH1) KHÔNG còn vách trong nào: Inner_Lane_Rail đã
    bỏ, vật giữ nguyên r mà tường xoắn thả ra (r ≥ DISC_R − ENTRANCE_W) rồi chạy
    theo vành tới cửa ra. None = không tường.
    """
    _ = width_open
    return _spiral_r_at_theta(GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th_deg)


def _unit2(x: float, y: float) -> tuple[float, float]:
    n = math.hypot(x, y) or 1.0
    return (x / n, y / n)


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
    """Máng chạy theo −Y từ EXIT_CHUTE_Y_START tới quá điểm rời đĩa muộn nhất
    trong kênh VÀ ra khỏi vành bát một đoạn EXIT_CHUTE_PAST_BOWL_MM."""
    y_end = max(abs(EXIT_CHUTE_Y_LEAVE) + RAMP_CATCH_MARGIN,
                abs(EXIT_CHUTE_Y_BOWL) + EXIT_CHUTE_PAST_BOWL_MM)
    return y_end - abs(EXIT_CHUTE_Y_START)


def ramp_geo(width_open: float, height_open: float) -> dict:
    """Máng nghiêng 40°, đổ −Y (ra Front), có đáy — HỨNG DƯỚI KÊNH EXIT.

    Lòng máng rộng đúng 2 cm (EXIT_CHUTE_W_MM), x ∈ [−77, −57]: mép trái thẳng
    hàng MẶT TRONG Exit_Inner_Wall, mép phải phủ hết hành trình
    Exit_Inner_Wall_2. Máng luồn DƯỚI đĩa (cách đáy đĩa RAMP_DISC_GAP) và bắt
    đầu trước điểm rời đĩa sớm nhất, nên viên nào đi hết kênh cũng rơi thẳng
    xuống lòng máng.
    """
    _ = width_open, height_open
    ux, uy = 0.0, -1.0
    x0, y0 = EXIT_CHUTE_X0, EXIT_CHUTE_Y_START  # mép trái lòng máng = mặt trong vách 1
    a = _deg2rad(RAMP_ANGLE_DEG)
    run = ramp_catch_run_mm()
    L = run / math.cos(a)
    drop = L * math.sin(a)
    w = EXIT_CHUTE_W_MM
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
        "under_exit_channel": True,
        "channel_x_mm": (EXIT_WALL_X + EXIT_WALL_T, EXIT_WALL2_X_MAX),
        "leave_y_mm": (-math.sqrt(max(0.0, DISC_R ** 2 - EXIT_CHUTE_X0 ** 2)),
                       EXIT_CHUTE_Y_LEAVE),
        "under_disc_gap_mm": RAMP_DISC_GAP,
        "wall_h_mm": CHUTE_WALL_H_MM,
        "slides": math.tan(a) > MU_WALL,
        "self_lock_deg": math.degrees(math.atan(MU_WALL)),
        "on_disc": False,
        "clock_h": 9,
        "heading_front": True,
    }


def make_bowl_exit_chute(_width_open: float | None = None, _height_open: float | None = None) -> Part.Shape:
    """Máng nghiêng 40° có đáy — child của Bowl_Tube, hứng dưới kênh exit.

    Dựng ở gốc: +x = dọc máng (chưa nghiêng), +y = hướng vào TÂM đĩa sau khi
    quay. Lòng máng y ∈ [0, w]; vách trái y ∈ [−t, 0] nên MẶT TRONG của nó nằm
    đúng x = EXIT_CHUTE_X0 (= mặt trong Exit_Inner_Wall) sau khi đặt.
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
    # Vách 2 TRƯỢT ngang ngay trên máng (đuôi thò quá vành đĩa nằm đúng trong
    # lòng máng) → gọt mọi phần vách máng cao tới cao độ hành trình của nó.
    try:
        cut = body.cut(make_exit_wall2_travel_cutter())
        if _shape_ok(cut, 200.0):
            body = cut
    except Exception:
        pass
    return _refine(body)


def make_exit_ramp(width_open: float, height_open: float) -> Part.Shape:
    """Alias — Bowl_Tube_Exit_Chute."""
    return make_bowl_exit_chute(width_open, height_open)


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
    Quỹ đạo rời rạc trên đĩa. Guide đẩy ra vành; luồng CỐ ĐỊNH [DISC_R−ENTRANCE_W,
    DISC_R] giữ vật (không còn Inner_Lane_Rail — vật tì vào thành bát); cửa 11h
    hạ stand→flat; thoát ở θ_exit. Không xuyên tường: PyBullet
    tube_l_egress_pybullet.py.
    """
    ap = lane_aperture(W)
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
            # Không còn vách trong kéo về tâm luồng: ly tâm + đĩa ép vật RA
            # thành bát, nên trôi về bờ NGOÀI (r_o) chứ không về r_c.
            r = 0.85 * r + 0.15 * r_o
            r = _clamp(r, r_i + 0.5 * xy_span, r_max - 0.5 * xy_span)

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

        rg = _inner_wall_r(th, W)
        if rg is not None and r <= rg + 0.5 * GUIDE_T + 0.55 * xy_span + 1.5:
            r = max(r, min(r_max, rg + 0.5 * GUIDE_T + 0.45 * xy_span))

        # Họng → luồng: drift ra thành bát (không còn vách trong)
        if _ang_between(th, ENTRANCE_TH0 - 2.0, THETA_EXIT_DEG + 2.0):
            if r >= GUIDE_R1 - 4.0:
                r = 0.65 * r + 0.35 * r_o
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
        if _overlap_volume(probe, guide) > thr:
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
    r_i = DISC_R - ENTRANCE_W  # bờ trong luồng cố định
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
    r_i = DISC_R - ENTRANCE_W  # bờ trong luồng cố định (họng ra Guide)
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
                # Vách trong duy nhất còn lại = tường xoắn Guide_System
                wall_t = GUIDE_T
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




__all__ = [_n for _n in dir() if not _n.startswith("__")]
