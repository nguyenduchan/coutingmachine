"""Fast capture: top-view at open=0 and open=max only (no heavy verify)."""
from __future__ import annotations

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

_HERE = Path(__file__).resolve().parent
OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(_HERE))

from l_flap_divert import (  # noqa: E402
    OPEN_DRIVE_HI,
    OPEN_DRIVE_LO,
    aperture_widths,
    build_l_flap_divert_parts,
    flap_state_for_open,
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


def shot(open_mm: float, path: Path):
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)
    doc = App.newDocument("L_Flap_TV")
    for n, sh, col in build_l_flap_divert_parts(open_mm, include_slider_gear=True):
        tr = 35 if n == "Divert_Frame" else 0
        if n.startswith("Lane_Fill") or n == "Inlet_Pill_Passage":
            tr = 65
        if n.startswith("Guide_Chute"):
            tr = 25
        add_part(doc, n, sh, col, tr)
    doc.recompute()
    aw = aperture_widths(open_mm)
    print("open=%.2f state=%s aperture=%s" % (open_mm, flap_state_for_open(open_mm), aw))
    if Gui is None or not App.GuiUp:
        print("NO GUI — cannot save", path)
        return
    Gui.ActiveDocument = Gui.getDocument(doc.Name)
    view = Gui.activeDocument().activeView()
    view.viewTop()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.updateGui()
    view.saveImage(str(path), 1600, 1200, "Current")
    print("Saved", path)


def main():
    shot(OPEN_DRIVE_LO, OUT / "l_flap_topview_open0_cover_small.png")
    shot(OPEN_DRIVE_HI, OUT / "l_flap_topview_open_max.png")
    if Gui is not None and App.GuiUp:
        Gui.activeDocument().activeView().viewTop()
        Gui.SendMsgToActiveView("ViewFit")


if __name__ == "__main__":
    main()
