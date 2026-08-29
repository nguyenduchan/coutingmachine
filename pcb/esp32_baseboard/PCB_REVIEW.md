# ESP32 Baseboard — yêu cầu bắt buộc trước khi đặt PCB

Carrier **235 × 132 mm**, 2 lớp, sinh bằng `gen_power_carrier.py`.

**Chạy cổng tự động (bắt buộc):**

```powershell
cd pcb\esp32_baseboard
python gen_power_carrier.py
python verify_pcb.py
```

### Hai bộ định tuyến

| | `maze_router.py` (tự viết) | **FreeRouting** (`route_freerouting.py`) |
|---|---|---|
| Thuật toán | Lee/A* trên lưới 0.55 mm + MST + rip-up | Push-and-shove trên hình học thật, đọc luật từ DSN |
| Thời gian | 20–30 phút | **~5 giây** |
| Kết quả gần nhất | 955 đoạn / 24 via / **17 chưa nối** | **0 chưa nối, DRC sạch** |

**FreeRouting là đường chính.** Lưới chiếm chỗ của bộ tự viết lưu *một net id mỗi ô*
nên về nguyên tắc không diễn tả nổi "ô này cách dây 0.7 mm đúng 0.30 mm" — mọi lỗi
clearance/ngắn mạch KiCad tìm được đều sinh ra từ đúng giới hạn đó. Nó vẫn được giữ
làm phương án dự phòng và để đối chiếu.

```sh
./loop_check.sh     # một vòng: sinh → schematic → định tuyến → đồng bộ lib → DRC
python verify_all.py   # phán quyết duy nhất cho toàn bộ PCB_REVIEW
```

`loop_check.sh` chạy đúng thứ tự sau, và **thứ tự này quan trọng**:

1. `gen_power_carrier.py` (với `PCB_SKIP_MAZE=1`) — chỉ bố trí + net, vài giây.
2. `gen_schematic_from_pcb.py` — dựng lại schematic **từ bảng net của PCB**, và
   đặt tên `unconnected-(…)` cho các pad cố ý bỏ trống. Phải chạy **trước** khi
   định tuyến: nếu không router tưởng các pad đó tự do và đi dây đè lên chúng.
3. `route_freerouting.py` — thử nhiều mức nỗ lực, chấm điểm từng lần bằng chính
   DRC của KiCad, dừng ở lần đầu nối đủ; xoá các mẩu dây thừa sau khi nhập SES.
4. `sync_footprint_lib.py` — ghi lại `.pretty` từ footprint đã đặt.
5. `kicad-cli pcb drc --schematic-parity`.

`route_freerouting.py` tự: bóc hết dây cũ → `ExportSpecctraDSN` (đưa luật thật của
KiCad cho router) → chạy `freerouting.jar` headless → `ImportSpecctraSES` →
ghi ra `out_freerouting/routed.kicad_pcb`. Tham số chỉnh ở đầu file
(`FR_PASSES`, `FR_VIA_COST`, `FR_THREADS`). **Bắt buộc `-mt 1`** — chính FreeRouting
cảnh báo tối ưu đa luồng của nó sinh lỗi clearance.

Chỉ đặt PCB khi `verify_pcb.py` → **OVERALL: PASS** **và** mục **Manual** bên dưới đã tick.

---

## A. Chính sách routing (bắt buộc)

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| A1 | **Ưu tiên đổi lớp tại pad THT**; chỉ thêm via khi net **không có** đường đi trên cùng một mặt. Router tính via = ~70 bước lưới nên chỉ mua khi hết cách | `verify_pcb.py` đếm `(via` ≤ 12 |
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
| B4 | `/OPTO_OUT8` **không** vào U1 (IO9 = `/BUZZER`) | `verify_connectivity.py` |
| B5 | R2 pull-up `/EN_TMC`; R3 pull-down `/BLOWER`; D2 freewheel bom | `verify_connectivity.py` §E/F |

---

## C. Module ↔ jack (bắt buộc)

| # | Khối | Kiểm |
|---|------|------|
| C1 | U3 TMC2209 ↔ J2 NEMA17 ↔ IO16/17/18 | `verify_connectivity.py` §B |
| C2 | U4/U9 opto ↔ J4 field + J8–J13 limit + J14 BUP | §C |
| C3 | U5–U7 DRV8871 ↔ J5–J7 GA12-N20 ↔ IO10–15 | §D |
| C4 | J17 TFT pinout (SPI + touch, không T_INT) | §E |
| C5 | J18 EC11 ENC_A/B → IO38 / IO41 | §E |
| C6 | J15 buzzer IO9; J16 blower IO3 + **+12V** (không U8) | §E |
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

