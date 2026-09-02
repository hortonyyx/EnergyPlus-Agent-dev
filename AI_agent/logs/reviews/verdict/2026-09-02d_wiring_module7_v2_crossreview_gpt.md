# 跨家族复核裁决 · 接线（模块 7 上半）v2 · GPT

- **被审 commit**：`17d998e`（施工原件 `687820f` 的逐字 cherry-pick）
- **复核工作树**：`/tmp/joint_review_gpt`，指定 HEAD `2e840f6`
- **裁决**：**REWORK**
- **计数**：**阻断 2 / 不阻断 2**

## 一、先给承重结论：这次模型链确实跑通了，但本单仍不能批准

这次的“跑通”在功能事实上是**真的**：本席没有采信施工档读数，而是从同一份真实
`sm25_2f_v2.json` 出发、不传 `fixed_responses`，独立调用生产入口；186.232 秒后得到
`success=True / exit_reason=success / 2 rounds`，round 0 裁决 22 项，round 1 对新 provisional
给出 `accept`，最终 provisional 哈希与施工档相同：
`c662ce0fba74b7ad79b062406c1170826bfe1ed1b23f3f9c8cae371f1656614a`。

但有两处验收级缺口：

1. **B-1（阻断）**：新建的 `correction_decision` 配置节没有真正接上线。
   `_make_decision_response_provider()` 调 `_section("correction_decision")`，而 `_section()` 会拼成
   `intake_correction_decision`；该键不存在后实际加载旧的 `intake_correction`。因此 route 写出的
   `model:correction_decision` 只表示“请求了这个名字”，不表示“实际加载了这个配置节”。今天两节恰好都指向
   `deepseek-v4-pro`，所以真实模型跑通不受影响；一旦把新节指向另一模型/温度，改动完全不生效。
2. **B-2（阻断）**：无坐标 guard 只识别小写 `x=/y=` 或“两个带小数点的数以逗号/分号相隔”。
   一个真实会出现的整数坐标字符串 `wall endpoint is at (12, 34)` 同时通过 raw guard 和严格 response schema。
   因而验收 5 的一般规则“模型响应结构上没有坐标”未成立；现有 neuter 只证明 decimal-pair 那一种夹具接对线。

## 二、开工自检

命令原文：

```bash
git -C /tmp/joint_review_gpt rev-parse --short HEAD && python -c "import src.agent.pipeline as m; print(m.__file__)"
```

输出原文：

```text
2e840f6
/tmp/joint_review_gpt/src/agent/pipeline.py
```

两条均满足请求书，才继续复核；未执行任何 `pip install` 或写 site-packages 的命令。

## 三、⭐⭐⭐ “这次跑通是不是真的”

### 3.1 独立真实模型复跑：是真的

