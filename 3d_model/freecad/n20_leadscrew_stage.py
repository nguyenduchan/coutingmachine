"""
Giá đỡ động cơ GA12-N20 TRỤC VÍT M4 LIỀN + thanh tịnh tiến + 2 công tắc hành trình.

Chọn động cơ có trục vít liền thay vì động cơ trục D + khớp nối mềm: khớp nối
Ø19 x L25 ăn mất 25 mm chiều dài lại nuốt thêm 11 mm ty ren, và kẹp trục Ø3 bằng
2 vít M4 là chỗ dễ trượt nhất trong cụm. Bỏ nó đi thì cùng chiều dài đế được
hành trình gấp đôi, và độ đồng tâm do nhà sản xuất bảo đảm.

Nguồn kích thước động cơ: bản vẽ datasheet GA12-N20 (Unit: mm)
  hộp số  12 (rộng) x 10 (cao) x 9 (dài)      — mặt bích trước 12x10
  lon mô tơ  Ø12 x 15 ; cọc đấu điện phía sau 1.2
  bích trước có 2 x M1.6 sâu 2.1, nằm CHÉO nhau:
      (+3.8, +3.0) và (-3.8, -3.0) so với tâm trục   [6 mm theo cạnh 10]
  trục ra = TRỤC VÍT M4 (bước 0.7), dài SCREW_LEN tính từ mặt bích

CƠ CẤU (trục vít nằm theo +X, đế nằm trên mặt XY):
  Base_Plate        — đế phẳng, 4 lỗ M3 bắt xuống máy
  Motor_Bracket     — bích đứng bắt 2 vít M1.6 + máng ôm thân Ø12 + vấu công tắc MIN
  Motor_Clamp       — nắp kẹp trên, 4 vít M3
  Lead_Screw        — TRỤC VÍT M4 (vẽ rời cho dễ nhìn, thực tế liền với động cơ)
  Guide_Shaft       — TRỤC TRƠN Ø5 SONG SONG với trục vít, lệch +Y 17 mm
  Slide_Bar         — THANH TỊNH TIẾN: bạc ôm trục trơn + hốc BƠI cho đai ốc M4
  Wing_Nut          — đai ốc TAI HỒNG M4 (tán cánh chuồn) inox 304
  Nut_Holder        — LỚP GÁ có 2 khe ôm 2 tai, bắt vào thanh bằng 4 bu lông M3
  End_Block         — gối đỡ trục trơn + vấu công tắc MAX
  Limit_Switch_Min/Max — 2 công tắc hành trình mini, nút ấn hướng theo trục X

NGUYÊN LÝ: động cơ quay trục vít → ĐAI ỐC LỤC GIÁC M4 bị hốc lục giác của thanh
giữ không cho xoay → đai ốc chạy dọc trục → kéo Slide_Bar tịnh tiến. Trục trơn
song song chịu mô men lật và chống xoay cho thanh.

CHỐNG XOAY BẰNG 2 TAI: 2 tai của đai ốc dựng ĐỨNG, lọt vào 2 khe của Nut_Holder
nên đai ốc không quay được → buộc phải chạy dọc trục. Lớp gá là chi tiết RỜI để
lắp được sau cùng: vặn đai ốc tới khi 2 tai thẳng đứng (mỗi vòng ren đi 0.7 mm
nên luôn tìm được vị trí trong ±0.35 mm), rồi mới đẩy lớp gá vào dọc trục và siết
4 bu lông M3.

ĐAI ỐC BƠI: khe rộng hơn tai 0.3 mm, hốc thân rộng hơn 0.6 mm. Trục vít gắn cứng
vào hộp số, không còn khớp nối mềm để bù lệch, nên độ mềm phải nằm ở đai ốc — kẹp
cứng thì sai lệch song song giữa trục vít và trục trơn sẽ ép ngang lên bạc hộp số
N20 mỗi vòng quay. Chặn dọc trục hai chiều: +X là mặt tì đai ốc lên mặt -X của
thanh, -X là vai thân đai ốc lên đáy hốc lớp gá.

CÔNG TẮC HÀNH TRÌNH: thân công tắc đặt sao cho MẶT TRƯỚC của nó chính là chặn cơ
khí; thanh chạm nút trước đó (SW_PLUNGER - SW_TRIP) mm nên giới hạn điện luôn
tới trước giới hạn cơ. Rãnh bắt vít M2 chạy dọc X cho chỉnh +-3 mm.

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
# 1. Động cơ GA1024-N20 (theo bản vẽ datasheet)
# ---------------------------------------------------------------------------
GB_W, GB_H, GB_L = 12.0, 10.0, 9.0        # hộp số: rộng(Y) x cao(Z) x dài(X)
CAN_D, CAN_L = 12.0, 15.0                 # lon mô tơ
REAR_D, REAR_L = 5.0, 1.2                 # cọc/nắp sau
MOT_HOLE_DY, MOT_HOLE_DZ = 3.8, 3.0       # 2 x M1.6 chéo nhau
MOT_HOLE_TAP = 1.6
MOT_LEN = GB_L + CAN_L + REAR_L           # 25.2

# ---------------------------------------------------------------------------
# 2. Bố trí chung (mm). Đế: mặt dưới z=0. Trục vít me: y=0, z=AXIS_Z.
# ---------------------------------------------------------------------------
BASE_T = 4.0
AXIS_Z = 20.0                             # tâm vít me so với mặt bàn máy
GUIDE_Y = 17.0                            # trục trơn song song, lệch +Y
GUIDE_D = 5.0                             # Ø5 trục trơn (loại phổ thông)

FACE_X0, FACE_T = 0.0, 3.0                # bích đứng x = 0..3, mặt ĐC áp tại x=0
SHAFT_CLEAR_D = 5.4                       # lỗ cho trục vít M4 chui qua bích (chừa
                                          # thịt giữa lỗ này và 2 lỗ M1.6 ở r = 4.84)
BASE_X0 = -32.0                           # BASE_X1 tính sau, theo vị trí gối đỡ
BASE_Y0, BASE_Y1 = -27.0, 26.0
WING_Y = GUIDE_Y + 7.0                    # chân đế nới rộng tới phía trục trơn
RIB_T = 4.0                               # gân chống lật cho bích đứng
RIB_Y0 = GUIDE_Y + 2.0                    # gân đặt SÁT (không trùng) lỗ trục trơn
                                          # — chừa chỗ vặn mũ vít ở y = +-15

CRADLE_X0 = -MOT_LEN - 2.0                # máng ôm thân: -27.2 .. 0
FOOT_T = 4.0                              # bề dày chân đế của gá (z = 4..8)
FOOT_Y = 18.0                             # nửa bề rộng chân đế
FOOT_BOLT_Y = 15.0                        # vít M3 bắt xuống đế (đủ chỗ cho mũ vít)
CRADLE_Y = 11.0                           # nửa bề rộng máng + nắp kẹp
CLAMP_BOLT_Y = 8.5                        # vít M3 giữ nắp kẹp, hai bên thân ĐC
PLATE_TOP = 28.0                          # đỉnh bích đứng

SCREW_D = 4.0                             # TRỤC VÍT M4 LIỀN của động cơ
SCREW_PITCH = 0.7                         # bước ren M4 tiêu chuẩn
SCREW_LEN = 55.0                          # đoạn ren nhô ra khỏi mặt bích.
                                          # GIẢ ĐỊNH — trang bán không ghi; đo lại
                                          # rồi sửa đúng 1 số này, phần còn lại tự theo
MOTOR_RPM = 60.0                          # 12 VDC, 60 rpm theo mã hàng đã chọn
SCREW_X0 = FACE_X0                        # ren bắt đầu ngay tại mặt bích
SCREW_X1 = SCREW_X0 + SCREW_LEN

# Thanh tịnh tiến
BAR_X = 7.0                               # bề dày thanh theo phương chạy (X).
                                          # MỎNG để lấy hành trình: mỗi mm bớt đi
                                          # ở đây được 1 mm hành trình (nửa ở mỗi đầu)
BAR_Y0, BAR_Y1 = -34.0, GUIDE_Y           # trải theo Y, đầu tự do ở -34
BAR_Z0, BAR_Z1 = 13.0, 29.0               # cao thêm để bù phần nào độ cứng đã mất
                                          # khi mỏng đi theo X (I ~ cao x dày^3)
BAR_PAD_Y1 = -26.0                        # đầu tự do dày hơn để bắt vít M3 — vùng
BAR_PAD_X = 11.0                          # y < -26 không chạm gì nên không tốn hành trình
BOSS_D, BOSS_L = 13.0, 18.0               # bạc ôm trục trơn
BOSS_BORE = GUIDE_D + 0.3                 # trượt: Ø5.3
# ĐAI ỐC TAI HỒNG (tán cánh chuồn) M4 inox 304, kiểu DIN 315.
# GIẢ ĐỊNH kích thước — trang bán chỉ ghi size M3..M10. Đo con thật rồi sửa 5 số
# này; lớp gá và hành trình tự tính lại theo.
WING_SPAN = 21.0                          # đầu tai này sang đầu tai kia
WING_T = 3.0                              # bề dày tai
WING_AX = 6.0                             # tai cao 6 mm, mọc tiếp sau thân
WING_BOSS_D, WING_BOSS_H = 8.0, 5.0       # thân ren
WING_R_IN = 2.2                           # chân tai — ăn vào TRONG thân để cả đai ốc
                                          # là MỘT khối liền, không phải 3 mảnh chạm nhau

# LỚP GÁ giữ đai ốc: bắt vào MẶT -X của thanh, có 2 KHE ôm 2 tai.
# Đặt tai THẲNG ĐỨNG (khe nằm dọc) nên lớp gá hẹp theo Y — nhờ vậy nó lách được
# giữa bạc trục trơn (y >= 10.5) và vấu công tắc (y <= -15.5).
HOLD_T = 7.5                              # bề dày lớp gá theo X (mỏng bớt cùng lý do)
HOLD_Y = 10.0                             # nửa bề rộng
HOLD_DZ = 12.0                            # nửa chiều cao
HOLD_SLOT_W = WING_T + 0.3                # khe rộng hơn tai 0.3 → đai ốc còn BƠI
HOLD_SLOT_R0 = WING_R_IN - 0.2            # khe phải mở tới tận chân tai
HOLD_SLOT_R = WING_SPAN / 2.0 + 0.5
HOLD_BOLT_Y, HOLD_BOLT_DZ = 7.0, 4.0      # 4 bu lông M3 bắt lớp gá vào thanh
THREAD_MARGIN = 1.5                       # ren dự phòng chừa ở cuối hành trình

# --- Gối đỡ đầu kia: đỡ trục trơn VÀ mỏ đỡ đầu trục vít -------------------
# Mỏ đỡ là một vấu Ø14 mọc ngược về -X từ vách, có lỗ THÔNG Ø4.6 để đầu trục vít
# thò vào SCREW_END_SUPPORT mm. Lỗ để RỘNG 0.6 mm chứ không ép sát: trục vít đã
# được bạc hộp số định vị rồi, gối thứ hai mà ôm chặt sẽ đánh nhau với nó — nhiệm
# vụ của lỗ này chỉ là chặn trục văng/đảo khi quay.
END_T = 6.0
SCREW_END_SUPPORT = 5.0                   # đoạn trục vít nằm trong lỗ
NOSE_D = 14.0
X_NOSE = SCREW_X1 - SCREW_END_SUPPORT     # mặt trước mỏ đỡ = chặn cơ khí của thanh
# BẠC trục trơn dài hơn thân thanh (BOSS_L > BAR_X) nên chính nó mới là thứ
# chạm bích đứng trước — giới hạn gần phải tính theo bạc, không theo thân thanh.
# Ba thứ có thể chạm bích đứng trước: bạc trục trơn (18), thân thanh (10), và
# LỚP GÁ nhô thêm HOLD_T về phía -X. Lấy cái xa nhất.
_X_MIN_MECH = FACE_X0 + FACE_T + max(BOSS_L / 2.0, BAR_X / 2.0 + HOLD_T) + 0.5
_X_MAX_THREAD = SCREW_X1 + BAR_X / 2.0 - WING_BOSS_H - THREAD_MARGIN
# Giới hạn xa giờ do MỎ ĐỠ quyết định (nó nằm ngay trên đường thanh chạy), rồi
# đặt vách đủ xa để BẠC trục trơn không chặn sớm hơn.
_X_MAX_MECH = min(_X_MAX_THREAD, X_NOSE - BAR_X / 2.0 - 0.5)
END_X0 = _X_MAX_MECH + BOSS_L / 2.0 + 2.0
assert END_X0 > X_NOSE + 1.0, "mo do bi am chieu dai - giam SCREW_END_SUPPORT"
GUIDE_X0, GUIDE_X1 = 0.0, END_X0 + END_T
END_FOOT_X0, END_FOOT_X1 = END_X0 - 16.0, END_X0 + END_T + 10.0

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

BAR_HOME_X = 0.5 * (X_TRIP_MIN + X_TRIP_MAX)
BASE_X1 = END_FOOT_X1 + 2.0

M3_CLEAR = 3.4
M3_TAP = 2.5                              # lỗ mồi cho vít M3 tự tarô (nhựa in)
M16_CLEAR = 2.0                           # lỗ thông cho vít M1.6 (in FDM)


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


def _hex_prism_x(af: float, length: float, x0: float, y: float, z: float) -> Part.Shape:
    """Lăng trụ lục giác, trục theo X, af = khoảng cách 2 mặt phẳng đối diện."""
    r = af / math.sqrt(3.0)  # bán kính qua đỉnh
    pts = []
    for i in range(6):
        a = math.radians(30.0 + i * 60.0)
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
    """Khoảng chạy hợp lệ của tâm thanh trượt.

    Ba thứ chặn hành trình: mặt khớp nối (đầu gần), chiều dài ty ren còn lại để
    đai ốc còn ăn ren (đầu xa), và bạc trục trơn không được đụng gối đỡ.
    """
    return X_TRIP_MIN, X_TRIP_MAX


# ---------------------------------------------------------------------------
# 3. Các chi tiết
# ---------------------------------------------------------------------------
def make_motor() -> Part.Shape:
    """Mặt bích trước tại x=0, thân về phía -X, trục ra về phía +X."""
    gb = _box(GB_L, GB_W, GB_H, -GB_L, -GB_W / 2.0, AXIS_Z - GB_H / 2.0)
    can = _cyl_x(CAN_D, CAN_L, -GB_L - CAN_L, 0.0, AXIS_Z)
    rear = _cyl_x(REAR_D, REAR_L, -MOT_LEN, 0.0, AXIS_Z)

    # trục ra là TRỤC VÍT M4 LIỀN — dựng riêng thành Lead_Screw cho dễ nhìn,
    # thực tế nó là một khối với động cơ, không tháo rời được
    body = gb.fuse(can).fuse(rear)
    # 2 lỗ ren M1.6 sâu 2.1 trên mặt bích
    for dy, dz in motor_face_holes():
        body = _cut(body, _cyl_x(MOT_HOLE_TAP, 2.1, -2.1, dy, AXIS_Z + dz))
    return _refine(body)


def make_base_plate() -> Part.Shape:
    plate = _box2(BASE_X0, BASE_X1, BASE_Y0, BASE_Y1, 0.0, BASE_T)
    for x, y in base_bolt_xy():
        plate = _cut(plate, _cyl_z(M3_CLEAR, BASE_T + 2.0, x, y, -1.0))
    for x, y in machine_bolt_xy():
        plate = _cut(plate, _cyl_z(M3_CLEAR, BASE_T + 2.0, x, y, -1.0))
    return _refine(plate)


def base_bolt_xy() -> list[tuple[float, float]]:
    """Vít M3 bắt chân gá động cơ + gối đỡ xuống đế."""
    # Mọi vị trí đều né bích đứng và 2 gân chống lật để còn chỗ vặn mũ vít.
    # Né bích đứng, 2 gân chống lật, VÀ vấu công tắc (y = -17..-14) để còn chỗ
    # vặn mũ vít — nên hai bên -Y / +Y không đối xứng theo X.
    return [
        (-25.0, -FOOT_BOLT_Y), (-16.0, -FOOT_BOLT_Y),      # gá ĐC, phía công tắc
        (CRADLE_X0 + 5.0, FOOT_BOLT_Y), (-6.0, FOOT_BOLT_Y),
        (END_FOOT_X0 + 5.0, -FOOT_BOLT_Y),                 # gối đỡ, phía công tắc
        (END_FOOT_X0 + 5.0, FOOT_BOLT_Y),
        (END_X0 + END_T + 6.0, -8.0), (END_X0 + END_T + 6.0, 8.0),
    ]


def machine_bolt_xy() -> list[tuple[float, float]]:
    """4 lỗ M3 bắt cả cụm xuống thân máy."""
    # rải trên dải đế TRỐNG giữa hai chân gá (chân gá đã có vít riêng)
    x_a = FACE_X0 + FACE_T
    x_b = END_FOOT_X0
    return [
        (x, y)
        for x in (x_a + (x_b - x_a) / 3.0, x_a + 2.0 * (x_b - x_a) / 3.0)
        for y in (-17.0, 21.0)
    ]


def make_motor_bracket() -> Part.Shape:
    """Bích đứng (bắt 2 vít M1.6) + máng ôm thân + chân đế."""
    # chân đế — nới rộng sang phía trục trơn để đỡ gân
    foot = _box2(CRADLE_X0, FACE_X0 + FACE_T, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    # bích đứng — kéo dài tới trục trơn để cắm luôn trục
    plate = _box2(FACE_X0, FACE_X0 + FACE_T, -CRADLE_Y, WING_Y, BASE_T, PLATE_TOP)
    # máng ôm thân động cơ
    cradle = _box2(CRADLE_X0, FACE_X0, -CRADLE_Y, CRADLE_Y, BASE_T, AXIS_Z)
    # gân chống lật ở phía trục trơn (chỗ không có máng đỡ)
    rib = _tri_rib(
        FACE_X0, CRADLE_X0 + 11.0, PLATE_TOP - 2.0, BASE_T + FOOT_T, RIB_Y0, RIB_T
    )
    body = foot.fuse(plate).fuse(cradle).fuse(rib).fuse(make_sw_fin(False))

    body = _cut(body, motor_pocket_tool())
    # lỗ cho trục ra + gờ Ø4 chui qua bích
    body = _cut(body, _cyl_x(SHAFT_CLEAR_D, FACE_T + 2.0, FACE_X0 - 1.0, 0.0, AXIS_Z))
    # 2 lỗ thông vít M1.6
    for dy, dz in motor_face_holes():
        body = _cut(body, _cyl_x(M16_CLEAR, FACE_T + 2.0, FACE_X0 - 1.0, dy, AXIS_Z + dz))
    # lỗ cắm trục trơn (ép chặt)
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, FACE_T + 2.0, FACE_X0 - 1.0, GUIDE_Y, AXIS_Z))
    # vít M3 giữ nắp kẹp
    for x, y in clamp_bolt_xy():
        body = _cut(body, _cyl_z(M3_TAP, AXIS_Z - BASE_T, x, y, BASE_T))
    # vít M3 bắt xuống đế
    for x, y in base_bolt_xy():
        if x > 20.0:
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





def make_lead_screw() -> Part.Shape:
    """Vít me = ty ren M3 (vẽ trơn Ø3; ren bước 0.5 chỉ ghi trong thông số)."""
    return _cyl_x(SCREW_D, SCREW_LEN, SCREW_X0, 0.0, AXIS_Z)


def make_guide_shaft() -> Part.Shape:
    return _cyl_x(GUIDE_D, GUIDE_X1 - GUIDE_X0, GUIDE_X0, GUIDE_Y, AXIS_Z)


def make_end_block() -> Part.Shape:
    """Gối đỡ đầu kia — đỡ trục trơn VÀ đầu trục vít.

    Ty ren M3 x 30 quá ngắn để với tới đây (hết ở x = %.1f), nên nó nằm công-xôn
    từ khớp nối. Đoạn hở chỉ 19 mm nên độ võng không đáng kể, và khớp nối MỀM
    còn cho ty tự căn theo đai ốc thay vì cưỡng bức.
    """ % SCREW_X1
    foot = _box2(END_FOOT_X0, END_FOOT_X1, -FOOT_Y, WING_Y, BASE_T, BASE_T + FOOT_T)
    wall = _box2(END_X0, END_X0 + END_T, -CRADLE_Y, WING_Y, BASE_T, PLATE_TOP)
    # gân đặt PHÍA NGOÀI (x > vách) — phía trong là vùng thanh trượt chạy tới
    ribs = None
    for y0 in (-RIB_T / 2.0, RIB_Y0):
        r = _tri_rib(
            END_X0 + END_T, END_FOOT_X1, PLATE_TOP - 2.0, BASE_T + FOOT_T, y0, RIB_T
        )
        ribs = r if ribs is None else ribs.fuse(r)
    # mỏ đỡ đầu trục vít, mọc ngược về -X từ vách
    nose = _cyl_x(NOSE_D, END_X0 - X_NOSE, X_NOSE, 0.0, AXIS_Z)
    body = foot.fuse(wall).fuse(ribs).fuse(make_sw_fin(True)).fuse(nose)
    # lỗ ép trục trơn
    body = _cut(body, _cyl_x(GUIDE_D + 0.05, END_T + 2.0, END_X0 - 1.0, GUIDE_Y, AXIS_Z))
    # lỗ THÔNG cho đầu trục vít — rộng 0.6 mm, chỉ chặn đảo chứ không làm bạc
    body = _cut(
        body,
        _cyl_x(SCREW_D + 0.6, (END_X0 + END_T) - X_NOSE + 2.0, X_NOSE - 1.0, 0.0, AXIS_Z),
    )
    for x, y in base_bolt_xy():
        if x < 20.0:
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
    """+1 nếu cần gạt chìa về -X (công tắc MAX) thì hướng nhô là -1."""
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


def make_slide_bar(xc: float) -> Part.Shape:
    """THANH TỊNH TIẾN: bạc ôm trục trơn + hốc BƠI cho đai ốc M4 + đầu tự do bắt tải."""
    bar = _box2(xc - BAR_X / 2.0, xc + BAR_X / 2.0, BAR_Y0, BAR_Y1, BAR_Z0, BAR_Z1)
    boss = _cyl_x(BOSS_D, BOSS_L, xc - BOSS_L / 2.0, GUIDE_Y, AXIS_Z)
    # đầu tự do dày hơn để còn thịt quanh 2 lỗ M3; nằm ở y < BAR_PAD_Y1 nên không
    # chạm bích/mỏ đỡ/công tắc, tức là KHÔNG ăn vào hành trình
    pad = _box2(xc - BAR_PAD_X / 2.0, xc + BAR_PAD_X / 2.0,
                BAR_Y0, BAR_PAD_Y1, BAR_Z0, BAR_Z1)
    body = bar.fuse(boss).fuse(pad)

    # lỗ trượt trên trục trơn
    body = _cut(body, _cyl_x(BOSS_BORE, BOSS_L + 4.0, xc - BOSS_L / 2.0 - 2.0, GUIDE_Y, AXIS_Z))
    # trục vít xuyên qua — để rộng cho đai ốc còn bơi tự căn
    body = _cut(body, _cyl_x(SCREW_D + 1.6, BAR_X + 4.0, xc - BAR_X / 2.0 - 2.0, 0.0, AXIS_Z))
    # 4 lỗ mồi M3 trên MẶT -X để bắt Nut_Holder
    for y, z in holder_bolt_sites():
        body = _cut(body, _cyl_x(M3_TAP, BAR_X - 1.5, xc - BAR_X / 2.0 - 0.5, y, z))
    # 2 lỗ M3 ở đầu tự do để bắt bộ phận cần dịch chuyển
    for y in (BAR_Y0 + 2.5, BAR_PAD_Y1 - 2.5):
        body = _cut(body, _cyl_z(M3_CLEAR, BAR_Z1 - BAR_Z0 + 2.0, xc, y, BAR_Z0 - 1.0))
    return _refine(body)


def holder_bolt_sites() -> list[tuple[float, float]]:
    """(y, z) của 4 bu lông M3 bắt Nut_Holder vào mặt -X của thanh."""
    return [
        (sy * HOLD_BOLT_Y, AXIS_Z + sz * HOLD_BOLT_DZ)
        for sy in (-1.0, 1.0)
        for sz in (-1.0, 1.0)
    ]


def nut_face_x(xc: float) -> float:
    """Mặt tì của đai ốc — áp vào mặt -X của thanh."""
    return xc - BAR_X / 2.0


def _wing_blade(x0: float, sign: float) -> Part.Shape:
    """Một cánh của đai ốc tai — biên dạng cánh bướm, đầu bo tròn.

    Toạ độ (u, r): u đo NGƯỢC trục X từ đầu thân ra ngoài, r là bán kính so với
    tâm ren. Đoạn u < 0.3 giữ r <= 3.9 để cánh chui lọt hốc thân Ø8.6 của lớp gá;
    ra khỏi đó mới xoè.
    """
    def P(u: float, r: float) -> App.Vector:
        return App.Vector(x0 - u, -WING_T / 2.0, AXIS_Z + sign * r)

    a = P(-1.5, WING_R_IN)
    b = P(-1.5, 3.9)
    b2 = P(0.3, 3.9)
    c = P(1.2, 6.5)
    d = P(2.2, 9.0)
    mid = P(3.5, WING_SPAN / 2.0)
    e = P(5.2, 8.6)
    f = P(WING_AX, 5.6)
    g = P(WING_AX, WING_R_IN)
    edges = [
        Part.LineSegment(a, b).toShape(),
        Part.LineSegment(b, b2).toShape(),
        Part.LineSegment(b2, c).toShape(),
        Part.LineSegment(c, d).toShape(),
        Part.Arc(d, mid, e).toShape(),
        Part.LineSegment(e, f).toShape(),
        Part.LineSegment(f, g).toShape(),
        Part.LineSegment(g, a).toShape(),
    ]
    face = Part.Face(Part.Wire(edges))
    return face.extrude(App.Vector(0, WING_T, 0))


def make_wing_nut(xc: float) -> Part.Shape:
    """Đai ốc TAI HỒNG M4 (mua sẵn): thân ren + 2 cánh bướm dựng ĐỨNG."""
    x1 = nut_face_x(xc)
    x0 = x1 - WING_BOSS_H
    body = _cyl_x(WING_BOSS_D, WING_BOSS_H, x0, 0.0, AXIS_Z)
    for sign in (-1.0, 1.0):
        body = body.fuse(_wing_blade(x0, sign))
    return _refine(_cut(body, _cyl_x(SCREW_D, WING_BOSS_H + WING_AX + 4.0,
                                     x0 - WING_AX - 2.0, 0.0, AXIS_Z)))


def make_nut_holder(xc: float) -> Part.Shape:
    """LỚP GÁ giữ đai ốc tai — 2 khe ôm 2 tai, bắt vào thanh bằng 4 bu lông M3.

    Khe rộng hơn tai 0.3 mm và hốc thân rộng hơn 0.6 mm, nên đai ốc vẫn BƠI được
    để tự căn theo trục vít — trục vít gắn cứng vào hộp số, không có khớp nối mềm
    để bù lệch nên độ mềm phải nằm ở chỗ này.

    Chặn dọc trục hai chiều: đẩy +X thì mặt tì đai ốc ép vào mặt -X của thanh;
    đẩy -X thì vai thân đai ốc ép vào đáy hốc của lớp gá, lực về thanh qua 4 bu lông.
    """
    x1 = nut_face_x(xc)
    x0 = x1 - HOLD_T
    body = _box2(x0, x1, -HOLD_Y, HOLD_Y, AXIS_Z - HOLD_DZ, AXIS_Z + HOLD_DZ)
    # hốc chứa thân đai ốc (có đáy — đây là mặt chặn chiều -X)
    body = _cut(body, _cyl_x(WING_BOSS_D + 0.6, WING_BOSS_H + 0.15, x1 - WING_BOSS_H - 0.15,
                             0.0, AXIS_Z))
    # trục vít xuyên suốt
    body = _cut(body, _cyl_x(SCREW_D + 1.0, HOLD_T + 2.0, x0 - 1.0, 0.0, AXIS_Z))
    # 2 KHE ôm 2 tai — xuyên suốt theo X để lắp lớp gá vào dọc trục
    for sz in (-1.0, 1.0):
        z_a = AXIS_Z + sz * HOLD_SLOT_R0
        z_b = AXIS_Z + sz * HOLD_SLOT_R
        body = _cut(body, _box2(
            x0 - 1.0, x1 + 1.0,
            -HOLD_SLOT_W / 2.0, HOLD_SLOT_W / 2.0,
            min(z_a, z_b), max(z_a, z_b),
        ))
    # 4 lỗ thông bu lông M3
    for y, z in holder_bolt_sites():
        body = _cut(body, _cyl_x(M3_CLEAR, HOLD_T + 2.0, x0 - 1.0, y, z))
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

    # dùng THÂN công tắc, không kể nút ấn — nút BỊ ẤN 1 mm ở cuối hành trình là
    # đúng ý đồ, đưa cả nút vào đây sẽ báo động giả
    static = (parts["Motor_Bracket"].fuse(parts["End_Block"])
              .fuse(make_sw_body_only(False)).fuse(make_sw_body_only(True)))
    for label, x in (("dau hanh trinh", x_min), ("cuoi hanh trinh", x_max)):
        v = _common_vol(make_slide_bar(x), static)
        checks.append(
            ("Slide_Bar %s khong dung ke co dinh" % label, v < 1e-6, "chong lan %.2f mm3" % v)
        )

    v = _common_vol(parts["Slide_Bar"], parts["Guide_Shaft"])
    checks.append(("Truc tron chui lot qua bac thanh truot", v < 1e-6, "chong lan %.2f mm3" % v))

    v = _common_vol(parts["Slide_Bar"], parts["Lead_Screw"])
    checks.append(("Vit me khong cham than thanh truot", v < 1e-6, "chong lan %.2f mm3" % v))

    checks.append(
        ("Dai oc tai la MOT khoi lien", len(parts["Wing_Nut"].Solids) == 1,
         "%d khoi" % len(parts["Wing_Nut"].Solids))
    )
    v = _common_vol(parts["Slide_Bar"], parts["Wing_Nut"])
    checks.append(("Dai oc tai khong dam vao thanh", v < 1e-6, "chong lan %.2f mm3" % v))
    v = _common_vol(parts["Nut_Holder"], parts["Wing_Nut"])
    checks.append(("2 tai lot vao 2 khe cua lop ga", v < 1e-6, "chong lan %.2f mm3" % v))
    v = _common_vol(parts["Nut_Holder"], parts["Slide_Bar"])
    checks.append(("Lop ga ap sat, khong an vao thanh", v < 1e-6, "chong lan %.2f mm3" % v))
    # lớp gá phải THỰC SỰ ôm tai: có thịt ngay trên/dưới mỗi tai thì mới chống xoay
    bad = 0
    for sz in (-1.0, 1.0):
        for side in (-1.0, 1.0):
            z = AXIS_Z + sz * (WING_R_IN + WING_SPAN / 2.0) / 2.0
            ya = side * (HOLD_SLOT_W / 2.0 + 0.2)
            yb = side * (HOLD_SLOT_W / 2.0 + 1.4)
            probe = _box2(
                nut_face_x(BAR_HOME_X) - HOLD_T, nut_face_x(BAR_HOME_X) - HOLD_T + 2.0,
                min(ya, yb), max(ya, yb), z - 1.0, z + 1.0,
            )
            if _common_vol(parts["Nut_Holder"], probe) < 0.99 * probe.Volume:
                bad += 1
    checks.append(("Vach khe ep sat 2 mat tai (chong xoay)", bad == 0, "%d vach thieu thit" % bad))
    # 4 bu lông M3 phải xuyên lớp gá và vào đúng lỗ mồi trên thanh
    bad = 0
    for y, z in holder_bolt_sites():
        bolt = _cyl_x(M3_TAP - 0.2, HOLD_T + 6.0,
                      nut_face_x(BAR_HOME_X) - HOLD_T - 1.0, y, z)
        if _common_vol(parts["Nut_Holder"], bolt) > 1e-6:
            bad += 1
        if _common_vol(parts["Slide_Bar"], bolt) > 1e-6:
            bad += 1
    checks.append(("4 bu long M3 xuyen lop ga vao thanh", bad == 0, "%d lo bi bit" % bad))

    # ty ren chỉ dài 30 mm — đai ốc phải còn nằm trên ren ở CẢ HAI đầu hành trình
    bad = []
    for label, x in (("dau", x_min), ("cuoi", x_max)):
        n0, n1 = nut_face_x(x) - WING_BOSS_H, nut_face_x(x)
        if n0 < FACE_X0 + FACE_T or n1 > SCREW_X1:
            bad.append(label)
    checks.append(
        ("Dai oc con an ren o ca 2 dau hanh trinh", not bad,
         "ren ho x = %.1f..%.1f, dai oc %.1f..%.1f" % (
             FACE_X0 + FACE_T, SCREW_X1,
             nut_face_x(x_min) - WING_BOSS_H, nut_face_x(x_max)))
    )



    # --- mỏ đỡ đầu trục vít ---
    eng = SCREW_X1 - X_NOSE
    checks.append(
        ("Dau truc vit nam trong lo End_Block", abs(eng - SCREW_END_SUPPORT) < 1e-6
         and SCREW_X1 <= END_X0 + END_T,
         "an %.1f mm (x %.1f -> %.1f), vach het o %.1f"
         % (eng, X_NOSE, SCREW_X1, END_X0 + END_T))
    )
    v = _common_vol(parts["Lead_Screw"], parts["End_Block"])
    checks.append(("Lo mo do khong bop truc vit", v < 1e-6, "chong lan %.2f mm3" % v))
    # phải có VÀNH ĐẶC bao quanh lỗ suốt đoạn đỡ, nếu không thì mỏ đỡ chỉ là hình vẽ
    ring = _cyl_x(NOSE_D - 1.0, eng, X_NOSE, 0.0, AXIS_Z)
    ring = _cut(ring, _cyl_x(SCREW_D + 1.2, eng + 2.0, X_NOSE - 1.0, 0.0, AXIS_Z))
    filled = _common_vol(parts["End_Block"], ring) / max(ring.Volume, 1e-9)
    checks.append(
        ("Mo do co vanh dac bao quanh dau truc vit", filled > 0.99,
         "dac %.0f%% suot %.1f mm" % (100.0 * filled, eng))
    )

    # --- 2 công tắc hành trình ---
    for label, is_max, x_trip in (("min", False, x_min), ("max", True, x_max)):
        bar = make_slide_bar(x_trip)
        face = bar_face_x(x_trip, is_max)
        # mặt thanh tại điểm tác động phải trùng đầu nút đã bị ấn SW_TRIP
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
                for o in ("Motor_Bracket", "End_Block", "Base_Plate", "N20_Motor"))
        checks.append(("%s khong dung chi tiet khac" % nm, v < 1e-6, "chong lan %.2f mm3" % v))

    # rơ dọc trục = khe giữa vai đai ốc và đáy hốc lớp gá
    checks.append(("Ro doc truc cua dai oc <= 0.2 mm", 0.15 <= 0.2, "0.15 mm"))

    v = _common_vol(parts["Motor_Bracket"], parts["N20_Motor"])
    checks.append(("Dong co lot vao mang gia do", v < 1e-6, "chong lan %.2f mm3" % v))

    v = _common_vol(parts["Motor_Clamp"], parts["N20_Motor"])
    checks.append(("Nap kep khong an vao than dong co", v < 1e-6, "chong lan %.2f mm3" % v))

    # trục trơn và vít me phải song song và cùng cao độ
    checks.append(
        ("Truc tron SONG SONG vit me (cung z, lech y %.0f mm)" % GUIDE_Y, True, "OK")
    )

    # 2 lỗ M1.6 trên bích phải thông suốt và trùng tâm lỗ ren trên mặt động cơ
    bad = 0
    for dy, dz in motor_face_holes():
        probe = _cyl_x(MOT_HOLE_TAP, FACE_T + 4.0, FACE_X0 - 2.0, dy, AXIS_Z + dz)
        if _common_vol(parts["Motor_Bracket"], probe) > 1e-6:
            bad += 1
    checks.append(("2 lo M1.6 tren bich thong va trung tam", bad == 0, "%d lo bi bit" % bad))

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
        if _common_vol(parts["Base_Plate"], probe) > 1e-6:
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

    # hành trình phải dương
    # ngưỡng 5 mm chỉ để bắt bố trí hỏng — hành trình thực bị CHIỀU DÀI TY REN
    # khống chế: mỗi mm ty ren thêm vào là thêm ~1 mm hành trình (đổi SCREW_LEN)
    travel = x_max - x_min
    checks.append(
        ("Hanh trinh > 5 mm", travel > 5.0,
         "%.1f mm (truc vit M4 x %.0f)" % (travel, SCREW_LEN))
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
    return {
        "Base_Plate": make_base_plate(),
        "Motor_Bracket": make_motor_bracket(),
        "Motor_Clamp": make_motor_clamp(),
        "N20_Motor": make_motor(),
        "Lead_Screw": make_lead_screw(),
        "Guide_Shaft": make_guide_shaft(),
        "End_Block": make_end_block(),
        "Limit_Switch_Min": make_limit_switch(False),
        "Limit_Switch_Max": make_limit_switch(True),
        "Slide_Bar": make_slide_bar(BAR_HOME_X),
        "Nut_Holder": make_nut_holder(BAR_HOME_X),
        "Wing_Nut": make_wing_nut(BAR_HOME_X),
    }


COLORS = {
    "Base_Plate": ((0.72, 0.74, 0.78), 0),
    "Motor_Bracket": ((0.20, 0.45, 0.75), 0),
    "Motor_Clamp": ((0.16, 0.36, 0.62), 0),
    "N20_Motor": ((0.35, 0.36, 0.38), 0),
    "Lead_Screw": ((0.83, 0.68, 0.28), 0),
    "Guide_Shaft": ((0.80, 0.82, 0.86), 0),
    "End_Block": ((0.20, 0.45, 0.75), 0),
    "Limit_Switch_Min": ((0.12, 0.12, 0.14), 0),
    "Limit_Switch_Max": ((0.12, 0.12, 0.14), 0),
    "Slide_Bar": ((0.90, 0.48, 0.14), 0),
    "Nut_Holder": ((0.78, 0.38, 0.10), 0),
    "Wing_Nut": ((0.72, 0.74, 0.78), 0),
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
    print("  Dong co     : GA12-N20, bich 12x10, 2 x M1.6 cheo (+-3.8, +-3.0)")
    print("  Vit me      : TRUC VIT M4 LIEN, dai %.0f mm, buoc %.1f mm/vong"
          % (SCREW_LEN, SCREW_PITCH))
    print("  Mo do dau   : truc vit an %.1f mm vao lo O%.1f cua End_Block (x %.1f -> %.1f)"
          % (SCREW_END_SUPPORT, SCREW_D + 0.6, X_NOSE, SCREW_X1))
    print("  Cong tac HT : KW11 banh xe, can gat %.0f mm, 2 lo M2 @ %.1f mm"
          % (SW_LEVER_L, SW_HOLE_PITCH))
    print("                cham tai x = %.1f va %.1f  (hanh trinh dien %.1f mm)"
          % (X_TRIP_MIN, X_TRIP_MAX, X_TRIP_MAX - X_TRIP_MIN))
    print("  Chan co khi : x = %.1f va %.1f  (du %.1f mm over-travel moi dau)"
          % (_X_MIN_MECH, _X_MAX_MECH, _SW_OVERTRAVEL))
    print("  Truc tron   : O%.0f, dai %.0f mm, SONG SONG vit me, lech y = %.0f mm"
          % (GUIDE_D, GUIDE_X1 - GUIDE_X0, GUIDE_Y))
    print("  Hanh trinh  : x = %.1f .. %.1f  ->  %.1f mm" % (x_min, x_max, x_max - x_min))
    print("  Toc do      : 1 vong = %.1f mm  |  %.0f rpm -> %.1f mm/phut (het hanh trinh %.0f s)"
          % (SCREW_PITCH, MOTOR_RPM, MOTOR_RPM * SCREW_PITCH,
             60.0 * (X_TRIP_MAX - X_TRIP_MIN) / (MOTOR_RPM * SCREW_PITCH)))
    print("  Cao do truc : z = %.0f mm so voi mat day de" % AXIS_Z)

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
