# ESP32 / STM32 Baseboard — yêu cầu bắt buộc trước khi đặt PCB

**Board sản xuất hiện tại (2026-09-17):** carrier **180 × 120 mm**, gốc KiCad
(50, 50), **4 lớp 1 oz**, dày 1,6 mm, HASL/ENIG. Mục tiêu: **tiệm cận tiêu chuẩn
công nghiệp** (IPC-2221 tiết diện, khe cách rộng hơn min xưởng, EMI stack chuẩn),
không phải prototype “sát sàn JLCPCB”.

**Stack EMI (bắt buộc):**

| Lớp | Vai trò |
|-----|---------|
| **F.Cu** | Tín hiệu + pad SMT/THT. Chỉ **fan-out ngắn** (pad → via). Không bus dài dưới module. |
| **In1.Cu** | **Mặt phẳng GND đặc** — đường về cho mọi tín hiệu / motor |
| **In2.Cu** | Tách nguồn: **+24V** nam; **+5V** tây-bắc; **+3V3** đông-bắc (khe ≥0,6 mm) |
| **B.Cu** | Tín hiệu / bus dài (ưu tiên A0) |

Khung lịch sử 190 × 100 mm 2 lớp (`gen_power_carrier.py`) **không** còn là nguồn
layout. **Không** chạy `gen_compact_carrier.py` / `route_4layer.py` SMT-swap —
chúng xoá track, silk và đế F1 5×20.

> Modules / courtyard **≥ 5 mm** từ Edge.Cuts (E11.10). **Dây và via ≥ 2 mm** mép
> (A12 — chặt hơn courtyard). Cụm khác MCU **≥ 10 mm** tới Eco MCU (E11.12).
> Cụm cùng mặt cách nhau **≥ 8 mm** (E11.2). Mounting M3 inset 3.5 mm góc.
> **Mặt trước (F.Cu) = lắp module + giắc.** **Đi dây ưu tiên B.Cu** + return In1.
>
> Board này **thiết kế như card I/O PLC** (tủ DIN, field 24 V, cách ly IN, DO công suất
> riêng) — mục **P** bắt buộc ngang A0–A13. Không layout như Arduino “cắm hết giữa board”.

**BOM chốt (MODULES.md):** U1 DevKitC N16R8 · U2 MP1584 · U3 TMC2209 ·
**U10 74HC595-24IO module** (Shopee, phải ESP32) · **U5–U7 ULN2003** ·
**M1** (D3+F1+D1 @ J30) · **M2** (PC817×4 @ J31A/B) ·
TFT+touch · J18 ENC · U5–U7 ULN module (28BYJ trên JST) · J8/J10/J12 HOME NC@12V · R2/R3/R4 boot.
**(Không J2 / J19–J22 field / U11 DIP)** — Mot trên U3; spare IO7/8/14/15.

**Chạy cổng tự động (bắt buộc):**

```powershell
cd pcb\esp32_baseboard
./loop_check.sh
python verify_all.py
python verify_modules.py
```

### Hai bộ định tuyến

| | `maze_router.py` (tự viết) | **FreeRouting 2.2.4+** (`route_freerouting.py`) |
|---|---|---|
| Thuật toán | Lee/A* lưới 0,55 mm + MST + rip-up | Push-and-shove trên hình học thật, đọc luật DSN |
| Vai trò | Vá net còn hở sau SES | **Đường chính** (PCB_REVIEW A2) |
| Ghi chú | Tôn trọng keepout hàng chân, via–pad 1 mm, mép 2 mm | Cần **JRE 25** + jar ≥2.2 (2.1 bỏ `-mp` headless, không ghi `.ses`) |

**FreeRouting là đường chính.** Maze chỉ `repair_open_pcb` — **không** `maze_full` sau khi đã có SES (sẽ strip toàn bộ đồng FR).

```sh
./loop_check.sh     # sinh → schematic → định tuyến → đồng bộ lib → DRC
python verify_all.py   # phán quyết duy nhất cho toàn bộ PCB_REVIEW
```

Chỉ **đi dây** (FreeRouting 2.2.4 + maze leftover) khi schematic khớp PCB.
**Không** `gen_power_carrier.py` / `gen_compact_carrier.py` trên board đang live.
Chỉ **đặt PCB** khi `verify_fab.py` G1–G7 PASS, A5–A13 PASS, **và** mục Manual đã tick.

---

## A. Chính sách routing (bắt buộc)

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| **A0** | **Đi dây ưu tiên B.Cu (mặt sau).** F.Cu dành cho **module + giắc** (mọi footprint TOP). Trên F.Cu chỉ cho phép **fan-out ngắn** từ pad THT tới via đổi lớp — **không** chạy bus / đường dài dưới cụm module. Bus tín hiệu & nguồn dài nằm trên **B.Cu** | mắt + độ dài track F vs B; FreeRouting prefer B |
| A1 | **Ưu tiên đổi lớp tại pad THT**; chỉ thêm via khi hết đường cùng mặt (sau A0: thoát pad → via → B.Cu) | `verify_pcb.py` / DRC |
| A2 | Maze autoroute F.Cu + B.Cu (dự phòng); FreeRouting = chính — **cấu hình ưu tiên lớp B** | `route_freerouting.py` |
| A3 | Bus phục vụ B.Cu sau maze — mỗi net tín hiệu một kênh riêng | Silk B.SilkS |
| A4 | Mọi net có ≥2 pad phải **một đảo đồng** | `_check_net_copper.py` → OPEN = 0 |
| A5 | **Tín hiệu cùng mặt không cắt nhau** — áp dụng **carrier + M1/M2** | `_check_signal_routing.py` / `verify_modules.py` → crossings = 0 |
| A6 | **Không chồng colinear** cùng mặt giữa 2 net tín hiệu — **carrier + M1/M2** | `_check_signal_routing.py` / `verify_modules.py` → colinear = 0 |
| A7 | **Không xuyên / quá sát lỗ** — ≥ drill/2 + **0,25 mm** + nửa bề rộng + **0,2 mm** tới pad THT/NPTH/via khác net (sàn DRC). **Router đi rộng hơn:** DSN `A7_CLEARANCE_UM=500` (0,50 mm đồng–đồng) | `_check_signal_routing.py` → hole hits = 0 |
| **A8** | Chỉ **via xuyên** F↔B (4 lớp: padstack `Via[0-3]_800:400_um`). **Cấm** blind / buried / microvia / **via-in-pad**. Một cỡ: **khoan 0,4 / pad 0,8** | DRC `annular_width`; mắt Gerber |
| A9 | **`clean_stubs.py` sau mỗi merge SES.** Specctra để lại đoạn trùng | `drc_report.txt` → `track_dangling` = 0 |
| **A10** | **EMI 4 lớp:** In1 = GND đặc; In2 tách +24V/+5V/+3V3; F/B không pour nguồn. Bulk C sát tải; MotA/B vòng nhỏ; field qua opto. Mục **R** | mắt + Manual |
| **A11** | **Via không trùng chân linh kiện**; **đồng via cách đồng pad ≥ 1,00 mm** (mọi pad SMT/THT có net; trừ lỗ mount H*) | `kicad_dru` + `python enforce_via_edge.py --check` |
| **A12** | **Track và via cách Edge.Cuts ≥ 2,00 mm** (không dùng sàn xưởng 0,3 mm) | DRC `edge_clearance` 2 mm + `enforce_via_edge.py --check` |
| **A13** | **Cấm đi xuyên hàng chân đế cắm** (TMC, XH, keypad, socket nguồn/rung). Không luồn khe 2,54 mm giữa hai cọc | `_check_signal_routing.py` A7 + `pin_row_keepout.py` |