命令原文（`fixed_responses` **未传**；输出只落 `/tmp`）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
CROSSREVIEW_RUN_DIR=$(mktemp -d /tmp/joint_review_gpt_model_replay_XXXXXX)
export CROSSREVIEW_RUN_DIR
python - <<'PY'
import json
import os
import time
from pathlib import Path
import src.agent.pipeline as pipeline
print(pipeline.__file__, flush=True)
run_dir = Path(os.environ["CROSSREVIEW_RUN_DIR"])
out_dir = run_dir / "1_correction"
source_dir = Path("AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out")
started = time.monotonic()
outcome = pipeline.run_correction_evidence_chain(
    source_dir,
    "sm25_2f_v2.json",
    out_dir=out_dir,
    profile="exploratory",
    round_budget=3,
)
elapsed = time.monotonic() - started
route = json.loads((run_dir / "_run/evidence_chain_route.json").read_text())
print(f"REPLAY_RUN_DIR={run_dir}")
print(f"REPLAY_ELAPSED_SECONDS={elapsed:.3f}")
print(f"REPLAY_SUCCESS={outcome.success}")
print(f"REPLAY_EXIT_REASON={outcome.exit_reason}")
print(f"REPLAY_ROUNDS={len(outcome.rounds)}")
print(f"REPLAY_RESPONSE_SOURCE={route['response_source']}")
print(f"REPLAY_FINAL_PROVISIONAL_SHA256={outcome.final_provisional_sha256}")
print(f"REPLAY_CONTENT_SHA256={outcome.content_sha256}")
print(f"REPLAY_RESIDUAL_OPEN_ITEMS={len(outcome.residual_open_item_ids)}")
print(f"REPLAY_FAILED_CHECKS={[list(r.failed_checks) for r in outcome.rounds]}")
PY
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
REPLAY_RUN_DIR=/tmp/joint_review_gpt_model_replay_5v62uR
REPLAY_ELAPSED_SECONDS=186.232
REPLAY_SUCCESS=True
REPLAY_EXIT_REASON=success
REPLAY_ROUNDS=2
REPLAY_RESPONSE_SOURCE=model:correction_decision
REPLAY_FINAL_PROVISIONAL_SHA256=c662ce0fba74b7ad79b062406c1170826bfe1ed1b23f3f9c8cae371f1656614a
REPLAY_CONTENT_SHA256=d22fe9440c7f622e7a1d5feddd8fb15bd89f7ad54e3076ec6a736f9c1044ee33
REPLAY_RESIDUAL_OPEN_ITEMS=0
REPLAY_FAILED_CHECKS=[[], []]
```

再核复跑产物内部绑定，命令原文：

```bash
python - <<'PY'
import json
from pathlib import Path
from src.agent.correction.decision_executor import decision_hash
from src.agent.correction.decision_schema import CorrectionDecisionResponseV1
from src.agent.correction.window_sources import canonical_sha256
run = Path('/tmp/joint_review_gpt_model_replay_5v62uR')
outcome = json.loads((run / '1_correction/decision_loop_outcome.json').read_text())
route = json.loads((run / '_run/evidence_chain_route.json').read_text())
raw = CorrectionDecisionResponseV1.model_validate_json((run / '1_correction/correction_decision_raw.txt').read_text())
content = dict(outcome)
stored_hash = content.pop('content_sha256')
print(f"ROUTE={route}")
print(f"ROUND_COUNT={len(outcome['rounds'])}")
print(f"ROUND0_SELECTED={len(outcome['rounds'][0]['selected_item_ids'])}")
print(f"ROUND0_FAILED_CHECKS={outcome['rounds'][0]['failed_checks']}")
print(f"ROUND1_SELECTED={len(outcome['rounds'][1]['selected_item_ids'])}")
print(f"ROUND1_FAILED_CHECKS={outcome['rounds'][1]['failed_checks']}")
print(f"LAST_RAW_VERDICT={raw.whole_building_review.verdict}")
print(f"LAST_PACKET_HASH_MATCH={raw.packet_hash == outcome['rounds'][-1]['packet_hash']}")
print(f"LAST_DECISION_HASH_MATCH={decision_hash(raw) == outcome['rounds'][-1]['decision_hash']}")
print(f"OUTCOME_CONTENT_HASH_MATCH={canonical_sha256(content) == stored_hash}")
print(f"RESIDUAL_OPEN_ITEMS={outcome['residual_open_item_ids']}")
print(f"RESIDUAL_DEBTS={outcome['residual_debt_ids']}")
print(f"FINAL_COMPLETION={outcome['final_completion']}")
PY
```

输出原文：

```text
ROUTE={'route': 'evidence_chain', 'source_file': 'sm25_2f_v2.json', 'contract': 'as_drawn_plan', 'adapter': 'adapt_as_drawn_plan', 'profile': 'exploratory', 'round_budget': 3, 'response_source': 'model:correction_decision', 'outcome_success': True, 'exit_reason': 'success', 'outcome_path': '/tmp/joint_review_gpt_model_replay_5v62uR/1_correction/decision_loop_outcome.json'}
ROUND_COUNT=2
ROUND0_SELECTED=22
ROUND0_FAILED_CHECKS=[]
ROUND1_SELECTED=0
ROUND1_FAILED_CHECKS=[]
LAST_RAW_VERDICT=accept
LAST_PACKET_HASH_MATCH=True
LAST_DECISION_HASH_MATCH=True
OUTCOME_CONTENT_HASH_MATCH=True
RESIDUAL_OPEN_ITEMS=[]
RESIDUAL_DEBTS=['debt_dimensions_sm25_2f_v2', 'debt_elevation_openings_sm25_2f_v2', 'debt_room_roles_sm25_2f_v2']
FINAL_COMPLETION=degraded
```

### 3.2 `response_source` 是谁写的，固定响应与模型路径分不分得开

结论：

- `response_source` **不是模型自报**。它由 `src/agent/pipeline.py:1050-1059` 根据
  `fixed_responses is not None` 的本地分支写成 `fixed_responses(...; model NOT called)` 或
  `model:<requested section name>`，再由 `src/agent/pipeline.py:1093-1114` 落盘。
- 因此正常代码路径上，fixture 与 model provider 在产物上**分得开**；模型响应 schema 根本没有这个字段，模型不能从响应里自称来源。
- 但它是普通、无签名 JSON，落盘后当然可被人手改；更重要的是 B-1 已实证：当前字符串记录的是**请求名**，不是实际解析到的配置节。
  所以该字段可承载“fixed/provider 分支”结论，不能单独承载“实际用了哪个配置节/模型”结论。

配置节探针与坐标绕过合并命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python - <<'PY'
import json
from pathlib import Path
import src.agent.pipeline as pipeline
from src.agent.correction.decision_executor import decision_hash
from src.agent.correction.decision_schema import (
    CorrectionDecisionResponseV1,
    assert_response_payload_carries_no_coordinates,
)
from src.agent.correction.window_sources import canonical_sha256
print(pipeline.__file__)
selected = []
real_loader = pipeline.load_llm_section
pipeline.load_llm_section = lambda name: selected.append(name) or {"selected": name}
try:
    resolved = pipeline._section("correction_decision")
finally:
    pipeline.load_llm_section = real_loader
print(f"CONFIG_REQUEST=correction_decision CONFIG_ACTUALLY_LOADED={selected[0]}")
print(f"CONFIG_PROBE_RESULT={resolved}")
payload = {
    "packet_hash": "a" * 64,
    "item_decisions": [{
        "item_id": "item_realistic_integer_coordinate",
        "action": "reject_all",
        "reason_code": "wall endpoint is at (12, 34)",
    }],
    "whole_building_review": {"verdict": "accept"},
}
assert_response_payload_carries_no_coordinates(payload)
parsed = CorrectionDecisionResponseV1.model_validate_json(json.dumps(payload))
print(f"INTEGER_COORDINATE_SMUGGLE_GUARD=PASSED SCHEMA=PASSED reason_code={parsed.item_decisions[0].reason_code!r}")
base = Path("AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run")
outcome = json.loads((base / "1_correction/decision_loop_outcome.json").read_text())
raw_text = (base / "1_correction/correction_decision_raw.txt").read_text()
raw = CorrectionDecisionResponseV1.model_validate_json(raw_text)
content = dict(outcome)
stored_outcome_hash = content.pop("content_sha256")
print(f"ARCHIVE_LAST_PACKET_HASH_MATCH={raw.packet_hash == outcome['rounds'][-1]['packet_hash']}")
print(f"ARCHIVE_LAST_DECISION_HASH_MATCH={decision_hash(raw) == outcome['rounds'][-1]['decision_hash']}")
print(f"ARCHIVE_OUTCOME_CONTENT_HASH_MATCH={canonical_sha256(content) == stored_outcome_hash}")
print("ARCHIVE_ROUND0_RAW_PRESENT=False (the single correction_decision_raw.txt contains round 1 only)")
PY
sha256sum AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/0_reading/sm25_2f_v2.json AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
CONFIG_REQUEST=correction_decision CONFIG_ACTUALLY_LOADED=intake_correction
CONFIG_PROBE_RESULT={'selected': 'intake_correction'}
INTEGER_COORDINATE_SMUGGLE_GUARD=PASSED SCHEMA=PASSED reason_code='wall endpoint is at (12, 34)'
ARCHIVE_LAST_PACKET_HASH_MATCH=True
ARCHIVE_LAST_DECISION_HASH_MATCH=True
ARCHIVE_OUTCOME_CONTENT_HASH_MATCH=True
ARCHIVE_ROUND0_RAW_PRESENT=False (the single correction_decision_raw.txt contains round 1 only)
bdf9a6fbd0e6ac6694575b748ca3c34f124ac7b4f11551e2ea816340e774d9e2  AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/0_reading/sm25_2f_v2.json
bdf9a6fbd0e6ac6694575b748ca3c34f124ac7b4f11551e2ea816340e774d9e2  AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json
```

