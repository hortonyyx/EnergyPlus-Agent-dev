"""Optional historical solver/source counterexamples."""
import json
from pathlib import Path
from tests.archive_paths import archive_path
from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry.build import build_geometry
from src.agent.geometry.source_model import materialize_source_model


def test_sm21_pipeline_writes_source_sidecar_without_changing_legacy_payload(tmp_path):
    from src.agent.legacy.pipeline import materialize_kernel_geometry
    from src.agent.geometry.specs import building_geometry_dict

    root = Path(__file__).resolve().parents[1]
    original = archive_path('case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/1_correction/correction_geometry_snapped.json')
    geom = CorrectedGeometry.model_validate_json(original.read_text())
    bg, issues = materialize_kernel_geometry(geom, tmp_path)
    assert bg is not None and issues == []
    source = json.loads((tmp_path / "source_model.json").read_text())
    assert len(source["spaces"]) == 14
    assert len(source["openings"]) == 15
    assert source["validation"]["status"] == "pass"
    assert json.loads((tmp_path / "building_geometry.json").read_text()) == building_geometry_dict(bg)


def test_sm24_historical_three_wall_counterexample():
    from scripts.tool_scripts.diagnose_source_partitions import (
        GROUPS, ROOT, extra_internal_walls, sm24_partition_reference, spaces,
    )
    from src.agent.judge.source_partition import compare_partitions

    old = archive_path('case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading')
    geom = CorrectedGeometry.model_validate_json((old / "1_correction/correction_geometry_snapped.json").read_text())
    archived = json.loads((old / "2_modelling/building_geometry.json").read_text())
    reference, id_map = sm24_partition_reference(geom, json.loads(GROUPS.read_text()))
    assert len(extra_internal_walls(archived, id_map)) == 3
    comparison = compare_partitions(spaces(reference), spaces(geom))
    assert comparison["status"] == "severe"
    assert sum(f["code"] == "source_space_split" for f in comparison["findings"]) == 2
    # This explicitly bounded preview retains 11 windows in the full candidate.
    assert len(reference.windows) == 11
    preview = reference.model_copy(update={"windows": []}, deep=True)
    bg = build_geometry(preview, capability_profile="orthogonal_polygon")
    source = materialize_source_model(preview, bg)
    assert len(source["spaces"]) == 8
    assert source["validation"]["status"] == "pass"
