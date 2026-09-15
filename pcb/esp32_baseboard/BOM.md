# ESP32 Baseboard → STM32G030 carrier — BOM (2026-09-15)

SoT mua hàng / ước giá.  
**PCB SoT:** `python gen_compact_carrier.py` → board **110×100 mm** (`esp32_baseboard.kicad_pcb`) — giắc field chỉ N/S; W/E để gài DIN.  
**Pinmap:** `stm32_pinmap.py` · **Verify:** `python verify_compact.py`

> **CHƯA MUA gì.**  
> **MCU: STM32G030C8T6** (LQFP48).  
> Nạp: **ARM Cortex Debug-10** (`J_DBG`) + UART tùy chọn (**CH340 + USB**).  
> **Layout DIN (bắt buộc):**  
> - **Cạnh dưới (S):** `J1` 24V → `J_MOT1`/`J_MOT2` (XH-4) + đế TMC/U_PWR — **không** kéo motor từ giắc sẵn trên module.  
> - **Cạnh trên (N):** cảm biến đếm → IN → keypad → display (gần MCU) · USB · debug.  
> - **Trái/phải:** không giắc field (DIN). Linh kiện không phải giắc ngoài: **cách Edge.Cuts ≥4 mm**.  
> - **Giắc N/S:** hàng chân **song song cạnh** (rot 90° / ngang) — không đặt dọc.  
> - **Giữa:** opto cách ly · **Trên lòng:** MCU 3V3 · **Dưới lòng:** 24V/buck/driver.  
> **Chính sách lắp:**  
> - **SMT / dán sẵn:** chỉ phần dùng chung (MCU, nguồn, TVS/PTC bảo vệ, opto, HMI IC, USB…).  
> - **Chân đế / giắc:** hàn tay — **U3/U4, J_MOT*, J_*, nút**.  
> - **Driver đắt:** **không dán sẵn** — cắm module khi cần.  
> Sensor: **NPN only** (không PNP). J14/J15 đếm + J_IN2/J_IN3.

**Tôpô bảo vệ (24V):**  
`J1 → D3(SS54 SMA) → F1(T2A) → +24V ← D1(SMBJ26A)`  
Motor1: `+24V → PTC_MOT 1.1A → +24V_MOT → U3`  
Motor2: `+24V → PTC_MOT2 1.1A → +24V_MOT2 → U4`  
SNS: `+24V → PTC_SNS 0.2A → R10 22Ω → +24V_SNS` → J14/J15/J_IN2/J_IN3  
Logic: `+24V → U2 → +5V ← D5(SMBJ5.0A) → U6 → +3V3 → U1`

**MCU / debug:**  
`U1 STM32G030C8T6` · `J_USB → U5 CH340C + Y1 12MHz` · USART1 **PA9/PA10**  
`J_DBG` CoreSight-10: VTREF(+3V3) / SWDIO(**PA13**) / SWCLK(**PA14**/BOOT0) / SWO(**PB3**) / nSRST · pin7 KEY  
`R_NRST`+`C_NRST`+`SW_NRST` · `R_BOOT` PD + `R_SWDIO` PU · `SW_BOOT` kéo BOOT0 lên 3V3

---

## GPIO (STM32 ports)

| Chức năng | Pin |
|-----------|-----|
| TMC1 STEP / DIR / EN (U3) | PA0 / PA1 / PA2 |
| TMC2 STEP / DIR / EN (U4) | PA6 / PA7 / PA8 |
| Count opto `/BUP` | PA3 |
| Input2 `/IN2` · Input3 `/IN3` | PB15 · PB4 |
| **U_PWR** PWM1/PWM2 / EN / DIR / FAULT | PA11 / PA12 / PB5 / PB6 / PB7 |
| **U_VIB** CTRL / FAULT | PB8 / PB9 |
| TM1637 CLK / DIO | PA4 / PA5 |
| Keypad ROW0–3 | PB0 / PB1 / PB2 / PB10 |
| Keypad COL0–3 | PB11 / PB12 / PB13 / PB14 |
| USART1 TX / RX (CH340) | PA9 / PA10 |
| SWDIO / SWCLK(BOOT0) / SWO | PA13 / PA14 / PB3 |