### 3.3 `success=True` 的四部分都真的被判了，且没有一项恒真

语义四部分与代码对应如下（第三部分本来就是“accept + 同 provisional hash”的一个语义条件）：

1. **无 blocking open item**：独立真模型复跑 `RESIDUAL_OPEN_ITEMS=[]`；负夹具
   `test_success_conjunct_open_item_falsified` 可单独打红。
2. **确定性检查通过**：两轮 `FAILED_CHECKS=[]`；负夹具
   `test_success_conjunct_checks_falsified` 制造 overlap，只使这一项为 false。
3. **模型对同一个 provisional 给 accept**：最后 raw 为 `accept`，packet/decision hash 均与最后 round 匹配；
   `test_success_conjunct_accept_falsified`、`test_select_round_cannot_succeed_on_its_own_accept` 分别打掉 verdict 与同-hash 绑定，
   `test_success_requires_next_round_accept_of_new_hash` 是正对照。
4. **没有 profile 禁止的 residual debt**：真实三条债都是 support-channel `missing_channel`，策略逐条为 false；
   `test_success_conjunct_debt_falsified_under_exploratory` 用 `ambiguous_face` 证明该项不是恒真。

定向命令原文（连同模块 7 全部新锁）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o22m7_evidence_wiring.py tests/test_o22m56_decision_loop.py::test_success_conjunct_open_item_falsified tests/test_o22m56_decision_loop.py::test_success_conjunct_checks_falsified tests/test_o22m56_decision_loop.py::test_success_conjunct_accept_falsified tests/test_o22m56_decision_loop.py::test_success_conjunct_debt_falsified_under_exploratory tests/test_o22m56_decision_loop.py::test_select_round_cannot_succeed_on_its_own_accept tests/test_o22m56_decision_loop.py::test_success_requires_next_round_accept_of_new_hash tests/test_f97_vector_contract.py::test_b3_as_drawn_directory_is_refused_by_the_pasted_json_leg tests/test_o22m1_as_drawn_producer_types.py::test_only_the_two_named_contracts_hold_wires
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

