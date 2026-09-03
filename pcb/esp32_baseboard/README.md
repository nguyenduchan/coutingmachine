# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595-24IO module)

**BOM đầy đủ (audit PCB):** [`BOM.md`](BOM.md) · **Module / mua hàng:** [`MODULES.md`](MODULES.md) · **Review:** [`PCB_REVIEW.md`](PCB_REVIEW.md).

PSU **Mean Well 12V**. Limits = mechanical HOME only (J8/J10/J12). Board = jacks + drivers; **D3/F1/D1 + PC817×4 hàn trên carrier**; **M3 gần động cơ**.

## On-board (carrier)

| Ref | Part | Role |
|-----|------|------|
| J1 | Terminal 2P 5.0 | 12V PSU in (RAW) |
| **D3** | **SS54** Schottky | Series chống ngược |
| **F1** | Đế 5×20 + ống **T3.15A** | Cầu chì rút ống |
| **D1** | **P6KE15A** TVS | Clamp surge trên +12V |
| **U41–U44** | **PC817** DIP-4 ×4 | HOME1-3 + BUP opto |
| **R41–R44 / R45–R48** | 2k2 / 10k | LED series / collector PU |
| **C26** | 100n | SNS HF @ opto |
| U1 | ESP32-S3-DevKitC-1 N16R8 | MCU |
| U2 | MP1584EN 5V | Logic buck (only) |
| U3 | TMC2209 | NEMA17 trên Mot (không J2) |
| J24 / J25 | Header cái 1×6 + 1×24 | Cắm **74HC595-24IO** (U10 mua rời) |
| R4 | 10k axial | LDEN/`OE` pull-up → +3V3 |
| U5–U7 | Socket **1×6** → **M3** | Cáp gần 28BYJ; JST trên M3 |
| R1 | 4k7 | BUP NPN pull-up → OPTO_IN4 |
| R2/R3 | 10k | EN_TMC PU / BLOWER PD |
| R10 / C10 / C11 | 10Ω / 47µ / 100n | Star SNS |
| D2 | **SS24** flyback | Blower inductive kick (rail TVS = D1) |
| C20 | 470µ | Bulk @ TMC |
| C21 | 220µ | Shared ULN VCC bulk |
| C24 / C25 | 100n 0805 | HF @ TMC / ULN |
| ~~J2~~ | — | **XOÁ** (Mot trên U3) |
| ~~J5–J7~~ | — | **XOÁ** (28BYJ trên M3) |
| ~~J30 / M1~~ | — | **XOÁ** — D3/F1/D1 trên carrier |
| J8/J10/J12 | **JST-XH 2P** | HOME dry NC SIG/SNS |
| J14 | **JST-XH 4P** | BUP-30S |
| J15 | **JST-XH 3P** | Buzzer 5V |
| J16 | **JST-XH 4P** | AOD4184 blower |
| J18 | **JST-XH 4P** | EC11 ENC |
| J17/J23 | 1×09 / 1×05 @2.54 | TFT LCD + touch |

**Pluggable (JLCPCB snap):** [`modules/`](modules/) — `m3_uln2003`, `submodules_panel`. Chi tiết SL: [`BOM.md`](BOM.md).

**Deleted:** J2, J5–J7, J30/M1, J31A/B/M2; PC817 trên carrier.

> All footprints on **TOP (F.Cu)**; **đi dây ưu tiên B.Cu** + **GND pour F+B**.

## An toàn điện — nguy cơ chập / cháy / cắm ngược

Chuỗi nguồn: `J1 → D3 SS54 → F1 đế 5×20 T3.15A → D1 TVS → +12V`.  
Opto: `PC817×4 + 2k2/10k` trên carrier. Panel: `modules/submodules_panel.kicad_pcb` (M3).

### Nguy cơ điện

| Mức | Nguy cơ | Bảo vệ | Ghi chú |
|-----|---------|--------|---------|
| **Cao** | Cắm **ngược** dây 12 V tại J1 | **D3 Schottky series** + silk `+`/`−`/`NO REVERSE` | Screw **không** khóa cơ — bắt buộc D3 + dây đỏ/đen |
| **Cao** | 28BYJ **5 V** trên rail 12 V | Chỉ mua **28BYJ-12V** | R-8 MODULES |
| **Cao** | NEMA17 stall / Vref cao | C20; F1 ống; FW timeout | Heatsink TMC |
| Trung | Chập +12V sau F1 | **F1 5×20 T3.15A** (rút ống) + track Power 1,0 mm | Dự phòng ống |
| Trung | Surge / ESD 12 V | **D1 P6KE15A** | K = +12V |
| Trung | Bơm inductive kick | **D2 SS24** @ J16 | Rail TVS = D1 |
| Trung | 595 boot → ULN kéo tải | **R4 OE pull-up** | Bắt buộc |
| Trung | J16 MOSFET cắm lệch | Silk pin + **JST-XH 4P keyed** | PWM/GND/+12V/FAN− |
| Thấp | HOME SNS chập GND | R2k2 + opto trên M2 | Không nối GPIO←12V |
| Thấp | Chập +5V logic | MP1584 limit nội | Tuỳ chọn PTC 0,5 A |

