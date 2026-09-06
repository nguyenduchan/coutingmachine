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
  BYJ_Motor      - 28BYJ-48 (mua sẵn): thân O28 x 19, LỆCH TÂM 8 mm, 2 tai thép cách
                   nhau 35 mm nằm trên đường VUÔNG GÓC với hướng lệch tâm. KHÔNG còn
                   gồm trục — có lỗ 2 tầng quanh trục: khoang rộng O(MOT_SHAFT_RET_BORE)
                   ở đáy (chứa gờ giữ trục) rồi thu lại thành lỗ trơn O(MOT_SHAFT_BORE)
  BYJ_Motor_Shaft - trục ĐC O5 hai mặt vát, TÁCH RIÊNG khỏi BYJ_Motor (chốt 2026-09-06,
                   người dùng yêu cầu): khe hở MOT_SHAFT_CLR quanh trục trong lỗ thân —
                   quay được độc lập (đổi Placement.Rotation để animate), khe hở đủ
                   rộng nên in 3D thử cũng lắp lọt (không phải kiểu ép chặt). Đáy trục
                   có GỜ GIỮ O(MOT_SHAFT_RET_D) nằm trong khoang rộng của thân (lần 22)
                   -> chống tuột lên, vẫn quay tự do
  Pinion         - bánh răng thẳng IN 3D, m≈1.0045, z=22 (STEPS_PER_MM=59, Ø đỉnh
                   ≈24.1 mm), PA 20 deg, lỗ O5 hai mặt vát. Đỉnh trụ+bán cầu Ø10
                   (không moay-ơ dưới)
  Slide_Bar      - THANH TỊNH TIẾN in liền, tiết diện chữ П CƯỠI LÊN bánh răng:
                   chân +Y mang THANH RĂNG + bạc trục A, chân -Y mang bạc trục B,
                   cầu nối nằm TRÊN đầu trục động cơ, trên cầu là TRỤ GÁ TẢI
  Guide_Rod_A/B  - 2 thanh dẫn hướng TRÒN Ø(ROD_D) cắt phẳng đáy, IN 3D (trơn hơn
                   vuông trên máy đời cũ). A: bạc lỗ tròn khít (định vị). B: bạc
                   capsule nới Y (chỉ chặn xoay). Đầu +X lỗ mồi tự ren cho Rod_Cap
  Guide_Rod_Cap_A/B - TẤM PHẲNG VUÔNG chặn đầu +X của mỗi thanh (chốt 2026-09-06, xem
                   "NẮP CHẶN TRỤC" bên dưới): úp khít cả mặt vách lẫn đầu thanh (đầu
                   thanh PHẲNG khít mặt vách, không cắm hốc), ép bằng DUY NHẤT 1 vít tự
                   ren M3 xuyên THẲNG HÀNG vào lỗ mồi ở đầu thanh (không có trụ bắt vít
                   riêng trên Housing) — THÁO ĐƯỢC, khoá thanh khỏi xô lệch dọc trục
  Limit_Switch_Min - MỘT KW11 bánh xe (HOME), bị ấn DỌC TRỤC bởi mặt đầu -X của thanh

ĐỔI SANG THANH VUÔNG IN 3D (chốt 2026-09-06, người dùng quyết, đánh đổi có cân nhắc):
  Bản trước Guide_Rod là trục thép O5 mạ crôm MUA SẴN — kết luận độ bền 3 năm trước đó
  (91 giờ chạy, quãng trượt 3.3-6.6 km) dựa trên thép + mỡ, KHÔNG phải nhựa in. Đổi
  sang thanh in liền cùng vật liệu Slide_Bar (PETG) là ma sát NHỰA-NHỰA khô, mòn nhanh
  hơn thép nhiều — người dùng đã được báo và CHẤP NHẬN đánh đổi này để khỏi phải mua/đo
  trục thép riêng. Nếu sau này thấy rơ tăng nhanh hoặc kẹt, việc dễ nhất là bôi mỡ vào
  2 bạc hoặc quay lại trục thép O5 (bạc vẫn vừa nếu khoét lại tròn).
  LÝ DO ĐỔI TIẾT DIỆN VUÔNG (không phải tròn khoét bẹt một mặt):
    - In một trụ tròn NẰM NGANG chỉ chạm bàn in theo MỘT ĐƯỜNG TIẾP TUYẾN suốt chiều
      dài — lớp đầu tiên mảnh như sợi chỉ dọc theo đó, dễ bong khỏi bàn (nhất là máy
      không có buồng kín / bàn không phẳng như Ender-3 Pro). Thanh vuông nằm bằng CẢ
      MỘT MẶT phẳng xuống bàn — bám y hệt in một khối hộp bình thường.
    - Bạc lỗ vuông tự chống xoay được (không cần thanh phải tròn để "lăn" trong bạc,
      cơ cấu này vốn dĩ không cho thanh quay quanh trục nó).
  KHÔNG đổi cả 2 bạc thành lỗ vuông KHÍT: giữ nguyên kiến trúc "A định vị khít + B chỉ
  chặn xoay (rộng theo Y)" của bản trục tròn — 2 lỗ khít trên một chi tiết in vẫn là
  SIÊU TĨNH bất kể tiết diện tròn hay vuông, xem mục dưới.
  2026-09-07 (lần 35→36): CẢ Guide_Rod_A VÀ B ĐỔI thành TRỤ TRÒN cắt phẳng đáy —
  phương án "tròn khoét bẹt một mặt" (bám bàn như vuông, trơn hơn vuông trên máy đời
  cũ). Chống xoay vẫn do CẶP 2 thanh (A khít + B rãnh rộng Y), không cần tiết diện vuông.

VÌ SAO 2 THANH DẪN HƯỚNG (bản ty ren chỉ cần 1):
  Bản ty ren dùng đai ốc + trục trơn = 2 ràng buộc song song nên thanh không xoay được.
  Ở đây ăn khớp răng KHÔNG chặn được thanh xoay quanh thanh dẫn hướng (xoay là NHẢ
  KHỚP). Nên phải có thanh thứ hai. Bạc thứ hai LÀ LỖ RỘNG chứ không phải lỗ khít: hai
  lỗ khít trên một chi tiết in là siêu tĩnh, sai số in / cong vênh sẽ làm kẹt.

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
  3. Ép Pinion lên trục ĐC (2 mặt vát tự canh), đáy bánh răng tì gờ O9.0
  4. Thả Slide_Bar thẳng từ trên xuống, cưỡi lên bánh răng, canh cho răng vào khớp
  5. Đẩy Guide_Rod_A rồi Guide_Rod_B (cả hai TRÒN đáy phẳng) TỪ NGOÀI vách +X vào,
     xuyên bạc, tì đáy hốc mù -X — lắp ở BẤT KỲ góc xoay nào cũng vừa (bạc A tròn
     khít; bạc B rãnh rộng Y chỉ chặn xoay)
  6. Úp Guide_Rod_Cap_A/B phẳng lên mặt ngoài vách +X (đầu thanh đã phẳng khít mặt vách
     sẵn), bắt 1 vít tự ren M3 mỗi cái XUYÊN QUA lỗ ROD_ACCESS_D trên vách rồi bắt THẲNG
     vào lỗ mồi ở đầu chính thanh (không có trụ riêng nào trên Housing) — vít KÉO thanh
     áp sát nắp, ép nắp áp sát vách, KHOÁ thanh khỏi xô lệch dọc trục (tháo lại được:
     chỉ cần tháo 2 vít này)
  7. Luồn dây vào máng, ra khe trên vách -X
  8. Hạ nắp thẳng từ trên xuống (trụ gá tải chui qua khe), bắt 4 vít M3 góc
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
# 1. ĐỘNG CƠ 28BYJ-48  (chốt 2026-09-06 theo bản vẽ nhà sản xuất người dùng gửi —
# thay cho phần lớn GIẢ ĐỊNH trước đó; xem cuối khối này về chỗ CÒN CHƯA CHỐT)
# ---------------------------------------------------------------------------
# Các hãng làm 28BYJ-48 khác nhau chút ở khối nối dây và bề dày tai. 4 số quan trọng
# nhất (O28, cao 19, lệch tâm 8, tai cách 35) thì thống nhất giữa các hãng.
MOT_D = 28.0                  # Ø thân
MOT_H = 19.0                  # cao thân (mặt dưới -> MẶT TRÊN có trục)
MOT_SHAFT_OFF = 8.0           # trục LỆCH TÂM 8 mm — ở đây hướng lệch là +X
MOT_SHAFT_D = 5.0
MOT_SHAFT_FLAT = 3.0          # khoảng cách 2 mặt vát (double-D)
MOT_SHAFT_FLAT_L = 6.0         # chiều dài đoạn CÓ VÁT, tính từ ĐẦU trục (chốt 2026-09-06
                                # lần 24, người dùng xác nhận qua bản vẽ: tổng trục nhô
                                # ra 10mm, "phần côn vát là 6mm" — CHỈ 6mm gần đầu có
                                # vát, phần còn lại (gờ Ø9 + đoạn tròn trơn phía dưới,
                                # tổng 4mm) VẪN TRÒN, không vát suốt cả 10mm như bản
                                # trước. Xem MOT_SHAFT_FLAT_Z0 bên dưới (sau khi có
                                # MOT_SHAFT_TOP) và make_pinion() — lỗ Pinion PHẢI đổi
                                # theo cho khớp (tròn ở dưới, vát chỉ ở trên).
MOT_SHAFT_L = 10.0            # trục nhô trên MẶT TRÊN thân — CHỐT 2026-09-06 (lần 23):
                                # "10" LÀ tổng chiều dài trục (đầu dãy dimension-chain
                                # trên cùng, liền kề "19" = cao thân, cùng 1 đường kích
                                # thước liên tục đo từ đầu trục -> hết thân). Số "6" bên
                                # cạnh cụm Ø9/5/3/1.5 chỉ là ĐOẠN CÓ VÁT 2 mặt (nằm
                                # TRONG 10mm đó, gần đầu trục) — chi tiết phụ, model này
                                # vát PHẲNG suốt cả 10mm (dư ra so với hàng thật chỉ vát
                                # 6mm gần đầu) là đơn giản hoá AN TOÀN, không ảnh hưởng
                                # khớp Pinion.
