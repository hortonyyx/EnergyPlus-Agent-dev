"""Tests for read_ep_end() and the EP exit-code gate in run_simulation.

Coverage:
  - read_ep_end: success line, fatal line, missing file, read-error fallback
  - run_simulation failure path: monkeypatched run_idf returns False + no end file
    → ToolResponse(success=False)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.runner.runner import read_ep_end


# ---------------------------------------------------------------------------
# read_ep_end unit tests
# ---------------------------------------------------------------------------

EP_SUCCESS_LINE = (
    "EnergyPlus Completed Successfully-- 25 Warning; 0 Severe Errors; "
    "Elapsed Time=00hr 00min  7.49sec"
)
EP_FATAL_LINE = (
    "EnergyPlus Terminated--Fatal Error Detected. 3 Warning; 2 Severe Errors; "
    "Elapsed Time=00hr 00min  1.23sec"
)


def test_read_ep_end_success(tmp_path: Path) -> None:
    (tmp_path / "eplusout.end").write_text(EP_SUCCESS_LINE + "\n", encoding="utf-8")
    result = read_ep_end(tmp_path)
    assert result is not None
    assert result["completed"] is True
    assert result["warnings"] == 25
    assert result["severe"] == 0
    assert result["raw"] == EP_SUCCESS_LINE


def test_read_ep_end_fatal(tmp_path: Path) -> None:
    (tmp_path / "eplusout.end").write_text(EP_FATAL_LINE + "\n", encoding="utf-8")
    result = read_ep_end(tmp_path)
    assert result is not None
    assert result["completed"] is False
    assert result["warnings"] == 3
    assert result["severe"] == 2
    assert "Terminated" in result["raw"]


def test_read_ep_end_missing_file(tmp_path: Path) -> None:
    # No eplusout.end written — e.g. segfault before EP output stage.
    result = read_ep_end(tmp_path)
    assert result is None


def test_read_ep_end_accepts_str_path(tmp_path: Path) -> None:
    (tmp_path / "eplusout.end").write_text(EP_SUCCESS_LINE, encoding="utf-8")
    result = read_ep_end(str(tmp_path))
    assert result is not None
    assert result["completed"] is True


def test_read_ep_end_no_counts_returns_minus_one(tmp_path: Path) -> None:
    # Line with "Completed Successfully" but no parseable counts.
    (tmp_path / "eplusout.end").write_text(
        "EnergyPlus Completed Successfully", encoding="utf-8"
    )
    result = read_ep_end(tmp_path)
    assert result is not None
    assert result["completed"] is True
    assert result["warnings"] == -1
    assert result["severe"] == -1


def test_read_ep_end_strips_whitespace(tmp_path: Path) -> None:
    (tmp_path / "eplusout.end").write_text(
        "  " + EP_SUCCESS_LINE + "  \n", encoding="utf-8"
    )
    result = read_ep_end(tmp_path)
    assert result is not None
    assert result["raw"] == EP_SUCCESS_LINE


# ---------------------------------------------------------------------------
# run_simulation failure path — lightweight integration via monkeypatch
# ---------------------------------------------------------------------------


def test_run_simulation_ep_failure_returns_false(tmp_path: Path) -> None:
    """When run_idf returns False and no eplusout.end is written, run_simulation
    must return ToolResponse(success=False) with a meaningful message.

    We monkeypatch EnergyPlusRunner.run_idf (returns False, writes nothing) and
    stub out the ConverterManager / ConfigState layers so the test stays fast
    and dependency-free.
    """
    from src.mcp.tools.workflow import WorkflowTool

    # --- minimal state stub that passes validate_references() ---
    mock_state = MagicMock()
    mock_state.validate_references.return_value = []  # no validation errors
    mock_state.export_yaml.return_value = None
    mock_state.get_summary.return_value = MagicMock(model_dump=lambda: {})

    # --- minimal manager stub with empty IDF objects ---
    mock_manager = MagicMock()
    mock_manager._idf.idfobjects.__getitem__ = lambda self, key: []
    mock_manager._idf.idfobjects = {"SCHEDULE:COMPACT": []}
    mock_manager.convert_all.return_value = None
    mock_manager.save_idf.return_value = None
    # idf property (deep-copy path)
    mock_manager.idf = MagicMock()

    output_dir = str(tmp_path / "ep_out")

    with (
        patch("src.mcp.tools.workflow.ConverterManager", return_value=mock_manager),
        patch("src.mcp.tools.workflow.validate_interzone_surface_pairs", return_value=[]),
        patch("src.mcp.tools.workflow.audit_interzone_surface_pairs", return_value="pair_issues=0"),
        patch("src.mcp.tools.workflow.validate_schedule_completeness", return_value=[]),
        patch("src.runner.runner.EnergyPlusRunner.run_idf", return_value=False),
    ):
        tool = WorkflowTool(state=mock_state)
        response = tool.run_simulation(epw_path="dummy.epw", output_dir=output_dir)

    assert response.success is False
    assert "FAILED" in response.message or "failed" in response.message.lower()
    assert response.data is not None
    # ep_end must be None (no file written) or contain completed=False
    ep_end = response.data.get("ep_end")
    assert ep_end is None or ep_end.get("completed") is False


def test_run_simulation_ep_run_subdir_nests(tmp_path: Path) -> None:
    """With ep_run_subdir set, EnergyPlus runs into output_dir/<subdir>/ (standard
    case layout EP/EP_run) while the IDF stays in output_dir; read_ep_end reads the
    nested eplusout.end."""
    from src.mcp.tools.workflow import WorkflowTool

    mock_state = MagicMock()
    mock_state.validate_references.return_value = []
    mock_state.export_yaml.return_value = None
    mock_state.get_summary.return_value = MagicMock(model_dump=lambda: {})

    mock_manager = MagicMock()
    mock_manager.convert_all.return_value = None
    mock_manager.save_idf.return_value = None
    mock_manager.idf = MagicMock()

    output_dir = tmp_path / "EP"

    def fake_run(*_args, **kwargs):
        # EP must be handed the nested run dir; write a success end file there.
        run_dir = Path(kwargs["output_directory"])
        assert run_dir == output_dir / "EP_run"
        (run_dir / "eplusout.end").write_text(EP_SUCCESS_LINE + "\n", encoding="utf-8")
        return True

    with (
        patch("src.mcp.tools.workflow.ConverterManager", return_value=mock_manager),
        patch("src.mcp.tools.workflow.validate_interzone_surface_pairs", return_value=[]),
        patch("src.mcp.tools.workflow.audit_interzone_surface_pairs", return_value="pair_issues=0"),
        patch("src.mcp.tools.workflow.validate_schedule_completeness", return_value=[]),
        patch("src.runner.runner.EnergyPlusRunner.run_idf", side_effect=fake_run),
    ):
        tool = WorkflowTool(state=mock_state)
        response = tool.run_simulation(
            epw_path="dummy.epw", output_dir=str(output_dir), ep_run_subdir="EP_run"
        )

    assert response.success is True
    assert (output_dir / "EP_run" / "eplusout.end").exists()
