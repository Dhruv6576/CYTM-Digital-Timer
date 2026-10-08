"""circuit.py -> timer.kicad_pcb: outline, rules, net classes, placed footprints with nets, GND pours.

Run with KiCad's python: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" scripts/gen_pcb.py
"""
import subprocess
import tempfile
from pathlib import Path

import pcbnew

import env
from circuit import PARTS, NETS, NETCLASS, BOARD_W, BOARD_H, FRONT_TEXT, BACK_TEXT
from gen_sch import uid, datasheet
from sexpr import parse, find, first

PCB = env.HW / "timer.kicad_pcb"
OX, OY = 100.0, 100.0  # board top-left on the KiCad page (mm)
MM = pcbnew.FromMM


def NET(name):
    """Board net name: KiCad names root-sheet label nets '/<label>'."""
    return "/" + name

CLASSES = {  # name: (track mm, clearance mm)
    "Default": (0.25, 0.2),
    "Power": (0.4, 0.2),  # <100 mA; 0.4 mm fits TSSOP pins (0.65 mm pitch)
    "Load": (1.0, 0.5),  # 3.0 mm load path is hand-routed in route.py; 1.0 mm for the D1 tap
}


def schematic_nets():
    """{(ref, pad): net} from KiCad's own netlist of timer.kicad_sch (exact names, incl. no-connects)."""
    out = Path(tempfile.gettempdir()) / "timer_pcb_netlist.net"
    subprocess.run([str(env.KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(out), str(env.HW / "timer.kicad_sch")], check=True, capture_output=True)
    p2n = {}
    for n in find(first(parse(out.read_text(encoding="utf-8")), "nets"), "net"):
        for node in find(n, "node"):
            p2n[(first(node, "ref")[1], first(node, "pin")[1])] = first(n, "name")[1]
    return p2n


def pt(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def setup_rules(board):
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = MM(0.2)
    ds.m_MinClearance = MM(0.2)
    ds.m_ViasMinSize = MM(0.6)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_CopperEdgeClearance = MM(0.5)
    ds.m_HoleClearance = MM(0.25)
    ds.m_HoleToHoleMin = MM(0.5)
    ds.m_SilkClearance = MM(0.1)
    ds.SetBoardThickness(MM(1.6))
    ds.SetAuxOrigin(pt(0, BOARD_H))  # drill/place origin = board bottom-left corner
    ns = ds.m_NetSettings
    for name, (track, clear) in CLASSES.items():
        nc = ns.GetDefaultNetclass() if name == "Default" else pcbnew.NETCLASS(name)
        nc.SetTrackWidth(MM(track))
        nc.SetClearance(MM(clear))
        nc.SetViaDiameter(MM(0.6 if name == "Default" else 0.8))
        nc.SetViaDrill(MM(0.3 if name == "Default" else 0.4))
        if name != "Default":
            ns.SetNetclass(name, nc)
    for net, cls in NETCLASS.items():
        ns.SetNetclassPatternAssignment(NET(net), cls)


def outline(board, r=1.0):
    w, h = BOARD_W, BOARD_H
    segs = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)), ((w - r, h), (r, h)), ((0, h - r), (0, r))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
        board.Add(s)
    for cx, cy, sx, sy in ((r, r, 0, r), (w - r, r, w - r, 0), (w - r, h - r, w, h - r), (r, h - r, r, h)):
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        a.SetCenter(pt(cx, cy)); a.SetStart(pt(sx, sy)); a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(MM(0.1))
        board.Add(a)


def courtyard_center(fp):
    fp.BuildCourtyardCaches()
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    poly = fp.GetCourtyard(layer)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False)
    return bb.Centre()


def place(board, ref, p, p2n):
    lib, name = p.footprint.split(":")
    base = env.HW if lib == "timer" else env.FP_DIR
    fp = pcbnew.FootprintLoad(str(base / f"{lib}.pretty"), name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(p.value)
    fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(datasheet(p.lib_id))
    fp.SetPath(pcbnew.KIID_PATH("/" + str(uid("root")) + "/" + str(uid("sym", ref))))
    board.Add(fp)
    fp.SetPosition(pt(0, 0))
    fp.SetOrientationDegrees(p.rot)
    if p.side == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    c = courtyard_center(fp)
    fp.Move(pt(p.x, p.y) - c)
    for pad in fp.Pads():
        net = p2n.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(board.FindNet(net))
    return fp


def gnd_zone(board, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(board.FindNet(NET("GND")).GetNetCode())
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0.3, 0.3), (BOARD_W - 0.3, 0.3), (BOARD_W - 0.3, BOARD_H - 0.3), (0.3, BOARD_H - 0.3)):
        o.Append(MM(OX + x), MM(OY + y))
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)  # SMD solid, THT thermal relief
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(0)
    z.SetZoneName(f"GND_{board.GetLayerName(layer)}")
    board.Add(z)


