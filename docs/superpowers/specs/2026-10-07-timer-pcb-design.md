# CYTM Digital Timer PCB — Design Spec

Date: 2026-10-07
Status: Prototype (capability test, not final product)

## Goal

A from-scratch PCB for a commercial 24 VDC cyclic relay timer. The board runs the existing
firmware (`Final/5-26.c`) without changes to its pin map. The output is a manufacturable
KiCad project with Gerbers, BOM and printable films.

## What the user said vs. what is assumed

Said:
- Commercial cyclic timer, designed from scratch, not a copy of CYTM_V4.
- 24 VDC input, 24 VDC switched output (front panel photo).
- Board fits the existing white enclosure; exact dimensions may be assumed.
- This is a test of capability, not the final product.

Assumed:
- Board 50 × 80 mm portrait, 4 × M3 corner holes.
- MG51FB9AE TSSOP-20 pinout equals N76E003 / MS51FB9AE TSSOP-20 (verify before production).
- 0.56" 3-digit common-anode display, generic 12-pin footprint (verify before production).
- 2-layer board for the prototype; single-sided version is a later task.
- Output rated 5 A.

## Front layout (component side, top to bottom)

1. 4 × 3 mm LEDs in a row: SEC, MIN, SET, ON/OFF.
2. 3-digit 0.56" display, centered.
3. STOP (left) and START (right) 6×6 mm tactile switches; SET centered below them.
4. 4-way 5.08 mm screw terminal on the bottom edge: IN+, IN−, OUT+, OUT−.

## Circuit

### Power input
- J1 screw terminal: IN+, IN−, OUT+, OUT−.
- D1 SS34 (SMA) series diode: reverse-polarity protection for the logic and relay coil.
- D2 SMBJ33A TVS across the protected rail: surge clamp.
- C1 100 µF / 50 V electrolytic bulk capacitor.
- U2 L78M05 (DPAK) linear regulator, 24 V → 5 V, with C2 10 µF input and C3 10 µF output
  ceramics. Tab sits on a copper pour for heat (about 0.9 W worst case).

### Relay output
- K1 Songle SRD-24VDC-SL-C, 24 V coil (about 15 mA), powered from the protected rail.
- Q5 S8050 (SOT-23) low-side coil driver. Base: R13 1 kΩ from P07, R14 10 kΩ pull-down.
- D3 1N4148W flyback diode across the coil.
- Relay COM connects to raw IN+ (before D1), so load current does not pass through D1.
  NO goes to OUT+. OUT− ties to IN−.
- Load path traces at least 3 mm wide with solder-mask openings for tinning.

### MCU
- U1 MG51FB9AE (TSSOP-20), 5 V supply.
- C4 100 nF and C5 10 µF at VDD.
- J2 5-pin 2.54 mm ICP header: VDD, ICE_DAT (P16), ICE_CLK (P02), nRST (P20), GND.
- R15 10 kΩ pull-up on P20 (nRESET / START key).

### Pin map (fixed by firmware)

| Pin | Function |
|-----|----------|
| P00 | Segment A |
| P02 | Segment B (also ICE_CLK) |
| P05 | Segment C |
| P12 | Segment D |
| P11 | Segment E |
| P01 | Segment F |
| P14 | Segment G |
| P13 | Segment DP |
| P10 | Digit 1 drive |
| P03 | Digit 2 drive |
| P04 | Digit 3 drive |
| P06 | LED group drive (DL) |
| P07 | Relay |
| P17 | SET key |
| P20 | START key |
| P30 | STOP key |
| P15, P16 | Spare (P16 used for ICE_DAT) |

### Display and LEDs
- Firmware logic: digit pin high = digit on, segment pin low = segment on.
- Q1–Q4 S8050 (SOT-23) emitter followers for D1, D2, D3, DL. Collector to 5 V,
  base through 1 kΩ (R9–R12) from the MCU pin, emitter to the common anode.
  This keeps the firmware polarity and moves digit current off the MCU pins.
- R1–R8 330 Ω segment resistors (about 5 mA per segment).
- LED group on DL: ON/OFF LED on segment B (relay on), SET LED on segment F
  (setting mode), SEC LED on segment A, MIN LED on segment C.
  SEC and MIN are wired but need a small firmware addition to light up.
- No buzzer (firmware has no buzzer code).

### Keys
- SW1 SET (P17), SW2 START (P20), SW3 STOP (P30), each to GND.
- Pull-ups: MCU quasi-bidirectional mode, plus R15 on P20. Firmware debounces.

## Toolchain

- KiCad 9 (installed with winget), scripted with Python where possible.
- Freerouting (jar, Java 17) for autorouting through Specctra DSN/SES.
- KiCad ERC and DRC must pass with zero errors.

## Deliverables (in `hardware/`)

- `timer.kicad_pro`, `timer.kicad_sch`, `timer.kicad_pcb`
- `output/schematic.pdf`
- `output/gerbers.zip` (Gerbers + Excellon drill)
- `output/bom.csv`
- `output/render_top.png`, `output/render_bottom.png` (3D renders)
- `output/films_panel_3x2.pdf` (copper, mask and silkscreen films, 3 × 2 panel, like the reference)

## Verification

- ERC: zero errors.
- DRC: zero errors, zero unrouted nets.
- Gerbers re-opened in KiCad's Gerber viewer or rendered to PNG and checked by eye.
- Every firmware pin in the pin map table connects to the right net (netlist check script).

## Out of scope

- Single-sided version with jumpers.
- Enclosure-accurate dimensions (need real measurements).
- Firmware changes for SEC/MIN LEDs.
- Certification (EMC, safety).

## Production checks (before ordering in volume)

- Confirm MG51FB9AE TSSOP-20 pinout from the Nuvoton datasheet.
- Confirm the display part number and its pinout.
- Measure the enclosure and move the display, keys, LEDs, holes and terminals to match.
