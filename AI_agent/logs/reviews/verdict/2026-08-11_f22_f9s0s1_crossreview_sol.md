# F-22 + F-9 S0/S1 交叉审阅裁决（sol）

- 日期：2026-08-11
- 审阅席：GPT / sol
- 仓库：`/workspaces/EnergyPlus-Agent-dev`
- 裁决：**CHANGES REQUIRED**
- 落库意见：**当前批次不得落库**。先消除 1 个 BLOCKER 与 3 个 MAJOR；MINOR 可随修复一并收口或形成有 owner/阶段的明确债项。
- 发现计数：**1 BLOCKER / 3 MAJOR / 3 MINOR / 1 NIT**

## 1. 结论先行

机械绿门属实，但不能证明本批语义正确。我独立跑得：

```text
2447 passed, 10 xfailed, 209 warnings in 356.56s (0:05:56)
exit=0
```

F-22 对 **schema v3 / `orthogonal_polygon` / post-F-17 deterministic output** 的修法成立：真实 `run_2026-08-11_continuous_e2e` 外包 8 边均 `delta=0.0/status=complete`，内墙 `extent_drift=0`。但施工把这一事实无条件推广到所有 `1_correction` 产物；当前 CLI 默认仍是 `rectangular`，对应 schema v1，而 schema v1 的权威模型注释仍明确为 centerline。当前判卷器会把一个仓内真实 legacy v1 产物的 N/E 两边判成 `miss`。新声明又只是未被执行路径读取的常量，不能充当守卫或 provenance。因此这是默认受支持路径上的错误，不可用“现代真实产物变好”抵消。

F-9 S0 的“不接 live production”边界守住了；S1 的共享 truth table 方向也对。但 S0 已用 V1/V2 名称冻结的合同缺少设计 v2.1 明定的 identity/hash-chain 字段，并能接受跨 raw/resolver 绑定重放及不可能的 `accepted` decision。S1 还留下一个真实 live 入口 `derive_facade_frame` 自算 sign；AST 锁对当前缺口和多种等价写法均无感。

六个重点问题的直接答案：

1. **声明必须显式限定范围；需要可执行守卫与可审 provenance；本批不能无守卫落库。** 最低要求是对不具备可信 `schema v3 + orthogonal_polygon + normalized-output` 身份的产物 fail closed；若要继续支持 schema v1，则须经批准保留 schema-aware normalization，不能再宣称单一无条件外皮口径。
2. 两把改写老锁**不是空锁**。我在内存中分别恢复被删公式，两把均在目标断言处转红，exit 均为 1。
3. 9→10 两把字面值锁有效。关键锁当前侧为 10、陈旧侧为 9、重算后为 10，没有把两侧一起改成相同值。
4. F-9 AST structure lock **可绕过，而且当前代码已经以“连续两次取反”的等价 XOR 绕过它**。
5. S1 不把严格 mirror adapter 直接接入 legacy `derive_facade_frame` 是正确的保守取舍；否则会把未知值从“False”改成异常，违反行为保持。但现有两个 legacy coercion 互相矛盾确是潜伏缺陷，必须在 S3/S4 live cutover 前通过命名、版本化边界消除。
6. 遮蔽审计见第 6 节：F-22 两把老锁、schema stale/current 主锁、三档与 renderer 主锁没有被第二防线冒充；F-9 若干所谓 neuter/structure 锁则存在空转、范围不足或被外层自哈希遮住内层 binding 缺失的问题。

## 2. 测试与工作区纪律

### 2.1 我实测的

所有 pytest/probe 均把 stdout/stderr 写入独立文件，并把退出码写入该命令专属 `.exit` 文件；测试命令中未接管道。

```bash
python -m pytest -q -n auto > /tmp/sol_full_pytest_20260811.out 2>&1
printf '%s\n' "$?" > /tmp/sol_full_pytest_20260811.exit
```

结果：

```text
2447 passed, 10 xfailed, 209 warnings in 356.56s (0:05:56)
0
```

定向门：

```text
F-22 targeted: 56 passed, 18 warnings in 18.46s; exit=0
F-9 S0/S1 targeted: 80 passed in 13.78s; exit=0
SCORER_SCHEMA 两锁: 2 passed in 9.15s; exit=0
compileall: exit=0
git diff --check: no output; exit=0
```

定向输出文件分别为：

```text
/tmp/sol_f22_targeted.out                 /tmp/sol_f22_targeted.exit
/tmp/sol_f9_s0s1_targeted.out             /tmp/sol_f9_s0s1_targeted.exit
/tmp/sol_verdict_schema_locks.out          /tmp/sol_verdict_schema_locks.exit
/tmp/sol_compileall.out                    /tmp/sol_compileall.exit
```

`git status --short` 在测试前后没有新增施工文件变化；我未执行 commit/stash/checkout，也未修改任何施工代码。裁决书是本席唯一写入。

### 2.2 我推理的

严重度不是由测试数量推导，而由受支持路径、合同可表达能力和 hostile mutation 的结果推导。尤其：绿门只证明现有夹具通过；它不能证明未被夹具实例化的 schema/profile 分支具有同一物理口径。

## 3. Findings

### BLOCKER-1 — F-22 把 schema-v3 外皮口径无条件套给默认 schema-v1 centerline 产物；声明既过宽又不可执行

#### 定位（文件行号）

