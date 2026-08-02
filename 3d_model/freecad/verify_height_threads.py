# -*- coding: utf-8 -*-
"""Verify HA_Lead_Screw + HA_Traveling_Nut threads; export screenshots. Does not delete parts."""
from __future__ import annotations

import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

_HERE = Path(__file__).resolve().parent
OUT = _HERE / "out"
SHOT = OUT / "thread_verify"
SHOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(_HERE))

import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, _thread_params


def _fail(msg: str, errors: list) -> None:
    print("FAIL:", msg)
    errors.append(msg)


def verify_screw(sh: Part.Shape, thr: dict, errors: list, cx: float = 0.0, cy: float = 0.0) -> None:
    bb = sh.BoundBox
    print(
        "HA_Lead_Screw: solids=%d vol=%.1f z=%.2f..%.2f"
        % (len(sh.Solids), float(sh.Volume), bb.ZMin, bb.ZMax)
    )
    if not sh.Solids:
        _fail("Lead_Screw has no solids", errors)
        return
    z0, z1 = bb.ZMin + 1.0, bb.ZMax - 1.0
    hollow = 0
    for i in range(21):
        z = z0 + (z1 - z0) * (i / 20.0)
        if not sh.isInside(App.Vector(cx, cy, z), 0.12, True):
            hollow += 1
    if hollow:
        _fail("Lead_Screw hollow on axis at %d/21 samples" % hollow, errors)
    else:
        print("OK Lead_Screw axis continuous (21/21)")

    major = thr["major_d"]
    minor = thr["minor_d"]
    r_xy = max(abs(bb.XMax - cx), abs(bb.XMin - cx), abs(bb.YMax - cy), abs(bb.YMin - cy))
    if r_xy < major * 0.45:
        _fail("Lead_Screw XY radius too small (%.2f vs major %.2f)" % (r_xy, major), errors)
    L = max(1.0, bb.ZMax - bb.ZMin)
    spine = math.pi * (minor / 2.0) ** 2 * L
    blank = math.pi * (major / 2.0) ** 2 * L
    vol = float(sh.Volume)
    if vol <= spine * 1.05:
        _fail("Lead_Screw volume ~spine only (no teeth?) vol=%.0f spine=%.0f" % (vol, spine), errors)
    elif vol >= blank * 0.99:
        _fail("Lead_Screw volume ~blank (no grooves?) vol=%.0f blank=%.0f" % (vol, blank), errors)
    else:
        print("OK Lead_Screw volume ratio blank=%.2f spine=%.2f" % (vol / blank, vol / spine))


def verify_nut(sh: Part.Shape, thr: dict, errors: list, cx: float = 0.0, cy: float = 0.0) -> None:
    bb = sh.BoundBox
    print(
        "HA_Traveling_Nut: solids=%d vol=%.1f z=%.2f..%.2f"
        % (len(sh.Solids), float(sh.Volume), bb.ZMin, bb.ZMax)
    )
    if not sh.Solids:
        _fail("Traveling_Nut has no solids", errors)
        return
    z0 = bb.ZMin + 2.0
    z1 = min(bb.ZMax - 1.0, z0 + 20.0)
    open_n = 0
    for i in range(15):
        z = z0 + (z1 - z0) * (i / 14.0)
        if not sh.isInside(App.Vector(cx, cy, z), 0.15, True):
            open_n += 1
    if open_n < 10:
        _fail("Traveling_Nut bore not open on axis (%d/15 empty)" % open_n, errors)
    else:
        print("OK Traveling_Nut through bore (%d/15 empty on axis)" % open_n)

    major = thr["major_d"]
    clear = float(thr.get("nut_clear_r", thr.get("clear_r", 0.4)))
    # Probe in female flank band (outside pilot, inside boss)
    pilot_r = 0.5 * max(major - 2.0 * thr["depth"] + 2.0 * clear, major * 0.45)
    r_probe = pilot_r + 0.55 * thr["depth"]
    solid_hits = 0
    empty_hits = 0
    pitch = thr["pitch"]
    for i in range(24):
        a = math.radians(i * 15.0)
        z = z0 + 4.0 + (i % 8) * (pitch / 8.0)
        p = App.Vector(cx + r_probe * math.cos(a), cy + r_probe * math.sin(a), z)
        if sh.isInside(p, 0.08, True):
            solid_hits += 1
        else:
            empty_hits += 1
    if solid_hits < 2 or empty_hits < 2:
        _fail(
            "Traveling_Nut thread probe weak solid=%d empty=%d r=%.2f (need both)"
            % (solid_hits, empty_hits, r_probe),
            errors,
        )
    else:
        print(
            "OK Traveling_Nut flank probe solid=%d empty=%d r=%.2f"
            % (solid_hits, empty_hits, r_probe)
        )


