"""Measure 3D socket pins vs PCB THT holes from a KiCad GLB export."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "out" / "sockets_pads.glb"
PCB = ROOT / "esp32_baseboard.kicad_pcb"
PNG = ROOT / "out" / "pin_vs_hole.png"
REFS = {
    "U3",
    "U4",
    "U_PWR1",
    "U_PWR2",
    "U_VIB",
    "J_KEY",
    "J14",
    "J_DISP",
    "J1",
    "J_MOT1",
}


def extract_fps(text: str) -> list[str]:
    blocks: list[str] = []
    i = 0
    token = "(footprint "
    while True:
        p = text.find(token, i)
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


def parse_at(s: str) -> tuple[float, float, float] | None:
    m = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?", s)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)


def pcb_tht_pads() -> list[tuple[str, str, float, float]]:
    text = PCB.read_text(encoding="utf-8")
    out: list[tuple[str, str, float, float]] = []
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
            r'\(pad "([^"]+)" thru_hole[\s\S]*?\(at\s+([-\d.]+)\s+([-\d.]+)',
            fp,
        ):
            px, py = float(m.group(2)), float(m.group(3))
            wx = fx + px * c - py * s
            wy = fy + px * s + py * c
            out.append((ref, m.group(1), wx, wy))
    return out


def cat(name: str) -> str:
    n = name.upper()
    if "PAD" in n:
        return "PAD"
    if "PINSOCKET" in n:
        return "SOCK"
    if "JST" in n:
        return "JST"
    if "TERMINAL" in n:
        return "TERM"
    return "OTHER"


def uniq_xy(pts: np.ndarray, tol: float = 0.35) -> np.ndarray:
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


def main() -> None:
    import sys

    glb = Path(sys.argv[1]) if len(sys.argv) > 1 else GLB
    png = Path(sys.argv[2]) if len(sys.argv) > 2 else PNG
    scene = trimesh.load(str(glb), force="scene")
    below: dict[str, list[np.ndarray]] = defaultdict(list)
    for node in scene.graph.nodes_geometry:
        T, geom_name = scene.graph.get(node)
        mesh = scene.geometry[geom_name]
        pts = trimesh.transform_points(mesh.vertices, T) * 1000.0
        c = cat(geom_name)
        if c not in ("SOCK", "JST", "TERM"):
            continue
        sel = pts[pts[:, 1] < -0.15]
        if len(sel):
            below[c].append(sel)

    pins: dict[str, np.ndarray] = {}
    for k, arrs in below.items():
        xy = np.vstack(arrs)[:, [0, 2]]
        pins[k] = uniq_xy(xy, 0.4)
        print(k, "below-board clusters", len(pins[k]))

    pads = pcb_tht_pads()
    print("pcb THT pads", len(pads), dict(defaultdict(int, {r: 0 for r in REFS})))
    byref: dict[str, int] = defaultdict(int)
    for r, *_ in pads:
        byref[r] += 1
    print(dict(byref))

    pcb_xy = np.array([(p[2], p[3]) for p in pads])
    all_pins = np.vstack([v for v in pins.values() if len(v)]) if pins else np.zeros((0, 2))

    print("\nPCB pad -> nearest 3D pin tip:")
    rows_by_ref: dict[str, list] = defaultdict(list)
    for ref, pn, wx, wy in pads:
        d = np.hypot(all_pins[:, 0] - wx, all_pins[:, 1] - wy)
        j = int(np.argmin(d))
        rows_by_ref[ref].append(
            (float(d[j]), pn, wx, wy, float(all_pins[j, 0]), float(all_pins[j, 1]))
        )
    for ref, rows in rows_by_ref.items():
        mx = max(r[0] for r in rows)
        med = float(np.median([r[0] for r in rows]))
        nbad = sum(1 for r in rows if r[0] > 0.5)
        print(f"  {ref:8s} n={len(rows):2d} max={mx:.3f} med={med:.3f} n>0.5={nbad}")
        if mx > 0.5:
            for r in sorted(rows, reverse=True)[:6]:
                print(
                    f"     pad{r[1]:>4s} err={r[0]:.3f} pad=({r[2]:.2f},{r[3]:.2f}) "
                    f"pin=({r[4]:.2f},{r[5]:.2f}) dxy=({r[4]-r[2]:+.2f},{r[5]-r[3]:+.2f})"
                )

    # Top-down overlay: pads red rings, pins cyan/yellow/green
    xs = np.concatenate([pcb_xy[:, 0], all_pins[:, 0]])
    ys = np.concatenate([pcb_xy[:, 1], all_pins[:, 1]])
    mrg = 10.0
    x0, x1 = float(xs.min()) - mrg, float(xs.max()) + mrg
    y0, y1 = float(ys.min()) - mrg, float(ys.max()) + mrg
    scale = 10.0
    W, H = int((x1 - x0) * scale) + 1, int((y1 - y0) * scale) + 1
    img = Image.new("RGB", (W, H), (18, 20, 26))
    dr = ImageDraw.Draw(img)

    def xy(x: float, y: float) -> tuple[int, int]:
        return int((x - x0) * scale), int((y1 - y) * scale)

    for _ref, _pn, wx, wy in pads:
        c = xy(wx, wy)
        r = int(0.85 * scale)
        dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(230, 70, 70), width=2)

    colors = {"SOCK": (70, 220, 255), "JST": (255, 210, 50), "TERM": (90, 220, 110)}
    for k, arr in pins.items():
        col = colors[k]
        for p in arr:
            c = xy(float(p[0]), float(p[1]))
            r = int(0.32 * scale)
            dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)
            d = np.hypot(pcb_xy[:, 0] - p[0], pcb_xy[:, 1] - p[1])
            j = int(np.argmin(d))
            if d[j] > 0.5:
                dr.line([c, xy(pcb_xy[j, 0], pcb_xy[j, 1])], fill=(255, 90, 90), width=2)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    legend = "red=PCB hole  cyan=PinSocket pin  yellow=JST pin  green=terminal  line=offset>0.5mm"
    dr.text((12, 8), legend, fill=(220, 220, 220), font=font)
    img.save(png)
    print("wrote", png, img.size)


if __name__ == "__main__":
    main()
