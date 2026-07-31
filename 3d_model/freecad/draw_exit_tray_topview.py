"""2D top-view — exit tray only.

Left wall: straight line
Right wall: quarter-circle Ø10cm (R=50) on top + straight below
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Polygon

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Same constants as show_jgb37_gui.py
ARC_D = 100.0
ARC_R = ARC_D / 2.0  # 50 mm — 1/4 đường tròn Ø10cm
CH_W = 12.0
STRAIGHT_LEN = 65.0
WT = 3.0
FLOOR_SIDE_PAD = 20.0
WALL_FRONT_CLEAR = 30.0  # thành cách cạnh trước đế 3 cm
ACX, ACY = -50.0, 50.0  # FROZEN — same as show_jgb37_gui.py


def thicken(xs, ys, t):
    pts = np.column_stack([xs, ys]).astype(float)
    n = len(pts)
    left, right = [], []
    for i in range(n):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == n - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        ln = float(np.linalg.norm(d)) or 1.0
        nx, ny = -d[1] / ln, d[0] / ln
        left.append(pts[i] + np.array([nx, ny]) * (t / 2))
        right.append(pts[i] - np.array([nx, ny]) * (t / 2))
    return np.vstack([left, right[::-1]])


def main() -> None:
    x_right = ACX - ARC_R
    y_top = ACY + ARC_R
    y_join = ACY
    y_floor_front = y_join - STRAIGHT_LEN
    y_wall_front = y_floor_front + WALL_FRONT_CLEAR
    x_left = x_right - CH_W - WT

    th = np.linspace(math.radians(90), math.radians(180), 60)
    arc_x = ACX + ARC_R * np.cos(th)
    arc_y = ACY + ARC_R * np.sin(th)

    # Floor — wider than walls
    x0 = x_left - WT / 2 - FLOOR_SIDE_PAD
    x1 = x_right + WT / 2 + FLOOR_SIDE_PAD
    floor = [
        [x0, y_floor_front],
        [x1, y_floor_front],
        [x1, y_join],
    ]
    for i in range(len(th) - 1, -1, -1):
        floor.append(
            [
                ACX + (ARC_R + CH_W + FLOOR_SIDE_PAD) * math.cos(th[i]),
                ACY + (ARC_R + CH_W + FLOOR_SIDE_PAD) * math.sin(th[i]),
            ]
        )
    floor.append([x0, y_top])

    fig, ax = plt.subplots(figsize=(6, 8.5), dpi=170)
    ax.set_aspect("equal")
    ax.set_title(
        "Khay thoát thuốc — hình chiếu bằng\n"
        "Đế rộng hơn ngang | Thành cách mép trước 3cm",
        fontsize=11,
        pad=8,
    )

    ax.add_patch(
        Polygon(floor, closed=True, fc="#e8f6ff", ec="#6aa8c8", lw=1.2, zorder=0)
    )

    MAG = "#b000b0"
    # Left straight (stops before floor front)
    ax.add_patch(
        Polygon(
            thicken([x_left, x_left], [y_wall_front, y_top], WT),
            closed=True,
            fc=MAG,
            ec="#700070",
            lw=0.5,
            zorder=3,
        )
    )
    # Right arc (quarter)
    ax.add_patch(
        Polygon(
            thicken(list(arc_x), list(arc_y), WT),
            closed=True,
            fc=MAG,
            ec="#700070",
            lw=0.5,
            zorder=3,
        )
    )
    # Right straight (stops 3cm before floor front)
    ax.add_patch(
        Polygon(
            thicken([x_right, x_right], [y_join, y_wall_front], WT),
            closed=True,
            fc=MAG,
            ec="#700070",
            lw=0.5,
            zorder=3,
        )
    )

    # Dim: quarter circle guide (thin)
    ax.add_patch(
        plt.Circle((ACX, ACY), ARC_R, fill=False, ec="#aaa", ls="--", lw=0.8, zorder=1)
    )
    ax.plot(ACX, ACY, "+", color="#888", ms=8)
    ax.text(ACX + 4, ACY + 4, "tâm 1/4\nØ10cm", fontsize=7, color="#666")

    ax.add_patch(
        FancyBboxPatch(
            (x0, y_floor_front - 12),
            (x1 - x0),
            10,
            boxstyle="round,pad=0.3,rounding_size=1.5",
            fc="#2e2e2e",
            ec="#111",
            lw=1,
            zorder=2,
        )
    )
    # Mark 3cm wall clear
    ax.annotate(
        "",
        xy=((x_left + x_right) / 2, y_floor_front),
        xytext=((x_left + x_right) / 2, y_wall_front),
        arrowprops=dict(arrowstyle="<->", color="#c60", lw=1.2),
    )
    ax.text(
        (x_left + x_right) / 2 + 6,
        (y_floor_front + y_wall_front) / 2,
        "3cm",
        color="#c60",
        fontsize=8,
        va="center",
    )

    ax.text(
        x_left - 8,
        (y_wall_front + y_top) / 2,
        "Wall_Left\n(thẳng)",
        color=MAG,
        fontsize=8,
        rotation=90,
        va="center",
        ha="right",
        fontweight="bold",
    )
    ax.text(
        ACX - ARC_R * 0.3,
        ACY + ARC_R * 0.55,
        "Wall_Right_Arc\n(1/4 Ø10cm)",
        color=MAG,
        fontsize=8,
        ha="center",
        fontweight="bold",
    )
    ax.text(
        x_right + 8,
        (y_join + y_wall_front) / 2,
        "Wall_Right\n_Straight",
        color=MAG,
        fontsize=8,
        va="center",
        fontweight="bold",
    )
    ax.text(
        (x_left + x_right) / 2,
        y_floor_front - 7,
        "cửa ra (đế)",
        color="white",
        fontsize=8,
        ha="center",
    )
    ax.text(
        (x_left + x_right) / 2,
        y_top + 6,
        "cửa vào",
        color="#0a7a0a",
        fontsize=9,
        ha="center",
        fontweight="bold",
    )

    ax.set_xlim(x0 - 25, max(x1, ACX + ARC_R) + 25)
    ax.set_ylim(y_floor_front - 25, y_top + 20)
    ax.axis("off")

    png = OUT / "exit_tray_topview.png"
    svg = OUT / "exit_tray_topview.svg"
    fig.tight_layout()
    fig.savefig(png, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    fig.savefig(svg, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    print("Wrote", png)
    print("Wrote", svg)


if __name__ == "__main__":
    main()
