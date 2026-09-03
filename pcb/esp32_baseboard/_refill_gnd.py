#!/usr/bin/env python3
"""Add+fill the F.Cu/B.Cu GND pour on esp32_baseboard.kicad_pcb.

Standalone, run in its own fresh pcbnew process. route_freerouting.py's
fill_gnd_zones() crashes when called right after ExportSpecctraDSN /
ImportSpecctraSES in the SAME process (KiCad10 pcbnew loses the BOARD type
on that object -- documented in PCB_REVIEW.md A9). A brand-new LoadBoard()
in a separate process never touches Specctra, so it keeps a real BOARD type.
"""
import pcbnew

PCB = "esp32_baseboard.kicad_pcb"

board = pcbnew.LoadBoard(PCB)
net = board.FindNet("GND")
if net is None or net.GetNetCode() <= 0:
    raise SystemExit("GND net missing")

bbox = board.GetBoardEdgesBoundingBox()
margin = pcbnew.FromMM(0.5)
x0, y0 = bbox.GetLeft() + margin, bbox.GetTop() + margin
x1, y1 = bbox.GetRight() - margin, bbox.GetBottom() - margin

added = 0
for layer_name, layer_id, prio in (("B.Cu", pcbnew.B_Cu, 0), ("F.Cu", pcbnew.F_Cu, 1)):
    zone = pcbnew.ZONE(board)
    zone.SetNetCode(net.GetNetCode())
    zone.SetLayer(layer_id)
    zone.SetAssignedPriority(prio)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetLocalClearance(pcbnew.FromMM(0.35))
    zone.SetMinThickness(pcbnew.FromMM(0.25))
    zone.SetThermalReliefGap(pcbnew.FromMM(0.5))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    zone.SetIsFilled(False)
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        chain.Append(pcbnew.VECTOR2I(x, y))
    chain.SetClosed(True)
    zone.Outline().AddOutline(chain)
    board.Add(zone)
    added += 1

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(list(board.Zones()))
pcbnew.SaveBoard(PCB, board)
print(f"added {added} zone(s), filled, saved -> {PCB}")
