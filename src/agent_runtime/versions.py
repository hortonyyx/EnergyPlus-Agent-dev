"""Six local version stamps; remote aliases are explicitly unverified."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from src.harness_contracts import RemoteModelIdentity, SourceRef, VersionManifest, VersionStamp
from .agent_registry import agent_version_record
from .store import EventStore


def make_versions(store: EventStore, *, root: Path, prompt: str,
                  tools: list[dict], parameters: dict, route: dict,
                  code_paths: tuple[str, ...] = ()) -> VersionManifest:
    root = root.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    # Working-tree file hashes also identify an uncommitted development run.
    sources = {}
    for relative in ("src/agent_runtime", "src/harness_contracts", *code_paths):
        path = root / relative
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        if path == root / "src/agent_runtime":
            files = sorted((*files, path / "model_profiles.json"))
        for file in files:
            sources[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
    code = store.source("code-manifest", {"commit": commit, "files": sources})

    def stamp(name, value):
        evidence = store.source(name, value)
        return VersionStamp(identifier=evidence.blob.sha256, evidence=evidence)

    agent = agent_version_record(root)
    agent_evidence = store.source("agent-version", agent)
    lock = root / "uv.lock"
    if not lock.is_file():
        raise ValueError("a dependency lock is required for a versioned run")
    lock_ref = store.put_bytes(lock.read_bytes(), "text/plain")
    prompt_ref = store.put_bytes(prompt.encode("utf-8"), "text/plain")
    return VersionManifest(
        code_commit=VersionStamp(identifier=commit, evidence=code),
        dependency_lock=VersionStamp(identifier=lock_ref.sha256, evidence=SourceRef(
            source_id="dependency-lock", source_kind="runtime", locator="uv.lock", blob=lock_ref)),
        agent_version=VersionStamp(identifier=agent["version_id"], evidence=agent_evidence),
        prompt=VersionStamp(identifier=prompt_ref.sha256, evidence=SourceRef(
            source_id="system-prompt", source_kind="runtime", locator="system-prompt", blob=prompt_ref)),
        tool_definitions=stamp("tool-definitions", tools),
        inference_parameters=stamp("inference-parameters", parameters),
        model_route=stamp("model-route", route),
        remote_model=RemoteModelIdentity(route_id=route["route_id"], remote_alias=route["model"], alias_status="unverified"))
