# ESP32 Baseboard — BOM mới nhất (2026-09-13)

SoT mua hàng / ước giá.  
**PCB SoT:** `python gen_compact_carrier.py` → board **100×100 mm** (`esp32_baseboard.kicad_pcb`; J_USB cạnh nam; J1→D3→F1 cạnh tây).  
Legacy `gen_power_carrier.py` (180×145 S3+595) **không** dùng cho fab mới.

Giá: Shopee VN + JLCPCB Economic (ước, **chưa voucher**, USD≈25.500₫).

> **CHƯA MUA gì.**  
> **Toàn bộ linh kiện chức năng = SMT dán** (JLCPCB / paste).  
> **Chân / đế / giắc = hàn tay sau:** J1, F1 đế cầu chì, U3 đế TMC, J14/J15 XH, J_DISP, J_KEY, **SW_BOOT, SW_EN**.  
> MCU: **ESP32-WROOM-32** + **CH340C** + USB Micro-B SMT + **AMS1117-3.3**.  
> Nạp/debug: crystal 12 MHz + auto DTR/RTS (C+NPN) + pull-up EN/IO0/IO2 + nút BOOT/EN.  
> Buck: **MP1584EN** + L SMD + Schottky SMA + Rfb. Rail **24V → 5V → 3V3**.  
> HMI: **TM1637** SOP-20 trên board; **7seg + keypad ngoài** (giắc).  
> In thử: **5 mạch** SMT full + hàn tay chân đế.

**Tôpô bảo vệ (24V):**  
`J1 → D3(SS54 SMA) → F1(T2A đế 5×20) → +24V ← D1(SMBJ26A)`  
Motor: `+24V → PTC_MOT 1.1A (1812) → +24V_MOT → U3 VM + C20/C24`  
SNS: `+24V → PTC_SNS 0.2A (1812) → R10 22Ω 1206 → +24V_SNS || C10 47µ || C11/C26 100n`  
Logic: `+24V → U2 → +5V ← D5(SMBJ5.0A) → U6 → +3V3`  
Bulk: **C21 220µ SMD @+24V** · **C20 470µ SMD + C24 100n @+24V_MOT** · **C5/C51 @+5V** · **C3/C31 @+3V3**  
**Placement:** chuỗi J1→D3→F1 khóa cạnh Tây (F1 dọc, ra +24V về Nam); mọi tải sau F1 (phía Nam/Đông).

**Buck rời:** `+24V → U2(MP1584EN) SW → L1 10µH → +5V` ; D4 SS34 SMA ; Rfb1 52k3 / Rfb2 10k ; Cbst 10n ; Cc 3n3

**USB-UART / auto-program:**  
`J_USB Micro-B SMT → U5 CH340C` · `Y1 12MHz + C_XI/C_XO 22p` · `C52/C53 100n`  
`DTR —C_DTR 100n— /IO0` + `DTR —R_DTR 10k— Q1(S8050) → /IO0`  
`RTS —C_RTS 100n— /EN` + `RTS —R_RTS 10k— Q2(S8050) → /EN`  
Pull-up: `R_EN / R_IO0 / R_IO2` 10k → +3V3 · Nút: `SW_BOOT(/IO0), SW_EN(/EN)`

---

## GPIO (14 chân chức năng + strap boot)

| Chức năng | GPIO |
|-----------|------|
| TMC STEP / DIR / EN | 16 / 17 / 18 |
| BUP opto (U-slot **hoặc** fiber) | 4 |
| TM1637 CLK / DIO | 22 / 23 |
| Keypad ROW0–3 (qua J_KEY) | 13 / 12 / 14 / 27 |
| Keypad COL0–3 (qua J_KEY) | 26 / 33 / 32 / 5 |
| **Tổng chức năng** | **14** |
| Boot strap (không HMI) | IO0, IO2, EN |

---

## Board

| | |
|--|--|
| Kích thước | **100 × 100 mm** (J1→D3→F1 cạnh Tây; tải 24V sau F1; J_USB cạnh nam; ESP32 anten lên; gap ≥2.0 mm) |
| Generator | `gen_compact_carrier.py` |
| Verify | `python verify_compact.py` |
| SMT | **toàn bộ IC / R / C / L / diode / TVS / PTC / PC817 / USB / WROOM / CH340 / crystal / S8050** |
| Hàn tay sau | **chân đế / giắc / 2 nút tact** (xem mục B) |
| Module socket | **chỉ U3 TMC2209** |
| Rail chính | **+24V** (PSU Mean Well LRS-*-24) |

---

## A) SMT dán sẵn (JLCPCB / paste)

