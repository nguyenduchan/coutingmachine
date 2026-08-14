# -*- coding: utf-8 -*-
"""
Verify cụm camera đếm tại cửa ra (part_exit_camera.py).

Kiểm những chỗ dễ sai nhất khi đặt camera vào một cụm cơ khí đã chật:
  A. TẦM NHÌN THÔNG — từ mọi điểm trên quỹ đạo rơi, tia tới ống kính VÀ tia
     tới đèn nền không được xuyên qua bất kỳ khối nào. Đây là phép kiểm thật:
     dựng trụ mảnh dọc tia rồi lấy giao khối, không phải ước lượng bằng mắt.
  B. KHUNG HÌNH PHỦ ĐỦ — quỹ đạo rơi của cả dải viên 2–25 mm phải nằm trong
     khung, từ mép đĩa (z=0, điểm cam kết) xuống tới miệng phễu.
  C. PHỄU HỨNG TRÚNG — viên mọi cỡ phải rơi vào trong miệng phễu, còn dư biên.
  D. KHÔNG VA — khối camera/đèn/phễu/trụ không đâm vào cụm cơ khí có sẵn.
  E. NGÂN SÁCH THỜI GIAN — số khung hình bắt được viên nhỏ nhất, nhoè chuyển
     động, và quãng trượt khi dừng đĩa.

Run:
  freecadcmd 3d_model\\freecad\\verify_exit_camera.py
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

import FreeCAD as App
import Part

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import part_exit_camera as CAM  # noqa: E402
from mech_common import (  # noqa: E402
    DISC_R, W_MAX, W_MIN, recommend_gap_mm,
)
from tube_l_exit_gate import build_tube_l_exit_gate_parts  # noqa: E402

OUT = _HERE / "out"
RAY_R = 0.8  # bán kính trụ thử tia (mm)
HIT_VOL = 1.0  # mm³ — dưới ngưỡng này coi như chỉ chạm mép
LOS_SIZES = (2.0, 8.0, 25.0)  # cỡ viên dùng cho phép kiểm tốn kém
FOV_SIZES = (2.0, 5.0, 8.0, 12.0, 18.0, 25.0)


def _v(xy, z) -> App.Vector:
    return App.Vector(xy[0], xy[1], z)


def _ray_solid(p0: App.Vector, p1: App.Vector, r: float = RAY_R):
    d = p1.sub(p0)
    L = d.Length
    if L < 1e-6:
        return None
    return Part.makeCylinder(r, L, p0, App.Vector(d.x / L, d.y / L, d.z / L))


def _blocked_by(ray, solids: list[tuple[str, object]]) -> list[dict]:
    hits = []
    rbb = ray.BoundBox
    for name, sol in solids:
        bb = sol.BoundBox
        if (bb.XMax < rbb.XMin - 1 or bb.XMin > rbb.XMax + 1
                or bb.YMax < rbb.YMin - 1 or bb.YMin > rbb.YMax + 1
                or bb.ZMax < rbb.ZMin - 1 or bb.ZMin > rbb.ZMax + 1):
            continue
        try:
            vol = float(ray.common(sol).Volume)
        except Exception:
            continue
        if vol > HIT_VOL:
            hits.append({"part": name, "vol_mm3": round(vol, 3)})
    return hits


def _fall_samples(D: float, z_top: float, z_bot: float, n: int = 7):
    out = []
    for i in range(n):
        z = z_top + (z_bot - z_top) * i / (n - 1.0)
        x, y = CAM.fall_xyz(D, min(0.0, z))
        out.append((x, y, z))
    return out


def check_line_of_sight(geo: dict) -> dict:
    """Dò cao độ viên THẬT SỰ lộ ra: z cao nhất mà cả tia tới ống kính lẫn tia
    tới đèn nền đều thông, rồi kiểm cả dải đếm bên dưới nó cũng thông."""
    cam_pt = _v(geo["camera_front_xy"], CAM.CAM_AXIS_Z)
    bl_pt = _v(geo["backlight_xy"], CAM.CAM_AXIS_Z)

    def clear_at(D, z, solids):
        x, y = CAM.fall_xyz(D, min(0.0, z))
        p = App.Vector(x, y, z)
        out = []
        for tgt, label in ((cam_pt, "camera"), (bl_pt, "backlight")):
            ray = _ray_solid(p, tgt)
            if ray is None:
                continue
            hits = _blocked_by(ray, solids)
            if hits:
                out.append({"toward": label, "hits": hits})
        return out

    rows = []
    z_vis_worst = 0.0
    for D in LOS_SIZES:
        gap = recommend_gap_mm(D, max(1.0, 0.5 * D))
        solids = [(n, s) for n, s, _c in
                  build_tube_l_exit_gate_parts(gap["W"], gap["H"])
                  if s is not None and not s.isNull()]
        z_vis, first_block = None, None
        for i in range(0, 21):
            z = -1.5 * i
            blocked = clear_at(D, z, solids)
            if blocked:
                if first_block is None:
                    first_block = {"z_mm": z, "why": blocked}
                continue
            z_vis = z
            break
        # dưới z_vis phải thông suốt hết dải đếm
        band_rows = []
        if z_vis is not None:
            for j in range(1, 7):
                z = z_vis - CAM.COUNT_BAND_MM * j / 6.0
                band_rows.append({"z_mm": round(z, 2),
                                  "blocked": bool(clear_at(D, z, solids))})
        rows.append({
            "D_mm": D,
            "z_visible_mm": z_vis,
            "first_block": first_block,
            "band_blocked": [r for r in band_rows if r["blocked"]],
            "pass": z_vis is not None and not any(r["blocked"] for r in band_rows),
        })
        if z_vis is not None:
            z_vis_worst = min(z_vis_worst, z_vis)

    ok = all(r["pass"] for r in rows)
    return {
        "pass": ok,
        "z_visible_worst_mm": z_vis_worst,
        "count_band_mm": CAM.COUNT_BAND_MM,
        "band_z_range": (z_vis_worst - CAM.COUNT_BAND_MM, z_vis_worst),
        "rows": rows,
    }


def check_fov_coverage(geo: dict, z_top: float, z_bot: float) -> dict:
    """Chiếu dải đếm lên hệ trục ảnh: u = hướng dạt ngang, w = phương z."""
    ux, uy = geo["drift_dir"]
    ax, ay = geo["axis_anchor_xy"]
    fov_w, fov_h = geo["fov_mm"]

    rows = []
    for D in FOV_SIZES:
        worst_u, worst_w, ok = 0.0, 0.0, True
        for (x, y, z) in _fall_samples(D, z_top, z_bot, n=9):
            du = (x - ax) * ux + (y - ay) * uy
            dw = z - CAM.CAM_AXIS_Z
            # viên có bề rộng: mép ngoài cùng phải còn trong khung
            need_u = abs(du) + 0.5 * D
            need_w = abs(dw) + 0.5 * D
            worst_u = max(worst_u, need_u)
            worst_w = max(worst_w, need_w)
            if need_u > 0.5 * fov_w or need_w > 0.5 * fov_h:
                ok = False
        rows.append({
            "D_mm": D, "pass": ok,
            "max_u_mm": round(worst_u, 2), "half_fov_w": round(0.5 * fov_w, 2),
            "max_w_mm": round(worst_w, 2), "half_fov_h": round(0.5 * fov_h, 2),
        })
    return {
        "pass": all(r["pass"] for r in rows),
        "band_z_range": (round(z_bot, 2), round(z_top, 2)),
        "rows": rows,
    }


def check_funnel_clear_of_band(z_bot: float) -> dict:
    """Phễu phải nằm DƯỚI đáy dải đếm, kể cả với viên to nhất."""
    need = z_bot - 0.5 * max(FOV_SIZES) - 2.0
    return {
        "pass": CAM.FUNNEL_TOP_Z < need,
        "funnel_top_z": CAM.FUNNEL_TOP_Z,
        "must_be_below_z": round(need, 2),
        "margin_mm": round(need - CAM.FUNNEL_TOP_Z, 2),
    }


def check_funnel_catch() -> dict:
    mx, my = CAM.fall_xyz(8.0, CAM.FUNNEL_TOP_Z)
    mw, mh = CAM.FUNNEL_MOUTH
    inner_w = mw - 2 * CAM.FUNNEL_T
    inner_h = mh - 2 * CAM.FUNNEL_T
    rows = []
    for D in FOV_SIZES:
        x, y = CAM.fall_xyz(D, CAM.FUNNEL_TOP_Z)
        mgx = 0.5 * inner_w - abs(x - mx) - 0.5 * D
        mgy = 0.5 * inner_h - abs(y - my) - 0.5 * D
        rows.append({
            "D_mm": D, "at_xy": (round(x, 2), round(y, 2)),
            "margin_x_mm": round(mgx, 2), "margin_y_mm": round(mgy, 2),
            "pass": mgx > 2.0 and mgy > 2.0,
        })
    return {"pass": all(r["pass"] for r in rows), "mouth_center": (round(mx, 2), round(my, 2)), "rows": rows}


def check_no_collision() -> dict:
    gap = recommend_gap_mm(8.0, 4.0)
    mech = [(n, s) for n, s, _c in build_tube_l_exit_gate_parts(gap["W"], gap["H"])
            if s is not None and not s.isNull()]
    new = [(n, s) for n, s, _c in CAM.build_exit_camera_parts()
           if s is not None and not s.isNull()]
    rows = []
    for na, sa in new:
        for nb, sb in mech:
            bba, bbb = sa.BoundBox, sb.BoundBox
            if (bba.XMax < bbb.XMin or bba.XMin > bbb.XMax
                    or bba.YMax < bbb.YMin or bba.YMin > bbb.YMax
                    or bba.ZMax < bbb.ZMin or bba.ZMin > bbb.ZMax):
                continue
            try:
                vol = float(sa.common(sb).Volume)
            except Exception:
                continue
            if vol > HIT_VOL:
                rows.append({"a": na, "b": nb, "vol_mm3": round(vol, 2)})
    return {"pass": not rows, "collisions": rows}


def check_timing(geo: dict) -> dict:
    v = geo["speed_at_rim_mm_s"]
    fov_h = CAM.COUNT_BAND_MM
    frames = {}
    for fps in (30, 60, 120):
        frames[str(fps)] = round((fov_h + W_MIN) / v * fps, 1)
    blur = {str(us): round(v * us * 1e-6, 4) for us in (100, 500, 1000, 2000)}
    slip = {str(ms): round(CAM.stop_slip_mm(ms * 1e-3), 2)
            for ms in (20, 50, 100, 200, 500)}
    return {
        "pass": frames["60"] >= 5.0,
        "speed_at_rim_mm_s": round(v, 2),
        "smallest_pill_frames": frames,
        "blur_mm_by_exposure_us": blur,
        "stop_slip_mm_by_t_stop_ms": slip,
        "px_per_mm": round(geo["px_per_mm"], 2),
        "smallest_pill_px": round(W_MIN * geo["px_per_mm"], 1),
    }


def main() -> None:
    geo = CAM.exit_view_geometry()
    los = check_line_of_sight(geo)
    z_top = los["z_visible_worst_mm"]
    z_bot = z_top - CAM.COUNT_BAND_MM
    fov = check_fov_coverage(geo, z_top, z_bot)
    clr = check_funnel_clear_of_band(z_bot)
    fun = check_funnel_catch()
    tim = check_timing(geo)
    col = check_no_collision()

    result = {
        "pass": all(x["pass"] for x in (fov, fun, clr, tim, col, los)),
        "geometry": {k: v for k, v in geo.items() if k != "sizes"},
        "sizes": geo["sizes"],
        "line_of_sight": los,
        "fov_coverage": fov,
        "funnel_clear_of_band": clr,
        "funnel_catch": fun,
        "no_collision": col,
        "timing": tim,
    }
    out_path = OUT / "exit_camera_verify.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print("A. Tam nhin thong        : pass=%s | vien lo ra tu z=%.1f mm, dai dem %.1f..%.1f"
          % (los["pass"], z_top, z_bot, z_top))
    for r in los["rows"]:
        print("     D=%-5.1f z_lo_ra=%s  chan dau tien: %s"
              % (r["D_mm"], r["z_visible_mm"],
                 (r["first_block"] or {}).get("why", "khong")))
        if r["band_blocked"]:
            print("        DAI DEM BI CHE:", r["band_blocked"])
    print("B. Khung hinh phu du     : pass=%s | dai dem z=%s"
          % (fov["pass"], fov["band_z_range"]))
    for r in fov["rows"]:
        if not r["pass"]:
            print("     THIEU:", r)
    print("B2. Pheu duoi dai dem    : pass=%s | pheu z=%.1f, phai duoi %.1f (du %.1f mm)"
          % (clr["pass"], clr["funnel_top_z"], clr["must_be_below_z"], clr["margin_mm"]))
    print("C. Pheu hung trung       : pass=%s | tam mieng %s"
          % (fun["pass"], fun["mouth_center"]))
    for r in fun["rows"]:
        if not r["pass"]:
            print("     TRUOT:", r)
    print("D. Khong va cham         : pass=%s | %s cap dam nhau"
          % (col["pass"], len(col["collisions"])))
    for r in col["collisions"]:
        print("     VA:", r)
    print("E. Ngan sach thoi gian   : pass=%s | vien 2mm = %s px, %s khung @60fps"
          % (tim["pass"], tim["smallest_pill_px"], tim["smallest_pill_frames"]["60"]))
    print("   nhoe theo phoi sang (mm):", tim["blur_mm_by_exposure_us"])
    print("   truot khi dung dia (mm) :", tim["stop_slip_mm_by_t_stop_ms"])
    print("OVERALL pass=%s -> %s" % (result["pass"], out_path))


if __name__ == "__main__" or True:
    main()