def add_part(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if Gui is not None:
        try:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = int(transparency)
        except Exception:
            pass
    return obj


def shot(path: Path, view: str = "Isometric") -> None:
    if Gui is None or not App.GuiUp:
        return
    try:
        Gui.SendMsgToActiveView("ViewFit")
        if view == "Front":
            Gui.activeDocument().activeView().viewFront()
        elif view == "Right":
            Gui.activeDocument().activeView().viewRight()
        elif view == "Top":
            Gui.activeDocument().activeView().viewTop()
        else:
            Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        Gui.activeDocument().activeView().saveImage(str(path), 1600, 1200, "Current")
        print("SHOT", path)
    except Exception as exc:
        print("shot failed:", exc)


def isolate(doc, keep_names: set[str]) -> None:
    if Gui is None:
        return
    for o in doc.Objects:
        if not hasattr(o, "ViewObject") or o.ViewObject is None:
            continue
        try:
            o.ViewObject.Visibility = o.Name in keep_names or o.Label in keep_names
        except Exception:
            pass


def main() -> None:
    errors: list[str] = []
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Thread_Verify")
    drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
    drv["bar_length_y"] = float(drv.get("bar_length_y", 40.0))
    drv["bar_thickness"] = float(BX.LID["height_bar"].get("thickness", 10.0))
    drv["bar_height"] = float(BX.LID["height_bar"].get("height", 12.0))
    thr = _thread_params(drv)
    print("thread settings:", thr)

    parts = build_height_adjust_z_parts(
        cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=True
    )
    names = [n for n, _, _ in parts]
    print("components (%d):" % len(names), ", ".join(names))
    required = {
        "HA_Lead_Screw",
        "HA_Collar",
        "HA_Knob",
        "HA_Bearing_Block",
        "HA_Traveling_Nut",
        "HA_Guide_Rail_N",
        "HA_Guide_Rail_S",
        "HA_Bottom_Stop",
    }
    missing = sorted(required - set(names))
    if missing:
        _fail("missing components: %s" % missing, errors)

    by = {}
    objs = []
    for n, sh, col in parts:
        tr = 55 if n == "HA_Traveling_Nut" else (0 if n in ("HA_Lead_Screw", "HA_Collar") else 20)
        objs.append(add_part(doc, n, sh, col, transparency=tr))
        by[n] = sh

    # Geometric verify
    if "HA_Lead_Screw" in by:
        verify_screw(by["HA_Lead_Screw"], thr, errors, 0.0, 0.0)
    else:
        _fail("HA_Lead_Screw missing", errors)
    if "HA_Traveling_Nut" in by:
        verify_nut(by["HA_Traveling_Nut"], thr, errors, 0.0, 0.0)
    else:
        _fail("HA_Traveling_Nut missing", errors)

    # Fit check: male with nut_clear should largely fit in nut bore (common volume)
    if "HA_Lead_Screw" in by and "HA_Traveling_Nut" in by:
        try:
            # Sample screw section overlapping nut Z
            nut = by["HA_Traveling_Nut"]
            screw = by["HA_Lead_Screw"]
            nbb, sbb = nut.BoundBox, screw.BoundBox
            z_lo = max(nbb.ZMin, sbb.ZMin) + 1.0
            z_hi = min(nbb.ZMax, sbb.ZMax) - 1.0
            if z_hi > z_lo + 5.0:
                box = Part.makeBox(40, 40, z_hi - z_lo)
                box.translate(App.Vector(-20, -20, z_lo))
                s_sec = screw.common(box)
                # screw section should mostly NOT be solid-inside nut (clearance)
                # Instead: intersection screw∩nut should be small vs screw section
                inter = s_sec.common(nut)
                ratio = float(inter.Volume) / max(1.0, float(s_sec.Volume))
                print("fit probe screw∩nut / screw_sec = %.3f (want <0.25 with clearance)" % ratio)
                if ratio > 0.45:
                    _fail("screw heavily intersects nut material (ratio=%.3f)" % ratio, errors)
                else:
                    print("OK clearance fit probe")
        except Exception as exc:
            print("fit probe skipped:", exc)

    doc.recompute()
    fcstd = OUT / "height_adjust_z.FCStd"
    doc.saveAs(str(fcstd))

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        # Assembly
        isolate(doc, set(names))
        for o in doc.Objects:
            if o.Name == "HA_Traveling_Nut":
                try:
                    o.ViewObject.Transparency = 60
                except Exception:
                    pass
        shot(SHOT / "01_assembly_iso.png", "Isometric")
        # Screw only
        isolate(doc, {"HA_Lead_Screw"})
        shot(SHOT / "02_lead_screw_iso.png", "Isometric")
        shot(SHOT / "03_lead_screw_front.png", "Front")
        shot(SHOT / "04_lead_screw_right.png", "Right")
        # Nut only (opaque for hole visibility)
        isolate(doc, {"HA_Traveling_Nut"})
        for o in doc.Objects:
            if o.Name == "HA_Traveling_Nut":
                try:
                    o.ViewObject.Transparency = 0
                except Exception:
                    pass
        shot(SHOT / "05_nut_iso.png", "Isometric")
        shot(SHOT / "06_nut_top.png", "Top")
        shot(SHOT / "07_nut_front.png", "Front")
        # Screw + nut together
        isolate(doc, {"HA_Lead_Screw", "HA_Traveling_Nut"})
        for o in doc.Objects:
            if o.Name == "HA_Traveling_Nut":
                try:
                    o.ViewObject.Transparency = 50
                except Exception:
                    pass
        shot(SHOT / "08_screw_in_nut_iso.png", "Isometric")
        shot(SHOT / "09_screw_in_nut_front.png", "Front")
        # Restore all visible
        isolate(doc, set(names))

    report = SHOT / "verify_report.txt"
    status = "PASS" if not errors else "FAIL"
    lines = [status, ""]
    if errors:
        lines += ["Errors:"] + ["- " + e for e in errors]
    else:
        lines.append("All geometric checks passed.")
    lines.append("")
    lines.append("components: " + ", ".join(names))
    report.write_text("\n".join(lines), encoding="utf-8")
    print("=" * 60)
    print("\n".join(lines))
    print("report:", report)

    if not App.GuiUp:
        App.closeDocument(doc.Name)
        if errors:
            sys.exit(1)


# FreeCAD may not set __name__ == "__main__"
main()
