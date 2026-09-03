# ESP32-S3 Baseboard — BOM (audit PCB 2026-09-04)

Nguồn: footprint trên `esp32_baseboard.kicad_pcb` + `modules/m3_*.kicad_pcb`.  
Chi tiết mua hàng / giỏ: [`MODULES.md`](MODULES.md) §B.

> **Trạng thái mua: CHƯA MUA gì.** Giỏ Shopee = dự định (§B1 MODULES). Thiếu bắt buộc = §B2.

**Tôpô nguồn:** `J1 → D3 → F1 → D1 → +12V` · Field: `PC817×4 trên carrier` · Stepper: `U5–U7 socket → cáp 6 lõi → ULN module gần motor → 28BYJ@JST`.

---

## A) Carrier — linh kiện hàn trên board

| Ref | Value (silk) | Footprint | SL | Ghi chú mua |
|-----|--------------|-----------|----|-------------|
| **U1** | ESP32-S3 DevKitC | `ESP32_S3_DevKitC_44Pin_Socket` | 1 | DevKit **N16R8** v1.1 + socket 2×22 @2.54 |
| **U2** | MP1584 5V | `MP1584_5V3A` | 1 | Module buck 5V cố định |
| **U3** | TMC2209 | `TMC2209_StepStick` | 1 | Stepstick + heatsink; NEMA17 trên chân Mot |
| **U5** | ULN2003 A1 | `ULN2003_Module` 1×6 | 1 | Socket cái → **M3** (gần motor), không hàn chip lên carrier |
| **U6** | ULN2003 A2 | `ULN2003_Module` 1×6 | 1 | như U5 |
| **U7** | ULN2003 A3 | `ULN2003_Module` 1×6 | 1 | như U5 |
| **J24** | 595_CTRL | `PinHeader_1x06_595CTRL` | 1 | Cắm module **74HC595-24IO** (U10 mua rời) |
| **J25** | 595_Q | `PinHeader_1x24_595Q` | 1 | Q0–23; 12 pha đầu → U5–U7 |
| **J1** | Screw_12V_IN | `TerminalBlock_2P_5.0mm` | 1 | PSU 12V |
| D3 | **SS54** | DO-41 | 1 | Series chống ngược (trên carrier) |
| F1 | Đế 5×20 + T3.15A | `Fuse_Holder_5x20_Open` | 1 | Cầu chì rút ống |
| D1 | **P6KE15A** | DO-41 | 1 | TVS +12V |
| **U41–U44** | **PC817** | `PC817_DIP4` | 4 | HOME1–3 + BUP opto |
| **R41–R44** | **2k2** | axial | 4 | LED series |
| **R45–R48** | **10k** | axial | 4 | Collector PU → 3V3 |
| **C26** | **100n** | 0805 | 1 | HF @ `+12V_SNS` opto |
| **J8** | HOME1 | `JST_XH_02_Socket` | 1 | Dry NC |
| **J10** | HOME2 | `JST_XH_02_Socket` | 1 | Dry NC |
| **J12** | HOME3 | `JST_XH_02_Socket` | 1 | Dry NC |
| **J14** | BUP-30S | `JST_XH_04_Socket` | 1 | Autonics |
| **J15** | BUZZER 5V | `JST_XH_03_Socket` | 1 | Active 5V |
| **J16** | AOD4184 12V | `JST_XH_04_Socket` | 1 | Module MOSFET + bơm 370 |
| **J17** | MSP3520 LCD | `PinHeader_1x09_TFT_LCD` | 1 | TFT pins 1–9 |
| **J23** | MSP3520 TP | `PinHeader_1x05_TFT_TP` | 1 | Touch pins 10–14 |
| **J18** | EC11 ENC | `JST_XH_04_Socket` | 1 | Encoder |
| **R1** | 4k7 | axial | 1 | BUP NPN pull-up |
| **R2** | 10k | axial | 1 | `/EN_TMC` → 3V3 |
| **R3** | 10k | axial | 1 | `/BLOWER` → GND |
| **R4** | 10k | axial | 1 | LDEN/`OE_595` → 3V3 (**bắt buộc**) |
| **R10** | 10R | 1206 | 1 | Star `+12V`→`+12V_SNS` |
| **C10** | 47u/25V | radial Ø~6 | 1 | Bulk SNS |
| **C11** | 100n | 0805 | 1 | HF SNS |
| **C20** | 470u/25V | radial Ø~8 | 1 | Bulk TMC VM |
| **C21** | 220u/25V | radial Ø~6 | 1 | Bulk chung ULN COM (+12V) |
| **C24** | 100n | 0805 | 1 | HF @ TMC |
| **C25** | 100n | 0805 | 1 | HF @ ULN |
| **D2** | **SS24** | DO-41 | 1 | Flyback bơm (K→+12V) — **không** 1N5819 |
| **H1–H4** | M3 | `MountingHole_M3` | 4 | Lỗ vít góc |

**Không còn trên carrier:** J30/M1 · J31A/B/M2 · J2 · J5–J7 · U45–U48 · D4.

---

## B) Sub-module — fab JLCPCB + linh kiện lắp

### B1 — ~~M1~~ **XOÁ** — D3/F1/D1 hàn trên carrier

