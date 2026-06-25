# 2026-06-25 Reading Scaffold P0 Restore Review

Verdict: **APPROVE-WITH-CHANGES**

No blocking finding: the P0 intent is mostly restored, and I do not see the reading-honest architecture being erased. I do see a few concrete issues that should be fixed before treating this as a clean restore.

## Findings

### 1. [major] `dimensions[]` example has P1a fields, but the sample chain fails the linter closure check

Evidence:
- `skills/intake_pipeline/0_reading/guide.md:191-216` shows `D1` as `role="overall"`, `value_m=15.00`, and only one segment `D2` with `value_m=5.00` in the same `chain_id`.
- `src/validator/checks/reading.py:382-417` checks `Σ segment values == overall value` per `chain_id`.
- Targeted linter probe on the exact example shape returns `reading.dimension_chain_closure = fail`, with `overall=15.0`, `segment_sum=5.0`.

Why it matters:
Candidate 16 is specifically about making `dimensions[]` structurally usable. Field names now match P1a, but the copied example demonstrates a chain that does not close. A reading agent may copy the shape and produce a flagged artifact despite following the guide.

Suggested fix:
Make the example internally closing, e.g. `overall=15.00` plus segment entries that sum to 15.00, or use a one-segment chain where the segment value is also 15.00. Prefer the former because it demonstrates the intended segment closure.

### 2. [major] `session_kickoff.md` is not just a pointer, and its elevation recap directly conflicts with `guide.md`

Evidence:
- `skills/intake_pipeline/0_reading/session_kickoff.md:8-9` says durable rules are not duplicated and the recap is only a pointer.
- `skills/intake_pipeline/0_reading/session_kickoff.md:21-40` then restates durable operating rules.
- `session_kickoff.md:33-36` says elevations should emit image-local facade fields, `view_facade`, and never write east/west into the in-image axis.
- `skills/intake_pipeline/0_reading/guide.md:88-92`, `guide.md:107-109`, and `guide.md:288-300` still require `facade_axis_note` with world axis/sign and say correction translates using it.
- `src/agent/reading/schema.py:13-18` agrees with the kickoff/P1b direction, not with the current guide prose.

Why it matters:
The root cause being fixed was drift in duplicated prompt discipline. The new kickoff reintroduces a second durable summary, and one part already disagrees with the guide. Even if the P1b guide conflict is known residual work, the kickoff should not become the second place where that unresolved contract lives.

Suggested fix:
Either make `session_kickoff.md` a true pointer plus workflow shell, or first align `guide.md` to the image-local P1b facade contract and then keep only a very short recap that cannot contradict the guide.

### 3. [major] The new versioned kickoff file is currently untracked

Evidence:
- `git status --short --untracked-files=all` shows `?? skills/intake_pipeline/0_reading/session_kickoff.md`.
- `git ls-files` shows `skills/intake_pipeline/0_reading/guide.md` and `AI_agent/guides/new_case_guide.md` tracked, but not `session_kickoff.md`.

Why it matters:
Versioning the kickoff prompt is one of the main fixes. If this file is not added, the repository can land the pointer in `new_case_guide.md` without landing the target file, recreating the non-versioned prompt problem in practice.

Suggested fix:
Add `skills/intake_pipeline/0_reading/session_kickoff.md` to version control with the P0 restore.

### 4. [minor] "`dimensions[]` with honest `provenance`" implies a field that `Dimension` does not define

Evidence:
- `guide.md:52-54` and `session_kickoff.md:23-25` say the dimension chain should carry honest `provenance`.
- `src/agent/reading/schema.py:55-70` defines `Dimension` fields: `text`, `text_verbatim`, `value_m`, `from`, `to`, `axis`, `chain_id`, `role`, `order`, `anchor`, `note`.
- `provenance/confidence/dimension_refs` are `Stroke` fields at `schema.py:35-46`, not `Dimension` fields.

Why it matters:
This will not fail parsing because `extra="allow"` is enabled, but it can teach agents to emit an unvalidated `Dimension.provenance` field or to believe dimension provenance is checked when it is not.

Suggested fix:
Reword to "dimension chain with literal OCR (`text_verbatim`), parsed value, chain metadata, and honest stroke provenance where coordinates are dimension-derived", unless a real `Dimension.provenance` field is intentionally added later.

### 5. [minor] Worktree contains extra untracked/generated files outside the stated restore scope

Evidence:
- Tracked-but-unlisted docs are modified: `AI_agent/CLAUDE.md`, `AI_agent/plan.md`.
- Untracked generated EP inputs are present under:
  - `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/EP/temp_20260623_163602.{idf,yaml}`
  - `case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/EP/temp_20260624_040328.{idf,yaml}`
- The requested backup/old scaffold comparison files are ignored by `.gitignore:7` (`20*_*/`) and therefore are not visible in normal `git status`.

Why it matters:
This does not change the P0 markdown semantics, but it is easy to accidentally land unrelated state or fail to land intended comparison artifacts.

Suggested fix:
Before committing, explicitly decide whether `AI_agent/CLAUDE.md` and `AI_agent/plan.md` are part of the doc restore, add the new kickoff file, and keep generated EP temp files out of the change.

## Requested Checks

1. **§0.1 coordinate hard line vs reading-honest**: acceptable. The new language keeps the default pressure high ("read every coordinate as final") while preserving recoverability only when the redundant dimension channel survives. I do not read it as permission to fill sloppy coordinates, because it explicitly says not to lean on correction and requires either a backing dimension chain or precise reading.

2. **Anti-over-segmentation candidate 14 preserved**: yes. `guide.md:66-68` keeps two-channel discipline; `guide.md:314-318` keeps and strengthens the dimension tick / window-jamb negative examples. `reading_guide.md:153-154` also still has the positive wall-vs-tick test.

3. **`dimensions[]` fields vs schema P1a**: field names and enum values are aligned: `text_verbatim`, `value_m`, `chain_id`, `role`, `order`, `anchor`, plus legacy-compatible `from` alias, `to`, `axis`, `note`. `anchor: null` is legal because `Dimension.anchor` is optional. However, the example chain itself does not close; see finding 1.

4. **`session_kickoff.md` pointer-only check**: not clean. It is concise, but it duplicates durable rules and already conflicts with `guide.md` on elevation orientation; see finding 2.

5. **P0 coverage / over-restore**: candidates 1, 2, 4, 12, and 16 are present in substance. I do not see over-restoration that weakens reading-honest. Candidate 16 needs the example closure fix, and the kickoff recap should be reduced/aligned so it does not create the next drift point.

6. **`new_case_guide.md` relative path**: correct. From `AI_agent/guides/new_case_guide.md`, `../../skills/intake_pipeline/0_reading/session_kickoff.md` resolves to the repo-root `skills/...` path. The single-line command also uses the repo-root path expected by the current workflow.

## Verification

- Read `git status --short --untracked-files=all`.
- Reviewed diffs for `skills/intake_pipeline/0_reading/guide.md` and `AI_agent/guides/new_case_guide.md`.
- Read new `skills/intake_pipeline/0_reading/session_kickoff.md`.
- Cross-checked `src/agent/reading/schema.py` and `src/validator/checks/reading.py`.
- Read `AI_agent/logs/review/2026-06-25_scaffold_degradation_audit/RECONCILED_candidates.md`.
- Ran a targeted linter probe against the new `dimensions[]` example shape; it confirmed the chain-closure failure.
