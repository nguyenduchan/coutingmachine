# ESP32 Baseboard → STM32G030 carrier — BOM (2026-09-17)

SoT mua hàng / ước giá.  
**PCB SoT:** `python gen_compact_carrier.py` → board **150×100 mm** (`esp32_baseboard.kicad_pcb`) — giắc field chỉ N/S; W/E để gài DIN.  
**Pinmap:** `stm32_pinmap.py` · **Verify (fab):** `python verify_pre_fab.py`

> **CHƯA MUA gì.**  
> **MCU: STM32G030C8T6** (LQFP48).  
> **LCSC SMT:** `jlc_lcsc.csv` (`python verify_jlc_bom.py`). P9: `R_PD_*` 10k + `C_V3` 100n.  
> **Chưa upload JLC:** DRC còn net hở + U2 footprint SOT-23-8 vs MP1584EN SOIC-8-EP.  
> Nạp: **USB (CH340)** + nút **BOOT0 / NRST** — **không** giắc J_DBG (lot nhỏ).  
> **Layout DIN (bắt buộc):**  
> - **Cạnh dưới (S):** `J1` 24V → `J_MOT1`/`J_MOT2` (XH-4) + đế TMC/**U_PWR1+U_PWR2** — **không** kéo motor từ giắc sẵn trên module.  
> - **Cạnh trên (N):** cảm biến đếm → IN → keypad → TM1637 (gần MCU) · USB · debug.  
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
SNS: `+24V → PTC_SNS 0.1A (Bourns 60V) → R10 22Ω → +24V_SNS` → J14/J15/J_IN2/J_IN3  
Logic: `+24V → U2 → +5V ← D5(SMBJ5.0A) → U6 → +3V3 → U1`

**MCU / debug:**  
`U1 STM32G030C8T6` · `J_USB → U5 CH340C + Y1 12MHz` · USART1 **PA9/PA10**  
Nạp UART: giữ **BOOT0** (`PA14`/`SWCLK`) + `SW_BOOT` / `SW_NRST` · `R_BOOT` PD · `R_SWDIO` PU · **không J_DBG**

---

## GPIO (STM32 ports)

Pinmap rút ngắn dây theo cạnh LQFP (N=HMI, W=đếm/opto, S=TMC, E/SE=PWR/VIB/UART). Chi tiết: `stm32_pinmap.py`.

| Chức năng | Pin |
|-----------|-----|
| TMC1 STEP / DIR / EN (U3) | PA4 / PA5 / PA6 |
| TMC2 STEP / DIR / EN (U4) | PA7 / PB0 / PB1 |
| Count opto `/BUP` | PA0 |
| **Count 5V `/CNT5`** | **PA3** |
| Input2 `/IN2` · Input3 `/IN3` | PA1 · PA2 |
| **U_PWR1 / U_PWR2** PWM / EN / FAULT | PB10+PB12 · PB11+PB13 · PB14 shared |
| **U_VIB** CTRL / FAULT | PB15 / PA8 |
| TM1637 CLK / DIO (**J_DISP** → module) | PA15 / PD0 |
| Keypad ROW0–3 | PB9 / PB8 / PB7 / PB6 |
| Keypad COL0–3 | PB5 / PB4 / PB3 / PD3 |
| USART1 TX / RX (CH340) | PA9 / PA10 |
| SWDIO / SWCLK(BOOT0) | PA13 / PA14 (USB-UART boot; no SWO) |

---

## Board

| | |
|--|--|
| Kích thước | **150×100 mm** (auto-grow nếu giắc N/S khe &lt;5 mm; tối đa 300 mm) |
| Generator | `gen_compact_carrier.py` (placement + nets, **no copper**) |
| MCU | **STM32G030C8T6** LQFP48 SMT |
| Hàn tay sau | **Chỉ hàn giắc/đế khi SKU cần** (pad đủ trên PCB). Luôn: J1, F1, J_USB, SW_*, J_DISP; tùy hạng: MOT/TMC/PWR/VIB/SNS/KEY/IN |
| Module socket | U3/U4 TMC · **U_PWR1+U_PWR2 MOSFET 1CH** · U_VIB SSR — cắm khi cần |
| Motor field | **J_MOT1 / J_MOT2** XH-4 cạnh dưới — không dùng giắc Mot trên StepStick |
| Sensor | **NPN only** — 24 V: J14/J15/IN2/IN3 · **5 V count: J_CNT5** |

### Bản đồ giắc IN/OUT (cạnh board)

**Cạnh trên (N) — W→E, một hàng, khe giữa giắc ≥5 mm (cắm 2 phích không chạm):**

| # | Ref | Loại | Hướng | Pinout ngắn |
|---|-----|------|-------|-------------|
| 1 | **J14** | XH-4 | IN đếm | +24V_SNS · GND · OUT · CTRL→+V (BUP Light ON) |
| 2 | **J15** | XH-3 | IN đếm | +24V_SNS · GND · OUT (fiber) |
| 3 | **J_IN2** | XH-3 | IN | +24V_SNS · GND · SIG (PLC start/jam) |
| 4 | **J_IN3** | XH-3 | IN | +24V_SNS · GND · SIG (stop / dự phòng) |
| 5 | **J_CNT5** | XH-3 | IN đếm | +5V · GND · OUT (IR) |
| 6 | **J_KEY** | 1×8 | IN | ROW0–3 · COL0–3 |
| 7 | **J_DISP** | XH-4 | OUT | CLK · DIO · +5V · GND (TM1637) |
| 8 | **J_USB** | Micro-B | I/O | Nạp / PC UART |

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
> **Linh kiện SMT** nằm lòng board, cách hàng giắc N/S ≥2.5 mm; SMT courtyard ≥2.5 mm. **Giắc N/S cách nhau ≥5 mm** để hai phích cắm không chạm.

## A) SMT dán sẵn (kho JLCPCB)

Map LCSC: `jlc_lcsc.csv` — **chỉ hãng kho LCSC** (ST/MPS/WCH/Omron/Molex/Littelfuse/Bourns/Rubycon/Panasonic/Samsung/Yageo/Sunlord/Lite-On/LGE). Tụ hóa nhôm 105°C.

| Ref | Mã JLC | Hãng / MPN | Ghi chú 3 năm |
|-----|--------|------------|----------------|
| U1 | C529329 | ST STM32G030C8T6 | Industrial −40…85°C |
| U2 | C15051 | **MPS MP1584EN-LF-Z SOIC-8-EP** | Giữ MPS 1.5 MHz. Clone rẻ 100–220 kHz không dùng. PCB **SOT-23-8** |
| U5 | C84681 | WCH CH340C | Listing rẻ hơn C7464026 |
| U6 | C6186 | AMS AMS1117-3.3 | Basic, hãng AMS (Mỹ) |
| U44–U47 | C114603 | Lite-On LTV-817S-TA1-D | Thay PC817 no-name |
| Y1 | C9002 | YXC 12 MHz 3225 −40…85 | Basic; aging ~3 ppm/năm |
| J_USB | C132560 | Molex 473460001 | Micro-B SMT 5+2 vỏ |
| SW_BOOT/NRST | C271750 | Omron B3FS-1000P | Chính hãng Omron 6×6 (rẻ hơn Panasonic) |
| L1 | C87982 | Sunlord SWPA6040S100MT | 10 µH 2.45 A 6×6 |
| D1 | C315992 | Littelfuse SMBJ26A | 26 V / 42.1 V / 600 W SMB |
| D5 | C83333 | Littelfuse SMBJ5.0A | 5 V / 9.2 V / 600 W SMB |
| D3/D4 | C2903855 | LGE SS54 SMA | ON/Vishay SS54 là SMC |
| PTC_MOT/MOT2 | C142747 | Littelfuse 1812L110/33MR | **33 V** 1.1 A |
| PTC_SNS | C12430 | Bourns MF-MSMF010-2 | **60 V** 0.1 A (BOM 0.2 A) |
| C3/C10/C20B/C21 | C88734 | Rubycon 47 µ/50 V 6.3 | Nhôm JP 105°C 2000 h |
| C5 | C110164 | Rubycon 100 µ/16 V 6.3 | |
| C20 | C178595 | Panasonic 220 µ/50 V Ø8 | 5000 h@105°C |
| 100 n 0805 | C1711 | Samsung X7R 50 V | |
| C_MCU2 1 µ | C28323 | Samsung X7R 50 V | |
| Cbst 10 n | C1710 | Samsung X7R 50 V Basic | |
| Cc 3n3 | C107149 | YAGEO X7R 50 V 0805 | Murata C0G đắt hơn |
| C_XI/XO 22 p | C1804 | Samsung C0G 50 V Basic | |
| 10 k / 4k7 / 1 k / 2k2 | C17414 / C17673 / C17513 / C17520 | UNI-ROYAL 0805 1% Basic | gồm `R_PD_*` P4.5 |
| C_V3 | C1711 | Samsung 100 n X7R | CH340 V3, không đấu AMS1117 |
| Rfb1 52k3 | C17740 | UNI-ROYAL 0805 1% | Chia 5 V với Rfb2 |
| R10 22 R | C17958 | UNI-ROYAL 1206 1% 250 mW | |

Giắc/đế THT (J1, F1 5×20, XH, header TMC…) = DNP — không có trong file LCSC SMT.

## B) Hàn tay sau — **chỉ hàn khi cần**

PCB layout đủ mọi footprint. Mua/hàn theo SKU; ô trống = **DNP** (không hàn).

| Ref | Value | Hàn khi |
|-----|-------|---------|
| J1 | Terminal 2P 5.0 | **Luôn** (24V IN) |
| F1 | Đế 5×20 + ống **T2A** | **Luôn** |
| J_USB | (SMT sẵn) | — |
| SW_BOOT / SW_NRST | (SMT Omron sẵn) | — |
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
| **J_P24S** | JST-XH 2P | Aux +24V cạnh motor/PWR (optional) |

### Pinout aux power (XH-2)

| Giắc | Pin1 | Pin2 | Vị trí |
|------|------|------|--------|
| **J_P24S** | +24V | GND | Cạnh dưới, cạnh U_PWR / motor |

> Đã bỏ `J_P24N` / `J_P5N` — cảm biến lấy nguồn trên giắc tín hiệu (J14/J15/J_CNT5/J_DISP).

### Pinout J14 (XH-4) — Autonics BUP-30S NPN

| Pin | Net | Màu cáp | Autonics |
|-----|-----|---------|----------|
| 1 | `+24V_SNS` | Brown | +V |
| 2 | `GND` | Blue | 0 V |
| 3 | `/OPTO_IN_BUP` | Black | OUT (NPN OC) |
| 4 | `+24V_SNS` | White | CTRL → +V = **Light ON** (mặc định) |

> Dark ON: cắt pin 4 trên phích / nối White→Blue (GND) ở cáp — không đổi PCB.
> Cáp XH: 1=Brn · 2=Blu · 3=Blk · 4=Wht.

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

## D) Giá linh kiện trên 1 board (kho JLCPCB · 2026-09-17)

**Chỉ linh kiện** — chưa PCB, chưa phí dán, chưa ship, chưa VAT. FX **26.000 VND/USD**.  
Nguồn: API JLCPCB 17/09/2026. Chỉ linh kiện **chính hãng kho LCSC** (không Shou Han / Honor / Brightking / MDD TVS).

### 1) SMT mục A — mỗi board

| Lô đặt | USD | VND | Ghi chú giá bậc |
|--------|-----|-----|-----------------|
| 1 | **~9.1** | **~237k** | Chính hãng; Omron/Rubycon giữ giá giữa |
| 5 | **~8.9** | **~231k** | |
| 10 | **~8.3** | **~216k** | |
| 100 | **~7.0** | **~182k** | |

So với no-name: USB Molex, TVS/PTC Littelfuse, C20 Panasonic. Giữ Omron + Rubycon (vẫn chính hãng, rẻ hơn Panasonic nút/tụ 47 µ). U2 vẫn MPS 1.5 MHz.

### 2) THT mục B — full giắc/đế (mua kho JLC, hàn tay)

Ước **~$1.48 / ~38k**: J1 C8465 $0.13 · XH 2/3/4P LAILAN · header cái BOOMELE 2×8 / 1×6 / 1×4 · J_KEY 1×8 · đế+ống F1 5×20 (~$0.33, không khớp mã chính xác). Generic, không phải JST/Molex. Mua lẻ VN vẫn **~65–110k** (mid **~85k**).

### 3) Tổng linh kiện 1 board (A SMT + B THT full)

| Lô | SMT A | THT B (lẻ JLC) | **Cộng** |
|----|-------|----------------|----------|
| 1 | 237k | 38k | **~275k** |
| 5 | 231k | 38k | **~269k** |
| 10 | 216k | 38k | **~254k** |
| 100 | 182k | ~35k | **~217k** |

Chưa gồm module TMC / MOSFET / SSR / TM1637 / cảm biến / PSU.

Chi tiết dòng: `out/jlc_part_cost.json`.

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
| 1 | **Board** linh kiện A SMT + B THT full | — | **~275k** | lot 1; SMT ~237k + THT ~38k (chưa PCB/dán) |
| 2 | **TMC2209** StepStick | U3 / U4 | **100k** | 80–150k |
| 3 | **NEMA17** 42 + dây pha | J_MOT1/2 | **110k** | 90–180k |
| 4 | **MOSFET module 1CH** 24V out | U_PWR1/2 | **60k** | 40–100k |
| 5 | **SSR / module máng rung AC** | U_VIB | **50k** | 30–80k |
| 6 | **TM1637** 4 số 0.36" | J_DISP | **15k** | 13–40k |
| 7 | **Keypad** membrane 4×4 | J_KEY | **20k** | 10–40k |
| 8 | **Cặp IR** thu–phát 5V (đếm rẻ) | J_CNT5 | **25k** | 15–40k |
| 9 | **BUP-U / U-slot** NPN 24V | J14 | **120k** | 80–200k |
| 10 | **Fiber** photo NPN 24V | J15 | **350k** | 250–550k |
| 11 | **Cảm biến IN** NPN 24V (jam/hopper/gate) | J_IN2 / J_IN3 | **40k**/cái | 25–80k |
| 12 | **PSU 24V** clone/LRS 50W | J1 | **150k** | 120–200k |
| 13 | **PSU 24V** LRS-75/100 | J1 | **230k** | 180–300k |
| 14 | **PSU 24V** LRS-150+ | J1 | **350k** | 280–450k |
| 15 | **Van / solenoid 24V** (tải MOSFET) | trên module PWR | **80k**/cái | 50–150k |
| 16 | **Cáp XH** + vỏ (MOT/DISP/SNS) | — | **25k**/máy | 15–40k |
| 17 | **Ống cầu chì T2A** dự phòng | F1 | **5k** | 3–8k |
| 18 | **USB Micro-B** cáp nạp | J_USB | **15k** | 10–25k |

