# sm25 F1 live behavior notes

Read-only observation of
`D:/EnergyPlus-Agent-worktrees/role-kernel-20261009/AI_agent/archive/local_backup/role_runtime_repair/sm25_f1`.
Tool arguments and raw results were resolved from committed `events.jsonl` captures with
`scripts.dev.observe_run._ReadOnlyStore` and `_tool_body`. No model call, prompt injection,
credential read, or frozen-tree write was made by the observer.

## Checkpoint: 28.2 minutes, before the first trial

- Frozen identity: commit `30085ccefdd50ee742ecea2fecf65941ad70f941`, `runtime-v2-20261009`,
  `domain-v56-20261009`; GLM subscription `glm-5.3-flash`, medium. The admitted image is
  `1f_view.png`, 1758 x 1496, SHA-256
  `6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644`.
- The HTTP boundary recorded 14 requests. At the checkpoint, 13 responses had produced about
  65k output tokens. There was no `trial_plan_bim` invocation or result and no candidate plan
  in the trial workspace.
- Executed tools: `inputs` once; `view_image` four times (the initial `{}` call failed because
  `name` was missing, then the full image and two lower-plan crops succeeded); `view_plan_blocks`
  once, returning eight overlapping blocks with complete image coverage; and
  `view_pixel_profile` 28 times.
- All 28 pixel-profile argument objects were distinct. They sampled separate horizontal or
  vertical slices: the first group used grey-wall targets, later calls cross-checked several
  coordinates from another axis, and the next group used cyan door/window targets. Twenty-one
  profiles returned at least one candidate; seven returned none. There is no exact repeated
  measurement in the journal.
- The distinct slices and cross-axis confirmations provide useful local evidence. At the same
  time, 28 profiles and roughly 65k output tokens before any compilable draft is a high
  pre-trial cost. Both observations are supported; distinct calls alone do not establish that
  all measurements were necessary for the eventual plan.
- One deterministic context compaction occurred after the two crop views. It emitted 18
  `remove_image` events. The post-compaction calls used new profile boxes and did not repeat
  `view_image`, `view_plan_blocks`, or any earlier profile arguments, so the event record does
  not show re-reading caused by compaction.
- A contemporaneous process snapshot from the run owner reported about 791 MiB total RSS for
  the wrapper plus three domain servers. It was a point snapshot, not a peak measurement.

No private reasoning text was used in these observations.

## First trial result: 35.7 minutes

- Request 14 returned after about 445.8 seconds with 21,503 output tokens. At event
  `event-000258`, the reader called `trial_plan_bim` with a complete `plan` argument for F1:
  13 partitions, 20 space seeds, 21 openings, two X anchors, two Y anchors, a six-vertex
  L-shaped footprint, dimension chains, assumptions, and basis. The argument omitted the
  required top-level `unresolved` field.
- Event `event-000259` returned `status: failed`, `error_type: plan_format`, with the single
  located error `plan.unresolved: 'unresolved' is a required property`. Validation stopped
  before numeric resolution: `candidate`, `draft`, compiled numeric plan, alignment, overlay,
  measurement bindings, and returned images were all absent or unavailable. Geometry quality
  therefore cannot be inferred from this trial result.
- The failed input remained durable as
  `trial_receipts/trial_001_plan.json` (10,109 bytes, SHA-256
  `00b760a87d7b7381ef6a2d01eee8a036c4cd0e975a58bcd98ce87a7fe8640818`). Its receipt is
  `trial_receipts/trial_001.json` (4,222 bytes, SHA-256
  `cbda1906754b8f73f3a49e014cb86f4fce76d62f32ce7af455121db3e411981a`). The receipt binds
  the same original plan hash and explicitly records `draft: null` and
  `source_geometry_ready: false`.
