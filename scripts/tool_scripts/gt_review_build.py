#!/usr/bin/env python3
"""Build a GT candidate review bundle from a conversion request (the missing third CLI).

Pairs with ``gt_review_sign.py`` (human G10 signature) and ``gt_review_rerun.py``
(mandatory signed second conversion).
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1
from src.agent.judge.tarch_review_bundle import build_review_bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dxf", type=Path, required=True)
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--raster-dir", type=Path, required=True,
                    help="directory holding the case rasters (only *.png are bundled)")
    ap.add_argument("--out", type=Path, required=True, help="bundle dir; must not exist")
    args = ap.parse_args()

    request = TarchConversionRequestV1.model_validate_json(args.request.read_bytes())
    staging = Path(tempfile.mkdtemp(prefix="gt_rasters_"))
    try:
        for png in sorted(args.raster_dir.glob("*.png")):
            shutil.copy2(png, staging / png.name)
        out = build_review_bundle(args.source_dxf, request, output_dir=args.out,
                                  raster_root=staging, review_annotations={})
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print(f"bundle: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
