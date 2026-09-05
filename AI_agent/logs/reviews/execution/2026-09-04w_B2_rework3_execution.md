# B2 返工 3 · 施工交件（GLM 家族施工席）

- **日期**：2026-09-04 · **施工方**：GLM 家族施工席 · **分支**：`wt/09.04w_b2_rework3`（基点 `b52c6f5b`）
- **派工单**：[`2026-09-04w`](../request/2026-09-04w_B2_rework3.md) · **上一轮裁决**：[`2026-09-04p`](../verdict/2026-09-04p_B2_rework2_crossreview_gpt.md)（REWORK / 阻断 1）
- **本轮提交**（分段）：
  - `bc864c41` 预置派工单 + 上轮裁决文档（主控预置，本席代为落库）
  - `173ed7ef` 核心：闭包封印 + 无 z 状态载体 + 消费端重推导（含两条旧测试按新语义改写）
  - `e4ccbd73` §二 自攻击回归测试 5 条 + 构造器参数名对齐（replace 命中具名封印）
  - （最后一笔）本交件

---

## 〇、开工自检（命令原文与输出原文）

```bash
cd /tmp/b2_rework3_glm && pwd && git log --oneline -1 && git status --porcelain
head -40 AI_agent/CLAUDE.md
```

```text
/tmp/b2_rework3_glm
b52c6f5b B2 rework 2 · execution doc — type-layer no-hand-fill; full suite 3782/0 (3777+5)
A  AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md
A  AI_agent/logs/reviews/verdict/2026-09-04p_B2_rework2_crossreview_gpt.md
```

（`AI_agent/CLAUDE.md` 头 40 行已读：科研项目口径 / agent 术语 banner / 管线术语 banner。）

**孤儿草稿处理声明**：§〇④ 的草稿目录不在本工作树，只在主树（只读借阅了
`README.md` 与 `multifloor_wip.py` 前段，未复制任何代码段）。它的 `_LADDER_SEAL`
是**模块级全局**——下划线全局仍可经 `m._LADDER_SEAL` 属性拿到，且它没处理
`object.__new__` 绕构造器与事后字段替换。本轮**自己重新论证**后改用**闭包持牌**
（令牌不是模块属性，比全局强一档），并叠加消费端重推导（草稿没有这层）。主控
README 第 3 条点名「私有哨兵是不是又一个表面」——本轮的答复写在 §四：哨兵本身
**不是承重层**，承重层是消费端全检；哨兵被 introspection 抠走也不放行任何 z。

## 一、改了什么（选择的方向与论证）

派工单 §一 给了三条合法方向，本席**走 (a)+(c) 的组合**，两层各自独立成墙：

**(a) 真封印（入口）**：`ValidatedFloorLadder` 的构造器要求出示一个**只存在于
工厂函数闭包里**的令牌（`multifloor.py:189-190`；⛔ 不是模块属性，比对在
`:236-247`）。
模块外拿不到这个名字 ⇒ 直接构造 / `dataclasses.replace` / 子类构造全部具名红
（`LADDER_MINT_SEAL_REQUIRED` / `LADDER_SEALED_NO_SUBCLASS`）。

**(c) 不信任载体携带的值（出口全检）**：上一轮声称走 (c) 却没生效，病根是
`:384-417` 直接读 `level.z_floor_m`。本轮把 (c) **搬到消费边界**：
- 载体**只存一个字段** `_artifact`（`:227`）——**不存在任何 z 携带状态**，
  「换元素」这个攻击类别没有了对象（上一轮被击穿的那个 `_levels` 字段已删除）；
- `__len__` / `__iter__` / `__getitem__`（`:297/:300/:303`）全部经
  `_levels_of_carrier`（`:275-295`）→ `_levels_of`（`:368-388`）**每次读取重新
  推导**：先 `validate_evidence_bundle`（`:382`，B3 同一道门复用，⛔ 不是第二份），
  再 `_byte_z` 从冻结字节解析；