- `src/agent/correction/schema.py:234-240`：`CorrectedGeometry` 明写 `centerline geometry primitives`，且默认 `schema_version="1"`。
- `src/agent/correction/parse.py:64-69`：`rectangular -> schema 1`，`orthogonal_polygon -> schema 3`。
- `scripts/tool_scripts/run_stage.py:2005-2006,2821-2825`：运行 profile 的解析仍允许两者，CLI 默认明确是 `rectangular`。
- `src/agent/correction/deterministic.py:760-785`：schema 3 才走 `apply_v3_envelope_transaction`；legacy 走另一条 `_apply_legacy_envelope_reconcile`。
- `src/agent/judge/correction_score.py:49-82`：新声明把所有 `1_correction` footprint 都说成 outer face。
- `src/agent/judge/correction_score.py:161-194,259-278,329-355`：两个 extractor 无条件 verbatim；没有 schema/profile/convention 守卫，也不把 convention 写进 evidence。
- `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/run_config.yaml:4-9`：真实仓内 run 明确为 schema v1 / rectangular。
- 同 run 的 `1_correction/attempts/001/output.json:1-9`：未显式写 schema（因此按 v1 解析），footprint 为 `[-0.1,14.65] × [-0.1,7.65]`。
- `case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e/run_config.yaml:32-33` 与其 `output.json:1-10`：现代路径明确 schema 3 / orthogonal，footprint 为 `[0,15] × [0,8]`。
- 原施工单自己把这件事列为必须停下上报的 P1/P4：`AI_agent/logs/reviews/request/2026-08-11_f22_judge_output_convention_dispatch_claude.md:105-113`。

#### 实测证据 A：默认 legacy 真实产物被当前 scorer 判掉一半边界

实际执行（输出、退出码分别在 `/tmp/sol_verdict_f22_current.out`、`.exit`）：

```bash
python - <<'PY' > /tmp/sol_verdict_f22_current.out 2>&1
import json
from pathlib import Path
from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.gt import load_gt

base = Path("case_tests/e2e_tests/sm21_anchor")
gt = load_gt("sm21_anchor")
for run in ("run_2026-08-05_probe_a_legacy_snapped", "run_2026-08-11_continuous_e2e"):
    raw = json.loads((base / run / "1_correction/attempts/001/output.json").read_text())
    scored = score_correction_geometry(raw, gt)
    print(run, "schema", raw.get("schema_version", "implicit-v1"))
    for floor, score in scored.scores.items():
        print(floor, "hits", score.boundary_hits(), {
            side: (m.read, m.delta, m.status) for side, m in score.boundary.items()
        })
PY
printf '%s\n' "$?" > /tmp/sol_verdict_f22_current.exit
```

输出片段：

```text
run_2026-08-05_probe_a_legacy_snapped schema implicit-v1
Floor 1 hits (2, 4) {'S': (-0.1, -0.1, 'within_tol'), 'N': (None, None, 'miss'),
                     'W': (-0.1, -0.1, 'within_tol'), 'E': (None, None, 'miss')}
Floor 2 hits (2, 4) ... N/E miss ...
run_2026-08-11_continuous_e2e schema 3
Floor 1 hits (4, 4) ... all delta 0.0 / complete ...
Floor 2 hits (4, 4) ... all delta 0.0 / complete ...
exit=0
```

另一个实际 probe 在内存中恢复 HEAD 的两段旧公式后比较 3 个 legacy run 与现代 run（`/tmp/sol_f22_legacy_vs_current.out`，exit=0）：

```text
legacy current:              boundary_hits [2,4] / [2,4]
legacy restored-old:         boundary_hits [4,4] / [4,4]
modern schema-v3 current:    delta 0.0, wall_hits [4,4] / [5,5], extent_drift 0
modern schema-v3 restored:   boundary delta ±0.12, extent_drift 4 / 5
```

这同时证实两件相反但可并存的事实：删外扩对现代 v3 是正确修复；无条件删外扩对 legacy v1 是错误修复。

#### 实测证据 B：所谓“声明”是 runtime inert

`rg -n 'CORRECTION_OUTPUT_CONVENTION' src/agent/judge/correction_score.py` 只返回定义与两个 docstring（`82,166,263`），两个函数体没有读取常量。实际把常量改成 `"bogus"` 后重算现代 run：

```text
before {'Floor 1': {'S': 0.0, 'N': 0.0, 'W': 0.0, 'E': 0.0}, ...}
after  {'Floor 1': {'S': 0.0, 'N': 0.0, 'W': 0.0, 'E': 0.0}, ...}
declaration_is_runtime_inert True
exit=0
```

证据文件：`/tmp/sol_verdict_f22_declaration.out`、`.exit`。

#### 推理与裁定

legacy footprint 的宽/深为 `14.75/7.75`，与 GT `15/8` 相差约一面墙厚 `0.24`；按 centerline 合同向两侧各扩 `0.12` 后，四边均落在相同的约 `-0.22/-0.23` registration offset，并全部在 0.30 容差内。当前 verbatim 判法却产生 S/W `-0.10`、N/E `-0.35` 的非对称结果，N/E 因而成为 miss。故不能把旧换算概括成“只是在遮住 registration offset”：对 v1，它先完成合同规定的 frame normalization，归一后才显出统一 registration offset。

必须同时做到：

