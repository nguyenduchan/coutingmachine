# -*- coding: utf-8 -*-
"""
Verify CỬA CHỈNH CHIỀU CAO ở đầu máng vào (Entry_Gate_Post/Slider/Barrier).

  A. KÍCH THƯỚC BARRIER — đo TRÊN KHỐI, không tin tham số dựng hình:
       nhìn từ trên rộng 30 mm, cạnh ngoài nằm trên cung mép đĩa,
       tấm ngang 20 mm dọc dòng chảy, tấm đứng cao 10 mm.
  B. KHE DƯỚI TRẦN = H — dò từ mặt đĩa lên tới khối đầu tiên tại giữa cửa,
       quét cả dải H 2–26 (1 mm trượt = 1 mm khe).
  C. CHẶN ĐƯỢC VẬT CAO — điểm ngay trên trần phải NẰM TRONG barrier (vật cao
       hơn H đâm vào trần/tấm đứng chứ không lọt).
  D. KHÔNG VA — barrier/slider/post với mọi khối còn lại, quét W×H góc.
  E. TRƯỢT ĐƯỢC — vòng ôm luôn nằm trên ray T ở cả H_MIN..H_MAX, và khớp
       trượt + bu-lông kẹp nằm NGOÀI vành bát (với tay từ trên).

Run:
  freecadcmd 3d_model\\freecad\\verify_entry_gate.py
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
from part_bowl_tube import make_bowl_tube_complete  # noqa: E402
from part_chute_slide import make_chute_slide  # noqa: E402
from part_entry_gate import (  # noqa: E402
    gate_rail_z_span, make_entry_gate_barrier, make_entry_gate_post,
    make_entry_gate_slider,
)
from part_guide_system import make_guide_system  # noqa: E402
from part_inner_lane_rail import make_inner_lane_rail  # noqa: E402
from part_rotor_disc import make_rotor_disc  # noqa: E402

OUT = _HERE / "out"
TOL = 1e-6
STEP = 0.05
DIM_TOL = 0.15  # mm — sai số cho phép khi đo trên khối (cung xấp xỉ đa giác)
H_SWEEP = (2.0, 5.0, 9.0, 14.0, 20.0, 26.0)


def _xy(r: float, th_deg: float) -> tuple[float, float]:
    a = math.radians(th_deg)
    return r * math.cos(a), r * math.sin(a)


def _inside(sh, x: float, y: float, z: float) -> bool:
    return bool(sh.isInside(App.Vector(x, y, z), TOL, True))


def _scan_radial(sh, th_deg: float, z: float) -> tuple[float, float]:
    """Biên trong/ngoài của khối theo phương xuyên tâm tại góc th, cao độ z."""
    lo = hi = None
    r = M.DISC_R + 6.0
    while r > 40.0:
        x, y = _xy(r, th_deg)
        if _inside(sh, x, y, z):
            if hi is None:
                hi = r
            lo = r
        r -= STEP
    return (lo if lo is not None else float("nan"),
            hi if hi is not None else float("nan"))


def _scan_theta(sh, r: float, z: float, th_c: float) -> tuple[float, float]:
    """Biên theo GÓC (đổi ra mm cung tại bán kính r)."""
    lo = hi = None
    th = th_c - 20.0
    dth = math.degrees(STEP / r)
    while th <= th_c + 20.0:
        x, y = _xy(r, th)
        if _inside(sh, x, y, z):
            if lo is None:
                lo = th
            hi = th
        th += dth
    if lo is None:
        return float("nan"), float("nan")
    return lo, hi


def check_barrier_dims() -> dict:
    g = M.entry_gate_geo(9.0)
    bar = make_entry_gate_barrier(9.0)
    th_c = 0.5 * (g["th_roof0_deg"] + g["th_roof1_deg"])
    z_roof = 0.5 * (g["z_roof0_mm"] + g["z_roof1_mm"])
    r_lo, r_hi = _scan_radial(bar, th_c, z_roof)
    width = r_hi - r_lo
    r_mid = g["r_mid_mm"]
    th0, th1 = _scan_theta(bar, r_mid, z_roof, th_c)
    along = math.radians(th1 - th0) * r_mid
    # tấm đứng: quét góc ở cao độ giữa tấm đứng
    z_wall = 0.5 * (g["z_roof1_mm"] + g["z_wall1_mm"])
    w0, w1 = _scan_theta(bar, r_mid, z_wall, th_c)
    wall_along = math.radians(w1 - w0) * r_mid
    # chiều cao tấm đứng: dò lên từ mặt trần
    z = g["z_roof1_mm"] + STEP
    x, y = _xy(r_mid, g["th_roof0_deg"] + 0.5 * g["wall_deg"])
    top = g["z_roof1_mm"]
    while z < g["z_wall1_mm"] + 6.0:
        if _inside(bar, x, y, z):
            top = z
        z += STEP
    wall_h = top - g["z_roof1_mm"]
    rows = {
        "top_view_w_mm": round(width, 3),
        "outer_edge_r_mm": round(r_hi, 3),
        "inner_edge_r_mm": round(r_lo, 3),
        "roof_along_mm": round(along, 3),
        "wall_along_mm": round(wall_along, 3),
        "wall_h_mm": round(wall_h, 3),
        "rim_r_mm": M.DISC_R,
        "gap_to_rim_mm": round(M.DISC_R - r_hi, 3),
    }
    # Cạnh trong là đường THẲNG (tấm 20 mm không côn), nên bề rộng đo theo
    # phương xuyên tâm ở GIỮA cửa lớn hơn 30 mm chừng 1 mm — dung sai 1.2 mm.
    ok = (
        abs(width - M.GATE_W_MM) <= 1.2
        and abs(r_hi - M.GATE_R_OUT) <= DIM_TOL
        and abs(along - M.GATE_ROOF_ALONG_MM) <= 1.0
        and abs(wall_h - M.GATE_WALL_H_MM) <= DIM_TOL
        and 0.0 <= (M.DISC_R - r_hi) <= M.CHUTE_DISC_GUIDE_CLEAR + DIM_TOL
    )
    rows["pass"] = bool(ok)
    return rows


def check_clear_height() -> dict:
    """Khe dưới trần đo trên khối = H đúng suốt dải chỉnh."""
    rows = []
    for H in H_SWEEP:
        g = M.entry_gate_geo(H)
        bar = make_entry_gate_barrier(H)
        th_c = 0.5 * (g["th_roof0_deg"] + g["th_roof1_deg"])
        x, y = _xy(g["r_mid_mm"], th_c)
        z = M.DISC_TOP_Z
        while z < g["z_roof0_mm"] + 8.0:
            if _inside(bar, x, y, z):
                break
            z += STEP
        clear = z - M.DISC_TOP_Z
        rows.append({
            "H_mm": H,
            "clear_measured_mm": round(clear, 3),
            "expect_mm": round(g["z_roof0_mm"] - M.DISC_TOP_Z, 3),
            "pass": abs(clear - (g["z_roof0_mm"] - M.DISC_TOP_Z)) <= DIM_TOL,
        })
    spread = [r["clear_measured_mm"] for r in rows]
    return {
        "pass": all(r["pass"] for r in rows),
        "travel_mm": round(max(spread) - min(spread), 3),
        "travel_expect_mm": M.H_TRAVEL,
        "rows": rows,
    }


def check_blocks_tall() -> dict:
    """Vật cao hơn H phải đâm vào trần (điểm ngay trên khe = trong khối)."""
    rows = []
    for H in H_SWEEP:
        g = M.entry_gate_geo(H)
        bar = make_entry_gate_barrier(H)
        th_c = 0.5 * (g["th_roof0_deg"] + g["th_roof1_deg"])
        hit = 0
        n = 0
        for u in (0.1, 0.3, 0.5, 0.7, 0.9):
            r = M.GATE_R_IN + u * (M.GATE_R_OUT - M.GATE_R_IN)
            x, y = _xy(r, th_c)
            n += 1
            if _inside(bar, x, y, g["z_roof0_mm"] + 0.5 * M.GATE_ROOF_T):
                hit += 1
        rows.append({"H_mm": H, "roof_covers": hit, "of": n, "pass": hit == n})
    return {"pass": all(r["pass"] for r in rows), "rows": rows}


def check_no_clash() -> dict:
    disc = make_rotor_disc()
    bowl = make_bowl_tube_complete()
    guide = make_guide_system()
    slide = make_chute_slide()
    post = make_entry_gate_post()
    hits = []

    def _ov(a, b) -> float:
        try:
            return float(a.common(b).Volume)
        except Exception:
            return -1.0

    for name, other in (("Bowl_Tube", bowl), ("Rotor_Disc", disc),
                        ("Guide_System", guide), ("Chute_Slide", slide)):
        v = _ov(post, other)
        if v > 0.05:
            hits.append({"pair": f"Entry_Gate_Post×{name}", "vol_mm3": round(v, 3)})
    for W in (M.W_MIN, 9.0, M.W_MAX):
        rail = make_inner_lane_rail(W)
        for H in (M.H_MIN, 9.0, M.H_MAX):
            bar = make_entry_gate_barrier(H)
            sld = make_entry_gate_slider(H)
            for pname, part in (("Entry_Gate_Barrier", bar), ("Entry_Gate_Slider", sld)):
                for name, other in (("Rotor_Disc", disc), ("Inner_Lane_Rail", rail),
                                    ("Bowl_Tube", bowl), ("Guide_System", guide),
                                    ("Chute_Slide", slide), ("Entry_Gate_Post", post)):
                    v = _ov(part, other)
                    if v > 0.05:
                        hits.append({"pair": f"{pname}×{name}", "W": W, "H": H,
                                     "vol_mm3": round(v, 3)})
            v = _ov(bar, sld)
            if v > 0.05:
                hits.append({"pair": "Entry_Gate_Barrier×Entry_Gate_Slider",
                             "W": W, "H": H, "vol_mm3": round(v, 3)})
    return {"pass": not hits, "n_hit": len(hits), "hits": hits[:12]}


def check_slide_travel() -> dict:
    z0, z1 = gate_rail_z_span()
    lo = M.entry_gate_geo(M.H_MIN)
    hi = M.entry_gate_geo(M.H_MAX)
    on_rail = (lo["z_collar0_mm"] >= z0 - 1e-9) and (hi["z_collar1_mm"] <= z1 + 1e-9)
    outside_bowl = M.GATE_RAIL_R0 >= M.BOWL_OR
    above_bowl = lo["z_collar0_mm"] > M.BOWL_Z0 + M.BOWL_H
    stroke = hi["z_arm0_mm"] - lo["z_arm0_mm"]
    return {
        "pass": bool(on_rail and outside_bowl and above_bowl
                     and abs(stroke - M.H_TRAVEL) < 1e-9),
        "rail_z_mm": (round(z0, 2), round(z1, 2)),
        "collar_z_at_Hmin": (round(lo["z_collar0_mm"], 2), round(lo["z_collar1_mm"], 2)),
        "collar_z_at_Hmax": (round(hi["z_collar0_mm"], 2), round(hi["z_collar1_mm"], 2)),
        "stroke_mm": round(stroke, 3),
        "travel_mm": M.H_TRAVEL,
        "collar_outside_bowl_rim": outside_bowl,
        "collar_above_bowl_top": above_bowl,
        "gate_theta_deg": round(M.GATE_TH_DEG, 2),
        "rail_tip_min_deg": round(M._RAIL_TIP_TH_DEG, 2),
        "gate_before_rail_tip": M.GATE_TH_DEG <= M._RAIL_TIP_TH_DEG - 1.0,
    }


def main() -> None:
    a = check_barrier_dims()
    b = check_clear_height()
    c = check_blocks_tall()
    d = check_no_clash()
    e = check_slide_travel()

    print("A. Kich thuoc barrier : pass=%s | rong tren %.2f mm, canh ngoai r=%.2f "
          "(mep dia %.0f), tran doc dong %.2f mm, tam dung cao %.2f mm"
          % (a["pass"], a["top_view_w_mm"], a["outer_edge_r_mm"], a["rim_r_mm"],
             a["roof_along_mm"], a["wall_h_mm"]))
    print("B. Khe duoi tran = H  : pass=%s | hanh trinh do duoc %.2f/%.0f mm"
          % (b["pass"], b["travel_mm"], b["travel_expect_mm"]))
    for r in b["rows"]:
        print("     H=%5.1f -> khe %6.2f mm %s"
              % (r["H_mm"], r["clear_measured_mm"], "OK" if r["pass"] else "SAI"))
    print("C. Chan vat cao       : pass=%s" % c["pass"])
    print("D. Khong va cham      : pass=%s | %d cap" % (d["pass"], d["n_hit"]))
    for h in d["hits"]:
        print("     VA:", h)
    print("E. Truot duoc         : pass=%s | ray z=%s, hanh trinh %.1f mm, cua o %.2f "
          "(dau rail som nhat %.2f)"
          % (e["pass"], e["rail_z_mm"], e["stroke_mm"], e["gate_theta_deg"],
             e["rail_tip_min_deg"]))

    out = {
        "pass": bool(a["pass"] and b["pass"] and c["pass"] and d["pass"] and e["pass"]),
        "A_barrier_dims": a,
        "B_clear_height": b,
        "C_blocks_tall": c,
        "D_no_clash": d,
        "E_slide_travel": e,
        "geo_at_H9": M.entry_gate_geo(9.0),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "entry_gate_verify.json"
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
