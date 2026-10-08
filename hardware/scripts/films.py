"""1:1 photo-plot films, 3 x 2 panel per layer (like resources/reference_pcb_panel_80x50mm.png).

Output: output/films_panel_3x2.pdf (one page per film) + output/films_preview.png (all films, small).
Back-side films are mirrored (seen from the back); solder-mask films are negative (openings clear).
"""
import subprocess
import tempfile
from pathlib import Path

import pymupdf

import env
from circuit import BOARD_W, BOARD_H

COLS, ROWS, MARGIN, TITLE = 3, 2, 10.0, 12.0
PANEL_W = COLS * BOARD_W + 2 * MARGIN
PANEL_H = ROWS * BOARD_H + 2 * MARGIN + TITLE
K = 72 / 25.4  # pt per mm

# (file tag, layers, mirror, negative, title)
FILMS = [
    ("top_copper", "F.Cu,Edge.Cuts", False, False, "TOP COPPER (F.Cu) - positive, viewed from top"),
    ("bottom_copper", "B.Cu,Edge.Cuts", True, False, "BOTTOM COPPER (B.Cu) - positive, mirrored (viewed from bottom)"),
    ("top_mask", "F.Mask,Edge.Cuts", False, True, "TOP SOLDER MASK (F.Mask) - negative, openings clear"),
    ("bottom_mask", "B.Mask,Edge.Cuts", True, True, "BOTTOM SOLDER MASK (B.Mask) - negative, mirrored"),
    ("top_silk", "F.Silkscreen,Edge.Cuts", False, False, "TOP LEGEND (F.Silkscreen)"),
    ("bottom_silk", "B.Silkscreen,Edge.Cuts", True, False, "BOTTOM LEGEND (B.Silkscreen) - mirrored"),
]


def plot(layers, mirror, negative, out):
    args = [str(env.KICAD_CLI), "pcb", "export", "pdf", "-l", layers, "--mode-single", "--black-and-white",
            "--subtract-soldermask", "--drill-shape-opt", "2" if "Cu" in layers else "0", "-o", str(out)]
    args += ["--mirror"] if mirror else []
    args += ["--negative"] if negative else []
    subprocess.run(args + [str(env.HW / "timer.kicad_pcb")], check=True, capture_output=True)


def board_rect(page):
    """Board outline on the plotted page: top/bottom Edge.Cuts lines are the only long horizontals."""
    lines = [d["rect"] for d in page.get_drawings() if d["rect"].width > 0.8 * BOARD_W * K and d["rect"].height < 0.5 * K]
    assert lines, "board outline not found"
    top = min(r.y0 for r in lines)
    cx = (lines[0].x0 + lines[0].x1) / 2
    return pymupdf.Rect(cx - BOARD_W / 2 * K, top, cx + BOARD_W / 2 * K, top + BOARD_H * K)


def main():
    tmp = Path(tempfile.mkdtemp())
    doc = pymupdf.open()
    for tag, layers, mirror, negative, title in FILMS:
        src_path = tmp / f"{tag}.pdf"
        plot(layers, mirror, negative, src_path)
        src = pymupdf.open(src_path)
        clip = board_rect(src[0])
        page = doc.new_page(width=PANEL_W * K, height=PANEL_H * K)
        page.insert_text((MARGIN * K, (MARGIN + 4) * K), f"CYTM V5  {title}", fontsize=9)
        page.insert_text((MARGIN * K, (MARGIN + 8.5) * K),
                         f"Scale 1:1   board {BOARD_W:g} x {BOARD_H:g} mm   panel {COLS} x {ROWS}", fontsize=7)
        x_bar = PANEL_W - MARGIN - 10  # 10 mm scale bar
        page.draw_line((x_bar * K, (MARGIN + 8) * K), ((x_bar + 10) * K, (MARGIN + 8) * K), width=1)
        page.insert_text((x_bar * K, (MARGIN + 5.5) * K), "10 mm", fontsize=6)
        for row in range(ROWS):
            for col in range(COLS):
                x0 = (MARGIN + col * BOARD_W) * K
                y0 = (MARGIN + TITLE + row * BOARD_H) * K
                tile = pymupdf.Rect(x0, y0, x0 + BOARD_W * K, y0 + BOARD_H * K)
                page.show_pdf_page(tile, src, 0, clip=clip)
                page.draw_rect(tile, color=(1, 0, 0), width=0.6)  # cut lines
        src.close()
    out = env.OUT / "films_panel_3x2.pdf"
    doc.save(out)
    # preview: all six films side by side
    pix = [p.get_pixmap(dpi=60) for p in doc]
    w, h = pix[0].width, pix[0].height
    sheet = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w * 3, h * 2), False)
    sheet.set_rect(sheet.irect, (255, 255, 255))
    for i, pm in enumerate(pix):
        pm.set_origin((i % 3) * w, (i // 3) * h)
        sheet.copy(pm, pm.irect)
    sheet.save(env.OUT / "films_preview.png")
    print(f"wrote {out.name} ({len(FILMS)} films) and films_preview.png")


if __name__ == "__main__":
    main()
