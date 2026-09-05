# 裁决 · T4-a 返工 1 跨家族审（GPT 家族复核席）

- 日期：2026-09-04
- 施工方：GLM 家族
- 复核方：GPT 家族
- 审对象：`git diff a91a1524..df57f9a3`
- 工作树：`/tmp/t4a_rw_review_gpt`，detached `df57f9a3`

## 一、裁决

**REWORK · 阻断 1 / 不阻断 2**

唯一阻断是验收 #1 没有成立：从活键生成的 19 项近错电池只覆盖有限词法族；在 seam 外挂一个与活键无字面相似的兼容映射 `"owner_b4" -> 活键` 后，注册表仍是 plain `dict`、键仍全是 plain `str`，import 审计通过，live-key identity 钉也保持成立。更关键的是，用施工锁自己采用的 `model_construct` 运行面造债后，`assert_obligations_backed` 通过，销账 binding 将该债实际退休，而整份新增锁仍为 **`28 passed`**。因此施工档所称“族外任意串由闭枚举 schema + 销账 binding 闭环兜住”只成立了一半：普通字符串经 `model_validate` 确实被 schema 拒绝，但 binding 并没有挡住 schema-bypass 债；它信任 resolver 返回的 canonical key/row，未再核原始 `debt.obligation`。

这正是没有锁住的方向：**解析函数的前像被扩张到有限近错族之外，而 live key、registry carrier、stored key 均不变**。`near_misses()` 只枚举有限变形（`tests/test_t4a_rework1_resolution_lock.py:77-112`），identity 钉只量 live keys（`:194-203`），两道类型钉只量全局注册表与其 stored keys（`opening_synthesis.py:338-365, 513-524`）；没有一条锁量“所有成功解析输入的集合必须恰等于 live key set”。验收明文允许用“别名 / 兼容表”任一扩法判红，本反例令其全绿，所以必须返工。

两个不阻断 finding：

1. `type(DEBT_REDEMPTION_REGISTRY) is dict` 会拒绝保持精确单值语义、且更安全的 `MappingProxyType`。实测其 exact lookup 指向同一 row，却在 import 与 seam 同报 `DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT`。这道钉确能挡住 `dict` 子类覆写，但它锁的是**可变 plain-dict 实现**，不是“精确单值查找”不变量；没有合法只读出口。
2. 查询侧仍有与 stored-key 钉不对称的 Python 对象边界：一个字面值为 `"owner_b4"`、但自定义 hash/equality 指向活键的 `str` 子类可通过 `EvidenceDebtV1.model_validate`，并被 Pydantic 规范成 canonical plain `str`。输出后的债仍安全地携带 canonical 值，故本轮不升阻断；但“strict Literal 拒一切未定义输入”的自证对 Python-object 输入并不准确，应明确边界或加 exact-input-type validator。

### 开工自检原文

命令：

```bash
cd /tmp/t4a_rw_review_gpt && pwd && git log --oneline -1 && git status --porcelain
```

输出：

```text
/tmp/t4a_rw_review_gpt
df57f9a3 T4-a rework1 execution report: regression direction bought back, 3809 = 3781 + 28
A  AI_agent/logs/reviews/request/2026-09-04v_T4a_rework1_crossreview.md
```

## 二、派工单 §三六条逐条对账

### #1 「债→行解析被扩成一对多/别名/兼容表时有锁」：失败，阻断 B-1

独立扩法没有复用施工测试的直接赋值安装法；用 `unittest.mock.patch.object` 在进程内给 seam 外挂兼容映射，且用 `-n 0` 保证进程内补丁真实作用于被测锁（全量仍按规定使用 `-n 6`）。

命令原文：