- 装配处 `levels = tuple(ladder)`（`:508`）——装配消费的 levels **永远来自这次
  调用中的重新推导**，⛔ 永远不是从实例状态读出来的值。

两层为什么都要：(a) 挡得住「正常语言构造语义」下的一切铸造（含 replace、子类），
但 `object.__new__` 绕过一切 `__init__`——**(c) 才是连它一起挡死的那层**：壳
载体唯一能塞进去的 `_artifact` 在读取时过门，塞鸭子类型 → `LADDER_CARRIER_CORRUPT`，
塞类型正确但漂移的真 artifact → `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`。
反之只有 (c) 没有 (a)，复核方那段脚本会死在一个没有名字的属性错误上——
(a) 给它一个具名的死法。

`_mint_ladder` 退回纯层级铸造（返回 levels 元组，`_levels_of` 是唯一推导核心，
derive / 读取 / 装配共用同一条路）；`derive_floor_ladder` 保持**急切过门**契约
（`:407` 先 `_levels_of` 再 `_mint_sealed_ladder`，坏 artifact 在门口具名红，
⛔ 不是懒推导）。

**⚠️ 一处语义变化（如实报）**：`NONPOSITIVE_CEILING_HEIGHT`（装配边界检查）
经**任何**构造路径都不可达了——`_mint_ladder` 对相邻 rung 强制严格递增
（`rise <= 0` 即 `FLOOR_LADDER_NOT_ASCENDING`），而装配消费的 levels 必然来自
`_mint_ladder`。该检查**保留**为纵深防御（防未来别的装配器从别处盖 z 章），
测试改为经 monkeypatch 缝隙（本文件既有模式）仍覆盖该分支。零高度输入本身
（`lower==upper` 的伪造层）现在死得更早：构造载体时即 `LADDER_MINT_SEAL_REQUIRED`。

**实测纠错一条（写进测试 docstring）**：`@dataclass(init=False)` 只是不**生成**
`__init__`，字段的 init 标志仍是 True ⇒ `dataclasses.replace`（连裸 replace）
会以 `_artifact=` 关键字调构造器。第一版构造器参数名不匹配、死于**碰巧的**
`TypeError`；已把参数名对齐为 `_artifact`（`:229`），使一切 replace 形状死于
**具名**封印错误。

## 二、本轮自证义务（派工单 §二 三小节）

### 二#1 原路复现（复核方脚本逐字重跑）

命令原文（= 裁决 `2026-09-04p` 阻断项里的脚本，一字未改）：

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
Traceback (most recent call last):
  File "<stdin>", line 17, in <module>
  File "/tmp/b2_rework3_glm/src/agent/correction/multifloor.py", line 237, in __init__
    raise MultiFloorAssemblyError(
src.agent.correction.multifloor.MultiFloorAssemblyError: LADDER_MINT_SEAL_REQUIRED: {'got': 'ValidatedFloorLadder', 'reason': 'ValidatedFloorLadder cannot be constructed outside multifloor: it is minted only by derive_floor_ladder, which runs the frozen-byte gate first (dispatch §一(a))'}
```

**失败点与死法**：死在脚本第 17 行 `ladder = ValidatedFloorLadder((hand_level,))`
——**构造器本身**，具名错误 `MultiFloorAssemblyError.code ==
'LADDER_MINT_SEAL_REQUIRED'`（`:236-247` 强制）。该行在 try 块**之前**，
所以装配函数根本没被触达；全程依旧没有 evidence artifact、没有冻结字节、
没过字节门——但现在这条路**连载体都造不出来**，而不是造出来后被装配消费。

### 二#2 自设同形但不同的伪造路径（两条主路径 + 四条附加）

命令原文：

```bash
python - <<'PY'
import dataclasses
from pathlib import Path
from types import SimpleNamespace

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.evidence_contract import (
    CorrectionEvidenceBundleArtifactV1,
    finalize_bundle,
)
from src.agent.correction.multifloor import (
    MultiFloorAssemblyError,
    ValidatedFloorLadder,
    assemble_multifloor_geometry,
    derive_floor_ladder,
)
from src.agent.correction.schema import CorrectedGeometryV3

raw = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json').read_bytes()
art = adapt_as_drawn_elevation(raw, input_id='probe_east', facade_ref='east')
fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})

