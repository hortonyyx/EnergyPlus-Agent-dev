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