### A8 chi tiết — via cho nhiều loại máy / xưởng

Mục tiêu: **cùng Gerber chạy được** trên dây chuyền cơ khí phổ thông (JLCPCB, PCBWay,
xưởng VN 2 lớp) **không** cần quy trình laser, HDI, hay filled via.

| Quy tắc | Lý do |
|---------|--------|
| Chỉ **through-via** (4 lớp: F↔In1↔In2↔B, một mũi khoan) | Blind/buried / HDI không dùng |
| **Drill 0,4 / pad 0,8** cố định | Mũi Ø0,4 phổ biến; vành 0,2 mm chịu lệch đăng ký |
| **Không via-in-pad** (filled via đắt — không dùng) | Thiếc hút vào lỗ, tombstone, hở hàn |
| **Đồng via cách đồng pad ≥ 1,00 mm (A11)** | Lệch khoan, hút thiếc, không chồng chân LQFP/XH |
| **Không microvia / laser** | Ngoài tầm fab class này |
| Ưu tiên **đổi lớp tại pad THT** (A1); via chỉ khi buộc phải | Ít lỗ = dễ khoan |

Min xưởng 0,3/0,6 **không dùng**. Board cố ý lớn hơn min.

### R. Khuyến nghị đi dây — tiêu chuẩn công nghiệp (bắt buộc)

Không thiết kế “sát min JLCPCB”. Các số dưới đây là **sàn thiết kế**; min xưởng
0,127 / 0,30 mm chỉ để biết Gerber vẫn chế được.

| Chủ đề | Làm | Không làm |
|--------|-----|-----------|
| **Khe cách** | Router ≥ **0,50 mm** đồng–đồng (`FR_CLEAR_UM=500`); DRC fab ≥ 0,20 mm | Đặt dây sát pad “vì DRC xanh” |
| **Mép board** | Track/via **≥ 2 mm** Edge.Cuts (A12). Plane In1/In2 inset **2 mm** | Copper ra sát V-cut / khe kẹp 0,3 mm |
| **Via** | 0,8/0,4 through; **≥ 1 mm** tới mọi pad (A11); SMT fan-out rồi mới via | Via-in-pad, via dưới chân LQFP/XH |
| **Hàng chân đế** | Đi **vòng** hàng 2,54 mm; keepout khe giữa cọc (`pin_row_keepout.py`, A13) | Luồn tín hiệu giữa hai pin socket / TMC |
| **Lớp** | Pad SMT → stub F ngắn → via → **B.Cu** (A0). Return **In1 GND** ngay dưới | Bus dài F dưới module; cắt plane GND dưới USB/STEP |
| **Nguồn** | +24V / motor trên In2 nam + track Power 0,50–1,00 mm (IPC-2221 ΔT 10 °C) | Default 0,25 mm cho Mot* / +24V |
| **Motor / chopper** | Cặp MotA/B sát nhau; C bulk ≤10 mm VM; GND In1 không khe dưới TMC | Vòng lớn F quanh U3/U4 |
| **USB D±** | Cặp sát, cùng lớp; via đối xứng nếu đổi lớp; ngắn tới jack | Tách D+/D−, via lệch |
| **Góc** | Ortho hoặc 45° | Góc nhọn <45°, neckdown dưới 0,20 mm |
| **Tụ** | 100 nF HF sát chân nguồn IC; bulk sát tải | Tụ “cùng net” nhưng 30 mm xa pad |
| **Silk** | Mọi footprint có **Reference** nhìn thấy; giắc ghi mục đích (MOTOR 1, 24V IN, …) | Ẩn ref; Value chồng pad |
| **F1** | Đế **5×20** rút ống | Đổi SMT 2410 khi chưa được hỏi |
| **Tắc dây** | Nới placement / board (E11.3) | Hạ 1 mm / 2 mm hoặc luồn hàng chân |

**Thứ tự khi xung đột:** an toàn khe cách (A11–A13) → EMI stack (A10) → đủ net.
Thiếu net thì **mở kênh / nới cụm**, không hạ clearance.

**Cổng sau mỗi lần đi dây:**

```powershell
python _check_signal_routing.py          # A5 A6 A7
python enforce_via_edge.py --check       # A11 A12
python verify_fab.py                     # schematic parity + DRC
```

**Pipeline đi dây:** FreeRouting 2.2.4 + JRE 25 (`route_freerouting.py`) →
`maze_router.repair_open_pcb` (vá leftover) → `enforce_via_edge.py` → fill zone
(`SKIP_FANOUT=1`). **Cấm** `maze_full` sau SES; **cấm** copy `routed.kicad_pcb`
stale nếu chưa có `.ses`.

### A10. ⚠️ Dấu của phép xoay pad — 3 cổng cùng nói dối một lúc

**Lỗi đã xảy ra thật, và KiCad DRC thì luôn đúng nên không ai nghi các cổng.**

Toạ độ pad trong footprint là toạ độ **local**; ra board phải xoay theo góc đặt.
KiCad xoay **ngược chiều kim đồng hồ trên màn hình**, mà **y tăng xuống dưới**, nên
công thức đúng là:

```python
px = fx + lx*cos(th) + ly*sin(th)
py = fy - lx*sin(th) + ly*cos(th)      # dấu sin ngược với dạng sách giáo khoa
```

Dạng "sách giáo khoa" (`lx*cos - ly*sin`, `lx*sin + ly*cos`) **trùng đáp số ở 0° và
180°**, chỉ sai ở **90° / 270°** — và sai đúng bằng phép lật 180°. Trên board này chỉ
có **J1 (90°)** và **U3 (270°)**, nên lỗi nằm im cho tới khi chúng có dây:

| Nơi dùng sai | Hậu quả |
|---|---|
| `clean_stubs.py` | Không thấy pad của U3/J1 → xoá **cả chuỗi** track chạm chúng như "dangling": `DIR` mất sạch, `+12V_RAW` đứt trước khi tới J1, `STEP` chỉ còn đoạn ở U1 |
| `maze_router._rot_xy` (→ `_check_net_copper.py`) | A4 báo 7 net hở trong khi KiCad báo 0 unconnected |
| `_check_signal_routing.py` | A5–A7 chấm trên vị trí lỗ **sai** của U3/J1 → PASS vô nghĩa |

→ **Không tự tính lại vị trí pad ở mỗi script.** Nếu buộc phải tính, so lại với toạ độ
KiCad in ra trong `drc_report.txt` (`@(x mm, y mm): PTH pad N of U3`) — đó là trọng tài.
→ Triệu chứng "FreeRouting bỏ hàng net của footprint xoay 90°" **là chẩn đoán sai** của
chính lỗi này: file `.ses` vẫn có đủ dây cho `DIR`/`+12V_RAW`, `clean_stubs` mới là nơi
chúng biến mất. FreeRouting đi dây footprint xoay 1/4 vòng bình thường.

**Net nguồn**: `GND`, `+5V`, `+3V3`, `+12V`, `+12V_RAW`, `+12V_SNS`, `BLW_RET`. (A5/A6 nay áp cho **mọi** net — miễn trừ nguồn từng che giấu 25 short nguồn-với-nguồn thật.)

**Net tín hiệu**: mọi net còn lại (GPIO, shift, BYJ pha, TFT, opto IN/OUT, …).

---

## B. ESP32-S3 DevKitC-1 (bắt buộc)

