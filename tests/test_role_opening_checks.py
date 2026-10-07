import asyncio
import json
from types import SimpleNamespace

from src.agent.runtime_roles.opening_checks import check_openings


def test_repeated_check_reuses_prior_report_but_changed_geometry_arguments_or_evidence_rechecks(tmp_path):
    run = tmp_path / "bim"
    candidate = run / "candidate_001"
    candidate.mkdir(parents=True)
    source = candidate / "source_model.json"
    source.write_text('{"openings": []}', encoding="utf-8")
    calls = []

    async def call(name, arguments):
        calls.append((name, arguments))
        # Generated reports must not invalidate the next call.
        (candidate / "height_coverage.json").write_text('{"coverage": []}', encoding="utf-8")
        return {"structuredContent": {"candidate": "candidate_001", "conflicts": ["missing W1"]},
                "content": [{"type": "text", "text": "prior conclusion"}]}

    def write(relative, value):
        path = tmp_path / relative
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    session = SimpleNamespace(run_directory=run, _source=lambda name: json.loads(source.read_bytes()),
        frozen=SimpleNamespace(call_tool=call), store=SimpleNamespace(task_directory=tmp_path, write_json=write))

    async def scenario():
        args = {"candidate": "candidate_001"}
        first = await check_openings(session, args)
        second = await check_openings(session, {**args, "review_json": "", "heights_only": False})
        assert len(calls) == 1
        value = second["structuredContent"]
        assert value["status"] == "unchanged"
        saved = json.loads((tmp_path / value["previous_result"]["file"]).read_bytes())
        assert saved["result"] == first
        assert saved["arguments"]["candidate"] == "candidate_001" and saved["dependencies"]["files"]
        assert value["previous_conclusion"]["conflict_count"] == 1
        source.write_text('{"openings": [{"id": "W1"}]}', encoding="utf-8")
        await check_openings(session, args)
        assert len(calls) == 2
        await check_openings(session, {**args, "heights_only": True})
        await check_openings(session, {**args, "review_json": '{"image":"plan.png"}'})
        assert len(calls) == 4
        evidence = run / "elevation_reviews"
        evidence.mkdir()
        (evidence / "review_001.json").write_text('{"new": true}', encoding="utf-8")
        await check_openings(session, args)
        assert len(calls) == 5
        # An unchanged report stays a pointer after session reconstruction.
        assert (await check_openings(session, args))["structuredContent"]["status"] == "unchanged"
        assert len(calls) == 5
        assemblies = run / "plan_assemblies"
        assemblies.mkdir()
        (assemblies / "assembly_001.json").write_text('{"floors": []}', encoding="utf-8")
        await check_openings(session, args)
        assert len(calls) == 6
    asyncio.run(scenario())


def test_failed_checks_are_never_cached(tmp_path):
    calls = []

    async def call(name, arguments):
        calls.append(name)
        return {"isError": True, "content": [{"type": "text", "text": "invalid review"}]}

    session = SimpleNamespace(run_directory=tmp_path, _source=lambda name: {},
        frozen=SimpleNamespace(call_tool=call), store=SimpleNamespace(task_directory=tmp_path))
    async def scenario():
        for _ in range(2):
            assert (await check_openings(session, {"candidate": "candidate_001"}))["isError"]
        assert len(calls) == 2
    asyncio.run(scenario())
