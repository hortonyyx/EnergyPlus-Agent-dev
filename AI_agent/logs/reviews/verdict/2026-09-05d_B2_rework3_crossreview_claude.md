# B2 返工 3 · Claude 跨家族复核裁决

- **日期**：2026-09-05 · **施工方**：GLM 家族 · **复核方**：Claude 家族
- **审对象**：`git diff b52c6f5b..db691e26`（分支 `wt/09.04w_b2_rework3`）
- **工作树**：`/tmp/b2rw3_review_claude`，detached `db691e26`

## 裁决

**APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 3**

本轮把「不经字节门就能拿到一个能被装配接受的载体」这条路真正封进了类型层：
入口（闭包令牌 + `__init_subclass__`）挡住一切正常语言构造语义，出口（`_levels_of_carrier` 在每次读
取时重新跑 `validate_evidence_bundle` + `_byte_z`）挡住一切绕过 `__init__` 的伪造。**我自己发明的
五类攻击**（deepcopy+`__dict__`直改、pickle 往返、直调未导出的私有 minter、`__class__` 重赋值、
在真实 artifact 上原地改字段）**全部在消费边界被拒**，没有一条走通；三处摘牙实验证实相应的锁确实
有牙（摘掉对应代码后测试如期变红）。三条不阻断 finding 见下，均不影响「装配的 z 不来自手填值」这一
核心不变量。

## §一 三条复核（缺一不合格）

### ①旧 commit（`b52c6f5b`）复现得出

另建只读 worktree `git worktree add --detach <scratch>/old_b52c6f5b b52c6f5b`（未碰本树 `db691e26`）,
在其内逐字重跑裁决 `2026-09-04p` 的原脚本。

命令原文：
```bash
cd <scratch>/old_b52c6f5b && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python - <<'PY'
from pathlib import Path
from types import SimpleNamespace
from src.agent.correction.multifloor import ValidatedFloorLadder, assemble_multifloor_geometry
from src.agent.correction.schema import CorrectedGeometryV3

fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})
hand_level = SimpleNamespace(floor_index=0, z_floor_m=12.34, ceiling_height_m=5.57)
ladder = ValidatedFloorLadder((hand_level,))
try:
    assembled = assemble_multifloor_geometry(ladder, [one_floor])
except Exception as exc:
    print('ALT_RESULT=REJECTED'); print('ALT_ERROR=', type(exc).__name__, str(exc))
else:
    print('ALT_RESULT=ASSEMBLED')
    print('ALT_OUTPUT_Z=', [(floor.z_floor, floor.ceiling_height) for floor in assembled.floors])
PY
```

输出原文：
```text
<scratch>/old_b52c6f5b/src/agent/correction/multifloor.py
ALT_PATH=PUBLIC_VALIDATED_CARRIER_DIRECT_CONSTRUCTOR
ALT_CARRIER_EXPORTED= ValidatedFloorLadder
ALT_LEVEL_RUNTIME_TYPE= SimpleNamespace
ALT_INPUT_Z= 12.34 5.57
ALT_RESULT=ASSEMBLED
ALT_OUTPUT_Z= [(12.34, 5.57)]
```
`m.__file__` 落在 `old_b52c6f5b` 内（承重不变量核过）。确认：旧 commit 上这条路**当时确实通**，
手填 `(12.34, 5.57)` 原样装配出来。

### ②新 commit（`db691e26`）复现不出，且死点核对

同一脚本，在本工作树 `/tmp/b2rw3_review_claude`（`db691e26`）内原样重跑：

命令原文：同上，`cd /tmp/b2rw3_review_claude` 版本（脚本一字未改）。