| # | Yêu cầu | Script |
|---|---------|--------|
| B1 | GPIO chức năng khớp `s3_pinmap.py` (opto×4 + BYJ×12 + TMC + TFT LCD + buzzer + blower) | `verify_esp32_nets.py` |
| B2 | **Không** dùng IO35 / IO36 / IO37 (octal PSRAM N16R8) | `verify_esp32_nets.py` |
| B3 | IO0, IO19, IO20, TX0, RX0, RST **không** route | `verify_esp32_nets.py` |
| B4 | `OPTO_OUT1..8` trên U1 (IO1/2/4/5/7/8/14/15); IO9 = `BUZZER`; IO6 = `T_IRQ` | `verify_esp32_nets.py` |
| B5 | R2 PU `EN_TMC`; R3 PD `BLOWER`; D2 freewheel bom (**không** R4/`OE_595`) | `verify_connectivity.py` §E/F |

---

## C. Module ↔ jack (bắt buộc)

| # | Khối | Kiểm |
|---|------|------|
| C1 | U3 TMC2209 Mot pins (NEMA17 trên module) ↔ IO16/17/18; **không J2** | `verify_connectivity.py` §B |
| C2 | **M2** (J31A 1×6 IN + J31B 1×5 OUT) PC817 ×4 ↔ J8/J10/J12 HOME + J14 BUP; LED 2k2 / PU 10k; **`+12V_SNS`** | §C |
| C3 | **U10 595-24IO** (J24/J25) → `SR_Q0–11` → **U5–U7 ULN module**; VCC=+12V; **28BYJ trên JST module** (không J5–J7) | §D |
| C4 | **TFT MSP3520 — hai giắc liền nhau, đúng thứ tự module** (xem E11.5): **J17 1×9 LCD** + **J23 1×5 touch**; J17.9 SDO **NC**; touch/BL GPIO | `verify_connectivity.py` §E |
| C5 | J18 EC11 ENC_A/B → IO38 / IO41; TFT_BL = IO45 PWM | §E |
| C6 | J15 buzzer IO9; J16 blower IO3 + **+12V** (không U8) | §E |
| C7 | J1 → **J30/M1** (D3+F1+D1) → +12V; **U2** MP1584 5V; R10 SNS | §F |
| C8 | **Không giắc trùng chức năng.** J2 xoá (Mot trên TMC); J4 đã xoá (trùng OPTO_IN) | `verify_connectivity.py` |
| C9 | **Đúng một** cặp vít nguồn 12V (J1) gần cạnh trái. **Hàng cọc song song cạnh gần nhất** (trái → rot **90°**, pad dọc theo cạnh) | mắt + `_check_rot.py` |
| C10 | **Xoay linh kiện khi dây chéo** (`ROT_TMC=270`, `ROT_ENC=180`, `ROT_DIP/BYJ=180`). Còn lại mặc định 0°. Silk nhãn theo rot footprint | mắt + `_check_rot.py` |
| C11 | **Mọi footprint trên TOP (F.Cu)** — mặt trước = module + giắc. **Đi dây ưu tiên B.Cu** (A0); F.Cu chỉ fan-out ngắn tới via | mắt + A0 |

---

## D. Điện & an toàn (bắt buộc)

| # | Yêu cầu |
|---|---------|
| D1 | +12V_RAW có **M1**: D3 Schottky + F1 PTC + D1 TVS (cắm J30) |
| D2 | Star sense: R10/C10/C11 + `+12V_SNS` tới limit/BUP |
| D3 | **Một** buck 5V (U2) cho logic; bơm **12V** từ rail `+12V` qua J16 |
| D4 | ULN2003 COM = +12V; TMC VM=12V / VIO=3V3 |
| D5 | Không net tín hiệu chạm net nguồn trên pad U1 |
| D6 | `/OE` 595 (OE_595) có R4 10k pull-up → +3V3; IO13 điều khiển |
| D7 | **Kiến trúc PLC (mục P):** field 24 V ≠ logic 5 V/3V3; IN qua opto; DO không ra thẳng GPIO; giắc field chỉ N/S |

---

## P. Thiết kế mạch in kiểu PLC (bắt buộc)

Carrier **không** phải board hobby. Coi nó như **một rack I/O PLC nhỏ**: vào nguồn có
bảo vệ, IN field có cách ly/hạ áp, DO công suất trên module, CPU nằm đảo sạch, cáp
field ra **cạnh tủ** — đúng thói quen tủ Siemens/Omron/Mitsubishi, không đúng shield
Arduino.

**So ánh xạ (để đọc schematic / silk cho đúng):**

| Slot PLC | Trên board này | Không làm |
|----------|----------------|-----------|
| **L+ / M** (24 V / 0 V) | `J1` → D3+F1+D1 → `+24V` / GND (In1) | Cấp MCU trực tiếp từ field |
| **CPU** | U1 (STM32 / DevKit) đảo **đông-bắc 3V3**, USB/HMI cạnh trên | Đặt MCU kề J1 / TMC |
| **DI 24 V** | J14/J15/J_IN2/J_IN3 → PC817 → GPIO; **NPN only** | PNP; 24 V vào chân MCU |
| **DI 5 V** | `J_CNT5` riêng (+5V·GND·OUT) | Chung giắc với IN 24 V |
| **DO 24 V** | `U_PWR1/2` MOSFET, `U_VIB` SSR — PWM/EN/FAULT | GPIO sink 24 V |
| **Motion** | TMC + `J_MOT*` cạnh **nam**; 28BYJ trên module ULN | Kéo motor từ header sẵn trên StepStick |
| **Cách ly** | **Đai opto giữa** field nam và MCU bắc | Track 24 V chạy dưới LQFP / USB |
| **Gài tủ** | **Trái/phải trống** (DIN). Giắc field **chỉ N/S** | Giắc 24 V cạnh DIN |

**GND chung một PSU** — PC817 **không** phải isolation galvanic (không hai nguồn
tách). Vai trò: hạ 24 V→3V3, chặn xung field, tách **kênh đồng**. Muốn isolation thật
thì PSU field riêng + GND tách — **chưa** là phạm vi board này.

### P1. Phân vùng (trước khi đi một sợi dây)

Thứ tự đặt linh kiện = thứ tự kỹ sư PLC bố trí card:

1. **Cạnh nam (S) — power + actuator:** `J1` 24 V IN (rot 90°, cọc ∥ mép) → bảo vệ
   D3/F1/D1 → buck U2 → TMC / MOSFET / `J_MOT*` / `J_P24S`.
2. **Lòng nam:** plane In2 `+24V`; bulk C sát VM/COM; PTC từng nhánh motor (`+24V_MOT`,
   `+24V_MOT2`).
3. **Đai giữa — isolation:** hàng PC817 + R LED 2k2 + R PU 10k + C HF `+24V_SNS`.
   Không module MCU/USB trong đai này.
4. **Lòng bắc:** MCU + 3V3 + USB/CH340 + TM1637/keypad (HMI).
5. **Cạnh bắc (N) — sensor / điều khiển:** `J_P24N`, đếm BUP/fiber, IN start/stop,
   `J_CNT5` 5 V, USB. Khe housing **≥ 5 mm**.
6. **Đông / tây:** **cấm giắc field** — khe DIN + ngón tay. Linh kiện không phải giắc
   ngoài **≥ 4 mm** mép (BOM); track/via vẫn **≥ 2 mm** (A12).

`E11.1` (12 V star POWER∥OPTO∥TMC…) là cùng luật, viết cho rail cũ. **Rail sản xuất
hiện tại = 24 V** (`BOM.md`). Đổi tên net không được đổi thứ tự vùng.

### P2. Cây nguồn — tách tải, không chung một nhánh

```
PSU 24V ──J1── D3 (ngược cực) ── F1 (rút ống 5×20) ── +24V ← D1 TVS
                              │
              ┌───────────────┼── PTC_MOT  ── +24V_MOT  ── TMC1 / J_MOT1
              ├── PTC_MOT2 ── +24V_MOT2 ── TMC2 / J_MOT2
              ├── PTC_SNS + R10 ── +24V_SNS ── J14/J15/IN2/IN3 (cảm biến)
              └── U2 MP1584 ── +5V ← D5 TVS ── LDO ── +3V3 ── U1
```