def text(board, s, x, y, layer, size=1.2):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(0.18))
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def silk_refs(fp):
    """Readable reference designators: small font, fab copy kept; values only on fab layer."""
    r = fp.Reference()
    r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    r.SetTextThickness(MM(0.12))
    if fp.GetReference().startswith("H"):
        r.SetVisible(False)
    fp.Value().SetVisible(False)


def _box(b, grow=0.0):
    g = MM(grow)
    return (b.GetLeft() - g, b.GetTop() - g, b.GetRight() + g, b.GetBottom() + g)


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def place_refs(board):
    """Put each reference label next to its part where it clears pads, silk and other labels."""
    obst = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for cu, silk in ((pcbnew.F_Cu, pcbnew.F_SilkS), (pcbnew.B_Cu, pcbnew.B_SilkS)):
                if pad.IsOnLayer(cu) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    obst[silk].append(_box(pad.GetBoundingBox(), 0.2))
        for g in fp.GraphicalItems():
            if g.GetLayer() in obst and g.GetClass() != "PCB_TEXT":
                obst[g.GetLayer()].append(_box(g.GetBoundingBox(), 0.12))
    for d in board.GetDrawings():
        if d.GetLayer() in obst:
            obst[d.GetLayer()].append(_box(d.GetBoundingBox(), 0.12))
    edge = _box(board.GetBoardEdgesBoundingBox(), -0.6)
    unplaced = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        r = fp.Reference()
        if not r.IsVisible():
            continue
        layer = r.GetLayer()
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        c = _box(cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False))
        cx, cyy = (c[0] + c[2]) // 2, (c[1] + c[3]) // 2
        found = False
        for angle in (0, 90):
            r.SetTextAngleDegrees(angle)
            r.SetPosition(pcbnew.VECTOR2I(int(cx), int(cyy)))
            tb = _box(r.GetBoundingBox())
            hw, hh = (tb[2] - tb[0]) / 2 + MM(0.25), (tb[3] - tb[1]) / 2 + MM(0.25)
            cands = [(c[2] + hw, cyy), (c[0] - hw, cyy), (cx, c[1] - hh), (cx, c[3] + hh),
                     (c[2] + hw, c[1] - hh), (c[0] - hw, c[1] - hh), (c[2] + hw, c[3] + hh), (c[0] - hw, c[3] + hh)]
            for x, y in cands:
                r.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                tb = _box(r.GetBoundingBox(), 0.05)
                inside = edge[0] <= tb[0] and edge[1] <= tb[1] and tb[2] <= edge[2] and tb[3] <= edge[3]
                if inside and not any(_hit(tb, o) for o in obst[layer]):
                    obst[layer].append(_box(r.GetBoundingBox(), 0.1))
                    found = True
                    break
            if found:
                break
        if not found:
            r.SetVisible(False)
            unplaced.append(fp.GetReference())
    return unplaced


def main():
    board = pcbnew.NewBoard(str(PCB))
    setup_rules(board)
    p2n = schematic_nets()
    for net in sorted(set(p2n.values())):
        board.Add(pcbnew.NETINFO_ITEM(board, net))
    outline(board)
    for ref, p in PARTS.items():
        silk_refs(place(board, ref, p, p2n))
    for s, x, y in FRONT_TEXT:
        text(board, s, x, y, pcbnew.F_SilkS)
    for s, x, y in BACK_TEXT:
        text(board, s, x, y, pcbnew.B_SilkS, 1.0)
    hidden = place_refs(board)
    if hidden:
        print("reference hidden (no room on silkscreen):", ", ".join(hidden))
    board.BuildConnectivity()  # GND pours are added by route.py after autorouting
    pcbnew.SaveBoard(str(PCB), board)
    print(f"wrote {PCB.name}: {len(board.GetFootprints())} footprints, {board.GetNetCount()} nets")


if __name__ == "__main__":
    main()