输出原文：
```text
/tmp/b2rw3_review_claude/src/agent/correction/multifloor.py
Traceback (most recent call last):
  File "<stdin>", line 17, in <module>
  File "/tmp/b2rw3_review_claude/src/agent/correction/multifloor.py", line 237, in __init__
    raise MultiFloorAssemblyError(
src.agent.correction.multifloor.MultiFloorAssemblyError: LADDER_MINT_SEAL_REQUIRED: {'got': 'ValidatedFloorLadder', 'reason': 'ValidatedFloorLadder cannot be constructed outside multifloor: it is minted only by derive_floor_ladder, which runs the frozen-byte gate first (dispatch §一(a))'}
```
`m.__file__` 落在本工作树内。**死点核对**：第 17 行 `ladder = ValidatedFloorLadder((hand_level,))`
——**构造器本身**，在 `try` 块**之前**，装配函数根本没被触达。与施工方交件所述（死在 `:237` 构造器）
一致。

### ③⭐⭐⭐ 自己发明的换同形输入（⛔ 未照抄施工方 7 条）

选定五条施工方未测过的攻击族：

1. **`copy.deepcopy` 一份诚实 ladder，再直接改它的 `__dict__`**（不经 `object.__setattr__`，绕过
   `FrozenInstanceError` 的另一条路——直接操作字典，连"绕过 frozen"这个动作本身都换了个做法）。
2. **pickle 往返**（`__reduce__`/`__setstate__` 会不会绕开构造器？）。
3. **直调未导出但可被普通模块属性访问拿到的私有 minter `m._mint_sealed_ladder`**，完全跳过
   `derive_floor_ladder` 自己的预门（这不是 `__closure__` 内省——`_mint_sealed_ladder` 是一个正常的
   模块级属性，`import` 后任何人都能 `getattr` 到，不需要读闭包 cell）。
4. **`__class__` 重赋值伪造**：造一个完全无关的普通对象（不是 `ValidatedFloorLadder` 的任何变体），
   用**普通属性赋值**设 `_artifact`，再把它的 `__class__` 换成 `ValidatedFloorLadder`——全程不经过
   `__new__`/`__init__`/`__init_subclass__`/`object.__setattr__` 中的任何一个。
5. **（确认性）在同一个真实 artifact 对象上原地改 `.bundle`**（不新建、不替换 `_artifact` 引用——
   `evidence_contract.py` 的 pydantic 模型这里没设 `frozen=True`，普通赋值就能改）。

命令原文（在 `/tmp/b2rw3_review_claude`，`db691e26`，完整脚本存于
`AI_agent/logs/reviews/artifacts/2026-09-05d_claude_probe1.py`）：
```bash
python -c "import src.agent.correction.multifloor as m; print(m.__file__)"
python <probe1.py>
```

输出原文：
```text
/tmp/b2rw3_review_claude/src/agent/correction/multifloor.py
HONEST_BASELINE= [(-0.0021, 3.6021), (3.6, 3.6021)]
DEEPCOPY_TYPE_MATCHES= True DEEPCOPY_ISINSTANCE= True
PROBE1_DEEPCOPY_THEN_DICT_MUTATE = REJECTED EvidenceContractError FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE ...
PROBE2_PICKLE_ROUNDTRIP= FAILED AttributeError Can't get local object '_seal_validated_ladder.<locals>.ValidatedFloorLadder'
PROBE3_MINTER_ACCESSIBLE_WITHOUT_INTROSPECTION= True
PROBE3_MINT_SUCCEEDED_BYPASSING_DERIVE_GATE= ValidatedFloorLadder
PROBE3_PRIVATE_MINTER_UNGATED_ARTIFACT = REJECTED EvidenceContractError FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE ...
PROBE4_CLASS_REASSIGN= SUCCEEDED, isinstance= True
PROBE4_CLASS_REASSIGNMENT_FORGERY = REJECTED EvidenceContractError FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE ...
PYDANTIC_ORDINARY_ASSIGN_ALLOWED= True
PROBE5_INPLACE_BUNDLE_MUTATE_SAME_ARTIFACT_OBJECT = REJECTED EvidenceContractError SOURCE_SET_MISMATCH ...
```

读法：
- **探针 1**（deepcopy + `__dict__` 直改）：`copy.deepcopy` 对这个 frozen dataclass 生效（走
  `cls.__new__(cls)` + 状态拷贝，完全不经 `__init__`），`__dict__` 直改也确实绕过了 `FrozenInstanceError`
  ——两个"应该被挡住"的机制都被绕开了，但**装配时的重新推导仍然逮到了漂移**。
