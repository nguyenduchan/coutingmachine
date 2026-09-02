"""Fast post-pass: connect open copper islands without full re-autoroute."""
from __future__ import annotations

import uuid
from pathlib import Path

from maze_router import repair_open_pcb

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
OX, OY = 35.0, 30.0
BW, BH = 190.0, 160.0


def main() -> None:
    text = PCB.read_text(encoding="utf-8")
    total = 0
    for rnd in range(1, 6):
        text, result = repair_open_pcb(
            text, OX, OY, BW, BH, grid=0.55, uid_fn=lambda: str(uuid.uuid4())
        )
        added = len(result.segments)
        total += added
        print(f"Round {rnd}: +{added} segments, {len(result.failed)} failed")
        if added == 0:
            break
    PCB.write_text(text, encoding="utf-8")
    print(f"Wrote {PCB} (+{total} repair segments total)")
    for net, name, axy, bxy in result.failed[:20]:
        print(f"  FAIL net {net} {name} {axy} -> {bxy}")


if __name__ == "__main__":
    main()
