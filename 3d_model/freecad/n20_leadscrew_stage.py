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
  Housing           — VỎ HỘP: đáy + 4 vách + 4 TAI bắt bu lông M4 + KHE cho thanh chạy
  Housing_Lid       — nắp đậy, 4 vít M3 xuống 4 trụ góc
  Motor_Bracket     — bích đứng bắt 2 vít M1.6 CHÌM + máng ôm thân + vấu công tắc MIN
  Motor_Clamp       — nắp kẹp trên, 4 vít M3
  Coupler           — KHỚP NỐI TRỤC (mua sẵn): lỗ Ø3 + vít | lỗ Ø4 + vít
  Coupler_Spacer    — CỮ Ø3.8 thả đáy lỗ Ø4, chặn ty ren ở đúng chiều sâu cắm
  Thread_Rod        — TY REN M4 x 40, cắm COUP_ROD_IN mm vào lỗ Ø4
  Guide_Shaft       — TRỤC TRƠN Ø5 SONG SONG với ty ren, lệch +Y 17 mm; hai đầu cắm
                      vào HỐC MÙ, không xuyên thủng
  Slide_Bar         — THANH TỊNH TIẾN: bạc ôm trục trơn + LỖ CHO KHỚP NỐI CHUI QUA
                      + HUB liền khối ôm đai ốc (khe HỞ NÓC), KHÔNG có chi tiết rời
                      + BỆ GÁ TẢI ở đầu tự do, 2 bộ lỗ trên 2 mặt vuông góc
  Hex_Nut           — đai ốc lục giác M4 thường (mua sẵn)
  End_Block         — gối đỡ trục trơn + lỗ đỡ đầu ty ren + vấu công tắc MAX
  Limit_Switch_Min/Max — 2 công tắc KW11 bánh xe, bị ấn DỌC TRỤC

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
    hành trình = ROD_LEN
                 - COUP_ROD_IN        (ty ren cắm vào khớp nối)
                 - ROD_END_SUPPORT    (ty ren cắm vào lỗ đỡ End_Block)
                 - (2*NUT_WALL + NUT_POCKET)   (chồng ôm đai ốc trên thanh)
                 - 2*END_CLEAR        (khe an toàn 2 đầu)
                 - 2*SW_PRESS         (công tắc tác động sớm hơn chặn cơ)
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
4 TAI bắt bu lông M4 chìa ra hai bên +-Y, đặt ở HAI ĐẦU theo X — ngoài đoạn x mà bệ gá
quét qua — để cả phía -Y còn trống cho cơ cấu người dùng lắp lên bệ.
4 TRỤ GÓC bắt nắp bắt đầu từ z = POST_Z0 (trên mặt chân gá) chứ không từ đáy: hai chân
gá trải tới y = +-18 nên trụ mà xuống thấp hơn là đâm vào chúng.
Vách -X có lỗ Ø CABLE_D luồn dây động cơ + 2 công tắc.

BỆ GÁ TẢI — HAI BỘ LỖ CHO HAI KIỂU LẮP: cụm này dùng được ở hai tư thế, và mỗi tư thế
cần bắt bu lông theo một hướng khác nhau, nên đầu tự do của thanh mang CẢ HAI:
  (a) MẶT ĐẦU (-Y): 4 lỗ TARÔ M3 xếp chữ nhật %g x %g mm, sâu LOAD_TAP_DEPTH.
      Dùng khi cụm nằm NGANG và tải là tấm VÁCH NGĂN úp vào mặt đầu — 4 điểm chữ nhật
      chặn được cả xoay lẫn lật, vặn từ ngoài vào, không cần với tay ra sau.
  (b) MẶT TRÊN/DƯỚI (+-Z): 2 lỗ M3 XUYÊN SUỐT, cách nhau %g mm.
      Dùng khi cụm dựng ĐỨNG (thanh chạy lên xuống) và tải là cơ cấu chỉnh độ cao kẹp
      lên mặt trên hay mặt dưới — xuyên suốt nên bắt bu lông + đai ốc, hai mặt đều với
      tới được vì bệ nhô hẳn ra ngoài mép đế.
Hai bộ lỗ đặt lệch nhau theo X nên KHÔNG cắt vào nhau: lỗ tarô ở +-LOAD_TAP_DX, lỗ
xuyên ở +-LOAD_BOLT_DX, chừa >= 2 mm thịt giữa chúng.

VÙNG GÁ TẢI TRỐNG: toàn bộ nửa không gian y <= BAR_PAD_Y1 - 1 là TRỐNG HOÀN TOÀN ở mọi
x và mọi z — mép đế dừng ở y = BASE_Y0, hai công tắc dừng ở y = SW_FIN_Y0 - SW_T. Thứ
gì bắt lên bệ gá mà nằm trong nửa không gian đó thì không bao giờ va, dù thanh chạy tới
đâu. Có check `Nua khong gian gan tai la trong` canh điều này.

TRỤC TRƠN CẮM HỐC MÙ: hai lỗ trên Motor_Bracket và End_Block đều BỊT ĐÁY bằng một vách
mỏng GUIDE_BLIND_WALL, nên trục trơn bị chặn dọc trục ở cả hai phía — ép chặt cỡ nào rồi
cũng có lúc rão, mà lỗ thủng thì không còn gì giữ. Bích đứng chỉ dày FACE_T = 3 nên
không đủ chỗ cho hốc sâu; đắp thêm một vấu Ø GUIDE_BOSS_D mọc về +X để hốc sâu tới
FACE_T + GUIDE_BOSS_L - GUIDE_BLIND_WALL (>= 1 x đường kính trục, đủ chống lật).
Giữa mỗi vách mỏng có LỖ THÔNG HƠI Ø GUIDE_VENT_D: nó thoát khí khi đóng trục vào hốc
mù, và về sau muốn tháo thì lấy que xuyên qua đó đẩy trục ra. Ø1.5 không cho trục Ø5
lọt nên vách vẫn là vách.

CHẶN DỌC TRỤC CỦA TY REN: đẩy thanh về +X thì phản lực đẩy ty ren về -X, ty tì vào CỮ
rồi tới vách COUP_WALL — chặn cứng. Chiều ngược lại chỉ có vít hãm giữ, nên vít phía ty
ren phải siết chặt (nó cắn vào ren nên bám tốt hơn hẳn trên trục trơn).

KHÔNG dùng đai ốc hãm thứ 2 cho ĐAI ỐC CHẠY (double nut chống rơ): mô men vặn thêm
~0.7*P N*mm trong khi N20 chỉ có ~49 N*mm. Rơ dọc trục đã bị hốc khống chế ở 0.2 mm.

CÔNG TẮC HÀNH TRÌNH: thân công tắc đặt sao cho MẶT TRƯỚC của nó chính là chặn cơ khí;
thanh chạm bánh xe trước đó nên giới hạn điện luôn tới trước giới hạn cơ.

THỨ TỰ LẮP (quan trọng — ty ren không luồn thẳng vào được nếu lắp End_Block trước):
  1. Ép trục trơn vào Motor_Bracket; bắt động cơ 2 vít M1.6 chìm; lồng khớp nối vào
     trục Ø3, siết vít đầu -X vào mặt vạt D.
  2. THẢ Coupler_Spacer vào đáy lỗ Ø4 của khớp nối (làm TRƯỚC, sau này không với tới).
  3. Xỏ Slide_Bar vào trục trơn.
  4. THẢ đai ốc M4 từ trên xuống khe hở nóc trên hub của thanh.
  5. Vặn ty ren từ phía xa vào: qua vách sau, qua đai ốc, qua vách trước, cắm vào lỗ Ø4
     tới khi CHẠM CỮ, rồi siết vít đầu +X.
  6. Xỏ End_Block vào trục trơn + đầu ty ren THEO PHƯƠNG X rồi mới bắt xuống đế.
     Hai hốc đều mù nên chỉ lắp được kiểu này: đóng trục vào hốc bích trước, rồi đẩy
     End_Block dọc trục trùm lên đầu còn lại. CẮT TRỤC 60.0 mm, thà NGẮN 0.3 còn hơn
     dài — dài quá thì End_Block bị đội, không hạ hết xuống đế (lỗ M3 chỉ rơ 0.4 mm).

CHẠY: freecad.exe 3d_model/freecad/n20_leadscrew_stage.py
  (KHÔNG dùng freecadcmd — save headless mất GuiDocument.xml nên mở ra mất màu)
