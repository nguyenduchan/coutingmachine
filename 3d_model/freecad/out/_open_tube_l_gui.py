# -*- coding: utf-8 -*-
"""Rebuild all components + assembly, ViewFit, save GuiDocument."""
import sys
from pathlib import Path

_HERE = Path(r"D:\Project\coutingmachine\3d_model\freecad")
sys.path.insert(0, str(_HERE))

import FreeCAD as App
import FreeCADGui as Gui

from tube_l_components import build_component_assembly, print_summary, FCSTD

for name in list(App.listDocuments().keys()):
    App.closeDocument(name)

doc, info = build_component_assembly(9.0, 5.0, rebuild=True, save=True)
print_summary(info)
Gui.ActiveDocument = Gui.getDocument(doc.Name)
Gui.activeDocument().activeView().viewAxonometric()
Gui.SendMsgToActiveView("ViewFit")
Gui.updateGui()
doc.save()
print("OK", FCSTD)