---

## Board

| | |
|--|--|
| Kích thước | **110×100 mm** (SoT; giắc ngoài chỉ cạnh trên/dưới) |
| Generator | `gen_compact_carrier.py` (placement + nets, **no copper**) |
| MCU | **STM32G030C8T6** LQFP48 SMT |
| Hàn tay sau | J1, F1, U3/U4, **J_MOT1/2**, **U_PWR**, **U_VIB**, J14/J15, J_IN2/3, J_DISP, J_KEY, J_DBG, SW_* |
| Module socket | U3/U4 TMC · U_PWR MOSFET/DC-vib · U_VIB SSR — cắm khi cần |
| Motor field | **J_MOT1 / J_MOT2** XH-4 cạnh dưới — không dùng giắc Mot trên StepStick |

---

## A) SMT dán sẵn

| Ref | Value / package | SL |
|-----|-----------------|----|
| **U1** | **STM32G030C8T6** LQFP48 | 1 |
| U2 | MP1584EN SOT-23-8 | 1 |
| U5 | CH340C SOP-16 | 1 |
| U6 | AMS1117-3.3 SOT-223 | 1 |
| U7 | TM1637 SOP-20 | 1 |
| U44 / U45 / U46 | PC817 SOP-4 (count / IN2 / IN3) | 1 mỗi |
| PTC_MOT / PTC_MOT2 / PTC_SNS | 1812 1.1A / 1.1A / 0.2A | 1 mỗi |
| J_USB | USB Micro-B SMT | 1 |
| C_MCU / C_MCU2 | 100n / 1µ @+3V3 gần U1 | 1 mỗi |
| R_NRST / C_NRST | 10k / 100n | 1 mỗi |
| R_BOOT / R_SWDIO | 10k PD BOOT0 · 10k PU SWDIO | 1 mỗi |
| Rfb / Cbst / Cc + R/C bulk | như trước (24V/5V/3V3) | — |

## B) Hàn tay sau

| Ref | Value | Ghi chú |
|-----|-------|---------|
| J1 | Terminal 2P 5.0 | 24V IN |
| F1 | Đế 5×20 + ống **T2A** | |
| U3 | Đế StepStick | TMC1 — NEMA17 chính |
| **J_MOT1** | Mot_XH_04 (XH-4) | Pha motor 1 cạnh board (A2 A1 B1 B2) |
| U4 | Đế StepStick | TMC2 — chống kẹt / trống |
| **J_MOT2** | Mot_XH_04 (XH-4) | Pha motor 2 cạnh board |
| **U_PWR** | Đế 2×6 `PowerMod_2CH_Sock` | Module MOSFET / H-bridge / rung **24 V** (2 CH) |
| **U_VIB** | Đế 1×4 `VibAC_Sock` | Module **SSR / máng rung AC** |
| J14 / J15 | JST-XH 4P / 3P | cảm biến **đếm** NPN (chọn 1) |
| **J_IN2** | JST-XH 3P | input2 NPN |
| **J_IN3** | JST-XH 3P | input3 NPN |
| J_DISP / J_KEY | 1×10 / 1×8 | HMI ngoài |

### Pinout U_PWR (2×6)

| Pin | Net | Pin | Net |
|-----|-----|-----|-----|
| 1 | +24V | 2 | +24V |
| 3 | GND | 4 | GND |
| 5 | +3V3 | 6 | /PWR_FAULT |
| 7 | /PWM_OUT1 | 8 | /PWM_OUT2 |
| 9 | /PWR_EN | 10 | /PWR_DIR |
| 11 | GND | 12 | GND |

### Pinout U_VIB (1×4)

