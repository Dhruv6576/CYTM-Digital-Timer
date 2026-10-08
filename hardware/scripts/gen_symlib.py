"""Project libraries (parts missing from KiCad's stock libraries):
- timer.kicad_sym: MG51FB9AE MCU, BA56-12EWA 3-digit 0.56" common-anode display
- timer.pretty: Display_3Digit_0.56in_CA footprint (37.8 x 19 mm body, 12 pins)

ASSUMED pinout = N76E003AT20 / MS51FB9AE TSSOP-20. Verify against the Nuvoton MG51 datasheet.
"""
import copy

import env
from sexpr import Q, dump, find, first, parse
from symlib import symbol

STOCK_FP = env.FP_DIR / "Display_7Segment.pretty" / "CA56-12EWA.kicad_mod"

NAME = "MG51FB9AE"
# (pin number, name, side) - left: port 0 + P2.0 + P3.0, right: port 1
PINS = [("16", "P0.0"), ("17", "P0.1"), ("18", "P0.2/ICE_CLK"), ("19", "P0.3"), ("20", "P0.4"),
        ("1", "P0.5"), ("2", "P0.6"), ("3", "P0.7"), ("4", "P2.0/nRST"), ("5", "P3.0")]
RIGHT = [("15", "P1.0"), ("14", "P1.1"), ("13", "P1.2"), ("12", "P1.3"), ("11", "P1.4"),
         ("10", "P1.5"), ("8", "P1.6/ICE_DAT"), ("6", "P1.7")]


def eff(hide=False):
    e = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        e.append(["hide", "yes"])
    return e


def pin(kind, x, y, ang, name, num):
    return ["pin", kind, "line", ["at", x, y, ang], ["length", 5.08],
            ["name", Q(name), eff()], ["number", Q(num), eff()]]


def display_symbol():
    """BA56-12EWA: CA56-12EWA pinout with digit 4 removed; pin 6 (CA4) is NC on 3-digit parts."""
    sym = copy.deepcopy(symbol("Display_Character:CA56-12EWA"))
    sym[1] = Q("BA56-12EWA")
    for prop in find(sym, "property"):
        if prop[1] == "Value":
            prop[2] = Q("BA56-12EWA")
        elif prop[1] == "Footprint":
            prop[2] = Q("timer:Display_3Digit_0.56in_CA")
        elif prop[1] == "Description":
            prop[2] = Q("3 digit 0.56in 7 segment common anode LED display (pin 6 NC)")
        elif prop[1] == "ki_fp_filters":
            prop[2] = Q("*3Digit*0.56in*CA*")
    for unit in find(sym, "symbol"):
        unit[1] = Q("BA56-12EWA" + unit[1][len("CA56-12EWA"):])
        keep = unit[:2]
        for g in unit[2:]:
            if isinstance(g, list) and g[0] == "polyline":
                if min(float(xy[1]) for xy in find(first(g, "pts"), "xy")) > 11:
                    continue  # digit 4 segments
            if isinstance(g, list) and g[0] == "text" and g[1] == "DP4":
                continue
            if isinstance(g, list) and g[0] == "circle" and float(first(g, "center")[1]) > 15:
                continue  # DP4 dot
            if isinstance(g, list) and g[0] == "pin" and first(g, "number")[1] == "6":
                g[1] = "no_connect"
                first(g, "name")[1] = Q("NC")
            keep.append(g)
        unit[:] = keep
    return sym


def display_model():
    """VRML body for the 3-digit display: dark 19 x 37.8 x 8 mm block with three red '8.' digits.

    Footprint frame: pin 1 at origin, pins 1-6 along +Y, digit tops toward +X.
    KiCad VRML unit = 0.1 inch; VRML Y = -footprint Y.
    """
    u = 1 / 2.54
    boxes = [((7.62, 6.35, 4.0), (19.0, 37.8, 8.0), (0.12, 0.12, 0.13))]
    seg, red = 1.1, (0.95, 0.08, 0.05)
    for dy in (-12.6, 0.0, 12.6):
        cx, cy = 7.62, 6.35 + dy
        for x in (cx + 6.2, cx, cx - 6.2):                      # a, g, d (horizontal bars along digit width)
            boxes.append(((x, cy, 8.02), (seg, 5.0, 0.05), red))
        for sx in (3.1, -3.1):                                  # f/b (upper) and e/c (lower) vertical bars
            for sy in (-2.9, 2.9):
                boxes.append(((cx + sx, cy + sy, 8.02), (5.6, seg, 0.05), red))
        boxes.append(((cx - 6.2, cy + 4.6, 8.02), (seg, seg, 0.05), red))  # DP
    nodes = []
    for (x, y, z), (sx, sy, sz), (r, g, b) in boxes:
        nodes.append(f"Transform {{ translation {x*u:.4f} {-y*u:.4f} {z*u:.4f} children [ Shape {{ "
                     f"appearance Appearance {{ material Material {{ diffuseColor {r} {g} {b} }} }} "
                     f"geometry Box {{ size {sx*u:.4f} {sy*u:.4f} {sz*u:.4f} }} }} ] }}")
    out = env.HW / "timer.3dshapes"
    out.mkdir(exist_ok=True)
    (out / "Display_3Digit_0.56in_CA.wrl").write_text("#VRML V2.0 utf8\n" + "\n".join(nodes) + "\n", encoding="utf-8")