> **KiCad DRC là trọng tài, không phải các script Python.** Các script chỉ *mô hình
> hoá* board; đã từng có bản chạy PASS toàn bộ gate Python trong khi KiCad báo
> **380 vi phạm + 29 mục chưa nối**. Vì vậy DRC thật nay nằm trong gate tự động
> (`verify_drc.py`, gọi `kicad-cli pcb drc`), không còn là mục tick tay.

| # | Yêu cầu | Cách kiểm |
|---|---------|-----------|
| E1 | Kích thước **235 × 132 mm** ±0.5 mm | `verify_pcb.py` |
| E2 | **KiCad DRC: 0 lỗi thuộc nhóm điện** (xem E2b) | `verify_drc.py` |
| E2a | Heuristic Python `_check_overlaps.py` (tham khảo) | `verify_pcb.py` hiện WARN nếu fail |
| E2b | Nhóm **điện — bắt buộc 0**: `unconnected_items`, `shorting_items`, `clearance`, `copper_edge_clearance`, `tracks_crossing`, `track_dangling`, `via_dangling`, `hole_clearance`, `hole_to_hole`, `annular_width`, `track_width` | `verify_drc.py` |
| E2c | Nhóm **thẩm mỹ — nên bằng 0**: `text_height`, `silk_overlap`, `silk_over_copper`, `silk_edge_clearance`, `nonmirrored_text_on_back_layer` | `verify_drc.py` liệt kê |
| E2d | `lib_footprint_mismatch` — **chấp nhận được**: generator ghi footprint kèm net thẳng vào `.kicad_pcb` nên không bao giờ khớp byte với `.kicad_mod` | ghi chú, không fail |
| E3 | 4× M3 mounting inset 3.5 mm từ cạnh; keepout đủ cho **đầu vít + long đền M3 (⌀7 mm)** | KiCad + silk |
| E4 | Không footprint module chồng nhau (kể cả TOP↔BOTTOM: chân THT xuyên qua thân module mặt kia) | `_check_overlaps.py` (info) |
| E5 | **A5–A7 bắt buộc** — xem mục A | `_check_signal_routing.py` |
| E6 | **Đồng cách mép board ≥ 0.5 mm** (Edge.Cuts) | DRC `copper_edge_clearance` |
| E7 | **Đổi lớp chỉ tại pad THT hoặc via thật** — không được "nhảy lớp giữa không trung" | DRC `unconnected_items` + `track_dangling` |
| E8 | **Silk ≥ 0.8 mm**, chữ mặt B **phải mirror**, không đè lên pad hở | DRC E2c |

#### E2e. Vì sao A7 phải tiêm vào DSN

Luật A7 đòi thêm **0,25 mm** ngoài clearance xưởng quanh mọi lỗ. KiCad chỉ mang
0,20 mm trong netclass, nên nếu không nói gì thì FreeRouting đi đúng 0,20 và A7
báo 86 lỗi — **mỗi lỗi đúng bằng 0,25 mm**. `route_freerouting.py` nâng *mọi*
mục `(clearance …)` trong DSN lên 0,45 mm trước khi chạy. Lưu ý KiCad ghi thêm
một khối `(rule …)` cho **từng netclass**, và các khối này **đè lên** luật toàn
cục — chỉ sửa luật toàn cục thì vẫn còn 33 lỗi.

FreeRouting 2.1 **không** hiểu `(clearance … (type wire_pin))`; các dòng đó vẫn
được ghi cho router khác, nhưng thứ thực sự có tác dụng là clearance toàn cục.

## E9. Quy tắc lưới ↔ bề rộng (vì sao chọn các trị số này)

Maze router đặt dây trên lưới **0.55 mm**, nên hai dây gần nhau nhất luôn cách
đúng 0.55 mm. Điều kiện DRC là `w_a/2 + w_b/2 + clearance`:

| Cặp | Cần | Ở 0.55 mm |
|---|---|---|
| 0.28 + 0.28 tín hiệu @0.20 | 0.48 | ✅ |
| 0.34 + 0.34 motor @0.20 | 0.54 | ✅ (nên `MAX_SIGNAL_WIDTH = 0.34`) |
| 0.70 + 0.28 nguồn/tín hiệu @0.25 | 0.74 | ❌ → track nguồn **phải tự chiếm cột lưới bên cạnh** |

`MAZE_CLEARANCE_MM` được chỉnh đúng để bán kính đánh dấu của track dày chạm tới
cột kề, còn track mảnh thì không — nếu sửa bề rộng hay bước lưới, **phải tính lại
bảng này**, nếu không sẽ có ngắn mạch mà gate Python không thấy.

---

