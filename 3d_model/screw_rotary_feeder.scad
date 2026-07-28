// ============================================================================
// Screw Rotary Disc Feeder — CountingMachine
// Target printer: Bambu Lab P1S (256 x 256 x 256 mm)
 // Units: mm
// Motion parts for simulation: rotary_disc, drive_hub (rotate about Z)
// Fixed parts: base_plate, hopper, cover, outlet_chute, brush_arm
// ============================================================================

/* [Global] */
part = "assembly"; // [assembly, exploded, base_plate, rotary_disc, hopper, cover, outlet_chute, drive_hub, brush_arm, all_printable]
screw_preview = true;
disc_angle = 0;     // degrees — animate for motion study
explode = 0;        // 0..1 for exploded view

/* [Screw / pocket] */
// Typical M3–M4 machine screw envelope (adjust to your fastener)
screw_head_d   = 6.5;
screw_head_h   = 2.5;
screw_shank_d  = 3.2;
screw_shank_l  = 12;
pocket_clearance = 0.6;

/* [Disc] */
disc_od        = 140;
disc_id        = 28;
disc_thickness = 6;
pocket_count   = 12;
pocket_radial_offset = 52; // center of pocket from disc center
hub_flat_width = 5.0;      // D-shaft flat for NEMA17 5mm shaft

/* [Housing] */
base_od        = 160;
base_thickness = 8;
wall_h         = 45;
wall_t         = 3.5;
outlet_w       = 10;
outlet_depth   = 28;
bearing_bore   = 16.2;     // 608ZZ OD + clearance (optional) or bushing
shaft_d        = 5.2;      // NEMA17 shaft clearance through disc
mount_hole_d   = 3.4;      // M3 clearance
mount_pcd      = 148;

/* [Hopper] */
hopper_od_top  = 120;
hopper_od_bot  = 100;
hopper_h       = 55;
hopper_wall    = 2.5;

/* [Print helpers] */
fn = 96;
eps = 0.05;

$fn = fn;

// ---- derived ----
pocket_w = screw_head_d + pocket_clearance * 2;
pocket_l = screw_head_d + screw_shank_l * 0.35 + pocket_clearance;
pocket_d = disc_thickness + 0.2;

module screw_dummy() {
    color("Silver") {
        cylinder(h = screw_head_h, d = screw_head_d);
        translate([0, 0, -screw_shank_l])
            cylinder(h = screw_shank_l + eps, d = screw_shank_d);
    }
}

module pocket_cut() {
    // Radial slot: head seat near rim, shank toward center
    hull() {
        translate([pocket_l * 0.35, 0, -eps])
            cylinder(h = pocket_d, d = pocket_w);
        translate([-pocket_l * 0.35, 0, -eps])
            cylinder(h = pocket_d, d = screw_shank_d + pocket_clearance * 2);
    }
    // Through-slot so screw can drop at outlet window
    translate([0, 0, -eps])
        cube([pocket_l * 1.1, screw_shank_d + pocket_clearance, pocket_d], center = true);
}

module rotary_disc() {
    difference() {
        union() {
            cylinder(h = disc_thickness, d = disc_od, center = false);
            // stiffening ribs
            for (a = [0 : 60 : 300])
                rotate([0, 0, a])
                    translate([disc_id / 2, -1.2, disc_thickness])
                        cube([disc_od / 2 - disc_id / 2 - 4, 2.4, 1.2]);
        }
        // center bore + D-flat for shaft drive (printed hub separate, disc keyed)
        translate([0, 0, -eps])
            cylinder(h = disc_thickness + 1.5 + 2 * eps, d = disc_id);

        // key slots for drive hub (4 tabs)
        for (a = [0 : 90 : 270])
            rotate([0, 0, a])
                translate([disc_id / 2 - 1, -3, -eps])
                    cube([4, 6, disc_thickness + 2 * eps]);

        // pockets
        for (i = [0 : pocket_count - 1]) {
            a = i * 360 / pocket_count;
            rotate([0, 0, a])
                translate([pocket_radial_offset, 0, 0])
                    rotate([0, 0, 90])
                        pocket_cut();
        }

        // lightening / print vents
        for (a = [15 : 30 : 345])
            rotate([0, 0, a])
                translate([36, 0, -eps])
                    cylinder(h = disc_thickness + 2 * eps, d = 8);
    }
}