def display_footprint():
    """3-digit 0.56in CA: same pads as CA56-12EWA, body 37.8 mm instead of 50.4 mm."""
    t = parse(STOCK_FP.read_text(encoding="utf-8"))
    t[1] = Q("Display_3Digit_0.56in_CA")
    first(t, "descr")[1] = Q("3 digit 0.56in 7 segment common anode LED display, 37.8x19mm, e.g. Kingbright BA56-12EWA")
    for prop in find(t, "property"):
        if prop[1] == "Value":
            prop[2] = Q("Display_3Digit_0.56in_CA")
    # Body is centred on the pad array (y = 6.35); 4-digit outline y -18.9..31.6 -> 3-digit -12.55..25.25
    shrink = {"-18.92": "-12.6", "31.62": "25.3", "-19.05": "-12.75", "31.75": "25.45", "-18.8": "-12.55", "31.5": "25.25"}
    for ln in find(t, "fp_line"):
        for key in ("start", "end"):
            pt = first(ln, key)
            pt[2] = shrink.get(pt[2], pt[2])
    model = first(t, "model")
    model[1] = Q("${KIPRJMOD}/timer.3dshapes/Display_3Digit_0.56in_CA.wrl")
    first(model, "offset")[1][1:4] = ["0", "0", "0"]
    first(model, "scale")[1][1:4] = ["1", "1", "1"]
    display_model()
    out = env.HW / "timer.pretty"
    out.mkdir(exist_ok=True)
    (out / "Display_3Digit_0.56in_CA.kicad_mod").write_text(dump(t) + "\n", encoding="utf-8")


def main():
    body = ["symbol", Q(f"{NAME}_0_1"),
            ["rectangle", ["start", -10.16, 13.97], ["end", 10.16, -13.97],
             ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]]
    pins = ["symbol", Q(f"{NAME}_1_1")]
    for i, (num, name) in enumerate(PINS):
        pins.append(pin("bidirectional", -15.24, round(11.43 - 2.54 * i, 2), 0, name, num))
    for i, (num, name) in enumerate(RIGHT):
        pins.append(pin("bidirectional", 15.24, round(8.89 - 2.54 * i, 2), 180, name, num))
    pins.append(pin("power_in", 0, 19.05, 270, "VDD", "9"))
    pins.append(pin("power_in", 0, -19.05, 90, "VSS", "7"))
    sym = ["symbol", Q(NAME), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"],
           ["in_bom", "yes"], ["on_board", "yes"],
           ["property", Q("Reference"), Q("U"), ["at", -10.16, 15.24, 0], eff()],
           ["property", Q("Value"), Q(NAME), ["at", 2.54, 15.24, 0], eff()],
           ["property", Q("Footprint"), Q("Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"), ["at", 0, 0, 0], eff(True)],
           ["property", Q("Datasheet"), Q("https://www.nuvoton.com/products/microcontrollers/8bit-8051-mcus/"),
            ["at", 0, 0, 0], eff(True)],
           ["property", Q("Description"), Q("Nuvoton MG51 1T 8051 MCU, 16KB flash, TSSOP-20 (pinout assumed = N76E003)"),
            ["at", 0, 0, 0], eff(True)],
           body, pins]
    lib = ["kicad_symbol_lib", ["version", "20241209"], ["generator", Q("timer_gen")], sym, display_symbol()]
    display_footprint()
    (env.HW / "timer.kicad_sym").write_text(dump(lib) + "\n", encoding="utf-8")
    (env.HW / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "timer")(type "KiCad")(uri "${KIPRJMOD}/timer.kicad_sym")(options "")(descr "Project symbols"))\n)\n',
        encoding="utf-8")
    (env.HW / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "timer")(type "KiCad")(uri "${KIPRJMOD}/timer.pretty")(options "")(descr "Project footprints"))\n)\n',
        encoding="utf-8")
    print("wrote timer.kicad_sym, timer.pretty")


if __name__ == "__main__":
    main()