```bash
python - <<'PY'
from unittest.mock import patch
import pytest
from pydantic import ValidationError
import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import ArtifactPointerV1, EvidenceDebtV1
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0
key = next(iter(osm.DEBT_REDEMPTION_REGISTRY)); alias = "owner_b4"
real = osm.redemption_row_for_obligation
def compat(name): return real({alias: key}.get(name, name))
base = {"debt_id":"review_arbitrary_alias", "kind":"other_known_missing",
        "channel":None, "affected_refs":(), "description":"review"}
try: EvidenceDebtV1.model_validate({**base, "obligation":alias})
except ValidationError as exc:
    print("SCHEMA=" + next(e for e in exc.errors() if e["loc"] == ("obligation",))["type"])
source = osm.ElevationSourceIdentity("review_input", CONTRACT_AS_DRAWN_ELEVATION_V0, "a" * 64)
ref = ArtifactPointerV1.model_validate({"input_id":source.input_id,
    "source_contract_id":source.source_contract_id,
    "source_output_sha256":source.source_output_sha256, "json_pointer":"/calibration"})
debt = EvidenceDebtV1.model_construct(**{**base, "affected_refs":(ref,)}, obligation=alias)
executed = osm.ExecutedRedemption(key, osm.DEBT_REDEMPTION_REGISTRY[key], source)
with patch.object(osm, "redemption_row_for_obligation", new=compat):
    print("STRUCTURE=" + type(osm.DEBT_REDEMPTION_REGISTRY).__name__ + "/" +
          ",".join(sorted({type(k).__name__ for k in osm.DEBT_REDEMPTION_REGISTRY})))
    osm._assert_registry_well_formed(); print("AUDIT=PASS")
    osm.assert_obligations_backed([debt]); print("BACKING=PASS")
    print("REDEEMED=" + repr(osm.redeemable_debt_ids([debt], executed=executed)))
    rc = pytest.main(["-q", "-n", "0", "--disable-warnings", "-p", "no:cacheprovider",
                      "tests/test_t4a_rework1_resolution_lock.py"])
    print("LOCK_RC=" + str(int(rc)))
try: real(alias)
except osm.OpeningSynthesisError as exc: print("RESTORED_ALIAS=" + exc.code)
osm._assert_registry_well_formed(); print("RESTORED_AUDIT=PASS")
PY
```

输出原文：

```text
SCHEMA=literal_error
STRUCTURE=dict/str
AUDIT=PASS
BACKING=PASS
REDEEMED=('review_arbitrary_alias',)
............................                                             [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
28 passed, 1 warning in 0.04s
LOCK_RC=0
RESTORED_ALIAS=OBLIGATION_UNBACKED
RESTORED_AUDIT=PASS
```

结论：schema 对普通 `"owner_b4"` 有牙；但施工方声称的第二层 binding 没牙，而且新增的 28 项锁对这一可观测扩法全绿。`redeemable_debt_ids` 在 `opening_synthesis.py:670-673` 比较的是 seam 返回的 `key,row`；compat seam 返回 canonical key/row 后，原始 alias 不再参与 binding。

### #2 没有为让锁红而把缺陷造回来：通过

生产中没有 alias、normalization、compat table 或多候选路径；`EvidenceDebtV1` 闭枚举和 10 个 mint 点所在的两个文件零改动。新 seam 仍先做 exact membership，再按同一 key 单值索引（`opening_synthesis.py:525-551`）。

命令原文：

```bash
git diff --exit-code a91a1524..df57f9a3 -- src/agent/correction/evidence_contract.py src/agent/correction/evidence_adapters.py && echo 'CONTRACT_AND_MINT_CODE_DIFF=NONE'
git diff --unified=0 a91a1524..df57f9a3 -- src/agent/correction/opening_synthesis.py | rg '^[+-].*(startswith|DEBT_REDEMPTION_REGISTRY\[obligation\]|obligation not in DEBT_REDEMPTION_REGISTRY|redemption_row_for_obligation)'
```

输出原文：

```text
CONTRACT_AND_MINT_CODE_DIFF=NONE
+single seam, :func:`redemption_row_for_obligation`, and it is exact
+def redemption_row_for_obligation(obligation: str) -> tuple[str, DebtRedemption]:
+    if obligation not in DEBT_REDEMPTION_REGISTRY:
+    return obligation, DEBT_REDEMPTION_REGISTRY[obligation]
+    :func:`redemption_row_for_obligation` -- THE seam -- so this entry
-        if debt.obligation not in DEBT_REDEMPTION_REGISTRY:
+        redemption_row_for_obligation(debt.obligation)
+       (:func:`redemption_row_for_obligation`, rework 1 of T4-a):
+        key, row = redemption_row_for_obligation(debt.obligation)
+    "redemption_row_for_obligation",
```

