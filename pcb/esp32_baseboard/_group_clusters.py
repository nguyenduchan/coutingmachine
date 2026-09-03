#!/usr/bin/env python3
"""Wrap each assembly cluster (POWER, MCU, TMC, OPTO, HMI, BUP, BLOWER, SHIFT,
A1-3) into a KiCad (group ...) so the user can select-and-drag / rotate a
whole module in one go, instead of hand-picking every footprint + label.

Membership = spatial: the cluster's own Eco1.User outline box (already drawn
by gen_power_carrier.py's cluster_outline()) tells us the true bounding
region: any footprint whose anchor, or any gr_text whose anchor, falls
inside that box belongs to the cluster. This needs no hardcoded reference
list (which would drift out of sync with the generator) and no textual
pairing between box and label (the two are emitted from different passes
and are not adjacent in the file, verified empirically).
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

PCB = Path(__file__).with_name("esp32_baseboard.kicad_pcb")

# Reference anchor (box x0,y0) for each cluster, used only to name a box
# found by position -- not used for membership itself.
CLUSTER_REF = {
    "POWER": (45.3, 87.3), "TMC": (49.6, 46.6), "A1": (72.8, 145.1),
    "MCU": (92.8, 69.8), "BUP": (93.3, 40.3), "A2": (106.8, 145.1),
    "OPTO": (132.8, 41.8), "A3": (140.8, 145.1), "HMI": (157.3, 42.8),
    "SHIFT": (175.3, 71.0), "BLOWER": (180.3, 41.3),
}


def uid() -> str:
    return str(uuid.uuid4())


def blocks(text: str, tag: str) -> list[tuple[int, int, str]]:
    out = []
    for m in re.finditer(r"\n\t\(" + tag + r"\b", text):
        st = m.start() + 1
        d = 0
        i = st
        while True:
            c = text[i]
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            i += 1
        out.append((st, i + 1, text[st : i + 1]))
    return out


def main() -> None:
    text = PCB.read_text(encoding="utf-8")
    if "(group " in text:
        raise SystemExit("groups already present -- run only once")

    # 1) Locate the 11 Eco1/Eco2 cluster outline boxes, name them by nearest
    #    known reference corner.
    boxes: dict[str, tuple[float, float, float, float, str]] = {}
    for st, en, blk in blocks(text, "gr_rect"):
        lm = re.search(r'\(layer "(Eco[12]\.User)"\)', blk)
        if not lm:
            continue
        s = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", blk)
        e = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", blk)
        um = re.search(r'\(uuid "([^"]+)"\)', blk)
        x0, y0 = float(s.group(1)), float(s.group(2))
        x1, y1 = float(e.group(1)), float(e.group(2))
        name = min(CLUSTER_REF, key=lambda k: (CLUSTER_REF[k][0] - x0) ** 2 + (CLUSTER_REF[k][1] - y0) ** 2)
        boxes[name] = (x0, y0, x1, y1, um.group(1))

    print(f"found {len(boxes)} cluster boxes: {sorted(boxes)}")

    def inside(name: str, x: float, y: float) -> bool:
        x0, y0, x1, y1, _ = boxes[name]
        return x0 <= x <= x1 and y0 <= y <= y1

    members: dict[str, list[str]] = {k: [v[4]] for k, v in boxes.items()}  # seed with the box itself

    # 2) Footprints
    for st, en, blk in blocks(text, "footprint"):
        at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", blk)
        um = re.search(r'\(uuid "([^"]+)"\)', blk)
        if not at or not um:
            continue
        x, y = float(at.group(1)), float(at.group(2))
        for name in boxes:
            if inside(name, x, y):
                members[name].append(um.group(1))
                break

    # 3) Free graphics (gr_text / gr_line / gr_rect other than the outline
    #    boxes themselves) belonging to a cluster's footprint.
    outline_uuids = {v[4] for v in boxes.values()}
    for tag in ("gr_text", "gr_line", "gr_rect", "gr_circle", "gr_poly"):
        for st, en, blk in blocks(text, tag):
            um = re.search(r'\(uuid "([^"]+)"\)', blk)
            if not um or um.group(1) in outline_uuids:
                continue
            if 'layer "Edge.Cuts"' in blk:
                continue
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
            if at:
                x, y = float(at.group(1)), float(at.group(2))
            else:
                s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
                e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
                if not (s and e):
                    continue
                x = (float(s.group(1)) + float(e.group(1))) / 2
                y = (float(s.group(2)) + float(e.group(2))) / 2
            for name in boxes:
                if inside(name, x, y):
                    members[name].append(um.group(1))
                    break

    # 4) Emit (group ...) blocks
    lines = []
    for name, ids in members.items():
        lines.append("\t(group " + f'"{name}"')
        lines.append(f'\t\t(uuid "{uid()}")')
        lines.append("\t\t(members")
        for mid in ids:
            lines.append(f'\t\t\t"{mid}"')
        lines.append("\t\t)")
        lines.append("\t)")
        print(f"  {name:8s} {len(ids):3d} member(s)")

    block = "\n" + "\n".join(lines) + "\n"
    idx = text.rstrip().rfind(")")
    text = text[:idx] + block + text[idx:]
    PCB.write_text(text, encoding="utf-8")
    print(f"wrote -> {PCB}")


if __name__ == "__main__":
    main()
