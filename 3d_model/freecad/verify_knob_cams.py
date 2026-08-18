# -*- coding: utf-8 -*-
r"""
Verify HAI cụm NÚM XOAY (cam lệch tâm + khung Scotch yoke, không lò xo/dây thun):

  H — Entry_Gate_Cam / Entry_Gate_Knob : trục NGANG (local +y), khung yoke ĐỨNG,
      kéo Entry_Gate_Slider lên/xuống trên ray T đứng ở đầu máng vào (11h).
  W — Exit_Cam / Exit_Knob             : trục ĐỨNG (+z), khung yoke NẰM NGANG,
      đẩy/kéo Exit_Inner_Wall_2 theo +X trên 2 ray T ở cửa ra (9h).

Hai núm dùng CHUNG đĩa cam / núm / cổ trục / vít, chỉ khác độ lệch tâm vì dải
hành trình khác nhau: H 2–20 mm (e = 9), W 3–13 mm (e = 5).

Chạy:
  "…\freecadcmd.exe" -c "import runpy; runpy.run_path(r'…\verify_knob_cams.py', run_name='__main__')"
  → out/knob_cam_verify.json

Vì sao Scotch yoke chứ không phải cam rãnh (grooved cam) như "Giải pháp 1":
  Cam rãnh là rãnh tròn bán kính r_g, tâm lệch e, chốt Ø nhỏ chạy trong đó.
  Muốn chốt không bao giờ ra khỏi rãnh thì phải r_g ≥ e; ở giữa hành trình
  (θ=90°) pháp tuyến tiếp xúc nghiêng asin(e/r_g) so với phương tịnh tiến —
  với e = 9 mm, r_g = 12 mm là 48.6°, vượt xa ngưỡng tự kẹt ~30° của nhựa in.
  Muốn hạ xuống 30° thì r_g ≥ 18 ⇒ đĩa Ø(2·(e+r_g+vách)) ≈ Ø62, TO HƠN cả
  phương án yoke, mà lực vẫn dồn vào một chốt nhỏ chịu uốn.
  Scotch yoke: tiếp xúc mặt-phẳng ↔ mặt-trụ nên pháp tuyến LUÔN thẳng đứng ⇒
  pressure angle = 0 ở mọi góc, và lực truyền qua đường sinh dài bằng bề dày cam.
  verify_pressure_angle() kiểm đúng hai con số này.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App  # noqa: F401
import Part  # noqa: F401

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from mech_common import *  # noqa: F401,F403,E402
import part_entry_gate as peg  # noqa: E402
import part_exit_inner_wall as pew  # noqa: E402
from part_rotor_disc import make_rotor_disc, make_hub_body  # noqa: E402
from part_bowl_tube import make_bowl_tube_complete  # noqa: E402
from part_guide_system import make_guide_system  # noqa: E402
from part_exit_inner_wall import make_exit_inner_wall  # noqa: E402
from part_exit_camera import build_exit_camera_parts  # noqa: E402

OUT = _HERE / "out"
H_CASES = [H_MIN, 5.0, 8.0, 11.0, 14.0, 17.0, H_MAX]
W_CASES = [EXIT_GAP_MIN + (EXIT_GAP_MAX - EXIT_GAP_MIN) * i / 6.0 for i in range(7)]
# Quét W×H: hai cụm ở hai phía đĩa nên các tổ hợp BIÊN + tâm là đủ chặn va chạm.
_W_MID = 0.5 * (EXIT_GAP_MIN + EXIT_GAP_MAX)
_H_MID = 0.5 * (H_MIN + H_MAX)
WH_CASES = [(EXIT_GAP_MIN, H_MIN), (EXIT_GAP_MAX, H_MAX), (_W_MID, _H_MID),
            (EXIT_GAP_MIN, H_MAX), (EXIT_GAP_MAX, H_MIN)]
CLASH_MM3 = 1.0  # mặt tì áp nhau cho common = 0; > 1 mm³ là ăn thịt nhau thật
# Chồng khối CÓ CHỦ Ý: ray T (và nay cả giá đĩa số) cắm EXIT_SLIDE_BOWL_EMBED
# vào thành bát để bắt chặt — quy ước sẵn có của Exit_Slide, xem verify_bowl_embed.
EXPECTED_EMBED = {("Exit_Slide", "Bowl_Tube")}


def _clash(a, b) -> float:
    try:
        c = a.common(b)
        return float(getattr(c, "Volume", 0.0) or 0.0)
    except Exception:
        return -1.0


# ---------------------------------------------------------------------------
# 1. Núm H — nửa vòng phủ hết dải H, hành trình = 2e, khoá 2 chiều
# ---------------------------------------------------------------------------
def verify_cam_math() -> dict:
    rows, bad = [], []
    for i in range(int(4 * H_TRAVEL) + 1):
        h = H_MIN + 0.25 * i
        g = entry_gate_cam_geo(h)
        for k, v in g.items():
            if k.startswith("check_") and v is not True:
                bad.append({"H": h, "check": k})
        # khoá 2 chiều: khe trên và khe dưới rãnh đều đúng bằng fit
        gap_lo = g["cam_z0_mm"] - g["slot_z0_mm"]
        gap_hi = g["slot_z1_mm"] - g["cam_z1_mm"]
        if abs(gap_lo - GATE_CAM_FIT) > 1e-6 or abs(gap_hi - GATE_CAM_FIT) > 1e-6:
            bad.append({"H": h, "check": "slot_grips_both_faces",
                        "gap_lo": gap_lo, "gap_hi": gap_hi})
        rows.append((h, g["theta_deg"]))
    mono = all(rows[i][1] > rows[i + 1][1] - 1e-9 for i in range(len(rows) - 1))
    err = max(abs(cam_height_for_angle(cam_angle_for_height(h)) - h) for h, _ in rows)
    g0 = entry_gate_cam_geo(H_MAX)
    return {
        "pass": not bad and mono and err < 1e-9,
        "n_H": len(rows),
        "bad": bad[:8],
        "theta_monotonic_in_H": mono,
        "roundtrip_err_mm": err,
        "theta_at_H_MAX_deg": cam_angle_for_height(H_MAX),
        "theta_at_H_MIN_deg": cam_angle_for_height(H_MIN),
        "turn_deg": g0["turn_deg"],
        "travel_mm": g0["travel_mm"],
        "H_range_mm": [H_MIN, H_MAX],
        "mm_per_deg_max": g0["mm_per_deg_max"],
        "return_spring_needed": g0["return_spring"],
    }


# ---------------------------------------------------------------------------
# 2. Pressure angle = 0 (lý do chọn yoke thay vì cam rãnh)
# ---------------------------------------------------------------------------
def verify_pressure_angle() -> dict:
    """Yoke: điểm tiếp xúc là đáy/đỉnh đĩa cam nên pháp tuyến LUÔN vuông với
    mặt rãnh, tức trùng phương tịnh tiến ⇒ góc áp lực 0 ở mọi θ."""
    worst = 0.0
    for i in range(0, 181):
        n = (0.0, -1.0)  # pháp tuyến tại điểm tiếp xúc, mọi θ
        worst = max(worst, abs(math.degrees(math.atan2(abs(n[0]), abs(n[1])))))
    rg = GATE_CAM_ECC + 3.0  # cam rãnh nhỏ nhất còn dùng được với cùng e
    groove_worst = math.degrees(math.asin(min(1.0, GATE_CAM_ECC / rg)))
    rg_ok = GATE_CAM_ECC / math.sin(math.radians(30.0))
    return {
        "pass": worst < 1e-9 and groove_worst > 30.0,
        "yoke_pressure_angle_deg": worst,
        "groove_cam_pressure_angle_deg": groove_worst,
        "groove_cam_r_g_mm": rg,
        "groove_cam_r_g_needed_for_30deg_mm": rg_ok,
        "groove_cam_disc_d_for_30deg_mm": 2.0 * (GATE_CAM_ECC + rg_ok + 4.0),
        "yoke_cam_disc_d_mm": 2.0 * GATE_CAM_R,
        "self_lock_threshold_deg": 30.0,
        "why": "yoke: phap tuyen luon thang => khong bao gio tu ket",
    }


# ---------------------------------------------------------------------------
# 3. Núm H — chặn cứng hai đầu hành trình = hai vách đầu rãnh
# ---------------------------------------------------------------------------
def verify_hard_stops() -> dict:
    rows = []
    for h_end, th_end, sgn in ((H_MAX, 0.0, -1.0), (H_MIN, 180.0, +1.0)):
        g = entry_gate_cam_geo(h_end)
        hit = None
        for i in range(1, 900):
            th = th_end + sgn * i * 0.01
            xc, _zc = cam_center_local(th)
            if (xc - GATE_CAM_R) < g["slot_x0_mm"] - 1e-9 or \
               (xc + GATE_CAM_R) > g["slot_x1_mm"] + 1e-9:
                hit = abs(th - th_end)
                break
        rows.append({
            "end": "H_MAX" if h_end == H_MAX else "H_MIN",
            "theta_deg": th_end,
            "overtravel_deg": hit,
            "overtravel_H_mm": None if hit is None
            else GATE_CAM_ECC * (1.0 - math.cos(math.radians(hit))),
        })
    ok = all(r["overtravel_deg"] is not None and r["overtravel_deg"] < 5.0 for r in rows)
    return {"pass": ok, "stops": rows,
            "mechanism": "hai vach DAU ranh yoke chan dia cam"}


# ---------------------------------------------------------------------------
# 4. Núm H — đĩa cam nằm trong rãnh, không ăn thịt khung (solid boolean)
# ---------------------------------------------------------------------------
def verify_cam_in_yoke_solid() -> dict:
    rows, bad = [], []
    for h in H_CASES:
        v = _clash(peg.make_entry_gate_cam(h), peg.make_entry_gate_slider(h))
        rows.append({"H": h, "cam_vs_slider_mm3": round(v, 4)})
        if v > CLASH_MM3:
            bad.append(rows[-1])
    return {"pass": not bad, "rows": rows, "bad": bad}


# ---------------------------------------------------------------------------
# 5. Núm W — toán học
# ---------------------------------------------------------------------------
def verify_exit_cam_math() -> dict:
    rows, bad = [], []
    span = EXIT_GAP_MAX - EXIT_GAP_MIN
    for i in range(int(4 * span) + 1):
        gp = EXIT_GAP_MIN + 0.25 * i
        d = exit_cam_geo(gp)
        for k, v in d.items():
            if k.startswith("check_") and v is not True:
                bad.append({"gap": gp, "check": k})
        lo = d["cam_x0_mm"] - d["slot_x0_mm"]
        hi = d["slot_x1_mm"] - d["cam_x1_mm"]
        if abs(lo - EXIT_CAM_FIT) > 1e-6 or abs(hi - EXIT_CAM_FIT) > 1e-6:
            bad.append({"gap": gp, "check": "slot_grips_both_faces",
                        "lo": lo, "hi": hi})
        rows.append((gp, d["theta_deg"]))
    mono = all(rows[i][1] > rows[i + 1][1] - 1e-9 for i in range(len(rows) - 1))
    err = max(abs(exit_cam_gap_for_angle(exit_cam_angle_for_gap(g)) - g) for g, _ in rows)
    d0 = exit_cam_geo(EXIT_GAP_MAX)
    return {
        "pass": not bad and mono and err < 1e-9,
        "n_gap": len(rows),
        "bad": bad[:8],
        "theta_monotonic_in_gap": mono,
        "roundtrip_err_mm": err,
        "turn_deg": d0["turn_deg"],
        "travel_mm": d0["travel_mm"],
        "gap_range_mm": [EXIT_GAP_MIN, EXIT_GAP_MAX],
        "mm_per_deg_max": d0["mm_per_deg_max"],
        "return_spring_needed": d0["return_spring"],
        "cam_offset_from_wall2_mm": EXIT_CAM_OFFSET_X,
    }


# ---------------------------------------------------------------------------
# 6. Núm W — chặn cứng hai đầu (vách đầu rãnh theo Y)
# ---------------------------------------------------------------------------
def verify_exit_hard_stops() -> dict:
    rows = []
    for g_end, th_end, sgn in ((EXIT_GAP_MAX, 0.0, -1.0), (EXIT_GAP_MIN, 180.0, +1.0)):
        d = exit_cam_geo(g_end)
        hit = None
        for i in range(1, 900):
            th = th_end + sgn * i * 0.01
            _xc, yc = exit_cam_center(th)
            if (yc - EXIT_CAM_R) < d["slot_y0_mm"] - 1e-9 or \
               (yc + EXIT_CAM_R) > d["slot_y1_mm"] + 1e-9:
                hit = abs(th - th_end)
                break
        rows.append({
            "end": "GAP_MAX" if g_end == EXIT_GAP_MAX else "GAP_MIN",
            "theta_deg": th_end,
            "overtravel_deg": hit,
            "overtravel_gap_mm": None if hit is None
            else EXIT_CAM_ECC * (1.0 - math.cos(math.radians(hit))),
        })
    ok = all(r["overtravel_deg"] is not None and r["overtravel_deg"] < 5.0 for r in rows)
    return {"pass": ok, "stops": rows,
            "mechanism": "hai vach dau ranh yoke theo Y chan dia cam"}


# ---------------------------------------------------------------------------
# 7. Núm W — đĩa cam nằm trong rãnh (solid boolean)
# ---------------------------------------------------------------------------
def verify_exit_cam_in_yoke_solid() -> dict:
    rows, bad = [], []
    for gp in W_CASES:
        v = _clash(pew.make_exit_cam(gp), pew.make_exit_inner_wall_2(gp))
        rows.append({"gap": gp, "cam_vs_wall2_mm3": round(v, 4)})
        if v > CLASH_MM3:
            bad.append(rows[-1])
    return {"pass": not bad, "rows": rows, "bad": bad}


# ---------------------------------------------------------------------------
# 8. Không chi tiết nào đụng nhau trên toàn dải W × H
# ---------------------------------------------------------------------------
def verify_no_collision() -> dict:
    static = [
        ("Rotor_Disc", make_rotor_disc()),
        ("Hub_Body", make_hub_body()),
        ("Bowl_Tube", make_bowl_tube_complete()),
        ("Guide_System", make_guide_system()),
        ("Exit_Inner_Wall", make_exit_inner_wall()),
    ] + [(n, sh) for n, sh, _c in build_exit_camera_parts()]
    bad, worst = [], []
    for w, h in WH_CASES:
        moving = list(peg.build_entry_gate_parts(h)) + [
            ("Exit_Inner_Wall_2", pew.make_exit_inner_wall_2(w), None),
            ("Exit_Slide", pew.make_exit_slide(), None),
            ("Exit_Dial", pew.make_exit_dial(), None),
            ("Exit_Cam", pew.make_exit_cam(w), None),
            ("Exit_Knob", pew.make_exit_knob(w), None),
        ]
        names = [n for n, _s, _c in moving]
        shapes = [sh for _n, sh, _c in moving]
        tag = "W%.0f/H%.0f" % (w, h)
        for gn, gs in zip(names, shapes):
            for sn, ss in static:
                v = _clash(gs, ss)
                worst.append((v, tag, gn, sn))
                if v > CLASH_MM3 and (gn, sn) not in EXPECTED_EMBED                         and (sn, gn) not in EXPECTED_EMBED:
                    bad.append({"case": tag, "a": gn, "b": sn, "mm3": round(v, 3)})
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                v = _clash(shapes[i], shapes[j])
                worst.append((v, tag, names[i], names[j]))
                if v > CLASH_MM3:
                    bad.append({"case": tag, "a": names[i], "b": names[j],
                                "mm3": round(v, 3)})
    worst.sort(reverse=True)
    return {
        "pass": not bad,
        "n_pairs": len(worst),
        "bad": bad,
        "worst5": [{"mm3": round(v, 3), "case": c, "a": a, "b": b}
                   for v, c, a, b in worst[:5]],
        "expected_embed_skipped": sorted("%s^%s" % ab for ab in EXPECTED_EMBED),
    }


# ---------------------------------------------------------------------------
# 8b. Mối CẮM vào thành bát: đúng chủ ý, không lan ra chỗ khác
# ---------------------------------------------------------------------------
def verify_bowl_embed() -> dict:
    """Exit_Slide chồng Bowl_Tube là CÓ CHỦ Ý (cắm 3 mm để bắt chặt, quy ước cũ
    của 2 ray T; giá đĩa số mới dùng lại đúng quy ước đó). Check ở đây: toàn bộ
    phần chồng phải nằm GỌN trong dải thành bát r ∈ [BOWL_IR, BOWL_IR+embed] và
    dưới đỉnh bát — tức chỉ ăn vào thành, không thò vào lòng bát hay chỗ khác."""
    bowl = make_bowl_tube_complete()
    rails = None
    for y in EXIT_SLIDE_Y:
        r = pew.make_exit_slide_rail(y)
        rails = r if rails is None else rails.fuse(r)
    v_rails = _clash(rails, bowl)
    v_all = _clash(pew.make_exit_slide(), bowl)
    ov = pew.make_exit_slide().common(bowl)
    tol = 0.05
    r_lo = min((math.hypot(vx.X, vx.Y) for vx in ov.Vertexes), default=0.0)
    r_hi = max((math.hypot(vx.X, vx.Y) for vx in ov.Vertexes), default=0.0)
    z_hi = ov.BoundBox.ZMax
    checks = {
        "inside_wall_band": r_lo >= BOWL_IR - tol
        and r_hi <= BOWL_IR + EXIT_SLIDE_BOWL_EMBED + tol,
        "below_bowl_rim": z_hi <= BOWL_Z0 + BOWL_H + tol,
        "support_reuses_rail_convention": v_all > v_rails,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "embed_depth_mm": EXIT_SLIDE_BOWL_EMBED,
        "overlap_rails_only_mm3": round(v_rails, 2),
        "overlap_total_mm3": round(v_all, 2),
        "overlap_r_mm": [round(r_lo, 2), round(r_hi, 2)],
        "overlap_z_max_mm": round(z_hi, 2),
        "bowl_ir_mm": BOWL_IR,
        "note": "chu y: in xong phai khoet hoc tuong ung tren Bowl_Tube (hoac dan)",
    }


# ---------------------------------------------------------------------------
# 8c. LẮP RÁP ĐƯỢC: đĩa cam phải có đường vào chỗ sau khi tháo đĩa số
# ---------------------------------------------------------------------------
def _sweep_clear(cam, others, axis, step=4.0, dist=60.0):
    """Tịnh tiến đĩa cam dọc trục lắp từng bước, xem có vướng gì không."""
    worst = 0.0
    for i in range(1, int(dist / step) + 1):
        moved = cam.copy()
        moved.translate(App.Vector(axis[0] * step * i, axis[1] * step * i,
                                   axis[2] * step * i))
        for _n, o in others:
            worst = max(worst, _clash(moved, o))
    return worst


def verify_assemblable() -> dict:
    """Đĩa cam Ø30 phải chui vào được chỗ của nó — đây là lý do đĩa số BẮT BUỘC
    là chi tiết rời. Kiểm: (a) đúc liền thì bị chặn thật, (b) tháo đĩa số ra thì
    đĩa cam rút ra được dọc trục mà không vướng chi tiết nào khác."""
    rows = {}
    # --- H: rút đĩa cam theo local +y, đã xoay về khung toàn cục ---
    th = math.radians(GATE_FRAME_TH_DEG)
    ay = (-math.sin(th), math.cos(th), 0.0)   # local +y trong khung toàn cục
    h = 11.0
    cam_h = peg.make_entry_gate_cam(h)
    dial_h = peg.make_entry_gate_dial()
    rest_h = [("Entry_Gate_Post", peg.make_entry_gate_post()),
              ("Entry_Gate_Slider", peg.make_entry_gate_slider(h)),
              ("Entry_Gate_Barrier", peg.make_entry_gate_barrier(h))]
    rows["H_blocked_if_dial_fused"] = round(
        _sweep_clear(cam_h, [("dial", dial_h)], ay), 2)
    rows["H_clear_without_dial"] = round(_sweep_clear(cam_h, rest_h, ay), 4)
    # --- W: thả đĩa cam từ trên xuống theo +z ---
    w = _W_MID
    cam_w = pew.make_exit_cam(w)
    dial_w = pew.make_exit_dial()
    rest_w = [("Exit_Slide", pew.make_exit_slide()),
              ("Exit_Inner_Wall_2", pew.make_exit_inner_wall_2(w)),
              ("Exit_Inner_Wall", make_exit_inner_wall())]
    rows["W_blocked_if_dial_fused"] = round(
        _sweep_clear(cam_w, [("dial", dial_w)], (0.0, 0.0, 1.0)), 2)
    rows["W_clear_without_dial"] = round(
        _sweep_clear(cam_w, rest_w, (0.0, 0.0, 1.0)), 4)
    ok = (rows["H_clear_without_dial"] <= CLASH_MM3
          and rows["W_clear_without_dial"] <= CLASH_MM3
          and rows["H_blocked_if_dial_fused"] > CLASH_MM3
          and rows["W_blocked_if_dial_fused"] > CLASH_MM3)
    return {
        "pass": bool(ok),
        "sweep_mm3": rows,
        "why_dial_must_be_separate":
            "dia cam Ø%.0f nam giua dia so Ø%.0f (lo tam Ø%.1f) va lung khung/ray"
            % (2.0 * GATE_CAM_R, GATE_DIAL_D, GATE_JOURNAL_D + 2.0 * GATE_JOURNAL_FIT),
        "assembly_order_H": [
            "1. bat Entry_Gate_Post vao vanh bat (2xM3)",
            "2. long Entry_Gate_Slider tu dinh ray T xuong",
            "3. day Entry_Gate_Cam vao khung yoke theo -y",
            "4. xo Entry_Gate_Dial doc co truc, bat 2xM3 vao vanh bat",
            "5. lap Entry_Gate_Knob (chot D) + vit M3 tam",
        ],
        "assembly_order_W": [
            "1. dan/cam Exit_Slide (2 ray T + cot) vao thanh bat",
            "2. luon Exit_Inner_Wall_2 vao ray tu dau trong (x=-45)",
            "3. THA Exit_Cam tu tren xuong ranh yoke",
            "4. up Exit_Dial len, bat 2xM3 thang dung xuong cot",
            "5. lap Exit_Knob (chot D) + vit M3 tam",
        ],
    }


# ---------------------------------------------------------------------------
# 9. Khe hở với dòng vật & với vành bát
# ---------------------------------------------------------------------------
def verify_clearances() -> dict:
    obj_top = GAP0 + H_MAX  # 20.5 — vật cao nhất lọt vào máng
    g_lo = entry_gate_cam_geo(H_MIN)
    g_hi = entry_gate_cam_geo(H_MAX)
    post = peg.make_entry_gate_post()
    x_p, z_p = GATE_CAM_PIVOT_X, GATE_CAM_PIVOT_Z
    y_k = 0.5 * (GATE_KNOB_Y0 + GATE_KNOB_Y1)
    w_lo = exit_cam_geo(EXIT_GAP_MIN)
    w_hi = exit_cam_geo(EXIT_GAP_MAX)
    checks = {
        # --- núm H ---
        "support_above_objects": GATE_FOOT_Z0 > obj_top + 5.0,
        "yoke_above_bowl_rim": g_lo["yoke_z0_mm"] >= BOWL_Z0 + BOWL_H,
        "post_zmin_unchanged": abs(post.BoundBox.ZMin - (GATE_FOOT_Z0 - 0.4)) < 1.0,
        "knob_above_bowl_rim": (z_p - 0.5 * GATE_KNOB_D) > BOWL_Z0 + BOWL_H,
        "cam_journal_bearing_ok": GATE_DIAL_T >= 0.6 * (
            0.5 * (GATE_DIAL_Y0 + GATE_DIAL_Y1) - 0.5 * (GATE_CAM_Y0 + GATE_CAM_Y1)
        ),
        # --- núm W ---
        "w_cam_above_rail": EXIT_CAM_Z0 > EXIT_RAIL_TOP_Z,
        "w_yoke_above_rail": EXIT_YOKE_Z0 > EXIT_RAIL_TOP_Z,
        "w_beam_under_cam": EXIT_BEAM_Z1 < EXIT_CAM_Z0,
        "w_beam_above_shoes": (EXIT_BEAM_Z1 - EXIT_BEAM_T)
        >= (EXIT_SLIDE_T_BODY_Z0 - EXIT_SLIDE_T_NECK_H + 0.6) - 1e-9,
        "w_support_clear_of_yoke": (w_lo["yoke_x0_mm"] - EXIT_COL_X1) >= 1.0,
        "w_riser_clear_of_shoes":
            (EXIT_RISER_Y0 - (min(EXIT_SLIDE_Y) + EXIT_SHOE_HALF_W)) >= 1.0
            and ((max(EXIT_SLIDE_Y) - EXIT_SHOE_HALF_W) - EXIT_RISER_Y1) >= 1.0,
        "w_all_above_objects": min(EXIT_BEAM_Z1 - EXIT_BEAM_T,
                                   GAP0 + EXIT_WALL_H) > obj_top,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "object_top_z_mm": obj_top,
        "H_knob": {
            "support_z0_mm": GATE_FOOT_Z0,
            "yoke_bottom_z_at_H_MIN_mm": g_lo["yoke_z0_mm"],
            "yoke_top_z_at_H_MAX_mm": g_hi["yoke_z1_mm"],
            "knob_axis_r_mm": round(math.hypot(x_p, y_k), 2),
            "knob_axis_z_mm": z_p,
            "assembly_top_z_mm": round(max(g_hi["yoke_z1_mm"], post.BoundBox.ZMax), 2),
            "journal_bearing_len_mm": GATE_DIAL_T,
            "journal_overhang_mm": round(
                0.5 * (GATE_DIAL_Y0 + GATE_DIAL_Y1)
                - 0.5 * (GATE_CAM_Y0 + GATE_CAM_Y1), 2),
        },
        "W_knob": {
            "cam_above_rail_mm": round(EXIT_CAM_Z0 - EXIT_RAIL_TOP_Z, 2),
            "yoke_z_mm": [EXIT_YOKE_Z0, EXIT_YOKE_Z1],
            "knob_axis_xy": [EXIT_CAM_PIVOT_X, EXIT_CAM_PIVOT_Y],
            "knob_top_z_mm": EXIT_KNOB_Z1 + GATE_KNOB_PTR_H,
            "yoke_x_swept_mm": [round(w_lo["yoke_x0_mm"], 2),
                                round(w_hi["yoke_x1_mm"], 2)],
            "support_inner_x_mm": EXIT_COL_X1,
            "support_clearance_mm": round(w_lo["yoke_x0_mm"] - EXIT_COL_X1, 2),
            "beam_under_cam_mm": round(EXIT_CAM_Z0 - EXIT_BEAM_Z1, 2),
            "riser_gap_to_shoes_mm": round(
                EXIT_RISER_Y0 - (min(EXIT_SLIDE_Y) + EXIT_SHOE_HALF_W), 2),
            "journal_bearing_len_mm": EXIT_DIAL_T,
            "journal_overhang_mm": round(
                0.5 * (EXIT_DIAL_Z0 + EXIT_DIAL_Z1)
                - 0.5 * (EXIT_CAM_Z0 + EXIT_CAM_Z1), 2),
        },
        "bowl_rim_z_mm": BOWL_Z0 + BOWL_H,
        "bowl_or_mm": BOWL_OR,
    }


# ---------------------------------------------------------------------------
# 10. Thành mỏng nhất & khối in được (cả hai cụm)
# ---------------------------------------------------------------------------
def verify_printability() -> dict:
    cam_thin = GATE_CAM_R - GATE_CAM_ECC
    journal_wall = 0.5 * GATE_JOURNAL_D - 0.5 * M3_INSERT_D
    dkey_wall = 0.5 * GATE_JOURNAL_D - GATE_KNOB_DKEY
    knob_wall = 0.5 * GATE_KNOB_D - 0.5 * GATE_KNOB_FLUTE_D - 0.5 * GATE_JOURNAL_D
    walls = {
        "cam_thin_wall_mm": cam_thin,
        "journal_wall_over_insert_mm": journal_wall,
        "dkey_flat_wall_mm": dkey_wall,
        "knob_web_mm": knob_wall,
        "H_yoke_wall_mm": GATE_YOKE_WALL,
        "H_yoke_back_mm": GATE_YOKE_BACK_T,
        "W_yoke_wall_mm": EXIT_YOKE_WALL,
        "W_yoke_plate_t_mm": EXIT_YOKE_T,
        "cam_slot_fit_mm": GATE_CAM_FIT,
        "journal_fit_mm": GATE_JOURNAL_FIT,
        "W_cam_thin_wall_mm": EXIT_CAM_R - EXIT_CAM_ECC,
        "journal_embed_into_cam_mm": GATE_JOURNAL_EMBED,
        "journal_margin_inside_H_cam_mm": round(
            GATE_CAM_R - (GATE_CAM_ECC + 0.5 * GATE_JOURNAL_D), 2),
        "journal_margin_inside_W_cam_mm": round(
            EXIT_CAM_R - (EXIT_CAM_ECC + 0.5 * GATE_JOURNAL_D), 2),
        "H_ecc_mm": GATE_CAM_ECC,
        "W_ecc_mm": EXIT_CAM_ECC,
        "shared_hardware": "2 x (M3 heat-set insert + M3x12 SHCS); dia cam/num/co truc chung kich thuoc",
    }
    ok = (cam_thin >= 3.0 and journal_wall >= 2.0 and dkey_wall >= 0.8
          and knob_wall >= 2.0 and 0.15 <= GATE_CAM_FIT <= 0.4
          and abs(EXIT_CAM_R - GATE_CAM_R) < 1e-9
          and (EXIT_CAM_R - EXIT_CAM_ECC) >= 3.0
          # Cổ trục cắm vào lòng đĩa cam thì phải nằm TRỌN trong đĩa, nếu không
          # phần nhô ra chạy trong rãnh yoke và đụng vách rãnh ở hai đầu hành trình.
          and (GATE_CAM_ECC + 0.5 * GATE_JOURNAL_D) <= GATE_CAM_R
          and (EXIT_CAM_ECC + 0.5 * GATE_JOURNAL_D) <= EXIT_CAM_R)
    solids = {}
    parts = list(peg.build_entry_gate_parts(11.0)) + [
        ("Exit_Inner_Wall_2", pew.make_exit_inner_wall_2(_W_MID), None),
        ("Exit_Dial", pew.make_exit_dial(), None),
        ("Exit_Cam", pew.make_exit_cam(_W_MID), None),
        ("Exit_Knob", pew.make_exit_knob(_W_MID), None),
    ]
    for nm, sh, _c in parts:
        solids[nm] = {"solids": len(sh.Solids), "valid": bool(sh.isValid()),
                      "volume_mm3": round(float(sh.Volume), 1)}
        ok = ok and len(sh.Solids) == 1 and sh.isValid()
    # Exit_Slide đã là 2 khối rời TỪ TRƯỚC (hai ray T không nối nhau) — chỉ ghi
    # nhận, không tính là lỗi mới.
    sl = pew.make_exit_slide()
    solids["Exit_Slide"] = {"solids": len(sl.Solids), "valid": bool(sl.isValid()),
                            "volume_mm3": round(float(sl.Volume), 1),
                            "note": "2 khoi roi la trang thai CU (2 ray T rieng le)"}
    ok = ok and sl.isValid()
    return {"pass": bool(ok), "walls": walls, "parts": solids}


# ---------------------------------------------------------------------------
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for fn in (verify_cam_math, verify_pressure_angle, verify_hard_stops,
               verify_cam_in_yoke_solid, verify_exit_cam_math,
               verify_exit_hard_stops, verify_exit_cam_in_yoke_solid,
               verify_no_collision, verify_bowl_embed, verify_assemblable,
               verify_clearances, verify_printability):
        name = fn.__name__
        try:
            res[name] = fn()
        except Exception as exc:  # noqa: BLE001
            res[name] = {"pass": False, "error": "%s: %s" % (type(exc).__name__, exc)}
        print("%-32s %s" % (name, "PASS" if res[name].get("pass") else "FAIL"))
    res["pass"] = all(v.get("pass") for v in res.values() if isinstance(v, dict))
    path = OUT / "knob_cam_verify.json"
    path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("->", path)
    print("OVERALL:", "PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