MOT_BOSS_D = 9.0               # gờ quanh chân trục — chốt theo bản vẽ (Ø9, trước 9.1)
MOT_BOSS_H = 1.5               # chốt theo bản vẽ (khớp cả 2 hình chi tiết trục)
# TRỤC TÁCH RIÊNG khỏi thân (chốt 2026-09-06, người dùng yêu cầu): trước đây trục được
# fuse() thẳng vào thân — dựng đúng nhưng KHÔNG thể hiện được việc trục quay tự do so
# với thân đứng yên (khác thực tế: thân là vỏ nhựa đứng yên, trục quay bên trong qua ổ
# bi/bạc). Giờ BYJ_Motor (thân, có LỖ quanh trục) và BYJ_Motor_Shaft (trục, đứng riêng)
# là 2 Part::Feature khác nhau, khe hở MOT_SHAFT_CLR quanh nhau — xoay được độc lập
# trong FreeCAD (đổi Placement.Rotation của BYJ_Motor_Shaft để animate). Khe hở đủ rộng
# để IN 3D IN-PLACE được (2 khối in cùng lúc, đúng vị trí lắp — xem
# export_byj_rack_print.py hàm export_motor_print_in_place).
# 2026-09-06 (lần 22): người dùng in thử BYJ_Motor_PrintInPlace.stl trên Ender-3 Pro —
# trục BỊ DÍNH CỨNG, không quay được. 0.6mm (khe hở BÁN KÍNH chỉ 0.3mm mỗi bên) NHỎ HƠN
# bề rộng 1 đường nhựa (0.4mm, nozzle phổ thông) — Cura/slicer không "vẽ" nổi 1 bức
# tường mỏng hơn nozzle ở khe đó, 2 bên chồng nhựa lên nhau thành ĐẶC luôn, không phải
# chỉ dính ở đáy. Tăng lên 1.0mm (khe BÁN KÍNH 0.5mm/bên — RỘNG HƠN 1 nozzle, kèm bù trừ
# Horizontal Expansion phía dưới) mới đủ AN TOÀN cho dung sai in thật của máy phổ thông.
# 2026-09-07 (lần 32): người dùng muốn GIẢM LẮC khi quay — thử thu hẹp 1.0→0.7mm
# (chưa có số liệu in thử thật ở mức này). Ngay sau đó (lần 33) tăng chiều dài đoạn ôm
# trục (MOT_SHAFT_BURY) để giảm lắc bằng đòn bẩy dài hơn thay vì khe hở hẹp hơn. Người
# dùng sau đó chủ động chọn AN TOÀN ("nếu rủi ro, tăng khe hở lên") — QUAY LẠI 1.0mm
# (giá trị ĐÃ CHỨNG MINH không dính trên Ender-3 Pro, xem lần 22), GIỮ NGUYÊN đoạn ôm
# trục dài hơn (lần 33, MOT_SHAFT_BURY=5.0) để bù lại độ lắc — kết hợp này AN TOÀN HƠN
# bản gốc lần 22 (đòn bẩy dài hơn ~gấp đôi ở CÙNG khe hở đã chứng minh an toàn).
MOT_SHAFT_CLR = 1.0            # khe hở ĐƯỜNG KÍNH quanh trục trong lỗ (in-place)
MOT_SHAFT_BORE = MOT_SHAFT_D + MOT_SHAFT_CLR       # 6.0  lỗ (đoạn trục trơn), quanh trục
# 2026-09-07 (lần 33): người dùng yêu cầu tăng chiều dài đoạn ÔM TRỤC (đoạn trục tròn
# trơn được THÂN bao quanh, tính cả đoạn chôn dưới mặt thân lẫn xuyên gờ Ø9 — "hình trụ
# đáy") để chống LẮC — đòn bẩy dài hơn thì cùng 1 khe hở (0.7mm) gây góc lắc nhỏ hơn hẳn.
# Tăng 3.0→5.0mm (dài thêm 2mm) — CHỈ kéo dài đoạn CHÔN trong thân (buried_neck), KHÔNG
# đụng tới chiều cao gờ Ø9 thật (MOT_BOSS_H, đã chốt theo bản vẽ) hay gờ giữ trục
# (MOT_SHAFT_RET_H) — "lỗ trong động cơ" (neck bore trong make_motor_body) tự động dài
# thêm tương ứng vì tính theo công thức phụ thuộc MOT_SHAFT_BURY.
MOT_SHAFT_BURY = 5.0           # đoạn trục CHÔN xuống trong thân (tròn) — cho trục có
                                # "gốc" nằm trong lỗ thay vì lơ lửng hoàn toàn phía trên
                                # mặt thân; datasheet không ghi trị này, tự chọn hợp lý
# GỜ GIỮ TRỤC chống tuột (lần 22, người dùng yêu cầu "trục không tuột khỏi động cơ"):
# trước đây lỗ trong thân là 1 ống thẳng đường kính KHÔNG ĐỔI suốt chiều sâu chôn — trục
# CHỈ dính tạm ở đáy lúc in (witness layer) để có chỗ tựa, không hề có gờ chặn thật —
# về mặt CƠ HỌC, sau khi bẻ lớp dính đáy để trục quay được thì KHÔNG GÌ giữ trục khỏi
# tuột thẳng lên trên. Giải pháp: 1 GỜ (flange) đường kính lớn hơn phần trục trơn phía
# trên, nằm trong 1 khoang RỘNG HƠN riêng ở ĐÁY lỗ — gờ không lọt qua được lỗ trục trơn
# (MOT_SHAFT_BORE) phía trên nó -> giữ trục không tuột lên, trong khi vẫn có khe hở
# quanh + phía trên gờ để quay tự do (không fuse cứng như witness layer cũ).
MOT_SHAFT_RET_D = MOT_SHAFT_D + 2.0                # 7.0  Ø gờ giữ (lớn hơn Ø trục trơn)
MOT_SHAFT_RET_CLR = 1.0                            # khe hở ĐƯỜNG KÍNH quanh gờ giữ
MOT_SHAFT_RET_BORE = MOT_SHAFT_RET_D + MOT_SHAFT_RET_CLR   # 8.0  Ø khoang chứa gờ
MOT_SHAFT_RET_H = 1.5                              # cao gờ giữ
MOT_SHAFT_RET_TOP_CLR = 0.4    # hở PHÍA TRÊN gờ giữ (không chạm trần khoang — tránh
                                # thêm 1 mặt dính khi in, chỉ đáy khoang mới cố ý chạm)
# 2026-09-06/07 (lần 26-31, đúc kết từ build_28byj48_reference.py — xem memory dự án):
# gờ giữ TỰA THẲNG lên đáy khoang (witness layer full-face, `distToShape()`=0.0 — CÓ
# CHẠM THẬT) vẫn là rủi ro dính chặt y hệt bài học lần 22, chỉ đổi từ "khe hở quanh trục"
# sang "khe hở đáy gờ". Áp dụng lại kỹ thuật đã kiểm chứng: gờ LƠ LỬNG (không chạm đáy
# khoang) + SỢI TƠ MẢNH (vành khuyên góc, xem _wedge_ring/_strut_pair) + 1 CHỐT TÂM nhỏ
# nối thẳng đáy khoang <-> đáy gờ (giải quyết đúng giới hạn hình học: hỗ trợ CHỈ ở rìa
# gờ KHÔNG BAO GIỜ đỡ được điểm ở TÂM đĩa, dù thêm bao nhiêu sợi rìa — đã xác nhận với
# người dùng, Ender-3 Pro không bắc cầu nổi khoảng cách ~3.5mm ở lớp in đầu tiên).
MOT_SHAFT_RET_FLOOR_GAP = 0.3  # khe hở DƯỚI gờ giữ — KHÔNG chạm đáy khoang nữa
MOT_SHAFT_RET_STRUT_N = 10     # số sợi tơ quanh gờ giữ (đủ dày để khe hở cung <2.1mm,
                                # an toàn bắc cầu trên Ender-3 Pro — xem tính toán trong
                                # hội thoại lần 28)
MOT_SHAFT_RET_STRUT_ANGLE = 4.0    # độ rộng CUNG (góc, độ) mỗi sợi
MOT_SHAFT_RET_STRUT_H = 0.4    # cao sợi (Z) — CHỈ ở đáy gờ giữ (nơi cần đỡ lớp in đầu
                                # tiên nhất), không cao hết cả gờ -> dễ bẻ hơn (lần 31)
MOT_SHAFT_RET_PIN_D = 0.6      # Ø chốt tâm — nối đáy khoang <-> đáy gờ, dệt tích cực
                                # nhỏ (~0.3mm²) nên vẫn dễ bẻ như sợi tơ
assert MOT_SHAFT_RET_D > MOT_SHAFT_BORE            # gờ PHẢI to hơn lỗ trục trơn phía
                                                    # trên nó, nếu không sẽ tuột lọt qua
assert (MOT_SHAFT_RET_FLOOR_GAP + MOT_SHAFT_RET_H + MOT_SHAFT_RET_TOP_CLR
       < MOT_SHAFT_BURY)                          # còn dư đoạn trục trơn phía trên gờ
                                                    # để dẫn hướng trong thân
MOT_EAR_SPAN = 35.0           # tâm-tâm 2 lỗ tai, trên đường VUÔNG GÓC hướng lệch tâm
MOT_EAR_T = 1.0                 # tai thép mỏng — chốt theo bản vẽ (trước 0.8)
MOT_EAR_W = 7.0               # bề rộng tai (theo X)
MOT_EAR_HOLE = 4.0             # chốt theo bản vẽ (Ø4, trước 4.2)
MOT_EAR_TIP = 21.0            # bán kính tới mép ngoài tai
MOT_CONN_W = 14.6             # khối nối dây, nhô ra phía -X (xa bánh răng)
MOT_CONN_H = 16.6
MOT_CONN_OUT = 5.0            # nhô ra khỏi Ø28
MOT_CONN_IN = 3.0             # ăn vào TRONG đường kính thân
# GỜ NỐI nhỏ giữa thân trụ và khối nối dây (chốt 2026-09-06, người dùng chỉ ra trên
# bản vẽ, hình chi tiết dưới-trái) — CÓ 2 GỜ, nằm ở 2 GÓC GIAO giữa khối nối dây (hình
# hộp) và thân (hình trụ), tức 2 mép Y = +-MOT_CONN_W/2 của khối nối dây, KHÔNG phải 1
# gờ ở giữa. Mỗi gờ nhô ra từ MẶT TRỤ THÂN, chạy dọc theo HƯỚNG TRỤC (song song trục
# Z). Không có số đo vị trí/độ nhô rõ trên bản vẽ (chỉ chắc chắn chiều dài = 6) — TỰ
# CHỌN độ nhô/bề rộng hợp lý (chi tiết trang trí/gia cố nhỏ, không ảnh hưởng khe hở
# nào khác trong thiết kế).
MOT_RIB_L = 6.0                # dài theo Z (dọc trục)
MOT_RIB_W = 1.6                 # rộng theo Y mỗi gờ — ước lượng, PHẢI nằm trong khe hở
                                # 1mm mà vành định vị ĐC (ring) đã chừa quanh khối nối
                                # dây (Housing chưa biết có gờ này) — xem assert dưới
MOT_RIB_PROUD = 0.4            # nhô ra khỏi mặt trụ thân — PHẢI nhỏ hơn khe hở 0.5mm
                                # chung quanh thân ĐC (Housing cắt "khe hở quanh thân
                                # động cơ" ở đúng mức đó) — xem assert dưới

