"""Every symbol/footprint in circuit.py exists in KiCad 10, and every net pin resolves."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import env  # noqa: E402
from circuit import PARTS, NETS  # noqa: E402
from symlib import pins, resolve  # noqa: E402

# Assumed MG51FB9AE TSSOP-20 pinout (same as N76E003AT20). Verify against the Nuvoton datasheet.
EXPECT_MCU = {"1": "P0.5", "2": "P0.6", "3": "P0.7", "4": "P2.0", "5": "P3.0", "6": "P1.7", "7": "VSS",
              "8": "P1.6", "9": "VDD", "10": "P1.5", "11": "P1.4", "12": "P1.3", "13": "P1.2", "14": "P1.1",
              "15": "P1.0", "16": "P0.0", "17": "P0.1", "18": "P0.2", "19": "P0.3", "20": "P0.4"}


def test_symbols_and_footprints_exist():
    for ref, p in PARTS.items():
        assert pins(p.lib_id) or p.lib_id.startswith("Mechanical:"), ref
        lib, name = p.footprint.split(":")
        base = env.HW if lib == "timer" else env.FP_DIR
        assert (base / f"{lib}.pretty" / f"{name}.kicad_mod").exists(), (ref, p.footprint)


def test_mcu_pinout():
    got = {p["number"]: p["name"].split("/")[0] for p in pins(PARTS["U1"].lib_id)}
    assert got == EXPECT_MCU, got


def test_every_net_pin_resolves():
    for net, refs in NETS.items():
        for ref, pin in refs:
            resolve(PARTS[ref].lib_id, pin)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
