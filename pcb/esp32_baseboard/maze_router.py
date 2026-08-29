"""2-layer grid A* maze autorouter for the ESP32 carrier PCB.

User policy:
  - Traces may meander on F.Cu and B.Cu freely (H+V on either face).
  - NO extra drill holes: never emit routing vias. Layer change only at
    existing thru-hole pads (headers / modules) which already pierce both faces.
"""

from __future__ import annotations

import heapq
import math
import random
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field

from pcb_parse import NetTable, pad_net, seg_net
from typing import Iterable


LAYERS = ("F.Cu", "B.Cu")
LAYER_F = 0
LAYER_B = 1
BLOCKED = -1  # module keepout zones (not net copper)

# Match _check_signal_routing.py
HOLE_EXTRA_MM = 0.25
TRACE_CLEARANCE_MM = 0.20
DEFAULT_HALF_TRACK = 0.15
# A7 keepout is track-width dependent: a thin signal fits between two 2.54 mm
# pins, a fat power track does not. Grid keepouts are baked for both.
# Widest signal track two of which still fit on neighbouring grid columns
# without breaking A6: grid pitch - TRACE_CLEARANCE_MM, minus a hair.
# Bus lanes must be at least a grid pitch apart or the occupancy grid cannot
# distinguish them; 0.7 also clears the widest A6 separation (0.65).
EDGE_CLEARANCE_MM = 0.5  # KiCad board-setup copper-to-edge
LANE_MIN_SEP = 0.7
# A hair of margin so a track that lands exactly on the A7 limit reads as
# outside it rather than as a violation by a rounding error.
KEEPOUT_EPS_MM = 0.02
VIA_DRILL = 0.4
VIA_SIZE = 0.8
# A via is the escape hatch, not a routing tool: priced at ~70 grid steps so
# the search only buys one when there is no same-layer way round at all.
VIA_COST = 70.0
MAX_SIGNAL_WIDTH = 0.34
BOOST_SCALE = 0.35  # how far a failed net moves up the order on the next pass
QUICK_EXPAND = 20000  # first-fit A* budget; phase 2 searches the whole grid
STUB_PROBE_EXTRA_MM = 0.02  # extra probe radius on the off-grid pad stubs
THIN_HALF_TRACK = 0.15
WIDE_HALF_TRACK = 0.35
# Set so a track's marked radius reaches the neighbouring grid column exactly
# when its width demands more than one pitch of separation: a 0.7 mm power
# track claims its neighbours (it needs 0.74-0.95 mm), while a 0.28 mm signal
# does not (0.48 mm fits inside one 0.55 mm pitch). Marking every track at
# 0.14 let a 0.7 mm rail sit one pitch from a signal and overlap its copper.
MAZE_CLEARANCE_MM = 0.29
ROUTE_ATTEMPTS = 8  # full routing passes, each promoting the previous losers
RIPUP_ROUNDS = 4  # neighbourhood rip-up rounds after each pass
RIPUP_MARGIN_MM = 4.0  # grows per round: how far around a failed edge to clear

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


def _pad_chunks(block: str) -> list[str]:
    """Split a footprint into one string per pad.

    A pad's `(net N "…")` line sits *after* its `(drill …)`, so a single regex
    anchored on the drill never sees the net and every pad reads as net 0 —
    i.e. as foreign to everything, including its own net.
    """
    starts = [m.start() for m in re.finditer(r"\(pad\s+\"", block)]
    return [
        block[s: (starts[i + 1] if i + 1 < len(starts) else len(block))]
        for i, s in enumerate(starts)
    ]


def parse_hole_sites(pcb_text: str) -> list[tuple[float, float, float, int]]:
    """Drill centers (x, y, drill_mm, net) for foreign-hole checks (A7)."""
    table = NetTable(pcb_text)
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
        for chunk in _pad_chunks(block):
            if not re.match(r'\(pad\s+"[^"]*"\s+(?:thru_hole|np_thru_hole)\s+\w+', chunk):
                continue
            am = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+[\d.-]+)?\)", chunk)
            zm = re.search(r"\(size\s+([\d.-]+)\s+([\d.-]+)\)", chunk)
            dm = re.search(r"\(drill\s+([\d.-]+)\)", chunk)
            if not (am and zm and dm):
                continue
            lx, ly = float(am.group(1)), float(am.group(2))
            sx, sy = float(zm.group(1)), float(zm.group(2))
            drill = float(dm.group(1))
            net, _nname = pad_net(chunk, table)
            wx = fx + lx * c - ly * s
            wy = fy + lx * s + ly * c
            # A7 is measured from the pad's copper, not the drill: a 1.7 mm
            # annulus around a 1.0 mm hole is 0.35 mm wider on every side.
            # _check_signal_routing.py uses max(size, drill), so match it or the
            # router happily lays copper the gate then rejects.
            d = max(sx, sy, drill if drill > 0.05 else 0.0)
            sites.append((wx, wy, d, net))
    return sites


def parse_keepout_holes(pcb_text: str) -> list[tuple[float, float, float]]:
    """Legacy wrapper — radii for external tools."""
    return [(x, y, keepout_radius(d)) for x, y, d, _ in parse_hole_sites(pcb_text)]