# Điện / cơ tính (dùng cho phần in thông số, không dựng hình)
MOT_DETENT = 34.3             # N.mm, self-positioning torque KHI ĐÃ TẮT ĐIỆN
MOT_RPM = 12.0                # vòng/phút thực tế đạt được (datasheet: out-traction >1000 Hz)
LOAD_N = 0.2                  # lực dọc trục thật (thanh nhựa vài gam + ma sát)

# ---------------------------------------------------------------------------
# 2. BÁNH RĂNG + THANH RĂNG
# ---------------------------------------------------------------------------
# m,z chọn sao cho STEPS_PER_MM nguyên đẹp: m = 4096/(STEPS_PER_MM · π · z)
# → mm/xung ≈ 1/N đúng tới sai số pi (thực dụng = 0 trong dải 2..30 mm).
# 2026-09-07: tăng Ø đỉnh 19.7 → ~24.1 (z19/N73 → z22/N59), vẫn t_full < 4s.
GEAR_Z = 22
GEAR_PA = 20.0                # góc áp lực
GEAR_FACE = 5.0               # bề rộng răng
GEAR_BL = 0.12                # rơ ăn khớp: bớt bề dày răng mỗi bên (cả pinion và rack)
MOTOR_STEPS_PER_REV = 4096.0   # 28BYJ-48 half-step
STEPS_PER_MM = 59              # HẰNG SỐ FIRMWARE: bước/mm (dùng trong code điều khiển)
GEAR_M = MOTOR_STEPS_PER_REV / (STEPS_PER_MM * math.pi * GEAR_Z)
# Đã BỎ moay-ơ dưới vành răng. Đỉnh trụ+bán cầu Ø PIN_CAP_D đẩy cầu Slide_Bar lên.
PIN_R = GEAR_M * GEAR_Z / 2.0
PIN_RA = PIN_R + GEAR_M
PIN_RF = PIN_R - 1.25 * GEAR_M
assert 2.0 * PIN_RF > 8.0                      # thân bánh răng (không tính răng) > 8mm
PIN_MM_PER_REV = 2.0 * math.pi * PIN_R
GEAR_PITCH = math.pi * GEAR_M
_TRUE_STEPS_PER_MM = MOTOR_STEPS_PER_REV / PIN_MM_PER_REV
_STEPS_PER_MM_ERR = abs(STEPS_PER_MM - _TRUE_STEPS_PER_MM) / _TRUE_STEPS_PER_MM
assert _STEPS_PER_MM_ERR < 0.001, "STEPS_PER_MM lech qua 0.1%% so voi so that, tinh lai"

TRAVEL = 30.0                 # HÀNH TRÌNH YÊU CẦU
# Biên mỗi đầu phải phủ ≥ bán kính đỉnh bánh — nếu không tip đụng fill khi quét hết hành trình
RACK_MARGIN = PIN_RA + 0.5
RACK_L = TRAVEL + 2.0 * RACK_MARGIN
RACK_BACK = 1.75              # bề dày lưng thanh răng, tính từ CHÂN răng
assert RACK_MARGIN + 1e-9 >= PIN_RA, "RACK_MARGIN phai phu kin O dinh banh"

# ---------------------------------------------------------------------------
# 3. BỐ TRÍ CHUNG. Gốc: TRỤC BÁNH RĂNG tại (x, y) = (0, 0). Đáy hộp z = 0.
# ---------------------------------------------------------------------------
BASE_T = 3.0                  # sàn
MOT_Z0 = BASE_T                                # ĐC ngồi thẳng trên sàn
MOT_TOP = MOT_Z0 + MOT_H                       # 22.0  mặt trên thân
# Tai bắt vít PHẲNG với mặt trên thân, KHÔNG lồi lên trên (chốt 2026-09-06, theo đúng
# hình 3D bản vẽ nhà sản xuất) — tai nằm NGAY DƯỚI mặt trên thân, mặt trên của tai
# TRÙNG mặt trên thân, không phải thò thêm lên trên như bản trước.
MOT_EAR_Z0 = MOT_TOP - MOT_EAR_T               # 21.0  mặt dưới tai
MOT_EAR_Z1 = MOT_TOP                           # 22.0  mặt trên tai = mặt trên thân
MOT_SHAFT_TOP = MOT_TOP + MOT_SHAFT_L          # 32.0  đỉnh trục
MOT_SHAFT_FLAT_Z0 = MOT_SHAFT_TOP - MOT_SHAFT_FLAT_L   # 26.0  z BẮT ĐẦU đoạn có vát
                                                # (phía dưới z này, trục TRÒN TRƠN —
                                                # xem MOT_SHAFT_FLAT_L)
assert MOT_SHAFT_FLAT_Z0 > MOT_TOP + MOT_BOSS_H  # đoạn vát phải nằm TRÊN gờ Ø9 (đoạn
                                                # tròn giữa gờ và chỗ vát còn dư > 0)
# --- NẮP CHỤP ĐẦU TRỤC trên Pinion (trụ + bán cầu Ø PIN_CAP_D, KHÔNG moay-ơ dưới) ---
# Trụ+bán cầu bọc kín đoạn trục thò trên vành răng. Đỉnh bán cầu (PIN_DOME_TOP) quyết
# chiều cao cầu Slide_Bar (BAR_LEG_Z1).
PIN_CAP_D = 10.0                               # Ø trụ + bán cầu trên đỉnh bánh răng
PIN_BORE_CLR = 0.25                            # khe lỗ / trục (dễ lắp)
PIN_CAP_BLIND_CLR = 1.0                        # khe hở đáy lỗ mù, phía trên đỉnh trục thật
PIN_CAP_TOP = MOT_SHAFT_TOP + PIN_CAP_BLIND_CLR            # đỉnh phần trụ = đáy bán cầu
PIN_DOME_R = PIN_CAP_D / 2.0                   # bán kính bán cầu = bán kính trụ, liền mạch
PIN_DOME_TOP = PIN_CAP_TOP + PIN_DOME_R        # đỉnh bán cầu — điểm CAO NHẤT cần né qua
EAR_SCREW_D = 3.0             # vít TỰ REN M3 bắt tai xuống trụ
EAR_SCREW_HEAD_D = 5.6
EAR_SCREW_HEAD_H = 2.0
EAR_SCREW_TOP = MOT_EAR_Z1 + EAR_SCREW_HEAD_H  # 24.0  đỉnh mũ vít bắt tai
EAR_PILOT_D = 2.5             # lỗ mồi trong trụ cho vít tự ren M3
EAR_SCREW_L = 8.0
EAR_POST_W = 8.0              # trụ bắt tai: X
EAR_POST_Y = 6.0              # trụ bắt tai: Y — mép trong phải NGOÀI Ø thân ĐC

BAR_CLR_MOT = 0.8             # khe thanh <-> mũ vít bắt tai ĐC
BAR_Z0 = EAR_SCREW_TOP + BAR_CLR_MOT           # 25.6  ĐÁY THANH (và đáy 2 chân П)
GEAR_Z0 = BAR_Z0 + 0.4                         # 26.0  đáy bánh răng / thanh răng
GEAR_Z1 = GEAR_Z0 + GEAR_FACE                  # 31.0
assert GEAR_Z1 <= MOT_SHAFT_TOP - 0.5          # bánh răng phải nằm trọn trên trục

ROD_D = 5.0                    # Ø thanh dẫn hướng TRÒN (A và B) — đáy phẳng dễ in
ROD_BORE = ROD_D + 0.4                         # bạc A: lỗ tròn khít Ø(ROD_D+0.4)
BAR_WALL = 1.3                                 # thịt quanh bạc
# Cả A và B: TRỤ TRÒN cắt phẳng đáy (bám bàn in). Chống xoay do CẶP 2 thanh: A khít,
# B trong rãnh rộng theo Y (chỉ chặn xoay, không siêu tĩnh).
ROD_FLAT_DEPTH = 1.0           # cắt phẳng đáy sâu 1.0mm — dải bám bàn ~4mm
assert ROD_FLAT_DEPTH < ROD_D / 2.0
BAR_LEG_Z1 = PIN_DOME_TOP + 0.4                 # đáy CẦU (phải trên đỉnh BÁN CẦU nắp Pinion)
BRIDGE_T = 2.0
BAR_Z1 = BAR_LEG_Z1 + BRIDGE_T                 # 34.4  NÓC THANH
# Bạc nằm trong CHÂN, mà chân cao HẾT thân thanh (cầu chỉ lấp khoảng giữa 2 chân ở
# phần trên đỉnh trục) — nên mốc của bạc là BAR_Z1, KHÔNG phải BAR_LEG_Z1.
ROD_Z = 0.5 * (BAR_Z0 + BAR_Z1)                # 30.0
assert ROD_Z + ROD_BORE / 2.0 + BAR_WALL <= BAR_Z1 + 1e-9
assert ROD_Z - ROD_BORE / 2.0 - BAR_WALL >= BAR_Z0 - 1e-9

# --- bố trí theo Y (bánh răng ở y = 0) ---
RACK_PITCH_Y = PIN_R                           # đường chia thanh răng
RACK_TIP_Y = RACK_PITCH_Y - GEAR_M             # đỉnh răng (chĩa về -Y)
RACK_ROOT_Y = RACK_PITCH_Y + 1.25 * GEAR_M     # chân răng
RACK_BACK_Y = RACK_ROOT_Y + RACK_BACK          # lưng thanh răng
ROD_SLOT_Y = 0.5                               # rãnh bạc B nới Y (đủ chống siêu tĩnh;
                                                # quá rộng → yaw lớn, răng chèn khi lệch)
