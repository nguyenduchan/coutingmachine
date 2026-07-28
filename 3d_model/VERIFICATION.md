# Verification — fixed spiral inclined track (máng dốc)

## Geometry reference

[RNA Bowl Feeder for Spring](https://www.youtube.com/shorts/ioa9o-LLHCA) — spiral ramp on bowl wall.

Drive is **rotary** (not vibratory like that video).

## Checklist

| # | Condition | Artifact |
|---|-----------|----------|
| 1 | Fixed `spiral_track` STL exists | `stl_cq/fixed/spiral_track.stl` |
| 2 | Sim shows continuous teal mang doc | GUI / `preview_still.png` |
| 3 | Screws climb track then chute fall-off | `dropped_off_chute >= 3` |
| 4 | Wrong pose back on disc | `wrong_still_in_bowl >= 1` |

```powershell
cd c:\workspace\embedded\CountingMachine\3d_model
python centrifugal_screw_feeder_cq.py
cd sim
python screw_feeder_pybullet.py --gui
```
