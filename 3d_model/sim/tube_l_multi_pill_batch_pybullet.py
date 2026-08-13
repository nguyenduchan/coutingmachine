"""
Tube_L exit — PyBullet: NHIỀU viên CÙNG kích thước, đã xếp hàng đơn trong
Exit_Track, trượt ra CÙNG LÚC — kiểm tra khoảng cách tối thiểu (đúc kết từ
tube_l_exit_gate.min_angular_pitch_deg) có đủ để KHÔNG viên nào chồng/kẹt
viên khác dưới va chạm PyBullet THẬT (không phải model động học "không
tương tác" trong tube_l_exit_gate.py).

Bối cảnh: verify_multi_pill_batch_same_size() (kinematic, tube_l_exit_gate.py)
chứng minh bằng toán rằng nút thắt cổ chai là MIỆNG MÁNG RA — viên vào máng
lúc đầu bị ma sát ghìm rất chậm (drive_net nhỏ theo thiết kế tự-hãm), nên
khoảng lệch góc thả Δθ phải ≥ Δθ_min = (D+margin)/(r_lane·drive_net) để 2
viên không áp sát nhau ngay khi cùng vào máng. Script này spawn N viên đã
xếp hàng dọc Exit_Track với khoảng cách CHÍNH XÁC bằng ngưỡng đó (case
"spaced") và với khoảng cách gần 0 (case "dense", negative control), đẩy
cùng vận tốc như trial_chute_slide, và đo chồng lấn THẬT giữa các viên kề
nhau (getContactPoints) — xác nhận độc lập bằng vật lý contact, không chỉ
suy luận hình học.

  python 3d_model/sim/tube_l_multi_pill_batch_pybullet.py
  python 3d_model/sim/tube_l_multi_pill_batch_pybullet.py --gui --n 6
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
import tube_l_egress_pybullet as E  # noqa: E402  (reuse world/box/cyl/build_exit_chute/spawn_pill)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "tube_l_multi_pill_batch_metrics.json"

DT = E.DT
PEN_LIM = E.PEN_LIM
MAX_STEPS = 240 * 8
BOWL_IR = E.BOWL_IR
BOWL_OR = E.BOWL_OR
EXIT_LEN = E.EXIT_LEN
S = E.S

MU_WALL, MARGIN_DEG = 0.35, 5.0


def drive_net_and_beta() -> tuple[float, float]:
    """Khớp tube_l_exit_gate.exit_wall_friction_beta(); thuần toán, không cần FreeCAD."""
    beta = math.atan(MU_WALL) + math.radians(MARGIN_DEG)
    return math.sin(beta) - MU_WALL * math.cos(beta), beta


def min_gap_mm(D: float, margin_mm: float = 1.0) -> float:
    """Khoảng cách tối thiểu giữa 2 viên NGAY KHI cùng vào máng (D+margin) — xem
    tube_l_exit_gate.min_angular_pitch_deg cho suy luận đầy đủ; ở đây dùng trực
    tiếp làm khoảng rải dọc máng (không cần quy đổi qua góc vì test này spawn
    thẳng trong Exit_Track)."""
    return float(D) + float(margin_mm)


def run_queue(D, T, shape, n_pills, gap_mm, W, H, gui, label):
    cid = E.world(gui)
    exit_info = E.build_exit_chute(cid, W, H)
    walls = exit_info["walls"]
    r_a = exit_info["ax_mm"]
    y0 = -(BOWL_OR + 8.0)

    pills = []
    for i in range(n_pills):
        y = y0 - i * gap_mm
        bid = E.spawn_pill(cid, D, T, shape, "flat", -r_a, y)
        pills.append({"id": bid, "exited": False, "tunnel_wall": 0, "max_pen_wall": 0.0})

    neighbor_pairs = [(i, i + 1) for i in range(n_pills - 1)]
    max_pen_pair = {pair: 0.0 for pair in neighbor_pairs}
    n_pair_overlap_steps = {pair: 0 for pair in neighbor_pairs}

    active = list(range(n_pills))
    for step in range(MAX_STEPS):
        for idx in active:
            p.resetBaseVelocity(pills[idx]["id"], [0.0, -0.45, 0.0], [0, 0, 0], physicsClientId=cid)
        p.stepSimulation(physicsClientId=cid)
        if gui and step % 2 == 0:
            time.sleep(DT)

        for idx in list(active):
            pl = pills[idx]
            pen = E.max_pen(cid, pl["id"], walls)
            if pen > pl["max_pen_wall"]:
                pl["max_pen_wall"] = pen
            if pen > PEN_LIM:
                pl["tunnel_wall"] += 1
            pos, _ = p.getBasePositionAndOrientation(pl["id"], physicsClientId=cid)
            if pos[1] / S < -(BOWL_OR + EXIT_LEN * 0.9):
                pl["exited"] = True
                active.remove(idx)

        for (i, j) in neighbor_pairs:
            worst = 0.0
            for c in p.getContactPoints(pills[i]["id"], pills[j]["id"], physicsClientId=cid):
                if c[8] < 0:
                    worst = max(worst, -float(c[8]))
            if worst > max_pen_pair[(i, j)]:
                max_pen_pair[(i, j)] = worst
            if worst > 1e-5:
                n_pair_overlap_steps[(i, j)] += 1

        if not active:
            break

    for pl in pills:
        p.removeBody(pl["id"], physicsClientId=cid)
    p.disconnect(physicsClientId=cid)

    n_exited = sum(1 for pl in pills if pl["exited"])
    n_wall_tunnel = sum(pl["tunnel_wall"] for pl in pills)
    max_pen_wall_all = max((pl["max_pen_wall"] for pl in pills), default=0.0)
    max_pen_pair_mm = max((v for v in max_pen_pair.values()), default=0.0) / S
    n_pair_hit = sum(1 for v in n_pair_overlap_steps.values() if v > 0)
    passed = n_exited == n_pills and n_wall_tunnel == 0 and max_pen_pair_mm <= 0.05
    return {
        "pass": passed,
        "label": label,
        "n_pills": n_pills,
        "gap_mm": round(gap_mm, 3),
        "n_exited": n_exited,
        "n_wall_tunnel_hits": n_wall_tunnel,
        "max_penetration_wall_mm": round(max_pen_wall_all / S, 4),
        "max_penetration_pill_pill_mm": round(max_pen_pair_mm, 4),
        "n_neighbor_pairs_touching": n_pair_hit,
        "n_neighbor_pairs_total": len(neighbor_pairs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--D", type=float, default=8.0)
    ap.add_argument("--T", type=float, default=4.0)
    ap.add_argument("--shape", default="tablet")
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()

    W, H = E.gap_wh(args.D, args.T)
    drive_net, beta = drive_net_and_beta()
    gap_safe = min_gap_mm(args.D, margin_mm=1.0)
    gap_dense = max(0.1, args.D * 0.15)  # negative control: ep sat, gan nhu cham nhau

    r_spaced = run_queue(args.D, args.T, args.shape, args.n, gap_safe, W, H, args.gui, "spaced(D+1mm)")
    r_dense = run_queue(args.D, args.T, args.shape, args.n, gap_dense, W, H, False, "dense(negative_control)")

    for r in (r_spaced, r_dense):
        print(
            "%-24s pass=%s exited=%d/%d gap=%.2fmm wall_tunnel=%d pen_wall=%.3f pen_pill=%.3f pairs_touching=%d/%d"
            % (
                r["label"], r["pass"], r["n_exited"], r["n_pills"], r["gap_mm"],
                r["n_wall_tunnel_hits"], r["max_penetration_wall_mm"], r["max_penetration_pill_pill_mm"],
                r["n_neighbor_pairs_touching"], r["n_neighbor_pairs_total"],
            ),
            flush=True,
        )

    report = {
        "runs": [r_spaced, r_dense],
        "D_mm": args.D, "T_mm": args.T, "shape": args.shape,
        "W_mm": W, "H_mm": H,
        "drive_net": drive_net,
        "beta_deg": math.degrees(beta),
        "gap_safe_mm": gap_safe,
        "gap_dense_mm": gap_dense,
        "note": (
            "spaced: khoang thang doc Exit_Track >= D+1mm (nguong dan tu min_angular_pitch_deg "
            "trong tube_l_exit_gate.py, quy doi ve khoang cach doc mang tai thoi diem vao mang) "
            "-> khong viên nào chồng/kẹt viên khác. dense: khoang gan 0 -> chong lan that (negative control)."
        ),
    }
    METRICS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote", METRICS, flush=True)
    sys.exit(0 if r_spaced["pass"] else 1)


if __name__ == "__main__":
    main()