def parse_pads(pcb_text: str) -> list[Pad]:
    table = NetTable(pcb_text)
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
        # One chunk per pad. The old single regex ran `[\s\S]*?(net ...)` from
        # the size line, so a pad with no net of its own (IO0, TX0/RX0, the
        # TMC's unused MS pins) silently borrowed the NEXT pad's net — putting
        # that net's Pad at the wrong coordinates and sending the router to a
        # walled-in unconnected hole instead of the real pin.
        for chunk in _pad_chunks(part):
            am2 = re.match(
                r"\(pad\s+\"[^\"]*\"\s+\w+\s+\w+\s*"
                r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)\s*"
                r"\(size\s+([\d.-]+)\s+([\d.-]+)\)",
                chunk,
            )
            if not am2:
                continue
            net, nname = pad_net(chunk, table)
            if not nname and not net:
                continue
            lx, ly = float(am2.group(1)), float(am2.group(2))
            sx, sy = float(am2.group(4)), float(am2.group(5))
            if net <= 0:
                continue
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
    """Vias already in the board (x, y, net, size)."""
    out: list[tuple[float, float, int, float]] = []
    table = NetTable(pcb_text)
    for m in re.finditer(
        r"\(via\s*\(at\s+([\d.-]+)\s+([\d.-]+)\)\s*\(size\s+([\d.-]+)\)"
        r"([\s\S]*?)\(uuid",
        pcb_text,
    ):
        nid, _ = pad_net(m.group(4), table)
        if not nid:
            nid, _ = seg_net(m.group(4), table)
        out.append((float(m.group(1)), float(m.group(2)), nid, float(m.group(3))))
    return out


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
        self.hole_keepout: list[dict[int, int]] = [{}, {}]
        self.pad_cells: dict[int, set[int]] = {}
        self.copper = CopperIndex()

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

    def _claim(self, layer: int, ix: int, iy: int, net: int) -> None:
        """Claim an endpoint cell without evicting another net's copper.

        The endpoint claim exists so a pad can start/end a search on its own
        cell; overwriting a foreign net there would hand this net a cell that
        already carries someone else's track, and the pad stub would then be
        drawn straight over it."""
        cur = self._get(layer, ix, iy)
        if cur == 0 or cur == net:
            self._set(layer, ix, iy, net)

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

    def add_edge_keepout(self, margin: float) -> None:
        """Block the ring along Edge.Cuts (KiCad's copper-to-edge constraint)."""
        n = max(1, int(math.ceil(margin / self.grid)))
        for li in (0, 1):
            for ix in range(self.nx):
                for iy in range(self.ny):
                    if ix < n or iy < n or ix >= self.nx - n or iy >= self.ny - n:
                        if self._get(li, ix, iy) == 0:
                            self._set(li, ix, iy, BLOCKED)

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
        self._build_hole_keepouts()

    def _build_hole_keepouts(self) -> None:
        """Bake the A7 drill keepout into the grid.

        The A* only ever consulted pad copper (≈0.77 mm around a 1.7 mm pad),
        which is smaller than the A7 rule's drill/2 + 0.25 + clearance + half
        track, so it happily threaded tracks past header and M3 holes. Two maps
        are kept because the allowed approach depends on the track: a 0.28 mm
        signal fits between two 2.54 mm-pitch pins, a 0.7 mm power track does
        not. A cell claimed by two different holes belongs to neither.
        """
        self.hole_keepout = [{}, {}]  # [thin, wide]
        for hx, hy, drill, hnet in self.hole_sites:
            self._add_hole_keepout(hx, hy, drill, hnet)

    def _add_hole_keepout(self, hx: float, hy: float, drill: float, hnet: int) -> None:
        owner = hnet if hnet else BLOCKED
        base = drill * 0.5 + HOLE_EXTRA_MM + TRACE_CLEARANCE_MM + KEEPOUT_EPS_MM
        for mi, half_w in enumerate((THIN_HALF_TRACK, WIDE_HALF_TRACK)):
            r = base + half_w
            m = self.hole_keepout[mi]
            ix0, iy0 = self._cell(hx - r, hy - r)
            ix1, iy1 = self._cell(hx + r, hy + r)
            r2 = r * r
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    cx, cy = self._xy(ix, iy)
                    if (cx - hx) ** 2 + (cy - hy) ** 2 > r2:
                        continue
                    k = self._key(ix, iy)
                    cur = m.get(k)
                    if cur is None:
                        m[k] = owner
                    elif cur != owner:
                        m[k] = BLOCKED

    def _hole_blocks_cell(self, ix: int, iy: int, net: int, half_w: float) -> bool:
        if not self.hole_keepout[0]:
            return False
        m = self.hole_keepout[1 if half_w > THIN_HALF_TRACK else 0]
        owner = m.get(self._key(ix, iy))
        return owner is not None and owner != net

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
        self.pad_cells.setdefault(self._key(*self._cell(pad.x, pad.y)), set()).add(pad.net)

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
        if cur != 0 and cur != net:
            return False
        return not self._hole_blocks_cell(ix, iy, net, half_w)

    def _stub_clear(
        self, xa: float, ya: float, xb: float, yb: float,
        layer: int, net: int, half: float,
    ) -> bool:
        """Is the pad-to-grid stub clear on this layer?

        The stubs are the one part of a path the A* never sees: the search
        works cell to cell, then the geometry pass joins the true pad centre to
        the first/last cell. The end stub is worse — the goal test matches a
        cell on *either* layer, so it can be drawn on a layer the escape walk
        never checked. Unchecked, those 3-4 mm legs drive straight across other
        nets: a short, not a DRC nit.

        Probed with an inflated half-width because the grid models clearance at
        MAZE_CLEARANCE_MM, under the TRACE_CLEARANCE_MM the A6 gate wants; the
        on-grid part of a path is saved from that gap by the 0.55 mm cell
        pitch, but a stub runs off-grid through the pad centre.
        """
        probe = half + STUB_PROBE_EXTRA_MM
        return all(
            _ortho_clear(self, layer, lx1, ly1, lx2, ly2, net, probe)
            for lx1, ly1, lx2, ly2 in _stub_legs(xa, ya, xb, yb)
        )

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

    def snap(self, x: float, y: float) -> tuple[float, float]:
        """Nearest grid point.

        Anything that lays long copper at an arbitrary coordinate (bus lanes,
        detour waypoints) has to land on the grid, or its distance to a normal
        on-grid track is no longer a multiple of the cell pitch — two runs end
        up 0.30 mm apart where the occupancy grid can only reason in 0.55 mm
        steps, and A6 catches what the router could not see.
        """
        return self._xy(*self._cell(x, y))

    def _can_pin_hop(self, ix: int, iy: int, net: int) -> bool:
        """Layer change only on a real thru-hole pad (or via) of this net.

        Testing grid ownership alone was not enough: as soon as a net had
        copper on both faces anywhere near a cell, the search read that as a
        pin and swapped layers in mid-air. The board then carried a track that
        simply stopped on one layer and resumed on the other with nothing
        joining them — KiCad reports those as dangling and unconnected.
        """
        return net in self.pad_cells.get(self._key(ix, iy), ())

    def _can_drop_via(self, ix: int, iy: int, net: int) -> bool:
        """Is there room for a new via here, on both faces?

        A via is a drilled hole, so it needs the same A7 clearance a pad does,
        on both layers, plus its own annulus footprint clear of other copper.
        """
        # Probe the via's *A7 keepout*, not just its annulus: registering the
        # keepout after placing the via only holds off later copper, while a
        # track routed earlier would already be sitting inside it.
        #
        # Scanned directly rather than through _ortho_clear, which takes a
        # zero-length segment as trivially clear and would wave every site
        # through.
        cx, cy = self._xy(ix, iy)
        r = VIA_SIZE * 0.5 + HOLE_EXTRA_MM + TRACE_CLEARANCE_MM + WIDE_HALF_TRACK
        ix0, iy0 = self._cell(cx - r, cy - r)
        ix1, iy1 = self._cell(cx + r, cy + r)
        r2 = r * r
        for layer in (0, 1):
            for jx in range(ix0, ix1 + 1):
                for jy in range(iy0, iy1 + 1):
                    px, py = self._xy(jx, jy)
                    if (px - cx) ** 2 + (py - cy) ** 2 > r2:
                        continue
                    if not self._passable(layer, jx, jy, net, VIA_SIZE * 0.5):
                        return False
        return not self._foreign_hole_blocks(cx, cy, net, VIA_SIZE * 0.5)

    def mark_via(self, x: float, y: float, net: int) -> None:
        """Claim a via's copper on both faces and register its drill for A7."""
        for layer in (0, 1):
            self._mark_disk(layer, x, y, VIA_SIZE * 0.5, net)
        self.pad_cells.setdefault(self._key(*self._cell(x, y)), set()).add(net)
        self.hole_sites.append((x, y, VIA_SIZE, net))
        self._add_hole_keepout(x, y, VIA_SIZE, net)

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
        max_expand: int | None = None,
        allow_via: bool = False,
    ) -> tuple[list[Seg], list[Via]] | None:
        """A* from a point until any goal cell (existing net copper)."""
        if not goals:
            return None
        layers = (prefer_layer,) if not both_layers else (LAYER_F, LAYER_B)
        for ly in layers:
            self._claim(ly, *self._cell(x1, y1), net)

        half_w = width * 0.5
        starts: list[tuple[int, int, int]] = []
        for ly in layers:
            for sx, sy, sl in self._escape_points(x1, y1, net, ly):
                gx0, gy0 = self._xy(sx, sy)
                if self._stub_clear(x1, y1, gx0, gy0, sl, net, half_w):
                    starts.append((sx, sy, sl))
        if not starts:
            return None
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
        # The old cap was a flat 18000 cells — under 9% of one layer on this
        # board — so any net that had to detour around the ESP32 socket (a
        # 56 mm wall of pads) was abandoned before the search ever reached the
        # way round. Default to the whole grid; callers pass a smaller budget
        # only for the cheap first-fit attempts.
        budget = self.nx * self.ny * (2 if both_layers else 1)
        max_expand = budget if max_expand is None else min(max_expand, budget)
        expands = 0
        while open_h and expands < max_expand:
            expands += 1
            _, _, cur = heapq.heappop(open_h)
            if cur in goals or (cur[0], cur[1]) in goal_xy:
                # Only stop here if the stub from this cell to the pad is
                # actually clear on this cell's layer. Vetoing the whole path
                # afterwards instead threw away good routes: the search had no
                # way to try a different final cell.
                ex0, ey0 = self._xy(cur[0], cur[1])
                tx0, ty0 = end_xy if end_xy is not None else (ex0, ey0)
                if self._stub_clear(ex0, ey0, tx0, ty0, cur[2], net, half_w):
                    found = cur
                    break
            ix, iy, ly = cur
            prev = came[cur]
            for dx, dy in dirs:
                nx_, ny_ = ix + dx, iy + dy
                if not self._passable(ly, nx_, ny_, net, width * 0.5):
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
            if both_layers:
                other = 1 - ly
                nxt = (ix, iy, other)
                hop = None
                if self._can_pin_hop(ix, iy, net):
                    hop = 0.35  # free layer change at this net's own thru-hole pad
                elif allow_via and self._can_drop_via(ix, iy, net):
                    hop = VIA_COST
                if hop is not None:
                    ng = gscore[cur] + hop
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
        return self._path_to_geometry(path, x1, y1, x2, y2, net, width, allow_via)

    def find_path(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        net: int,
        width: float,
        prefer_layer: int = LAYER_B,
        allow_via: bool = False,  # last resort only — see VIA_COST
        both_layers: bool = True,
        max_expand: int | None = None,
    ) -> tuple[list[Seg], list[Via]] | None:
        """A* on F/B. Layer hops only at existing thru-hole pads (no new drills)."""
        layers = (prefer_layer,) if not both_layers else (LAYER_F, LAYER_B)
        for ly in layers:
            self._claim(ly, *self._cell(x1, y1), net)
            self._claim(ly, *self._cell(x2, y2), net)

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
            max_expand=max_expand,
            allow_via=allow_via,
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
        allow_via: bool = False,
    ) -> tuple[list[Seg], list[Via]] | None:
        half = width * 0.5
        segs: list[Seg] = []
        vias: list[Via] = []

        def add_ortho(xa, ya, xb, yb, layer: int) -> None:
            for lx1, ly1, lx2, ly2 in _stub_legs(xa, ya, xb, yb):
                segs.append(Seg(lx1, ly1, lx2, ly2, LAYERS[layer], net, width))
                self._mark_seg(layer, lx1, ly1, lx2, ly2, half, net)

        pts: list[tuple[tuple[float, float], int]] = [
            (self._xy(ix, iy), layer) for ix, iy, layer in path
        ]
        if not pts:
            return [], []
        (gx, gy), layer0 = pts[0]
        (ex, ey), layer1 = pts[-1]
        if not self._stub_clear(x1, y1, gx, gy, layer0, net, half):
            return None
        if not self._stub_clear(ex, ey, x2, y2, layer1, net, half):
            return None
        add_ortho(x1, y1, gx, gy, layer0)
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
        # Layer changes that are not on one of this net's own thru-hole pads
        # need a drilled via; the A* only chose them where nothing else worked.
        for step_a, step_b in zip(path, path[1:]):
            if step_a[2] == step_b[2]:
                continue
            ix, iy = step_a[0], step_a[1]
            if self._can_pin_hop(ix, iy, net):
                continue
            vx, vy = self._xy(ix, iy)
            vias.append(Via(vx, vy, net, VIA_DRILL, VIA_SIZE))
            self.mark_via(vx, vy, net)
        return segs, vias


