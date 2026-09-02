#!/usr/bin/env python3
"""Remove antenna tracks (and the duplicates that hide them) from a board.

Why this is not done with pcbnew: after ExportSpecctraDSN/ImportSpecctraSES
have run, this KiCad build hands back board objects whose Python proxy has lost
its BOARD type, so the connectivity calls raise AttributeError. Even in a clean
interpreter, ``TestTrackEndpointDangling`` misses FreeRouting's usual leftover
-- a via with a short leg on each layer running to the same free point -- which
KiCad's own DRC then reports as two dangling ends. So the sweep is done here,
geometrically, on the board file.

An endpoint is supported when, on its own layer, another segment of the same
net touches or crosses it, a via of that net sits on it, or a pad of that net
covers it. Segments with an unsupported end are antennas: they carry no
current, they radiate, and they are what the [track_dangling] rule flags.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from pcb_parse import NetTable, pad_net

TOL = 0.002  # mm; KiCad stores nanometres, so endpoints that meet meet exactly


def _fmt(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s or "0"


def _blocks(text: str, kind: str):
    """Yield whole top-level ``(kind ...)`` s-expressions.

    A non-greedy regex is not enough: nested elements close at the same indent
    in places, so a pattern that stops at the first ``\\n\\t)`` swallowed pairs
    of footprints and lost half the pads -- which made every track terminating
    on one of those pads look like an antenna.
    """
    for m in re.finditer(r"\n\t\(%s[\s\"(]" % kind, text):
        i = m.start() + 1
        depth = 0
        j = i
        while j < len(text):
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield text[i:j + 1], i, j + 1


def _pads(text: str, table: NetTable):
    """(net, x, y, radius, layers) for every pad, in board coordinates."""
    out = []
    for blk, _a, _b in _blocks(text, "footprint"):
        at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        th = math.radians(float(at.group(3) or 0))
        # KiCad rotates footprint-local pad coordinates counter-clockwise while
        # y grows downward, so the sine terms flip sign against the usual form.
        # The last pad of a footprint has no following "(pad" to stop at, so the
        # lookahead has to accept the end of the block too -- otherwise one pad
        # per footprint goes missing and the tracks landing on it look dangling.
        for pm in re.finditer(r'\(pad "[^"]*"[\s\S]*?(?=\n\t\t\(pad |\Z)', blk):
            chunk = pm.group(0)
            lm = re.search(r"\(at ([-\d.]+) ([-\d.]+)", chunk)
            sm = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", chunk)
            if not lm or not sm:
                continue
            nid, name = pad_net(chunk, table)
            if not name:
                continue
            lx, ly = float(lm.group(1)), float(lm.group(2))
            px = fx + lx * math.cos(th) - ly * math.sin(th)
            py = fy + lx * math.sin(th) + ly * math.cos(th)
            r = max(float(sm.group(1)), float(sm.group(2))) / 2 + 0.05
            lay = "*" if '"*.Cu"' in chunk else ("F.Cu" if '"F.Cu"' in chunk else "B.Cu")
            out.append((name, px, py, r, lay))
    return out


def _on_segment(px, py, x1, y1, x2, y2) -> bool:
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(px - x1, py - y1) <= TOL
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    if t < -TOL or t > 1 + TOL:
        return False
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy)) <= TOL


def clean(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    table = NetTable(text)
    pads = _pads(text, table)

    segs = []
    for blk, a, b in _blocks(text, "segment"):
        st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
        en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
        lay = re.search(r'\(layer "([^"]+)"\)', blk)
        net = re.search(r'\(net (?:(\d+)|"([^"]*)")\s*\)', blk)
        if not (st and en and lay and net):
            continue
        segs.append({
            "span": (a, b), "layer": lay.group(1), "net": table.resolve(net)[1],
            "p": (float(st.group(1)), float(st.group(2))),
            "q": (float(en.group(1)), float(en.group(2))),
        })

    vias = []
    for blk, _a, _b in _blocks(text, "via"):
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", blk)
        net = re.search(r'\(net (?:(\d+)|"([^"]*)")\s*\)', blk)
        if at and net:
            vias.append((table.resolve(net)[1], float(at.group(1)), float(at.group(2))))

    # Redundant copper first: the SES merge lands the same run several times,
    # sometimes as an exact copy (forwards or backwards) and sometimes as a
    # short piece lying inside a longer one. Both defeat the antenna sweep
    # below -- a doubled stub sees its own copy on its free end -- and the
    # contained piece is what KiCad reports as a dangling end, because its far
    # end stops in the middle of the track it sits on instead of at a junction.
    # Keep the longest of each overlapping set.
    order = sorted(range(len(segs)),
                   key=lambda i: -math.dist(segs[i]["p"], segs[i]["q"]))
    kept, drop = [], set()
    for i in order:
        s = segs[i]
        for j in kept:
            o = segs[j]
            if o["net"] != s["net"] or o["layer"] != s["layer"]:
                continue
            if _on_segment(*s["p"], *o["p"], *o["q"]) and \
                    _on_segment(*s["q"], *o["p"], *o["q"]):
                drop.add(i)
                break
        else:
            kept.append(i)
    dups = len(drop)

    stubs = 0
    while True:
        live = [i for i in range(len(segs)) if i not in drop]

        def supported(idx, pt) -> bool:
            s = segs[idx]
            for name, vx, vy, in ((n, x, y) for n, x, y in vias):
                if name == s["net"] and math.hypot(pt[0] - vx, pt[1] - vy) <= TOL:
                    return True
            for name, px, py, r, lay in pads:
                if name == s["net"] and lay in ("*", s["layer"]) \
                        and math.hypot(pt[0] - px, pt[1] - py) <= r:
                    return True
            for j in live:
                if j == idx:
                    continue
                o = segs[j]
                if o["net"] != s["net"] or o["layer"] != s["layer"]:
                    continue
                if _on_segment(pt[0], pt[1], o["p"][0], o["p"][1], o["q"][0], o["q"][1]):
                    return True
            return False

        doomed = [i for i in live
                  if not supported(i, segs[i]["p"]) or not supported(i, segs[i]["q"])]
        if not doomed:
            break
        drop.update(doomed)
        stubs += len(doomed)

    if drop:
        out, last = [], 0
        for i in sorted(drop, key=lambda k: segs[k]["span"][0]):
            a, b = segs[i]["span"]
            out.append(text[last:a])
            last = b
        out.append(text[last:])
        path.write_text("".join(out), encoding="utf-8")
    return dups, stubs


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]] or [Path(__file__).with_name("esp32_baseboard.kicad_pcb")]
    total = 0
    for p in paths:
        dups, stubs = clean(p)
        total += dups + stubs
        print(f"{p.name}: {dups} duplicate segment(s), {stubs} antenna(s) removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