| # | Luật | Lý do PLC |
|---|------|-----------|
| **P2.1** | Sensor **không** lấy từ `+24V_MOT` | Inrush/stall motor làm tụt L+ → DI giả, opto LED đói |
| **P2.2** | `+24V_SNS` có PTC ~0,1 A | Đầu cảm biến chập không kéo sập rail MCU |
| **P2.3** | Logic chỉ từ buck; **TVS +5V** sát U2/U6 | Surge field không đi vào VDD |
| **P2.4** | F1 **đế 5×20 rút ống** (không SMT 2410 khi chưa hỏi) | Bảo trì tủ: thay cầu chì không tháo board |
| **P2.5** | Track Power **0,50–1,00 mm** (E9); In2 nam = `+24V` | IPC-2221 ΔT 10 °C, không Default 0,25 mm |
| **P2.6** | `+24V*` ↔ net khác **≥ 0,40 mm** (sàn JLC 24 V); router **0,50 mm** | Creepage 24 V; min xưởng 0,10 mm **không đủ** |

### P3. Ngõ vào số (DI) — card input 24 V

Chuẩn tủ: cảm biến **NPN 3 dây** (L+, 0 V, OUT sink). Board **không hỗ trợ PNP**.

| # | Luật | Trên board |
|---|---------|------------|
| **P3.1** | Mỗi DI: `+V · 0V · SIG` trên **một** giắc keyed (XH) | J14/J15/IN2/IN3 = 24 V; `J_CNT5` = 5 V — **không gộp** |
| **P3.2** | SIG 24 V → R LED → anode PC817; cathode → field 0 V (NPN đóng) | R41–R44 **2k2** (~10 mA @ 24 V) |
| **P3.3** | Collector opto → GPIO, **PU 10k → 3V3**; emitter → GND logic | R45–R48; MCU không thấy 24 V |
| **P3.4** | C HF (`C26` 100 nF) trên `+24V_SNS` tại cụm opto | IEC-style: lọc burst, không debounce 100 ms trên PCB |
| **P3.5** | Track DI field (24 V) **nam / đai opto**; sau opto = tín hiệu 3V3 trên **B.Cu** về MCU | Không song song MotA/B trên cùng mặt dài |
| **P3.6** | Đếm nhanh (BUP / fiber / CNT5) **giắc riêng, dây ngắn tới opto/MCU** | Không daisy-chain SIG qua jack motor |

### P4. Ngõ ra số (DO) / motion — card output

GPIO MCU **không** là đầu ra PLC.

| # | Luật | Trên board |
|---|------|------------|
| **P4.1** | Tải 24 V (van, MOSFET 1CH): module `U_PWR*` — PWM + EN + FAULT | FAULT về MCU; không để chân FAULT NC nếu module có |
| **P4.2** | Rung / AC / cách ly tải: `U_VIB` SSR | Không ULN cho tải cảm ứng lớn |
| **P4.3** | Stepper: TMC (NEMA) / ULN+JST (28BYJ) — **cáp motor ra cạnh nam** | Cấm dùng giắc Mot in sẵn trên StepStick (kéo ồn vào module) |
| **P4.4** | Freewheel / TVS sát tải (D2 bơm; diode trên module PWR) | Inductive kick không về In1 qua via ngẫu nhiên |
| **P4.5** | **Fail-safe boot:** mọi DO = OFF khi CPU reset (Hi-Z). Compact: EN TMC **PU** (`R2`/`R2B`, active-low); PWM/EN MOSFET + `VIB_CTRL` **PD 10k** (P9) | Thiếu PD → van/SSR có thể bật lúc reset |
| **P4.6** | Cặp MotA/B (và Mot2*) **sát nhau, vòng nhỏ**, bulk VM ≤ 10 mm | Chopper không phải GPIO |

### P5. Mặt đồng / EMI — “card trong rack kim loại”

| # | Luật | Khớp |
|---|------|------|
| **P5.1** | In1 = **0 V đặc** (M của PLC). Không khe dưới USB, STEP/DIR, opto collector | A10, E10.6 |
| **P5.2** | In2 **tách** `+24V` nam / `+5V` TB / `+3V3` ĐB, khe ≥ 0,6 mm | Không pour 24 V dưới MCU |
| **P5.3** | F.Cu = pad + fan-out; bus field/logic dài = **B.Cu** | A0 |
| **P5.4** | 24 V và 3V3 **không** đi song song sát trên cùng lớp; giao nhau thì một lớp + GND In1 ở giữa | Tránh coupling DI giả |
| **P5.5** | USB D± / UART: cặp, cùng lớp, ngắn tới jack **bắc** | Xa TMC nam |
| **P5.6** | Stitch GND: via 0,8/0,4 **≥ 1 mm** pad (A11); **không** via-in-pad | A8 |

### P6. Giắc & cáp — thói quen tủ điện

| # | Luật |
|---|------|
| **P6.1** | Field **chỉ cạnh N và S**. W/E = DIN + tay — không XH 24 V. |
| **P6.2** | Hàng chân giắc **song song cạnh** (rot 90° / ngang). Miệng cắm ra ngoài tủ. |
| **P6.3** | Cùng hàng: khe **housing ≥ 5 mm** (rút hai phích không chạm). |
| **P6.4** | Thứ tự pin in silk **như borne PLC**: `+V`, `0V`, `SIG` (không đảo 0V/SIG giữa các jack cùng loại). |
| **P6.5** | Một giắc = một chức năng (C8). Không “header đa năng” field. |
| **P6.6** | Cáp motor / MOSFET **cạnh nam**; cáp đếm / IN **cạnh bắc** — hai phía tủ, giảm crosstalk. |
| **P6.7** | Silk **mục đích** (24V IN, MOTOR 1, DI BUP, CNT 5V) — không chỉ J14. |

### P7. Bảo vệ & bảo trì

| # | Luật |
|---|------|
| **P7.1** | TVS **sát chân vào** (D1 @ `+24V`, D5 @ `+5V`) — không 40 mm sau fuse. |
| **P7.2** | F1 nhìn thấy, ống rút được, silk định mức. |
| **P7.3** | Test point (hoặc pad đo) `+24V` / `+5V` / `+3V3` / GND — E10.9. |
| **P7.4** | Courtyard module ≥ 8 mm (E11.2); MCU ≥ 10 mm (E11.12) — chỗ kẹp probe + luồng khí TMC. |
| **P7.5** | SKU: pad DO/TMC **để trống khi không lắp** (DNP) — không cắt net, không jumper 24 V vào chân FAULT. |

### P8. Thứ tự quyết định khi tắc (PLC, không “hạ DRC”)

1. Tách vùng P1 (nới đai opto / đẩy MCU bắc).
2. Đổi cạnh giắc (motor nam, sensor bắc) — E11.3.
3. Mở board, **không** hạ 0,50 mm / 1 mm via–pad / 2 mm mép.
4. Chỉ sau đó mới thêm via fan-out (A0).

**Cổng:** mắt P1–P6 + `verify_compact.py` (giắc N/S, 24 V) + A5–A13 + mục F (P).

### P9. Chân IC không dùng — PLC (không để float trên DO)

Audit pad trên PCB live (KiCad 10). **Bắt buộc / nên / cấm** — không bịa LCSC; 0805 Basic khi thêm.

