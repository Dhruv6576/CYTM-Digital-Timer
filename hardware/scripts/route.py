"""Route timer.kicad_pcb: fixed 3 mm load path, Freerouting for the rest, then fill GND pours.

Run with KiCad's python: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" scripts/route.py
"""
import subprocess

import pcbnew

import env
from gen_pcb import gnd_zone

PCB = env.HW / "timer.kicad_pcb"
DSN = env.OUT / "timer.dsn"
SES = env.OUT / "timer.ses"
PRE = env.OUT / "timer_preroute.kicad_pcb"
OX, OY = 100.0, 100.0
MM = pcbnew.FromMM

# 5 A load path, built from the placed J1 / K1 pads (front-view mm). Offsets keep >= 3.3 mm from the
# centres of neighbouring J1/K1 pads; DRC in build.py rejects the board if a placement change breaks that.
def load_routes(board):
    def pad(ref, num):
        q = [p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0].GetPosition()
        return pcbnew.ToMM(q.x) - OX, pcbnew.ToMM(q.y) - OY
    j1, j2, j3, j4 = (pad("J1", n) for n in "1234")
    com, no = pad("K1", "1"), pad("K1", "3")
    xv = j1[0] - 2.38                      # IN+ rises left of J1.1, clear of relay coil pad K1.2
    yo = j1[1] - 3.91                      # OUT+ runs above the J1 pads
    yg = j2[1] - 3.51                      # IN-/OUT- return runs above J1.3
    return [
        ("/VIN_RAW", pcbnew.F_Cu, [j1, (xv, j1[1] - 2.38), (xv, com[1] + 2.0), (xv + 2.0, com[1]), com]),
        ("/OUT_P", pcbnew.B_Cu, [no, (no[0] + (yo - no[1]), yo), (j3[0] - (j3[1] - yo), yo), j3]),
        ("/GND", pcbnew.F_Cu, [j2, (j2[0] + 2.04, yg), (j4[0] - 2.02, yg), (j4[0], yg + 2.02), j4]),
    ]


LOAD_WIDTH = 3.0


def pt(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def add_route(board, net, layer, pts, width=LOAD_WIDTH):
    """Locked copper track. No mask opening: the path runs under the J1/K1 bodies, so it could not be
    tinned there, and openings clip their silkscreen. 3 mm / 1 oz carries 5 A at ~10 C rise (IPC-2152)."""
    n = board.FindNet(net)
    assert n, net
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a)); t.SetEnd(pt(*b))
        t.SetLayer(layer); t.SetWidth(MM(width)); t.SetNet(n)
        t.SetLocked(True)
        board.Add(t)


def prepare():
    """Stage 1: strip tracks/pours, add the locked load path, export DSN."""
    board = pcbnew.LoadBoard(str(PCB))
    # gen_pcb.py output: no tracks, pours or mask drawings yet. Deleting items in-process breaks
    # pcbnew's SWIG wrappers, so this stage only adds.
    assert not board.GetTracks() and not board.GetAreaCount(), "run gen_pcb.py first"
    for route in load_routes(board):
        add_route(board, *route)
    env.OUT.mkdir(exist_ok=True)
    pcbnew.SaveBoard(str(PRE), board)
    assert pcbnew.ExportSpecctraDSN(board, str(DSN)), "DSN export failed"


def stitch(board, pitch=4.0, margin=0.75):
    """GND vias on a grid wherever both pours are solid around the point and no part sits there."""
    zones = [board.GetArea(i) for i in range(board.GetAreaCount())]
    gnd = board.FindNet("/GND")
    keep_out = []
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            poly = fp.GetCourtyard(layer)
            if poly.OutlineCount():
                keep_out.append(poly.BBox())
    ring = [(0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin),
            (0.7 * margin, 0.7 * margin), (-0.7 * margin, 0.7 * margin), (0.7 * margin, -0.7 * margin), (-0.7 * margin, -0.7 * margin)]
    count = 0
    y = 2.0
    while y < 80:
        x = 2.0
        while x < 50:
            c = pt(x, y)
            solid = all(z.HitTestFilledArea(z.GetLayer(), pt(x + dx, y + dy)) for z in zones for dx, dy in ring)
            if solid and not any(bb.Contains(c) for bb in keep_out):
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(c)
                v.SetWidth(MM(0.6))
                v.SetDrill(MM(0.3))
                v.SetNet(gnd)
                board.Add(v)
                count += 1
            x += pitch
        y += pitch
    return count