结论：当前生产结构仍是闭枚举 + plain dict + 精确 membership/index；返工没有把旧前缀缺陷造回来。B-1 是回归锁分辨力不足，不是当前生产默认路径已安装别名。

### #3 两个错误码不再指同一件事：通过

代码归属已拆开：`DEBT_REGISTRY_PREMISE_AMBIGUOUS` 在 import 审计（`opening_synthesis.py:409-417`），`PREMISE_GATE_AMBIGUOUS` 在 premise runtime lookup（`:473-477`）；`DEBT_TYPE_AMBIGUOUS` 回到 obligation seam 的 claimant 检查（`:533-550`）。独立注入两行共享 premise 时，premise 两道牙响，债侧 exact hit 本身不响 `DEBT_TYPE_AMBIGUOUS` 且照常退休。

命令原文：

```bash
python - <<'PY'
from unittest.mock import patch
import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import ArtifactPointerV1, EvidenceDebtV1
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0
key = next(iter(osm.DEBT_REDEMPTION_REGISTRY)); row = osm.DEBT_REDEMPTION_REGISTRY[key]
source = osm.ElevationSourceIdentity("review_input", CONTRACT_AS_DRAWN_ELEVATION_V0, "c" * 64)
ref = ArtifactPointerV1.model_validate({"input_id":source.input_id,
    "source_contract_id":source.source_contract_id,
    "source_output_sha256":source.source_output_sha256, "json_pointer":"/calibration"})
debt = EvidenceDebtV1.model_validate({"debt_id":"review_direction", "kind":"other_known_missing",
    "channel":None, "affected_refs":(ref,), "description":"direction", "obligation":key})
executed = osm.ExecutedRedemption(key, row, source)
with patch.dict(osm.DEBT_REDEMPTION_REGISTRY,
                {"review_distinct_obligation": osm.DebtRedemption(row.premise, row.gate)}):
    for label, call in (("IMPORT_PREMISE", osm._assert_registry_well_formed),
                        ("RUNTIME_PREMISE", lambda: osm.redemption_row_for_premise(row.premise))):
        try: call()
        except osm.OpeningSynthesisError as exc: print(label + "=" + exc.code)
    print("DEBT_SIDE=" + repr(osm.redeemable_debt_ids([debt], executed=executed)))
osm._assert_registry_well_formed(); print("RESTORED_AUDIT=PASS")
PY
```

输出原文：

```text
IMPORT_PREMISE=DEBT_REGISTRY_PREMISE_AMBIGUOUS
RUNTIME_PREMISE=PREMISE_GATE_AMBIGUOUS
DEBT_SIDE=('review_direction',)
RESTORED_AUDIT=PASS
```

结论：上一轮的“premise 借壳”已删除；两个方向不再重复报码。

### #4 上一轮六条通过项不退化：通过

四把行为/结构控制锁独立点跑：闭枚举、接线不靠债 id 前缀的两方向、无处理器响亮、注册表牙均绿。

命令原文：

```bash
python -m pytest -q -n 0 -p no:cacheprovider tests/test_o22m2_evidence_contract.py::test_obligation_is_a_closed_enum_not_a_free_string tests/test_b4_opening_synthesis.py::test_obligation_not_prefix_is_the_wiring_criterion tests/test_b4_opening_synthesis.py::test_unbacked_obligation_fails_loudly tests/test_b4_opening_synthesis.py::test_registry_rows_are_wiring_not_decoration
```

输出原文：

```text
....                                                                     [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
4 passed in 0.88s
```

接线 receiver 的 AST 扫描：

```bash
python - <<'PY'
import ast
from pathlib import Path
calls=[]
for path in Path('src').rglob('*.py'):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'startswith':
            calls.append((str(path), node.lineno, ast.unparse(node.func.value)))
print('STARTSWITH_CALLS_IN_SRC=', len(calls))
print('DEBT_RECEIVER_CALLS=', [(p,n,r) for p,n,r in calls if 'debt' in r.lower()])
print('OPENING_SYNTHESIS_CALLS=', [(p,n,r) for p,n,r in calls if p.endswith('opening_synthesis.py')])
PY
```

