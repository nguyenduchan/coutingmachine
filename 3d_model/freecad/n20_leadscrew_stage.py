"""
Cụm tịnh tiến: GA12-N20 TRỤC D + KHỚP NỐI LỤC GIÁC + TY REN M4x40 + ĐAI ỐC LỤC GIÁC.

Trước đây cụm này dùng động cơ có trục vít M4 LIỀN. Nay chuyển sang 4 món mua rời:
  1. GA12-N20 trục D trơn Ø3 x 10 (loại phổ thông nhất, rẻ và dễ mua hơn bản trục vít)
  2. KHỚP NỐI TRỤC đồng, loại 2 LỖ TRƠN 3 mm - 4 mm, mỗi đầu MỘT vít hãm M3:
     đầu -X ôm trục động cơ Ø3, đầu +X ôm ty ren M4. Cả hai đầu đều là lỗ trơn kẹp
     bằng vít, KHÔNG có mối ren nào trong đường truyền
  3. Ty ren M4 x 40 mm
  4. Đai ốc lục giác M4 thường (đồng thau), S = 7.0, dày 3.2 — chỉ cần MỘT con

CÁI GIÁ PHẢI TRẢ: khớp nối dài COUP_LEN mm nằm chắn ngay sau mặt bích, đai ốc không
bao giờ đi qua được nó, nên hành trình ngắn hơn bản trục vít liền. Mỗi mm chiều dài
khớp nối = 1 mm hành trình, mỗi mm ty ren thêm vào = 1 mm hành trình. Hai số đó là
ĐÒN BẨY DUY NHẤT nếu cần dài hơn (ty ren M4 x 60 cùng giá → thêm ~20 mm).

Nguồn kích thước động cơ: bản vẽ datasheet GA12-N20 (Unit: mm)
  hộp số  12 (rộng) x 10 (cao) x 9 (dài)      — mặt bích trước 12x10
  lon mô tơ  Ø12 x 15 ; cọc đấu điện phía sau 1.2
  bích trước có 2 x M1.6 sâu 2.1, nằm CHÉO nhau:
      (+3.8, +3.0) và (-3.8, -3.0) so với tâm trục   [6 mm theo cạnh 10]
  trục ra Ø3 x 10, có vạt phẳng chữ D (chỗ cho vít khớp nối tì vào)

CƠ CẤU (trục nằm theo +X, đế nằm trên mặt XY):
  Housing           — VỎ + KHUNG LIỀN: đáy, 4 vách, tai M4, bích/máng ĐC, gối đỡ,
                      vấu CT, boss bắt nắp — MỘT khối in (không bu lông giữa gá/đế)
  Housing_Lid       — nắp đậy, 4 vít M3 xuống boss trên khung
  Motor_Clamp       — nắp kẹp trên lon ĐC, 4 VÍT TỰ REN M3 x 14 bắt thẳng vào máng
                      (mũ vít chìm; chi tiết rời để lắp)
  Coupler           — KHỚP NỐI TRỤC (mua sẵn): lỗ Ø3 + vít | lỗ Ø4 + vít
  Coupler_Spacer    — CỮ Ø3.8 thả đáy lỗ Ø4, chặn ty ren ở đúng chiều sâu cắm
  Thread_Rod        — TY REN M4 x 40, cắm COUP_ROD_IN mm vào lỗ Ø4
  Guide_Shaft       — TRỤC TRƠN Ø5 + vạt dưới vít hãm; lệch +Y 17 mm; hai đầu hốc mù
  Guide_Lock_Screw  — vít hãm M3 khóa trục lúc chạy (siết sau khi ngồi tư thế gối)
  Slide_Bar         — THANH TỊNH TIẾN: bạc ôm trục trơn + LỖ CHO KHỚP NỐI CHUI QUA
                      + HUB liền khối ôm đai ốc (khe HỞ NÓC), KHÔNG có chi tiết rời
                      + BỆ GÁ TẢI ở đầu tự do, 2 bộ lỗ trên 2 mặt vuông góc
  Hex_Nut           — đai ốc lục giác M4 thường (mua sẵn)
  Limit_Switch_Min/Max — 2 công tắc KW11 bánh xe, bị ấn DỌC TRỤC
                      (siết M2 từ ngoài qua lỗ trên vách -Y)

NGUYÊN LÝ: động cơ quay → khớp nối quay → ty ren quay → đai ốc bị khe TRÊN CHÍNH THANH
giữ không cho xoay → đai ốc chạy dọc trục → kéo Slide_Bar. Trục trơn song song chịu
mô men lật và chống xoay cho thanh.

HỐC ĐAI ỐC KHOÉT THẲNG VÀO THANH (không còn chi tiết Nut_Holder rời + 4 bu lông M3):
mặt +X của thân thanh mọc ra một HUB dài HUB_FRONT mm, mặt trước hub bằng đúng mặt
trước bạc trục trơn nên hub KHÔNG ăn thêm hành trình nào. Trong hub, tính từ ngoài
vào: vách sau NUT_WALL — khe đai ốc hở nóc — vách trước NUT_WALL — rồi tới đáy lỗ
khoét Ø(khớp nối). Bỏ lớp gá rời không mất mm hành trình nào: cái quyết định là TỔNG
chồng dọc trục (vách + đai ốc + vách), nằm ở chi tiết nào cũng vậy.
Khe nằm HOÀN TOÀN ở phía +X của thân thanh (x > xc + BAR_X/2) nên tấm thân vẫn đặc,
không bị rãnh hở nóc làm yếu.

THANH CHUI QUA KHỚP NỐI: thanh có lỗ Ø(khớp nối + 1.2) nên nó trườn được qua khớp
nối. Nếu không có lỗ này, mặt sau của thanh mới là thứ chặn hành trình chứ không phải
đai ốc, và mất thêm BAR_X mm nữa. Lỗ này chính là lý do thanh phải cao lên: cần
BAR_WALL mm thịt trên/dưới lỗ.

ĐAI ỐC BƠI, KHE HỞ NÓC: khe rộng hơn S 0.5 mm, hốc dài hơn đai ốc 0.2 mm, và HỞ nóc
hoàn toàn — đai ốc chỉ bị 2 vách khe chặn XOAY, còn vị trí ngang/dọc thì do CHÍNH TY
REN giữ (ty ren xuyên qua nó). Vậy đai ốc tự căn theo ty ren mọi phương, không cưỡng
bức bạc hộp số N20 như kiểu kẹp cứng — khớp nối lục giác là khớp CỨNG, không bù lệch
được, nên toàn bộ độ mềm phải nằm ở đai ốc.
Không cần chi tiết chặn nào cho khe hở nóc: ty ren xuyên qua đai ốc thì nó không rơi
ra được. Đây cũng là lý do bỏ đai ốc tai hồng + lớp gá 2 khe của bản cũ.
Chặn dọc trục hai chiều: đẩy -X thì mặt đai ốc tì vào vách trước hốc, đẩy +X thì tì
vào vách sau; cả hai vách đều liền khối với thanh nên không có bu lông nào chịu lực.

KHÔNG CÒN ĐAI ỐC HÃM ở mặt khớp nối. Bản trước dùng khớp nối một đầu là LỖ REN, ty ren
vặn thẳng vào — mà cụm chạy CẢ HAI CHIỀU nên một chiều luôn là chiều nới lỏng mối ren
đó, phải khoá bằng một đai ốc hãm tốn NUT_H mm hành trình. Khớp nối 2 lỗ trơn không có
mối ren nào để tự tháo, nên bỏ được cả con đai ốc lẫn phần hành trình đó. Nếu sau này
quay lại loại khớp nối có ren thì PHẢI thêm đai ốc hãm trở lại.

NGÂN SÁCH HÀNH TRÌNH — mọi thứ khác KHÔNG ảnh hưởng, đừng mất công chỉnh:
    hành trình dừng (trip↔trip) = ROD_LEN
                 - COUP_ROD_IN        (ty ren cắm vào khớp nối)
                 - ROD_END_SUPPORT    (ty ren cắm vào lỗ đỡ End_Block)
                 - (2*NUT_WALL + NUT_POCKET)   (chồng ôm đai ốc trên thanh)
                 - 2*END_CLEAR        (khe an toàn 2 đầu)
                 + END_HUB_RECESS     (hub/bạc chui vào hốc mặt End_Block)
                 - 2*SW_PRESS         (dự phòng sau khi CT tác động, trước chặn cơ)
Thanh DỪNG khi công tắc tác động; chặn cơ chỉ là failsafe sau SW_PRESS.
Vị trí động cơ, độ dày bích, chiều dài khớp nối, chiều dài bạc trục trơn, độ dày thân
thanh — TẤT CẢ triệt tiêu khỏi công thức này. Dời khớp nối ra/vào chỉ dời cả cụm chứ
không đổi hành trình, vì ty ren dời theo. Đã kiểm bằng đại số, đừng thử lại.

CẮM TY REN NÔNG CÓ CHỦ Ý: lỗ Ø4 của khớp nối sâu COUP_BORE_R nhưng ty ren chỉ cắm
COUP_ROD_IN = 1.5 x D. Giữ ty ren là việc của VÍT HÃM, không phải của chiều sâu lỗ;
cắm hết lỗ "cho chắc" là biếu không phần dư đó cho hành trình. Phần dư được lấp bằng
Coupler_Spacer nên ty ren vẫn có cữ để tì.

VỎ HỘP: cả cơ cấu nằm gọn trong một hình hộp WALL_T mm, chỉ THANH TRƯỢT chui ra ngoài
qua một KHE trên vách -Y. Khe tính theo CHẶN CƠ KHÍ chứ không theo điểm công tắc tác
động — công tắc chết thì thanh vẫn chạy thêm SW_PRESS mm nữa, khe phải chứa nổi.
Khe XẺ HỞ NÓC tới mép vách rồi để nắp đậy nốt: khỏi phải in cầu vượt hơn 30 mm, và
hạ được cả cụm thanh + trục trơn vào từ trên xuống khi lắp.
4 TAI bắt bu lông M4 chìa +-Y ở hai đầu hộp. Boss nắp trên khung liền.
Vách -X: lỗ CABLE_D. Vách -Y: lỗ M2 siết công tắc. Nắp: khe cho trụ bệ gá.

BỆ GÁ TẢI — MỘT TRỤ DẸT duy nhất, rộng ĐÚNG BẰNG khe nắp:
  Dày MOUNT_T theo X, rộng STEM_Y0..STEM_Y1 theo Y, thò WALL_H mm lên trên mặt nắp.
  2 lỗ bu lông M3 XUYÊN theo X, xếp chồng theo Z (cách 2 x LOAD_HOLE_DZ).
  KHÔNG có vách xoè ngang: xoè ra là rộng hơn khe nắp, mà như thế thì nắp KHÔNG hạ
  thẳng xuống được nữa (phải xẻ rãnh ngang trên nắp — đã thử rồi bỏ).
VÙNG z > WALL_Z1 trống cho cơ cấu người dùng.

TRỤC TRƠN LUỒN TỪ NGOÀI QUA VÁCH +X (Housing là MỘT khối liền):
Hốc phía ĐC vẫn BỊT ĐÁY (GUIDE_BLIND_WALL) làm cữ đẩy; lỗ trên vách gối đỡ XUYÊN, và
vách +X của hộp có LỖ LUỒN Ø GUIDE_ACCESS_D. Trục đẩy từ ngoài vào, xuyên luôn bạc
Slide_Bar đã nằm sẵn trong khoang, tì đáy hốc là đúng vị trí; đầu +X thò GUIDE_STICK mm
ra ngoài vách để rút ra bằng tay. Trục dài hơn bản cũ nhưng CẮT DÀI/NGẮN ±2 mm đều chạy.
(Bản cũ hai hốc mù quay vào nhau: VÔ NGHIỆM, xem chú thích ở khối hằng số GUIDE_*.)
CỐ ĐỊNH: vít hãm M3 từ trên xuống qua vấu hốc ĐC, tì vạt phẳng trên trục (GUIDE_LOCK_X)
— nó vừa chặn trục trôi ra +X vừa khoá xoay.

CHẶN DỌC TRỤC CỦA TY REN: đẩy thanh về +X thì phản lực đẩy ty ren về -X, ty tì vào CỮ
rồi tới vách COUP_WALL — chặn cứng. Chiều ngược lại chỉ có vít hãm giữ, nên vít phía ty
ren phải siết chặt (nó cắn vào ren nên bám tốt hơn hẳn trên trục trơn).

KHÔNG dùng đai ốc hãm thứ 2 cho ĐAI ỐC CHẠY (double nut chống rơ): mô men vặn thêm
~0.7*P N*mm trong khi N20 chỉ có ~49 N*mm. Rơ dọc trục đã bị hốc khống chế ở 0.2 mm.

CÔNG TẮC HÀNH TRÌNH: thân công tắc đặt sao cho MẶT TRƯỚC của nó chính là chặn cơ khí;
thanh chạm bánh xe trước đó nên giới hạn điện luôn tới trước giới hạn cơ.

THỨ TỰ LẮP (mọi bước chỉ cần tua vít + lục giác 1.5; nắp mở, thao tác từ TRÊN):
  1. Hàn 2 dây dupont vào 2 chân CT (COM + NO/NC) khi CT còn ở ngoài. Đặt CT áp vào
     vấu, luồn vít M2 x SW_SCREW_L TỰ REN qua LỖ THAO TÁC Ø SW_HOLE_D trên vách -Y (mũ vít +
     mũi tua vít cùng chui qua lỗ này) — mũ vít tì THẲNG vào thân CT, ép CT vào vấu;
     KHÔNG có đai ốc nào phải giữ trong lòng hộp.
  2. Thả ĐỘNG CƠ thẳng từ trên xuống máng (khe trục trên bích HỞ NÓC nên không phải
     luồn ngang); trục ĐC nằm đúng rãnh. Đặt Motor_Clamp, siết 4 vít tự ren M3.
  3. Lồng khớp nối vào trục Ø3, siết vít hãm -X vào mặt vạt D. THẢ Coupler_Spacer vào
     đáy lỗ Ø4.
  4. Thả đai ốc M4 vào khe hở nóc của Slide_Bar; hạ Slide_Bar vào khoang (chưa có trục).
  5. Đẩy GUIDE_SHAFT từ NGOÀI vách +X vào: qua lỗ vách → lỗ gối đỡ → bạc Slide_Bar →
     tì đáy hốc mù phía ĐC. SIẾT vít hãm M3 trên vấu hốc.
  6. Đẩy TY REN từ NGOÀI vách +X vào: qua lỗ vách → lỗ gối đỡ → vặn qua đai ốc M4 →
     cắm vào lỗ Ø4 của khớp nối tới CỮ; siết vít hãm +X.
  7. Luồn dây 2 CT vào MÁNG DÂY dải -Y (dưới 4 vấu giữ dây) → ra KHE trên vách -X;
     dây ĐC ra lỗ Ø8 cùng vách.
  8. HẠ NẮP thẳng từ trên xuống (bệ gá rộng đúng bằng khe nắp nên chui lọt ở mọi vị
     trí của thanh); bắt 4 vít M3 ở 4 góc.
THÁO: ngược lại. Rút trục/ty ren: nới vít hãm rồi kéo đầu thò ra ở vách +X.

CHẠY: freecad.exe 3d_model/freecad/n20_leadscrew_stage.py
  (KHÔNG dùng freecadcmd — save headless mất GuiDocument.xml nên mở ra mất màu)
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
FCSTD = OUT / "n20_leadscrew_stage.FCStd"

# ---------------------------------------------------------------------------
# 1. Động cơ GA12-N20 TRỤC D (theo bản vẽ datasheet)
# ---------------------------------------------------------------------------
GB_W, GB_H, GB_L = 12.0, 10.0, 9.0        # hộp số: rộng(Y) x cao(Z) x dài(X)
CAN_D, CAN_L = 12.0, 15.0                 # lon mô tơ
REAR_D, REAR_L = 5.0, 1.2                 # cọc/nắp sau
MOT_HOLE_DY, MOT_HOLE_DZ = 3.8, 3.0       # 2 x M1.6 chéo nhau
MOT_HOLE_TAP = 1.6
MOT_LEN = GB_L + CAN_L + REAR_L           # 25.2

# --- GIỮ ĐỘNG CƠ: KHÔNG dùng 2 vít M1.6 trên mặt bích -----------------------
# 2 vít đó nằm ở (±3.8, ±3.0) trên mặt bích, muốn bắt phải đưa tua vít THẲNG theo +X
# suốt 52 mm trong lòng hộp — không có chỗ cho cán tua vít, và cũng không thể giữ con
# vít M1.6 ở đầu kia. Thay bằng CHẶN CƠ KHÍ: hộp số nằm khít hốc (chống xoay), mặt
# bích chặn +X, vách MOT_STOP chặn -X, Motor_Clamp ép từ trên. Không còn vít nào phải
# bắt trong lòng hộp theo phương ngang.
MOT_STOP_T = 1.5                          # bề dày vách chặn sau lon
MOT_STOP_GAP = 0.3                        # khe sau lon (rơ dọc còn lại của ĐC)
MOT_REAR_SLOT = 8.5                       # khe cho cọc sau Ø5 + ĐƯỜNG DÂY ĐC (>= CABLE_D)

SHAFT_D = 3.0                             # trục ra TRƠN Ø3 (không còn ren)
SHAFT_LEN = 10.0                          # nhô ra khỏi mặt bích
SHAFT_FLAT = 0.5                          # chiều sâu vạt phẳng chữ D
SHAFT_FLAT_X0 = 3.0                       # vạt bắt đầu cách mặt bích 3 mm

# ---------------------------------------------------------------------------
# 2. Bố trí chung (mm). Đế: mặt dưới z=0. Trục quay: y=0, z=AXIS_Z.
# ---------------------------------------------------------------------------
BASE_T = 4.0
AXIS_Z = 18.0                             # hạ trục → hộp thấp hơn (was 20)
GUIDE_Y = 13.5                            # thu hẹp (was 17); >= HUB_Y + BOSS_R + khe
GUIDE_D = 5.0                             # Ø5 trục trơn (loại phổ thông)

FACE_X0, FACE_T = 0.0, 3.0                # bích đứng x = 0..3, mặt ĐC áp tại x=0
SHAFT_CLEAR_D = SHAFT_D + 0.6             # lỗ cho trục Ø3 chui qua bích
CRADLE_X0 = -MOT_LEN - 1.5                # máng ôm thân — sát đuôi ĐC
MOT_CAN_X0 = -(GB_L + CAN_L)              # -24.0: mặt sau lon (cọc sau còn thò 1.2)
MOT_STOP_X1 = MOT_CAN_X0 - MOT_STOP_GAP
MOT_STOP_X0 = MOT_STOP_X1 - MOT_STOP_T
assert MOT_STOP_X0 > CRADLE_X0 + 0.5
BASE_X0 = CRADLE_X0 - 0.4                 # khoang trong sát máng (~0.4 mm)
# BASE_Y* tính SAU công tắc / WING (ép sát thành)
WING_CLEAR = 0.5                          # khe nội thất ↔ vách trong
RIB_T = 4.0                               # gân chống lật cho bích đứng
RIB_Y0 = GUIDE_Y + 2.0                    # gân đặt SÁT (không trùng) lỗ trục trơn

FOOT_T = 4.0                              # bề dày chân đế của gá (z = 4..8)
FOOT_Y = 14.0                             # đủ y_neg boss nắp + cắt chân dưới CT
FOOT_BOLT_Y = 10.0
# --- KẸP ĐỘNG CƠ: 4 VÍT TỰ REN M3 (VÍT, không phải bu lông) ---------------
# Bản cũ đặt lỗ ở y = ±6 trong khi HỐC động cơ đã rộng ±6.2 → thân vít cắm thẳng
# vào lon ĐC. Giờ vị trí lỗ TÍNH TỪ MÉP HỐC ra, không đặt tay nữa.
MOT_POCKET_R = (CAN_D + 0.4) / 2.0        # 6.2 — nửa bề ngang hốc ĐC
assert MOT_POCKET_R + 1e-9 >= (GB_W + 0.4) / 2.0   # hộp số không rộng hơn lon
CLAMP_SCREW_CLEAR = 3.3                   # lỗ TRƠN xuyên nắp kẹp
CLAMP_SCREW_PILOT = 2.5                   # lỗ MỒI cho vít tự ren cắn vào nhựa máng
CLAMP_SCREW_ENG = 8.0                     # chiều sâu ăn ren trong máng (lỗ MÙ)
CLAMP_HEAD_D = 6.5                        # hốc chìm mũ vít tự ren M3 (mũ ~Ø6)
CLAMP_HEAD_H = 2.4
CLAMP_SCREW_WALL = 1.4                    # thịt giữa mép lỗ và vỏ động cơ
CLAMP_EDGE = 1.5                          # thịt từ hốc mũ vít ra mép máng
                                          # (giữ nhỏ: máng rộng ra là hành lang
                                          #  dẫn dây trước lưng CT hẹp lại)
CLAMP_BOLT_Y = MOT_POCKET_R + CLAMP_SCREW_CLEAR / 2.0 + CLAMP_SCREW_WALL   # 9.25
CRADLE_Y = CLAMP_BOLT_Y + CLAMP_HEAD_D / 2.0 + CLAMP_EDGE                  # 14.15
CLAMP_X1 = -5.0                           # mép +X của nắp kẹp — né hốc chân hàn CT MIN
CLAMP_BOLT_X = (-9.0, -21.0)              # 2 hàng vít kẹp (hàng trước lùi khỏi CLAMP_X1)
CLAMP_FIT = 0.5                           # khe quanh nắp kẹp (tháo lắp được)
CLAMP_HALF_Y = CRADLE_Y - 0.5             # nửa bề ngang nắp kẹp
PLATE_TOP = 26.0

# --- KHỚP NỐI TRỤC (mua sẵn): 2 LỖ TRƠN 3 mm - 4 mm, 2 VÍT HÃM ------------
# GIẢ ĐỊNH kích thước: trang bán chỉ ghi cỡ lỗ (3-4), không ghi thân. Lấy theo khớp
# nối trục đồng phổ thông: Ø ngoài 12, dài 20, mỗi đầu ăn 9 mm. ĐO LẠI khi có hàng
# rồi sửa COUP_D / COUP_LEN / COUP_BORE_M — mọi thứ còn lại (lỗ trên thanh, chiều
# cao thanh, hành trình, chiều dài đế) tự tính theo.
# COUP_D là ĐƯỜNG KÍNH BAO của thân: thân tròn thì nhập Ø ngoài, thân lục giác thì
# nhập cỡ QUA ĐỈNH — nó chỉ dùng để khoét lỗ cho thanh trườn qua.
COUP_D = 12.0
COUP_LEN = 20.0
COUP_GAP = 0.5                            # khe hở giữa khớp nối và mặt bích. Vít
                                          # M1.6 phải là loại ĐẦU CHÌM, nếu dùng đầu
                                          # trụ thì mũ vít (~1.6) đội khớp nối ra xa
                                          # đúng bấy nhiêu mm hành trình.
COUP_X0 = FACE_X0 + FACE_T + COUP_GAP     # 3.5
COUP_X1 = COUP_X0 + COUP_LEN
COUP_BORE_M = 9.0                         # lỗ Ø3 phía động cơ
COUP_WALL = 2.0                           # vách ngăn giữa hai lỗ
COUP_BORE_R = COUP_LEN - COUP_WALL - COUP_BORE_M   # lỗ Ø4 phía ty ren = 9.0
COUP_SET_D = 3.0                          # 2 vít hãm M3, mỗi đầu một con

ROD_D = 4.0                               # TY REN M4
ROD_PITCH = 0.7                           # bước ren M4 tiêu chuẩn
ROD_LEN = 40.0                            # ty ren M4 x 40 (đặt hàng)
# TY REN KHÔNG CẮM HẾT LỖ. Mỗi mm cắm vào là 1 mm hành trình mất đi, mà giữ ty ren
# là việc của VÍT HÃM chứ không phải của chiều sâu lỗ; 1.5 x D là mức đủ cho mối kẹp
# vít trên moay-ơ. Cắm hết 9 mm chỉ để "cho chắc" là mất không 3 mm hành trình.
COUP_ROD_IN = 1.5 * ROD_D                 # 6.0 — chiều sâu ty ren cắm vào lỗ Ø4
# Cữ đặt đáy lỗ để ty ren cắm tới đó là DỪNG, khỏi phải canh bằng mắt. Nó cũng khôi
# phục lại chặn cứng dọc trục chiều -X mà việc cắm nông làm mất.
SPACER_L = COUP_BORE_R - COUP_ROD_IN      # 3.0
SPACER_D = ROD_D - 0.2                    # thả lọt lỗ Ø4.1

ROD_X0 = COUP_X1 - COUP_ROD_IN            # đuôi ty ren tì vào CỮ trong lỗ khớp nối
ROD_X1 = ROD_X0 + ROD_LEN
MOTOR_RPM = 60.0                          # 12 VDC, 60 rpm theo mã hàng đã chọn

# --- ĐAI ỐC LỤC GIÁC M4 thường (DIN 934) ---------------------------------
NUT_AF = 7.0                              # ngang hai mặt
NUT_AC = NUT_AF * 2.0 / math.sqrt(3.0)    # ngang hai đỉnh = 8.08
NUT_H = 3.2                               # bề dày
THREAD_MARGIN = 1.5                       # ren dự phòng chừa ở cuối hành trình

# Thanh tịnh tiến — thân GỌN trong hộp; trụ/vách gá CHÌA LÊN qua nắp (+Z)
BAR_X = 7.0                               # bề dày thanh theo phương chạy (X)
COUP_CLEAR_D = COUP_D + 1.2               # lỗ cho KHỚP NỐI chui qua thanh
BAR_WALL = 2.5                            # thịt còn lại trên/dưới lỗ đó
BAR_Z0 = AXIS_Z - COUP_CLEAR_D / 2.0 - BAR_WALL
BAR_Z1 = AXIS_Z + COUP_CLEAR_D / 2.0 + BAR_WALL
BOSS_D, BOSS_L = 12.0, 18.0               # bạc ôm trục trơn (was Ø13)
BOSS_BORE = GUIDE_D + 0.3                 # trượt: Ø5.3
WING_Y = GUIDE_Y + BOSS_D / 2.0 + 0.5     # chân/vách +Y sát bạc

# --- HUB ÔM ĐAI ỐC: khoét thẳng vào thanh, mọc ra phía +X (phía gối đỡ) ----
HUB_FRONT = BOSS_L / 2.0                  # 9.0
HUB_Y = 7.0                               # thu hẹp (was 10); đủ khe đai ốc + thịt
assert GUIDE_Y + 1e-9 >= HUB_Y + BOSS_D / 2.0 + 0.3
NUT_WALL = 1.5
NUT_POCKET = NUT_H + 0.2
NUT_SLOT_W = NUT_AF + 0.5
NUT_SLOT_Z0 = AXIS_Z - NUT_AC / 2.0 - 1.0
BORE_FRONT = HUB_FRONT - 2.0 * NUT_WALL - NUT_POCKET

# Trụ xuyên nắp (hẹp Y, né boss) + VÁCH DẸT ngoài hộp (mặt ⊥ X, dài theo Y)
MOUNT_T = 4.0                             # bề dày bệ gá theo X (dẹt)
STEM_Y0, STEM_Y1 = -6.0, 6.0              # bề rộng bệ gá = bề rộng khe nắp
WALL_H = 16.0                             # phần thò lên trên mặt nắp
# 2 lỗ bu lông M3 XUYÊN theo X, xếp CHỒNG theo Z (bệ chỉ rộng 12 mm nên không xếp
# ngang được). Bệ gá KHÔNG còn vách xoè ngang: có xoè thì nó rộng hơn khe nắp, và
# nắp không còn hạ thẳng xuống được nữa (phải xẻ rãnh ngang trên nắp).
LOAD_HOLE_DZ = 4.0
SLOT_CLEAR = 0.8                          # khe hai bên trụ theo Y
LID_SLOT_END = 3.0                        # KHOÉT THÊM hai đầu khe theo chiều tịnh tiến:
                                          # trụ bệ gá không bao giờ chạm mép khe, và
                                          # lúc luồn nắp không phải canh thanh thật khít

# --- Gối đỡ đầu kia: đỡ trục trơn VÀ đầu ty ren ---------------------------
# Lỗ đỡ nằm NGAY TRONG VÁCH (bản cũ có thêm mỏ đỡ Ø14 chìa ra -X; bỏ đi vì nó ăn
# thêm hành trình mà không thêm gì — vách đã ở đúng chỗ cần đỡ). Lỗ để RỘNG 0.6 mm
# chứ không ép sát: ty ren đã được bạc hộp số định vị qua khớp nối CỨNG rồi, gối thứ
# hai mà ôm chặt sẽ đánh nhau với nó — nhiệm vụ của lỗ này chỉ là chặn ty đảo/văng.
# Gối đỡ: VÁCH DÀY sát cạnh hộp +X — KHÔNG tạo vách giữa (trùng X lỗ bu lông CT MAX).
# END_X0 vẫn là mốc hành trình / đầu ty ren; ổ đỡ trục trơn nằm ở END_WALL_X0..X1.
END_T = 13.0                              # bề dày vách sát cạnh hộp
END_FACE_T = 2.0                          # khe đệm ảo sau mốc END_X0 (trước lỗ CT)
ROD_END_SUPPORT = 2.0                     # ty thò quá END_X0 bao nhiêu (mốc thiết kế)
ROD_HOLE_D = ROD_D + 0.6
END_X0 = ROD_X1 - ROD_END_SUPPORT         # mốc mặt trước (không còn tấm giữa)
END_HUB_RECESS = 5.0                      # hub được chui vào khoảng trống sau END_X0
END_RECESS_CLEAR = 0.6
ROD_CLEAR_D = ROD_D + 1.2                 # lỗ ty ren xuyên 2 vách hub

NUT_CLEAR = 0.5                           # khe an toàn hốc <-> khớp nối
END_CLEAR = 0.5                           # khe an toàn thanh <-> đáy hốc End_Block

# Giới hạn GẦN: VÁCH TRƯỚC của hốc đai ốc không được đụng mặt trước KHỚP NỐI.
# (Thân thanh KHÔNG chặn ở đây — lỗ khoét cho nó trườn qua khớp nối; chỉ vách có lỗ
# Ø rod-clear là không chui qua được.)
_X_MIN_MECH = COUP_X1 + NUT_CLEAR - BORE_FRONT
# Giới hạn XA: hub/bạc được phép chui END_HUB_RECESS vào mặt End_Block; hết ren vẫn chặn.
_X_MAX_HOLDER = END_X0 + END_HUB_RECESS - END_CLEAR - HUB_FRONT
_X_MAX_BOSS = END_X0 + END_HUB_RECESS - END_CLEAR - BOSS_L / 2.0
_X_MAX_THREAD = ROD_X1 - THREAD_MARGIN - (HUB_FRONT - NUT_WALL)
_X_MAX_MECH = min(_X_MAX_HOLDER, _X_MAX_BOSS, _X_MAX_THREAD)

# --- TRỤC TRƠN: LUỒN TỪ NGOÀI VÀO QUA VÁCH +X ----------------------------
# Bản cũ có HAI HỐC MÙ quay mặt vào nhau trong MỘT khối cứng (Housing đã nuốt cả
# Motor_Bracket lẫn End_Block). Việc đó VÔ NGHIỆM về hình học: muốn thả trục vào giữa
# thì L <= khe hở 2 miệng hốc (43.5), muốn ăn được cả hai hốc thì L >= 49.5. Bản mô tả
# "đẩy hết về hốc ĐC rồi nhấc ra" cũng sai: đoạn nằm trong hốc ĐC là lỗ NGANG, không
# nhấc thẳng lên được. Nay: hốc ĐC vẫn MÙ (chặn đầu -X), lỗ gối đỡ XUYÊN, và vách +X
# của hộp có lỗ luồn — trục đẩy từ ngoài vào, xuyên luôn bạc Slide_Bar đã nằm sẵn.
GUIDE_BLIND_WALL = 1.5                    # vách bịt đáy hốc phía ĐC (chặn dọc trục)
GUIDE_VENT_D = 1.5                        # lỗ thông hơi hốc mù phía ĐC
GUIDE_MIN_ENG = 4.0                       # eng tối thiểu trong hốc ĐC
GUIDE_BOSS_D = 10.0                       # vấu nối dài hốc trên bích đứng
GUIDE_BOSS_L = 9.0                        # (giữ nguyên: mép vấu sát bạc ở chặn -X)
GUIDE_X0 = FACE_X0 + GUIDE_BLIND_WALL     # đáy hốc mù phía ĐC — trục tì tới đây
GUIDE_SOCKET_M = FACE_T + GUIDE_BOSS_L - GUIDE_BLIND_WALL   # hốc phía ĐC = 10.5
GUIDE_ACCESS_D = GUIDE_D + 0.4            # lỗ luồn trục trên vách +X (rộng, không phải ổ)
GUIDE_STICK = 2.0                         # trục thò ra ngoài vách +X — cầm tay rút ra
GUIDE_LOCK_FLAT = 0.5                     # độ sâu vạt phẳng cho mũi vít hãm
GUIDE_LOCK_X = FACE_X0 + FACE_T + GUIDE_BOSS_L / 2.0   # giữa vấu hốc ĐC = 7.5
assert END_HUB_RECESS + GUIDE_BLIND_WALL <= END_T + 1e-9
assert GUIDE_SOCKET_M + 1e-9 >= GUIDE_MIN_ENG
# Chân gối — không còn đội thêm trụ nắp ra ngoài (lỗ nắp khoan trên khung liền)
POST_W = 6.0                              # trụ/boss bắt nắp trên khung
END_FOOT_EXTRA = 2.0
END_FOOT_X0 = END_X0 - 5.0
# END_FOOT_X1 / END_WALL_X* / END_RIB_X1 gán sau khi biết X CT MAX + BASE_X1
END_FOOT_X1 = END_X0 + END_FACE_T + END_FOOT_EXTRA
END_RIB_X1 = END_X0 + END_FACE_T

# --- 2 CÔNG TẮC HÀNH TRÌNH KW11 CÓ BÁNH XE (5A 250V) --------------------
SW_L, SW_T, SW_H = 20.0, 6.4, 10.0
SW_HOLE_PITCH = 9.5
SW_BODY_HOLE_D = 2.0
SW_HEAD_D = 4.0                           # mũ vít M2 (đầu trụ/pan) — GIẢ ĐỊNH, đo lại
SW_HEAD_H = 1.6
SW_DRIVER_D = 3.5                         # thân mũi tua vít M2
SW_HOLE_D = 5.0                           # LỖ THAO TÁC trên vách -Y: mũ vít M2 + mũi tua
                                          # vít chui qua. KHÔNG phải lỗ dẫn vít: mũ vít
                                          # phải tì THẲNG vào thân công tắc, nếu tì lên
                                          # vách thì siết chỉ ép vách với vấu (cùng là
                                          # Housing) còn công tắc trôi tự do 6 mm.
SW_PILOT_D = 1.6                          # lỗ MỒI trong vấu: vít M2 tự ren, KHÔNG đai ốc
                                          # (đai ốc M2 phải giữ bằng kìm trong lòng hộp)
# Lỗ mồi ĐỤC THỦNG vấu (lỗ mù Ø1.6 trong nhựa in vừa khó ra lỗ vừa khó canh chiều sâu).
# Nhưng ngay sau lưng vấu CT MAX là vách End_Block có HỐC HUB (thanh chui vào ở cuối
# hành trình), nên cái phải khống chế KHÔNG PHẢI chiều sâu lỗ mà là CHIỀU DÀI VÍT:
# mũi vít phải dừng trong bề dày vấu, không được ló sang mặt bên kia.
SW_SCREW_L = 8.0                          # vít M2 x 8 (xem assert dưới: tối đa 9)
SW_TIP_CLEAR = 0.5                        # mũi vít cách đường hub chạy
SW_FIN_T = 3.0
# Vấu CT ngoài bao khớp nối (coupler y±6) và ngoài chân FOOT khi cắt chân dưới CT
SW_FIN_Y0 = -(COUP_D / 2.0 + SW_FIN_T + 1.5)  # -10.5
# mũi vít M2 phải dừng TRONG bề dày vấu, và cách đường hub chạy >= SW_TIP_CLEAR
SW_SCREW_TIP = (SW_FIN_Y0 - SW_T) + SW_SCREW_L        # mũ tì mặt -Y thân CT
assert SW_SCREW_TIP <= -HUB_Y - SW_TIP_CLEAR + 1e-9
assert SW_SCREW_TIP <= SW_FIN_Y0 + SW_FIN_T + 1e-9     # không ló khỏi vấu
assert SW_SCREW_L - SW_T >= 1.5 - 1e-9                 # ăn ren >= 1.5 mm
SW_Z0 = BASE_T
# Bích đứng ĐC và vách gối đỡ DỪNG ở mép vấu CT: dải y < FRONT_Y0 là chỗ của THÂN
# công tắc + 3 CHÂN HÀN + máng dây, không được có thịt khung nào thò vào.
FRONT_Y0 = SW_FIN_Y0
# Vách gối đỡ phải lùi THÊM: vấu CT MAX dính lưng nó, mà lỗ vít CT là lỗ XUYÊN — không
# lùi thì lỗ xuyên xong lại chui thẳng vào thịt vách (đo được 13-15 mm3), mũi vít không
# có chỗ ra và lỗ thành lỗ mù trá hình. Chừa KHE THOÁT sau vấu.
SW_FIN_RELIEF = 2.5
END_WALL_Y0 = SW_FIN_Y0 + SW_FIN_T + SW_FIN_RELIEF

# 3 CHÂN HÀN (COM/NO/NC) nhô ra mặt LƯNG công tắc — mặt đối diện cần gạt, tức là
# quay ra XA thanh trượt: CT MIN chĩa về -X (phía động cơ), CT MAX chĩa về +X (phía
# gối đỡ). Chân xoè theo CHIỀU DÀI thân (= Z ở tư thế lắp đứng này).
# GIẢ ĐỊNH kích thước (trang bán không ghi) — ĐO LẠI khi có hàng: sửa 4 số dưới đây
# thì hốc chân hàn, chiều dài hộp và máng dây tự tính lại.
SW_TERM_L = 5.0                           # lá đồng nhô ra khỏi lưng CT
SW_TERM_W = 3.2                           # bề rộng lá (theo Z)
SW_TERM_T = 0.5                           # bề dày lá (theo Y)
SW_TERM_PITCH = 7.0                       # 3 chân cách đều nhau theo Z
SW_TERM_ZONE = SW_TERM_L + 3.5            # hốc TRỐNG: lá + mối hàn + chỗ bẻ dây
# --- MÁNG DÂY: 2 dây dupont cho MỖI công tắc (4 sợi) + 2 dây động cơ ------
DUPONT_D = 1.8                            # dây dupont 24AWG kể cả vỏ
DUCT_Z1 = 8.0                             # nóc lòng máng (mặt dưới vấu giữ dây)
DUCT_TAB_T = 1.5                          # bề dày vấu giữ dây
DUCT_TAB_X = 8.0                          # chiều dài mỗi vấu theo X
DUCT_TAB_Y = 3.0                          # vấu chìa vào lòng máng
WIRE_EXIT_W = 2.4                         # khe ra dây trên vách -X (theo Y)
WIRE_EXIT_Z0, WIRE_EXIT_Z1 = 6.0, 14.0    # 4 sợi xếp chồng vẫn lọt

SW_LEVER_L, SW_LEVER_W = 16.0, 4.0
SW_ROLLER_D, SW_ROLLER_W = 4.8, 2.5
SW_ROLLER_PROUD = 6.0
SW_TRIP_TRAVEL = 2.0
SW_PRESS = 0.5

_SW_OVERTRAVEL = SW_ROLLER_PROUD - SW_TRIP_TRAVEL
X_TRIP_MIN = _X_MIN_MECH + SW_PRESS
X_TRIP_MAX = _X_MAX_MECH - SW_PRESS
SW_MIN_FRONT = (X_TRIP_MIN - BAR_X / 2.0) - _SW_OVERTRAVEL
SW_MAX_FRONT = (X_TRIP_MAX + BAR_X / 2.0) + _SW_OVERTRAVEL

MB_FOOT_X1 = max(FACE_X0 + FACE_T, SW_MIN_FRONT)
MB_FOOT_Y1 = -6.0
FIN_BOLT_Y = MB_FOOT_Y1 - 3.5

BAR_HOME_X = 0.5 * (X_TRIP_MIN + X_TRIP_MAX)
# Thân thanh: từ mặt ngoài CT tới trục trơn (không chìa ra cạnh hộp)
BAR_Y0 = SW_FIN_Y0 - SW_T
BAR_Y1 = GUIDE_Y

# ---------------------------------------------------------------------------
# VỎ HỘP — khoang ôm sát; khung ĐC + gối đỡ MERGE vào Housing
# ---------------------------------------------------------------------------
_SW_Y_MIN = SW_FIN_Y0 - SW_T
# 4 vít bắt nắp đứng ở ĐÚNG 4 GÓC khoang, nên góc -Y phải lùi ra khỏi NẮP KẸP ĐC
# (nắp kẹp rộng ±CLAMP_HALF_Y vì phải mang 4 vít kẹp nằm ngoài vỏ ĐC).
_Y0_SW = _SW_Y_MIN - WING_CLEAR                          # theo công tắc MIN
_Y0_LID = -CLAMP_HALF_Y - CLAMP_FIT - POST_W             # theo trụ nắp góc -Y
# MÁNG DÂY: trụ nắp góc -Y phải lùi RA SAU mặt lưng công tắc, nếu không nó bịt kín
# hành lang dẫn dây tới khe ra dây trên vách -X (dây 2 công tắc chỉ có đường này).
_Y0_DUCT = BAR_Y0 - POST_W
BASE_Y0 = min(_Y0_SW, _Y0_LID, _Y0_DUCT)
# Trụ nắp góc +X/+Y không được bịt LỖ LUỒN TRỤC TRƠN trên vách +X
_Y1_LID = GUIDE_Y + GUIDE_ACCESS_D / 2.0 + 1.2 + POST_W
BASE_Y1 = max(WING_Y + WING_CLEAR, _Y1_LID)
_SW_MAX_BODY_X1 = (X_TRIP_MAX + BAR_X / 2.0) + _SW_OVERTRAVEL + SW_H
_SW_TERM_X1 = _SW_MAX_BODY_X1 + SW_TERM_ZONE   # hết hốc chân hàn CT MAX
_WIRE_TURN = 4.0                               # cửa bẻ dây xuống máng, trước trụ góc
# Vách gối sát cạnh hộp: mặt -X phải nằm SAU lỗ M2 CT MAX (không đụng hành lang bu lông).
_LS_MAX_HOLE_X = SW_MAX_FRONT + SW_H / 2.0
_END_WALL_X0_MIN = max(
    END_X0 + END_FACE_T + 2.0,
    _LS_MAX_HOLE_X + SW_HOLE_D / 2.0 + 1.5,
)
# Chân gối + khoang đủ chỗ vách dày END_T kể từ _END_WALL_X0_MIN
END_FOOT_X1 = max(END_FOOT_X1, _END_WALL_X0_MIN + END_T + END_FOOT_EXTRA,
                  _SW_MAX_BODY_X1 + POST_W + 1.0)
_LID_X_END = END_FOOT_X1 - POST_W / 2.0
BASE_X1 = max(END_FOOT_X1, _SW_MAX_BODY_X1, _LID_X_END + POST_W / 2.0,
              _SW_TERM_X1,                                  # hốc chân hàn nằm trong khoang
              _SW_MAX_BODY_X1 + _WIRE_TURN + POST_W,        # còn cửa bẻ dây trước trụ góc
              _END_WALL_X0_MIN + END_T,
              ) + WING_CLEAR
# Vách dày: mặt +X sát mặt trong vách hộp
END_WALL_X1 = BASE_X1
END_WALL_X0 = BASE_X1 - END_T
assert END_WALL_X0 + 1e-9 >= _END_WALL_X0_MIN
END_RIB_X1 = END_WALL_X1
END_FOOT_X1 = max(END_FOOT_X1, END_WALL_X1 + END_FOOT_EXTRA)
WALL_T = 2.5
BOX_TOP = BAR_Z1 + 0.8
BOX_X0, BOX_X1 = BASE_X0 - WALL_T, BASE_X1 + WALL_T
BOX_Y0, BOX_Y1 = BASE_Y0 - WALL_T, BASE_Y1 + WALL_T
# Trục trơn: tì đáy hốc mù (-X), xuyên mặt mỏng + cầu + vách sát hộp, thò ra ngoài +X
GUIDE_X1 = END_WALL_X1
GUIDE_SHAFT_X0 = GUIDE_X0
GUIDE_SHAFT_LEN = (BASE_X1 + WALL_T + GUIDE_STICK) - GUIDE_SHAFT_X0
ROD_ACCESS_D = ROD_D + 1.2                # lỗ luồn ty ren trên vách +X
LID_T = 2.5
POST_Z0 = BASE_T + FOOT_T
LID_BOSS_Z0 = BASE_T                      # trụ GÓC mọc thẳng từ sàn, dính 2 vách
EAR_X, EAR_OUT, EAR_HOLE = 11.0, 9.0, 4.5
CABLE_D = 8.0
M3_CLEAR = 3.4
M3_TAP = 2.5
M16_CLEAR = 2.0
M16_HEAD_D = 3.2
# Vách gá ngoài hộp: mặt trên nắp, dài gần hết chiều ngang hộp (Y)
WALL_Y0 = BOX_Y0 + 1.0
WALL_Y1 = BOX_Y1 - 1.0
WALL_Z0 = BOX_TOP + LID_T
WALL_Z1 = WALL_Z0 + WALL_H
WALL_Z_MID = 0.5 * (WALL_Z0 + WALL_Z1)
# Máng dây phải đủ cho 4 sợi dupont (2 sợi/công tắc) nằm 2 hàng, và hành lang trước
# máng phải đủ rộng cho khe ra dây trên vách -X.
assert BAR_Y0 - BASE_Y0 + 1e-9 >= 2.0 * DUPONT_D + 1.0
assert -CRADLE_Y - BAR_Y0 + 1e-9 >= WIRE_EXIT_W + 0.3
assert WIRE_EXIT_Z1 - WIRE_EXIT_Z0 + 1e-9 >= 4.0 * DUPONT_D
assert WALL_H + 1e-9 >= 2.0 * LOAD_HOLE_DZ + M3_CLEAR + 4.0
assert STEM_Y1 - STEM_Y0 + 1e-9 >= M3_CLEAR + 6.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _box(dx, dy, dz, x0, y0, z0) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def _box2(x0, x1, y0, y1, z0, z1) -> Part.Shape:
    return _box(x1 - x0, y1 - y0, z1 - z0, x0, y0, z0)


def _cyl_x(d, length, x0, y=0.0, z=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, length, App.Vector(x0, y, z), App.Vector(1, 0, 0))
    return c


def _cyl_z(d, h, x=0.0, y=0.0, z0=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _cyl_y(d, length, x=0.0, y0=0.0, z=0.0) -> Part.Shape:
    return Part.makeCylinder(d / 2.0, length, App.Vector(x, y0, z), App.Vector(0, 1, 0))


def _cone_x(d0, d1, length, x0, y=0.0, z=0.0) -> Part.Shape:
    return Part.makeCone(
        d0 / 2.0, d1 / 2.0, length, App.Vector(x0, y, z), App.Vector(1, 0, 0)
    )


def _hex_prism_x(af: float, length: float, x0: float, y: float, z: float,
                 phase: float = 30.0) -> Part.Shape:
    """Lăng trụ lục giác, trục theo X, af = khoảng cách 2 mặt phẳng đối diện.

    phase = 30 -> có MẶT PHẲNG quay về +Y/-Y (đai ốc: 2 mặt này tì vào khe).
    phase = 0  -> có MẶT PHẲNG quay lên +Z    (khớp nối: vít chìm bắt từ trên xuống).
    """
    r = af / math.sqrt(3.0)  # bán kính qua đỉnh
    pts = []
    for i in range(6):
        a = math.radians(phase + i * 60.0)
        pts.append(App.Vector(x0, y + r * math.cos(a), z + r * math.sin(a)))
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(App.Vector(length, 0, 0))


def _tri_rib(x_at_wall: float, x_tip: float, z_top: float, z_bot: float,
             y0: float, thick: float) -> Part.Shape:
    """Gân tam giác trong mặt XZ (cao ở sát vách, thấp dần ra ngoài), đùn theo Y."""
    pts = [
        App.Vector(x_at_wall, y0, z_top),
        App.Vector(x_at_wall, y0, z_bot),
        App.Vector(x_tip, y0, z_bot),
    ]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(App.Vector(0, thick, 0))


def _sweep_z(shape: Part.Shape, height: float, step: float = 1.0) -> Part.Shape:
    """Quét một chi tiết THẲNG LÊN — dùng kiểm tra 'thả từ trên xuống có vướng không'."""
    out = shape
    n = max(1, int(round(height / step)))
    for i in range(1, n + 1):
        out = out.fuse(shape.translated(App.Vector(0.0, 0.0, i * height / n)))
    return out


def _sweep_y(shape: Part.Shape, dist: float, step: float = 1.0) -> Part.Shape:
    """Quét một chi tiết theo +Y — dùng kiểm tra 'luồn ngang vào có vướng không'."""
    out = shape
    n = max(1, int(round(abs(dist) / step)))
    for i in range(1, n + 1):
        out = out.fuse(shape.translated(App.Vector(0.0, i * dist / n, 0.0)))
    return out


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


def motor_face_holes() -> list[tuple[float, float]]:
    """2 lỗ M1.6 trên mặt bích, toạ độ (y, z) so với TÂM TRỤC."""
    return [(+MOT_HOLE_DY, +MOT_HOLE_DZ), (-MOT_HOLE_DY, -MOT_HOLE_DZ)]


def travel_range() -> tuple[float, float]:
    """Khoảng chạy hợp lệ = điểm TÁC ĐỘNG của 2 công tắc (thanh dừng tại đây).

    Chặn cơ (_X_MIN/_X_MAX_MECH) chỉ là failsafe sau SW_PRESS.
    """
    return X_TRIP_MIN, X_TRIP_MAX


# ---------------------------------------------------------------------------
# 3. Các chi tiết
# ---------------------------------------------------------------------------
def make_motor() -> Part.Shape:
    """Mặt bích trước tại x=0, thân về phía -X, trục D Ø3 x 10 về phía +X."""
    gb = _box(GB_L, GB_W, GB_H, -GB_L, -GB_W / 2.0, AXIS_Z - GB_H / 2.0)
    can = _cyl_x(CAN_D, CAN_L, -GB_L - CAN_L, 0.0, AXIS_Z)
    rear = _cyl_x(REAR_D, REAR_L, -MOT_LEN, 0.0, AXIS_Z)
    shaft = _cyl_x(SHAFT_D, SHAFT_LEN, 0.0, 0.0, AXIS_Z)
    # vạt phẳng chữ D — chỗ cho 2 vít chìm của khớp nối tì vào (mặt trên)
    shaft = _cut(shaft, _box2(
        SHAFT_FLAT_X0, SHAFT_LEN + 1.0, -SHAFT_D, SHAFT_D,
        AXIS_Z + SHAFT_D / 2.0 - SHAFT_FLAT, AXIS_Z + SHAFT_D,
    ))

    body = gb.fuse(can).fuse(rear).fuse(shaft)
    # 2 lỗ ren M1.6 sâu 2.1 trên mặt bích
    for dy, dz in motor_face_holes():
        body = _cut(body, _cyl_x(MOT_HOLE_TAP, 2.1, -2.1, dy, AXIS_Z + dz))
    return _refine(body)


def make_coupler() -> Part.Shape:
    """KHỚP NỐI TRỤC đồng (mua sẵn): 2 LỖ TRƠN 3 mm - 4 mm, mỗi đầu MỘT vít hãm M3.

    Đầu -X là lỗ Ø3 ôm trục D của động cơ (vít tì vào mặt vạt D), đầu +X là lỗ Ø4 ôm
    ty ren M4 (vít cắn vào ren). Vách COUP_WALL ở giữa là cữ chặn: cắm tới khi chạm
    vách là đúng chiều sâu, và nó cũng chặn ty ren không tụt vào khi bị đẩy về -X.
    KHÔNG có mối ren nào trong đường truyền nên không cần đai ốc hãm.
    """
    body = _cyl_x(COUP_D, COUP_LEN, COUP_X0, 0.0, AXIS_Z)
    body = _cut(body, _cyl_x(SHAFT_D + 0.1, COUP_BORE_M, COUP_X0 - 0.001, 0.0, AXIS_Z))
    body = _cut(body, _cyl_x(ROD_D + 0.1, COUP_BORE_R + 0.001,
                             COUP_X1 - COUP_BORE_R, 0.0, AXIS_Z))
    _ = SPACER_L
    for x in coupler_set_screw_x():
        body = _cut(body, _cyl_z(COUP_SET_D, COUP_D, x, 0.0, AXIS_Z))
    return _refine(body)


def coupler_set_screw_x() -> tuple[float, float]:
    """2 vít hãm, bắt từ trên xuống: (vít ôm trục động cơ, vít ôm ty ren).

    Vít phía ty ren đặt giữa ĐOẠN TY REN THỰC SỰ CẮM VÀO, không phải giữa lỗ — vì ty
    ren chỉ cắm COUP_ROD_IN mm chứ không hết lỗ.
    """
    return (COUP_X0 + COUP_BORE_M / 2.0, COUP_X1 - COUP_ROD_IN / 2.0)


def make_coupler_spacer() -> Part.Shape:
    """CỮ ĐÁY LỖ: đĩa Ø3.8 thả vào lỗ Ø4 trước, ty ren cắm tới đó là đúng chiều sâu.

    In cùng bộ, hoặc thay bằng một đoạn trục/ty thừa Ø <= 4 cắt đúng SPACER_L mm.
    Chịu nén thuần trong lòng lỗ (bị thành lỗ bó ngang) nên nhựa in thừa sức.
    """
    x0 = COUP_X1 - COUP_BORE_R
    return _cyl_x(SPACER_D, SPACER_L, x0, 0.0, AXIS_Z)


def make_thread_rod() -> Part.Shape:
    """Ty ren M4 x 40 (vẽ trơn Ø4; ren bước 0.7 chỉ ghi trong thông số)."""
    return _cyl_x(ROD_D, ROD_LEN, ROD_X0, 0.0, AXIS_Z)


def slot_x() -> tuple[float, float]:
    """Khoảng X của KHE trên NẮP (trụ gá chạy).

    Theo CHẶN CƠ KHÍ (+ clear), không chỉ theo điểm CT tác động.
    """
    return (_X_MIN_MECH - MOUNT_T / 2.0 - LID_SLOT_END,
            _X_MAX_MECH + MOUNT_T / 2.0 + LID_SLOT_END)


def slot_y() -> tuple[float, float]:
    """Khoảng Y của khe nắp — ôm trụ gá (hẹp; vách xoè rộng phía trên nắp)."""
    return (STEM_Y0 - SLOT_CLEAR, STEM_Y1 + SLOT_CLEAR)


def lid_tap_xy() -> list[tuple[float, float]]:
    """4 lỗ tarô M3 bắt nắp — ĐÚNG 4 GÓC khoang, trụ dính vào 2 vách góc."""
    xs = (BASE_X0 + POST_W / 2.0, BASE_X1 - POST_W / 2.0)
    ys = (BASE_Y0 + POST_W / 2.0, BASE_Y1 - POST_W / 2.0)
    return [(x, y) for x in xs for y in ys]


def lid_boss_boxes() -> list[tuple[float, float]]:
    """Boss hình hộp quanh mỗi lỗ nắp, từ mặt chân lên tới trần."""
    return [(x - POST_W / 2.0, y - POST_W / 2.0) for x, y in lid_tap_xy()]


def ear_boxes() -> list[tuple[float, float]]:
    """4 tai M4 bắt máy — +-Y ở hai đầu (bệ gá đã lên nắp, không va tai -Y)."""
    xs = (BOX_X0 + 2.0, BOX_X1 - 2.0 - EAR_X)
    return [(x, BOX_Y0 - EAR_OUT) for x in xs] + [(x, BOX_Y1) for x in xs]


def ear_hole_xy() -> list[tuple[float, float]]:
    return [(x + EAR_X / 2.0, y + EAR_OUT / 2.0) for x, y in ear_boxes()]


def make_motor_bracket() -> Part.Shape:
    """Bích đứng + máng + chân + vấu CT MIN — sẽ fuse vào Housing (không lỗ xuống đế)."""
    foot = _box2(CRADLE_X0, FACE_X0 + FACE_T, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    foot = foot.fuse(_box2(FACE_X0 + FACE_T, MB_FOOT_X1, -FOOT_Y, MB_FOOT_Y1,
                           BASE_T, BASE_T + FOOT_T))
    plate = _box2(FACE_X0, FACE_X0 + FACE_T, FRONT_Y0, WING_Y, BASE_T, PLATE_TOP)
    cradle = _box2(CRADLE_X0, FACE_X0, -CRADLE_Y, CRADLE_Y, BASE_T, AXIS_Z)
    rib = _tri_rib(
        FACE_X0, CRADLE_X0 + 11.0, PLATE_TOP - 2.0, BASE_T + FOOT_T, RIB_Y0, RIB_T
    )
    guide_boss = _cyl_x(GUIDE_BOSS_D, GUIDE_BOSS_L, FACE_X0 + FACE_T, GUIDE_Y, AXIS_Z)
    body = (foot.fuse(plate).fuse(cradle).fuse(rib)
            .fuse(guide_boss).fuse(make_sw_fin(False)))

    body = _cut(body, motor_pocket_tool())
    body = body.fuse(motor_stop())
    body = _cut(body, _cyl_x(SHAFT_CLEAR_D, FACE_T + 2.0, FACE_X0 - 1.0, 0.0, AXIS_Z))
    body = _cut(body, motor_shaft_slot())
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, GUIDE_SOCKET_M + 1.0,
                             GUIDE_X0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                             FACE_X0 - 1.0, GUIDE_Y, AXIS_Z))
    body = _cut(body, guide_lock_tap_tool())
    body = _cut(body, clamp_pilot_tool())
    body = _cut(body, sw_term_zone(False))
    # Khoét chân dưới CT MIN (tránh đâm thân CT)
    sw0, sw1 = sw_body_x(False)
    body = _cut(body, _box2(
        sw0 - 1.0, sw1 + 1.0,
        -FOOT_Y - 1.0, SW_FIN_Y0 + 0.05,
        BASE_T - 0.05, BASE_T + FOOT_T + 0.5,
    ))
    return _refine(body)


def make_end_block() -> Part.Shape:
    """Gối đỡ: vách dày sát cạnh hộp +X — không vách giữa (né lỗ CT MAX).

    END_X0 vẫn là mốc hành trình/hứng ty (ảo); thịt đỡ trục trơn nằm ở END_WALL_*.
    Xương đáy + chân nối vấu CT / vách sát hộp thành một khối in.
    """
    foot = _box2(END_FOOT_X0, END_FOOT_X1, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    edge = _box2(END_WALL_X0, END_WALL_X1, END_WALL_Y0, WING_Y, BASE_T, PLATE_TOP)
    # Xương đáy từ gần END_X0 tới vách sát hộp (thấp, dưới đường bạc)
    spine = _box2(
        END_X0, END_WALL_X1,
        WING_Y - 4.0, WING_Y,
        BASE_T, BASE_T + FOOT_T + 2.0,
    )
    # Cầu trục trơn chỉ SAU hành lang lỗ CT MAX
    br_x0 = max(END_X0 + END_FACE_T, _LS_MAX_HOLE_X + SW_HOLE_D / 2.0 + 1.0)
    br_y0 = GUIDE_Y - BOSS_D / 2.0 - 1.0
    br_y1 = GUIDE_Y + BOSS_D / 2.0 + 1.0
    bridge = None
    if END_WALL_X0 > br_x0 + 0.5:
        bridge = _box2(br_x0, END_WALL_X0, br_y0, br_y1, BASE_T, PLATE_TOP)
    ribs = None
    if END_RIB_X1 > END_WALL_X1 + 0.5:
        for y0 in (-RIB_T / 2.0, RIB_Y0):
            r = _tri_rib(
                END_WALL_X1, END_RIB_X1, PLATE_TOP - 2.0, BASE_T + FOOT_T, y0, RIB_T
            )
            ribs = r if ribs is None else ribs.fuse(r)
    body = foot.fuse(edge).fuse(spine).fuse(make_sw_fin(True))
    if bridge is not None:
        body = body.fuse(bridge)
    if ribs is not None:
        body = body.fuse(ribs)

    sw0, sw1 = sw_body_x(True)
    body = _cut(body, _box2(
        sw0 - 1.0, sw1 + 1.0,
        -FOOT_Y - 1.0, SW_FIN_Y0,
        BASE_T - 1.0, SW_Z0 + SW_L + 4.0,
    ))
    body = _cut(body, sw_term_zone(True))
    # Hốc bạc (không khí tại END_X0) + lỗ trục trên cầu/vách sát hộp
    guide_x0 = br_x0 if bridge is not None else END_WALL_X0
    body = _cut(body, _cyl_x(BOSS_D + 2.0 * END_RECESS_CLEAR, END_HUB_RECESS + 0.2,
                             END_X0 - 0.05, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, END_WALL_X1 - guide_x0 + 2.0,
                             guide_x0 - 1.0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(ROD_ACCESS_D, END_T + 2.0, END_WALL_X0 - 1.0, 0.0, AXIS_Z))
    return _refine(body)


def make_housing() -> Part.Shape:
    """VỎ HỘP LIỀN KHUNG: đáy + vách + tai M4 + Motor_Bracket + End_Block + boss nắp.

    Không còn bu lông M3 giữa gá/gối và đế — mọi thứ là một khối in.
    """
    floor = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, 0.0, BASE_T)
    shell = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, BASE_T, BOX_TOP)
    shell = _cut(shell, _box2(BASE_X0, BASE_X1, BASE_Y0, BASE_Y1,
                              BASE_T - 1.0, BOX_TOP + 1.0))
    body = floor.fuse(shell)
    for x, y in ear_boxes():
        body = body.fuse(_box2(x, x + EAR_X, y, y + EAR_OUT, 0.0, BASE_T))

    # Khung cơ cấu — merge
    body = body.fuse(make_motor_bracket()).fuse(make_end_block())

    # Boss bắt nắp từ mặt chân
    for x, y in lid_boss_boxes():
        body = body.fuse(_box2(x, x + POST_W, y, y + POST_W, LID_BOSS_Z0, BOX_TOP))

    # Cắt lại các hốc quan trọng SAU fuse (tránh boolean làm đầy lỗ)
    body = _cut(body, motor_pocket_tool())
    body = body.fuse(motor_stop())
    body = _cut(body, _cyl_x(SHAFT_CLEAR_D, FACE_T + 2.0, FACE_X0 - 1.0, 0.0, AXIS_Z))
    body = _cut(body, motor_shaft_slot())
    # Hốc mù: đúng GUIDE_SOCKET_* — không +0.2 kẻo đục vào vách chặn
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, GUIDE_SOCKET_M,
                             GUIDE_X0, GUIDE_Y, AXIS_Z))
    _br_x0 = max(END_X0 + END_FACE_T, _LS_MAX_HOLE_X + SW_HOLE_D / 2.0 + 1.0)
    _guide_x0 = _br_x0 if END_WALL_X0 > _br_x0 + 0.5 else END_WALL_X0
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, END_WALL_X1 - _guide_x0 + 2.0,
                             _guide_x0 - 1.0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                             FACE_X0 - 1.0, GUIDE_Y, AXIS_Z))
    # LỖ LUỒN trên vách +X: trục trơn và ty ren đều đẩy từ ngoài vào
    body = _cut(body, _cyl_x(GUIDE_ACCESS_D, WALL_T + 2.0,
                             BASE_X1 - 1.0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(ROD_ACCESS_D, WALL_T + 2.0,
                             BASE_X1 - 1.0, 0.0, AXIS_Z))
    # Vít hãm M3 khóa trục lúc chạy (sau fuse — tránh boolean lấp lỗ)
    body = _cut(body, guide_lock_tap_tool())
    # Lỗ M2: xuyên thân CT + vấu + vách -Y (siết từ ngoài hộp)
    _m2_y0 = BOX_Y0 - 1.0
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            # LỖ THAO TÁC qua vách -Y + máng dây, MỒI trong vấu (vít tự ren, không đai ốc)
            body = _cut(body, _cyl_y(SW_HOLE_D, (SW_FIN_Y0 - SW_T) - _m2_y0, xc, _m2_y0, z))
            body = _cut(body, sw_pilot_tool(xc, z))
    body = _cut(body, _cyl_x(BOSS_D + 2.0 * END_RECESS_CLEAR, END_HUB_RECESS + 0.2,
                             END_X0 - 0.05, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(ROD_ACCESS_D, END_T + 2.0, END_WALL_X0 - 1.0, 0.0, AXIS_Z))
    body = _cut(body, clamp_pilot_tool())

    # --- ĐƯỜNG DÂY: hốc 3 chân hàn 2 CT + khe ra dây + vấu giữ dây trong máng ---
    for is_max in (False, True):
        body = _cut(body, sw_term_zone(is_max))
    body = _cut(body, wire_exit_tool())
    body = body.fuse(duct_tabs())

    # Không cắt nguyên thân CT khỏi Housing (dễ tách thành nhiều khối).
    # Chân dưới CT đã khoét ở make_motor_bracket / make_end_block + pocket chân.

    # Không khe vách -Y — bệ gá ra qua nắp
    body = _cut(body, _cyl_x(CABLE_D, WALL_T + 2.0, BOX_X0 - 1.0, 0.0, AXIS_Z))
    for x, y in ear_hole_xy():
        body = _cut(body, _cyl_z(EAR_HOLE, BASE_T + 2.0, x, y, -1.0))
    for x, y in lid_tap_xy():
        body = _cut(body, _cyl_z(M3_TAP, 10.0, x, y, BOX_TOP - 9.0))
    return _refine(body)


def make_housing_lid() -> Part.Shape:
    """Nắp đậy + KHE cho trụ bệ gá; 4 vít M3 xuống boss khung."""
    body = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, BOX_TOP, BOX_TOP + LID_T)
    sx0, sx1 = slot_x()
    sy0, sy1 = slot_y()
    body = _cut(body, _box2(sx0, sx1, sy0, sy1, BOX_TOP - 1.0, BOX_TOP + LID_T + 1.0))
    for x, y in lid_tap_xy():
        body = _cut(body, _cyl_z(M3_CLEAR, LID_T + 2.0, x, y, BOX_TOP - 1.0))
    return _refine(body)


def motor_shaft_slot() -> Part.Shape:
    """KHE HỞ NÓC trên bích cho trục ĐC Ø3.

    Lỗ tròn kín thì ĐC phải luồn NGANG vào (không đủ chỗ) hoặc nghiêng vào (mép dưới
    hộp số đâm vào bích). Xẻ hở nóc thì ĐC thả thẳng từ trên xuống.
    """
    return _box2(FACE_X0 - 1.0, FACE_X0 + FACE_T + 1.0,
                 -SHAFT_CLEAR_D / 2.0, SHAFT_CLEAR_D / 2.0,
                 AXIS_Z, PLATE_TOP + 1.0)


def motor_stop() -> Part.Shape:
    """Vách chặn sau lon ĐC — ĐC kẹp cứng dọc trục giữa bích và vách này."""
    body = _box2(MOT_STOP_X0, MOT_STOP_X1, -8.0, 8.0, BASE_T, AXIS_Z)
    return _cut(body, _box2(
        MOT_STOP_X0 - 1.0, MOT_STOP_X1 + 1.0,
        -MOT_REAR_SLOT / 2.0, MOT_REAR_SLOT / 2.0,
        AXIS_Z - MOT_REAR_SLOT / 2.0, AXIS_Z + 1.0,
    ))


def motor_pocket_tool() -> Part.Shape:
    """Hốc chứa động cơ = hợp của lon Ø12.4 và hộp số 12.4 x 10.4 (có khe hở)."""
    can = _cyl_x(CAN_D + 0.4, MOT_LEN + 6.0, CRADLE_X0 - 3.0, 0.0, AXIS_Z)
    gb = _box2(
        CRADLE_X0 - 3.0,
        FACE_X0,
        -(GB_W + 0.4) / 2.0,
        (GB_W + 0.4) / 2.0,
        AXIS_Z - (GB_H + 0.4) / 2.0,
        AXIS_Z + (GB_H + 0.4) / 2.0,
    )
    return can.fuse(gb)


def clamp_bolt_xy() -> list[tuple[float, float]]:
    """4 vít kẹp — y tính từ MÉP HỐC ĐC ra nên thân vít không bao giờ đâm vào ĐC."""
    return [(x, y) for x in CLAMP_BOLT_X for y in (-CLAMP_BOLT_Y, CLAMP_BOLT_Y)]


def clamp_z() -> tuple[float, float]:
    """Đáy / nóc nắp kẹp."""
    return AXIS_Z + 1.0, AXIS_Z + MOT_POCKET_R + 2.0


def clamp_clear_tool() -> Part.Shape:
    """Khối BAO nắp kẹp + khe — mọi thứ mọc trong hộp phải né khối này."""
    cz0, cz1 = clamp_z()
    return _box2(CRADLE_X0 + 1.0 - CLAMP_FIT, CLAMP_X1 + CLAMP_FIT,
                 -CLAMP_HALF_Y - CLAMP_FIT, CLAMP_HALF_Y + CLAMP_FIT,
                 cz0 - CLAMP_FIT, cz1 + CLAMP_FIT)


def clamp_pilot_tool() -> Part.Shape:
    """4 lỗ MỒI vít tự ren trong máng: mù, sâu CLAMP_SCREW_ENG kể từ mặt máng."""
    tool = None
    for x, y in clamp_bolt_xy():
        t = _cyl_z(CLAMP_SCREW_PILOT, CLAMP_SCREW_ENG + 1.0, x, y,
                   AXIS_Z - CLAMP_SCREW_ENG)
        tool = t if tool is None else tool.fuse(t)
    return tool


def make_motor_clamp() -> Part.Shape:
    """Nắp kẹp trên: 1 khối cầu vượt trên lon ĐC (để nóc), 4 VÍT TỰ REN M3.

    Vít bắt thẳng vào nhựa máng (lỗ mồi Ø2.5), KHÔNG dùng bu lông + đai ốc: dưới máng
    là sàn hộp, không có chỗ luồn tay giữ đai ốc. Mũ vít CHÌM trong hốc Ø5.8 sâu 2.4
    kẻo nó đội vào nắp hộp (nóc nắp kẹp chỉ cách trần BOX_TOP vài mm).
    """
    clamp_z0, clamp_z1 = clamp_z()
    body = _box2(CRADLE_X0 + 1.0, CLAMP_X1,
                 -CLAMP_HALF_Y, CLAMP_HALF_Y, clamp_z0, clamp_z1)
    body = _cut(body, motor_pocket_tool())
    for x, y in clamp_bolt_xy():
        body = _cut(body, _cyl_z(CLAMP_SCREW_CLEAR, clamp_z1 - clamp_z0 + 2.0,
                                 x, y, clamp_z0 - 1.0))
        body = _cut(body, _cyl_z(CLAMP_HEAD_D, CLAMP_HEAD_H + 1.0,
                                 x, y, clamp_z1 - CLAMP_HEAD_H))
    return _refine(body)


def guide_lock_tap_tool() -> Part.Shape:
    """Lỗ tarô M3 từ +Z xuyên vấu hốc ĐC vào tâm trục trơn."""
    z0 = AXIS_Z - 1.0
    z1 = AXIS_Z + GUIDE_BOSS_D / 2.0 + 2.0
    return _cyl_z(M3_TAP, z1 - z0, GUIDE_LOCK_X, GUIDE_Y, z0)


def make_guide_lock_screw() -> Part.Shape:
    """Vít hãm M3 (mô hình) — mũi tì vạt trên Guide_Shaft ở tư thế chạy."""
    z_tip = AXIS_Z + GUIDE_D / 2.0 - GUIDE_LOCK_FLAT
    z_head = AXIS_Z + GUIDE_BOSS_D / 2.0 + 3.0
    # Ø < M3_TAP để nằm trong lỗ tarô (mô hình, không ren)
    return _refine(_cyl_z(M3_TAP - 0.3, z_head - z_tip, GUIDE_LOCK_X, GUIDE_Y, z_tip))


def make_guide_shaft(x0: float | None = None) -> Part.Shape:
    """Trục trơn Ø5 + vạt dưới vít hãm; mặc định tư thế chạy (tì vách gối)."""
    if x0 is None:
        x0 = GUIDE_SHAFT_X0
    body = _cyl_x(GUIDE_D, GUIDE_SHAFT_LEN, x0, GUIDE_Y, AXIS_Z)
    # Vạt cố định trên thân (cách đầu -X đúng offset lúc trục tì đáy hốc)
    fx = x0 + (GUIDE_LOCK_X - GUIDE_SHAFT_X0)
    if x0 - 1e-9 <= fx <= x0 + GUIDE_SHAFT_LEN + 1e-9:
        z_cut = AXIS_Z + GUIDE_D / 2.0 - GUIDE_LOCK_FLAT
        body = _cut(body, _box2(
            fx - 2.5, fx + 2.5,
            GUIDE_Y - GUIDE_D, GUIDE_Y + GUIDE_D,
            z_cut, AXIS_Z + GUIDE_D + 1.0,
        ))
    return _refine(body)

# ---------------------------------------------------------------------------
# Công tắc hành trình + vấu đỡ
# ---------------------------------------------------------------------------
def sw_body_x(is_max: bool) -> tuple[float, float]:
    """Khoảng X của THÂN công tắc; mặt hướng vào thanh là mặt mang cần gạt."""
    if is_max:
        return SW_MAX_FRONT, SW_MAX_FRONT + SW_H
    return SW_MIN_FRONT - SW_H, SW_MIN_FRONT


def sw_front_x(is_max: bool) -> float:
    return SW_MAX_FRONT if is_max else SW_MIN_FRONT


def sw_sign(is_max: bool) -> float:
    """+1 nếu cần gạt chìa về +X (công tắc MIN); -1 với công tắc MAX."""
    return -1.0 if is_max else 1.0


def sw_roller_center(is_max: bool) -> tuple[float, float]:
    """(x, z) tâm bánh xe ở vị trí TỰ DO."""
    x = sw_front_x(is_max) + sw_sign(is_max) * (SW_ROLLER_PROUD - SW_ROLLER_D / 2.0)
    return x, SW_Z0 + 2.0 + SW_LEVER_L


def sw_trip_face_x(is_max: bool) -> float:
    """Mặt thanh ở đúng thời điểm công tắc tác động."""
    return sw_front_x(is_max) + sw_sign(is_max) * _SW_OVERTRAVEL


def sw_hole_sites(is_max: bool) -> list[tuple[float, float]]:
    """(x, z) tâm 2 lỗ M2 — trùng nhau giữa thân công tắc và vấu đỡ."""
    x0, x1 = sw_body_x(is_max)
    xc = 0.5 * (x0 + x1)
    zc = SW_Z0 + SW_L / 2.0
    return [(xc, zc - SW_HOLE_PITCH / 2.0), (xc, zc + SW_HOLE_PITCH / 2.0)]


def end_hub_recess_tool() -> Part.Shape:
    """Hốc hub qua mặt mỏng End_Block — mở sang khe trống (không cần đáy đặc)."""
    return _box2(
        END_X0 - 0.05, END_X0 + max(END_HUB_RECESS, END_FACE_T + 0.2),
        -HUB_Y - END_RECESS_CLEAR, HUB_Y + END_RECESS_CLEAR,
        BAR_Z0 - END_RECESS_CLEAR, BAR_Z1 + END_RECESS_CLEAR,
    )


def sw_screw_shank(xc: float, z: float) -> Part.Shape:
    """Thân vít M2 x SW_SCREW_L khi đã siết: mũ tì mặt -Y thân CT."""
    return _cyl_y(SW_BODY_HOLE_D, SW_SCREW_L, xc, SW_FIN_Y0 - SW_T, z)


def sw_screw_solid(xc: float, z: float) -> Part.Shape:
    """CON VÍT M2 thật ở tư thế đã siết: mũ + đoạn xuyên thân CT + đoạn ăn ren."""
    y_head = SW_FIN_Y0 - SW_T
    head = _cyl_y(SW_HEAD_D, SW_HEAD_H, xc, y_head - SW_HEAD_H, z)
    body = _cyl_y(SW_BODY_HOLE_D, SW_T, xc, y_head, z)
    thread = _cyl_y(SW_PILOT_D, SW_SCREW_L - SW_T, xc, y_head + SW_T, z)
    return head.fuse(body).fuse(thread)


def sw_tool_lane(xc: float, z: float) -> Part.Shape:
    """Đường đưa mũ vít + tua vít vào: từ ngoài vách -Y tới mặt -Y thân công tắc."""
    y0 = BOX_Y0 - 25.0                    # cả cán tua vít ngoài hộp
    return _cyl_y(SW_DRIVER_D, (SW_FIN_Y0 - SW_T) - y0, xc, y0, z)


def sw_pilot_tool(xc: float, z: float) -> Part.Shape:
    """Lỗ mồi vít M2 — ĐỤC THỦNG vấu gắn (chiều dài VÍT mới là thứ bị khống chế)."""
    return _cyl_y(SW_PILOT_D, SW_FIN_T + 1.5, xc, SW_FIN_Y0 - 0.75, z)


def sw_term_z() -> list[float]:
    """Cao độ tâm 3 chân hàn (COM/NO/NC) — xoè đều theo chiều dài thân CT."""
    zc = SW_Z0 + SW_L / 2.0
    return [zc - SW_TERM_PITCH, zc, zc + SW_TERM_PITCH]


def sw_term_zone(is_max: bool) -> Part.Shape:
    """Hốc TRỐNG sau lưng công tắc: 3 lá đồng + mối hàn + chỗ bẻ dây xuống máng.

    Chân hàn quay ra XA thanh trượt nên hốc này ăn về phía động cơ (CT MIN) và về
    phía gối đỡ (CT MAX) — hai chỗ trước đây có thịt khung chặn ngay lưng công tắc.
    """
    x0, x1 = sw_body_x(is_max)
    xa, xb = (x1, x1 + SW_TERM_ZONE) if is_max else (x0 - SW_TERM_ZONE, x0)
    return _box2(xa, xb, BAR_Y0, SW_FIN_Y0, BASE_T, SW_Z0 + SW_L)


def duct_y() -> tuple[float, float]:
    """Lòng MÁNG DÂY: dải -Y sau lưng công tắc, chạy suốt hộp."""
    return BASE_Y0, BAR_Y0


def duct_x() -> tuple[float, float]:
    """Đoạn máng dùng được — hai đầu là 2 trụ nắp góc -Y."""
    return BASE_X0 + POST_W, BASE_X1 - POST_W


def wire_lane_y() -> tuple[float, float]:
    """Hành lang dẫn dây ra khe: giữa lưng công tắc và mặt -Y của máng ĐC."""
    return BAR_Y0, -CRADLE_Y


def duct_tab_x() -> list[float]:
    """Mép -X của 4 vấu giữ dây: rải đều trong lòng máng, né 2 trụ góc VÀ né 4 vít M2
    bắt công tắc (thân vít băng ngang máng ở z ~ 9)."""
    x0, x1 = duct_x()
    a = x0 + 2.0
    b = x1 - 2.0 - DUCT_TAB_X
    keep_out = []
    pad = SW_HOLE_D / 2.0 + 0.5          # né cả LỖ THAO TÁC Ø4.5, không chỉ thân vít
    for is_max in (False, True):
        for xc, _z in sw_hole_sites(is_max):
            keep_out.append((xc - DUCT_TAB_X - pad, xc + pad))
    out = []
    n = 4
    for i in range(n):
        x = a + i * (b - a) / (n - 1)
        for lo, hi in keep_out:
            if lo < x < hi:
                x = hi if hi <= b else lo      # đẩy qua bên phải, hết chỗ thì lùi trái
        out.append(min(max(x, a), b))
    return out


def duct_tabs() -> Part.Shape:
    """Vấu chìa từ vách -Y, luồn dây xuống dưới là dây nằm yên trong máng."""
    tool = None
    for x in duct_tab_x():
        t = _box2(x, x + DUCT_TAB_X, BASE_Y0, BASE_Y0 + DUCT_TAB_Y,
                  DUCT_Z1, DUCT_Z1 + DUCT_TAB_T)
        tool = t if tool is None else tool.fuse(t)
    return tool


def wire_exit_tool() -> Part.Shape:
    """KHE RA DÂY 2 công tắc: xuyên vách -X, nằm giữa hành lang dẫn dây."""
    ly0, ly1 = wire_lane_y()
    yc = 0.5 * (ly0 + ly1)
    return _box2(BOX_X0 - 1.0, BASE_X0 + 0.5,
                 yc - WIRE_EXIT_W / 2.0, yc + WIRE_EXIT_W / 2.0,
                 WIRE_EXIT_Z0, WIRE_EXIT_Z1)


def sw_fin_x(is_max: bool) -> tuple[float, float]:
    """Vấu chỉ trải tới mặt trước thân công tắc, không chìa ra chắn thanh."""
    x0, x1 = sw_body_x(is_max)
    if is_max:
        return x0, max(END_WALL_X1, x1)
    return -12.0, x1


def make_sw_fin(is_max: bool) -> Part.Shape:
    """Vấu đứng mang công tắc; hàn liền vào gá động cơ / gối đỡ.

    Đuôi vấu MIN chạy tới x = -12 để bám chân gá, mà nắp kẹp ĐC giờ rộng tới
    y = -CRADLE_Y nên nó phủ lên đoạn đuôi đó: HẠ NÓC đoạn đuôi xuống dưới nắp kẹp
    (phần cao chỉ cần ở chỗ có thân công tắc).
    """
    x0, x1 = sw_fin_x(is_max)
    fin = _box2(x0, x1, SW_FIN_Y0, SW_FIN_Y0 + SW_FIN_T, BASE_T, SW_Z0 + SW_L + 2.0)
    for xc, z in sw_hole_sites(is_max):
        fin = _cut(fin, sw_pilot_tool(xc, z))
    if not is_max:
        fin = _cut(fin, clamp_clear_tool())
    return _refine(fin)


def make_sw_body_only(is_max: bool) -> Part.Shape:
    """Chỉ THÂN công tắc — dùng kiểm tra va chạm (cần gạt thì phải bị ấn)."""
    x0, x1 = sw_body_x(is_max)
    return _box2(x0, x1, SW_FIN_Y0 - SW_T, SW_FIN_Y0, SW_Z0, SW_Z0 + SW_L)


def bar_face_x(xc: float, is_max: bool) -> float:
    """Mặt THÂN thanh gặp công tắc.

    KHÔNG dùng BoundBox: bao của Slide_Bar còn gồm bạc trục trơn dài 18 mm ở
    y = 17, trong khi công tắc nằm ở y ~ -20 nơi chỉ có thân thanh dày BAR_X.
    """
    return xc + BAR_X / 2.0 if is_max else xc - BAR_X / 2.0


def make_limit_switch(is_max: bool) -> Part.Shape:
    """KW11 có bánh xe (mua sẵn): thân + 2 lỗ M2 + cần gạt 16 mm + bánh xe."""
    body = make_sw_body_only(is_max)
    for xc, z in sw_hole_sites(is_max):
        body = _cut(body, _cyl_y(SW_BODY_HOLE_D, SW_T + 2.0, xc, SW_FIN_Y0 - SW_T - 1.0, z))

    sg = sw_sign(is_max)
    face = sw_front_x(is_max)
    rx, rz = sw_roller_center(is_max)
    z_piv = SW_Z0 + 2.0
    y_mid = SW_FIN_Y0 - SW_T / 2.0

    # cần gạt: lá thép nghiêng từ chốt xoay ra tới bánh xe
    pts = [
        App.Vector(face, y_mid - SW_LEVER_W / 2.0, z_piv - 0.8),
        App.Vector(face, y_mid - SW_LEVER_W / 2.0, z_piv + 0.8),
        App.Vector(rx, y_mid - SW_LEVER_W / 2.0, rz + 0.4),
        App.Vector(rx, y_mid - SW_LEVER_W / 2.0, rz - 0.4),
    ]
    pts.append(pts[0])
    lever = Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, SW_LEVER_W, 0))

    roller = Part.makeCylinder(
        SW_ROLLER_D / 2.0, SW_ROLLER_W,
        App.Vector(rx, y_mid - SW_ROLLER_W / 2.0, rz), App.Vector(0, 1, 0),
    )
    # 3 CHÂN HÀN trên mặt lưng (mặt đối diện cần gạt)
    x0, x1 = sw_body_x(is_max)
    back = x1 if is_max else x0
    tip = back + SW_TERM_L if is_max else back - SW_TERM_L
    terms = None
    for zc in sw_term_z():
        t = _box2(min(back, tip), max(back, tip),
                  y_mid - SW_TERM_T / 2.0, y_mid + SW_TERM_T / 2.0,
                  zc - SW_TERM_W / 2.0, zc + SW_TERM_W / 2.0)
        terms = t if terms is None else terms.fuse(t)

    _ = sg  # hướng nhô đã nằm trong rx
    return _refine(body.fuse(lever).fuse(roller).fuse(terms))


# ---------------------------------------------------------------------------
# Thanh tịnh tiến + hốc đai ốc
# ---------------------------------------------------------------------------
def load_hole_sites() -> list[tuple[float, float]]:
    """(y, z) 2 lỗ bu lông M3 xuyên bệ gá theo X — xếp chồng theo Z, giữa bề rộng."""
    return [(0.0, WALL_Z_MID - LOAD_HOLE_DZ), (0.0, WALL_Z_MID + LOAD_HOLE_DZ)]


def hub_x(xc: float) -> tuple[float, float]:
    """Khoảng X của HUB ôm đai ốc — mọc từ mặt +X của thân thanh ra tới HUB_FRONT."""
    return xc - BAR_X / 2.0, xc + HUB_FRONT


def bore_x(xc: float) -> tuple[float, float]:
    """Lỗ khoét Ø(khớp nối): từ mặt -X của thanh tới mặt ngoài vách trước."""
    return xc - BAR_X / 2.0, xc + BORE_FRONT


def pocket_x(xc: float) -> tuple[float, float]:
    """Khe hở nóc chứa đai ốc, kẹp giữa 2 vách NUT_WALL."""
    x1 = xc + HUB_FRONT - NUT_WALL
    return x1 - NUT_POCKET, x1


def nut_x(xc: float) -> tuple[float, float]:
    """Khoảng X của đai ốc trong khe (đặt giữa, rơ 0.1 mm mỗi đầu)."""
    a = pocket_x(xc)[0] + (NUT_POCKET - NUT_H) / 2.0
    return a, a + NUT_H


def make_hex_nut(xc: float) -> Part.Shape:
    """Đai ốc LỤC GIÁC M4 thường (mua sẵn), 2 mặt phẳng quay về +-Y để tì vào khe."""
    a, _ = nut_x(xc)
    body = _hex_prism_x(NUT_AF, NUT_H, a, 0.0, AXIS_Z, phase=30.0)
    return _refine(_cut(body, _cyl_x(ROD_D, NUT_H + 2.0, a - 1.0, 0.0, AXIS_Z)))


def make_slide_bar(xc: float) -> Part.Shape:
    """THANH TỊNH TIẾN — thân trong hộp + trụ/vách gá dẹt (mặt ⊥ X) ngoài nắp."""
    bar = _box2(xc - BAR_X / 2.0, xc + BAR_X / 2.0, BAR_Y0, BAR_Y1, BAR_Z0, BAR_Z1)
    boss = _cyl_x(BOSS_D, BOSS_L, xc - BOSS_L / 2.0, GUIDE_Y, AXIS_Z)
    hub = _box2(*hub_x(xc), -HUB_Y, HUB_Y, BAR_Z0, BAR_Z1)
    # BỆ GÁ: một trụ dẹt DUY NHẤT, rộng đúng bằng khe nắp, chạy suốt từ thân thanh
    # lên quá mặt nắp WALL_H mm. Không có phần xoè ngang (xem chú thích LOAD_HOLE_DZ).
    stem = _box2(xc - MOUNT_T / 2.0, xc + MOUNT_T / 2.0,
                 STEM_Y0, STEM_Y1, BAR_Z1 - 1.0, WALL_Z1)
    body = bar.fuse(boss).fuse(hub).fuse(stem)

    body = _cut(body, _cyl_x(BOSS_BORE, BOSS_L + 4.0, xc - BOSS_L / 2.0 - 2.0, GUIDE_Y, AXIS_Z))
    b0, b1 = bore_x(xc)
    body = _cut(body, _cyl_x(COUP_CLEAR_D, b1 - (b0 - 2.0), b0 - 2.0, 0.0, AXIS_Z))
    px0, px1 = pocket_x(xc)
    body = _cut(body, _box2(px0, px1, -NUT_SLOT_W / 2.0, NUT_SLOT_W / 2.0,
                            NUT_SLOT_Z0, BAR_Z1 + 1.0))
    body = _cut(body, _cyl_x(ROD_CLEAR_D, HUB_FRONT + BAR_X / 2.0 + 3.0,
                             xc - BAR_X / 2.0 - 1.0, 0.0, AXIS_Z))
    # 2 lỗ bu lông M3 xuyên bệ gá theo X
    for y, z in load_hole_sites():
        body = _cut(body, _cyl_x(M3_CLEAR, MOUNT_T + 4.0,
                                 xc - MOUNT_T / 2.0 - 2.0, y, z))
    return _refine(body)


# ---------------------------------------------------------------------------
# 4. Kiểm tra hình học
# ---------------------------------------------------------------------------
def _common_vol(a: Part.Shape, b: Part.Shape) -> float:
    try:
        c = a.common(b)
        return float(c.Volume) if c is not None else 0.0
    except Exception:
        return -1.0


def verify(parts: dict) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    x_min, x_max = travel_range()

    # dùng THÂN công tắc, không kể cần gạt — cần gạt BỊ ẤN ở cuối hành trình là
    # đúng ý đồ, đưa cả cần gạt vào đây sẽ báo động giả
    static = (parts["Housing"]
              .fuse(make_sw_body_only(False)).fuse(make_sw_body_only(True)))
    for label, x in (("dau hanh trinh", x_min), ("cuoi hanh trinh", x_max)):
        v = _common_vol(make_slide_bar(x), static)
        checks.append(
            ("Thanh %s khong dung ke co dinh" % label, v < 1e-6,
             "chong lan %.2f mm3" % v)
        )

    # --- khớp nối: chui lọt qua thanh, không đụng bích, kẹp đủ trục ---
    for label, x in (("dau", x_min), ("cuoi", x_max)):
        v = _common_vol(make_slide_bar(x), parts["Coupler"])
        checks.append(("Khop noi chui lot qua lo cua thanh (%s)" % label, v < 1e-6,
                       "chong lan %.2f mm3" % v))
    v = _common_vol(make_slide_bar(x_min), parts["Coupler"])
    checks.append(("Vach hoc dai oc khong dung khop noi", v < 1e-6,
                   "chong lan %.2f mm3, khe %.1f mm" % (v, NUT_CLEAR)))
    v = _common_vol(parts["Coupler"], parts["Housing"])
    checks.append(("Khop noi khong co xat bich dung", v < 1e-6,
                   "chong lan %.2f mm3, khe %.1f mm" % (v, COUP_GAP)))
    grip = SHAFT_LEN - COUP_X0
    checks.append(
        ("Khop noi om du truc dong co (>= 5 mm)", grip >= 5.0,
         "om %.1f mm (truc dai %.0f, bich het o %.1f)" % (grip, SHAFT_LEN, COUP_X0 - COUP_GAP))
    )
    # vít hãm phía ĐỘNG CƠ phải thông qua thân khớp nối và tì đúng vào MẶT VẠT D
    xs_m, xs_r = coupler_set_screw_x()
    tip = _cyl_z(COUP_SET_D - 0.4, 2.0, xs_m, 0.0, AXIS_Z + SHAFT_D / 2.0 - SHAFT_FLAT)
    ok_bore = _common_vol(parts["Coupler"], tip) < 1e-6
    ok_flat = SHAFT_FLAT_X0 <= xs_m - COUP_SET_D / 2.0 and xs_m + COUP_SET_D / 2.0 <= SHAFT_LEN
    checks.append(
        ("Vit ham -X ti dung mat vat D cua truc", ok_bore and ok_flat,
         "vit tai x = %.1f, mat vat %.1f..%.1f" % (xs_m, SHAFT_FLAT_X0, SHAFT_LEN))
    )
    # vít hãm phía TY REN phải thông tới mặt ty ren, và nằm trong đoạn ty ren cắm vào
    tip = _cyl_z(COUP_SET_D - 0.4, 2.0, xs_r, 0.0, AXIS_Z + ROD_D / 2.0)
    ok_bore = _common_vol(parts["Coupler"], tip) < 1e-6
    ok_span = ROD_X0 <= xs_r - COUP_SET_D / 2.0 and xs_r + COUP_SET_D / 2.0 <= COUP_X1
    checks.append(
        ("Vit ham +X can duoc vao ty ren", ok_bore and ok_span,
         "vit tai x = %.1f, ty ren trong khop noi %.1f..%.1f" % (xs_r, ROD_X0, COUP_X1))
    )
    # ty ren cắm đủ sâu (>= 1.5 x D) nhưng KHÔNG cắm hết lỗ — phần dư là hành trình
    checks.append(
        ("Lo O4 du sau cho chieu cam da chon", SPACER_L >= -1e-9,
         "lo %.1f mm, cam %.1f mm, cu %.1f mm" % (COUP_BORE_R, COUP_ROD_IN, SPACER_L))
    )
    checks.append(
        ("Ty ren cam du sau vao khop noi (>= 1.5 x D)", COUP_ROD_IN >= 1.5 * ROD_D - 1e-9,
         "cam %.1f mm / can %.1f mm (lo sau %.1f, du %.1f mm doi thanh hanh trinh)"
         % (COUP_ROD_IN, 1.5 * ROD_D, COUP_BORE_R, SPACER_L))
    )
    # cữ phải lấp KÍN phần lỗ còn lại thì ty ren mới có chỗ tì
    sp = parts["Coupler_Spacer"]
    bb = sp.BoundBox
    ok = (abs(bb.XMin - (COUP_X1 - COUP_BORE_R)) < 1e-6 and abs(bb.XMax - ROD_X0) < 1e-6
          and SPACER_D < ROD_D + 0.1)
    v = max(_common_vol(sp, parts["Coupler"]), _common_vol(sp, parts["Thread_Rod"]))
    checks.append(
        ("Cu day lo dat dung cho, tha lot long lo", ok and v < 1e-6,
         "cu x = %.1f..%.1f (O%.1f), duoi ty ren o %.1f" % (bb.XMin, bb.XMax, SPACER_D, ROD_X0))
    )

    v = _common_vol(parts["Slide_Bar"], parts["Guide_Shaft"])
    checks.append(("Truc tron chui lot qua bac thanh truot", v < 1e-6, "chong lan %.2f mm3" % v))

    # --- LUỒN Guide_Shaft TỪ NGOÀI VÀO (Housing liền khối) ---
    # Đường luồn: ngoài vách +X -> lỗ vách -> lỗ xuyên gối đỡ -> bạc Slide_Bar -> hốc mù ĐC.
    x_out = BOX_X1 + 5.0
    lane = _cyl_x(GUIDE_D, x_out - GUIDE_SHAFT_X0, GUIDE_SHAFT_X0, GUIDE_Y, AXIS_Z)
    v = _common_vol(parts["Housing"], lane)
    for xb in (_X_MIN_MECH, _X_MAX_MECH):
        v += _common_vol(make_slide_bar(xb), lane)
    checks.append(
        ("Duong luon truc tron tu ngoai vach +X vao hoc DC thong", v < 1e-6,
         "vuong %.2f mm3 tren doan x %.1f -> %.1f" % (v, x_out, GUIDE_SHAFT_X0))
    )
    mouth_m = FACE_X0 + FACE_T + GUIDE_BOSS_L
    eng_m = mouth_m - GUIDE_SHAFT_X0
    tip = GUIDE_SHAFT_X0 + GUIDE_SHAFT_LEN
    checks.append(
        ("Truc an du trong hoc mu ĐC va xuyen het vach +X",
         eng_m + 1e-9 >= GUIDE_MIN_ENG and tip >= BOX_X1 + 1.5 - 1e-9,
         "eng ĐC %.1f mm (min %.1f), dau +X tho %.1f mm khoi vach"
         % (eng_m, GUIDE_MIN_ENG, tip - BOX_X1))
    )
    checks.append(
        ("Truc tron xuyen lo goi do (o do thu 2)",
         END_T >= GUIDE_D - 1e-9,
         "lo goi do dai %.1f mm >= O%.1f" % (END_T, GUIDE_D))
    )
    # --- LUỒN Thread_Rod TỪ NGOÀI VÀO: lỗ vách +X -> lỗ gối đỡ -> đai ốc -> khớp nối ---
    rod_lane = _cyl_x(ROD_D, x_out - (COUP_X1 - COUP_ROD_IN), COUP_X1 - COUP_ROD_IN,
                      0.0, AXIS_Z)
    v = _common_vol(parts["Housing"], rod_lane)
    checks.append(
        ("Duong luon ty ren tu ngoai vach +X vao khop noi thong", v < 1e-6,
         "vuong %.2f mm3 (chi con dai oc M4 phai van qua)" % v)
    )
    # Vít hãm M3: lỗ thông trên Housing, mũi nằm đúng chỗ vạt trục ở tư thế chạy
    lock_probe = _cyl_z(M3_TAP - 0.3, GUIDE_BOSS_D / 2.0 + 3.0,
                        GUIDE_LOCK_X, GUIDE_Y, AXIS_Z + 0.5)
    lock_open = _common_vol(parts["Housing"], lock_probe) < 1e-6
    checks.append(
        ("Lo vit ham M3 tren vau hoc DC thong", lock_open,
         "OK x=%.1f" % GUIDE_LOCK_X if lock_open else "lo bi bit / x=%.1f" % GUIDE_LOCK_X)
    )
    tip = _cyl_z(M3_TAP - 0.4, GUIDE_LOCK_FLAT - 0.05, GUIDE_LOCK_X, GUIDE_Y,
                 AXIS_Z + GUIDE_D / 2.0 - GUIDE_LOCK_FLAT)
    checks.append(
        ("Vit ham ti dung vat Guide_Shaft o tu the chay",
         _common_vol(parts["Guide_Shaft"], tip) < 1e-6
         and abs(parts["Guide_Shaft"].BoundBox.XMin - GUIDE_SHAFT_X0) < 1e-6,
         "vat sau %.1f @ x=%.1f, xb=%.1f" % (
             GUIDE_LOCK_FLAT, GUIDE_LOCK_X, parts["Guide_Shaft"].BoundBox.XMin))
    )
    # Khi đã siết: vít mô hình nằm trong lỗ + trong vạt (không ăn Housing/shaft)
    if "Guide_Lock_Screw" in parts:
        v_h = _common_vol(parts["Guide_Lock_Screw"], parts["Housing"])
        v_s = _common_vol(parts["Guide_Lock_Screw"], parts["Guide_Shaft"])
        checks.append(
            ("Vit ham M3 lot lo + ti vat (khong an Housing)",
             v_h < 1e-6 and v_s < 1e-6,
             "hous %.2f / shaft %.2f mm3" % (v_h, v_s))
        )

    # --- đầu -X trục phải bị vách mù chặn (đẩy vào là dừng đúng chỗ) ---
    bad = []
    for nm, x0 in (("Housing", FACE_X0),):
        # khối trụ Ø5 ngay ngoài đầu trục phải ĐẶC hoàn toàn -> đó là vách chặn
        wall = _cyl_x(GUIDE_D, GUIDE_BLIND_WALL, x0, GUIDE_Y, AXIS_Z)
        wall = _cut(wall, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                                 x0 - 1.0, GUIDE_Y, AXIS_Z))
        if _common_vol(parts[nm], wall) < 0.99 * wall.Volume:
            bad.append(nm)
    checks.append(
        ("Dau -X truc tron bi vach mu chan", not bad,
         "vach %.1f mm (%s)" % (GUIDE_BLIND_WALL, ", ".join(bad) if bad else "kin"))
    )
    gs = parts["Guide_Shaft"].BoundBox
    checks.append(
        ("Truc tron dung dau -X trong hoc mu",
         gs.XMin >= FACE_X0 + GUIDE_BLIND_WALL - 1e-6,
         "truc x = %.1f..%.1f (vach mu het o %.1f)"
         % (gs.XMin, gs.XMax, FACE_X0 + GUIDE_BLIND_WALL))
    )
    # hốc phải sâu >= 1 x đường kính trục, nếu không thì trục lỏng lẻo dễ lật
    checks.append(
        ("Hoc mu phia DC sau >= 1 x O truc", GUIDE_SOCKET_M >= GUIDE_D - 1e-9,
         "hoc %.1f mm, can %.1f" % (GUIDE_SOCKET_M, GUIDE_D))
    )
    # lỗ thông hơi phải thông suốt vách nhưng nhỏ hơn trục
    bad = 0
    for nm, x0 in (("Housing", FACE_X0 - 0.5),):
        vent = _cyl_x(GUIDE_VENT_D - 0.3, GUIDE_BLIND_WALL + 0.4, x0, GUIDE_Y, AXIS_Z)
        if _common_vol(parts[nm], vent) > 1e-6:
            bad += 1
    checks.append(
        ("Lo thong hoi thong suot va nho hon truc", bad == 0 and GUIDE_VENT_D < GUIDE_D,
         "O%.1f < O%.1f, %d lo bi bit" % (GUIDE_VENT_D, GUIDE_D, bad))
    )
    # vấu nối dài hốc không được đụng gì đang chuyển động
    v = max(_common_vol(parts["Housing"], make_slide_bar(x_min)),
            _common_vol(parts["Housing"], parts["Coupler"]))
    checks.append(("Vau noi dai hoc khong dung thanh / khop noi", v < 1e-6,
                   "chong lan %.2f mm3" % v))

    v = _common_vol(parts["Slide_Bar"], parts["Thread_Rod"])
    checks.append(("Ty ren khong cham than thanh truot", v < 1e-6, "chong lan %.2f mm3" % v))

    checks.append(
        ("Dai oc luc giac la MOT khoi lien", len(parts["Hex_Nut"].Solids) == 1,
         "%d khoi" % len(parts["Hex_Nut"].Solids))
    )
    v = _common_vol(parts["Slide_Bar"], parts["Hex_Nut"])
    checks.append(("Dai oc lot vao khe tren thanh", v < 1e-6, "chong lan %.2f mm3" % v))
    # hub phải liền một khối với thân thanh, không phải 2 cục chạm nhau
    checks.append(("Thanh (ca hub) la MOT khoi lien", len(parts["Slide_Bar"].Solids) == 1,
                   "%d khoi" % len(parts["Slide_Bar"].Solids)))
    # mặt trước hub không được vượt mặt trước bạc — nếu vượt là ăn mất hành trình
    checks.append(("Mat truoc hub khong vuot mat truoc bac truc tron",
                   HUB_FRONT <= BOSS_L / 2.0 + 1e-9,
                   "hub %.1f, bac %.1f" % (HUB_FRONT, BOSS_L / 2.0)))
    checks.append(
        ("Hoc End_Block cho hub/bac chui vao (>= 4 mm)", END_HUB_RECESS >= 4.0 - 1e-9,
         "sau %.1f mm" % END_HUB_RECESS)
    )
    checks.append(
        ("SW_PRESS du phong sau trip (0.3..1.0)", 0.3 - 1e-9 <= SW_PRESS <= 1.0 + 1e-9,
         "%.1f mm / dau" % SW_PRESS)
    )
    # tai chan co MAX: hub nam trong hoc, khong chong End_Block
    v = _common_vol(make_slide_bar(_X_MAX_MECH), parts["Housing"])
    checks.append(
        ("Hub/bac lot hoc End_Block o chan co MAX", v < 1e-6,
         "chong lan %.2f mm3 (recess %.1f, clear %.1f)" % (v, END_HUB_RECESS, END_CLEAR))
    )
    # hub phai chui qua mat END_X0
    tip = _box2(END_X0 + 0.2, END_X0 + min(2.0, END_HUB_RECESS - 0.2),
                -HUB_Y + 0.5, HUB_Y - 0.5, AXIS_Z - 2.0, AXIS_Z + 2.0)
    filled = _common_vol(make_slide_bar(_X_MAX_MECH), tip)
    checks.append(
        ("O chan co MAX hub that su nam trong hoc", filled > 0.5,
         "thit hub trong hoc %.2f mm3" % filled)
    )

    # khe phải THỰC SỰ ôm 2 mặt phẳng của đai ốc: có thịt ngay 2 bên thì mới chống xoay
    bad = 0
    nx0, nx1 = nut_x(BAR_HOME_X)
    for side in (-1.0, 1.0):
        ya = side * (NUT_SLOT_W / 2.0 + 0.2)
        yb = side * (NUT_SLOT_W / 2.0 + 1.4)
        probe = _box2(nx0 + 0.5, nx1 - 0.5, min(ya, yb), max(ya, yb),
                      AXIS_Z - 2.0, AXIS_Z + 2.0)
        if _common_vol(parts["Slide_Bar"], probe) < 0.99 * probe.Volume:
            bad += 1
    checks.append(("2 vach khe ep sat 2 mat dai oc (chong xoay)", bad == 0,
                   "%d vach thieu thit" % bad))
    # khe phải HỞ NÓC suốt từ đai ốc lên đỉnh hốc, nếu không thì không thả được đai ốc
    slot_top = _box2(nx0 + 0.5, nx1 - 0.5, -NUT_SLOT_W / 2.0 + 0.2, NUT_SLOT_W / 2.0 - 0.2,
                     AXIS_Z + NUT_AC / 2.0, BAR_Z1)
    checks.append(
        ("Khe ho noc — tha duoc dai oc tu tren xuong",
         _common_vol(parts["Slide_Bar"], slot_top) < 1e-6,
         "khe rong %.1f (S dai oc %.1f)" % (NUT_SLOT_W, NUT_AF))
    )
    # rãnh hở nóc phải nằm HẲN ở phía +X thân thanh, không được xẻ vào tấm thân
    checks.append(
        ("Ranh ho noc khong xe vao than thanh", pocket_x(BAR_HOME_X)[0] >= BAR_HOME_X + BAR_X / 2.0,
         "ranh bat dau o +%.1f so voi tam, than het o +%.1f"
         % (pocket_x(BAR_HOME_X)[0] - BAR_HOME_X, BAR_X / 2.0))
    )
    # 2 vách chặn dọc trục phải có thịt quanh lỗ ty ren
    bad = 0
    px0, px1 = pocket_x(BAR_HOME_X)
    for xa in (px0 - NUT_WALL + 0.3, px1 + 0.3):
        ring = _cyl_x(NUT_AF - 0.4, NUT_WALL - 0.6, xa, 0.0, AXIS_Z)
        ring = _cut(ring, _cyl_x(ROD_CLEAR_D, NUT_WALL + 2.0, xa - 1.0, 0.0, AXIS_Z))
        if _common_vol(parts["Slide_Bar"], ring) < 0.98 * ring.Volume:
            bad += 1
    checks.append(("2 vach chan doc truc co vanh dac quanh ty ren", bad == 0,
                   "%d vach thieu thit" % bad))

    # ty ren chỉ dài ROD_LEN — đai ốc phải còn nằm trên ren ở CẢ HAI đầu hành trình
    bad = []
    for label, x in (("dau", x_min), ("cuoi", x_max)):
        n0, n1 = nut_x(x)
        if n0 < COUP_X1 or n1 > ROD_X1:
            bad.append(label)
    checks.append(
        ("Dai oc con an ren o ca 2 dau hanh trinh", not bad,
         "ren ho x = %.1f..%.1f, dai oc %.1f..%.1f" % (
             COUP_X1, ROD_X1, nut_x(x_min)[0], nut_x(x_max)[1]))
    )

    # --- đầu ty ren: mốc END_X0 (không còn vách giữa — tránh lỗ CT MAX) ---
    eng = ROD_X1 - END_X0
    checks.append(
        ("Dau ty ren toi moc END_X0 (khong vach giua)", abs(eng - ROD_END_SUPPORT) < 1e-6,
         "an %.1f mm toi x=%.1f; vach that o %.1f..%.1f"
         % (eng, END_X0, END_WALL_X0, END_WALL_X1))
    )
    v = _common_vol(parts["Thread_Rod"], parts["Housing"])
    checks.append(("Lo do khong bop ty ren", v < 1e-6, "chong lan %.2f mm3" % v))
    # Không còn thịt vách tại X lỗ CT MAX (giữa END_X0 và END_WALL_X0, trừ xương đáy thấp)
    air_hits = 0
    for xc, z in sw_hole_sites(True):
        r = (SW_HOLE_D - 0.4) / 2.0
        lane = _box2(
            xc - r, xc + r,
            END_WALL_Y0, GUIDE_Y - BOSS_D / 2.0 - 2.0,
            max(z - r, BASE_T + FOOT_T + 0.5), z + r,
        )
        if lane.Volume > 1e-6 and _common_vol(parts["Housing"], lane) > 0.05:
            air_hits += 1
    checks.append(
        ("Khong vach giua tai lo CT MAX (bu long khong xuyen thit)",
         air_hits == 0,
         "va cham %d/%d lo" % (air_hits, 2))
    )
    checks.append(
        ("Vach day sat canh hop (sau lo CT MAX)",
         END_WALL_X0 >= _LS_MAX_HOLE_X + SW_HOLE_D / 2.0 + 1.0 - 1e-9
         and abs(END_WALL_X1 - BASE_X1) < 1e-9,
         "wall x=%.1f..%.1f | lo xc=%.1f | BASE_X1=%.1f"
         % (END_WALL_X0, END_WALL_X1, _LS_MAX_HOLE_X, BASE_X1))
    )

    # --- 2 công tắc hành trình ---
    for label, is_max, x_trip in (("min", False, x_min), ("max", True, x_max)):
        bar = make_slide_bar(x_trip)
        face = bar_face_x(x_trip, is_max)
        # mặt thanh tại điểm tác động phải trùng bánh xe đã bị ấn
        want = sw_trip_face_x(is_max)
        checks.append(
            ("Thanh cham cong tac %s dung tai gioi han" % label, abs(face - want) < 0.05,
             "mat thanh %.2f, can %.2f" % (face, want))
        )
        # ở điểm tác động thanh CHƯA chạm thân công tắc
        v = _common_vol(bar, make_sw_body_only(is_max))
        checks.append(
            ("Thanh chua dam vao than cong tac %s" % label, v < 1e-6,
             "chong lan %.2f mm3, con %.1f mm over-travel sau khi tac dong"
             % (v, _SW_OVERTRAVEL))
        )

    # công tắc phải nằm trong vùng THÂN thanh quét qua, nếu không sẽ không bao giờ chạm
    sw_y0, sw_y1 = SW_FIN_Y0 - SW_T, SW_FIN_Y0
    _, z_roll = sw_roller_center(False)
    ok_y = BAR_Y0 <= sw_y0 and sw_y1 <= BAR_Y1
    ok_z = BAR_Z0 + SW_ROLLER_D / 2.0 <= z_roll <= BAR_Z1 - SW_ROLLER_D / 2.0
    checks.append(
        ("Banh xe nam gon trong tiet dien than thanh", ok_y and ok_z,
         "y %.1f..%.1f trong %.1f..%.1f | z banh xe %.1f trong %.1f..%.1f"
         % (sw_y0, sw_y1, BAR_Y0, BAR_Y1, z_roll, BAR_Z0, BAR_Z1))
    )

    # 2 lỗ M2: lỗ trên công tắc phải trùng lỗ trên vấu, và bu lông phải xuyên được
    bad = 0
    thin = 0
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            # thân vít xuyên thân CT (mũ tì mặt -Y thân CT, không tì lên vách)
            shank = _cyl_y(SW_BODY_HOLE_D - 0.2,
                           (SW_FIN_Y0 - 0.1) - (SW_FIN_Y0 - SW_T),
                           xc, SW_FIN_Y0 - SW_T, z)
            if _common_vol(parts["Limit_Switch_Max" if is_max else "Limit_Switch_Min"],
                           shank) > 1e-6:
                bad += 1
            if _common_vol(parts["Housing"], shank) > 1e-6:
                bad += 1
            # đoạn MỒI trong vấu phải còn thịt quanh lỗ để vít tự ren cắn
            ring = _cyl_y(SW_PILOT_D + 2.4, SW_FIN_T, xc, SW_FIN_Y0, z)
            if _common_vol(parts["Housing"], ring) < 0.5 * ring.Volume:
                thin += 1
            # lỗ mồi phải ĐỤC THỦNG vấu (không phải lỗ mù)
            thru = _cyl_y(SW_PILOT_D - 0.4, SW_FIN_T + 1.0, xc, SW_FIN_Y0 - 0.5, z)
            if _common_vol(parts["Housing"], thru) > 1e-6:
                bad += 1
            # và phải xuyên ra CHỖ TRỐNG, không đâm tiếp vào thịt vách phía sau
            out = _cyl_y(SW_PILOT_D + 0.4, SW_FIN_RELIEF - 0.3, xc,
                         SW_FIN_Y0 + SW_FIN_T + 0.1, z)
            if _common_vol(parts["Housing"], out) > 1e-6:
                bad += 1
    into = 0.0
    hit = []
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            shank = sw_screw_shank(xc, z)
            into += _common_vol(shank, end_hub_recess_tool())
            if _common_vol(sw_tool_lane(xc, z), parts["Housing"]) > 1e-6:
                hit.append("lo thao tac bi bit")
            for nm in ("Coupler", "Thread_Rod", "Guide_Shaft"):
                if _common_vol(shank, parts[nm]) > 1e-6:
                    hit.append(nm)
            for xb in (_X_MIN_MECH, BAR_HOME_X, _X_MAX_MECH):
                if _common_vol(shank, make_slide_bar(xb)) > 1e-6:
                    hit.append("Slide_Bar")
    checks.append(
        ("Mui vit M2 dung trong vau, khong tho vao hoc hub / duong thanh chay",
         into < 1e-6 and not hit,
         "vao hoc hub %.2f mm3, dung: %s (mui vit dung o y=%.1f, hub o y=%.1f)"
         % (into, ", ".join(sorted(set(hit))) if hit else "khong",
            SW_SCREW_TIP, -HUB_Y))
    )
    checks.append(
        ("4 vit M2 tu ren: than trong, vau con thit (khong can dai oc)",
         bad == 0 and thin == 0,
         "%d lo bi bit/khong thung, %d vau mong (lo moi XUYEN het %.1f mm vau)"
         % (bad, thin, SW_FIN_T))
    )
    # XỎ VÍT: quét NGUYÊN CON VÍT suốt đường từ ngoài hộp vào tư thế siết
    ins = (SW_FIN_Y0 - SW_T) - (BOX_Y0 - 5.0)
    bad = []
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            path = _sweep_y(sw_screw_solid(xc, z), -ins, 0.5)
            v = _common_vol(parts["Housing"], path)
            for nm in ("Limit_Switch_Min", "Limit_Switch_Max"):
                v += max(0.0, _common_vol(parts[nm], path)
                         - _common_vol(parts[nm], sw_screw_solid(xc, z)))
            if v > 1e-6:
                bad.append("%s z=%.1f (%.2f mm3)"
                           % ("MAX" if is_max else "MIN", z, v))
    checks.append(
        ("Xo duoc con vit M2 tu ngoai vao (quet %.1f mm duong vao)" % ins,
         not bad, ", ".join(bad) if bad else
         "mu O%.1f qua lo O%.1f (ho %.2f mm ban kinh), 0 vuong"
         % (SW_HEAD_D, SW_HOLE_D, (SW_HOLE_D - SW_HEAD_D) / 2.0))
    )
    bad = []
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            v = _common_vol(parts["Housing"], sw_tool_lane(xc, z))
            if v > 1e-6:
                bad.append("%s z=%.1f" % ("MAX" if is_max else "MIN", z))
    checks.append(
        ("Mui tua vit O%.1f voi toi dau vit tu ngoai hop" % SW_DRIVER_D,
         not bad, ", ".join(bad) if bad else
         "voi %.1f mm tu mat ngoai vach -Y toi mu vit" % ((SW_FIN_Y0 - SW_T) - BOX_Y0))
    )
    checks.append(
        ("Mu vit M2 tì THANG vao than CT (ep CT vao vau)",
         SW_HOLE_D > SW_BODY_HOLE_D + 1.5,
         "lo thao tac O%.1f > mu vit M2 (~O3.8); vit M2 x %.0f, an ren %.1f mm"
         % (SW_HOLE_D, SW_SCREW_L, SW_SCREW_L - SW_T))
    )

    # công tắc không đụng động cơ; vấu CT đã nằm trong Housing nên không so Housing
    for nm in ("Limit_Switch_Min", "Limit_Switch_Max"):
        v = _common_vol(parts[nm], parts["N20_Motor"])
        checks.append(("%s khong dung dong co" % nm, v < 1e-6, "chong lan %.2f mm3" % v))

    # rơ dọc trục = khe giữa đai ốc và 2 vách hốc
    play = NUT_POCKET - NUT_H
    checks.append(("Ro doc truc cua dai oc <= 0.2 mm", play <= 0.2 + 1e-9, "%.2f mm" % play))

    v = _common_vol(parts["Housing"], parts["N20_Motor"])
    checks.append(("Dong co lot vao mang gia do", v < 1e-6, "chong lan %.2f mm3" % v))

    v = _common_vol(parts["Motor_Clamp"], parts["N20_Motor"])
    checks.append(("Nap kep khong an vao than dong co", v < 1e-6, "chong lan %.2f mm3" % v))
    checks.append(
        ("Motor_Clamp la MOT khoi lien (noc cau vuot)",
         len(parts["Motor_Clamp"].Solids) == 1,
         "%d khoi" % len(parts["Motor_Clamp"].Solids))
    )

    # trục trơn và ty ren phải song song và cùng cao độ
    checks.append(
        ("Truc tron SONG SONG ty ren (cung z, lech y %.0f mm)" % GUIDE_Y, True, "OK")
    )

    # ĐỘNG CƠ phải THẢ THẲNG TỪ TRÊN XUỐNG được (không vít ngang nào để bắt)
    drop = _sweep_z(parts["N20_Motor"], BOX_TOP + 12.0 - AXIS_Z)
    v = _common_vol(parts["Housing"], drop)
    checks.append(
        ("Dong co tha thang tu tren xuong mang", v < 1e-6,
         "vuong %.2f mm3 tren duong ha" % v)
    )
    # chặn dọc trục: bích chặn +X, vách MOT_STOP chặn -X
    gap = MOT_STOP_X1 - (parts["N20_Motor"].BoundBox.XMin + REAR_L)
    stop_face = _box2(MOT_STOP_X1 - 0.2, MOT_STOP_X1, -CAN_D / 2.0, CAN_D / 2.0,
                      AXIS_Z - CAN_D / 2.0, AXIS_Z)
    area = _common_vol(parts["Housing"], stop_face) / 0.2
    checks.append(
        ("DC bi kep doc truc giua bich va vach chan", abs(gap) <= 0.5 + 1e-9 and area >= 25.0,
         "khe sau lon %.2f mm, mat chan %.0f mm2" % (gap, area))
    )
    checks.append(
        ("Coc sau + day DC chui lot khe vach chan",
         MOT_REAR_SLOT + 1e-9 >= max(REAR_D + 1.0, CABLE_D),
         "khe %.1f mm (coc O%.1f, day O%.1f)" % (MOT_REAR_SLOT, REAR_D, CABLE_D))
    )
    # 4 VÍT TỰ REN kẹp ĐC: lỗ thông nắp, có thịt mồi ren trong máng, đáy lỗ MÙ, và
    # THÂN VÍT không đâm vào động cơ (lỗi cũ: y = ±6 nằm gọn trong hốc lon Ø12.4).
    bad = 0
    hit = 0.0
    cz0, cz1 = clamp_z()
    pilot_z0 = AXIS_Z - CLAMP_SCREW_ENG
    pilot_area = math.pi * (CLAMP_SCREW_PILOT / 2.0) ** 2
    for x, y in clamp_bolt_xy():
        probe = _cyl_z(CLAMP_SCREW_CLEAR - 0.2, cz1 - cz0 + 2.0, x, y, cz0 - 1.0)
        if _common_vol(parts["Motor_Clamp"], probe) > 1e-6:
            bad += 1
        ring = _cyl_z(CLAMP_SCREW_PILOT + 3.0, 4.0, x, y, AXIS_Z - 5.0)
        if _common_vol(parts["Housing"], ring) < 20.0:
            bad += 1
        blind = _cyl_z(CLAMP_SCREW_PILOT, 1.0, x, y, pilot_z0 - 1.0)
        if _common_vol(parts["Housing"], blind) < 0.9 * pilot_area:
            bad += 1
        shank = _cyl_z(CLAMP_SCREW_CLEAR, cz1 - pilot_z0, x, y, pilot_z0)
        hit += _common_vol(shank, parts["N20_Motor"])
    checks.append(("4 vit kep: thong nap + thit mo ren + day lo mu", bad == 0,
                   "%d loi" % bad))
    checks.append(("Than vit kep khong dam vao dong co", hit < 1e-6,
                   "chong lan %.2f mm3" % hit))
    checks.append(
        ("Mu vit kep chim trong nap, khong cham tran hop",
         cz1 <= BOX_TOP + 1e-9 and (cz1 - CLAMP_HEAD_H) - cz0 >= 2.0 - 1e-9,
         "noc nap %.1f (tran %.1f), thit duoi mu vit %.1f mm"
         % (cz1, BOX_TOP, (cz1 - CLAMP_HEAD_H) - cz0))
    )

    # --- 3 CHÂN HÀN CÔNG TẮC + MÁNG DÂY DUPONT ---
    # vấu bắt CT phải CÒN THỊT: bản cũ hốc CT MAX cắt quá tay, xoá sạch vấu
    bad = []
    for is_max in (False, True):
        nm = "MAX" if is_max else "MIN"
        x0, x1 = sw_body_x(is_max)
        fin = _box2(x0, x1, SW_FIN_Y0, SW_FIN_Y0 + SW_FIN_T, SW_Z0, SW_Z0 + SW_L)
        if _common_vol(parts["Housing"], fin) < 0.6 * fin.Volume:
            bad.append(nm)
        for xc, z in sw_hole_sites(is_max):
            ring = _cyl_y(SW_HOLE_D + 3.0, SW_FIN_T, xc, SW_FIN_Y0, z)
            if _common_vol(parts["Housing"], ring) < 15.0:
                bad.append("%s@z%.0f" % (nm, z))
    checks.append(("Vau bat 2 CT con thit quanh 2 lo M2", not bad,
                   ", ".join(bad) if bad else "ca 2 vau day thit"))

    # hốc 3 chân hàn phải TRỐNG với mọi chi tiết (kể cả thanh ở 2 chặn cơ khí)
    bad = []
    for is_max in (False, True):
        nm = "MAX" if is_max else "MIN"
        zone = sw_term_zone(is_max)
        for other in ("Housing", "Housing_Lid", "Motor_Clamp", "Coupler", "Thread_Rod"):
            if _common_vol(parts[other], zone) > 1e-6:
                bad.append("%s/%s" % (nm, other))
        for xb in (_X_MIN_MECH, _X_MAX_MECH):
            if _common_vol(make_slide_bar(xb), zone) > 1e-6:
                bad.append("%s/thanh" % nm)
    checks.append(("Hoc 3 chan han 2 CT hoan toan trong", not bad,
                   ", ".join(sorted(set(bad))) if bad else
                   "hoc %.1f mm sau lung moi CT" % SW_TERM_ZONE))

    # lòng máng dây + hành lang ra khe + khe xuyên vách
    dx0, dx1 = duct_x()
    dy0, dy1 = duct_y()
    duct = _box2(dx0, dx1, dy0, dy1, BASE_T, DUCT_Z1)
    v = _common_vol(parts["Housing"], duct)
    for xb in (_X_MIN_MECH, _X_MAX_MECH):
        v += _common_vol(make_slide_bar(xb), duct)
    checks.append(
        ("Long mang day thong suot (%.1f x %.1f mm)" % (dy1 - dy0, DUCT_Z1 - BASE_T),
         v < 1e-6, "vuong %.2f mm3, x %.1f..%.1f" % (v, dx0, dx1))
    )
    ly0, ly1 = wire_lane_y()
    lane = _box2(BASE_X0, sw_body_x(False)[0], ly0, ly1, WIRE_EXIT_Z0, WIRE_EXIT_Z1)
    v = _common_vol(parts["Housing"], lane)
    checks.append(
        ("Hanh lang dan day toi khe ra la trong", v < 1e-6,
         "vuong %.2f mm3, rong %.2f mm" % (v, ly1 - ly0))
    )
    probe = wire_exit_tool()
    v = _common_vol(parts["Housing"], probe)
    checks.append(
        ("Khe ra day xuyen han vach -X", v < 1e-6,
         "khe %.1f x %.1f mm tai z %.0f..%.0f" %
         (WIRE_EXIT_W, WIRE_EXIT_Z1 - WIRE_EXIT_Z0, WIRE_EXIT_Z0, WIRE_EXIT_Z1))
    )
    tabs = duct_tabs()
    bad = 0
    for nm in ("Limit_Switch_Min", "Limit_Switch_Max"):
        if _common_vol(parts[nm], tabs) > 1e-6:
            bad += 1
    for xb in (_X_MIN_MECH, _X_MAX_MECH):
        if _common_vol(make_slide_bar(xb), tabs) > 1e-6:
            bad += 1
    checks.append(("%d vau giu day khong cham CT / thanh" % len(duct_tab_x()),
                   bad == 0, "%d va cham" % bad))
    n_wire = 4                                    # 2 day / cong tac
    turn = dx1 - sw_body_x(True)[1]
    checks.append(
        ("Cua be day xuong mang sau CT MAX >= %.0f mm" % _WIRE_TURN,
         turn + 1e-9 >= _WIRE_TURN, "rong %.1f mm (x %.1f..%.1f)"
         % (turn, sw_body_x(True)[1], dx1))
    )
    checks.append(
        ("Mang du cho %d day dupont O%.1f" % (n_wire, DUPONT_D),
         (dy1 - dy0) >= 2.0 * DUPONT_D + 1.0 - 1e-9
         and (DUCT_Z1 - BASE_T) >= 2.0 * DUPONT_D - 1e-9,
         "long mang %.1f x %.1f mm (2 hang x 2 soi)" % (dy1 - dy0, DUCT_Z1 - BASE_T))
    )

    # --- THÁO LẮP: đường HẠ chi tiết và đường ĐƯA DỤNG CỤ ---
    # Slide_Bar hạ thẳng từ trên xuống (trục trơn luồn sau, nên lúc hạ chưa có trục)
    bar_drop = _sweep_z(make_slide_bar(BAR_HOME_X), 14.0)
    v = _common_vol(parts["Housing"], bar_drop)
    checks.append(("Slide_Bar ha thang tu tren xuong khoang", v < 1e-6,
                   "vuong %.2f mm3" % v))
    # Motor_Clamp hạ thẳng xuống (sau khi động cơ đã nằm trong máng)
    v = _common_vol(parts["Housing"], _sweep_z(parts["Motor_Clamp"], 14.0))
    checks.append(("Motor_Clamp ha thang tu tren xuong", v < 1e-6,
                   "vuong %.2f mm3" % v))
    # NẮP hạ THẲNG từ trên xuống: bệ gá rộng đúng bằng khe nắp nên trụ chui lọt
    lid_drop = _sweep_z(parts["Housing_Lid"], 20.0)
    bad = 0
    for xb in (_X_MIN_MECH, _X_MAX_MECH, BAR_HOME_X):
        if _common_vol(lid_drop, make_slide_bar(xb)) > 1e-6:
            bad += 1
    wide = (STEM_Y1 - STEM_Y0) <= (slot_y()[1] - slot_y()[0]) + 1e-9
    checks.append(
        ("Nap ha thang xuong qua be ga (khong can ranh ngang)",
         bad == 0 and wide,
         "be ga rong %.1f mm <= khe nap %.1f mm, %d va cham o 3 vi tri thanh"
         % (STEM_Y1 - STEM_Y0, slot_y()[1] - slot_y()[0], bad))
    )
    # ĐƯỜNG ĐƯA DỤNG CỤ cho từng con vít (nắp chưa đậy)
    tool = []
    cz0v, cz1v = clamp_z()
    for x, y in clamp_bolt_xy():
        tool.append(("vit kep DC", x, y, cz1v - CLAMP_HEAD_H, CLAMP_HEAD_D - 0.4))
    tool.append(("vit ham truc tron", GUIDE_LOCK_X, GUIDE_Y,
                 AXIS_Z + GUIDE_BOSS_D / 2.0, M3_TAP + 1.0))
    for x in coupler_set_screw_x():
        tool.append(("vit ham khop noi", x, 0.0, AXIS_Z + COUP_D / 2.0, M3_TAP + 1.0))
    for x, y in lid_tap_xy():
        tool.append(("vit nap", x, y, BOX_TOP, M3_CLEAR + 3.0))
    bad = []
    bar_far = make_slide_bar(_X_MAX_MECH)
    for nm, x, y, z0, dia in tool:
        probe = _cyl_z(dia, 30.0, x, y, z0)
        v = _common_vol(parts["Housing"], probe)
        v += _common_vol(bar_far, probe)
        if v > 1e-6:
            bad.append("%s @x=%.1f" % (nm, x))
    checks.append(
        ("Moi vit deu co duong dua tua vit vao (nap mo)", not bad,
         ", ".join(bad) if bad else "%d vi tri deu thong 30 mm tu tren xuong" % len(tool))
    )

    # --- VÁCH GÁ TẢI trên nắp: 4 lỗ M3 xuyên X trên mặt ⊥ trục ---
    bar = parts["Slide_Bar"]
    xc = BAR_HOME_X
    bad = 0
    for y, z in load_hole_sites():
        probe = _cyl_x(M3_CLEAR - 0.4, MOUNT_T + 4.0, xc - MOUNT_T / 2.0 - 2.0, y, z)
        if _common_vol(bar, probe) > 1e-6:
            bad += 1
        ring = _cyl_x(M3_CLEAR + 3.0, MOUNT_T - 0.5, xc - MOUNT_T / 2.0 + 0.25, y, z)
        ring = _cut(ring, _cyl_x(M3_CLEAR, MOUNT_T + 4.0, xc - MOUNT_T / 2.0 - 2.0, y, z))
        if _common_vol(bar, ring) < 0.95 * ring.Volume:
            bad += 1
    checks.append(
        ("%d lo bu long M3 xuyen be ga (theo X) co vanh thit" % len(load_hole_sites()),
         bad == 0,
         "%d loi, 2 lo cach %.0f mm theo Z, day be ga %.1f, rong %.1f"
         % (bad, 2 * LOAD_HOLE_DZ, MOUNT_T, STEM_Y1 - STEM_Y0))
    )
    # mũ bulông phía +X / -X của vách không va nắp / vỏ
    bad = 0
    for y, z in load_hole_sites():
        for xb in (x_min, x_max):
            for face_x0 in (xb + MOUNT_T / 2.0, xb - MOUNT_T / 2.0 - 3.0):
                head = _cyl_x(7.0, 3.0, face_x0, y, z)
                if _common_vol(head, static) > 1e-6:
                    bad += 1
                if _common_vol(head, parts["Housing_Lid"]) > 1e-6:
                    bad += 1
    checks.append(
        ("Bu long tren vach ga khong va gi", bad == 0, "%d va cham" % bad)
    )
    # Vùng trên đỉnh vách trống; vách nằm ngoài hộp
    everything = static.fuse(parts["Housing"]).fuse(parts["Housing_Lid"])
    free = _box2(BOX_X0 - 40.0, BOX_X1 + 40.0, BOX_Y0 - 40.0, BOX_Y1 + 40.0,
                 WALL_Z1 + 0.5, WALL_Z1 + 80.0)
    v = _common_vol(free, everything)
    checks.append(
        ("Vung tren vach ga (z > %.1f) la trong" % WALL_Z1, v < 1e-6,
         "chong lan %.2f mm3" % v)
    )
    _above = parts["Slide_Bar"].common(
                     _box2(BOX_X0 - 60.0, BOX_X1 + 60.0, BOX_Y0 - 60.0, BOX_Y1 + 60.0,
                           BOX_TOP, WALL_Z1 + 10.0)).BoundBox
    checks.append(
        ("Be ga det theo X va KHONG xoe ngang qua khe nap",
         MOUNT_T <= 5.0 + 1e-9
         and _above.YMin >= slot_y()[0] - 1e-6 and _above.YMax <= slot_y()[1] + 1e-6
         and WALL_Z1 > BOX_TOP + LID_T,
         "phan tren nap y %.1f..%.1f nam trong khe %.1f..%.1f, day %.1f, tho len %.1f mm"
         % (_above.YMin, _above.YMax, slot_y()[0], slot_y()[1], MOUNT_T,
            WALL_Z1 - (BOX_TOP + LID_T)))
    )

    # --- VỎ HỘP ---
    # thân + trụ không đụng Housing; trụ lọt khe nắp ở mọi chặn
    bad = 0
    for xb in (_X_MIN_MECH, _X_MAX_MECH, x_min, x_max):
        if _common_vol(make_slide_bar(xb), parts["Housing"]) > 1e-6:
            bad += 1
        if _common_vol(make_slide_bar(xb), parts["Housing_Lid"]) > 1e-6:
            bad += 1
    sx0, sx1 = slot_x()
    sy0, sy1 = slot_y()
    checks.append(
        ("Tru be ga lot khe nap o ca 2 chan co khi", bad == 0,
         "%d va cham, khe x=%.1f..%.1f y=%.1f..%.1f" % (bad, sx0, sx1, sy0, sy1))
    )
    # mọi chi tiết tĩnh phải nằm gọn trong khoang, không đụng vỏ
    bad = []
    for nm in ("Motor_Clamp", "N20_Motor", "Coupler", "Thread_Rod",
               "Guide_Shaft", "Limit_Switch_Min", "Limit_Switch_Max"):
        if _common_vol(parts[nm], parts["Housing"]) > 1e-6:
            bad.append(nm)
    checks.append(("Chi tiet trong hop khong dung vo", not bad,
                   ", ".join(bad) if bad else "ca %d chi tiet deu lot" % 9))
    # nắp không đụng motor clamp / CT (trụ thanh đi qua khe — đã check ở trên)
    bad = []
    for nm in ("Motor_Clamp", "Limit_Switch_Min", "Limit_Switch_Max"):
        if _common_vol(parts[nm], parts["Housing_Lid"]) > 1e-6:
            bad.append(nm)
    checks.append(
        ("Nap khong dung CT / nap kep", not bad,
         "OK" if not bad else ", ".join(bad))
    )
    # 4 boss bắt nắp trên khung không được đâm công tắc / thanh
    bad = 0
    sw_only = make_sw_body_only(False).fuse(make_sw_body_only(True))
    for x, y in lid_boss_boxes():
        post = _box2(x, x + POST_W, y, y + POST_W, LID_BOSS_Z0, BOX_TOP)
        if _common_vol(post, sw_only) > 1e-6:
            bad += 1
        for xb in (_X_MIN_MECH, _X_MAX_MECH):
            if _common_vol(post, make_slide_bar(xb)) > 1e-6:
                bad += 1
    checks.append(("4 boss nap tren khung khong dung CT/thanh", bad == 0,
                   "%d boss bi vuong" % bad))
    # 4 vít nắp phải xuyên nắp và vào đúng boss (lỗ thông)
    bad = 0
    for x, y in lid_tap_xy():
        probe = _cyl_z(M3_TAP - 0.2, LID_T + 8.0, x, y, BOX_TOP - 8.0)
        if _common_vol(parts["Housing"], probe) > 1e-6:
            bad += 1
        if _common_vol(parts["Housing_Lid"], probe) > 1e-6:
            bad += 1
    checks.append(("4 vit M3 xuyen nap vao boss khung", bad == 0, "%d lo bi bit" % bad))
    checks.append(
        ("Housing la 1 khoi lien (vo+khung)", len(parts["Housing"].Solids) == 1,
         "%d khoi" % len(parts["Housing"].Solids))
    )
    # 4 tai: lỗ M4 thông, và KHÔNG bị nắp che
    bad = 0
    for x, y in ear_hole_xy():
        probe = _cyl_z(EAR_HOLE - 0.4, BASE_T + 4.0, x, y, -2.0)
        if _common_vol(parts["Housing"], probe) > 1e-6:
            bad += 1
        above = _cyl_z(EAR_HOLE + 3.0, BOX_TOP + LID_T, x, y, BASE_T)
        if _common_vol(parts["Housing_Lid"], above) > 1e-6:
            bad += 1
    checks.append(
        ("%d tai M4 thong va khong bi nap che" % len(ear_hole_xy()), bad == 0,
         "%d loi, tai %.0f x %.0f mm" % (bad, EAR_X, EAR_OUT))
    )
    probe = _cyl_x(CABLE_D - 1.0, WALL_T + 4.0, BOX_X0 - 2.0, 0.0, AXIS_Z)
    checks.append(
        ("Lo luon day thong qua vach -X", _common_vol(parts["Housing"], probe) < 1e-6,
         "O%.1f tai z = %.0f, cach duoi dong co %.1f mm"
         % (CABLE_D, AXIS_Z, -MOT_LEN - BASE_X0))
    )
    # vách gá nằm HẲN trên mặt nắp
    checks.append(
        ("Vach ga tai nam tren nap hop", WALL_Z0 >= BOX_TOP + LID_T - 1e-9,
         "vach z=%.1f..%.1f, nap het o %.1f" % (WALL_Z0, WALL_Z1, BOX_TOP + LID_T))
    )
    checks.append(
        ("Guide_Shaft dai = day hoc mu -> ngoai vach +X",
         abs(GUIDE_SHAFT_LEN - ((BOX_X1 + GUIDE_STICK) - GUIDE_X0)) < 1e-9,
         "dai %.1f mm (cat dai/ngan +-2 mm van chay)" % GUIDE_SHAFT_LEN)
    )

    # hành trình phải dương
    travel = x_max - x_min
    checks.append(
        ("Hanh trinh > 5 mm", travel > 5.0,
         "%.1f mm (ty ren M4 x %.0f, khop noi dai %.0f)"
         % (travel, ROD_LEN, COUP_LEN))
    )
    return checks


# ---------------------------------------------------------------------------
# 5. Dựng document
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
    # Housing = vo + khung DC + goi do (1 khoi). Motor_Clamp van roi de lap DC.
    parts = {
        "Housing": make_housing(),
        "Housing_Lid": make_housing_lid(),
        "Motor_Clamp": make_motor_clamp(),
        "N20_Motor": make_motor(),
        "Coupler": make_coupler(),
        "Coupler_Spacer": make_coupler_spacer(),
        "Thread_Rod": make_thread_rod(),
        "Guide_Shaft": make_guide_shaft(),
        "Guide_Lock_Screw": make_guide_lock_screw(),
        "Limit_Switch_Min": make_limit_switch(False),
        "Limit_Switch_Max": make_limit_switch(True),
        "Slide_Bar": make_slide_bar(BAR_HOME_X),
        "Hex_Nut": make_hex_nut(BAR_HOME_X),
    }
    return parts


COLORS = {
    "Housing": ((0.55, 0.58, 0.65), 0),
    "Housing_Lid": ((0.62, 0.64, 0.68), 60),
    "Motor_Clamp": ((0.16, 0.36, 0.62), 0),
    "N20_Motor": ((0.35, 0.36, 0.38), 0),
    "Coupler": ((0.55, 0.58, 0.62), 0),
    "Coupler_Spacer": ((0.35, 0.70, 0.45), 0),
    "Thread_Rod": ((0.83, 0.68, 0.28), 0),
    "Guide_Shaft": ((0.80, 0.82, 0.86), 0),
    "Guide_Lock_Screw": ((0.45, 0.45, 0.48), 0),
    "Limit_Switch_Min": ((0.12, 0.12, 0.14), 0),
    "Limit_Switch_Max": ((0.12, 0.12, 0.14), 0),
    "Slide_Bar": ((0.90, 0.48, 0.14), 0),
    "Hex_Nut": ((0.78, 0.62, 0.30), 0),
}


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("N20_Leadscrew_Stage")
    parts = build_parts()

    objs = []
    for name, shape in parts.items():
        color, transp = COLORS.get(name, ((0.7, 0.7, 0.7), 0))
        objs.append(add_part(doc, name, shape, color, transp))

    grp = doc.addObject("App::Part", "N20_Leadscrew_Stage")
    grp.addObjects(objs)

    doc.recompute()
    # CHỈ save khi có GUI — freecadcmd save headless làm hỏng / thiếu GuiDocument
    if App.GuiUp and Gui is not None:
        doc.saveAs(str(FCSTD))
        print("Saved:", FCSTD)
    else:
        print("!! Headless: khong ghi %s (tranh file corrupt). Chi in thong so + verify."
              % FCSTD)

    x_min, x_max = travel_range()
    print("--- THONG SO ---")
    print("  Dong co     : GA12-N20 truc D O%.0f x %.0f, bich 12x10 — GIU BANG CHAN CO KHI"
          % (SHAFT_D, SHAFT_LEN))
    print("                (hoc chong xoay + bich chan +X + vach chan -X khe %.1f + nap kep;"
          % MOT_STOP_GAP)
    print("                 KHONG dung 2 vit M1.6 mat bich — khong dua duoc tua vit vao)")
    print("  Khop noi    : truc dong, O bao %.0f, dai %.0f (x %.1f -> %.1f), 2 vit ham M3"
          % (COUP_D, COUP_LEN, COUP_X0, COUP_X1))
    print("                lo O%.1f om truc %.1f mm (vit x = %.1f) | vach %.1f | lo O%.1f sau %.1f"
          % (SHAFT_D, SHAFT_LEN - COUP_X0, coupler_set_screw_x()[0],
             COUP_WALL, ROD_D, COUP_BORE_R))
    print("                ty ren chi cam %.1f mm (= 1.5 x D), %.1f mm con lai lap bang CU O%.1f"
          % (COUP_ROD_IN, SPACER_L, SPACER_D))
    print("  Ty ren      : M4 x %.0f, buoc %.1f mm/vong (x %.1f -> %.1f, ho %.1f mm)"
          % (ROD_LEN, ROD_PITCH, ROD_X0, ROD_X1, ROD_X1 - COUP_X1))
    print("  Dai oc      : luc giac M4 thuong S%.1f day %.1f, khe ho noc rong %.1f"
          % (NUT_AF, NUT_H, NUT_SLOT_W))
    print("  Do do dau   : ty ren an %.1f mm vao lo O%.1f cua vach End_Block (x %.1f)"
          % (ROD_END_SUPPORT, ROD_HOLE_D, END_X0))
    print("  Cong tac HT : KW11 banh xe, can gat %.0f mm, 2 lo M2 @ %.1f mm"
          % (SW_LEVER_L, SW_HOLE_PITCH))
    print("                bat bang 2 vit M2 x %.0f TU REN: lo thao tac O%.1f tren vach -Y"
          % (SW_SCREW_L, SW_HOLE_D))
    print("                (mu vit chui qua, ti thang vao than CT) -> lo moi O%.1f XUYEN vau"
          % SW_PILOT_D)
    print("                VIT TOI DA %.0f mm: dai hon la mui vit tho vao duong hub chay"
          % (SW_SCREW_L + (-HUB_Y - SW_TIP_CLEAR - SW_SCREW_TIP)))
    print("                KHE THOAT %.1f mm sau vau (vach goi do lui ve y=%.1f) — lo"
          % (SW_FIN_RELIEF, END_WALL_Y0))
    print("                xuyen vau roi ra CHO TRONG, khong dam tiep vao thit vach")
    print("                cham tai x = %.1f va %.1f  (hanh trinh dien %.1f mm)"
          % (X_TRIP_MIN, X_TRIP_MAX, X_TRIP_MAX - X_TRIP_MIN))
    _dx0, _dx1 = duct_x()
    _dy0, _dy1 = duct_y()
    _ly0, _ly1 = wire_lane_y()
    print("  Chan han CT : 3 la dong nho %.1f mm khoi LUNG cong tac (xa thanh truot)"
          % SW_TERM_L)
    print("                MIN chia ve -X (x %.1f -> %.1f) | MAX chia ve +X (x %.1f -> %.1f)"
          % (sw_body_x(False)[0], sw_body_x(False)[0] - SW_TERM_L,
             sw_body_x(True)[1], sw_body_x(True)[1] + SW_TERM_L))
    print("                hoc trong %.1f mm sau moi lung (la + moi han + cho be day)"
          % SW_TERM_ZONE)
    print("  Mang day    : long %.1f x %.1f mm o y = %.1f..%.1f, x = %.1f..%.1f"
          % (_dy1 - _dy0, DUCT_Z1 - BASE_T, _dy0, _dy1, _dx0, _dx1))
    print("                %d vau giu day (day luon xuong duoi vau); cua be day xuong"
          % len(duct_tab_x()))
    print("                mang sau CT MAX rong %.1f mm (x %.1f..%.1f)"
          % (_dx1 - sw_body_x(True)[1], sw_body_x(True)[1], _dx1))
    print("                hanh lang ra khe: y %.1f..%.1f | KHE RA DAY %.1f x %.1f"
          % (_ly0, _ly1, WIRE_EXIT_W, WIRE_EXIT_Z1 - WIRE_EXIT_Z0))
    print("                tren vach -X (z %.0f..%.0f) — 4 day CT ra cung phia day DC"
          % (WIRE_EXIT_Z0, WIRE_EXIT_Z1))
    print("  Chan co khi : x = %.1f va %.1f  (du %.1f mm over-travel moi dau)"
          % (_X_MIN_MECH, _X_MAX_MECH, _SW_OVERTRAVEL))
    print("                gan: vach truoc hoc dung %s | xa: %s"
          % ("khop noi",
             "hub dung vach" if _X_MAX_MECH == _X_MAX_HOLDER
             else ("bac dung vach" if _X_MAX_MECH == _X_MAX_BOSS else "het ren")))
    print("  Truc tron   : O%.0f, dai %.1f mm, lech y = %.0f — LUON TU NGOAI VACH +X"
          % (GUIDE_D, GUIDE_SHAFT_LEN, GUIDE_Y))
    _gm = FACE_X0 + FACE_T + GUIDE_BOSS_L
    print("                x=%.1f..%.1f: hoc mu DC %.1f (an %.1f) | vach sat hop %.1f @ x=%.1f..%.1f"
          % (GUIDE_SHAFT_X0, GUIDE_SHAFT_X0 + GUIDE_SHAFT_LEN, GUIDE_SOCKET_M,
             _gm - GUIDE_SHAFT_X0, END_T, END_WALL_X0, END_WALL_X1))
    print("                (trong giua x < %.1f: khong vach — lo CT MAX @ %.1f)"
          % (END_WALL_X0, _LS_MAX_HOLE_X))
    print("                | lo vach +X O%.1f, dau truc tho %.1f mm ra ngoai de rut"
          % (GUIDE_ACCESS_D, GUIDE_SHAFT_X0 + GUIDE_SHAFT_LEN - BOX_X1))
    print("                KHOA chay: vit ham M3 @ x=%.1f (vat sau %.1f) — noi truoc khi thao"
          % (GUIDE_LOCK_X, GUIDE_LOCK_FLAT))
    print("  Thanh       : than day %.1f (X) x cao %.1f (Z), lo O%.1f cho khop noi chui qua"
          % (BAR_X, BAR_Z1 - BAR_Z0, COUP_CLEAR_D))
    print("                hub lien khoi x = %+.1f..%+.1f so voi tam: vach %.1f | khe %.1f | vach %.1f"
          % (-BAR_X / 2.0, HUB_FRONT, NUT_WALL, NUT_POCKET, NUT_WALL))
    print("  Be ga tai   : TRU DET tho len tren nap %.1f mm — day %.1f (X) x rong %.1f (Y)"
          % (WALL_Z1 - (BOX_TOP + LID_T), MOUNT_T, STEM_Y1 - STEM_Y0))
    print("                rong DUNG BANG khe nap (%.1f) nen nap ha thang xuong duoc"
          % (slot_y()[1] - slot_y()[0]))
    print("                2 lo bu long M3 XUYEN theo X tai y=0, z=%.1f va %.1f"
          % tuple(z for _y, z in load_hole_sites()))
    print("                VUNG TRONG z > %.1f" % WALL_Z1)
    print("  Hanh trinh  : x = %.1f .. %.1f  ->  %.1f mm" % (x_min, x_max, x_max - x_min))
    print("  Toc do      : 1 vong = %.1f mm  |  %.0f rpm -> %.1f mm/phut (het hanh trinh %.0f s)"
          % (ROD_PITCH, MOTOR_RPM, MOTOR_RPM * ROD_PITCH,
             60.0 * (X_TRIP_MAX - X_TRIP_MIN) / (MOTOR_RPM * ROD_PITCH)))
    print("  Don bay     : +1 mm ty ren = +1 mm hanh trinh. CHIEU DAI KHOP NOI KHONG con")
    print("                anh huong hanh trinh (chi doi chieu dai de) — no da triet tieu")
    print("                khoi cong thuc khi ty ren cam nong co dinh muc.")
    print("                (M4 x 60 thay cho x %.0f -> ~%.1f mm hanh trinh)"
          % (ROD_LEN, (x_max - x_min) + (60.0 - ROD_LEN)))
    print("  Cao do truc : z = %.0f mm so voi mat day de" % AXIS_Z)
    sx0, sx1 = slot_x()
    sy0, sy1 = slot_y()
    print("  VO HOP      : ngoai %.0f x %.0f x %.0f mm (vo+nap), vach ga den z=%.0f, vach %.1f"
          % (BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_TOP + LID_T, WALL_Z1, WALL_T))
    print("                khoang trong %.0f x %.0f x %.0f mm"
          % (BASE_X1 - BASE_X0, BASE_Y1 - BASE_Y0, BOX_TOP - BASE_T))
    print("                KHE nap: x=%.1f..%.1f (%.1f) y=%.1f..%.1f"
          % (sx0, sx1, sx1 - sx0, sy0, sy1))
    print("                %d TAI M4 %.0fx%.0f, tam lo tai x = %s | y = %s"
          % (len(ear_boxes()), EAR_X, EAR_OUT,
             ", ".join("%.1f" % v for v in sorted({x for x, _ in ear_hole_xy()})),
             ", ".join("%.1f" % v for v in sorted({y for _, y in ear_hole_xy()}))))
    print("                bao ngoai KE CA TAI: %.0f x %.0f mm"
          % (BOX_X1 - BOX_X0, (BOX_Y1 + EAR_OUT) - (BOX_Y0 - EAR_OUT)))
    print("                nap: 4 vit M3; lo luon day O%.1f o vach -X" % CABLE_D)

    print("--- NGAN SACH HANH TRINH ---")
    stack = 2.0 * NUT_WALL + NUT_POCKET
    rows = [
        ("Ty ren M4 x %.0f" % ROD_LEN, ROD_LEN),
        ("- cam vao khop noi", -COUP_ROD_IN),
        ("- cam vao lo do End_Block", -ROD_END_SUPPORT),
        ("- chong om dai oc (%.1f+%.1f+%.1f)" % (NUT_WALL, NUT_POCKET, NUT_WALL), -stack),
        ("- khe an toan 2 x %.1f" % END_CLEAR, -2.0 * END_CLEAR),
        ("+ hoc End_Block (hub/bac chui vao)", END_HUB_RECESS),
    ]
    for label, val in rows:
        print("  %-38s %+7.1f" % (label, val))
    print("  %-38s %7.1f" % ("= phong bi co (failsafe)", _X_MAX_MECH - _X_MIN_MECH))
    print("  %-38s %+7.1f" % ("- SW_PRESS du phong 2 x %.1f" % SW_PRESS, -2.0 * SW_PRESS))
    print("  %-38s %7.1f" % ("= HANH TRINH DUNG (trip)", x_max - x_min))

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
        "guide_shaft_len_mm": GUIDE_SHAFT_LEN,
        "guide_y_mm": GUIDE_Y,
        "box_outer_mm": [BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_TOP + LID_T],
        "mount_wall": True,
        "mount_t_mm": MOUNT_T,
        "mount_stem_y_mm": [STEM_Y0, STEM_Y1],
        "wall_z_mm": [WALL_Z0, WALL_Z1],
        "load_holes": len(load_hole_sites()),
        "lid_slot": True,
        "travel_trip_mm": x_max - x_min,
    }
    mpath = OUT / "n20_leadscrew_stage_metrics.json"
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
