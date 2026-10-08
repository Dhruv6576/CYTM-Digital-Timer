from pathlib import Path

HW = Path(__file__).resolve().parents[1]
KICAD = Path(r"C:\Program Files\KiCad\10.0")
KICAD_CLI = KICAD / "bin" / "kicad-cli.exe"
KICAD_PY = KICAD / "bin" / "python.exe"
SYM_DIR = KICAD / "share" / "kicad" / "symbols"
FP_DIR = KICAD / "share" / "kicad" / "footprints"
MODEL_DIR = KICAD / "share" / "kicad" / "3dmodels"
FREEROUTING = HW / "tools" / "freerouting-1.9.0.jar"  # 2.5.0 native CLI crashes (GraalVM serialization bug)
JAVA = Path(r"C:\Program Files\Microsoft\jdk-17.0.17.10-hotspot\bin\java.exe")
OUT = HW / "output"
