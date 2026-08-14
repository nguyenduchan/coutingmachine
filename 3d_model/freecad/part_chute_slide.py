"""
Chute_Slide — 2 thanh tịnh tiến nằm ngang cho máng.

  • Bắt đầu tại thành đĩa Ø20 cm: 8 giờ (210°) và 10 giờ (150°)
  • Chạy ngang theo +X vào lòng đĩa
  • Nối liền thành đĩa bằng đế cung tại mép r = DISC_R
  • Component riêng (App::Part + 2 child) — không dính Exit_Track / Bowl_Tube
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

from mech_common import *  # noqa: F401,F403


def make_chute_slide_bar_8h() -> Part.Shape:
    return make_chute_slide_bar_at_clock(210.0)


def make_chute_slide_bar_10h() -> Part.Shape:
    return make_chute_slide_bar_at_clock(150.0)


def make_chute_slide(_width_open: float | None = None) -> Part.Shape:
    """Hai thanh 8h + 10h (cố định, không theo W)."""
    return make_chute_slide_bars(_width_open)


def chute_slide_bar_children() -> list[tuple[str, object]]:
    return [
        ("Chute_Slide_Bar_8h", make_chute_slide_bar_8h()),
        ("Chute_Slide_Bar_10h", make_chute_slide_bar_10h()),
    ]


def write_chute_slide_component(path, color=(0.45, 0.48, 0.55), style_fn=None) -> None:
    """Ghi Chute_Slide.FCStd: parent App::Part + 2 child Part::Feature."""
    doc = App.newDocument("Chute_Slide")
    kids = []
    for name, shape in chute_slide_bar_children():
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        obj.Label = name
        if style_fn is not None:
            style_fn(obj, color, 0)
        kids.append(obj)
    grp = doc.addObject("App::Part", "Chute_Slide")
    grp.Label = "Chute_Slide"
    if hasattr(grp, "addObjects"):
        grp.addObjects(kids)
    else:
        grp.Group = kids
    try:
        origin = getattr(grp, "Origin", None)
        if origin is not None and hasattr(origin, "Visibility"):
            origin.Visibility = False
    except Exception:
        pass
    doc.recompute()
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
