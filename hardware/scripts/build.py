"""Rebuild everything from circuit.py, then run every check. Usage: python scripts/build.py"""
import subprocess
import sys

import env

PY, KPY = sys.executable, str(env.KICAD_PY)
STEPS = [
    (PY, "scripts/gen_symlib.py"),
    (PY, "scripts/gen_sch.py"),
    (KPY, "scripts/gen_pcb.py"),
    (KPY, "scripts/route.py"),
    (PY, "scripts/export.py"),
    (PY, "scripts/films.py"),
    (PY, "tests/test_libs.py"),
    (PY, "tests/test_circuit.py"),
    (KPY, "tests/test_pcb.py"),
    (PY, "tests/test_outputs.py"),
]


def check(cmd, report, marker):
    subprocess.run([str(env.KICAD_CLI), *cmd, "--severity-all", "-o", str(report)], check=True, capture_output=True)
    text = report.read_text(encoding="utf-8")
    assert all(m in text for m in marker), f"{report.name} not clean:\n{text[-1500:]}"
    print(f"{report.name}: clean")


def main():
    for exe, script in STEPS:
        print(f"== {script}", flush=True)
        r = subprocess.run([exe, script], cwd=env.HW, capture_output=True, text=True)
        out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                        if "image handler" not in l and "memory leak" not in l and "jenkins" not in l)
        print(out.strip())
        if r.returncode:
            sys.exit(f"FAILED: {script}")
    check(["sch", "erc", str(env.HW / "timer.kicad_sch")], env.OUT / "erc.rpt", ["Errors 0  Warnings 0"])
    check(["pcb", "drc", "--schematic-parity", str(env.HW / "timer.kicad_pcb")], env.OUT / "drc.rpt",
          ["Found 0 DRC violations", "Found 0 unconnected pads", "Found 0 Footprint errors"])
    print("BUILD OK")


if __name__ == "__main__":
    main()