..............................                                           [100%]
30 passed in 5.58s
```

债务策略实测命令原文：

```bash
python - <<'PY'
from pathlib import Path
from src.agent.correction.decision_executor import _debt_blocks_success
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
p = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json')
a = adapt_as_drawn_plan(p.read_bytes(), input_id=p.stem, floor_ref='2f')
for debt in a.bundle.evidence_debts:
    print(f"DEBT id={debt.debt_id} kind={debt.kind} channel={debt.channel} exploratory_blocks={_debt_blocks_success(debt.kind, debt.channel, 'exploratory')}")
PY
```

输出原文：

```text
DEBT id=debt_dimensions_sm25_2f_v2 kind=missing_channel channel=dimensions exploratory_blocks=False
DEBT id=debt_elevation_openings_sm25_2f_v2 kind=missing_channel channel=elevation_openings exploratory_blocks=False
DEBT id=debt_room_roles_sm25_2f_v2 kind=missing_channel channel=room_roles exploratory_blocks=False
```

## 四、三条假说

### H1：没有静默第三态——成立

`ADAPT` 在分类账内确实“不进 consumed、不当 offender、进入 adapted”；但这不是最终静默通道。
当 `run_correction()` 保持默认 `evidence_chain=False` 时，真实 ADAPT 文件使 pasted-JSON 腿在模型调用前抛
`UnconsumableVectorFile`，文件名与开关都被点名，LLM 没有被调用。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import src.agent.pipeline as pipeline
print(pipeline.__file__)
src = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json')
with TemporaryDirectory(prefix='joint_review_h1_') as tmp:
    run = Path(tmp)
    vector = run / '0_reading'
    vector.mkdir()
    (vector / src.name).write_bytes(src.read_bytes())
    (vector / 'reading_summary.md').write_text('cross-review H1 summary', encoding='utf-8')
    out = run / '1_correction'
    out.mkdir()
    called = []
    real_call = pipeline._call_json_llm
    pipeline._call_json_llm = lambda *a, **k: called.append(True) or (_ for _ in ()).throw(AssertionError('LLM touched'))
    try:
        pipeline.run_correction(vector, '{}', out_dir=out)
    except Exception as exc:
        print(f"H1_EXCEPTION_TYPE={type(exc).__name__}")
        print(f"H1_EXCEPTION={exc}")
    finally:
        pipeline._call_json_llm = real_call
    print(f"H1_LLM_CALLED={bool(called)}")
PY
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
H1_EXCEPTION_TYPE=UnconsumableVectorFile
H1_EXCEPTION=1_correction pasted-JSON leg refuses to run over /tmp/joint_review_h1_wndftqmg/0_reading: 1 file(s) are wired to the correction evidence adapter (module 7) and must NOT be silently dropped from this run's evidence:
  - sm25_2f_v2.json
Open the evidence chain (run_correction(..., evidence_chain=True)) or move these products out of this run's 0_reading directory.
H1_LLM_CALLED=False
```

