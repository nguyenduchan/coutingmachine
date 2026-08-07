"""
Disc_Access_Lid — shared FreeCAD tree assembly.

Geometry makers live in show_jgb37_gui.py (same solids as the counting machine).
Both show_disc_access_lid_gui.py and show_jgb37_gui.py call assemble_disc_access_lid
so edits to box_settings.LID / make_lid_* rebuild the lid model and the box alike.
"""

from __future__ import annotations

from typing import Callable, Optional


KeepFn = Callable[[str], bool]
AddPartFn = Callable[..., object]
AddGroupFn = Callable[..., object]
MakePartsFn = Callable[[float], list]


def assemble_disc_access_lid(
    doc,
    z_disc: float,
    *,
    add_part: AddPartFn,
    add_group: AddGroupFn,
    make_lid_top_parts: MakePartsFn,
    make_lid_bottom_parts: MakePartsFn,
    make_lid_fill_parts: MakePartsFn,
    make_disc_access_lid_parts: MakePartsFn,
    make_width_adjust_drive_parts: MakePartsFn,
    make_height_adjust_drive_parts: MakePartsFn,
    lid_cfg: dict,
    keep_assembly: Optional[KeepFn] = None,
) -> dict:
    """
    Build Disc_Access_Lid App::Part tree under doc.

    Returns dict with lid_top_objs, lid_top_grp, count_msg (or empty if skipped).
    """
    keep = keep_assembly or (lambda _name: True)
    if not keep("Disc_Access_Lid"):
        return {
            "built": False,
            "lid_top_objs": [],
            "lid_top_grp": None,
            "count_msg": None,
        }

    lid_top_objs: list = []
    hub_kids: list = []
    sw_chute_kids: list = []
    sw_rest = None
    for n, sh, col in make_lid_top_parts(z_disc):
        tr = 0 if n == "Lid_Top_Arc_Corner" else 25
        obj = add_part(doc, n, sh, col, transparency=tr)
        if n.startswith("Lid_Top_Deck_S_Hub_"):
            hub_kids.append(obj)
        elif n.startswith("Lid_Top_Out_SW_Chute_"):
            sw_chute_kids.append(obj)
        elif n == "Lid_Top_Out_SW_Rest":
            sw_rest = obj
        else:
            lid_top_objs.append(obj)
    if hub_kids:
        lid_top_objs.append(add_group(doc, "Lid_Top_Deck_S_Hub", hub_kids))
    sw_kids: list = []
    if sw_chute_kids:
        sw_kids.append(add_group(doc, "Lid_Top_Out_SW_Chute", sw_chute_kids))
    if sw_rest is not None:
        sw_kids.append(sw_rest)
    if sw_kids:
        lid_top_objs.append(add_group(doc, "Lid_Top_Out_SW", sw_kids))
    lid_top_grp = add_group(doc, "Lid_Top", lid_top_objs)
    lid_kids = [lid_top_grp]

    lid_bot_objs = [
        add_part(doc, n, sh, col, transparency=25)
        for n, sh, col in make_lid_bottom_parts(z_disc)
    ]
    if lid_bot_objs:
        lid_kids.append(add_group(doc, "Lid_Bottom", lid_bot_objs))

    lid_fill_objs = [
        add_part(doc, n, sh, col, transparency=20)
        for n, sh, col in make_lid_fill_parts(z_disc)
    ]
    if lid_fill_objs:
        lid_kids.append(add_group(doc, "Lid_Fill", lid_fill_objs))

    lid_rest = [
        add_part(doc, n, sh, col, transparency=25)
        for n, sh, col in make_disc_access_lid_parts(z_disc)
    ]

    drive_objs: list = []
    if keep("Width_Adjust_Drive") or keep("Width_Lead_Screw"):
        drive_objs = [
            add_part(doc, n, sh, col, transparency=15)
            for n, sh, col in make_width_adjust_drive_parts(z_disc)
        ]
        if drive_objs:
            lid_rest.append(add_group(doc, "Width_Adjust_Drive", drive_objs))

    h_drive_objs: list = []
    if bool(lid_cfg.get("height_bar", {}).get("drive", {}).get("enabled", False)):
        h_drive_objs = [
            add_part(doc, n, sh, col, transparency=15)
            for n, sh, col in make_height_adjust_drive_parts(z_disc)
        ]
        if h_drive_objs:
            lid_rest.append(add_group(doc, "Height_Adjust_Drive", h_drive_objs))

    add_group(doc, "Disc_Access_Lid", lid_kids + lid_rest)
    count_msg = (
        "Disc_Access_Lid(Top %d + Bottom %d + Fill %d + rest %d + w_drive %d + h_drive %d)"
        % (
            len(lid_top_objs),
            len(lid_bot_objs),
            len(lid_fill_objs),
            len(lid_rest) - (1 if drive_objs else 0) - (1 if h_drive_objs else 0),
            len(drive_objs),
            len(h_drive_objs),
        )
    )
    return {
        "built": True,
        "lid_top_objs": lid_top_objs,
        "lid_top_grp": lid_top_grp,
        "count_msg": count_msg,
    }


def enforce_lid_parent_pz0(doc, disc_clear: float) -> None:
    """Keep Disc_Access_Lid parent Pz=0 so wall bottoms stay at disc+clear."""
    import FreeCAD as App

    lid_grp = doc.getObject("Disc_Access_Lid")
    if lid_grp is None or not hasattr(lid_grp, "Placement"):
        return
    pl = lid_grp.Placement
    if abs(float(pl.Base.z)) > 1e-6:
        print(
            "Disc_Access_Lid: Pz %.3f -> 0 (Lid_Wall bottom = disc+%.1f mm)"
            % (pl.Base.z, disc_clear)
        )
        pl.Base = App.Vector(pl.Base.x, pl.Base.y, 0.0)
        lid_grp.Placement = pl


def force_show_lid_top(doc, lid_top_objs: list, lid_top_grp) -> None:
    for obj in list(lid_top_objs) + [lid_top_grp, doc.getObject("Disc_Access_Lid")]:
        if obj is None:
            continue
        vo = getattr(obj, "ViewObject", None)
        if vo is not None and hasattr(vo, "Visibility"):
            vo.Visibility = True
