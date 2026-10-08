"""circuit.py -> timer.kicad_sch: every part placed, every connected pin tagged with a net label."""
import uuid

import env
from circuit import PARTS, NETS
from sexpr import Q, dump, find, first
from symlib import pins, resolve, symbol

SCH = env.HW / "timer.kicad_sch"
PROJECT = "timer"
NS = uuid.UUID("6f1d3c52-6a5e-4c3e-9b1e-1f6f0f6c7a10")
G = 1.27  # schematic grid
PAPER_W, PAPER_H, MARGIN = 420.0, 297.0, 17.78  # A3


def uid(*key):
    return Q(str(uuid.uuid5(NS, "/".join(map(str, key)))))


def snap(v):
    return round(round(v / G) * G, 4)


def font(size=1.27, justify=None, hide=False):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


def num(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# Net label direction: pin angle = direction from connection point into the body.
LABEL_DIR = {0: (180, "right"), 180: (0, "left"), 90: (270, "right"), 270: (90, "left")}


def pin_to_net():
    out = {}
    for net, refs in NETS.items():
        for ref, pin in refs:
            for n in resolve(PARTS[ref].lib_id, pin):
                out[(ref, n)] = net
    return out


GROUPS = [
    ("POWER INPUT  24 VDC", ["J1", "D1", "D2", "C1", "C2", "U2", "C3", "#FLG01", "#FLG02", "#FLG03"]),
    ("MCU  MG51FB9AE", ["U1", "C4", "C5", "R15", "J2"]),
    ("RELAY OUTPUT", ["K1", "D3", "Q5", "R13", "R14"]),
    ("SEGMENT RESISTORS", [f"R{i}" for i in range(1, 9)]),
    ("DIGIT / LED DRIVERS  (pin high = on)", ["R9", "Q1", "R10", "Q2", "R11", "Q3", "R12", "Q4"]),
    ("DISPLAY + INDICATORS", ["U3", "LED1", "LED2", "LED3", "LED4"]),
    ("KEYS", ["SW1", "SW2", "SW3"]),
    ("MOUNTING", ["H1", "H2", "H3", "H4"]),
]
FLAGS = {"#FLG01": "VIN_RAW", "#FLG02": "VIN", "#FLG03": "GND"}
BLOCK_W = 200.0  # max block width before a member wraps to a new line


def label_len(net):
    return len(net) * 1.05 + 2.54


def bbox(ref, p2n):
    """Symbol extent incl. net labels, relative to the symbol origin (schematic Y down)."""
    if ref in FLAGS:
        return -6.35, -7.62, 6.35, label_len(FLAGS[ref]) + 1.27
    ps = pins(PARTS[ref].lib_id)
    if not ps:
        return -5.08, -5.08, 5.08, 7.62
    x0 = min(p["x"] for p in ps); x1 = max(p["x"] for p in ps)
    y0 = min(-p["y"] for p in ps); y1 = max(-p["y"] for p in ps)
    for p in ps:
        ext = label_len(p2n.get((ref, p["number"]), "")) if (ref, p["number"]) in p2n else 2.54
        a = int(p["angle"]) % 360
        if a == 0:
            x0 = min(x0, p["x"] - ext)
        elif a == 180:
            x1 = max(x1, p["x"] + ext)
        elif a == 270:
            y0 = min(y0, -p["y"] - ext)
        else:
            y1 = max(y1, -p["y"] + ext)
    return x0 - 3.81, y0 - 3.81, x1 + 6.35, y1 + 3.81


def layout(p2n):
    """Pack each group into a block, then shelf-pack blocks on the page.
    Returns ({ref: (x, y)}, [(title, x0, y0, x1, y1)])."""
    blocks = []
    for title, refs in GROUPS:
        local, x, y, row_h, w = {}, 0.0, 6.35, 0.0, 0.0
        for ref in refs:
            bx0, by0, bx1, by1 = bbox(ref, p2n)
            bw, bh = bx1 - bx0, by1 - by0
            if x and x + bw > BLOCK_W:
                x, y, row_h = 0.0, y + row_h, 0.0
            local[ref] = (x - bx0, y - by0)
            x += bw
            w, row_h = max(w, x), max(row_h, bh)
        blocks.append((title, local, w, y + row_h))
    pos, frames = {}, []
    x, y, row_h = MARGIN, MARGIN, 0.0
    for title, local, w, h in blocks:
        if x + w > PAPER_W - MARGIN:
            x, y, row_h = MARGIN, y + row_h + 7.62, 0.0
        for ref, (lx, ly) in local.items():
            pos[ref] = (snap(x + lx), snap(y + ly))
        frames.append((title, snap(x - 2.54), snap(y - 2.54), snap(x + w), snap(y + h)))
        x += w + 7.62
        row_h = max(row_h, h)
    assert y + row_h < PAPER_H - 40, f"schematic does not fit the page ({y + row_h:.0f} mm)"
    return pos, frames


def datasheet(lib_id):
    """Library datasheet URL, or "~" (KiCad's empty value)."""
    for q in find(symbol(lib_id), "property"):
        if q[1] == "Datasheet" and q[2] not in ("", "~"):
            return q[2]
    return "~"


def lib_symbol(lib_id):
    s = list(symbol(lib_id))
    s[1] = Q(lib_id)
    return s


def placed_symbol(ref, p, x, y, root):
    sym = symbol(p.lib_id)
    props = {q[1]: q for q in find(sym, "property")}
    node = ["symbol", ["lib_id", Q(p.lib_id)], ["at", num(x), num(y), 0], ["unit", 1],
            ["exclude_from_sim", "no"], ["in_bom", "no" if ref.startswith("H") else "yes"],
            ["on_board", "yes"], ["dnp", "no"], ["uuid", uid("sym", ref)]]
    ref_at = first(props["Reference"], "at") if "Reference" in props else None
    for name, val in (("Reference", ref), ("Value", p.value), ("Footprint", p.footprint),
                      ("Datasheet", datasheet(p.lib_id))):
        src = props.get(name)
        at = first(src, "at") if src else ["at", 0, 0, 0]
        hide = name in ("Footprint", "Datasheet")
        if name == "Value" and ref_at is not None and src is not None:
            dx, dy = float(at[1]) - float(ref_at[1]), float(at[2]) - float(ref_at[2])
            if abs(dy) < 1.3 and abs(dx) < (len(ref) + len(val)) * 0.65:  # library puts them on one line
                at = ["at", at[1], float(at[2]) + 2.54] + at[3:]
        node.append(["property", Q(name), Q(val),
                     ["at", num(x + float(at[1])), num(y - float(at[2])), at[3] if len(at) > 3 else 0],
                     font(hide=hide)])
    for pn in sorted({q["number"] for q in pins(p.lib_id)}):
        node.append(["pin", Q(pn), ["uuid", uid("pin", ref, pn)]])
    node.append(["instances", ["project", Q(PROJECT),
                               ["path", Q(f"/{root}"), ["reference", Q(ref)], ["unit", 1]]]])
    return node


def main():
    root = uid("root")
    p2n = pin_to_net()
    pos, frames = layout(p2n)
    used = sorted({p.lib_id for p in PARTS.values()} | {"power:PWR_FLAG"})
    sch = ["kicad_sch", ["version", "20250610"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
           ["uuid", root], ["paper", Q("A3")],
           ["title_block", ["title", Q("CYTM Digital Timer V5")], ["date", Q("2026-10-08")], ["rev", Q("A")],
            ["company", Q("H&D")],
            ["comment", 1, Q("ASSUMED: MG51FB9AE pinout = N76E003AT20; verify before production")]],
           ["lib_symbols"] + [lib_symbol(l) for l in used]]
    labels = []
    for ref, p in PARTS.items():
        x, y = pos[ref]
        sch.append(placed_symbol(ref, p, x, y, root))
        for pin in pins(p.lib_id):
            px, py = snap(x + pin["x"]), snap(y - pin["y"])
            net = p2n.get((ref, pin["number"]))
            if net is None:
                if pin["type"] != "no_connect":
                    labels.append(["no_connect", ["at", num(px), num(py)], ["uuid", uid("nc", ref, pin["number"])]])
                continue
            ang, just = LABEL_DIR[int(pin["angle"]) % 360]
            labels.append(["label", Q(net), ["at", num(px), num(py), ang], font(justify=f"{just} bottom"),
                           ["uuid", uid("lbl", ref, pin["number"])]])
    # Power flags: nets fed from outside the board or by passive parts
    for ref, net in FLAGS.items():
        x, y = pos[ref]
        node = ["symbol", ["lib_id", Q("power:PWR_FLAG")], ["at", num(x), num(y), 0], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                ["uuid", uid("sym", ref)],
                ["property", Q("Reference"), Q(ref), ["at", num(x), num(y - 1.905), 0], font(hide=True)],
                ["property", Q("Value"), Q("PWR_FLAG"), ["at", num(x), num(y - 3.81), 0], font()],
                ["property", Q("Footprint"), Q(""), ["at", num(x), num(y), 0], font(hide=True)],
                ["property", Q("Datasheet"), Q("~"), ["at", num(x), num(y), 0], font(hide=True)],
                ["pin", Q("1"), ["uuid", uid("pin", ref)]],
                ["instances", ["project", Q(PROJECT), ["path", Q(f"/{root}"), ["reference", Q(ref)], ["unit", 1]]]]]
        sch.append(node)
        labels.append(["label", Q(net), ["at", num(x), num(y), 270], font(justify="right bottom"),
                       ["uuid", uid("flaglbl", net)]])
    # Block frames + titles
    for title, x0, y0, x1, y1 in frames:
        sch.append(["rectangle", ["start", num(x0), num(y0)], ["end", num(x1), num(y1)],
                    ["stroke", ["width", 0.1524], ["type", "dash"]], ["fill", ["type", "none"]],
                    ["uuid", uid("frame", title)]])
        sch.append(["text", Q(title), ["exclude_from_sim", "yes"], ["at", num(x0 + 1.27), num(y0 + 3.175), 0],
                    font(size=2.0, justify="left bottom"), ["uuid", uid("title", title)]])
    sch += labels
    sch.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    SCH.write_text(dump(sch) + "\n", encoding="utf-8")
    pro = env.HW / "timer.kicad_pro"
    if not pro.exists():
        pro.write_text('{\n  "meta": {"filename": "timer.kicad_pro", "version": 3}\n}\n', encoding="utf-8")
    print(f"wrote {SCH.name}: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    main()