EAR_POST_YC = MOT_EAR_SPAN / 2.0               # +-17.5  tâm 2 trụ bắt tai
# Trục A (định vị): đủ ngoài lưng rack + bạc; không thấp hơn tâm tai ĐC.
ROD_A_Y = max(
    EAR_POST_YC,
    RACK_BACK_Y + BAR_WALL + ROD_BORE / 2.0 + 0.5,
)
# RÃNH П đủ rộng = Ø đỉnh bánh (2*PIN_RA) — lắp ngang từ đầu thanh.
LEG_B_Y1 = RACK_TIP_Y - 2.0 * PIN_RA - 0.5     # mặt trong chân -Y, đủ né CẢ bánh răng
ROD_B_Y = LEG_B_Y1 - ROD_BORE / 2.0 - ROD_SLOT_Y / 2.0 - BAR_WALL - 0.25
BAR_Y1 = ROD_A_Y + ROD_BORE / 2.0 + BAR_WALL
BAR_Y0 = ROD_B_Y - ROD_BORE / 2.0 - ROD_SLOT_Y / 2.0 - BAR_WALL
assert RACK_BACK_Y + BAR_WALL <= ROD_A_Y - ROD_BORE / 2.0 + 1e-9
assert ROD_B_Y + ROD_BORE / 2.0 + ROD_SLOT_Y / 2.0 + BAR_WALL <= LEG_B_Y1 + 1e-9

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
SW_LEVER_GAP = 2.5                             # bánh xe cách mép +Y thân CT
# SW_YC: bánh xe phải ấn trúng chân +Y (>= RACK_ROOT_Y); thân CT lọt giữa 2 trục.
SW_YC = max(4.0, RACK_ROOT_Y - SW_L / 2.0 + SW_LEVER_GAP + 0.2)
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
ROD_END_GAP = 0.15             # đầu +X của thanh LÙI VÀO 0.15mm so với mặt ngoài vách
                                # -> nắp Rod_Cap ép SÁT VÁCH được (không bị thanh chặn
                                # hờ ở giữa), mà thanh vẫn coi như PHẲNG KHÍT mặt vách
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
ROD_LEN = (BOX_X1 - ROD_END_GAP) - ROD_X0
ROD_ACCESS_D = ROD_D + 0.4    # lỗ xuyên vách +X
# Lỗ xuyên vách +X phải xuyên LUÔN qua 2 trụ nắp góc +X (đứng ngay trước vách, x =
# [INNER_X1-POST_W, INNER_X1], Y rất gần Y 2 thanh dẫn hướng) — xem bẫy đã bắt được
# trong make_housing(). CÓ 4 TRỤ NẮP GÓC (2 đầu -X, 2 đầu +X) — 2 trụ đầu -X (x =
# [INNER_X0, INNER_X0+POST_W]) cũng dính bẫy y hệt với hốc mù -X, phải xuyên nốt qua
# đó nữa. Constants này dùng chung giữa make_housing() và verify().
ROD_CLEAR_X0 = INNER_X1 - POST_W - 0.5
ROD_CLEAR_LEN = (INNER_X1 - 0.5 + WALL_T + 2.0) - ROD_CLEAR_X0
ROD_POCKET_CLEAR_LEN = (INNER_X0 + POST_W + 0.5) - ROD_X0

# --- NẮP CHẶN TRỤC (Rod_Cap), chốt 2026-09-06, ĐƠN GIẢN HOÁ LẦN 2 cùng ngày ---
# Đẩy thanh dẫn hướng từ ngoài vào tới khi tì đáy hốc mù -X là xong PHÍA -X, nhưng đầu
# +X trước đây chỉ có khe hở 0.4 mm quanh thanh và KHÔNG có gì chặn lại: rung động mỗi
# lần Slide_Bar quét qua quét lại làm thanh XÔ LỆCH dần theo X, thậm chí tuột ra ngoài.
# Đầu +X của thanh PHẲNG KHÍT với mặt ngoài vách (ROD_END_GAP chỉ để nắp ép sát được).
# VÍT XUYÊN THẲNG HÀNG VỚI TRỤC THANH: vít đi từ ngoài, qua lỗ nắp, qua ĐÚNG lỗ xuyên
# ROD_ACCESS_D sẵn có trên vách (không khoét thêm lỗ nào khác trên Housing), rồi tự ren
# vào lỗ mồi khoan sẵn Ở ĐẦU chính thanh dẫn hướng (ROD_TAP_D/ROD_TAP_L) — vít KÉO thanh
# áp sát nắp trong khi ép nắp áp sát vách, cùng lúc. Thanh bị kẹp giữa đáy hốc mù -X và
# lực kéo của vít ở +X, hết xô lệch. Vẫn THÁO ĐƯỢC: tháo vít, gỡ nắp, rút thanh ra.
# (2 bản trước: bản 1 có hốc cắm sâu + 2 chốt gài; bản 2 bỏ chốt nhưng vít vẫn bắt vào 1
# trụ RIÊNG trong Housing, lệch tâm 10mm theo Z để né lỗ ren nắp hộp. Bản này bỏ luôn
# trụ riêng đó — vít bắt thẳng vào CHÍNH thanh nên không cần trụ, không cần né lỗ ren
# nắp hộp nữa vì không còn khoét gì thêm trên vách cả.)
ROD_TAP_D = M3_TAP                 # lỗ mồi tự ren ở đầu thanh (dùng chung cỡ M3_TAP)
ROD_TAP_L = 8.0                    # sâu 8mm — cùng độ sâu ren với EAR_SCREW_L cho nhất quán
CAP_T = 3.0                        # bề dày nắp: đủ chỗ hốc chìm đầu vít (2.0) + 1mm thịt
CAP_PAD = 2.0                      # viền vật liệu quanh lỗ trục / quanh vít
CAP_W = max(ROD_BORE, EAR_SCREW_HEAD_D) + 2.0 * CAP_PAD        # 9.6  nắp vuông, tâm = trục thanh
CAP_SCREW_Z = ROD_Z                            # vít THẲNG HÀNG với tâm thanh, không lệch
CAP_Z0 = CAP_SCREW_Z - CAP_W / 2.0
CAP_Z1 = CAP_SCREW_Z + CAP_W / 2.0
assert ROD_TAP_L < ROD_LEN - 20.0                  # lo mo (khoan tu dau thanh) khong
                                                    # vuot qua het chieu dai thanh
assert M3_CLEAR < ROD_D                            # lo vit tren nap NHO HON tiet dien
                                                    # thanh -> thanh khong the lot qua
assert ROD_A_Y + CAP_W / 2.0 <= BOX_Y1 - 0.5       # nap khong tho qua mep hop
assert ROD_B_Y - CAP_W / 2.0 >= BOX_Y0 + 0.5

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


def _box_x(wy, wz, length, x0, y=0.0, z=0.0) -> Part.Shape:
    """Khối chữ nhật quét dọc X, tâm (y, z), cạnh wy (theo Y) x wz (theo Z), dài
    `length` từ x0. Dùng thay _cyl_x() cho thanh dẫn hướng VUÔNG (Guide_Rod) và bạc
    của nó — wy != wz cho bạc RÃNH (chặn xoay nhưng nới theo Y)."""
    return _box2(x0, x0 + length, y - wy / 2.0, y + wy / 2.0, z - wz / 2.0, z + wz / 2.0)


def _rod_shape_x(round_shape: bool, d, length, x0, y=0.0, z=0.0) -> Part.Shape:
    """Probe/lỗ thanh dẫn hướng. `round_shape=True` (mặc định A+B): trụ Ød.
    `False` giữ hộp vuông (legacy)."""
    if round_shape:
        return _cyl_x(d, length, x0, y, z)
    return _box_x(d, d, length, x0, y, z)


def _flat_round_rod_x(d, length, x0, y, z, flat_depth) -> Part.Shape:
    """Trụ tròn Ød cắt phẳng đáy — in nằm bàn trên máy đời cũ."""
    body = _cyl_x(d, length, x0, y, z)
    flat_z1 = z - d / 2.0 + flat_depth
    flat_cut = _box2(x0 - 0.5, x0 + length + 0.5,
                     y - d / 2.0 - 0.5, y + d / 2.0 + 0.5,
                     z - d / 2.0 - 1.0, flat_z1)
    return _cut(body, flat_cut)


def _flat_round_bore_x(d, length, x0, y, z, flat_depth, y_widen: float = 0.0) -> Part.Shape:
    """Lỗ tròn Ød (capsule nếu y_widen>0) + cung phẳng đáy khớp thanh ray đáy phẳng."""
    bore = _cyl_x(d, length, x0, y, z)
    if y_widen > 1e-9:
        bore = bore.fuse(_box_x(d + y_widen, d, length, x0, y, z))
    # Cung phẳng đáy: nới thêm dưới mặt phẳng của thanh (rod flat) một chút khe
    flat_z1 = z - d / 2.0 + flat_depth + 0.15
    flat_pocket = _box2(x0, x0 + length,
                        y - (d + y_widen) / 2.0 - 0.05,
                        y + (d + y_widen) / 2.0 + 0.05,
                        z - d / 2.0 - 0.05, flat_z1)
    return bore.fuse(flat_pocket)


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


def _wedge_ring(r0: float, r1: float, h: float, z0: float, angle_deg: float,
                n: int, cx: float, cy: float) -> Part.Shape:
    """n miếng VÀNH KHUYÊN GÓC (pie-slice annulus) từ bán kính r0 đến r1, cao h, cách
    đều quanh tâm (cx,cy) — mỗi miếng rộng angle_deg độ. Dùng CUNG TRÒN thật
    (Part.makeCylinder có angle) chứ KHÔNG dùng box phẳng — box có 2 mặt đầu PHẲNG chỉ
    tiếp xúc mặt trụ CONG theo 1 ĐƯỜNG (không phải 1 MẶT), khiến fuse() không gộp được
    thành 1 khối liên thông (bẫy đã gặp khi làm build_28byj48_reference.py — xem
    memory dự án). Dùng làm sợi tơ mảnh nối thân/trục, dễ bẻ khi xoay."""
    outer = Part.makeCylinder(r1, h, App.Vector(0, 0, z0), App.Vector(0, 0, 1), angle_deg)
    inner = Part.makeCylinder(r0, h, App.Vector(0, 0, z0), App.Vector(0, 0, 1), angle_deg)
    one = outer.cut(inner)
    one.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -angle_deg / 2.0)
    parts = []
    for i in range(n):
        s = one.copy()
        s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / n)
        s.translate(App.Vector(cx, cy, 0))
        parts.append(s)
    out = parts[0]
    for p in parts[1:]:
        out = out.fuse(p)
    return out


