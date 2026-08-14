# -*- coding: utf-8 -*-
"""
Kiểm hành trình THANH TỊNH TIẾN chỉnh W và con trượt chỉnh H, đối chiếu với
BỀ RỘNG / CHIỀU CAO LÒNG MÁNG ĐO ĐƯỢC TRÊN KHỐI CAD.

Động học (mech_common):
    s = width_clamp_s(W) = CHANNEL_R_OUTER - W      → thanh chạy 24 mm cho W 2→26
    z = height_scraper_z(H) = GAP0 + H              → con trượt chạy 24 mm cho H 2→26
Cả hai đều 1:1 (1 mm thanh = 1 mm khẩu độ).

Nhưng đó mới là TOÁN. Script này đo lòng máng thật bằng cách chấm điểm trong
khối CAD (verify_chute_width), rồi so với con số ra lệnh. Phép đo trước đã cho
thấy hai thứ này lệch nhau ở vài chỗ, nên không thể tin toán mà không đo.

Quy ước chiều cao: khe đứng vật lý từ mặt đĩa lên đáy lưỡi gạt = GAP0 + H
(GAP0 là khe đáy hở, không đỡ viên) — nên chiều cao đo được phải ≈ H + GAP0.

Run:
  freecadcmd 3d_model\\freecad\\verify_adjust_travel.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import mech_common as M  # noqa: E402
from verify_chute_width import (  # noqa: E402
    PILL_Z, _clear_span, _solids, clear_height,
)

OUT = _HERE / "out"
W_STEPS = (2.0, 6.0, 10.0, 14.0, 18.0, 22.0, 26.0)
H_STEPS = (2.0, 6.0, 10.0, 14.0, 18.0, 22.0, 26.0)
W_NOM, H_NOM = 9.0, 5.0
TOL_W = 0.6  # mm — sai lệch bề rộng chấp nhận được
TOL_H = 0.6


def _lane_probe(W: float, H: float, th_deg: float):
    """Điểm giữa lane tại góc th, và pháp tuyến xuyên tâm."""
    ap = M.aperture_from_opens(W, H)
    r = 0.5 * (ap["r_inner"] + ap["r_outer"])
    thr = math.radians(th_deg)
    c = App.Vector(r * math.cos(thr), r * math.sin(thr), M.DISC_TOP_Z + PILL_Z)
    n = App.Vector(math.cos(thr), math.sin(thr), 0.0)
    floor = App.Vector(c.x, c.y, M.DISC_TOP_Z + 0.05)
    return c, n, floor


# Bề rộng: đo giữa lane, tránh khuỷu nối (θ_exit=180) và họng vào (θ_mouth=90).
PROBE_TH = (110.0, 130.0, 150.0)
# Chiều cao: lưỡi gạt CHỈ nằm ở cửa vào (TH_ADJ_DEG = THETA_MOUTH_DEG = 90°),
# không chạy quanh lane — đo ở giữa lane sẽ không gặp gì và ra "hở 60 mm".
# Lưỡi bắt đầu ĐÚNG tại TH_ADJ_DEG và kéo theo chiều +θ (chiều viên chạy) chừng
# SCRAPER_BLADE_ALONG ≈ 3.6°. Đo ở θ-1 là đo TRƯỚC lưỡi → ra H+5 mm, không phải
# lỗi cơ cấu.
PROBE_TH_H = (M.TH_ADJ_DEG, M.TH_ADJ_DEG + 1.0, M.TH_ADJ_DEG + 2.0)


def sweep_width() -> dict:
    rows = []
    for W in W_STEPS:
        s = M.width_clamp_s(W)
        solids = _solids(W, H_NOM)
        meas = []
        for th in PROBE_TH:
            c, n, _f = _lane_probe(W, H_NOM, th)
            w, lo, hi, by_lo, by_hi = _clear_span(solids, c, n)
            meas.append({"th": th, "w": round(w, 2), "by_lo": by_lo, "by_hi": by_hi})
        widths = [m["w"] for m in meas]
        worst = max(abs(x - W) for x in widths)
        rows.append({
            "W_cmd": W, "bar_s_mm": round(s, 3),
            "bar_travel_from_Wmin_mm": round(M.width_clamp_s(M.W_MIN) - s, 3),
            "w_meas_mm": widths,
            "max_err_mm": round(worst, 2),
            "pass": worst <= TOL_W,
            "detail": meas,
        })
    span = M.width_clamp_s(M.W_MIN) - M.width_clamp_s(M.W_MAX)
    return {
        "pass": all(r["pass"] for r in rows) and abs(span - M.W_TRAVEL) < 1e-9,
        "bar_span_mm": round(span, 3),
        "bar_span_expected_mm": M.W_TRAVEL,
        "ratio_1to1": abs(span - M.W_TRAVEL) < 1e-9,
        "tol_mm": TOL_W,
        "rows": rows,
    }


def sweep_height() -> dict:
    rows = []
    for H in H_STEPS:
        z = M.height_scraper_z(H)
        solids = _solids(W_NOM, H)
        meas = []
        for th in PROBE_TH_H:
            _c, _n, floor = _lane_probe(W_NOM, H, th)
            h, by = clear_height(solids, floor)
            # cộng lại 0.05 mm đã nhấc khỏi sàn khi đặt điểm đo
            meas.append({"th": th, "h": round(h + 0.05, 2), "by": by})
        heights = [m["h"] for m in meas]
        want = M.GAP0 + H  # khe đứng vật lý từ mặt đĩa lên đáy lưỡi
        worst = max(abs(x - want) for x in heights)
        rows.append({
            "H_cmd": H, "slider_z_mm": round(z, 3),
            "slider_travel_from_Hmin_mm": round(z - M.height_scraper_z(M.H_MIN), 3),
            "h_expected_mm": round(want, 2),
            "h_meas_mm": heights,
            "max_err_mm": round(worst, 2),
            "pass": worst <= TOL_H,
            "detail": meas,
        })
    span = M.height_scraper_z(M.H_MAX) - M.height_scraper_z(M.H_MIN)
    return {
        "pass": all(r["pass"] for r in rows) and abs(span - M.H_TRAVEL) < 1e-9,
        "slider_span_mm": round(span, 3),
        "slider_span_expected_mm": M.H_TRAVEL,
        "ratio_1to1": abs(span - M.H_TRAVEL) < 1e-9,
        "tol_mm": TOL_H,
        "rows": rows,
    }


def check_independence() -> dict:
    """Chỉnh W không được làm đổi H và ngược lại."""
    rows = []
    for W in (2.0, 26.0):
        for H in (2.0, 26.0):
            p = M.adjust_pose_math(W, H)
            rows.append({
                "W": W, "H": H, "s": p["s_mm"], "z": p["z_scraper_mm"],
                "W_from_s_ok": p["check_W_from_s"],
                "H_from_z_ok": p["check_H_from_z"],
                "s_eq_rinner": p["check_s_eq_rin"],
            })
    w_indep = abs(M.aperture_from_opens(2.0, 2.0)["width_mm"]
                  - M.aperture_from_opens(2.0, 26.0)["width_mm"]) < 1e-9
    h_indep = abs(M.aperture_from_opens(2.0, 2.0)["height_mm"]
                  - M.aperture_from_opens(26.0, 2.0)["height_mm"]) < 1e-9
    return {
        "pass": all(r["W_from_s_ok"] and r["H_from_z_ok"] and r["s_eq_rinner"]
                    for r in rows) and w_indep and h_indep,
        "W_unaffected_by_H": w_indep,
        "H_unaffected_by_W": h_indep,
        "corners": rows,
    }


def main() -> None:
    ind = check_independence()
    sw = sweep_width()
    sh = sweep_height()
    result = {"pass": all(x["pass"] for x in (ind, sw, sh)),
              "independence": ind, "width_sweep": sw, "height_sweep": sh}
    out_path = OUT / "adjust_travel_verify.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print("THANH TINH TIEN (W): chay %.1f mm cho W %.0f->%.0f | 1:1=%s"
          % (sw["bar_span_mm"], M.W_MIN, M.W_MAX, sw["ratio_1to1"]))
    print("  %-7s %-9s %-11s %-22s %-8s" % ("W ra", "vi tri s", "da chay", "rong do duoc", "sai"))
    for r in sw["rows"]:
        print("  %-7.1f %-9.2f %-11.2f %-22s %-8.2f %s"
              % (r["W_cmd"], r["bar_s_mm"], r["bar_travel_from_Wmin_mm"],
                 r["w_meas_mm"], r["max_err_mm"], "OK" if r["pass"] else "LECH"))
    print()
    print("CON TRUOT (H): chay %.1f mm cho H %.0f->%.0f | 1:1=%s"
          % (sh["slider_span_mm"], M.H_MIN, M.H_MAX, sh["ratio_1to1"]))
    print("  %-7s %-9s %-11s %-10s %-22s %-8s"
          % ("H ra", "z luoi", "da chay", "cho doi", "cao do duoc", "sai"))
    for r in sh["rows"]:
        print("  %-7.1f %-9.2f %-11.2f %-10.2f %-22s %-8.2f %s"
              % (r["H_cmd"], r["slider_z_mm"], r["slider_travel_from_Hmin_mm"],
                 r["h_expected_mm"], r["h_meas_mm"], r["max_err_mm"],
                 "OK" if r["pass"] else "LECH"))
    print()
    print("Doc lap: W khong doi theo H=%s | H khong doi theo W=%s"
          % (ind["W_unaffected_by_H"], ind["H_unaffected_by_W"]))
    print("OVERALL pass=%s -> %s" % (result["pass"], out_path))


if __name__ == "__main__" or True:
    main()