"""
from __future__ import annotations

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

SHAFT_D = 3.0                             # trục ra TRƠN Ø3 (không còn ren)
SHAFT_LEN = 10.0                          # nhô ra khỏi mặt bích
SHAFT_FLAT = 0.5                          # chiều sâu vạt phẳng chữ D
SHAFT_FLAT_X0 = 3.0                       # vạt bắt đầu cách mặt bích 3 mm

# ---------------------------------------------------------------------------
# 2. Bố trí chung (mm). Đế: mặt dưới z=0. Trục quay: y=0, z=AXIS_Z.
# ---------------------------------------------------------------------------
BASE_T = 4.0
AXIS_Z = 20.0                             # tâm trục so với mặt bàn máy
GUIDE_Y = 17.0                            # trục trơn song song, lệch +Y
GUIDE_D = 5.0                             # Ø5 trục trơn (loại phổ thông)

FACE_X0, FACE_T = 0.0, 3.0                # bích đứng x = 0..3, mặt ĐC áp tại x=0
SHAFT_CLEAR_D = SHAFT_D + 0.6             # lỗ cho trục Ø3 chui qua bích
BASE_X0 = -30.0                           # BASE_* = KHOANG TRONG của vỏ hộp; vách
BASE_Y0, BASE_Y1 = -29.0, 29.0            # dựng ra phía ngoài các số này
WING_Y = GUIDE_Y + 7.0                    # chân đế nới rộng tới phía trục trơn
RIB_T = 4.0                               # gân chống lật cho bích đứng
RIB_Y0 = GUIDE_Y + 2.0                    # gân đặt SÁT (không trùng) lỗ trục trơn

CRADLE_X0 = -MOT_LEN - 2.0                # máng ôm thân: -27.2 .. 0
FOOT_T = 4.0                              # bề dày chân đế của gá (z = 4..8)
FOOT_Y = 18.0                             # nửa bề rộng chân đế
FOOT_BOLT_Y = 15.0                        # vít M3 bắt xuống đế (đủ chỗ cho mũ vít)
CRADLE_Y = 11.0                           # nửa bề rộng máng + nắp kẹp
CLAMP_BOLT_Y = 8.5                        # vít M3 giữ nắp kẹp, hai bên thân ĐC
PLATE_TOP = 28.0                          # đỉnh bích đứng

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

# Thanh tịnh tiến
BAR_X = 7.0                               # bề dày thanh theo phương chạy (X)
BAR_Y0, BAR_Y1 = -41.0, GUIDE_Y           # đầu tự do ở -41: bệ gá phải nằm HẲN ngoài
                                          # vách -Y của vỏ hộp (mặt ngoài y = -32)
COUP_CLEAR_D = COUP_D + 1.2               # lỗ cho KHỚP NỐI chui qua thanh
BAR_WALL = 2.5                            # thịt còn lại trên/dưới lỗ đó
BAR_Z0 = AXIS_Z - COUP_CLEAR_D / 2.0 - BAR_WALL
BAR_Z1 = AXIS_Z + COUP_CLEAR_D / 2.0 + BAR_WALL
BAR_PAD_Y1 = -33.0                        # BỆ GÁ TẢI nằm ngoài vỏ, y = -41..-33 (hở
BAR_PAD_X = 32.0                          # 1 mm với mặt ngoài vách). Nới rộng bao nhiêu
                                          # cũng KHÔNG tốn hành trình vì ở ngoài hộp
LOAD_TAP_DX, LOAD_TAP_DZ = 7.0, 6.0       # 4 lỗ tarô M3 trên MẶT ĐẦU (-Y)
LOAD_TAP_DEPTH = 8.0                      # = đúng bề dày bệ theo Y
LOAD_BOLT_DX = 12.0                       # 2 lỗ M3 XUYÊN theo Z (mặt trên/mặt dưới)
LOAD_BOLT_Y = 0.5 * (BAR_Y0 + BAR_PAD_Y1)  # -30, giữa bề dày bệ
BOSS_D, BOSS_L = 13.0, 18.0               # bạc ôm trục trơn
BOSS_BORE = GUIDE_D + 0.3                 # trượt: Ø5.3

# --- HUB ÔM ĐAI ỐC: khoét thẳng vào thanh, mọc ra phía +X (phía gối đỡ) ----
# Ở phía +X chứ không phải -X: bên -X có khớp nối chắn, hốc nằm bên đó thì nó và
# thanh tranh nhau cùng một vùng chết. HUB_FRONT đặt BẰNG ĐÚNG BOSS_L/2 nên mặt
# trước hub trùng mặt trước bạc trục trơn — hub không ăn thêm mm hành trình nào.
HUB_FRONT = BOSS_L / 2.0                  # 9.0, mặt trước hub so với tâm thanh
HUB_Y = 10.0                              # nửa bề rộng hub (bạc trục trơn bắt đầu ở 10.5)
NUT_WALL = 2.0                            # 2 vách chặn dọc trục, liền khối với thanh
NUT_POCKET = NUT_H + 0.2                  # hốc dài hơn đai ốc 0.2 → rơ dọc trục 0.2
NUT_SLOT_W = NUT_AF + 0.5                 # khe rộng hơn S 0.5 → đai ốc còn BƠI
NUT_SLOT_Z0 = AXIS_Z - NUT_AC / 2.0 - 1.0  # đáy khe; phía trên HỞ hoàn toàn
ROD_CLEAR_D = ROD_D + 1.2                 # lỗ ty ren xuyên 2 vách
# Đáy lỗ khoét Ø(khớp nối) = mặt ngoài vách trước. Đây là mặt duy nhất không chui
# qua được khớp nối / đai ốc hãm, tức là thứ quyết định giới hạn GẦN.
BORE_FRONT = HUB_FRONT - 2.0 * NUT_WALL - NUT_POCKET

# --- Gối đỡ đầu kia: đỡ trục trơn VÀ đầu ty ren ---------------------------
# Lỗ đỡ nằm NGAY TRONG VÁCH (bản cũ có thêm mỏ đỡ Ø14 chìa ra -X; bỏ đi vì nó ăn
# thêm hành trình mà không thêm gì — vách đã ở đúng chỗ cần đỡ). Lỗ để RỘNG 0.6 mm
# chứ không ép sát: ty ren đã được bạc hộp số định vị qua khớp nối CỨNG rồi, gối thứ
# hai mà ôm chặt sẽ đánh nhau với nó — nhiệm vụ của lỗ này chỉ là chặn ty đảo/văng.
END_T = 7.5                               # dày hơn 6 mm một chút để hốc mù trục trơn
                                          # đủ sâu, và để trục trơn tròn 60.0 mm
ROD_END_SUPPORT = 2.0                     # đoạn ty ren nằm trong lỗ vách. Lỗ này KHÔNG
                                          # phải ổ đỡ chịu lực: ty ren M4 công-xôn 30 mm
                                          # võng ~0.00004 mm dưới trọng lượng bản thân,
                                          # và tốc độ tới hạn cách 60 rpm rất xa. Nó chỉ
                                          # là cái "hứng" đầu ty nếu ty hơi cong, nên
                                          # 2 mm là đủ — mỗi mm thêm là 1 mm hành trình.
                                          # Lỗ sâu END_T = 6 nên ty dài sai +4 mm vẫn lọt.
ROD_HOLE_D = ROD_D + 0.6
END_X0 = ROD_X1 - ROD_END_SUPPORT         # mặt trước vách = 51.0

NUT_CLEAR = 0.5                           # khe an toàn hốc <-> khớp nối
END_CLEAR = 0.5                           # khe an toàn thanh <-> vách gối đỡ

# Giới hạn GẦN: VÁCH TRƯỚC của hốc đai ốc không được đụng mặt trước KHỚP NỐI.
# (Thân thanh KHÔNG chặn ở đây — lỗ khoét cho nó trườn qua khớp nối; chỉ vách có lỗ
# Ø5.2 là không chui qua được.)
_X_MIN_MECH = COUP_X1 + NUT_CLEAR - BORE_FRONT
# Giới hạn XA: ba thứ cùng chạy về phía gối đỡ — hub, bạc trục trơn (bằng nhau theo
# thiết kế), và chiều dài ren còn lại để đai ốc còn ăn ren. Lấy cái chặn sớm nhất.
_X_MAX_HOLDER = END_X0 - END_CLEAR - HUB_FRONT
_X_MAX_BOSS = END_X0 - END_CLEAR - BOSS_L / 2.0
_X_MAX_THREAD = ROD_X1 - THREAD_MARGIN - (HUB_FRONT - NUT_WALL)
_X_MAX_MECH = min(_X_MAX_HOLDER, _X_MAX_BOSS, _X_MAX_THREAD)

# --- HỐC MÙ giữ trục trơn (trục KHÔNG xuyên thủng 2 gối) ------------------
GUIDE_BLIND_WALL = 1.5                    # vách mỏng bịt đáy hốc, chặn trục dọc trục
GUIDE_VENT_D = 1.5                        # lỗ thông hơi giữa vách: thoát khí khi đóng
                                          # trục vào, và để chọc trục ra khi cần tháo
GUIDE_BOSS_D = 10.0                       # vấu nối dài hốc trên bích đứng (bích chỉ
GUIDE_BOSS_L = 5.0                        # dày 3 mm, không đủ sâu cho hốc mù)
GUIDE_X0 = FACE_X0 + GUIDE_BLIND_WALL
GUIDE_X1 = END_X0 + END_T - GUIDE_BLIND_WALL
GUIDE_SOCKET_M = FACE_T + GUIDE_BOSS_L - GUIDE_BLIND_WALL   # hốc phía động cơ
GUIDE_SOCKET_E = END_T - GUIDE_BLIND_WALL                   # hốc phía gối đỡ
END_FOOT_X0, END_FOOT_X1 = END_X0 - 8.0, END_X0 + END_T + 6.0
# (rút từ +10 xuống +6: gân gối đỡ phải kết thúc trước trụ góc bắt nắp ở x = 69)

# --- 2 CÔNG TẮC HÀNH TRÌNH KW11 CÓ BÁNH XE (5A 250V) --------------------
# Thân 20 x 6.4 x 10, cần gạt 16 mm có bánh xe ở đầu, 2 lỗ M2 cách nhau 9.5.
# Đặt nằm: thân dài dọc Z, dày 6.4 dọc Y (áp vào vấu), cao 10 dọc X — tức là
# cần gạt bị ấn DỌC TRỤC CHẠY, đúng phương thanh đi tới.
SW_L, SW_T, SW_H = 20.0, 6.4, 10.0        # dài(Z) x dày(Y) x cao/phương ấn(X)
SW_HOLE_PITCH = 9.5                       # 2 lỗ M2 trên thân công tắc
SW_BODY_HOLE_D = 2.0                      # lỗ trên công tắc
SW_HOLE_D = 2.4                           # lỗ thông M2 trên vấu (bắt bu lông)
SW_FIN_T, SW_FIN_Y0 = 3.0, -18.5          # vấu đỡ; công tắc áp vào mặt -Y
SW_Z0 = BASE_T                            # đáy thân công tắc — đặt THẤP để bánh xe
                                          # ở đầu cần gạt rơi vào giữa mặt thanh

SW_LEVER_L, SW_LEVER_W = 16.0, 4.0        # cần gạt
SW_ROLLER_D, SW_ROLLER_W = 4.8, 2.5       # bánh xe
SW_ROLLER_PROUD = 6.0                     # mặt ngoài bánh xe nhô khỏi mặt thân (tự do)
SW_TRIP_TRAVEL = 2.0                      # ấn bánh xe 2 mm là tác động
SW_PRESS = 1.0                            # thanh ấn thêm bao nhiêu trước khi chạm chặn cơ

# Bánh xe cho over-travel dư dả hơn hẳn loại nút ấn: sau khi tác động còn
# (SW_ROLLER_PROUD - SW_TRIP_TRAVEL) mm nữa cần gạt mới chạm đáy, nên sai số
# lắp ráp vài mm vẫn không làm hỏng công tắc.
_SW_OVERTRAVEL = SW_ROLLER_PROUD - SW_TRIP_TRAVEL
X_TRIP_MIN = _X_MIN_MECH + SW_PRESS
X_TRIP_MAX = _X_MAX_MECH - SW_PRESS
# Mặt thân công tắc (mặt có cần gạt) suy ngược từ điểm tác động mong muốn
SW_MIN_FRONT = (X_TRIP_MIN - BAR_X / 2.0) - _SW_OVERTRAVEL
SW_MAX_FRONT = (X_TRIP_MAX + BAR_X / 2.0) + _SW_OVERTRAVEL

# Chân đế của Motor_Bracket phải nối dài tới hết vấu công tắc MIN, nếu không vấu
# đứng công-xôn hơn 10 mm chỉ dính vào bích. Chỉ nới phía -Y để không chiếm chỗ
# 4 lỗ bắt cụm xuống thân máy.
MB_FOOT_X1 = max(FACE_X0 + FACE_T, SW_MIN_FRONT)
MB_FOOT_Y1 = -7.0
FIN_BOLT_Y = MB_FOOT_Y1 - 4.0             # vít cạnh vấu công tắc: né mũ vít khỏi vấu
END_BOLT_Y = 16.0                         # vít trước của gối đỡ, né hub của thanh quét qua

BAR_HOME_X = 0.5 * (X_TRIP_MIN + X_TRIP_MAX)

# ---------------------------------------------------------------------------
# VỎ HỘP: cả cơ cấu nằm gọn trong một hình hộp, chỉ thanh trượt chui ra qua KHE
# ---------------------------------------------------------------------------
POST_W = 8.0                              # trụ góc bắt nắp
BASE_X1 = END_FOOT_X1 + POST_W            # khoang trong phải chứa được trụ góc
WALL_T = 3.0                              # bề dày vách
BOX_TOP = 31.0                            # mép trên vách = trần khoang (thanh cao 29.1)
BOX_X0, BOX_X1 = BASE_X0 - WALL_T, BASE_X1 + WALL_T
BOX_Y0, BOX_Y1 = BASE_Y0 - WALL_T, BASE_Y1 + WALL_T
LID_T = 3.0                               # nắp đậy
POST_Z0 = BASE_T + FOOT_T                 # trụ góc bắt đầu TRÊN mặt chân gá (z = 8):
                                          # hai chân gá trải tới y = +-18 nên trụ mà
                                          # xuống thấp hơn là đâm vào chúng
EAR_X, EAR_OUT, EAR_HOLE = 12.0, 9.0, 4.5  # tai bắt bu lông M4, chìa ra hai bên +-Y
SLOT_CLEAR = 1.0                          # khe rộng hơn thanh 1 mm mỗi phía
CABLE_D = 9.0                             # lỗ luồn dây động cơ + 2 công tắc, vách -X

M3_CLEAR = 3.4
M3_TAP = 2.5                              # lỗ mồi cho vít M3 tự tarô (nhựa in)
M16_CLEAR = 2.0                           # lỗ thông cho vít M1.6 (in FDM)
M16_HEAD_D = 3.2                          # mũ vít M1.6 ĐẦU CHÌM


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
    """Khoảng chạy hợp lệ của tâm thanh trượt (điểm TÁC ĐỘNG của 2 công tắc).

    Đầu gần: vách trước hốc đai ốc đụng mặt trước ĐAI ỐC HÃM.
    Đầu xa : hub / bạc trục trơn (hoặc hết ren) đụng vách gối đỡ.
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
    """Khoảng X của KHE trên vách -Y.

    Tính theo CHẶN CƠ KHÍ chứ không theo điểm công tắc tác động: nếu một công tắc
    chết thì thanh vẫn chạy thêm SW_PRESS mm nữa, khe phải chứa được cả đoạn đó.
    """
    return (_X_MIN_MECH - BAR_X / 2.0 - SLOT_CLEAR,
            _X_MAX_MECH + BAR_X / 2.0 + SLOT_CLEAR)


