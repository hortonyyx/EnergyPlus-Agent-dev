# partA Correction Constraint Set Design Review

Date: 2026-06-07
Reviewer: Codex
Scope: Design-direction review for `AI_agent/logs/review/request/2026-06-07_partA_correction_constraint_set_request.md`. No code, skill, or contract implementation reviewed.

## Verdict

整体 sound，可以按这个方向推进，但需要三处修正后再逐篇落地。

1. **切割轴 "确定性 vs 判断" 是对的主轴**，比按现象或数据通道切更适合作为未来 codify 接缝。
2. **五篇分解基本成立**，但 A0 不能只是常数表；A0 必须同时定义 evidence / conflict / correction / validation 的结构化契约。否则 A1/A2/A3 会各自发明一套审计口径。
3. **A1/A2 不能被描述成"几乎无误修风险"的纯机械步骤**。它们在"已选定证据、已判定同一意图墙/轴"之后是确定性的；但证据身份、同一墙聚类、合法错位 vs 抖动的判别必须有升级到 A3 的机制。

我建议的落地序微调为：

1. **A0**
2. **A1-min + A2 同批**（A1 写最小坐标/中线/世界系契约，A2 写规范轴与吸附）
3. **A4 stub**
4. **A3**

不要把 A2 独立写在 A1 前面。运行时 A1 在 A2 上游，如果 A2 先写，极容易把世界坐标、中线约定、立面映射这些前提暗埋在 A2 里，之后拆不干净。

## Findings

### 1. High - A0 必须升级为"证据与审计契约"，不能只是容差常数脊柱

Evidence:
- `recognition_modeling_capability.md` 已把 `corrections[]` 定为放宽约束的前提，否则无法区分"看错 vs 改错"。
- 当前 `phase2/rules.md` 的 9 个 `*_specs` 都是自然语言，下游不可稳定解析 corrections / conflicts。
- sm21 的真因不是单个阈值缺失，而是 phase1 把估算坐标、尺寸链、低置信立面信息混在同一等级里。

Risk:
如果 A0 只列 50mm、闭缝阈值、±5% WWR 等常数，A1/A2 可以"修"几何，A3 可以"仲裁"冲突，但没有统一方式证明这次修改来自哪个证据、触发哪个规则、改变了多少、是否允许。这样会重演 prose-only prompt 时代的问题。

Recommended action:
A0 至少定义：

- evidence grades: `direct_measurement | transcribed_dimension | estimated_stroke | inferred_topology | prior | unknown`;
- conflict types: `stroke_vs_dimension | cross_floor_axis_jitter | checksum_failure | facade_plan_mismatch | semantic_size_prior | unsupported_geometry`;
- correction schema: source ids, original value, resolved value, rule id, threshold, delta, confidence before/after, whether it changes topology;
- validation schema: coverage, min width/edge, checksum, containment, residuals, unsupported flags;
- mode-specific tolerance policy: `room_identity`, `use_grouped_rooms`, and `perimeter_core` may use different correction strictness.

If A0 does this, five篇分解成立。If A0 stays as constants only, add an A5 "diagnostics / verifier contract" document.

### 2. High - A1/A2 are codifiable only after evidence selection; ambiguous inputs must escalate to A3

Evidence:
- A1 wants to solve inner-surface vs centerline drift, e.g. corridor wall at x=0.24 m.
- A2 wants to cluster canonical axes and unify cross-floor jitter.
- sm21 shows a 5cm cross-floor jitter created degenerate EP fragments, but the current phase2 rules also intentionally allow real cross-floor partition mismatch.

Risk:
Axis snapping is a perfect tool for noise and a dangerous tool for real staggered geometry. If A2 clusters purely by coordinate proximity, it can erase legitimate offsets, shafts, transfer walls, or non-aligned floors. If A1 always converts an inner face to a centerline without wall-thickness provenance, it can introduce a confident-looking false correction.

Recommended action:
Define A1/A2 as deterministic transforms over an already typed evidence graph:

- A1 deterministic path: coordinate frame, facade local-to-world, z-stack, known wall-thickness centerline conversion.
- A1 escalation path: unknown side of wall, missing thickness, conflicting origin, facade-plan orientation conflict -> A3.
- A2 deterministic path: cluster axes within tolerance only when evidence says "same intended axis/wall".
- A2 escalation path: offset exceeds jitter tolerance, semantic evidence says different wall/shaft/stair, or clustering would delete a real room -> A3 / unsupported.

This keeps "future codify 接缝"成立 without pretending all normalization decisions are mechanical.

### 3. Medium - Five documents are not too many, but each must have a crisp output contract

