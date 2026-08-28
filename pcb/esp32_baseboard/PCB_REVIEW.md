# ESP32 Baseboard — yêu cầu bắt buộc trước khi đặt PCB

Carrier **225 × 132 mm**, 2 lớp, sinh bằng `gen_power_carrier.py`.

**Chạy cổng tự động (bắt buộc):**

```powershell
cd pcb\esp32_baseboard
python gen_power_carrier.py
python verify_pcb.py
```

Chỉ đặt PCB khi `verify_pcb.py` → **OVERALL: PASS** **và** mục **Manual** bên dưới đã tick.

---

## A. Chính sách routing (bắt buộc)

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| A1 | **Không via routing** — chỉ đổi lớp tại pad THT (header/module xuyên 2 mặt) | `verify_pcb.py` đếm `(via` = 0 |
| A2 | Maze autoroute F.Cu + B.Cu (H/V tung mat); **net tin hieu khac nhau tren cung mat khong duoc cat nhau** (xem A5) | `USE_MAZE_AUTOROUTE = True` + `_check_signal_routing.py` |
| A3 | Bus phuc vu B.Cu (TFT, motor/power) sau maze — **moi net tin hieu mot kenh rieng** (`BusLaneAllocator`) | Silk B.SilkS; khong GND spine doc toan board (tranh cham net) |
| A4 | Mọi net có ≥2 pad phải **một đảo đồng** (pad ↔ track ↔ via pad) | `_check_net_copper.py` → OPEN = 0 |
| A5 | **Tín hiệu cùng mặt không cắt nhau** — hai net tín hiệu khác nhau trên F.Cu hoặc B.Cu **không được giao nhau** (giao trong thân đoạn, không tính chung điểm đầu/cuối) | `_check_signal_routing.py` → crossings = 0 |
| A6 | **Không chồng colinear** — hai net tín hiệu khác nhau không được nằm cùng đường thẳng H/V chồng đồng trên một mặt | `_check_signal_routing.py` → colinear = 0 |
| A7 | **Không xuyên lỗ / quá sát lỗ** — track giữ khoảng cách ≥ drill/2 + **0,25 mm** + nửa bề rộng track + **0,2 mm** clearance tới mọi pad THT/NPTH **khác net** (M3 H1–H4, header, module) | `_check_signal_routing.py` → hole hits = 0 |

**Net nguồn** (không áp A5/A6): `GND`, `+5V`, `+3V3`, `+12V`, `+12V_RAW`, `+12V_SNS`, `/OPTO_VCC_I`, `/BLW_RET`.

**Net tín hiệu**: mọi net còn lại (GPIO, motor logic, TFT, opto IN/OUT, …).

Điểm nối pad của **cùng net** được phép (fanout ≤ 1 mm từ tâm lỗ).

---

## B. ESP32-S3 DevKitC-1 (bắt buộc)

| # | Yêu cầu | Script |
|---|---------|--------|
| B1 | 28 GPIO chức năng khớp `s3_pinmap.py` | `verify_esp32_nets.py` |
| B2 | **Không** dùng IO35 / IO36 / IO37 (octal PSRAM N16R8) | `verify_esp32_nets.py` |
| B3 | IO0, IO19, IO20, TX0, RX0, RST **không** route | `verify_esp32_nets.py` |
| B4 | `/OPTO_OUT8` **không** vào U1 (IO9 = `/ENC_A`) | `verify_connectivity.py` |
| B5 | R2 pull-up `/EN_TMC`; R3 pull-down `/BLOWER`; D2 freewheel bom | `verify_connectivity.py` §E/F |

---

## C. Module ↔ jack (bắt buộc)

