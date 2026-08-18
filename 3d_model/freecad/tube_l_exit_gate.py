"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

File nay la ASSEMBLY (lap rap): import cac co cau tu module rieng (part_*.py)
va cac helper/hang so dung chung (mech_common.py), roi ghep lai
(build_tube_l_exit_gate_parts) + chua toan bo verify_* suite. Sua 1 module con
(part_*.py hoac mech_common.py) se tu dong duoc lay vao lan chay lap rap tiep
theo (import Python thuong — khong can dong bo tay).

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng                         [part_rotor_disc.py]
  Bowl_Tube           — thành bao xung quanh đĩa (outer wall)  [part_bowl_tube.py]
  Guide_System        — vách điều hướng (T-spiral hub→vành)    [part_guide_system.py]
  Entry_Gate_Post     — trụ cố định + ray T ĐỨNG ở đầu máng vào  [part_entry_gate.py]
  Entry_Gate_Slider   — thanh tịnh tiến ĐỨNG (chỉnh H)          [part_entry_gate.py]
  Entry_Gate_Barrier  — barrier chữ L chặn chiều cao vào máng    [part_entry_gate.py]
  Entry_Gate_Dial     — đĩa số + cột (CỐ ĐỊNH, bắt vít rời)        [part_entry_gate.py]
  Entry_Gate_Cam      — đĩa cam lệch tâm 9 mm trong khung yoke    [part_entry_gate.py]
  Entry_Gate_Knob     — núm vặn tay khía + vít M3 siết ma sát     [part_entry_gate.py]
  Exit_Inner_Wall     — vách trong CỐ ĐỊNH tại 9h                 [part_exit_inner_wall.py]
  Exit_Inner_Wall_2   — vách TRƯỢT theo +X (chỉnh W) + khung yoke  [part_exit_inner_wall.py]
  Exit_Slide          — 2 ray T + cột đỡ đĩa số                   [part_exit_inner_wall.py]
  Exit_Dial           — đĩa số W (CỐ ĐỊNH, bắt 2 vít M3 rời)      [part_exit_inner_wall.py]
  Exit_Cam / Exit_Knob— cam lệch tâm 9 mm + núm vặn cho W         [part_exit_inner_wall.py]
  Exit_Track          — máng sát cuối lane; θ=180° đổ −Y ra Front [mech_common.py]

LUỒNG: Inner_Lane_Rail + Chute_Slide ĐÃ BỎ — trong LANE không còn vách trong.
Bề rộng lane cố định = họng ra Guide_System (ENTRANCE_W = 20 mm thông thuỷ tính
từ mép đĩa); vật rời tường xoắn thì bị đĩa + ly tâm ép vào thành bát và chạy
theo vành tới cửa ra 9h. Chỗ chỉnh W nằm ở CỬA RA: kênh giữa Exit_Inner_Wall và
Exit_Inner_Wall_2, vách 2 trượt ngang nên bóp/mở kênh được 2–20 mm.

THAO TÁC CHỈNH — HAI NÚM XOAY, cùng nguyên lý cam lệch tâm + Scotch yoke:
  W: VẶN NÚM Exit_Knob (trục ĐỨNG, vặn từ trên xuống) — nửa vòng đưa bề rộng
     thông thuỷ kênh exit từ 13 xuống 3 mm bằng cách trượt Exit_Inner_Wall_2
     theo +X trên 2 ray T. (Họng ra Guide_System vẫn cố định 20 mm.)
  H: VẶN NÚM Entry_Gate_Knob — nửa vòng (0°→180°) đưa H từ 20 xuống 2 mm.
     Cam lệch tâm nằm khít trong khung Scotch yoke của con trượt nên xoay chiều
     nào cũng CƯỠNG BỨC kéo/đẩy (không lò xo, không dây thun, không bánh răng);
     hai vách đầu rãnh là CHẶN CỨNG hai đầu dải H; vít M3 ở tâm núm kẹp đĩa số
     làm phanh ma sát tự giữ. Screw_Gate_H chỉ còn là khoá phụ (siết SAU khi
     chỉnh; phải nới ra trước khi vặn núm).
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

# Dam bao import duoc cac module anh em (mech_common.py, part_*.py) du file nay
# duoc chay bang cach nao (freecadcmd truc tiep, runpy.run_path, import tu script
# khac...) — cac cach chay khong phai "truc tiep" khong tu dong them thu muc cua
# file vao sys.path.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ---------------------------------------------------------------------------
# Layout (mm). Disc top Z=0. CCW: at +X velocity ≈ +Y.
# Ref: SchanerDesigns rotary table + slotted crossbar + open-bottom guides.
# ---------------------------------------------------------------------------