输出原文：

```text
STARTSWITH_CALLS_IN_SRC= 33
DEBT_RECEIVER_CALLS= []
OPENING_SYNTHESIS_CALLS= [('src/agent/correction/opening_synthesis.py', 420, 'other'), ('src/agent/correction/opening_synthesis.py', 420, 'key')]
```

10 个生产 mint 点的 obligation 面：

```text
src/agent/correction/evidence_adapters.py:767 obligation='elevation_chain_spans_whole_building'
src/agent/correction/evidence_adapters.py:469 obligation=None
src/agent/correction/evidence_adapters.py:501 obligation=None
src/agent/correction/evidence_adapters.py:517 obligation=None
src/agent/correction/evidence_adapters.py:528 obligation=None
src/agent/correction/evidence_adapters.py:801 obligation=None
src/agent/correction/evidence_adapters.py:817 obligation=None
src/agent/correction/evidence_adapters.py:949 obligation=None
src/agent/correction/evidence_adapters.py:967 obligation=None
src/agent/correction/evidence_adapters.py:338 obligation=None
```

源绑定按 AST 语义块核哈希：

```text
a91a1524 binds_ast_sha256=82c016266d4160d347944913a81f1d8d876a82d4ebbc3cf34bc726e9c5264a2b
a91a1524 source_guard_ast_sha256=01d07e4a1de748b6e96bf426ac3a40413f43800dd6bd5baafc4aa86acb2eaa52
df57f9a3 binds_ast_sha256=82c016266d4160d347944913a81f1d8d876a82d4ebbc3cf34bc726e9c5264a2b
df57f9a3 source_guard_ast_sha256=01d07e4a1de748b6e96bf426ac3a40413f43800dd6bd5baafc4aa86acb2eaa52
```

结论：六项均未退化：枚举仍闭；债接线 receiver 的 `startswith` 为 0；无处理器锁绿；B4 源绑定两段 AST 前后一致；枚举面仍为 1 个真实值 + 9 个 `None`；原注册表牙及本轮债侧 M4 牙都被目标测试覆盖。全 `src/` 的 `startswith` 实数仍为 33，R4 更正文案属实。

运维项也已核：

```bash
git show --stat --oneline --no-renames 544ffecb
```

输出原文：

```text
544ffecb T4-a rework1 R3: fix the vacuous 'or True' assertion (review N-4)
 .../reviews/request/2026-09-04o_T4a_rework1.md     |  97 ++++
 .../verdict/2026-09-04h_T4a_v2_crossreview_gpt.md  | 603 +++++++++++++++++++++
 tests/test_b4_opening_synthesis.py                 |   2 +-
 3 files changed, 701 insertions(+), 1 deletion(-)
```

第一笔除一行测试修正外只捎带两份预置材料，没有夹带其他项目改动，按复核单 §六不记 finding。

### #5 零恒真断言：通过

`tests/test_b4_opening_synthesis.py:1131` 已由恒真的 `assert ... or True` 改为可失败的 `assert not renamed.debt_id.startswith("debt_")`。对本轮两个 changed test files 做 AST 同型扫描，并对新增行做文本扫描，均为 0。

命令原文：

```bash
python - <<'PY'
import ast, subprocess
changed=subprocess.check_output(['git','diff','--name-only','a91a1524..df57f9a3','--','tests/*.py'], text=True).splitlines()
sus=[]
for name in changed:
    tree=ast.parse(open(name).read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert): continue
        test=node.test
        why=None
        if isinstance(test,ast.Constant) and test.value is True: why='assert True'
        elif isinstance(test,ast.UnaryOp) and isinstance(test.op,ast.Not) and isinstance(test.operand,ast.Constant) and test.operand.value is False: why='assert not False'
        elif isinstance(test,ast.BoolOp) and isinstance(test.op,ast.Or) and any(isinstance(v,ast.Constant) and bool(v.value) for v in test.values): why='or truthy literal'
        elif isinstance(test,ast.BoolOp) and isinstance(test.op,ast.And) and any(isinstance(v,ast.Constant) and not bool(v.value) for v in test.values): why='and falsy literal'
        if why: sus.append((name,node.lineno,why))
print('CHANGED_TEST_FILES=', changed)
print('VACUOUS_ASSERT_SUSPECTS=', sus)
PY
if git diff --unified=0 a91a1524..df57f9a3 -- 'tests/*.py' | rg '^\+.*assert.*(or\s+True|and\s+False|assert\s+True|not\s+False)' ; then :; else echo 'ADDED_ASSERT_TEXT_SCAN=NO_MATCH'; fi
```

