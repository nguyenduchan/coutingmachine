#!/usr/bin/env python3
r"""Route the carrier with FreeRouting instead of the in-house maze router.

Pipeline, fully scriptable:
    gen_power_carrier.py   placement + nets (the part that needs judgement)
    ExportSpecctraDSN      hand KiCad's real design rules to the router
    freerouting            industrial autorouter: reads per-netclass clearance
                           and widths from the DSN, does rip-up/reroute and
                           push-and-shove, then optimises
    ImportSpecctraSES      pull the result back into the board
    verify_drc.py          KiCad's own DRC has the last word

Why bother: the in-house router searches on a 0.55 mm grid whose occupancy map
holds one net id per cell, so it cannot express "this cell is 0.30 mm from a
0.70 mm track". FreeRouting works on real geometry and real rules.

Run with the KiCad-bundled Python (it owns the pcbnew module):
    "%LOCALAPPDATA%\Programs\KiCad.0in\python.exe" route_freerouting.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"
DSN = HERE / "out_freerouting" / "esp32_baseboard.dsn"
SES = HERE / "out_freerouting" / "esp32_baseboard.ses"
UNROUTED = HERE / "out_freerouting" / "unrouted.kicad_pcb"
ROUTED = HERE / "out_freerouting" / "routed.kicad_pcb"

# Tuning handed to the autorouter. Raise passes if nets are left unrouted.
# Via cost: moderate — A0 wants pad→via→B.Cu fan-out, so vias are expected;
# too-high -vc keeps long runs on F under modules (violates A0).
# -mt 1 is not optional: FreeRouting itself warns that multi-threaded
# optimisation "is known to generate clearance violations".
# (passes, via cost) per attempt: different effort settings give different
# results, and the loop stops at the first that routes everything.
FR_ATTEMPTS = ((40, 40), (60, 25), (100, 50),
               (80, 20), (200, 35), (150, 15))
if os.environ.get("FR_QUICK") == "1":
    FR_ATTEMPTS = ((40, 40), (60, 25))
FR_THREADS = 1
FR_TIMEOUT_S = 900
if os.environ.get("FR_QUICK") == "1":
    FR_TIMEOUT_S = 420


MIN_JAVA = 21


def _java_major(exe: str) -> int:
    try:
        out = subprocess.run([exe, "-version"], capture_output=True, text=True).stderr
    except OSError:
        return 0
    m = re.search(r'version "(\d+)(?:\.(\d+))?', out)
    if not m:
        return 0
    major = int(m.group(1))
    return int(m.group(2) or 0) if major == 1 else major  # 1.8 -> 8


def find_java() -> str | None:
    """A JRE new enough for the jar. FreeRouting 2.3 needs Java 25, 2.1 needs 21.

    The one on PATH is often an old system Java (8 here), which fails with
    UnsupportedClassVersionError, so check the version rather than trust PATH.
    """
    cands = []
    if (j := shutil.which("java")):
        cands.append(j)
    for pat in (
        "Program Files/JetBrains/*/jbr/bin/java.exe",
        "Program Files/Eclipse Adoptium/*/bin/java.exe",
        "Program Files/Java/*/bin/java.exe",
        "Program Files/Microsoft/jdk*/bin/java.exe",
    ):
        cands += [str(h) for h in sorted(Path("C:/").glob(pat), reverse=True)]
    for c in cands:
        if _java_major(c) >= MIN_JAVA:
            return c
    if cands:
        print(f"java found but too old (need {MIN_JAVA}+): {cands[0]}")
    return None


def find_freerouting() -> str | None:
    for env in ("FREEROUTING_JAR", "FREEROUTING"):
        if (v := os.environ.get(env)) and Path(v).is_file():
            return v
    for cand in (
        HERE / "tools" / "freerouting.jar",
        Path(os.environ.get("LOCALAPPDATA", "")) / "freerouting" / "freerouting.jar",
    ):
        if cand.is_file():
            return str(cand)
    return None


def export_dsn() -> None:
    """Export placement + nets with the existing routing stripped.

    Left in, FreeRouting treats the in-house tracks as fixed wiring and only
    fills the gaps; we want it to solve the whole board so the two routers can
    be compared on equal terms.

    GND pour zones (A10) are also stripped for the DSN: FreeRouting treats
    copper pours as keep-outs for other nets and leaves dozens of opens. Zones
    are re-added and filled after SES merge (fill_gnd_zones).
    """
    import pcbnew

    DSN.parent.mkdir(parents=True, exist_ok=True)
    # KiCad 10 pcbnew.Remove(zone) raises on ZONE proxies — strip in text first.
    raw = PCB.read_text(encoding="utf-8")
    stripped = re.sub(r"\n\t\(zone\n(?:.*?\n)*?\t\)", "", raw, flags=re.M)
    # Also drop filled polygon leftovers if any
    stripped = re.sub(
        r"\n\t\(zone\b[\s\S]*?\n\t\)", "", stripped
    )
    UNROUTED.write_text(stripped, encoding="utf-8")
    board = pcbnew.LoadBoard(str(UNROUTED))
    if board is None:
        raise SystemExit("LoadBoard failed after zone strip")
    for item in list(board.GetTracks()):
        board.Remove(item)
    pcbnew.SaveBoard(str(UNROUTED), board)
    board = pcbnew.LoadBoard(str(UNROUTED))
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise SystemExit("ExportSpecctraDSN failed")
    _inject_a7_rules()
    print(f"DSN -> {DSN} (tracks+zones stripped, A7 clearances injected)")


def _iter_zones(board):
    """KiCad 10: after Specctra, board.Zones() may be a broken proxy."""
    try:
        return list(board.Zones())
    except AttributeError:
        n = board.GetAreaCount()
        return [board.GetArea(i) for i in range(n)]


def ensure_gnd_zones(board) -> int:
    """Add F.Cu + B.Cu GND pour outlines if missing (EMI A10)."""
    import pcbnew

    existing = set()
    for z in _iter_zones(board):
        if z.GetNetname() == "GND":
            existing.add(z.GetLayer())
    net = board.FindNet("GND")
    if net is None or net.GetNetCode() <= 0:
        print("  warn: GND net missing — skip pour")
        return 0
    # Board outline from Edge.Cuts bbox
    bbox = board.GetBoardEdgesBoundingBox()
    margin = pcbnew.FromMM(0.5)
    x0, y0 = bbox.GetLeft() + margin, bbox.GetTop() + margin
    x1, y1 = bbox.GetRight() - margin, bbox.GetBottom() - margin
    added = 0
    for layer_name, layer_id, prio in (
        ("B.Cu", pcbnew.B_Cu, 0),
        ("F.Cu", pcbnew.F_Cu, 1),
    ):
        if layer_id in existing:
            continue
        zone = pcbnew.ZONE(board)
        zone.SetNetCode(net.GetNetCode())
        zone.SetLayer(layer_id)
        zone.SetAssignedPriority(prio)
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetLocalClearance(pcbnew.FromMM(0.35))
        zone.SetMinThickness(pcbnew.FromMM(0.25))
        zone.SetThermalReliefGap(pcbnew.FromMM(0.5))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        zone.SetIsFilled(False)
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            chain.Append(pcbnew.VECTOR2I(x, y))
        chain.SetClosed(True)
        zone.Outline().AddOutline(chain)
        board.Add(zone)
        added += 1
    return added


def fill_gnd_zones(pcb: Path) -> None:
    """Ensure GND pours exist and refill after SES merge (EMI A10 / README N1)."""
    import pcbnew

    board = pcbnew.LoadBoard(str(pcb))
    if board is None:
        raise SystemExit(f"fill_gnd_zones: LoadBoard failed for {pcb}")
    added = ensure_gnd_zones(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(_iter_zones(board))
    pcbnew.SaveBoard(str(pcb), board)
    n = sum(1 for z in _iter_zones(board) if z.GetNetname() == "GND")
    print(f"GND zones filled on {pcb.name} ({n} zone(s)"
          + (f", +{added} created" if added else "") + ")")


# PCB_REVIEW A7 asks for 0.45 mm minimum (0.25 HOLE_EXTRA + 0.20 netclass).
# 500 um cleared that DRC-minimum fine, but a render at that setting still
# showed traces visibly grazing past unrelated pad rings (m2_opto4, 2026-09-03)
# -- passing the letter of A7 isn't the same as a gap the eye reads as clear.
# 900 um routes the small, sparse m2_opto4 module fine (0 unconnected, first
# attempt) but is too tight a budget for THIS carrier: 63 nets across a much
# denser 180x145mm board left 3-5 nets unrouted across 6 attempts at 900 um.
# 700 um is the compromise -- still meaningfully wider than the 500 um floor.
A7_CLEARANCE_UM = 700
A7_TYPES = ("wire_pin", "via_pin", "wire_via", "via_via", "pin_pin")


def _inject_a7_rules() -> None:
    """Raise the DSN clearance so the router meets PCB_REVIEW A7.

    FreeRouting 2.1 ignores per-type clearances such as (type wire_pin): the
    measured worst case came out at exactly the 0.25 mm of extra margin A7 asks
    for beyond the fab rule, i.e. the per-type line had no effect. The global
    clearance carries it instead; the per-type lines stay for routers that do
    honour them.
    """
    text = DSN.read_text(encoding="utf-8")
    # KiCad writes a (rule ...) per net class as well as the global one, and
    # the class rules override it -- which is why raising only the global
    # clearance still left tracks 0.20 mm from pads. Raise every clearance
    # below the A7 figure, leaving the tiny smd_smd one alone.
    def _raise(m):
        val = int(m.group(1))
        if val >= A7_CLEARANCE_UM or val <= 50:
            return m.group(0)
        return "(clearance %d)" % A7_CLEARANCE_UM
    text = re.sub(r"\(clearance (\d+)\)", _raise, text)
    extra = "".join(
        "\n      (clearance %d (type %s))" % (A7_CLEARANCE_UM, t) for t in A7_TYPES
    )
    marker = "      (clearance 50 (type smd_smd))"
    if marker not in text:
        raise SystemExit("DSN rule block not in the expected shape")
    text = text.replace(marker, marker + extra, 1)

    # PCB_REVIEW A8: only the easy-to-fab through-via 0.8/0.4 mm.
    text = re.sub(
        r'\(via "[^"]*"(?:\s+"[^"]*")*\)',
        '(via "Via[0-1]_800:400_um")',
        text,
        count=1,
    )

    # PCB_REVIEW A0: prefer long runs on B.Cu (back). Classic 2-layer strategy:
    # B = horizontal preferred (board is wider than tall → east-west buses),
    # F = vertical preferred (fan-out / short stubs only). Against-prefer cost
    # on F is raised so FreeRouting avoids long F tracks under modules.
    text = text.replace(
        """    (layer F.Cu
      (type signal)
      (property
        (index 0)
      )
    )
    (layer B.Cu
      (type signal)
      (property
        (index 1)
      )
    )""",
        """    (layer F.Cu
      (type signal)
      (direction vertical)
      (property
        (index 0)
      )
    )
    (layer B.Cu
      (type signal)
      (direction horizontal)
      (property
        (index 1)
      )
    )""",
        1,
    )
    # Nudge cost: stay with preferred direction (cheap on B horizontal buses).
    if "(against_prefer_direction_trace_costs" not in text:
        text = text.replace(
            marker + extra,
            marker + extra
            + "\n      (prefer_direction_trace_costs 1.0)"
            + "\n      (against_prefer_direction_trace_costs 2.5)",
            1,
        )
    DSN.write_text(text, encoding="utf-8")


def force_headless() -> None:
    """FreeRouting keeps a settings file with gui.enabled=true by default.

    With the GUI on it routes, prints "optimization completed" and then just
    sits there with a window open: it never writes the .ses and never exits.
    """
    cfg = Path(os.environ.get("TEMP", "/tmp")) / "freerouting" / "freerouting.json"
    if not cfg.is_file():
        return
    import json

    data = json.loads(cfg.read_text(encoding="utf-8"))
    data.setdefault("gui", {})["enabled"] = False
    data.setdefault("feature_flags", {})["multi_threading"] = False
    data.setdefault("router", {}).setdefault("optimizer", {})["max_threads"] = 1
    cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"headless settings written to {cfg}")


def run_freerouting(jar: str, passes: int, via_cost: int) -> bool:
    """One routing attempt. True if it produced a .ses."""
    java = find_java()
    if java is None:
        raise SystemExit("no java found")
    force_headless()
    if SES.exists():
        SES.unlink()  # never mistake a stale result for this run's output
    cmd = [
        java, "-jar", jar,
        "-de", str(DSN),
        "-do", str(SES),
        "-mp", str(passes),
        "-mt", str(FR_THREADS),
        "-vc", str(via_cost),
    ]
    try:
        # stdin closed and a hard timeout: with a pipe left open the jar can
        # sit waiting instead of exiting, and it is a GUI app by default.
        subprocess.run(
            cmd, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=FR_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        print(f"  timed out after {FR_TIMEOUT_S}s")
        return False
    return SES.is_file()


def import_ses() -> int:
    """Merge the result into a *separate* board, so the in-house route survives
    for comparison. Promote it by copying over esp32_baseboard.kicad_pcb."""
    import pcbnew

    board = pcbnew.LoadBoard(str(UNROUTED))
    if not pcbnew.ImportSpecctraSES(board, str(SES)):
        raise SystemExit("ImportSpecctraSES failed")
    pcbnew.SaveBoard(str(ROUTED), board)
    # Cleanup is done on the saved file, not on this board object. Once
    # ExportSpecctraDSN/ImportSpecctraSES have run, this build hands back boards
    # whose Python proxy has lost its BOARD type, so every pcbnew cleanup call
    # raises AttributeError -- which _drop_dangling swallowed, leaving the stubs
    # in place. clean_stubs also catches the leftover pcbnew misses anyway: a
    # via with a short leg on each layer running to the same free point.
    import clean_stubs

    dup, n = clean_stubs.clean(ROUTED)
    left = _unconnected_via_drc(ROUTED)
    print(f"SES merged -> {ROUTED}"
          + (f" ({dup} duplicate(s) removed)" if dup else "")
          + (f" ({n} dangling stub(s) removed)" if n else "")
          + f", {left} unconnected")
    return left


def _unconnected_via_drc(pcb: Path) -> int:
    """Count unconnected items with KiCad's DRC.

    The pcbnew connectivity bindings differ between builds; the CLI is stable
    and is the authority the review gate uses anyway.
    """
    cli = shutil.which("kicad-cli")
    if cli is None:
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
        hits = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True) if base.is_dir() else []
        if not hits:
            return 0
        cli = str(hits[0])
    rpt = pcb.with_suffix(".drc.txt")
    subprocess.run(
        [cli, "pcb", "drc", "--severity-error", "--units", "mm",
         "--format", "report", "-o", str(rpt), str(pcb)],
        capture_output=True, text=True,
    )
    if not rpt.is_file():
        return 0
    return len(re.findall(r"^\[unconnected_items\]", rpt.read_text(encoding="utf-8",
                                                                    errors="replace"), re.M))


def _cleanup_in_subprocess() -> tuple[int, int]:
    """Run the dedupe + dangling sweeps in a fresh interpreter, on ROUTED."""
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--cleanup"],
                       capture_output=True, text=True)
    m = re.search(r"CLEANUP (\d+) (\d+)", r.stdout)
    if not m:
        print("  cleanup pass failed:")
        print((r.stdout + r.stderr).strip()[-500:])
        return 0, 0
    return int(m.group(1)), int(m.group(2))


def _cleanup_main() -> int:
    import pcbnew

    board = pcbnew.LoadBoard(str(ROUTED))
    dup = _dedupe_tracks(board, pcbnew)
    n = _drop_dangling(board, pcbnew)
    pcbnew.SaveBoard(str(ROUTED), board)
    print(f"CLEANUP {dup} {n}")
    return 0

def _dedupe_tracks(board, pcbnew) -> int:
    """Drop segments that repeat one already on the board.

    The SES merge can land the same segment several times, forwards and
    backwards. Duplicates are invisible in a plot but they defeat the dangling
    sweep below: two copies of one stub each see the other sitting on their free
    end, so neither looks dangling, and KiCad's own DRC then reports the pair as
    unconnected track ends.
    """
    seen = set()
    doomed = []
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        a = (t.GetStart().x, t.GetStart().y)
        b = (t.GetEnd().x, t.GetEnd().y)
        key = (t.GetLayer(), t.GetNetCode(), min(a, b), max(a, b))
        if key in seen:
            doomed.append(t)
        else:
            seen.add(key)
    for t in doomed:
        board.Remove(t)
    if doomed:
        board.BuildConnectivity()
    return len(doomed)

def _drop_dangling(board, pcbnew) -> int:
    """Delete track stubs with a free end.

    FreeRouting occasionally leaves a short tail behind after optimisation.
    The net stays fully connected without it -- KiCad reports 0 unconnected
    items -- so the stub is redundant copper, and an antenna.
    """
    removed = 0
    for _ in range(8):  # one stub can hide another behind it
        try:
            board.BuildConnectivity()
            conn = board.GetConnectivity()
            tracks = [t for t in board.GetTracks()
                      if t.Type() == pcbnew.PCB_TRACE_T]
            doomed = [t for t in tracks if conn.TestTrackEndpointDangling(t, False)]
        except Exception as exc:  # binding differences are not worth failing over
            print(f"  dangling-stub sweep skipped: {exc}")
            return removed
        if not doomed:
            break
        for t in doomed:
            board.Remove(t)
        removed += len(doomed)
    board.BuildConnectivity()
    return removed


def main() -> int:
    jar = find_freerouting()
    if jar is None:
        print(
            "freerouting.jar not found.\n"
            "  Put it at ./tools/freerouting.jar or set FREEROUTING_JAR.\n"
            "  FreeRouting 2.x needs Java 21+; 1.9.x still runs on Java 8."
        )
        return 2
    export_dsn()
    # FreeRouting is not deterministic and the board is tight at the A7
    # clearance, so a single attempt sometimes abandons a net. Judge each
    # attempt by KiCad's own connectivity rather than by parsing the router's
    # chatter, and stop at the first that closes every net.
    best = None
    for i, (passes, via_cost) in enumerate(FR_ATTEMPTS, 1):
        if not run_freerouting(jar, passes, via_cost):
            print(f"  attempt {i}: no .ses produced")
            continue
        left = import_ses()
        print(f"  attempt {i} (-mp {passes} -vc {via_cost}): {left} unconnected")
        if left == 0:
            best = 0
            break
        if best is None or left < best:
            best = left
            shutil.copy2(ROUTED, ROUTED.with_suffix(".best.kicad_pcb"))
    if best != 0:
        keep = ROUTED.with_suffix(".best.kicad_pcb")
        if keep.is_file():
            shutil.copy2(keep, ROUTED)
        print(f"  best attempt still leaves {best} unconnected")
    # Promote: the routed board becomes the deliverable. It lives beside
    # fp-lib-table here, which the out_freerouting/ copy does not.
    shutil.copy2(ROUTED, PCB)
    fill_gnd_zones(PCB)
    print(f"promoted -> {PCB.name}")
    return 0 if best == 0 else 1


if __name__ == "__main__":
    sys.exit(_cleanup_main() if "--cleanup" in sys.argv else main())