| Chip | Chân NC / lệch | Hiện trạng PCB | Quyết định PLC |
|------|----------------|----------------|----------------|
| **U1 STM32G030C8T6** | PC13, PC14, PC15, PF0, PF1, PC6, PC7, PA15, PD0, PD2, PD3, PB3 (pad 1–3, 8–9, 30–31, 37–38, 40–42) | `unconnected-(U1-P…)` | **Không hàn R/C.** Firmware: analog input, không pull. **Cấm** GND/VDD cứng PF0/PF1 (OSC) và PC14/PC15 (OSC32) — có thể không boot / khóa HSI. Không thêm thạch anh 32 kHz trừ khi cần RTC. |
| **U1 DO đã dùng** | PA11/12 PWM, PB5/6 EN, PB8 VIB, PA0/1 + PA6/7 STEP/DIR | `R_PD_PWM*` `R_PD_EN*` `R_PD_VIB` `R_PD_STEP*` `R_PD_DIR*` 10k→GND | Đã hàn P4.5. |
| **U1 boot** | NRST, PA13, PA14/BOOT0 | `R_NRST` PU + `C_NRST`; `R_SWDIO` PU; `R_BOOT` PD | Đủ. Không thêm. |
| **U2 MP1584EN** | EN pad 2 | Không net (float) | **Giữ float** = luôn bật (datasheet). **Cấm** kéo EN lên `+24V` (abs max ~6 V). Optional UVLO: divider + zener 5V1 từ VIN — không bắt buộc máy luôn-on. Schematic: `no_connect` EN. COMP/FB/FREQ/BST đã có Cc, Rfb, R_FREQ, Cbst. |
| **U3/U4 TMC2209 socket** | MS1, MS2, PDN/UART, PDN2, CLK (pad 2–6) | NC trên carrier | **Không thêm trên carrier.** MS1/MS2/UART/CLK xử lý **trên module**. CLK module thường đã GND (osc trong). DIAG không ra header 16 chân này — stallGuard = đổi footprint, không R treo. EN đã `R2`/`R2B` PU (disable lúc boot). |
| **U5 CH340C** | 9–15 CTS/DSR/RI/DCD/DTR/RTS/R232 | NC | **Không thêm** (không handshake). |
| **U5 CH340C** | 4 V3 (LDO 3V3 nội) | `/CH340_V3` + `C_V3` 100 n→GND; **không** AMS1117 | Đã sửa. |
| **U5 CH340C** | USB D± | Không TVS/ESD | **Nên** array ESD (USBLC6-2SC6 hoặc SKU JLC **trong** `jlc_lcsc.csv`) sát `J_USB`. |
| **U6 AMS1117** | GND / VOUT / VIN / TAB | Đủ; C3 47 µ + C31 100 n | Không thêm. |
| **U44–U47 PC817** | Cả 4 chân dùng | LED R 2k2/1k + collector PU 10k | **Nên** 100 pF–1 nF collector→GND (`/BUP` `/IN2` `/IN3` `/CNT5`) — lọc burst IEC, P3.4 hiện chỉ C26 trên rail SNS. |
| **U_PWR* / U_VIB** | FAULT | `R_PWR_FLT` / `R_VIB_FLT` 10k PU; PWM/EN/CTRL PD | Đủ. |
| **J_USB.4 ID** | NC | OK USB device | Không nối. |
| **J14.4** | silk cũ ENC_B | NC | Để NC (hoặc shield→GND nếu đổi giắc 4P có vỏ). Không phải chân IC. |

**Firmware (cùng P9, không BOM):** GPIO NC = analog; GPIO DO = push-pull sau khi PD cứng đã kéo OFF; không `GPIO_PULLUP` trên PWM/EN/VIB.

**BOM P9 (đã lên board — 0805, LCSC từ `jlc_lcsc.csv`):**

| Ref (đề xuất) | Net | Giá trị | Mức |
|---------------|-----|---------|-----|
| `R_PD_PWM1/2` | `/PWM_OUT*` → GND | 10k | **Bắt buộc** P4.5 |
| `R_PD_EN1/2` | `/PWR_EN*` → GND | 10k | **Bắt buộc** P4.5 |
| `R_PD_VIB` | `/VIB_CTRL` → GND | 10k | **Bắt buộc** P4.5 |
| `R_PD_STEP/DIR` ×4 | `/STEP*` `/DIR*` → GND | 10k | Nên |
| `C_V3` | U5.4 V3 → GND; **cắt** V3 khỏi `+3V3` | 100n | **Bắt buộc** datasheet |
| `C_DI1…4` | collector opto → GND | **3n3 C107149** (csv; không có 100p–1n) | Nên (EMI DI) |
| ESD USB | D+ D− GND sát jack | — | Nên (P7); chỉ khi có mã kho |

Không chạy `gen_compact_carrier.py` lên board live khi thêm — placement `placement_saved.py` + cập nhật `build_parts` rồi regenerate schematic / tay trên PCB.

### P10. Ổn định / bền (audit live 2026-09-17)

Rà **toàn BOM + pad live** (không bịa LCSC). P9 fail-safe đã đủ. Dưới đây là khe **ổn định nguồn / EMI / field** — khác P9 (chân float).

**Đã đủ (không thêm SKU):** D3 ngược cực + F1 5×20 + D1 SMBJ26A; PTC_MOT/MOT2 + C20/C20B; PTC_SNS+R10+C10/C11; D5 SMBJ5.0A + C5/C51; U6 C3+C31; NRST 10k+100n; BOOT PD / SWDIO PU; TMC EN PU; P4.5 PD; CH340 C_V3; Y1+22p; opto LED 2k2/1k + collector 10k; FAULT PU; C26/C27 trên rail SNS/5V.

#### P10.1. Tụ đã có nhưng **xa pad** (ưu tiên dịch, không thêm mã)

HF decoupling vô nghĩa nếu >10 mm. Toạ độ `placement_saved.py`:

| Tụ (đã trên BOM) | Net | Chỗ hiện tại | IC cần lọc | Khoảng | Việc |
|------------------|-----|--------------|------------|--------|------|
| `C_MCU` 100n | +3V3 | 180.5, 126.5 | U1 VDD/VSS (182.5, 75) | **~52 mm** | **Dịch ≤5 mm** chân 6/7 |
| `C_MCU2` 1µ | +3V3 | 173.5, 127 | U1 VDDA/VREF+ (cùng +3V3) | **~52 mm** | **Dịch** sát U1.4–6 |
| `C21` 47µ | +24V | 78.5, 118 | U2 VIN pin 7 (123.1, 102.1) | **~48 mm** | Dịch gần U2 **hoặc** thêm ceramic VIN |
| `C53` 100n | +5V | 181, 121 | U5.16 VCC (215.5, 80.8) | **~53 mm** | Dịch sát CH340 **hoặc** thêm `C_CH340` |
| `C20` 220µ | +24V_MOT | 127.5, 123.5 | U3.9 VM (119.6, 144.4) | **~22 mm** | Nên ≤10 mm (P4.6) |

`C52` (113, 73) là 100n +3V3 nhưng **cụm opto**, không thay C_MCU.

#### P10.2. Nên bổ sung — LCSC **đã có** trong `jlc_lcsc.csv`