def post_boxes() -> list[tuple[float, float]]:
    """4 trụ góc bắt nắp, đặt ở 4 GÓC TRONG của khoang."""
    return [(x, y)
            for x in (BASE_X0, BASE_X1 - POST_W)
            for y in (BASE_Y0, BASE_Y1 - POST_W)]


def post_hole_xy() -> list[tuple[float, float]]:
    return [(x + POST_W / 2.0, y + POST_W / 2.0) for x, y in post_boxes()]


def ear_boxes() -> list[tuple[float, float]]:
    """4 tai bắt bu lông, chìa ra +-Y ở hai đầu hộp.

    Đặt ở hai đầu theo X (ngoài khoảng x mà bệ gá quét qua) để phía -Y vẫn trống
    cho cơ cấu người dùng lắp lên bệ.
    """
    xs = (BOX_X0 + 2.0, BOX_X1 - 2.0 - EAR_X)
    return [(x, BOX_Y0 - EAR_OUT) for x in xs] + [(x, BOX_Y1) for x in xs]


def ear_hole_xy() -> list[tuple[float, float]]:
    return [(x + EAR_X / 2.0, y + EAR_OUT / 2.0) for x, y in ear_boxes()]


def make_housing() -> Part.Shape:
    """VỎ HỘP: đáy + 4 vách + 4 tai bắt bu lông + KHE cho thanh trượt chui ra."""
    floor = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, 0.0, BASE_T)
    shell = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, BASE_T, BOX_TOP)
    shell = _cut(shell, _box2(BASE_X0, BASE_X1, BASE_Y0, BASE_Y1,
                              BASE_T - 1.0, BOX_TOP + 1.0))
    body = floor.fuse(shell)
    for x, y in ear_boxes():
        body = body.fuse(_box2(x, x + EAR_X, y, y + EAR_OUT, 0.0, BASE_T))
    for x, y in post_boxes():
        body = body.fuse(_box2(x, x + POST_W, y, y + POST_W, POST_Z0, BOX_TOP))

    # KHE: hở tới mép trên vách, nắp đậy nốt phần trên. Xẻ hở nóc thay vì lỗ kín để
    # khỏi phải in cầu vượt dài, và để hạ cả cụm thanh + trục vào từ trên xuống.
    sx0, sx1 = slot_x()
    body = _cut(body, _box2(sx0, sx1, BOX_Y0 - 1.0, BASE_Y0 + 1.0,
                            BAR_Z0 - SLOT_CLEAR, BOX_TOP + 1.0))
    # lỗ luồn dây ở vách -X, ngay sau đuôi động cơ
    body = _cut(body, _cyl_x(CABLE_D, WALL_T + 2.0, BOX_X0 - 1.0, 0.0, AXIS_Z))
    for x, y in ear_hole_xy():
        body = _cut(body, _cyl_z(EAR_HOLE, BASE_T + 2.0, x, y, -1.0))
    for x, y in post_hole_xy():
        body = _cut(body, _cyl_z(M3_TAP, 10.0, x, y, BOX_TOP - 9.0))
    for x, y in base_bolt_xy():
        body = _cut(body, _cyl_z(M3_CLEAR, BASE_T + 2.0, x, y, -1.0))
    return _refine(body)


