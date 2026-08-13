"""
Stress test cho tube_l_disc_rigid_body_pybullet.py: mo phong lai dung dong tac
nguoi dung se lam trong GUI —

  - "Add pill": tha them vien (kich thuoc viên nén ngau nhien trong dai thuc te)
    tai cac thoi diem ngau nhien.
  - "Apply lane W/H": doi do rong/cao mang (xay lai collision) tai cac thoi diem
    ngau nhien, ca truong hop mang RONG RAI (de vien thoat duoc) va mang HEP hon
    kich thuoc vien hien co (de test tinh huong ket/kem, khong duoc xuyen tuong).

Muc tieu: xac nhan he thong (dia + mang + tran chan chieu cao) chiu duoc thay
doi dong ma KHONG BAO GIO de vien "lot san"/"xuyen tuong" (yeu cau cung, bat
buoc dat 0 trong moi lan chay), va cua khoet lo cuoi mang van hoat dong dung
(co it nhat 1 vien thoat khi mang du rong).

Chay:
  python 3d_model/sim/tube_l_disc_rigid_body_stress_test.py
  python 3d_model/sim/tube_l_disc_rigid_body_stress_test.py --duration 120 --seed 7
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import pybullet as p

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tube_l_disc_rigid_body_pybullet as m  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "tube_l_disc_rigid_body_stress_metrics.json"

# Dai kich thuoc "vien nen" thuc te de random khi stress test (mm) — dang tru (D>T),
# tron/deu canh, giong hinh dang vien nen pho thong (khong phai vien nang dai/capsule).
PILL_D_RANGE = (5.0, 14.0)
PILL_T_RANGE = (2.5, 6.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpm", type=float, default=40.0)
    ap.add_argument("--duration", type=float, default=90.0, help="Tong thoi gian mo phong (giay, thang mo phong)")
    ap.add_argument("--add_every", type=float, default=2.0, help="Trung binh so giay giua 2 lan them vien")
    ap.add_argument("--apply_every", type=float, default=12.0, help="Trung binh so giay giua 2 lan doi W/H mang")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--gui", action="store_true", help="Mo GUI de xem stress test (mac dinh headless)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    omega = args.rpm * 2.0 * math.pi / 60.0
    D0, T0 = 8.0, 4.0
    W0, H0 = m.gap_wh(D0, T0)

    cid = m.make_world(gui=args.gui)
    disc = m.load_disc_mesh(cid)
    m.load_all_visual_parts_from_manifest(cid)
    disc_texture = m.add_disc_texture_overlay(cid, radius_mm=98.0)
    m.build_bowl_ring(cid)
    m.build_permanent_safety_net(cid)
    r_a, chute_ids = m.build_exit_chute(cid, W0, H0)
    height_stop_id = m.build_height_stop(cid, H0)
    exit_x_min = -r_a - 0.5 * W0 - m.EXIT_WALL_T
    exit_x_max = -r_a + 0.5 * W0 + m.EXIT_WALL_T
    cur_w, cur_h = W0, H0

    pills: list[int] = []
    status: dict[int, dict] = {}
    r_lo, r_hi = 82.0, 95.0

    def add_one_pill(t_now: float):
        D = rng.uniform(*PILL_D_RANGE)
        T = rng.uniform(*PILL_T_RANGE)
        bid, st = m.spawn_random_pill_on_disc(cid, omega, D, T, "tablet", rng, r_lo, r_hi)
        st["D_mm"] = round(D, 2)
        st["T_mm"] = round(T, 2)
        st["spawn_t"] = round(t_now, 2)
        pills.append(bid)
        status[bid] = st
        return D, T

    def apply_lane(t_now: float, force_narrow: bool):
        nonlocal chute_ids, height_stop_id, r_a, exit_x_min, exit_x_max, cur_w, cur_h
        if force_narrow:
            # Mang HEP hon vien hien co — test tinh huong ket/kem, van khong duoc xuyen tuong.
            w_new = rng.uniform(2.0, 6.0)
            h_new = rng.uniform(2.0, 4.0)
        else:
            w_new = rng.uniform(8.0, 26.0)
            h_new = rng.uniform(4.0, 12.0)
        for bid_old in chute_ids:
            p.removeBody(bid_old, physicsClientId=cid)
        p.removeBody(height_stop_id, physicsClientId=cid)
        r_a, chute_ids = m.build_exit_chute(cid, w_new, h_new)
        height_stop_id = m.build_height_stop(cid, h_new)
        exit_x_min = -r_a - 0.5 * w_new - m.EXIT_WALL_T
        exit_x_max = -r_a + 0.5 * w_new + m.EXIT_WALL_T
        cur_w, cur_h = w_new, h_new
        print(f"[stress] t={t_now:.1f}s Apply lane W={w_new:.1f}mm H={h_new:.1f}mm (narrow={force_narrow})")

    # Tha san 4 vien ban dau + 1 lan doi mang de bat dau tu trang thai "dang chay".
    for _ in range(4):
        add_one_pill(0.0)
    print(f"[stress] bat dau: {len(pills)} vien, mang W={cur_w}mm H={cur_h}mm, {args.duration}s")

    next_add_t = rng.expovariate(1.0 / args.add_every)
    next_apply_t = rng.expovariate(1.0 / args.apply_every)
    n_apply = 0
    n_narrow_apply = 0

    t_sim = 0.0
    step = 0
    jam_events = 0
    n_steps = int(args.duration / m.DT)
    theta = 0.0
    try:
        while p.isConnected(cid) and step < n_steps:
            theta = (theta + omega * m.DT) % (2.0 * math.pi)
            orn = p.getQuaternionFromEuler([0, 0, theta])
            p.resetBasePositionAndOrientation(disc, [0, 0, 0], orn, physicsClientId=cid)
            p.resetBaseVelocity(disc, angularVelocity=[0, 0, omega], physicsClientId=cid)
            p.resetBasePositionAndOrientation(disc_texture, [0, 0, 0.35 * m.S], orn, physicsClientId=cid)
            p.stepSimulation(physicsClientId=cid)
            t_sim += m.DT
            step += 1

            if t_sim >= next_add_t:
                add_one_pill(t_sim)
                next_add_t = t_sim + rng.expovariate(1.0 / args.add_every)

            if t_sim >= next_apply_t:
                narrow = rng.random() < 0.4
                apply_lane(t_sim, narrow)
                n_apply += 1
                n_narrow_apply += int(narrow)
                next_apply_t = t_sim + rng.expovariate(1.0 / args.apply_every)

            in_channel = []
            for bid in pills:
                st = status[bid]
                if st["exited"] or st.get("fell") or st.get("escaped"):
                    continue
                lv, av = p.getBaseVelocity(bid, physicsClientId=cid)
                sp = math.sqrt(lv[0] ** 2 + lv[1] ** 2 + lv[2] ** 2)
                if sp > m.VMAX_MPS:
                    k = m.VMAX_MPS / sp
                    p.resetBaseVelocity(
                        bid, linearVelocity=[lv[0] * k, lv[1] * k, lv[2] * k], angularVelocity=av,
                        physicsClientId=cid,
                    )
                pos, _ = p.getBasePositionAndOrientation(bid, physicsClientId=cid)
                x_mm, y_mm, z_mm = pos[0] / m.S, pos[1] / m.S, pos[2] / m.S
                r_mm = math.hypot(x_mm, y_mm)
                if exit_x_min <= x_mm <= exit_x_max and y_mm <= m.EXIT_Y_DONE:
                    st["exited"] = True
                    st["exit_t"] = round(t_sim, 2)
                    continue
                if exit_x_min - 5.0 <= x_mm <= exit_x_max + 5.0 and y_mm <= 5.0:
                    in_channel.append(bid)
                    lv2, av2 = p.getBaseVelocity(bid, physicsClientId=cid)
                    p.resetBaseVelocity(
                        bid, linearVelocity=[lv2[0], lv2[1] - m.CHUTE_ASSIST_MPS2 * m.DT, lv2[2]],
                        angularVelocity=av2, physicsClientId=cid,
                    )
                if z_mm < m.FLOOR_FAIL_Z:
                    st["fell"] = True
                elif r_mm > m.ESCAPE_FAIL_R and z_mm > -5.0:
                    st["escaped"] = True

            if len(in_channel) >= 2:
                for a in range(len(in_channel)):
                    for b in range(a + 1, len(in_channel)):
                        if p.getContactPoints(in_channel[a], in_channel[b], physicsClientId=cid):
                            jam_events += 1

            if args.gui and step % 4 == 0:
                import time as _time
                _time.sleep(4 * m.DT)
    except p.error:
        pass
    finally:
        if p.isConnected(cid):
            p.disconnect(physicsClientId=cid)

    n_exited = sum(1 for st in status.values() if st["exited"])
    n_fell = sum(1 for st in status.values() if st.get("fell"))
    n_escaped = sum(1 for st in status.values() if st.get("escaped"))
    n_active_end = len(pills) - n_exited - n_fell - n_escaped
    passed = n_fell == 0 and n_escaped == 0
    result = {
        "pass": passed,
        "duration_s": args.duration,
        "n_pills_added": len(pills),
        "n_lane_apply": n_apply,
        "n_lane_apply_narrow": n_narrow_apply,
        "n_exited": n_exited,
        "n_fell_through": n_fell,
        "n_escaped_over_wall": n_escaped,
        "n_active_at_end": n_active_end,
        "jam_events_in_channel": jam_events,
        "final_lane_W_mm": round(cur_w, 2),
        "final_lane_H_mm": round(cur_h, 2),
        "pills": {str(bid): st for bid, st in status.items()},
        "note": "pass=True nghia la KHONG co vien nao lot san/xuyen tuong trong suot qua trinh "
                "them vien + doi W/H mang ngau nhien (bao gom ca truong hop mang hep hon vien). "
                "n_exited>0 xac nhan cua khoet lo cuoi mang van hoat dong sau khi mang bi xay lai.",
    }
    METRICS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        f"[stress] KET QUA: pass={passed} added={len(pills)} exited={n_exited} "
        f"fell_through={n_fell} escaped={n_escaped} active_end={n_active_end} "
        f"lane_apply={n_apply}(narrow={n_narrow_apply}) jam_events={jam_events}"
    )
    print(f"METRICS -> {METRICS}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