- The next response was short (371 output tokens). At event `event-000291`, the reader tried
  one `set unresolved` operation containing six concrete open items, rather than resubmitting
  the complete plan. Event `event-000292` rejected it with `No editable plan yet; submit a
  complete plan with valid fields and pixel references`. This second rejection preserved the
  first plan but made no editable draft and produced no new plan artifact.
- At 35.9 minutes the read-only observer showed 16 requests / 15 responses, 87,166 output
  tokens, 36 tool executions, two compactions, no capture errors, and three failed tool
  outcomes: the initial missing-name image call, the format-failed first trial, and the
  rejected operations retry. Request 16 was pending when this milestone note was closed.

Behavior versus output at this milestone: the reader gathered broad, mostly productive local
pixel evidence and produced a substantial first plan argument, but spent 35.7 minutes and 28
profiles before its first compiler feedback. A single missing required list prevented all
geometry checks, and the immediate retry used the operations form even though the receipt had
no editable draft. No accepted or compilable plan exists yet.

## Trials 002-010 and first source candidate

- `trial_002` was the complete resubmission and created `draft_001`. It still had 13
  partitions, 20 seeds and 21 openings. It failed because `room3` and `room4` occupied the
  same compiled space. Its declared footprint was approximately
  `[[282,1055],[519,1055],[519,1224],[1437,1224],[1437,310],[282,310]]`. The original image
  independently shows that the building's upper-right exterior turns down around x=970 to
  y=957 and only the lower wing continues to x=1438. The declaration instead enclosed the
  otherwise blank upper-right rectangle. The receipt's 22 drawing differences did not cover
  exterior-wall or whole-building fidelity, so they could not expose that footprint error.
- The first 31-operation repair was atomically rejected for zero-width/zero-height operation
  boxes. The corrected replay became `draft_002`: it retained the original 13 partitions,
  added five office-bay dividers plus the room-3/4 divider and corridor-stub wall, replaced
  two room-3/4 openings with two wall-hosted doors plus an open passage, and replaced one seed.
  Thus this was a substantive partition and opening repair, rather than only seed deletion.
  `trial_003` then failed on explicit polygonization dangles. Its reported interior drawing
  difference count reached zero, but the report explicitly excluded exterior walls and
  whole-building fidelity; the upper-right footprint error remained visible in the overlay.
- The endpoint repair for those dangles accidentally extended `P3_ab` through several rooms,
  and `trial_004` failed because `roomA` and `roomB` occupied one space. `trial_005` restored
  `P3_ab`, preserving that separation. Subsequent failures led to removal of `corrV`, then
  `strip`, then `corrStub` seeds in trials 006-008. These edits did not delete the newly found
  room partitions, but they reduced the declared seeds from 20 to 17 by collapsing labels in
  connected regions. `trial_008` then failed because `D_entry` had no full-boundary host.
- For `trial_009`, seven exterior openings were moved onto the declared rectangle's boundary:
  east `D_entry`, west `D_wentry`/`W_wA`, north `W_nA`/`W_nB`, and south `W_s1`/`W_s2`.
  It still failed because `W_nB` crossed a boundary junction. After an original-image crop,
  the reader changed only that window's west endpoint from x=505 to x=530. `trial_010` passed
  and created `candidate_01` from `draft_009` with 19 partitions, 17 spaces and 22 openings.
- The successful source candidate remains materially inconsistent with the original. Its
  six-point footprint is
  `[[281,957.5],[512.4,957.5],[512.4,1235],[1438,1235],[1438,310],[281,310]]`, and its source
  plan renders the blank upper-right region as a very large `Z08_F1_Lobby_NE`. The original
  and the automatic overlay instead show the drawn upper-right exterior at about x=970 until
  y=957. The candidate's source self-consistency pass and zero interior drawing differences
  therefore establish internal compilation only; both records explicitly leave original
  drawing fidelity unevaluated. Moving openings to the erroneous outer rectangle helped make
  the geometry compile but did not repair this boundary.