# --- exact geometric clearance -------------------------------------------
# The occupancy grid stores one net id per cell, so it cannot express "this
# cell is 0.30 mm from a 0.70 mm track". Every clearance and shorting error
# KiCad found came from that one limitation. The grid stays as the *search*
# heuristic; this index is the gate that decides whether an emitted path is
# actually legal, measured on real geometry with real widths.

POWER_CLEARANCE_NETS = frozenset(
    {"+12V", "+12V_RAW", "+12V_SNS", "+5V", "+3V3", "GND",
     "/MotA1", "/MotA2", "/MotB1", "/MotB2",
     "/MotDC1_A", "/MotDC1_B", "/MotDC2_A", "/MotDC2_B",
     "/MotDC3_A", "/MotDC3_B"}
)
DEFAULT_CLEARANCE_MM = 0.20
POWER_NETCLASS_CLEARANCE_MM = 0.25


def pair_clearance(name_a: str, name_b: str) -> float:
    """Clearance KiCad will demand between two nets (widest netclass wins)."""
    if name_a in POWER_CLEARANCE_NETS or name_b in POWER_CLEARANCE_NETS:
        return POWER_NETCLASS_CLEARANCE_MM
    return DEFAULT_CLEARANCE_MM


def _seg_seg_dist(a1, a2, b1, b2) -> float:
    """Shortest distance between two line segments."""
    def pt_seg(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        ln2 = dx * dx + dy * dy
        if ln2 < 1e-15:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ln2))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    d1 = (a2[0] - a1[0], a2[1] - a1[1])
    d2 = (b2[0] - b1[0], b2[1] - b1[1])
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denom) > 1e-12:
        r = (b1[0] - a1[0], b1[1] - a1[1])
        t = (r[0] * d2[1] - r[1] * d2[0]) / denom
        u = (r[0] * d1[1] - r[1] * d1[0]) / denom
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            return 0.0  # they intersect
    return min(
        pt_seg(a1[0], a1[1], b1[0], b1[1], b2[0], b2[1]),
        pt_seg(a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]),
        pt_seg(b1[0], b1[1], a1[0], a1[1], a2[0], a2[1]),
        pt_seg(b2[0], b2[1], a1[0], a1[1], a2[0], a2[1]),
    )