def _strut_pair(r0: float, r1: float, angle_deg: float, z0: float, z1: float,
                n: int, cx: float, cy: float) -> tuple[Part.Shape, Part.Shape]:
    """Chia sợi tơ làm 2 NỬA tại bán kính giữa (rmid): nửa trong (r0..rmid) thuộc VỀ
    TRỤC, nửa ngoài (rmid..r1) thuộc VỀ THÂN — 2 nửa CHẠM NHAU đúng 1 MẶT TRỤ CONG
    mỏng tại rmid (giống 1 "witness layer" nhưng TIẾT DIỆN RẤT NHỎ)."""
    rmid = 0.5 * (r0 + r1)
    shaft_half = _wedge_ring(r0, rmid, z1 - z0, z0, angle_deg, n, cx, cy)
    body_half = _wedge_ring(rmid, r1, z1 - z0, z0, angle_deg, n, cx, cy)
    return shaft_half, body_half


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
    """Bánh răng IN 3D liền khối: vành răng + trụ Ø PIN_CAP_D + bán cầu trên đỉnh.
    Không moay-ơ dưới. Lỗ mù bọc kín đầu trục ĐC."""
    pts = gear_profile(GEAR_M, GEAR_Z, GEAR_PA, GEAR_BL)
    vecs = [App.Vector(x, y, GEAR_Z0) for x, y in pts]
    vecs.append(vecs[0])
    face = Part.Face(Part.makePolygon(vecs))
    body = face.extrude(App.Vector(0, 0, GEAR_FACE))
    # trụ + bán cầu trên đỉnh bánh răng
    cap = _cyl_z(PIN_CAP_D, PIN_CAP_TOP - GEAR_Z1, 0.0, 0.0, GEAR_Z1)
    dome = Part.makeSphere(PIN_DOME_R, App.Vector(0.0, 0.0, PIN_CAP_TOP),
                           App.Vector(0, 0, 1), 0.0, 90.0, 360.0)
    body = body.fuse(cap).fuse(dome)
    # Lỗ mù từ đáy vành răng tới PIN_CAP_TOP. Đoạn dưới tròn / đoạn vát double-D.
    bore_d = MOT_SHAFT_D + PIN_BORE_CLR
    bore_z0 = GEAR_Z0
    bore_h = PIN_CAP_TOP - bore_z0
    flat_z0 = max(MOT_SHAFT_FLAT_Z0, bore_z0)
    if flat_z0 > bore_z0 + 0.2:
        round_bore = _cyl_z(bore_d, flat_z0 - bore_z0, 0.0, 0.0, bore_z0)
        flat_bore = _cyl_z(bore_d, bore_z0 + bore_h - flat_z0, 0.0, 0.0, flat_z0)
        flat = MOT_SHAFT_FLAT + PIN_BORE_CLR
        keep = _box2(-MOT_SHAFT_D, MOT_SHAFT_D, -flat / 2.0, flat / 2.0,
                     flat_z0 - 0.5, bore_z0 + bore_h)
        flat_bore = flat_bore.common(keep)
        bore = round_bore.fuse(flat_bore)
    else:
        flat_bore = _cyl_z(bore_d, bore_h, 0.0, 0.0, bore_z0)
        flat = MOT_SHAFT_FLAT + PIN_BORE_CLR
        keep = _box2(-MOT_SHAFT_D, MOT_SHAFT_D, -flat / 2.0, flat / 2.0,
                     bore_z0 - 0.5, bore_z0 + bore_h)
        bore = flat_bore.common(keep)
    body = _cut(body, bore)
    body = _refine(body)
    if abs(angle_deg) > 1e-9:
        body.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
    return body


def make_pinion_envelope() -> Part.Shape:
    """Bao hình Pinion trừ RĂNG (thân Ø chân răng + trụ nắp + bán cầu). Va chạm phần
    này khi lắp = LỖI; va chạm chỉ ở dải răng = bình thường (cần xoay canh khớp)."""
    root = _cyl_z(2.0 * PIN_RF, GEAR_FACE, 0.0, 0.0, GEAR_Z0)
    cap = _cyl_z(PIN_CAP_D, PIN_CAP_TOP - GEAR_Z1, 0.0, 0.0, GEAR_Z1)
    dome = Part.makeSphere(PIN_DOME_R, App.Vector(0.0, 0.0, PIN_CAP_TOP),
                           App.Vector(0, 0, 1), 0.0, 90.0, 360.0)
    return _refine(root.fuse(cap).fuse(dome))


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
# 8. Chi tiết mua sẵn (động cơ, công tắc) + thanh dẫn hướng in 3D
# ---------------------------------------------------------------------------
def make_motor_body() -> Part.Shape:
    """28BYJ-48 dựng đứng; tâm thân (MOT_CX, 0). KHÔNG gồm trục — xem make_motor_shaft().
    Có lỗ Ø(MOT_SHAFT_BORE) xuyên gờ + khoét sâu xuống thân (MOT_SHAFT_BURY) để trục
    lắp vào với khe hở MOT_SHAFT_CLR, quay tự do quanh trục Z."""
    body = _cyl_z(MOT_D, MOT_H, MOT_CX, 0.0, MOT_Z0)
    # 2 tai thép PHẲNG với mặt trên thân (không lồi lên), trên đường vuông góc hướng
    # lệch tâm (=> theo Y)
    for s in (+1.0, -1.0):
        ear = _box2(MOT_CX - MOT_EAR_W / 2.0, MOT_CX + MOT_EAR_W / 2.0,
                    min(0.0, s * MOT_EAR_TIP), max(0.0, s * MOT_EAR_TIP),
                    MOT_EAR_Z0, MOT_EAR_Z1)
        body = body.fuse(ear)
        hole = _cyl_z(MOT_EAR_HOLE, MOT_EAR_T + 1.0, MOT_CX, s * EAR_POST_YC,
                      MOT_EAR_Z0 - 0.5)
        body = _cut(body, hole)
    # gờ quanh chân trục
    body = body.fuse(_cyl_z(MOT_BOSS_D, MOT_BOSS_H, 0.0, 0.0, MOT_TOP))
    # lỗ cho trục: 2 TẦNG đường kính — khoang RỘNG ở đáy (chứa gờ giữ trục của
    # BYJ_Motor_Shaft, xem make_motor_shaft) rồi thu lại thành lỗ trục trơn xuyên hết
    # gờ Ø9 phía trên. Trục KHÔNG fuse vào đây, chỉ đặt lọt trong lỗ này.
    _bore_z0 = MOT_TOP - MOT_SHAFT_BURY                        # 19.0  đáy khoang giữ
    _chamber_h = (MOT_SHAFT_RET_FLOOR_GAP + MOT_SHAFT_RET_H
                 + MOT_SHAFT_RET_TOP_CLR)   # cao khoang (hở đáy + gờ + hở đỉnh)
    chamber = _cyl_z(MOT_SHAFT_RET_BORE, _chamber_h, 0.0, 0.0, _bore_z0)
    body = _cut(body, chamber)
    _neck_z0 = _bore_z0 + _chamber_h                           # đáy lỗ trục trơn, trên khoang giữ
    neck = _cyl_z(MOT_SHAFT_BORE, MOT_BOSS_H + MOT_SHAFT_BURY + 1.0 - _chamber_h,
                 0.0, 0.0, _neck_z0)
    body = _cut(body, neck)
    # Sợi tơ mảnh (nửa THÂN) nối với gờ giữ của trục — xem make_motor_shaft() và lần
    # 26-31 trong memory dự án: gờ giữ LƠ LỬNG (không tựa đáy khoang), chỉ nối qua
    # SỢI TƠ MẢNH (dễ bẻ khi xoay) + 1 chốt tâm nhỏ (thuộc về trục, xem bên dưới).
    _flange_z0 = _bore_z0 + MOT_SHAFT_RET_FLOOR_GAP
    _, _struts_body = _strut_pair(MOT_SHAFT_RET_D / 2.0, MOT_SHAFT_RET_BORE / 2.0,
                                  MOT_SHAFT_RET_STRUT_ANGLE, _flange_z0,
                                  _flange_z0 + MOT_SHAFT_RET_STRUT_H,
                                  MOT_SHAFT_RET_STRUT_N, 0.0, 0.0)
    body = body.fuse(_struts_body)
    # khối nối dây, nhô về -X
    conn = _box2(MOT_CONN_X0, MOT_CONN_X1,
                 -MOT_CONN_W / 2.0, MOT_CONN_W / 2.0,
                 MOT_Z0 + 1.0, MOT_Z0 + 1.0 + MOT_CONN_H)
    body = body.fuse(conn)
    # 2 gờ nối nhỏ Ở 2 GÓC GIAO giữa khối nối dây và thân trụ (y = +-MOT_CONN_W/2),
    # dọc trục Z. ĐÁY GỜ BẰNG ĐÁY KHỐI NỐI DÂY (z = MOT_Z0 + 1.0, không phải đáy thân
    # MOT_Z0 — khối nối dây tự nó cũng hụt 1mm so với đáy thân, xem MOT_CONN_H). Mặt
    # trụ CONG nên ở y = +-MOT_CONN_W/2 nó KHÔNG còn ở đúng bán kính MOT_D/2 nữa (đó là
    # điểm lồi nhất, chỉ đúng tại y=0) — phải tính lại đúng điểm trên mặt trụ tại y đó,
    # nếu không gờ sẽ lơ lửng ngoài mặt thân, không fuse dính vào đâu cả.
    _rib_x_edge = MOT_CX - math.sqrt((MOT_D / 2.0) ** 2 - (MOT_CONN_W / 2.0) ** 2)
    _rib_z0 = MOT_Z0 + 1.0                     # bằng đáy khối nối dây
    for _s in (1.0, -1.0):
        _rib_y = _s * MOT_CONN_W / 2.0
        rib = _box2(_rib_x_edge - MOT_RIB_PROUD, _rib_x_edge + 2.0,
                   _rib_y - MOT_RIB_W / 2.0, _rib_y + MOT_RIB_W / 2.0,
                   _rib_z0, _rib_z0 + MOT_RIB_L)
        body = body.fuse(rib)
    return _refine(body)


def make_motor_shaft() -> Part.Shape:
    """Trục ĐC, TÁCH RIÊNG khỏi thân (khe hở MOT_SHAFT_CLR quanh nó trong lỗ của
    make_motor_body) — quay tự do quanh trục Z, không fuse với thân. Đáy trục có GỜ GIỮ
    (MOT_SHAFT_RET_D) nằm trong khoang rộng của thân — gờ LƠ LỬNG (không chạm đáy khoang,
    chốt lần 26-31 sau khi phát hiện witness-layer full-face vẫn CÓ CHẠM THẬT — xem
    memory dự án), chỉ nối với thân qua SỢI TƠ MẢNH quanh rìa (dễ bẻ khi xoay) + 1 CHỐT
    TÂM nhỏ (giải quyết giới hạn hình học: hỗ trợ chỉ ở rìa không bao giờ đỡ được điểm ở
    TÂM đĩa). Gờ KHÔNG lọt qua được lỗ trục trơn phía trên -> giữ trục không tuột lên.
    Đoạn trục trơn (chôn, giữa gờ và mặt thân) tròn Ø(MOT_SHAFT_D); đoạn nhô khỏi thân
    CŨNG TRÒN TRƠN cho tới MOT_SHAFT_FLAT_Z0 — CHỈ đoạn cuối MOT_SHAFT_FLAT_L (gần đầu
    trục) mới vát 2 mặt (double-D, MOT_SHAFT_FLAT), đúng theo bản vẽ + xác nhận người
    dùng (lần 24): tổng nhô ra 10mm, chỉ 6mm ở đầu có vát."""
    _bore_z0 = MOT_TOP - MOT_SHAFT_BURY                         # 19.0  đáy khoang (thân)
    _flange_z0 = _bore_z0 + MOT_SHAFT_RET_FLOOR_GAP             # 19.3  đáy gờ giữ (LƠ LỬNG)
    ret = _cyl_z(MOT_SHAFT_RET_D, MOT_SHAFT_RET_H, 0.0, 0.0, _flange_z0)
    buried_neck = _cyl_z(MOT_SHAFT_D,
                        MOT_TOP - (_flange_z0 + MOT_SHAFT_RET_H),
                        0.0, 0.0, _flange_z0 + MOT_SHAFT_RET_H)
    # đoạn TRÒN TRƠN nhô khỏi thân (từ mặt thân tới ngay trước chỗ vát) — bao gồm cả
    # đoạn còn nằm trong gờ Ø9 của thân (không quan trọng, bị gờ che khuất) lẫn đoạn
    # thật sự lộ ra ngoài phía trên gờ
    round_top = _cyl_z(MOT_SHAFT_D, MOT_SHAFT_FLAT_Z0 - MOT_TOP, 0.0, 0.0, MOT_TOP)
    exposed_flat = _cyl_z(MOT_SHAFT_D, MOT_SHAFT_FLAT_L, 0.0, 0.0, MOT_SHAFT_FLAT_Z0)
    keep = _box2(-MOT_SHAFT_D, MOT_SHAFT_D, -MOT_SHAFT_FLAT / 2.0, MOT_SHAFT_FLAT / 2.0,
                 MOT_SHAFT_FLAT_Z0, MOT_SHAFT_TOP + 1.0)
    # sợi tơ mảnh (nửa TRỤC) + 1 chốt tâm nối thẳng đáy khoang <-> đáy gờ giữ
    _struts_shaft, _ = _strut_pair(MOT_SHAFT_RET_D / 2.0, MOT_SHAFT_RET_BORE / 2.0,
                                   MOT_SHAFT_RET_STRUT_ANGLE, _flange_z0,
                                   _flange_z0 + MOT_SHAFT_RET_STRUT_H,
                                   MOT_SHAFT_RET_STRUT_N, 0.0, 0.0)
    center_pin = _cyl_z(MOT_SHAFT_RET_PIN_D, MOT_SHAFT_RET_FLOOR_GAP,
                        0.0, 0.0, _bore_z0)
    shaft = (ret.fuse(buried_neck).fuse(round_top).fuse(exposed_flat.common(keep))
            .fuse(_struts_shaft).fuse(center_pin))
    return _refine(shaft)