| Ref | Value | SL | Ghi chú |
|-----|-------|----|---------|
| D3 | **SS54** (hoặc SB560) DO-41 | 1 | Series chống ngược @ J1 |
| F1 | Đế cầu chì PCB 5×20 mở + ống **T3.15A** 250V (dự phòng 5–10 ống) | 1+ | **rút ống khi chảy** |
| D1 | **P6KE15A** DO-41 | 1 | TVS rail +12V |

### B2 — ~~M2~~ **XOÁ** — PC817×4 + 2k2/10k + C26 hàn trên carrier

### B3 — M3 `m3_uln2003` ×**3** (gần động cơ; cáp từ U5/U6/U7)

| Ref | Value | SL / board | Tổng ×3 | Ghi chú |
|-----|-------|------------|---------|---------|
| P1 | Pin header đực 1×6 @2.54 | 1 | **3** | Cáp 6 lõi từ socket U5–U7 |
| U1 | **ULN2003AN** DIP-16 | 1 | **3** | COM=+12V; IN5–7→GND |
| J1 | **JST-XH 5P** cái | 1 | **3** | 28BYJ A/B/C/D/+12V |
| C1 | **100n** 0805 | 1 | **3** | HF local COM |

**Thay thế fab M3:** mua sẵn **28BYJ(12V)+ULN2003** Shopee ×3 (giỏ §B1) — vẫn nối 6 dây vào U5–U7; không bắt buộc fab `m3_uln2003`.

Panel snap: `modules/submodules_panel.kicad_pcb` (M3 only).

---

## C) Module / thiết bị cắm ngoài (không hàn lên PCB)

| Mục | SL | Cắm vào | Ghi chú |
|-----|----|---------|---------|
| Mean Well **LRS-50-12** | 1 | J1 | PSU |
| **74HC595-24IO** (3×595) | 1 | J24+J25 | “U10” — không footprint riêng |
| **28BYJ-48 12V** | **3** | M3.J1 (hoặc ULN Shopee) | **Không** bản 5V |
| **NEMA17** 42×34 | 1 | U3 Mot | |
| Limit dry NC + XH-2 | 3 | J8/J10/J12 | |
| Autonics **BUP-30S** | 1 | J14 | |
| TFT MSP3520 ILI9488 | 1 | J17+J23 | |
| EC11 encoder | 1 | J18 | |
| Buzzer active 5V | 1 | J15 | |
| Module **AOD4184** | 1 | J16 | |
| Bơm khí **370 12V** | 1+1 | qua AOD4184 | |
| Cáp 6 lõi U5–U7↔M3 | 3 | — | IN1–4/GND/+12V |
| Header cái 1×5 / 1×6 (nếu chưa gồm footprint THT) | — | J23 / J24 / U5–7 | Female module |

---

## D) Tổng hợp SL mua (passive + IC trên carrier + M3)

| Linh kiện | SL | Nơi dùng |
|-----------|----|----------|
| SS54 DO-41 | 1 | Carrier D3 |
| P6KE15A DO-41 | 1 | Carrier D1 |
| Đế fuse 5×20 PCB + ống T3.15A (+spare) | 1 bộ | Carrier F1 |
| **SS24** DO-41 | 1 | Carrier D2 |
| PC817 DIP-4 | **4** (+dự phòng) | Carrier U41–U44 |
| 2k2 axial | **4** | Carrier R41–R44 |
| 10k axial | **4+3=7** | R45–R48 + R2/R3/R4 |
| 4k7 axial | 1 | R1 |
| 10Ω 1206 | 1 | R10 |
| 100n 0805 | **1+3+2=6** | C26 + M3.C1×3 + C11+C24+C25 |
| 47µF 25V radial | 1 | C10 |
| 220µF 25V radial Ø6 | 1 | C21 |
| 470µF 25V radial Ø8 | 1 | C20 |
| ULN2003AN DIP-16 | **3** | M3 (hoặc module Shopee) |
| JST-XH 5P cái | **3** | M3.J1 |
| JST-XH 2P cái | 3 | J8/10/12 |
| JST-XH 3P cái | 1 | J15 |
| JST-XH 4P cái | 3 | J14/J16/J18 |
| Pin header cái 1×5 | 1 | J23 |
| Pin header cái 1×6 | **4** | J24 + U5+U6+U7 |
| Pin header cái 1×9 | 1 | J17 |
| Pin header cái 1×24 | 1 | J25 |
| Pin header đực 1×6 | M3×3 | Daughters |
| Terminal 2P 5.0 | 1 | J1 |
| Socket 2×22 ESP32 | 1 | U1 |
| PCB carrier | 1 | ~180×145 (xem gen) |
| PCB M3 panel | 1 panel | JLCPCB 2L |

---

## E) Lệch so với tài liệu cũ (đã sửa)

| Cũ | Đúng (PCB hiện tại) |
|----|---------------------|
| PC817 U41–U48 ×8 / M2 pluggable | **U41–U44 ×4 + R + C26 trên carrier** |
| D2 = 1N5819 | **D2 = SS24** |
| J30/M1 pluggable | **XOÁ — D3/F1/D1 trên carrier** |
| J31A/B / M2 pluggable | **XOÁ — opto hàn carrier** |
| ULN hàn / socket DIP trên carrier | **U5–U7 = 1×6 socket → M3 gần motor** |
| C21 footprint tên `100u` | Silk **220u/25V** (mua 220µF Ø6) |
| Field IN5–8 / J19–J22 | **Đã bỏ** |