| Ref | Việc | LCSC (cùng mã đang dùng) | Mức | Lý do bền |
|-----|------|--------------------------|-----|-----------|
| `C_VIN` | 100n (và/hoặc 1µ `C28323`) U2.7 VIN→GND | C1711 / C28323 | **Bắt buộc** nếu không dịch C21 | MP1584 cần ceramic sát VIN; bulk 48 mm → ring / brownout 5 V |
| `C_CH340` | 100n U5.16 +5V→GND | C1711 | Nên (hoặc dịch C53) | CH340 USB packet; C_V3 chỉ lọc LDO V3 |
| `C_DI1…4` | **3n3** collector `/BUP` `/IN2` `/IN3` `/CNT5`→GND | **C107149** (cùng `Cc`) | Nên P3.4 | 100p–1n **không** có trong csv. 3n3×10k ≈ 5 kHz — lọc EFT, đếm viên vẫn qua. **Không** dùng C1711 100n trên kênh đếm (chậm). |
| `D_USB` | SS54 `J_USB.1` (`/USB_VBUS`) → `+5V` | C2903855 (cùng D3/D4) | **Bắt buộc** nếu vừa USB vừa 24 V | Hiện VBUS **trùng net `+5V` buck** — hai nguồn 5 V đấu nhau, ngược về PC |
| `PTC_5V` | C12430 `+5V` → `+5V_AUX` cho `J_P5N`+`J_CNT5` | C12430 (cùng PTC_SNS) | Nên | Chập IR/LED 5 V làm sập AMS1117/MCU. `J_DISP` giữ `+5V` sau buck (không qua PTC 0,1 A) |
| `R_TM_CLK` `R_TM_DIO` | 1k series PA4/PA5 | C17513 (cùng R47) | Nên | Module TM1637 kéo lên 5 V. PA4=`FT_a`, PA5=`FT_ea` (digital 5 V OK; **cấm** bật ADC). 1k giới hạn inject. Firmware: open-drain, tắt PU nội. |

USB ESD array / ferrite: **không thêm** — không có mã trong `jlc_lcsc.csv`.

#### P10.3. Không thêm (đủ hoặc cấm)

| Ý tưởng | Quyết định |
|---------|------------|
| Thạch anh 32 kHz PC14/15 | **Cấm** P9 — HSI đủ; hard-tie OSC có thể không boot |
| ESD USB USBLC6 | Nên về EMI, **hoãn** đến khi map LCSC Basic thật |
| TVS thêm trên `+24V_SNS` | D1 đã kẹp `+24V`; PTC+R10+C10 đủ nhánh sensor |
| Series 22 Ω STEP/DIR | Module TMC đã có; 22 Ω 0805 không có (chỉ R10 1206) |
| R keypad 8×1k | Membrane 3V3, rủi ro thấp |
| Test point THT E10.9 | Không SMT JLC; đo tại giắc/`C3`/`C5`/`C21` |
| UVLO U2 EN | Giữ float (P9); máy luôn-on |
| Freewheel extra trên carrier | Diode nằm **module** PWR/TMC (P4.4) |

#### P10.4. Firmware (không BOM)

IWDG + brownout (`PWR_CR3`); GPIO NC = analog; TM1637 OD; không ADC trên PA4/PA5; debounce IN2/IN3 phần mềm; đếm BUP/CNT5 cạnh lên, không tin mức tĩnh khi EFT.

**Khi đưa P10.2 lên live board:** tay schematic+PCB (như P9), `dump_saved_pos.py`, **không** `gen_compact_carrier.py`. Dịch P10.1 trước nếu còn chỗ courtyard cạnh U1/U2/U5.

---

## E. Kiểm tra geometry / DRC (bắt buộc)

> **KiCad DRC là trọng tài.** Gate: `verify_drc.py` / `verify_all.py`.

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| E1 | Kích thước **180 × 120 mm** ±0.5 mm, gốc (50, 50) | `verify_pcb.py` / Edge.Cuts |
| E2 | **KiCad DRC: 0 lỗi nhóm điện** (E2b) | `verify_drc.py` |
| E2a | Heuristic `_check_overlaps.py` (tham khảo) | WARN nếu fail |
| E2b | Nhóm **điện — bắt buộc 0**: `unconnected_items`, `shorting_items`, `clearance`, `copper_edge_clearance`, `tracks_crossing`, `track_dangling`, `via_dangling`, `hole_clearance`, `hole_to_hole`, `annular_width`, `track_width` | `verify_drc.py` |
| E2c | Nhóm **thẩm mỹ — nên 0**: silk / text | liệt kê |
| E2d | `lib_footprint_mismatch` — chấp nhận được | ghi chú |
| E3 | 4× M3 mounting inset 3.5 mm; keepout đầu vít ⌀7 mm | KiCad + silk |
| E4 | Không footprint module chồng nhau (kể cả TOP↔BOTTOM) | `_check_overlaps.py` |
| E5 | **A5–A7 bắt buộc trên carrier và M1/M2** | `_check_signal_routing.py` + `verify_modules.py` / `_check_a5a7_all.py` |
| E6 | **Đồng (track / via / plane) cách mép ≥ 2,00 mm** (A12). DRC `min_copper_edge_clearance=2.0`; custom rule 2 mm — **không** giữ rule JLC 0,30 mm cạnh | DRC `copper_edge_clearance` + `enforce_via_edge.py --check` |
| E7 | Đổi lớp chỉ tại pad THT hoặc via thật | DRC |
| E8 | **Silk ≥ 0.8 mm**, chữ B mirror | DRC E2c |

#### E2e. A7 tiêm vào DSN

`route_freerouting.py` nâng mọi `(clearance …)` trong DSN lên **`A7_CLEARANCE_UM`**
(mặc định **500 µm = 0,50 mm**) — không dừng ở sàn DRC 0,20 mm. Riêng
`(clearance type via_pin)` = **`VIA_PIN_CLEAR_UM=1000`** (A11). DSN còn
keepout hàng chân (`pin_row_keepout.py`) và bốn rect mép 2 mm.

**2026-09-17 — carrier 4 lớp 180×120:** `FR_CLEAR_UM=500` là sàn **công nghiệp**
(không hạ xuống 250 để “đủ net”). `maze_router` dùng cùng `EDGE_CLEARANCE_MM=2.0`
và `VIA_PAD_GAP_MM=1.0`.

**Không pour GND trên F.Cu/B.Cu** — return là **In1 plane**. Zone In1/In2 inset
**2 mm** mép. Fill sau route với `SKIP_FANOUT=1` (fan-out via không chiếm track
→ short). Bug Specctra “mất kiểu BOARD” (A9) vẫn đúng: refill zone ở **tiến trình mới**.

## E9. Quy tắc bề rộng dây — fab tiêu chuẩn + dòng tải

### E9.1 Min xưởng (JLCPCB / PCBWay class — 2 lớp 1 oz)

| Tham số | Min xưởng điển hình | **Board này (bắt buộc ≥)** |
|---------|---------------------|----------------------------|
| Trace width | 0.127 mm (5 mil) / khuyến nghị 0.15–0.20 | **0.25 mm** Default |
| Clearance | 0.127 mm | **0.20 mm** (Power 0.25) |
| Via drill / pad | 0.3 / 0.5–0.6 | **0.4 / 0.8** (A8 — một cỡ, through only) |
| Annular ring | 0.13 mm | **≥ 0.15 mm** |
| Copper–edge | 0.3–0.5 mm (xưởng) | **≥ 2,00 mm** (A12 / E6) — plane inset 2 mm |

→ **Không có dây “quá nhỏ” so với fab** nếu mọi track ≥ 0.25 mm. Cổng `track_width` trong DRC phải = 0.

### E9.2 IPC-2221 approx (1 oz Cu, ΔT 10 °C, ngoài trời)

| Width | ~I max | Dùng cho |
|-------|--------|----------|
| 0.25–0.28 mm | ~0.7–0.9 A | GPIO, SPI, opto, shift `SER/SRCLK/…` |
| 0.30–0.34 mm | ~1.0 A | `BYJ*_` pha (~40 mA) — dư; MotA/B NEMA |
| 0.45 mm | ~1.3 A | +5V / +3V3 / SNS |
| **0.70 mm** | **~1.8 A** | **+12V / GND chính** |
| ≥1.0 mm | ≥2.2 A | nếu đỉnh PSU >2 A kéo dài — không dùng pour, tăng bề rộng track/netclass |