输出原文：

```text
CHANGED_TEST_FILES= ['tests/test_b4_opening_synthesis.py', 'tests/test_t4a_rework1_resolution_lock.py']
VACUOUS_ASSERT_SUSPECTS= []
ADDED_ASSERT_TEXT_SCAN=NO_MATCH
```

### #6 全量绿、逐位闭合：通过

规定命令原文：

```bash
cd /tmp/t4a_rw_review_gpt && \
python -c "import src.agent.correction.evidence_contract as c, src.agent.correction.opening_synthesis as o; print(c.__file__); print(o.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

输出原文（首两行与 summary；命令 exit 0，summary 行存在）：

```text
/tmp/t4a_rw_review_gpt/src/agent/correction/evidence_contract.py
/tmp/t4a_rw_review_gpt/src/agent/correction/opening_synthesis.py
3809 passed, 2 skipped, 13 xfailed, 211 warnings in 487.95s (0:08:07)
```

新增锁实际收集数命令：

```bash
python -m pytest --collect-only -q -p no:cacheprovider tests/test_t4a_rework1_resolution_lock.py | tail -n 3
```

输出原文：

```text

F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
28 tests collected in 0.83s
```

结论：两个 import 路径均落在指定工作树；全量无失败；`3809 = 3781 + 28`，其中新增文件为 19 项参数化电池 + 9 项非参数化测试；skip/xfail 与基线逐位不变。此项通过不抵消 #1 的变异分辨力阻断。

## 三、三个重点的正面结论

### 重点 1：电池边界与族外任意串

结论是**没有被另一道防线完整兜住**。普通字符串 `owner_b4` 的正常 schema 路径报 `literal_error`；但同一字符串经施工锁自己认可的 `model_construct` 运行面进入后，旁路 compat resolver 不改注册表 carrier、不改 stored keys，故 import 域牙和两个结构钉全部看不见。resolver 返回 canonical key/row 后，backing 通过且 binding 将债退休；28 项新增锁全绿。

缺锁方向可精确表述为：

```text
resolve 的成功输入前像 ⊋ DEBT_REDEMPTION_REGISTRY.keys()
但 live-key identity、carrier type、stored-key type 全部保持不变
```

原因不是“加了就会红”，而是有限电池没有该串、identity 只遍历活键、结构钉不观察 resolver 外挂状态。建议把不可替换的 exact-membership/postcondition 放在 resolver 外层或各消费者处，始终对**原始 obligation**复核；可扩 resolver 只位于其内层。仅继续补几个别名样例仍是有限名单，不会形成语义闭包。

### 重点 2：两道 `type() is ...` 结构钉的两面

绕过面结论：不存在一个 Python 对象既满足 `type(x) is dict` 又覆写 builtin `dict` 查找；但这不等于整个解析面被封住。实测的外部 compat table + patched resolver 保持 carrier 为 `dict`、stored keys 全为 `str`，仍接受并退休 alias；查询侧的 equality-smuggling `str` 子类也不触 stored-key 钉。

合法出口实测命令原文：

```bash
python - <<'PY'
from types import MappingProxyType
from unittest.mock import patch
import src.agent.correction.opening_synthesis as osm
canonical = next(iter(osm.DEBT_REDEMPTION_REGISTRY))
real = osm.redemption_row_for_obligation
readonly = MappingProxyType(dict(osm.DEBT_REDEMPTION_REGISTRY))
print("READONLY_EXACT=" + str(readonly[canonical] is osm.DEBT_REDEMPTION_REGISTRY[canonical]))
with patch.object(osm, "DEBT_REDEMPTION_REGISTRY", new=readonly):
    for label, call in (("AUDIT", osm._assert_registry_well_formed), ("SEAM", lambda: real(canonical))):
        try: call()
        except osm.OpeningSynthesisError as exc: print(label + "=" + exc.code)
        else: print(label + "=PASS")
