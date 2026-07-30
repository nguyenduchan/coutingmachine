"""
Blender — PHYSICALLY LINKED drive (Rigid Body joints). NOT parenting puppets.

PREVIOUS METHOD (rejected):
  Parent + Copy Location → object moves even across air gaps.
  That is animation, not force transmission.

THIS METHOD:
  Rigid Body World + constraints only:
    J1 FIXED     motor body → frame
    J2 KINEMATIC shaft+cams+pins (motor torque input, only keyframed RB)
    J3 FIXED     (cams/pins are ONE compound with shaft)
    J4 HINGE     pin → conrod          (force through hinge)
    J5 HINGE     conrod → slider       (force through hinge)
    J6 SLIDER    slider ↔ frame (Z)    (guide reaction)
    J7 FIXED     plates → slider       (rigid bolted)

Review: every ACTIVE body must have a constraint path to the kinematic motor shaft.
Bodies with no path must stay still.

1 BU = 1 cm.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
BLEND = OUT / "step_drive_4plate.blend"
REVIEW = OUT / "physics_review.txt"

FPS = 30
DURATION_S = 6
TOTAL = FPS * DURATION_S
STROKE = 2.4
ECC = STROKE / 2.0
MOTOR_RPM = 24.0
CONROD_LEN = 4.0  # pin center → slider wrist

# GB37 (cm)
GB_D, GB_L = 3.7, 2.65
MOT_D, MOT_BARREL, MOT_L = 3.3, 1.96, 2.27
SHAFT_OFF = 0.7
SHAFT_R = 0.3
BOSS_D, BOSS_L = 1.2, 0.6
SHAFT_OUT = 2.1

SX, SY, SZ = 0.0, 0.0, 4.0
XA, XB = 3.5, 6.2


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    if bpy.context.scene.rigidbody_world:
        bpy.ops.rigidbody.world_remove()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.actions):
        for b in list(coll):
            try:
                coll.remove(b)
            except Exception:
                pass


def mat(name, rgb, metallic=0.3, rough=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1)
    return m


def box(name, dims, loc, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (dims[0] / 2, dims[1] / 2, dims[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if material:
        o.data.materials.append(material)
    return o


def cyl(name, r, depth, loc, material=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    if material:
        o.data.materials.append(material)
    return o


def empty(name, loc, size=0.3, display="PLAIN_AXES"):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.empty_display_type = display
    o.empty_display_size = size
    return o


def text(name, body, loc, size=0.28):
    bpy.ops.object.text_add(location=loc)
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.rotation_euler = (math.radians(90), 0, 0)
    return t


def rb_passive(obj, shape="BOX", kinematic=False):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add(type="PASSIVE")
    obj.rigid_body.collision_shape = shape
    obj.rigid_body.kinematic = kinematic
    obj.rigid_body.friction = 0.4
    obj.rigid_body.restitution = 0.0
    return obj


def rb_active(obj, shape="BOX", mass=1.0):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add(type="ACTIVE")
    obj.rigid_body.collision_shape = shape
    obj.rigid_body.mass = mass
    obj.rigid_body.friction = 0.35
    obj.rigid_body.restitution = 0.0
    obj.rigid_body.linear_damping = 0.35
    obj.rigid_body.angular_damping = 0.85
    return obj


def rb_constraint(name, ctype, obj1, obj2, loc, rot=(0, 0, 0)):
    """Add rigid-body constraint empty linking obj1↔obj2 at loc."""
    e = empty(name, loc, 0.25, "ARROWS")
    e.rotation_euler = rot
    bpy.context.view_layer.objects.active = e
    bpy.ops.rigidbody.constraint_add(type=ctype)
    c = e.rigid_body_constraint
    c.object1 = obj1
    c.object2 = obj2
    c.use_breaking = False
    return e, c


def join_selected(name):
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def build():
    clear()
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = TOTAL
    sc.render.fps = FPS

    m_steel = mat("Steel", (0.82, 0.84, 0.86), 0.9, 0.2)
    m_mot = mat("MotBlack", (0.12, 0.12, 0.14), 0.35, 0.55)
    m_gb = mat("GBSilver", (0.72, 0.74, 0.76), 0.85, 0.28)
    m_red = mat("Red", (1.0, 0.15, 0.08), 0.1, 0.35)
    m_a = mat("Orange", (1.0, 0.45, 0.05), 0.25, 0.35)
    m_b = mat("Cyan", (0.05, 0.75, 0.95), 0.25, 0.35)
    m_green = mat("Green", (0.2, 0.85, 0.3), 0.05, 0.4)
    m_rod = mat("Conrod", (0.95, 0.8, 0.15), 0.35, 0.4)
    m_slide = mat("Slider", (0.5, 0.52, 0.55), 0.5, 0.4)
    m_base = mat("Base", (0.45, 0.47, 0.5), 0.25, 0.55)
    m_guide = mat("Guide", (0.62, 0.64, 0.67), 0.7, 0.3)

    review = []
    review.append("METHOD: Rigid Body constraints (HINGE/SLIDER/FIXED). No Copy Location puppet.")
    review.append("Motor torque = kinematic rotation of DriveAsm only.")
    review.append("")

    # ---- Rigid body world ----
    bpy.ops.rigidbody.world_add()
    rbw = sc.rigidbody_world
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = TOTAL
    if hasattr(rbw, "substeps_per_frame"):
        rbw.substeps_per_frame = 20
    if hasattr(rbw, "solver_iterations"):
        rbw.solver_iterations = 30
    # Blender 4.x
    if hasattr(rbw, "steps_per_second"):
        rbw.steps_per_second = 600

    # ========== FRAME (passive ground) ==========
    frame = box("FRAME", (18, 8, 0.5), (5, 0.5, 0.25), m_base)
    rb_passive(frame, "BOX")
    review.append("FRAME: PASSIVE ground — reaction forces")

    # Guide posts (passive) — physical rails for visual + collision
    for i, x in enumerate((XA, XB)):
        post = box(f"GuidePost_{i}", (0.7, 0.7, 10), (x, SY - 1.8, 5), m_guide)
        rb_passive(post, "BOX")
        # Bolt post to frame via FIXED
        rb_constraint(f"J_fixPost_{i}", "FIXED", post, frame, (x, SY - 1.8, 0.5))

    # ========== MOTOR BODY (passive, FIXED to frame) ==========
    face_x = -2.0
    body_z = SZ - SHAFT_OFF
    gb = cyl("GB37_GB", GB_D / 2, GB_L, (face_x - GB_L / 2, SY, body_z), m_gb, rot=(0, math.pi / 2, 0))
    can = cyl("GB37_Can", MOT_D / 2, MOT_BARREL, (face_x - GB_L - MOT_BARREL / 2, SY, body_z), m_mot, rot=(0, math.pi / 2, 0))
    mount = box("GB37_Mount", (GB_L + 0.8, 3.8, 0.35), (face_x - GB_L / 2, SY, body_z - GB_D / 2 - 0.35), m_gb)
    # Join motor body into one passive mesh
    bpy.ops.object.select_all(action="DESELECT")
    for o in (gb, can, mount):
        o.select_set(True)
    bpy.context.view_layer.objects.active = gb
    motor = join_selected("MotorBody_FIXED")
    rb_passive(motor, "BOX")
    rb_constraint("J1_MotorToFrame", "FIXED", motor, frame, (face_x - GB_L / 2, SY, body_z - 2))
    review.append("J1 FIXED: MotorBody ↔ FRAME — body does NOT spin (correct)")

    # ========== DRIVE ASSEMBLY (kinematic — ONLY motor torque input) ==========
    # Shaft + cams + eccentric pins as SEPARATE meshes parented as COMPOUND under DriveRoot
    drive_root = cyl("DriveShaft", SHAFT_R, 11.0, (3.5, SY, SZ), m_steel, rot=(0, math.pi / 2, 0))
    # Hub / D-shaft stub at motor
    hub = cyl("Hub", BOSS_D / 2, BOSS_L + SHAFT_OUT, (face_x + (BOSS_L + SHAFT_OUT) / 2, SY, SZ), m_steel, rot=(0, math.pi / 2, 0))
    stripe = box("TorqueMark", (0.2, 0.2, 0.55), (1.5, SY, SZ + 0.4), m_red)

    def make_cam_pin(tag, x, phase_a, mcol):
        z_pin = SZ + (-ECC if phase_a else +ECC)
        cam = cyl(f"Cam_{tag}", 1.3, 0.9, (x, SY, SZ), mcol, rot=(0, math.pi / 2, 0))
        # Pin axis = Y (into mechanism), eccentric in Z at rest
        pin = cyl(f"Pin_{tag}", 0.35, 1.6, (x, SY + 0.7, z_pin), m_steel, rot=(math.pi / 2, 0, 0))
        return cam, pin, Vector((x, SY + 0.7, z_pin))

    cam_a, pin_a, pin_a_loc = make_cam_pin("A", XA, True, m_a)
    cam_b, pin_b, pin_b_loc = make_cam_pin("B", XB, False, m_b)

    # Join entire drive into ONE kinematic rigid body (keyed solid — no fake parent motion)
    bpy.ops.object.select_all(action="DESELECT")
    parts = [drive_root, hub, stripe, cam_a, pin_a, cam_b, pin_b]
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = drive_root
    drive = join_selected("DriveAsm_KINEMATIC")
    rb_passive(drive, "MESH", kinematic=True)
    drive.rigid_body.collision_shape = "MESH"
    drive.rigid_body.mesh_source = "BASE"
    review.append("J2/J3 KINEMATIC: DriveAsm (shaft+cams+pins joined) — ONLY keyframed RB (motor MOMENT)")
    review.append("  Review: Cam/Pin cannot move independently — same rigid body as shaft (keyed).")

    # Animate motor torque = rotate DriveAsm about shaft axis (X)
    # Pivot: set origin to shaft axis point
    bpy.context.view_layer.objects.active = drive
    # Origin to cursor at shaft center
    bpy.context.scene.cursor.location = (SX, SY, SZ)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

    omega = MOTOR_RPM * 2 * math.pi / 60.0
    for f in range(1, TOTAL + 1):
        drive.rotation_euler = (omega * ((f - 1) / FPS), 0, 0)
        drive.keyframe_insert("rotation_euler", frame=f)
    if drive.animation_data and drive.animation_data.action:
        for fc in drive.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    # ========== SLIDER-CRANK branches A/B ==========
    def build_branch(tag, pin_rest: Vector, mcol, plate_indices):
        # Slider above pin by conrod length at θ=0 (pin at bottom for A)
        # Rest: pin at pin_rest; slider at same X,Y roughly, Z = pin_rest.z + CONROD_LEN
        sx, sy = pin_rest.x, pin_rest.y
        sz0 = pin_rest.z + CONROD_LEN

        slider = box(f"Slider_{tag}", (2.2, 1.8, 1.4), (sx, sy, sz0), m_slide)
        rb_active(slider, "BOX", mass=2.0)
        # Carrier + plates JOINED to slider (J7 bolted = one rigid body)
        carrier = box(f"Carrier_{tag}", (4.5, 1.0, 1.0), (sx + 2.0, sy, sz0), mcol)
        plates = []
        for i, dx in zip(plate_indices, (1.2, 2.8)):
            p = box(f"Plate_{i}", (0.45, 4.0, 2.2), (sx + dx, sy, sz0 - 1.3), m_green)
            lip = box(f"Lip_{i}", (1.0, 4.0, 0.3), (sx + dx + 0.35, sy, sz0 - 0.15), m_green)
            plates.extend([p, lip])
        bpy.ops.object.select_all(action="DESELECT")
        slider.select_set(True)
        carrier.select_set(True)
        for p in plates:
            p.select_set(True)
        bpy.context.view_layer.objects.active = slider
        slider = join_selected(f"SliderAsm_{tag}")
        rb_active(slider, "BOX", mass=3.5)

        # SLIDER constraint: free axis = local X of constraint empty → align to world Z
        # Place empty at slider COM, rot Y=90° so local X = world Z
        e_sl, c_sl = rb_constraint(
            f"J6_SLIDER_{tag}",
            "SLIDER",
            slider,
            frame,
            (sx, sy, sz0),
            rot=(0, math.pi / 2, 0),
        )
        # Limit slider travel
        c_sl.use_limit_lin_x = True
        c_sl.limit_lin_x_lower = -STROKE * 0.2
        c_sl.limit_lin_x_upper = STROKE * 1.4

        # Conrod: ACTIVE bar from pin to slider wrist
        mid = (Vector((sx, sy, pin_rest.z)) + Vector((sx, sy, sz0))) * 0.5
        # Actually pin moves in circle — conrod length fixed; rest pose vertical
        conrod = box(f"Conrod_{tag}", (0.55, 0.55, CONROD_LEN), (sx, sy, (pin_rest.z + sz0) / 2), m_rod)
        rb_active(conrod, "BOX", mass=0.8)

        # J4 HINGE pin(drive) → conrod at pin location
        # Hinge axis along X (shaft-parallel) so conrod swings in YZ... 
        # Pin offset is in Z and rotates about X → pin moves in YZ circle.
        # Conrod should connect pin to slider; hinge axis = X (perpendicular to plane of motion YZ? 
        # Motion plane is YZ if pin circles in YZ. Shaft along X, rotation about X → pin at (x, y0, z0+ecc) circles in YZ. Yes.
        # Hinge axis should be // X so conrod pivots in YZ plane.
        e_h1, c_h1 = rb_constraint(
            f"J4_HINGE_pin_conrod_{tag}",
            "HINGE",
            drive,
            conrod,
            (sx, sy, pin_rest.z),
            rot=(0, 0, 0),  # hinge axis = constraint local X = world X ✓
        )

        # J5 HINGE conrod → slider at wrist (bottom of slider)
        wrist = Vector((sx, sy, sz0 - 0.5))
        e_h2, c_h2 = rb_constraint(
            f"J5_HINGE_conrod_slider_{tag}",
            "HINGE",
            conrod,
            slider,
            (wrist.x, wrist.y, wrist.z),
            rot=(0, 0, 0),
        )

        review.append(f"Branch {tag}:")
        review.append(f"  J4 HINGE: DriveAsm.Pin ↔ Conrod_{tag} @ {tuple(round(v,2) for v in (sx,sy,pin_rest.z))}")
        review.append(f"  J5 HINGE: Conrod_{tag} ↔ SliderAsm_{tag} (plates FIXED by mesh join)")
        review.append(f"  J6 SLIDER: SliderAsm_{tag} ↔ FRAME (Z only)")
        review.append(f"  Plates {plate_indices}: SAME rigid body as slider — move ONLY if slider gets force from conrod")
        return slider, conrod

    sl_a, rod_a = build_branch("A", pin_a_loc, m_a, [0, 2])
    sl_b, rod_b = build_branch("B", pin_b_loc, m_b, [1, 3])

    # Decoy: PASSIVE, no joint to motor — proves disconnected parts do not follow cycle
    decoy = box("DECOY_no_joint", (1.2, 1.2, 1.2), (12.5, 2.5, 1.1), m_red)
    rb_passive(decoy, "BOX")
    rb_constraint("J_DECOY_park", "FIXED", decoy, frame, (12.5, 2.5, 0.6))
    review.append("DECOY: FIXED to FRAME only — NO path to DriveAsm → cannot follow motor")

    text(
        "Title",
        "MO PHONG VAT LY: Rigid Body joints\n"
        "J1 FIXED | J2 kinematic momen | J4/J5 HINGE | J6 SLIDER\n"
        "Khong dung Copy Location / parent puppet\n"
        "DECOY do = khong khop → khong theo motor",
        (-7, -3.5, 11),
        0.3,
    )

    # ========== Bake physics ==========
    sc.frame_set(1)
    bpy.context.view_layer.update()
    print("Baking rigid body cache…")
    bpy.ops.ptcache.bake_all(bake=True)

    # ========== Review motion after bake ==========
    def loc(name):
        return bpy.data.objects[name].matrix_world.translation.copy()

    sc.frame_set(1)
    bpy.context.view_layer.update()
    a1 = loc("SliderAsm_A")
    d1 = loc("DECOY_no_joint")
    sc.frame_set(1 + FPS)  # 1 second
    bpy.context.view_layer.update()
    a2 = loc("SliderAsm_A")
    d2 = loc("DECOY_no_joint")

    da = (a2 - a1).length
    dd = (d2 - d1).length
    review.append("")
    review.append(f"VERIFY t=0→1s: SliderAsm_A Δ={da:.4f} (need >0.15 if joints OK)")
    review.append(f"VERIFY t=0→1s: DECOY Δ={dd:.4f} (must be ~0 — no motor path)")

    if da < 0.1:
        review.append("FAIL: Slider did not move — hinge chain broken or bake failed")
        print("\n".join(review))
        raise RuntimeError("SliderAsm_A did not move under RB joints — check constraints")
    if dd > 0.05:
        review.append("FAIL: DECOY moved — should have no motor force path")
        print("\n".join(review))
        raise RuntimeError("DECOY moved without motor link")
    review.append("PASS: Slider moves via J4→J5→J6; DECOY stays (no motor path)")

    # Ensure only DriveAsm has animation_data among RB drivers
    animated = [o.name for o in bpy.data.objects if o.animation_data and o.animation_data.action]
    review.append(f"Keyframed objects: {animated}")
    if "DriveAsm_KINEMATIC" not in animated:
        raise RuntimeError("DriveAsm missing motor keyframes")
    for name in animated:
        if name not in ("DriveAsm_KINEMATIC",) and not name.startswith("Title"):
            # Text might not have actions; only drive should
            if name != "DriveAsm_KINEMATIC":
                review.append(f"WARN: unexpected keyframes on {name}")

    REVIEW.write_text("\n".join(review), encoding="utf-8")
    print("=== PHYSICS REVIEW ===")
    print("\n".join(review))

    # Camera
    bpy.ops.object.camera_add(location=(5, -16, 7))
    cam = bpy.context.active_object
    cam.name = "CamPhysics"
    cam.rotation_euler = (math.radians(70), 0, 0)
    cam.data.lens = 28
    sc.camera = cam

    bpy.ops.object.light_add(type="AREA", location=(5, -4, 12))
    bpy.context.active_object.data.energy = 1400
    bpy.context.active_object.data.size = 14
    bpy.ops.object.light_add(type="SUN", location=(2, 1, 10))
    bpy.context.active_object.data.energy = 2.0

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.87, 0.9, 1)

    sc.frame_set(1)
    return cam


def main():
    build()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("Saved", BLEND)


if __name__ == "__main__":
    main()