class CopperIndex:
    """Spatial hash of placed copper, for exact pairwise clearance tests."""

    CELL = 4.0

    def __init__(self) -> None:
        self.by_cell: dict[tuple[int, int, int], list] = defaultdict(list)

    def _cells(self, x1, y1, x2, y2, pad):
        ix0 = int(math.floor((min(x1, x2) - pad) / self.CELL))
        ix1 = int(math.floor((max(x1, x2) + pad) / self.CELL))
        iy0 = int(math.floor((min(y1, y2) - pad) / self.CELL))
        iy1 = int(math.floor((max(y1, y2) + pad) / self.CELL))
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                yield ix, iy

    def add(self, seg: Seg, name: str) -> None:
        li = 0 if seg.layer == "F.Cu" else 1
        rec = ((seg.x1, seg.y1), (seg.x2, seg.y2), seg.width * 0.5, seg.net, name)
        for ix, iy in self._cells(seg.x1, seg.y1, seg.x2, seg.y2, seg.width):
            self.by_cell[(li, ix, iy)].append(rec)

    def clear_net(self, nets: set[int]) -> None:
        for k, lst in list(self.by_cell.items()):
            keep = [r for r in lst if r[3] not in nets]
            if keep:
                self.by_cell[k] = keep
            else:
                del self.by_cell[k]

    def conflicts(self, seg: Seg, name: str) -> bool:
        li = 0 if seg.layer == "F.Cu" else 1
        half = seg.width * 0.5
        seen: set[int] = set()
        for ix, iy in self._cells(seg.x1, seg.y1, seg.x2, seg.y2, half + 1.0):
            for rec in self.by_cell.get((li, ix, iy), ()):
                if rec[3] == seg.net or id(rec) in seen:
                    continue
                seen.add(id(rec))
                need = half + rec[2] + pair_clearance(name, rec[4])
                if _seg_seg_dist((seg.x1, seg.y1), (seg.x2, seg.y2), rec[0], rec[1]) < need:
                    return True
        return False

    def path_ok(self, segs: list, name: str) -> bool:
        """Would this whole path clear everything already placed?"""
        return not any(self.conflicts(sg, name) for sg in segs)


