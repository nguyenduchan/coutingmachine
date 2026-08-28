"""2-layer grid A* maze autorouter for the ESP32 carrier PCB.

User policy:
  - Traces may meander on F.Cu and B.Cu freely (H+V on either face).
  - NO extra drill holes: never emit routing vias. Layer change only at
    existing thru-hole pads (headers / modules) which already pierce both faces.
"""

from __future__ import annotations

import heapq
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterable


LAYERS = ("F.Cu", "B.Cu")
LAYER_F = 0
LAYER_B = 1
BLOCKED = -1  # module keepout zones (not net copper)

# Match _check_signal_routing.py
HOLE_EXTRA_MM = 0.25
TRACE_CLEARANCE_MM = 0.20
DEFAULT_HALF_TRACK = 0.15
MAZE_CLEARANCE_MM = 0.14

POWER_NET_NAMES = frozenset(
    {
        "GND",
        "+5V",
        "+3V3",
        "+12V",
        "+12V_RAW",
        "+12V_SNS",
        "/OPTO_VCC_I",
    }
)


@dataclass
class Pad:
    x: float
    y: float
    net: int
    name: str
    radius: float = 0.95
    ref: str = ""
    drill: float = 1.0


@dataclass
class Seg:
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str
    net: int
    width: float


@dataclass
class Via:
    x: float
    y: float
    net: int
    drill: float = 0.4
    size: float = 0.8


@dataclass
class RouteResult:
    segments: list[Seg] = field(default_factory=list)
    vias: list[Via] = field(default_factory=list)  # always empty
    failed: list[tuple[int, str, tuple[float, float], tuple[float, float]]] = field(
        default_factory=list
    )


def _rot_xy(lx: float, ly: float, rot_deg: float) -> tuple[float, float]:
    r = math.radians(rot_deg % 360.0)
    c, s = math.cos(r), math.sin(r)
    return lx * c - ly * s, lx * s + ly * c


def is_power_net(name: str) -> bool:
    return name in POWER_NET_NAMES or name.startswith("+")


def keepout_radius(drill: float) -> float:
    return drill * 0.5 + HOLE_EXTRA_MM + TRACE_CLEARANCE_MM + DEFAULT_HALF_TRACK


def parse_hole_sites(pcb_text: str) -> list[tuple[float, float, float, int]]:
    """Drill centers (x, y, drill_mm, net) for foreign-hole checks (A7)."""
    sites: list[tuple[float, float, float, int]] = []
    for block in re.split(r"(?=\t\(footprint )", pcb_text):
        if "(footprint " not in block[:40] and "\t(footprint " not in block:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", block)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = math.radians(float(at.group(3) or 0))
        c, s = math.cos(rot), math.sin(rot)
        for pm in re.finditer(
            r'\(pad\s+"[^"]*"\s+(?:thru_hole|np_thru_hole)\s+\w+'
            r"[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+[\d.-]+)?\)"
            r"[\s\S]*?\(size\s+([\d.-]+)\s+([\d.-]+)\)"
            r"[\s\S]*?\(drill\s+([\d.-]+)\)",
            block,
        ):
            lx, ly = float(pm.group(1)), float(pm.group(2))
            sx, sy = float(pm.group(3)), float(pm.group(4))
            drill = float(pm.group(5))
            chunk = pm.group(0)
            nm = re.search(r'\(net\s+(\d+)\s+"', chunk)
            net = int(nm.group(1)) if nm else 0
            wx = fx + lx * c - ly * s
            wy = fy + lx * s + ly * c
            d = drill if drill > 0.05 else max(sx, sy) * 0.55
            sites.append((wx, wy, d, net))
    return sites


def parse_keepout_holes(pcb_text: str) -> list[tuple[float, float, float]]:
    """Legacy wrapper — radii for external tools."""
    return [(x, y, keepout_radius(d)) for x, y, d, _ in parse_hole_sites(pcb_text)]


def parse_pads(pcb_text: str) -> list[Pad]:
    pads: list[Pad] = []
    chunks = re.split(r"(?=\n\t\(footprint )", pcb_text)
    for part in chunks:
        if "(footprint " not in part[:40] and not part.lstrip().startswith("(footprint"):
            if "\t(footprint " not in part:
                continue
        am = re.search(
            r"\(footprint\s+\"[^\"]+\"[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)",
            part,
        )
        if not am:
            continue
        fx, fy = float(am.group(1)), float(am.group(2))
        frot = float(am.group(3) or 0.0)
        rm = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', part)
        ref = rm.group(1) if rm else ""
        for pm in re.finditer(
            r"\(pad\s+\"[^\"]*\"\s+\w+\s+\w+\s*"
            r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)\s*"
            r"\(size\s+([\d.-]+)\s+([\d.-]+)\)"
            r"[\s\S]*?"
            r"\(net\s+(\d+)\s+\"([^\"]*)\"\)",
            part,
        ):
            lx, ly = float(pm.group(1)), float(pm.group(2))
            sx, sy = float(pm.group(4)), float(pm.group(5))
            net = int(pm.group(6))
            nname = pm.group(7)
            if net <= 0:
                continue
            chunk = pm.group(0)
            dm = re.search(r"\(drill\s+([\d.-]+)\)", chunk)
            drill = float(dm.group(1)) if dm else max(sx, sy) * 0.55
            wx, wy = _rot_xy(lx, ly, frot)
            rad = 0.45 * max(sx, sy)
            pads.append(Pad(fx + wx, fy + wy, net, nname, rad, ref=ref, drill=drill))
    return pads


def strip_routes(pcb_text: str) -> str:
    """Remove all segments and ALL vias (no holes beyond component pins)."""
    text = re.sub(r"\n\t\(segment\b[\s\S]*?\n\t\)", "", pcb_text)
    text = re.sub(r"\n\t\(via\b[\s\S]*?\n\t\)", "", text)
    return text


def parse_kept_vias(pcb_text: str) -> list[tuple[float, float, int, float]]:
    return []


