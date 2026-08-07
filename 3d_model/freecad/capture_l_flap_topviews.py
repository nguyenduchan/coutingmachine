"""
Capture L_Flap top-view PNGs at slider open=0 (cover small) and open=max,
then verify knob-driven travel has no blocking collisions.

  freecad.exe 3d_model/freecad/capture_l_flap_topviews.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"d:\Project\coutingmachine\3d_model\freecad")

OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(_HERE))

from l_flap_divert import (  # noqa: E402
    OPEN_DRIVE_HI,
    OPEN_DRIVE_LO,
    OPEN_LARGE_HI,
    OPEN_SMALL_LO,
    aperture_widths,
    build_l_flap_divert_parts,
    clamp_open,
    common_volume,
    flap_state_for_open,
    knob_angle_deg,
    make_divert_frame,
    make_gap_slider,
    make_geneva_driver,
    make_malta_cross,
    malta_angle_for_open,
    slider_x_left,
    verify_knob_slider_drive,
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


def build_doc(open_mm: float):
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)
    doc = App.newDocument("L_Flap_TopView")
    parts = build_l_flap_divert_parts(slider_open_mm=open_mm, include_slider_gear=True)
    for n, sh, col in parts:
        tr = 40 if n == "Divert_Frame" else (30 if n.startswith("Guide_Chute") else 0)
        if n.startswith("Lane_Fill") or n == "Inlet_Pill_Passage":
            tr = 70
        add_part(doc, n, sh, col, transparency=tr)
    doc.recompute()
    return doc


def capture_top(doc, path: Path, *, px=1600, py=1200):
    if Gui is None or not App.GuiUp:
        print("SKIP capture (no GUI):", path)
        return False
    Gui.ActiveDocument = Gui.getDocument(doc.Name)
    view = Gui.activeDocument().activeView()
    view.viewTop()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.updateGui()
    # Slight zoom-out margin
    try:
        cam = view.getCameraNode()
        if cam is not None and hasattr(cam, "height"):
            cam.height.setValue(float(cam.height.getValue()) * 1.08)
    except Exception:
        pass
    Gui.updateGui()
    view.saveImage(str(path), px, py, "Current")
    print("Saved", path)
    return True


def verify_travel_no_jam(n_steps: int = 18) -> dict:
    """Knob turns open LO→HI: slider must move; no blocking solid jams."""
    frame = make_divert_frame()
    rows = []
    max_ill = 0.0
    jam = 0
    aw0 = aperture_widths(OPEN_DRIVE_LO)
    aw1 = aperture_widths(OPEN_DRIVE_HI)
    cover_small0 = aw0["small_mm"] < 0.15
    large_full = aw1["large_mm"] >= 11.5

    x0 = slider_x_left(OPEN_DRIVE_LO)
    x1 = slider_x_left(OPEN_DRIVE_HI)
    travel_mm = x1 - x0

    for i in range(n_steps):
        t = i / max(1, n_steps - 1)
        op = OPEN_DRIVE_LO + t * (OPEN_DRIVE_HI - OPEN_DRIVE_LO)
        op = clamp_open(op)
        slider = make_gap_slider(op)
        malta = make_malta_cross(malta_angle_for_open(op))
        driver = make_geneva_driver(op)
        ov_sf = common_volume(slider, frame)
        ov_sm = common_volume(slider, malta)
        ov_sd = common_volume(slider, driver)
        # Rail seat is intentional contact — ignore tiny; flag deep digs
        ill = 0.0
        if ov_sf > 30.0:
            ill = max(ill, ov_sf)
        if ov_sm > 8.0:
            ill = max(ill, ov_sm)
        if ov_sd > 8.0:
            ill = max(ill, ov_sd)
        max_ill = max(max_ill, ill)
        if ill >= 30.0:
            jam += 1
        aw = aperture_widths(op)
        rows.append(
            {
                "open_mm": round(op, 3),
                "knob_deg": round(knob_angle_deg(op), 2),
                "slider_x_left": round(slider_x_left(op), 3),
                "state": flap_state_for_open(op),
                "small_mm": aw["small_mm"],
                "large_mm": aw["large_mm"],
                "ov_slider_frame": round(ov_sf, 3),
                "ov_slider_malta": round(ov_sm, 3),
                "ov_slider_driver": round(ov_sd, 3),
            }
        )

    gear = verify_knob_slider_drive(n_steps=6)
    couple_ok = bool(gear.get("couple_ok"))
    # Monotonic +X travel when knob increases
    mono = all(
        rows[i]["slider_x_left"] <= rows[i + 1]["slider_x_left"] + 1e-6
        for i in range(len(rows) - 1)
    )
    passed = bool(
        cover_small0
        and large_full
        and travel_mm >= (OPEN_LARGE_HI - OPEN_SMALL_LO) - 0.05
        and jam == 0
        and max_ill < 30.0
        and couple_ok
        and mono
        and gear.get("pass")
    )
    return {
        "pass": passed,
        "cover_small_at_rest": cover_small0,
        "small_mm_at_0": aw0["small_mm"],
        "large_mm_at_max": aw1["large_mm"],
        "large_full_at_max": large_full,
        "slider_travel_mm": round(travel_mm, 3),
        "knob_deg_span": round(knob_angle_deg(OPEN_DRIVE_HI) - knob_angle_deg(OPEN_DRIVE_LO), 2),
        "monotonic_slider": mono,
        "couple_ok": couple_ok,
        "jam_hits": jam,
        "max_illegal_mm3": round(max_ill, 3),
        "gear": {
            "pass": gear.get("pass"),
            "circular_pitch_mm": gear.get("circular_pitch_mm"),
            "knob_deg_per_1mm": gear.get("knob_deg_per_1mm"),
            "max_overlap_mm3": gear.get("max_overlap_mm3"),
        },
        "samples": rows,
        "note": "Default open=0 covers small; max open opens large; knob rack drive no jam",
    }


def main():
    png0 = OUT / "l_flap_topview_open0_cover_small.png"
    png1 = OUT / "l_flap_topview_open_max.png"
    report_path = OUT / "l_flap_slider_knob_travel_verify.json"

    print("=== Top view open=0 (cover small) ===")
    doc = build_doc(OPEN_DRIVE_LO)
    aw = aperture_widths(OPEN_DRIVE_LO)
    print("aperture", aw, "state", flap_state_for_open(OPEN_DRIVE_LO))
    capture_top(doc, png0)

    print("=== Top view open=max ===")
    doc = build_doc(OPEN_DRIVE_HI)
    aw = aperture_widths(OPEN_DRIVE_HI)
    print("aperture", aw, "state", flap_state_for_open(OPEN_DRIVE_HI))
    capture_top(doc, png1)

    print("=== Knob travel collision ===")
    rep = verify_travel_no_jam()
    report_path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(
        "pass=%s cover0=%s large_max=%s travel=%.2f jam=%s ill=%.1f couple=%s"
        % (
            rep["pass"],
            rep["cover_small_at_rest"],
            rep["large_full_at_max"],
            rep["slider_travel_mm"],
            rep["jam_hits"],
            rep["max_illegal_mm3"],
            rep["couple_ok"],
        )
    )
    print("Wrote", report_path)
    print("PNG:", png0.name, "|", png1.name)

    if Gui is not None and App.GuiUp:
        # Leave max-travel model open for user
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewTop()
        Gui.SendMsgToActiveView("ViewFit")
    if not rep["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