from mech_common import *  # noqa: F401,F403
from part_rotor_disc import make_rotor_disc, make_hub_body
from part_bowl_tube import make_bowl_tube, make_bowl_tube_complete
from part_guide_system import make_guide_system
from part_entry_gate import (
    make_entry_gate_barrier, make_entry_gate_slider, make_entry_gate_post,
    build_entry_gate_parts, entry_gate_bolt_site,
)
from part_exit_inner_wall import (
    make_exit_inner_wall, make_exit_inner_wall_2, make_exit_slide,
    make_exit_cam, make_exit_knob, make_exit_dial,
)


# Cac ham duoi day goi truc tiep vao part_*.py (make_guide_system, ...) —
# chuyen tu mech_common.py sang day de tranh vong lap import (mech_common khong
# duoc phep goi nguoc vao part_*.py, xem docstring mech_common.py).
def make_center_director() -> Part.Shape:
    """Alias — cùng khối Guide_System (không tách rời)."""
    return make_guide_system()


def make_funnel_guide() -> Part.Shape:
    """Alias — cùng khối Guide_System (không tách rời)."""
    return make_guide_system()


def adjust_howto() -> dict:
    return {
        "overview": (
            "W: VẶN NÚM Exit_Knob (trục đứng, vặn từ trên) — cam lệch tâm trong "
            "khung Scotch yoke nằm ngang đẩy/kéo Exit_Inner_Wall_2 trên 2 ray T, "
            "đổi bề rộng thông thuỷ kênh exit 3–13 mm. Họng ra Guide_System vẫn cố định. "
            "H: VẶN NÚM Entry_Gate_Knob (nửa vòng = cả dải 20→2 mm) — đĩa cam lệch "
            "tâm nhốt trong khung Scotch yoke của Entry_Gate_Slider, cưỡng bức nâng/hạ "
            "barrier chữ L trên ray T ĐỨNG; khe dưới trần = H. Guide_System cố định."
        ),
        "anti_play": {
            "height_t_rail": "Vòng ôm chữ C ôm bích ray T đứng — chống nghiêng/xoay",
            "height_positive_drive": (
                "Đĩa cam lệch tâm nhốt trong khung Scotch yoke: rãnh cao ĐÚNG Ø đĩa "
                "nên kẹp đĩa cả trên lẫn dưới ⇒ vặn chiều nào con trượt cũng bị "
                "cưỡng bức đi theo, KHÔNG cần lò xo/dây thun hồi vị"
            ),
            "height_lock_screw": (
                "Vít M3 ở TÂM núm siết núm + đĩa cam kẹp đĩa số cố định vào giữa "
                "(phanh đĩa) — đó là cơ cấu tự giữ. Screw_Gate_H trên vòng ôm là "
                "khoá phụ chống rung, nới ra trước khi vặn núm"
            ),
            "print_tips": [
                "Fit ray T ~0.25 mm (PETG)",
                "Khe đĩa cam ↔ rãnh yoke 0.30 mm mỗi phía; cổ trục Ø14 fit 0.30 mm",
                "In Entry_Gate_Cam NẰM (trục thẳng đứng) để cổ trục không tách lớp",
                "Heat-set insert M3 ở đầu cổ trục + trên vòng ôm; 2+2×M3 bắt vào vành bát",
                "Vặn núm về đúng vạch rồi mới siết vít tâm",
                "ĐĨA SỐ PHẢI LÀ CHI TIẾT RỜI: đĩa cam Ø30 bị nhốt giữa đĩa số "
                "Ø52 (lỗ tâm Ø11.6) và lưng khung/ray — đúc liền là không lắp được",
            ],
        },
        "width": {
            "part": "Exit_Inner_Wall_2 trượt theo +X trên 2 ray T của Exit_Slide",
            "screws": ["Screw_Exit_Cam_Pivot (M3 tâm núm W)"],
            "math": "gap = x2 - (EXIT_WALL_X + EXIT_WALL_T)",
            "range_mm": [EXIT_GAP_MIN, EXIT_GAP_MAX],
            "travel_mm": EXIT_GAP_MAX - EXIT_GAP_MIN,
            "adjustable": True,
            "drive": {
                "type": "cam lech tam trong khung Scotch yoke NAM NGANG "
                        "(truc DUNG, num ngua len — van tu tren xuong)",
                "knob": "Exit_Knob (Ø%.0f, %d hom ngon tay, gan mui chi)"
                        % (GATE_KNOB_D, GATE_KNOB_FLUTES),
                "ecc_mm": EXIT_CAM_ECC,
                "cam_d_mm": 2.0 * EXIT_CAM_R,
                "turn_for_full_range_deg": 180.0,
                "math": "gap = EXIT_GAP_MAX - e*(1-cos(theta)), theta 0..180 deg",
                "mm_per_deg_max": round(EXIT_CAM_ECC * math.pi / 180.0, 4),
                "hard_stops": "hai vach dau ranh yoke theo Y",
                "return_spring": False,
                "self_hold": "vit M3 tam num kep dia so nhu phanh dia",
                "dial": "vach chia gap moi 1 mm tren mat TREN dia so",
                "open_wider": "quay num NGUOC chieu kim dong ho (nhin tu tren)",
                "close": "quay num THEO chieu kim dong ho (nhin tu tren)",
            },
            "lane_note": "bề rộng LANE (họng ra Guide_System) vẫn cố định "
                         "ENTRANCE_W = %.0f mm — chỉ kênh exit chỉnh được"
                         % ENTRANCE_W,
        },
        "height": {
            "part": "Entry_Gate_Slider + Entry_Gate_Barrier trên Entry_Gate_Post",
            "screws": ["Screw_Cam_Pivot (M3 tâm núm)", "Screw_Gate_H (khoá phụ)"],
            "rail": "ray T ĐỨNG tại đầu máng vào + khung Scotch yoke ăn đĩa cam",
            "drive": {
                "type": "cam lech tam trong khung Scotch yoke (positive, 2 chieu)",
                "knob": "Entry_Gate_Knob (Ø%.0f, %d hom ngon tay, gan mui chi)"
                        % (GATE_KNOB_D, GATE_KNOB_FLUTES),
                "ecc_mm": GATE_CAM_ECC,
                "cam_d_mm": 2.0 * GATE_CAM_R,
                "turn_for_full_range_deg": 180.0,
                "math": "H = H_MAX - e*(1-cos(theta)), theta 0..180 deg",
                "mm_per_deg_max": round(GATE_CAM_ECC * math.pi / 180.0, 4),
                "hard_stops": "hai vach dau ranh yoke (qua dai H ~1.9 deg la chan)",
                "return_spring": False,
                "self_hold": "vit M3 tam num kep dia so nhu phanh dia",
                "dial": "vach chia H moi 1 mm tren mat dia so, vach dai moi 4 mm",
            },
            "math": "z_roof0 = GAP0 + H; nâng cụm => H lên",
            "move_up": "quay num NGUOC chieu kim dong ho (theta giam) => H tang",
            "move_down": "quay num THEO chieu kim dong ho (theta tang) => H giam",
            "range_mm": [H_MIN, H_MAX],
            "travel_mm": H_TRAVEL,
            "gate_theta_deg": GATE_TH_DEG,
            "barrier_mm": {
                "top_view_w": GATE_W_MM,
                "roof_along": GATE_ROOF_ALONG_MM,
                "wall_h": GATE_WALL_H_MM,
                "outer_edge_r": GATE_R_OUT,
            },
            "open_bottom": True,
        },
        "cad_preview": "WIDTH_OPEN / HEIGHT_OPEN in show_tube_l_exit_gate_gui.py",
        "video_ref": "https://www.youtube.com/shorts/ju5vIg66NNk",
    }


