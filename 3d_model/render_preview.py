"""Render CountingMachine rotary screw feeder STL assembly to PNG previews."""
from pathlib import Path
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(r"c:\workspace\embedded\CountingMachine\3d_model")
STL = ROOT / "stl"
OUT = ROOT / "preview"
OUT.mkdir(exist_ok=True)

# Matches screw_rotary_feeder.scad assembly() transforms
BASE_T = 8.0
DISC_T = 6.0
BASE_OD = 160.0
OUTLET_DEPTH = 28.0
OUTLET_W = 10.0
DISC_OD = 140.0


def load(name: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(STL / name, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh.dump(concatenate=True)
    return mesh


def transform(mesh: trimesh.Trimesh, mat: np.ndarray) -> trimesh.Trimesh:
    m = mesh.copy()
    m.apply_transform(mat)
    return m


def T(x=0, y=0, z=0, rz_deg=0):
    m = np.eye(4)
    if rz_deg:
        a = np.deg2rad(rz_deg)
        c, s = np.cos(a), np.sin(a)
        m[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    m[:3, 3] = [x, y, z]
    return m


def build_assembly(disc_angle=0.0, explode=0.0):
    ez = explode * 30.0
    parts = [
        ("base_plate.stl", T(), "#4a4a4a"),
        ("drive_hub.stl", T(z=BASE_T - 2 - ez * 0.3), "#6b6b6b"),
        ("rotary_disc.stl", T(z=BASE_T + 0.5 + ez, rz_deg=disc_angle), "#2f6fed"),
        ("cover.stl", T(z=BASE_T + DISC_T + 0.2 + ez), "#8a9bb0"),
        ("hopper.stl", T(z=BASE_T + DISC_T + 1 + ez * 1.5), "#3d8b8b"),
        (
            "outlet_chute.stl",
            T(x=BASE_OD / 2 - OUTLET_DEPTH - 4, y=-(OUTLET_W + 10) / 2, z=-2 - ez * 0.5),
            "#e87722",
        ),
    ]
    # brush arm: rotate 140° then translate
    brush = load("brush_arm.stl")
    brush = transform(brush, T(x=DISC_OD / 2 - 20, y=-5, z=BASE_T + DISC_T + 8 + ez))
    brush = transform(brush, T(rz_deg=140))
    meshes = []
    colors = []
    for fname, mat, color in parts:
        meshes.append(transform(load(fname), mat))
        colors.append(color)
    meshes.append(brush)
    colors.append("#8b5a2b")
    return meshes, colors


def plot_meshes(meshes, colors, title, out_path, elev=28, azim=-55, max_faces=12000):
    fig = plt.figure(figsize=(11, 8.5), facecolor="#f4f4f4")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#f4f4f4")
    for mesh, color in zip(meshes, colors):
        m = mesh
        if len(m.faces) > max_faces:
            # uniform face subset for speed
            idx = np.linspace(0, len(m.faces) - 1, max_faces, dtype=int)
            faces = m.faces[idx]
        else:
            faces = m.faces
        tris = m.vertices[faces]
        coll = Poly3DCollection(tris, linewidths=0.05, alpha=0.92)
        coll.set_facecolor(color)
        coll.set_edgecolor((0.15, 0.15, 0.15, 0.25))
        ax.add_collection3d(coll)

    all_v = np.vstack([m.vertices for m in meshes])
    center = all_v.mean(axis=0)
    span = (all_v.max(axis=0) - all_v.min(axis=0)).max() / 2 * 1.15
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span * 0.4, center[2] + span * 1.1)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=13, pad=12)
    ax.set_box_aspect([1, 1, 0.75])
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("wrote", out_path)


def plot_part(stl_name, title, out_path, color="#2f6fed"):
    mesh = load(stl_name)
    plot_meshes([mesh], [color], title, out_path, elev=35, azim=-60)


def main():
    plot_part("rotary_disc.stl", "Rotary disc (motion part)", OUT / "rotary_disc.png")
    plot_part("base_plate.stl", "Base plate (fixed)", OUT / "base_plate.png", "#4a4a4a")
    plot_part("hopper.stl", "Hopper", OUT / "hopper.png", "#3d8b8b")
    plot_part("drive_hub.stl", "Drive hub (keyed to disc)", OUT / "drive_hub.png", "#6b6b6b")
    plot_part("cover.stl", "Cover ring", OUT / "cover.png", "#8a9bb0")
    plot_part("outlet_chute.stl", "Outlet chute", OUT / "outlet_chute.png", "#e87722")
    plot_part("brush_arm.stl", "Brush arm", OUT / "brush_arm.png", "#8b5a2b")

    meshes, colors = build_assembly(disc_angle=0, explode=0)
    plot_meshes(meshes, colors, "Screw rotary disc feeder — assembly", OUT / "assembly.png")

    meshes_e, colors_e = build_assembly(disc_angle=20, explode=1.0)
    plot_meshes(
        meshes_e,
        colors_e,
        "Screw rotary disc feeder — exploded (sim / assembly aid)",
        OUT / "exploded.png",
        elev=25,
        azim=-45,
    )

    # Motion frames for simulation reference
    frames_dir = OUT / "motion_frames"
    frames_dir.mkdir(exist_ok=True)
    for i, ang in enumerate(range(0, 360, 30)):
        m, c = build_assembly(disc_angle=ang, explode=0)
        plot_meshes(
            m,
            c,
            f"Motion frame  angle={ang} deg",
            frames_dir / f"frame_{i:02d}_a{ang:03d}.png",
            elev=40,
            azim=-70,
            max_faces=8000,
        )


if __name__ == "__main__":
    main()
