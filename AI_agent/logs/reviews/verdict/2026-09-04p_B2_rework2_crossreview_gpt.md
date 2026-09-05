# B2 返工 2 · GPT 跨家族复核裁决

- 日期：2026-09-04
- 施工方：Claude 家族；复核方：GPT 家族
- 审对象：`git diff a45f778c..b52c6f5b`
- 工作树：`/tmp/b2rw2_review_gpt`，detached `b52c6f5b`

## 裁决

**REWORK / 阻断 1 / 不阻断 0**

上一轮的公开 `model_copy(z_m=...) -> derive_floor_ladder -> assemble_multifloor_geometry` 路径已经关闭，旧裸 z 生产参数、footprint 误贴与回归测试也均通过本席复核；施工方关于“自造完整自洽 reading 不在 B2 范围”的范围主张亦成立。

但是返工的核心类型不变量仍未成立。`ValidatedFloorLadder` 是一个公开导出的普通 dataclass，公开构造器直接接收 `_levels`（`src/agent/correction/multifloor.py:184-206,460-464`）；Python 不会运行时强制其注解中的 `_DerivedFloorLevel` 元素类型。装配边界只检查最外层 `isinstance(ladder, ValidatedFloorLadder)`（`:356-368`），随后直接读取元素的 `z_floor_m` / `ceiling_height_m`（`:384-417`）。本席只用公开 API 直接构造该“受验证”类型，放入一个手填 z 的 `SimpleNamespace`，成功装配出 `(12.34, 5.57)`，全程没有 evidence artifact、冻结字节或字节门。

因此施工方“唯一铸造者是 `derive_floor_ladder`”“为什么现在构造不出来”的回答均为假；当前只是给未封印的公开构造器取了 `Validated...` 名字。§四 #1、#2 仍阻断。

## 阻断项 B-2 · 公开 `ValidatedFloorLadder(...)` 可直接伪造，手填 z 仍可装配

承重代码事实：

```text
src/agent/correction/multifloor.py:184  @dataclass(frozen=True, eq=False)
src/agent/correction/multifloor.py:185  class ValidatedFloorLadder:
src/agent/correction/multifloor.py:197      _levels: tuple[_DerivedFloorLevel, ...]
src/agent/correction/multifloor.py:356      if not isinstance(ladder, ValidatedFloorLadder):
src/agent/correction/multifloor.py:368      levels = tuple(ladder)
src/agent/correction/multifloor.py:415      "z_floor": float(level.z_floor_m),
src/agent/correction/multifloor.py:416      "ceiling_height": float(level.ceiling_height_m),
src/agent/correction/multifloor.py:462      "ValidatedFloorLadder",
```

直接构造使用的单层 XY 来自一个仓内已落库、可由 `CorrectedGeometryV3` 解析的真实 fixture；没有复用施工方 B2 测试的 `_elevation` / `_claim_at` / `_DerivedFloorLevel` 构造写法。

命令原文：

```bash
python - <<'PY'
from pathlib import Path
from types import SimpleNamespace
from src.agent.correction.multifloor import (
    ValidatedFloorLadder,
    assemble_multifloor_geometry,
)
from src.agent.correction.schema import CorrectedGeometryV3

fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})
hand_level = SimpleNamespace(
    floor_index=0,
    z_floor_m=12.34,
    ceiling_height_m=5.57,
)
ladder = ValidatedFloorLadder((hand_level,))
print('ALT_PATH=PUBLIC_VALIDATED_CARRIER_DIRECT_CONSTRUCTOR')
print('ALT_CARRIER_EXPORTED=', ValidatedFloorLadder.__name__)
print('ALT_LEVEL_RUNTIME_TYPE=', type(tuple(ladder)[0]).__name__)
print('ALT_INPUT_Z=', hand_level.z_floor_m, hand_level.ceiling_height_m)
try:
    assembled = assemble_multifloor_geometry(ladder, [one_floor])
except Exception as exc:
    print('ALT_RESULT=REJECTED')
    print('ALT_ERROR=', type(exc).__name__, str(exc))
else:
    print('ALT_RESULT=ASSEMBLED')
    print('ALT_OUTPUT_Z=', [(floor.z_floor, floor.ceiling_height) for floor in assembled.floors])
PY
```