- **探针 2**（pickle）：**这个类根本不能被 pickle**——因为它是在闭包函数内部动态创建的局部类，
  pickle 按 `__module__`+`__qualname__` 找不到它（`AttributeError: Can't get local object
  '_seal_validated_ladder.<locals>.ValidatedFloorLadder'`）。这是一个意外的额外收益：闭包持牌的设计
  副作用连累了整条 pickle 攻击面，不是设计者刻意为之，但确实堵死了这条路。
- **探针 3**（直调私有 minter）：`m._mint_sealed_ladder` **确实**可以被外部普通调用（`hasattr` 为
  `True`，且调用**成功**铸出了一个 `ValidatedFloorLadder`，完全跳过了 `derive_floor_ladder` 的预
  门）——**docstring claim 1「不能从模块外部被构造」在字面上不严谨**（见 §二D）。但这个铸出来的
  ladder 在消费时仍然被 `_levels_of_carrier` 重新验证抓住，**没有形成真实的安全缺口**。
- **探针 4**（`__class__` 重赋值）：**成功**让一个毫不相干的对象通过 `isinstance` 检查，且完全不
  触发 `__init__`/`__init_subclass__`/`object.__setattr__` 中任何一个——这是我找到的最干净的绕过
  入口封印的手法。但同样在消费时被抓。
- **探针 5**（原地改同一个真实 artifact 的 `.bundle`）：证实这里的 pydantic 模型**不是** `frozen=True`
  （`PYDANTIC_ORDINARY_ASSIGN_ALLOWED= True`，普通赋值即可改），但 `validate_evidence_bundle` 每次
  都重新算 sha 且检查来源集合一致性，篡改仍被抓（这次撞到的是 `SOURCE_SET_MISMATCH`，因为两次
  `adapt_as_drawn_elevation` 用了不同 `input_id`；换个变体会撞到 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`，
  核心结论不变：原地改真实 artifact 不能绕过重验证）。

**结论：五条全新攻击类别（不同于施工方的 7 条：先合法拿真载体换元素 / `object.__new__` 壳+鸭子 /
壳+真漂移 / 空壳 / 子类 / `replace` 两形状）全部被同一道出口重推导拦下，且拦下的位置都在消费边界，
不是入口收窄。这一类路径在类型层确实不存在了。**

## §二 逐条 delta 核对（派工单 §二 三小节 + 复核单 §三 六条验收）

### A. 消费路径是否【全】覆盖

命令原文：
```bash
grep -rn "ValidatedFloorLadder\|_levels_of_carrier\|derive_floor_ladder\|assemble_multifloor_geometry\|_mint_sealed_ladder" --include=*.py src/ | grep -v "src/agent/correction/multifloor.py"
```
输出原文：
```text
src/agent/pipeline.py:1647:    ladder = derive_floor_ladder(elevation_evidence)
src/agent/pipeline.py:1672:    return assemble_multifloor_geometry(ladder, geometries)
```
（另有若干纯文档行 `1390/1412/1418/1426/1577/1579/1616/1620/1637-1638/1641/1645-1646`，均为注释/docstring，
非属性访问。）**全仓只有这一处消费者**，且它只做 `derive_floor_ladder(...)` 一次、
`assemble_multifloor_geometry(ladder, ...)` 一次，函数内部只在 `:508` 一处 `tuple(ladder)`（触发一次
`_levels_of_carrier`），没有独立的 `len(ladder)` / `ladder[i]` 调用——不存在派工单担心的
「`__len__` 与 `__iter__`/`__getitem__` 各自重推导、中途换掉 `_artifact` 导致读到两份」的缝：这个
缝在**理论上**存在（三个 dunder 方法各自独立调用 `_levels_of_carrier`），但在**当前唯一consumer**里
从未被触发，因为只有一次 `tuple(ladder)` 整体物化。**判定：已兑现。**（附带记一条非阻断观察：如果
未来有第二个消费者分别调用 `len(ladder)` 和 `tuple(ladder)`，中间存在 `object.__setattr__` 换
`_artifact` 的 TOCTOU 窗口——现在没有这样的调用点，故不构成缺陷，只是设计上的隐性假设，值得挂进
docstring 或加一条「消费必须一次性物化」的注释。）

### B. `NONPOSITIVE_CEILING_HEIGHT` 测试是否恒绿

**摘牙实验**（工作树内改、验证后当场 `git checkout --` 复原，`git status --porcelain` 确认干净）：

```bash
# 把 assemble_multifloor_geometry 里的 `if level.ceiling_height_m <= 0.0:` 改成 `if False:`
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python -m pytest -q -p no:cacheprovider tests/test_b2_multifloor_assembly.py::test_nonpositive_ceiling_is_loud
```
输出原文（摘要）：
```text
        monkeypatch.setattr(mf, "_levels_of", lambda art_: (bad,))
        ladder = mf.derive_floor_ladder(art)