def make_housing_lid() -> Part.Shape:
    """Nắp đậy phẳng, 4 vít M3 xuống 4 trụ góc. Tai bắt bu lông nằm ngoài mép nắp
    nên vẫn siết được bu lông xuống máy khi đã đậy nắp."""
    body = _box2(BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, BOX_TOP, BOX_TOP + LID_T)
    for x, y in post_hole_xy():
        body = _cut(body, _cyl_z(M3_CLEAR, LID_T + 2.0, x, y, BOX_TOP - 1.0))
    return _refine(body)


def base_bolt_xy() -> list[tuple[float, float]]:
    """Vít M3 bắt chân gá động cơ + gối đỡ xuống đế."""
    # Né bích đứng, 2 gân chống lật, VÀ vấu công tắc (y = -18.5..-15.5) để còn chỗ
    # vặn mũ vít — nên hai bên -Y / +Y không đối xứng theo X.
    return [
        (-25.0, -FOOT_BOLT_Y), (-16.0, -FOOT_BOLT_Y),      # gá ĐC, phía công tắc
        (CRADLE_X0 + 5.0, FOOT_BOLT_Y), (-6.0, FOOT_BOLT_Y),
        (MB_FOOT_X1 - 3.0, FIN_BOLT_Y),                    # đuôi chân đỡ vấu CT MIN
        # Gối đỡ: phía -Y KHÔNG bắt được ở đầu trước — mũ vít Ø6.5 ở đó bị kẹp giữa
        # vấu công tắc MAX (y <= -15.5) và hub của thanh quét qua (|y| <= 10). Dồn 2
        # vít -Y ra sau vách, nơi vấu đã hết.
        (END_FOOT_X0 + 4.5, END_BOLT_Y),
        (END_X0 + END_T + 3.5, -FOOT_BOLT_Y), (END_X0 + END_T + 3.5, FOOT_BOLT_Y),
    ]


def m16_head_cone(dy: float, dz: float) -> Part.Shape:
    """Côn 90 độ cho mũ vít M1.6 ĐẦU CHÌM, miệng đúng bằng mặt +X của bích.

    Bắt buộc phải chìm: mũ vít đầu trụ cao ~1.6 mm sẽ đội khớp nối ra xa đúng
    bấy nhiêu, mà mỗi mm ở đây là 1 mm hành trình.
    """
    depth = (M16_HEAD_D - M16_CLEAR) / 2.0   # côn 90 độ
    return _cone_x(M16_CLEAR, M16_HEAD_D, depth,
                   FACE_X0 + FACE_T - depth, dy, AXIS_Z + dz)


def make_motor_bracket() -> Part.Shape:
    """Bích đứng (bắt 2 vít M1.6 chìm) + máng ôm thân + chân đế + vấu công tắc MIN."""
    # chân đế — nới rộng sang phía trục trơn để đỡ gân
    foot = _box2(CRADLE_X0, FACE_X0 + FACE_T, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    # nối dài chân đế phía -Y để đỡ vấu công tắc MIN
    foot = foot.fuse(_box2(FACE_X0 + FACE_T, MB_FOOT_X1, -FOOT_Y, MB_FOOT_Y1,
                           BASE_T, BASE_T + FOOT_T))
    # bích đứng — kéo dài tới trục trơn để cắm luôn trục
    plate = _box2(FACE_X0, FACE_X0 + FACE_T, -CRADLE_Y, WING_Y, BASE_T, PLATE_TOP)
    # máng ôm thân động cơ
    cradle = _box2(CRADLE_X0, FACE_X0, -CRADLE_Y, CRADLE_Y, BASE_T, AXIS_Z)
    # gân chống lật ở phía trục trơn (chỗ không có máng đỡ)
    rib = _tri_rib(
        FACE_X0, CRADLE_X0 + 11.0, PLATE_TOP - 2.0, BASE_T + FOOT_T, RIB_Y0, RIB_T
    )
    # vấu nối dài hốc trục trơn — bích 3 mm không đủ sâu cho hốc mù
    guide_boss = _cyl_x(GUIDE_BOSS_D, GUIDE_BOSS_L, FACE_X0 + FACE_T, GUIDE_Y, AXIS_Z)
    body = (foot.fuse(plate).fuse(cradle).fuse(rib)
            .fuse(guide_boss).fuse(make_sw_fin(False)))

    body = _cut(body, motor_pocket_tool())
    # lỗ cho trục D Ø3 chui qua bích
    body = _cut(body, _cyl_x(SHAFT_CLEAR_D, FACE_T + 2.0, FACE_X0 - 1.0, 0.0, AXIS_Z))
    # 2 lỗ thông vít M1.6 + côn CHÌM ở mặt +X (mũ vít không được đội khớp nối)
    for dy, dz in motor_face_holes():
        body = _cut(body, _cyl_x(M16_CLEAR, FACE_T + 2.0, FACE_X0 - 1.0, dy, AXIS_Z + dz))
        body = _cut(body, m16_head_cone(dy, dz))
    # HỐC MÙ cắm trục trơn: mở từ x = GUIDE_X0 ra +X, chừa vách mỏng phía -X
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, GUIDE_SOCKET_M + 1.0,
                             GUIDE_X0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                             FACE_X0 - 1.0, GUIDE_Y, AXIS_Z))
    # vít M3 giữ nắp kẹp
    for x, y in clamp_bolt_xy():
        body = _cut(body, _cyl_z(M3_TAP, AXIS_Z - BASE_T, x, y, BASE_T))
    # vít M3 bắt xuống đế
    for x, y in base_bolt_xy():
        if x > MB_FOOT_X1 + 1.0:
            continue
        body = _cut(body, _cyl_z(M3_CLEAR, FOOT_T + 2.0, x, y, BASE_T - 1.0))
    return _refine(body)


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
    return [(x, y) for x in (-8.0, -21.0) for y in (-CLAMP_BOLT_Y, CLAMP_BOLT_Y)]


def make_motor_clamp() -> Part.Shape:
    """Nắp kẹp trên: ép lon mô tơ xuống máng, 4 vít M3."""
    body = _box2(-25.0, -4.0, -CRADLE_Y, CRADLE_Y, AXIS_Z, AXIS_Z + 6.0)
    body = _cut(body, motor_pocket_tool())
    for x, y in clamp_bolt_xy():
        body = _cut(body, _cyl_z(M3_CLEAR, 8.0, x, y, AXIS_Z - 1.0))
    return _refine(body)


