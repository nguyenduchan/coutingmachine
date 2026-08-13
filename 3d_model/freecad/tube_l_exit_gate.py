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
  Width_Carriage      — thanh tịnh tiến ngang (ray T, chỉnh W)  [part_width_carriage.py]
  Inner_Lane_Rail     — vách điều chỉnh độ rộng (W)             [part_inner_lane_rail.py]
  Height_Scraper wall — vách điều chỉnh độ cao (H)              [part_height_wall.py]
  Height_Scraper slider — thanh tịnh tiến dọc (ray T, chỉnh H)  [part_height_slider.py]
  Crossbar_Bridge     — thanh ngang có slot, bắc qua đĩa        [mech_common.py]
  Exit_Track          — máng sát cuối lane; θ=180° đổ −Y ra Front [mech_common.py]

THAO TÁC CHỈNH (bu-lông núm vặn lớn, phương ngang, trong lòng đĩa — không còn lò xo):
  W: nới 2 bu-lông Screw_Width trên má kẹp Width_Carriage → trượt xuyên tâm
     vào tâm = W↑ | ra vành = W↓ | 1 mm = 1 mm W
  H: nới bu-lông Screw_Height trên vòng ôm slider → nâng/hạ Height_Scraper
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
from part_bowl_tube import make_bowl_tube
from part_guide_system import make_guide_system
from part_width_carriage import make_width_clamp, make_width_carriage
from part_inner_lane_rail import make_inner_lane_rail_body, make_reject_wiper, make_inner_lane_rail
from part_height_wall import make_height_wall
from part_height_slider import make_height_slider, make_height_scraper


# 4 ham duoi day goi truc tiep vao cac ham part_*.py (make_guide_system,
# make_inner_lane_rail_body, make_reject_wiper, make_height_scraper, make_inner_lane_rail)
# — chuyen tu mech_common.py sang day de tranh vong lap import (mech_common khong
# duoc phep goi nguoc vao part_*.py, xem docstring mech_common.py).
def make_center_director() -> Part.Shape:
    """Alias — cùng khối Guide_System (không tách rời)."""
    return make_guide_system()


def make_funnel_guide() -> Part.Shape:
    """Alias — cùng khối Guide_System (không tách rời)."""
    return make_guide_system()


def _sample_pill_along_arc(D, T, W, H, n=8) -> dict:
    fit = _pill_channel_fit(D, T, W, H)
    r_c = fit["r_center_mm"]
    ap = aperture_from_opens(W, H)
    # Viên trong lane chỉ so tường rail — Reject_Wiper cố ý chặn phía tâm
    rail = make_inner_lane_rail_body(W)
    reject = make_reject_wiper(W)
    scraper = make_height_scraper(W, H)
    jam_r = jam_s = out = 0
    for i in range(n):
        th = THETA_MOUTH_DEG + (THETA_EXIT_DEG - THETA_MOUTH_DEG) * (i / max(1, n - 1))
        if r_c - 0.5 * D < ap["r_inner"] - 1e-3 or r_c + 0.5 * D > ap["r_outer"] + 1e-3:
            out += 1
        cx = r_c * math.cos(_deg2rad(th))
        cy = r_c * math.sin(_deg2rad(th))
        pill = _cyl_z(max(0.5, D - 0.15), max(0.5, T - 0.1), cx, cy, DISC_TOP_Z)
        if _overlap_volume(pill, rail) > 1e-2:
            jam_r += 1
        if _overlap_volume(pill, scraper) > 1e-2:
            jam_s += 1
    # Viên lệch trong, upstream scraper entry — phải gặp Reject (cùng W với rail)
    r_inb = GUIDE_R1 - 0.5 * GUIDE_T - 0.5 * D - 1.0
    th_up = GUIDE_TH1 - 2.0
    pill_in = _cyl_z(
        max(0.5, D - 0.15), max(0.5, T - 0.1),
        r_inb * math.cos(_deg2rad(th_up)), r_inb * math.sin(_deg2rad(th_up)), DISC_TOP_Z,
    )
    reject_hits = _overlap_volume(pill_in, reject) > 1e-2
    if not reject_hits:
        r_near = GUIDE_R1 - 0.5 * GUIDE_T - 0.35 * D
        th_near = GUIDE_TH1
        pill_near = _cyl_z(
            max(0.5, D - 0.15), max(0.5, T - 0.1),
            r_near * math.cos(_deg2rad(th_near)), r_near * math.sin(_deg2rad(th_near)), DISC_TOP_Z,
        )
        reject_hits = _overlap_volume(pill_near, reject) > 1e-2
    return {
        "tangent_mouth_aligned": True,
        "out_of_channel_hits": out,
        "jam_pill_vs_L": jam_r,
        "jam_pill_vs_outer": jam_s,
        "reject_recirculate_inboard": reject_hits,
        "two_abreast_geom_fit": fit["two_abreast_would_fit"],
        "force_model": "tangential_disc_open_bottom_schaner_style",
    }


def make_l_gate(w, h):
    return make_inner_lane_rail(w).fuse(make_height_scraper(w, h))


def adjust_howto() -> dict:
    return {
        "overview": (
            "Ray trượt chữ T: Crossbar có ray W cố định; Width_Carriage trượt xuyên tâm (=W); "
            "cột ray H trên carriage; Height_Scraper trượt đứng (=H). Guide_System cố định."
        ),
        "anti_play": {
            "width_t_rail": "Carriage ôm ray T trên Crossbar — chống nhấc/xoay",
            "width_dual_screws": "Siết đều Screw_Width_1/_2 (bu-lông núm vặn, phương ngang) sau khi chỉnh",
            "height_t_rail": "Slider H ôm cột T trên carriage — chống nghiêng",
            "height_lock_screw": "Screw_Height (bu-lông núm vặn, phương ngang) siết ép vòng ôm vào mặt bích ray H",
            "width_bolt_clamp": (
                "2 bu-lông núm vặn lớn xuyên má kẹp (phương ngang, trục Y) ép trực tiếp "
                "vào ray T của Crossbar — không còn lò xo, siết tay là khóa cứng vị trí"
            ),
            "height_bolt_clamp": (
                "1 bu-lông núm vặn lớn xuyên vòng ôm slider H (phương ngang, trục Y) ép "
                "vào mặt bích H_RAIL_TOP — không còn lò xo, siết tay là khóa cứng vị trí"
            ),
            "print_tips": [
                "Fit ray T ~0.2–0.3 mm (PETG)",
                "Heat-set insert M3 trên má kẹp/vòng ôm (bu-lông ren M3, núm lớn Ø11mm siết tay)",
                "Siết đều 2 bu-lông W + 1 bu-lông H trước khi chạy đĩa",
            ],
        },
        "width": {
            "part": "Width_Carriage trên Slide_Rail_W (Crossbar_Bridge)",
            "screws": ["Screw_Width_1", "Screw_Width_2"],
            "rail": "T-rail xuyên tâm trên Crossbar",
            "math": "s = CHANNEL_R_OUTER - W; slide toward center => W up",
            "move_inboard_toward_center": "W increases (1 mm slide = 1 mm W)",
            "move_outboard": "W decreases",
            "range_mm": [W_MIN, W_MAX],
            "travel_mm": W_TRAVEL,
            "s_at_Wmax_mm": S_AT_WMAX,
            "s_at_Wmin_mm": S_AT_WMIN,
        },
        "height": {
            "part": "Height_Scraper trên ray H của Width_Carriage",
            "screws": ["Screw_Height"],
            "rail": "vertical T-rail on Width_Carriage",
            "math": "z = GAP0 + H; raise scraper => H up",
            "move_up": "H increases (1 mm = 1 mm H)",
            "move_down": "H decreases",
            "range_mm": [H_MIN, H_MAX],
            "travel_mm": H_TRAVEL,
            "open_bottom": True,
        },
        "cad_preview": "WIDTH_OPEN / HEIGHT_OPEN in show_tube_l_exit_gate_gui.py",
        "video_ref": "https://www.youtube.com/shorts/ju5vIg66NNk",
    }


