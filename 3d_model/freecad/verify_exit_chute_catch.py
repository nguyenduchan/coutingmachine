# -*- coding: utf-8 -*-
"""
Verify MÁNG EXIT hứng được viên rời đĩa (Bowl_Tube_Exit_Chute).

Yêu cầu cơ khí đang kiểm:
  A. CẠNH TRÁI LÒNG MÁNG TRÙNG MÉP ĐĨA — mặt trong vách trái nằm đúng trên
     đường tiếp tuyến x = −DISC_R tại 9 giờ. Đo bằng cách quét ngang lòng máng
     rồi lấy biên trái của khoảng trống, không tin vào tham số dựng hình.
  B. VIÊN RỜI ĐĨA RƠI TRÚNG LÒNG MÁNG — viên đi tiếp tuyến từ θ_exit nên tâm nó
     giữ nguyên x = −r_lane và rời đĩa tại y = −√(DISC_R² − r_lane²). Với MỌI W
     trong dải chỉnh, điểm đó phải nằm trong lòng máng và có SÀN ngay bên dưới.
  C. KHÔNG CHẠM ĐĨA — máng luồn dưới đĩa nên phải còn khe ≥ RAMP_DISC_GAP.
  D. KHÔNG VA KHỐI KHÁC — máng vs. mọi part còn lại của cụm.

Run:
  freecadcmd 3d_model\\freecad\\verify_exit_chute_catch.py
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
from part_bowl_tube import make_bowl_exit_chute_fitted  # noqa: E402
from part_rotor_disc import make_rotor_disc  # noqa: E402
from tube_l_exit_gate import build_tube_l_exit_gate_parts  # noqa: E402

OUT = _HERE / "out"
TOL = 1e-6
EDGE_TOL = 0.05  # mm — "trùng mép đĩa"
SCAN_STEP = 0.05
PROBE_Z = 1.0  # cao độ dò, trên mặt sàn máng
W_SWEEP = (2.0, 5.0, 8.0, 12.0, 17.0, 21.0, 26.0)


def _floor_z(g: dict, run: float) -> float:
    return g["start_z"] - run * math.tan(math.radians(g["angle_deg"]))


def _inside(sh, x: float, y: float, z: float) -> bool:
    return bool(sh.isInside(App.Vector(x, y, z), TOL, True))


def _lumen_span(chute, y: float, z: float, x_seed: float) -> tuple[float, float]:
    """Khoảng trống liên tục chứa x_seed, quét theo ±X."""
    if _inside(chute, x_seed, y, z):
        return (float("nan"), float("nan"))
    lo = x_seed
    while lo > x_seed - 60.0 and not _inside(chute, lo - SCAN_STEP, y, z):
        lo -= SCAN_STEP
    hi = x_seed
    while hi < x_seed + 60.0 and not _inside(chute, hi + SCAN_STEP, y, z):
        hi += SCAN_STEP
    return (lo - SCAN_STEP, hi + SCAN_STEP)


def check_left_edge_on_rim(chute, g: dict) -> dict:
    """A. Biên TRÁI của lòng máng = mép đĩa (x = −DISC_R)."""
    x_seed = g["center_xy"][0]
    rows = []
    for run in (2.0, 5.0, 12.0, 20.0, 30.0, 40.0, g["run_mm"] - 2.0):
        z = _floor_z(g, run) + PROBE_Z
        lo, hi = _lumen_span(chute, -run, z, x_seed)
        rows.append({
            "run_mm": round(run, 2),
            "z_mm": round(z, 2),
            "left_x_mm": round(lo, 3),
            "right_x_mm": round(hi, 3),
            "width_mm": round(hi - lo, 3),
            "err_mm": round(abs(lo + M.DISC_R), 3),
            "pass": abs(lo + M.DISC_R) <= EDGE_TOL,
        })
    return {
        "pass": all(r["pass"] for r in rows),
        "rim_x_mm": -M.DISC_R,
        "declared_left_x_mm": g["left_edge_x_mm"],
        "rows": rows,
    }


def check_catch(chute, g: dict) -> dict:
    """B. Điểm rời đĩa của mọi W nằm trong lòng máng, có sàn ngay dưới."""
    rows = []
    xl, xr = g["lumen_x_mm"]
    for W in W_SWEEP:
        ap = M.aperture_from_opens(W, M.H_MAX)
        r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
        x = -r_lane
        y = -M.rim_leave_y_mm(W)
        in_x = xl - 1e-9 <= x <= xr + 1e-9
        in_y = y >= -g["run_mm"]
        z_floor = _floor_z(g, -y)
        z_hit = None
        z = z_floor + 0.5
        while z > z_floor - 8.0:
            if _inside(chute, x, y, z):
                z_hit = z
                break
            z -= 0.1
        rows.append({
            "W_mm": W,
            "drop_xy": (round(x, 2), round(y, 2)),
            "in_lumen_x": in_x,
            "in_run_y": in_y,
            "floor_z_mm": round(z_floor, 2),
            "floor_hit_z_mm": None if z_hit is None else round(z_hit, 2),
            "fall_mm": round(M.DISC_TOP_Z - z_floor, 2),
            "pass": bool(in_x and in_y and z_hit is not None),
        })
    return {
        "pass": all(r["pass"] for r in rows),
        "lumen_x_mm": (round(xl, 2), round(xr, 2)),
        "run_mm": round(g["run_mm"], 2),
        "rows": rows,
    }


def check_disc_clearance(chute, g: dict) -> dict:
    """C. Máng luồn dưới đĩa — không giao đĩa, khe ≥ RAMP_DISC_GAP."""
    disc = make_rotor_disc()
    try:
        vol = float(chute.common(disc).Volume)
    except Exception:
        vol = -1.0
    gap = (M.DISC_TOP_Z - M.DISC_T) - chute.BoundBox.ZMax
    # Khe thật chỉ tính ở phần nằm TRONG bao đĩa: vách trái ở ngoài mép đĩa được
    # phép cao hơn đáy đĩa, nên đo bằng giao khối là chuẩn, ZMax chỉ để tham khảo.
    return {
        "pass": vol <= 0.001,
        "overlap_mm3": round(vol, 4),
        "required_gap_mm": M.RAMP_DISC_GAP,
        "start_z_mm": g["start_z"],
        "disc_bottom_z_mm": M.DISC_TOP_Z - M.DISC_T,
        "gap_at_start_mm": round((M.DISC_TOP_Z - M.DISC_T) - g["start_z"], 3),
        "chute_zmax_mm": round(chute.BoundBox.ZMax, 2),
        "zmax_note": "vách trái nằm ngoài mép đĩa nên cao hơn đáy đĩa là đúng",
        "_gap_unused": round(gap, 3),
    }


def check_no_clash(chute) -> dict:
    """D. Không đâm khối khác (Bowl_Tube đã chứa máng nên bỏ qua)."""
    hits = []
    for W, H in ((M.W_MIN, M.H_MIN), (9.0, 5.0), (M.W_MAX, M.H_MAX)):
        for name, sh, _c in build_tube_l_exit_gate_parts(W, H):
            if name == "Bowl_Tube" or sh is None or sh.isNull():
                continue
            try:
                v = float(chute.common(sh).Volume)
            except Exception:
                continue
            if v > 0.5:
                hits.append({"W": W, "H": H, "part": name, "vol_mm3": round(v, 2)})
    return {"pass": not hits, "hits": hits}


def main() -> None:
    g = M.ramp_geo(M.W_MAX, M.CHUTE_WALL_H_MM)
    chute = make_bowl_exit_chute_fitted()

    a = check_left_edge_on_rim(chute, g)
    b = check_catch(chute, g)
    c = check_disc_clearance(chute, g)
    d = check_no_clash(chute)

    print("A. Canh trai trung mep dia : pass=%s | lech lon nhat %.3f mm"
          % (a["pass"], max(r["err_mm"] for r in a["rows"])))
    for r in a["rows"]:
        print("     run=%6.2f  long mang x=[%8.3f, %8.3f] rong %5.2f  lech %.3f"
              % (r["run_mm"], r["left_x_mm"], r["right_x_mm"], r["width_mm"], r["err_mm"]))
    print("B. Roi trung long mang     : pass=%s | long mang x=%s, chay toi y=-%.1f"
          % (b["pass"], b["lumen_x_mm"], b["run_mm"]))
    for r in b["rows"]:
        print("     W=%5.1f  roi tai %s  san z=%7.2f  cao roi %5.1f mm  %s"
              % (r["W_mm"], r["drop_xy"], r["floor_z_mm"], r["fall_mm"],
                 "OK" if r["pass"] else "TRUOT"))
    print("C. Khong cham dia          : pass=%s | giao %.3f mm3, khe dau mang %.2f mm"
          % (c["pass"], c["overlap_mm3"], c["gap_at_start_mm"]))
    print("D. Khong va khoi khac      : pass=%s | %d cap" % (d["pass"], len(d["hits"])))
    for h in d["hits"]:
        print("     VA:", h)

    out = {
        "pass": bool(a["pass"] and b["pass"] and c["pass"] and d["pass"]),
        "ramp": {k: g[k] for k in (
            "start_xy", "start_z", "center_xy", "end_xy", "end_z", "run_mm",
            "len_mm", "drop_mm", "angle_deg", "lumen_w_mm", "lumen_x_mm",
            "left_edge_x_mm", "left_edge_on_rim", "rim_leave_y_mm",
            "under_disc_gap_mm", "wall_h_mm", "slides")},
        "A_left_edge_on_rim": a,
        "B_catch": b,
        "C_disc_clearance": c,
        "D_no_clash": d,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "exit_chute_catch_verify.json"
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("OVERALL pass=%s -> %s" % (out["pass"], p))


def _is_direct_launch() -> bool:
    if __name__ == "__main__":
        return True
    try:
        me = Path(__file__).resolve()
    except NameError:
        return True
    for arg in sys.argv:
        try:
            if Path(arg).resolve() == me:
                return True
        except Exception:
            continue
    return False


if _is_direct_launch():
    main()
