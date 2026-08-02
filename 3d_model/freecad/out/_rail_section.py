    # -------------------------------------------------------------------------
    # HA_Bearing_Rail — see .cursor/rules/ha-bearing-rail.mdc (C1–C11)
    #   C1  one solid    C2 tongue overlap    C3 web band / no journal fill
    #   C4  ±X M3        C5 split @ z_pin     C6 −X hole OPEN (window to ex)
    #   C7  nut access   C8 fuse then re-cut  C9 hardware   C10 journal
    #   C11 planar −X + clamp window
    # -------------------------------------------------------------------------
    rail_x0 = bar_cx - 0.5 * (bar_x + 2 * rail_wall)
    rail_x1 = bar_cx + 0.5 * (bar_x + 2 * rail_wall)
    brg_x0 = cx - 0.5 * (bearing_w + 8.0)
    brg_x1 = cx + 0.5 * (bearing_w + 8.0)
    # Full web into bearing foot (C1) — stop before journal at cx (no saddle fill)
    # −X face flush with rail outer (no link_x0 overhang / stepped left wall)
    link_x0 = rail_x0
    link_x1 = min(brg_x0 + 8.0, cx - 0.5 * bush - 2.0)
    if link_x1 < link_x0 + 4.0:
        link_x1 = link_x0 + 4.0
    # Web thickness = rail band only — must NOT invade follower Y corridor
    link_t = rail_t
    foot_h = 5.5
    link_z0 = z_pin - 0.5 * bearing_h - foot_h
    link_z1 = z_pin
    y_fol_s = cy - 0.5 * bar_y - rail_clear
    y_fol_n = cy + 0.5 * bar_y + rail_clear
    print(
        "HA_web: X[%.1f,%.1f] t=%.1f (stops before journal)"
        % (link_x0, link_x1, link_t)
    )
    print(
        "HA_rail_thick: wall=%.1f rail_t=%.1f bearing_t=%.1f foot_h=%.1f"
        % (rail_wall, rail_t, bearing_t, foot_h)
    )

    def _stiff_web(y0_plane: float, *, z_bot: float | None = None) -> Part.Shape:
        """Continuous web rail ↔ bearing in rail Y band only (no follower clash)."""
        z_flange0 = z_rail0 + 2.0 if z_bot is None else float(z_bot) + 2.0
        dx = max(1.0, link_x1 - link_x0)
        dz = max(1.0, link_z1 - link_z0)
        web = Part.makeBox(dx, link_t, dz)
        web.translate(App.Vector(link_x0, y0_plane, link_z0))
        band = 5.5  # thicker top/bottom chords
        top = Part.makeBox(dx, link_t, band)
        top.translate(App.Vector(link_x0, y0_plane, z_pin - band))
        bot = Part.makeBox(dx, link_t, band)
        bot.translate(App.Vector(link_x0, y0_plane, link_z0))
        rib_w = 6.0
        pieces = [web, top, bot]
        # Edge ribs only in rail X — skip mid rib through follower X span
        for x_rib in (link_x0, link_x1 - rib_w):
            rib = Part.makeBox(rib_w, link_t, dz)
            rib.translate(App.Vector(x_rib, y0_plane, link_z0))
            pieces.append(rib)
        flange_h = max(6.0, link_z1 - z_flange0)
        flange = Part.makeBox(max(4.0, rail_x1 - rail_x0), link_t, flange_h)
        flange.translate(App.Vector(rail_x0, y0_plane, z_flange0))
        pieces.append(flange)
        if z_bot is not None and float(z_bot) < link_z0 - 1.0:
            apron_h = link_z0 - float(z_bot)
            apron = Part.makeBox(dx, link_t, apron_h)
            apron.translate(App.Vector(link_x0, y0_plane, float(z_bot)))
            pieces.append(apron)
            for x_rib in (link_x0, link_x1 - rib_w):
                rib_d = Part.makeBox(rib_w, link_t, apron_h)
                rib_d.translate(App.Vector(x_rib, y0_plane, float(z_bot)))
                pieces.append(rib_d)
        out = pieces[0]
        for p in pieces[1:]:
            try:
                out = out.fuse(p)
            except Exception:
                pass
        return _as_one_solid(out)

    def _nsol(shape: Part.Shape) -> int:
        return len(list(getattr(shape, "Solids", []) or []))

    def _cut_keep_one(solid: Part.Shape, tool: Part.Shape) -> Part.Shape:
        """Boolean cut that refuses to split C1 (rolls back if multi-solid)."""
        try:
            nxt = _as_one_solid(solid.cut(tool))
        except Exception:
            return solid
        if nxt is None or getattr(nxt, "isNull", lambda: False)():
            return solid
        if _nsol(nxt) > 1:
            return solid
        return nxt

    def _minus_x_clamp_window(ex: float, y0: float, z_ear0: float) -> Part.Shape:
        """
        C6/C11: open -X face to hole axis (x <= ex) in lower-ear Z band.
        Stops at hole center so X>ex keeps rail<->bearing continuous (C1).
        Includes under-ear nut finger space (C7).
        """
        hy = y0 + 0.5 * bearing_t
        half_h = 0.5 * BOLT_EAR
        y_pad = 0.25
        y0w = y0 + y_pad
        yw = max(2.5, bearing_t - 2.0 * y_pad)
        # Full lower ear height + nut pocket below
        z0w = z_ear0 - M3_NUT_POCKET_H - 1.2
        zw = (z_pin - z0w) + 0.2
        # From outer -X wall up to hole axis (do NOT pass ex — C1)
        x0w = rail_x0 - 0.6
        x1w = ex + 0.15  # just into hole void
        dx = max(2.0, x1w - x0w)
        win = Part.makeBox(dx, yw, zw)
        win.translate(App.Vector(x0w, y0w, z0w))
        nut = _m3_nut_pocket_z(ex, hy, z_ear0)
        hole = _m3_hole_z(ex, hy, z0w - 0.2, zw + half_h + 0.5)
        try:
            return _as_one_solid(win.fuse(nut).fuse(hole))
        except Exception:
            try:
                return _as_one_solid(win.fuse(hole))
            except Exception:
                return win

    def _finish_rail_one_solid(
        brg_lo: Part.Shape,
        rail: Part.Shape,
        y0: float,
        y_plane: float,
        *,
        z_bot: float | None = None,
    ) -> Part.Shape:
        """Fuse to one solid (C1), then +/-X M3 + -X window (C4-C8)."""
        web = _stiff_web(y_plane, z_bot=z_bot)
        solid = brg_lo
        for piece in (rail, web):
            try:
                solid = _as_one_solid(solid.fuse(piece))
            except Exception:
                pass
        if _nsol(solid) > 1:
            print(
                "HA_Bearing_Rail y0=%.1f: WARN fuse pre-cut solids=%d"
                % (y0, _nsol(solid))
            )
        hy = y0 + 0.5 * bearing_t
        z_ear0 = z_pin - 0.5 * BOLT_EAR
        half_h = 0.5 * BOLT_EAR
        eps = 0.05
        for sx in (-1.0, 1.0):
            ex = _m3_clamp_x(sx)
            # Lower half ear only — Cap owns material above z_pin (C5)
            ear = Part.makeBox(BOLT_EAR, bearing_t, half_h)
            ear.translate(App.Vector(ex - 0.5 * BOLT_EAR, y0, z_ear0))
            try:
                solid = _as_one_solid(solid.fuse(ear))
            except Exception:
                pass
            hole_z0 = z_ear0 - M3_NUT_POCKET_H - 0.4
            hole_h = M3_NUT_POCKET_H + half_h + eps + 0.8
            solid = _cut_keep_one(solid, _m3_hole_z(ex, hy, hole_z0, hole_h))
            solid = _cut_keep_one(solid, _m3_nut_pocket_z(ex, hy, z_ear0))
            if sx < 0.0:
                # C6: expose -X hole; must succeed (not silently roll back)
                tool = _minus_x_clamp_window(ex, y0, z_ear0)
                before = solid
                solid = _cut_keep_one(solid, tool)
                if solid is before:
                    print(
                        "HA_Bearing_Rail y0=%.1f: FAIL C6 window cut rolled back"
                        % y0
                    )
            else:
                # +X: small under-ear finger box only (ear already on outer +X)
                aw = M3_NUT_POCKET_AF + 1.5
                ah = M3_NUT_POCKET_H + 2.0
                pocket = Part.makeBox(aw, aw, ah)
                pocket.translate(
                    App.Vector(ex - 0.5 * aw, hy - 0.5 * aw, z_ear0 - ah + 0.2)
                )
                solid = _cut_keep_one(solid, pocket)
        nsol = _nsol(solid)
        print(
            "HA_Bearing_Rail y0=%.1f: solids=%d (want 1) | +/-X M3 + C6 window"
            % (y0, nsol)
        )
        if nsol != 1:
            print("HA_Bearing_Rail FAIL C1: still multi-solid after clamp cuts")
        return solid

    rail_s_assy = _finish_rail_one_solid(
        brg_l_lo, rail_s, y_brg_l, y_s_plane, z_bot=z_rail_bot
    )
    rail_n_assy = _finish_rail_one_solid(
        brg_r_lo, rail_n, y_brg_r, y_n_plane - link_t, z_bot=z_rail_bot
    )

    def _flatten_minus_x(solid: Part.Shape, x_face: float) -> Part.Shape:
        """Shave any material with X < x_face so -X wall is planar (// YZ)."""
        bb = solid.BoundBox
        if bb.XMin >= x_face - 0.02:
            return solid
        cut = Part.makeBox(
            (x_face - bb.XMin) + 1.0,
            bb.YLength + 20.0,
            bb.ZLength + 20.0,
        )
        cut.translate(App.Vector(bb.XMin - 0.5, bb.YMin - 10.0, bb.ZMin - 10.0))
        try:
            out = _cut_keep_one(solid, cut)
            if out is solid:
                out = _as_one_solid(solid.cut(cut))
            print(
                "HA_flatten_-X: XMin %.3f -> face %.3f | solids=%d"
                % (bb.XMin, x_face, _nsol(out))
            )
            return out
        except Exception:
            return solid

    rail_s_assy = _flatten_minus_x(rail_s_assy, rail_x0)
    rail_n_assy = _flatten_minus_x(rail_n_assy, rail_x0)

    def _recut_left_m3_after_flatten(solid: Part.Shape, y0: float) -> Part.Shape:
        """C8: re-open C6 window + hole after flatten (no flash)."""
        ex = _m3_clamp_x(-1.0)
        z_ear0 = z_pin - 0.5 * BOLT_EAR
        before = solid
        solid = _cut_keep_one(solid, _minus_x_clamp_window(ex, y0, z_ear0))
        ok = solid is not before or _nsol(solid) == 1
        # Verify channel: sample mid-face toward hole
        hy = y0 + 0.5 * bearing_t
        z_mid = z_ear0 + 0.35 * BOLT_EAR
        x_mid = 0.5 * (rail_x0 + ex)
        buried = False
        try:
            buried = bool(solid.isInside(App.Vector(x_mid, hy, z_mid), 0.08, True))
        except Exception:
            pass
        print(
            "HA_M3_-X window @ x=%.1f solids=%d channel_clear=%s"
            % (ex, _nsol(solid), "yes" if (ok and not buried) else "NO")
        )
        if buried:
            print("HA_Bearing_Rail FAIL C6: -X hole still buried behind web")
        return solid

    rail_s_assy = _recut_left_m3_after_flatten(rail_s_assy, y_brg_l)
    rail_n_assy = _recut_left_m3_after_flatten(rail_n_assy, y_brg_r)

