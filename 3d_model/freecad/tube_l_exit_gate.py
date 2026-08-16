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
  Exit_Track          — máng sát cuối lane; θ=180° đổ −Y ra Front [mech_common.py]

LUỒNG: Inner_Lane_Rail + Chute_Slide ĐÃ BỎ — không còn vách trong, không còn
chỉnh W. Bề rộng luồng cố định = họng ra Guide_System (ENTRANCE_W = 20 mm thông
thuỷ tính từ mép đĩa); vật rời tường xoắn thì bị đĩa + ly tâm ép vào thành bát
và chạy theo vành tới cửa ra 9h.

THAO TÁC CHỈNH:
  W: KHÔNG chỉnh được nữa (cố định 20 mm — đổi thì phải sửa ENTRANCE_W)
  H: nới Screw_Gate_H trên vòng ôm → nâng/hạ cụm barrier ở đầu máng vào (11h)
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
            "W: KHÔNG chỉnh được — bề rộng luồng cố định = họng ra Guide_System "
            "(ENTRANCE_W, thông thuỷ tính từ mép đĩa). "
            "H: hạ/nâng Entry_Gate_Slider trên ray T ĐỨNG của Entry_Gate_Post ở đầu "
            "máng vào — barrier chữ L treo dưới, khe dưới trần = H. Guide_System cố định."
        ),
        "anti_play": {
            "height_t_rail": "Vòng ôm chữ C ôm bích ray T đứng — chống nghiêng/xoay",
            "height_lock_screw": (
                "Screw_Gate_H (bu-lông núm vặn, phương ngang) siết vòng ôm ép vào bích "
                "ray T — siết tay là khóa cứng vị trí, không dùng lò xo"
            ),
            "print_tips": [
                "Fit ray T ~0.25 mm (PETG)",
                "Heat-set insert M3 trên vòng ôm + 2×M3 bắt chân trụ vào vành bát",
                "Siết bu-lông H trước khi chạy đĩa",
            ],
        },
        "width": {
            "part": "họng ra Guide_System (cố định — không còn cơ cấu trượt)",
            "math": "lane_w = ENTRANCE_W = DISC_R - (GUIDE_R1 + GUIDE_T/2)",
            "fixed_mm": ENTRANCE_W,
            "range_mm": [ENTRANCE_W, ENTRANCE_W],
            "travel_mm": 0.0,
            "adjustable": False,
        },
        "height": {
            "part": "Entry_Gate_Slider + Entry_Gate_Barrier trên Entry_Gate_Post",
            "screws": ["Screw_Gate_H"],
            "rail": "ray T ĐỨNG ngoài vành bát tại đầu máng vào",
            "math": "z_roof0 = GAP0 + H; nâng cụm => H lên",
            "move_up": "H increases (1 mm = 1 mm H)",
            "move_down": "H decreases",
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
    _ = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)  # W cố định — giữ chữ ký cũ
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    parts = [
        ("Rotor_Disc", make_rotor_disc(), COLORS["disc"]),
        ("Hub_Body", make_hub_body(), COLORS["disc"]),
        ("Bowl_Tube", make_bowl_tube_complete(), COLORS["bowl"]),
        ("Guide_System", make_guide_system(), COLORS["guide"]),
        ("Exit_Inner_Wall", make_exit_inner_wall(), COLORS["rail"]),
        ("Exit_Inner_Wall_2", make_exit_inner_wall_2(), COLORS["rail"]),
        ("Exit_Slide", make_exit_slide(), COLORS["slide"]),
    ] + list(build_entry_gate_parts(h))
    # Holes only — do not add Screw_* solids (M3 hardware is not modelled)
    return parts


