"""Print courtyard bbox (mm, unrotated, relative to footprint origin) for every part. Run with KiCad python."""
import sys
import pcbnew
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import env
from circuit import PARTS
for ref, p in PARTS.items():
    lib, name = p.footprint.split(":")
    base = env.HW if lib == "timer" else env.FP_DIR
    fp = pcbnew.FootprintLoad(str(base / f"{lib}.pretty"), name)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    pads = [(pd.GetNumber(), round(pcbnew.ToMM(pd.GetPosition().x), 2), round(pcbnew.ToMM(pd.GetPosition().y), 2)) for pd in fp.Pads()]
    print(f"{ref:5} {name[:38]:38} x {pcbnew.ToMM(bb.GetLeft()):7.2f}..{pcbnew.ToMM(bb.GetRight()):6.2f}  y {pcbnew.ToMM(bb.GetTop()):7.2f}..{pcbnew.ToMM(bb.GetBottom()):6.2f}  pads {pads[:6]}")