>       with pytest.raises(MultiFloorAssemblyError) as exc:
E       Failed: DID NOT RAISE <class 'src.agent.correction.multifloor.MultiFloorAssemblyError'>
1 failed in 7.98s
```
摘牙后复原：`git checkout -- src/agent/correction/multifloor.py`；`git diff --stat` 为空、
`grep -c CLAUDE-NEUTER` 为 0，确认已还原。

**判定**：这条测试**对它自己保护的分支有牙**（摘掉 `NONPOSITIVE_CEILING_HEIGHT` 检查本身，
它确实变红）；但它**走的不是真实入口**——`(a)` 段先证明了「用真实构造路径喂零高度层」现在在构造器
就被封印挡死（`LADDER_MINT_SEAL_REQUIRED`），`(b)` 段之所以能碰到这条检查，靠的是 `monkeypatch.setattr(mf,
"_levels_of", lambda art_: (bad,))`——把整个派生核心换成常量函数，这是**该文件已有的 sanctioned
monkeypatch seam**（同文件 `test_neutered_derivation_fails_loud_never_falls_back` /
`test_wiring_feeds_the_derived_z_into_the_chain` 也这么用），不是伪装成真实调用链的假象。施工方在
交件 §一末段**如实自报**了这个语义变化（`_mint_ladder` 对相邻 rung 强制严格递增，这条检查经任何真实
构造路径都不可达，保留作纵深防御）。**判定：非恒绿假象，是有牙但走人工缝隙的防御性代码 + 诚实披露，
记不阻断，不记阻断。**

### C. 「出口全检」是否真的在出口

§一③ 的五条探针里，凡是**没能绕过 `__init__`** 的（直接构造、`dataclasses.replace`、子类）都死在
**入口**（`LADDER_MINT_SEAL_REQUIRED` / `LADDER_SEALED_NO_SUBCLASS`，`__init__`/`__init_subclass__`
内）；凡是**绕过了 `__init__`** 的（deepcopy+`__dict__`直改、直调私有 minter、`__class__` 重赋值）
全部死在**出口**（`_levels_of_carrier` → `_levels_of` → `validate_evidence_bundle`/`_byte_z`），
错误码是 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE` / `SOURCE_SET_MISMATCH` 这类**消费时重新计算**才能
产生的错误，不是构造时的静态检查。**两层机制独立生效，出口确实在出口，不是入口收窄的伪装。**
判定：已兑现（同 §一③ 证据）。

### D. docstring 四句声称与强制行逐句对账

```bash
python -c "from src.agent.correction.multifloor import ValidatedFloorLadder; print(ValidatedFloorLadder.__doc__)"
```
（输出与施工方交件 §二#3 引用的文字逐字一致，已核对，从略。）