Assessment:
- **A0**: worth single列。It is the schema and policy spine, not just constants.
- **A1**: clean if scoped to coordinate frames / centerline convention / z and facade transforms.
- **A2**: clean if scoped to canonical axis sets, snapping, chain closure, grid quantization, and minimum-sliver prevention.
- **A3**: clean if scoped to decisions that require choosing among plausible interpretations.
- **A4**: worth separating as data, because priors will grow and should not be mixed with decision rules.

Main boundary risk:
A2 "dimension-chain = total length closure" can require A3 if multiple chains conflict. A3 can require A4 priors, but A4 should never decide on its own.

Recommended action:
Each document should start with:

- input artifact fields it consumes;
- output artifact fields it may write;
- when it must emit `corrections[]`;
- when it must emit `conflicts[]` / unsupported instead of fixing;
- whether it can change topology.

That one header convention will keep the five docs from becoming five piles of prompt prose.

### 4. Medium - Runtime should be staged with feedback, not a one-way A1 -> A2 -> A3 line

The proposed runtime order is basically right: normalize frame, regularize axes, then arbitrate remaining conflicts. But real cases need feedback:

1. A1 normalizes obvious coordinate frames.
2. A2 attempts deterministic snapping / checksum closure.
3. If A2 detects an over-tolerance conflict, it calls A3 to choose evidence or mark unsupported.
4. A2 re-runs on the resolved evidence.
5. Final validation emits residuals and corrections.

Example:
If dimension chain and stroke axes conflict, A2 can detect the failure, but A3 must choose the dimension chain or preserve the stroke. After that choice, A2 can deterministically build the canonical axis set.

Recommended action:
Write the runtime as **A1 -> A2-detect -> A3-resolve(+A4) -> A2-apply -> validate**, while keeping the conceptual docs A1/A2/A3 separated.

### 5. Medium - A4 redline is right but not sufficient; priors need hard gating

Evidence:
- `recognition_modeling_capability.md` already warns that priors can "fix" a real 1.2m equipment room away.
- `phase2/rules.md` says not to invent roles unsupported by OCR labels and geometry.

Risk:
"Priors never override consistent measurement" is necessary, but not enough. A real small room may have low-confidence geometry but high-confidence OCR label ("Storage", "Shaft", "WC"). A naive prior could still normalize it into an office bay because the measurement is not "consistent" enough.

Recommended action:
Make A4 usage rules hard:

- Priors first emit warnings / plausibility scores, not corrections.
- Prior-driven correction is allowed only when evidence is missing, contradictory, or below confidence threshold.
- If semantic evidence supports an unusual small room, keep it or mark `conflict`, do not normalize it.
- Every prior use must write `corrections[]` or `conflicts[]` with `prior_id`.
- Priors should be typed by building type and space type; do not use one global minimum-room table for all spaces.

This is the real guardrail against "修掉真实异常设计".

### 6. Medium - `corrections[]` should be a hard requirement, but only for material changes

Verdict:
Yes, make it hard.

Refinement:
Not every rounding artifact needs a verbose correction entry. A0 should separate:

- **normalization events**: harmless formatting / final coordinate rounding within output precision;
- **corrections**: changed source value, changed topology, closed gap, snapped axis, selected one evidence channel over another;
- **conflicts**: unresolved or over-threshold ambiguity;
- **unsupported flags**: cannot correct safely under current regime.

Hard rule:
If a transformation changes geometry beyond output rounding, changes topology, changes evidence authority, or invokes a prior, it must be logged. If it cannot be logged with source ids and a rule id, the model should mark unsupported rather than silently proceed.

### 7. Medium - partA is shared infrastructure, but A3/A4 should be mode-aware to avoid over-investing for perimeter_core

Evidence:
- The zonification review concluded `perimeter_core` needs reliable envelope/facade/WWR more than high internal-wall precision.
- `recognition_modeling_capability.md` says partA is shared by both legs, but also says the true leg difference is zonification granularity and correction precision demand.

Assessment:
A1/A2 are still worth doing now. They are cheap, mostly deterministic, and support the faithful `room_identity` leg plus `use_grouped_rooms`. They also improve facade/window anchoring and room attribution even for `perimeter_core`.

Risk:
A3/A4 are where over-investment and over-correction live. If the future path chooses `perimeter_core`, detailed internal room arbitration may be unnecessary except for major exceptions and attribution.

Recommended action:
Make A0 define method profiles:

- `room_identity`: full partA strictness, internal walls matter.
- `use_grouped_rooms`: room-cell closure and adjacency matter; exact wall thickness less important.
- `perimeter_core`: envelope, facade, floor height, roof/ground, and WWR strict; internal walls only for exception spaces and attribution.

Then A3/A4 can be invoked conservatively under `perimeter_core`, aggressively only under `room_identity`.

### 8. Low - phase1 provenance belongs in this request as an input contract, but implementation belongs to phase1 skill work