module drive_hub() {
    h = disc_thickness + 12;
    difference() {
        union() {
            cylinder(h = h, d = disc_id - 0.4);
            // flange under disc
            cylinder(h = 3, d = disc_id + 10);
            // key tabs into disc
            for (a = [0 : 90 : 270])
                rotate([0, 0, a])
                    translate([disc_id / 2 - 1.2, -2.8, 3])
                        cube([3.6, 5.6, disc_thickness]);
        }
        // shaft bore
        translate([0, 0, -eps])
            cylinder(h = h + 2 * eps, d = shaft_d);
        // D-flat
        translate([shaft_d / 2 - 0.5, -hub_flat_width / 2, -eps])
            cube([3, hub_flat_width, h + 2 * eps]);
        // set-screw hole
        translate([0, 0, h - 5])
            rotate([0, 90, 0])
                cylinder(h = disc_id, d = 2.6, $fn = 24);
    }
}

module base_plate() {
    difference() {
        union() {
            cylinder(h = base_thickness, d = base_od);
            // outer wall ring seat
            translate([0, 0, base_thickness])
                difference() {
                    cylinder(h = 4, d = base_od);
                    translate([0, 0, -eps])
                        cylinder(h = 4 + 2 * eps, d = base_od - 2 * wall_t);
                }
            // outlet chute boss
            translate([base_od / 2 - outlet_depth / 2 - 2, 0, base_thickness / 2])
                cube([outlet_depth, outlet_w + 8, base_thickness], center = true);
        }
        // center bearing / bushing bore
        translate([0, 0, -eps])
            cylinder(h = base_thickness + 4 + 2 * eps, d = bearing_bore);

        // drop window under disc — single pocket release
        rotate([0, 0, 0])
            translate([pocket_radial_offset, 0, -eps])
                hull() {
                    cylinder(h = base_thickness + 2 * eps, d = pocket_w + 1);
                    translate([8, 0, 0])
                        cylinder(h = base_thickness + 2 * eps, d = pocket_w + 1);
                }

        // outlet channel through boss
        translate([base_od / 2 - outlet_depth / 2, 0, base_thickness / 2])
            cube([outlet_depth + 4, outlet_w, base_thickness + 2], center = true);

        // M3 mount holes (motor bracket / feet)
        for (a = [45 : 90 : 315])
            rotate([0, 0, a])
                translate([mount_pcd / 2, 0, -eps])
                    cylinder(h = base_thickness + 2 * eps, d = mount_hole_d);

        // hopper / cover bolt circle
        for (a = [0 : 60 : 300])
            rotate([0, 0, a])
                translate([(base_od - 12) / 2, 0, -eps])
                    cylinder(h = base_thickness + 6, d = mount_hole_d);
    }
}

module hopper() {
    difference() {
        union() {
            // conical shell
            cylinder(h = hopper_h, d1 = hopper_od_bot, d2 = hopper_od_top);
            // mounting flange
            cylinder(h = 4, d = hopper_od_bot + 16);
        }
        translate([0, 0, -eps])
            cylinder(h = hopper_h + 2 * eps, d1 = hopper_od_bot - 2 * hopper_wall,
                     d2 = hopper_od_top - 2 * hopper_wall);
        // open bottom to disc (slightly above disc OD clearance ring)
        translate([0, 0, -eps])
            cylinder(h = 6, d = disc_od - 6);
        // flange bolts
        for (a = [0 : 60 : 300])
            rotate([0, 0, a])
                translate([(hopper_od_bot + 8) / 2, 0, -eps])
                    cylinder(h = 6, d = mount_hole_d);
        // fill window cut
        translate([hopper_od_top / 2 - 5, 0, hopper_h - 18])
            rotate([0, 90, 0])
                cylinder(h = 20, d = 28);
    }
}

