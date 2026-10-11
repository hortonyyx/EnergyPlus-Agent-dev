"""Optional full-prefix validation of an explicitly selected original frozen journal."""
import json
import os
from pathlib import Path
import pytest
from src.agent_runtime.store import EventStore
from src.harness_contracts.incremental import EventValidationIndex
from src.harness_contracts import BudgetAmounts, BudgetEventPayload, BudgetLedger
from tests.test_runtime_journal_incremental import _accept


def test_frozen_1269_events_all_prefixes_match_full_validation():
    source = os.environ.get("RUNTIME_JOURNAL_FROZEN_RUN")
    if not source:
        pytest.skip("set RUNTIME_JOURNAL_FROZEN_RUN to the read-only frozen run")
    directory = Path(source)
    metadata = json.loads((directory / "journal.json").read_bytes())
    limit = BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"]))
    events = EventStore.read_events(directory / "events.jsonl")
    assert len(events) == 1269
    index = EventValidationIndex(run_id=metadata["run_id"], root_task_id=metadata["task_id"], budget_limit=limit)
    full = object.__new__(EventStore)
    full.root_task_id, full.budget_limit = metadata["task_id"], limit
    for count, event in enumerate(events, 1):
        log = full._validate_events(events[:count])
        _accept(index, event)
        assert tuple(index.events_by_id.values()) == log.events
        if isinstance(event.payload, BudgetEventPayload):
            ledger = BudgetLedger(total_limit=limit,
                reservations=tuple(e.payload.reservation for e in index.budget.reservations.values()),
                settlements=tuple(e.payload.settlement for e in index.budget.settlements.values()))
            assert index.budget._amounts() == ledger.committed
            assert index.budget.available == ledger.available
