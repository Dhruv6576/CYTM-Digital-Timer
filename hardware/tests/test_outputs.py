"""Fabrication outputs exist and are complete (run after scripts/export.py)."""
import csv
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import env  # noqa: E402
from circuit import PARTS  # noqa: E402

GERBER_LAYERS = ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen", "F_Paste", "B_Paste", "Edge_Cuts")


def test_gerber_zip():
    z = zipfile.ZipFile(env.OUT / "gerbers.zip")
    names = z.namelist()
    for layer in GERBER_LAYERS:
        assert any(layer in n for n in names), (layer, names)
    assert any(n.endswith(".drl") for n in names), names


def test_bom_covers_every_part():
    rows = list(csv.DictReader(open(env.OUT / "bom.csv", encoding="utf-8")))
    refs = set()
    for r in rows:
        refs |= {x.strip() for x in r["Refs"].split(",")}
    want = {r for r in PARTS if not r.startswith("H")}
    assert refs == want, (refs ^ want)



def test_bom_orderable():
    """Every line names a buyable part: caps carry a voltage rating, no front-panel labels as values."""
    labels = {"SEC", "MIN", "SET", "ON/OFF", "START", "STOP", "ICP", "IN+ IN- OUT+ OUT-"}
    for r in csv.DictReader(open(env.OUT / "bom.csv", encoding="utf-8")):
        assert r["Value"] not in labels, r
        if r["Refs"].startswith("C"):
            assert "V" in r["Value"], r


def test_no_stray_files():
    assert not list(env.OUT.glob("timer_preroute*")), list(env.OUT.glob("timer_preroute*"))


def test_placement_file():
    rows = list(csv.DictReader(open(env.OUT / "positions.csv", encoding="utf-8")))
    assert {r["Ref"] for r in rows} >= {r for r, p in PARTS.items() if p.side == "B" and not r.startswith("J")}


def test_docs_and_renders():
    for f in ("schematic.pdf", "render_top.png", "render_bottom.png"):
        assert (env.OUT / f).stat().st_size > 10_000, f


def test_film_panel():
    import pymupdf
    from films import FILMS, PANEL_W, PANEL_H
    d = pymupdf.open(env.OUT / "films_panel_3x2.pdf")
    assert d.page_count == len(FILMS), d.page_count
    k = 72 / 25.4
    for page in d:
        assert abs(page.rect.width / k - PANEL_W) < 0.1 and abs(page.rect.height / k - PANEL_H) < 0.1, page.rect
    assert (env.OUT / "films_preview.png").stat().st_size > 10_000


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