# a REAL sealed artifact whose two lowest claims' z_m drifted (refs kept,
# re-finalized) — built from PUBLIC API exactly like the reviewers' rounds 2-3
ordered = sorted(art.bundle.floor_level_claims, key=lambda c: c.z_m)
drift = {ordered[0].structure_line_id: 12.34, ordered[1].structure_line_id: 17.91}
drifted_claims = [
    c.model_copy(update={'z_m': drift[c.structure_line_id]})
    if c.structure_line_id in drift else c
    for c in art.bundle.floor_level_claims
]
drifted_art = CorrectionEvidenceBundleArtifactV1(
    bundle=finalize_bundle(art.bundle.model_copy(update={'floor_level_claims': drifted_claims})),
    frozen_sources=art.frozen_sources,
)

def outcome(label, thunk):
    try:
        thunk()
    except Exception as exc:
        print(label, '= REJECTED', type(exc).__name__, getattr(exc, 'code', ''), str(exc)[:120])
    else:
        print(label, '= !!!ACCEPTED!!!')

print('PROBE1_HONEST_BASELINE=', [(round(l.z_floor_m, 6), round(l.ceiling_height_m, 6)) for l in derive_floor_ladder(art)][:2])

# ── path A: 先合法拿到真载体，再事后换掉它唯一的字段（绕过 frozen 守卫） ──
ladder = derive_floor_ladder(art)
object.__setattr__(ladder, '_artifact', drifted_art)
outcome('PATH_A_POSTHOC_ARTIFACT_SWAP', lambda: assemble_multifloor_geometry(ladder, [one_floor]))

# ── path B: object.__new__ 壳（绕过一切 __init__）+ 鸭子类型 artifact（手填 z） ──
duck = SimpleNamespace(
    bundle=SimpleNamespace(floor_level_claims=()),
    frozen_sources=[SimpleNamespace(
        artifact=SimpleNamespace(input_id='hand'),
        raw_bytes=('{"structure_lines": [{"id": "b", "constant_quantity": "z", "pos_m": 12.34},'
                   '{"id": "t", "constant_quantity": "z", "pos_m": 17.91}], "openings": []}').encode(),
    )],
)
shell = object.__new__(ValidatedFloorLadder)
object.__setattr__(shell, '_artifact', duck)
outcome('PATH_B_OBJECT_NEW_SHELL_DUCK_ARTIFACT', lambda: assemble_multifloor_geometry(shell, [one_floor]))

# ── extra B2: 同一壳 + 真·漂移 artifact（类型正确但没过门） ──
shell2 = object.__new__(ValidatedFloorLadder)
object.__setattr__(shell2, '_artifact', drifted_art)
outcome('EXTRA_B1_SHELL_REAL_DRIFTED_ARTIFACT', lambda: assemble_multifloor_geometry(shell2, [one_floor]))

# ── extra B3: 空 壳（什么都不设） ──
outcome('EXTRA_B2_BARE_SHELL', lambda: assemble_multifloor_geometry(object.__new__(ValidatedFloorLadder), [one_floor]))

# ── extra C: 子类（isinstance 可过 + 覆写 __init__） ──
def _try_subclass():
    class FakeLadder(ValidatedFloorLadder):
        def __init__(self, levels):
            object.__setattr__(self, '_levels', levels)
    return FakeLadder
outcome('EXTRA_C_SUBCLASS_AT_CLASS_CREATION', _try_subclass)

