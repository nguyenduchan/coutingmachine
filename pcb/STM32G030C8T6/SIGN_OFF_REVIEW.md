# PCB Hardware Sign-off Review (LLM-executable)

**Project:** Counting-machine carrier · MCU STM32G030C8T6  
**Board path:** `pcb/STM32G030C8T6/`  
**Fab target:** JLCPCB 2-layer FR-4 1.6 mm, 1 oz, HASL lead-free  
**Purpose:** Verify **physical PCB hardware only** (no firmware, no power-on).  
**Gate to order:** every **BLOCKER** below = PASS. Warnings may ship with note.

This file is both:
1. A **reusable checklist** for humans / LLM agents on later revisions.
2. A **filled review** for the current board state (see § Current review).

---

## How an LLM should run this review

```text
Working directory: pcb/STM32G030C8T6
Environment: PYTHONUTF8=1 (Windows console)

1. Read this file + JLCPCB_REVIEW.md + jlcpcb_limits.py
2. Run:  python verify_pre_fab.py
3. Read: out/pre_fab_report.json, out/fab_verify.json,
         out/jlcpcb_verify.json, out/orientation_verify.json
4. Fill § Current review (date, PASS/FAIL per step, evidence)
5. List BLOCKERS (must fix before order) vs WARNINGS (document only)
6. Do NOT click “order” if any BLOCKER remains
```

Optional deeper scripts (same folder):

| Script | Maps to |
|--------|---------|
| `verify_schematic.py` | ERC / pin nets on SCH |
| `verify_fab.py` | SCH ↔ PCB parity, copper connectivity |
| `verify_compact.py` | Electrical intent (STM32 pinmap, power tree) |
| `verify_orientation.py` | Pin-1 / diode K / USB mouth / electrolytics |
| `verify_jlcpcb.py` | DFM/DFA house rules |
| `verify_jlc_bom.py` | LCSC on every SMT |
| `verify_track_width.py` | Power track IPC-2221 width |
| `kicad-cli pcb drc` | Copper shorts / clearance / unconnected |

**Out of scope for this hardware sign-off (do not block on):**
- Firmware, LED blink logic, sensor timing visibility
- Full SI (DDR/USB3/RF) — N/A on this 2L CH340 board
- Full thermal CFD — use track-width + bulk caps as proxy
- Paper 1:1 print — human step; LLM notes “needs human”

---

## Step 1 — Schematic ↔ PCB sync (ERC + Update)

### Checklist
- [ ] ERC: 0 fatal (`verify_schematic.py` / `verify_fab` G2)
- [ ] Every required IC pin on correct net (SCH)
- [ ] PCB footprints + pad nets match schematic (`verify_fab` G3–G4)
- [ ] KiCad schematic_parity: 0 real mismatches (ignore `{slash}` alias)
- [ ] No intentional “PCB-only” parts unless documented as WIP

### Tools
```bash
python verify_schematic.py
python verify_fab.py
```

### Pass criteria
- SCH ERC fatal = 0  
- SCH↔PCB pin mismatch = 0  
- Footprint set SCH == PCB  

### Fail examples
- Part on PCB missing from SCH (e.g. hand-dropped LEDs)
- U1 pad net changed on PCB but SCH still NC

---

## Step 2 — Footprint / pin-1 / polarity (paper + silk)

### Checklist
- [ ] `verify_orientation.py` OVERALL PASS
- [ ] Diode pad1=A pad2=K; TVS A=GND K=rail
- [ ] Electrolytic pin1 = `+`
- [ ] LQFP/SOIC pin1 orientation documented (U1 rot 0, pin1 NW)
- [ ] USB Micro-B mouth toward board edge (north)
- [ ] TMC EN west / VM east; jack pin1 = +V on field XH
- [ ] **Human:** print TOP/BOTTOM PDF 1:1; overlay real parts (paper test)

### Tools
```bash
python verify_orientation.py
# Human: File → Plot PDF 1:1 from pcbnew
```

### Pass criteria
- Orientation JSON: FAIL = 0  
- Silk shows ref + polarity cues for polarized parts  

---

## Step 3 — DRC = factory limits (JLCPCB)

### House rules (from `jlcpcb_limits.py`)
| Rule | House | JLC published min |
|------|-------|-------------------|
| Track / space | ≥ 0.15 mm | 0.10 mm |
| KiCad min track (project) | 0.20 mm | — |
| PTH annular | ≥ 0.18 mm | ~0.13–0.18 |
| Hole–hole (pads) | ≥ 0.45 mm | — |
| Copper–edge | ≥ 0.20 mm (KiCad 0.30) | 0.2 |
| +24V to other net | ≥ 0.40 mm | (0.10 not enough) |
| Via house | 0.4 / 0.8 mm | — |

