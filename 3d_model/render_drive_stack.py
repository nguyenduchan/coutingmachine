"""Preview drive stack: motor + base + hub + frame."""
from pathlib import Path
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "preview_cq"
MOV = ROOT / "stl_cq" / "moving"
FIX = ROOT / "stl_cq" / "fixed"
REF = ROOT / "stl_cq" / "reference"
OUT.mkdir(exist_ok=True)

BASE_T = 10.0


def load(path: Path) -> trimesh.Trimesh:
    m = trimesh.load_mesh(path, force="mesh")
    if not isinstance(m, trimesh.Trimesh):
        m = m.dump(concatenate=True)
    return m


def xf(m, x=0, y=0, z=0, rz=0):
    out = m.copy()
    T = np.eye(4)
    if rz:
        a = np.deg2rad(rz)
        c, s = np.cos(a), np.sin(a)
        T[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    T[:3, 3] = [x, y, z]
    out.apply_transform(T)
    return out


def plot(items, title, path, elev=18, azim=-55, max_faces=10000):
    fig = plt.figure(figsize=(11, 8.5), facecolor="#f2f2f2")
    ax = fig.add_subplot(111, projection="3d")
    meshes = []
    for mesh, color in items:
        meshes.append(mesh)
        faces = mesh.faces
        if len(faces) > max_faces:
            faces = faces[np.linspace(0, len(faces) - 1, max_faces, dtype=int)]
        coll = Poly3DCollection(mesh.vertices[faces], linewidths=0.04, alpha=0.9)
        coll.set_facecolor(color)
        coll.set_edgecolor((0.1, 0.1, 0.1, 0.15))
        ax.add_collection3d(coll)
    v = np.vstack([m.vertices for m in meshes])
    c = v.mean(0)
    span = (v.max(0) - v.min(0)).max() / 2 * 1.2
    ax.set_xlim(c[0] - span, c[0] + span)
    ax.set_ylim(c[1] - span, c[1] + span)
    ax.set_zlim(c[2] - span * 0.6, c[2] + span * 0.8)
    ax.set_xlabel("X mm")
    ax.set_ylabel("Y mm")
    ax.set_zlabel("Z mm")
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    ax.set_box_aspect([1, 1, 0.9])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path)


def main():
    items = [
        (xf(load(REF / "geared_motor_GB37_24V.stl"), z=0), "#1abc9c"),
        (xf(load(FIX / "motor_clamp.stl"), z=-4), "#7f8c8d"),
        (xf(load(FIX / "base.stl")), "#2c3e50"),
        (xf(load(MOV / "shaft_collar.stl"), z=1.5), "#e67e22"),
        (xf(load(MOV / "drive_hub.stl"), z=BASE_T - 1), "#c0392b"),
        (xf(load(MOV / "rotor_spiral.stl"), z=BASE_T + 2, rz=20), "#e74c3c"),
        (xf(load(FIX / "frame_riser.stl"), x=85, z=-48), "#8e44ad"),
    ]
    plot(items, "Drive stack: GB37 motor + clamp + base + hub + rotor", OUT / "drive_stack.png")
    plot(items, "Drive stack (side)", OUT / "drive_stack_side.png", elev=5, azim=-90)

    # Exploded drive only
    exp = [
        (xf(load(REF / "geared_motor_GB37_24V.stl"), z=-35), "#1abc9c"),
        (xf(load(FIX / "motor_clamp.stl"), z=-18), "#7f8c8d"),
        (xf(load(FIX / "base.stl"), z=0), "#2c3e50"),
        (xf(load(MOV / "shaft_collar.stl"), z=18), "#e67e22"),
        (xf(load(MOV / "drive_hub.stl"), z=35), "#c0392b"),
        (xf(load(MOV / "rotor_spiral.stl"), z=55, rz=15), "#e74c3c"),
        (xf(load(FIX / "frame_riser.stl"), x=95, z=-70), "#8e44ad"),
    ]
    plot(exp, "Exploded drive / frame mount (print parts separately)", OUT / "drive_exploded.png", elev=15, azim=-50)


if __name__ == "__main__":
    main()