def heal(board, snap=0.001):
    """SES import can leave track ends 1 nm apart and zero-length stubs: snap ends, drop stubs."""
    tol = MM(snap)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    for t in tracks:
        if (t.GetEnd() - t.GetStart()).EuclideanNorm() < tol:
            board.Delete(t)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    ends = {}
    for t in tracks:
        for q in (t.GetStart(), t.GetEnd()):
            ends.setdefault((t.GetNetCode(), t.GetLayer()), []).append(q)
    for t in tracks:
        pool = ends[(t.GetNetCode(), t.GetLayer())]
        for get, put in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            q = get()
            for o in pool:
                if o != q and (o - q).EuclideanNorm() < tol:
                    put(pcbnew.VECTOR2I(o.x, o.y))
                    break


def tie_islands(board, step=0.5, margin=0.75):
    """One GND via in every pour island that has none, where both layers are solid, so no island
    hangs on thermal spokes alone (DRC starved_thermal)."""
    zones = [board.GetArea(i) for i in range(board.GetAreaCount())]
    gnd = board.FindNet("/GND")
    vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "/GND"]
    ring = [(0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin)]
    added = 0
    for z in zones:
        polys = z.GetFilledPolysList(z.GetLayer())
        for i in range(polys.OutlineCount()):
            island = polys.Outline(i)
            if any(island.PointInside(v) for v in vias):
                continue
            bb = island.BBox()
            x = bb.GetLeft()
            spot = None
            while x < bb.GetRight() and spot is None:
                y = bb.GetTop()
                while y < bb.GetBottom():
                    c = pcbnew.VECTOR2I(int(x), int(y))
                    if island.PointInside(c) and all(
                            zz.HitTestFilledArea(zz.GetLayer(), c + pcbnew.VECTOR2I(MM(dx), MM(dy)))
                            for zz in zones for dx, dy in ring):
                        spot = c
                        break
                    y += MM(step)
                x += MM(step)
            if spot is None:
                continue
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(spot); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(gnd)
            board.Add(v)
            vias.append(spot)
            added += 1
    return added


def finish():
    """Stage 3: import the Freerouting session, lock the load path, pour GND, save."""
    board = pcbnew.LoadBoard(str(PRE))
    assert pcbnew.ImportSpecctraSES(board, str(SES)), "SES import failed"
    heal(board)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and pcbnew.ToMM(t.GetWidth()) >= 3.0 - 1e-6:
            t.SetLocked(True)
    gnd_zone(board, pcbnew.F_Cu)
    gnd_zone(board, pcbnew.B_Cu)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    n = stitch(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    n += tie_islands(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(PCB), board)
    print(f"stitching vias: {n}")
    left = board.GetConnectivity().GetUnconnectedCount(False)
    print(f"routed: {len(board.GetTracks())} tracks/vias, unrouted {left}")
    raise SystemExit(3 if left else 0)


def main():
    """Each stage in its own KiCad python process: pcbnew's SWIG wrappers do not survive
    track/zone deletion inside one process."""
    py = str(env.KICAD_PY)
    subprocess.run([py, __file__, "prepare"], check=True)
    # Default strategy is deterministic; later attempts vary it so a stuck result is not repeated.
    strategies = [[], ["-us", "global"], ["-is", "random"], ["-us", "hybrid", "-hr", "1:1"]] + [["-is", "random"]] * 6
    for attempt, extra in enumerate(strategies, 1):
        SES.unlink(missing_ok=True)
        r = subprocess.run([str(env.JAVA), "-jar", str(env.FREEROUTING), "-de", str(DSN), "-do", str(SES),
                            "-mp", "100", "-l", "en", *extra], capture_output=True, text=True, timeout=1800)
        (env.OUT / "freerouting.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        assert SES.exists(), "Freerouting produced no session; see output/freerouting.log"
        done = subprocess.run([py, __file__, "finish"])
        if done.returncode == 0:
            break
        print(f"attempt {attempt} {' '.join(extra) or 'default'}: unrouted connections left, retrying")
    else:
        raise SystemExit(f"routing incomplete after {len(strategies)} attempts")
    for f in env.OUT.glob("timer_preroute*"):
        f.unlink()


if __name__ == "__main__":
    import sys
    {"prepare": prepare, "finish": finish}.get(sys.argv[1] if len(sys.argv) > 1 else "", main)()