class MazeRouter:
    def __init__(
        self,
        x0: float,
        y0: float,
        width: float,
        height: float,
        grid: float = 0.55,
        clearance: float = MAZE_CLEARANCE_MM,
    ):
        self.x0 = x0
        self.y0 = y0
        self.grid = grid
        self.clearance = clearance
        self.nx = max(2, int(math.ceil(width / grid)) + 1)
        self.ny = max(2, int(math.ceil(height / grid)) + 1)
        self.occ: list[dict[int, int]] = [{}, {}]
        self.hole_sites: list[tuple[float, float, float, int]] = []

    def _key(self, ix: int, iy: int) -> int:
        return ix * self.ny + iy

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        ix = int(round((x - self.x0) / self.grid))
        iy = int(round((y - self.y0) / self.grid))
        return max(0, min(self.nx - 1, ix)), max(0, min(self.ny - 1, iy))

    def _xy(self, ix: int, iy: int) -> tuple[float, float]:
        return self.x0 + ix * self.grid, self.y0 + iy * self.grid

    def _get(self, layer: int, ix: int, iy: int) -> int:
        return self.occ[layer].get(self._key(ix, iy), 0)

    def _set(self, layer: int, ix: int, iy: int, net: int) -> None:
        self.occ[layer][self._key(ix, iy)] = net

    def _mark_disk(
        self, layer: int, x: float, y: float, radius: float, net: int, extra: float = 0.12
    ) -> None:
        r = radius + self.clearance + extra
        ix0, iy0 = self._cell(x - r, y - r)
        ix1, iy1 = self._cell(x + r, y + r)
        r2 = r * r
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                cx, cy = self._xy(ix, iy)
                if (cx - x) ** 2 + (cy - y) ** 2 > r2:
                    continue
                cur = self._get(layer, ix, iy)
                if cur == 0 or cur == net:
                    self._set(layer, ix, iy, net)

    def add_rect_keepout(self, x_min: float, y_min: float, x_max: float, y_max: float) -> None:
        ix0, iy0 = self._cell(x_min, y_min)
        ix1, iy1 = self._cell(x_max, y_max)
        for li in (0, 1):
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    if self._get(li, ix, iy) == 0:
                        self._set(li, ix, iy, BLOCKED)

    def add_hole_sites(self, sites: list[tuple[float, float, float, int]]) -> None:
        self.hole_sites.extend(sites)

    def _foreign_hole_blocks(self, cx: float, cy: float, net: int, half_w: float = 0.0) -> bool:
        for hx, hy, drill, hnet in self.hole_sites:
            if hnet == net and hnet != 0:
                continue
            kr = keepout_radius(drill) + half_w
            if (cx - hx) ** 2 + (cy - hy) ** 2 < kr * kr:
                return True
        return False

    def add_pad(self, pad: Pad) -> None:
        # Thru-hole: both layers owned by net (natural layer bridge at pin)
        for li in (0, 1):
            self._mark_disk(li, pad.x, pad.y, pad.radius, pad.net, extra=0.02)

    def add_existing_via(self, x: float, y: float, net: int, size: float = 0.9) -> None:
        return  # unused — no vias

    def _mark_seg(
        self, layer: int, x1: float, y1: float, x2: float, y2: float, half_w: float, net: int
    ) -> None:
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            self._mark_disk(layer, x1, y1, half_w, net, extra=0.04)
            return
        steps = max(1, int(math.ceil(length / (self.grid * 0.4))))
        for i in range(steps + 1):
            t = i / steps
            self._mark_disk(layer, x1 + t * dx, y1 + t * dy, half_w, net, extra=0.04)

    def _passable(self, layer: int, ix: int, iy: int, net: int, half_w: float = 0.0) -> bool:
        if not (0 <= ix < self.nx and 0 <= iy < self.ny):
            return False
        cur = self._get(layer, ix, iy)
        if cur == BLOCKED:
            return False
        return cur == 0 or cur == net

    def _escape_points(
        self, x: float, y: float, net: int, layer: int, span: int = 8
    ) -> list[tuple[int, int, int]]:
        ix, iy = self._cell(x, y)
        out: list[tuple[int, int, int]] = [(ix, iy, layer)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for k in range(1, span + 1):
                nx_, ny_ = ix + dx * k, iy + dy * k
                if not self._passable(layer, nx_, ny_, net):
                    break
                out.append((nx_, ny_, layer))
        return out

    def snapshot(self) -> list[dict[int, int]]:
        return [dict(d) for d in self.occ]

    def restore(self, snap: list[dict[int, int]]) -> None:
        self.occ = [dict(d) for d in snap]

    def _can_pin_hop(self, ix: int, iy: int, net: int) -> bool:
        """Layer change only where both faces already belong to this net (thru-hole pad)."""
        return self._get(0, ix, iy) == net and self._get(1, ix, iy) == net

    def flood_component(
        self, seeds: list[tuple[float, float]], net: int
    ) -> set[tuple[int, int, int]]:
        """Cells reachable staying on this net's copper (pin hops OK)."""
        q: deque[tuple[int, int, int]] = deque()
        seen: set[tuple[int, int, int]] = set()
        for x, y in seeds:
            ix, iy = self._cell(x, y)
            for ly in (0, 1):
                if self._get(ly, ix, iy) == net:
                    s = (ix, iy, ly)
                    if s not in seen:
                        seen.add(s)
                        q.append(s)
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        while q:
            ix, iy, ly = q.popleft()
            for dx, dy in dirs:
                nx_, ny_ = ix + dx, iy + dy
                if not (0 <= nx_ < self.nx and 0 <= ny_ < self.ny):
                    continue
                if self._get(ly, nx_, ny_) != net:
                    continue
                nxt = (nx_, ny_, ly)
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
            if self._can_pin_hop(ix, iy, net):
                nxt = (ix, iy, 1 - ly)
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return seen

    def find_path_to_cells(
        self,
        x1: float,
        y1: float,
        net: int,
        width: float,
        goals: set[tuple[int, int, int]],
        prefer_layer: int = LAYER_B,
        both_layers: bool = True,
        end_xy: tuple[float, float] | None = None,
    ) -> tuple[list[Seg], list[Via]] | None:
        """A* from a point until any goal cell (existing net copper)."""
        if not goals:
            return None
        layers = (prefer_layer,) if not both_layers else (LAYER_F, LAYER_B)
        for ly in layers:
            self._set(ly, *self._cell(x1, y1), net)

        starts: list[tuple[int, int, int]] = []
        for ly in layers:
            starts.extend(self._escape_points(x1, y1, net, ly))
        goal_xy = {(gx, gy) for gx, gy, _ in goals}
        # Precompute a small set of goal anchors for the heuristic
        anchors: list[tuple[int, int]] = []
        for gx, gy in goal_xy:
            anchors.append((gx, gy))
            if len(anchors) >= 64:
                break

        def heur(ix: int, iy: int, _ly: int) -> float:
            if not anchors:
                return 0.0
            return min(abs(ix - gx) + abs(iy - gy) for gx, gy in anchors)

        open_h: list[tuple[float, int, tuple[int, int, int]]] = []
        seq = 0
        came: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
        gscore: dict[tuple[int, int, int], float] = {}
        for s in starts:
            if s in goals:
                continue  # already on target copper — skip trivial
            came[s] = None
            gscore[s] = 0.0
            heapq.heappush(open_h, (heur(*s), seq, s))
            seq += 1
        if not open_h:
            return None

        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        found = None
        max_expand = min(self.nx * self.ny * (4 if both_layers else 3), 18000)
        expands = 0
        while open_h and expands < max_expand:
            expands += 1
            _, _, cur = heapq.heappop(open_h)
            if cur in goals or (cur[0], cur[1]) in goal_xy:
                found = cur
                break
            ix, iy, ly = cur
            prev = came[cur]
            for dx, dy in dirs:
                nx_, ny_ = ix + dx, iy + dy
                if not self._passable(ly, nx_, ny_, net):
                    continue
                turn = 0.0
                if prev is not None and prev[2] == ly:
                    pdx, pdy = ix - prev[0], iy - prev[1]
                    if (pdx, pdy) != (dx, dy):
                        turn = 0.12
                nxt = (nx_, ny_, ly)
                ng = gscore[cur] + 1.0 + turn
                if ng < gscore.get(nxt, 1e18):
                    gscore[nxt] = ng
                    came[nxt] = cur
                    seq += 1
                    heapq.heappush(open_h, (ng + heur(nx_, ny_, ly), seq, nxt))
            if both_layers and self._can_pin_hop(ix, iy, net):
                other = 1 - ly
                nxt = (ix, iy, other)
                ng = gscore[cur] + 0.35
                if ng < gscore.get(nxt, 1e18):
                    gscore[nxt] = ng
                    came[nxt] = cur
                    seq += 1
                    heapq.heappush(open_h, (ng + heur(ix, iy, other), seq, nxt))

        if found is None:
            return None

        path: list[tuple[int, int, int]] = []
        cur2: tuple[int, int, int] | None = found
        while cur2 is not None:
            path.append(cur2)
            cur2 = came[cur2]
        path.reverse()
        if end_xy is not None:
            x2, y2 = end_xy
        else:
            x2, y2 = self._xy(found[0], found[1])
        return self._path_to_geometry(path, x1, y1, x2, y2, net, width)

    def find_path(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        net: int,
        width: float,
        prefer_layer: int = LAYER_B,
        allow_via: bool = False,  # ignored — never emit vias
        both_layers: bool = True,
    ) -> tuple[list[Seg], list[Via]] | None:
        """A* on F/B. Layer hops only at existing thru-hole pads (no new drills)."""
        layers = (prefer_layer,) if not both_layers else (LAYER_F, LAYER_B)
        for ly in layers:
            self._set(ly, *self._cell(x1, y1), net)
            self._set(ly, *self._cell(x2, y2), net)

        goals: set[tuple[int, int, int]] = set()
        for ly in layers:
            goals.update(self._escape_points(x2, y2, net, ly))
        return self.find_path_to_cells(
            x1,
            y1,
            net,
            width,
            goals,
            prefer_layer=prefer_layer,
            both_layers=both_layers,
            end_xy=(x2, y2),
        )

    def _path_to_geometry(
        self,
        path: list[tuple[int, int, int]],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        net: int,
        width: float,
    ) -> tuple[list[Seg], list[Via]]:
        half = width * 0.5
        segs: list[Seg] = []

        def add_ortho(xa, ya, xb, yb, layer: int) -> None:
            if abs(xa - xb) < 1e-9 and abs(ya - yb) < 1e-9:
                return
            if abs(ya - yb) < 1e-9 or abs(xa - xb) < 1e-9:
                segs.append(Seg(xa, ya, xb, yb, LAYERS[layer], net, width))
                self._mark_seg(layer, xa, ya, xb, yb, half, net)
                return
            segs.append(Seg(xa, ya, xb, ya, LAYERS[layer], net, width))
            self._mark_seg(layer, xa, ya, xb, ya, half, net)
            segs.append(Seg(xb, ya, xb, yb, LAYERS[layer], net, width))
            self._mark_seg(layer, xb, ya, xb, yb, half, net)

        pts: list[tuple[tuple[float, float], int]] = [
            (self._xy(ix, iy), layer) for ix, iy, layer in path
        ]
        if not pts:
            return [], []
        (gx, gy), layer0 = pts[0]
        add_ortho(x1, y1, gx, gy, layer0)
        (ex, ey), layer1 = pts[-1]
        i = 0
        while i < len(pts) - 1:
            (px, py), layer = pts[i]
            j = i + 1
            dx = pts[j][0][0] - px
            dy = pts[j][0][1] - py
            while j + 1 < len(pts) and pts[j + 1][1] == layer:
                ndx = pts[j + 1][0][0] - pts[j][0][0]
                ndy = pts[j + 1][0][1] - pts[j][0][1]
                if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                    break
                if abs(ndx) < 1e-12 and abs(ndy) < 1e-12:
                    break
                if abs(dx * ndy - dy * ndx) > 1e-6 or dx * ndx + dy * ndy < 0:
                    break
                j += 1
            qx, qy = pts[j][0]
            add_ortho(px, py, qx, qy, layer)
            i = j
        add_ortho(ex, ey, x2, y2, layer1)
        return segs, []  # never vias


def _mst_edges(pads: list[Pad]) -> list[tuple[Pad, Pad]]:
    if len(pads) < 2:
        return []
    n = len(pads)
    in_tree = [False] * n
    in_tree[0] = True
    edges: list[tuple[Pad, Pad]] = []
    for _ in range(n - 1):
        best = None
        best_d = 1e18
        bj = -1
        for i in range(n):
            if not in_tree[i]:
                continue
            for j in range(n):
                if in_tree[j]:
                    continue
                d = (pads[i].x - pads[j].x) ** 2 + (pads[i].y - pads[j].y) ** 2
                if d < best_d:
                    best_d = d
                    best = (pads[i], pads[j])
                    bj = j
        if best is None:
            break
        edges.append(best)
        in_tree[bj] = True
    return edges


def net_width(net: int, name: str) -> float:
    if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
        return 0.7
    if name in ("+5V", "+3V3", "+12V", "+12V_SNS", "/BLW_RET") or net in (
        3,
        4,
        46,
        56,
        61,
    ):
        return 0.45
    if "MotDC" in name or name.startswith("/Mot"):
        return 0.4
    return 0.28


def route_priority(net: int, name: str) -> tuple:
    """Signals first (thin), then motors, then fat power last."""
    w = net_width(net, name)
    if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
        return (3, -w, net)
    if name in ("+5V", "+3V3", "+12V", "+12V_SNS", "/BLW_RET") or net in (
        3,
        4,
        46,
        56,
        61,
    ):
        return (2, -w, net)
    if "MotDC" in name or name.startswith("/MotA") or name.startswith("/MotB"):
        return (1, -w, net)
    return (0, -w, net)


def _dedupe_pads(pads: list[Pad]) -> list[Pad]:
    uniq: list[Pad] = []
    for p in pads:
        if any(abs(p.x - q.x) < 0.35 and abs(p.y - q.y) < 0.35 for q in uniq):
            continue
        uniq.append(p)
    return uniq


def parse_segments(pcb_text: str) -> list[Seg]:
    segs: list[Seg] = []
    for m in re.finditer(
        r"\(segment\s+"
        r"\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+"
        r"\(end\s+([\d.-]+)\s+([\d.-]+)\)\s+"
        r"\(width\s+([\d.-]+)\)\s+"
        r'\(layer\s+"([^"]+)"\)\s+'
        r"\(net\s+(\d+)\)",
        pcb_text,
        re.S,
    ):
        segs.append(
            Seg(
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                m.group(6),
                int(m.group(7)),
                float(m.group(5)),
            )
        )
    return segs


def build_router_from_pcb(
    pads: list[Pad],
    segs: list[Seg],
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    grid: float = 0.55,
    clearance: float = MAZE_CLEARANCE_MM,
    hole_sites: list[tuple[float, float, float, int]] | None = None,
) -> MazeRouter:
    router = MazeRouter(x0, y0, board_w, board_h, grid=grid, clearance=clearance)
    if hole_sites:
        router.add_hole_sites(hole_sites)
    for p in pads:
        router.add_pad(p)
    _apply_segments(router, segs)
    return router


def _ortho_clear(
    router: MazeRouter, layer: int, x1: float, y1: float, x2: float, y2: float, net: int, half_w: float
) -> bool:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return True
    steps = max(1, int(math.ceil(length / (router.grid * 0.35))))
    for i in range(steps + 1):
        t = i / steps
        cx, cy = x1 + t * dx, y1 + t * dy
        cx, cy = x1 + t * dx, y1 + t * dy
        ix, iy = router._cell(cx, cy)
        r = half_w + router.clearance
        ix0, iy0 = router._cell(cx - r, cy - r)
        ix1, iy1 = router._cell(cx + r, cy + r)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                if not router._passable(layer, ix, iy, net, half_w):
                    return False
    return True


def _ortho_clear_strict(
    router: MazeRouter, layer: int, x1: float, y1: float, x2: float, y2: float, net: int, half_w: float
) -> bool:
    """Like _ortho_clear plus foreign drill keepout (A7) for repair/bus lanes."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return not router._foreign_hole_blocks(x1, y1, net, half_w)
    steps = max(1, int(math.ceil(length / (router.grid * 0.35))))
    for i in range(steps + 1):
        t = i / steps
        cx, cy = x1 + t * dx, y1 + t * dy
        if router._foreign_hole_blocks(cx, cy, net, half_w):
            return False
        ix, iy = router._cell(cx, cy)
        r = half_w + router.clearance
        ix0, iy0 = router._cell(cx - r, cy - r)
        ix1, iy1 = router._cell(cx + r, cy + r)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                if not router._passable(layer, ix, iy, net, half_w):
                    return False
    return True


def _try_bus_route(
    router: MazeRouter,
    a: Pad,
    b: Pad,
    net: int,
    w: float,
) -> tuple[list[Seg], list[Via]] | None:
    """Route via board margin channels (3-segment bus, no A*)."""
    half = w * 0.5
    x0, y0 = router.x0, router.y0
    bw = (router.nx - 1) * router.grid
    bh = (router.ny - 1) * router.grid
    xbuses = (x0 + 2.0, x0 + bw * 0.25, x0 + bw * 0.5, x0 + bw * 0.75, x0 + bw - 2.0)
    ybuses = (y0 + 2.0, y0 + bh * 0.25, y0 + bh * 0.5, y0 + bh * 0.75, y0 + bh - 2.0)

    def try_path(segs: list[Seg]) -> tuple[list[Seg], list[Via]] | None:
        for layer in (LAYER_B, LAYER_F):
            lname = LAYERS[layer]
            ok = True
            for x1, y1, x2, y2 in (
                (segs[0].x1, segs[0].y1, segs[0].x2, segs[0].y2),
                (segs[1].x1, segs[1].y1, segs[1].x2, segs[1].y2),
                (segs[2].x1, segs[2].y1, segs[2].x2, segs[2].y2),
            ):
                if not _ortho_clear(router, layer, x1, y1, x2, y2, net, half):
                    ok = False
                    break
            if ok:
                return (
                    [
                        Seg(segs[0].x1, segs[0].y1, segs[0].x2, segs[0].y2, lname, net, w),
                        Seg(segs[1].x1, segs[1].y1, segs[1].x2, segs[1].y2, lname, net, w),
                        Seg(segs[2].x1, segs[2].y1, segs[2].x2, segs[2].y2, lname, net, w),
                    ],
                    [],
                )
        return None

    for xb in xbuses:
        out = try_path(
            [
                Seg(a.x, a.y, xb, a.y, "B.Cu", net, w),
                Seg(xb, a.y, xb, b.y, "B.Cu", net, w),
                Seg(xb, b.y, b.x, b.y, "B.Cu", net, w),
            ]
        )
        if out:
            return out
    for yb in ybuses:
        out = try_path(
            [
                Seg(a.x, a.y, a.x, yb, "B.Cu", net, w),
                Seg(a.x, yb, b.x, yb, "B.Cu", net, w),
                Seg(b.x, yb, b.x, b.y, "B.Cu", net, w),
            ]
        )
        if out:
            return out
    return None


def _copper_pad_groups(
    pads: list[Pad], segs: list[Seg], tol: float = 0.85
) -> list[list[int]]:
    """Group pad indices joined by track copper (same logic as _check_net_copper)."""
    n_pad = len(pads)
    if n_pad < 2:
        return [list(range(n_pad))] if n_pad else []

    nodes: list[tuple[float, float]] = [(p.x, p.y) for p in pads]
    for s in segs:
        nodes.append((s.x1, s.y1))
        nodes.append((s.x2, s.y2))

    parent = list(range(len(nodes)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def near(ax: float, ay: float, bx: float, by: float) -> bool:
        return abs(ax - bx) <= tol and abs(ay - by) <= tol

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if near(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1]):
                union(i, j)

    for s in segs:
        ia = ib = None
        for i, (x, y) in enumerate(nodes):
            if near(x, y, s.x1, s.y1):
                ia = i
            if near(x, y, s.x2, s.y2):
                ib = i
        if ia is not None and ib is not None:
            union(ia, ib)

    buckets: dict[int, list[int]] = defaultdict(list)
    for i in range(n_pad):
        buckets[find(i)].append(i)
    return list(buckets.values())


def _try_simple_l(
    router: MazeRouter,
    a: Pad,
    b: Pad,
    net: int,
    w: float,
) -> tuple[list[Seg], list[Via]] | None:
    """Fast H-V or V-H on each layer (no A*)."""
    half = w * 0.5
    for layer in (LAYER_B, LAYER_F):
        lname = LAYERS[layer]
        for mx, my in ((b.x, a.y), (a.x, b.y)):
            if not _ortho_clear(router, layer, a.x, a.y, mx, my, net, half):
                continue
            if not _ortho_clear(router, layer, mx, my, b.x, b.y, net, half):
                continue
            segs = [
                Seg(a.x, a.y, mx, my, lname, net, w),
                Seg(mx, my, b.x, b.y, lname, net, w),
            ]
            return segs, []
    return None


def _try_quick_maze(
    router: MazeRouter,
    a: Pad,
    b: Pad,
    net: int,
    w: float,
    net_name: str = "",
) -> tuple[list[Seg], list[Via]] | None:
    prefer = _prefer_signal_layer(net, net_name)
    for layer in (prefer, 1 - prefer):
        snap = router.snapshot()
        path = router.find_path(
            a.x, a.y, b.x, b.y, net, w, prefer_layer=layer, both_layers=False
        )
        if path is not None:
            return path
        router.restore(snap)
    snap = router.snapshot()
    path = router.find_path(
        a.x, a.y, b.x, b.y, net, w, prefer_layer=prefer, both_layers=True
    )
    if path is not None:
        return path
    router.restore(snap)
    return None


def _try_route_to_group(
    router: MazeRouter,
    pad: Pad,
    net: int,
    w: float,
    group: list[Pad],
) -> tuple[list[Seg], list[Via]] | None:
    """Route pad to nearest pad on main island (L-shape only — fast)."""
    targets = sorted(group, key=lambda q: (pad.x - q.x) ** 2 + (pad.y - q.y) ** 2)
    for tw in (w, 0.22, 0.18):
        for target in targets[:2]:
            if abs(pad.x - target.x) < 0.35 and abs(pad.y - target.y) < 0.35:
                continue
            path = _try_simple_l(router, pad, target, net, tw)
            if path is not None:
                return path
            path = _try_bus_route(router, pad, target, net, tw)
            if path is not None:
                return path
    return None


def _try_route_to_component(
    router: MazeRouter,
    pad: Pad,
    net: int,
    w: float,
    goals: set[tuple[int, int, int]],
    net_name: str = "",
) -> tuple[list[Seg], list[Via]] | None:
    prefer = _prefer_signal_layer(net, net_name)
    layers = (prefer, 1 - prefer)
    for tw in (w, 0.28, 0.22, 0.2):
        for ly in layers:
            snap = router.snapshot()
            path = router.find_path_to_cells(
                pad.x,
                pad.y,
                net,
                tw,
                goals,
                prefer_layer=ly,
                both_layers=True,
            )
            if path is not None:
                return path
            router.restore(snap)
    return None


def _pad_in_component(
    router: MazeRouter, pad: Pad, comp: set[tuple[int, int, int]]
) -> bool:
    ix, iy = router._cell(pad.x, pad.y)
    return (ix, iy, 0) in comp or (ix, iy, 1) in comp


def _apply_segments(router: MazeRouter, segs: list[Seg]) -> None:
    for s in segs:
        li = LAYER_F if s.layer == "F.Cu" else LAYER_B
        router._mark_seg(li, s.x1, s.y1, s.x2, s.y2, s.width * 0.5, s.net)


def _repair_open_nets(
    router: MazeRouter,
    by_net: dict[int, list[Pad]],
    result: RouteResult,
    segs_by_net: dict[int, list[Seg]],
    only_nets: set[int] | None = None,
    x0: float = 0.0,
    y0: float = 0.0,
    board_w: float = 200.0,
    board_h: float = 130.0,
) -> int:
    """Connect pads still on separate copper islands (same net, no new drills)."""
    n_fixed = 0
    for net in sorted(by_net.keys()):
        if only_nets is not None and net not in only_nets:
            continue
        uniq = _dedupe_pads(by_net[net])
        if len(uniq) < 2:
            continue
        name = uniq[0].name
        w = net_width(net, name)
        if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
            w = min(w, 0.35)

        groups = _copper_pad_groups(uniq, segs_by_net.get(net, []))
        if len(groups) <= 1:
            continue

        groups.sort(key=lambda g: -len(g))
        main_grp = groups[0]
        print(f"  repair net {net} {name}: {len(groups)} islands")
        for grp in groups[1:]:
            j = grp[0]
            pad = uniq[j]
            main_pads = [uniq[k] for k in main_grp]
            target = min(
                main_pads,
                key=lambda q: (pad.x - q.x) ** 2 + (pad.y - q.y) ** 2,
            )
            path = None
            for tw in (w, 0.22, 0.18, 0.15):
                path = _try_simple_l(router, pad, target, net, tw)
                if path:
                    break
                path = _try_bus_route(router, pad, target, net, tw)
                if path:
                    break
                path = _try_quick_maze(router, pad, target, net, tw, net_name=name)
                if path:
                    break
                segs = _try_lane_route(
                    router, pad, target, net, tw, x0, y0, board_w, board_h, name=name
                )
                if segs:
                    path = (segs, [])
                    break
            if path is None:
                result.failed.append(
                    (net, name, (pad.x, pad.y), (target.x, target.y))
                )
                continue
            segs, _ = path
            result.segments.extend(segs)
            _apply_segments(router, segs)
            segs_by_net[net].extend(segs)
            main_grp.extend(grp)
            n_fixed += 1
    return n_fixed


def _segments_strict_clear(router: MazeRouter, segs: list[Seg], net: int) -> bool:
    """Reject routes that violate foreign drill keepout (A7)."""
    for s in segs:
        li = LAYER_F if s.layer == "F.Cu" else LAYER_B
        half = s.width * 0.5
        if not _ortho_clear_strict(router, li, s.x1, s.y1, s.x2, s.y2, net, half):
            return False
    return True


def _prefer_signal_layer(net: int, name: str) -> int:
    if is_power_net(name):
        return LAYER_B
    if name.startswith("/TFT") or name.startswith("/T_") or name.startswith("/ENC"):
        return LAYER_F
    if name.startswith("/OPTO"):
        return LAYER_B
    if name.startswith("/DC") and name.endswith("IN2"):
        return LAYER_B
    if name.startswith("/DC") and name.endswith("IN1"):
        return LAYER_F
    if name.startswith("/MotA") or name.startswith("/MotB"):
        return LAYER_B
    if "MotDC" in name:
        return LAYER_B
    return LAYER_F if (net % 2 == 0) else LAYER_B


def _try_lane_route(
    router: MazeRouter,
    a: Pad,
    b: Pad,
    net: int,
    w: float,
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    lanes: BusLaneAllocator | None = None,
    name: str = "",
) -> list[Seg] | None:
    """Clearance-aware bus lane route (A5/A6/A7) — never bypasses occupancy."""
    if lanes is None:
        lanes = BusLaneAllocator(x0, board_w, board_h=board_h, y0=y0, pitch=2.2)
    prefer = _prefer_signal_layer(net, name)
    layers = (prefer, 1 - prefer)
    for ly in layers:
        for _ in range(16):
            bus_x = lanes.alloc_west()
            path = _bus_via_x(router, a.x, a.y, b.x, b.y, bus_x, net, w, ly)
            if path:
                return path
        for _ in range(16):
            bus_x = lanes.alloc_east()
            path = _bus_via_x(router, a.x, a.y, b.x, b.y, bus_x, net, w, ly)
            if path:
                return path
    path = _try_bus_route(router, a, b, net, w)
    if path:
        return path[0]
    path = _try_quick_maze(router, a, b, net, w)
    if path:
        return path[0]
    return None


def _try_route(
    router: MazeRouter,
    a: Pad,
    b: Pad,
    net: int,
    w: float,
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    bridges: list[Pad] | None = None,
    net_name: str = "",
) -> tuple[list[Seg], list[Via]] | None:
    prefer = _prefer_signal_layer(net, net_name)
    alt = 1 - prefer
    dc = net_name.startswith("/DC")
    tft_enc = (
        net_name.startswith("/TFT")
        or net_name.startswith("/T_")
        or net_name.startswith("/ENC")
    )
    widths = (w, 0.28, 0.22, 0.2) if w > 0.28 else (w, 0.22, 0.2)
    for tw in widths:
        snap = router.snapshot()
        path = router.find_path(
            a.x, a.y, b.x, b.y, net, tw, prefer_layer=prefer, both_layers=False
        )
        if path is not None:
            return path
        router.restore(snap)
    if not (dc or tft_enc):
        for tw in widths:
            snap = router.snapshot()
            path = router.find_path(
                a.x, a.y, b.x, b.y, net, tw, prefer_layer=alt, both_layers=False
            )
            if path is not None:
                return path
            router.restore(snap)
    if not dc:
        for tw in widths:
            snap = router.snapshot()
            path = router.find_path(
                a.x, a.y, b.x, b.y, net, tw, prefer_layer=prefer, both_layers=True
            )
            if path is not None:
                return path
            router.restore(snap)
    for tw in (0.22, 0.18):
        path = _try_bus_route(router, a, b, net, tw)
        if path is not None:
            return path
    # edge + corner waypoints
    for mx, my in (
        (x0 + board_w - 2.5, 0.5 * (a.y + b.y)),
        (x0 + 2.5, 0.5 * (a.y + b.y)),
        (0.5 * (a.x + b.x), y0 + 2.5),
        (0.5 * (a.x + b.x), y0 + board_h - 2.5),
        (x0 + board_w - 2.5, y0 + 2.5),
        (x0 + 2.5, y0 + board_h - 2.5),
        (x0 + board_w - 2.5, y0 + board_h - 2.5),
        (x0 + 2.5, y0 + 2.5),
    ):
        snap = router.snapshot()
        p1 = router.find_path(
            a.x, a.y, mx, my, net, 0.22, prefer_layer=prefer, both_layers=True
        )
        if p1 is None:
            router.restore(snap)
            continue
        p2 = router.find_path(
            mx, my, b.x, b.y, net, 0.22, prefer_layer=prefer, both_layers=True
        )
        if p2 is None:
            router.restore(snap)
            continue
        return (p1[0] + p2[0], [])
    if bridges:
        others = sorted(
            bridges,
            key=lambda c: min(
                (c.x - a.x) ** 2 + (c.y - a.y) ** 2,
                (c.x - b.x) ** 2 + (c.y - b.y) ** 2,
            ),
        )[:6]
        for c in others:
            if abs(c.x - a.x) < 0.4 and abs(c.y - a.y) < 0.4:
                continue
            if abs(c.x - b.x) < 0.4 and abs(c.y - b.y) < 0.4:
                continue
            snap = router.snapshot()
            p1 = router.find_path(
                a.x, a.y, c.x, c.y, net, 0.22, prefer_layer=prefer, both_layers=True
            )
            if p1 is None:
                router.restore(snap)
                continue
            p2 = router.find_path(
                c.x, c.y, b.x, b.y, net, 0.22, prefer_layer=prefer, both_layers=True
            )
            if p2 is None:
                router.restore(snap)
                continue
            return (p1[0] + p2[0], [])
    return None


def autoroute_pads(
    pads: list[Pad],
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    existing_vias: Iterable[tuple[float, float, int, float]] = (),
    grid: float = 0.55,
    keepouts: list[tuple[float, float, float]] | None = None,
    hole_sites: list[tuple[float, float, float, int]] | None = None,
) -> RouteResult:
    by_net: dict[int, list[Pad]] = defaultdict(list)
    for p in pads:
        by_net[p.net].append(p)

    if hole_sites is None and keepouts is not None:
        hole_sites = []
    def rebuild(keep_segs: list[Seg]) -> MazeRouter:
        r = MazeRouter(x0, y0, board_w, board_h, grid=grid, clearance=MAZE_CLEARANCE_MM)
        if hole_sites:
            r.add_hole_sites(hole_sites)
        for p in pads:
            r.add_pad(p)
        for s in keep_segs:
            li = LAYER_F if s.layer == "F.Cu" else LAYER_B
            r._mark_seg(li, s.x1, s.y1, s.x2, s.y2, s.width * 0.5, s.net)
        return r

    jobs: list[tuple[tuple, float, int, str, Pad, Pad, list[Pad]]] = []
    for net, plist in by_net.items():
        uniq = _dedupe_pads(plist)
        if len(uniq) < 2:
            continue
        name = uniq[0].name
        pri = route_priority(net, name)
        for a, b in _mst_edges(uniq):
            dist = math.hypot(a.x - b.x, a.y - b.y)
            jobs.append((pri, dist, net, name, a, b, uniq))
    jobs.sort(key=lambda t: (t[0], t[1], t[2]))

    router = rebuild([])
    result = RouteResult()
    ok_segs: list[Seg] = []
    n_ok = 0
    for i, (_pri, _dist, net, name, a, b, uniq) in enumerate(jobs, 1):
        if i % 25 == 0:
            print(f"  … routed {n_ok}/{i} edges, failed {len(result.failed)}")
        w = net_width(net, name)
        path = _try_route(router, a, b, net, w, x0, y0, board_w, board_h, bridges=uniq, net_name=name)
        if path is None:
            result.failed.append((net, name, (a.x, a.y), (b.x, b.y)))
            continue
        segs, _ = path
        ok_segs.extend(segs)
        result.segments.extend(segs)
        n_ok += 1

    if result.failed:
        bad = {n for n, _, _, _ in result.failed}
        print(f"  Rip-up retry for {len(bad)} nets ({len(result.failed)} failed edges)…")
        keep = [s for s in ok_segs if s.net not in bad]
        retry_jobs = [j for j in jobs if j[2] in bad]
        router = rebuild(keep)
        result.segments = list(keep)
        result.failed = []
        n_ok = sum(1 for j in jobs if j[2] not in bad)
        for i, (_pri, _dist, net, name, a, b, uniq) in enumerate(retry_jobs, 1):
            if i % 10 == 0:
                print(f"  … rip-up {i}/{len(retry_jobs)}, failed {len(result.failed)}")
            w = net_width(net, name)
            if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
                w = min(w, 0.45)  # thinner on rip-up — less blockage
            path = _try_route(
                router, a, b, net, w, x0, y0, board_w, board_h, bridges=uniq, net_name=name
            )
            if path is None:
                result.failed.append((net, name, (a.x, a.y), (b.x, b.y)))
                continue
            segs, _ = path
            result.segments.extend(segs)
            n_ok += 1

    print(
        f"Maze policy: no extra vias (pin bridges OK); free F/B; "
        f"{n_ok} edges routed, {len(result.failed)} failed"
    )
    return result


def _pad_for_ref(pads: list[Pad], net: int, ref: str) -> Pad | None:
    for p in pads:
        if p.net == net and p.ref == ref:
            return p
    return None


@dataclass
class BusLaneAllocator:
    """Assign unique B.Cu bus coordinates (avoid net-on-net overlap)."""

    x0: float
    board_w: float
    board_h: float = 132.0
    y0: float = 30.0
    pitch: float = 2.2
    _west_i: int = 0
    _east_i: int = 0
    _y_i: int = 0
    reserved_x: set[float] = field(default_factory=set)
    reserved_y: set[float] = field(default_factory=set)

    def reserve(self, x: float) -> None:
        self.reserved_x.add(round(x, 2))

    def _free_x(self, x: float) -> float:
        xr = round(x, 2)
        while xr in self.reserved_x:
            x += 0.35
            xr = round(x, 2)
        self.reserved_x.add(xr)
        return x

    def _free_y(self, y: float) -> float:
        yr = round(y, 2)
        while yr in self.reserved_y:
            y += 0.35
            yr = round(y, 2)
        self.reserved_y.add(yr)
        return y

    def alloc_west(self) -> float:
        x = self.x0 + 10.0 + self._west_i * self.pitch
        self._west_i += 1
        return self._free_x(x)

    def alloc_east(self) -> float:
        x = self.x0 + self.board_w - 10.0 - self._east_i * self.pitch
        self._east_i += 1
        return self._free_x(x)

    def alloc_bus_y(self) -> float:
        opts = (
            self.y0 + 4.0,
            self.y0 + 8.0,
            self.y0 + self.board_h - 4.0,
            self.y0 + self.board_h - 8.0,
        )
        y = opts[self._y_i % len(opts)]
        self._y_i += 1
        return self._free_y(y)


def _force_channel_route(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    bus_x: float | None,
    bus_y: float | None,
    net: int,
    w: float,
    layer: str = "B.Cu",
) -> list[Seg]:
    """Orthogonal route through a reserved bus channel (no maze clearance check)."""
    out: list[Seg] = []
    if bus_x is not None:
        legs = ((ax, ay, bus_x, ay), (bus_x, ay, bus_x, by), (bus_x, by, bx, by))
    elif bus_y is not None:
        legs = ((ax, ay, ax, bus_y), (ax, bus_y, bx, bus_y), (bx, bus_y, bx, by))
    else:
        return out
    for x1, y1, x2, y2 in legs:
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            continue
        out.append(Seg(x1, y1, x2, y2, layer, net, w))
    return out


def _route_bus_channel(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    net: int,
    w: float,
    bus_x: float,
    avoid_x: float | None = None,
    y0: float = 0.0,
    board_h: float = 130.0,
    lanes: BusLaneAllocator | None = None,
) -> list[Seg]:
    """Vertical bus lane; if a horizontal leg would cross avoid_x, use a unique margin bus_y."""
    if avoid_x is not None:
        lo, hi = min(ax, bx), max(ax, bx)
        if lo + 0.4 < avoid_x < hi - 0.4:
            if lanes is not None:
                bus_y = lanes.alloc_bus_y()
                path = _force_channel_route(ax, ay, bx, by, None, bus_y, net, w)
                if path:
                    return path
            for bus_y in (y0 + 4.0, y0 + board_h - 4.0, 0.5 * (ay + by)):
                path = _force_channel_route(ax, ay, bx, by, None, bus_y, net, w)
                if path:
                    return path
    return _force_channel_route(ax, ay, bx, by, bus_x, None, net, w)


def _try_force_channel(
    a: Pad,
    b: Pad,
    net: int,
    w: float,
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    allocator: BusLaneAllocator | None = None,
) -> list[Seg] | None:
    """Route via reserved west/east B.Cu corridors (unique lane per call when allocator set)."""
    if allocator is not None:
        avoid_x = x0 + 5.5
        for _ in range(6):
            bus_x = allocator.alloc_west()
            segs = _route_bus_channel(
                a.x, a.y, b.x, b.y, net, w, bus_x, avoid_x=avoid_x, y0=y0, board_h=board_h, lanes=allocator
            )
            if segs:
                return segs
        for _ in range(6):
            bus_x = allocator.alloc_east()
            segs = _route_bus_channel(
                a.x, a.y, b.x, b.y, net, w, bus_x, avoid_x=avoid_x, y0=y0, board_h=board_h, lanes=allocator
            )
            if segs:
                return segs
        for bus_y in (
            allocator.alloc_bus_y(),
            allocator.alloc_bus_y(),
            y0 + 4.0,
            y0 + board_h - 4.0,
        ):
            segs = _force_channel_route(a.x, a.y, b.x, b.y, None, bus_y, net, w)
            if segs:
                return segs
        return None

    buses_x = (
        x0 + 4.0,
        x0 + 8.0,
        x0 + 12.0,
        x0 + 18.0,
        x0 + 24.0,
        x0 + board_w - 4.0,
        x0 + board_w - 8.0,
        x0 + board_w - 12.0,
        x0 + board_w - 18.0,
        x0 + board_w - 24.0,
    )
    buses_y = (
        y0 + 4.0,
        y0 + 8.0,
        y0 + board_h - 4.0,
        y0 + board_h - 8.0,
    )
    for bus_x in buses_x:
        segs = _force_channel_route(a.x, a.y, b.x, b.y, bus_x, None, net, w)
        if segs:
            return segs
    for bus_y in buses_y:
        segs = _force_channel_route(a.x, a.y, b.x, b.y, None, bus_y, net, w)
        if segs:
            return segs
    return None


def _bus_via_x(
    router: MazeRouter,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    bus_x: float,
    net: int,
    w: float,
    layer: int = LAYER_B,
) -> list[Seg] | None:
    """Three-segment route through a vertical bus channel on one layer."""
    lname = LAYERS[layer]
    half = w * 0.5
    legs = ((ax, ay, bus_x, ay), (bus_x, ay, bus_x, by), (bus_x, by, bx, by))
    for x1, y1, x2, y2 in legs:
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            continue
        if not _ortho_clear_strict(router, layer, x1, y1, x2, y2, net, half):
            return None
    out: list[Seg] = []
    for x1, y1, x2, y2 in legs:
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            continue
        out.append(Seg(x1, y1, x2, y2, lname, net, w))
    return out


def emit_service_buses(
    pcb_text: str,
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    uid_fn=None,
) -> tuple[str, RouteResult]:
    """Fixed B.Cu buses: GND spine + per-signal TFT/HMI channels (no vias)."""
    import uuid

    uid = uid_fn or (lambda: str(uuid.uuid4()))
    pads = parse_pads(pcb_text)
    segs = parse_segments(pcb_text)
    hole_sites = parse_hole_sites(pcb_text)
    router = build_router_from_pcb(
        pads, segs, x0, y0, board_w, board_h, grid=0.55, clearance=MAZE_CLEARANCE_MM,
        hole_sites=hole_sites,
    )
    result = RouteResult()
    by_net: dict[int, list[Pad]] = defaultdict(list)
    for p in pads:
        by_net[p.net].append(p)

    bus_gnd_x = x0 + 5.5
    w_gnd = 0.4
    lanes = BusLaneAllocator(x0, board_w, board_h=board_h, y0=y0, pitch=2.2)
    lanes.reserve(bus_gnd_x)
    # GND: no full-board spine (crosses signal buses). Islands closed in loop below.

    segs_by_net: dict[int, list[Seg]] = defaultdict(list)
    for s in segs:
        segs_by_net[s.net].append(s)

    def _already_connected(net: int, a: Pad, b: Pad) -> bool:
        plist = _dedupe_pads(by_net.get(net, []))
        ai = bi = None
        for i, p in enumerate(plist):
            if abs(p.x - a.x) < 0.01 and abs(p.y - a.y) < 0.01:
                ai = i
            if abs(p.x - b.x) < 0.01 and abs(p.y - b.y) < 0.01:
                bi = i
        if ai is None or bi is None:
            return False
        groups = _copper_pad_groups(plist, segs_by_net.get(net, []))
        for g in groups:
            if ai in g and bi in g:
                return True
        return False

    bus_tft_x0 = x0 + 14.0
    bus_pitch = 1.8
    # TFT + touch + ENC on dedicated B.Cu channels (skip if maze already connected)
    channel_routes: list[tuple[int, str, str, float]] = [
        (47, "U1", "J17", 0.28),
        (48, "U1", "J17", 0.28),
        (52, "U1", "J17", 0.28),
        (50, "U1", "J17", 0.28),
        (51, "U1", "J17", 0.28),
        (58, "U1", "J17", 0.28),
        (59, "U1", "J17", 0.28),
        (53, "U1", "J17", 0.28),
        (60, "U1", "J18", 0.28),
        (62, "U1", "J18", 0.28),
        (54, "U1", "J15", 0.28),
        (55, "U1", "J16", 0.28),
        (4, "U1", "J17", 0.35),
    ]
    for i, (net, src_ref, dst_ref, tw) in enumerate(channel_routes):
        src = _pad_for_ref(by_net.get(net, []), net, src_ref)
        dst = _pad_for_ref(by_net.get(net, []), net, dst_ref)
        if not src or not dst:
            continue
        if _already_connected(net, src, dst):
            continue
        bus_x = lanes._free_x(bus_tft_x0 + i * bus_pitch)
        path = _try_lane_route(
            router, src, dst, net, tw, x0, y0, board_w, board_h, lanes=lanes,
            name=by_net.get(net, [src])[0].name,
        )
        if path:
            result.segments.extend(path)
            _apply_segments(router, path)
            segs_by_net[net].extend(path)

    bus_east = x0 + board_w - 6.0
    east_pitch = 1.8
    east_routes: list[tuple[int, str, str, float]] = [
        (3, "U1", "U2", 0.35),
        (57, "J1", "F1", 0.4),
        (40, "U1", "U5", 0.28),
        (41, "U1", "U5", 0.28),
        (42, "U1", "U6", 0.28),
        (43, "U1", "U6", 0.28),
        (44, "U1", "U7", 0.28),
        (45, "U1", "U7", 0.28),
        (12, "U3", "J2", 0.28),
        (13, "U3", "J2", 0.28),
        (14, "U3", "J2", 0.28),
        (15, "U3", "J2", 0.28),
        (34, "U5", "J5", 0.3),
        (35, "U5", "J5", 0.3),
        (36, "U6", "J6", 0.3),
        (37, "U6", "J6", 0.3),
        (38, "U7", "J7", 0.3),
        (39, "U7", "J7", 0.3),
        (24, "U4", "J4", 0.35),
        (26, "U4", "J8", 0.28),
        (27, "U4", "J4", 0.28),
        (29, "U9", "J12", 0.28),
        (30, "U9", "J13", 0.28),
        (31, "U9", "J4", 0.28),
        (32, "U9", "J4", 0.28),
    ]
    for i, (net, src_ref, dst_ref, tw) in enumerate(east_routes):
        plist = by_net.get(net, [])
        src = _pad_for_ref(plist, net, src_ref)
        dst = _pad_for_ref(plist, net, dst_ref)
        if not src or not dst:
            # fallback: merge copper islands via east bus
            groups = _copper_pad_groups(_dedupe_pads(plist), [s for s in segs if s.net == net])
            if len(groups) < 2:
                continue
            groups.sort(key=lambda g: -len(g))
            uniq = _dedupe_pads(plist)
            src = uniq[groups[1][0]]
            dst = uniq[groups[0][0]]
        if _already_connected(net, src, dst):
            continue
        pname = _dedupe_pads(plist)[0].name if plist else ""
        path = _try_lane_route(
            router, src, dst, net, tw, x0, y0, board_w, board_h, lanes=lanes, name=pname,
        )
        if path:
            result.segments.extend(path)
            _apply_segments(router, path)
            segs_by_net[net].extend(path)

    # Close remaining open islands on dedicated east/west B.Cu lanes
    for net, plist in by_net.items():
        uniq = _dedupe_pads(plist)
        if len(uniq) < 2:
            continue
        groups = _copper_pad_groups(uniq, segs_by_net.get(net, []))
        if len(groups) <= 1:
            continue
        groups.sort(key=lambda g: -len(g))
        w = net_width(net, uniq[0].name)
        if net in (1, 2, 57) or uniq[0].name in ("GND", "+12V_RAW"):
            w = min(w, 0.35 if net != 2 else 0.40)
        for grp in groups[1:]:
            pad = uniq[grp[0]]
            target = min(
                [uniq[k] for k in groups[0]],
                key=lambda q: (pad.x - q.x) ** 2 + (pad.y - q.y) ** 2,
            )
            segs = _try_lane_route(
                router, pad, target, net, w, x0, y0, board_w, board_h, lanes=lanes,
                name=uniq[0].name,
            )
            if segs:
                result.segments.extend(segs)
                _apply_segments(router, segs)
                segs_by_net[net].extend(segs)
                groups[0].extend(grp)

    print(f"Service buses: {len(result.segments)} B.Cu segments")
    if not result.segments:
        return pcb_text, result
    return inject_routes(pcb_text, format_routes(result, uid)), result


OPEN_NETS: set[int] | None = None  # auto-detect from copper


def repair_open_pcb(
    pcb_text: str,
    x0: float,
    y0: float,
    board_w: float,
    board_h: float,
    grid: float = 0.55,
    uid_fn=None,
    only_nets: set[int] | None = OPEN_NETS,
) -> tuple[str, RouteResult]:
    """Append routes to close open copper islands (no full re-autoroute)."""
    import uuid

    uid = uid_fn or (lambda: str(uuid.uuid4()))
    pads = parse_pads(pcb_text)
    segs = parse_segments(pcb_text)
    segs_by_net: dict[int, list[Seg]] = defaultdict(list)
    for s in segs:
        segs_by_net[s.net].append(s)
    by_net: dict[int, list[Pad]] = defaultdict(list)
    for p in pads:
        by_net[p.net].append(p)

    open_nets: set[int] = set()
    if only_nets is None:
        for net, plist in by_net.items():
            uniq = _dedupe_pads(plist)
            if len(uniq) < 2:
                continue
            if len(_copper_pad_groups(uniq, segs_by_net.get(net, []))) > 1:
                open_nets.add(net)
    else:
        open_nets = only_nets

    router = build_router_from_pcb(
        pads, segs, x0, y0, board_w, board_h, grid=grid, clearance=MAZE_CLEARANCE_MM,
        hole_sites=parse_hole_sites(pcb_text),
    )
    result = RouteResult()
    n = _repair_open_nets(
        router, by_net, result, segs_by_net, only_nets=open_nets,
        x0=x0, y0=y0, board_w=board_w, board_h=board_h,
    )
    print(f"Repair: {n} new connections, {len(result.segments)} segments, {len(result.failed)} failed")
    if not result.segments:
        return pcb_text, result
    return inject_routes(pcb_text, format_routes(result, uid)), result


def format_routes(result: RouteResult, uid_fn) -> list[str]:
    lines: list[str] = []
    for s in result.segments:
        if abs(s.x1 - s.x2) < 1e-9 and abs(s.y1 - s.y2) < 1e-9:
            continue
        lines += [
            "\t(segment",
            f"\t\t(start {s.x1:.4f} {s.y1:.4f})",
            f"\t\t(end {s.x2:.4f} {s.y2:.4f})",
            f"\t\t(width {s.width})",
            f'\t\t(layer "{s.layer}")',
            f"\t\t(net {s.net})",
            f'\t\t(uuid "{uid_fn()}")',
            "\t)",
        ]
    # deliberately omit vias
    return lines


def inject_routes(pcb_text: str, route_lines: list[str]) -> str:
    if not route_lines:
        return pcb_text
    block = "\n" + "\n".join(route_lines) + "\n"
    idx = pcb_text.rstrip().rfind(")")
    if idx < 0:
        return pcb_text + block
    return pcb_text[:idx] + block + pcb_text[idx:]