### Giắc / đế — ưu tiên chống ngược

| Giắc | Loại hiện tại | Chống ngược? | Hành động lắp |
|------|---------------|--------------|---------------|
| **J1** | Screw 2P 5,0 | Silk + D3 điện | Dây **đỏ=+ / đen=−**; không đảo |
| **F1** | Đế 5×20 PCB | — | Rút ống khi chảy |
| J8/10/12 | **JST-XH 2P** | **Có** | Dry NC SIG/SNS |
| J14 | **JST-XH 4P** | **Có** | BUP Brn/Blu/Blk/Wht |
| J15/J16/J18 | **XH-3 / XH-4** | **Có** | Không hàn pin trần |
| J17+J23 | TFT 9+5 @2.54 | Module 2 hàng cố định | Không đảo hàng |
| J24/J25 | 595 CTRL+Q | Module Shopee cố định | Khớp silkscreen module |
| U1/U3/U5–7 | Socket module | Pin1 notch / silkscreen | Đúng hướng module |

**Không thay:** D3 ≥5 A Schottky; F1 ống **T ~3 A** 5×20; D1 uni TVS ~15 V; **không** bỏ khóa JST-XH field I/O.

## GPIO

| Function | GPIO |
|----------|------|
| HOME OUT1-3 / BUP OUT4 | IO1,2,4,5 |
| SER / SRCLK / RCLK / OE_595 | IO10–13 |
| TMC STEP/DIR/EN | IO16–18 |
| TFT SPI + BL + touch | IO39/40/42/21/46/45 + MISO47 T_CS48 T_IRQ6 |
| ENC_A / ENC_B | IO38 / IO41 |
| Buzzer / blower | IO9 / IO3 |
| Spare | IO7,8,14,15 |

## Chống nhiễu khi đi dây (EMI / EMC)

Board 2 lớp, tải động cơ + SPI TFT + opto 12 V — nhiễu chủ yếu từ **return path**, **loop diện tích**, và **đường dài dưới module**. Áp dụng khi route / review:

| # | Đề xuất | Trên board này |
|---|---------|----------------|
| N1 | **Pour GND hai mặt** (F.Cu + B.Cu), thermal relief pad THT | Zone GND inset 0,5 mm mép; fill sau FreeRouting |
| N2 | **Tín hiệu dài trên B.Cu**; F.Cu chỉ fan-out pad→via (A0) | FreeRouting prefer B ngang / F dọc |
| N3 | **Return GND sát tín hiệu** — tránh “đảo” GND đứt bởi bus dài | Pour liên tục; via stitch khi đổi lớp |
| N4 | **Nguồn rộng + star tại J1** — +12V / GND không dùng chung đường mỏng với GPIO | Netclass Power **1,00 mm**; star silk tại J1 |
| N5 | **Bulk sát tải nhiễu** — C20 ≤10 mm TMC VM; C21 chung ULN COM | Placement floorplan |
| N6 | **Vòng motor nhỏ** — MotA/B cặp gần nhau; 28BYJ trên **M3 gần motor** | E10.5 |
| N7 | **Tách êm / ồn** — HMI+MCU đông; POWER+TMC+ULN+opto tây/nam | Eco cụm E11 |
| N8 | **SPI / ENC ngắn** — J17/J23/J18 gần U1; không vòng quanh motor | Floorplan HMI |
| N9 | **Cách ly field 12 V** — HOME/BUP vào opto; không nối thẳng GPIO | PC817 + R series |
| N10 | **Via một cỡ 0,4/0,8** (A8); ưu tiên đổi lớp tại pad THT (A1) | Ít via “lạ”, dễ fab |
| N11 | **Không chạy bus dưới cụm module trên F.Cu** | A0 + Manual tick |
| N12 | Clearance track↔lỗ ≥ A7 (0,45 mm trong DSN) | `route_freerouting` inject |

**Khi fab / lắp:** dây motor xoắn hoặc cặp gần nhau; GND PSU ngắn tới J1; cable TFT/ENC tránh song song dài với dây 12 V motor.

Chi tiết bắt buộc: `PCB_REVIEW.md` mục **A0 / A8 / A10 / E10**.

## Regenerate

```powershell
$env:PCB_SKIP_MAZE=1; python gen_power_carrier.py
python gen_schematic_from_pcb.py
& "$env:LOCALAPPDATA\Programs\KiCad.0in\python.exe" route_freerouting.py
python verify_all.py
```

Board **180×145 mm** (bội 5; layout XY đóng băng; Eco ≥10 mm mép). Modules ≥10 mm mép; ≥10 mm MCU Eco; ≥8 mm giữa Ecos. Power netclass **1,00 mm** (peak +12V ~2,3 A).