**Ngân sách dòng sau đổi BOM (ước lượng):**

| Tải | Typ | Peak |
|-----|-----|------|
| 3× 28BYJ-48 12V | ~0.15 A | ~0.45 A |
| NEMA17 + TMC | ~0.8 A | ~1.5 A stall |
| Bơm 370 | ~0.2 A | ~0.3 A |
| Logic / TFT | từ +5V (U2) | — |
| **+12V tổng** | ~1.2 A | **~2.3 A** |

→ Track +12V **0.70 mm ≈ 1.8 A** hơi sát peak stall — **chấp nhận được** cho burst ngắn; nếu đo stall thường xuyên: widen netclass Power lên **1.0 mm**. Netclass trong PCB **phải khớp** bề rộng router thật phát (E10.12): Power = **1.00 mm** (nâng từ 0.70 theo chính khuyến nghị ở trên; xem E9.4).

### E9.3 ⚠️ Netclass không khớp tên net = dây bé đi âm thầm

**Đây là lỗi đã xảy ra thật trên board này, và KiCad KHÔNG báo.**

Netclass `Power` liệt kê chân stepper bằng tên cũ còn dấu `/`:

```
(add_net "/MotA1")   ← không khớp net nào
```

Nhưng `write_pcb()` đã bỏ dấu `/` khỏi mọi tên net (để khớp global label của
schematic — xem E2). Tên không khớp thì netclass **không áp dụng, không cảnh báo**:
bốn net pha NEMA17 rơi về **Default 0,25 mm = 0,88 A**, trong khi TMC2209 lái cuộn
dây ở **~1 A**. Bảng E9.2 ghi MotA/B ở 0,30–0,34 mm, nhưng thực tế trên đồng là 0,25.

→ **Mỗi lần đổi quy ước đặt tên net, phải soi lại toàn bộ danh sách `add_net`.**
→ `verify_track_width.py` bắt được gián tiếp: nó so bề rộng **thực tế trên board**
với dòng tải khai trong `NET_CURRENT_A`, nên netclass hụt sẽ lộ ra ngay.

### E9.4 Cổng tự động

```sh
python verify_track_width.py
```

| # | Yêu cầu | Ghi chú |
|---|---------|---------|
| E9.4.1 | Mọi track **≥ `MIN_TRACK_MM` = 0,20 mm** | trên mọi mức tiêu chuẩn của xưởng |
| E9.4.2 | Mỗi net đủ tiết diện cho **dòng khai trong `NET_CURRENT_A`** (1 oz, ΔT 10 °C) | +12V/GND 2,2 A · MotA/B 1,0 A · BYJ 0,15 A |
| E9.4.3 | Netclass `Power` = **1,00 mm** (2,39 A) — đã nâng từ 0,70 mm (1,85 A) vì peak +12V ~2,3 A | khớp E9.2 |
| E9.4.4 | Đổi động cơ/tải → **cập nhật `NET_CURRENT_A`**, đừng chỉnh mỗi bảng trong tài liệu | tay |

**2026-09-03:** tái xác nhận sau khi sắp xếp lại placement tay + route lại ở
`A7_CLEARANCE_UM=700` — `verify_track_width.py` → PASS (47 net, bề rộng dùng
0.25mm/0.88A cho tín hiệu và 1mm/2.39A cho nguồn, đều đủ cho dòng khai báo).

### E9.3 Lưới maze (nếu bật lại)

Maze lưới **0.55 mm**: `0.28+0.28@0.20=0.48` OK; `0.34+0.34@0.20=0.54` OK; nguồn 0.70 cần chiếm cột kề.

---

## E11. Trước khi đi dây — bố trí & giắc (bắt buộc)

> Gate **placement + net + footprint** trước FreeRouting / maze.
> Chạy `PCB_SKIP_MAZE=1` → `python gen_power_carrier.py` rồi tick bảng dưới.
> **Không** gọi `route_freerouting.py` khi E11 hoặc C4 còn FAIL.

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| E11.1 | **Module nối nhau → đặt gần nhau** (12V star: POWER∥OPTO∥TMC∥BLOWER∥BUP∥AXIS; MCU+HMI phía đông 3V3/5V). Đường bao **Eco1 = cyan** | mắt + đo ctr cụm |
| E11.2 | **U1 khớp đường bao MCU** (Eco = courtyard DevKit ở **rot=0**); khe POWER→OPTO→MCU→TMC; **không** bắt buộc tâm board. Vành trống tới cụm kề **≥ 8 mm** (`MODULE_CLUSTER_GAP`) | mắt + gen E11.2 |
| E11.3 | **Tắc dây thì nới khoảng cách / mở rộng board, KHÔNG thu nhỏ.** Chỉ thu gọn board sau khi đã đi dây xong và đúng (0 unconnected, DRC sạch) | `_route.log` |
| E11.4 | **0 chồng lấn courtyard, 0 chi tiết ra ngoài Edge.Cuts** | `_overlap.py` → `overlaps=0 outside=0` |
| E11.5 | **TFT = hai header liền nhau, thứ tự giống hệt module MSP3520 / lcdwiki** (MODULES R-1): | mắt + `verify_connectivity.py` §E |
| | • **J17** `PinHeader_1x09_TFT_LCD` — module pins **1–9**: VCC, GND, CS, RESET, DC, SDI, SCK, LED, SDO | |
| | • **J23** `PinHeader_1x05_TFT_TP` — module pins **10–14**: T_CLK, T_CS, T_DIN, T_DO, T_IRQ | |
| | • Cùng cột X, J23.origin = J17.origin + **9 × 2,54 mm** (J17.9 → J23.1 liên tục) | |
| | • Silk tên chân đúng tên module (VCC…SDO / T_CLK…T_IRQ); J17.9 **NC**; SPI chung SCK↔T_CLK, MOSI↔T_DIN; MISO chỉ từ T_DO | |
| E11.6 | **J1** terminal 12V gần cạnh trái; **rot 90°** — hàng cọc **song song** cạnh gần nhất; miệng vào dây hướng ra mép | mắt + `_check_rot.py` |
| E11.7 | **Linh kiện rời (R/C/D/F):** silk **Reference + Value** + `fp_rect` bao chữ nhật (F/B.SilkS) | mắt + E10.13 |
| E11.8 | Connectivity / pinmap **PASS** trước route (`verify_connectivity.py`, `verify_esp32_nets.py`) | `verify_all.py` phần net |
| E11.9 | **Đường bao cụm cùng mặt không cắt nhau** (Eco1 vs Eco1). Generator `raise` nếu overlap. Cột tây 12V: POWER∥OPTO∥TMC∥BLOWER∥BUP∥**A1/A2/A3**; đông: MCU∥HMI | gen + `_cluster_balance.py` |
| E11.10 | **Mọi cụm module / courtyard ≥ 5 mm từ Edge.Cuts** (`MODULE_EDGE_CLEAR`). Lỗ M3 vẫn inset 3.5 mm góc | gen `raise` + `_check_edge_clear.py` |
| E11.11 | **Nhãn silk linh kiện rời** (pin1 notch, A/K/C/E, diode K, tụ +/−, header pin name) nằm trong footprint local — **xoay cùng rot đặt linh kiện** (chống cắm nhầm) | mắt + `_check_rot.py` |
| E11.12 | **Cụm module khác MCU ≥ 10 mm tới Eco MCU** (`MODULE_MCU_CLEAR`) — OPTO / TMC / HMI / blower / BUP / AXIS | gen E11.12 |
| E11.13 | **Xoay module nếu rubber-band chéo** (TMC 270°, DIP+BYJ 180°). **J1 90°** (cọc \|\| mép trái). TFT J17+J23 giữ 0° (thứ tự module) | mắt + `_check_rot.py` |
| E11.14 | **Mọi footprint (trừ lỗ mount H*) nằm trong một đường bao Eco1** — pad/at ∈ cụm; Eco = union courtyard thành viên | `_check_cluster_cover.py` (gen gọi sau ghi PCB) |


