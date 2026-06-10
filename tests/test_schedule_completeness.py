"""Unit tests for the deterministic Schedule:Compact completeness gate.

Mock-based (no IDF fixture / no EnergyPlus): each test builds a tiny fake IDF
exposing just what `src.validator.schedules` reads — `idfobjects[...]` and, per
schedule, `.Name` and `.fieldvalues`. Covers the exact failure that segfaulted
EP 25.1.0 on sm21 (Weekdays + Weekends Holidays, no AllOtherDays).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.validator.schedules import validate_schedule_completeness


@dataclass
class FakeSchedule:
    Name: str
    fieldvalues: list[str]


@dataclass
class FakeIDF:
    schedules: list[FakeSchedule] = field(default_factory=list)

    @property
    def idfobjects(self) -> dict[str, list[FakeSchedule]]:
        return {"SCHEDULE:COMPACT": self.schedules}


def _sched(name: str, *for_clauses: str) -> FakeSchedule:
    """Build a fake schedule; each clause is the text after 'For:' (e.g. 'Weekdays')."""
    fv: list[str] = ["SCHEDULE:COMPACT", name, "Fraction", "Through: 12/31"]
    for clause in for_clauses:
        fv.append(f"For: {clause}")
        fv.append("Until: 24:00")
        fv.append("1.0")
    return FakeSchedule(name, fv)


def test_alldays_is_complete():
    idf = FakeIDF([_sched("S", "AllDays")])
    assert validate_schedule_completeness(idf) == []


def test_allotherdays_catch_all_completes():
    idf = FakeIDF([_sched("S", "Weekdays", "Weekends Holidays", "AllOtherDays")])
    assert validate_schedule_completeness(idf) == []


def test_full_explicit_enumeration_is_complete():
    idf = FakeIDF(
        [
            _sched(
                "S",
                "Weekdays",
                "Saturday",
                "Sunday",
                "Holiday",
                "SummerDesignDay",
                "WinterDesignDay",
                "CustomDay1",
                "CustomDay2",
            )
        ]
    )
    assert validate_schedule_completeness(idf) == []


def test_weekdays_plus_weekends_holidays_is_incomplete():
    # The exact sm21 4_MEP mistake — design + custom days left uncovered.
    idf = FakeIDF([_sched("Office_People_Number", "Weekdays", "Weekends Holidays")])
    issues = validate_schedule_completeness(idf)
    assert len(issues) == 1
    assert "Office_People_Number" in issues[0]
    assert "SummerDesignDay" in issues[0]
    assert "WinterDesignDay" in issues[0]
    assert "CustomDay1" in issues[0]
    assert "CustomDay2" in issues[0]
    # Holiday and the weekdays/weekend ARE covered, so must not be reported missing.
    assert "Holiday'" not in issues[0]
    assert "Saturday" not in issues[0]


def test_weekdays_only_is_incomplete():
    idf = FakeIDF([_sched("S", "Weekdays")])
    issues = validate_schedule_completeness(idf)
    assert len(issues) == 1
    assert "Saturday" in issues[0] and "Sunday" in issues[0]


def test_unknown_token_is_flagged():
    idf = FakeIDF([_sched("S", "AllDays", "Funday")])
    issues = validate_schedule_completeness(idf)
    # AllDays makes coverage complete, so only the unknown-token issue remains.
    assert len(issues) == 1
    assert "Funday" in issues[0]
    assert "unrecognised" in issues[0].lower()


def test_multiple_schedules_each_reported():
    idf = FakeIDF(
        [
            _sched("Good", "AllDays"),
            _sched("Bad1", "Weekdays"),
            _sched("Bad2", "Weekdays", "Weekends Holidays"),
        ]
    )
    issues = validate_schedule_completeness(idf)
    assert len(issues) == 2
    assert any("Bad1" in i for i in issues)
    assert any("Bad2" in i for i in issues)
    assert all("Good" not in i for i in issues)


def test_case_insensitive_tokens():
    idf = FakeIDF([_sched("S", "WEEKDAYS", "weekends holidays", "allotherdays")])
    assert validate_schedule_completeness(idf) == []


def test_empty_idf_is_clean():
    assert validate_schedule_completeness(FakeIDF([])) == []