| Pin | Net |
|-----|-----|
| 1 | +24V (SSR input supply) |
| 2 | GND |
| 3 | /VIB_CTRL |
| 4 | /VIB_FAULT |
| **J_DBG** | **Cortex Debug 10-pin 1.27 mm** (Samtec FTSH-105 class; pin7 KEY) | ST-Link / ULINK |
| SW_BOOT / SW_NRST | Tact 6×6 | BOOT0 / reset |

### Pinout J_DBG (ARM CoreSight-10)

| Pin | Tín hiệu | Net |
|-----|----------|-----|
| 1 | VTREF | +3V3 |
| 2 | SWDIO | /SWDIO (PA13) |
| 3 | GND | GND |
| 4 | SWCLK | /SWCLK (PA14) |
| 5 | GND | GND |
| 6 | SWO | /SWO (PB3) |
| 7 | KEY | không chân (NPTH) |
| 8 | TDI (SWD NC) | GND |
| 9 | GNDDetect | GND |
| 10 | nSRST | /NRST |

## C) Field (ngoài board)

TMC2209 · NEMA17 · 7seg · keypad · BUP **hoặc** fiber · PSU LRS-*-24 — như trước.

## D) Ước giá (1 board mid, VND · 2026-09)

**Chính sách:** JLC/PCBA **chỉ SMT mục A**. **Đế cắm + giắc + nút (mục B) tự mua + hàn tay** — không gửi nhà máy dán.

Giả định: lot **5 tấm**, PCB **110×100** 2L HASL, ship amort, mua linh kiện VN/LCSC mid.

### 1) Nhà máy (PCBA SMT)

| Hạng mục | Low–High / tấm | Mid | Ghi chú |
|----------|----------------|-----|---------|
| **PCB trần** 2L 110×100 | 25–55k | **~35k** | >100×100 → mất promo $2/5; ~$15–25/5 + ship |
| **Linh kiện SMT (A)** | 80–120k | **~100k** | MCU 15–25 · buck/USB/CH340/TM1637/opto/PTC/TVS/R/C |
| **Phí dán SMT** | 70–140k | **~100k** | setup + place amort 5; ~50–70 điểm SMT |
| **Cộng PCBA (A)** | **≈180–300k** | **~235k** | board ra lò, **chưa** đế/giắc |

### 2) Hàn tay sau (mục B) — đế & giắc

| Nhóm | SL | Mid / tấm | Ghi chú |
|------|-----|-----------|---------|
| Đế StepStick U3/U4 | 2 | **20–30k** | 2× female 2.54 (16 chân/module) |
| Đế U_PWR 2×6 | 1 | **5–10k** | |
| Đế U_VIB 1×4 | 1 | **2–4k** | |
| J1 terminal 2P + F1 đế 5×20 | 1+1 | **10–18k** | + ống T2A ~3–5k |
| J_MOT1/2 XH-4 | 2 | **10–16k** | |
| JST đếm/IN (J14/15/IN2/IN3) | 4 | **12–20k** | |
| J_KEY 1×8 + J_DISP 1×10 | 2 | **5–10k** | |
| J_DBG Cortex-10 | 1 | **15–35k** | clone FTSH; chính hãng đắt hơn |
| SW_BOOT / SW_NRST | 2 | **2–4k** | |
| **Cộng hàn tay (B)** | | **≈80–140k** | mid **~100k** (linh kiện; công hàn tự làm ≈0) |

### 3) Tổng 1 board đủ chân (chưa module driver)

| | Mid | Dải |
|--|-----|-----|
| PCBA SMT (A) | **~235k** | 180–300k |
| Đế/giắc hàn tay (B) | **~100k** | 80–140k |
| **Board hoàn thiện chân** | **~335k** | **≈260–440k** |

### 4) Module cắm thêm (không tính vào board trần)

| Module | Mid / cái |
|--------|-----------|
| TMC2209 StepStick | 80–150k (×1 hoặc ×2) |
| MOSFET / H-bridge (U_PWR) | 50–150k |
| SSR máng rung (U_VIB) | 30–80k |

PSU 24 V, NEMA, cảm biến, 7seg, keypad = **field**, ngoài ước giá board.

