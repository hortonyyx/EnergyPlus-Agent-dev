from scripts.tool_scripts.bim_agent_guidance import (
    CORE, DRAWING_METHOD, MESH_METHOD, REFERENCES, build_guide)


def test_system_prompt_carries_only_the_methods_for_admitted_inputs():
    drawings = build_guide(drawings=True, mesh=False)
    mesh = build_guide(drawings=False, mesh=True)
    assert drawings.startswith(CORE) and DRAWING_METHOD in drawings and MESH_METHOD not in drawings
    assert MESH_METHOD in mesh and DRAWING_METHOD not in mesh
    assert DRAWING_METHOD in build_guide(drawings=True, mesh=True)


def test_reconstruction_reference_is_the_single_drawing_method():
    assert REFERENCES["reconstruction"] is DRAWING_METHOD