def make_guide_rod(y: float, round_shape: bool = True) -> Part.Shape:
    """Thanh dẫn hướng TRÒN Ø(ROD_D) cắt phẳng đáy — in nằm bàn (máy đời cũ).
    A và B cùng hình; bạc B trên Slide_Bar nới theo Y để chống xoay không siêu tĩnh.
    Đầu +X: lỗ mồi tự ren cho Rod_Cap."""
    body = _flat_round_rod_x(ROD_D, ROD_LEN, ROD_X0, y, ROD_Z, ROD_FLAT_DEPTH)
    if not round_shape:
        # legacy vuông — không dùng nữa
        body = _box_x(ROD_D, ROD_D, ROD_LEN, ROD_X0, y, ROD_Z)
    tap_x0 = ROD_X0 + ROD_LEN - ROD_TAP_L
    body = _cut(body, _cyl_x(ROD_TAP_D, ROD_TAP_L + 0.5, tap_x0, y, ROD_Z))
    return _refine(body)


def make_guide_rod_cap(y: float) -> Part.Shape:
    """Nắp chặn đầu +X của MỘT thanh dẫn hướng — khoá thanh khỏi xô lệch theo X khi đã
    lắp, nhưng vẫn tháo được (1 vít tự ren M3). MỘT TẤM PHẲNG VUÔNG úp trực tiếp lên cả
    mặt ngoài vách +X (x = BOX_X1) LẪN đầu thanh (đầu thanh phẳng khít, xem ROD_END_GAP)
    — không hốc, không chốt: mặt tiếp xúc phẳng rộng tự chống xoay. Vít xuyên nắp, xuyên
    ĐÚNG lỗ ROD_ACCESS_D sẵn có trên vách (không khoét gì thêm trên Housing), rồi tự ren
    thẳng vào lỗ mồi ở đầu CHÍNH thanh dẫn hướng — vít THẲNG HÀNG với tâm thanh, kéo
    thanh áp sát nắp và ép nắp áp sát vách cùng lúc. Guide_Rod_Cap_A/B CÙNG HÌNH DẠNG,
    chỉ khác y."""
    body = _box2(BOX_X1, BOX_X1 + CAP_T, y - CAP_W / 2.0, y + CAP_W / 2.0,
                 CAP_Z0, CAP_Z1)
    # lỗ xuyên cho thân vít, xuyên hết bề dày nắp
    body = _cut(body, _cyl_x(M3_CLEAR, CAP_T + 1.0, BOX_X1 - 0.5, y, CAP_SCREW_Z))
    # hốc chìm đầu vít, khoét từ mặt NGOÀI nắp
    body = _cut(body, _cyl_x(EAR_SCREW_HEAD_D, EAR_SCREW_HEAD_H + 0.5,
                             BOX_X1 + CAP_T - EAR_SCREW_HEAD_H, y, CAP_SCREW_Z))
    return _refine(body)


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
    # 2 bạc tròn đáy phẳng (khớp thanh ray): A khít; B capsule nới Y (chống xoay).
    body = _cut(body, _flat_round_bore_x(ROD_BORE, BAR_L + 2.0, x0 - 1.0, ROD_A_Y, ROD_Z,
                                         ROD_FLAT_DEPTH))
    body = _cut(body, _flat_round_bore_x(ROD_BORE, BAR_L + 2.0, x0 - 1.0, ROD_B_Y, ROD_Z,
                                         ROD_FLAT_DEPTH, y_widen=ROD_SLOT_Y))
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
    # Trụ chỉ cao tới MOT_EAR_Z0 (không phải MOT_TOP) — CHỪA ĐÚNG chỗ dày MOT_EAR_T cho
    # tai động cơ nằm PHẲNG với mặt trên thân (không lồi lên), xem MOT_EAR_Z0/Z1.
    for s in (-1.0, 1.0):
        post = _box2(MOT_CX - EAR_POST_W / 2.0, MOT_CX + EAR_POST_W / 2.0,
                     s * EAR_POST_YC - EAR_POST_Y / 2.0,
                     s * EAR_POST_YC + EAR_POST_Y / 2.0, BASE_T, MOT_EAR_Z0)
        body = body.fuse(post)
        body = _cut(body, _cyl_z(EAR_PILOT_D, EAR_SCREW_L + 0.5,
                                 MOT_CX, s * EAR_POST_YC,
                                 MOT_EAR_Z1 - EAR_SCREW_L))
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
    # --- thanh dẫn hướng tròn đáy phẳng: HỐC MÙ vách -X, lỗ XUYÊN vách +X ---
    # (Vít nắp Rod_Cap bắt THẲNG vào chính thanh — xem make_guide_rod/make_guide_rod_cap
    # — nên không cần trụ hay lỗ ren riêng nào trên Housing ở đây nữa.)
    # BẪY VỪA BẮT ĐƯỢC (2026-09-06, check "khong dung TOAN BO housing" mới thêm): CẢ 4
    # trụ nắp góc (2 đầu -X, 2 đầu +X, vòng for phía trên) đứng NGAY TRƯỚC 2 vách, và Y
    # của chúng rất gần Y của 2 thanh dẫn hướng (cách có ~2mm) — hốc/lỗ trước đây chỉ dài
    # vừa đủ hết bề dày vách, KHÔNG xuyên qua hết phần trụ, nên thanh đâm thẳng vào thân
    # trụ đặc = KHÔNG lắp được ở CẢ HAI đầu. Phải kéo dài hốc/lỗ thêm đúng POST_W để
    # xuyên nốt qua trụ. Trụ chỉ mất tiết diện ở ĐÚNG dải Z của thanh (~5.4mm trong tổng
    # chiều cao trụ ~32mm) — vẫn còn nguyên phần trên/dưới để chịu va đập cữ cứng, mà tải
    # va đập ở đây vốn đã rất nhẹ (~4N, xem "HARD_STOP_X").
    for y in (ROD_A_Y, ROD_B_Y):
        body = _cut(body, _flat_round_bore_x(ROD_BORE, ROD_POCKET_CLEAR_LEN,
                                             ROD_X0, y, ROD_Z, ROD_FLAT_DEPTH))
        body = _cut(body, _flat_round_bore_x(ROD_ACCESS_D, ROD_CLEAR_LEN,
                                             ROD_CLEAR_X0, y, ROD_Z, ROD_FLAT_DEPTH))
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
    # thân + trục giờ là 2 Part::Feature TÁCH RIÊNG (khe hở, quay tự do) — mọi check
    # va chạm dưới đây phải tính trên CẢ CỤM (không phải chỉ thân) mới đúng thực tế
    motor_body = parts["BYJ_Motor"]
    motor_shaft = parts["BYJ_Motor_Shaft"]
    pinion_home = parts["Pinion"]
    pinion_envelope = make_pinion_envelope()
    motor = motor_body.fuse(motor_shaft)

    # --- 0. Trục ĐC tách rời: có khe hở thật trong lỗ thân, không chạm nhau ---
    v_shaft_body = _common_vol(motor_body, motor_shaft)
    checks.append(("Truc DC tach roi: khong dung than (khe ho O%.1f quanh truc O%.1f, "
                   "go giu O%.1f trong khoang O%.1f)"
                   % (MOT_SHAFT_BORE, MOT_SHAFT_D, MOT_SHAFT_RET_D, MOT_SHAFT_RET_BORE),
                   v_shaft_body < 1e-6, "dung %.3f mm3" % v_shaft_body))
    # --- 0-bis. soi to + chot tam THAT SU noi lien than/truc (khong roi rac) ---
    _n_solids_motor = len(motor.Solids)
    checks.append(("Than+truc DC qua soi to/chot tam la 1 KHOI LIEN THONG (khong roi)",
                   _n_solids_motor == 1, "%d khoi" % _n_solids_motor))

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

    # --- 4d. 2 bạc thanh dẫn hướng thông suốt, thanh xỏ qua được ---
    bad = []
    for nm, y, is_round in (("A", ROD_A_Y, True), ("B", ROD_B_Y, True)):
        probe = _rod_shape_x(is_round, ROD_D + 0.2, BAR_L + 4.0, bar_x0(0.0) - 2.0, y, ROD_Z)
        if _common_vol(probe, make_slide_bar(0.0)) > 1e-6:
            bad.append(nm)
    checks.append(("2 bac thanh dan huong THONG SUOT ca chieu dai thanh", not bad,
                   "bac A tron O%.1f khit, bac B ranh rong +-%.1f theo Y (thanh B tron)"
                   % (ROD_BORE, ROD_SLOT_Y / 2.0)))

    # --- 5. lắp: động cơ thả thẳng từ trên xuống ---
    drop = _sweep_z(motor, INNER_TOP - MOT_Z0 + 5.0)
    v = _common_vol(drop, housing)
    checks.append(("Dong co tha THANG tu tren xuong khong vuong", v < 1e-6,
                   "vuong %.2f mm3" % v))

    # --- 6. lắp: thanh thả thẳng từ trên xuống (Pinion đã ép lên trục, chưa có trục
    # trơn). BẪY BẮT ĐƯỢC (2026-09-06): check cũ có TÊN nhắc "banh rang" nhưng CODE chỉ
    # so va chạm với `motor`, KHÔNG hề đưa Pinion vào — hoàn toàn không phát hiện được
    # nếu Pinion (nhất là sau khi thêm trụ+bán cầu, có thể cao/rộng hơn) cản đường hạ
    # thanh. Giờ tách riêng, so ĐÚNG với Pinion tại vị trí lắp thật (moay-ơ hướng lên
    # trên trục, xem make_pinion(0.0)).
    bar_home = make_slide_bar(0.0)
    drop = _sweep_z(bar_home, INNER_TOP - BAR_Z0 + 5.0)
    v = _common_vol(drop, housing)
    v_mot = _common_vol(drop, motor)
    v_pin = _common_vol(drop, pinion_home)
    checks.append(("Slide_Bar ha THANG xuong khong vuong vo", v < 1e-6,
                   "vuong %.2f mm3" % v))
    checks.append(("Slide_Bar ha THANG xuong khong vuong DONG CO",
                   v_mot < 1e-6, "vuong %.2f mm3" % v_mot))
    # Tách "va cham o RANG" (BINH THUONG — moi banh rang-thanh rang THANG deu can
    # xoay/canh nhe khi ha xuong, khong xoay duoc trong phep tha thang tuyet doi nay,
    # ban chat an khop chu khong phai loi) khoi "va cham o moay-o/tru nap/ban cau"
    # (LOI THAT — nghia la phan than banh rang qua kho so voi ranh Slide_Bar).
    v_pin_env = _common_vol(drop, pinion_envelope)
    checks.append(("Slide_Bar ha THANG: tru nap/ban cau KHONG vuong (rieng RANG "
                   "thi binh thuong, xem ghi chu)", v_pin_env < 1e-6,
                   "vuong %.3f mm3 (rang cham rieng %.2f mm3, xem check duoi)"
                   % (v_pin_env, v_pin)))
    checks.append(("(thong tin) Rang cham khi ha thang — BINH THUONG, can xoay nhe luc "
                   "lap (xem THU TU LAP buoc 4)", True, "cham %.2f mm3" % v_pin))

    # --- 7. lắp: 2 thanh dẫn hướng đẩy TỪ NGOÀI vách +X (xuyên CẢ trụ nắp góc +X) ---
    for nm, y, is_round in (("A", ROD_A_Y, True), ("B", ROD_B_Y, True)):
        probe = _rod_shape_x(is_round, ROD_D + 0.2, BOX_X1 - ROD_CLEAR_X0 + 0.5,
                             ROD_CLEAR_X0, y, ROD_Z)
        thru = _common_vol(probe, housing) < 1e-6
        pocket = _rod_shape_x(is_round, ROD_D + 0.2, ROD_POCKET - 0.5,
                              ROD_X0 + 0.3, y, ROD_Z)
        blind = _common_vol(pocket, housing) < 1e-6
        checks.append(("Thanh dan huong %s: lo XUYEN vach +X (ca trụ) + hoc mu -X" % nm,
                       thru and blind,
                       "xuyen=%s hoc=%s, thanh dai %.1f mm" % (thru, blind, ROD_LEN)))
        # --- 7-bis. check TONG QUAT: thanh khong dung BAT KY dau nao cua housing tren
        # suot chieu dai — bat duoc dung bay nay (truoc gio chi check tung doan nho gan
        # 2 dau, khong check TOAN BO chieu dai, nen bo lot va cham voi tru nap goc +X)
        v_full = _common_vol(make_guide_rod(y, round_shape=is_round), housing)
        checks.append(("Thanh dan huong %s: KHONG dung housing tren SUOT chieu dai" % nm,
                       v_full < 1e-6, "dung %.3f mm3" % v_full))

    # --- 7b. Nắp Rod_Cap: đầu thanh không đụng nắp, nắp CHE kín lối thoát, vít có đường vặn ---
    for nm, y, is_round in (("A", ROD_A_Y, True), ("B", ROD_B_Y, True)):
        cap = parts["Guide_Rod_Cap_%s" % nm]
        rod = make_guide_rod(y, round_shape=is_round)
        v_rod = _common_vol(rod, cap)
        # neu thanh bi day THEM 3mm nua (vuot qua vi tri nghi phang khit), no PHAI dung
        # nap -> xac nhan nap thuc su CHAN duoc thanh, khong ho mot khe nao
        escape = _rod_shape_x(is_round, ROD_D, 3.0, BOX_X1 - ROD_END_GAP, y, ROD_Z)
        v_block = _common_vol(escape, cap)
        # vit tu ren XUYEN QUA lo ROD_ACCESS_D co san tren vach (khong khoet gi them tren
        # Housing) roi cam THANG vao lo moi o dau thanh -- duong nay phai THONG suot,
        # khong dung Housing lan phan than thanh NGOAI vung lo moi da khoan san
        drv_x0 = (ROD_X0 + ROD_LEN - ROD_TAP_L) + 0.5
        drv_len = (BOX_X1 + 0.5) - drv_x0
        drv = _cyl_x(ROD_TAP_D - 0.3, drv_len, drv_x0, y, CAP_SCREW_Z)
        v_drv = _common_vol(drv, housing) + _common_vol(drv, rod)
        checks.append(("Nap Rod_Cap %s: dau thanh khong dung nap (con khe %.2f)"
                       % (nm, ROD_END_GAP), v_rod < 1e-6, "dung %.3f mm3" % v_rod))
        # Nap co lo vit (M3_CLEAR) xuyen giua nen KHONG con chan het duoc tiet dien thanh
        # nhu ban khong-lo truoc do -- nhung M3_CLEAR < ROD_D (assert o tren) da bao dam
        # thanh khong the LOT QUA duoc; check nay chi xac nhan CON tiep xuc chan that,
        # khong phai nap bi dat sai vi tri lech hoan toan khoi thanh.
        _rod_area = math.pi * (ROD_D / 2.0) ** 2 if is_round else ROD_D * ROD_D
        checks.append(("Nap Rod_Cap %s: nap CO chan thanh (khong lech vi tri)" % nm,
                       v_block > 0.15 * 3.0 * _rod_area,
                       "chan %.1f / %.1f mm3" % (v_block, 3.0 * _rod_area)))
        checks.append(("Nap Rod_Cap %s: duong vit toi lo mo dau thanh thong suot" % nm,
                       v_drv < 1e-6, "vuong %.3f mm3" % v_drv))
        # check tong: nap up dung vi tri, khong dung vo (vit + khoi nap deu da tinh o tren)
        v_cap_housing = _common_vol(cap, housing)
        checks.append(("Nap Rod_Cap %s: up khit vach, khong dung vo" % nm,
                       v_cap_housing < 1e-6, "dung %.3f mm3" % v_cap_housing))

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

    # --- 16. Độ cứng / xô lệch ở tốc độ THẤP (<=60 rpm), quay XUÔI + NGƯỢC ---
    # Quán tính nhỏ (quasi-tĩnh): xô lệch do rơ bạc + lực tách khớp (góc áp lực), không
    # do rung tốc độ cao. Bạc A (cạnh thanh răng) định vị Y; bạc B chỉ chặn xoay.
    rig = analyze_rigidity_low_rpm()
    checks.append(("Ro bac: yaw toi da <= 1.1 deg (tranh chen rang)",
                   rig["yaw_max_deg"] <= 1.1,
                   "%.2f deg (clr_A=%.2f clr_B_Y=%.2f L=%.1f)"
                   % (rig["yaw_max_deg"], rig["clr_A_mm"], rig["clr_B_y_mm"],
                      rig["rod_span_mm"])))
    checks.append(("Xo lech Y tai an khop << do sau rang (con du an khop)",
                   rig["mesh_y_play_mm"] <= 0.45 * rig["working_depth_mm"],
                   "play %.3f / depth %.2f mm (du %.2f)"
                   % (rig["mesh_y_play_mm"], rig["working_depth_mm"],
                      rig["mesh_engage_margin_mm"])))
    checks.append(("Luc tach khop (PA) << luc day (detent/R) o <=60 rpm",
                   rig["F_sep_N"] <= 0.5 * rig["F_drive_N"],
                   "F_sep=%.2f F_drv=%.2f N" % (rig["F_sep_N"], rig["F_drive_N"])))
    checks.append(("Uon thanh in (PETG, 2 dau) duoi F_sep: do vong < 0.5 mm",
                   rig["rod_deflect_mm"] <= 0.5,
                   "%.3f mm @ F_sep (E=2 GPa, fixed-fixed)" % rig["rod_deflect_mm"]))
    checks.append(("Vung chet doi chieu (rang+hop so ~1.5deg) <= 0.8 mm",
                   rig["reverse_deadband_mm"] <= 0.8,
                   "%.3f mm (mesh %.2f + GB %.2f)"
                   % (rig["reverse_deadband_mm"], rig["bl_mesh_mm"], rig["bl_gearbox_mm"])))
    checks.append(("Quan tinh o 60 rpm khong xoc (F_inert << F_drv khi dung 0.2s)",
                   rig["F_inert_60rpm_N"] <= 0.15 * rig["F_drive_N"],
                   "F_i=%.3f N (%.1f%% F_drv)" % (rig["F_inert_60rpm_N"],
                   100.0 * rig["F_inert_60rpm_N"] / rig["F_drive_N"])))

    # Quét hình học — tư thế đạt được trong bạc + đổi chiều trong rơ răng:
    #   (a) tịnh tiến Y ±clr_A (lực tách/ép khớp) pha danh nghĩa
    #   (b) yaw ±yaw_max quanh A (B dùng hết rãnh)
    #   (c) tại pose danh nghĩa: lệch góc ±half backlash (đổi sườn khi đảo chiều)
    worst_clash = 0.0
    min_touch_skew = 1e9
    yaw_deg = rig["yaw_max_deg"]
    half_bl = 0.5 * math.degrees(rig["bl_mesh_mm"] / PIN_R)
    poses = [("nom", 0.0, 0.0)]
    for y_sign in (-1.0, 1.0):
        poses.append(("ty", y_sign * rig["clr_A_mm"], 0.0))
    for yaw_sign in (-1.0, 1.0):
        poses.append(("yaw", 0.0, yaw_sign * yaw_deg))
    for off in _offsets(5):
        for _kind, dy, dyaw in poses:
            bar = make_slide_bar(off)
            if abs(dy) > 1e-12:
                bar.translate(App.Vector(0.0, dy, 0.0))
            if abs(dyaw) > 1e-12:
                bar.rotate(App.Vector(0.0, ROD_A_Y, ROD_Z), App.Vector(0, 0, 1), dyaw)
            g = make_pinion(pinion_angle(off))
            worst_clash = max(worst_clash, _common_vol(g, bar))
            probe = _cyl_z(2.0 * (PIN_RA + 0.45), GEAR_FACE, 0.0, 0.0, GEAR_Z0)
            min_touch_skew = min(min_touch_skew, _common_vol(probe, bar))
        # Đảo chiều: chỉ lệch góc trong vùng rơ, thanh ở pose danh nghĩa
        bar0 = make_slide_bar(off)
        for dang in (half_bl, -half_bl):
            g = make_pinion(pinion_angle(off) + dang)
            worst_clash = max(worst_clash, _common_vol(g, bar0))
    checks.append(("Lech bac/doi chieu <=60rpm: khong CHEN rang",
                   worst_clash < 0.05,
                   "chen toi da %.4f mm3 (nguong 0.05 — mep rang o yaw max)"
                   % worst_clash))
    checks.append(("Lech bac: van CON an khop",
                   min_touch_skew > 1.0,
                   "chong lan nho nhat %.2f mm3" % min_touch_skew))
    return checks