> Aux `J_P24S` chỉ là giắc trên board — nguồn đi kèm cảm biến/tải trên giắc tín hiệu, không tính module riêng.

### E2) Ba hạng — SL × tiền (mid)

| # | Hạng mục | **Rẻ** | **Trung** | **Đắt** |
|---|----------|--------|-----------|---------|
| 1 | Board linh kiện A+B | **~275k** | **~269k** | **~275k** |
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
| | **Cộng điện mid** | **≈740k** | **≈1.33tr** | **≈1.97tr** |
| | **Dải ước** | **0.50–0.90tr** | **1.0–1.7tr** | **1.6–2.7tr** |

### E3) Giắc **hàn theo hạng** (DNP phần còn lại)

| Ref | Rẻ | Trung | Đắt |
|-----|----|-------|-----|
| J1 · F1 · SW_* · J_DISP · J_KEY | hàn | hàn | hàn |
| J_CNT5 | **hàn** | DNP | DNP |
| J14 | DNP | **hàn** | DNP |
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
- Lot board ≥50: SMT A **~228k** linh kiện (lô 100) + PCB/dán riêng → mỗi hạng điện **không** còn ~95k SMT.  
- Rẻ có thể thêm U3+J_MOT1+TMC+NEMA (+~210k) nếu cần đĩa quay.  
- Pad trống không hàn: phủ sơn / để vậy — không ảnh hưởng điện nếu firmware không dùng kênh đó.