1. 文本把适用范围缩到可信的 schema-v3/orthogonal/post-transform 产物；
2. scorer 在执行时验证该身份，模糊或 legacy 输入不得静默套用 outer-skin；
3. 把实际/假定 convention 与 schema/profile provenance 写入 sidecar，并纳入 cache 语义身份；
4. 若仍支持 rectangular/v1 判卷，需经派工方重新定 scope，保留 schema-aware normalization；若本批坚持“单一 convention、不得加兼容分支”，则 v1 必须显式 fail closed，而非误判。

仅改注释不够。当前默认 CLI 就能进入 v1，所以本批不能在无守卫状态落库。

---

### MAJOR-1 — F-9 S0 的 V2 resolver artifact / raw context 没有实现设计规定的认证绑定，错误的 raw/context 组合可合法自哈希

#### 定位（文件行号）

- 设计 `AI_agent/proposals/f9_route2_evidence_citation_design.md:254-260` 要求 context 记录 floor/z-band ring hash、view datum、scope，并绑定 authenticated raw/resolver inputs。
- 设计 `:579-582` 要求 V2 artifact 内嵌 direction/datum sidecar bytes，并要求 replay 从 raw bytes 重建 context，context hash 进入 resolver/decision preimage。
- 实现 `src/agent/correction/window_position.py:114-127` 的 floor/context 只有 `floor_id / footprint_fingerprint / z_floor / ceiling_height / raw_draw_sha256 / resolver_hash`；没有 view datum、scope、authenticated direction facts。
- 实现 `:185-209` 的 V2 artifact 没有 direction/datum sidecar bytes；validator 只验证外层 `content_sha256`，不核对 `sha256(raw_draw_canonical_bytes) == raw_projection_context.raw_draw_sha256`。
- 更直接地，正向夹具自己在 `tests/test_f9_route2_s0_raw_contract.py:176-179` 用固定 bytes 生成 context，却在 `:371-389` 放入另一组 raw bytes；该不一致仍被 round-trip 当作合法样本。

#### 实测证据

同一 probe 的尾部构造了当前测试同型的 V2 artifact，结果：

复现命令（与我实际执行的 `/tmp/sol_verdict_f9_contract_v2.out` probe 中 artifact 段相同）：

```bash
python - <<'PY' > /tmp/sol_repro_f9_artifact_binding.out 2>&1
import hashlib, importlib.util, json
from pathlib import Path
from src.agent.correction.window_position import WindowResolverInputsArtifactV2
from src.agent.correction.window_sources import RawReadingArtifactV1, canonical_sha256

spec = importlib.util.spec_from_file_location("s0", Path("tests/test_f9_route2_s0_raw_contract.py"))
s0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s0)
draw = s0.CorrectionDrawV3CitationV2.model_validate(s0._raw_payload())
ctx = s0._context_for(draw)  # hashes b"canonical-bytes-fixture"
raw_bytes = json.dumps(s0._raw_payload(), sort_keys=True).encode()
readings = (RawReadingArtifactV1(input_id="1f_view", raw_bytes=b"{}"),)
body = {
    "artifact_version": "window_resolver_inputs_v2",
    "raw_draw_canonical_bytes": raw_bytes.decode(),
    "raw_view_manifest_bytes": "{}",
    "raw_reading_artifacts": [r.model_dump(mode="json") for r in readings],
    "raw_projection_context": ctx.model_dump(mode="json"),
}
artifact = WindowResolverInputsArtifactV2(
    artifact_version="window_resolver_inputs_v2",
    raw_draw_canonical_bytes=raw_bytes, raw_view_manifest_bytes=b"{}",
    raw_reading_artifacts=readings, raw_projection_context=ctx,
    content_sha256=canonical_sha256(body),
)
actual = hashlib.sha256(artifact.raw_draw_canonical_bytes).hexdigest()
print("raw_hash_mismatch_accepted", actual != artifact.raw_projection_context.raw_draw_sha256)
PY
printf '%s\n' "$?" > /tmp/sol_repro_f9_artifact_binding.exit
```

```text
raw_hash_mismatch_accepted True
exit=0
```

完整输出：`/tmp/sol_verdict_f9_contract_v2.out`；退出码：`/tmp/sol_verdict_f9_contract_v2.exit`。

这里不是“改了 bytes 却忘了重算外层 hash”的普通 tamper；攻击者/错误 writer 对互相矛盾的两份字段重算外层 hash 后，模型仍接受。`tests/test_f9_route2_s0_raw_contract.py:397-401` 只锁住外层自哈希，恰好遮住了缺失的 cross-field authentication。

#### 推理与要求

S0 虽然不接 live，但其职责就是先冻结合同/版本壳。现在以 `window_resolver_inputs_v2` 命名的 wire 无法表达设计的重放身份，后续补字段会造成事实上的 wire 变更。应在落库前补齐 direction/datum bytes、scope/datum/context identity，并加入 hostile cross-field validators/tests；不能把这些全部推给 S2 的算法实现。

---

### MAJOR-2 — `WindowPositionDecisionV1` 的 preimage 与 accepted 语义过弱，可跨 raw/resolver 重放并接受不可能 decision

#### 定位（文件行号）