### H2：翻 pin 后规则仍活——成立

继任规则同时精确锁住 `consuming == {reading_view_legacy}` 与 `adapting == {as_drawn_plan}`。
本席没有只运行施工方内置的 monkeypatch 自证，而是临时在生产 `CONTRACTS` 里加入第三个 `ADAPT` 合同；两把真实规则锁同时红，恢复源码后又回绿。

临时变异原文：

```diff
     ContractSpec(
         CONTRACT_STAGE_CHECK_REPORT,
         Disposition.EXCLUDE,
         _detect_stage_check_report,
         "undeclared sidecar: declares stage/results/report_schema_version AND "
         "parses as validator/checks/schema.py:CheckReport",
     ),
+    ContractSpec(
+        "crossreview_third_adapting_contract",
+        Disposition.ADAPT,
+        lambda raw: False,
+        "temporary GPT cross-review mutation",
+    ),
 )
```

变异后命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o22m1_as_drawn_producer_types.py::test_only_the_two_named_contracts_hold_wires tests/test_o22m7_evidence_wiring.py::test_4b_the_wiring_rule_holds_on_the_real_contracts
```

输出原文（预期红）：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

FF                                                                       [100%]
E       AssertionError: evidence chain quietly grew: {'as_drawn_plan', 'crossreview_third_adapting_contract'}
E       AssertionError: assert {'as_drawn_pl...ing_contract'} == {'as_drawn_plan'}
FAILED tests/test_o22m1_as_drawn_producer_types.py::test_only_the_two_named_contracts_hold_wires
FAILED tests/test_o22m7_evidence_wiring.py::test_4b_the_wiring_rule_holds_on_the_real_contracts
2 failed in 3.25s
```

恢复后命令与输出原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o22m1_as_drawn_producer_types.py::test_only_the_two_named_contracts_hold_wires tests/test_o22m7_evidence_wiring.py::test_4b_the_wiring_rule_holds_on_the_real_contracts tests/test_o22m7_evidence_wiring.py::test_5_the_beat_rejects_smuggled_coordinates_end_to_end tests/test_f97_vector_contract.py::test_b3_as_drawn_directory_is_refused_by_the_pasted_json_leg
```

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

....                                                                     [100%]
4 passed in 3.42s
```

### H3：现有 decimal-pair 锁是实现挣的，但一般“无坐标”规则仍失败

摘掉 `_validate_against()` 内 guard 调用后，现有端到端拒绝锁确实由绿变红；所以施工方的 neuter 对**那一种夹具**成立，不是夹具/schema 自己撑绿。
然而 §三验收 5 是一般规则，本席新增的整数坐标真实形态已在 B-2 中穿过 guard 与 schema，故 H3 总裁定为**部分成立、验收失败**。

临时 neuter 原文：

```diff
     def _validate_against(packet: object, parsed: dict) -> None:
-        assert_response_payload_carries_no_coordinates(parsed)
+        # Temporary GPT cross-review neuter: coordinate guard removed.
         if parsed.get("packet_hash") != packet.packet_hash:
```