def _stub_legs(xa, ya, xb, yb) -> list[tuple[float, float, float, float]]:
    """Ortho legs joining a pad centre to a grid cell (L-shaped when needed)."""
    if abs(xa - xb) < 1e-9 and abs(ya - yb) < 1e-9:
        return []
    if abs(ya - yb) < 1e-9 or abs(xa - xb) < 1e-9:
        return [(xa, ya, xb, yb)]
    return [(xa, ya, xb, ya), (xb, ya, xb, yb)]


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
        # A6 wants wa/2 + wb/2 + TRACE_CLEARANCE between two signal tracks, and
        # the maze can only place them a grid pitch apart. At 0.4 mm two motor
        # tracks on neighbouring columns need 0.60 mm and only get 0.55 — every
        # parallel run was a violation. 0.34 keeps the pair legal (0.54 < 0.55)
        # and still carries the stepper phase current on 1 oz copper.
        return MAX_SIGNAL_WIDTH
    return 0.28


def route_priority(net: int, name: str) -> tuple:
    """Signals first (thin), then motors, then fat power last.

    Class and width only — no net id. With the id in here the tuple was a
    total order over every net all by itself, so the edge length that the
    callers sort on next never had any say and every ordering strategy
    collapsed onto the same sequence.
    """
    w = net_width(net, name)
    if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
        return (3, -w)
    if name in ("+5V", "+3V3", "+12V", "+12V_SNS", "/BLW_RET") or net in (
        3,
        4,
        46,
        56,
        61,
    ):
        return (2, -w)
    if "MotDC" in name or name.startswith("/MotA") or name.startswith("/MotB"):
        return (1, -w)
    return (0, -w)


_ORDER_NAMES = ("short-first", "losers-first", "long-first", "losers+short", "shuffled")


def _order_jobs(jobs: list, boost: set[int], attempt: int) -> list:
    """Order one routing pass.

    A single greedy order has one fixed point: re-running it reproduces the
    same losers. Each attempt therefore uses a different strategy, and the
    caller keeps whichever pass came out best. Shortest-first stays the
    default — it is what stops an 11 mm connection from being detoured across
    the board by a 120 mm one that grabbed the corridor first.
    """
    mode = _ORDER_NAMES[attempt % len(_ORDER_NAMES)]
    if mode == "short-first":
        key = lambda t: (t[0], t[1], t[2])
    elif mode == "losers-first":
        key = lambda t: (t[0], 0 if t[2] in boost else 1, t[1], t[2])
    elif mode == "long-first":
        key = lambda t: (t[0], -t[1], t[2])
    elif mode == "losers+short":
        key = lambda t: (t[0], t[1] * (BOOST_SCALE if t[2] in boost else 1.0), t[2])
    else:  # deterministic shuffle, biased towards the losers
        rnd = random.Random(1000 + attempt)
        jitter = {j[2]: rnd.random() for j in jobs}
        key = lambda t: (
            t[0],
            t[1] * (BOOST_SCALE if t[2] in boost else 1.0) * (0.5 + jitter[t[2]]),
            t[2],
        )
    return sorted(jobs, key=key)


