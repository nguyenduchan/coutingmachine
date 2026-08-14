# -*- coding: utf-8 -*-
"""
Đo BỀ RỘNG LÒNG MÁNG dọc toàn bộ đường đi của viên, từ họng vào tới cuối dốc.

Cách đo: tại mỗi trạm trên đường tâm, quét một đoạn VUÔNG GÓC với hướng đi ở
đúng cao độ viên, chấm từng điểm xem có nằm trong khối nào không, rồi lấy
khoảng trống LIÊN TỤC chứa điểm tâm. Đó là bề rộng viên thực sự đi lọt — không
phải khoảng cách danh nghĩa giữa hai đường dựng hình.

3 đoạn:
  LANE  — cung tròn từ θ_mouth tới θ_exit, sàn = mặt đĩa
  CHUTE — máng phẳng tiếp tuyến, sàn = mặt đĩa (đáy hở)
  RAMP  — dốc 30° có đáy, sàn = mặt dốc

Run:
  freecadcmd 3d_model\\freecad\\verify_chute_width.py
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
from part_bowl_tube import make_bowl_tube  # noqa: E402
from part_guide_system import make_guide_system  # noqa: E402
from part_height_slider import make_height_scraper  # noqa: E402
from part_inner_lane_rail import make_inner_lane_rail  # noqa: E402
from part_rotor_disc import make_rotor_disc  # noqa: E402
from part_width_carriage import make_width_carriage  # noqa: E402

OUT = _HERE / "out"
SCAN_HALF = 45.0  # nửa đoạn quét vuông góc (mm)
SCAN_STEP = 0.2
PILL_Z = 2.0  # cao độ đo, trên sàn cục bộ
TOL = 1e-6


def _solids(W: float, H: float) -> list[tuple[str, object]]:
    out = []
    for name, fn in (
        # Rotor_Disc PHẢI có trong danh sách: ở đầu dốc, thành trong của lòng
        # máng chính là VÀNH ĐĨA (dốc bị cắt theo bao đĩa nên không có vách
        # riêng ở đó). Thiếu nó thì đo ra "hở 45 mm" trong khi thực tế viên
        # tựa vào mép đĩa.
        ("Rotor_Disc", lambda: make_rotor_disc()),
        ("Bowl_Tube", lambda: make_bowl_tube()),
        ("Inner_Lane_Rail", lambda: make_inner_lane_rail(W)),
        ("Exit_Track", lambda: M.make_exit_track(W, H)),
        ("Exit_Ramp", lambda: M.make_exit_ramp(W, H)),
        ("Guide_System", lambda: make_guide_system()),
        ("Width_Carriage", lambda: make_width_carriage(W)),
        ("Height_Scraper", lambda: make_height_scraper(W, H)),
    ):
        try:
            s = fn()
        except Exception as e:
            # KHÔNG nuốt lặng: thiếu một khối là phép đo sai theo hướng nguy
            # hiểm (báo "thoáng" ở chỗ thực ra có vật cản).
            print("  !! khong dung duoc %s: %s" % (name, e))
            continue
        if s is None or s.isNull():
            print("  !! %s rong" % name)
            continue
        out.append((name, s))
    return out


def _inside_any(solids, p: App.Vector) -> str | None:
    for name, s in solids:
        try:
            if s.isInside(p, TOL, True):
                return name
        except Exception:
            continue
    return None


def _clear_span(solids, c: App.Vector, n: App.Vector):
    """Khoảng trống liên tục chứa tâm c, quét theo ±n."""
    hit = _inside_any(solids, c)
    if hit:
        return 0.0, 0.0, 0.0, hit, hit
    lo = hi = 0.0
    by_hi = by_lo = "(ho)"
    t = SCAN_STEP
    while t <= SCAN_HALF:
        h = _inside_any(solids, c.add(App.Vector(n.x * t, n.y * t, n.z * t)))
        if h:
            by_hi = h
            break
        hi = t
        t += SCAN_STEP
    t = SCAN_STEP
    while t <= SCAN_HALF:
        h = _inside_any(solids, c.sub(App.Vector(n.x * t, n.y * t, n.z * t)))
        if h:
            by_lo = h
            break
        lo = -t
        t += SCAN_STEP
    return hi - lo, lo, hi, by_lo, by_hi


def clear_height(solids, floor_pt: App.Vector, up_max: float = 60.0) -> tuple[float, str]:
    """Khoảng hở ĐỨNG tính từ mặt sàn lên tới vật cản đầu tiên (lưỡi gạt/nóc)."""
    t = SCAN_STEP
    last = 0.0
    while t <= up_max:
        h = _inside_any(solids, App.Vector(floor_pt.x, floor_pt.y, floor_pt.z + t))
        if h:
            return last, h
        last = t
        t += SCAN_STEP
    return last, "(ho)"


def _stations(W: float, H: float) -> list[dict]:
    """Đường tâm: lane (cung) → máng phẳng → dốc."""
    ap = M.aperture_from_opens(W, H)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    pose = M.exit_tangent_pose(W, H)
    ux, uy = pose["chute_dir"]
    ax, ay = pose["anchor_xy"]
    g = M.ramp_geo(W, H)
    s_cross = g["s_cross_mm"]

    st = []
    # LANE: θ từ họng tới θ_exit
    for i in range(19):
        th = M.THETA_MOUTH_DEG + (M.THETA_EXIT_DEG - M.THETA_MOUTH_DEG) * i / 18.0
        thr = math.radians(th)
        st.append({
            "seg": "LANE", "at": round(th, 1),
            "c": App.Vector(r_lane * math.cos(thr), r_lane * math.sin(thr),
                            M.DISC_TOP_Z + PILL_Z),
            "n": App.Vector(math.cos(thr), math.sin(thr), 0.0),
        })
    # CHUTE: s = 0 .. s_cross (còn trên đĩa)
    n_ch = 10
    for i in range(n_ch + 1):
        s = s_cross * i / n_ch
        st.append({
            "seg": "CHUTE", "at": round(s, 1),
            "c": App.Vector(ax + s * ux, ay + s * uy, M.DISC_TOP_Z + PILL_Z),
            "n": App.Vector(-uy, ux, 0.0),
        })
    # RAMP: dọc mặt dốc
    a = math.radians(M.RAMP_ANGLE_DEG)
    x0, y0 = g["start_xy"]
    n_rp = 12
    for i in range(1, n_rp + 1):
        L = M.RAMP_LEN * i / n_rp
        run, drop = L * math.cos(a), L * math.sin(a)
        st.append({
            "seg": "RAMP", "at": round(L, 1),
            "c": App.Vector(x0 + run * ux, y0 + run * uy,
                            g["start_z"] + PILL_Z * math.cos(a) - drop),
            "n": App.Vector(-uy, ux, 0.0),
        })
    return st


def measure(W: float, H: float) -> dict:
    solids = _solids(W, H)
    rows = []
    for s in _stations(W, H):
        w, lo, hi, by_lo, by_hi = _clear_span(solids, s["c"], s["n"])
        rows.append({"seg": s["seg"], "at": s["at"], "width_mm": round(w, 2),
                     "off_lo": round(lo, 2), "off_hi": round(hi, 2),
                     "by_lo": by_lo, "by_hi": by_hi})
    widths = [r["width_mm"] for r in rows if r["width_mm"] > 0]
    blocked = [r for r in rows if r["width_mm"] <= 0.0]
    narrow = [r for r in rows if 0 < r["width_mm"] < W - 0.5]
    wide = [r for r in rows if r["width_mm"] > W + 3.0]
    return {
        "W_nominal": W, "H_nominal": H,
        "n_station": len(rows),
        "min_mm": round(min(widths), 2) if widths else 0.0,
        "max_mm": round(max(widths), 2) if widths else 0.0,
        "spread_mm": round(max(widths) - min(widths), 2) if widths else 0.0,
        "n_blocked": len(blocked), "blocked": blocked[:8],
        "n_narrow": len(narrow), "narrow": narrow[:10],
        "n_wide": len(wide), "wide": wide[:10],
        "rows": rows,
    }


def main() -> None:
    results = {}
    for D in (2.0, 8.0, 25.0):
        gap = M.recommend_gap_mm(D, max(1.0, 0.5 * D))
        W, H = gap["W"], gap["H"]
        r = measure(W, H)
        results["D=%.0f" % D] = r
        print("D=%-5.1f W=%-5.1f | rong %.2f..%.2f mm (lech %.2f) | "
              "chan=%d hep=%d rong_qua=%d"
              % (D, W, r["min_mm"], r["max_mm"], r["spread_mm"],
                 r["n_blocked"], r["n_narrow"], r["n_wide"]))
        for r2 in r["blocked"]:
            print("     CHAN  :", r2)
        for r2 in r["narrow"]:
            print("     HEP   :", r2)
        for r2 in r["wide"][:6]:
            print("     RONG  :", r2)

    out_path = OUT / "chute_width_verify.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("->", out_path)


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