neuter 后命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o22m7_evidence_wiring.py::test_5_the_beat_rejects_smuggled_coordinates_end_to_end
```

输出原文（预期红）：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
E       Failed: DID NOT RAISE <class 'RuntimeError'>
FAILED tests/test_o22m7_evidence_wiring.py::test_5_the_beat_rejects_smuggled_coordinates_end_to_end
1 failed in 3.32s
```

## 五、施工方自披露边界：`adapted` 是“加不改”，认可

裁定：**认可，不构成禁止的 ledger 重排**。

- `VectorDirDecision` 新增 `adapted`，`as_ledger()` 在既有 `consumed` 后插入新键；既有键
  `ledger_version / consumed / counts / files` 的相对顺序及含义均未改变。
- `as_ledger()` 在 `vector_contract.py` 外零直接消费者；生产侧新增消费者读的是
  `VectorDirDecision.adapted`，不是按 ledger 位置解包。
- `vector_contract.py` 内无 `sha256`，没有被此次键增加破坏的账本哈希。

命令原文：

```bash
python - <<'PY'
from src.agent.reading.vector_contract import VectorDirDecision
print(f"LEDGER_KEYS={list(VectorDirDecision(consumed=[], adapted=[], rows=[]).as_ledger())}")
PY
rg -n '\.as_ledger\(' src tests || true
rg -n 'sha256' src/agent/reading/vector_contract.py || true
```

输出原文：

```text
LEDGER_KEYS=['ledger_version', 'consumed', 'adapted', 'counts', 'files']
src/agent/reading/vector_contract.py:570:    ).as_ledger()
```

最后一条 `rg sha256` 无输出。

## 六、七条验收逐条裁定

| 验收 | 裁定 | 独立证据 |
|---|---|---|
| 1 | ✅ | 真实 `sm25_2f_v2.json`、真实 model provider 独立复跑；186.232 s、2 轮、22 项、`success=True`，终局哈希与施工档一致。 |
| 2 | ✅ | 当前指定 HEAD 全量 `3657 passed / 13 xfailed / 0 failed`；多出的 3 条来自当前分支早已在被审提交父提交中的 F156/O21d 并行工作，不是本 diff 回归。变动锁清单见 §七。 |
| 3 | ✅ | `tests/test_o22m7_evidence_wiring.py` 的 source_read / adapt / compile / model / loop 五环均独立造错；异常穿出、failure record 点名、无 outcome 成功产物；定向 30 条全绿。 |
| 4 | ✅ | 真实新格式走 as-drawn adapter，真实旧格式走 legacy adapter，损坏且带 legacy disguise 的新格式仍 UNKNOWN；定向全绿。 |
| 4b | ✅ | 两集合均锁；生产源码临时加入第三条 ADAPT 后两锁 `2 failed`，恢复后回绿。 |
| 5 | ❌ | decimal-pair neuter 证明接线存在，但整数坐标 `(12, 34)` 同时过 guard/schema；一般规则未满足（B-2）。 |
| 6 | ✅ | 指定 `.env`、同命令导入自证、`-n 6 -p no:cacheprovider`：全量 0 failed。 |

## 七、验收 2 的锁变动清单

### 7.1 既有 pin：实测是 7 个测试函数受影响，不是请求书 H2 写的 8 个

1. `test_f97_vector_contract.py::test_b3_as_drawn_plan_is_known_but_not_consumed`
   → `test_b3_as_drawn_plan_is_wired_to_the_adapter`：旧规则“不贴 prompt”由 `ADAPT` 分流继续保护。
2. `test_f97_vector_contract.py::test_nf1_empty_face_lines_list_is_still_as_drawn_plan`（名字未改、断言翻 pin）：
   诚实空 reading 仍识别为 as-drawn，但 disposition 由等待接线改成 `ADAPT`。
3. `test_f97_vector_contract.py::test_b3_as_drawn_raises_and_says_known_not_unknown`
   → `test_b3_as_drawn_directory_is_refused_by_the_pasted_json_leg`：旧腿仍响亮拒绝并点名新开关。
4. `test_o22m1_as_drawn_producer_types.py::test_as_drawn_is_still_known_but_not_consumed`
   → `test_as_drawn_plan_is_wired_to_the_adapter`：注册已发生但仍不进 CONSUME。