def analyze_rigidity_low_rpm() -> dict:
    """Ước lượng xô lệch / độ cứng khi ĐC quay xuôi–ngược ở tốc độ thấp (<=60 rpm).

    Ở <=60 rpm quán tính thanh ~ vài phần trăm lực đẩy — bài toán gần tĩnh. Xô lệch
    chính: (1) rơ bạc A/B → yaw Slide_Bar, (2) lực tách khớp F·tan(PA), (3) rơ đổi chiều
    (răng in + hộp số 28BYJ), (4) uốn thanh nhựa in giữa 2 vách.
    """
    clr_A = 0.5 * (ROD_BORE - ROD_D)
    clr_B_y = 0.5 * (ROD_BORE + ROD_SLOT_Y - ROD_D)
    span = ROD_A_Y - ROD_B_Y
    yaw = math.atan((clr_A + clr_B_y) / span)
    # Thanh răng nằm cùng chân với bạc A → lệch Y an khớp ≈ clr_A + yaw·Δy
    mesh_y = clr_A + abs(math.tan(yaw) * (PIN_R - ROD_A_Y))
    working_depth = 2.25 * GEAR_M
    F_drive = MOT_DETENT / PIN_R
    F_sep = F_drive * math.tan(math.radians(GEAR_PA))
    # Uốn 1 thanh in PETG: fixed-fixed, nhịp ~ khoảng trong giữa 2 vách, F_sep lên A
    E_petg = 2000.0  # N/mm^2
    I_rod = math.pi * (ROD_D ** 4) / 64.0 * 0.85  # trừ đáy phẳng ~15%
    L_bend = max(INNER_X1 - INNER_X0 - 2.0 * POST_W, BAR_L)
    rod_deflect = F_sep * (L_bend ** 3) / (192.0 * E_petg * I_rod)
    bl_mesh = 2.0 * GEAR_BL  # mỗi bên GEAR_BL trên pinion+rack → dọc pitch ~2·bl
    bl_gb = math.radians(1.5) * PIN_R  # hộp số 28BYJ điển hình ~1–2°
    # Quán tính: m≈35 g (Slide_Bar PETG), dừng từ v(60rpm) trong Δt=0.2 s
    m_bar_kg = 0.035
    v_60 = (PIN_MM_PER_REV * 60.0 / 60.0) / 1000.0  # m/s
    F_inert = m_bar_kg * (v_60 / 0.2)
    return {
        "rpm_design": MOT_RPM,
        "rpm_check_max": 60.0,
        "clr_A_mm": clr_A,
        "clr_B_y_mm": clr_B_y,
        "rod_span_mm": span,
        "yaw_max_deg": math.degrees(yaw),
        "mesh_y_play_mm": mesh_y,
        "working_depth_mm": working_depth,
        "mesh_engage_margin_mm": working_depth - mesh_y,
        "F_drive_N": F_drive,
        "F_sep_N": F_sep,
        "rod_deflect_mm": rod_deflect,
        "bl_mesh_mm": bl_mesh,
        "bl_gearbox_mm": bl_gb,
        "reverse_deadband_mm": bl_mesh + bl_gb,
        "F_inert_60rpm_N": F_inert,
        "v_mm_s": {
            "12": PIN_MM_PER_REV * 12.0 / 60.0,
            "30": PIN_MM_PER_REV * 30.0 / 60.0,
            "60": PIN_MM_PER_REV * 60.0 / 60.0,
        },
    }


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
        "BYJ_Motor": make_motor_body(),
        "BYJ_Motor_Shaft": make_motor_shaft(),
        "Pinion": make_pinion(0.0),
        "Slide_Bar": make_slide_bar(0.0),
        "Guide_Rod_A": make_guide_rod(ROD_A_Y),
        "Guide_Rod_B": make_guide_rod(ROD_B_Y),
        "Guide_Rod_Cap_A": make_guide_rod_cap(ROD_A_Y),
        "Guide_Rod_Cap_B": make_guide_rod_cap(ROD_B_Y),
        "Limit_Switch_Min": make_limit_switch(False),
    }
    if SW_MAX:
        parts["Limit_Switch_Max"] = make_limit_switch(True)
    return parts


