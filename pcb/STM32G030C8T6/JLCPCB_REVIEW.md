# Review PCB trước khi đặt JLCPCB

Board: **2 lớp FR-4 1.6 mm, 1 oz, 180×120 mm**, HASL chì-free. Gia công sai + dán
SMT rất đắt — **không upload Gerber** nếu `verify_pre_fab.py` không PASS toàn bộ.

Hạn mức: [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities)
+ [assembly rails/fiducials](https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order)
+ [assembly T&C](https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service).
Mã hoá trong `jlcpcb_limits.py`. KiCad DRC cùng ngưỡng trong
`STM32G030C8T6.kicad_pro` + `STM32G030C8T6.kicad_dru`.

## Một lệnh (bắt buộc)

```text
cd pcb/STM32G030C8T6
python verify_pre_fab.py
```

Phải **PASS toàn bộ**. Không “PASS trừ routing”, không “PASS trừ LCSC”.

| # | Script | Chặn gì (fail = không đặt) |
|---|--------|----------------------------|
| 1 | `verify_schematic.py` | Mỗi chân schematic đúng net; ERC |
| 2 | `verify_fab.py` | Ý đồ mạch ↔ schematic ↔ pad PCB |
| 3 | `verify_compact.py` | STM32 / nguồn / giắc / opto / TMC đúng chân + courtyard |
| 4 | `verify_orientation.py` | Diode K, tụ hóa +, IC pin 1, USB miệng, TMC EN, giắc pin 1 |
| 5 | `verify_jlcpcb.py` | Lỗ, vành pad, mép, 24 V, plug gap, track/via, courtyard SMT |
| 6 | `verify_jlc_bom.py` | Mọi SMD dán phải có mã LCSC; THT = DNP/hàn tay |
| 7 | `kicad-cli pcb drc --schematic-parity` | Short, hở đồng, clearance, lỗ |
| 8 | `verify_track_width.py` | Track ≥ 0.20 mm và đủ IPC-2221 cho dòng 24 V |
| 9 | CAM dry-run | Gerber F/In1/In2/B.Cu + Mask + Silk + Edge + drill + CPL |

JSON: `out/pre_fab_report.json`, `out/fab_verify.json`, `out/orientation_verify.json`, `out/jlcpcb_verify.json`, `out/jlc_bom_verify.json`.

## Thuật toán từng cổng

**Orientation** — pad 1 diode = anode, pad 2 = cathode (vạch silk); tụ hóa pin 1 = `+`;
LQFP/SOIC pin 1 góc tây-bắc (rot 0°); USB rot 180° miệng bắc; TMC EN tây / VM đông;
giắc N pin 1 = `+V`. JSON: `out/orientation_verify.json`.

**Nets** — mỗi chân P() trên generator phải cùng tên net trên schematic XML và
pad PCB. Rail nguồn không được dính nhau.

**DFM** — parse footprint/pad/lỗ trên `.kicad_pcb`:

- 2 lớp, 1.6 mm, 180×120 trong envelope JLC.
- Drill PTH 0.15–6.3 mm; NPTH ≥ 0.50 và đúng **4× Ø3.2 M3**.
- Annular PTH ≥ 0.18 (nhà ≥ 0.20). SMD pad ≥ 0.25.
- Lỗ tường–tường khác footprint ≥ 0.45 mm.
- Đồng/lỗ ≥ 0.20 mm tới Edge.Cuts.
- Pad khác net không chồng; **+24V\* ≥ 0.40 mm** tới net khác (JLC min 0.10 không đủ 24 V).
- **Có track** (board chưa route = FAIL). Track ≥ 0.15, via nhà 0.4/0.8, không blind/buried.

**DFA** — courtyard SMT không chồng (+0.3 mm). Thân SMT ≥ 2.5 mm mép (giắc N/S loại trừ).
Giắc field cùng hàng: khe housing ≥ **5 mm** (hai phích không chạm). Fiducial thiếu =
cảnh báo (JLC gắn rail). Silk < 1.0 mm = cảnh báo.

**BOM SMT** — mọi footprint `smd` không nằm danh sách DNP-THT phải có `C` + số LCSC
trên schematic (`property "LCSC"`) hoặc `jlc_lcsc.csv`. Xoay CPL 0/90/180/270.
Map kho: `jlc_lcsc.csv`. J_USB = SMT Molex; F1 5×20 THT = DNP/hàn tay.