- Candidate evidence is durable: `trial_010.json` SHA-256
  `01fca2b7dc6a16edd9dec9dc6c8453ee2aaac422ddd54a16be1c9aa62fafacce`, candidate source-model
  SHA-256 `ccee8cb4766cd3baaa7e822a53da7dc5ef4f9fd5d78521cfcdc0b37378ba2c26`, original image
  SHA-256 `6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644`, and automatic
  `image_overlays/overlay_001.png` are recorded in the trial result.

After the successful trial, the reader viewed one additional original-image crop and began
submission. Multiple `submit_plan_reading` attempts were rejected first for a wall-reference
schema field and then for note object-reference syntax. Those are handled rejections and had
not yet changed or accepted the candidate at this checkpoint.

## Terminal record: 57.8 minutes

- Submission took ten attempts in total: nine were rejected and the last was accepted at
  event `event-000599`. Early failures corrected an unsupported `wall_reference` field and
  several note references; later attempts repeatedly failed the perimeter `dimension_basis`
  contract. The accepted attempt omitted `wall_reference` and retained three scoped notes.
  The accepted plan itself stayed at 19 partitions, 17 seeds and 22 openings with the same
  erroneous six-point footprint. Its unresolved list records five plan-level uncertainties
  plus the `W_nB` endpoint uncertainty, but it does not identify the upper-right footprint as
  uncertain.
- The final observer record is complete (`partial_tail: false`): 40 requests and 40 responses,
  146,171 output tokens, 57.8 minutes total, four compactions, 67 tool executions, and 21
  failed tool outcomes. Tool counts were 28 `view_pixel_profile`, 12 `view_image`, 3
  `pixel_profile`, 12 `trial_plan_bim`, 10 `submit_plan_reading`, one `inputs`, and one
  `view_plan_blocks`. First trial was at 35.7 minutes, first successful trial at 53.0, first
  submission attempt at 55.5, and accepted submission at 57.6.
- `probe_result.json` reports `probe_status: passed` after about 3,484.8 seconds. All terminal
  runner checks are true: exact task, no auto-added tasks, accepted artifact, exact request
  route, bounded request count, unchanged versions/original/runner, and journal-count match.
  Every recorded request used `glm-subscription-anthropic`, `glm-5.3-flash`, medium; measured
  counts are 40 plan-reader and zero coordinator model requests. The frozen identities remain
  commit `30085ccefdd50ee742ecea2fecf65941ad70f941`, runtime
  `runtime-v2-20261009`, domain `domain-v56-20261009`, original SHA-256
  `6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644`, and runner SHA-256
  `e7545313109375b49a93f19d001d2172ec334d4e0a9e104ef4fbb44fef2c26dd`.
- Terminal accepted-artifact evidence is present and hash-bound. The artifact path is
  `tasks/c1c3b11072b0cc1a10539ba75831d98e96c9275f8d8498eeb15cff1977aa386d/reader_artifact.json`,
  file SHA-256 `c20135f69ff62c2fff1c439b9b06d1bfa08447170237237f2b5e203ef10671d8`, record blob SHA-256
  `8d794b4f61f7a07d39163aa9c12fa5a0bd34f6e4ea8387448a927356116ff920`, accepted plan SHA-256
  `4cee3e7e5c9794e014e3b8522ea819eb2de568fca7f17d7a6d01339d8c8eb3a5`, compiled numeric plan
  SHA-256 `9d21c5ea0475052e52f89c19504e50729176e36cf3c561b7242262d62ee5c506`, and current candidate
  source SHA-256 `266630eba090977af1d7141ff46fae4f5240c294539d528acce24046d45d161f`.

The terminal status is mechanically successful and evidence-complete, but the accepted result
has a blocking drawing-quality defect: it converts a visibly undrawn upper-right exterior/void
into the building's largest room. The success resulted from making openings and topology
self-consistent with that footprint. The run therefore demonstrates terminal evidence and
route isolation, while its accepted geometry should not be treated as faithful to the original
without the scoped evaluator and a corrected boundary.