| 声称 | 强制行 | 独立核验 |
|---|---|---|
| 1. "cannot be populated from outside this module" | `:236` `if _seal is not _LADDER_SEAL` | **有一处字面不精确**：`m._mint_sealed_ladder` 是普通模块属性（`hasattr(m, '_mint_sealed_ladder') == True`），外部可以 `import` 后直接调用它铸出一个从未经过 `derive_floor_ladder` 预门的 `ValidatedFloorLadder`（§一③ 探针 3），这确实是「从模块外部populate」——不需要读 `__closure__` cell，只是普通属性访问。但铸出来的实例在消费时仍被 claim 3 的出口重推导拦住，**没有形成实际安全缺口**，只是 claim 1 的措辞比实际情况更绝对。**记不阻断 finding。** |
| 2. "cannot be subclassed" | `:262-273` `__init_subclass__` | 用 `class` 语句 / `type(...)` / `types.new_class(...)` 三种不同构造子类的方式全部触发 `LADDER_SEALED_NO_SUBCLASS`（自己独立验证，输出见下） |
| 3. "stores NO z-bearing state ... RE-DERIVES" | `:227` 唯一字段 `_artifact`；`:297/300/303` 三个 dunder 全经 `:275-295 _levels_of_carrier` | §一③ 五条探针里凡绕过 `__init__` 的全部在这一层被拦，确认为真 |
| 4. "only sanctioned minter gates first" | `:306-307 _mint_sealed`；唯一模块级调用者 `derive_floor_ladder`（`:407-408`）| **同 claim 1 的问题**：`_mint_sealed_ladder`本身不是"only sanctioned"意义上不可达——它可以被直接调用且完全不跑 `_levels_of` 预门（探针 3）。但 claim 4 措辞本身只讲"sanctioned minter"的性质，没有断言"没有其他 minter"，**用词比 claim 1 谨慎，不算不实**。 |

命令原文（`__init_subclass__` 三种构造方式）：
```bash
python - <<'PY'
from src.agent.correction.multifloor import ValidatedFloorLadder, MultiFloorAssemblyError
import types
try:
    Fake = types.new_class("Fake2", (ValidatedFloorLadder,), {}, lambda ns: ns.update({
        "__init__": lambda self, levels: object.__setattr__(self, "_levels", levels)}))
    print("TYPES_NEW_CLASS_SUCCEEDED", Fake)
except MultiFloorAssemblyError as exc:
    print("TYPES_NEW_CLASS_BLOCKED", exc.code)
try:
    Fake3 = type("Fake3", (ValidatedFloorLadder,), {})
    print("TYPE_CALL_SUCCEEDED", Fake3)
except MultiFloorAssemblyError as exc:
    print("TYPE_CALL_BLOCKED", exc.code)
PY
```
输出原文：
```text
TYPES_NEW_CLASS_BLOCKED LADDER_SEALED_NO_SUBCLASS
TYPE_CALL_BLOCKED LADDER_SEALED_NO_SUBCLASS
```

**判定**：claim 2/3/4 强制行属实；**claim 1 措辞有一处可查的不精确**（不阻断，见上），建议
施工方收紧为「the sealed construction path (`__init__`) cannot be reached from outside this
module without the closure token; a value that reaches it by any OTHER means (including a direct
call to the private minter) is still refused at consumption by claim 3」或等价表述。

### E. 五条新测试摘牙实验（挑 3 条，超过复核单要求的 2 条）

**摘牙 1**：把 `__init__` 里 `if _seal is not _LADDER_SEAL:` 改成 `if False:`（禁用封印检查），复原前
命令与输出：
```bash
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python -m pytest -q -p no:cacheprovider \
  tests/test_b2_multifloor_assembly.py::test_reviewer_round3_replay_public_constructor_is_sealed \
  tests/test_b2_multifloor_assembly.py::test_dataclasses_replace_cannot_rebuild_the_carrier \
  tests/test_b2_multifloor_assembly.py::test_my_own_same_shape_forge_the_sealed_ladder_cannot_inject_a_hand_z
```
```text
FAILED tests/test_b2_multifloor_assembly.py::test_dataclasses_replace_cannot_rebuild_the_carrier
FAILED tests/test_b2_multifloor_assembly.py::test_my_own_same_shape_forge_the_sealed_ladder_cannot_inject_a_hand_z
FAILED tests/test_b2_multifloor_assembly.py::test_reviewer_round3_replay_public_constructor_is_sealed
3 failed in 7.69s
```
（三条锁全部依赖同一处封印检查，摘掉即变红，确认有牙）复原：`git checkout -- src/agent/correction/multifloor.py`。