输出原文：

```text
ALT_PATH=PUBLIC_VALIDATED_CARRIER_DIRECT_CONSTRUCTOR
ALT_CARRIER_EXPORTED= ValidatedFloorLadder
ALT_LEVEL_RUNTIME_TYPE= SimpleNamespace
ALT_INPUT_Z= 12.34 5.57
ALT_RESULT=ASSEMBLED
ALT_OUTPUT_Z= [(12.34, 5.57)]
```

这条路径与上一轮同形但不同：上一轮篡改 claim，本轮不碰 claim，直接使用本轮新公开的 carrier 构造器。它正面证明守住的是上一条样例，而不是“未经字节验证的 z 无法装配”这一类。

返工门仍是任务书原句：让装配边界消费一个调用方无法自行铸造为“已验证”的载体，或让验证入口独占装配能力。仅靠 dataclass 名字、类型注解、外层 `isinstance` 与“唯一铸造者”注释不构成运行时封印。

## 三件指定复核

### 1. 上一轮路径逐字同形重跑：现已在 derive 阶段具名失败

本席以公开生产 adapter 从仓内真实 east elevation bytes 得到诚实 artifact；保留引用字段，仅 `model_copy` 两个 `z_m`，重新计算 bundle 内容哈希后，只尝试两个公开 multifloor helper。`derive_floor_ladder` 已在装配前失败，故第二个 helper 不可达。

命令原文：

```bash
python - <<'PY'
from pathlib import Path
from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.evidence_contract import (
    CorrectionEvidenceBundleArtifactV1,
    EvidenceContractError,
    finalize_bundle,
)
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry,
    derive_floor_ladder,
)

raw = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json').read_bytes()
honest = adapt_as_drawn_elevation(raw, input_id='review_east', facade_ref='east')
ordered = sorted(honest.bundle.floor_level_claims, key=lambda claim: claim.z_m)
replacement = {
    ordered[0].structure_line_id: 12.34,
    ordered[1].structure_line_id: 17.91,
}
tampered_claims = [
    claim.model_copy(update={'z_m': replacement[claim.structure_line_id]})
    if claim.structure_line_id in replacement else claim
    for claim in honest.bundle.floor_level_claims
]
refs_unchanged = [
    changed.z_ref == original.z_ref
    for changed, original in zip(tampered_claims, honest.bundle.floor_level_claims)
]
tampered_bundle = finalize_bundle(
    honest.bundle.model_copy(update={'floor_level_claims': tampered_claims})
)
tampered = CorrectionEvidenceBundleArtifactV1(
    bundle=tampered_bundle,
    frozen_sources=honest.frozen_sources,
)
print('ROUND2_REPLAY_REFS_UNCHANGED=', all(refs_unchanged))
print('ROUND2_REPLAY_MULTIFLOOR_EXPORTS=', derive_floor_ladder.__name__, assemble_multifloor_geometry.__name__)
try:
    ladder = derive_floor_ladder(tampered)
except EvidenceContractError as exc:
    print('ROUND2_REPLAY_RESULT=REJECTED')
    print('ROUND2_REPLAY_FAILED_AT=derive_floor_ladder')
    print('ROUND2_REPLAY_ERROR_TYPE=', type(exc).__name__)
    print('ROUND2_REPLAY_ERROR_CODE=', exc.code)
    print('ROUND2_REPLAY_ERROR_TEXT=', str(exc))
else:
    print('ROUND2_REPLAY_DERIVE=ACCEPTED', [(x.z_floor_m, x.ceiling_height_m) for x in ladder])
PY
```

输出原文：

```text
ROUND2_REPLAY_REFS_UNCHANGED= True
ROUND2_REPLAY_MULTIFLOOR_EXPORTS= derive_floor_ladder assemble_multifloor_geometry
ROUND2_REPLAY_RESULT=REJECTED
ROUND2_REPLAY_FAILED_AT=derive_floor_ladder
ROUND2_REPLAY_ERROR_TYPE= EvidenceContractError
ROUND2_REPLAY_ERROR_CODE= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE
ROUND2_REPLAY_ERROR_TEXT= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE: {'structure_line_id': 'S05', 'pointer': '/structure_lines/4/pos_m', 'claim_value': 17.91, 'frozen_byte': 3.6}
```

