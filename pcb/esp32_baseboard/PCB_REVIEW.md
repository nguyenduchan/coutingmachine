# ESP32 Baseboard — yêu cầu bắt buộc trước khi đặt PCB

Carrier **190 × 100 mm** (2026-09-04: thu khít theo vị trí linh kiện hiện có
còn 185.8×96.2mm với 5 mm mép mỗi cạnh — xem E11.10; 2026-09-05: làm tròn lên
190×100mm, phần dư mở rộng đều 4 hướng nên mép thật ≥5mm), 2 lớp, khung sinh
ban đầu bằng `gen_power_carrier.py` (mặc định 180×145 trong script, không dùng
nữa vì layout hiện tại đã sắp tay). Pluggable daughters: `modules/m1_power_prot`,
`modules/m2_opto4` (+ panel).

> Modules **≥ 5 mm** từ Edge.Cuts (E11.10). Cụm khác MCU **≥ 10 mm** tới Eco MCU (E11.12).
> Cụm cùng mặt cách nhau **≥ 8 mm** (E11.2). Mounting M3 vẫn inset 3.5 mm góc.
> **Mặt trước (F.Cu) = lắp module + giắc cắm.** **Đi dây ưu tiên mặt sau (B.Cu)**;
> F.Cu chỉ đoạn ngắn thoát pad / fan-out; không chạy bus dài trên mặt lắp linh kiện.

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

| | `maze_router.py` (tự viết) | **FreeRouting** (`route_freerouting.py`) |
|---|---|---|
| Thuật toán | Lee/A* trên lưới 0.55 mm + MST + rip-up | Push-and-shove trên hình học thật, đọc luật từ DSN |
| Thời gian | 20–30 phút | **~5–30 giây** |
| Kết quả gần nhất | dự phòng | **đường chính — 0 chưa nối, DRC sạch** |

**FreeRouting là đường chính.**

```sh
./loop_check.sh     # sinh → schematic → định tuyến → đồng bộ lib → DRC
python verify_all.py   # phán quyết duy nhất cho toàn bộ PCB_REVIEW
```

`loop_check.sh` thứ tự (quan trọng):

1. `gen_power_carrier.py` (`PCB_SKIP_MAZE=1`) — bố trí + net.
2. `gen_schematic_from_pcb.py` — schematic từ net PCB; `unconnected-(…)` cho pad cố ý bỏ trống (**trước** router).
3. `route_freerouting.py` — nhiều mức nỗ lực, chấm bằng DRC KiCad.
4. `sync_footprint_lib.py`
5. `kicad-cli pcb drc --schematic-parity`

Chỉ **đi dây** (FreeRouting) khi E11 + C4 đã xanh. Chỉ **đặt PCB** khi `verify_all.py` → **OVERALL: PASS** **và** mục **Manual** đã tick.

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
| A7 | **Không xuyên / quá sát lỗ** — ≥ drill/2 + **0,25 mm** + nửa bề rộng + **0,2 mm** tới pad THT/NPTH/via khác net (mức DRC tối thiểu). **Router thực tế đi rộng hơn mức tối thiểu này** — xem E2e | `_check_signal_routing.py` / `python _check_a5a7_all.py` / `verify_modules.py` → hole hits = 0 |
| A8 | **Via đổi mặt — dễ chế tạo nhất, một cỡ cho mọi xưởng.** Chỉ **via xuyên (PTH through)** F↔B; **cấm** blind / buried / microvia / via-in-pad. **Một kích thước duy nhất: khoan 0,4 mm / pad 0,8 mm** (vành ≥0,2 mm) — mũi khoan cơ khí chuẩn, aspect ~4:1 trên board 1,6 mm, dư dung sai lệch khoan so với min 0,3/0,6. Không thu nhỏ “cho đẹp”; không thêm cỡ via thứ hai | `net_class Default` + DRC `annular_width` / `hole_to_hole`; mắt Gerber |
| A9 | **`clean_stubs.py` chạy sau mỗi lần merge SES.** FreeRouting trả về đoạn trùng (bản sao y hệt, và đoạn ngắn nằm đè bên trong đoạn dài) — chúng làm hỏng phép quét antenna vì hai bản sao tựa vào đầu tự do của nhau. `pcbnew.TestTrackEndpointDangling` bỏ sót kiểu này, và sau lệnh Specctra thì binding pcbnew mất kiểu BOARD nên mọi lệnh dọn bằng pcbnew ném AttributeError rồi bị nuốt lặng | `drc_report.txt` → `track_dangling` = 0 |
| **A10** | **Chống nhiễu (EMI):** GND đi **track** netclass Power **1,00 mm** (**không phủ đồng/pour** — bỏ 2026-09-05, xem ghi chú dưới E2e); bulk C20/C21 sát tải; MotA/B vòng nhỏ; 28BYJ không route carrier; SPI/ENC gần MCU; field 12 V qua opto. Chi tiết bảng N1–N12 trong `README.md` | mắt + `verify_track_width.py` + Manual |

### A8 chi tiết — via cho nhiều loại máy / xưởng

