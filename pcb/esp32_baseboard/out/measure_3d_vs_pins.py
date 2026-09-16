#!/usr/bin/env python3
"""Measure 3D pin tips vs PCB THT holes. Does not modify the board."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "esp32_baseboard.kicad_pcb"
GLB = ROOT / "out" / "tht_pins.glb"
REFS = {
    "J1", "J_MOT1", "J_MOT2", "J_P24S", "U_PWR1", "U_PWR2", "U_VIB",
    "J14", "J15", "J_IN2", "J_IN3", "J_CNT5", "J_P24N", "J_P5N",
    "J_KEY", "J_DISP", "J_USB", "U3", "U4", "SW_BOOT", "SW_NRST", "F1",
}


def extract_fps(text: str) -> list[str]:
    blocks: list[str] = []
    i = 0
    while True:
        p = text.find("(footprint ", i)
        if p < 0:
            break
        depth = 0
        for j in range(p, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[p : j + 1])
                    i = j + 1
                    break
        else:
            break
    return blocks


def parse_at(s: str):
    m = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?", s)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)


def pcb_tht():
    text = PCB.read_text(encoding="utf-8")
    out = []
    for fp in extract_fps(text):
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', fp)
        if not ref_m or ref_m.group(1) not in REFS:
            continue
        ref = ref_m.group(1)
        fat = None
        for line in fp.splitlines()[:12]:
            if "(at " in line:
                fat = parse_at(line)
                break
        if fat is None:
            continue
        fx, fy, fr = fat
        rad = np.deg2rad(fr)
        c, s = np.cos(rad), np.sin(rad)
        for m in re.finditer(
            r'\(pad "([^"]+)" (?:thru_hole|smd)[\s\S]*?\(at\s+([-\d.]+)\s+([-\d.]+)',
            fp,
        ):
            if "thru_hole" not in fp[m.start() : m.start() + 80] and "smd" in m.group(0):
                continue
            px, py = float(m.group(2)), float(m.group(3))
            wx = fx + px * c - py * s
            wy = fy + px * s + py * c
            out.append((ref, m.group(1), wx, wy, fx, fy, fr, px, py))
    return out


def uniq_xy(pts: np.ndarray, tol: float = 0.4) -> np.ndarray:
    if len(pts) == 0:
        return np.zeros((0, 2))
    used = np.zeros(len(pts), dtype=bool)
    out = []
    for i, p in enumerate(pts):
        if used[i]:
            continue
        d = np.hypot(pts[:, 0] - p[0], pts[:, 1] - p[1])
        used[d < tol] = True
        out.append((float(p[0]), float(p[1])))
    return np.array(out)


def cat(name: str) -> str | None:
    n = name.upper()
    if "PAD" in n:
        return None
    if any(k in n for k in ("PINSOCKET", "JST", "TERMINAL", "USB", "PUSH", "FUSE", "SCHURTER")):
        return "BODY"
    return None


def main() -> None:
    scene = trimesh.load(str(GLB), force="scene")
    below = []
    for node in scene.graph.nodes_geometry:
        T, geom_name = scene.graph.get(node)
        if cat(geom_name) is None:
            continue
        mesh = scene.geometry[geom_name]
        pts = trimesh.transform_points(mesh.vertices, T) * 1000.0
        sel = pts[pts[:, 1] < -0.10]
        if len(sel):
            below.append(sel[:, [0, 2]])
    pins = uniq_xy(np.vstack(below), 0.35) if below else np.zeros((0, 2))
    pads = pcb_tht()
    print(f"3D pin clusters={len(pins)}  PCB THT pads={len(pads)}")

    byref: dict[str, list] = defaultdict(list)
    for ref, pn, wx, wy, fx, fy, fr, px, py in pads:
        if len(pins) == 0:
            continue
        d = np.hypot(pins[:, 0] - wx, pins[:, 1] - wy)
        j = int(np.argmin(d))
        byref[ref].append(
            (float(d[j]), pn, wx, wy, float(pins[j, 0]), float(pins[j, 1]), fx, fy, fr, px, py)
        )

    print("\nref        n  max   med   n>0.5  mean_dxy_world     local_dxy (for offset)")
    for ref, rows in sorted(byref.items()):
        mx = max(r[0] for r in rows)
        med = float(np.median([r[0] for r in rows]))
        nbad = sum(1 for r in rows if r[0] > 0.5)
        # world pin - pad
        ddx = np.mean([r[4] - r[2] for r in rows])
        ddy = np.mean([r[5] - r[3] for r in rows])
        fr = rows[0][8]
        rad = np.deg2rad(fr)
        c, s = np.cos(rad), np.sin(rad)
        # world error -> footprint local (inverse rot)
        lx = c * ddx + s * ddy
        ly = -s * ddx + c * ddy
        # KiCad 3D offset Y is inverted vs footprint Y
        print(
            f"{ref:10s} {len(rows):2d} {mx:5.3f} {med:5.3f} {nbad:3d}  "
            f"({ddx:+6.3f},{ddy:+6.3f})  loc({lx:+6.3f},{ly:+6.3f})  3Doff({lx:+.3f},{-ly:+.3f})"
        )
        if mx > 0.45:
            for r in sorted(rows, reverse=True)[:4]:
                print(
                    f"    pad{r[1]:>4s} err={r[0]:.3f} pad=({r[2]:.2f},{r[3]:.2f}) "
                    f"pin=({r[4]:.2f},{r[5]:.2f})"
                )


if __name__ == "__main__":
    main()