- 设计 `AI_agent/proposals/f9_route2_evidence_citation_design.md:348-352` 要求 `canonical_window_key`。
- 设计 `:560-575` 明列 decision preimage：raw/resolver/context、locators、intervals、frame/scope hashes、z datum、source/window scope ids/projected z、plan floor ref、distance/tolerance/decision/derived span。
- 实现 `src/agent/correction/window_position.py:216-245` 只有 window id、locators、两个 interval 列表、distance/tolerance/decision/derived span；缺少上述 identity/context/frame/scope/z/floor 字段。
- wrapper `:249-263` 只在外层放 raw/resolver hash；没有 `hydrated_geometry_sha256`，也不验证每个 decision 属于该 raw/resolver/context。
- `_shape` 仅检查三个 elevation tuple 等长、distance 非负、accepted 有 span；没有“accepted 至少一条 elevation”“所有距离 <= tolerance”“derived span == plan authority”等不变量。

#### 实测证据

实际命令用公开 builder 构造 hostile-but-self-hashed 实例，再把同一个 decision 放进两组不同外层 binding；输出：

复现命令：

```bash
python - <<'PY' > /tmp/sol_repro_f9_decision_binding.out 2>&1
from src.agent.correction.window_position import (
    SourceIntervalV1, WindowPositionEvidenceArtifactV1,
    build_window_position_decision,
)
from src.agent.correction.window_sources import canonical_sha256

plan = SourceIntervalV1(lo=1.24, hi=3.64)
elev = SourceIntervalV1(lo=1.12, hi=3.52)
def build(locs, intervals, distances, span):
    return build_window_position_decision(
        window_id="W-F1-N-1", plan_locator="src:" + "1" * 64,
        elevation_locators=locs, plan_world_interval=plan,
        elevation_projected_intervals=intervals, distances=distances,
        tolerance_name="window_evidence_pairing_tol_m", tolerance_value=0.30,
        decision="accepted", derived_span=span,
    )
cases = (
    ("accepted_without_elevation", build((), (), (), plan)),
    ("accepted_wrong_derived_span", build(("src:" + "2" * 64,), (elev,), (0.12,), SourceIntervalV1(lo=7, hi=8))),
    ("accepted_distance_over_tolerance", build(("src:" + "2" * 64,), (elev,), (0.31,), plan)),
)
for label, decision in cases:
    print(label, "=>", decision.decision, decision.decision_sha256)
decision = cases[1][1]
for raw_hash, resolver_hash in (("a" * 64, "b" * 64), ("c" * 64, "d" * 64)):
    body = {"raw_draw_sha256": raw_hash, "resolver_hash": resolver_hash,
            "decisions": [decision.model_dump(mode="json")]}
    artifact = WindowPositionEvidenceArtifactV1(
        raw_draw_sha256=raw_hash, resolver_hash=resolver_hash, decisions=(decision,),
        content_sha256=canonical_sha256(body),
    )
    print("evidence_binding", raw_hash[0], resolver_hash[0], artifact.decisions[0].decision_sha256)
PY
printf '%s\n' "$?" > /tmp/sol_repro_f9_decision_binding.exit
```

```text
accepted_without_elevation => accepted 5b8c0b...
accepted_wrong_derived_span => accepted 3dc938...
accepted_distance_over_tolerance => accepted b69a44...
evidence_binding a b 3dc93866...
evidence_binding c d 3dc93866...
exit=0
```

证据：`/tmp/sol_verdict_f9_contract_v2.out`、`.exit`。关键构造与正式测试相同，均通过 `build_window_position_decision`/Pydantic validator，并非 `model_construct` 绕过验证。

#### 推理与要求

当前 `decision_sha256` 只能证明“这组不完整字段没有被事后改动”，不能证明 decision 属于哪次 raw/resolver/context，也不能证明 `accepted` 是合法对账结论。这会把 S0 壳冻结成无法承载 §8.1 hash chain 的版本。落库前应补齐设计列出的 preimage 字段及 `canonical_window_key`，让 per-decision hash 直接绑定 raw/resolver/context；并增加上述三个 hostile rejection lock。外层再自哈希不能替代内层身份绑定。

---

### MAJOR-3 — F-9 S1 没有完整合并 inline sign 规则；真实 live 入口仍绕开 shared resolver，AST 锁可被等价语法轻易绕过

#### 定位（文件行号）

- 设计 `AI_agent/proposals/f9_route2_evidence_citation_design.md:386-396,712-719` 要求四处只消费 gt-free convention，删除本地 table **和 inline XOR**。
- `src/agent/correction/facade.py:65-92` 的 `derive_facade_frame` 虽取 shared tables，却仍以两次条件取反自行实现等价 XOR，完全没调用 `facade_convention.resolve_sign`。
- 这不是 dead legacy：`src/validator/checks/correction.py:355-365` 在真实 correction check 中直接调用它；`src/agent/correction/envelope.py:222` 则调用另一个已接线入口，仓内两条入口并存。
- AST helper `tests/test_f9_route2_s1_convention_truth.py:153-164` 只识别 `ast.Assign(value=ast.Dict)` 的三个精确变量名，以及 `ast.BinOp(BitXor)`。
- structure tests `:167-189` 因而看不到 `AnnAssign`、`dict()`、alias、`operator.xor`、`!=` 或连续取反；当前连续取反就是实质漏检。
- 唯一动态 neuter `:200-222` 只打 `derive_view_projection_frame`；`derive_facade_frame` 未覆盖。
- `:225-263` 对另外两个 consumer 只检查 import 形状，不检查调用；dead import 也可过。