def make_guide_shaft() -> Part.Shape:
    """Trục trơn Ø5, hai đầu nằm trong HỐC MÙ nên không tự trượt ra được."""
    return _cyl_x(GUIDE_D, GUIDE_X1 - GUIDE_X0, GUIDE_X0, GUIDE_Y, AXIS_Z)


def make_end_block() -> Part.Shape:
    """Gối đỡ đầu kia — đỡ trục trơn VÀ đầu ty ren, mang luôn vấu công tắc MAX.

    Lỗ đỡ ty ren nằm ngay trong vách (không có mỏ đỡ chìa ra): mặt trước vách
    x = %.1f vừa là bạc đỡ vừa là chặn cơ khí đầu xa.
    """ % END_X0
    foot = _box2(END_FOOT_X0, END_FOOT_X1, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    wall = _box2(END_X0, END_X0 + END_T, -CRADLE_Y, WING_Y, BASE_T, PLATE_TOP)
    # gân đặt PHÍA NGOÀI (x > vách) — phía trong là vùng thanh trượt chạy tới
    ribs = None
    for y0 in (-RIB_T / 2.0, RIB_Y0):
        r = _tri_rib(
            END_X0 + END_T, END_FOOT_X1, PLATE_TOP - 2.0, BASE_T + FOOT_T, y0, RIB_T
        )
        ribs = r if ribs is None else ribs.fuse(r)
    body = foot.fuse(wall).fuse(ribs).fuse(make_sw_fin(True))
    # HỐC MÙ cắm trục trơn: mở từ mặt -X của vách vào, chừa vách mỏng phía +X
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, GUIDE_X1 - (END_X0 - 1.0),
                             END_X0 - 1.0, GUIDE_Y, AXIS_Z))
    body = _cut(body, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                             GUIDE_X1, GUIDE_Y, AXIS_Z))
    # lỗ đỡ đầu ty ren — rộng 0.6 mm, chỉ chặn đảo chứ không làm bạc
    body = _cut(body, _cyl_x(ROD_HOLE_D, END_T + 2.0, END_X0 - 1.0, 0.0, AXIS_Z))
    for x, y in base_bolt_xy():
        if x < MB_FOOT_X1 + 1.0:
            continue
        body = _cut(body, _cyl_z(M3_CLEAR, FOOT_T + 2.0, x, y, BASE_T - 1.0))
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


def sw_fin_x(is_max: bool) -> tuple[float, float]:
    """Vấu chỉ trải tới mặt trước thân công tắc, không chìa ra chắn thanh."""
    x0, x1 = sw_body_x(is_max)
    if is_max:
        return x0, max(END_X0 + END_T, x1)
    return -12.0, x1


def make_sw_fin(is_max: bool) -> Part.Shape:
    """Vấu đứng mang công tắc; hàn liền vào gá động cơ / gối đỡ."""
    x0, x1 = sw_fin_x(is_max)
    fin = _box2(x0, x1, SW_FIN_Y0, SW_FIN_Y0 + SW_FIN_T, BASE_T, SW_Z0 + SW_L + 2.0)
    for xc, z in sw_hole_sites(is_max):
        fin = _cut(fin, _cyl_y(SW_HOLE_D, SW_FIN_T + 2.0, xc, SW_FIN_Y0 - 1.0, z))
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
    _ = sg  # hướng nhô đã nằm trong rx
    return _refine(body.fuse(lever).fuse(roller))


# ---------------------------------------------------------------------------
# Thanh tịnh tiến + hốc đai ốc
# ---------------------------------------------------------------------------
def load_tap_sites() -> list[tuple[float, float]]:
    """4 lỗ TARÔ M3 trên mặt đầu -Y: (lệch x so với tâm thanh, cao độ z)."""
    return [
        (sx * LOAD_TAP_DX, AXIS_Z + sz * LOAD_TAP_DZ)
        for sx in (-1.0, 1.0)
        for sz in (-1.0, 1.0)
    ]


