# ESP32 Baseboard → STM32G030 carrier — BOM (2026-09-15)

SoT mua hàng / ước giá.  
**PCB SoT:** `python gen_compact_carrier.py` → board **185×120 mm** (`esp32_baseboard.kicad_pcb`) — giắc field chỉ N/S; W/E để gài DIN.  
**Pinmap:** `stm32_pinmap.py` · **Verify:** `python verify_compact.py`

> **CHƯA MUA gì.**  
> **MCU: STM32G030C8T6** (LQFP48).  
> Nạp: **USB (CH340)** + nút **BOOT0 / NRST** — **không** giắc J_DBG (lot nhỏ).  
> **Layout DIN (bắt buộc):**  
> - **Cạnh dưới (S):** `J1` 24V → `J_MOT1`/`J_MOT2` (XH-4) + đế TMC/**U_PWR1+U_PWR2** — **không** kéo motor từ giắc sẵn trên module.  
> - **Cạnh trên (N):** cảm biến đếm → IN → keypad → display (gần MCU) · USB · debug.  
> - **Trái/phải:** không giắc field (DIN). Linh kiện không phải giắc ngoài: **cách Edge.Cuts ≥4 mm**.  
> - **Giắc N/S:** hàng chân **song song cạnh** (rot 90° / ngang) — không đặt dọc.  
> - **Giữa:** opto cách ly · **Trên lòng:** MCU 3V3 · **Dưới lòng:** 24V/buck/driver.  
> **Chính sách lắp:**  
> - **SMT / dán sẵn:** chỉ phần dùng chung (MCU, nguồn, TVS/PTC bảo vệ, opto, USB…). TM1637 nằm trên **module ngoài**.  
> - **Giắc / đế (mục B): chỉ hàn khi SKU cần** — PCB vẫn có đủ pad cho 3 hạng; không hàn = để trống.  
> - **Driver đắt:** **không dán sẵn** — cắm module khi cần.  
> Sensor: **NPN only** (không PNP). J14/J15 đếm **24 V** · **J_CNT5 đếm 5 V** · J_IN2/J_IN3.

**Tôpô bảo vệ (24V):**  
`J1 → D3(SS54 SMA) → F1(T2A) → +24V ← D1(SMBJ26A)`  
Motor1: `+24V → PTC_MOT 1.1A → +24V_MOT → U3`  
Motor2: `+24V → PTC_MOT2 1.1A → +24V_MOT2 → U4`  
SNS: `+24V → PTC_SNS 0.2A → R10 22Ω → +24V_SNS` → J14/J15/J_IN2/J_IN3  
Logic: `+24V → U2 → +5V ← D5(SMBJ5.0A) → U6 → +3V3 → U1`

**MCU / debug:**  
`U1 STM32G030C8T6` · `J_USB → U5 CH340C + Y1 12MHz` · USART1 **PA9/PA10**  
Nạp UART: giữ **BOOT0** (`PA14`/`SWCLK`) + `SW_BOOT` / `SW_NRST` · `R_BOOT` PD · `R_SWDIO` PU · **không J_DBG**

---

## GPIO (STM32 ports)

| Chức năng | Pin |
|-----------|-----|
| TMC1 STEP / DIR / EN (U3) | PA0 / PA1 / PA2 |
| TMC2 STEP / DIR / EN (U4) | PA6 / PA7 / PA8 |
| Count opto `/BUP` | PA3 |
| **Count 5V `/CNT5`** | **PD1** |
| Input2 `/IN2` · Input3 `/IN3` | PB15 · PB4 |
| **U_PWR1 / U_PWR2** PWM / EN / FAULT | PA11+PB5 · PA12+PB6 · PB7 shared |
| **U_VIB** CTRL / FAULT | PB8 / PB9 |
| TM1637 CLK / DIO (**J_DISP** → module) | PA4 / PA5 |
| Keypad ROW0–3 | PB0 / PB1 / PB2 / PB10 |
| Keypad COL0–3 | PB11 / PB12 / PB13 / PB14 |
| USART1 TX / RX (CH340) | PA9 / PA10 |
| SWDIO / SWCLK(BOOT0) | PA13 / PA14 (USB-UART boot; no SWO) |

---

## Board

| | |
|--|--|
| Kích thước | **185×120 mm** (auto-grow nếu courtyard gap &lt;2.5 mm; tối đa 300 mm) |
| Generator | `gen_compact_carrier.py` (placement + nets, **no copper**) |
| MCU | **STM32G030C8T6** LQFP48 SMT |
| Hàn tay sau | **Chỉ hàn giắc/đế khi SKU cần** (pad đủ trên PCB). Luôn: J1, F1, J_USB, SW_*, J_DISP; tùy hạng: MOT/TMC/PWR/VIB/SNS/KEY/IN |
| Module socket | U3/U4 TMC · **U_PWR1+U_PWR2 MOSFET 1CH** · U_VIB SSR — cắm khi cần |
| Motor field | **J_MOT1 / J_MOT2** XH-4 cạnh dưới — không dùng giắc Mot trên StepStick |
| Sensor | **NPN only** — 24 V: J14/J15/IN2/IN3 · **5 V count: J_CNT5** |

### Bản đồ giắc IN/OUT (cạnh board)

**Cạnh trên (N) — W→E, một hàng, khe hàn ≥2.5 mm (KEY/DISP/USB ≥3 mm):**

| # | Ref | Loại | Hướng | Pinout ngắn |
|---|-----|------|-------|-------------|
| 1 | **J_P24N** | XH-2 | Aux out | +24V_SNS · GND |
| 2 | **J14** | XH-4 | IN đếm | +24V_SNS · GND · OUT (BUP) |
| 3 | **J15** | XH-3 | IN đếm | +24V_SNS · GND · OUT (fiber) |
| 4 | **J_IN2** | XH-3 | IN | +24V_SNS · GND · SIG (PLC start/jam) |
| 5 | **J_IN3** | XH-3 | IN | +24V_SNS · GND · SIG (stop / dự phòng) |
| 6 | **J_P5N** | XH-2 | Aux out | +5V · GND |
| 7 | **J_CNT5** | XH-3 | IN đếm | +5V · GND · OUT (IR) |
| 8 | **J_KEY** | 1×8 | IN | ROW0–3 · COL0–3 |
| 9 | **J_DISP** | XH-4 | OUT | CLK · DIO · +5V · GND (TM1637) |
| 10 | **J_USB** | Micro-B | I/O | Nạp / PC UART |

**Cạnh dưới (S) — W→E (mọi đế/giắc nối ngoài):**

| # | Ref | Loại | Hướng | Pinout ngắn |
|---|-----|------|-------|-------------|
| 1 | **J1** | Terminal 2P | IN nguồn | +24V_RAW · GND |
| 2 | **J_MOT1** | XH-4 | OUT | A2 · A1 · B1 · B2 |
| 3 | **U3** | Đế StepStick | Module TMC1 | STEP/DIR/EN · VM · pha |
| 4 | **J_MOT2** | XH-4 | OUT | A2 · A1 · B1 · B2 |
| 5 | **U4** | Đế StepStick | Module TMC2 | STEP/DIR/EN · VM · pha |
| 6 | **U_PWR1** | Đế 1×6 | Module MOSFET 1 | +24V · GND · 3V3 · PWM · EN · FAULT |
| 7 | **U_PWR2** | Đế 1×6 | Module MOSFET 2 | như trên |
| 8 | **U_VIB** | Đế 1×4 | Module SSR rung | +24V · GND · CTRL · FAULT |
| 9 | **J_P24S** | XH-2 | Aux out | +24V · GND |

**Trên board (không ra cạnh — không phải giắc field):** `F1` đế cầu chì · `SW_BOOT`/`SW_NRST` **cạnh J_USB** (phía trong) · linh kiện SMT.

> Kích thước vật lý dọc cạnh (ước): XH-2 ~4.5 mm · XH-3 ~7 mm · XH-4 ~9.5 mm · KEY 1×8 ~19 mm · USB ~7 mm · **TMC đế ~20 mm** · PowerMod 1×6 ~15 mm · Vib 1×4 ~9 mm. Hàng S cần board rộng (~130–160 mm).  
> **Linh kiện SMT** nằm lòng board, cách hàng giắc N/S ≥2.5 mm; **mọi courtyard cách nhau ≥2.5 mm** (không chạm / sát mép).

## A) SMT dán sẵn

| Ref | Value / package | SL |
|-----|-----------------|----|
| **U1** | **STM32G030C8T6** LQFP48 | 1 |
| U2 | MP1584EN SOT-23-8 | 1 |
| U5 | CH340C SOP-16 | 1 |
| U6 | AMS1117-3.3 SOT-223 | 1 |
| U44 / U45 / U46 / **U47** | PC817 SOP-4 (count24 / IN2 / IN3 / **count5V**) | 1 mỗi |
| PTC_MOT / PTC_MOT2 / PTC_SNS | 1812 1.1A / 1.1A / 0.2A | 1 mỗi |
| J_USB | USB Micro-B SMT | 1 |
| C_MCU / C_MCU2 | 100n / 1µ @+3V3 gần U1 | 1 mỗi |
| R_NRST / C_NRST | 10k / 100n | 1 mỗi |
| R_BOOT / R_SWDIO | 10k PD BOOT0 · 10k PU SWDIO | 1 mỗi |
| Rfb / Cbst / Cc + R/C bulk | như trước (24V/5V/3V3) | — |

## B) Hàn tay sau — **chỉ hàn khi cần**

PCB layout đủ mọi footprint. Mua/hàn theo SKU; ô trống = **DNP** (không hàn).

| Ref | Value | Hàn khi |
|-----|-------|---------|
| J1 | Terminal 2P 5.0 | **Luôn** (24V IN) |
| F1 | Đế 5×20 + ống **T2A** | **Luôn** |
| J_USB | (SMT sẵn) | — |
| SW_BOOT / SW_NRST | Tact 6×6 | **Luôn** (nạp USB) |
| **J_DISP** | `Disp_XH_04` | **Luôn** (TM1637) |
| J_KEY | 1×8 | Có keypad (thường cả 3 hạng) |
| U3 · **J_MOT1** | Đế StepStick + XH-4 | Có motor 1 (trung/đắt; rẻ nếu có đĩa) |
| U4 · **J_MOT2** | Đế StepStick + XH-4 | Có motor 2 (**đắt**) |
| **U_PWR1** | Đế 1×6 | Có van/out 1 |
| **U_PWR2** | Đế 1×6 | Có van/out 2 |
| **U_VIB** | Đế 1×4 | Có máng rung (**đắt**) |
| J14 | JST-XH 4P | Đếm BUP 24V (**trung**) |
| J15 | JST-XH 3P | Đếm fiber (**đắt**) |
| **J_CNT5** | JST-XH 3P | Đếm IR 5V (**rẻ**) |
| **J_IN2** / **J_IN3** | JST-XH 3P | Cảm biến phụ khi cần (`J_IN3` dự phòng) |
| **J_P24N** / **J_P5N** / **J_P24S** | JST-XH 2P | Aux nguồn khi wiring tách (optional) |

### Pinout aux power (XH-2)

| Giắc | Pin1 | Pin2 | Vị trí |
|------|------|------|--------|
| **J_P24N** | +24V_SNS | GND | Cạnh trên, trước cụm đếm 24 V |
| **J_P5N** | +5V | GND | Cạnh trên, trước J_CNT5 |
| **J_P24S** | +24V | GND | Cạnh dưới, cạnh U_PWR / motor |

> Dùng cấp LED phát / module ngoài khi tín hiệu đi giắc I/O riêng. `+24V_SNS` có PTC 0.2 A; `+24V` sau F1.

### Pinout J_DISP (XH-4) — module TM1637

| Pin | Net | Module (silk thường) |
|-----|-----|----------------------|
| 1 | `/TM_CLK` | CLK |
| 2 | `/TM_DIO` | DIO |
| 3 | `+5V` | VCC |
| 4 | `GND` | GND |

> Driver trên module — **không** hàn U7 SOP-20 trên board.

### Pinout J_CNT5 (1×3) — đếm 5 V

| Pin | Net | Ghi chú |
|-----|-----|---------|
| 1 | +5V | Cấp phát + thu IR |
| 2 | GND | |
| 3 | /OPTO_IN_5V | OUT cảm biến **NPN hoặc OC kéo GND** khi có viên |

> MCU đọc `/CNT5` (PD1) qua PC817. Không cắm chung lúc chạy với BUP 24 V trừ khi firmware chọn kênh. Module TTL active-high cần transistor OC ngoài.

### Pinout U_PWR1 / U_PWR2 (1×6) — mỗi kênh 1 module MOSFET

| Pin | Net U_PWR1 | Net U_PWR2 |
|-----|------------|------------|
| 1 | +24V | +24V |
| 2 | GND | GND |
| 3 | +3V3 | +3V3 |
| 4 | /PWM_OUT1 | /PWM_OUT2 |
| 5 | /PWR_EN1 | /PWR_EN2 |
| 6 | /PWR_FAULT (chung OD) | /PWR_FAULT |

> **1 output 24 V = 1 module cắm rời.** Tải nối trên module (không qua carrier). Logic 3.3 V.

### Pinout U_VIB (1×4)

| Pin | Net |
|-----|-----|
| 1 | +24V (SSR input supply) |
| 2 | GND |
| 3 | /VIB_CTRL |
| 4 | `/VIB_FAULT` |

> `SW_BOOT` / `SW_NRST`: tact 6×6 — **luôn hàn** (BOOT0 / reset).

## C) Field (ngoài board)

TMC2209 · NEMA17 · **module TM1637 4 số** (~13–20k) · keypad · BUP **hoặc** fiber · PSU LRS-*-24 — như trước.

## D) Ước giá (1 board mid, VND · 2026-09)

**Chính sách:** JLC/PCBA **chỉ SMT mục A**. **Đế cắm + giắc + nút (mục B) tự mua + hàn tay** — không gửi nhà máy dán.

Giả định: lot **5 tấm**, PCB **110×100** 2L HASL, ship amort, mua linh kiện VN/LCSC mid.

### 1) Nhà máy (PCBA SMT)

| Hạng mục | Low–High / tấm | Mid | Ghi chú |
|----------|----------------|-----|---------|
| **PCB trần** 2L 110×100 | 25–55k | **~35k** | >100×100 → mất promo $2/5; ~$15–25/5 + ship |
| **Linh kiện SMT (A)** | 75–110k | **~95k** | MCU 15–25 · buck/USB/CH340/opto/PTC/TVS/R/C (không U7) |
| **Phí dán SMT** | 70–140k | **~100k** | setup + place amort 5; ~50–70 điểm SMT |
| **Cộng PCBA (A)** | **≈180–300k** | **~235k** | board ra lò, **chưa** đế/giắc |

### 2) Hàn tay sau (mục B) — đế & giắc

| Nhóm | SL | Mid / tấm | Ghi chú |
|------|-----|-----------|---------|
| Đế StepStick U3/U4 | 2 | **20–30k** | 2× female 2.54 (16 chân/module) |
| Đế U_PWR1/2 1×6 | 2 | **6–12k** | |
| Đế U_VIB 1×4 | 1 | **2–4k** | |
| J1 terminal 2P + F1 đế 5×20 | 1+1 | **10–18k** | + ống T2A ~3–5k |
| J_MOT1/2 XH-4 | 2 | **10–16k** | |
| JST đếm/IN (J14/15/IN2/IN3) | 4 | **12–20k** | |
| J_KEY 1×8 + J_DISP XH-4 | 2 | **4–8k** | |

| SW_BOOT / SW_NRST | 2 | **2–4k** | |
| **Cộng hàn tay (B) đủ hết** | | **≈65–110k** | mid **~85k** — chỉ khi hàn **full**; SKU thực tế ít hơn (xem E3) |

### 3) Tổng 1 board (SMT A + hàn B)

| | Mid | Ghi chú |
|--|-----|---------|
| PCBA SMT (A) | **~235k** | luôn đủ |
| Hàn tay B **full** | **~85k** | mọi giắc |
| Hàn tay B **theo SKU** | **~40–110k** | rẻ/trung/đắt |
| **Board rẻ / trung / đắt** | **≈275 / 310 / 330k** | A + B thực tế |

### 4) Module cắm thêm (không tính vào board trần)

| Module | Mid / cái |
|--------|-----------|
| **TM1637 4 số** (qua **J_DISP**) | **13–20k** |
| TMC2209 StepStick | 80–150k (×1 hoặc ×2) |
| MOSFET module 1CH (U_PWR1/2) | 40–100k ×2 |
| SSR máng rung (U_VIB) | 30–80k |

PSU 24 V, NEMA, cảm biến, keypad = **field**, ngoài ước giá board.

---

## E) Ngoại vi + 3 hạng máy (VND · lot nhỏ VN · 2026-09)

**Cùng 1 PCB.** Cột **Đơn giá mid** = mua lẻ/Shopee–LCSC. Cột R/T/Đ = SL × tiền đưa vào SKU (0 = không mua).

### E1) Bảng đơn giá ngoại vi (đầy đủ)

| # | Ngoại vi | Giắc / đế | Đơn giá mid | Dải lẻ |
|---|----------|-----------|-------------|--------|
| 1 | **Board** SMT A + hàn B theo SKU | — | **275 / 310 / 330k** | rẻ / trung / đắt |
| 2 | **TMC2209** StepStick | U3 / U4 | **100k** | 80–150k |
| 3 | **NEMA17** 42 + dây pha | J_MOT1/2 | **110k** | 90–180k |
| 4 | **MOSFET module 1CH** 24V out | U_PWR1/2 | **60k** | 40–100k |
| 5 | **SSR / module máng rung AC** | U_VIB | **50k** | 30–80k |
| 6 | **TM1637** 4 số 0.36" | J_DISP | **15k** | 13–40k |
| 7 | **Keypad** membrane 4×4 | J_KEY | **20k** | 10–40k |
| 8 | **Cặp IR** thu–phát 5V (đếm rẻ) | J_CNT5 + J_P5N | **25k** | 15–40k |
| 9 | **BUP-U / U-slot** NPN 24V | J14 + J_P24N | **120k** | 80–200k |
| 10 | **Fiber** photo NPN 24V | J15 + J_P24N | **350k** | 250–550k |
| 11 | **Cảm biến IN** NPN 24V (jam/hopper/gate) | J_IN2 / J_IN3 | **40k**/cái | 25–80k |
| 12 | **PSU 24V** clone/LRS 50W | J1 | **150k** | 120–200k |
| 13 | **PSU 24V** LRS-75/100 | J1 | **230k** | 180–300k |
| 14 | **PSU 24V** LRS-150+ | J1 | **350k** | 280–450k |
| 15 | **Van / solenoid 24V** (tải MOSFET) | trên module PWR | **80k**/cái | 50–150k |
| 16 | **Cáp XH** + vỏ (MOT/DISP/SNS) | — | **25k**/máy | 15–40k |
| 17 | **Ống cầu chì T2A** dự phòng | F1 | **5k** | 3–8k |
| 18 | **USB Micro-B** cáp nạp | J_USB | **15k** | 10–25k |