Mục tiêu: **cùng Gerber chạy được** trên dây chuyền cơ khí phổ thông (JLCPCB, PCBWay,
xưởng VN 2 lớp) **không** cần quy trình laser, HDI, hay filled via.

| Quy tắc | Lý do |
|---------|--------|
| Chỉ **through-via** F.Cu ↔ B.Cu | Mọi máy khoan PCB 2 lớp đều làm được; blind/buried cần ép lớp riêng |
| **Drill 0,4 / pad 0,8** cố định | Mũi Ø0,4 phổ biến; vành 0,2 mm chịu lệch đăng ký giữa nhiều máy |
| **Không via-in-pad** (trừ khi fab filled — đắt, không dùng) | Tránh thiếc hút vào lỗ / hở hàn khi xưởng không plug |
| **Không microvia / laser** | Chỉ fab HDI; ngoài tầm board 2 lớp thường |
| Via–via / via–pad theo DRC board (≥ hole_to_hole, clearance) | Tránh cầu đồng / gãy vành khi khoan lệch |
| Ưu tiên **đổi lớp tại pad THT** (A1); via chỉ khi buộc phải | Ít lỗ = dễ khoan, ít rủi ro plating |

Min xưởng điển hình 0,3/0,6 **không dùng** — sát sàn thì lệch khoan một chút là mất annular.
Board này cố ý **lớn hơn min** để nhiều máy vẫn ra board tốt ở bậc giá rẻ.

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

---

## E. Kiểm tra geometry / DRC (bắt buộc)

> **KiCad DRC là trọng tài.** Gate: `verify_drc.py` / `verify_all.py`.

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| E1 | Kích thước **190 × 100 mm** ±0.5 mm | `verify_pcb.py` |
| E2 | **KiCad DRC: 0 lỗi nhóm điện** (E2b) | `verify_drc.py` |
| E2a | Heuristic `_check_overlaps.py` (tham khảo) | WARN nếu fail |
| E2b | Nhóm **điện — bắt buộc 0**: `unconnected_items`, `shorting_items`, `clearance`, `copper_edge_clearance`, `tracks_crossing`, `track_dangling`, `via_dangling`, `hole_clearance`, `hole_to_hole`, `annular_width`, `track_width` | `verify_drc.py` |
| E2c | Nhóm **thẩm mỹ — nên 0**: silk / text | liệt kê |
| E2d | `lib_footprint_mismatch` — chấp nhận được | ghi chú |
| E3 | 4× M3 mounting inset 3.5 mm; keepout đầu vít ⌀7 mm | KiCad + silk |
| E4 | Không footprint module chồng nhau (kể cả TOP↔BOTTOM) | `_check_overlaps.py` |
| E5 | **A5–A7 bắt buộc trên carrier và M1/M2** | `_check_signal_routing.py` + `verify_modules.py` / `_check_a5a7_all.py` |
| E6 | **Đồng cách mép ≥ 0.5 mm** | DRC `copper_edge_clearance` |
| E7 | Đổi lớp chỉ tại pad THT hoặc via thật | DRC |
| E8 | **Silk ≥ 0.8 mm**, chữ B mirror | DRC E2c |

#### E2e. A7 tiêm vào DSN

`route_freerouting.py` nâng mọi `(clearance …)` trong DSN lên **`A7_CLEARANCE_UM`**
trước khi chạy — không dừng ở mức tối thiểu DRC (0.45 mm = 0.20 netclass + 0.25 A7).
Sửa cả khối `(rule …)` từng netclass.

**2026-09-03 — tăng khoảng cách đi dây/lỗ, ghi lại quyết định:** mức 0.45 mm tuy
qua DRC nhưng khi render vẫn thấy dây chạy sát mép các pad lạ (ban đầu phát hiện
trên `modules/m2_opto4`) — đạt yêu cầu về con số nhưng không đạt yêu cầu "nhìn
là biết an toàn". Đã thử và chốt theo board:

| Board | `A7_CLEARANCE_UM` | Vì sao |
|---|---|---|
| **Carrier chính** (`esp32_baseboard.kicad_pcb`, 63 net, 180×145mm dày đặc) | **0.7 mm** | 0.9 mm khiến FreeRouting bỏ sót 3–5 net sau 6 lần thử (board quá chật ở mức đó); 0.7 mm đóng đủ 0 unconnected ngay lần đầu |
| **`modules/m2_opto4`** (14 net, 26×34mm rất thoáng) | **0.9 mm** | board nhỏ, dư chỗ — đi rộng hơn không tốn gì, dây vòng tránh xa mép pad rõ ràng trên render |

**Quy trình xác nhận bắt buộc mỗi khi đổi `A7_CLEARANCE_UM`:** `kicad-cli pcb drc`
(0 unconnected) + `_check_signal_routing.py` (A5/A6/A7 PASS) + **render 3D top-down
để mắt thường xác nhận** — số liệu PASS không thay thế được bước nhìn. Nếu FreeRouting
không đóng đủ net ở mức mới, **hạ dần** (không cố ép bằng cách tăng số lần thử) vì đây
là dấu hiệu board không đủ chỗ cho khoảng cách đó, không phải do router yếu.