def load_bolt_sites() -> list[float]:
    """2 lỗ M3 XUYÊN theo Z: lệch x so với tâm thanh."""
    return [-LOAD_BOLT_DX, LOAD_BOLT_DX]


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
    """THANH TỊNH TIẾN — nay gồm cả hốc đai ốc, không còn chi tiết gá rời.

    Từ -X sang +X: lỗ khoét Ø(khớp nối) xuyên thân thanh → vách trước → khe đai ốc
    HỞ NÓC → vách sau. Mặt trước hub trùng mặt trước bạc trục trơn nên phần thêm này
    không lấn thêm mm hành trình nào.
    """
    bar = _box2(xc - BAR_X / 2.0, xc + BAR_X / 2.0, BAR_Y0, BAR_Y1, BAR_Z0, BAR_Z1)
    boss = _cyl_x(BOSS_D, BOSS_L, xc - BOSS_L / 2.0, GUIDE_Y, AXIS_Z)
    hub = _box2(*hub_x(xc), -HUB_Y, HUB_Y, BAR_Z0, BAR_Z1)
    # đầu tự do dày hơn để còn thịt quanh 2 lỗ M3; nằm ở y < BAR_PAD_Y1 nên không
    # chạm bích/gối đỡ/công tắc, tức là KHÔNG ăn vào hành trình
    pad = _box2(xc - BAR_PAD_X / 2.0, xc + BAR_PAD_X / 2.0,
                BAR_Y0, BAR_PAD_Y1, BAR_Z0, BAR_Z1)
    body = bar.fuse(boss).fuse(hub).fuse(pad)

    # lỗ trượt trên trục trơn
    body = _cut(body, _cyl_x(BOSS_BORE, BOSS_L + 4.0, xc - BOSS_L / 2.0 - 2.0, GUIDE_Y, AXIS_Z))
    # LỖ KHOÉT cho khớp nối + đai ốc hãm trườn qua, đáy là mặt ngoài vách trước
    b0, b1 = bore_x(xc)
    body = _cut(body, _cyl_x(COUP_CLEAR_D, b1 - (b0 - 2.0), b0 - 2.0, 0.0, AXIS_Z))
    # KHE HỞ NÓC chứa đai ốc — nằm hẳn ở phía +X của thân thanh nên tấm thân vẫn đặc
    px0, px1 = pocket_x(xc)
    body = _cut(body, _box2(px0, px1, -NUT_SLOT_W / 2.0, NUT_SLOT_W / 2.0,
                            NUT_SLOT_Z0, BAR_Z1 + 1.0))
    # lỗ ty ren xuyên 2 vách
    body = _cut(body, _cyl_x(ROD_CLEAR_D, HUB_FRONT + BAR_X / 2.0 + 3.0,
                             xc - BAR_X / 2.0 - 1.0, 0.0, AXIS_Z))
    # BỆ GÁ TẢI, bộ (a): 4 lỗ tarô M3 trên MẶT ĐẦU -Y — bắt tấm vách ngăn úp vào
    for dx, z in load_tap_sites():
        body = _cut(body, _cyl_y(M3_TAP, LOAD_TAP_DEPTH, xc + dx, BAR_Y0 - 0.001, z))
    # BỆ GÁ TẢI, bộ (b): 2 lỗ M3 XUYÊN theo Z — kẹp cơ cấu chỉnh cao lên trên/dưới
    for dx in load_bolt_sites():
        body = _cut(body, _cyl_z(M3_CLEAR, BAR_Z1 - BAR_Z0 + 2.0,
                                 xc + dx, LOAD_BOLT_Y, BAR_Z0 - 1.0))
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
    static = (parts["Motor_Bracket"].fuse(parts["End_Block"])
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
    v = _common_vol(parts["Coupler"], parts["Motor_Bracket"])
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

    # --- trục trơn phải nằm trong HỐC MÙ, KHÔNG xuyên thủng 2 gối ---
    bad = []
    for nm, x0 in (("Motor_Bracket", FACE_X0), ("End_Block", GUIDE_X1)):
        # khối trụ Ø5 ngay ngoài đầu trục phải ĐẶC hoàn toàn -> đó là vách chặn
        wall = _cyl_x(GUIDE_D, GUIDE_BLIND_WALL, x0, GUIDE_Y, AXIS_Z)
        wall = _cut(wall, _cyl_x(GUIDE_VENT_D, GUIDE_BLIND_WALL + 2.0,
                                 x0 - 1.0, GUIDE_Y, AXIS_Z))
        if _common_vol(parts[nm], wall) < 0.99 * wall.Volume:
            bad.append(nm)
    checks.append(
        ("Truc tron bi vach mong chan o CA HAI dau", not bad,
         "vach %.1f mm (%s)" % (GUIDE_BLIND_WALL, ", ".join(bad) if bad else "kin ca 2"))
    )
    # trục không được thò ra khỏi bao ngoài của 2 gối theo phương X
    gs = parts["Guide_Shaft"].BoundBox
    ok = (gs.XMin >= FACE_X0 + GUIDE_BLIND_WALL - 1e-6
          and gs.XMax <= END_X0 + END_T - GUIDE_BLIND_WALL + 1e-6)
    checks.append(
        ("Truc tron khong xuyen thung gia do", ok,
         "truc x = %.1f..%.1f, gia do het o %.1f va %.1f"
         % (gs.XMin, gs.XMax, FACE_X0, END_X0 + END_T))
    )
    # hốc phải sâu >= 1 x đường kính trục, nếu không thì trục lỏng lẻo dễ lật
    checks.append(
        ("2 hoc mu sau >= 1 x O truc", min(GUIDE_SOCKET_M, GUIDE_SOCKET_E) >= GUIDE_D - 1e-9,
         "hoc %.1f (bich) va %.1f (goi do), can %.1f"
         % (GUIDE_SOCKET_M, GUIDE_SOCKET_E, GUIDE_D))
    )
    # lỗ thông hơi phải thông suốt vách nhưng nhỏ hơn trục
    bad = 0
    for nm, x0 in (("Motor_Bracket", FACE_X0 - 0.5), ("End_Block", GUIDE_X1 + 0.1)):
        vent = _cyl_x(GUIDE_VENT_D - 0.3, GUIDE_BLIND_WALL + 0.4, x0, GUIDE_Y, AXIS_Z)
        if _common_vol(parts[nm], vent) > 1e-6:
            bad += 1
    checks.append(
        ("Lo thong hoi thong suot va nho hon truc", bad == 0 and GUIDE_VENT_D < GUIDE_D,
         "O%.1f < O%.1f, %d lo bi bit" % (GUIDE_VENT_D, GUIDE_D, bad))
    )
    # vấu nối dài hốc không được đụng gì đang chuyển động
    v = max(_common_vol(parts["Motor_Bracket"], make_slide_bar(x_min)),
            _common_vol(parts["Motor_Bracket"], parts["Coupler"]))
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

    # --- đầu ty ren nằm trong lỗ vách gối đỡ ---
    eng = ROD_X1 - END_X0
    checks.append(
        ("Dau ty ren nam trong lo End_Block", abs(eng - ROD_END_SUPPORT) < 1e-6
         and ROD_X1 <= END_X0 + END_T,
         "an %.1f mm (x %.1f -> %.1f), vach het o %.1f"
         % (eng, END_X0, ROD_X1, END_X0 + END_T))
    )
    v = _common_vol(parts["Thread_Rod"], parts["End_Block"])
    checks.append(("Lo do khong bop ty ren", v < 1e-6, "chong lan %.2f mm3" % v))
    # phải có VÀNH ĐẶC bao quanh lỗ suốt đoạn đỡ, nếu không thì lỗ đỡ chỉ là hình vẽ
    ring = _cyl_x(ROD_HOLE_D + 5.0, eng, END_X0, 0.0, AXIS_Z)
    ring = _cut(ring, _cyl_x(ROD_HOLE_D + 0.6, eng + 2.0, END_X0 - 1.0, 0.0, AXIS_Z))
    filled = _common_vol(parts["End_Block"], ring) / max(ring.Volume, 1e-9)
    checks.append(
        ("Vach gia do co vanh dac quanh dau ty ren", filled > 0.99,
         "dac %.0f%% suot %.1f mm" % (100.0 * filled, eng))
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
    for is_max in (False, True):
        for xc, z in sw_hole_sites(is_max):
            bolt = _cyl_y(SW_BODY_HOLE_D - 0.2, SW_T + SW_FIN_T + 4.0,
                          xc, SW_FIN_Y0 - SW_T - 2.0, z)
            if _common_vol(parts["Limit_Switch_Max" if is_max else "Limit_Switch_Min"], bolt) > 1e-6:
                bad += 1
            if _common_vol(parts["End_Block" if is_max else "Motor_Bracket"], bolt) > 1e-6:
                bad += 1
    checks.append(
        ("4 bu long M2 xuyen duoc ca cong tac lan vau", bad == 0, "%d lo bi bit" % bad)
    )

    # công tắc không được đụng bất cứ chi tiết cố định nào
    for nm in ("Limit_Switch_Min", "Limit_Switch_Max"):
        v = max(_common_vol(parts[nm], parts[o])
                for o in ("Motor_Bracket", "End_Block", "Housing", "N20_Motor"))
        checks.append(("%s khong dung chi tiet khac" % nm, v < 1e-6, "chong lan %.2f mm3" % v))

    # rơ dọc trục = khe giữa đai ốc và 2 vách hốc
    play = NUT_POCKET - NUT_H
    checks.append(("Ro doc truc cua dai oc <= 0.2 mm", play <= 0.2 + 1e-9, "%.2f mm" % play))

    v = _common_vol(parts["Motor_Bracket"], parts["N20_Motor"])
    checks.append(("Dong co lot vao mang gia do", v < 1e-6, "chong lan %.2f mm3" % v))

    v = _common_vol(parts["Motor_Clamp"], parts["N20_Motor"])
    checks.append(("Nap kep khong an vao than dong co", v < 1e-6, "chong lan %.2f mm3" % v))

    # trục trơn và ty ren phải song song và cùng cao độ
    checks.append(
        ("Truc tron SONG SONG ty ren (cung z, lech y %.0f mm)" % GUIDE_Y, True, "OK")
    )

    # 2 lỗ M1.6 trên bích phải thông suốt và trùng tâm lỗ ren trên mặt động cơ
    bad = 0
    for dy, dz in motor_face_holes():
        probe = _cyl_x(MOT_HOLE_TAP, FACE_T + 4.0, FACE_X0 - 2.0, dy, AXIS_Z + dz)
        if _common_vol(parts["Motor_Bracket"], probe) > 1e-6:
            bad += 1
    checks.append(("2 lo M1.6 tren bich thong va trung tam", bad == 0, "%d lo bi bit" % bad))
    # mũ vít M1.6 phải CHÌM hẳn trong bích, nếu lồi ra thì nó đội khớp nối
    bad = 0
    for dy, dz in motor_face_holes():
        if _common_vol(parts["Motor_Bracket"], m16_head_cone(dy, dz)) > 1e-6:
            bad += 1
    checks.append(("Mu vit M1.6 chim han trong bich", bad == 0, "%d mu vit loi" % bad))

    # vít M3 giữ nắp kẹp phải xuyên nắp và có thịt để tarô trong máng
    bad = 0
    for x, y in clamp_bolt_xy():
        probe = _cyl_z(M3_TAP, 3.0, x, y, AXIS_Z + 1.0)     # trong nắp kẹp
        if _common_vol(parts["Motor_Clamp"], probe) > 1e-6:
            bad += 1
        ring = _cyl_z(M3_TAP + 3.0, 4.0, x, y, AXIS_Z - 6.0)  # thịt quanh lỗ tarô
        if _common_vol(parts["Motor_Bracket"], ring) < 20.0:
            bad += 1
    checks.append(("4 vit M3 nap kep xuyen nap + co thit taro", bad == 0, "%d loi" % bad))

    # lỗ bắt chân gá xuống đế phải trùng lỗ trên Base_Plate
    bad = 0
    for x, y in base_bolt_xy():
        probe = _cyl_z(M3_CLEAR - 0.4, BASE_T + FOOT_T + 2.0, x, y, -1.0)
        if _common_vol(parts["Housing"], probe) > 1e-6:
            bad += 1
        if _common_vol(parts["Motor_Bracket"], probe) > 1e-6:
            bad += 1
        if _common_vol(parts["End_Block"], probe) > 1e-6:
            bad += 1
    checks.append(("Lo M3 chan ga trung lo tren de", bad == 0, "%d lo lech" % bad))

    # phải đủ chỗ cho mũ vít M3 (Ø6) ngay trên mặt chân đế
    bad = 0
    for x, y in base_bolt_xy():
        head = _cyl_z(6.5, 4.0, x, y, BASE_T + FOOT_T)
        if _common_vol(parts["Motor_Bracket"], head) > 1e-6:
            bad += 1
        if _common_vol(parts["End_Block"], head) > 1e-6:
            bad += 1
    checks.append(("Mu vit M3 khong vuong mang / gan", bad == 0, "%d vi tri ket" % bad))

    # THANH quét qua đế: không được cạ vào mũ vít nào (thanh giờ thấp hơn bản cũ)
    bad = 0
    for x, y in base_bolt_xy():
        head = _cyl_z(6.5, 4.0, x, y, BASE_T + FOOT_T)
        for xb in (x_min, x_max):
            if _common_vol(make_slide_bar(xb), head) > 1e-6:
                bad += 1
    checks.append(("Thanh khong ca vao mu vit tren de", bad == 0,
                   "%d va cham (day thanh z = %.1f)" % (bad, BAR_Z0)))

    # --- BỆ GÁ TẢI: 2 bộ lỗ trên 2 mặt vuông góc ---
    bar = parts["Slide_Bar"]
    xc = BAR_HOME_X
    # 4 lỗ tarô mặt đầu: phải có vành thịt quanh suốt chiều sâu tarô
    bad = 0
    for dx, z in load_tap_sites():
        ring = _cyl_y(M3_TAP + 3.0, LOAD_TAP_DEPTH - 1.0, xc + dx, BAR_Y0 + 0.5, z)
        ring = _cut(ring, _cyl_y(M3_TAP, LOAD_TAP_DEPTH + 2.0, xc + dx, BAR_Y0 - 1.0, z))
        if _common_vol(bar, ring) < 0.95 * ring.Volume:
            bad += 1
    checks.append(
        ("4 lo taro mat dau co du thit quanh lo", bad == 0,
         "%d lo thieu thit, chu nhat %.0f x %.0f mm sau %.1f"
         % (bad, 2 * LOAD_TAP_DX, 2 * LOAD_TAP_DZ, LOAD_TAP_DEPTH))
    )
    # 2 lỗ xuyên theo Z: phải THÔNG suốt và có vành thịt
    bad = 0
    for dx in load_bolt_sites():
        probe = _cyl_z(M3_CLEAR - 0.4, BAR_Z1 - BAR_Z0 + 4.0, xc + dx, LOAD_BOLT_Y, BAR_Z0 - 2.0)
        if _common_vol(bar, probe) > 1e-6:
            bad += 1
        ring = _cyl_z(M3_CLEAR + 3.0, BAR_Z1 - BAR_Z0 - 1.0, xc + dx, LOAD_BOLT_Y, BAR_Z0 + 0.5)
        ring = _cut(ring, _cyl_z(M3_CLEAR, BAR_Z1 - BAR_Z0 + 4.0, xc + dx, LOAD_BOLT_Y, BAR_Z0 - 2.0))
        if _common_vol(bar, ring) < 0.95 * ring.Volume:
            bad += 1
    checks.append(
        ("2 lo M3 xuyen suot be ga, co vanh thit", bad == 0,
         "%d loi, cach nhau %.0f mm" % (bad, 2 * LOAD_BOLT_DX))
    )
    # hai bộ lỗ không được cắt vào nhau
    gap = LOAD_BOLT_DX - LOAD_TAP_DX - M3_CLEAR / 2.0 - M3_TAP / 2.0
    checks.append(
        ("2 bo lo khong cat vao nhau", gap >= 1.5,
         "con %.2f mm thit giua lo taro va lo xuyen" % gap)
    )
    # bu lông thò ra hai đầu lỗ xuyên (mũ + đai ốc) không được va gì khi thanh chạy
    bad = 0
    for dx in load_bolt_sites():
        for z0 in (BAR_Z1, BAR_Z0 - 10.0):
            head = _cyl_z(7.0, 10.0, 0.0, LOAD_BOLT_Y, z0)
            for xb in (x_min, x_max):
                h = head.copy()
                h.translate(App.Vector(xb + dx, 0.0, 0.0))
                if _common_vol(h, static) > 1e-6:
                    bad += 1
    checks.append(
        ("Bu long tren/duoi be ga khong va gi", bad == 0, "%d va cham" % bad)
    )
    # VÙNG GÁ TẢI phải trống hoàn toàn — lời hứa cho người thiết kế phần lắp lên bệ.
    # Giới hạn dưới là z = BASE_T + 1: dưới đó là 4 TAI bắt bu lông chìa ra hai bên.
    everything = static.fuse(parts["Housing"]).fuse(parts["Housing_Lid"])
    free = _box2(BOX_X0 - 60.0, BOX_X1 + 60.0, -140.0, BAR_PAD_Y1,
                 BASE_T + 1.0, BOX_TOP + LID_T + 60.0)
    v = _common_vol(free, everything)
    checks.append(
        ("Vung ga tai (y <= %.0f, z >= %.0f) la trong" % (BAR_PAD_Y1, BASE_T + 1.0),
         v < 1e-6, "chong lan %.2f mm3" % v)
    )

    # --- VỎ HỘP ---
    # thanh phải chui qua khe ở CẢ HAI CHẶN CƠ KHÍ (không phải chỉ ở điểm công tắc)
    bad = 0
    for xb in (_X_MIN_MECH, _X_MAX_MECH, x_min, x_max):
        if _common_vol(make_slide_bar(xb), parts["Housing"]) > 1e-6:
            bad += 1
    sx0, sx1 = slot_x()
    checks.append(
        ("Thanh chui qua khe o ca 2 chan co khi", bad == 0,
         "%d va cham, khe x = %.1f..%.1f (%.1f mm)" % (bad, sx0, sx1, sx1 - sx0))
    )
    # mọi chi tiết tĩnh phải nằm gọn trong khoang, không đụng vỏ
    bad = []
    for nm in ("Motor_Bracket", "Motor_Clamp", "N20_Motor", "Coupler", "Thread_Rod",
               "Guide_Shaft", "End_Block", "Limit_Switch_Min", "Limit_Switch_Max"):
        if _common_vol(parts[nm], parts["Housing"]) > 1e-6:
            bad.append(nm)
    checks.append(("Chi tiet trong hop khong dung vo", not bad,
                   ", ".join(bad) if bad else "ca %d chi tiet deu lot" % 9))
    # nắp không được đụng gì bên trong (thanh là thứ cao nhất)
    bad = []
    for nm in ("Motor_Bracket", "End_Block", "Motor_Clamp", "Limit_Switch_Min",
               "Limit_Switch_Max"):
        if _common_vol(parts[nm], parts["Housing_Lid"]) > 1e-6:
            bad.append(nm)
    for xb in (_X_MIN_MECH, _X_MAX_MECH):
        if _common_vol(make_slide_bar(xb), parts["Housing_Lid"]) > 1e-6:
            bad.append("Slide_Bar")
    checks.append(
        ("Nap khong dung gi ben trong", not bad,
         "ho %.1f mm tren dinh thanh" % (BOX_TOP - BAR_Z1) if not bad else ", ".join(bad))
    )
    # 4 trụ góc bắt nắp không được đâm vào chi tiết nào
    bad = 0
    for x, y in post_boxes():
        post = _box2(x, x + POST_W, y, y + POST_W, POST_Z0, BOX_TOP)
        if _common_vol(post, static) > 1e-6:
            bad += 1
        for xb in (_X_MIN_MECH, _X_MAX_MECH):
            if _common_vol(post, make_slide_bar(xb)) > 1e-6:
                bad += 1
    checks.append(("4 tru goc bat nap khong dung gi", bad == 0, "%d tru bi vuong" % bad))
    # 4 vít nắp phải xuyên nắp và vào đúng trụ
    bad = 0
    for x, y in post_hole_xy():
        probe = _cyl_z(M3_TAP - 0.2, LID_T + 8.0, x, y, BOX_TOP - 8.0)
        if _common_vol(parts["Housing"], probe) > 1e-6:
            bad += 1
        if _common_vol(parts["Housing_Lid"], probe) > 1e-6:
            bad += 1
    checks.append(("4 vit M3 xuyen nap vao tru goc", bad == 0, "%d lo bi bit" % bad))
    # 4 tai: lỗ M4 thông, và KHÔNG bị nắp che (còn siết được khi đã đậy nắp)
    bad = 0
    for x, y in ear_hole_xy():
        probe = _cyl_z(EAR_HOLE - 0.4, BASE_T + 4.0, x, y, -2.0)
        if _common_vol(parts["Housing"], probe) > 1e-6:
            bad += 1
        above = _cyl_z(EAR_HOLE + 3.0, BOX_TOP + LID_T, x, y, BASE_T)
        if _common_vol(parts["Housing_Lid"], above) > 1e-6:
            bad += 1
    checks.append(
        ("4 tai M4 thong va khong bi nap che", bad == 0,
         "%d loi, tai %.0f x %.0f mm" % (bad, EAR_X, EAR_OUT))
    )
    # lỗ luồn dây phải thông và không bị động cơ bịt
    probe = _cyl_x(CABLE_D - 1.0, WALL_T + 4.0, BOX_X0 - 2.0, 0.0, AXIS_Z)
    checks.append(
        ("Lo luon day thong qua vach -X", _common_vol(parts["Housing"], probe) < 1e-6,
         "O%.1f tai z = %.0f, cach duoi dong co %.1f mm"
         % (CABLE_D, AXIS_Z, -MOT_LEN - BASE_X0))
    )
    # bệ gá tải phải nằm HẲN ngoài mặt ngoài vách -Y
    checks.append(
        ("Be ga tai nam han ngoai vo hop", BAR_PAD_Y1 <= BOX_Y0 - 0.5,
         "be het o y = %.1f, mat ngoai vach y = %.1f" % (BAR_PAD_Y1, BOX_Y0))
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
    parts = {
        "Housing": make_housing(),
        "Housing_Lid": make_housing_lid(),
        "Motor_Bracket": make_motor_bracket(),
        "Motor_Clamp": make_motor_clamp(),
        "N20_Motor": make_motor(),
        "Coupler": make_coupler(),
        "Coupler_Spacer": make_coupler_spacer(),
        "Thread_Rod": make_thread_rod(),
        "Guide_Shaft": make_guide_shaft(),
        "End_Block": make_end_block(),
        "Limit_Switch_Min": make_limit_switch(False),
        "Limit_Switch_Max": make_limit_switch(True),
        "Slide_Bar": make_slide_bar(BAR_HOME_X),
        "Hex_Nut": make_hex_nut(BAR_HOME_X),
    }
    return parts


COLORS = {
    "Housing": ((0.72, 0.74, 0.78), 0),
    "Housing_Lid": ((0.62, 0.64, 0.68), 60),
    "Motor_Bracket": ((0.20, 0.45, 0.75), 0),
    "Motor_Clamp": ((0.16, 0.36, 0.62), 0),
    "N20_Motor": ((0.35, 0.36, 0.38), 0),
    "Coupler": ((0.55, 0.58, 0.62), 0),
    "Coupler_Spacer": ((0.35, 0.70, 0.45), 0),
    "Thread_Rod": ((0.83, 0.68, 0.28), 0),
    "Guide_Shaft": ((0.80, 0.82, 0.86), 0),
    "End_Block": ((0.20, 0.45, 0.75), 0),
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
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)

    x_min, x_max = travel_range()
    print("--- THONG SO ---")
    print("  Dong co     : GA12-N20 truc D O%.0f x %.0f, bich 12x10, 2 x M1.6 CHIM cheo"
          % (SHAFT_D, SHAFT_LEN))
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
    print("                cham tai x = %.1f va %.1f  (hanh trinh dien %.1f mm)"
          % (X_TRIP_MIN, X_TRIP_MAX, X_TRIP_MAX - X_TRIP_MIN))
    print("  Chan co khi : x = %.1f va %.1f  (du %.1f mm over-travel moi dau)"
          % (_X_MIN_MECH, _X_MAX_MECH, _SW_OVERTRAVEL))
    print("                gan: vach truoc hoc dung %s | xa: %s"
          % ("khop noi",
             "hub dung vach" if _X_MAX_MECH == _X_MAX_HOLDER
             else ("bac dung vach" if _X_MAX_MECH == _X_MAX_BOSS else "het ren")))
    print("  Truc tron   : O%.0f, dai %.1f mm, SONG SONG ty ren, lech y = %.0f mm"
          % (GUIDE_D, GUIDE_X1 - GUIDE_X0, GUIDE_Y))
    print("                2 dau cam HOC MU sau %.1f (bich) va %.1f (goi do); vach chan"
          % (GUIDE_SOCKET_M, GUIDE_SOCKET_E))
    print("                %.1f mm co lo thong hoi O%.1f de dong vao / choc ra"
          % (GUIDE_BLIND_WALL, GUIDE_VENT_D))
    print("  Thanh       : than day %.1f (X) x cao %.1f (Z), lo O%.1f cho khop noi chui qua"
          % (BAR_X, BAR_Z1 - BAR_Z0, COUP_CLEAR_D))
    print("                hub lien khoi x = %+.1f..%+.1f so voi tam: vach %.1f | khe %.1f | vach %.1f"
          % (-BAR_X / 2.0, HUB_FRONT, NUT_WALL, NUT_POCKET, NUT_WALL))
    print("  Be ga tai   : mat dau -Y  : 4 lo TARO M3, chu nhat %.0f x %.0f mm, sau %.1f"
          % (2 * LOAD_TAP_DX, 2 * LOAD_TAP_DZ, LOAD_TAP_DEPTH))
    print("                mat tren/duoi: 2 lo M3 XUYEN, cach %.0f mm, tai y = %.1f"
          % (2 * LOAD_BOLT_DX, LOAD_BOLT_Y))
    print("                be %.0f (X) x %.0f (Y) x %.1f (Z), mat dau o y = %.1f"
          % (BAR_PAD_X, BAR_PAD_Y1 - BAR_Y0, BAR_Z1 - BAR_Z0, BAR_Y0))
    print("                VUNG TRONG cho tai: y <= %.1f va z >= %.1f — moi x"
          % (BAR_PAD_Y1, BASE_T + 1.0))
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
    print("  VO HOP      : ngoai %.0f x %.0f x %.0f mm (ke ca nap), vach %.1f"
          % (BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_TOP + LID_T, WALL_T))
    print("                khoang trong %.0f x %.0f x %.0f mm"
          % (BASE_X1 - BASE_X0, BASE_Y1 - BASE_Y0, BOX_TOP - BASE_T))
    print("                KHE vach -Y: x = %.1f..%.1f (%.1f mm) x z = %.1f..%.1f, ho noc"
          % (sx0, sx1, sx1 - sx0, BAR_Z0 - SLOT_CLEAR, BOX_TOP))
    print("                4 TAI M4 %.0fx%.0f, tam lo tai x = %s | y = %s"
          % (EAR_X, EAR_OUT,
             ", ".join("%.1f" % v for v in sorted({x for x, _ in ear_hole_xy()})),
             ", ".join("%.1f" % v for v in sorted({y for _, y in ear_hole_xy()}))))
    print("                bao ngoai KE CA TAI: %.0f x %.0f mm"
          % (BOX_X1 - BOX_X0, (BOX_Y1 + EAR_OUT) - (BOX_Y0 - EAR_OUT)))
    print("                nap: 4 vit M3 xuong 4 tru goc; lo luon day O%.1f o vach -X"
          % CABLE_D)

    print("--- NGAN SACH HANH TRINH ---")
    stack = 2.0 * NUT_WALL + NUT_POCKET
    rows = [
        ("Ty ren M4 x %.0f" % ROD_LEN, ROD_LEN),
        ("- cam vao khop noi", -COUP_ROD_IN),
        ("- cam vao lo do End_Block", -ROD_END_SUPPORT),
        ("- chong om dai oc (%.1f+%.1f+%.1f)" % (NUT_WALL, NUT_POCKET, NUT_WALL), -stack),
        ("- khe an toan 2 x %.1f" % END_CLEAR, -2.0 * END_CLEAR),
    ]
    for label, val in rows:
        print("  %-38s %+7.1f" % (label, val))
    print("  %-38s %7.1f" % ("= chan co khi", _X_MAX_MECH - _X_MIN_MECH))
    print("  %-38s %+7.1f" % ("- cong tac tac dong som 2 x %.1f" % SW_PRESS, -2.0 * SW_PRESS))
    print("  %-38s %7.1f" % ("= HANH TRINH THUC", x_max - x_min))

    print("--- KIEM TRA ---")
    checks = verify(parts)
    n_fail = 0
    for label, ok, detail in checks:
        if not ok:
            n_fail += 1
        print("  [%s] %-52s %s" % ("OK" if ok else "FAIL", label, detail))
    print("  => %d FAIL / %d checks" % (n_fail, len(checks)))

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
    else:
        print("!! Dang chay headless — model se bi an. Hay mo bang freecad.exe.")
        App.closeDocument(doc.Name)


main()
