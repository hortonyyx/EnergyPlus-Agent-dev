import json

from scripts.tool_scripts import bim_agent_continuation
from scripts.tool_scripts.bim_agent_guidance import (
    CORE, DELIVERY, DRAWING_METHOD, FINISHING, IMAGE_KINDS, MESH_METHOD, MESH_VIEWS, PHOTOS, REFERENCES, TOOLS,
    build_guide)
from scripts.tool_scripts.run_bim_agent import run_guide


def test_system_prompt_carries_only_the_methods_for_the_declared_inputs():
    drawings = build_guide(images="drawings")
    assert drawings.startswith(CORE) and DRAWING_METHOD in drawings
    assert all(text not in drawings for text in (MESH_METHOD, MESH_VIEWS, PHOTOS, IMAGE_KINDS))
    views = build_guide(images="mesh_views")
    assert MESH_VIEWS in views and DRAWING_METHOD not in views and MESH_METHOD not in views
    photos = build_guide(images="photos")
    assert PHOTOS in photos and DRAWING_METHOD not in photos
    mixed = build_guide(images="unknown", mesh=True)
    assert all(text in mixed for text in (IMAGE_KINDS, DRAWING_METHOD, MESH_VIEWS, MESH_METHOD))
    mesh = build_guide(mesh=True)
    assert MESH_METHOD in mesh and DRAWING_METHOD not in mesh and MESH_VIEWS not in mesh
    assert all(build_guide(images=kind).endswith(TOOLS + "\n" + DELIVERY)
               for kind in ("drawings", "mesh_views", "photos", "unknown"))


def test_run_guide_follows_the_manifest_and_legacy_runs_keep_their_old_meaning(tmp_path):
    def guide(**manifest):
        (tmp_path / "inputs.json").write_text(json.dumps(manifest))
        return run_guide(tmp_path)
    assert guide(images={"a.png": {}}, image_kind="photos") == build_guide(images="photos")
    assert guide(images={"a.png": {}}) == build_guide(images="drawings")
    assert guide(images={"a.png": {}}, mesh_input={"sha256": "x"}) == build_guide(images="unknown", mesh=True)
    assert guide(images={}, mesh_input={"sha256": "x"}) == build_guide(mesh=True)


def test_reconstruction_reference_is_the_single_drawing_method():
    assert REFERENCES["reconstruction"] is DRAWING_METHOD


def test_finishing_rule_has_one_source_for_delivery_and_continuation():
    assert FINISHING in DELIVERY and bim_agent_continuation.FINISHING is FINISHING


def test_room_use_and_note_formats_are_given_where_delivery_needs_them():
    assert '"op":"set_space_role"' in DELIVERY and '"op":"replace_note"' in DELIVERY
    assert "Thickness" not in REFERENCES["claims"] and "replace_note" not in REFERENCES["claims"]
    assert "set_component_thickness" in REFERENCES["wall_dimensions"]
    assert '"op":"replace_note"' in REFERENCES["edits"]