5. `test_o22m1_as_drawn_producer_types.py::test_no_new_contract_became_consumable`
   → `test_only_the_two_named_contracts_hold_wires`：同时精确保护 consuming 与 adapting 两集合。
6. `test_o22m2_evidence_contract.py::test_as_drawn_is_still_not_consumed`
   → `test_as_drawn_plan_is_adapt_not_consumed`：模块 2 保持分层，但 pin 跟随注册翻转。
7. `test_o22m3_evidence_adapters.py::test_as_drawn_is_still_not_consumed`
   → `test_as_drawn_plan_is_adapt_not_consumed`：adapter 成为真实 wire，仍不贴 prompt。

### 7.2 新增 22 条锁及其规则

1. `test_route_direction_1_new_format_plan_takes_the_as_drawn_adapter`：真实新格式路由。
2. `test_route_direction_2_legacy_view_takes_the_legacy_adapter`：真实旧格式统一进 bundle。
3. `test_route_direction_3_damaged_new_format_is_unknown_never_legacy`：损坏声明不回落 legacy。
4. `test_link_failure_source_read`：源读取失败穿出并点名。
5. `test_link_failure_adapt`：adapter 失败穿出并点名。
6. `test_link_failure_compile`：compiler 失败穿出并点名。
7. `test_link_failure_model`：模型 transport 失败穿出并点名。
8. `test_link_failure_loop`：loop 内容错误穿出并点名。
9. `test_evidence_chain_switch_defaults_off`：显式开关默认关闭。
10. `test_switch_on_reaches_the_terminus_loudly`：开启后到 module 7 终点，不伪造 `CorrectedGeometry`。
11. `test_switch_on_without_a_product_is_a_loud_value_error`：开启必须点名冻结产物。
12. `test_4b_the_wiring_rule_holds_on_the_real_contracts`：两线集合精确值。
13. `test_4b_a_third_contract_quietly_turning_adapting_goes_red`：第三条 adapting 变异自证。
14. `test_4b_a_third_contract_quietly_turning_consuming_goes_red`：第三条 consuming 变异自证。
15. `test_adapt_files_are_named_not_consumed_not_offenders`：ADAPT 的 ledger 三态语义。
16. `test_5_guard_passes_legal_and_rejects_every_smuggle_channel`：当前三种 guard 夹具。
17. `test_5_the_beat_rejects_smuggled_coordinates_end_to_end`：raw→provider 端到端拒绝。
18. `test_5_neuter_the_guard_and_the_rejection_disappears`：摘 guard 后 decimal pair 放行。
19. `test_provider_seats_the_model_in_the_loop`：provider 每轮收到当前 packet。
20. `test_response_sources_are_mutually_exclusive`：fixed/provider 不可同时给。
21. `test_provider_mode_requires_an_explicit_round_budget`：provider 必须有限预算。
22. `test_outcome_lands_with_as_measured_success_and_exit_reason`：outcome 如实落盘，失败不冒充成功。

清单命令与输出原文：

```bash
rg -n '^def test_' tests/test_o22m7_evidence_wiring.py
rg -n '^def test_' tests/test_o22m7_evidence_wiring.py | wc -l
```

```text
117:def test_route_direction_1_new_format_plan_takes_the_as_drawn_adapter(tmp_path):
139:def test_route_direction_2_legacy_view_takes_the_legacy_adapter(tmp_path):
163:def test_route_direction_3_damaged_new_format_is_unknown_never_legacy(tmp_path):
206:def test_link_failure_source_read(tmp_path, booby_trap_pasteed_leg):
217:def test_link_failure_adapt(tmp_path, booby_trap_pasteed_leg):
250:def test_link_failure_compile(tmp_path, booby_trap_pasteed_leg):
291:def test_link_failure_model(tmp_path, booby_trap_pasteed_leg, monkeypatch):
308:def test_link_failure_loop(tmp_path, booby_trap_pasteed_leg):
333:def test_evidence_chain_switch_defaults_off():
340:def test_switch_on_reaches_the_terminus_loudly(tmp_path, booby_trap_pasteed_leg):
364:def test_switch_on_without_a_product_is_a_loud_value_error(tmp_path):
391:def test_4b_the_wiring_rule_holds_on_the_real_contracts():
397:def test_4b_a_third_contract_quietly_turning_adapting_goes_red(monkeypatch):
415:def test_4b_a_third_contract_quietly_turning_consuming_goes_red(monkeypatch):
436:def test_adapt_files_are_named_not_consumed_not_offenders(tmp_path):
531:def test_5_guard_passes_legal_and_rejects_every_smuggle_channel():
553:def test_5_the_beat_rejects_smuggled_coordinates_end_to_end(
580:def test_5_neuter_the_guard_and_the_rejection_disappears(
615:def test_provider_seats_the_model_in_the_loop(tmp_path):
662:def test_response_sources_are_mutually_exclusive(tmp_path):
698:def test_provider_mode_requires_an_explicit_round_budget(tmp_path):
724:def test_outcome_lands_with_as_measured_success_and_exit_reason(tmp_path):
22
```

