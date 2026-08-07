import json, sys, traceback
from pathlib import Path
log = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\verify_log.txt")
try:
    sys.path.insert(0, r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
    import l_flap_divert as C
    lines = ["import ok", "OPEN_HI %.2f" % C.OPEN_LARGE_HI]
    for op in [C.OPEN_SMALL_LO, 3.0, C.OPEN_SMALL_HI, C.OPEN_LARGE_LO, C.OPEN_LARGE_HI]:
        lines.append("open %.2f %s" % (op, C.aperture_widths(op)))
    report = C.verify_mechanism()
    Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad\out\l_flap_divert_verify.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    lines.append("pass=%s max_ov=%.3f width_progress=%s" % (report["pass"], report["max_overlap_mm3"], report["width_progress"]))
    for s in report["samples"]:
        lines.append("sample %s" % s)
    log.write_text("\n".join(lines), encoding="utf-8")
except Exception:
    log.write_text(traceback.format_exc(), encoding="utf-8")