def _dedupe_pads(pads: list[Pad]) -> list[Pad]:
    uniq: list[Pad] = []
    for p in pads:
        if any(abs(p.x - q.x) < 0.35 and abs(p.y - q.y) < 0.35 for q in uniq):
            continue
        uniq.append(p)
    return uniq


def parse_segments(pcb_text: str) -> list[Seg]:
    table = NetTable(pcb_text)
    segs: list[Seg] = []
    for m in re.finditer(
        r"\(segment\s+"
        r"\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+"
        r"\(end\s+([\d.-]+)\s+([\d.-]+)\)\s+"
        r"\(width\s+([\d.-]+)\)\s+"
        r'\(layer\s+"([^"]+)"\)\s+'
        r"(\(net\s+(?:\d+|\"[^\"]*\")\s*\))",
        pcb_text,
        re.S,
    ):
        nid, _ = seg_net(m.group(7), table)
        segs.append(
            Seg(
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                m.group(6),
                nid,
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
    vias: list[tuple[float, float, int, float]] | None = None,
) -> MazeRouter:
    router = MazeRouter(x0, y0, board_w, board_h, grid=grid, clearance=clearance)
    if hole_sites:
        router.add_hole_sites(hole_sites)
    for p in pads:
        router.add_pad(p)
    router.add_edge_keepout(EDGE_CLEARANCE_MM + WIDE_HALF_TRACK)
    # Vias placed by the maze are drilled holes like any other: later bus and
    # repair lanes have to respect their copper and their A7 keepout.
    for vx, vy, vnet, _vsize in vias or []:
        router.mark_via(vx, vy, vnet)
    _apply_segments(router, segs)
    names = {p.net: p.name for p in pads}
    for sg in segs:
        router.copper.add(sg, names.get(sg.net, ""))
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
    xbuses = tuple(
        router.snap(x, y0)[0]
        for x in (x0 + 2.0, x0 + bw * 0.25, x0 + bw * 0.5, x0 + bw * 0.75, x0 + bw - 2.0)
    )
    ybuses = tuple(
        router.snap(x0, y)[1]
        for y in (y0 + 2.0, y0 + bh * 0.25, y0 + bh * 0.5, y0 + bh * 0.75, y0 + bh - 2.0)
    )

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


def _join_hops(router, p1, p2, net: int, net_name: str):
    """Concatenate two half-routes, bridging a layer change with a via.

    A waypoint route is two separate A* results. Nothing makes them end and
    start on the same face, and a bare concatenation across faces leaves the
    board with a track that stops on one layer and resumes on the other with
    no copper joining them.
    """
    segs = p1[0] + p2[0]
    vias = list(p1[1]) + list(p2[1])
    if p1[0] and p2[0]:
        end, start = p1[0][-1], p2[0][0]
        if end.layer != start.layer:
            jx, jy = end.x2, end.y2
            if abs(jx - start.x1) > 1e-6 or abs(jy - start.y1) > 1e-6:
                return None
            ix, iy = router._cell(jx, jy)
            if router._can_pin_hop(ix, iy, net):
                pass  # a real pad already bridges the faces here
            elif router._can_drop_via(ix, iy, net):
                vx, vy = router._xy(ix, iy)
                vias.append(Via(vx, vy, net, VIA_DRILL, VIA_SIZE))
                router.mark_via(vx, vy, net)
            else:
                return None
    if not router.copper.path_ok(segs, net_name):
        return None
    return (segs, vias)


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

    def accept(path, snap):
        """Take a candidate only if real geometry says it clears everything.

        The grid search reasons in whole cells, so it happily places a 0.7 mm
        rail one 0.55 mm pitch from a signal whose copper it then overlaps.
        This is the gate that actually decides.
        """
        if path is None:
            router.restore(snap)
            return None
        if not router.copper.path_ok(path[0], net_name):
            router.restore(snap)
            return None
        return path

    def astar(tw: float, layer: int, both: bool, budget: int | None, via: bool = False):
        snap = router.snapshot()
        path = router.find_path(
            a.x, a.y, b.x, b.y, net, tw,
            prefer_layer=layer, both_layers=both, max_expand=budget,
            allow_via=via,
        )
        return accept(path, snap)

    # Phase 1 — cheap first fit. A short budget keeps the common case fast.
    for tw in widths:
        path = astar(tw, prefer, False, QUICK_EXPAND)
        if path is not None:
            return path
    if not (dc or tft_enc):
        for tw in widths:
            path = astar(tw, alt, False, QUICK_EXPAND)
            if path is not None:
                return path
    if not dc:
        for tw in widths:
            path = astar(tw, prefer, True, QUICK_EXPAND)
            if path is not None:
                return path

    # Phase 2 — full search before falling back to fixed bus shapes. Detours
    # round the socket cost far more than the quick budget allows, and giving
    # up here is what left those nets for the crude fallbacks below.
    for layer, both in ((prefer, True), (alt, True), (prefer, False), (alt, False)):
        for tw in widths:
            path = astar(tw, layer, both, None)
            if path is not None:
                return path

    for tw in (0.22, 0.18):
        snap = router.snapshot()
        path = accept(_try_bus_route(router, a, b, net, tw), snap)
        if path is not None:
            return path
    # edge + corner waypoints
    for mx, my in [
        router.snap(wx, wy)
        for wx, wy in (
            (x0 + board_w - 2.5, 0.5 * (a.y + b.y)),
            (x0 + 2.5, 0.5 * (a.y + b.y)),
            (0.5 * (a.x + b.x), y0 + 2.5),
            (0.5 * (a.x + b.x), y0 + board_h - 2.5),
            (x0 + board_w - 2.5, y0 + 2.5),
            (x0 + 2.5, y0 + board_h - 2.5),
            (x0 + board_w - 2.5, y0 + board_h - 2.5),
            (x0 + 2.5, y0 + 2.5),
        )
    ]:
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
        # The two halves are independent searches: if one ends on F.Cu and the
        # next starts on B.Cu, joining them is a layer change with nothing
        # bridging it — KiCad reports exactly that as dangling + unconnected.
        joined = _join_hops(router, p1, p2, net, net_name)
        if joined is None:
            router.restore(snap)
            continue
        return joined
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
            joined = _join_hops(router, p1, p2, net, net_name)
            if joined is None:
                router.restore(snap)
                continue
            return joined

    # Phase 3 — last resort: let the search buy a via. Priced at VIA_COST so it
    # is only taken where no same-layer way round exists at all, which holds
    # the count down to the few nets that genuinely need one.
    for layer in (prefer, alt):
        for tw in widths:
            path = astar(tw, layer, True, None, via=True)
            if path is not None:
                return path
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
    def rebuild(keep_segs: list[Seg], keep_vias: list[Via] | None = None) -> MazeRouter:
        r = MazeRouter(x0, y0, board_w, board_h, grid=grid, clearance=MAZE_CLEARANCE_MM)
        if hole_sites:
            r.add_hole_sites(hole_sites)
        for p in pads:
            r.add_pad(p)
        r.add_edge_keepout(EDGE_CLEARANCE_MM + WIDE_HALF_TRACK)
        for v in keep_vias or []:
            r.mark_via(v.x, v.y, v.net)
        for s in keep_segs:
            li = LAYER_F if s.layer == "F.Cu" else LAYER_B
            r._mark_seg(li, s.x1, s.y1, s.x2, s.y2, s.width * 0.5, s.net)
            r.copper.add(s, net_name_of.get(s.net, ""))
        return r

    net_name_of = {p.net: p.name for p in pads}
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

    def _route_pass(
        boost: set[int], attempt: int
    ) -> tuple[list[Seg], list[Via], list, int]:
        """One full routing pass; nets in `boost` get first pick of the board."""
        r = rebuild([])
        segs_out: list[Seg] = []
        vias_out: list[Via] = []
        failed_out: list = []
        n = 0
        ordered = _order_jobs(jobs, boost, attempt)
        for i, (_pri, _dist, net, name, a, b, uniq) in enumerate(ordered, 1):
            if i % 40 == 0:
                print(f"  … routed {n}/{i} edges, failed {len(failed_out)}")
            w = net_width(net, name)
            path = _try_route(
                r, a, b, net, w, x0, y0, board_w, board_h, bridges=uniq, net_name=name
            )
            if path is None:
                failed_out.append((net, name, (a.x, a.y), (b.x, b.y)))
                continue
            segs, vias = path
            for sg in segs:
                r.copper.add(sg, name)
            segs_out.extend(segs)
            vias_out.extend(vias)
            n += 1
        return segs_out, vias_out, failed_out, n

    def _ripup_improve(
        segs_in: list[Seg], vias_in: list[Via], failed_in: list, n_in: int
    ) -> tuple[list[Seg], list[Via], list, int]:
        """Clear the neighbourhood of each failed edge and re-route it first."""
        cur = (list(segs_in), list(vias_in), list(failed_in), n_in)
        local_best = cur
        for rnd in range(RIPUP_ROUNDS):
            segs_cur, vias_cur, failed_cur, _ = cur
            if not failed_cur:
                break
            bad = {n for n, _, _, _ in failed_cur}
            margin = RIPUP_MARGIN_MM * (rnd + 1)
            boxes = [
                (min(ax, bx) - margin, min(ay, by) - margin,
                 max(ax, bx) + margin, max(ay, by) + margin)
                for _n, _nm, (ax, ay), (bx, by) in failed_cur
            ]
            victims = set(bad)
            for s in segs_cur:
                if s.net in victims:
                    continue
                sx0, sx1 = min(s.x1, s.x2), max(s.x1, s.x2)
                sy0, sy1 = min(s.y1, s.y2), max(s.y1, s.y2)
                if any(
                    sx1 >= bx0 and sx0 <= bx1 and sy1 >= by0 and sy0 <= by1
                    for bx0, by0, bx1, by1 in boxes
                ):
                    victims.add(s.net)
            keep = [s for s in segs_cur if s.net not in victims]
            keep_vias = [v for v in vias_cur if v.net not in victims]
            retry_jobs = sorted(
                (j for j in jobs if j[2] in victims),
                key=lambda j: (0 if j[2] in bad else 1, j[0], j[1], j[2]),
            )
            print(
                f"    rip-up {rnd + 1}: {len(bad)} failed nets, "
                f"{len(victims)} nets ripped up"
            )
            r = rebuild(keep, keep_vias)
            segs_new = list(keep)
            vias_new = list(keep_vias)
            failed_new: list = []
            n_new = sum(1 for j in jobs if j[2] not in victims)
            for _pri, _dist, net, name, a, b, uniq in retry_jobs:
                w = net_width(net, name)
                if name in ("+12V", "+12V_RAW", "GND") or net in (1, 2, 57):
                    w = min(w, 0.45)  # thinner on rip-up — less blockage
                path = _try_route(
                    r, a, b, net, w, x0, y0, board_w, board_h,
                    bridges=uniq, net_name=name,
                )
                if path is None:
                    failed_new.append((net, name, (a.x, a.y), (b.x, b.y)))
                    continue
                segs, vias = path
                for sg in segs:
                    r.copper.add(sg, name)
                segs_new.extend(segs)
                vias_new.extend(vias)
                n_new += 1
            cur = (segs_new, vias_new, failed_new, n_new)
            if len(failed_new) < len(local_best[2]):
                local_best = cur
        return local_best

    # A single greedy pass leaves whichever nets lost the race for a corridor
    # unrouted, and re-trying just those against the same copper reproduces the
    # same failure. So do both: re-run the whole pass with the losers promoted
    # to the head of the order (accumulating across attempts), and after each
    # pass clear the neighbourhood of whatever still fails and re-route it
    # first. Keep the best board any attempt produced — a rip-up round can
    # trade one failure for two, and the caller only wants the winner.
    result = RouteResult()
    boost: set[int] = set()
    best: tuple[list[Seg], list[Via], list, int] | None = None
    for attempt in range(ROUTE_ATTEMPTS):
        segs_out, vias_out, failed_out, n_ok = _route_pass(boost, attempt)
        print(
            f"  Pass {attempt + 1} ({_ORDER_NAMES[attempt % len(_ORDER_NAMES)]}): "
            f"{len(failed_out)} failed edges after first fit"
        )
        segs_out, vias_out, failed_out, n_ok = _ripup_improve(
            segs_out, vias_out, failed_out, n_ok
        )
        if best is None or len(failed_out) < len(best[2]):
            best = (segs_out, vias_out, failed_out, n_ok)
        if not failed_out:
            break
        newly = {n for n, _, _, _ in failed_out} - boost
        print(
            f"  Pass {attempt + 1}: {len(failed_out)} failed edges "
            f"(best {len(best[1])}), promoting {len(newly)} more net(s)"
        )
        boost |= newly
    result.segments = list(best[0])
    result.vias = list(best[1])
    result.failed = list(best[2])
    n_ok = best[3]

    print(
        f"Maze policy: vias only where no same-layer route exists; free F/B; "
        f"{n_ok} edges routed, {len(result.vias)} via(s), "
        f"{len(result.failed)} failed"
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
        # Step by a whole grid pitch, not 0.35. The occupancy grid cannot tell
        # two lanes 0.35 mm apart from each other — both fall inside one cell —
        # so it waved through pairs that A6 then flagged as too close.
        xr = round(x, 2)
        while any(abs(xr - r) < LANE_MIN_SEP for r in self.reserved_x):
            x += LANE_MIN_SEP
            xr = round(x, 2)
        self.reserved_x.add(xr)
        return x

    def _free_y(self, y: float) -> float:
        yr = round(y, 2)
        while any(abs(yr - r) < LANE_MIN_SEP for r in self.reserved_y):
            y += LANE_MIN_SEP
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
    bus_x = router.snap(bus_x, ay)[0]
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
        hole_sites=hole_sites, vias=parse_kept_vias(pcb_text),
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
        hole_sites=parse_hole_sites(pcb_text), vias=parse_kept_vias(pcb_text),
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
    for v in result.vias:
        lines += [
            "\t(via",
            f"\t\t(at {v.x:.4f} {v.y:.4f})",
            f"\t\t(size {v.size})",
            f"\t\t(drill {v.drill})",
            '\t\t(layers "F.Cu" "B.Cu")',
            f"\t\t(net {v.net})",
            f'\t\t(uuid "{uid_fn()}")',
            "\t)",
        ]
    return lines


def inject_routes(pcb_text: str, route_lines: list[str]) -> str:
    if not route_lines:
        return pcb_text
    block = "\n" + "\n".join(route_lines) + "\n"
    idx = pcb_text.rstrip().rfind(")")
    if idx < 0:
        return pcb_text + block
    return pcb_text[:idx] + block + pcb_text[idx:]