判定：这个具体例子已修复。失败点是 `derive_floor_ladder` 内第一步 `validate_evidence_bundle`（`multifloor.py:260-282`），具名错误为 `EvidenceContractError.code == FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`。

### 2. 自设同形但不同路径：公开 carrier 直接构造成功

结果即阻断项中的 `ALT_*` 原文。它绕过新加的构造函数 `derive_floor_ladder`，而不绕过任何语言访问控制：`ValidatedFloorLadder` 明确在 `__all__` 公开导出。判定：**失败，形成阻断**。

### 3. 范围主张的正面裁定

#### 可测事实 ①：sha256 / 契约分类门实际上拦不拦

本席从零写一份自洽的 `as_drawn_elevation_v0` JSON（闭合 x/z calibration、两条水平结构线、空 openings），让生产 adapter 自己计算 sha、构造冻结 carrier 并在返回前调用 `validate_evidence_bundle`，然后再显式验证、derive、assemble。

命令原文：

```bash
python - <<'PY'
import hashlib
import json
from pathlib import Path
from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.evidence_contract import validate_evidence_bundle
from src.agent.correction.multifloor import derive_floor_ladder, assemble_multifloor_geometry
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.reading.vector_contract import classify_vector_json

doc = {
    'schema': 'as_drawn_elevation_v0',
    'calibration': {
        'x': {'values_mm': [9000.0], 'cum_mm': [0.0, 9000.0], 'overall_mm': 9000.0},
        'z': {'values_mm': [5570.0], 'cum_mm': [0.0, 5570.0], 'overall_mm': 5570.0},
    },
    'structure_lines': [
        {'id': 'invented_base', 'constant_quantity': 'z', 'pos_m': 12.34},
        {'id': 'invented_top', 'constant_quantity': 'z', 'pos_m': 17.91},
    ],
    'openings': [],
}
raw = json.dumps(doc, sort_keys=True, separators=(',', ':')).encode('utf-8')
decision = classify_vector_json(doc)
artifact = adapt_as_drawn_elevation(
    raw, input_id='self_authored_reading', facade_ref='invented'
)
validate_evidence_bundle(artifact)
declared_sha = artifact.frozen_sources[0].artifact.source_output_sha256
measured_sha = hashlib.sha256(raw).hexdigest()
ladder = derive_floor_ladder(artifact)
fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})
assembled = assemble_multifloor_geometry(ladder, [one_floor])
print('SCOPE_CLASSIFICATION=', decision.contract_id, decision.disposition.value)
print('SCOPE_SHA_MATCH=', declared_sha == measured_sha)
print('SCOPE_VALIDATE_EVIDENCE_BUNDLE=PASSED')
print('SCOPE_DERIVED_FROM_SELF_AUTHORED_BYTES=', [(x.z_floor_m, x.ceiling_height_m) for x in ladder])
print('SCOPE_ASSEMBLY_RESULT=', [(x.z_floor, x.ceiling_height) for x in assembled.floors])
PY
```

输出原文：

```text
SCOPE_CLASSIFICATION= as_drawn_elevation_v0 adapt
SCOPE_SHA_MATCH= True
SCOPE_VALIDATE_EVIDENCE_BUNDLE=PASSED
SCOPE_DERIVED_FROM_SELF_AUTHORED_BYTES= [(12.34, 5.57)]
SCOPE_ASSEMBLY_RESULT= [(12.34, 5.57)]
```

事实裁定：**不拦**。`evidence_contract` 的 sha 门验证“冻结 bytes 与声明 hash 是否一致”，契约门验证“内容是否匹配注册的 elevation 形状”；二者都不证明 bytes 由谁产生，也无法区分诚实 reading 与调用方自写但自洽的 reading。

#### 可测事实 ②：B2 原始声明范围本来是否包含防自洽 reading 伪造