module cover() {
    // Low cover ring keeping screws on disc; open toward outlet
    difference() {
        union() {
            cylinder(h = 10, d = disc_od + 8);
            // brush mount boss
            rotate([0, 0, 140])
                translate([disc_od / 2 - 6, 0, 5])
                    cube([14, 12, 10], center = true);
        }
        translate([0, 0, -eps])
            cylinder(h = 10 + 2 * eps, d = disc_od - 10);
        // outlet sector open
        translate([pocket_radial_offset, 0, 5])
            cube([40, outlet_w + 6, 12], center = true);
        // bolt holes matching base
        for (a = [0 : 60 : 300])
            rotate([0, 0, a])
                translate([(base_od - 12) / 2, 0, -eps])
                    cylinder(h = 12, d = mount_hole_d);
        // brush screw
        rotate([0, 0, 140])
            translate([disc_od / 2 - 6, 0, -eps])
                cylinder(h = 12, d = 3.2);
    }
}

module outlet_chute() {
    difference() {
        union() {
            translate([0, 0, 0])
                cube([outlet_depth + 6, outlet_w + 10, 18]);
            // tube stub for flexible hose / rail
            translate([outlet_depth + 2, (outlet_w + 10) / 2, 9])
                rotate([0, 90, 0])
                    cylinder(h = 16, d = outlet_w + 6);
        }
        translate([3, 5, 4])
            cube([outlet_depth + 20, outlet_w, 12]);
        translate([outlet_depth + 2, (outlet_w + 10) / 2, 9])
            rotate([0, 90, 0])
                cylinder(h = 18, d = outlet_w);
        // mount holes to base boss
        translate([8, 3, -eps]) cylinder(h = 20, d = 3.2);
        translate([8, outlet_w + 7, -eps]) cylinder(h = 20, d = 3.2);
    }
}

module brush_arm() {
    // Soft brush holder — insert nylon bristle strip or TPU wipe
    difference() {
        union() {
            cube([28, 10, 6]);
            translate([0, 3, 6])
                cube([28, 4, 8]);
        }
        translate([6, 5, -eps]) cylinder(h = 8, d = 3.2);
        translate([22, 5, -eps]) cylinder(h = 8, d = 3.2);
        // bristle slot
        translate([2, 3.5, 8])
            cube([24, 3, 7]);
    }
}

module assembly(expl = 0, show_screws = true, angle = 0) {
    ez = expl * 30;

    color("DimGray")
        base_plate();

    color("SteelBlue")
        translate([0, 0, base_thickness + 0.5 + ez])
            rotate([0, 0, angle])
                rotary_disc();

    color("SlateGray")
        translate([0, 0, base_thickness - 2 - ez * 0.3])
            drive_hub();

    color("CadetBlue")
        translate([0, 0, base_thickness + disc_thickness + 1 + ez * 1.5])
            hopper();

    color("LightSlateGray")
        translate([0, 0, base_thickness + disc_thickness + 0.2 + ez])
            cover();

    color("DarkOrange")
        translate([base_od / 2 - outlet_depth - 4, -(outlet_w + 10) / 2, -2 - ez * 0.5])
            outlet_chute();

    color("SaddleBrown")
        rotate([0, 0, 140])
            translate([disc_od / 2 - 20, -5, base_thickness + disc_thickness + 8 + ez])
                brush_arm();

    if (show_screws) {
        for (i = [0 : pocket_count - 1]) {
            a = i * 360 / pocket_count + angle;
            rotate([0, 0, a])
                translate([pocket_radial_offset, 0, base_thickness + disc_thickness + 0.5 + ez])
                    screw_dummy();
        }
    }
}

module all_printable() {
    // Layout for single-plate preview / batch export reference (P1S bed)
    translate([-80, -80, 0]) base_plate();
    translate([90, -70, 0]) rotary_disc();
    translate([-80, 90, 0]) hopper();
    translate([90, 90, 0]) cover();
    translate([-20, 0, 0]) drive_hub();
    translate([40, 20, 0]) outlet_chute();
    translate([40, 50, 0]) brush_arm();
}

if (part == "assembly")
    assembly(0, screw_preview, disc_angle);
else if (part == "exploded")
    assembly(explode > 0 ? explode : 1, screw_preview, disc_angle);
else if (part == "base_plate")
    base_plate();
else if (part == "rotary_disc")
    rotary_disc();
else if (part == "hopper")
    hopper();
else if (part == "cover")
    cover();
else if (part == "outlet_chute")
    outlet_chute();
else if (part == "drive_hub")
    drive_hub();
else if (part == "brush_arm")
    brush_arm();
else if (part == "all_printable")
    all_printable();
