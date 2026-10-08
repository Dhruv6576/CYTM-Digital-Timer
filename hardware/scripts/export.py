"""Fabrication + documentation outputs into hardware/output/.

gerbers.zip (Gerber X2 + Excellon), bom.csv, positions.csv, schematic.pdf, render_top/bottom/iso.png
"""
import shutil
import subprocess
import zipfile

import env

PCB = str(env.HW / "timer.kicad_pcb")
SCH = str(env.HW / "timer.kicad_sch")
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def cli(*args):
    r = subprocess.run([str(env.KICAD_CLI), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"kicad-cli {' '.join(args)}\n{r.stdout}\n{r.stderr}")


def main():
    out = env.OUT
    gdir = out / "gerbers"
    shutil.rmtree(gdir, ignore_errors=True)
    gdir.mkdir(parents=True)
    cli("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "-o", str(gdir), PCB)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--excellon-separate-th",
        "--drill-origin", "plot", "--generate-map", "--map-format", "pdf", "-o", str(gdir) + "/", PCB)
    with zipfile.ZipFile(out / "gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.iterdir()):
            if f.suffix != ".pdf":
                z.write(f, f.name)
    cli("sch", "export", "bom", "--fields", "Reference,Value,Footprint,QUANTITY",
        "--labels", "Refs,Value,Footprint,Qty", "--group-by", "Value,Footprint", "--ref-range-delimiter", "",
        "--exclude-dnp", "-o", str(out / "bom.csv"), SCH)
    cli("pcb", "export", "pos", "--side", "both", "--format", "csv", "--units", "mm", "--use-drill-file-origin",
        "-o", str(out / "positions.csv"), PCB)
    cli("sch", "export", "pdf", "-o", str(out / "schematic.pdf"), SCH)
    for side in ("top", "bottom"):
        cli("pcb", "render", "--side", side, "--quality", "high", "--width", "1400", "--height", "2100",
            "--background", "opaque", "-o", str(out / f"render_{side}.png"), PCB)
    cli("pcb", "render", "--side", "top", "--quality", "high", "--width", "1800", "--height", "1400",
        "--rotate", "-40,0,30", "--perspective", "--background", "opaque", "-o", str(out / "render_iso.png"), PCB)
    print("exported to", out)


if __name__ == "__main__":
    main()
