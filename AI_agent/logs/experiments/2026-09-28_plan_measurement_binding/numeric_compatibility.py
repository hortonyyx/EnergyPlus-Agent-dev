"""Corrected historical compiler comparison; no model invocation or old writes."""
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels

HERE = Path(__file__).resolve().parent


def main():
    rows = []
    for number in (57, 58, 83):
        run = next(HERE.parent.glob(f"*_run{number}"))
        for path in sorted(run.glob("plan_drafts/*/plan.json")):
            original_hash = digest(path)
            raw = json.loads(path.read_text())
            image = json.loads((path.parent / "input.json").read_text())["image"]
            inventory = json.loads((run / "inputs.json").read_text())["images"][image]

            def no_profile(_):
                raise AssertionError("Numeric plans must not load profiles")

            resolved, bindings = resolve_plan_pixels(raw, image=image,
                image_sha256=inventory["sha256"], load_profile=no_profile)
            assert resolved == raw and not bindings
            outcomes = []
            for plan in (raw, resolved):
                try:
                    proposal, mapping = compile_plan_partition(plan,
                        image_size=tuple(inventory["size"]), image_name=image)
                    outcomes.append(dict(proposal=proposal, mapping=mapping))
                except ValueError as error:
                    outcomes.append(dict(error=str(error), kind=type(error).__name__))
            assert outcomes[0] == outcomes[1]
            assert digest(path) == original_hash
            rows.append(dict(run=number, draft=path.parent.name, sha256=original_hash,
                identical=True, compiled="proposal" in outcomes[0],
                error=outcomes[0].get("error")))
    assert any(row["compiled"] for row in rows)
    report = dict(model_calls=0, comparisons=rows,
        supersedes="report.json numeric_historical_compatibility only: first script passed a list as image_size, so all compiler calls stopped before geometry. Declaration equality and actual Toolkit wall replay remain valid.")
    path = HERE / "numeric_compatibility.json"
    with path.open("x") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(drafts=len(rows), compiled=sum(row["compiled"] for row in rows),
                         identical=all(row["identical"] for row in rows))))


if __name__ == "__main__":
    main()
