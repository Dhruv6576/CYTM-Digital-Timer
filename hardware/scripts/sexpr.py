"""Minimal S-expression reader/writer for KiCad files (.kicad_sym, .kicad_sch, netlists)."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


class Q(str):
    """Atom that was quoted in the source; always written back quoted."""


def parse(text):
    stack, cur = [], []
    pos, n = 0, len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip():
                raise ValueError(f"bad token at {pos}: {text[pos:pos+30]!r}")
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done, cur = cur, stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(Q(re.sub(r'\\(.)', lambda e: {'n': '\n'}.get(e.group(1), e.group(1)), m.group(3))))
        else:
            cur.append(m.group(4))
    assert not stack, "unbalanced parentheses"
    return cur[0] if len(cur) == 1 else cur


def _atom(a):
    if isinstance(a, Q) or a == "" or re.search(r'[\s()"\\]', a):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    return a


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(str(node) if not isinstance(node, str) else node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return "(" + " ".join(dump(c) for c in node) + ")"
    pad = "\t" * (indent + 1)
    head = [dump(c) for c in node if not isinstance(c, list)]
    out = "(" + " ".join(head)
    for c in node:
        if isinstance(c, list):
            out += "\n" + pad + dump(c, indent + 1)
    return out + "\n" + "\t" * indent + ")"


def find(node, tag):
    """Direct children lists whose head is tag."""
    return [c for c in node if isinstance(c, list) and c and c[0] == tag]


def first(node, tag):
    r = find(node, tag)
    return r[0] if r else None


if __name__ == "__main__":
    src = '(a "b c" (d 1 2) (e "x\\"y" (f)))'
    t = parse(src)
    assert t == ["a", "b c", ["d", "1", "2"], ["e", 'x"y', ["f"]]], t
    assert parse(dump(t)) == t
    assert first(t, "d") == ["d", "1", "2"]
    print("ok")