COLORS = {
    "Housing": ((0.55, 0.58, 0.65), 0),
    "Housing_Lid": ((0.62, 0.66, 0.72), 55),
    "BYJ_Motor": ((0.25, 0.28, 0.34), 0),
    "BYJ_Motor_Shaft": ((0.80, 0.65, 0.30), 0),
    "Pinion": ((0.92, 0.62, 0.18), 0),
    "Slide_Bar": ((0.30, 0.66, 0.42), 0),
    "Guide_Rod_A": ((0.78, 0.80, 0.84), 0),
    "Guide_Rod_B": ((0.78, 0.80, 0.84), 0),
    "Guide_Rod_Cap_A": ((0.62, 0.66, 0.72), 0),
    "Guide_Rod_Cap_B": ((0.62, 0.66, 0.72), 0),
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
    print("  Do phan giai (%.0f buoc/vg) : %.7f mm/buoc (that, co pi)"
          % (MOTOR_STEPS_PER_REV, PIN_MM_PER_REV / MOTOR_STEPS_PER_REV))
    print("  STEPS_PER_MM firmware      : %d buoc/mm (that = %.4f, lech %.5f%%)"
          % (STEPS_PER_MM, _TRUE_STEPS_PER_MM, _STEPS_PER_MM_ERR * 100.0))
    _err30 = max(abs(round(d * STEPS_PER_MM) / _TRUE_STEPS_PER_MM - d) for d in range(2, 31))
    print("  Sai so xa nhat khi di 2..30mm bang STEPS_PER_MM: %.6f mm (%.1f micromet)"
          % (_err30, _err30 * 1000.0))
    print("  Luc giu khi TAT DIEN       : %.2f N (detent %.1f N.mm / R %.1f)"
          % (MOT_DETENT / PIN_R, MOT_DETENT, PIN_R))
    if SW_MAX:
        print("  Cong tac                   : 2 (MIN home + MAX bao ve)")
    else:
        print("  Cong tac                   : 1 (chi MIN home) — SW_MAX=False")
        print("  Cu cung dau +X             : x = %.1f, tuc +%.1f mm sau diem trip"
              % (HARD_STOP_X, HARD_STOP_X - X_TRIP_MAX))
        print("  Gioi han mem khuyen nghi   : 0 .. %.1f mm" % (TRAVEL - 1.0))
    print("  Thanh dan huong           : A+B tron O%.0f day phang -- 2 cay IN 3D, dai %.1f mm"
          % (ROD_D, ROD_LEN))

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

    rig = analyze_rigidity_low_rpm()
    print("--- DO CUNG / XO LECH @ <=60 rpm (xuoi+nguoc) ---")
    print("  Yaw toi da (ro bac)         : %.2f deg" % rig["yaw_max_deg"])
    print("  Lech Y tai an khop          : %.3f mm (do sau rang %.2f, du %.2f)"
          % (rig["mesh_y_play_mm"], rig["working_depth_mm"],
             rig["mesh_engage_margin_mm"]))
    print("  F day / F tach (PA 20)      : %.2f / %.2f N" % (rig["F_drive_N"], rig["F_sep_N"]))
    print("  Uon thanh in @ F_sep        : %.3f mm" % rig["rod_deflect_mm"])
    print("  Vung chet doi chieu         : %.3f mm" % rig["reverse_deadband_mm"])
    print("  F quan tinh dung @ 60rpm    : %.3f N" % rig["F_inert_60rpm_N"])
    print("  Van toc pitch 12/30/60 rpm  : %.1f / %.1f / %.1f mm/s"
          % (rig["v_mm_s"]["12"], rig["v_mm_s"]["30"], rig["v_mm_s"]["60"]))

    metrics = {
        "pass": n_fail == 0,
        "checks_fail": n_fail,
        "checks_total": len(checks),
        "travel_mm": TRAVEL,
        "box_outer_mm": [BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_Z1],
        "gear": {"m": GEAR_M, "z": GEAR_Z, "R": PIN_R, "mm_per_rev": PIN_MM_PER_REV,
                "body_dia_mm": 2.0 * PIN_RF},
        "steps_per_mm_firmware": STEPS_PER_MM,
        "steps_per_mm_true": _TRUE_STEPS_PER_MM,
        "steps_per_mm_err_pct": _STEPS_PER_MM_ERR * 100.0,
        "rack_len_mm": RACK_L,
        "bar_len_mm": BAR_L,
        "rod_len_mm": ROD_LEN,
        "rod_cross_section_mm": [ROD_D, ROD_D - ROD_FLAT_DEPTH],
        "rod_printed": True,
        "sec_full_travel": TRAVEL / (MOT_RPM * PIN_MM_PER_REV / 60.0),
        "hold_force_N": MOT_DETENT / PIN_R,
        "sw_max": SW_MAX,
        "n_switches": 2 if SW_MAX else 1,
        "hard_stop_x": HARD_STOP_X,
        "hard_stop_over_trip_mm": HARD_STOP_X - X_TRIP_MAX,
        "soft_limit_mm": TRAVEL - 1.0,
        "rigidity_low_rpm": rig,
    }
    mpath = OUT / "byj_rack_stage_metrics.json"
    mpath.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print("Metrics:", mpath)
    rpath = OUT / "byj_rack_rigidity_metrics.json"
    rpath.write_text(json.dumps({
        "pass": n_fail == 0,
        "rpm_max_checked": 60.0,
        "bidirectional": True,
        **rig,
    }, indent=2) + "\n", encoding="utf-8")
    print("Rigidity:", rpath)

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
    else:
        App.closeDocument(doc.Name)


def _is_main_script() -> bool:
    """True nếu file NÀY là script được gọi trực tiếp (freecadcmd không set
    __name__ == "__main__" — nó set thành tên file, giống hệt tên module khi bị
    import, nên __name__ không phân biệt được. Dùng sys.argv[-1] (script freecadcmd
    được yêu cầu chạy) so với __file__ của chính module này."""
    try:
        return Path(sys.argv[-1]).resolve() == Path(__file__).resolve()
    except Exception:
        return False


if __name__ == "__main__" or _is_main_script():
    main()