任务书 §四 #1-#2（文件本身 `:122-123`）要求的是“未经冻结字节验证的 z 不得装配”和“低层 helper 不得重新获得装配能力”。上述自写 reading 实际通过了既定冻结字节验证；任务书没有追加 reading 来源真实性/签名/授权链要求。

任务书 §五原文（文件本身 `:140-145`）更明确把以下内容列为本轮“明确不做”：

```text
⛔ 碰 `src/agent/correction/evidence_contract.py` / `opening_synthesis.py` / `evidence_adapters.py`
（**T4-a 正被 GPT 席位复审，会撞**）· ⛔ 碰 B4 洞口合成 · ⛔ 动 B3 的立面适配器 ·
⛔ 改任何已落库产物的哈希或基线 · ⛔ `pip install -e .`（venv 全机共享）· ⛔ `git add -A`（逐路径 add）。
```

范围裁定：**施工方主张成立，不记缺口。** 两输入合并为：①该上游门确实覆盖不到“作者真实性”；②B2 本单没有“应覆盖该真实性”的职责，反而明禁施工触碰点名的 reading/evidence 层。不能只凭①把它升级为 B2 缺口。

这与本裁决阻断不冲突：阻断路径根本没有造 reading，也没有通过字节门；它只伪造了公开 `ValidatedFloorLadder` 外壳，属于 §四 #1-#2 明确要求 B2 自己封住的低层装配能力。

## §四七条逐条对账

