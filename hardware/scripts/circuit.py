"""Single source of truth for the CYTM timer board: parts, nets, placement.

Coordinates: centre of the footprint courtyard in mm from the board's top-left corner,
seen from the FRONT (panel side); rot in degrees, applied before flipping to the back.
Side "F" = front (panel side, display/keys/LEDs/terminal), "B" = back.
Pins: pin number ("1") or pin name ("P0.7", "K", "COM"); names resolve against
the KiCad symbol, so the netlist reads like the datasheet.
"""
from collections import namedtuple

Part = namedtuple("Part", "lib_id value footprint side x y rot")

BOARD_W, BOARD_H = 50.0, 80.0

R0805 = "Resistor_SMD:R_0805_2012Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"

PARTS = {
    # --- MCU (back, between the display pin rows) -----------------------------
    "U1": Part("timer:MG51FB9AE", "MG51FB9AE", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm", "B", 25, 20, 0),
    "C4": Part("Device:C", "100nF 50V X7R", C0805, "B", 27.5, 25.3, 0),  # next to VDD/VSS (pins 9/7)
    "C5": Part("Device:C", "10uF 16V X5R", C0805, "B", 23, 25.3, 0),
    "R15": Part("Device:R", "10k", R0805, "B", 19, 15, 0),
    "J2": Part("Connector_Generic:Conn_01x05", "PinHeader 1x5 2.54mm (ICP)", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
               "B", 3, 19.08, 0),
    # --- Power ---------------------------------------------------------------
    "J1": Part("Connector:Screw_Terminal_01x04", "MKDS 1,5/4-5,08",
               "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal", "F", 25, 73.6, 0),
    "D1": Part("Diode:SS36", "SS36", "Diode_SMD:D_SMA", "B", 30, 65, 0),  # 60 V > TVS clamp
    "D2": Part("Device:D_TVS", "SMBJ28CA", "Diode_SMD:D_SMB", "B", 36, 69.6, 90),  # on raw input, before D1
    "C1": Part("Device:C_Polarized", "100uF 50V", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", "B", 44, 63, 0),
    "C2": Part("Device:C", "10uF 50V X7R", "Capacitor_SMD:C_1206_3216Metric", "B", 37, 63.5, 0),
    "U2": Part("Regulator_Linear:LM78M05_TO252", "L78M05ABDT", "Package_TO_SOT_SMD:TO-252-2", "B", 31, 57, 0),
    "C3": Part("Device:C", "10uF 16V X5R", C0805, "B", 38.6, 57.2, 90),
    # --- Relay ---------------------------------------------------------------
    "K1": Part("Relay:SANYOU_SRD_Form_C", "SRD-24VDC-SL-C", "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C",
               "B", 12.5, 60.5, 0),
    "Q5": Part("Transistor_BJT:MMBTA06", "MMBTA06", SOT23, "B", 6, 47, 0),  # Vceo 80 V > TVS clamp
    "R13": Part("Device:R", "1k", R0805, "B", 11, 45, 0),
    "R14": Part("Device:R", "10k", R0805, "B", 11, 48.5, 0),
    "D3": Part("Diode:1N4148W", "1N4148W", "Diode_SMD:D_SOD-123", "B", 16.5, 47, 0),
    # --- Display (front) and its drivers (back) -------------------------------
    "U3": Part("timer:BA56-12EWA", "BA56-12EWA", "timer:Display_3Digit_0.56in_CA", "F", 25, 20, 90),
    # rot 180: pad 2 (display side) faces the display; x=8 leaves an 8 mm routing channel
    **{f"R{i}": Part("Device:R", "330", R0805, "B", 8, round(12.5 + 2.8 * (i - 1), 2), 180) for i in range(1, 9)},
    # rot 180: base resistor pad 2 faces the transistor's B/E side -> straight base link
    **{f"R{i}": Part("Device:R", "1k", R0805, "B", 38, 13.5 + 4.5 * (i - 9), 180) for i in range(9, 13)},
    **{f"Q{i}": Part("Transistor_BJT:SS8050", "SS8050", SOT23, "B", 44, 13.5 + 4.5 * (i - 1), 180) for i in range(1, 5)},
    "LED1": Part("Device:LED", "LED 3mm red", "LED_THT:LED_D3.0mm", "F", 11.5, 6, 0),
    "LED2": Part("Device:LED", "LED 3mm red", "LED_THT:LED_D3.0mm", "F", 20.5, 6, 0),
    "LED3": Part("Device:LED", "LED 3mm red", "LED_THT:LED_D3.0mm", "F", 29.5, 6, 0),
    "LED4": Part("Device:LED", "LED 3mm green", "LED_THT:LED_D3.0mm", "F", 38.5, 6, 0),
    # --- Keys (front) ----------------------------------------------------------
    "SW1": Part("Switch:SW_Push", "Tact 6x6x5mm", "Button_Switch_THT:SW_PUSH_6mm", "F", 25, 47, 0),
    "SW2": Part("Switch:SW_Push", "Tact 6x6x5mm", "Button_Switch_THT:SW_PUSH_6mm", "F", 38, 38, 0),
    "SW3": Part("Switch:SW_Push", "Tact 6x6x5mm", "Button_Switch_THT:SW_PUSH_6mm", "F", 12, 38, 0),
    # --- Mechanical ----------------------------------------------------------
    **{f"H{i}": Part("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", "F", x, y, 0)
       for i, (x, y) in enumerate(((4, 4), (46, 4), (4, 76), (46, 76)), 1)},
}

# Front-panel labels (silkscreen, front): text, x, y
FRONT_TEXT = [("SEC", 11.5, 2.2), ("MIN", 20.5, 2.2), ("SET", 29.5, 2.2), ("ON/OFF", 38.5, 2.2),
              ("STOP", 12, 43.4), ("START", 38, 43.4), ("SET", 25, 52.4)]
BACK_TEXT = [("CYTM V5  H&D", 25, 33.2), ("2026-10  REV A", 25, 35.2)]

SEGS = "A B C D E F G DP".split()
SEG_PIN = dict(zip(SEGS, ("P0.0", "P0.2", "P0.5", "P1.2", "P1.1", "P0.1", "P1.4", "P1.3")))
DISP_PIN = {s: s.lower() for s in SEGS} | {"DP": "DPX"}  # BA56-12EWA symbol pin names
LED_SEG = {"LED1": "A", "LED2": "C", "LED3": "F", "LED4": "B"}  # SEC, MIN, SET, ON/OFF

NETS = {
    "VIN_RAW": [("J1", "1"), ("D2", "1"), ("D1", "A"), ("K1", "1")],  # K1.1 = COM; TVS clamps before D1
    "OUT_P": [("K1", "3"), ("J1", "3")],  # K1.3 = NO
    "VIN": [("D1", "K"), ("C1", "1"), ("C2", "1"), ("U2", "VI"), ("K1", "5"), ("D3", "K")],
    "+5V": [("U2", "VO"), ("C3", "1"), ("C4", "1"), ("C5", "1"), ("U1", "VDD"), ("R15", "2"), ("J2", "1"),
            ("Q1", "C"), ("Q2", "C"), ("Q3", "C"), ("Q4", "C")],
    "GND": [("J1", "2"), ("J1", "4"), ("D2", "2"), ("C1", "2"), ("C2", "2"), ("U2", "GND"), ("C3", "2"),
            ("C4", "2"), ("C5", "2"), ("U1", "VSS"), ("J2", "5"), ("Q5", "E"), ("R14", "2"),
            ("SW1", "2"), ("SW2", "2"), ("SW3", "2")],
    # Relay driver (K1 SRD Form C: 1=COM, 3=NO, 4=NC, 2/5=coil)
    "RELAY": [("U1", "P0.7"), ("R13", "1")],
    "RLY_B": [("R13", "2"), ("R14", "1"), ("Q5", "B")],
    "RLY_COIL": [("Q5", "C"), ("K1", "2"), ("D3", "A")],
    # Keys + programming
    "KEY_SET": [("U1", "P1.7"), ("SW1", "1")],
    "KEY_START": [("U1", "P2.0"), ("SW2", "1"), ("R15", "1"), ("J2", "4")],
    "KEY_STOP": [("U1", "P3.0"), ("SW3", "1")],
    "ICE_DAT": [("U1", "P1.6"), ("J2", "2")],
    # Digit drivers: emitter followers, pin high = digit on (firmware polarity)
    "DRV1": [("U1", "P1.0"), ("R9", "1")],
    "DRV2": [("U1", "P0.3"), ("R10", "1")],
    "DRV3": [("U1", "P0.4"), ("R11", "1")],
    "DRVL": [("U1", "P0.6"), ("R12", "1")],
    **{f"BASE{i}": [(f"R{8 + i}", "2"), (f"Q{i}", "B")] for i in range(1, 5)},
    "DIG1": [("Q1", "E"), ("U3", "CA1")],
    "DIG2": [("Q2", "E"), ("U3", "CA2")],
    "DIG3": [("Q3", "E"), ("U3", "CA3")],
    "LED_COM": [("Q4", "E")] + [(led, "A") for led in LED_SEG],
}
# Segments: MCU pin -> 330R -> display segment (+ indicator LED cathodes)
for i, s in enumerate(SEGS, 1):
    NETS[f"SEG_{s}"] = [("U1", SEG_PIN[s]), (f"R{i}", "1")]
    NETS[f"SEG_{s}_D"] = [(f"R{i}", "2"), ("U3", DISP_PIN[s])] + [(led, "K") for led, seg in LED_SEG.items() if seg == s]
NETS["SEG_B"].append(("J2", "3"))  # ICE_CLK shares P0.2

NETCLASS = {"VIN_RAW": "Load", "OUT_P": "Load", "VIN": "Power", "+5V": "Power", "GND": "Power"}