### Checklist
- [ ] `verify_jlcpcb.py` overall PASS
- [ ] KiCad DRC fatal = 0: `shorting_items`, `clearance`, `unconnected_items`,
      `copper_edge_clearance`, `hole_clearance`, `annular_width`, `track_width`
- [ ] Prefer 45° routing (cosmetic; not auto-gated — visual/LLM sample tracks)
- [ ] No blind/buried vias

### Tools
```bash
python verify_jlcpcb.py
python verify_pre_fab.py   # includes kicad-cli DRC
```

### Pass criteria
- No overlapping pads of different nets  
- No courtyard collisions on SMT (+0.3 mm)  
- Unconnected = 0 **after** routing complete  

---

## Step 4 — Power & ground integrity (hardware proxy)

### Checklist
- [ ] Tree: `J1 → D3 → F1 → +24V ← D1` then PTC branches + buck (`verify_compact`)
- [ ] Decoupling: `C_MCU` 100n + `C_MCU2` 1u on +3V3; HF 100n near rails
- [ ] Bulk: C20/C21/C5/C3 present on MOT/24V/5V/3V3
- [ ] `verify_track_width.py` PASS (Power24 / Mot / 5V / 3V3)
- [ ] Zones: after edits, **Refill zones** in pcbnew (no orphan copper islands)
- [ ] TVS D1 on +24V, D5 on +5V; fail-safe R_PD_* on DO

### Tools
```bash
python verify_compact.py
python verify_track_width.py
# Human/LLM note: confirm zone refill in GUI after copper edits
```

### Pass criteria
- Compact power section OK  
- Track width gate PASS  
- No documented floating power pin on U1 VDD/VSS/VBAT/VREF+  

### Not required here
- Full SPICE PI / thermal FEM  

---

## Step 5 — Mechanical / 3D / enclosure

### Checklist
- [ ] 4× M3 NPTH H1–H4 present (`verify_jlcpcb`)
- [ ] SMT keep ≥ 2.5 mm from Edge.Cuts (jacks excluded)
- [ ] Tall parts (C20 Ø8, L1 6×6, F1 5×20, USB, XH) clearance vs lid — **human/CAD**
- [ ] Export STEP from pcbnew; drop into Fusion/FreeCAD housing if available
- [ ] Screw head keepout around H1–H4 (no thin tracks under washer)

### Tools
```bash
python verify_jlcpcb.py   # holes + edge clearance
# Human: pcbnew → File → Export → STEP
```

---

## Step 6 — Factory DFM upload (last insurance)

### Checklist
- [ ] `verify_pre_fab.py` OVERALL PASS
- [ ] Gerbers in `out/jlc_cam/` (F.Cu, B.Cu, Mask, Silk, Edge, drill, CPL)
- [ ] Note: **2-layer board** — no In1/In2; ignore “missing inner” if 2L
- [ ] Upload zip to JLCPCB → run **online DFM**
- [ ] Confirm outline, NPTH holes, no slivers; then pay

### Tools
```bash
python verify_pre_fab.py
# Upload out/jlc_cam/ at jlcpcb.com
```

---

## Extra gates (this repo)

| Gate | Script | BLOCKER? |
|------|--------|----------|
| SMT LCSC codes | `verify_jlc_bom.py` | Yes for SMT order |
| Field jack housing gap ≥5 mm | `verify_jlcpcb` warn | Warning (plug clash) |
| Fiducials | warn | Warning (JLC may add rails) |
| Silk &lt; 1 mm / silk overlap | cosmetic | No |

---

## Verdict vocabulary

| Tag | Meaning |
|-----|---------|
| **PASS** | Gate green |
| **FAIL / BLOCKER** | Must fix before order |
| **WARN** | Document; may order if accepted |
| **N/A** | Not applicable to this board |
| **HUMAN** | Needs eyes / paper / enclosure CAD |
| **WIP** | Known incomplete (e.g. unrouted LEDs) |

---

# Current review

**Date:** 2026-09-21  
**Board:** `STM32G030C8T6.kicad_pcb` 150×100 mm, 2L  
**Command:** `PYTHONUTF8=1 python verify_pre_fab.py`  
**Report:** `out/pre_fab_report.json`  
**Overall:** **FAIL — do not order**

### Step results