| # | Khối | Kiểm |
|---|------|------|
| C1 | U3 TMC2209 ↔ J2 NEMA17 ↔ IO16/17/18 | `verify_connectivity.py` §B |
| C2 | U4/U9 opto ↔ J4 field + J8–J13 limit + J14 BUP | §C |
| C3 | U5–U7 DRV8871 ↔ J5–J7 GA12-N20 ↔ IO10–15 | §D |
| C4 | J17 TFT pinout (SPI + touch, không T_INT) | §E |
| C5 | J18 EC11 ENC_A/B → IO9 / IO41 | §E |
| C6 | J15 buzzer IO38; J16 blower IO3 + **+12V** (không U8) | §E |
| C7 | J1 → F1 PTC → +12V; **U2** MP1584 5V; R10 SNS | §F |

---

## D. Điện & an toàn (bắt buộc)

| # | Yêu cầu |
|---|---------|
| D1 | +12V_RAW có F1 PTC + D1 TVS tại đầu vào |
| D2 | Star sense: R10/C10/C11 + `+12V_SNS` tới limit/BUP |
| D3 | **Một** buck 5V (U2) cho logic; bơm **12V** từ rail `+12V` qua J16 |
| D4 | DRV8871 VM = +12V; logic = +3V3/+5V theo module |
| D5 | Không net tín hiệu chạm net nguồn trên pad U1 |

---

## E. Kiểm tra geometry / DRC (bắt buộc)

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| E1 | Kích thước **225 × 132 mm** ±0.5 mm | `verify_pcb.py` |
| E2 | **KiCad DRC = 0 loi** (clearance, annular ring, silk) — bat buoc | pcbnew -> Inspect -> DRC |
| E2a | Heuristic Python `_check_overlaps.py` (tham khao; co the bao cao nhieu hon DRC) | `verify_pcb.py` hien WARN neu fail |
| E3 | 4x M3 mounting inset 3.5 mm tu canh | KiCad + silk |
| E4 | Khong footprint module chong (< 6 mm giua U*) | `_check_overlaps.py` (info) |
| E5 | **A5–A7 bat buoc** — xem muc A | `_check_signal_routing.py` |

---

## F. Manual — sign-off người (bắt buộc trước fab)

- [ ] Mở `esp32_baseboard.kicad_pcb` — bật F.Cu + B.Cu, zoom bus trái (TFT) và bus phải (motor)
- [ ] **A5–A7**: không thấy dây tín hiệu cắt nhau trên cùng mặt; không track cắt qua lỗ M3 / lỗ header
- [ ] DRC chạy với rule 2-layer fab (clearance ≥ 0.2 mm, track ≥ 0.2 mm)
- [ ] 3D/preview: ESP32 socket, TMC, DRV không đụng nhau; jack hướng đúng silk
- [ ] BOM khớp `README.md` + `MODULES.md` (DevKitC-1 **N8R2**, không N16R8V)
- [ ] Gerber export: kiểm tra lớp `.GTL` / `.GBL` / `.GKO` đúng 225 mm
- [ ] Ghi chú fab: **2 layer**, **1.6 mm**, **HASL hoặc ENIG**, **không impedance controlled**

---

## G. Lệnh nhanh

```powershell
# Regenerate + full gate
python gen_power_carrier.py
python verify_pcb.py

# Từng bước
python _check_net_copper.py
python verify_connectivity.py
python verify_esp32_nets.py
python _check_overlaps.py
python _check_signal_routing.py
python repair_open_nets.py   # chi khi OPEN > 0 sau sửa generator
```

---

## H. Khi FAIL

1. Sửa `gen_power_carrier.py` / `maze_router.py` / `s3_pinmap.py` — **không** sửa tay `.kicad_pcb` (sẽ mất khi regen).
2. Chạy lại `gen_power_carrier.py` → `verify_pcb.py`.
3. Nếu OPEN > 0: xem log maze + `repair_open_nets.py`; cân nhắc thêm `BOARD_W` hoặc bus lane.
4. Neu A5/A6 fail: tang `BusLaneAllocator.pitch`, doi lop (F/B), hoac `BOARD_W` — tin hieu phai co kenh rieng tung mat.
5. Neu A7 fail: ne track qua header/M3; sua maze keepout hoac bus_y margin.
