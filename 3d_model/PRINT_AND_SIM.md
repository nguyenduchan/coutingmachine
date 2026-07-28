# Screw Rotary Disc Feeder — CountingMachine
# Printer: Bambu Lab P1S (256 x 256 x 256 mm)

## Mục đích
Hệ thống cấp phôi ốc vít dạng **đĩa xoay** (rotary indexing disc):
1. Hopper chứa ốc vít hàng loạt
2. Đĩa xoay có pocket bắt từng con ốc
3. Cửa sổ xả trên base + máng outlet đưa ốc ra từng viên
4. Brush/wiper hạn chế kẹt / double-feed

Các file STL tách riêng để:
- In 3D trên Bambu P1S
- Đưa vào mô phỏng chuyển động (đĩa + hub quay quanh trục Z)

## Cài phần mềm đã dùng
- **OpenSCAD 2021.01** — `C:\Program Files\OpenSCAD\openscad.exe`
- **Python 3.12** + `trimesh`, `matplotlib` — render preview

Mở mô hình chỉnh tham số:
```
& "C:\Program Files\OpenSCAD\openscad.exe" "c:\workspace\embedded\CountingMachine\3d_model\screw_rotary_feeder.scad"
```

## Cấu trúc thư mục
```
3d_model/
  screw_rotary_feeder.scad   # nguồn parametric
  export_*.scad / export/    # wrapper xuất từng chi tiết
  stl/                       # file in / mô phỏng
  preview/                   # ảnh PNG
  render_preview.py          # render assembly từ STL
  PRINT_AND_SIM.md           # file này
```

## Chi tiết STL (in được)
| File | Vai trò | Chuyển động mô phỏng |
|------|---------|----------------------|
| `base_plate.stl` | Đế + cửa sổ xả + vòng bắt vít | Cố định |
| `rotary_disc.stl` | Đĩa 12 pocket | Quay Z (revolute) |
| `drive_hub.stl` | Hub khóa đĩa + lỗ trục NEMA17 Ø5 mm (D-shaft) | Quay Z cùng đĩa |
| `hopper.stl` | Phễu nạp | Cố định |
| `cover.stl` | Vành giữ ốc trên đĩa | Cố định |
| `outlet_chute.stl` | Máng ra phôi | Cố định |
| `brush_arm.stl` | Giá gắn chổi/TPU wipe | Cố định |
| `assembly_reference.stl` | Ghép tham chiếu (không in nguyên khối) | — |

## Thông số mặc định (chỉnh trong Customizer OpenSCAD)
- Ốc tham chiếu: head Ø6.5 × 2.5, shank Ø3.2 × 12 (gần M3–M4)
- Đĩa Ø140 × dày 6, **12 pocket**
- Đế Ø160 — vừa giường P1S
- Lỗ trục hub: Ø5.2 + D-flat; bore đế Ø16.2 (608ZZ / bạc)

Đổi `screw_head_d`, `screw_shank_d`, `pocket_count`, `disc_od` theo loại ốc thực tế rồi xuất lại STL.

## Gợi ý in Bambu P1S (Bambu Studio)
| Chi tiết | Hướng in | Layer | Infill | Support | Ghi chú |
|----------|----------|-------|-------|---------|---------|
| base_plate | Đáy nằm giường | 0.20 | 30–40% | Không | Gyroid / grid |
| rotary_disc | Đáy nằm giường | 0.16–0.20 | 40–60% | Không | PETG/ABS chịu mòn tốt hơn PLA |
| hopper | Flange dưới | 0.20 | 20% | Có thể cần | Thành mỏng |
| cover | Đáy dưới | 0.20 | 20% | Không | |
| drive_hub | Flange dưới | 0.16 | 50%+ | Không | Siết set-screw M2.5/M3 |
| outlet_chute | Đáy kênh | 0.20 | 30% | Tùy | |
| brush_arm | Đáy phẳng | 0.20 | 30% | Không | Chèn lông nylon / in TPU lưỡi gạt |

Tolerance lắp: giữ nguyên `pocket_clearance = 0.6`; nếu ốc kẹt thì tăng 0.1–0.2 mm.

## Mô phỏng chuyển động
- Khớp quay: trục Z qua tâm `drive_hub` / `rotary_disc`
- Bước index: `360 / pocket_count` = **30°** / pocket (12 ô)
- Xuất phôi khi pocket trùng cửa sổ trên `base_plate` (hướng +X mặc định)
- Animate trong OpenSCAD: chỉnh `disc_angle`
- Frame PNG: `preview/motion_frames/`
- Render lại:
```
python c:\workspace\embedded\CountingMachine\3d_model\render_preview.py
```

## Xuất lại STL sau khi sửa .scad
```powershell
$openscad = "C:\Program Files\OpenSCAD\openscad.exe"
$root = "c:\workspace\embedded\CountingMachine\3d_model"
foreach ($p in @("base_plate","rotary_disc","hopper","cover","outlet_chute","drive_hub","brush_arm")) {
  & $openscad -o "$root\stl\$p.stl" "$root\export\$p.scad"
}
```

## Phần cứng gợi ý (ngoài in 3D)
- Động cơ NEMA17 + driver (TB6600 / BTT)
- Khớp nối 5 mm hoặc bắt trực tiếp hub
- Vòng bi 608ZZ (tuỳ chọn) hoặc bạc nhựa in
- Vít M3 bắt đế / nắp / hopper
- Cảm biến quang tại outlet để đếm (CountingMachine)