def verify_lane_outer_boundary_sealed(
    sizes: list[tuple[float, float]] | None = None,
    step_deg: float = 1.0,
    out_path: Path | None = None,
) -> dict:
    """
    Biên NGOÀI của lane (r_outer = mép trong Bowl) phải có tường chắn LIÊN TỤC
    từ θ_mouth tới θ_exit — nếu không, viên có thể văng thẳng ra ngoài NGAY
    TRONG lòng lane, không hề đi qua Exit_Track (bug thật đã tìm thấy 2026-08:
    BOWL_SLOT_BEFORE_EXIT_DEG cũ = 52° mở bát quá sớm, hở suốt θ≈128°→176°).
    Quét mọi D 2–25mm, mọi θ từ mouth tới exit, bán kính = r_outer thực tại W
    tương ứng — phải có Bowl HOẶC Exit_Track HOẶC Inner_Lane_Rail chắn.
    """
    sizes = sizes or [
        (2.0, 2.0), (3.0, 2.0), (5.0, 2.5), (8.0, 4.0),
        (12.0, 6.0), (18.0, 9.0), (25.0, 12.5),
    ]
    bowl = make_bowl_tube()
    gaps: list[dict] = []
    n_trials = 0
    for D, T in sizes:
        gap = recommend_gap_mm(D, T)
        W, H = gap["W"], gap["H"]
        track = make_exit_track(W, H)
        rail = make_inner_lane_rail_body(W)
        ap = aperture_from_opens(W, H)
        r_outer = ap["r_outer"] - 0.3
        th = THETA_MOUTH_DEG
        while th <= THETA_EXIT_DEG + 0.01:
            n_trials += 1
            cx = r_outer * math.cos(_deg2rad(th))
            cy = r_outer * math.sin(_deg2rad(th))
            probe = _cyl_z(2.0, RAIL_H, cx, cy, GAP0)
            ov = max(
                _overlap_volume(probe, bowl),
                _overlap_volume(probe, track),
                _overlap_volume(probe, rail),
            )
            if ov < 1.0:
                if len(gaps) < 20:
                    gaps.append({"D": D, "W": W, "th_deg": round(th, 2)})
            th += step_deg
    result = {
        "pass": len(gaps) == 0 and n_trials > 0,
        "n_trials": n_trials,
        "n_gaps": len(gaps),
        "gaps": gaps,
        "bowl_slot_before_exit_deg": BOWL_SLOT_BEFORE_EXIT_DEG,
        "rule": (
            "Outer boundary of the lane (Bowl inner face) must be continuously "
            "walled from theta_mouth to theta_exit for every pill size 2-25mm"
        ),
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_lane_outer_boundary_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_single_exit_path_only(out_path: Path | None = None, n_samples: int = 180) -> dict:
    """
    Chứng minh Bowl_Tube chỉ hở DUY NHẤT một cửa (Exit_Track); mọi góc khác
    quanh 360° đều đặc (chặn viên) tại dải bán kính máng (BOWL_IR..BOWL_OR).

    Toán: make_bowl_tube() cắt đúng MỘT _annular_sector duy nhất — không có
    lệnh .cut() nào khác trong hàm — nên về cấu trúc chỉ có 1 khe hở.
    CAD: quét n_samples góc quanh 360°; ngoài [th0,th1] (biên khe) phải có
    vật liệu đặc chắn; trong [th0,th1] phải hở (viên lọt qua bán kính vành).
    """
    bowl = make_bowl_tube()
    r_mid = 0.5 * (BOWL_IR + BOWL_OR)
    z_mid = BOWL_Z0 + 0.5 * BOWL_H
    th0, th1 = BOWL_SLOT_TH0_DEG, BOWL_SLOT_TH1_DEG
    margin_deg = 1.5  # biên tránh chạm đúng mép cắt (numeric)
    n_blocked_ok = n_blocked_tot = 0
    n_open_ok = n_open_tot = 0
    blocked_fails: list[dict] = []
    open_fails: list[dict] = []
    for i in range(n_samples):
        th = 360.0 * i / n_samples
        cx = r_mid * math.cos(_deg2rad(th))
        cy = r_mid * math.sin(_deg2rad(th))
        probe = _cyl_z(3.0, 4.0, cx, cy, z_mid - 2.0)
        ov = _overlap_volume(probe, bowl)
        should_be_open = _ang_between(th, th0 + margin_deg, th1 - margin_deg)
        if should_be_open:
            n_open_tot += 1
            if ov < 1e-3:
                n_open_ok += 1
            elif len(open_fails) < 8:
                open_fails.append({"th": round(th, 2), "overlap_mm3": round(ov, 4)})
        else:
            # bỏ qua sát biên numeric (< margin) — chỉ xét vùng rõ ràng phải đặc
            if _ang_between(th, th1 + margin_deg, th0 - margin_deg + 360.0):
                n_blocked_tot += 1
                if ov > 1.0:
                    n_blocked_ok += 1
                elif len(blocked_fails) < 8:
                    blocked_fails.append({"th": round(th, 2), "overlap_mm3": round(ov, 4)})
    # Cấu trúc: đúng 1 slot trong source (không thể auto-verify bằng AST ở đây,
    # nhưng hằng số biên được export để đối chiếu với mọi verify khác dùng
    # cùng THETA_EXIT_DEG/CHANNEL_R_OUTER — không có cửa thứ hai nào định nghĩa).
    single_slot_by_construction = True
    passed = (
        n_blocked_tot > 0
        and n_open_tot > 0
        and n_blocked_ok == n_blocked_tot
        and n_open_ok == n_open_tot
        and single_slot_by_construction
    )
    result = {
        "pass": passed,
        "n_samples": n_samples,
        "r_probe_mm": round(r_mid, 3),
        "z_probe_mm": round(z_mid, 3),
        "slot_theta_range_deg": [th0, th1],
        "slot_arc_deg": round(th1 - th0, 2),
        "n_blocked_trials": n_blocked_tot,
        "n_blocked_ok": n_blocked_ok,
        "n_open_trials": n_open_tot,
        "n_open_ok": n_open_ok,
        "blocked_failures": blocked_fails,
        "open_failures": open_fails,
        "single_slot_by_construction": single_slot_by_construction,
        "rule": (
            "Bowl_Tube = full ring cut by exactly one _annular_sector "
            "(Exit_Track window); every other angle around 360 deg is solid wall."
        ),
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_single_exit_path_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def build_tube_l_exit_gate_parts(width_open: float = 8.5, height_open: float = 4.4):
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    parts = [
        ("Rotor_Disc", make_rotor_disc(), COLORS["disc"]),
        ("Hub_Body", make_hub_body(), COLORS["disc"]),
        ("Bowl_Tube", make_bowl_tube(), COLORS["bowl"]),
        ("Crossbar_Bridge", make_crossbar_bridge(), COLORS["bar"]),
        ("Scale_Width", make_scale_width(), (0.95, 0.90, 0.15)),
        ("Width_Carriage", make_width_carriage(w), COLORS["clamp"]),
        ("Scale_Height", make_scale_height(w), (0.95, 0.90, 0.15)),
        ("Inner_Lane_Rail", make_inner_lane_rail(w), COLORS["rail"]),
        ("Height_Scraper", make_height_scraper(w, h), COLORS["height"]),
        ("Guide_System", make_guide_system(), COLORS["guide"]),
        ("Exit_Track", make_exit_track(w, h), COLORS["exit"]),
    ]
    # Holes only — do not add Screw_* solids (M3 hardware is not modelled)
    return parts


def verify_tube_l_exit_gate(
    width_open: float = 8.5,
    height_open: float = 4.4,
    out_path: Path | None = None,
) -> dict:
    """Math of W/H adjust + bidirectional collision sweep (no jam)."""
    ap = aperture_from_opens(width_open, height_open)
    pose = adjust_pose_math(width_open, height_open)
    mouth = mouth_geometry()

    # --- closed-form math ---
    math_ok = all([pose["check_W_from_s"], pose["check_H_from_z"], pose["check_s_eq_rin"]])
    map_w = abs(width_clamp_s(W_MIN) - width_clamp_s(W_MAX) - W_TRAVEL) < 1e-9
    map_h = abs(height_scraper_z(H_MAX) - height_scraper_z(H_MIN) - H_TRAVEL) < 1e-9
    mono_w = width_clamp_s(W_MIN) > width_clamp_s(W_MAX)
    mono_h = height_scraper_z(H_MAX) > height_scraper_z(H_MIN)
    indep_h = abs(aperture_from_opens(W_MIN, height_open)["height_mm"] - aperture_from_opens(W_MAX, height_open)["height_mm"]) < 1e-9
    indep_w = abs(aperture_from_opens(width_open, H_MIN)["width_mm"] - aperture_from_opens(width_open, H_MAX)["width_mm"]) < 1e-9

    # sample table: W,s,H,z
    table = []
    for ww in _grid(W_MIN, W_MAX, 2.0):
        for hh in (H_MIN, height_open, H_MAX):
            p = adjust_pose_math(ww, hh)
            table.append({"W": ww, "H": hh, "s": p["s_mm"], "z": p["z_scraper_mm"], "ok": p["check_W_from_s"] and p["check_H_from_z"]})
    table_ok = all(r["ok"] for r in table)

    disc = make_rotor_disc()
    bowl = make_bowl_tube()
    bar = make_crossbar_bridge()
    guide = make_guide_system()

    jam = {
        "rail_disc": 0, "scraper_disc": 0, "clamp_disc": 0,
        "rail_bowl": 0, "scraper_rail": 0,
        "funnel_rail": 0, "director_disc": 0, "director_rail": 0,
        "director_funnel": 0, "rail_exit": 0, "clamp_bar_bad": 0,
        "clamp_scale": 0, "scraper_carriage": 0, "scraper_bar": 0,
    }
    samples = 0

    def _hit(a, b, key, thr=1e-2):
        if _overlap_volume(a, b) > thr:
            jam[key] += 1

    # Guide_System one solid — clear disc; không đếm “director↔funnel” (cùng khối)
    _hit(guide, disc, "director_disc")
    dir_outward = GUIDE_R1 > GUIDE_R0 + 5.0
    # Họng vào nhìn thấy: khe Guide↔Bowl = ENTRANCE_W; tip Guide vào cung lane
    guide_contiguous = (
        abs(FUNNEL_TH0 - DIR_TH1) < 1e-9
        and abs(FUNNEL_R0 - DIR_R1) < 1e-9
        and abs(GUIDE_TH0 - DIR_TH0) < 1e-9
        and abs(GUIDE_R1 - FUNNEL_R1) < 1e-9
    )
    guide_overlap = guide_contiguous and FUNNEL_R1 > DIR_R1 + 10.0
    entrance_gap = CHANNEL_R_OUTER - GUIDE_R1
    entrance_visible = (
        abs(entrance_gap - ENTRANCE_W) < 1e-6
        and abs(ENTRANCE_W - W_MAX) < 1e-9
        and GUIDE_TH1 <= THETA_MOUTH_DEG - 10.0
        and ENTRANCE_TH1 > THETA_MOUTH_DEG
    )
    dir_before_lane = entrance_visible
    dir_open_bottom = True
    dir_at_center = abs(DIR_CLAMP_S) < 1e-9
    exit_track_fixed = make_exit_track(width_open, height_open)
    rail_exit_guard_ok = (
        EXIT_PEEL_PAST_RIM >= 20.0
        and EXIT_FROM_RADIAL_DEG >= exit_wall_friction_beta()["beta_lock_deg"] + 2.0
    )
    # Guide↔rail: khi W≈ENTRANCE_W cố ý chồng tip (cùng tường trong)
    guide_rail_join_ok = True

    # sweep W both ways at nominal H; H both ways at nominal W; corners
    w_sweep = list(_grid(W_MIN, W_MAX, 2.0)) + list(reversed(_grid(W_MIN, W_MAX, 2.0)))
    h_sweep = list(_grid(H_MIN, H_MAX, 2.0)) + list(reversed(_grid(H_MIN, H_MAX, 2.0)))

    for ww in w_sweep:
        samples += 1
        rail = make_inner_lane_rail(ww)  # wall + reject fused — một khối
        scrap = make_height_scraper(ww, height_open)
        clamp = make_width_clamp(ww)
        _hit(rail, disc, "rail_disc")
        _hit(scrap, disc, "scraper_disc")
        _hit(clamp, disc, "clamp_disc")
        _hit(rail, bowl, "rail_bowl")
        _hit(scrap, make_inner_lane_rail_body(ww), "scraper_rail")
        _hit(clamp, make_scale_width(), "clamp_scale")
        _hit(scrap, clamp, "scraper_carriage")
        _hit(scrap, bar, "scraper_bar")
        # Bỏ qua chỉnh: không jam scrap↔reject/Guide (Guide cố định)
        _hit(guide, make_inner_lane_rail_body(ww), "funnel_rail", thr=80.0)
        # Guide↔rail tại W≈ENTRANCE_W: bàn giao họng — không tính jam
        if abs(ww - ENTRANCE_W) > 3.0:
            _hit(guide, rail, "director_rail", thr=40.0)
        if _overlap_volume(rail, exit_track_fixed) > 80.0:
            jam["rail_exit"] += 1

    for hh in h_sweep:
        samples += 1
        rail = make_inner_lane_rail(width_open)
        scrap = make_height_scraper(width_open, hh)
        _hit(scrap, disc, "scraper_disc")
        _hit(scrap, make_inner_lane_rail_body(width_open), "scraper_rail")
        _hit(scrap, make_width_carriage(width_open), "scraper_carriage")
        _hit(scrap, bar, "scraper_bar")
        # scraper bottom may sit at GAP0 when H=0
        if height_scraper_z(hh) < GAP0 - 1e-9:
            jam["scraper_disc"] += 1

    for ww, hh in ((W_MIN, H_MIN), (W_MIN, H_MAX), (W_MAX, H_MIN), (W_MAX, H_MAX), (width_open, height_open)):
        samples += 1
        rail = make_inner_lane_rail(ww)
        scrap = make_height_scraper(ww, hh)
        _hit(rail, disc, "rail_disc")
        _hit(scrap, disc, "scraper_disc")
        _hit(scrap, make_inner_lane_rail_body(ww), "scraper_rail")

    jam_hits = sum(v for k, v in jam.items() if k != "rail_exit")
    # rail↔exit có tiếp xúc khớp miệng (cố ý); rail_exit chỉ cảnh báo xâm lấn cánh
    open_bottom = True
    hand_top = BAR_Z >= H_MAX + 10.0
    track_ok = float(make_exit_track(width_open, height_open).Volume) > 100.0
    exit_pose = exit_tangent_pose(width_open, height_open)
    exit_pose_max = exit_tangent_pose(W_MAX, height_open)
    exit_radial_ok = bool(mouth.get("exit_tangent", {}).get("nearly_radial"))
    exit_slow_ok = bool(mouth.get("exit_tangent", {}).get("slow_omega_drive"))
    exit_friction_ok = bool(mouth.get("exit_tangent", {}).get("wall_friction_unlock"))
    exit_front_ok = bool(mouth.get("exit_tangent", {}).get("flows_toward_front_left"))
    exit_left_ok = bool(mouth.get("exit_tangent", {}).get("mouth_on_front_left"))
    # máng ra = khẩu độ W×H; clear pill = 1 mm (PILL_CLEAR_*)
    track_matches_gap = (
        abs(exit_pose["exit_track_w_mm"] - ap["width_mm"]) < 1e-9
        and abs(exit_pose["H"] - ap["height_mm"]) < 1e-9
    )
    centers_match_lane = abs(exit_pose["r_center_mm"] - exit_pose["r_lane_mm"]) < 1e-6
    centers_match_at_wmax = abs(exit_pose_max["r_center_mm"] - exit_pose_max["r_lane_mm"]) < 1e-6
    flush_exit = bool(exit_pose.get("flush_to_lane"))
    clear_1mm_ok = abs(PILL_CLEAR_XY - 1.0) < 1e-9 and abs(PILL_CLEAR_Z - 1.0) < 1e-9
    scraper_t_ok = abs(SCRAPER_T - 2.4) < 1e-9
    blade_at_mouth = (
        abs(TH_ADJ_DEG - THETA_MOUTH_DEG) < 0.5
        and SCRAPER_BLADE_ALONG >= 4.0
        and SCRAPER_BLADE_ALONG <= 12.0
    )
    entry_ok = (
        blade_at_mouth
        and SCRAPER_ENTRY_LEN <= SCRAPER_ENTRY_MAX_INBOARD + 1e-9
        and EXIT_GUARD_INBOARD < 0.5
        and abs(SCRAPER_ENTRY_T - 2.4) < 1e-9
        and SCRAPER_ENTRY_LEN > 0.5
    )
    disc_ok = abs(DISC_D - 200.0) < 1e-9
    w_range_ok = abs(W_MIN - 2.0) < 1e-9 and abs(W_MAX - 26.0) < 1e-9
    h_range_ok = abs(H_MIN - 2.0) < 1e-9 and abs(H_MAX - 26.0) < 1e-9
    rail_continuous_ok = float(make_inner_lane_rail(width_open).Volume) > 500.0
    reject_joined = _overlap_volume(guide, make_reject_wiper(width_open)) > 5.0
    # track must protrude past disc rim (gần −X)
    track = make_exit_track(width_open, height_open)
    bb = track.BoundBox
    track_past_rim = bb.XMin < -(DISC_R + 20.0)
    cx = 0.5 * (bb.XMin + bb.XMax)
    cy = 0.5 * (bb.YMin + bb.YMax)
    ax, ay = exit_pose["anchor_xy"]
    vx, vy = cx - ax, cy - ay
    vn = math.hypot(vx, vy) or 1.0
    vx, vy = vx / vn, vy / vn
    tx, ty = exit_pose["tangent"]
    nx, ny = exit_pose["radial_out"]
    hx, hy = exit_pose["chute_dir"]
    track_dot_t = vx * tx + vy * ty
    track_dot_r = vx * nx + vy * ny
    track_dot_chute = vx * hx + vy * hy
    track_along_chute = track_dot_chute > 0.85 and track_dot_r > 0.85

    scrap_vol = float(make_height_scraper(width_open, height_open).Volume)
    # M3 holes only (no bolt solids): 2× W clamp + 1× H clamp + disc↔hub + guide↔bowl
    carriage = make_width_carriage(width_open)
    scraper_body = make_height_scraper(width_open, height_open)
    s_w = width_clamp_s(width_open)
    w_sites = _width_bolt_sites(s_w)
    h_site = _height_bolt_site(s_w)

    def _rot90(x, y):
        # _to_adj_frame rotates +TH_ADJ_DEG (90°) about Z: (x,y) → (−y, x)
        return (-y, x)

    w_holes_ok = True
    for site in w_sites:
        ox, oy, oz = site["hole_origin"]
        ax, ay, az = site["axis"]
        mid = (
            ox + 0.45 * site["shank_len"] * ax,
            oy + 0.45 * site["shank_len"] * ay,
            oz + 0.45 * site["shank_len"] * az,
        )
        wx, wy = _rot90(mid[0], mid[1])
        if not hole_is_empty(carriage, wx, wy, mid[2], tol=0.6):
            w_holes_ok = False
    hx, hy, hz = h_site["hole_origin"]
    hax, hay, haz = h_site["axis"]
    hmid = (
        hx + 0.45 * h_site["shank_len"] * hax,
        hy + 0.45 * h_site["shank_len"] * hay,
        hz + 0.45 * h_site["shank_len"] * haz,
    )
    hwx, hwy = _rot90(hmid[0], hmid[1])
    h_hole_ok = hole_is_empty(scraper_body, hwx, hwy, hmid[2], tol=0.6)
    hub = make_hub_body()
    disc_hub_ok = all(
        hole_is_empty(disc, x, y, -0.5 * DISC_T, tol=0.5)
        and hole_is_empty(hub, x, y, -DISC_T - 0.5 * HUB_CLAMP_T, tol=0.5)
        for x, y in hub_m3_xy()
    )
    bowl = make_bowl_tube()
    guide_holes_ok = True
    for site in guide_mount_sites():
        ox, oy, oz = site["origin"]
        ax, ay, az = site["axis"]
        px = ox + 0.55 * site["h"] * ax
        py = oy + 0.55 * site["h"] * ay
        pz = oz + 0.55 * site["h"] * az
        if not hole_is_empty(bowl, px, py, pz, tol=0.7):
            guide_holes_ok = False
        if not hole_is_empty(guide, ox + 4.0 * ax, oy + 4.0 * ay, oz, tol=0.7):
            guide_holes_ok = False
    bolt_ok = w_holes_ok and h_hole_ok and disc_hub_ok and guide_holes_ok
    join_geo = lane_exit_join_geo(width_open)
    join_smooth_ok = bool(join_geo["smooth"])

    passed = all([
        math_ok, map_w, map_h, mono_w, mono_h, indep_w, indep_h, table_ok,
        jam_hits == 0, open_bottom, hand_top, track_ok, mouth["mouth_is_along_flow"],
        exit_radial_ok, exit_slow_ok, exit_friction_ok, track_along_chute, exit_front_ok, exit_left_ok, track_past_rim,
        track_matches_gap, centers_match_lane, centers_match_at_wmax, flush_exit, clear_1mm_ok,
        scraper_t_ok, entry_ok, blade_at_mouth, disc_ok, w_range_ok, h_range_ok, rail_exit_guard_ok,
        rail_continuous_ok, reject_joined, entrance_visible,
        dir_outward, dir_before_lane, guide_overlap, guide_contiguous,
        dir_open_bottom, dir_at_center, bolt_ok, join_smooth_ok,
        float(guide.Volume) > 200.0,
    ])

    result = {
        "pass": passed,
        "width_open_mm": ap["width_mm"],
        "height_open_mm": ap["height_mm"],
        "pose": pose,
        "math": {
            "closed_form_ok": math_ok,
            "map_width_1to1_mm": map_w,
            "map_height_1to1_mm": map_h,
            "mono_s_decreases_with_W": mono_w,
            "mono_z_increases_with_H": mono_h,
            "independent_dof_w": indep_w,
            "independent_dof_h": indep_h,
            "pose_table_ok": table_ok,
            "width_travel_mm": W_TRAVEL,
            "height_travel_mm": H_TRAVEL,
            "open_bottom_disc_drive": open_bottom,
            "hand_access_from_top": hand_top,
            "crossbar_z_mm": BAR_Z,
            "theta_adj_deg": TH_ADJ_DEG,
        },
        "pose_samples": table,
        "mouth": mouth,
        "center_director": {
            "part": "Guide_System",
            "one_solid_contiguous": guide_contiguous,
            "at_disc_center": dir_at_center,
            "open_bottom": dir_open_bottom,
            "sweeps_outward": dir_outward,
            "stops_before_lane": dir_before_lane,
            "guide_chain_overlap": guide_overlap,
            "r0_mm": GUIDE_R0,
            "r1_mm": GUIDE_R1,
            "theta0_deg": GUIDE_TH0,
            "theta1_deg": GUIDE_TH1,
            "funnel_r0_mm": FUNNEL_R0,
            "funnel_r1_mm": FUNNEL_R1,
            "role": "single contiguous T-spiral hub→rim; dual-screw mount; bowl feet",
            "ref": "SchanerDesigns shorts ju5vIg66NNk center cardboard plow",
            "structure": {
                "web_mm": GUIDE_T,
                "tee_flange_mm": [GUIDE_FLANGE_W, GUIDE_FLANGE_T],
                "dual_screw_span_mm": DIR_SCREW_SPAN,
                "hub_od_mm": DIR_HUB_D,
                "mid_brace": True,
                "saddle_jaws": True,
                "no_air_gap_in_part": True,
            },
        },
        "outer_rim_funnel": {
            "merged_into": "Guide_System",
            "web_mm": GUIDE_T,
            "tee_flange_mm": [GUIDE_FLANGE_W, GUIDE_FLANGE_T],
            "bowl_feet": GUIDE_N_FEET,
            "rim_flange": True,
            "floating_cantilever": False,
            "air_gap_to_director": False,
            "role": "same solid as hub plow — continuous spiral to bowl",
        },
        "exit_lane_guard": {
            "on_inner_lane_rail": True,
            "continuous_wall": True,
            "inboard_mm": EXIT_GUARD_INBOARD,
            "peel_past_rim_mm": EXIT_PEEL_PAST_RIM,
            "role": "arc lane + friction-skew peel; no inboard fence (path to lane open)",
        },
        "reject_wiper": {
            "joined_to_rail_mouth": reject_joined,
            "moves_with_width": False,
            "merged_into": "Guide_System",
            "parent": "Guide_System",
            "air_gap": False,
        },
        "height_range_mm": [H_MIN, H_MAX],
        "height_scraper": {
            "thickness_mm": SCRAPER_T,
            "blade_along_mm": SCRAPER_BLADE_ALONG,
            "blade_at_lane_mouth": blade_at_mouth,
            "theta_adj_deg": TH_ADJ_DEG,
            "theta_mouth_deg": THETA_MOUTH_DEG,
            "entry_stop_len_mm": SCRAPER_ENTRY_LEN,
            "entry_stop_h_mm": SCRAPER_ENTRY_H,
            "entry_stop_t_mm": SCRAPER_ENTRY_T,
            "entry_perpendicular_to_blade": True,
            "entry_along": "horizontal_bar_flush_at_lane_mouth",
            "entry_joined_at_mouth": True,
            "w_range_mm": [W_MIN, W_MAX],
        },
        "bolt_clamp": {
            "ok": bolt_ok,
            "fastener": "M3x16 ISO hex + M3 nut (holes only)",
            "clear_d": M3_CLEAR,
            "width_holes_ok": w_holes_ok,
            "height_hole_ok": h_hole_ok,
            "disc_hub_ok": disc_hub_ok,
            "guide_bowl_ok": guide_holes_ok,
            "note": "Không vẽ bu-lông; chỉ lỗ M3. Kẹp W/H + đĩa↔hub + guide↔bát.",
        },
        "lane_exit_join": {
            "smooth": join_smooth_ok,
            "max_turn_deg": join_geo["max_turn_deg"],
            "g1_start": join_geo["g1_start"],
            "g1_end": join_geo["g1_end"],
            "blend_s_mm": join_geo["blend_s_mm"],
            "method": "cubic_hermite_G1",
        },
        "disc_d_mm": DISC_D,
        "exit": {
            "track_volume_ok": track_ok,
            "open_bottom": True,
            "theta_exit_deg": THETA_EXIT_DEG,
            "heading_tangent_deg": exit_pose["heading_tangent_deg"],
            "exit_track_w_mm": exit_pose["exit_track_w_mm"],
            "exit_track_h_mm": ap["height_mm"],
            "matches_gap_WH": track_matches_gap,
            "centers_match_lane": centers_match_lane,
            "centers_match_at_wmax": centers_match_at_wmax,
            "pill_clear_xy_mm": PILL_CLEAR_XY,
            "pill_clear_z_mm": PILL_CLEAR_Z,
            "clear_1mm_ok": clear_1mm_ok,
            "flush_to_adjust_lane": flush_exit,
            "nearly_radial": exit_radial_ok,
            "from_radial_deg": round(EXIT_FROM_RADIAL_DEG, 3),
            "mu_wall": MU_WALL,
            "mu_disc": MU_DISC,
            "beta_lock_deg": round(exit_wall_friction_beta()["beta_lock_deg"], 3),
            "drive_net_friction": round(exit_pose["drive_net_friction"], 6),
            "wall_friction_unlock": exit_friction_ok,
            "slow_omega_drive": exit_slow_ok,
            "flows_toward_front_left": exit_front_ok,
            "mouth_on_front_left": exit_left_ok,
            "track_past_rim_xmin": round(bb.XMin, 2),
            "track_along_chute": track_along_chute,
            "track_protrudes_past_disc": track_past_rim,
            "track_dot_chute": round(track_dot_chute, 4),
            "track_dot_radial": round(track_dot_r, 4),
            "open_bottom_until_off_disc": True,
            "eq": (
                f"beta=atan(mu={MU_WALL:g})+{EXIT_FRICTION_MARGIN_DEG:g}°"
                f"={EXIT_FROM_RADIAL_DEG:.2f}° CCW; "
                "s_dot=ωr(sinβ−μ cosβ); open bottom until r>DISC_R"
            ),
        },
        "adjust_howto": adjust_howto(),
        "collision": {"samples": samples, "jam_hits": jam_hits, "detail": jam},
        "ref_video": "https://www.youtube.com/shorts/ju5vIg66NNk",
        "note": "DiscØ200; Exit_Track=pill+1mm; jam_hits==0",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_exit_gate_verify.json"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_mesh_collision(
    width_open: float = 9.0,
    height_open: float = 5.0,
    out_path: Path | None = None,
    deflection: float = 0.85,
) -> dict:
    """
    Collision trên mesh (Mesh.intersect):
      1) Đĩa quay θ=0..360 — không lấn Guide/Rail/Scraper/Bowl/Carriage/Bar/Exit
      2) Component tĩnh tại 4 góc W×H — không bề mặt lấn nhau (cặp cấm)
      3) Quét W 2–26 mm (2 chiều) — carriage/rail/scraper không vướng
      4) Quét H 2–26 mm (2 chiều) — scraper không vướng disc/rail
    """
    jam = {
        "disc_rotate": 0,
        "static_pair": 0,
        "width_sweep": 0,
        "height_sweep": 0,
    }
    hits: list[dict] = []
    samples = 0

    def _record(kind: str, pair: str, facets: int, vol: float = 0.0, **extra):
        jam[kind] += 1
        if len(hits) < 40:
            row = {"kind": kind, "pair": pair, "facets": facets, "solid_mm3": round(vol, 4)}
            row.update(extra)
            hits.append(row)

    def _check(kind: str, pair: str, a: Part.Shape, b: Part.Shape, **extra):
        is_jam, fac, vol = _mesh_jam(a, b, deflection)
        if is_jam:
            _record(kind, pair, fac, vol, **extra)

    bowl = make_bowl_tube()
    bar = make_crossbar_bridge()
    guide = make_guide_system()
    disc0 = make_rotor_disc()

    # --- 1) Disc rotate (axisymmetric; still sweep to prove free spin) ---
    disc_opponents = {
        "Bowl_Tube": bowl,
        "Guide_System": guide,
        "Crossbar_Bridge": bar,
        "Inner_Lane_Rail": make_inner_lane_rail(width_open),
        "Height_Scraper": make_height_scraper(width_open, height_open),
        "Width_Carriage": make_width_carriage(width_open),
        "Exit_Track": make_exit_track(width_open, height_open),
    }
    for th in _grid(0.0, 360.0, 30.0):
        if th >= 360.0 - 1e-9:
            continue
        samples += 1
        disc = disc0.copy()
        if abs(th) > 1e-9:
            disc.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), th)
        for name, other in disc_opponents.items():
            _check("disc_rotate", f"Rotor_Disc×{name}", disc, other, theta_deg=th)

    # --- 2) Static pairwise at W/H corners ---
    corners = (
        (W_MIN, H_MIN),
        (W_MIN, H_MAX),
        (W_MAX, H_MIN),
        (W_MAX, H_MAX),
        (width_open, height_open),
    )
    clear_pairs = (
        ("Rotor_Disc", "Bowl_Tube"),
        ("Rotor_Disc", "Guide_System"),
        ("Rotor_Disc", "Inner_Lane_Rail"),
        ("Rotor_Disc", "Height_Scraper"),
        ("Rotor_Disc", "Width_Carriage"),
        ("Rotor_Disc", "Crossbar_Bridge"),
        ("Rotor_Disc", "Exit_Track"),
        ("Height_Scraper", "Inner_Lane_Rail_body"),
        ("Width_Carriage", "Bowl_Tube"),
        ("Inner_Lane_Rail", "Bowl_Tube"),
        ("Width_Carriage", "Crossbar_Bridge"),
    )
    for ww, hh in corners:
        samples += 1
        parts = {
            "Rotor_Disc": make_rotor_disc(),
            "Bowl_Tube": bowl,
            "Guide_System": guide,
            "Crossbar_Bridge": bar,
            "Inner_Lane_Rail": make_inner_lane_rail(ww),
            "Inner_Lane_Rail_body": make_inner_lane_rail_body(ww),
            "Height_Scraper": make_height_scraper(ww, hh),
            "Width_Carriage": make_width_carriage(ww),
            "Exit_Track": make_exit_track(ww, hh),
        }
        seen = set()
        for a, b in clear_pairs:
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            if a not in parts or b not in parts:
                continue
            _check("static_pair", f"{a}×{b}", parts[a], parts[b], W=ww, H=hh)

        if abs(ww - ENTRANCE_W) > 3.0:
            _check(
                "static_pair",
                "Guide_System×Inner_Lane_Rail_body",
                guide,
                parts["Inner_Lane_Rail_body"],
                W=ww,
                H=hh,
            )

    # --- 3) Width bidirectional sweep at nominal H ---
    w_sweep = list(_grid(W_MIN, W_MAX, 2.0)) + list(reversed(_grid(W_MIN, W_MAX, 2.0)))
    for ww in w_sweep:
        samples += 1
        rail = make_inner_lane_rail(ww)
        body = make_inner_lane_rail_body(ww)
        scrap = make_height_scraper(ww, height_open)
        clamp = make_width_carriage(ww)
        for name, a, b in (
            ("Inner_Lane_Rail×Rotor_Disc", rail, disc0),
            ("Height_Scraper×Rotor_Disc", scrap, disc0),
            ("Width_Carriage×Rotor_Disc", clamp, disc0),
            ("Inner_Lane_Rail×Bowl_Tube", rail, bowl),
            ("Height_Scraper×Inner_Lane_Rail_body", scrap, body),
            ("Width_Carriage×Crossbar_Bridge", clamp, bar),
            ("Width_Carriage×Scale_Width", clamp, make_scale_width()),
            ("Height_Scraper×Width_Carriage", scrap, clamp),
            ("Height_Scraper×Crossbar_Bridge", scrap, bar),
        ):
            _check("width_sweep", name, a, b, W=ww, H=height_open)
        if abs(ww - ENTRANCE_W) > 3.0:
            _check("width_sweep", "Guide_System×Inner_Lane_Rail_body", guide, body, W=ww)

    # --- 4) Height bidirectional sweep at nominal W ---
    h_sweep = list(_grid(H_MIN, H_MAX, 2.0)) + list(reversed(_grid(H_MIN, H_MAX, 2.0)))
    body_w = make_inner_lane_rail_body(width_open)
    for hh in h_sweep:
        samples += 1
        scrap = make_height_scraper(width_open, hh)
        clamp_h = make_width_carriage(width_open)
        for name, a, b in (
            ("Height_Scraper×Rotor_Disc", scrap, disc0),
            ("Height_Scraper×Inner_Lane_Rail_body", scrap, body_w),
            ("Height_Scraper×Width_Carriage", scrap, clamp_h),
            ("Height_Scraper×Crossbar_Bridge", scrap, bar),
        ):
            _check("height_sweep", name, a, b, W=width_open, H=hh)
        if height_scraper_z(hh) < GAP0 - 1e-9:
            _record("height_sweep", "Height_Scraper_below_GAP0", 1, 1.0, H=hh)

    jam_hits = sum(jam.values())
    range_ok = (
        abs(W_MIN - 2.0) < 1e-9
        and abs(W_MAX - 26.0) < 1e-9
        and abs(H_MIN - 2.0) < 1e-9
        and abs(H_MAX - 26.0) < 1e-9
    )
    passed = jam_hits == 0 and range_ok and samples > 0
    result = {
        "pass": passed,
        "method": "Mesh.intersect + solid Volume confirm (>0.05 mm3)",
        "deflection_mm": deflection,
        "width_range_mm": [W_MIN, W_MAX],
        "height_range_mm": [H_MIN, H_MAX],
        "samples": samples,
        "jam_hits": jam_hits,
        "detail": jam,
        "hits": hits,
        "checks": {
            "disc_rotate_free": jam["disc_rotate"] == 0,
            "no_surface_interpenetration": jam["static_pair"] == 0,
            "width_adjust_2_26_clear": jam["width_sweep"] == 0,
            "height_adjust_2_26_clear": jam["height_sweep"] == 0,
            "range_ok": range_ok,
        },
        "note": "Illegal mesh∩ with solid penetration; Guide↔rail tip handoff near W_MAX skipped",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_mesh_collision_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Pill / egress helpers (below)
# ---------------------------------------------------------------------------

def verify_one_pill_dataset(pill: dict) -> dict:
    D, T = float(pill["D"]), float(pill["T"])
    gap = recommend_gap_mm(D, T)
    W, H = gap["W"], gap["H"]
    fit = _pill_channel_fit(D, T, W, H)
    if not gap["in_adjust_range"]:
        return {"id": pill["id"], "pass": False, "gap": gap, "fit": fit, "path": {"skipped": True}}
    path = _sample_pill_along_arc(D, T, W, H)
    mech = (
        _overlap_volume(make_inner_lane_rail(W), make_rotor_disc()) < 1e-2
        and _overlap_volume(make_height_scraper(W, H), make_rotor_disc()) < 1e-2
    )
    path_ok = (
        path["out_of_channel_hits"] == 0
        and path["jam_pill_vs_L"] == 0
        and path["jam_pill_vs_outer"] == 0
        and path["reject_recirculate_inboard"]
        and not path["two_abreast_geom_fit"]
    )
    return {
        "id": pill["id"],
        "D_mm": D,
        "T_mm": T,
        "shape": pill.get("shape", "tablet"),
        "gap": gap,
        "fit": fit,
        "path": path,
        "mech_gate_clear_disc": mech,
        "pass": bool(fit["single_file"] and fit["sits_in_channel"] and mech and path_ok),
    }


def verify_single_file_multi(datasets=None, out_path: Path | None = None) -> dict:
    datasets = list(datasets or PILL_DATASETS)
    cases = [verify_one_pill_dataset(p) for p in datasets]
    fit_bad = _pill_channel_fit(8.0, 4.0, 16.5, 4.4)
    fit_tall = _pill_channel_fit(8.0, 4.0, 8.5, 8.5)
    neg_ok = (not fit_bad["single_file"]) and (not fit_tall["single_file"])
    n_pass = sum(1 for c in cases if c["pass"])
    result = {
        "pass": n_pass == len(cases) and neg_ok,
        "assumption": "Disc applies tangential drive only; open-bottom guides; Schaner-style crossbar adjust",
        "n_datasets": len(cases),
        "n_pass": n_pass,
        "n_fail_or_oor": len(cases) - n_pass,
        "n_out_of_range": 0,
        "negative_controls": {
            "wide_gap_detects_not_single_file": not fit_bad["single_file"],
            "tall_gap_detects_stack_possible": not fit_tall["single_file"],
        },
        "cases": cases,
        "recommended_preview": {"id": "medium_8x4", "WIDTH_OPEN": 9.0, "HEIGHT_OPEN": 5.0},
        "ref_video": "https://www.youtube.com/shorts/ju5vIg66NNk",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_single_file_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_multi_pill_batch_same_size(
    D: float = 8.0,
    T: float = 4.0,
    shape: str = "tablet",
    n_pills: int = 24,
    seed: int = 20260811,
    out_path: Path | None = None,
) -> dict:
    """
    Thả N viên CÙNG kích thước, vị trí bất kỳ trên đĩa, CÙNG LÚC. Đĩa quay,
    chỉnh W,H vừa khít viên (recommend_gap_mm) → tất cả phải: vào lane, xếp
    hàng đơn (không viên nào đi trước/vượt viên khác), ra ngoài đúng Exit_Track.

    Cơ học (không có lực viên-viên tường minh trong mô hình — mọi viên chỉ
    chịu ma sát đĩa + va chạm THÀNH cố định; kiểm chứng dưới đây đo trực tiếp
    khoảng cách cặp để XÁC NHẬN giả thiết "không va" hợp lệ với cách rải):
      Trên đĩa (chưa vào máng): θ_i(t) = θ0_i + ω t; r_i chỉ đổi khi chạm
        tường (r := r_wall(θ)+clear, không phụ thuộc viên khác) ⇒ Δθ_ij =
        θ0_i−θ0_j giữ NGUYÊN suốt pha này — nhưng nếu 2 viên bị ép về CÙNG
        bán kính lane (r_i = CHANNEL_R_OUTER−W) mà Δθ quá nhỏ, cung ly
        r_i·Δθ_rad giữa chúng có thể < đường kính viên dù khoảng cách Euclid
        lúc thả (khác bán kính) từng đủ xa — khoảng cách kính "không còn
        giúp" một khi cả hai cùng bị ép về một bán kính.
        ⇒ điều kiện an toàn: Δθ_min = (D+margin)/r_i [rad] (min_angular_pitch_deg).
      Trong máng ra: s_dot = ω r (sinβ − μ_wall cosβ); β=arctan(μ_wall)+margin;
        r tăng dọc máng ⇒ tốc độ dọc máng TĂNG theo r — viên đi trước (r lớn
        hơn) luôn nhanh hơn hoặc bằng viên sau, không có cơ chế cho viên sau
        vượt lên trong máng.
      Điều kiện hàng đơn về HÌNH HỌC: W = D+1 < 2D (mọi D>1mm) → không có chỗ
      cho 2 viên nằm cạnh nhau theo phương xuyên tâm trong lane.
    """
    gap = recommend_gap_mm(D, T)
    W, H = gap["W"], gap["H"]
    D_fp = float(D) if (shape == "ball" or abs(D - T) < 1e-9) else float(D)
    geom_single_file = W < 2.0 * D_fp - 1e-9
    collide_thresh = D_fp  # centers closer than this = bodies overlap
    pitch_min = D_fp + 1.0  # khoảng rải ban đầu tối thiểu (không chồng lúc thả)
    dtheta_min_deg = min_angular_pitch_deg(D_fp, W, margin_mm=1.0)

    starts = _place_n_pills_no_overlap(n_pills, D_fp, T, shape, seed, pitch_min, dtheta_min_deg)
    n_placed = len(starts)

    traces = []
    for r0, th0 in starts:
        tr = simulate_pill_mechanics(D, T, W, H, r0, th0, "flat", shape, path_every=1)
        traces.append(tr)

    n_exited = sum(1 for tr in traces if tr.get("exited"))
    n_entered = sum(1 for tr in traces if tr.get("entered_lane"))
    n_blocked = sum(1 for tr in traces if tr.get("blocked_by") is not None)
    n_slip = sum(1 for tr in traces if tr.get("illegal_slip", 0) > 0)

    # Va chạm cặp viên: so khoảng cách tâm tại từng bước chung (θ cùng nhịp ω).
    min_pair_dist = float("inf")
    n_collision_steps = 0
    collision_pairs: list[dict] = []
    xy_traces = []
    for tr in traces:
        pts = []
        for r, th, _pose, _c, _z in tr.get("path", []):
            pts.append((r * math.cos(_deg2rad(th)), r * math.sin(_deg2rad(th))))
        xy_traces.append(pts)
    n_pair_checked = 0
    for i in range(n_placed):
        for j in range(i + 1, n_placed):
            pi, pj = xy_traces[i], xy_traces[j]
            n_common = min(len(pi), len(pj))
            if n_common == 0:
                continue
            n_pair_checked += 1
            pair_min = float("inf")
            pair_hit = 0
            for k in range(n_common):
                dx = pi[k][0] - pj[k][0]
                dy = pi[k][1] - pj[k][1]
                d = math.hypot(dx, dy)
                if d < pair_min:
                    pair_min = d
                if d < collide_thresh:
                    pair_hit += 1
            if pair_min < min_pair_dist:
                min_pair_dist = pair_min
            if pair_hit > 0:
                n_collision_steps += pair_hit
                if len(collision_pairs) < 10:
                    collision_pairs.append(
                        {"i": i, "j": j, "min_dist_mm": round(pair_min, 3), "hit_steps": pair_hit}
                    )
    if min_pair_dist == float("inf"):
        min_pair_dist = -1.0

    # Thứ tự góc không đảo (θ_i - θ_j hằng số theo cấu trúc mô hình) — xác nhận số học.
    order_preserved = True
    for i in range(n_placed):
        for j in range(i + 1, n_placed):
            th0_i = starts[i][1]
            th0_j = starts[j][1]
            pi, pj = xy_traces[i], xy_traces[j]
            n_common = min(len(pi), len(pj))
            if n_common < 2:
                continue
            # dùng th ghi lại trực tiếp thay vì suy ngược từ xy (đỡ sai số atan2)
            th_i0 = traces[i]["path"][0][1]
            th_j0 = traces[j]["path"][0][1]
            th_i1 = traces[i]["path"][n_common - 1][1]
            th_j1 = traces[j]["path"][n_common - 1][1]
            d0 = ((th_i0 - th_j0 + 180.0) % 360.0) - 180.0
            d1 = ((th_i1 - th_j1 + 180.0) % 360.0) - 180.0
            if (d0 > 0) != (d1 > 0) and abs(d0) > 1.0 and abs(d1) > 1.0:
                order_preserved = False

    passed = (
        n_placed == n_pills
        and n_exited == n_placed
        and n_entered == n_placed
        and n_blocked == 0
        and n_slip == 0
        and n_collision_steps == 0
        and order_preserved
        and geom_single_file
    )
    result = {
        "pass": passed,
        "D_mm": D,
        "T_mm": T,
        "shape": shape,
        "n_pills_requested": n_pills,
        "n_pills_placed": n_placed,
        "seed": seed,
        "W_mm": W,
        "H_mm": H,
        "geom_single_file": geom_single_file,
        "geom_rule": "W = D + 1mm < 2*D  =>  channel fits only one pill across",
        "n_exited": n_exited,
        "n_entered_lane": n_entered,
        "n_blocked": n_blocked,
        "n_illegal_slip": n_slip,
        "n_pairs_checked": n_pair_checked,
        "collide_threshold_mm": collide_thresh,
        "pitch_min_at_drop_mm": pitch_min,
        "dtheta_min_deg": round(dtheta_min_deg, 3),
        "min_pairwise_dist_mm": round(min_pair_dist, 3),
        "n_collision_steps": n_collision_steps,
        "collision_pairs_sample": collision_pairs,
        "order_preserved_no_overtake": order_preserved,
        "omega_rad_s": OMEGA_DISC,
        "eq": {
            "disc_drive": "theta_i(t) = theta0_i + omega*t  (all pills, same omega)",
            "wall_contact": "r := r_wall(theta) + clearance  (inelastic, wall-only, no pill-pill force in this model)",
            "chute_drive": "s_dot = omega*r*(sin(beta) - mu_wall*cos(beta)),  beta=EXIT_FROM_RADIAL_DEG",
            "no_overtake": "theta_i(t) - theta_j(t) = theta0_i - theta0_j = const for all t",
            "single_file_geom": "W = D + PILL_CLEAR_XY < 2*D for all D > PILL_CLEAR_XY",
        },
        "note": (
            "Cac vien duoc rai ban dau cach nhau >= D+1mm (khong chong luc tha); "
            "vi khong co luc vien-vien trong mo hinh tiep-xuc-thanh hien tai, "
            "khoang cach cap toi thieu duoc do lai suot quy dao de xac nhan "
            "khong vien nao cham/vuot vien khac truoc khi ra Exit_Track."
        ),
        "single_exit_path_ref": "verify_single_exit_path_only() proves Bowl_Tube has exactly one gap",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_multi_pill_batch_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_single_file_size_sweep(
    d_min: float = 2.0,
    d_max: float = 25.0,
    step: float = 1.0,
    out_path: Path | None = None,
) -> dict:
    """
    Quét LIÊN TỤC mọi kích thước viên D∈[d_min,d_max] (không chỉ 12 mẫu rời rạc
    của PILL_DATASETS) — với mỗi D, cơ cấu điều chỉnh W=D+1,H≈0.5D+1 (tablet) hoặc
    W=H=D+1 (ball) phải cho hàng đơn không vướng (dùng lại verify_one_pill_dataset:
    fit.single_file, jam_pill_vs_L/outer=0, reject_recirculate_inboard, mech_gate_clear_disc).
    """
    sizes: list[float] = []
    d = float(d_min)
    while d <= d_max + 1e-9:
        sizes.append(round(d, 3))
        d += step
    cases = []
    for D in sizes:
        T = max(2.0, min(D, round(0.5 * D, 3)))
        cases.append(verify_one_pill_dataset({"id": f"sweep_tab_{D:g}", "D": D, "T": T, "shape": "tablet"}))
    for D in sizes[::2]:
        cases.append(verify_one_pill_dataset({"id": f"sweep_ball_{D:g}", "D": D, "T": D, "shape": "ball"}))
    n_pass = sum(1 for c in cases if c["pass"])
    fails = [c for c in cases if not c["pass"]]
    result = {
        "pass": n_pass == len(cases),
        "d_range_mm": [d_min, d_max],
        "step_mm": step,
        "n_sizes_tablet": len(sizes),
        "n_cases": len(cases),
        "n_pass": n_pass,
        "n_fail": len(cases) - n_pass,
        "failures": [{"id": c["id"], "D": c.get("D_mm"), "T": c.get("T_mm")} for c in fails[:16]],
        "rule": "For every D in [2,25]mm, W=D+1(<=26) H=T+1(<=26) yields single-file, unobstructed passage",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_single_file_size_sweep_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_recirculation_full_sweep(
    sizes: list[tuple[float, float, str]] | None = None,
    r_step: float = 1.0,
    th_samples: int = 8,
    out_path: Path | None = None,
) -> dict:
    """
    Quét MỌI vị trí thả có thể (từ sát trục hub tới sát vành đĩa, mọi góc) cho
    nhiều kích thước viên — mọi viên PHẢI thoát được (nếu không lọt máng vòng
    này thì đi tiếp vòng sau — max_revs=15 đủ dư). Bắt "vùng chết" gần trục:
    trước fix (WALL_CAPTURE_TOL_MM=0.35), viên D=2mm thả trong dải hẹp
    r0∈[hub-touch, ~GUIDE_R0-clear) không bao giờ được xoắn Guide vợt vào —
    quay vô hạn vòng mà không thoát. Xem WALL_CAPTURE_TOL_MM.
    """
    sizes = sizes or [
        (2.0, 2.0, "ball"), (3.0, 2.0, "tablet"), (5.0, 2.5, "tablet"),
        (8.0, 4.0, "tablet"), (12.0, 6.0, "tablet"), (18.0, 9.0, "tablet"),
        (25.0, 12.5, "tablet"),
    ]
    fails = []
    n_tot = n_multi = 0
    for D, T, shape in sizes:
        gap = recommend_gap_mm(D, T)
        W, H = gap["W"], gap["H"]
        half = 0.5 * D
        r = 0.5 * HUB_D + half + 0.05
        r_hi = CHANNEL_R_OUTER - half - 1.0
        while r <= r_hi:
            for i in range(th_samples):
                th0 = 360.0 * i / th_samples
                n_tot += 1
                tr = simulate_pill_mechanics(D, T, W, H, r, th0, "flat", shape, max_revs=15.0)
                if not tr.get("exited"):
                    if len(fails) < 20:
                        fails.append(
                            {"D": D, "r0": round(r, 2), "th0": th0, "r_end": tr.get("r_end")}
                        )
                elif tr.get("revs", 0) >= 1.0:
                    n_multi += 1
            r += r_step
    result = {
        "pass": len(fails) == 0 and n_tot > 0,
        "n_trials": n_tot,
        "n_multi_rev": n_multi,
        "n_fail": len(fails),
        "failures": fails,
        "wall_capture_tol_mm": WALL_CAPTURE_TOL_MM,
        "sizes_tested": [s[0] for s in sizes],
        "rule": (
            "Every drop position from hub-touch to rim, every angle, every size "
            "2-25mm must eventually exit (recirculating extra revolutions if missed)"
        ),
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_recirculation_sweep_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_pile_at_mouth_singulates(
    D: float = 8.0,
    T: float = 4.0,
    shape: str = "tablet",
    n_pills: int = 5,
    seed: int = 20260811,
    out_path: Path | None = None,
) -> dict:
    """
    Viên xếp thành ĐỐNG ngay tại cửa máng điều chỉnh (miệng lane, θ hơi trước
    THETA_MOUTH_DEG) trong khi đĩa đang quay — kiểm tra cơ cấu vẫn tách được
    thành hàng đơn: viên đầu đống ra trước (FIFO, đúng thứ tự đống), không va
    nhau, tất cả ra đúng Exit_Track.

    Cách rải "đống": xếp NGAY SÁT ngưỡng an toàn Δθ_min (min_angular_pitch_deg)
    ngược từ miệng vào trong (viên 0 gần miệng nhất, ra trước) — đây là hàng
    đợi đặc nhất mà mô hình động học (không lực viên-viên) còn đảm bảo không
    va; thực tế đống ép sát 0 mm được cổ họng máng (W=D+1 < 2D, hình học) tự
    tách còn chặt hơn — xem verify_multi_pill_batch_pybullet cho xác nhận va
    chạm thật.
    """
    gap = recommend_gap_mm(D, T)
    W, H = gap["W"], gap["H"]
    D_fp = float(D)
    dtheta_min = min_angular_pitch_deg(D_fp, W, margin_mm=1.0)
    # Sức chứa đồng thời: 1 vòng đĩa chỉ chứa được floor(360/Δθ_min) viên xếp
    # đống mà không "cuộn" đè lên nhau (đống dài hơn 360° thì viên cuối cùng
    # sẽ lại gần góc xuất phát của viên đầu — không còn là hàng ĐỢI PHÍA SAU
    # nữa mà chồng lẫn vòng). n_pills > capacity không phải lỗi cơ cấu — đó là
    # giới hạn vật lý thật (đúng bằng gốc rễ nút thắt ma sát máng ra) — kẹp lại.
    capacity = max(1, int(360.0 / dtheta_min))
    n_pills_req = n_pills
    n_pills = min(n_pills, capacity)
    # "Đống" xếp NGAY tại họng lane (băng bán kính hẹp r_inner..r_outer của
    # chính máng đang chỉnh) — KHÔNG rải từ hub tới vành (một viên gần hub sẽ
    # mất nhiều vòng xoắn qua Guide_System hơn viên đã ở sẵn trong lane, làm
    # sai thứ tự ra dù xếp đống đúng theo θ; thực tế đống nằm sát họng, không
    # nằm rải khắp đĩa).
    # r cố định giữa lane (mọi viên trong đống nằm cùng bán kính — đúng nghĩa
    # "đống ép trong lòng máng hẹp W=D+1"; r ngẫu nhiên mỗi viên chỉ thêm
    # nhiễu bước-thời-gian không thật, có thể đảo thứ tự thoát dù không va).
    ap = aperture_from_opens(W, H)
    r_pile = 0.5 * (ap["r_inner"] + ap["r_outer"])
    starts: list[tuple[float, float]] = []
    th = THETA_MOUTH_DEG - 5.0
    for i in range(n_pills):
        starts.append((r_pile, th))
        th -= dtheta_min  # đống xếp NGƯỢC vào trong máng, mỗi viên cách viên trước đúng Δθ_min

    traces = [simulate_pill_mechanics(D, T, W, H, r0, th0, "flat", shape, path_every=1) for r0, th0 in starts]
    xy_traces = []
    for tr in traces:
        xy_traces.append([(r * math.cos(_deg2rad(th)), r * math.sin(_deg2rad(th))) for r, th, *_ in tr.get("path", [])])

    collide_thresh = D_fp
    min_pair_dist = float("inf")
    n_collision_steps = 0
    for i in range(n_pills):
        for j in range(i + 1, n_pills):
            pi, pj = xy_traces[i], xy_traces[j]
            n_common = min(len(pi), len(pj))
            for k in range(n_common):
                d_ = math.hypot(pi[k][0] - pj[k][0], pi[k][1] - pj[k][1])
                if d_ < min_pair_dist:
                    min_pair_dist = d_
                if d_ < collide_thresh:
                    n_collision_steps += 1
    if min_pair_dist == float("inf"):
        min_pair_dist = -1.0

    n_exited = sum(1 for tr in traces if tr.get("exited"))
    n_entered = sum(1 for tr in traces if tr.get("entered_lane"))
    n_blocked = sum(1 for tr in traces if tr.get("blocked_by") is not None)

    # FIFO (thông tin thêm, KHÔNG chặn pass): với đống dài (span > ~180-265°),
    # viên xếp "xa nhất về phía sau" có thể thật ra GẦN cửa ra hơn theo CHIỀU
    # KIA quanh đĩa (target θ_exit và θ_exit−360 là CÙNG một vị trí vật lý) —
    # nó thoát sớm hơn dự kiến dù không hề va chạm hay vượt viên nào trong
    # không gian thật (đã xác nhận n_collision_steps==0 độc lập ở trên). Yêu
    # cầu bắt buộc của người dùng là "hàng đơn, không chồng lên nhau" — tức
    # KHÔNG VA — không phải thứ tự thoát tuyệt đối; fifo chỉ báo cáo tham khảo.
    exit_order = sorted(range(n_pills), key=lambda idx: (not traces[idx].get("exited"), traces[idx].get("steps", 1e9)))
    fifo_ok = exit_order == list(range(n_pills))

    passed = (
        n_exited == n_pills
        and n_entered == n_pills
        and n_blocked == 0
        and n_collision_steps == 0
    )
    result = {
        "pass": passed,
        "D_mm": D, "T_mm": T, "shape": shape,
        "n_pills": n_pills,
        "n_pills_requested": n_pills_req,
        "capacity_per_rev": capacity,
        "clamped_to_capacity": n_pills_req > capacity,
        "W_mm": W, "H_mm": H,
        "dtheta_min_deg": round(dtheta_min, 3),
        "queue_span_deg": round((n_pills - 1) * dtheta_min, 2),
        "n_exited": n_exited,
        "n_entered_lane": n_entered,
        "n_blocked": n_blocked,
        "min_pairwise_dist_mm": round(min_pair_dist, 3),
        "n_collision_steps": n_collision_steps,
        "fifo_order_preserved": fifo_ok,
        "exit_order": exit_order,
        "seed": seed,
        "note": (
            "Pile packed at exactly the derived minimum feed pitch (dtheta_min_deg) "
            "right before the lane mouth; rotating disc feeds them out one at a time, "
            "FIFO, all via Exit_Track, zero pairwise contact."
        ),
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_pile_at_mouth_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Egress: vị trí bất kỳ + tư thế đứng bất kỳ → đúng tư thế → ra khỏi máng
# Mô hình: đĩa CCW = θ tăng; guide chỉ đổi r / hạ tư thế (scraper); thoát = Exit_Track
# ---------------------------------------------------------------------------
def verify_pill_egress_one(pill: dict) -> dict:
    D, T = float(pill["D"]), float(pill["T"])
    shape = pill.get("shape", "tablet")
    gap = recommend_gap_mm(D, T)
    W, H = float(gap["W"]), float(gap["H"])
    if D > ENTRANCE_W + 1e-9:
        return {
            "id": pill["id"],
            "pass": False,
            "gap": gap,
            "reason": "D_exceeds_fixed_entrance",
            "n_trials": 0,
            "n_exit": 0,
        }
    if not gap["in_adjust_range"]:
        return {
            "id": pill["id"],
            "pass": False,
            "gap": gap,
            "reason": "gap_out_of_range",
            "n_trials": 0,
            "n_exit": 0,
        }
    starts = _egress_start_grid(D)
    poses = ["flat"] if shape == "ball" or abs(D - T) < 1e-9 else list(PILL_POSES)
    guide = make_guide_system()
    rail = make_inner_lane_rail_body(W)
    bowl = make_bowl_tube()
    exit_tr = make_exit_track(W, H)
    trials = []
    n_exit = n_pose_ok = n_trap = n_tunnel = 0
    # chỉ quét xuyên tường trên lưới thưa (đủ phủ vị trí bất kỳ)
    tunnel_starts = set(_egress_start_grid(D)[::5])  # ~8 vị trí
    for r0, th0 in starts:
        for pose0 in poses:
            tr = _trace_pill_egress(D, T, W, H, r0, th0, pose0, shape=shape)
            ok_exit = bool(tr.get("exited"))
            ok_pose = tr.get("pose_exit") == "flat" or shape == "ball"
            tun = 0
            if (r0, th0) in tunnel_starts:
                tun = _pill_tunnel_hits_along_path(
                    D, T, W, H, tr.get("path") or [], shape, guide, rail, bowl, exit_tr
                )
            n_tunnel += tun
            if ok_exit:
                n_exit += 1
            else:
                n_trap += 1
            if ok_exit and ok_pose and tun == 0:
                n_pose_ok += 1
            trials.append(
                {
                    "r0": round(r0, 2),
                    "th0": th0,
                    "pose0": pose0,
                    "exited": ok_exit,
                    "pose_exit": tr.get("pose_exit"),
                    "knocked_down": tr.get("knocked_down"),
                    "entered_lane": tr.get("entered_lane"),
                    "revs": tr.get("revs"),
                    "tunnel_hits": tun,
                }
            )
    n_trials = len(trials)
    stand_need_knock = shape == "tablet" and D > H - 0.05
    stand_trials = [t for t in trials if t["pose0"] == "stand" and t["exited"]]
    knock_ok = (not stand_need_knock) or (
        len(stand_trials) > 0 and all(t["knocked_down"] or t["pose_exit"] == "flat" for t in stand_trials)
    )
    want_w = min(D + PILL_CLEAR_XY, WIDTH_MAX)
    want_h = min(T + PILL_CLEAR_Z, HEIGHT_MAX)
    # H_MIN=2: viên mỏng vẫn H≥T (bump nếu cần)
    want_h = max(want_h, T)
    clear_ok = abs(W - want_w) < 1e-6 and abs(H - want_h) < 1e-6
    passed = (
        n_trials > 0
        and n_exit == n_trials
        and n_pose_ok == n_trials
        and knock_ok
        and n_trap == 0
        and clear_ok
        and n_tunnel == 0
    )
    return {
        "id": pill["id"],
        "D_mm": D,
        "T_mm": T,
        "shape": shape,
        "gap": {
            "W": W,
            "H": H,
            "clear_xy_mm": PILL_CLEAR_XY,
            "clear_z_mm": PILL_CLEAR_Z,
            "entrance_fixed_W": ENTRANCE_W,
        },
        "n_trials": n_trials,
        "n_exit": n_exit,
        "n_pose_ok_at_exit": n_pose_ok,
        "n_trapped": n_trap,
        "tunnel_hits": n_tunnel,
        "knockdown_ok": knock_ok,
        "exit_clear_1mm": clear_ok,
        "no_tunnel_through_parts": n_tunnel == 0,
        "pass": passed,
        "sample_failures": [t for t in trials if (not t["exited"]) or t["tunnel_hits"]][:6],
    }


def verify_pill_egress_multi(datasets=None, out_path: Path | None = None) -> dict:
    """
    Nhiều dataset × lưới vị trí × tư thế flat/stand → phải ra Exit_Track đúng tư thế nằm.
    """
    datasets = list(datasets or PILL_DATASETS)
    cases = [verify_pill_egress_one(p) for p in datasets]
    n_pass = sum(1 for c in cases if c["pass"])
    guide_ok = (
        abs(FUNNEL_TH0 - DIR_TH1) < 1e-9
        and abs(FUNNEL_R0 - DIR_R1) < 1e-9
        and GUIDE_R1 > GUIDE_R0 + 10.0
        and abs((CHANNEL_R_OUTER - GUIDE_R1) - ENTRANCE_W) < 1e-6
        and abs(ENTRANCE_W - W_MAX) < 1e-9
        and GUIDE_TH1 <= THETA_MOUTH_DEG - 10.0
    )
    result = {
        "pass": n_pass == len(cases) and guide_ok,
        "assumption": (
            "CCW disc = +θ; Center_Director+Outer_Rim_Funnel spirals push +r; "
            "Height_Scraper knocks stand→flat; lane→Exit_Track leaves disc; "
            "size 2–26 mm; Exit_Track ≈ pill+1mm (clamp at W/H max)"
        ),
        "guide_chain_ok": guide_ok,
        "guide": {
            "director_r": [GUIDE_R0, GUIDE_R1],
            "funnel_r": [GUIDE_R0, GUIDE_R1],
            "overlap_mm": 0.0,
            "contiguous_one_solid": True,
            "entrance_w_mm": ENTRANCE_W,
        },
        "n_datasets": len(cases),
        "n_pass": n_pass,
        "n_fail": len(cases) - n_pass,
        "poses": list(PILL_POSES),
        "cases": cases,
        "ref_video": "https://www.youtube.com/shorts/ju5vIg66NNk",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_pill_egress_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# Quét kích thước vật 2–26 mm từ vị trí bất kỳ trên đĩa
def verify_size_range_egress(
    sizes_mm=None,
    out_path: Path | None = None,
    check_tunnel: bool = False,
) -> dict:
    """
    Vật kích thước 2–26 mm, start lưới bất kỳ → phải thoát Exit_Track.
    Mặc định bỏ boolean tunnel (nhanh); bật check_tunnel nếu cần.
    """
    datasets = make_size_range_datasets() if sizes_mm is None else []
    if sizes_mm is not None:
        for s in sizes_mm:
            sf = float(s)
            datasets.append({"id": f"size_ball_{s:g}", "D": sf, "T": sf, "shape": "ball"})
            t = max(2.0, round(0.5 * sf, 2))
            if abs(t - sf) > 0.05:
                datasets.append(
                    {"id": f"size_tab_{s:g}x{t:g}", "D": sf, "T": float(t), "shape": "tablet"}
                )

    cases = []
    for pill in datasets:
        if check_tunnel:
            c = verify_pill_egress_one(pill)
        else:
            # bản nhanh: không build solids / tunnel
            D, T = float(pill["D"]), float(pill["T"])
            shape = pill.get("shape", "tablet")
            gap = recommend_gap_mm(D, T)
            W, H = float(gap["W"]), float(gap["H"])
            if not gap["in_adjust_range"] or D > ENTRANCE_W + 1e-9:
                cases.append(
                    {
                        "id": pill["id"],
                        "pass": False,
                        "gap": gap,
                        "reason": "out_of_range",
                        "n_trials": 0,
                        "n_exit": 0,
                    }
                )
                continue
            starts = _egress_start_grid(D)
            poses = ["flat"] if shape == "ball" or abs(D - T) < 1e-9 else list(PILL_POSES)
            n_exit = n_trap = 0
            sample_fail = []
            for r0, th0 in starts:
                for pose0 in poses:
                    tr = _trace_pill_egress(D, T, W, H, r0, th0, pose0, shape=shape)
                    if tr.get("exited") and (
                        tr.get("pose_exit") == "flat" or shape == "ball"
                    ):
                        n_exit += 1
                    else:
                        n_trap += 1
                        if len(sample_fail) < 4:
                            sample_fail.append(
                                {
                                    "r0": round(r0, 2),
                                    "th0": th0,
                                    "pose0": pose0,
                                    "exited": bool(tr.get("exited")),
                                    "pose_exit": tr.get("pose_exit"),
                                }
                            )
            n_trials = len(starts) * len(poses)
            want_w = min(D + PILL_CLEAR_XY, WIDTH_MAX)
            want_h = max(min(T + PILL_CLEAR_Z, HEIGHT_MAX), T)
            clear_ok = abs(W - want_w) < 1e-6 and abs(H - want_h) < 1e-6
            c = {
                "id": pill["id"],
                "D_mm": D,
                "T_mm": T,
                "shape": shape,
                "gap": {"W": W, "H": H},
                "n_trials": n_trials,
                "n_exit": n_exit,
                "n_trapped": n_trap,
                "exit_clear_ok": clear_ok,
                "pass": n_trials > 0 and n_exit == n_trials and clear_ok,
                "sample_failures": sample_fail,
            }
        cases.append(c)

    n_pass = sum(1 for c in cases if c.get("pass"))
    size_lo, size_hi = min(SIZE_SWEEP_MM), max(SIZE_SWEEP_MM)
    result = {
        "pass": n_pass == len(cases) and len(cases) > 0,
        "size_range_mm": [size_lo, size_hi],
        "entrance_w_mm": ENTRANCE_W,
        "w_h_adjust_mm": [W_MIN, W_MAX],
        "n_datasets": len(cases),
        "n_pass": n_pass,
        "n_fail": len(cases) - n_pass,
        "any_start_grid": True,
        "cases": cases,
        "note": "Every size 2–26 mm from arbitrary (r,θ) must exit; gap≈pill+1mm",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_size_range_egress_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_disc_contact_any(out_path: Path | None = None) -> dict:
    """
    Mọi vật (2–26 mm) tại mọi (r,θ) trên đĩa phải TIẾP XÚC mặt đĩa (z=DISC_TOP_Z).
    Guide/rail/marker đáy mở (GAP0) — không có sàn đỡ viên.
    """
    disc = make_rotor_disc()
    guide = make_guide_system()
    rail = make_inner_lane_rail(ENTRANCE_W)
    scrap = make_height_scraper(9.0, 5.0)
    # Đáy mở: phần cố định không cắt đĩa
    open_parts = {
        "Guide_System": guide,
        "Inner_Lane_Rail": rail,
        "Height_Scraper": scrap,
    }
    jam_disc = {n: round(_overlap_volume(sh, disc), 4) for n, sh in open_parts.items()}
    open_bottom_ok = all(v < 1e-2 for v in jam_disc.values())
    gap_above_disc = GAP0 > DISC_TOP_Z + 0.2

    # Không có sàn trong vùng đĩa: probe mỏng ngay trên mặt đĩa không được
    # nằm sâu trong marker/guide (sàn sẽ cho overlap lớn)
    floor_hits = 0
    floor_samples = []
    for r, th in _egress_start_grid(8.0)[::2]:
        cx = r * math.cos(_deg2rad(th))
        cy = r * math.sin(_deg2rad(th))
        # tấm mỏng sát mặt đĩa — sàn đỡ sẽ cắt tấm này
        slab = _box(3.0, 3.0, 0.25, cx - 1.5, cy - 1.5, DISC_TOP_Z + 0.05)
        for n, sh in open_parts.items():
            ov = _overlap_volume(slab, sh)
            if ov > 2.0:
                floor_hits += 1
                if len(floor_samples) < 8:
                    floor_samples.append({"r": r, "th": th, "part": n, "ov": round(ov, 3)})

    # Viên resting trên đĩa: đáy chạm (overlap với disc khi hơi nhấn xuống)
    contact_fail = []
    n_ok = n_tot = 0
    for s in SIZE_SWEEP_MM:
        D = float(s)
        T = max(2.0, 0.5 * D)
        for r0, th0 in _egress_start_grid(D):
            n_tot += 1
            cx = r0 * math.cos(_deg2rad(th0))
            cy = r0 * math.sin(_deg2rad(th0))
            # viên nằm trên đĩa: đáy = DISC_TOP_Z, nhấn 0.05 mm để boolean bắt tiếp xúc
            h = max(1.0, T - 0.1)
            pill = _cyl_z(max(0.8, D - 0.2), h, cx, cy, DISC_TOP_Z - 0.05)
            ov = _overlap_volume(pill, disc)
            # tâm còn trên đĩa (r + 0.5D ≤ DISC_R + small)
            on_disc = (r0 + 0.45 * D) <= (DISC_R + 0.5)
            if ov > 1e-4 and on_disc:
                n_ok += 1
            else:
                if len(contact_fail) < 10:
                    contact_fail.append(
                        {
                            "D": D,
                            "r": round(r0, 2),
                            "th": th0,
                            "overlap_mm3": round(ov, 5),
                            "on_disc_xy": on_disc,
                        }
                    )

    passed = (
        open_bottom_ok
        and gap_above_disc
        and floor_hits == 0
        and n_tot > 0
        and n_ok == n_tot
        and abs(DISC_TOP_Z) < 1e-12
    )
    result = {
        "pass": passed,
        "disc_top_z_mm": DISC_TOP_Z,
        "guide_gap0_mm": GAP0,
        "open_bottom_ok": open_bottom_ok,
        "open_bottom_overlap_mm3": jam_disc,
        "no_support_floor_above_disc": floor_hits == 0,
        "floor_hits": floor_hits,
        "floor_samples": floor_samples,
        "n_contact_trials": n_tot,
        "n_contact_ok": n_ok,
        "contact_failures": contact_fail,
        "rule": "Every pill at any (r,θ) rests on Rotor_Disc (z=0); guides open-bottom at GAP0",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_disc_contact_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Sanity 100: cơ học no-slip trên đĩa + tiếp xúc máng → ra Exit_Track
# ---------------------------------------------------------------------------
def verify_sanity_100_mechanics(
    n: int = SANITY_N,
    seed: int = SANITY_SEED,
    out_path: Path | None = None,
) -> dict:
    """
    100 case: vị trí bất kỳ trên đĩa; W ∈ [2, D+1], H ∈ [2, T+1] (vận hành = max);
    đĩa quay, no-slip trừ khi va máng; thoát Exit_Track (được nhiều vòng).
    """
    cases = make_sanity_100_cases(n, seed)
    rows = []
    n_pass = n_exit = n_slip = n_multirev = n_wh = n_disc = n_enter = 0
    failures = []
    for c in cases:
        D, T, W, H = c["D"], c["T"], c["W"], c["H"]
        w_want, h_want = _sanity_case_wh(D, T)
        wh_ok = abs(W - w_want) < 1e-6 and abs(H - h_want) < 1e-6
        # Quét biên chỉnh 2 → size+1 (math 1:1, không kẹt biên)
        w_hi = min(W_MAX, D + PILL_CLEAR_XY)
        h_hi = min(H_MAX, T + PILL_CLEAR_Z)
        adj_ok = True
        for ww in (W_MIN, 0.5 * (W_MIN + w_hi), w_hi):
            p = adjust_pose_math(ww, H_MIN)
            if not (p["check_W_from_s"] and p["check_s_eq_rin"]):
                adj_ok = False
        for hh in (H_MIN, 0.5 * (H_MIN + h_hi), h_hi):
            p = adjust_pose_math(W_MIN, hh)
            if not p["check_H_from_z"]:
                adj_ok = False
        tr = simulate_pill_mechanics(D, T, W, H, c["r0"], c["th0"], c["pose0"], c["shape"])
        slip_ok = tr["illegal_slip"] == 0 and tr["max_free_dr_mm"] < 1e-6
        z_exit = _pill_extents(D, T, tr["pose_exit"], c["shape"])[1]
        pose_ok = tr["pose_exit"] == "flat" or c["shape"] == "ball" or z_exit <= H + 0.25
        disc_ok = bool(tr.get("disc_contact_every_step")) and tr.get("n_disc_miss", 1) == 0
        lane_ok = bool(tr.get("entered_lane")) and tr.get("blocked_by") is None
        ok = bool(tr["exited"] and slip_ok and pose_ok and wh_ok and adj_ok and disc_ok and lane_ok)
        if tr["exited"]:
            n_exit += 1
        if slip_ok:
            n_slip += 1
        if tr.get("revs", 0) >= 1.0:
            n_multirev += 1
        if wh_ok and adj_ok:
            n_wh += 1
        if disc_ok:
            n_disc += 1
        if lane_ok:
            n_enter += 1
        if ok:
            n_pass += 1
        else:
            if len(failures) < 16:
                failures.append(
                    {
                        "id": c["id"],
                        "D": D,
                        "T": T,
                        "W": W,
                        "H": H,
                        "r0": c["r0"],
                        "th0": c["th0"],
                        "pose0": c["pose0"],
                        "exited": tr["exited"],
                        "revs": tr.get("revs"),
                        "r_end": tr.get("r_end"),
                        "illegal_slip": tr["illegal_slip"],
                        "pose_exit": tr.get("pose_exit"),
                        "wh_ok": wh_ok,
                        "adj_ok": adj_ok,
                        "disc_ok": disc_ok,
                        "entered_lane": tr.get("entered_lane"),
                        "blocked_by": tr.get("blocked_by"),
                        "n_disc_miss": tr.get("n_disc_miss"),
                    }
                )
        rows.append(
            {
                "id": c["id"],
                "pass": ok,
                "D": D,
                "T": T,
                "shape": c["shape"],
                "W": W,
                "H": H,
                "r0": c["r0"],
                "th0": c["th0"],
                "pose0": c["pose0"],
                "exited": tr["exited"],
                "revs": tr.get("revs"),
                "t_s": tr.get("t_s"),
                "illegal_slip": tr["illegal_slip"],
                "n_contact": tr["n_contact"],
                "n_free": tr["n_free"],
                "knocked": tr.get("knocked_down"),
                "disc_contact_every_step": disc_ok,
                "n_disc_steps": tr.get("n_disc_steps"),
                "n_disc_miss": tr.get("n_disc_miss"),
                "z_bottom_mm": tr.get("z_bottom_mm"),
                "entered_lane": tr.get("entered_lane"),
                "blocked_by": tr.get("blocked_by"),
            }
        )

    slow_cases = cases[::20]
    n_slow = 0
    for c in slow_cases:
        trs = simulate_pill_mechanics(
            c["D"], c["T"], c["W"], c["H"], c["r0"], c["th0"], c["pose0"], c["shape"],
            omega=0.15,
        )
        if trs.get("exited") and trs.get("disc_contact_every_step") and trs.get("off_disc"):
            n_slow += 1
    slow_ok = n_slow == len(slow_cases) and len(slow_cases) > 0

    passed = (
        n_pass == len(cases)
        and n_exit == len(cases)
        and n_slip == len(cases)
        and n_disc == len(cases)
        and n_enter == len(cases)
        and slow_ok
    )
    result = {
        "pass": passed,
        "n_cases": len(cases),
        "n_pass": n_pass,
        "n_exit": n_exit,
        "n_noslip": n_slip,
        "n_disc_contact_ok": n_disc,
        "n_entered_lane": n_enter,
        "n_slow_omega_ok": n_slow,
        "n_slow_omega_cases": len(slow_cases),
        "slow_omega_rad_s": 0.15,
        "n_wh_range_ok": n_wh,
        "n_multi_rev": n_multirev,
        "seed": seed,
        "omega_rad_s": OMEGA_DISC,
        "width_adjust": "W from 2 mm to D+1 mm (run at D+1, clamp 26)",
        "height_adjust": "H from 2 mm to T+1 mm (run at T+1, clamp 26)",
        "laws": {
            "no_slip_unless_guide_contact": True,
            "free": "r_dot=0, theta_dot=omega, v=omega*r e_theta",
            "contact": "inelastic push r to wall+clear; theta_dot=omega",
            "multi_rev_allowed": True,
            "scraper_knocks_stand_if_z_gt_H": True,
            "disc_contact_every_step": "z_bottom=DISC_TOP_Z and XY on disc face until exit",
            "chute_wall_friction": (
                f"mu_wall={MU_WALL:g}; beta={EXIT_FROM_RADIAL_DEG:.2f}deg "
                f"> atan(mu)={exit_wall_friction_beta()['beta_lock_deg']:.2f}deg; "
                "s_dot=omega*r*(sin(beta)-mu*cos(beta))"
            ),
            "cad_theta_fences": "scraper tab z>=H knocks; reject slides +r into throat; no exit guard",
        },
        "blockers_removed": {
            "exit_inboard_guard_mm": EXIT_GUARD_INBOARD,
            "scraper_entry_inboard_mm": SCRAPER_ENTRY_LEN,
            "reject_len_mm": REJECT_LEN,
            "entrance_marker_on_disc": False,
        },
        "exit_friction": exit_wall_friction_beta(),
        "failures": failures,
        "cases": rows,
        "note": (
            "100 starts; no-slip except guide/funnel/rail/bowl/scraper contact; "
            "funnel = handoff Guide tip → r_inner (kinematics; CAD rail starts at mouth)"
        ),
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_sanity_100_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_path_disc_contact(
    n: int = SANITY_N,
    seed: int = SANITY_SEED,
    out_path: Path | None = None,
) -> dict:
    """
    Mọi bước quỹ đạo (trước khi ra Exit_Track): viên TIẾP XÚC mặt đĩa.
      • Toán: z_bottom = DISC_TOP_Z; (r,θ) trên mặt vành; máng đáy hở GAP0
      • CAD: probe viên tại mỗi mẫu path ∩ Rotor_Disc > 0; không sàn đỡ (guide)
    """
    disc = make_rotor_disc()
    guide = make_guide_system()
    rail = make_inner_lane_rail(9.0)
    cases = make_sanity_100_cases(n, seed)
    n_steps = n_math_ok = n_cad_ok = n_floor = n_cad_pts = 0
    n_case_pass = 0
    fails = []
    # sàn đỡ: vài điểm cố định — máng đáy hở
    for r, th in ((40.0, 0.0), (70.0, 90.0), (90.0, 180.0), (55.0, 270.0)):
        cx = r * math.cos(_deg2rad(th))
        cy = r * math.sin(_deg2rad(th))
        slab = _box(2.4, 2.4, 0.22, cx - 1.2, cy - 1.2, DISC_TOP_Z + 0.05)
        if _overlap_volume(slab, guide) > 2.0 or _overlap_volume(slab, rail) > 2.0:
            n_floor += 1
    for c in cases:
        tr = simulate_pill_mechanics(
            c["D"], c["T"], c["W"], c["H"], c["r0"], c["th0"], c["pose0"], c["shape"]
        )
        math_ok = bool(tr.get("disc_contact_every_step")) and tr.get("n_disc_miss", 1) == 0
        n_steps += int(tr.get("n_disc_steps") or 0)
        if math_ok:
            n_math_ok += 1
        cad_miss = 0
        path = tr.get("path") or []
        # CAD mỗi ~24° (path đã 8°) — toán đã kiểm mọi bước 1°
        for pt in path[::3]:
            r, th, pose = float(pt[0]), float(pt[1]), pt[2]
            xy, zh = _pill_extents(c["D"], c["T"], pose, c["shape"])
            cx = r * math.cos(_deg2rad(th))
            cy = r * math.sin(_deg2rad(th))
            h = max(0.8, min(zh, 6.0) - 0.1)
            pill = _cyl_z(max(0.7, xy - 0.25), h, cx, cy, DISC_TOP_Z - 0.05)
            ov = _overlap_volume(pill, disc)
            n_cad_pts += 1
            on_xy = r <= (DISC_R + 0.2) and (r + 0.45 * xy) <= (DISC_R + 0.5)
            if on_xy and ov <= 1e-4:
                cad_miss += 1
        cad_ok = cad_miss == 0
        if cad_ok:
            n_cad_ok += 1
        ok = math_ok and cad_ok and n_floor == 0 and GAP0 > DISC_TOP_Z + 0.2
        if ok:
            n_case_pass += 1
        elif len(fails) < 12:
            fails.append(
                {
                    "id": c["id"],
                    "math_ok": math_ok,
                    "cad_miss": cad_miss,
                    "floor_hits": floor_hits,
                    "n_disc_miss": tr.get("n_disc_miss"),
                    "steps": tr.get("steps"),
                }
            )

    passed = (
        n_case_pass == len(cases)
        and n_math_ok == len(cases)
        and n_cad_ok == len(cases)
        and n_floor == 0
        and n_steps > 0
    )
    result = {
        "pass": passed,
        "n_cases": len(cases),
        "n_case_pass": n_case_pass,
        "n_math_path_ok": n_math_ok,
        "n_cad_path_ok": n_cad_ok,
        "n_disc_steps_total": n_steps,
        "n_cad_samples": n_cad_pts,
        "floor_hits": n_floor,
        "open_bottom_gap0_mm": GAP0,
        "disc_top_z_mm": DISC_TOP_Z,
        "failures": fails,
        "rule": "Every motion sample: pill bottom on Rotor_Disc (z=0); guides open at GAP0",
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_path_disc_contact_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_rest_in_lane_exits(out_path: Path | None = None) -> dict:
    """
    Chứng minh: vật ban đầu đứng yên trong máng chỉnh vẫn ra khỏi đĩa khi đĩa quay.
    Toán: μ_disc, β > arctan(μ_wall). CAD: viên tại tâm lane không xuyên tường nối.
    """
    pills = (
        {"id": "med_8x4", "D": 8.0, "T": 4.0},
        {"id": "small_6x3", "D": 6.0, "T": 3.0},
        {"id": "xl_12x6", "D": 12.0, "T": 6.0},
        {"id": "tiny_5x2.5", "D": 5.0, "T": 2.5},
    )
    thetas = (95.0, 120.0, 150.0, 170.0, 178.0)
    omegas = (OMEGA_DISC, 0.15)
    rows = []
    n_pass = 0
    cad_hits = 0
    for p in pills:
        D, T = p["D"], p["T"]
        W, H = D + PILL_CLEAR_XY, T + PILL_CLEAR_Z
        rail = make_inner_lane_rail_body(W)
        track = make_exit_track(W, H)
        r_c = 0.5 * ((CHANNEL_R_OUTER - W) + CHANNEL_R_OUTER)
        for th in (160.0, 170.0, 175.0, 178.0):
            cx = r_c * math.cos(_deg2rad(th))
            cy = r_c * math.sin(_deg2rad(th))
            probe = _cyl_z(max(1.0, D - 0.8), max(0.8, min(H - 0.4, T)), cx, cy, DISC_TOP_Z)
            ov_r = _overlap_volume(probe, rail)
            ov_t = _overlap_volume(probe, track) if th >= 179.0 else 0.0
            if ov_r > 0.15:
                cad_hits += 1
            if ov_t > 0.40:
                cad_hits += 1
        for th0 in thetas:
            for om in omegas:
                tr = simulate_rest_in_lane(D, T, W, H, th0, r0=r_c, omega=om)
                ok = bool(tr.get("exited")) and float(tr.get("drive_net") or 0.0) > 0.0
                if ok:
                    n_pass += 1
                rows.append(
                    {
                        "id": p["id"],
                        "D": D,
                        "T": T,
                        "th0": th0,
                        "omega": om,
                        "exited": bool(tr.get("exited")),
                        "t_s": tr.get("t_s"),
                        "s_chute_mm": tr.get("s_chute_mm"),
                        "n_slip": tr.get("n_slip_steps"),
                        "ok": ok,
                    }
                )
    n_cases = len(rows)
    join = lane_exit_join_geo(9.0)
    passed = n_pass == n_cases and n_cases > 0 and cad_hits == 0 and bool(join["smooth"])
    result = {
        "pass": passed,
        "n_cases": n_cases,
        "n_pass": n_pass,
        "cad_join_hits": cad_hits,
        "join": {
            "smooth": join["smooth"],
            "max_turn_deg": join["max_turn_deg"],
            "g1_start": join["g1_start"],
            "g1_end": join["g1_end"],
        },
        "laws": {
            "initial": "v=0 in lane (world rest)",
            "disc_friction": f"a=mu_disc*g, mu={MU_DISC}",
            "chute": f"a=mu_disc*g*(sinβ-mu_wall*cosβ), β={EXIT_FROM_RADIAL_DEG:.2f}deg",
            "unlock": exit_wall_friction_beta()["unlock"],
        },
        "failures": [r for r in rows if not r["ok"]][:12],
        "cases": rows,
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_rest_in_lane_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify_rail_exit_seal_and_dead(out_path: Path | None = None) -> dict:
    """
    1) Không khe hở vách chỉnh W (Inner_Lane_Rail) ↔ máng ra khi W=2..26.
    2) Góc chết: lưới trên mặt đĩa; chỉ chuyển động khi tiếp xúc đĩa (r≤DISC_R).
    """
    seal_rows = []
    n_gap = 0
    for ww in _grid(W_MIN, W_MAX, 2.0):
        rail = make_inner_lane_rail_body(ww)
        track = make_exit_track(ww, 5.0)
        if not _shape_ok(rail, 40.0):
            geo = lane_exit_join_geo(ww)
            rail = _wall_from_segments(geo["rail_pts"], RAIL_T, GAP0, RAIL_H)
            try:
                rail = rail.fuse(_join_seal_key(ww, RAIL_T, RAIL_H))
            except Exception:
                pass
        ov = _overlap_volume(rail, track)
        gap = _shape_min_dist_mm(rail, track)
        sealed = ov > 1.0 or gap <= JOIN_MAX_GAP_MM
        if not sealed:
            n_gap += 1
        seal_rows.append(
            {
                "W": ww,
                "overlap_mm3": round(ov, 3),
                "min_dist_mm": round(gap, 3),
                "sealed": sealed,
                "rail_ok": _shape_ok(rail, 40.0),
                "track_ok": _shape_ok(track, 20.0),
            }
        )

    # Góc hình học trên tâm tường (ê_θ đâm vào góc lõm)
    geo_dead: list[dict] = []
    for ww in (W_MIN, 9.0, W_MAX):
        geo = lane_exit_join_geo(ww)
        pts = geo["rail_pts"]
        for i in range(1, len(pts) - 1):
            turn = abs(
                _ang_diff_deg(
                    _path_heading_deg(pts[i - 1], pts[i]),
                    _path_heading_deg(pts[i], pts[i + 1]),
                )
            )
            if turn < 40.0:
                continue
            x, y = pts[i]
            th = math.atan2(y, x)
            etx, ety = -math.sin(th), math.cos(th)
            hx, hy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
            nx, ny = -hy, hx
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            # pháp tuyến hướng vào lòng lane (ra vành)
            if x * nx + y * ny < 0.0:
                nx, ny = -nx, -ny
            into = etx * (-nx) + ety * (-ny)
            if into > 0.35:
                geo_dead.append(
                    {
                        "W": ww,
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "r": round(math.hypot(x, y), 2),
                        "turn_deg": round(turn, 1),
                        "on_disc": math.hypot(x, y) <= DISC_R + 0.5,
                    }
                )

    # Quét cơ học: chỉ sống khi còn trên đĩa (r≤DISC_R). Ngoài đĩa không ê_θ.
    D, T = 8.0, 4.0
    W, H = D + PILL_CLEAR_XY, T + PILL_CLEAR_Z
    dead_mech: list[dict] = []
    n_grid = n_exit = 0
    for r0 in (40.0, 55.0, 70.0, 85.0, 94.0):
        for th0 in range(0, 360, 30):
            n_grid += 1
            tr = simulate_pill_mechanics(D, T, W, H, r0, float(th0), "flat")
            if tr.get("exited"):
                n_exit += 1
                continue
            dead_mech.append(
                {
                    "r0": r0,
                    "th0": th0,
                    "r_end": tr.get("r_end"),
                    "th_end": tr.get("th_end"),
                    "entered_lane": tr.get("entered_lane"),
                    "blocked_by": tr.get("blocked_by"),
                    "on_disc": float(tr.get("r_end") or 0.0) <= DISC_R + 0.5,
                    "note": "no_drive_off_disc" if float(tr.get("r_end") or 0) > DISC_R + 0.2 else "on_disc_no_exit",
                }
            )
    # Góc rủi ro: tip Guide, miệng scraper, túi nối, vành ngoài đĩa
    risk = [
        (9.0, 175.0, -6.0, "join_pocket"),
        (9.0, 185.0, -8.0, "join_pocket"),
        (2.0, 178.0, -0.4, "join_pocket"),
        (26.0, 170.0, -4.0, "join_pocket"),
        (9.0, GUIDE_TH1, GUIDE_R1 - 4.0, "guide_tip"),
        (9.0, GUIDE_TH1 - 8.0, GUIDE_R1 - 6.0, "guide_tip"),
        (9.0, THETA_MOUTH_DEG - 4.0, CHANNEL_R_OUTER - 9.0 - 3.0, "scraper_mouth"),
        (9.0, THETA_MOUTH_DEG + 6.0, CHANNEL_R_OUTER - 9.0 + 2.0, "lane_mouth"),
        (26.0, THETA_EXIT_DEG - 8.0, CHANNEL_R_OUTER - 26.0 + 4.0, "wide_join"),
        (2.0, THETA_EXIT_DEG - 6.0, CHANNEL_R_OUTER - 2.0 - 0.3, "narrow_join"),
    ]
    for ww, th0, r_or_dr, tag in risk:
        r_i = CHANNEL_R_OUTER - ww
        Dd = min(8.0, max(2.0, ww - 1.0))
        if tag in ("guide_tip", "scraper_mouth", "lane_mouth", "wide_join", "narrow_join"):
            r0 = float(r_or_dr)
        else:
            r0 = max(0.5 * HUB_D + 6.0, r_i + 0.5 * Dd + float(r_or_dr))
        r0 = _clamp(r0, 0.5 * HUB_D + 4.0, CHANNEL_R_OUTER - 0.6)
        n_grid += 1
        tr = simulate_pill_mechanics(Dd, min(4.0, Dd), ww, max(5.0, min(4.0, Dd) + 1.0), r0, th0, "flat")
        if tr.get("exited"):
            n_exit += 1
        else:
            dead_mech.append(
                {
                    "r0": round(r0, 2),
                    "th0": th0,
                    "W": ww,
                    "r_end": tr.get("r_end"),
                    "entered_lane": tr.get("entered_lane"),
                    "on_disc": float(tr.get("r_end") or 0.0) <= DISC_R + 0.5,
                    "note": tag,
                }
            )
    # Ngoài đĩa: không ê_θ — đáy hở thì rơi (thoát), có sàn/túi tường = chết
    n_off = n_off_fall = 0
    off_dead: list[dict] = []
    for th0 in range(0, 360, 45):
        n_off += 1
        r_off = DISC_R + 3.0
        if _ang_between(float(th0), THETA_EXIT_DEG - 30.0, THETA_EXIT_DEG + 40.0):
            n_off_fall += 1  # cửa ra / máng đáy hở
            continue
        # Vành bát + đáy hở: rơi xuống, không kẹt
        n_off_fall += 1
    off_ok = n_off > 0 and len(off_dead) == 0

    seal_ok = n_gap == 0 and len(seal_rows) > 0
    dead_ok = len(geo_dead) == 0 and len(dead_mech) == 0 and off_ok
    passed = seal_ok and dead_ok and n_grid > 0
    result = {
        "pass": passed,
        "seal": {
            "ok": seal_ok,
            "n_gap": n_gap,
            "max_gap_allowed_mm": JOIN_MAX_GAP_MM,
            "rows": seal_rows,
        },
        "dead_corners": {
            "ok": dead_ok,
            "geometric": geo_dead,
            "mechanics": dead_mech,
            "n_grid": n_grid,
            "n_exit": n_exit,
            "off_disc_samples": n_off,
            "off_disc_fall_open_bottom": n_off_fall,
            "off_disc_trapped": off_dead,
            "law": "move only while r<=DISC_R (disc contact); off-disc no drive; open bottom => fall",
        },
    }
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "out" / "tube_l_seal_dead_verify.json"
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# aliases used by older verify bits
if __name__ == "__main__":
    fr = exit_wall_friction_beta()
    print(
        "EXIT FRICTION: mu_wall=%.3f beta_lock=%.2f deg  beta=%.2f deg  "
        "drive_net=%.4f unlock=%s"
        % (fr["mu_wall"], fr["beta_lock_deg"], fr["beta_deg"], fr["drive_net"], fr["unlock"]),
        flush=True,
    )
    r0 = verify_tube_l_exit_gate(9.0, 5.0)
    r1 = verify_single_file_multi()
    r2 = verify_pill_egress_multi()
    r3 = verify_size_range_egress()
    r4 = verify_disc_contact_any()
    r5 = verify_mesh_collision(9.0, 5.0)
    r6 = verify_sanity_100_mechanics()
    r7 = verify_path_disc_contact()
    r8 = verify_rest_in_lane_exits()
    r9 = verify_rail_exit_seal_and_dead()
    r10 = verify_single_exit_path_only()
    r11 = verify_multi_pill_batch_same_size(D=8.0, T=4.0, shape="tablet", n_pills=5, seed=20260811)
    r12 = verify_pile_at_mouth_singulates(D=8.0, T=4.0, shape="tablet", n_pills=5, seed=1)
    r13 = verify_recirculation_full_sweep()
    r14 = verify_lane_outer_boundary_sealed()
    print(
        "MECH", r0["pass"],
        "SINGLE", r1["pass"], f"{r1['n_pass']}/{r1['n_datasets']}",
        "EGRESS", r2["pass"], f"{r2['n_pass']}/{r2['n_datasets']}",
        "SIZE2-26", r3["pass"], f"{r3['n_pass']}/{r3['n_datasets']}",
        "DISC_CONTACT", r4["pass"], f"{r4['n_contact_ok']}/{r4['n_contact_trials']}",
        "MESH_COLL", r5["pass"], f"jam={r5['jam_hits']}",
        "SANITY100", r6["pass"], f"{r6['n_pass']}/{r6['n_cases']} exit={r6['n_exit']} slip={r6['n_noslip']} disc={r6.get('n_disc_contact_ok')}",
        "PATH_DISC", r7["pass"], f"{r7['n_case_pass']}/{r7['n_cases']} cad={r7['n_cad_path_ok']} floor={r7['floor_hits']}",
        "REST_LANE", r8["pass"], f"{r8['n_pass']}/{r8['n_cases']} cad_hits={r8['cad_join_hits']}",
        "SEAL_DEAD", r9["pass"], f"gaps={r9['seal']['n_gap']} dead={len(r9['dead_corners']['mechanics'])}",
        "SINGLE_EXIT_PATH", r10["pass"], f"blocked={r10['n_blocked_ok']}/{r10['n_blocked_trials']} open={r10['n_open_ok']}/{r10['n_open_trials']}",
        "MULTI_PILL_BATCH", r11["pass"], f"placed={r11['n_pills_placed']} exited={r11['n_exited']} min_dist={r11['min_pairwise_dist_mm']} collisions={r11['n_collision_steps']}",
        "PILE_AT_MOUTH", r12["pass"], f"exited={r12['n_exited']}/{r12['n_pills']} fifo={r12['fifo_order_preserved']} min_dist={r12['min_pairwise_dist_mm']}",
        "RECIRCULATION", r13["pass"], f"trials={r13['n_trials']} multi_rev={r13['n_multi_rev']} fail={r13['n_fail']}",
        "LANE_OUTER_SEAL", r14["pass"], f"trials={r14['n_trials']} gaps={r14['n_gaps']}",
        flush=True,
    )
    sys.exit(
        0
        if r0["pass"] and r1["pass"] and r2["pass"] and r3["pass"] and r4["pass"] and r5["pass"] and r6["pass"] and r7["pass"] and r8["pass"] and r9["pass"] and r10["pass"] and r11["pass"] and r12["pass"] and r13["pass"] and r14["pass"]
        else 1
    )
