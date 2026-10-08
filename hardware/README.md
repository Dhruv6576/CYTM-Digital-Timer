# CYTM V5 Digital Timer PCB

24 VDC cyclic relay timer board for the firmware in `../Final/5-26.c` (MG51FB9AE, unchanged pin map).
2-layer, 50 x 80 mm, display/LEDs/keys/terminal on the front, everything else on the back.

Status: prototype (Rev A). ERC 0 errors / 0 warnings, DRC 0 violations, 0 unconnected, schematic parity clean.

## Rebuild

Everything is generated from `scripts/circuit.py` (parts, nets, placement). One command rebuilds and checks it all:

```
python scripts/build.py
```

Needs: KiCad 10 (`C:\Program Files\KiCad\10.0`), Python 3.10+ with PyMuPDF, Java 17, and
`tools/freerouting-1.9.0.jar` (not in git; get it with
`gh release download v1.9.0 -R freerouting/freerouting -p freerouting-1.9.0.jar -D hardware/tools`).
`scripts/env.py` holds the paths. Takes about 4 minutes, most of it autorouting and 3D renders.

Freerouting does not give the same tracks on every run. `build.py` only reports `BUILD OK` when the new board
passes every test, ERC and DRC, so any accepted run is clean; the files in `output/` belong to the last run.

| Step | Script | Output |
|------|--------|--------|
| Project libraries | `gen_symlib.py` | `timer.kicad_sym`, `timer.pretty/`, `timer.3dshapes/` |
| Schematic | `gen_sch.py` | `timer.kicad_sch` |
| Board + placement | `gen_pcb.py` (KiCad python) | `timer.kicad_pcb` |
| Routing | `route.py` (KiCad python + Freerouting 1.9.0) | routed `timer.kicad_pcb` |
| Fabrication files | `export.py` | `output/` |
| Films | `films.py` | `output/films_panel_3x2.pdf` |
| Checks | `tests/*.py`, ERC, DRC | `output/erc.rpt`, `output/drc.rpt` |

## Outputs (`output/`)

- `gerbers.zip`: Gerber X2 (both copper, mask, paste, legend, outline) + Excellon drill. Upload to the PCB maker.
- `bom.csv`: parts grouped by value and footprint.
- `positions.csv`: pick-and-place, mm, origin at the board's bottom-left corner.
- `schematic.pdf`
- `render_top.png`, `render_bottom.png`, `render_iso.png`
- `films_panel_3x2.pdf`: 1:1 films, 3 x 2 panel, one page per layer (back layers mirrored, mask negative).
  Check the 10 mm scale bar after printing.

## Circuit summary

- 24 V in: SMBJ28CA bidirectional TVS on the raw input, then SS36 (60 V) reverse-polarity diode,
  100 uF bulk, L78M05 (DPAK) to 5 V.
- Relay: SRD-24VDC-SL-C, 24 V coil from the protected rail, MMBTA06 driver (80 V), 1N4148W flyback.
  COM is fed from raw IN+ so load current bypasses the diode. IN+ -> COM, NO -> OUT+ and IN- <-> OUT- are 3 mm tracks (5 A).
- Display: 3-digit 0.56" common anode (BA56-12EWA pinout). Each digit and the LED group is driven by an
  SS8050 emitter follower, so "pin high = digit on" (firmware polarity) and the digit pins carry only base
  current. The 8 segment pins each sink their segment current through 330 ohm (~4.5-6 mA peak).
- The 3 mm load tracks are not tinned (no mask opening): they run under the terminal and relay bodies.
  3 mm of 1 oz copper carries 5 A at about 10 C rise.
- LEDs on the LED group (P0.6): SEC = seg A, ON/OFF = seg B (relay on), MIN = seg C, SET = seg F (setting mode).
- Keys to GND: SET P1.7, START P2.0 (10k pull-up), STOP P3.0.
- ICP header J2: 1 VDD, 2 ICE_DAT (P1.6), 3 ICE_CLK (P0.2), 4 nRST (P2.0), 5 GND.

## Before ordering in volume

1. **MCU pinout.** The MG51FB9AE symbol assumes the N76E003 / MS51FB9AE TSSOP-20 pinout
   (`scripts/gen_symlib.py`, checked by `tests/test_libs.py`). Confirm it against the Nuvoton MG51 datasheet.
2. **Display.** Pinout taken from Kingbright CA56-12 with pin 6 not connected (3-digit BA56-12EWA, 37.8 x 19 mm).
   Confirm the part you buy uses the same 12-pin layout.
3. **Enclosure.** Board size, display, key, LED, hole and terminal positions are assumptions. Measure the
   enclosure and change the coordinates in `scripts/circuit.py`, then run `build.py`.
4. **Firmware.** The SEC and MIN LEDs are wired (seg A / seg C in the LED-group slot) but the current firmware
   does not light them. ON/OFF and SET already work.
5. **Relay rating.** The tracks carry 5 A. The SRD relay is rated 10 A, but the terminal block and board are not.
6. **Surges.** The L78M05 is rated 35 V; the SMBJ28CA clamps up to 45 V on a full-energy surge. For harsh
   supplies use a 40 V+ regulator (or a small buck converter) in the same position.
7. **Prototype checks.** Measure the regulator tab temperature (about 0.9 W at 24 V) and the display brightness
   (330 ohm gives about 1.2-1.5 mA average per segment; 220 ohm is brighter but heats the regulator more).
8. **Inductive loads.** For valves or contactor coils on OUT, fit a freewheel diode at the load.