**KiCad DRC** — `unconnected_items`, `shorting_items`, `clearance`, `hole_to_hole`,
`annular_width`, `copper_edge_clearance` là FATAL. Silk/lib cosmetics bỏ.

## Tay trên jlcpcb.com (chỉ sau script xanh)

1. **PCB:** 2 layer · 1.6 mm · 1 oz · green · HASL lead-free · 180×120.
2. Zip `out/jlc_cam/` (Gerber + `.drl`). Chạy **JLCDFM** trên trang order.
3. Confirm outline kín; H1–H4 là **NPTH**; không nhầm PTH.
4. **SMT:** Economic, **front only**. JLC có thể thêm 5 mm rail + fiducial.
   Check 2D polarity: USB, SMA diode, AMS1117 tab, LQFP pin 1, điện phân.
5. BOM: cột LCSC cho SMT; giắc/đế THT = **Do not place** / hand solder.
6. Tải 2D/3D production, nhìn từng linh kiện phân cực, **rồi mới Confirm**.

## Ngưỡng cứng

- Track/space ≥ **0.15 mm** (JLC 0.10; nhà 0.15). KiCad min_track **0.20**.
- PTH annular ≥ **0.18**. Via nhà **0.4 / 0.8**.
- Hole wall-to-wall ≥ **0.45**. Copper-to-edge ≥ **0.20** (KiCad 0.30).
- **0** unconnected, **0** short, **0** clearance DRC.
- 24 V pad ≥ **0.40 mm**. Jack housing ≥ **5 mm**.
- SMT LCSC đủ 100%. Courtyard SMT overlap = 0.
- Diode / tụ hóa / IC pin 1 / USB miệng: `verify_orientation.py` PASS.

## Danh sách bài kiểm tra

Cổng đặt hàng = `python verify_pre_fab.py` (phải PASS hết). Script lẻ chạy được riêng.

### Bắt buộc trước khi đặt JLCPCB

| Script | Việc kiểm tra |
|--------|----------------|
| `verify_schematic.py` | ERC schematic; mỗi chân đúng net (J1, D3, MCU, USB…) |
| `verify_fab.py` | Schematic ↔ pad PCB cùng net; ERC; sanity nguồn không dính |
| `verify_compact.py` | STM32 pinmap, chuỗi 24 V, giắc N/S, opto, TMC, courtyard |
| `verify_orientation.py` | Chiều diode/tụ/IC/USB/TMC/giắc (pin 1, K, `+`) |
| `verify_jlcpcb.py` | DFM JLC: lỗ, annular, mép, 24 V clearance, track/via, courtyard, khe giắc |
| `verify_jlc_bom.py` | SMT có mã LCSC; giắc/đế THT = DNP |
| `verify_track_width.py` | Track ≥ 0.20 mm; bề rộng đủ dòng IPC-2221 |
| `kicad-cli pcb drc` | Short, hở đồng, clearance, lỗ (trong `verify_pre_fab.py`) |
| CAM dry-run | Xuất Gerber 4 lớp + drill + CPL + BOM (`out/jlc_cam/`) |

Báo cáo tổng: `out/pre_fab_report.json`.

### Hỗ trợ / không chặn đặt hàng STM32

| Script | Ghi chú |
|--------|---------|
| `verify_drc.py` | Chỉ DRC KiCad (trùng cổng trong pre_fab) |
| `_check_net_copper.py` | Đảo đồng theo net (dùng khi debug route) |
| `_check_signal_routing.py` | A5–A7 cắt tín hiệu cùng mặt |
| `_check_edge_clear.py` | Linh kiện cách mép |
| `label_silk.py` | Nhãn silk giắc |

### Legacy — board ESP32 / M3 cũ, **không** dùng cho carrier STM32

| Script | Lý do bỏ qua |
|--------|----------------|
| `verify_all.py` | Pinmap ESP32, M1/M2, `_check_rot` allowlist cũ |
| `verify_STM32G030C8T6_nets.py` | GPIO ESP32-S3 |
| `verify_connectivity.py` | 74HC595 + ULN + TFT |
| `verify_modules.py` | Panel M3 ULN2003 |
| `verify_pcb.py` | Kích thước 190×100 ESP32-era |

## Không đặt khi

Board **0 segment / 0 via** (generator không đi dây). Thiếu LCSC. Lỗ giắc chồng.
DRC còn unconnected. Sửa xong chạy lại `python verify_pre_fab.py`.