def build_tube_l_exit_gate_parts(width_open: float = 8.5, height_open: float = 4.4):
    # W = bề rộng thông thuỷ kênh exit (Exit_Inner_Wall_2 trượt theo +X).
    # Kẹp theo DẢI KÊNH EXIT (3–13 mm), không theo dải cỡ vật W_MIN/W_MAX (2–20):
    # hai dải nay khác nhau, kẹp nhầm sẽ im lặng cho ra vị trí vách sai.
    w = _clamp(width_open, EXIT_GAP_MIN, EXIT_GAP_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    parts = [
        ("Rotor_Disc", make_rotor_disc(), COLORS["disc"]),
        ("Hub_Body", make_hub_body(), COLORS["disc"]),
        ("Bowl_Tube", make_bowl_tube_complete(), COLORS["bowl"]),
        ("Guide_System", make_guide_system(), COLORS["guide"]),
        ("Exit_Inner_Wall", make_exit_inner_wall(), COLORS["rail"]),
        ("Exit_Inner_Wall_2", make_exit_inner_wall_2(w), COLORS["rail"]),
        ("Exit_Slide", make_exit_slide(), COLORS["slide"]),
        ("Exit_Dial", make_exit_dial(), COLORS["bar"]),
        ("Exit_Cam", make_exit_cam(w), COLORS["reject"]),
        ("Exit_Knob", make_exit_knob(w), COLORS["mouth"]),
    ] + list(build_entry_gate_parts(h))
    # Holes only — do not add Screw_* solids (M3 hardware is not modelled)
    return parts