#### 实测证据

实际 probe（`/tmp/sol_verdict_f9_ast.out`，exit=0）先用测试文件自己的 AST helper 扫当前 `facade.py`，再 monkeypatch shared resolver，最后构造 `AnnAssign + operator.xor + dead import` 变体：

复现命令：

```bash
python - <<'PY' > /tmp/sol_repro_f9_ast.out 2>&1
import ast, importlib.util
from pathlib import Path
from src.agent.correction import facade, facade_convention

spec = importlib.util.spec_from_file_location("s1", Path("tests/test_f9_route2_s1_convention_truth.py"))
s1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)
tree = ast.parse(Path("src/agent/correction/facade.py").read_text())
print("actual_forbidden_names", s1._assigned_names(tree))
print("actual_bitxor", s1._has_xor_binop(tree))
baseline = facade.derive_facade_frame(
    view_facade="North", footprint_x=[2,10], footprint_y=[3,7], mirrored="false"
).sign
real = facade_convention.resolve_sign
facade_convention.resolve_sign = lambda *a, **k: 1
try:
    legacy = facade.derive_facade_frame(
        view_facade="North", footprint_x=[2,10], footprint_y=[3,7], mirrored="false"
    ).sign
    new = facade.derive_view_projection_frame(
        vertices=[(2,3),(10,3),(10,7),(2,7)], facade_family="North",
        mirrored=False, local_x_positive="image_left_to_right",
    ).sign
finally:
    facade_convention.resolve_sign = real
print("derive_facade_frame", baseline, "=>", legacy)
print("derive_view_projection_frame_after_neuter", new)
synthetic = ast.parse('''
from src.agent.correction import facade_convention
import operator
_BASE_SIGN: dict[str, int] = {"North": -1}
sign = -_BASE_SIGN["North"] if operator.xor(mirrored, rtl) else _BASE_SIGN["North"]
''')
print("synthetic_forbidden_names", s1._assigned_names(synthetic))
print("synthetic_bitxor", s1._has_xor_binop(synthetic))
print("synthetic_lock_would_pass",
      not (s1._assigned_names(synthetic) & {"_BASE_SIGN", "_CONVENTION", "_AXIS"})
      and not s1._has_xor_binop(synthetic))
PY
printf '%s\n' "$?" > /tmp/sol_repro_f9_ast.exit
```

```text
actual_forbidden_names set()
actual_bitxor False
derive_facade_frame -1 => -1
derive_view_projection_frame_after_neuter 1
synthetic_forbidden_names set()
synthetic_bitxor False
synthetic_lock_would_pass True
exit=0
```

也就是说，shared `resolve_sign` 被中和后，新入口响应、legacy live 入口不响应；而结构锁仍认为当前文件合格。

#### 推理与要求

修复不需要把严格 mirror adapter 接进 legacy。可先保留 `_is_mirrored` 的历史 coercion，得到 bool 后统一调用 `facade_convention.resolve_sign`，从而同时满足行为保持与公式单源。锁应至少对每个真实 call site 做动态 mutation/dataflow 验证；若保留 AST 锁，应检查目标函数确实调用 module attribute，而不是只搜精确语法/变量名。

---

### MINOR-1 — boundary 三档按“先 round(2) 再比 0.05”实现，实际绿色阈值并非请求书字面 `<= 0.05`

#### 定位与实测

请求书 `AI_agent/logs/reviews/request/2026-08-11_f22_judge_output_convention_dispatch_claude.md:91-93` 定义 `<=0.05` 绿、`<=0.30` 橙。实现 `src/agent/judge/reading_score.py:383-401` 在 `:396` 先 `round(..., 2)`，再在 `:397` 比 `complete_eps`。

复现命令：

```bash
python - <<'PY' > /tmp/sol_verdict_f22_threshold.out 2>&1
from src.agent.judge.reading_score import _match_lines
for value in (0.05, 0.054, 0.055, 0.30, 0.301):
    match = _match_lines([value], [0.0], 0.30, complete_eps=0.05)[0][0]
    print(value, "stored_delta", match.delta, "status", match.status)
PY
printf '%s\n' "$?" > /tmp/sol_verdict_f22_threshold.exit
```

```text
0.05  stored_delta 0.05 status complete
0.054 stored_delta 0.05 status complete
0.055 stored_delta 0.06 status within_tol
0.3   stored_delta 0.3  status within_tol
0.301 stored_delta None status miss
exit=0
```

证据：`/tmp/sol_verdict_f22_threshold.out`、`.exit`。

#### 推理与要求

这不影响 complete/within_tol 都计 hit 的 headline，但影响要求新增的可见颜色语义。请明确“阈值比较基于原始量还是厘米量化值”；若是字面物理阈值，应先用未舍入误差判档、只对展示 delta 舍入，并补 `0.05±epsilon` 锁。

---

### MINOR-2 — 若干 F-9 “neuter/总量/版本”测试标题强于其实际判别力

#### 定位与遮蔽

复现/审计命令：

```bash
nl -ba tests/test_f9_route2_s0_raw_contract.py | sed -n '95,218p;318,365p'
rg -n 'correction_target_v2\(|parse_raw_correction_draw\(' --glob '*.py'
```

输出中的关键位置正是下列 `:109-161`、`:192-200`、`:318-325`、`:336-356`；第二条命令只列出定义与测试调用，没有 live production caller。