osm._assert_registry_well_formed()
print("RESTORED=GREEN")
PY
```

输出原文：

```text
READONLY_EXACT=True
AUDIT=DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT
SEAM=DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT
RESTORED=GREEN
```

`MappingProxyType` 不提供 alias/normalization/multi-candidate 行为，且 exact lookup 返回同一 row，仍被拒。因此 `type(carrier) is dict` 是“用固定实现消灭一个攻击载体”，不是对“精确单值解析”语义本身的刻画；它把合法只读实现写死了。

查询侧 `str` 子类边界的独立命令：

```bash
python - <<'PY'
import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import EvidenceDebtV1
canonical = next(iter(osm.DEBT_REDEMPTION_REGISTRY))
class AliasStr(str):
    def __new__(cls, visible, target):
        obj = super().__new__(cls, visible); obj.target = target; return obj
    def __hash__(self): return hash(self.target)
    def __eq__(self, other): return other == self.target
    def __ne__(self, other): return not self == other
alias = AliasStr("owner_b4", canonical)
payload = dict(debt_id="review_str_subclass", kind="other_known_missing", channel=None,
               affected_refs=(), description="str subclass", obligation=alias)
debt = EvidenceDebtV1.model_validate(payload)
print("INPUT=" + repr(alias))
print("INPUT_TYPE=" + type(alias).__name__)
print("INPUT_IS_STR=" + str(isinstance(alias, str)))
print("VALIDATED=" + repr(debt.obligation))
print("VALIDATED_TYPE=" + type(debt.obligation).__name__)
print("SEAM=" + repr(osm.redemption_row_for_obligation(debt.obligation)[0]))
PY
```

输出原文：

```text
INPUT='owner_b4'
INPUT_TYPE=AliasStr
INPUT_IS_STR=True
VALIDATED='elevation_chain_spans_whole_building'
VALIDATED_TYPE=str
SEAM='elevation_chain_spans_whole_building'
```

这不会让 post-validation 债多行解析，故列为不阻断；但它证明 `type(key) is str` 只钉 stored key，不足以支持“strict schema 拒绝所有未定义 Python 输入”的广义表述。

### 重点 3：独立重造 M3 / M5 / M6 与恢复

三项均用 `mock.patch.object` 上下文安装，未复用施工方的直接全局赋值/手写 `finally`；上下文退出后分别重跑锁函数及 registry audit。M3 用候选列表后 `min` 静默选行；M5 用覆写 `__contains__`/`__getitem__` 且只在旁表存 redirect 的 carrier；M6 只改 exact hit 的返回 row。

命令原文：

```bash
python - <<'PY'
import importlib.util
from unittest.mock import patch
import src.agent.correction.opening_synthesis as osm
spec = importlib.util.spec_from_file_location("review_lock", "tests/test_t4a_rework1_resolution_lock.py")
lock = importlib.util.module_from_spec(spec); spec.loader.exec_module(lock)
canonical = next(iter(osm.DEBT_REDEMPTION_REGISTRY))
real = osm.redemption_row_for_obligation

def candidates_then_pick(name):
    try: return real(name)
    except osm.OpeningSynthesisError as exc:
        if exc.code != "OBLIGATION_UNBACKED": raise
        hits = [(k, r) for k, r in osm.DEBT_REDEMPTION_REGISTRY.items()
                if k.startswith(name) or name.startswith(k)]
        if not hits: raise
        return min(hits, key=lambda pair: (len(pair[0]), pair[0]))

probe = "elevation_chain_spans"
with patch.object(osm, "redemption_row_for_obligation", new=candidates_then_pick):
    try: lock.test_near_miss_obligations_are_refused_on_every_entry("review_m3", probe)
    except BaseException as exc: print("M3_LOCK=RED:" + type(exc).__name__)
    else: print("M3_LOCK=GREEN_UNEXPECTED")