**2026-09-05 — bỏ phủ đồng GND (pour):** board không còn dùng zone GND trên
F.Cu/B.Cu nữa — GND đi **track thường** như mọi net nguồn khác, netclass Power
**1,00 mm** (đủ 2,39 A theo E9.4.3, không cần pour để đạt tiết diện). Đã xoá 2
zone GND khỏi `esp32_baseboard.kicad_pcb`. Ghi chú lịch sử: trước đây từng có
bug khi gọi `fill_gnd_zones()` (trong `route_freerouting.py`) ngay sau
`ExportSpecctraDSN`/`ImportSpecctraSES` **cùng tiến trình** — pcbnew mất kiểu
`BOARD` của đối tượng đó (xem mục A9) nên lệnh phủ zone ném `AttributeError`.
Bug này (BOARD mất kiểu sau Specctra) **vẫn còn liên quan** cho các thao tác
dọn khác sau route (`clean_stubs.py`, xem A9) dù không còn phủ GND —
`_refill_gnd.py` (script tiến trình mới, tránh bug) vẫn còn trong repo nếu sau
này cần bật lại pour, nhưng **không** còn được gọi mặc định trong pipeline.

## E9. Quy tắc bề rộng dây — fab tiêu chuẩn + dòng tải

### E9.1 Min xưởng (JLCPCB / PCBWay class — 2 lớp 1 oz)

| Tham số | Min xưởng điển hình | **Board này (bắt buộc ≥)** |
|---------|---------------------|----------------------------|
| Trace width | 0.127 mm (5 mil) / khuyến nghị 0.15–0.20 | **0.25 mm** Default |
| Clearance | 0.127 mm | **0.20 mm** (Power 0.25) |
| Via drill / pad | 0.3 / 0.5–0.6 | **0.4 / 0.8** (A8 — một cỡ, through only) |
| Annular ring | 0.13 mm | **≥ 0.15 mm** |
| Copper–edge | 0.3–0.5 mm | **≥ 0.5 mm** |

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
| E10.6 | Return path GND liền kề tín hiệu dài | 2 lớp hạn chế |
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
| E10.17 | **GND đi track** netclass Power 1,00 mm, **không pour** (bỏ 2026-09-05, A10) — return path liền kề tín hiệu dài (E10.6) | mắt + `verify_track_width.py` |

---

## F. Manual — sign-off người (bắt buộc trước fab)

- [ ] **E11 trước đi dây**: TFT J17+J23 liền cột; J1 trái **90°** (cọc \|\| mép); Eco không cắt (E11.9); cụm ≥5 mm mép (E11.10); ≥10 mm tới MCU (E11.12); ≥8 mm giữa cụm (E11.2); mọi part trong Eco (E11.14); overlap=0; `_check_rot` + connectivity PASS
- [ ] Mở `esp32_baseboard.kicad_pcb` — F.Cu + B.Cu; kiểm bus TFT / motor / shift
- [ ] **A0**: bus dài trên **B.Cu**; F.Cu chỉ fan-out pad→via (mặt trước = module + giắc)
- [ ] **A8**: mọi via = **through 0,4/0,8**; không blind/buried/microvia/via-in-pad
- [ ] **A10 / README N1–N12**: GND đi track netclass Power 1,00 mm (không pour); không bus dưới module trên F; Mot/SPI/opto theo bảng chống nhiễu
- [ ] **A5–A7**: không tín hiệu cắt nhau cùng mặt; không track cắt lỗ (header/M3/PC817…) — **cả carrier và M1/M2**
- [ ] DRC: clearance ≥ 0.2, track ≥ 0.25
- [ ] 3D: ESP32, TMC, ULN/595, opto không đụng; jack hướng đúng + silk pin1/A/K/+
- [ ] BOM khớp `MODULES.md` + `README.md` (ULN+595, **không** DRV8871; DevKit **N16R8** không hậu tố V)
- [ ] Xác nhận TFT = ILI9488 + XPT2046, giắc **J17 1×9 + J23 1×5** khớp module (R-1 / E11.5)
- [ ] Gerber: **190 × 100 mm**, 2 layer, 1.6 mm, HASL/ENIG, không impedance controlled
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
python verify_drc.py

# E11 placement (trước đi dây)
python _overlap.py
python _check_edge_clear.py
python _check_rot.py
python _check_cluster_cover.py
```

---

## H. Khi FAIL

1. Sửa `gen_power_carrier.py` / `s3_pinmap.py` / `route_freerouting.py` — **không** sửa tay `.kicad_pcb` làm nguồn.
2. Chạy lại `./loop_check.sh` → `verify_all.py`.
3. OPEN > 0: xem log FR; cân nhắc `BOARD_W/H` hoặc vị trí DIP.
4. A5/A6 fail: đổi lớp / tách kênh / mở board.
5. A7 fail: né header/M3; clearance DSN 0.45.
6. Trace quá hẹp: tăng `net_width` trong maze / netclass Power — không hạ dưới 0.25.
