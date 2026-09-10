"""Offline developer probe of saved outputs; never a generating model input."""
import json
from pathlib import Path
import sys

from PIL import Image

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.bim_delivery import summarize_delivery
from src.agent.geometry.source_image_overlay import render_source_overlay
from scripts.tool_scripts.run_bim_agent import digest, dump

SOURCE = RUN.parent / "2026-09-10_bim_agent_sm21_run06"
reviews = [json.loads(p.read_text()) for p in sorted((SOURCE / "opening_reviews").glob("*.json"))]
for candidate in ("candidate_02", "candidate_03"):
    source = json.loads((SOURCE / candidate / "source_model.json").read_text())
    dump(RUN / f"delivery_{candidate}.json", summarize_delivery(source, reviews))

image_path = SOURCE / "images/1f_view.png"
with Image.open(image_path) as image:
    overlay, metadata = render_source_overlay(source, image, floor_id="F1",
        x_anchors=[[426, 0], [1815, 15]], y_anchors=[[1087, 0], [347, 8]],
        basis="Developer posthoc selection: original plan's outer grey-wall extents and printed 15000/8000 overall dimensions. No GT used. Wall representative-plane offsets remain approximate.")
overlay.save(RUN / "overlay_F1.png")
metadata.update(image_sha256=digest(image_path),
                input_mode="saved_source_developer_observed_anchors_offline_probe",
                source_candidate="../2026-09-10_bim_agent_sm21_run06/candidate_03",
                generator_input=False)
dump(RUN / "overlay_F1.json", metadata)
print("Saved two source-bound delivery reports and original-image projection; no model/GT calls.")
