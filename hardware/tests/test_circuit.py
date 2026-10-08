"""Netlist rules for circuit.py, including the firmware pin map from Final/5-26.c."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from circuit import PARTS, NETS, NETCLASS, DISP_PIN  # noqa: E402

# Firmware pin map, parsed from the #defines in Final/5-26.c (macro -> net in circuit.py)
FW_MACRO_NET = {"RELAY": "RELAY", "B_SET": "KEY_SET", "B_STP": "KEY_STOP", "B_STA": "KEY_START",
                "D1": "DRV1", "D2": "DRV2", "D3": "DRV3", "DL": "DRVL",
                "SA": "SEG_A", "SB": "SEG_B", "SC": "SEG_C", "SD": "SEG_D", "SE": "SEG_E",
                "SF": "SEG_F", "SG": "SEG_G", "SDP": "SEG_DP"}
FIRMWARE = Path(__file__).resolve().parents[2] / "Final" / "5-26.c"


def firmware_pins():
    import re
    defs = {m: (a, b) for m, a, b in re.findall(r"^#define\s+(\w+)\s+P(\d)(\d)\s", FIRMWARE.read_text(encoding="utf-8"), re.M)}
    found = {m: f"P{p[0]}.{p[1]}" for m, p in ((m, defs[m]) for m in defs if m in FW_MACRO_NET)}
    assert set(found) == set(FW_MACRO_NET), set(FW_MACRO_NET) ^ set(found)
    return {FW_MACRO_NET[m]: pin for m, pin in found.items()} | {"ICE_DAT": "P1.6"}


FW = firmware_pins()

# Component ratings (datasheet values) for the parts circuit.py may choose
VCEO = {"SS8050": 25, "BC817-40": 45, "MMBTA06": 80}
VRRM = {"SS34": 40, "SS36": 60, "SS310": 100}
TVS = {"SMBJ28CA": (28.0, 45.4), "SMBJ33CA": (33.0, 53.3)}  # (standoff, max clamp)
VIN_MAX = 24 * 1.1  # 24 V rail +10 %


def test_firmware_pins():
    for net, pin in FW.items():
        assert ("U1", pin) in NETS[net], (net, pin)


def test_no_pin_on_two_nets_and_no_single_pin_nets():
    seen = set()
    for net, pins in NETS.items():
        assert len(pins) >= 2, net
        for p in pins:
            assert p[0] in PARTS, p
            assert p not in seen, ("pin on two nets", p)
            seen.add(p)


def test_display_mapping():
    for i, s in enumerate("A B C D E F G DP".split()):
        r = f"R{i + 1}"
        assert (r, "1") in NETS[f"SEG_{s}"], s
        assert (r, "2") in NETS[f"SEG_{s}_D"] and ("U3", DISP_PIN[s]) in NETS[f"SEG_{s}_D"], s
    for i in (1, 2, 3):
        assert ("U3", f"CA{i}") in NETS[f"DIG{i}"]
    # LED indicators on the DL group (spec): SEC=A, MIN=C, SET=F, ON/OFF=B
    for led, seg in (("LED1", "A"), ("LED2", "C"), ("LED3", "F"), ("LED4", "B")):
        assert (led, "K") in NETS[f"SEG_{seg}_D"] and (led, "A") in NETS["LED_COM"]


def test_reverse_polarity_path():
    # Unprotected input: terminal, TVS (clamps before D1), protection diode anode, relay COM
    assert sorted(NETS["VIN_RAW"]) == sorted([("J1", "1"), ("D2", "1"), ("D1", "A"), ("K1", "1")])  # K1.1 = COM
    assert ("D2", "2") in NETS["GND"]
    assert ("D1", "K") in NETS["VIN"] and ("U2", "VI") in NETS["VIN"]
    assert NETCLASS["VIN_RAW"] == NETCLASS["OUT_P"] == "Load"


def test_voltage_ratings():
    standoff, clamp = TVS[PARTS["D2"].value]
    assert standoff >= VIN_MAX, "TVS conducts on a normal supply"
    assert VRRM[PARTS["D1"].value] >= clamp, "D1 not rated for the TVS clamp voltage"
    assert VCEO[PARTS["Q5"].value] >= clamp, "relay driver not rated for the TVS clamp voltage"


def test_relay_driver():
    assert ("U1", "P0.7") in NETS["RELAY"] and ("R13", "1") in NETS["RELAY"]
    assert {("R13", "2"), ("R14", "1"), ("Q5", "B")} <= set(NETS["RLY_B"])
    assert {("Q5", "C"), ("D3", "A")} <= set(NETS["RLY_COIL"]) and ("D3", "K") in NETS["VIN"]
    assert sorted(NETS["OUT_P"]) == sorted([("K1", "3"), ("J1", "3")])  # K1.3 = NO


def test_schematic_netlist_matches_circuit():
    """KiCad's own netlist of timer.kicad_sch must equal circuit.NETS (pin names resolved)."""
    import subprocess, tempfile
    import env
    from sexpr import parse, find, first
    from symlib import resolve
    sch = env.HW / "timer.kicad_sch"
    if not sch.exists():
        raise AssertionError("timer.kicad_sch missing: run scripts/gen_sch.py")
    out = Path(tempfile.gettempdir()) / "timer_netlist.net"
    subprocess.run([str(env.KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(out), str(sch)], check=True, capture_output=True)
    got = {}
    for n in find(first(parse(out.read_text(encoding="utf-8")), "nets"), "net"):
        nodes = {(first(x, "ref")[1], first(x, "pin")[1]) for x in find(n, "node")}
        got[first(n, "name")[1].lstrip("/")] = {x for x in nodes if not x[0].startswith("#")}
    want = {net: {(r, num) for r, p in refs for num in resolve(PARTS[r].lib_id, p)} for net, refs in NETS.items()}
    got = {k: v for k, v in got.items() if not k.startswith("unconnected-")}
    assert got == want, {k: (got.get(k), want.get(k)) for k in set(got) | set(want) if got.get(k) != want.get(k)}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