| Step | Result | Evidence |
|------|--------|----------|
| 1 SCH↔PCB | **FAIL / BLOCKER** | 16 LED/R on PCB missing from SCH; U1.21=`/LED_RUN`, U1.30=`/LED_ERR` not on SCH; fab G3/G4/G7 fail |
| 1 ERC SCH alone | **PASS** | `verify_schematic` ERC fatal=0 (pre-LED SCH) |
| 2 Footprint / polarity | **PASS** | `orientation_verify` OK=128 FAIL=0 |
| 2 Paper 1:1 | **HUMAN** | Not run this session |
| 3 DRC / JLCPCB | **FAIL / BLOCKER** | Pad overlaps + courtyard + shorts + unconnected |
| 4 Power / GND | **PASS** (core) | `verify_compact` + `verify_track_width` PASS; zone refill **HUMAN** after LED move |
| 5 Mechanical | **WARN** | 4×M3 OK; LED courtyard clash; STEP/housing **HUMAN** |
| 6 Factory DFM | **BLOCKED** | Do not upload until local gates green; CAM 2L OK (ignore In1/In2 fail) |

### DRC snapshot (fatal-relevant)

| Type | Count | Notes |
|------|------:|-------|
| shorting_items | 10 | LED pads vs L1 / SW_BOOT |
| unconnected_items | 21 | LED nets not routed (expected WIP) |
| schematic_parity_real | 18 | LED + U1 PB2/PC6 |
| clearance | 3 | fatal subset |
| hole_clearance | 1 | |
| courtyards_overlap | 13 | L1/SNS LEDs, SW_BOOT/STATUS, J_USB/D_LED24 |

### Pad overlap (must move parts)

```
L1.1 / R_LEDIN2.2, L1.1 / R_LEDIN3.2
L1.2 / D_LEDIN2.2, L1.2 / D_LEDIN3.2
SW_BOOT.2 / D_LED3V3.1, SW_BOOT.3 / D_LEDRUN.1
```

### Courtyard clashes (must move)

```
L1 ↔ R_LEDIN2, D_LEDIN2, R_LEDIN3, D_LEDIN3
J_USB ↔ D_LED24
SW_BOOT ↔ R_LED33, D_LED3V3, R_LEDRUN
```

### What already looks good (pre-LED / core board)

- ERC schematic logic, power tree J1→D3→F1→TVS, PTC branches  
- STM32 pinmap intent (TMC/opto/HMI/UART/boot)  
- Orientation diodes / electrolytics / USB / TMC / XH pin1  
- Track widths IPC for 24 V / Mot / 5 V / 3V3  
- JLCPCB envelope, drills, annular, 4× M3 NPTH  
- LCSC present for SMT including LED lines in `jlc_lcsc.csv`  

### BLOCKER list (order when all cleared)

1. Move STATUS + SNS LED/R clusters clear of L1, SW_BOOT, J_USB (courtyard ≥0.3 mm).  
2. Add same 8 LED + 8 R (+ nets `/LED_*`) to **schematic**; update PCB from SCH (or regen SCH from netlist).  
3. Hand-route all LED nets; DRC `unconnected_items` → 0.  
4. Refill GND/+rail zones; re-run DRC.  
5. `python verify_pre_fab.py` → overall PASS.  
6. Upload Gerber to JLCPCB online DFM; confirm; then order.

### WARN (non-blocking if accepted)

- North/south jack housing gaps &lt; 5 mm (plug clash risk)  
- No fiducials (JLC may add panel rails)  
- Dense silk / small text (cosmetic)  
- Gerber script “missing In1/In2” on **2-layer** board — ignore  

### N/A this product

- SI for DDR / USB3 / RF  
- Full PI thermal simulation  

---

## LLM output template (copy when re-reviewing)

```markdown
### Sign-off review — YYYY-MM-DD
Board: pcb/STM32G030C8T6/STM32G030C8T6.kicad_pcb
Command: python verify_pre_fab.py → overall: PASS|FAIL

| Step | Result | Notes |
|------|--------|-------|
| 1 SCH↔PCB | | |
| 2 Footprint/polarity | | |
| 3 DRC/JLCPCB | | |
| 4 Power/GND | | |
| 5 Mechanical | | |
| 6 Factory DFM | | |

BLOCKERS:
- ...

WARNINGS:
- ...

Order recommendation: YES / NO
```

---

## Related docs

- [JLCPCB_REVIEW.md](JLCPCB_REVIEW.md) — fab thresholds & upload steps  
- [BOM.md](BOM.md) — parts + LED table  
- [STM32_PINOUT.html](STM32_PINOUT.html) — pin / LED intent  
- [jlcpcb_limits.py](jlcpcb_limits.py) — numeric house limits  
- [verify_pre_fab.py](verify_pre_fab.py) — single gate script  