## E10. Điện & chế tạo (bắt buộc — chưa tự động hoá)

| # | Yêu cầu | Ghi chú |
|---|---------|---------|
| E10.1 | **Tiết diện dây theo dòng** (IPC-2221, đồng 1 oz, ΔT 10 °C): 0.28 mm ≈ 0.9 A · 0.34 mm ≈ 1.0 A · 0.70 mm ≈ 1.8 A | +12V vào ~2.5 A đỉnh → kiểm lại nếu đổi tải |
| E10.2 | **Annular ring ≥ 0.15 mm** mỗi bên (pad 1.7 / khoan 1.0 → 0.35 ✅; via 0.8 / 0.4 → 0.20 ✅) | JLCPCB tối thiểu 0.13 |
| E10.3 | **Khoan nhỏ nhất ≥ 0.3 mm**, tỉ lệ aspect ≤ 8:1 với board 1.6 mm | via 0.4 ✅ |
| E10.4 | **Tụ lọc đặt sát chân nó phục vụ** — bulk 470 µF ≤ 10 mm tới chân VM của DRV/TMC | C20–C23 |
| E10.5 | **Diện tích vòng dây (loop area)** của cặp motor/stepper phải nhỏ — hai dây một pha đi song song, không tách xa | MotA1/A2, MotB1/B2, MotDC*_A/B |
| E10.6 | **Đường về dòng (return path)** — GND phải có đường liền kề dây tín hiệu dài | 2 lớp không có mặt phẳng GND ⇒ hạn chế |
| E10.7 | **Bảo vệ đầu vào 12 V**: F1 PTC + D1 TVS; cân nhắc thêm **chống ngược cực** (MOSFET P hoặc diode nối tiếp) | hiện chưa có |
| E10.8 | **Định mức F1** ≥ 1.5× dòng làm việc, < dòng tối đa của nguồn | PTC 3 A / PSU 4.2 A ✅ |
| E10.9 | **Điểm đo (test point)** cho +12V, +5V, +3V3, GND | tiện dò lỗi |
| E10.10 | **Chiều cao linh kiện & va chạm 3D** — đế ESP32, TMC + tản nhiệt, tụ 470 µF đứng | kiểm bằng 3D viewer |
| E10.11 | **Giắc: chiều cắm, đánh dấu chân 1, đủ chỗ rút cáp**, không bị module mặt kia chắn | silk + 3D |
| E10.12 | **Netclass phải khớp bề rộng router thật phát ra** — netclass ghi 1.5 mm mà router phát 0.7 mm là sai lệch gây hiểu nhầm khi sửa tay | xem `net_class` trong `.kicad_pcb` |
| E10.13 | **Schematic ↔ PCB parity** | `kicad-cli pcb drc --schematic-parity` |
| E10.14 | **Nhiệt**: DRV8871 và TMC2209 tản nhiệt qua module; đảm bảo có khe thoáng, không bị giắc che | bố trí |

---

## F. Manual — sign-off người (bắt buộc trước fab)

- [ ] Mở `esp32_baseboard.kicad_pcb` — bật F.Cu + B.Cu, zoom bus trái (TFT) và bus phải (motor)
- [ ] **A5–A7**: không thấy dây tín hiệu cắt nhau trên cùng mặt; không track cắt qua lỗ M3 / lỗ header
- [ ] DRC chạy với rule 2-layer fab (clearance ≥ 0.2 mm, track ≥ 0.2 mm)
- [ ] 3D/preview: ESP32 socket, TMC, DRV không đụng nhau; jack hướng đúng silk
- [ ] BOM khớp `README.md` + `MODULES.md` (DevKitC-1 **N8R2**, không N16R8V)
- [ ] Gerber export: kiểm tra lớp `.GTL` / `.GBL` / `.GKO` đúng 235 mm
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
python verify_drc.py         # KiCad DRC that (kicad-cli)
python repair_open_nets.py   # chi khi OPEN > 0 sau sửa generator
```

---

## H. Khi FAIL

1. Sửa `gen_power_carrier.py` / `maze_router.py` / `s3_pinmap.py` — **không** sửa tay `.kicad_pcb` (sẽ mất khi regen).
2. Chạy lại `gen_power_carrier.py` → `verify_pcb.py`.
3. Nếu OPEN > 0: xem log maze + `repair_open_nets.py`; cân nhắc thêm `BOARD_W` hoặc bus lane.
4. Neu A5/A6 fail: tang `BusLaneAllocator.pitch`, doi lop (F/B), hoac `BOARD_W` — tin hieu phai co kenh rieng tung mat.
5. Neu A7 fail: ne track qua header/M3; sua maze keepout hoac bus_y margin.
