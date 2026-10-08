"""Board checks. Run with KiCad's python: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tests/test_pcb.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pcbnew  # noqa: E402
import env  # noqa: E402
from circuit import PARTS, NETS, BOARD_W, BOARD_H, NETCLASS  # noqa: E402
from symlib import resolve  # noqa: E402

PCB = env.HW / "timer.kicad_pcb"
FRONT_ONLY = {"U3", "LED1", "LED2", "LED3", "LED4", "SW1", "SW2", "SW3", "J1"}
mm = pcbnew.ToMM


def board():
    assert PCB.exists(), "timer.kicad_pcb missing: run scripts/gen_pcb.py"
    return pcbnew.LoadBoard(str(PCB))


def test_outline_50x80():
    bb = board().GetBoardEdgesBoundingBox()
    assert abs(mm(bb.GetWidth()) - BOARD_W) < 0.2 and abs(mm(bb.GetHeight()) - BOARD_H) < 0.2, \
        (mm(bb.GetWidth()), mm(bb.GetHeight()))


def test_sides():
    b = board()
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        want = pcbnew.F_Cu if ref in FRONT_ONLY or ref.startswith("H") else pcbnew.B_Cu
        assert fp.GetLayer() == want, (ref, fp.GetLayerName())
    assert {fp.GetReference() for fp in b.GetFootprints()} == set(PARTS)


def test_pad_nets():
    b = board()
    want = {}
    for net, refs in NETS.items():
        for ref, pin in refs:
            for n in resolve(PARTS[ref].lib_id, pin):
                want[(ref, n)] = net
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            key = (fp.GetReference(), pad.GetNumber())
            if pad.GetNumber():
                got = pad.GetNetname()
                if key in want:
                    assert got == "/" + want[key], (key, got, want[key])
                else:
                    assert got.startswith("unconnected-("), (key, got)


def test_parts_inside_outline():
    b = board()
    edge = b.GetBoardEdgesBoundingBox()
    for fp in b.GetFootprints():
        bb = fp.GetBoundingBox(False)
        assert edge.Contains(bb.GetOrigin()) and edge.Contains(bb.GetEnd()), fp.GetReference()


def test_netclasses():
    b = board()
    for net, cls in NETCLASS.items():
        assert b.FindNet("/" + net).GetNetClassName() == cls, (net, b.FindNet("/" + net).GetNetClassName())


def test_track_widths():
    """Load nets (5 A) carry >= 3.0 mm copper; VIN/+5V (<100 mA) >= 0.4 mm."""
    b = board()
    load = [t for t in b.GetTracks() if t.GetNetname().lstrip("/") in ("VIN_RAW", "OUT_P") and t.GetClass() == "PCB_TRACK"]
    big = [t for t in load if mm(t.GetWidth()) >= 3.0 - 1e-6]
    assert big, "no 3 mm load tracks"
    # every load-net connection between J1 and K1 runs on 3 mm copper
    for t in load:
        if mm(t.GetWidth()) < 3.0 - 1e-6:
            assert t.GetNetname() == "/VIN_RAW", ("thin OUT_P track", mm(t.GetWidth()))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname().lstrip("/") in ("VIN", "+5V"):
            assert mm(t.GetWidth()) >= 0.4 - 1e-6, (t.GetNetname(), mm(t.GetWidth()))


LOAD_PATHS = [("J1", "1", "K1", "1", "/VIN_RAW"), ("K1", "3", "J1", "3", "/OUT_P"), ("J1", "2", "J1", "4", "/GND")]


def _pad(b, ref, num):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]


def test_load_paths_3mm():
    """Each 5 A path is a continuous chain of >= 3.0 mm tracks from pad to pad."""
    b = board()
    for r1, n1, r2, n2, net in LOAD_PATHS:
        wide = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == net
                and mm(t.GetWidth()) >= 3.0 - 1e-6]
        start, goal = _pad(b, r1, n1), _pad(b, r2, n2)
        seen, todo = set(), [t for t in wide if start.HitTest(t.GetStart()) or start.HitTest(t.GetEnd())]
        reached = False
        while todo:
            t = todo.pop()
            if id(t) in seen:
                continue
            seen.add(id(t))
            if goal.HitTest(t.GetStart()) or goal.HitTest(t.GetEnd()):
                reached = True
                break
            ends = (t.GetStart(), t.GetEnd())
            todo += [u for u in wide if id(u) not in seen and (u.GetStart() in ends or u.GetEnd() in ends)]
        assert reached, f"no 3 mm chain {r1}.{n1} -> {r2}.{n2}"


def test_decoupling_next_to_vdd():
    b = board()
    vdd = _pad(b, "U1", "9").GetPosition()
    c4 = b.FindFootprintByReference("C4").GetPosition()
    assert mm((c4 - vdd).EuclideanNorm()) < 4.0, mm((c4 - vdd).EuclideanNorm())


def test_fully_routed():
    b = board()
    b.BuildConnectivity()
    n = b.GetConnectivity().GetUnconnectedCount(False)
    assert n == 0, f"{n} unrouted connections"


if __name__ == "__main__":
    only = sys.argv[1:]
    for name, fn in list(globals().items()):
        if name.startswith("test_") and (not only or name in only):
            fn()
    print("ok")