lock.test_near_miss_obligations_are_refused_on_every_entry("review_m3", probe)
print("M3_RESTORED=GREEN")

class CompatibilityCarrier(dict):
    def __init__(self, source, redirects): super().__init__(source); self.redirects = redirects
    def __contains__(self, key): return super().__contains__(self.redirects.get(key, key))
    def __getitem__(self, key): return super().__getitem__(self.redirects.get(key, key))
carrier = CompatibilityCarrier(osm.DEBT_REDEMPTION_REGISTRY, {"owner_b4": canonical})
print("M5_RAW_ALIAS=" + str("owner_b4" in carrier and carrier["owner_b4"] is carrier[canonical]))
with patch.object(osm, "DEBT_REDEMPTION_REGISTRY", new=carrier):
    try: lock.test_every_live_key_resolves_to_exactly_its_own_row()
    except BaseException as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print("M5_LOCK=RED:" + code)
    else: print("M5_LOCK=GREEN_UNEXPECTED")
lock.test_every_live_key_resolves_to_exactly_its_own_row()
osm._assert_registry_well_formed()
print("M5_RESTORED=GREEN")

other = osm.DebtRedemption("review_redirect", osm.span_equality_gate)
def exact_redirect(name):
    key, _ = real(name); return key, other
with patch.object(osm, "redemption_row_for_obligation", new=exact_redirect):
    try: lock.test_every_live_key_resolves_to_exactly_its_own_row()
    except BaseException as exc: print("M6_LOCK=RED:" + type(exc).__name__)
    else: print("M6_LOCK=GREEN_UNEXPECTED")
lock.test_every_live_key_resolves_to_exactly_its_own_row()
osm._assert_registry_well_formed()
print("M6_RESTORED=GREEN")
PY
```

输出原文：

```text
M3_LOCK=RED:Failed
M3_RESTORED=GREEN
M5_RAW_ALIAS=True
M5_LOCK=RED:DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT
M5_RESTORED=GREEN
M6_LOCK=RED:AssertionError
M6_RESTORED=GREEN
```

正面判定：

- M3 的规则生成电池有分辨力；安装候选 resolver 后锁红，恢复后绿。
- M5 的 carrier tooth 能挡 compat `dict` 子类，恢复后绿；但同一 tooth 对安全 `MappingProxyType` 也红，构成 N-1 的合法出口问题。
- M6 的精确键重定向不扩大可解析输入集，因此电池不红而 identity 钉红，这是诚实边界，不是单独缺口；恢复后 identity 钉回绿。
- 上述三项成立仍不能覆盖 B-1：族外 compat resolver 不改 carrier/live keys，且 identity 保持，28 项锁实测全绿。

## 四、未复现项清单

1. **未复现施工方“族外 alias 的 schema-bypass 债过不了销账 binding、最多保持 open”的自报**：实测 `REDEEMED=('review_arbitrary_alias',)`，结果相反，已列阻断 B-1。
2. **未复现恢复污染**：独立 M3/M5/M6 均在补丁上下文退出后回绿，registry audit 也回绿。
3. **未复现当前生产默认路径的别名/归一化/前缀回退**：生产 seam 仍是 exact membership + exact index；缺陷在回归锁的未来扩法分辨力。
4. **未复现全量失败或计数漂移**：规定全量为 `3809 passed, 2 skipped, 13 xfailed`，新增文件实际收集 28 项。
5. 本轮按复核单要求独立重造 M3/M5/M6；M1 与 M4 没有另写独立安装器，只执行了施工方随新增文件交付的对应测试并在目标/全量中见绿。
6. 没有在本 detached 工作树切换到 `a91a1524` 重跑基线；`3781` 采用派工单固定基线及上一轮本席独立结果，本轮只核 `df57f9a3` 与新增 28 项的闭合。

## 五、是否改过项目代码

**没有。** 复核期间未修改 `src/`、`tests/`、既有日志或任何项目代码；只新增本裁决文件 `AI_agent/logs/reviews/verdict/2026-09-04v_T4a_rework1_crossreview_gpt.md`。开工时已 staged 的复核单保持原状，未执行 `git add`/commit。