- `tests/test_f9_route2_s0_raw_contract.py:109-161` 两个“neuter”只直接调用 schema，未变异或调用 production parser；删除 production preflight 后它们仍会绿。好消息是主锁 `:95-106` 精确断言 `WindowResolverInputError/code/category`，所以主目标仍会红；问题是两把 neuter 本身不承重。
- `:192-200` 声称 context “purely a function of floors”，但没有删除/改变 windows 后比较 context；当前实现确实只循环 floors（`window_position.py:158-166`），测试没有锁住这个性质。
- `:318-325` 名为“new runs always get artifact v2”，实际只断言 registry 同时含 v1/v2；鉴于 S0 明确不接 live，正确表述应是 target/version shell，而非 new-run 行为。
- `:336-356` 的“never inspects span”只拿 unknown version 测 fail closed。一个对 known version 仍按 span shape 分派、对 unknown version 拒绝的变体可通过全部这些断言。

#### 要求

不用为 S0 接 live；应把标题/断言缩到当前 S0 可证明的事实，并给 loader 加 known-version hostile shape cases，给 context 加 windows mutation invariance。否则后续审阅会把说明性测试误当 mutation lock。

---

### MINOR-3 — 保留 legacy 宽松 mirror coercion 是对的，但两套 coercion 的矛盾仍是明确潜伏缺陷

#### 定位与实测

- `src/agent/correction/facade.py:59-62`：bool 原样，否则仅 `str(value).lower()=="true"`，未知值静默为 False。
- `src/agent/correction/window_sources.py:667-686`：只有真实 bool 才采用；字符串 `"true"` 也静默为 False。
- 新严格 adapter `src/agent/correction/facade_convention.py:67-85`：仅 bool 与大小写精确的 `"true"/"false"`，其余抛 `UnresolvedMirrorError`。
- 设计已经点名该矛盾：`AI_agent/proposals/f9_route2_evidence_citation_design.md:398-409`。

实际 probe：

```bash
python - <<'PY' > /tmp/sol_verdict_f9_mirror.out 2>&1
from src.agent.correction.facade import derive_facade_frame
from src.agent.correction.facade_convention import normalize_mirror_flag
for value in ("false", "unknown", None, "banana", 0):
    legacy = derive_facade_frame(
        view_facade="South", footprint_x=[0,10], footprint_y=[0,8], mirrored=value,
    ).sign
    try:
        strict = f"accepted:{normalize_mirror_flag(value)}"
    except Exception as exc:
        strict = f"raised:{type(exc).__name__}"
    print(repr(value), "legacy_sign", legacy, "strict_adapter", strict)
PY
printf '%s\n' "$?" > /tmp/sol_verdict_f9_mirror.exit
```

```text
'false'   legacy_sign=1 strict_adapter=accepted:False
'unknown' legacy_sign=1 strict_adapter=raised:UnresolvedMirrorError
None      legacy_sign=1 strict_adapter=raised:UnresolvedMirrorError
'banana'  legacy_sign=1 strict_adapter=raised:UnresolvedMirrorError
0         legacy_sign=1 strict_adapter=raised:UnresolvedMirrorError
exit=0
```

证据：`/tmp/sol_verdict_f9_mirror.out`、`.exit`。

#### 推理与裁定

如果 S1 直接把 legacy `_is_mirrored` 换成严格 adapter，上述四类历史输入会从正常返回改成异常，故施工席此次“不接严格版”是正确的行为保持选择。另一方面，`facade("true") == True` 而 `window_sources("true") == False` 的现状会对同一证据生成相反 frame，确是潜伏缺陷。应保留为显式 legacy compatibility adapter/debt，并在 S3/S4 新 live v3 边界 fail closed；不能永远靠两个匿名宽松 helper 分叉。

---

### NIT-1 — 测试/注释仍保留旧语义与旧版本字面，容易误导下次维护

复现命令：

```bash
nl -ba tests/test_judge_batch_b.py | sed -n '190,265p'
nl -ba tests/test_e2e_break_r2_locks.py | sed -n '495,548p'
nl -ba scripts/tool_scripts/run_stage.py | sed -n '76,93p'
nl -ba tests/test_f9_route2_s1_convention_truth.py | sed -n '14,27p;192,223p'
```

- `tests/test_judge_batch_b.py:196,254` 的函数名仍写 `expands_centerline...`，实际锁的是“不扩”。docstring 已解释，但 test id/失败日志反义。
- `tests/test_e2e_break_r2_locks.py:500-503` 仍写 stale 8/current 9；真实断言在 `:531,536,542` 已是 current 10/stale 9/rewrite 10。
- `scripts/tool_scripts/run_stage.py:78` 仍称 sidecar label v9，紧接 `:86-92` 才说明已升 10。
- `tests/test_f9_route2_s1_convention_truth.py:23-26` 说动态 neuter 证明 `window_sources.py`，实际 `:200-222` 只测 `facade.py::derive_view_projection_frame`。

只改文案/名称即可；不影响本次严重度主结论。

## 4. 指定问题的正向核实

### 4.1 两把被改写的老锁：不是空锁

测试位置：`tests/test_judge_batch_b.py:196-251` 与 `:254-305`。

我没有改文件，而是在 Python 进程内分别 monkeypatch 回旧的 half-thickness 公式，再直接调用测试函数。边界变异：

