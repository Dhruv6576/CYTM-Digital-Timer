"""Read KiCad symbols and resolve circuit.py pin references to pin numbers."""
from functools import lru_cache

import env
from sexpr import parse, find, first


@lru_cache(maxsize=None)
def _lib(lib):
    path = env.HW / "timer.kicad_sym" if lib == "timer" else env.SYM_DIR / f"{lib}.kicad_sym"
    return parse(path.read_text(encoding="utf-8"))


def symbol(lib_id):
    """Symbol node with `extends` resolved; name is the bare symbol name."""
    lib, name = lib_id.split(":")
    syms = {s[1]: s for s in find(_lib(lib), "symbol")}
    if name not in syms:
        raise KeyError(f"symbol {lib_id} not found")
    sym = syms[name]
    ext = first(sym, "extends")
    if not ext:
        return sym
    parent = symbol(f"{lib}:{ext[1]}")
    props = {p[1]: p for p in find(sym, "property")}
    out = ["symbol", name]
    for c in parent[2:]:
        if isinstance(c, list) and c[0] == "property" and c[1] in props:
            out.append(props.pop(c[1]))
        elif isinstance(c, list) and c[0] == "symbol":  # units: rename Parent_u_s -> Name_u_s
            out.append(["symbol", name + c[1][len(ext[1]):]] + c[2:])
        else:
            out.append(c)
    out[2:2] = list(props.values())
    return out


def pins(lib_id):
    """[{number, name, x, y, angle, length, unit}] for every pin of the symbol."""
    out = []
    for unit in find(symbol(lib_id), "symbol"):
        u = int(unit[1].rsplit("_", 2)[-2])
        for p in find(unit, "pin"):
            at = first(p, "at")
            out.append(dict(number=first(p, "number")[1], name=first(p, "name")[1],
                            x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=float(first(p, "length")[1]), unit=u, type=p[1]))
    return out


def resolve(lib_id, ref_pin):
    """Pin numbers matching ref_pin: number, then exact name, then name prefix before '/'."""
    ps = pins(lib_id)
    for key in (lambda p: p["number"], lambda p: p["name"], lambda p: p["name"].split("/")[0]):
        hit = sorted({p["number"] for p in ps if key(p) == ref_pin})
        if hit:
            return hit
    raise KeyError(f"{lib_id}: no pin {ref_pin!r}; have {[(p['number'], p['name']) for p in ps]}")