Assessment:
This belongs in partA as a dependency because partA cannot correct safely if phase1 does not preserve provenance. But it should not be implemented inside A1/A2/A3.

Recommended action:
A0 should include an "upstream input contract" section:

- phase1 must not emit estimated coordinates as indistinguishable from measured strokes;
- strokes, dimension chains, OCR labels, facade windows, and self-check notes need structured provenance/confidence;
- estimated geometry should link to the dimension ids or inference rule that produced it;
- partA may still run on legacy phase1 JSON, but must degrade confidence and produce more conflicts.

Then create / update phase1 skill docs separately when implementation starts.

## Direct Responses To The 8 Focus Questions

1. **切割轴对不对**: 对。It is the best primary axis. Add a third visible category: diagnostics / validation / evidence contract. This can live in A0 or become A5 if A0 would get too crowded.

2. **五篇分解是否干净**: 基本干净。A0 and A4 are worth separating. The split is not too碎 for a skill library if each document has a short input/output header. Watch A2/A3 overlap around "which dimension chain is authoritative".

3. **"确定性篇=未来 codify 接缝"是否成立**: Mostly. A1/A2 can be codified as transforms and validators, but only after evidence is typed. Evidence selection and ambiguous clustering remain A3.

4. **落地序合不合理**: Adjust. Use `A0 -> A1-min + A2 -> A4 stub -> A3`. A2 before A1 is risky because A2 needs coordinate-frame and centerline assumptions. It is fine to implement A1-min and A2 in one batch.

5. **红线够不够**: Directionally yes, mechanically no. Add prior gating, semantic exception handling, prior ids in corrections/conflicts, and confidence downgrades. A real small service room should survive if semantic evidence supports it.

6. **`corrections[]` 硬要求对不对**: Yes. Make it structured and mandatory for material geometry/evidence changes. Distinguish small output rounding from actual corrections.

7. **与 zonification 精度耦合**: A1/A2 are not wasted even if `perimeter_core` wins later. A3/A4 should be mode-aware and conservative unless target method is `room_identity` or `use_grouped_rooms`.

8. **phase1 配套小改放这儿对不对**: Yes as an upstream contract; no as implementation scope. partA should specify the provenance fields it needs, then phase1 skill changes can be handled as a separate implementation step.

## Recommended Document Shape

### A0 - Tolerances, Evidence, Corrections, Validation

Include:

- tolerance classes, not just values;
- evidence grades and confidence model;
- correction / conflict / unsupported schema;
- method profiles by zonification target;
- validation checklist and fail/continue policy;
- upstream phase1 provenance requirements.

### A1 - Coordinate Normalization

Include:

- world coordinate system;
- plan/facade local-to-world transforms;
- z-stack and floor-height reconciliation;
- wall centerline convention;
- known wall-thickness conversion;
- escalation rules for ambiguous wall side / origin / facade orientation.

### A2 - Regularization And Snapping

Include:

- canonical axis set construction;
- cross-floor axis clustering;
- grid quantization after canonicalization, not before;
- dimension-chain checksum and closure;
- minimum width / min sliver prevention;
- topology-preserving snapping rules;
- escalation triggers to A3.

### A4 - Architectural Priors Stub

Include first:

- window sill / height bands;
- door / window width ranges;
- common modular grids;
- room-size priors by space type;
- building-type scoping;
- prior ids and confidence.

Keep it as data. No correction rule should live here.

### A3 - Conflict Arbitration And Completion

Include:

- channel priority under explicit conflict classes;
- missing-value completion;
- prior usage rules;
- unsupported policy;
- confidence downgrade policy;
- how to call A2 again after a decision.

## Acceptance Criteria For The Future Skill Docs

- sm21 case can explain all known corrections: 0.24m wall-side gap, 5cm cross-floor jitter, dimension-chain vs stroke conflict, 1.2m ghost room suspicion.
- Every correction has source ids and rule ids.
- A2 cannot merge axes solely by coordinate proximity if semantic evidence says they are distinct.
- A4 prior cannot override high-confidence evidence and cannot erase a labeled service/shaft/WC room without a conflict.
- `perimeter_core` mode can skip high-detail internal-room arbitration while still preserving envelope/facade/WWR correctness.
- Legacy phase1 JSON can run with degraded confidence, but new phase1 provenance fields are explicitly requested.

## Sources Checked

Internal:

- `AI_agent/logs/review/request/2026-06-07_partA_correction_constraint_set_request.md`
- `AI_agent/capability/recognition_modeling_capability.md`
- `skills/energyplus_mcp_twostep/phase2/rules.md`
- `AI_agent/logs/review/review/2026-06-07_zonification_approach_review.md`

No external research was needed for this design-direction review.

No code changes requested from this review.