```text
AssertionError at tests/test_judge_batch_b.py:239
exit=1
```

证据：`/tmp/sol_verdict_f22_mut_boundary.out`、`.exit`。失败点就是四边 delta 的目标断言，不是 parser/schema/fixture 前置门。

内墙变异：

```text
AssertionError at tests/test_judge_batch_b.py:301
assert match.status == "complete"
exit=1
```

证据：`/tmp/sol_verdict_f22_mut_wall_v2.out`、`.exit`。失败点就是旧外扩造成的 extent/status 降级，不是第二防线。

因此裁定：两把锁虽名字陈旧，但均能杀死精确回归变异。

### 4.2 SCORER_SCHEMA 9→10：陈旧侧与当前侧没有被改成同值

静态证据：

- `tests/test_e2e_break_r2_locks.py:524-532` 先生成真实当前 sidecar，并断言 `== 10`。
- `:534-542` 只把 tag 改成 `9`，spy 断言 scorer 被调用，重写结果回到 `10`。
- `:545-548` 再拿当前 sidecar，spy 断言 scorer 未调用。
- 第二把字面值锁 `tests/test_c2_b4b_contract.py:121-124` 明确断言 legacy run-stage `10`、typed v3 `8`，也没有 lockstep 改值。

实测：

```bash
python -m pytest -q \
  tests/test_e2e_break_r2_locks.py::test_major1_stale_schema_sidecar_recomputed_current_reused \
  tests/test_c2_b4b_contract.py::test_legacy_scorer_schema_is_independent_of_typed_v8_contract_label \
  > /tmp/sol_verdict_schema_locks.out 2>&1
printf '%s\n' "$?" > /tmp/sol_verdict_schema_locks.exit
```

```text
2 passed in 9.15s
exit=0
```

裁定：这两把锁有效；唯一问题是 NIT-1 所述旧 docstring。

### 4.3 外包三档与渲染链：主路径接通

- `src/agent/judge/reading_score.py:87-96,383-420`：`LineMatch.status` 与 complete/within_tol/miss 三档存在。
- `scripts/tool_scripts/run_stage.py:1079-1080,1217-1226`：status 进入 sidecar/elevation boundary record。
- `scripts/tool_scripts/render_grade.py:426-452`：miss 红虚线、within_tol 橙、其余绿。
- `tests/test_judge_batch_b.py:393-439`：0.0/0.12/0.5 与 serializer 正向锁。
- `tests/test_render_grade.py:422-439`：直接 sidecar 像素锁橙且非绿。

除 MINOR-1 的阈值边缘外，本条施工目标成立。

### 4.4 F-9 S0 没有接 live production：属实

```bash
rg -n 'correction_target_v2\(|parse_raw_correction_draw\(|WindowResolverInputsArtifactV2\(' --glob '*.py'
```

结果只出现定义与 `tests/test_f9_route2_s0_raw_contract.py`；`src/agent/correction/parse.py:72-93,259-295` 的新入口没有 production caller。这个范围控制是正确的，MAJOR-1/2 指向合同壳本身不完整，不要求现在接 live。

## 5. 对 orchestrator 背景陈述的独立核验

| 陈述 | 独立结论 | 证据 |
|---|---|---|
| 全量 2447 passed / 10 xfailed / 0 failed | **证实** | `/tmp/sol_full_pytest_20260811.out/.exit`，exit=0 |
| 基线 2361 绿 | **未把请求书当证据；本席没有 checkout 基线重跑** | 工作区有未提交成果，纪律禁止 checkout；不影响当前语义裁定 |
| modern continuous_e2e 外包 8 边 delta 0/status complete | **证实** | `/tmp/sol_verdict_f22_current.out`，schema 3 两层各 4/4，delta 0 |
| modern continuous_e2e 内墙 extent_drift 9→0 | **证实“当前为 0”；恢复旧公式后为 4+5”** | `/tmp/sol_f22_legacy_vs_current.out` |
| “产物现在都在外皮框” | **证伪** | schema v1 合同、CLI default、legacy run 与动态评分证据，见 BLOCKER-1 |
| 两把旧锁被改空 | **证伪** | 两个精确旧公式变异均 exit=1 |
| stale/current 可能一起改成 10 | **证伪** | 当前 10、stale 9、rewrite 10；spy 分别 `[True]`/`[]` |
| S1 已完整单源 | **证伪** | `derive_facade_frame` 对 shared resolver mutation 无响应 |

## 6. 逐锁遮蔽审计

这里按“同一目标/同一 fixture 的锁族”列出；parameterized truth-table 的 16 行视为一个锁族，否则重复 32 次不会增加信息。