> Aux `J_P24N`/`J_P5N`/`J_P24S` chỉ là giắc trên board — nguồn đi kèm cảm biến/tải, không tính module riêng.

### E2) Ba hạng — SL × tiền (mid)

| # | Hạng mục | **Rẻ** | **Trung** | **Đắt** |
|---|----------|--------|-----------|---------|
| 1 | Board A+B theo SKU | **275k** | **310k** | **330k** |
| 2 | TMC2209 | **0** | **1×100k** | **2×200k** |
| 3 | NEMA17 | **0** | **1×110k** | **2×220k** |
| 4 | MOSFET 1CH | **1×60k** (van/stop) | **2×120k** | **2×120k** |
| 5 | SSR rung | **0** | **0** | **1×50k** |
| 6 | TM1637 | 15k | 15k | 15k |
| 7 | Keypad | 15k | 20k | 30k |
| 8 | Đếm IR 5V | **25k** | 0 | 0 |
| 9 | Đếm BUP-U | 0 | **120k** | 0 |
| 10 | Đếm fiber | 0 | 0 | **350k** |
| 11 | IN2 + IN3 | **0** | **1×40k** (jam) | **2×80k** |
| 12–14 | PSU 24V | **150k** (50W) | **230k** (100W) | **350k** (150W) |
| 15 | Solenoid/van 24V | **1×80k** | **2×160k** | **2×160k** |
| 16 | Cáp XH bộ | 20k | 25k | 35k |
| 17 | Cầu chì dự phòng | 5k | 5k | 5k |
| 18 | Cáp USB | 15k | 15k | 15k |
| | **Cộng điện mid** | **≈680k** | **≈1.27tr** | **≈1.96tr** |
| | **Dải ước** | **0.50–0.90tr** | **1.0–1.7tr** | **1.6–2.7tr** |