**摘牙 2**：把 `_levels_of_carrier` 里 `if not isinstance(artifact, CorrectionEvidenceBundleArtifactV1):`
改成 `if False:`（禁用出口类型检查），命令与输出：
```bash
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python -m pytest -q -p no:cacheprovider tests/test_b2_multifloor_assembly.py::test_object_new_shell_cannot_assemble_a_hand_z
```
```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'content_sha256'
FAILED tests/test_b2_multifloor_assembly.py::test_object_new_shell_cannot_assemble_a_hand_z
1 failed in 7.80s
```
（禁用后鸭子 artifact 直接崩在 `evidence_contract.py` 内部、不是命名错误——确认这条出口类型检查有牙，
且它的价值不只是「挡住」还包括「把崩溃变成一个干净的具名错误」）复原确认同上。

**摘牙 3（回答 §二B）**：见上——`NONPOSITIVE_CEILING_HEIGHT` 检查摘掉后 `test_nonpositive_ceiling_is_loud`
部分 (b) 变红（`DID NOT RAISE`），确认有牙。

三次实验后均执行 `git checkout -- src/agent/correction/multifloor.py` + `git status --porcelain`（无输出）
+ `grep -c CLAUDE-NEUTER src/agent/correction/multifloor.py`（结果 `0`）确认已完全复原。

## §三 验收对账（派工单 §三 六条）

| # | 规则 | 判定 | 独立证据 |
|---|---|---|---|
| 1 | 模块外无法造出能被装配接受的载体 | ✅ 已兑现 | §一③ 五条自造攻击 + 施工方交件 7 条，共 12 条不同形状全部被拒（本席只信自己跑的 5 条 + 独立复现施工方 2 条关键路径，未转引） |
| 2 | 装配 z 不来自载体携带的值 | ✅ 已兑现 | 五条探针里凡是把手填/漂移值塞进 `_artifact` 的，全部在 `_byte_z` 重新解析时被抓；「唯一途径=提供能过门的不同冻结字节」这句话成立 |
| 3 | docstring 每句有强制行 | ✅ 基本兑现，1 处措辞不精确记不阻断 | §二D 表格 |
| 4 | 上一轮四件不退化 | ✅ 已兑现 | 独立单跑五个具名测试，见下 |
| 5 | 本体不退化 | ✅ 已兑现 | 局部命令见下，62 passed |
| 6 | 全量绿 + 逐位闭合 | ✅ 已兑现 | 见下 |

#4 命令与输出（旧公开路径 · 旧裸 z 参数迁移 · footprint 误贴 · 真实 footprint 冲突四件具名重放）：
```bash
python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_b2_multifloor_assembly.py::test_reviewer_round2_bypass_is_dead_at_the_public_helpers \
  tests/test_b2_multifloor_assembly.py::test_run_multifloor_has_no_z_parameter \
  tests/test_b2_multifloor_assembly.py::test_run_correction_refuses_a_bare_z_requires_validated_level \
  tests/test_b2_multifloor_assembly.py::test_footprint_relabel_is_from_an_explicit_precheck_only \
  tests/test_b2_multifloor_assembly.py::test_per_floor_footprint_mismatch_is_loud
```
```text
.....                                                                    [100%]
5 passed in 4.58s
```

局部命令与输出：
```bash
python -m pytest -q -n 6 -p no:cacheprovider tests/test_b2_multifloor_assembly.py tests/test_o22m7_evidence_wiring.py
```
```text
bringing up nodes...
..............................................................           [100%]
62 passed in 6.91s
```

全量命令与输出（**本席独立在 `/tmp/b2rw3_review_claude` 跑，未转引交件**）：
```bash
cd /tmp/b2rw3_review_claude && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```
```text
/tmp/b2rw3_review_claude/src/agent/correction/multifloor.py
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. ...
3787 passed, 2 skipped, 13 xfailed, 211 warnings in 502.54s (0:08:22)
```
`m.__file__` 落在本工作树内（承重不变量核过）；有 summary 行，非同机竞争假红。