## 八、全量

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

输出原文（导入行与 pytest 汇总行）：

```text
/tmp/joint_review_gpt/src/agent/pipeline.py
3657 passed, 13 xfailed, 211 warnings in 462.81s (0:07:42)
```

退出码原文：`0`。

请求书/施工档的 `3654` 来自施工原树；当前指定分支在施工基线 `36f80be` 与被审 cherry-pick 的父提交
`11d8b72` 之间已有另一条并行 F156/O21d 工作新增 3 条测试，所以当前树正好为 `3654 + 3 = 3657`。

命令原文：

```bash
git diff --no-ext-diff 36f80be..11d8b72 -- tests | rg '^\+def test_|^-def test_' || true
```

输出原文：

```text
+def test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated(facts):
+def test_flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view(real_inputs):
+def test_a_flood_in_one_view_reddens_where_a_global_count_would_stay_green(real_inputs):
```

## 九、不阻断发现

### NF-1：多轮模型 raw/thinking 被同名文件覆盖，首轮 22 条决定无法从归档独立重算

`_call_json_llm()` 每一轮都写同一个 `correction_decision_raw.txt` / `correction_decision_thinking.txt`；
施工归档和本席复跑归档都只保留 round 1 的空决策 accept。`DecisionLoopOutcomeV1` 留了 round 0 的
`decision_hash` 与 22 个 selected item ids，但没留 candidate ids / reason codes，因此第三方不能从归档重算 round 0 decision hash。
这不推翻本席的独立真模型复跑，也不影响 loop 正确性，故列不阻断；但它削弱“只核落盘证据”时对首轮裁决的可审计性。

对应原始探针输出：

```text
ARCHIVE_LAST_PACKET_HASH_MATCH=True
ARCHIVE_LAST_DECISION_HASH_MATCH=True
ARCHIVE_OUTCOME_CONTENT_HASH_MATCH=True
ARCHIVE_ROUND0_RAW_PRESENT=False (the single correction_decision_raw.txt contains round 1 only)
```

### NF-2：请求书 H2 写“8 把 pin”，被审 diff 实际影响 7 个既有测试函数

六个函数改名，另一个 `test_nf1_empty_face_lines_list_is_still_as_drawn_plan` 保持名字但翻 disposition 断言，合计 7；
施工 commit message 也写 7。继任规则与变异能力本身成立，故这是 B 层外围计数不对称，不阻断。

## 十、返工最小要求

1. 让 decision beat 直接解析并加载实际的 `correction_decision` 节（或统一重命名为 `_section()` 真正支持的键），
   并加锁：给 `correction_decision` 与 `intake_correction` 两个不同 model sentinel，断言 provider 实际拿到前者；route 应记录**解析后的**节/模型，而不是只回显请求名。
2. 修复字符串坐标通道。至少让整数 pair、大小写/带空格的轴赋值、括号/数组常见坐标形式过反例；更稳的方向是收窄
   `reason_code` 为 code token，并让可自由叙述字段采用不可能承载坐标的类型化词表，而不是继续穷举坐标正则。
3. 为 B-1、B-2 各补一个先红后绿锁；重跑本文件列出的定向命令与全量。

---

**最终裁决：REWORK · 阻断 2 · 不阻断 2。**