### E3) Giắc **hàn theo hạng** (DNP phần còn lại)

| Ref | Rẻ | Trung | Đắt |
|-----|----|-------|-----|
| J1 · F1 · SW_* · J_DISP · J_KEY | hàn | hàn | hàn |
| J_CNT5 · (J_P5N optional) | **hàn** | DNP | DNP |
| J14 · (J_P24N optional) | DNP | **hàn** | DNP |
| J15 | DNP | DNP | **hàn** |
| J_IN2 | DNP | optional | **hàn** |
| J_IN3 | DNP | DNP / dự phòng | optional |
| U3 · J_MOT1 | DNP / optional đĩa | **hàn** | **hàn** |
| U4 · J_MOT2 | DNP | DNP | **hàn** |
| U_PWR1 | **hàn** | **hàn** | **hàn** |
| U_PWR2 | DNP | **hàn** | **hàn** |
| U_VIB | DNP | DNP | **hàn** |
| J_P24S | DNP | optional | optional |

**Hàn tay thực tế (ước):** rẻ **~40–55k** · trung **~70–90k** · đắt **~90–110k** (không phải đủ ~85–110k mọi SKU).

### E4) Ghi chú

- **Chưa gồm** khung, máng rung cơ, đĩa chia, tủ, DIN rail, nhãn — thường **+0.5–3tr** tùy cơ khí.  
- Lot board ≥50: SMT A **~180–250k** → mỗi hạng điện **−50–100k**.  
- Rẻ có thể thêm U3+J_MOT1+TMC+NEMA (+~210k) nếu cần đĩa quay.  
- Pad trống không hàn: phủ sơn / để vậy — không ảnh hưởng điện nếu firmware không dùng kênh đó.