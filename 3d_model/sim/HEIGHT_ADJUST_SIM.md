# Height_Adjust sim — spur rack & pinion (exact FreeCAD meshes)

## Active CAD parts (print / bolt)
| Part | Role |
|------|------|
| `HA_Pinion_Shaft` | Pinion + shaft **fused** (one 3D print) |
| `HA_Bearing_Rail_S/N` | Lower saddle + rail; bolt to base (M3) |
| `HA_Bearing_Cap_S/N` | Upper half; **M3** clamp onto journals |
| `HA_Knob` | Drive; **M3 cross-bolt** onto shaft end |
| `HA_Friction_Washer` | Friction hold |
| `HA_Follower` | Rack + Z slide |

## Hardware
**M3×16 ISO hex bolt + M3 hex nut** (wrench AF 5.5)
- Clearance hole Ø**3.6** mm (FDM)
- Cap: counterbore Ø6.5 × 2.2 for hex head
- Rail: square nut pocket 6.0 AF × 2.8 deep
- Per side: 2× M3 on **±X** (one each side of pinion shaft); knob: 1× M3 through D-flat
- **C1** one solid rail+bearing+web | **C2** ±X M3 beside shaft | **C3** local nut access under holes (re-cut after fuse)

## Assembly
1. Bolt rails S/N to base.
2. Drop `HA_Pinion_Shaft` into open saddles (mesh rack).
3. Cap on journals; **M3×16** from above into nut pockets (4× total).
4. Washer + knob; **1× M3** through knob into shaft flat.

Remove: reverse — unbolt caps, lift pinion-shaft out.

## Kinematics
- Pinion axis **Y** ⊥ rack travel **Z**
- m=2, z=18, α=20° → ~113 mm/turn

## Pipeline
```bash
freecadcmd 3d_model/freecad/export_height_adjust_meshes.py
python 3d_model/sim/height_adjust_pybullet.py [--gui]
```