---

## E10. Điện & chế tạo (bắt buộc)

| # | Yêu cầu | Ghi chú |
|---|---------|---------|
| E10.1 | Tiết diện theo E9.2 | +12V peak ~2.3 A → theo dõi |
| E10.2 | Annular ≥ 0.15 mm | via 0.8/0.4 → 0.20 ✅ |
| E10.3 | Khoan ≥ 0.3 mm; aspect ≤ 8:1 @ 1.6 mm | via 0.4 ✅ |
| E10.4 | Tụ lọc sát chân: C20 470µ ≤10 mm tới TMC VM; **C21 100µ** chung ULN COM; **không** C22/C23 | |
| E10.5 | Loop area nhỏ: cặp MotA/B; pha 28BYJ nằm trên ULN module (không route trên carrier) | |
| E10.6 | Return path: tín hiệu F/B nằm trên **In1 GND đặc**; không khe plane dưới USB/STEP/chopper | 4 lớp — bắt buộc |
| E10.7 | Bảo vệ 12V: **D3 Schottky ngược cực** + F1 + D1; xem README mục an toàn | D3 SS54 series |
| E10.8 | F1 định mức ≥1.5× I làm việc | PTC 3A / PSU 4.2A ✅ |
| E10.9 | Test point +12V/+5V/+3V3/GND | nên có |
| E10.10 | Chiều cao 3D: ESP32 socket, TMC+heatsink, DIP-16 | 3D viewer |
| E10.11 | Giắc: hướng cắm, pin 1, chỗ rút cáp | silk |
| E10.12 | Netclass khớp bề rộng router | Power **1,00 mm** |
| E10.13 | **Linh kiện rời (R/C/D/F):** silk có **Reference + Value** và **đường bao chữ nhật** (`fp_rect` trên F/B.SilkS) | mắt + grep PCB |
| E10.13 | Schematic ↔ PCB parity | `kicad-cli --schematic-parity` |
| E10.14 | Nhiệt: ULN mát hơn DRV; TMC vẫn cần khe thoáng | |
| E10.15 | **28BYJ-48 bản 12V** (R~150–300Ω); VCC module ULN = +12V; motor cắm JST trên module | R-8 MODULES |
| E10.16 | **R4** bắt buộc — `/OE` Hi-Z lúc boot | verify §D |
| E10.17 | **GND = In1 plane** (không pour F/B). Track GND chỉ stitch / thermal. Via–pad ≥1 mm; mép ≥2 mm (A11–A12) | mắt + `enforce_via_edge.py --check` |

---

## F. Manual — sign-off người (bắt buộc trước fab)

- [ ] **E11 trước đi dây**: TFT J17+J23 liền cột; J1 trái **90°** (cọc \|\| mép); Eco không cắt (E11.9); cụm ≥5 mm mép (E11.10); ≥10 mm tới MCU (E11.12); ≥8 mm giữa cụm (E11.2); mọi part trong Eco (E11.14); overlap=0; `_check_rot` + connectivity PASS
- [ ] **P1 vùng PLC:** nam = 24 V + motor/DO; đai giữa = opto; bắc = MCU + DI/HMI/USB; **W/E không giắc field** (DIN)
- [ ] **P2:** `+24V_MOT*` ≠ `+24V_SNS`; F1 5×20; TVS sát vào; In2 khe 24 V / 5 V / 3V3
- [ ] **P3/P4:** IN 24 V chỉ NPN + opto; `J_CNT5` riêng 5 V; DO = MOSFET/SSR/TMC — GPIO không ra 24 V; EN TMC PU; PWM/EN MOSFET + VIB **PD 10k** (P9)
- [ ] **P9:** GPIO NC = analog FW (không GND OSC); CH340 V3 = 100 n→GND **không** đấu AMS1117; không R treo MS1/UART TMC trên carrier
- [ ] **P6:** giắc N/S, pin `+V · 0V · SIG`, khe housing ≥ 5 mm, silk borne (24V IN, MOTOR, DI …)
- [ ] Mở `esp32_baseboard.kicad_pcb` — F.Cu + B.Cu; kiểm bus TFT / motor / shift
- [ ] **A0**: bus dài trên **B.Cu**; F.Cu chỉ fan-out pad→via (mặt trước = module + giắc)
- [ ] **A8**: mọi via = **through 0,4/0,8**; không blind/buried/microvia/via-in-pad
- [ ] **A11**: via không trùng pad; đồng via–pad ≥ 1 mm (`enforce_via_edge.py --check`)
- [ ] **A12**: track/via/plane ≥ 2 mm Edge.Cuts
- [ ] **A13**: không đi xuyên hàng chân đế 2,54 mm
- [ ] **A10 / R**: In1 GND đặc; In2 tách nguồn; không bus F dưới module; Mot/USB theo bảng R
- [ ] **A5–A7**: không tín hiệu cắt nhau cùng mặt; không track cắt lỗ
- [ ] DRC: clearance ≥ 0.2, track ≥ 0.25, **edge ≥ 2,0**, via–pad ≥ 1,0
- [ ] 3D: MCU, TMC, ULN, F1 5×20, jack hướng đúng + silk pin1 / mục đích giắc
- [ ] Mọi footprint có **tên (Reference)** nhìn thấy
- [ ] Gerber: **180 × 120 mm**, **4 layer**, 1.6 mm, HASL/ENIG, không impedance controlled
- [ ] **M1/M2**: `python verify_modules.py` PASS (gồm A5–A7); pin mate khớp J30 / J31A / J31B
- [ ] **A7 modules**: `python _check_a5a7_all.py modules/m1_power_prot.kicad_pcb modules/m2_opto4.kicad_pcb` → hole hits = 0

---

## G. Lệnh nhanh

```powershell
./loop_check.sh
python verify_all.py
python verify_modules.py

python _check_net_copper.py
python verify_connectivity.py
python verify_esp32_nets.py
python _check_signal_routing.py
python enforce_via_edge.py --check
python verify_drc.py
python verify_fab.py
python verify_compact.py   # giắc N/S, 24 V, opto — cổng P

# E11 placement (trước đi dây)
python _overlap.py
python _check_edge_clear.py
python _check_rot.py
python _check_cluster_cover.py
```

---

## H. Khi FAIL

1. **Schematic là nguồn chân / net.** PCB phải khớp pin map schematic — không bịa LCSC / không `gen_compact_carrier.py`.
2. A11 (via–pad < 1 mm) / A12 (dây sát mép): chạy `enforce_via_edge.py` rồi `repair_open_pcb` — **không** hạ 1 mm / 2 mm.
3. A13 / A7 (xuyên hàng chân): keepout `pin_row_keepout.py`; đi vòng, không luồn 2,54 mm.
4. OPEN > 0: FreeRouting leftover → maze **repair** (không `maze_full` sau SES). Tắc thì nới placement (E11.3).
5. A5/A6 fail: đổi lớp / tách kênh / mở board.
6. Trace quá hẹp: tăng netclass Power — không hạ dưới 0.25 mm Default / 0,50 mm Mot.
7. **P (PLC):** track 24 V dưới MCU / USB, DI chung giắc 5 V, sensor lấy `+24V_MOT`, GPIO sink tải — **đưa về vùng P1**, không “vá dây cho xong”.