| Ref | Value / package | SL |
|-----|-----------------|----|
| U1 | ESP32-WROOM-32 | 1 |
| U2 | MP1584EN SOT-23-8 | 1 |
| U5 | CH340C SOP-16 | 1 |
| U6 | AMS1117-3.3 SOT-223 | 1 |
| U7 | TM1637 SOP-20 | 1 |
| U44 | **PC817 SOP-4** | 1 |
| Q1 / Q2 | **S8050 SOT-23** (auto BOOT / EN) | 1 mỗi |
| Y1 | **12 MHz** crystal 3225 | 1 |
| L1 | 10µH ~6×6 SMD | 1 |
| D3 | **SS54 SMA** | 1 |
| D4 | **SS34 SMA** | 1 |
| D1 | **SMBJ26A** (SMB TVS @+24V) | 1 |
| D5 | **SMBJ5.0A** (SMB TVS @+5V) | 1 |
| PTC_MOT | **1812 PTC 1.1A hold** (≥30V, vd. 1812L110 / MF-MSMF110) | 1 |
| PTC_SNS | **1812 PTC 0.2A hold** (≥30V, vd. 1812L020 / MF-MSMF020) | 1 |
| J_USB | **USB Micro-B SMT** (vd. LCSC C10418) | 1 |
| Rfb1 / Rfb2 | 52k3 / 10k 0805 | 1 mỗi |
| Cbst / Cc | 10n / 3n3 0805 | 1 mỗi |
| C_XI / C_XO | **22p** 0805 (crystal load) | 1 mỗi |
| C_DTR / C_RTS | **100n** 0805 (DTR→IO0, RTS→EN) | 1 mỗi |
| C52 / C53 | **100n** 0805 (CH340 V3 / VCC) | 1 mỗi |
| R_DTR / R_RTS | **10k** 0805 (base Q1/Q2) | 1 mỗi |
| R_EN / R_IO0 / R_IO2 | **10k** 0805 pull-up | 1 mỗi |
| R1/R2/R10/R44/R48 | 4k7 / 10k / **22R 1206** / 2k2 / 10k | 1 mỗi |
| C11/C24/C26/C51/C31 | 100n 0805 | 5 |
| C10 | **47µ/50V SMD** elec ~6.3×5.8 | 1 |
| C21 | **220µ/50V SMD** elec ~6.3×5.8 | 1 |
| C20 | **470µ/50V SMD** elec ~8×10 | 1 |
| C5 | **100µ/16V SMD** elec | 1 |
| C3 | **47µ/10V SMD** elec | 1 |

## B) Hàn tay sau (chân / đế / giắc / nút)

| Ref | Value | Ghi chú |
|-----|-------|---------|
| **J1** | Terminal 2P 5.0 mm | 24V IN |
| **F1** | Đế cầu chì 5×20 + ống **T2A** time-lag | đế hàn tay; chặt hơn T2.5A với LRS-50-24 |
| **U3** | Female header / đế StepStick | cắm TMC2209 |
| **J14** | JST-XH 4P | BUP-U (nếu dùng) |
| **J15** | JST-XH 3P | fiber (nếu dùng) |
| **J_DISP** | PinHeader 1×10 | LED 7seg ngoài |
| **J_KEY** | PinHeader 1×8 | keypad ngoài |
| **SW_BOOT** | Tact 6×6 mm | IO0→GND (nạp tay) |
| **SW_EN** | Tact 6×6 mm | EN→GND (reset) |

**Không** hàn LED 7seg / keypad lên board.

## C) Field / cắm (ngoài board)

| Ref | Thiết bị | Giắc trên board | Ghi chú |
|-----|----------|-----------------|---------|
| — | **TMC2209 StepStick** | U3 socket | VM = **+24V_MOT** (sau PTC_MOT) |
| — | NEMA17 | qua TMC | |
| **J_DISP** | LED 7seg 3 số CC | PinHeader 1×10 | G1–G3 + A–G từ U7 |
| **J_KEY** | Keypad matrix 4×4 | PinHeader 1×8 | R0–3 / C0–3 |
| **J14** *hoặc* **J15** | BUP-U / fiber amp **12–24V** | XH-4 / XH-3 | Chỉ lắp **một** |
| **J1** | PSU | Terminal 2P | **LRS-*-24** |

### Cảm biến đếm (chọn 1 khi lắp)

| Giắc | Loại | Pin | Ghi chú |
|------|------|-----|---------|
| **J14** | Hồng ngoại chữ U (BUP-30S NPN) | XH-4: +24 / GND / OUT | Model **12–24V** |
| **J15** | Sợi quang + amp NPN | XH-3: +24 / GND / OUT | Model **12–24V** |
| Chung | PC817 → GPIO4 `/BUP` | | NPN OC wire-OR; **không cắm cả hai** |

### Pinout J_DISP (1×10)

| Pin | Net | Tới LED |
|-----|-----|---------|
| 1–3 | /TM_G1…G3 | GRID 1–3 (CC) |
| 4–10 | /TM_SA…SG | SEG A–G |

### Pinout J_KEY (1×8)

| Pin | Net |
|-----|-----|
| 1–4 | /KEY_R0…R3 |
| 5–8 | /KEY_C0…C3 |

## D) Ước giá (1 máy mid, cập nhật SMT)

PCBA SMT full (kèm USB-UART + auto-prog) ~**350–460k** · hàn tay chân đế + 2 nút ~**25–45k** nhân công  
+ TMC + NEMA + LRS-50-24 + HMI + cảm biến (IR hoặc fiber) → xem ước giá trước (~**1,3–2,2tr**/máy tùy cảm biến).
