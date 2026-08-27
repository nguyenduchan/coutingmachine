"""
Cụm tịnh tiến BÁNH RĂNG - THANH RĂNG: 28BYJ-48 + PINION m1 z16 + RACK in liền thanh.

Bản thay thế cho `n20_leadscrew_stage.py` (GA12-N20 + ty ren M4 + đai ốc). Lý do đổi:
  - N20 là DC CHỔI THAN. Ở duty thật của máy (100 lần/ngày x 3 s = 91 giờ trong 3 năm,
    duty 0.35%) chổi than KHÔNG phải điểm chết — nhưng 28BYJ-48 không có chổi, tuổi thọ
    datasheet >10.000 h, và rẻ hơn (~25k cả bộ kèm ULN2003).
  - TẢI THẬT chỉ vài gam (thanh nhựa). Mô men cần trên ren M4 là ~0.1-1 N.mm, trong khi
    N20 cho 49 N.mm -> đang chạy ở ~1% mô men stall. Mô men KHÔNG còn là ràng buộc,
    nên đổi sang cơ cấu ưu tiên TỐC ĐỘ được.
  - Ren M4 bước 0.7 quá chậm cho 28BYJ-48 (12 rpm -> 8.4 mm/phút). Bánh răng m1 z16
    cho 50.3 mm/vòng -> 30 mm trong ~3.0 s ở 12 rpm. Nhanh gấp 6 lần cụm ty ren.

CÁI ĐÁNH ĐỔI (đọc kỹ trước khi chốt):
  1. BÁNH RĂNG - THANH RĂNG KHÔNG TỰ KHOÁ. Hiệu suất ~95% cả hai chiều, không có góc
     nâng nào để khoá. Thứ giữ vị trí là DETENT TORQUE của 28BYJ-48 (self-positioning
     torque >= 34.3 N.mm khi ĐÃ TẮT ĐIỆN) chia cho bán kính bánh răng:
         lực giữ = 34.3 / 8.0 = 4.3 N   (tải thật ~0.2 N -> dư 21 lần)
     Nghĩa là nó "tự khoá ở lực vừa phải": giữ tới ~4 N rồi TRƯỢT. Trượt thì không gãy
     răng (đó là ưu điểm), nhưng MẤT GỐC TOẠ ĐỘ vì stepper chạy hở -> phải về home lại.
  2. RƠ (backlash) tăng mạnh: ty ren M4 rơ ~0.002 mm quy về đường thẳng; ở đây là rơ
     hộp số 28BYJ-48 (~1-2 deg) x R8 + rơ ăn khớp răng in ~ TỔNG 0.2-0.5 mm.
     CÁCH SỬA MIỄN PHÍ: luôn tiếp cận vị trí đích TỪ MỘT CHIỀU DUY NHẤT.
  3. Hộp DÀI HƠN. Ty ren: dài ~ hành trình + đai ốc + khớp nối. Thanh răng: thanh răng
     vừa phải đủ dài để LUÔN ăn khớp, vừa phải QUÉT trọn hành trình -> chiều dài trong
     hộp ~ 2 x hành trình + biên. Đây là chi phí cố định của cơ cấu này.
  4. Hộp CAO HƠN (38 vs 30 mm): trục 28BYJ-48 vuông góc mặt thân nên phải dựng đứng,
     thân O28 x 19 nằm dưới, thanh chạy bên trên mũ vít bắt tai động cơ.

CƠ CẤU (hành trình theo +X; đáy hộp z = 0; TRỤC BÁNH RĂNG THẲNG ĐỨNG tại x = 0, y = 0):
  Housing        - vỏ + sàn + 4 vách + bệ đỡ ĐC + 2 trụ bắt tai ĐC + hốc/lỗ trục trơn
                   + bệ công tắc + máng dây + 4 tai bắt máy + 4 boss bắt nắp. MỘT khối in.
  Housing_Lid    - nắp, 4 vít M3, có KHE cho trụ gá tải chui lên
  BYJ_Motor      - 28BYJ-48 (mua sẵn): thân O28 x 19, trục O5 hai mặt vát, LỆCH TÂM 8 mm,
                   2 tai thép cách nhau 35 mm nằm trên đường VUÔNG GÓC với hướng lệch tâm
  Pinion         - bánh răng thẳng IN 3D, m = 1, z = 16, PA 20 deg, lỗ O5 hai mặt vát
                   (ép thẳng lên trục — hai mặt vát đã truyền mô men, không cần vít hãm)
  Slide_Bar      - THANH TỊNH TIẾN in liền, tiết diện chữ П CƯỠI LÊN bánh răng:
                   chân +Y mang THANH RĂNG + bạc trục A, chân -Y mang bạc trục B,
                   cầu nối nằm TRÊN đầu trục động cơ, trên cầu là TRỤ GÁ TẢI
  Guide_Rod_A/B  - 2 trục trơn O5 (mua sẵn), song song X. Bạc A LỖ TRÒN (định vị),
                   bạc B LỖ RÃNH theo Y (chỉ chặn xoay) -> KHÔNG siêu tĩnh, không kẹt
  Limit_Switch_Min - MỘT KW11 bánh xe (HOME), bị ấn DỌC TRỤC bởi mặt đầu -X của thanh

VÌ SAO 2 TRỤC TRƠN (bản ty ren chỉ cần 1):
  Bản ty ren dùng đai ốc + trục trơn = 2 ràng buộc song song nên thanh không xoay được.
  Ở đây ăn khớp răng KHÔNG chặn được thanh xoay quanh trục trơn (xoay là NHẢ KHỚP).
  Nên phải có trục thứ hai. Bạc thứ hai LÀ RÃNH chứ không phải lỗ tròn: hai lỗ tròn
  trên một chi tiết in là siêu tĩnh, sai số in / cong vênh sẽ làm kẹt.

VÌ SAO THANH PHẢI CƯỠI CHỮ П LÊN BÁNH RĂNG:
  Bánh răng O18 và đầu trục ĐC (z tới 32.0) đứng ngay giữa hộp tại (0, 0) và KHÔNG di
  chuyển, còn thanh quét qua đó. Nên thanh không được có thịt nào trong vùng
  |y| < 9.5 ở khoảng z = 25.6..32.0. Hai chân nối nhau bằng CẦU nằm TRÊN đỉnh trục.

CHỈ MỘT CÔNG TẮC (chốt 2026-08-28, người dùng quyết) — vì sao đủ:
  - CT MIN (home) là BẮT BUỘC: stepper chạy hở, mất điện là mất vị trí tuyệt đối, và
    cơ cấu này TRƯỢT được (xem mục 1 ở trên) nên có thể mất bước giữa chừng.
  - CT MAX ĐÃ BỎ. Chính con HOME đã làm luôn việc của nó: mỗi lần về home, so số bước
    THỰC với số bước DỰ KIẾN là ra đúng lượng đã trôi. CT MAX chỉ thêm được "báo sớm",
    mà hậu quả của việc không báo sớm ở đây là thanh đâm cữ rồi TRƯỢT RĂNG — không tự
    khoá nên không kẹt, stepper stall thì dòng vẫn như lúc chạy nên không cháy.
  - Giới hạn +X do PHẦN MỀM lo (giới hạn mềm 0..29 mm) + CỮ CỨNG cơ khí (dưới đây).
  - `SW_MAX = True` dựng lại con thứ hai, hộp dài thêm 16 mm. Chỉ nên bật lại nếu:
    (a) firmware KHÔNG home lại định kỳ, (b) tải tăng quá ~1 N, (c) có người hay chạm
    tay vào cơ cấu.

CỮ CỨNG ĐẦU +X — BẮT BUỘC KHI KHÔNG CÓ CT MAX:
  Khi còn CT MAX, cữ cứng chính là cần gạt công tắc bị ấn kịch. Bỏ nó đi thì phải có
  thứ khác chặn, nếu không thanh chạy tiếp ~20 mm tới khi va lung tung. Ở đây cữ là
  MẶT -X CỦA 2 TRỤ NẮP GÓC +X (HARD_STOP_X): 2 chân П của thanh đập vào 2 trụ cùng
  lúc nên lực đối xứng, và trụ dính liền 2 vách nên rất cứng. Thang bậc:
      29.0 mm  giới hạn mềm (firmware)
      30.0 mm  hết hành trình danh nghĩa
      30.5 mm  chặn cơ danh nghĩa (_X_MAX_MECH)
      31.5 mm  CỮ CỨNG chạm thật -> bánh răng trượt, vô hại
  Có 2 check canh giữ: cữ phải TỒN TẠI, và phải nằm ngoài vùng thanh quét bình thường.

THỨ TỰ LẮP (7 bước):
  1. Hàn dây công tắc HOME, bắt 2 vít M2 TỪ TRÊN XUỐNG vào bệ công tắc
  2. Thả 28BYJ-48 thẳng từ trên xuống (2 tai rơi đúng 2 trụ), bắt 2 vít tự ren M3
  3. Ép Pinion lên trục ĐC (2 mặt vát tự canh), đáy bánh răng tì gờ O9.1
  4. Thả Slide_Bar thẳng từ trên xuống, cưỡi lên bánh răng, canh cho răng vào khớp
  5. Đẩy Guide_Rod_A rồi Guide_Rod_B TỪ NGOÀI vách +X vào, xuyên bạc, tì đáy hốc mù -X
  6. Luồn dây vào máng, ra khe trên vách -X
  7. Hạ nắp thẳng từ trên xuống (trụ gá tải chui qua khe), bắt 4 vít M3 góc
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Windows freecadcmd mặc định cp1252 — unicode trong print() làm hỏng rebuild
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")

OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
FCSTD = OUT / "byj_rack_stage.FCStd"

# ---------------------------------------------------------------------------
# 0. CÔNG TẮC MAX: bật/tắt cả con + phần hộp nó chiếm
# ---------------------------------------------------------------------------
SW_MAX = False

# ---------------------------------------------------------------------------
# 1. ĐỘNG CƠ 28BYJ-48  (GIẢ ĐỊNH — ĐO LẠI KHI CÓ HÀNG, sửa ở đây là đủ)
# ---------------------------------------------------------------------------
# Các hãng làm 28BYJ-48 khác nhau chút ở khối nối dây và bề dày tai. 4 số quan trọng
# nhất (O28, cao 19, lệch tâm 8, tai cách 35) thì thống nhất giữa các hãng.
MOT_D = 28.0                  # Ø thân
MOT_H = 19.0                  # cao thân (mặt dưới -> MẶT TRÊN có trục)
MOT_SHAFT_OFF = 8.0           # trục LỆCH TÂM 8 mm — ở đây hướng lệch là +X
MOT_SHAFT_D = 5.0
MOT_SHAFT_FLAT = 3.0          # khoảng cách 2 mặt vát (double-D)
MOT_SHAFT_L = 10.0            # trục nhô trên MẶT TRÊN thân
MOT_BOSS_D = 9.1              # gờ quanh chân trục
MOT_BOSS_H = 1.5
MOT_EAR_SPAN = 35.0           # tâm-tâm 2 lỗ tai, trên đường VUÔNG GÓC hướng lệch tâm
MOT_EAR_T = 0.8               # tai thép mỏng, nằm TRÊN mặt trên thân
MOT_EAR_W = 7.0               # bề rộng tai (theo X)
MOT_EAR_HOLE = 4.2
MOT_EAR_TIP = 21.0            # bán kính tới mép ngoài tai
MOT_CONN_W = 14.6             # khối nối dây, nhô ra phía -X (xa bánh răng)
MOT_CONN_H = 16.6
MOT_CONN_OUT = 5.0            # nhô ra khỏi Ø28
MOT_CONN_IN = 3.0             # ăn vào TRONG đường kính thân

# Điện / cơ tính (dùng cho phần in thông số, không dựng hình)
MOT_DETENT = 34.3             # N.mm, self-positioning torque KHI ĐÃ TẮT ĐIỆN
MOT_RPM = 12.0                # vòng/phút thực tế đạt được (datasheet: out-traction >1000 Hz)
LOAD_N = 0.2                  # lực dọc trục thật (thanh nhựa vài gam + ma sát)

# ---------------------------------------------------------------------------
# 2. BÁNH RĂNG + THANH RĂNG
# ---------------------------------------------------------------------------
GEAR_M = 1.0                  # module — m1 z18 lỗ 5 là cỡ MUA SẴN được (POM/đồng)
# z = 18 chứ KHÔNG phải 16. Với PA 20 deg, số răng tối thiểu không bị CẮT CHÂN
# (undercut) là 17. Bản đầu để z = 16: biên dạng dựng ở đây giữ nguyên thân khai xuống
# tận vòng cơ sở, trong khi răng thật ở z<17 bị dao cắt lẹm mất phần đó — nên đỉnh răng
# của thanh răng đâm vào chân răng bánh răng (check "An khop" bắt được 22.7 mm3).
# z >= 17 thì không còn undercut và biên dạng radial dưới vòng cơ sở là AN TOÀN
# (nó mảnh hơn chân răng thật, chỉ yếu hơn chút chứ không chèn).
GEAR_Z = 18
GEAR_PA = 20.0                # góc áp lực
GEAR_FACE = 5.0               # bề rộng răng
GEAR_BL = 0.12                # rơ ăn khớp: bớt bề dày răng mỗi bên (cả pinion và rack)
GEAR_HUB_D = 11.0             # moay-ơ bánh răng (ôm trục, chống nghiêng)
# Moay-ơ nằm PHÍA DƯỚI vành răng, không phải phía trên: phía trên là CẦU của Slide_Bar
# (cầu phải vượt qua đỉnh trục ĐC nên nó quét ngang ngay trên vành răng). Moay-ơ dưới
# còn được việc thứ hai: tì lên gờ Ø9.1 của động cơ -> định vị dọc trục cho bánh răng.
PIN_R = GEAR_M * GEAR_Z / 2.0                  # 8.0  bán kính vòng chia
PIN_RA = PIN_R + GEAR_M                        # 9.0  đỉnh răng
PIN_RF = PIN_R - 1.25 * GEAR_M                 # 6.75 chân răng
PIN_MM_PER_REV = 2.0 * math.pi * PIN_R         # 50.27 mm/vòng
GEAR_PITCH = math.pi * GEAR_M                  # 3.1416 bước răng

TRAVEL = 30.0                 # HÀNH TRÌNH YÊU CẦU
RACK_MARGIN = 6.0             # thanh răng thò thêm mỗi đầu để LUÔN còn ăn khớp
RACK_L = TRAVEL + 2.0 * RACK_MARGIN            # 42.0
RACK_BACK = 1.75              # bề dày lưng thanh răng, tính từ CHÂN răng

# ---------------------------------------------------------------------------
# 3. BỐ TRÍ CHUNG. Gốc: TRỤC BÁNH RĂNG tại (x, y) = (0, 0). Đáy hộp z = 0.
# ---------------------------------------------------------------------------
BASE_T = 3.0                  # sàn
MOT_Z0 = BASE_T                                # ĐC ngồi thẳng trên sàn
MOT_TOP = MOT_Z0 + MOT_H                       # 22.0  mặt trên thân
MOT_EAR_Z1 = MOT_TOP + MOT_EAR_T               # 22.8  mặt trên tai
MOT_SHAFT_TOP = MOT_TOP + MOT_SHAFT_L          # 32.0  đỉnh trục
EAR_SCREW_D = 3.0             # vít TỰ REN M3 bắt tai xuống trụ
EAR_SCREW_HEAD_D = 5.6
EAR_SCREW_HEAD_H = 2.0
EAR_SCREW_TOP = MOT_EAR_Z1 + EAR_SCREW_HEAD_H  # 24.8  đỉnh mũ vít bắt tai
EAR_PILOT_D = 2.5             # lỗ mồi trong trụ cho vít tự ren M3
EAR_SCREW_L = 8.0
EAR_POST_W = 8.0              # trụ bắt tai: X
EAR_POST_Y = 6.0              # trụ bắt tai: Y — mép trong phải NGOÀI Ø thân ĐC

BAR_CLR_MOT = 0.8             # khe thanh <-> mũ vít bắt tai ĐC
BAR_Z0 = EAR_SCREW_TOP + BAR_CLR_MOT           # 25.6  ĐÁY THANH (và đáy 2 chân П)
GEAR_Z0 = BAR_Z0 + 0.4                         # 26.0  đáy bánh răng / thanh răng
GEAR_Z1 = GEAR_Z0 + GEAR_FACE                  # 31.0
GEAR_HUB_Z0 = MOT_TOP + MOT_BOSS_H             # 23.5  moay-ơ TÌ LÊN gờ Ø9.1 của ĐC
GEAR_HUB_H = GEAR_Z0 - GEAR_HUB_Z0             # 2.5
assert GEAR_HUB_H >= 1.5
assert GEAR_Z1 <= MOT_SHAFT_TOP - 0.5          # bánh răng phải nằm trọn trên trục

ROD_D = 5.0
ROD_BORE = ROD_D + 0.4                         # bạc trượt in: khe 0.4
BAR_WALL = 1.3                                 # thịt quanh bạc
BAR_LEG_Z1 = MOT_SHAFT_TOP + 0.4               # 32.4  đáy CẦU (phải trên đỉnh trục ĐC)
BRIDGE_T = 2.0
BAR_Z1 = BAR_LEG_Z1 + BRIDGE_T                 # 34.4  NÓC THANH
# Bạc nằm trong CHÂN, mà chân cao HẾT thân thanh (cầu chỉ lấp khoảng giữa 2 chân ở
# phần trên đỉnh trục) — nên mốc của bạc là BAR_Z1, KHÔNG phải BAR_LEG_Z1.
ROD_Z = 0.5 * (BAR_Z0 + BAR_Z1)                # 30.0
assert ROD_Z + ROD_BORE / 2.0 + BAR_WALL <= BAR_Z1 + 1e-9
assert ROD_Z - ROD_BORE / 2.0 - BAR_WALL >= BAR_Z0 - 1e-9

# --- bố trí theo Y (bánh răng ở y = 0, vòng đỉnh +-9) ---
RACK_PITCH_Y = PIN_R                           # +8.0  đường chia thanh răng
RACK_TIP_Y = RACK_PITCH_Y - GEAR_M             # +7.0  đỉnh răng (chĩa về -Y)
RACK_ROOT_Y = RACK_PITCH_Y + 1.25 * GEAR_M     # +9.25 chân răng
RACK_BACK_Y = RACK_ROOT_Y + RACK_BACK          # +11.0 lưng thanh răng
ROD_A_Y = 17.5                                 # trục ĐỊNH VỊ (lỗ tròn), phía thanh răng
# (17.0 chứ không phải 15.5: THÂN CÔNG TẮC phải chui lọt giữa hai trục trơn, mà bánh xe
#  của nó lại phải ấn vào CHÂN +Y của thanh — xem SW_YC / sw_roller_y() phía dưới)
ROD_B_Y = -15.5                                # trục CHỐNG XOAY (lỗ rãnh), phía kia
# (-14.5 chứ không phải -13: mép trên lỗ RÃNH phải nằm ngoài vòng đỉnh bánh răng,
#  mà rãnh rộng hơn lỗ tròn ROD_SLOT_Y/2 mỗi bên nên nó mới là cái quyết định)
ROD_SLOT_Y = 2.0                               # rãnh bạc B nới thêm theo Y
LEG_B_Y1 = -(PIN_RA + 0.5)                     # -9.5  mặt trong chân -Y (né vòng đỉnh)
BAR_Y1 = ROD_A_Y + ROD_BORE / 2.0 + BAR_WALL   # +19.5
BAR_Y0 = ROD_B_Y - ROD_BORE / 2.0 - ROD_SLOT_Y / 2.0 - BAR_WALL   # -17.0
assert RACK_BACK_Y + BAR_WALL <= ROD_A_Y - ROD_BORE / 2.0 + 1e-9
assert ROD_B_Y + ROD_BORE / 2.0 + ROD_SLOT_Y / 2.0 + BAR_WALL <= LEG_B_Y1 + 1e-9
EAR_POST_YC = MOT_EAR_SPAN / 2.0               # +-17.5  tâm 2 trụ bắt tai

# --- bố trí theo X ---
# Ở HOME, bánh răng ăn khớp tại điểm cách đầu -X của thanh răng RACK_MARGIN + TRAVEL,
# để khi thanh chạy hết +TRAVEL thì bánh răng còn cách đầu +X đúng RACK_MARGIN.
RACK_X0_HOME = -(RACK_MARGIN + TRAVEL)         # -36.0
RACK_X1_HOME = RACK_X0_HOME + RACK_L           # +6.0
BAR_END_T = 1.5                                # mẩu đặc 2 đầu thanh (mặt ấn công tắc)
BAR_X0_HOME = RACK_X0_HOME - BAR_END_T         # -37.5
BAR_L = RACK_L + 2.0 * BAR_END_T               # 45.0
BAR_X1_HOME = BAR_X0_HOME + BAR_L              # +7.5
MOT_CX = -MOT_SHAFT_OFF                        # -8.0  tâm thân ĐC (trục lệch về +X)
MOT_CONN_X0 = MOT_CX - MOT_D / 2.0 - MOT_CONN_OUT   # -27.0
MOT_CONN_X1 = MOT_CX - MOT_D / 2.0 + MOT_CONN_IN    # -19.0

# ---------------------------------------------------------------------------
# 4. CÔNG TẮC KW11 BÁNH XE (5A 250V)
# Tư thế: H (10) theo X = HƯỚNG BỊ ẤN ; L (20) theo Y ; T (6.4) theo Z.
# 2 lỗ bắt vít xuyên bề dày T -> vít M2 bắt TỪ TRÊN XUỐNG, siết trước khi đậy nắp.
# (Bản ty ren bắt vít ngang qua vách -Y; ở đây thanh cao nên bệ CT cũng cao, bắt từ
#  trên xuống dễ hơn nhiều và không cần lỗ thao tác trên vách.)
# ---------------------------------------------------------------------------
SW_L, SW_T, SW_H = 20.0, 6.4, 10.0
SW_HOLE_PITCH = 9.5
SW_BODY_HOLE_D = 2.0
SW_SCREW_HEAD_D = 4.0
SW_SCREW_HEAD_H = 1.6
SW_PILOT_D = 1.6
SW_SCREW_L = 8.0
SW_LEVER_L, SW_LEVER_W = 16.0, 4.0
SW_ROLLER_D, SW_ROLLER_W = 4.8, 2.5
SW_ROLLER_PROUD = 6.0                          # bánh xe nhô khỏi mặt trước thân
SW_TRIP_TRAVEL = 2.0                           # ấn bao nhiêu thì nhả tiếp điểm
SW_PRESS = 0.5                                 # ấn thêm sau điểm tác động (dự phòng)
SW_TERM_L, SW_TERM_W, SW_TERM_T = 5.0, 3.2, 0.5
SW_TERM_PITCH = 7.0
SW_TERM_ZONE = SW_TERM_L + 3.5                 # hốc trống: lá đồng + mối hàn + bẻ dây
# SW_YC bị kẹp giữa HAI ràng buộc ngược nhau:
#   - THÂN công tắc (dài 20 theo Y) phải chui lọt giữa 2 trục trơn
#   - BÁNH XE (lệch về +Y so với tâm thân) phải ấn trúng CHÂN +Y của thanh, tức
#     y >= RACK_ROOT_Y (9.25) — thấp hơn thì nó thò vào vùng trống của chữ П và
#     KHÔNG chạm gì cả (bản đầu đặt SW_YC = 2.0 -> bánh xe ở y = 7.0, hụt).
SW_YC = 4.0                                    # tâm thân CT theo Y
SW_LEVER_GAP = 2.5                             # bánh xe cách mép +Y thân CT
SW_HINGE_GAP = 1.0                             # bản lề cần gạt cách mép -Y thân CT
SW_Z0 = 26.2                                   # đáy thân CT
SW_Z1 = SW_Z0 + SW_T                           # 32.6
SW_SCREW_TOP = SW_Z1 + SW_SCREW_HEAD_H         # 34.2
SW_PED_TOP = SW_Z0                             # nóc bệ đỡ CT
SW_PED_PAD = 1.5                               # bệ rộng hơn thân CT mỗi bên

_SW_OVERTRAVEL = SW_ROLLER_PROUD - SW_TRIP_TRAVEL          # 4.0
X_TRIP_MIN = BAR_X0_HOME                                   # -37.5 mặt -X thanh khi HOME
X_TRIP_MAX = BAR_X1_HOME + TRAVEL                          # +37.5 mặt +X thanh khi hết
_X_MIN_MECH = X_TRIP_MIN - SW_PRESS
_X_MAX_MECH = X_TRIP_MAX + SW_PRESS
SW_MIN_FRONT = X_TRIP_MIN - _SW_OVERTRAVEL                 # -41.5 mặt trước thân CT MIN
SW_MAX_FRONT = X_TRIP_MAX + _SW_OVERTRAVEL                 # +41.5

# ---------------------------------------------------------------------------
# 5. VỎ HỘP
# ---------------------------------------------------------------------------
WALL_T = 2.5
WALL_END_T = 6.0              # vách -X dày hơn: chứa 2 HỐC MÙ đỡ đầu trục trơn
ROD_POCKET = 4.5              # chiều sâu hốc mù
ROD_STICK = 2.0               # trục thò ra ngoài vách +X (để rút ra khi tháo)
LID_T = 2.5
POST_W = 6.0                  # trụ bắt nắp ở 4 góc
M3_CLEAR = 3.4
M3_TAP = 2.5
CABLE_D = 6.5                 # lỗ ra dây trên vách -X
DUPONT_D = 1.8
DUCT_W = 5.0                  # hành lang dẫn dây dọc cạnh -Y
DUCT_Z1 = 9.0

# CỮ CỨNG đầu +X = mặt -X của 2 trụ nắp góc +X. Khe từ CHẶN CƠ danh nghĩa tới cữ cứng:
# đủ để thanh không bao giờ chạm trong vận hành bình thường, nhưng đủ gần để mất bước
# tích luỹ không kịp đẩy thanh đi đâu xa. Xem docstring "CỮ CỨNG ĐẦU +X".
HARD_STOP_GAP = 1.0
# Khoang trong theo X: đủ chỗ cụm công tắc (thân + hốc chân hàn)
_INNER_X0 = (SW_MIN_FRONT - SW_H - SW_TERM_ZONE) - 1.0     # -61.0
if SW_MAX:
    _INNER_X1 = (SW_MAX_FRONT + SW_H + SW_TERM_ZONE) + 1.0  # +61.0
else:
    # Không có CT MAX thì cái quyết định mép +X là TRỤ NẮP GÓC: nó đứng lùi vào
    # POST_W/2 kể từ mép khoang, mà thanh quét tới tận _X_MAX_MECH. Để 2.0 mm như bản
    # đầu thì trụ góc nằm hẳn trong đường thanh chạy (check bắt được 159 mm3).
    _INNER_X1 = _X_MAX_MECH + POST_W + HARD_STOP_GAP        # +45.0
INNER_X0, INNER_X1 = _INNER_X0, _INNER_X1
# Khoang trong theo Y: chứa cả thanh và 2 trụ bắt tai ĐC
INNER_Y0 = min(BAR_Y0, -EAR_POST_YC - EAR_POST_Y / 2.0) - 1.0
INNER_Y1 = max(BAR_Y1, EAR_POST_YC + EAR_POST_Y / 2.0) + 1.0
INNER_TOP = max(BAR_Z1, SW_SCREW_TOP) + 1.0                # 35.4
BOX_X0, BOX_X1 = INNER_X0 - WALL_END_T, INNER_X1 + WALL_T
BOX_Y0, BOX_Y1 = INNER_Y0 - WALL_T, INNER_Y1 + WALL_T
BOX_Z1 = INNER_TOP + LID_T

# Trục trơn: hốc mù trong vách -X, lỗ XUYÊN vách +X (đẩy từ ngoài vào — bài học của
# bản ty ren: hai hốc mù quay vào nhau là VÔ NGHIỆM khi cả hai nằm trên một khối cứng)
ROD_X0 = INNER_X0 - ROD_POCKET
ROD_LEN = (BOX_X1 + ROD_STICK) - ROD_X0
ROD_ACCESS_D = ROD_D + 0.4    # lỗ xuyên vách +X

# 4 tai bắt máy ở 2 đầu theo X (giống bản ty ren: chừa trọn 2 cạnh Y cho cơ cấu ngoài)
EAR_X, EAR_OUT, EAR_HOLE = 11.0, 9.0, 4.5
MACHINE_EAR_X = [BOX_X0 + EAR_X / 2.0, BOX_X1 - EAR_X / 2.0]

# Trụ gá tải trên thanh: MỘT trụ dẹt lọt trong khe nắp (bài học bản ty ren — mọi thứ
# cao hơn mặt nắp phải nằm lọt bề rộng khe, nếu không là mất đường lắp nắp)
POSTL_X, POSTL_Y = 4.0, 12.0
POSTL_H = 16.0                # thò trên mặt nắp
LOAD_HOLE_D = M3_CLEAR
LOAD_HOLE_DZ = 8.0            # 2 lỗ M3 xuyên theo X, xếp chồng theo Z
LID_SLOT_END = 3.0

# Lỗ ra dây phải LÙI RA SAU trụ nắp góc -Y, nếu không trụ bịt kín hành lang dẫn dây
# (đúng cái bẫy đã gặp ở bản ty ren).
_DUCT_LO = INNER_Y0 + POST_W                      # mep trong tru nap goc -Y
_DUCT_HI = SW_YC - SW_L / 2.0 - SW_PED_PAD        # mep -Y be cong tac MIN
DUCT_YC = 0.5 * (_DUCT_LO + _DUCT_HI)
# Mặt -X của 2 trụ nắp góc +X — đây là CỮ CỨNG cơ khí ở đầu +X
HARD_STOP_X = INNER_X1 - POST_W
assert _DUCT_HI - _DUCT_LO >= CABLE_D + 1.0, (_DUCT_LO, _DUCT_HI)

assert INNER_Y1 - BAR_Y1 >= 0.5
assert BAR_Z0 > EAR_SCREW_TOP
assert SW_YC + SW_L / 2.0 - SW_LEVER_GAP >= RACK_ROOT_Y   # bánh xe ấn trúng chân +Y
assert SW_YC + SW_L / 2.0 <= ROD_A_Y - ROD_BORE / 2.0     # thân CT lọt dưới trục A
assert SW_YC - SW_L / 2.0 >= ROD_B_Y + ROD_BORE / 2.0 + ROD_SLOT_Y / 2.0


# ---------------------------------------------------------------------------
# 6. Helper hình học
# ---------------------------------------------------------------------------
def _box(dx, dy, dz, x0, y0, z0) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def _box2(x0, x1, y0, y1, z0, z1) -> Part.Shape:
    return _box(x1 - x0, y1 - y0, z1 - z0, x0, y0, z0)


def _cyl_z(d, h, x=0.0, y=0.0, z0=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _cyl_x(d, length, x0, y=0.0, z=0.0) -> Part.Shape:
    return Part.makeCylinder(d / 2.0, length, App.Vector(x0, y, z), App.Vector(1, 0, 0))


def _cyl_y(d, length, x=0.0, y0=0.0, z=0.0) -> Part.Shape:
    return Part.makeCylinder(d / 2.0, length, App.Vector(x, y0, z), App.Vector(0, 1, 0))


def _refine(shape: Part.Shape) -> Part.Shape:
    try:
        return shape.removeSplitter()
    except Exception:
        return shape


def _cut(shape: Part.Shape, tool: Part.Shape) -> Part.Shape:
    """Cắt an toàn: giữ nguyên hình cũ nếu phép cắt cho ra khối rỗng."""
    try:
        nxt = shape.cut(tool)
        if nxt is not None and getattr(nxt, "Solids", None):
            return nxt
    except Exception:
        pass
    return shape


def _sweep_z(shape: Part.Shape, height: float, step: float = 1.5) -> Part.Shape:
    """Quét chi tiết THẲNG LÊN — kiểm tra 'thả từ trên xuống có vướng không'."""
    out = shape
    n = max(1, int(round(height / step)))
    for i in range(1, n + 1):
        out = out.fuse(shape.translated(App.Vector(0.0, 0.0, i * height / n)))
    return out


def _sweep_x(shape: Part.Shape, dist: float, step: float = 2.0) -> Part.Shape:
    """Quét chi tiết theo +X — kiểm tra 'đẩy dọc trục vào có vướng không'."""
    out = shape
    n = max(1, int(round(abs(dist) / step)))
    for i in range(1, n + 1):
        out = out.fuse(shape.translated(App.Vector(i * dist / n, 0.0, 0.0)))
    return out


def _common_vol(a: Part.Shape, b: Part.Shape) -> float:
    try:
        c = a.common(b)
        return c.Volume if c is not None else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# 7. Biên dạng răng
# ---------------------------------------------------------------------------
def _inv(a: float) -> float:
    return math.tan(a) - a


def gear_profile(m: float, z: int, pa_deg: float, bl: float,
                 n_flank: int = 8, phase_deg: float = 90.0) -> list[tuple[float, float]]:
    """Biên dạng THÂN KHAI của bánh răng trụ răng thẳng, trả về list (x, y).

    phase_deg = góc TÂM của một răng. Mặc định 90 deg: luôn có một răng chĩa thẳng
    về +Y, tức là răng ăn vào RÃNH của thanh răng (rãnh tâm tại x = 0) khi ở HOME —
    đúng pha ăn khớp, và KHÔNG phụ thuộc z có chia hết cho 4 hay không.
    bl = lượng bớt bề dày răng (mm, đo trên vòng chia) để tạo rơ ăn khớp.
    """
    rp = m * z / 2.0
    ap = math.radians(pa_deg)
    rb = rp * math.cos(ap)
    ra = rp + m
    rf = max(rp - 1.25 * m, 0.35 * rp)
    # nửa góc chiếm chỗ của răng tại vòng chia
    psi = (math.pi * m / 2.0 - bl) / (2.0 * rp)
    k = psi + _inv(ap)

    def flank(r: float) -> float:
        """Nửa góc răng tại bán kính r (dương = còn thịt)."""
        rr = max(r, rb)
        return k - _inv(math.acos(min(1.0, rb / rr)))

    r_lo = max(rb, rf)
    radii = [r_lo + (ra - r_lo) * i / (n_flank - 1) for i in range(n_flank)]
    fa_lo = flank(r_lo)
    step = 2.0 * math.pi / z
    ph = math.radians(phase_deg)
    pts: list[tuple[float, float]] = []
    for t in range(z):
        a0 = ph + t * step
        # chân răng phía -: nối từ đáy răng trước sang chân thân khai
        if rf < rb - 1e-9:
            pts.append((rf * math.cos(a0 - fa_lo), rf * math.sin(a0 - fa_lo)))
        # sườn phải: r tăng dần
        for r in radii:
            a = a0 - flank(r)
            pts.append((r * math.cos(a), r * math.sin(a)))
        # sườn trái: r giảm dần
        for r in reversed(radii):
            a = a0 + flank(r)
            pts.append((r * math.cos(a), r * math.sin(a)))
        if rf < rb - 1e-9:
            pts.append((rf * math.cos(a0 + fa_lo), rf * math.sin(a0 + fa_lo)))
        # đáy rãnh sang răng kế: 2 điểm cho tròn
        a1 = a0 + step
        for f in (1.0 / 3.0, 2.0 / 3.0):
            a = (a0 + fa_lo) + f * ((a1 - fa_lo) - (a0 + fa_lo))
            pts.append((rf * math.cos(a), rf * math.sin(a)))
    return pts


def make_pinion(angle_deg: float = 0.0) -> Part.Shape:
    """Bánh răng IN 3D, trục z, tâm (0,0). angle_deg = góc quay quanh z."""
    pts = gear_profile(GEAR_M, GEAR_Z, GEAR_PA, GEAR_BL)
    vecs = [App.Vector(x, y, GEAR_Z0) for x, y in pts]
    vecs.append(vecs[0])
    face = Part.Face(Part.makePolygon(vecs))
    body = face.extrude(App.Vector(0, 0, GEAR_FACE))
    hub = _cyl_z(GEAR_HUB_D, GEAR_HUB_H, 0.0, 0.0, GEAR_HUB_Z0)
    body = body.fuse(hub)
    # lỗ trục Ø5 hai mặt vát 3.0 — ép thẳng lên trục ĐC
    bore_z0 = GEAR_HUB_Z0 - 1.0
    bore_h = GEAR_Z1 - bore_z0 + 1.0
    bore = _cyl_z(MOT_SHAFT_D + 0.15, bore_h, 0.0, 0.0, bore_z0)
    flat = MOT_SHAFT_FLAT + 0.15
    keep = _box2(-MOT_SHAFT_D, MOT_SHAFT_D, -flat / 2.0, flat / 2.0,
                 bore_z0 - 0.5, bore_z0 + bore_h + 0.5)
    bore = bore.common(keep)
    body = _cut(body, bore)
    body = _refine(body)
    if abs(angle_deg) > 1e-9:
        body.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
    return body


def pinion_angle(offset: float) -> float:
    """Góc quay bánh răng (deg) khi thanh đã dịch `offset` mm theo +X.

    Thanh răng nằm ở +Y: thanh đi +X thì điểm tiếp xúc trên đỉnh bánh răng đi +X,
    tức bánh răng quay THEO CHIỀU KIM ĐỒNG HỒ nhìn từ +Z -> góc ÂM.
    """
    return -math.degrees(offset / PIN_R)


def rack_profile(x0: float, length: float, m: float, pa_deg: float,
                 bl: float, phase: float = 0.0) -> list[tuple[float, float]]:
    """Biên dạng thanh răng (mặt cắt XY), răng CHĨA VỀ -Y, lưng ở +Y.

    Trả về đa giác kín đi theo chiều +X ở phía răng rồi vòng về ở phía lưng.
    Ở HOME (phase = 0) có một RÃNH răng tâm tại x = 0, khớp với răng bánh răng tâm
    ở 90 deg.

    `phase` = quãng thanh ĐÃ DỊCH theo +X. BẮT BUỘC truyền vào, vì răng phải TỊNH
    TIẾN CÙNG THANH. Bản đầu tính tâm răng theo lưới tuyệt đối (k+0.5)*p nên khi thanh
    dịch, răng bị "ghim" tại chỗ và tự đánh chỉ số lại -> lệch pha với bánh răng, tăng
    dần theo hành trình (check "An khop" bắt được 24.5 mm3 ở đúng vùng sườn răng).
    """
    p = math.pi * m
    ta = math.tan(math.radians(pa_deg))
    half_p = p / 4.0 - bl / 2.0
    half_t = half_p - m * ta                    # nửa bề rộng ở ĐỈNH răng
    half_r = half_p + 1.25 * m * ta             # nửa bề rộng ở CHÂN răng
    y_tip = RACK_TIP_Y
    y_root = RACK_ROOT_Y
    # tâm răng ở (k + 0.5) * p + phase  -> rãnh răng tâm tại k * p + phase (có x = phase)
    kmin = int(math.floor((x0 - phase) / p)) - 1
    kmax = int(math.ceil((x0 + length - phase) / p)) + 1
    centers = []
    for k in range(kmin, kmax + 1):
        c = (k + 0.5) * p + phase
        if c - half_r >= x0 and c + half_r <= x0 + length:
            centers.append(c)
    pts: list[tuple[float, float]] = [(x0, y_root)]
    for c in centers:
        pts.append((c - half_r, y_root))
        pts.append((c - half_t, y_tip))
        pts.append((c + half_t, y_tip))
        pts.append((c + half_r, y_root))
    pts.append((x0 + length, y_root))
    pts.append((x0 + length, RACK_BACK_Y))
    pts.append((x0, RACK_BACK_Y))
    return pts


# ---------------------------------------------------------------------------
# 8. Chi tiết mua sẵn: động cơ, trục trơn, công tắc
# ---------------------------------------------------------------------------
def make_motor() -> Part.Shape:
    """28BYJ-48 dựng đứng, trục lên; tâm thân (MOT_CX, 0), trục tại (0, 0)."""
    body = _cyl_z(MOT_D, MOT_H, MOT_CX, 0.0, MOT_Z0)
    # 2 tai thép nằm TRÊN mặt trên thân, trên đường vuông góc hướng lệch tâm (=> theo Y)
    for s in (+1.0, -1.0):
        ear = _box2(MOT_CX - MOT_EAR_W / 2.0, MOT_CX + MOT_EAR_W / 2.0,
                    min(0.0, s * MOT_EAR_TIP), max(0.0, s * MOT_EAR_TIP),
                    MOT_TOP, MOT_EAR_Z1)
        body = body.fuse(ear)
        hole = _cyl_z(MOT_EAR_HOLE, MOT_EAR_T + 1.0, MOT_CX, s * EAR_POST_YC,
                      MOT_TOP - 0.5)
        body = _cut(body, hole)
    # gờ quanh chân trục + trục hai mặt vát
    body = body.fuse(_cyl_z(MOT_BOSS_D, MOT_BOSS_H, 0.0, 0.0, MOT_TOP))
    shaft = _cyl_z(MOT_SHAFT_D, MOT_SHAFT_L, 0.0, 0.0, MOT_TOP)
    keep = _box2(-MOT_SHAFT_D, MOT_SHAFT_D, -MOT_SHAFT_FLAT / 2.0, MOT_SHAFT_FLAT / 2.0,
                 MOT_TOP, MOT_SHAFT_TOP + 1.0)
    body = body.fuse(shaft.common(keep))
    # khối nối dây, nhô về -X
    conn = _box2(MOT_CONN_X0, MOT_CONN_X1,
                 -MOT_CONN_W / 2.0, MOT_CONN_W / 2.0,
                 MOT_Z0 + 1.0, MOT_Z0 + 1.0 + MOT_CONN_H)
    body = body.fuse(conn)
    return _refine(body)


def make_guide_rod(y: float) -> Part.Shape:
    return _cyl_x(ROD_D, ROD_LEN, ROD_X0, y, ROD_Z)


def sw_sign(is_max: bool) -> float:
    """Hướng RA XA thanh (thân công tắc + 3 chân hàn nằm phía này)."""
    return 1.0 if is_max else -1.0


def sw_dir(is_max: bool) -> float:
    """Hướng VỀ PHÍA thanh (cần gạt + bánh xe nhô ra phía này). Ngược sw_sign().

    Hai hướng này ngược nhau và RẤT dễ lẫn: bản đầu dùng sw_sign() cho bánh xe nên
    bánh xe chĩa ra ngoài, cách mặt thanh 5 mm và không bao giờ bị ấn.
    """
    return -sw_sign(is_max)


def sw_front_x(is_max: bool) -> float:
    return SW_MAX_FRONT if is_max else SW_MIN_FRONT


def sw_body_x(is_max: bool) -> tuple[float, float]:
    f = sw_front_x(is_max)
    s = sw_sign(is_max)
    return (f, f + SW_H) if is_max else (f - SW_H, f)


def sw_roller_y() -> float:
    """Tâm bánh xe theo Y. PHẢI nằm trong chân +Y của thanh (>= RACK_ROOT_Y)."""
    return SW_YC + SW_L / 2.0 - SW_LEVER_GAP


def sw_hole_xy(is_max: bool) -> list[tuple[float, float]]:
    x0, x1 = sw_body_x(is_max)
    xc = 0.5 * (x0 + x1)
    return [(xc, SW_YC - SW_HOLE_PITCH / 2.0), (xc, SW_YC + SW_HOLE_PITCH / 2.0)]


def make_limit_switch(is_max: bool) -> Part.Shape:
    """KW11: thân L(Y) x H(X) x T(Z); cần gạt + bánh xe chĩa VỀ PHÍA THANH."""
    s = sw_sign(is_max)
    x0, x1 = sw_body_x(is_max)
    body = _box2(x0, x1, SW_YC - SW_L / 2.0, SW_YC + SW_L / 2.0, SW_Z0, SW_Z1)
    for x, y in sw_hole_xy(is_max):
        body = _cut(body, _cyl_z(SW_BODY_HOLE_D, SW_T + 2.0, x, y, SW_Z0 - 1.0))
    # cần gạt: bản lề ở đầu -Y của thân, chạy dọc L, bánh xe gần đầu +Y; nhô ra theo X
    f = sw_front_x(is_max)
    d = sw_dir(is_max)
    roll_x = f + d * (SW_ROLLER_PROUD - SW_ROLLER_D / 2.0)
    # Cần gạt vẽ CHỒNG từ mặt thân ra tới tâm bánh xe. Nếu chỉ vẽ sát mặt thân thì nó
    # TIẾP XÚC ĐÚNG MẶT với bánh xe -> fuse suy biến, OCC trả về Null shape.
    lev = _box2(min(f, roll_x), max(f, roll_x),
                SW_YC - SW_L / 2.0 + SW_HINGE_GAP, sw_roller_y() + SW_ROLLER_D / 2.0,
                SW_Z0 + (SW_T - SW_LEVER_W) / 2.0, SW_Z0 + (SW_T + SW_LEVER_W) / 2.0)
    body = body.fuse(lev)
    body = body.fuse(_cyl_z(SW_ROLLER_D, SW_ROLLER_W, roll_x, sw_roller_y(),
                            SW_Z0 + (SW_T - SW_ROLLER_W) / 2.0))
    # 3 chân hàn nhô ra mặt LƯNG (xa thanh)
    back = x1 if is_max else x0
    for i in (-1, 0, 1):
        tab = _box2(min(back, back + s * SW_TERM_L), max(back, back + s * SW_TERM_L),
                    SW_YC + i * SW_TERM_PITCH / 2.0 - SW_TERM_W / 2.0,
                    SW_YC + i * SW_TERM_PITCH / 2.0 + SW_TERM_W / 2.0,
                    SW_Z0 + (SW_T - SW_TERM_T) / 2.0, SW_Z0 + (SW_T + SW_TERM_T) / 2.0)
        body = body.fuse(tab)
    return _refine(body)


def sw_list() -> list[bool]:
    return [False, True] if SW_MAX else [False]


# ---------------------------------------------------------------------------
# 9. Slide_Bar (in 3D) — tiết diện chữ П cưỡi lên bánh răng
# ---------------------------------------------------------------------------
def bar_x0(offset: float) -> float:
    return BAR_X0_HOME + offset


def make_slide_bar(offset: float = 0.0) -> Part.Shape:
    x0 = bar_x0(offset)
    x1 = x0 + BAR_L
    # chân +Y: từ đỉnh răng tới mép ngoài (mang thanh răng + bạc A)
    leg_a = _box2(x0, x1, RACK_ROOT_Y, BAR_Y1, BAR_Z0, BAR_LEG_Z1)
    # thanh răng: nằm giữa theo X, chừa 2 mẩu đặc ở đầu để ấn công tắc
    rpts = rack_profile(RACK_X0_HOME + offset, RACK_L, GEAR_M, GEAR_PA, GEAR_BL,
                        phase=offset)
    vecs = [App.Vector(px, py, GEAR_Z0) for px, py in rpts]
    vecs.append(vecs[0])
    rack = Part.Face(Part.makePolygon(vecs)).extrude(App.Vector(0, 0, GEAR_FACE))
    # phần chân +Y phía dưới/trên dải răng vẫn đặc tới đỉnh răng
    fill = _box2(x0, x1, RACK_TIP_Y, RACK_ROOT_Y, BAR_Z0, BAR_LEG_Z1)
    fill = _cut(fill, _box2(RACK_X0_HOME + offset - 0.001,
                            RACK_X1_HOME + offset + 0.001,
                            RACK_TIP_Y - 1.0, RACK_ROOT_Y + 1.0,
                            GEAR_Z0 - 0.001, GEAR_Z1 + 0.001))
    body = leg_a.fuse(rack).fuse(fill)
    # chân -Y: mang bạc B
    body = body.fuse(_box2(x0, x1, BAR_Y0, LEG_B_Y1, BAR_Z0, BAR_LEG_Z1))
    # cầu nối, nằm TRÊN đỉnh trục động cơ
    body = body.fuse(_box2(x0, x1, BAR_Y0, BAR_Y1, BAR_LEG_Z1, BAR_Z1))
    # KHÔNG bịt đặc 2 mặt đầu ngang qua giữa: vùng |y| < 9.5 ở z = 25.6..32.4 là chỗ
    # của BÁNH RĂNG và ĐẦU TRỤC (đứng yên tại x = 0, còn thanh thì quét qua đó). Bản
    # đầu có 2 mẩu đặc ở đây và nó đâm thẳng vào răng khi thanh về gần HOME.
    # Mặt ấn công tắc là MẶT ĐẦU CỦA CHÂN +Y — nên bánh xe công tắc phải đặt ở
    # y = sw_roller_y() >= RACK_ROOT_Y (có check riêng canh giữ).
    # 2 bạc trục trơn
    body = _cut(body, _cyl_x(ROD_BORE, BAR_L + 2.0, x0 - 1.0, ROD_A_Y, ROD_Z))
    slot = _cyl_x(ROD_BORE, BAR_L + 2.0, x0 - 1.0, ROD_B_Y, ROD_Z)
    slot = slot.fuse(_box2(x0 - 1.0, x1 + 1.0,
                           ROD_B_Y - ROD_SLOT_Y / 2.0, ROD_B_Y + ROD_SLOT_Y / 2.0,
                           ROD_Z - ROD_BORE / 2.0, ROD_Z + ROD_BORE / 2.0))
    body = _cut(body, slot)
    # TRỤ GÁ TẢI: trụ dẹt, mọc trên cầu, thò lên qua khe nắp
    pxc = 0.5 * (x0 + x1)
    post = _box2(pxc - POSTL_X / 2.0, pxc + POSTL_X / 2.0,
                 -POSTL_Y / 2.0, POSTL_Y / 2.0, BAR_Z1, BOX_Z1 + POSTL_H)
    body = body.fuse(post)
    for z in load_hole_z():
        body = _cut(body, _cyl_x(LOAD_HOLE_D, POSTL_X + 2.0,
                                 pxc - POSTL_X / 2.0 - 1.0, 0.0, z))
    return _refine(body)


def load_hole_z() -> list[float]:
    z1 = BOX_Z1 + POSTL_H - 4.0
    return [z1 - LOAD_HOLE_DZ, z1]


def make_hex_dummy() -> Part.Shape:
    return Part.Shape()


# ---------------------------------------------------------------------------
# 10. Housing + Lid
# ---------------------------------------------------------------------------
def lid_tap_xy() -> list[tuple[float, float]]:
    return [(INNER_X0 + POST_W / 2.0, INNER_Y0 + POST_W / 2.0),
            (INNER_X0 + POST_W / 2.0, INNER_Y1 - POST_W / 2.0),
            (INNER_X1 - POST_W / 2.0, INNER_Y0 + POST_W / 2.0),
            (INNER_X1 - POST_W / 2.0, INNER_Y1 - POST_W / 2.0)]


def machine_ear_xy() -> list[tuple[float, float]]:
    out = []
    for x in MACHINE_EAR_X:
        for s in (-1.0, 1.0):
            out.append((x, s * (max(abs(BOX_Y0), abs(BOX_Y1)) + EAR_OUT / 2.0)))
    return out


def sw_pedestal(is_max: bool) -> Part.Shape:
    x0, x1 = sw_body_x(is_max)
    s = sw_sign(is_max)
    # bệ ôm cả thân + hốc chân hàn, dính vào vách đầu hộp
    px0 = min(x0, x0 + s * SW_TERM_ZONE, x1, x1 + s * SW_TERM_ZONE) - 1.0
    px1 = max(x0, x0 + s * SW_TERM_ZONE, x1, x1 + s * SW_TERM_ZONE) + 1.0
    px0 = max(px0, INNER_X0)
    px1 = min(px1, INNER_X1)
    ped = _box2(px0, px1, SW_YC - SW_L / 2.0 - SW_PED_PAD, SW_YC + SW_L / 2.0 + SW_PED_PAD,
                BASE_T, SW_PED_TOP)
    # rỗng ruột cho nhẹ, chừa vành 3 mm và nóc 4 mm
    ped = _cut(ped, _box2(px0 + 3.0, px1 - 3.0,
                          SW_YC - SW_L / 2.0 + 1.0, SW_YC + SW_L / 2.0 + 1.0,
                          BASE_T - 1.0, SW_PED_TOP - 4.0))
    # hốc TRỐNG cho 3 chân hàn (không được có thịt bệ ở đó)
    ped = _cut(ped, _box2(min(x0, x0 + s * 99.0) if not is_max else x1,
                          x0 if not is_max else max(x1, x1 + s * 99.0),
                          SW_YC - SW_L / 2.0 - 3.0, SW_YC + SW_L / 2.0 + 3.0,
                          SW_Z0 - 1.5, SW_Z1 + 1.0))
    for x, y in sw_hole_xy(is_max):
        ped = _cut(ped, _cyl_z(SW_PILOT_D, SW_SCREW_L, x, y,
                               SW_PED_TOP - SW_SCREW_L + (SW_Z1 - SW_Z0)))
    return ped


def make_housing() -> Part.Shape:
    outer = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, 0.0, INNER_TOP)
    body = _cut(outer, _box2(INNER_X0, INNER_X1, INNER_Y0, INNER_Y1,
                             BASE_T, INNER_TOP + 1.0))
    # --- bệ / trụ bắt tai động cơ ---
    for s in (-1.0, 1.0):
        post = _box2(MOT_CX - EAR_POST_W / 2.0, MOT_CX + EAR_POST_W / 2.0,
                     s * EAR_POST_YC - EAR_POST_Y / 2.0,
                     s * EAR_POST_YC + EAR_POST_Y / 2.0, BASE_T, MOT_TOP)
        body = body.fuse(post)
        body = _cut(body, _cyl_z(EAR_PILOT_D, EAR_SCREW_L,
                                 MOT_CX, s * EAR_POST_YC,
                                 MOT_TOP - EAR_SCREW_L + MOT_EAR_T))
    # vành định vị thân ĐC (chống xoay/chống trôi khi chưa siết vít)
    ring = _cyl_z(MOT_D + 5.0, 4.0, MOT_CX, 0.0, BASE_T)
    ring = _cut(ring, _cyl_z(MOT_D + 0.6, 6.0, MOT_CX, 0.0, BASE_T - 1.0))
    # cắt bỏ phần vành chắn KHỐI NỐI DÂY. Mốc +X phải là MẶT TRONG của khối nối dây
    # (MOT_CONN_X1) chứ không phải mép Ø thân: khối nối ăn sâu 3 mm vào trong đường
    # kính thân, cắt hụt là vành xén vào nó ngay khi ĐC còn chưa nhúc nhích.
    ring = _cut(ring, _box2(BOX_X0 - 1.0, MOT_CONN_X1 + 1.5,
                            -MOT_CONN_W / 2.0 - 1.0, MOT_CONN_W / 2.0 + 1.0,
                            BASE_T - 1.0, BASE_T + 5.0))
    body = body.fuse(ring)
    # --- bệ 2 công tắc ---
    for is_max in sw_list():
        body = body.fuse(sw_pedestal(is_max))
    # --- 4 trụ bắt nắp ở 4 góc khoang ---
    for x, y in lid_tap_xy():
        p = _box2(x - POST_W / 2.0, x + POST_W / 2.0, y - POST_W / 2.0, y + POST_W / 2.0,
                  BASE_T, INNER_TOP)
        body = body.fuse(p)
        body = _cut(body, _cyl_z(M3_TAP, 10.0, x, y, INNER_TOP - 10.0))
    # --- trục trơn: HỐC MÙ vách -X, lỗ XUYÊN vách +X ---
    for y in (ROD_A_Y, ROD_B_Y):
        body = _cut(body, _cyl_x(ROD_D + 0.4, INNER_X0 - ROD_X0 + 0.001,
                                 ROD_X0, y, ROD_Z))
        body = _cut(body, _cyl_x(ROD_ACCESS_D, WALL_T + 2.0, INNER_X1 - 0.5, y, ROD_Z))
    # --- lỗ ra dây trên vách -X ---
    body = _cut(body, _cyl_x(CABLE_D, WALL_END_T + 2.0, BOX_X0 - 1.0,
                             DUCT_YC, BASE_T + DUCT_Z1 / 2.0))
    # --- khe hở quanh thân động cơ: bảo đảm thả ĐC thẳng từ trên xuống được ---
    body = _cut(body, _cyl_z(MOT_D + 1.0, MOT_H + 1.0, MOT_CX, 0.0, BASE_T - 0.5))
    # --- 4 tai bắt máy ---
    for x, y in machine_ear_xy():
        ear = _box2(x - EAR_X / 2.0, x + EAR_X / 2.0,
                    min(y, y - math.copysign(EAR_OUT, y)),
                    max(y, y - math.copysign(EAR_OUT, y)), 0.0, BASE_T)
        body = body.fuse(ear)
        body = _cut(body, _cyl_z(EAR_HOLE, BASE_T + 2.0, x, y, -1.0))
    return _refine(body)


def lid_slot_x() -> tuple[float, float]:
    pxc0 = 0.5 * (bar_x0(0.0) + bar_x0(0.0) + BAR_L)
    return (pxc0 - POSTL_X / 2.0 - LID_SLOT_END,
            pxc0 + TRAVEL + POSTL_X / 2.0 + LID_SLOT_END)


def make_housing_lid() -> Part.Shape:
    lid = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, INNER_TOP, BOX_Z1)
    sx0, sx1 = lid_slot_x()
    lid = _cut(lid, _box2(sx0, sx1, -POSTL_Y / 2.0 - 0.6, POSTL_Y / 2.0 + 0.6,
                          INNER_TOP - 1.0, BOX_Z1 + 1.0))
    for x, y in lid_tap_xy():
        lid = _cut(lid, _cyl_z(M3_CLEAR, LID_T + 2.0, x, y, INNER_TOP - 1.0))
    return _refine(lid)


# ---------------------------------------------------------------------------
# 11. Kiểm tra
# ---------------------------------------------------------------------------
def _offsets(n: int = 9) -> list[float]:
    return [TRAVEL * i / (n - 1) for i in range(n)]


def verify(parts: dict) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    housing = parts["Housing"]
    motor = parts["BYJ_Motor"]

    # --- 1. thanh quét cả hành trình: không đụng vỏ / động cơ / bệ công tắc ---
    worst_h = worst_m = 0.0
    for off in _offsets():
        bar = make_slide_bar(off)
        worst_h = max(worst_h, _common_vol(bar, housing))
        worst_m = max(worst_m, _common_vol(bar, motor))
    checks.append(("Thanh quet 0..%.0f mm khong dung VO" % TRAVEL, worst_h < 1e-6,
                   "va cham %.3f mm3" % worst_h))
    checks.append(("Thanh quet khong dung DONG CO (than/tai/vit/truc)", worst_m < 1e-6,
                   "va cham %.3f mm3" % worst_m))

    # --- 2. ăn khớp thật: bánh răng quay đúng pha thì KHÔNG chèn vào thanh răng ---
    worst_mesh = 0.0
    for off in _offsets(7):
        g = make_pinion(pinion_angle(off))
        worst_mesh = max(worst_mesh, _common_vol(g, make_slide_bar(off)))
    checks.append(("An khop: banh rang khong chen vao thanh rang", worst_mesh < 1e-3,
                   "chen %.4f mm3 (bl = %.2f mm)" % (worst_mesh, GEAR_BL)))

    # --- 3. và vẫn CÓ tiếp xúc (không phải hụt khớp) ---
    min_touch = 1e9
    for off in _offsets(7):
        big = make_pinion(pinion_angle(off))
        big = big.common(_cyl_z(2.0 * (PIN_RA + 0.45), GEAR_FACE + 1.0,
                                0.0, 0.0, GEAR_Z0 - 0.5))
        # nong vong dinh len 0.45 -> phai cham thanh rang
        probe = _cyl_z(2.0 * (PIN_RA + 0.45), GEAR_FACE, 0.0, 0.0, GEAR_Z0)
        min_touch = min(min_touch, _common_vol(probe, make_slide_bar(off)))
    checks.append(("Banh rang luon nam trong dai rang cua thanh", min_touch > 1.0,
                   "chong lan nho nhat %.2f mm3" % min_touch))

    # --- 4. công tắc: ấn đúng, và chặn cơ đứng sau điểm tác động ---
    for is_max in sw_list():
        name = "MAX" if is_max else "MIN"
        off = TRAVEL if is_max else 0.0
        bar = make_slide_bar(off)
        face = bar.BoundBox.XMax if is_max else bar.BoundBox.XMin
        trip = X_TRIP_MAX if is_max else X_TRIP_MIN
        ok = abs(face - trip) < 0.05
        checks.append(("CT %s: mat dau thanh dung diem tac dong" % name, ok,
                       "mat o %.2f, diem trip %.2f" % (face, trip)))
    checks.append(("Chan co dung SAU diem trip %.1f mm" % SW_PRESS,
                   _X_MIN_MECH < X_TRIP_MIN and _X_MAX_MECH > X_TRIP_MAX,
                   "co %.1f..%.1f, trip %.1f..%.1f"
                   % (_X_MIN_MECH, _X_MAX_MECH, X_TRIP_MIN, X_TRIP_MAX)))
    # thân công tắc phải nằm ngoài vùng thanh quét
    bad = 0
    for is_max in sw_list():
        sw_body = _box2(*sw_body_x(is_max), SW_YC - SW_L / 2.0, SW_YC + SW_L / 2.0,
                        SW_Z0, SW_Z1)
        for off in _offsets():
            if _common_vol(make_slide_bar(off), sw_body) > 1e-6:
                bad += 1
    checks.append(("Than 2 CT nam NGOAI vung thanh quet", bad == 0,
                   "%d va cham" % bad))

    # --- 4b. BÁNH XE công tắc phải ấn trúng CHÂN +Y của thanh ---
    # Đây là cái bẫy riêng của cơ cấu này: thanh có tiết diện chữ П, vùng giữa
    # (|y| < PIN_RA + 0.5) là RỖNG. Bánh xe đặt trong vùng đó thì không chạm gì cả.
    bad = []
    for is_max in sw_list():
        off = TRAVEL if is_max else 0.0
        f = sw_front_x(is_max)
        s = sw_sign(is_max)
        roll = _cyl_z(SW_ROLLER_D, SW_ROLLER_W,
                      f + sw_dir(is_max) * (SW_ROLLER_PROUD - SW_ROLLER_D / 2.0),
                      sw_roller_y(),
                      SW_Z0 + (SW_T - SW_ROLLER_W) / 2.0)
        v = _common_vol(roll, make_slide_bar(off))
        if v < 1.0:
            bad.append("%s (%.2f mm3)" % ("MAX" if is_max else "MIN", v))
    checks.append(("Banh xe CT an trung CHAN +Y cua thanh", not bad,
                   "banh xe o y = %.2f (chan +Y bat dau %.2f)%s"
                   % (sw_roller_y(), RACK_ROOT_Y,
                      "" if not bad else " HUT: " + ", ".join(bad))))

    # --- 4c. ở CHẶN CƠ, thanh vẫn chưa đụng vách đầu hộp ---
    worst = 0.0
    for off in (-SW_PRESS, TRAVEL + SW_PRESS):
        worst = max(worst, _common_vol(make_slide_bar(off), housing))
    checks.append(("O CHAN CO (+-%.1f mm) thanh chua dung vo" % SW_PRESS, worst < 1e-6,
                   "va cham %.3f mm3" % worst))

    # --- 4c-bis. CỮ CỨNG đầu +X phải TỒN TẠI (chỉ có nghĩa khi bỏ CT MAX) ---
    # Không có CT MAX thì cần gạt công tắc không còn làm cữ. Nếu không có gì chặn,
    # mất bước tích luỹ sẽ đẩy thanh chạy tiếp tới khi va bừa vào trụ/vách/trục.
    if not SW_MAX:
        over = HARD_STOP_X - X_TRIP_MAX          # thanh còn đi thêm được bao nhiêu
        hit = _common_vol(make_slide_bar(TRAVEL + over + 0.5), housing)
        clear = _common_vol(make_slide_bar(TRAVEL + over - 0.3), housing)
        checks.append(("Co CU CUNG chan o dau +X", hit > 1.0 and clear < 1e-6,
                       "cham o +%.1f mm sau diem trip (%.1f mm3), truoc do sach"
                       % (over, hit)))
        checks.append(("Cu cung cach diem trip 0.8..3.0 mm",
                       0.8 <= over <= 3.0, "%.1f mm" % over))

    # --- 4d. 2 bạc trục trơn thông suốt, trục xỏ qua được ---
    bad = []
    for nm, y in (("A", ROD_A_Y), ("B", ROD_B_Y)):
        probe = _cyl_x(ROD_D + 0.2, BAR_L + 4.0, bar_x0(0.0) - 2.0, y, ROD_Z)
        if _common_vol(probe, make_slide_bar(0.0)) > 1e-6:
            bad.append(nm)
    checks.append(("2 bac truc tron THONG SUOT ca chieu dai thanh", not bad,
                   "bac A O%.1f tron, bac B ranh +-%.1f theo Y"
                   % (ROD_BORE, ROD_SLOT_Y / 2.0)))

    # --- 5. lắp: động cơ thả thẳng từ trên xuống ---
    drop = _sweep_z(motor, INNER_TOP - MOT_Z0 + 5.0)
    v = _common_vol(drop, housing)
    checks.append(("Dong co tha THANG tu tren xuong khong vuong", v < 1e-6,
                   "vuong %.2f mm3" % v))

    # --- 6. lắp: thanh thả thẳng từ trên xuống (chưa có trục trơn) ---
    bar_home = make_slide_bar(0.0)
    drop = _sweep_z(bar_home, INNER_TOP - BAR_Z0 + 5.0)
    v = _common_vol(drop, housing)
    v2 = _common_vol(drop, motor)
    checks.append(("Slide_Bar ha THANG xuong khong vuong vo", v < 1e-6,
                   "vuong %.2f mm3" % v))
    checks.append(("Slide_Bar ha THANG xuong khong vuong DC/banh rang",
                   v2 < 1e-6, "vuong %.2f mm3" % v2))

    # --- 7. lắp: 2 trục trơn đẩy TỪ NGOÀI vách +X ---
    for nm, y in (("A", ROD_A_Y), ("B", ROD_B_Y)):
        probe = _cyl_x(ROD_D + 0.2, BOX_X1 - INNER_X1 + 2.0, INNER_X1 - 0.5, y, ROD_Z)
        thru = _common_vol(probe, housing) < 1e-6
        pocket = _cyl_x(ROD_D + 0.2, ROD_POCKET - 0.5, ROD_X0 + 0.3, y, ROD_Z)
        blind = _common_vol(pocket, housing) < 1e-6
        checks.append(("Truc tron %s: lo XUYEN vach +X + hoc mu -X" % nm,
                       thru and blind,
                       "xuyen=%s hoc=%s, truc dai %.1f mm" % (thru, blind, ROD_LEN)))

    # --- 8. lắp: nắp hạ thẳng, trụ gá tải lọt khe suốt hành trình ---
    lid = parts["Housing_Lid"]
    bad = 0
    for off in _offsets():
        if _common_vol(make_slide_bar(off), lid) > 1e-6:
            bad += 1
    checks.append(("Tru ga tai lot khe nap suot hanh trinh", bad == 0,
                   "%d va cham, khe x = %.1f..%.1f" % ((bad,) + lid_slot_x())))
    drop = _sweep_z(lid, 12.0)
    checks.append(("Nap ha THANG tu tren xuong", _common_vol(drop, housing) < 1e-6,
                   "vuong %.2f mm3" % _common_vol(drop, housing)))

    # --- 9. mọi con vít đều có đường đưa tua vít vào (cột thẳng đứng) ---
    bad = []
    # (tên, x, y, Ø mũ vít, z ĐỈNH MŨ VÍT) — cột thăm dò bắt đầu TỪ ĐỈNH MŨ VÍT trở lên,
    # không phải từ chân vít: dưới mũ vít chính là bệ/trụ mà vít bắt vào.
    screws = [("tai DC -Y", MOT_CX, -EAR_POST_YC, EAR_SCREW_HEAD_D, EAR_SCREW_TOP),
              ("tai DC +Y", MOT_CX, +EAR_POST_YC, EAR_SCREW_HEAD_D, EAR_SCREW_TOP)]
    for is_max in sw_list():
        for i, (x, y) in enumerate(sw_hole_xy(is_max)):
            screws.append(("CT %s #%d" % ("MAX" if is_max else "MIN", i + 1),
                           x, y, SW_SCREW_HEAD_D, SW_SCREW_TOP))
    for nm, x, y, d, z0 in screws:
        col = _cyl_z(d + 1.0, INNER_TOP + 2.0 - z0, x, y, z0)
        if _common_vol(col, housing) > 1e-6:
            bad.append(nm)
    checks.append(("Moi vit deu co duong dua tua vit vao (thang dung)", not bad,
                   "vuong: %s" % (", ".join(bad) if bad else "khong")))

    # --- 10. 4 vít nắp xuyên nắp vào đúng trụ ---
    bad = 0
    for x, y in lid_tap_xy():
        probe = _cyl_z(M3_TAP - 0.3, LID_T + 8.0, x, y, INNER_TOP - 8.0)
        if _common_vol(housing, probe) > 1e-6:
            bad += 1
        if _common_vol(lid, probe) > 1e-6:
            bad += 1
    checks.append(("4 vit M3 xuyen nap vao tru khung", bad == 0, "%d lo bi bit" % bad))

    # --- 11. 4 tai bắt máy thông và không bị nắp che ---
    bad = 0
    for x, y in machine_ear_xy():
        probe = _cyl_z(EAR_HOLE - 0.4, BASE_T + 4.0, x, y, -2.0)
        if _common_vol(housing, probe) > 1e-6:
            bad += 1
        if _common_vol(lid, _cyl_z(EAR_HOLE + 3.0, BOX_Z1, x, y, BASE_T)) > 1e-6:
            bad += 1
    checks.append(("4 tai M4 thong va khong bi nap che", bad == 0, "%d loi" % bad))

    # --- 12. lỗ ra dây thông ---
    probe = _cyl_x(CABLE_D - 1.0, WALL_END_T + 4.0, BOX_X0 - 2.0,
                   DUCT_YC, BASE_T + DUCT_Z1 / 2.0)
    checks.append(("Lo luon day thong qua vach -X", _common_vol(housing, probe) < 1e-6,
                   "O%.1f tai y = %.1f" % (CABLE_D, DUCT_YC)))

    # --- 13. khối liền + hành trình ---
    checks.append(("Housing la 1 khoi lien", len(housing.Solids) == 1,
                   "%d khoi" % len(housing.Solids)))
    checks.append(("Hanh trinh dat yeu cau %.0f mm" % TRAVEL,
                   abs((X_TRIP_MAX - X_TRIP_MIN) - (TRAVEL + BAR_L)) < 1e-6,
                   "%.1f mm (thanh dai %.1f)" % (TRAVEL, BAR_L)))
    # --- 14. lực giữ khi TẮT ĐIỆN (detent) so với tải ---
    hold = MOT_DETENT / PIN_R
    checks.append(("Luc giu khi tat dien >= 10x tai", hold >= 10.0 * LOAD_N,
                   "%.1f N (tai %.2f N, du %.0f lan)" % (hold, LOAD_N, hold / LOAD_N)))
    # --- 15. thời gian chạy hết hành trình ---
    secs = TRAVEL / (MOT_RPM * PIN_MM_PER_REV / 60.0)
    checks.append(("Chay het hanh trinh <= 4 s", secs <= 4.0,
                   "%.2f s @ %.0f rpm (%.1f mm/vong)" % (secs, MOT_RPM, PIN_MM_PER_REV)))
    return checks


# ---------------------------------------------------------------------------
# 12. Dựng document
# ---------------------------------------------------------------------------
def add_part(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    vo = getattr(obj, "ViewObject", None)
    if vo is not None:
        vo.ShapeColor = color
        if transparency:
            vo.Transparency = transparency
    return obj


def build_parts() -> dict:
    parts = {
        "Housing": make_housing(),
        "Housing_Lid": make_housing_lid(),
        "BYJ_Motor": make_motor(),
        "Pinion": make_pinion(0.0),
        "Slide_Bar": make_slide_bar(0.0),
        "Guide_Rod_A": make_guide_rod(ROD_A_Y),
        "Guide_Rod_B": make_guide_rod(ROD_B_Y),
        "Limit_Switch_Min": make_limit_switch(False),
    }
    if SW_MAX:
        parts["Limit_Switch_Max"] = make_limit_switch(True)
    return parts


COLORS = {
    "Housing": ((0.55, 0.58, 0.65), 0),
    "Housing_Lid": ((0.62, 0.66, 0.72), 55),
    "BYJ_Motor": ((0.25, 0.28, 0.34), 0),
    "Pinion": ((0.92, 0.62, 0.18), 0),
    "Slide_Bar": ((0.30, 0.66, 0.42), 0),
    "Guide_Rod_A": ((0.78, 0.80, 0.84), 0),
    "Guide_Rod_B": ((0.78, 0.80, 0.84), 0),
    "Limit_Switch_Min": ((0.85, 0.25, 0.25), 0),
    "Limit_Switch_Max": ((0.85, 0.25, 0.25), 0),
}


def main() -> None:
    doc = App.newDocument("byj_rack_stage")
    parts = build_parts()
    for name, shape in parts.items():
        color, tr = COLORS.get(name, ((0.7, 0.7, 0.7), 0))
        add_part(doc, name, shape, color, tr)
    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)

    print("--- THONG SO ---")
    print("  Hop ngoai (X x Y x Z)      : %.1f x %.1f x %.1f mm"
          % (BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_Z1))
    print("  Khoang trong               : %.1f x %.1f x %.1f mm"
          % (INNER_X1 - INNER_X0, INNER_Y1 - INNER_Y0, INNER_TOP - BASE_T))
    print("  HANH TRINH                 : %.1f mm  (x = %.1f .. %.1f)"
          % (TRAVEL, X_TRIP_MIN, X_TRIP_MIN + TRAVEL))
    print("  Banh rang                  : m%.2f z%d, R = %.2f, O dinh = %.1f"
          % (GEAR_M, GEAR_Z, PIN_R, 2 * PIN_RA))
    print("  Thanh rang                 : dai %.1f mm, thanh dai %.1f mm"
          % (RACK_L, BAR_L))
    print("  Toc do                     : %.2f mm/vong -> %.1f mm/phut @ %.0f rpm"
          % (PIN_MM_PER_REV, PIN_MM_PER_REV * MOT_RPM, MOT_RPM))
    print("  Het hanh trinh             : %.2f s"
          % (TRAVEL / (MOT_RPM * PIN_MM_PER_REV / 60.0)))
    print("  Do phan giai (4096 buoc/vg): %.4f mm/buoc" % (PIN_MM_PER_REV / 4096.0))
    print("  Luc giu khi TAT DIEN       : %.2f N (detent %.1f N.mm / R %.1f)"
          % (MOT_DETENT / PIN_R, MOT_DETENT, PIN_R))
    if SW_MAX:
        print("  Cong tac                   : 2 (MIN home + MAX bao ve)")
    else:
        print("  Cong tac                   : 1 (chi MIN home) — SW_MAX=False")
        print("  Cu cung dau +X             : x = %.1f, tuc +%.1f mm sau diem trip"
              % (HARD_STOP_X, HARD_STOP_X - X_TRIP_MAX))
        print("  Gioi han mem khuyen nghi   : 0 .. %.1f mm" % (TRAVEL - 1.0))
    print("  Truc tron O%.0f             : 2 cay, dai %.1f mm" % (ROD_D, ROD_LEN))

    print("--- NGAN SACH CHIEU DAI HOP (X) ---")
    end_zone = X_TRIP_MIN - INNER_X0
    rows = [
        ("Thanh rang (= hanh trinh + 2 x bien an khop)", RACK_L),
        ("+ 2 mep dac dau thanh", 2.0 * BAR_END_T),
        ("= chieu dai THANH", BAR_L),
        ("+ HANH TRINH (thanh quet di)", TRAVEL),
        ("= vung thanh quet", BAR_L + TRAVEL),
    ]
    for label, val in rows:
        print("  %-46s %7.1f" % (label, val))
    print("  %-46s %7.1f" % ("+ cum CT MIN (banh xe %.0f + than %.0f + chan han %.1f)"
                             % (_SW_OVERTRAVEL, SW_H, SW_TERM_ZONE), end_zone))
    if SW_MAX:
        print("  %-46s %7.1f" % ("+ cum CT MAX", INNER_X1 - X_TRIP_MAX))
    else:
        print("  %-46s %7.1f" % ("+ khe cuoi (KHONG co CT MAX)", INNER_X1 - X_TRIP_MAX))
    print("  %-46s %7.1f" % ("= khoang trong", INNER_X1 - INNER_X0))
    print("  %-46s %7.1f" % ("+ vach -X (%.1f, chua 2 hoc mu) + vach +X (%.1f)"
                             % (WALL_END_T, WALL_T), WALL_END_T + WALL_T))
    print("  %-46s %7.1f" % ("= HOP NGOAI theo X", BOX_X1 - BOX_X0))

    print("--- KIEM TRA ---")
    checks = verify(parts)
    n_fail = 0
    for label, ok, detail in checks:
        if not ok:
            n_fail += 1
        print("  [%s] %-52s %s" % ("OK" if ok else "FAIL", label, detail))
    print("  => %d FAIL / %d checks" % (n_fail, len(checks)))

    metrics = {
        "pass": n_fail == 0,
        "checks_fail": n_fail,
        "checks_total": len(checks),
        "travel_mm": TRAVEL,
        "box_outer_mm": [BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_Z1],
        "gear": {"m": GEAR_M, "z": GEAR_Z, "R": PIN_R, "mm_per_rev": PIN_MM_PER_REV},
        "rack_len_mm": RACK_L,
        "bar_len_mm": BAR_L,
        "rod_len_mm": ROD_LEN,
        "sec_full_travel": TRAVEL / (MOT_RPM * PIN_MM_PER_REV / 60.0),
        "hold_force_N": MOT_DETENT / PIN_R,
        "sw_max": SW_MAX,
        "n_switches": 2 if SW_MAX else 1,
        "hard_stop_x": HARD_STOP_X,
        "hard_stop_over_trip_mm": HARD_STOP_X - X_TRIP_MAX,
        "soft_limit_mm": TRAVEL - 1.0,
    }
    mpath = OUT / "byj_rack_stage_metrics.json"
    mpath.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print("Metrics:", mpath)

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
    else:
        App.closeDocument(doc.Name)


main()