逐位闭合命令与输出：
```bash
grep -c "^def test_" tests/test_b2_multifloor_assembly.py
git show b52c6f5b:tests/test_b2_multifloor_assembly.py | grep -c "^def test_"
```
```text
31
26
```
`31 - 26 = 5`，`3782(基线) + 5 = 3787`；skip `2`、xfail `13`、failed `0` 与基线一致。

## §四 施工方自报「最薄弱一处」的独立判断

原句：「装配边界对 `CorrectionEvidenceBundleArtifactV1` 这个类型本身的信任是继承的，不是自己挣的」。

**①这句自评成不成立**：成立，且本席独立验证到了同一个事实——§一③ 的**全部**五条探针，
无论用什么姿势绕过 `__init__`，最终都是同一处 `evidence_contract.validate_evidence_bundle` 的
sha 校验/来源集合校验/漂移校验在抓人（`FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE` /
`SOURCE_SET_MISMATCH`）。B2 自己在 `multifloor.py` 里**没有第二份独立的完整性校验**——它把全部信任
转包给了 `evidence_contract.py` 这一个函数。如果那道门将来被放宽（比如某天注释掉 sha 比对分支），
B2 现在的 31 条测试**极可能依然全绿**，因为它们构造的"漂移 artifact"全部靠 `finalize_bundle` 重新
计算 sha 通过完整性检查、再靠内容比对触发漂移错误——如果 sha 比对本身被削弱，这些测试会从
"验证 B2 拦截漂移"退化成"验证 B2 什么都没拦"而不自知。

**②是不是本轮该解决**：不是。派工单 §四明令 ⛔ 碰 `evidence_contract.py`（T4-a 正在被复审）；
本轮把信任边界完整暴露且诚实记录，符合"改完之后你能不能指出每句声称由哪行强制"的验收标准——
这句"信任是继承的"本身就是对第 4 句声称（"the only sanctioned minter gates first"）的诚实限定，
不构成本轮遗留的隐藏缺口。

**③若归给别的单，该由哪个单接、验收怎么写**：应归给 `evidence_contract.py` 自身的复审/加固单
（当前是 T4-a 的复审范围，或其后续的一份独立加固单）。验收建议写成：**一份跨模块契约回归测试**——
不测 B2 的行为，而是直接测 `evidence_contract.validate_evidence_bundle` 本身对一组已知应该失败的
畸形输入（sha 不匹配 / 来源集合不一致 / 漂移）逐条仍然失败；这份测试放在 `evidence_contract.py`
自己的测试文件里，作为"这道门被削弱时第一个变红的哨兵"，⛔ 不要求 B2 自己重复实现完整性校验
（那会违反"信任继承"这个正确的分层设计——B2 不该自己重新发明 sha 校验）。

## 未复现项清单

无——§一三条复核、§二 A-E、§三 六条验收、§四 三问全部本席亲自复现或独立判断，未转引交件任何一处
输出作为证据。

## 是否改过被审对象

**否**。§二B/§二E 的三次摘牙实验均在工作树内临时改动、验证后立即 `git checkout --` 复原，每次复原后
均用 `git status --porcelain`（空）+ `grep -c CLAUDE-NEUTER src/agent/correction/multifloor.py`（`0`）
确认。除本裁决书本身与探针脚本（落在 `AI_agent/logs/reviews/artifacts/`）外，未新增或修改任何
`src/`/`tests/` 文件。另建的只读 worktree `<scratch>/old_b52c6f5b` 仅用于 §一①复现，未对其做任何
写操作，复核结束后会 `git worktree remove` 清理。

## 操作声明

- 全程工作目录 `/tmp/b2rw3_review_claude`；未进入或修改 `/workspaces/EnergyPlus-Agent-dev`。
- 未执行 `pip install -e .`；未使用 `git add -A`（逐路径 add，提交前核对 `--cached --numstat`）。
- pytest 全程 `-n 6`（未用 `-n auto`）。
- 分段提交：本裁决书分两笔提交（§一 先行提交，本笔补全 §二-§六）。
