#!/usr/bin/env python3
"""Align the A1/A2/A3 (HOME+ULN2003) module groups: same top edge (y0),
even horizontal gaps, outer edges (A3 left, A2 right) kept fixed as anchors.
Translation only -- no rotation change, no resizing.
"""
from __future__ import annotations

import re
from pathlib import Path

PCB = Path("esp32_baseboard.kicad_pcb")


def blocks(text: str, tag: str) -> list[tuple[int, int, str]]:
    out = []
    for m in re.finditer(r"\n\t\(" + tag + r"\b", text):
        st = m.start(); d = 0; i = st + 1
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

    groups: dict[str, set[str]] = {}
    for st, en, blk in blocks(text, "group"):
        name = re.search(r'\(group "([^"]+)"', blk).group(1)
        mem_block = re.search(r"\(members([\s\S]*?)\)\s*\)\s*$", blk)
        members = set(re.findall(r'"([0-9a-f-]{36})"', mem_block.group(1))) if mem_block else set()
        groups[name] = members

    box_uuids = {
        "A3": "be7d1a98-6d8d-42cb-923d-4dacd6dfa306",
        "A1": "b6ff0713-e1f0-49c0-8d08-ef5c672a97b0",
        "A2": "c6112ff1-ecec-496a-b74c-85c486b58c9c",
    }
    rects = {}
    for st, en, blk in blocks(text, "gr_rect"):
        um = re.search(r'\(uuid "([^"]+)"\)', blk)
        s = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", blk)
        e = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", blk)
        if um:
            rects[um.group(1)] = (float(s.group(1)), float(s.group(2)), float(e.group(1)), float(e.group(2)))

    boxes = {name: rects[u] for name, u in box_uuids.items()}
    for name, (x0, y0, x1, y1) in boxes.items():
        print(f"{name}: before ({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f})")

    # Target layout: common y0, even x-gaps, A3 left edge & A2 right edge fixed.
    y_target = boxes["A1"][1]  # 140.10, current median
    x0_a3 = boxes["A3"][0]
    x1_a2 = boxes["A2"][2]
    w1 = boxes["A3"][2] - boxes["A3"][0]
    w2 = boxes["A1"][2] - boxes["A1"][0]
    w3 = boxes["A2"][2] - boxes["A2"][0]
    total_w = w1 + w2 + w3
    gap = (x1_a2 - x0_a3 - total_w) / 2.0
    target_x0 = {
        "A3": x0_a3,
        "A1": x0_a3 + w1 + gap,
        "A2": x0_a3 + w1 + gap + w2 + gap,
    }

    deltas = {}
    for name, (x0, y0, x1, y1) in boxes.items():
        dx = target_x0[name] - x0
        dy = y_target - y0
        deltas[name] = (dx, dy)
        print(f"{name}: delta ({dx:+.3f},{dy:+.3f})")

    # Collect all shiftable items (footprint / gr_text / gr_rect / gr_line /
    # gr_circle / gr_arc / gr_poly) keyed by uuid, with their (start,end) span.
    all_items: dict[str, tuple[int, int, str, str]] = {}  # uuid -> (st,en,tag,block)
    for tag in ("footprint", "gr_text", "gr_rect", "gr_line", "gr_circle", "gr_arc", "gr_poly"):
        for st, en, blk in blocks(text, tag):
            if tag == "footprint":
                um = re.search(r"\n\t\t\(uuid \"([^\"]+)\"\)", blk)
            else:
                um = re.search(r'\(uuid "([^"]+)"\)', blk)
            if not um:
                continue
            all_items[um.group(1)] = (st, en, tag, blk)

    edits = []  # (st, en, new_blk)
    for name, member_uuids in groups.items():
        if name not in deltas:
            continue
        dx, dy = deltas[name]
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            continue
        for u in member_uuids:
            if u not in all_items:
                continue
            st, en, tag, blk = all_items[u]
            new_blk = blk
            if tag == "footprint":
                m = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", blk)
                x, y = float(m.group(1)), float(m.group(2))
                new_blk = blk[: m.start()] + f"\n\t\t(at {x+dx:.4f} {y+dy:.4f}{m.group(3)})" + blk[m.end():]
            elif tag == "gr_text":
                m = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", blk)
                x, y = float(m.group(1)), float(m.group(2))
                new_blk = blk[: m.start()] + f"\n\t\t(at {x+dx:.4f} {y+dy:.4f}{m.group(3)})" + blk[m.end():]
            elif tag in ("gr_rect", "gr_line"):
                for key in ("start", "end"):
                    mm = re.search(r"\(" + key + r" ([-\d.]+) ([-\d.]+)\)", new_blk)
                    x, y = float(mm.group(1)), float(mm.group(2))
                    new_blk = new_blk[: mm.start()] + f"({key} {x+dx:.4f} {y+dy:.4f})" + new_blk[mm.end():]
            elif tag == "gr_circle":
                for key in ("center", "end"):
                    mm = re.search(r"\(" + key + r" ([-\d.]+) ([-\d.]+)\)", new_blk)
                    if not mm:
                        continue
                    x, y = float(mm.group(1)), float(mm.group(2))
                    new_blk = new_blk[: mm.start()] + f"({key} {x+dx:.4f} {y+dy:.4f})" + new_blk[mm.end():]
            elif tag == "gr_arc":
                for key in ("start", "mid", "end"):
                    mm = re.search(r"\(" + key + r" ([-\d.]+) ([-\d.]+)\)", new_blk)
                    if not mm:
                        continue
                    x, y = float(mm.group(1)), float(mm.group(2))
                    new_blk = new_blk[: mm.start()] + f"({key} {x+dx:.4f} {y+dy:.4f})" + new_blk[mm.end():]
            elif tag == "gr_poly":
                def _shift_xy(mm):
                    x, y = float(mm.group(1)), float(mm.group(2))
                    return f"(xy {x+dx:.4f} {y+dy:.4f})"
                new_blk = re.sub(r"\(xy ([-\d.]+) ([-\d.]+)\)", _shift_xy, new_blk)
            edits.append((st, en, new_blk))

    print(f"shifting {len(edits)} items")
    edits.sort(reverse=True)
    for st, en, new_blk in edits:
        text = text[:st] + new_blk + text[en:]

    PCB.write_text(text, encoding="utf-8")
    print(f"wrote -> {PCB}")


if __name__ == "__main__":
    main()