| 锁族 | 是否有第二防线先拦 | 裁定 |
|---|---:|---|
| F-22 两把改写老锁（boundary / wall span） | **否（实测）** | 精确恢复旧变换分别死在 `:239` delta 与 `:301` status；目标门承重。 |
| F-22 self-proving double-expansion（`test_judge_batch_b.py:308-358`） | 否 | premise 是独立算术，随后走 public scorer；恢复旧 transform 会死在 public result，不只死在 premise。 |
| F-22 0.0 / 0.12 / 0.5 三档（`:393-439`） | 绿/橙否；红由 candidate tolerance gate 产生 | 0.12 明确进入 match 后断言 within_tol；0.5 的“先无候选再 miss”就是 red 的定义，不是冒充的 schema 门。阈值边缘未锁，见 MINOR-1。 |
| F-22 `_boundary_match_dict` status 传播（`:415-429`） | 否 | 前置 sanity 只证明输入确为 orange；把 serializer 改回硬编码 complete 时，目标输出断言才红。 |
| F-22 plan renderer orange pixel（`test_render_grade.py:422-439`） | 否 | 直接喂 sidecar；指定像素无 wall 重叠，且同时断言非绿。 |
| F-22 generic missing-schema recompute（`test_judge_batch_b.py:509-558`） | **有** | sidecar 缺 schema 及多项现代身份字段，可由多种 invalidation 触发；它不隔离 9→10。真正承重的是下一把。 |
| F-22 stale 9 / current 10 spy lock（`test_e2e_break_r2_locks.py:495-548`） | **否** | 先生产 authentic sidecar，再只改 schema；spy 区分 recompute/reuse，目标隔离良好。 |
| F-22 legacy10 / typed8 字面锁（`test_c2_b4b_contract.py:106-124`） | 否 | 直接两个独立常量断言；不是同值锁。 |
| F-9 raw span stable-code 主锁（`test_f9...s0:95-106`） | 否 | Pydantic 也会拒绝 span，但精确异常类型/code/category 排除了 generic backstop 冒充。 |
| F-9 两把 raw “neuter”（`:109-161`） | **是/不承重** | 它们只证明直接 schema 调用不会给 stable code；production preflight 的 mutation 由主锁而非这两把捕获。 |
| F-9 raw context type guard（`:220-270`） | 否 | 显式 `isinstance` 在任何 full-model/placeholder 深层读取前触发，目标就是结构 guard。 |
| F-9 context window-independent/totality（`:192-218`） | **锁不足** | fixture 有 window，但不做 windows mutation；不能排除未来偷偷读 window。 |
| F-9 historical v1/v2/v3-V1 byte parity（`:275-315`） | 否 | 真实 bytes 与明确 loader 类型/内容；与新 V2 壳分离，锁有效。 |
| F-9 unknown version fail closed（`:328-356`） | 否于 unknown；**不足于 known shape heuristic** | unknown 精确 stable code 有效；但不能证明 known-version 路径不偷看 span，见 MINOR-2。 |
| F-9 V2 round-trip/tamper（`:359-401`） | **有** | 外层 content hash 会先拦普通 byte tamper；不会拦“重算外层 hash但 nested raw hash 不匹配”，而正向 fixture 本身就接受后者，见 MAJOR-1。 |
| F-9 decision round-trip/hash/rejected-shape（`:418-475`） | **局部有效、合同不全** | 能拦现有字段事后 tamper 与 rejected+span；无法拦跨 raw/context 重放、accepted 无 elevation/超 tol/错 span，见 MAJOR-2。 |
| F-9 16-row handwritten truth table（`test_f9...s1:55-108`） | 否 | expected 是外部手写，lo/hi 非零；shared function 与 `derive_view_projection_frame` 的行为锁有效。 |
| F-9 strict mirror adapter boundary（`:115-135`） | 否，但只覆盖未接 live 的新 adapter | 它准确锁 helper，不证明 legacy coercion 已统一；范围应明确。 |
| F-9 AST local-table/XOR（`:145-183`） | **可绕过** | 当前连续取反、AnnAssign、operator.xor 均通过，见 MAJOR-3。 |
| F-9 dynamic real-path neuter（`:200-222`） | 否于该一个入口；**覆盖不足** | `derive_view_projection_frame` 真正响应 mutation；另一个 live `derive_facade_frame` 不响应。 |
| F-9 applicability/judge import-shape（`:225-263`） | **是/可空转** | 只证 module import，dead import 即可过；不证明调用 shared resolver。 |

## 7. 最小返工验收门

1. F-22：以真实 schema/profile/provenance 限定 convention；对 schema v1 明确 normalize 或 fail closed；新增 default rectangular/implicit-v1 真实产物回归锁。常量必须参与执行或改为不可误称“seam”的文档，并把 convention identity 写入 sidecar/cache preimage。
2. F-22：明确 status 用 raw error 还是厘米量化 error；按结论补 `0.05±epsilon`。
3. F-9 S0：按 v2.1 `:254-260,348-352,560-582` 补齐 context/artifact/decision identity 与 hash preimage； hostile mismatch、cross-binding、accepted-invalid 三类必须 fail。
4. F-9 S1：`derive_facade_frame` 在保留 legacy coercion 后调用 shared resolver；对所有真实 call site 做动态 neuter，不能用 import presence 代替调用证明。
5. mirror：本批不要直接 strictify legacy；建立命名的兼容 adapter/债项，并写明 S3/S4 cutover 的 fail-closed 边界。
6. 重跑同一全量门及上述 hostile probes；只有全部通过后，裁决才有资格从 `CHANGES REQUIRED` 上调。

## 8. 最终裁决

**CHANGES REQUIRED**。

理由不是“测试不够多”，而是已实测存在默认受支持 schema-v1 路径误判，且 F-9 已命名版本壳不能表达设计要求的身份链；同时 S1 的单源主张被一个真实 live 入口直接证伪。这三类问题都会在后续缓存重放、证据 hydration 或 legacy rerun 中固化错误，必须在落库前修正。
