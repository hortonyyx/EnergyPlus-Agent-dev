"""Evidence sheet for the PERCEPTION step: which two face lines are one wall?

⭐ 2026-08-24.  The guide's ruling is that code enumerates pairing candidates and
the MODEL chooses.  A model cannot choose from a 374-row JSON table it cannot
see, so this renders the candidates onto the drawing: every face line drawn over
its own real runs, labelled with its id, at a zoom where a 5 px gap between two
faces of one wall is visible.

⛔ It is a VIEW.  Nothing here is recomputed: positions and runs come from the
product's own observation layer, candidate links from its own candidate list.
It exists so the perception step has the same evidence a human would demand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DIM = 0.30
C_COL = (255, 90, 90)      # vertical face lines (constant x)
C_ROW = (60, 160, 255)     # horizontal face lines (constant y)
C_TXT = (255, 255, 0)


def main(doc_path: str, image: str, out_path: str, *, scale: int = 2) -> int:
    doc = json.loads(Path(doc_path).read_text())
    im = Image.open(image).convert("RGB")
    im = Image.blend(Image.new("RGB", im.size, (255, 255, 255)), im, DIM)
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    except OSError:
        font = ImageFont.load_default()

    for f in doc["observations"]["face_lines"]:
        c0, c1 = (v * scale for v in f["support_cols_px"])
        col = C_COL if f["axis"] == "col" else C_ROW
        for a, b in f["runs_px"]:
            a, b = a * scale, b * scale
            box = [c0 - 1, a, c1 + 1, b] if f["axis"] == "col" else [a, c0 - 1, b, c1 + 1]
            d.rectangle(box, fill=col)
        a0 = min(min(r) for r in f["runs_px"]) * scale
        pos = (c1 + 3, a0) if f["axis"] == "col" else (a0, c1 + 3)
        d.text(pos, f["id"][1:], fill=C_TXT, font=font)

    im.save(out_path)
    print(f"{out_path}  {im.size}  face_lines={len(doc['observations']['face_lines'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3],
                          scale=int(sys.argv[4]) if len(sys.argv) > 4 else 2))
