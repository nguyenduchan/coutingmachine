import re
import zipfile
from pathlib import Path

p = Path(r"d:\Project\coutingmachine\3d_model\freecad\out\jgb37_motor_bracket.FCStd")
with zipfile.ZipFile(p) as z:
    xml = z.read("Document.xml").decode("utf-8", "replace")
for name in ["Exit_Guide_Tray", "Gap_Lining_Up"]:
    m = re.search(r'<Object name="%s"[^>]*>.*?</Object>' % name, xml, re.S)
    pm = re.search(
        r'<Property name="Placement"[^>]*>\s*<PropertyPlacement\s+([^/]+)/>',
        m.group(0),
    )
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(1)))
    print(name, float(attrs["Px"]), float(attrs["Py"]), float(attrs["Pz"]))
print("Exit tray children:")
for t, n in re.findall(r'<Object type="([^"]+)" name="([^"]+)"', xml):
    if n.startswith("Exit_Tray") or n == "Exit_Guide_Tray":
        print(" ", n)
