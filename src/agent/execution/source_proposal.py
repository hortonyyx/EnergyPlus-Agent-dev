"""Export an agent-supplied legacy geometry proposal as an inspectable source BIM.

This entry point has no correction-run authority.  It stores the proposal as it
was supplied, validates/builds a fresh source BIM candidate, and leaves both
drawing fidelity and human confirmation explicitly unevaluated.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.geometry.source_bim import build_source_bim, source_view_geometry
from src.agent.geometry.source_model import _digest


_PROPOSAL_FIELDS = {"geometry", "assumptions", "unresolved", "enclosure_declaration"}


def _json_bytes(value: object, *, indent: int | None = None) -> bytes:
    """Serialize only ordinary JSON values, rejecting lossy custom encoders."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _validate_proposal(proposal: dict) -> tuple[dict, list[str], list[str], dict | None]:
    if not isinstance(proposal, dict):
        raise TypeError("proposal must be an object")
    unknown = set(proposal) - _PROPOSAL_FIELDS
    missing = {"geometry", "assumptions", "unresolved"} - set(proposal)
    if unknown or missing:
        details = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unknown " + ", ".join(sorted(unknown)))
        raise ValueError("proposal fields: " + "; ".join(details))
    if not isinstance(proposal["geometry"], dict):
        raise TypeError("proposal.geometry must be an object")
    for field in ("assumptions", "unresolved"):
        if not isinstance(proposal[field], list) or any(not isinstance(item, str) for item in proposal[field]):
            raise TypeError(f"proposal.{field} must be a list of strings")
    enclosure = proposal.get("enclosure_declaration")
    if enclosure is not None and not isinstance(enclosure, dict):
        raise TypeError("proposal.enclosure_declaration must be an object")
    return proposal["geometry"], list(proposal["assumptions"]), list(proposal["unresolved"]), enclosure


def _html_list(rows: list[str]) -> str:
    if not rows:
        return "<li>无</li>"
    return "".join(f"<li>{html.escape(row, quote=True)}</li>" for row in rows)


def export_source_proposal(proposal: dict, out_dir: Path, *, provenance: dict | None = None) -> dict:
    """Write a direct agent geometry proposal to a new, inspectable source-BIM directory.

    ``proposal`` contains legacy v1/v2 corrected geometry plus the agent's
    assumptions and unresolved items.  The output is always a new directory;
    this function neither reads nor creates correction acceptance/run records.
    """
    from scripts.tool_scripts.render_geometry_viewer import build_viewer_html

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    report: dict = {
        "mode": "agent_geometry_proposal",
        "status": "not_evaluated",
        "source_geometry_ready": False,
        "model_calls": 0,
        "solver_calls": 0,
        "scope": "agent-supplied geometry to independent source BIM; no correction run or solver stage",
        "drawing_fidelity": "not_evaluated",
        "human_confirmation": "not_evaluated",
        "source_geometry_self_consistency": "not_evaluated",
        "not_evaluated": [
            "original drawing fidelity and completeness",
            "human confirmation",
            "thermal properties and EnergyPlus adaptation",
        ],
    }
    try:
        raw_proposal = _json_bytes(proposal, indent=2)
        (out_dir / "proposal.json").write_bytes(raw_proposal)
        report["proposal_sha256"] = hashlib.sha256(raw_proposal).hexdigest()
        geometry, assumptions, unresolved, enclosure = _validate_proposal(proposal)
        if provenance is not None:
            if not isinstance(provenance, dict):
                raise TypeError("provenance must be an object")
            # Check serializability before retaining it in the report so a bad
            # provenance record cannot prevent error-report persistence.
            _json_bytes(provenance)
            report["provenance"] = provenance

        report["agent_assumptions"] = assumptions
        report["unresolved"] = unresolved

        geom = ensure_corrected_geometry(geometry)
        source = build_source_bim(
            geom,
            capability_profile="orthogonal_polygon",
            enclosure_declaration=enclosure,
        )
        # The standalone BIM must retain the same caveats as its HTML/report.
        # Keep this adapter metadata out of the legacy kernel and its outputs.
        source["assumptions"].extend(assumptions)
        source["generation"] = {
            "method": "agent_geometry_proposal",
            "proposal_sha256": report["proposal_sha256"],
            "provenance": provenance or {},
            "unresolved": unresolved,
            "notes": geom.notes,
        }
        source["source_model_sha256"] = _digest(
            {key: value for key, value in source.items() if key != "source_model_sha256"}
        )
        validation = source["validation"]
        report["source_geometry_self_consistency"] = {
            "status": validation["status"],
            "scope": validation["scope"],
            "findings": validation["findings"],
        }
        report["source_validation"] = validation
        report["status"] = "severe" if validation["status"] == "severe" else "not_evaluated"
        report["source_geometry_ready"] = validation["status"] in {"pass", "warning"}
        report["counts"] = {
            name: len(source[name])
            for name in ("spaces", "boundaries", "openings", "connections", "unbuilt_openings", "unsupported")
        }
        report["source_model_sha256"] = source["source_model_sha256"]

        (out_dir / "source_model.json").write_bytes(_json_bytes(source, indent=2))
        display = source_view_geometry(source)
        (out_dir / "display_geometry.json").write_bytes(_json_bytes(display, indent=2))

        title = "源 BIM 候选：几何检查通过，原图保真待评价"
        if not report["source_geometry_ready"]:
            title = "源 BIM 候选：几何检查有严重问题，仍保留查看结果"
        viewer = build_viewer_html(display, title=title)
        banner = (
            '<aside style="position:fixed;bottom:12px;left:12px;z-index:30;background:white;padding:10px;'
            'max-width:55vw;max-height:45vh;overflow:auto">'
            f"<strong>{html.escape(title)}</strong><br>"
            "模型提交的几何方案；原图保真尚未核对，未经人工确认。"
            "<details open><summary>假设</summary><ul>" + _html_list(assumptions) + "</ul></details>"
            "<details open><summary>未解决项</summary><ul>" + _html_list(unresolved) + "</ul></details>"
            '<a href="report.json">质量与来源记录</a> · <a href="proposal.json">原始方案</a> · '
            '<a href="source_model.json">源模型</a></aside>'
        )
        (out_dir / "viewer.html").write_text(viewer.replace("</body>", banner + "</body>"), encoding="utf-8")
    except Exception as exc:
        report.update(status="error", source_geometry_ready=False, error=f"{type(exc).__name__}: {exc}")
    (out_dir / "report.json").write_bytes(_json_bytes(report, indent=2))
    return report