| # | 判定 | 独立证据与结论 |
|---|---|---|
| 1 | **失败（阻断）** | 上一轮 claim 漂移虽被拒，但公开 `ValidatedFloorLadder((SimpleNamespace(z=...)))` 无字节验证即可装配。所谓“唯一构造入口”不存在；为什么现在构造不出来这句话不成立。 |
| 2 | **失败（并入同一阻断）** | 原路已拒；本席自设的公开 carrier 直接构造路径却装配成功。低层公开类型 + assembly helper 重新获得了生产装配能力。 |
| 3 | **通过** | `run_correction` 的两个旧 `float` 参数已移除，当前只有 `evidence_chain_level`（`pipeline.py:1366`），运行时要求 `_DerivedFloorLevel`（`:1414-1428`），再从其属性构造 projection（`:1442-1445`）。迁移后的 evidence-chain 调用者是 `run_multifloor_correction`（`:1658-1669`），传的是 derive 后的 `level`。这次是旧 `run_correction` 面本身被收窄，不只是旁边增加无人使用的新入口。全仓 `src/` 内 `run_multifloor_correction(` 仍只有定义，已如实记录，但不否定任务书明确允许的“收窄参数类型”迁移方案。 |
| 4 | **通过** | 本席换用“重复 floor id”：相同 footprint 下报 `DUPLICATE_FLOOR_ID`，`NON_FOOTPRINT_WAS_RELABELED=False`。实现已删除 `loc/type` 判据；`PER_FLOOR_FOOTPRINT_MISMATCH` 只在显式 footprint precheck `multifloor.py:425-439` 产生，最终 Pydantic 构造无 catch/relabel（`:441-450`）。 |
| 5 | **通过** | 使用两份不同真实 fixture footprint，具名报 `PER_FLOOR_FOOTPRINT_MISMATCH`。 |
| 6 | **通过** | B2 + o22m7 局部 `57 passed`；定向的三层混排、两层连续性、计划数/非递增/退化/非正层高六项均通过；另独立把真实 east elevation 中间 rung 改为 `8.7654321`、保留 ref、重新 finalize 后，仍报 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`。 |
| 7 | **通过** | 指定同一条环境自证 + 全量命令得到 `3782 passed / 2 skipped / 13 xfailed / 0 failed`，有 summary，exit 0。B2 文件当前 26 tests，基线为 21，`3777 + 5 = 3782` 逐位闭合。 |

### #3 旧生产面改前/改后与调用者：命令、输出原文

命令原文：

```bash
git show a45f778c:src/agent/pipeline.py | rg -n "evidence_chain_(z_floor_m|ceiling_height_m)|def run_correction|def run_multifloor_correction"
rg -n "evidence_chain_(z_floor_m|ceiling_height_m|level)|def run_correction|def run_multifloor_correction" src/agent/pipeline.py
rg -n "run_multifloor_correction\(" src --glob '*.py'
rg -n "run_correction\(" src --glob '*.py'
```

输出原文：

```text
1032:def run_correction_evidence_chain(
1347:def run_correction(
1366:    evidence_chain_z_floor_m: float | None = None,
1367:    evidence_chain_ceiling_height_m: float | None = None,
1389:    mode).  ``evidence_chain_z_floor_m`` / ``evidence_chain_ceiling_height_m``
1406:        if evidence_chain_z_floor_m is None or (
1407:            evidence_chain_ceiling_height_m is None
1411:                    ("evidence_chain_z_floor_m", evidence_chain_z_floor_m),
1413:                        "evidence_chain_ceiling_height_m",
1414:                        evidence_chain_ceiling_height_m,
1438:                z_floor_m=evidence_chain_z_floor_m,
1439:                ceiling_height_m=evidence_chain_ceiling_height_m,
1565:# hand-filled parameter (``evidence_chain_z_floor_m`` /
1566:# ``evidence_chain_ceiling_height_m``) is now DERIVED from B3's
1597:def run_multifloor_correction(
1617:    is fed straight into ``run_correction``'s ``evidence_chain_z_floor_m`` /
1618:    ``evidence_chain_ceiling_height_m``; this function exposes NO z parameter,
1659:            evidence_chain_z_floor_m=level.z_floor_m,
1660:            evidence_chain_ceiling_height_m=level.ceiling_height_m,
1032:def run_correction_evidence_chain(
1347:def run_correction(
1366:    evidence_chain_level: "object | None" = None,
1389:    ``evidence_chain_level`` — a byte-validated ``_DerivedFloorLevel`` minted by
1415:        if evidence_chain_level is None:
1417:                "evidence_chain=True needs evidence_chain_level: a byte-"
1423:        if not isinstance(evidence_chain_level, _DerivedFloorLevel):
1425:                "evidence_chain_level must be a _DerivedFloorLevel minted by "
1444:                z_floor_m=evidence_chain_level.z_floor_m,
1445:                ceiling_height_m=evidence_chain_level.ceiling_height_m,
1605:def run_multifloor_correction(
1625:    ``evidence_chain_level`` (a ``_DerivedFloorLevel`` — ⛔ not two bare z
1669:            evidence_chain_level=level,
src/agent/pipeline.py:1605:def run_multifloor_correction(
src/agent/pipeline.py:484:            + "\nOpen the evidence chain (run_correction(..., "
src/agent/pipeline.py:846:    ``run_correction(evidence_chain=True)`` returns.
src/agent/pipeline.py:1347:def run_correction(
src/agent/pipeline.py:1658:        geom = run_correction(
src/agent/pipeline.py:2310:    geom = run_correction(
```

### #4/#5 非 footprint 错误与真实 footprint 冲突：命令、输出原文

命令原文：

```bash
python - <<'PY'
from pathlib import Path
from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.multifloor import MultiFloorAssemblyError, derive_floor_ladder, assemble_multifloor_geometry
from src.agent.correction.schema import CorrectedGeometryV3

raw = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json').read_bytes()
artifact = adapt_as_drawn_elevation(raw, input_id='review_errors', facade_ref='east')
ladder = derive_floor_ladder(artifact)
a = CorrectedGeometryV3.model_validate_json(Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json').read_text())
b = CorrectedGeometryV3.model_validate_json(Path('AI_agent/logs/experiments/2026-08-25_kernel_probe_from_gt/out/draw_outer.json').read_text())
one_a = a.model_copy(update={'floors': [a.floors[0]], 'windows': [], 'facade_segments': []})
one_b = b.model_copy(update={'floors': [b.floors[0]], 'windows': [], 'facade_segments': []})

print('DUPLICATE_FOOTPRINTS_EQUAL=', a.floors[0].footprint.vertices == a.floors[0].footprint.vertices)
try:
    assemble_multifloor_geometry(ladder, [one_a, one_a])
except MultiFloorAssemblyError as exc:
    print('NON_FOOTPRINT_MODEL_RULE_RESULT=REJECTED')
    print('NON_FOOTPRINT_MODEL_RULE_CODE=', exc.code)
    print('NON_FOOTPRINT_WAS_RELABELED=', exc.code == 'PER_FLOOR_FOOTPRINT_MISMATCH')
else:
    print('NON_FOOTPRINT_MODEL_RULE_RESULT=ACCEPTED')

print('MISMATCH_FOOTPRINTS_EQUAL=', a.floors[0].footprint.vertices == b.floors[0].footprint.vertices)
try:
    assemble_multifloor_geometry(ladder, [one_a, one_b])
except MultiFloorAssemblyError as exc:
    print('TRUE_FOOTPRINT_RESULT=REJECTED')
    print('TRUE_FOOTPRINT_CODE=', exc.code)
else:
    print('TRUE_FOOTPRINT_RESULT=ACCEPTED')
PY
```

输出原文：

```text
DUPLICATE_FOOTPRINTS_EQUAL= True
NON_FOOTPRINT_MODEL_RULE_RESULT=REJECTED
NON_FOOTPRINT_MODEL_RULE_CODE= DUPLICATE_FLOOR_ID
NON_FOOTPRINT_WAS_RELABELED= False
MISMATCH_FOOTPRINTS_EQUAL= False
TRUE_FOOTPRINT_RESULT=REJECTED
TRUE_FOOTPRINT_CODE= PER_FLOOR_FOOTPRINT_MISMATCH
```

### #6 中间 rung 变异重封：命令、输出原文

命令原文：

```bash
python - <<'PY'
from pathlib import Path
from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.evidence_contract import CorrectionEvidenceBundleArtifactV1, EvidenceContractError, finalize_bundle
from src.agent.correction.multifloor import derive_floor_ladder

raw = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json').read_bytes()
honest = adapt_as_drawn_elevation(raw, input_id='review_mid_rung', facade_ref='east')
ordered = sorted(honest.bundle.floor_level_claims, key=lambda claim: claim.z_m)
mid = ordered[len(ordered) // 2]
mutated = [
    claim.model_copy(update={'z_m': 8.7654321}) if claim.structure_line_id == mid.structure_line_id else claim
    for claim in honest.bundle.floor_level_claims
]
resealed = CorrectionEvidenceBundleArtifactV1(
    bundle=finalize_bundle(honest.bundle.model_copy(update={'floor_level_claims': mutated})),
    frozen_sources=honest.frozen_sources,
)
print('BYTE_GATE_MIDDLE_ID=', mid.structure_line_id)
print('BYTE_GATE_MIDDLE_ORIGINAL_Z=', mid.z_m)
print('BYTE_GATE_MIDDLE_MUTATED_Z=', 8.7654321)
print('BYTE_GATE_REF_UNCHANGED=', next(c for c in mutated if c.structure_line_id == mid.structure_line_id).z_ref == mid.z_ref)
try:
    derive_floor_ladder(resealed)
except EvidenceContractError as exc:
    print('BYTE_GATE_RESULT=REJECTED')
    print('BYTE_GATE_ERROR_TYPE=', type(exc).__name__)
    print('BYTE_GATE_ERROR_CODE=', exc.code)
else:
    print('BYTE_GATE_RESULT=ACCEPTED')
PY
```

输出原文：

```text
BYTE_GATE_MIDDLE_ID= S05
BYTE_GATE_MIDDLE_ORIGINAL_Z= 3.6
BYTE_GATE_MIDDLE_MUTATED_Z= 8.7654321
BYTE_GATE_REF_UNCHANGED= True
BYTE_GATE_RESULT=REJECTED
BYTE_GATE_ERROR_TYPE= EvidenceContractError
BYTE_GATE_ERROR_CODE= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE
```

### #6 局部与定向回归：命令、输出原文

局部命令：

```bash
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_b2_multifloor_assembly.py tests/test_o22m7_evidence_wiring.py
```

输出原文：

```text
/tmp/b2rw2_review_gpt/src/agent/correction/multifloor.py
bringing up nodes...
bringing up nodes...

.........................................................                [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
57 passed in 5.73s
```

定向命令：

```bash
python -m pytest -vv -n 6 -p no:cacheprovider \
  tests/test_b2_multifloor_assembly.py::test_two_storey_assembles_and_passes_pipeline_zstack_check \
  tests/test_b2_multifloor_assembly.py::test_three_storey_mixed_heights_assemble_three_floors \
  tests/test_b2_multifloor_assembly.py::test_plan_count_mismatch_is_loud \
  tests/test_b2_multifloor_assembly.py::test_non_ascending_ladder_is_loud \
  tests/test_b2_multifloor_assembly.py::test_degenerate_ladder_is_loud \
  tests/test_b2_multifloor_assembly.py::test_nonpositive_ceiling_is_loud
```

尾部输出原文：

```text
[gw3] [ 16%] PASSED tests/test_b2_multifloor_assembly.py::test_non_ascending_ladder_is_loud
[gw5] [ 33%] PASSED tests/test_b2_multifloor_assembly.py::test_nonpositive_ceiling_is_loud
[gw4] [ 50%] PASSED tests/test_b2_multifloor_assembly.py::test_degenerate_ladder_is_loud
[gw2] [ 66%] PASSED tests/test_b2_multifloor_assembly.py::test_plan_count_mismatch_is_loud
[gw1] [ 83%] PASSED tests/test_b2_multifloor_assembly.py::test_three_storey_mixed_heights_assemble_three_floors
[gw0] [100%] PASSED tests/test_b2_multifloor_assembly.py::test_two_storey_assembles_and_passes_pipeline_zstack_check

F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
============================== 6 passed in 3.39s ===============================
```

### #7 全量、数量与逐位闭合

指定命令原文（同一条环境自证 + pytest；未用 `-n auto`）：

```bash
cd /tmp/b2rw2_review_gpt && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

首行与末尾 summary 原文：

```text
/tmp/b2rw2_review_gpt/src/agent/correction/multifloor.py
3782 passed, 2 skipped, 13 xfailed, 211 warnings in 482.81s (0:08:02)
```

进程 exit 0 且有 summary，故不是资源竞争假红。

测试数核对命令与原文输出：

```bash
rg -n "^def test_" tests/test_b2_multifloor_assembly.py | wc -l
git show a45f778c:tests/test_b2_multifloor_assembly.py | rg -n "^def test_" | wc -l
```

```text
26
21
```

所以 B2 文件新增 5 条，`3777 + 5 = 3782`；skip `2`、xfail `13` 不变，failed `0`。

## 未复现项清单

- **未复现**上一轮“手改 claims 经两个公开 multifloor helper 装配成功”；本轮在 `derive_floor_ladder` 已具名拒绝。
- **未复现**中间 rung 改值、重封 bundle 后被接受；仍具名拒绝。
- **未复现**非 footprint 错误被贴成 `PER_FLOOR_FOOTPRINT_MISMATCH`；重复 id 得到 `DUPLICATE_FLOOR_ID`。
- **未复现**真实 footprint 冲突漏报；仍得到 `PER_FLOOR_FOOTPRINT_MISMATCH`。
- **未复现**旧两个裸 z 参数仍存在；它们已从当前 `run_correction` 签名与 `src/` 调用处消失。
- **未复现**局部或全量测试回归、测试数虚报、无 summary 假红。
- 未重新做上两轮已经由 judge 完成的 GT 像素/米制数值对账；本单要求核类型不变量、错误身份与回归，不要求重算 GT，且本席没有把这项写成新通过证据。
- 未把 B2 与旁支 B4 做合并树组合验证；审对象固定为 `a45f778c..b52c6f5b`，未擅自合并其它分支。

## 操作声明

复核期间**未修改任何项目代码、测试、配置、已落库产物或基线**；未执行 `pip install -e .`，未进入或修改 `/workspaces/EnergyPlus-Agent-dev`。本席只新增本裁决 markdown。开工时工作树已有用户/主控预置并暂存的 `AI_agent/logs/reviews/request/2026-09-04p_B2_rework2_crossreview.md`，保持原状。
