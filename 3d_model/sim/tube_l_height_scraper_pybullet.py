"""
Height_Scraper (thanh giới hạn chiều cao) — PyBullet contact thật.

Ma sát đĩa chỉ đẩy viên theo phương TIẾP TUYẾN (v=omega x r); ngay tại miệng
lane, cung tiếp tuyến đó xấp xỉ MỘT ĐƯỜNG THẲNG cục bộ (bán kính ~90-100mm >>
kích thước viên) — nên bài test này dùng đẩy thẳng đều (giống
trial_chute_slide trong tube_l_egress_pybullet.py) làm đại diện cục bộ cho
đúng lực đó, tập trung vào vật lý cốt lõi: lưỡi gạt cố định ở độ cao H có
thực sự CHẶN được vật cao hơn H hay không (tiếp xúc + trọng lực + mô-men lật
thật, không phải suy luận hình học).

  A) viên "đứng" (stand, cao = D > H)      -> phải bị lưỡi gạt hạ xuống nằm
  B) 2 viên chồng lên nhau (cao ~ 2T > H)  -> viên trên phải bị chặn/gạt rơi,
     không được lọt cả cụm qua khe

  python 3d_model/sim/tube_l_height_scraper_pybullet.py
  python 3d_model/sim/tube_l_height_scraper_pybullet.py --gui
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import pybullet as p

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tube_l_egress_pybullet as E  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "tube_l_height_scraper_metrics.json"

DT = E.DT
S = E.S
GAP0 = E.GAP0
MAX_STEPS = 240 * 8
PUSH_V = 0.35  # m/s, giong trial_chute_slide


SCRAPER_ENTRY_H_MM = 8.0  # tuong duong SCRAPER_ENTRY_H trong tube_l_exit_gate.py
SCRAPER_ENTRY_T_MM = 2.0  # tuong duong SCRAPER_ENTRY_T


SCRAPER_RAMP_LEN_MM = 10.0  # khop SCRAPER_RAMP_LEN trong tube_l_exit_gate.py


def build_floor_and_bar(cid, H, lane_half_w, bar_x_mm, with_ramp=True):
    floor = E.box(cid, 0.09, 0.02, 0.001, [0.0, 0.0, GAP0 * S - 0.001], (0.5, 0.5, 0.5, 1), fr=0.5)
    t = 2.0 * S
    hz = 0.5 * t
    z = (GAP0 + H) * S + hz
    # hx = mong theo huong day (=SCRAPER_T=2mm); hy = trai rong theo lane (Y).
    bar = E.box(
        cid, 1.0 * S, lane_half_w * S, hz, [bar_x_mm * S, 0.0, z],
        rgba=(0.9, 0.15, 0.15, 1), fr=0.5,
    )
    # Ghi chu: KHONG dung thanh L (SCRAPER_ENTRY_T/H) ngang het be rong lane —
    # trong CAD that (make_height_scraper) no chi la mot mieng nho (2mm huong
    # kinh x 6mm tiep tuyen) dung o MEP TRONG cua luoi, khong choan het lane
    # (thu dau dung nguyen ca chieu rong khien ca vien NAM cung bi chan sai).
    # Doc nghieng (_height_ramp_local that su trong CAD) — xap xi bang cau
    # thang nhieu bac mong, day thap dan tu xa (khong chan) den H tai mep bar.
    if with_ramp:
        # Cau thang N bac xap xi doc nghieng thuc (tam giac trong CAD that):
        # bac gan bar nhat co day = H (khop luoi); bac xa nhat co day = HIGH
        # (khong chan gi ca) — vien cao/chong bi ep thap dan truoc khi toi bar.
        n = 8
        seg_len_mm = SCRAPER_RAMP_LEN_MM / n
        z_high = H + 25.0
        plate_thick_mm = 20.0
        for i in range(n):
            # i=0: xa bar nhat (upstream) -> day cao (z_high); i=n-1: sat bar -> day=H
            frac_near_bar = i / (n - 1)  # 0..1
            bottom_mm = z_high - (z_high - H) * frac_near_bar
            x_center_mm = bar_x_mm - SCRAPER_RAMP_LEN_MM + (i + 0.5) * seg_len_mm
            top_mm = bottom_mm + plate_thick_mm
            z_center_mm = 0.5 * (bottom_mm + top_mm)
            E.box(
                cid, 0.5 * seg_len_mm * S, lane_half_w * S, 0.5 * plate_thick_mm * S,
                [x_center_mm * S, 0.0, (GAP0 + z_center_mm) * S],
                rgba=(0.95, 0.6, 0.2, 1), fr=0.5,
            )
    return floor, bar


def spawn_stand_pill(cid, D, T, x_mm, y_mm):
    # Vien nam "dung tren canh" (lan tren via tron): duong kinh D quyet dinh
    # chieu cao (giong pose="stand" trong tube_l_exit_gate._pill_extents ->
    # (T, D)); truoc day dao nguoc rad/length khien vien lai THAP (=T), khong
    # thu duoc dung kich ban "cao hon H" can test.
    rad = 0.5 * D * S
    length = T * S
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=rad, height=length, physicsClientId=cid)
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=rad, length=length, rgbaColor=[0.2, 0.7, 1.0, 1], physicsClientId=cid)
    z = GAP0 * S + rad + 0.0006
    orn = p.getQuaternionFromEuler([math.pi / 2.0, 0, 0])
    bid = p.createMultiBody(0.0008, col, vis, [x_mm * S, y_mm * S, z], orn, physicsClientId=cid)
    p.changeDynamics(bid, -1, lateralFriction=0.5, restitution=0.05, physicsClientId=cid)
    return bid


def spawn_flat_pill(cid, D, T, x_mm, y_mm, z_bottom_mm, rgba=(1, 0.6, 0.15, 1)):
    rad = 0.5 * D * S
    h = T * S
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=rad, height=h, physicsClientId=cid)
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=rad, length=h, rgbaColor=list(rgba), physicsClientId=cid)
    z = z_bottom_mm * S + 0.5 * h + 0.0004
    bid = p.createMultiBody(0.0008, col, vis, [x_mm * S, y_mm * S, z], physicsClientId=cid)
    p.changeDynamics(bid, -1, lateralFriction=0.5, restitution=0.05, physicsClientId=cid)
    return bid


PUSH_FORCE_N = 0.02  # ap tai diem gan DAY vien — dung ban chat ma sat nghi
# dia (luc tac dung tai mat tiep xuc dia, KHONG phai tai tam vien). Dung
# resetBaseVelocity(tam) truoc day cho ket qua SAI: khong sinh mo-men lat vien
# dung; ap luc tai day moi tao dung cap luc (day duoi + can tren tai bar) lam
# lat vien — khop dung co che that (dia keo day, bar can tren).


def drive_and_run(cid, bodies, bar_x_mm, gui):
    passed_bar = {b: False for b in bodies}
    max_h = {b: 0.0 for b in bodies}
    for step in range(MAX_STEPS):
        for bid in bodies:
            pos, _ = p.getBasePositionAndOrientation(bid, physicsClientId=cid)
            if not passed_bar[bid]:
                contact_pt = [pos[0], pos[1], GAP0 * S + 0.0005]
                p.applyExternalForce(bid, -1, [PUSH_FORCE_N, 0, 0], contact_pt, p.WORLD_FRAME, physicsClientId=cid)
                if pos[0] / S > bar_x_mm + 3.0:
                    passed_bar[bid] = True
        p.stepSimulation(physicsClientId=cid)
        if gui and step % 2 == 0:
            time.sleep(DT)
        for bid in bodies:
            pos, _ = p.getBasePositionAndOrientation(bid, physicsClientId=cid)
            max_h[bid] = max(max_h[bid], pos[2] / S)
    final = {}
    for bid in bodies:
        pos, orn = p.getBasePositionAndOrientation(bid, physicsClientId=cid)
        final[bid] = {
            "x_mm": pos[0] / S, "y_mm": pos[1] / S, "z_mm": pos[2] / S,
            "max_z_mm": max_h[bid], "passed_bar": passed_bar[bid],
        }
    return final


def scenario_stand_pill(D, T, gui):
    cid = E.world(gui)
    W, H = E.gap_wh(D, T)
    bar_x = 20.0
    build_floor_and_bar(cid, H, 0.5 * W + 2.0, bar_x)
    pill = spawn_stand_pill(cid, D, T, -20.0, 0.0)
    result = drive_and_run(cid, [pill], bar_x, gui)
    r = result[pill]
    knocked_down = r["z_mm"] <= (GAP0 + H + 1.0)
    p.disconnect(physicsClientId=cid)
    return {
        "scenario": "stand_pill_taller_than_H",
        "D_mm": D, "T_mm": T, "H_mm": H,
        "final": r,
        "knocked_down": bool(knocked_down),
        "pass": bool(knocked_down and r["passed_bar"]),
    }


def scenario_stacked_pills(D, T, gui):
    cid = E.world(gui)
    W, H = E.gap_wh(D, T)
    bar_x = 20.0
    build_floor_and_bar(cid, H, 0.5 * W + 2.0, bar_x)
    bottom = spawn_flat_pill(cid, D, T, -20.0, 0.0, GAP0, rgba=(1, 0.6, 0.15, 1))
    top = spawn_flat_pill(cid, D, T, -20.0, 0.0, GAP0 + T + 0.1, rgba=(0.9, 0.9, 0.1, 1))
    result = drive_and_run(cid, [bottom, top], bar_x, gui)
    rb, rt = result[bottom], result[top]
    bottom_passed = rb["passed_bar"]
    top_separated = (not rt["passed_bar"]) or (rt["z_mm"] < GAP0 + H + 1.0 and rt["x_mm"] < bar_x)
    top_low_after = rt["z_mm"] <= (GAP0 + H + 1.0)
    p.disconnect(physicsClientId=cid)
    return {
        "scenario": "two_pills_stacked",
        "D_mm": D, "T_mm": T, "H_mm": H,
        "bottom_final": rb, "top_final": rt,
        "bottom_passed_alone": bool(bottom_passed),
        "top_blocked_or_flattened": bool((not rt["passed_bar"]) or top_low_after),
        "pass": bool(bottom_passed and ((not rt["passed_bar"]) or top_low_after)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--D", type=float, default=8.0)
    ap.add_argument("--T", type=float, default=4.0)
    args = ap.parse_args()

    r1 = scenario_stand_pill(args.D, args.T, args.gui)
    r2 = scenario_stacked_pills(args.D, args.T, False)
    for r in (r1, r2):
        print(r["scenario"], "pass=", r["pass"], flush=True)
    report = {"pass": r1["pass"] and r2["pass"], "stand": r1, "stacked": r2}
    METRICS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote", METRICS, flush=True)
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