# ── extra D: dataclasses.replace 两种形状 ──
outcome('EXTRA_D_REPLACE_WITH_SWAP', lambda: dataclasses.replace(derive_floor_ladder(art), _artifact=drifted_art))
outcome('EXTRA_D_REPLACE_BARE', lambda: dataclasses.replace(derive_floor_ladder(art)))
PY
```

输出原文：

```text
PROBE1_HONEST_BASELINE= [(-0.0021, 3.6021), (3.6, 3.6021)]
PATH_A_POSTHOC_ARTIFACT_SWAP = REJECTED EvidenceContractError FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE: {'structure_line_id': 'S05', 'pointer': '/structure_lines/4/pos_m', 'claim_value'
PATH_B_OBJECT_NEW_SHELL_DUCK_ARTIFACT = REJECTED MultiFloorAssemblyError LADDER_CARRIER_CORRUPT LADDER_CARRIER_CORRUPT: {'got': 'SimpleNamespace', 'reason': 'the carrier carries no sealed artifact — an object.__new__
EXTRA_B1_SHELL_REAL_DRIFTED_ARTIFACT = REJECTED EvidenceContractError FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE: {'structure_line_id': 'S05', 'pointer': '/structure_lines/4/pos_m', 'claim_value'
EXTRA_B2_BARE_SHELL = REJECTED MultiFloorAssemblyError LADDER_CARRIER_CORRUPT LADDER_CARRIER_CORRUPT: {'got': 'None', 'reason': 'the carrier carries no sealed artifact — an object.__new__ shell or a
EXTRA_C_SUBCLASS_AT_CLASS_CREATION = REJECTED MultiFloorAssemblyError LADDER_SEALED_NO_SUBCLASS LADDER_SEALED_NO_SUBCLASS: {'subclass': 'FakeLadder', 'reason': 'ValidatedFloorLadder is sealed; an isinstance-passing s
EXTRA_D_REPLACE_WITH_SWAP = REJECTED MultiFloorAssemblyError LADDER_MINT_SEAL_REQUIRED LADDER_MINT_SEAL_REQUIRED: {'got': 'ValidatedFloorLadder', 'reason': 'ValidatedFloorLadder cannot be constructed outside
EXTRA_D_REPLACE_BARE = REJECTED MultiFloorAssemblyError LADDER_MINT_SEAL_REQUIRED LADDER_MINT_SEAL_REQUIRED: {'got': 'ValidatedFloorLadder', 'reason': 'ValidatedFloorLadder cannot be constructed outside
```

读法：
- **路径 A**（先合法拿真载体、再 `object.__setattr__` 换掉唯一字段、绕过 frozen
  守卫——上一轮载体「换元素」攻击的直系同形）：换了也没用，装配时重新过门，
  具名 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`。
- **路径 B**（`object.__new__` 壳——**任何 `__init__` 封印都挡不住的最强伪造** +
  鸭子类型 artifact 自带手填 z 字节）：读取时类型全检，具名
  `LADDER_CARRIER_CORRUPT`。
- 附加四条：壳+真漂移 artifact → 门红；空壳 → 具名红；子类 → 类创建即红；
  replace 两种形状 → 具名封印红。全部拒，无一 `!!!ACCEPTED!!!`。
- 这 7 条全部已固化为回归测试（见 §三#1），不是一次性探针。

### 二#3 声称与强制逐句对账

`ValidatedFloorLadder` docstring 原文（`python -c "from src.agent.correction.multifloor import ValidatedFloorLadder; print(ValidatedFloorLadder.__doc__)"` 导出，仅去除类体缩进，文字未动）：

```text
The SEALED assembly carrier (dispatch §一(a)+(c), rework-3).

⭐ CLAIM LEDGER — every claim below names the code that enforces it
(rework-3 dispatch §二#3); a claim with no enforcing line gets deleted,
⛔ not narrated:

1. "It cannot be populated from outside this module" — ``__init__``
   compares ``_seal`` against the closure-held ``_LADDER_SEAL``; any
   external construction attempt (direct call, ``dataclasses.replace``,
   a subclass's inherited constructor) raises the named
   ``LADDER_MINT_SEAL_REQUIRED``.  ``object.__new__`` can still yield an
   attribute-less shell — no ``__init__`` can stop that — which is why
   claim 3 exists.
2. "It cannot be subclassed" — ``__init_subclass__`` raises the named
   ``LADDER_SEALED_NO_SUBCLASS`` at class-creation time, so an
   ``isinstance``-passing subclass with an overridden constructor
   cannot exist.
3. "It stores NO z-bearing state, so there is nothing to swap" — its
   only field is ``_artifact``; ``__len__`` / ``__iter__`` /
   ``__getitem__`` all go through ``_levels_of_carrier``, which
   RE-DERIVES the levels (``validate_evidence_bundle`` first, then
   ``_byte_z`` resolution) on every read.  An ``object.__new__`` shell
   — or an honest carrier whose ``_artifact`` was swapped post-hoc —
   either assembles its artifact's GATED bytes or fails by name
   (``LADDER_CARRIER_CORRUPT`` / ``EvidenceContractError``); it can
   never assemble a value that was merely SET on an instance.
4. "The only sanctioned minter gates first" — the closure-held
   ``_mint_sealed`` is module-private, and its only module-level caller
   is :func:`derive_floor_ladder`, whose first act is ``_levels_of``
   (the gate + derivation), so a bad artifact is a named red at the
   minter's door, ⛔ never inside assembly.
```

逐句对账表：

| docstring 句 | 强制行（`src/agent/correction/multifloor.py`） | 实证 |
|---|---|---|
| 标题句 "The SEALED assembly carrier" | 由下四句共同强制；本轮之前这句是**谎言**（裁决阻断项），现在有封印实体 | §二#1 输出 |
| 引导句 "every claim below names the code that enforces it" | 本表本身 | — |
| 1 "cannot be populated from outside this module" | `:189-190` 令牌定义于闭包（⛔ 非模块属性）；`:236-247` `if _seal is not _LADDER_SEAL → LADDER_MINT_SEAL_REQUIRED`；`:229` 参数名对齐字段名使 replace 的 FIELD 名 kwargs 也进这道检查 | §二#1 + EXTRA_D 两形状 |
| 1 内嵌让步句 "`object.__new__` can still yield an attribute-less shell … which is why claim 3 exists" | 陈述 Python 事实 + 指向第 3 句；由 `:275-295` 兜住 | PATH_B / EXTRA_B1 / EXTRA_B2 |
| 2 "cannot be subclassed" | `:262-273` `__init_subclass__` 类创建时 raise `LADDER_SEALED_NO_SUBCLASS` | EXTRA_C |
| 3 "stores NO z-bearing state" | `:227` 类体唯一字段 `_artifact`（上一轮的 `_levels` 字段已物理删除，非隐藏） | `git diff` 173ed7ef |
| 3 "every read RE-DERIVES (validate first, then _byte_z)" | `:297/:300/:303` 三个读口全部走 `:275-295` `_levels_of_carrier` → `:295` `return _levels_of(artifact)` → `:382` `validate_evidence_bundle` 在解析前；z 只经 `:97 _byte_z`（`:160/:164` 属性、`:339` 排序键）从冻结字节来 | PATH_A：事后换字段也被这次重推导覆盖 |
| 3 "shell / swapped carrier either assembles GATED bytes or fails by name" | `:279-291` 非 sealed artifact 类型 → `LADDER_CARRIER_CORRUPT`；否则 `:382` 门红原样冒泡（装配处 ⛔ 不包裹） | PATH_B / EXTRA_B1 |
| 4 "only sanctioned minter gates first" | `:306-307` `_mint_sealed` 定义于工厂内（持牌）；其模块级唯一调用点 `:408`，且 `:407` 先 `_levels_of(evidence)`（门）后铸造 | `grep -n "_mint_sealed_ladder(" src` 仅 `:408` 一处；§三#4a 探针 |

未写进 docstring 的**不声称**项（同样重要）：没有声称「绝对不可构造」——
`object.__new__` 壳的存在在句 1 里如实写明；没有声称「防 runtime introspection」
（闭包抠牌 / 改模块全局 = 等价于改代码，见 §五）。

## 三、验收对账（派工单 §三 六条）

**#1（模块外无法造出能被装配接受的载体）✅** §二#1 复核方原路死在构造器
（具名 `LADDER_MINT_SEAL_REQUIRED`）；§二#2 两条自设主路径 + 四条附加全部具名拒。
全部 7 条已固化为回归测试：`test_reviewer_round3_replay_public_constructor_is_sealed` ·
`test_posthoc_artifact_swap_is_gated_at_consumption` ·
`test_object_new_shell_cannot_assemble_a_hand_z`（含 duck/漂移/空壳三子形状） ·
`test_subclassing_the_carrier_is_refused_at_class_creation` ·
`test_dataclasses_replace_cannot_rebuild_the_carrier`，全绿。

**#2（(c) 装配 z 不来自载体携带的值 / (a) 元素不可公开构造）✅（两者都做）**
正面说明「为什么现在造不出来」：
- **(a)** 构造要求出示闭包令牌（`:236`）。模块外的名字空间里**不存在**这个绑定
  （它不是模块属性——冒烟检查 `hasattr(m, '_LADDER_SEAL') == False`）；而
  `object.__new__` 壳虽能存在，但——
- **(c)** 装配消费的 levels 不是实例状态：`levels = tuple(ladder)`（`:508`）
  每次经 `_levels_of`（`:382` 门在前）**重推导**，z 只能来自 `:97 _byte_z`
  对冻结字节的解析。**要移动装配出来的那个数，唯一途径是提供一份能过门的不同
  冻结字节** = 自造一份自洽 reading 产物 = reading 信任根（裁决 §三#3 已裁定
  不在 B2 范围）。载体内已无 `_levels` 字段，「换元素」没有对象。

**#3（docstring 每句有强制行）✅** §二#3 逐句对账表；指不出强制行的句子
（本轮之前的 "The SEALED assembly carrier" 空称）已由实体封印兑现，无删除项。

**#4（上一轮已过审四件不退化）✅**
- 旧公开路径（model_copy z_m → 公开 helper）仍关：探针输出原文
  `ROUND2_REPLAY_RESULT=REJECTED CODE= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`
  （命令见裁决同形脚本，驱动 `derive_floor_ladder`，`tests/...
  ::test_reviewer_round2_bypass_is_dead_at_the_public_helpers` 亦绿）。
- 旧裸 z 生产参数仍已迁移：`test_run_correction_refuses_a_bare_z_requires_validated_level`
  + `test_run_multifloor_has_no_z_parameter` 绿（本轮 `pipeline.py` **零改动**，
  `git diff --stat b52c6f5b..HEAD -- src/agent/pipeline.py` 为空）。
- footprint 误贴仍已修：`test_footprint_relabel_is_from_an_explicit_precheck_only` ·
  `test_no_loctype_or_substring_footprint_predicate_remains` ·
  `test_per_floor_footprint_mismatch_is_loud` · `test_duplicate_floor_id_is_loud` 绿。
- 字节门（中间 rung 改值重封 ⇒ 仍拒）：探针输出原文
  `BYTE_GATE_MIDDLE_ID= S05 ORIG= 3.6` ·
  `BYTE_GATE_RESULT=REJECTED CODE= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`。

**#5（本体不退化）✅** 三层混排 `test_three_storey_mixed_heights_assemble_three_floors`
（2.9/3.3/4.2）· 两层连续性 `test_two_storey_assembles_and_passes_pipeline_zstack_check`
· 具名坏输入（计划数 `FLOOR_PLAN_COUNT_MISMATCH` · 非递增 `FLOOR_LADDER_NOT_ASCENDING`
· 退化 `FLOOR_LADDER_DEGENERATE` · 非正层高 `NONPOSITIVE_CEILING_HEIGHT`——语义
变化见 §一末段，分支仍被测试覆盖）· 该文件既有测试全部绿（31/31）。
sm25 常量 grep 锁（`test_no_sm25_elevation_reading_is_hardcoded_in_new_code`）绿；
gt 零接触锁（`test_new_files_never_touch_gt`）绿。

**#6（全量绿 · 逐位闭合）✅** 指定命令原文（环境自证与 pytest 同一条）：

```bash
cd /tmp/b2_rework3_glm && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

首行与 summary 原文：

```text
/tmp/b2_rework3_glm/src/agent/correction/multifloor.py
3787 passed, 2 skipped, 13 xfailed, 211 warnings in 466.56s (0:07:46)
```

有 summary 行 ⇒ 非同机竞争假红。逐位闭合：基线 `3782 = 3777 + 5`；
B2 文件 `grep -c "^def test_"` 本轮 `31`、上轮 `26`（`git show b52c6f5b:…` 核对），
新增 **5** ⇒ `3782 + 5 = 3787` ✓；skip `2`、xfail `13`、failed `0` 不变。

局部（B2 + o22m7）：`62 passed in 5.97s`（上轮 57 + 5）。

## 四、边界如实声明（什么不在这道门之内）

1. **runtime introspection**：闭包抠牌（`__closure__`）、改模块全局、monkeypatch
   本模块——Python 没有真私有。**但这不恢复任何 z**：就算抠出令牌铸出载体，
   装配消费的仍是读取时重过门的字节。哨牌不是承重层，出口全检才是。
2. **reading 作者真实性**：自造一份自洽冻结 reading（自己的 sha、契约分类、
   claim↔字节一致）仍可过门并被装配——裁决 `2026-09-04p` §三#3 已实测并裁定
   为 reading 信任根、不在 B2 范围（本单 §〇② 重申别再动）。
3. **中间产物**：`run_correction(evidence_chain_level=…)` 的单层中间产物在装配
   前仍带该层的 z；装配对最终产物**重新盖章**（`:552-556` 从重推导 levels 取值），
   最终 `floors[]` 的 z 恒为门内字节。B2 的门是装配门，此为口径如实记录。

## 五、最薄弱一处

**装配边界对 `CorrectionEvidenceBundleArtifactV1` 这个类型本身的信任是继承的，
不是自己挣的**：本轮把「不可伪造」压到了「载体里必须是一份过门的 sealed
artifact」这一层，而那份 artifact 的完整性完全由
`evidence_contract.validate_evidence_bundle`（⛔ 本轮明令不许碰的文件）承担。
若 T4-a 复审后那道门被放宽（比如某天跳过某个校验分支），本模块的出口全检会
**跟着一起弱**，而 B2 的 31 条测试可能依然全绿——因为它们用的合成 artifact
不必然踩中放宽的那个分支。次弱（同族）：闭包令牌可被 introspection 抠出，
但如 §四#1 所述抠出后仍无 z 权限，故列为次弱而非最弱。

## 六、停报核查（派工单 §五）

未触发任何 A 层条件：① 未动 §四 禁令（`evidence_contract.py` /
`opening_synthesis.py` / `evidence_adapters.py` 零改动——`git diff --stat
b52c6f5b..HEAD` 全量核对，本轮只改 `multifloor.py`、B2 测试文件、本交件与预置
文档）；② §一 (a)(c) 两条已论证成立并落地（(b) 被吸收为 `:279-291` 的出口
类型全检的一环，不是独立方案）；③ 未改任何已落库产物哈希或基线（原料只读）。
无 B 层需要记录的事项。

## 七、操作声明

- 全程工作目录 `/tmp/b2_rework3_glm`；**未进入** `/workspaces/EnergyPlus-Agent-dev`
  做任何写操作（仅只读借阅孤儿草稿三份文件作思路）。
- 未执行 `pip install -e .` 或任何写 `site-packages` 的命令；未用 `git add -A`
  （逐路径 add，每次 commit 前看 `--cached --numstat`）；pytest 一律 `-n 6`。
- 主树预置的两份审阅文档（派工单 + 上轮裁决）原样落库为第一笔提交，未改动内容。
