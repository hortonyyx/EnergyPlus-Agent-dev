# 执行档 · 模块 4 返工：`single_face` 通道补锁

- **日期**：2026-09-01 · **施工方**：GLM 家族（模块 4 原席位）· **待审**：GPT 家族
- **派工单**：[2026-09-01_o22m4_rework_single_face_channel.md](../request/2026-09-01_o22m4_rework_single_face_channel.md)
- **裁决**：[2026-09-01_o22m4_crossreview_claude.md](../verdict/2026-09-01_o22m4_crossreview_claude.md)（REWORK / 阻断 1 / 题错 #55）
- **基线 commit**：`a6f5383`（= 派工单声明的排程前提；开工时 `git log --oneline -1` 亲核）

---

## 一、开工自检（三件，全部亲核）

| # | 项 | 命令 | 实测 |
|---|---|---|---|
| 1 | HEAD + 干净树 | `git log --oneline -1 && git status --porcelain` | `a6f5383 09.01e_DispatchThreeSeats_Baseline3601_ConcurrencyClauses`；status 空 |
| 2 | `.pth` 哨兵（开工） | `sha256sum /opt/venv/.../_editable_impl_energyplus_agent.pth` | `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |
| 3 | 派工单点名文件 | `ls` / `grep -n` | `wall_compiler.py` 1419 行、`test_o22m4_wall_compiler.py` 1045 行、裁决 md 8159 B 均在；`_compile_single_face` 唯一出口 `return wall, [item], []`（840 行）亲读 |

---

## 二、前提复现（§一 承重前提，逐条重跑）

### 1. 既有 43 条全绿（43 = m4 22 + m3 21，口径来自裁决 §一.1）

```
$ python -m pytest tests/test_o22m4_wall_compiler.py tests/test_o22m3_evidence_adapters.py -q -n 6
43 passed in 11.37s
```

### 2. 四通道存货普查（改造前，`_compile_single_face` 必须 0 命中）

```
$ python /tmp/o22m4_channel_probe.py tests/test_o22m4_wall_compiler.py tests/test_o22m3_evidence_adapters.py
43 passed, 1 warning in 14.00s
pytest rc=0
_compile_legacy_trace    35
_compile_paired          260
_compile_single_face     0
_compile_solid_band      16
```

**与裁决 §一.2 逐字对齐（260 / 16 / 0 / 35）⇒ 前提复现成立，不停报。**

⚠️ **探针实现方式差异（§六"只记不停"层）**：复核方当年在独立 worktree 里**改源码**插探针；本席被禁建 worktree、且生产码必须零 diff，故改为**父模块属性换 wrap**（`setattr(wc, '_compile_single_face', counting_wrapper)`——模块内调用点走模块 globals，wrap 生效）+ `pytest.main` 同进程跑。⚠️⚠️ **顺带撞出的坑，写给后来者**：repo 的 `pyproject.toml addopts = ["-n", "auto", "--dist", "load"]` 会让任何 wrap 式探针**静默失效**（xdist worker 子进程重新 import，绕开 wrap），且 pytest rc=0 全绿——我第一次跑拿到四通道全 0 的假读数。**wrap 式探针必须显式 `-n0`**。wrap 生效的自证见 §四 验收 1 的计数对账。

探针脚本全文（38 行，一次性测量，不入仓库；复读数可按此复现）：

```python
"""One-shot channel-inventory probe for the o22m4 rework (2026-09-01).

Wraps the four _compile_* entry points by swapping the PARENT module's
attributes (in-module call sites resolve through module globals), then runs
the given test files in-process with pytest.main so the wrappers stay live.
Serial on purpose: xdist workers re-import the module and would dodge the
wrap.
"""
from __future__ import annotations

import sys

import pytest

import src.agent.correction.wall_compiler as wc

COUNTS: dict[str, int] = {name: 0 for name in (
    "_compile_paired", "_compile_solid_band", "_compile_single_face",
    "_compile_legacy_trace",
)}


def _wrap(name: str) -> None:
    original = getattr(wc, name)

    def wrapper(claim, ctx, _name=name, _original=original):
        COUNTS[_name] += 1
        return _original(claim, ctx)

    setattr(wc, name, wrapper)


for _name in COUNTS:
    _wrap(_name)

if __name__ == "__main__":
    targets = sys.argv[1:] or ["tests/test_o22m4_wall_compiler.py"]
    # -n0 on purpose: repo addopts force xdist, whose workers re-import the
    # module in another process and would dodge the in-process wrap.
    rc = pytest.main(targets + ["-q", "-n0", "-p", "no:cacheprovider"])
    print(f"pytest rc={rc}")
    for key in sorted(COUNTS):
        print(f"{key:<24} {COUNTS[key]}")
    sys.exit(rc)
```

### 3. 夹具可造性（§六必停项「夹具造不出来」——先手工证明再写测试）

写测试前用一次性脚本证明五个夹具全部构造得出来且编译行为符合裁决描述（真实 L012 四候选 ±0.24/±0.12、preview 锚在 `pos_m=9.1516`、决策半边关闭、`observed_unclaimed`/`ink_present_unpromoted` 手换后 validator 全绿）。**未撞上「必停」任何一条；补锁过程中没有发现实现有 bug**（`_compile_single_face` 的行为与设计稿 §4.1/§5.2/§6.1 及其 docstring 逐条吻合）。

---

## 三、改了什么（⚠️ 生产代码零改动，唯一改动文件 = `tests/test_o22m4_wall_compiler.py`）

| 新增 | 内容 |
|---|---|
| `_unpaired_face_doc(callouts, *, with_counterface)` | 合成夹具：恰一条 unpaired 墙面 F04（+可选 non_wall F05）；`callouts=None` 即「源里没有任何厚度尺度」 |
| `_assert_axis_item_open_not_silent(comp, wall)` | 通道不变量一处成文：`axis_offset_undetermined` 开项开着 · `IDENTITY_BAN` 在排除项 · 无中线/无厚度/无 output_basis · **无任何 auto action 触碰该墙** |
| `_rebound_single_face_claim(art, **updates)` | 在 adapter 自己产的 bundle 上换 claim 的 counterface 字段后重新 `finalize_bundle`（channel/debt 路由复用 adapter 产物，不手抄） |
| **A** `test_single_face_real_l012_opens_axis_item_with_both_offset_families` | **真实夹具** sm25_2f `L012`（unpaired 桶恰 1 条、ambiguous=0、callouts [240,120]，前提全部在产品上实测）：候选 = {POS,NEG}×{0.24,0.12}、preview 逐个对 `pos±v/2`（pos 从 doc 独立重读）、全 `declared_callout` 出处、`completion="degraded"`、**决策半边**（OFFSET_POSITIVE(0.24) ⇒ 中线 `pos+0.12`、`output_basis="wall_axis"`、item 关闭）——锁「开项不是死胡同、显式决定是唯一 close 路」 |
| **B** `test_single_face_unique_thickness_scale_still_requires_a_decision` | **反方向**（设计稿 §6.1）：单一厚度尺度（callouts=[200] ⇒ 候选只剩符号自由度 =「筛成唯一」在编译器可见的极限）⇒ **仍开项**、无中线、重编译无决策时什么也不变 |
| **C** `test_single_face_without_any_scale_opens_with_empty_candidates` | **无候选支**（任务 5）：无任何厚度尺度 ⇒ 候选集空、item **仍开**、`IDENTITY_BAN` 在；对空候选集下决策 ⇒ `UNKNOWN_DECISION_CANDIDATE` 且 `available=[]`（合法出口只有显式决定/再感知/降级 profile，绝不静默定轴） |
| **D1** `test_single_face_observed_unclaimed_counterface_still_no_silent_axis` | `counterface_state='observed_unclaimed'`（counterface 被观测但被 non_wall 处置吃掉）⇒ 同通道同行为：仍开项、无中线 |
| **D2** `test_single_face_ink_present_unpromoted_witness_still_no_silent_axis` | `counterface_state='ink_present_unpromoted'`（= L012 那段 prose 的真实故事，手绑定）⇒ witness 可解析（该层对 witness 的唯一硬性质）、同通道同行为 |

文件头 docstring 补了 Rework 段（说明本批锁的来历与覆盖）。共 **+5 条测试**（22 → 27），**既有 22 条断言零改动**。

**三条任务↔夹具对账**：任务 1（claim 夹具 + counterface 取值）→ A/B/C（`not_in_observations`，adapter 真实产出）+ D1/D2（另两种）；任务 2（`axis_offset_undetermined` + 候选 + `IDENTITY_BAN`）→ A（带候选）与 C（无候选）都锁；任务 3（证明能红）→ §四 变异 1；任务 4（筛成唯一仍开项）→ B + 变异 2；任务 5（无候选支）→ C + 变异 3。

---

## 四、验收表逐条读数

### 验收 1 ⭐⭐⭐ 存货普查复现：`_compile_single_face` 命中 > 0

```
$ python /tmp/o22m4_channel_probe.py tests/test_o22m4_wall_compiler.py tests/test_o22m3_evidence_adapters.py
48 passed, 1 warning in 9.41s
pytest rc=0
_compile_legacy_trace    35
_compile_paired          302
_compile_single_face     8      ← 0 → 8
_compile_solid_band      16
```

**计数对账（wrap 生效的自证，非「测试名字里带 single_face」）**：A 调 `compile_wall_ir` 2 次 × 1 面单 = 2；B 2 次（初编 + 无决策重编）= 2；C 2 次（初编 + `_expect_error` 里那次）= 2；D1/D2 各 1 次 = 2 ⇒ **8，与实测精确吻合**。`_compile_paired` 260→302 的 +42 也对得上：A 的真实产品 sm25_2f 有 21 个 selected pairs × 2 次编译 = 42。

### 验收 2 ⭐⭐⭐ M7 变异（`return wall, [item], []` → `return wall, [], []`）必须红

```
$ python /tmp/o22m4_mutate.py m7_drop_item
mutation m7_drop_item applied to _compile_single_face body (lines 784..842)
 src/agent/correction/wall_compiler.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
FAILED tests/.../test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
FAILED tests/.../test_single_face_real_l012_opens_axis_item_with_both_offset_families
FAILED tests/.../test_single_face_without_any_scale_opens_with_empty_candidates
5 failed, 22 passed in 14.61s      ← 五条新锁全红；既有 22 条仍绿
$ git checkout -- src/agent/correction/wall_compiler.py
```

（变异注入按函数体 span 定位，只落在 `_compile_single_face` 内——`_compile_legacy_trace` 里同形的 `return wall, [item], []` 不受影响，故 legacy 锁全绿是预期而非漏网。）

### 验收 3 ⭐⭐ 「筛成唯一就自动执行」写进去 ⇒ 必须红（独立锁）

变异：在 `_compile_single_face` 的 `if candidates:` 之前注入「所有候选共享同一厚度值 ⇒ 自动取正向偏移、不开项」（9 行）。

```
$ python /tmp/o22m4_mutate.py unique_auto_exec
 src/agent/correction/wall_compiler.py | 9 +++++++++
FAILED tests/.../test_single_face_unique_thickness_scale_still_requires_a_decision
1 failed, 26 passed in 9.41s      ← 恰好只红 B 那条
```

### 验收 4 ⭐ 无候选那一支：变异「`if not candidates: return wall, [], []`」⇒ 必须红

```
$ python /tmp/o22m4_mutate.py empty_no_item
 src/agent/correction/wall_compiler.py | 2 ++
FAILED tests/.../test_single_face_without_any_scale_opens_with_empty_candidates
FAILED tests/.../test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
FAILED tests/.../test_single_face_observed_unclaimed_counterface_still_no_silent_axis
3 failed, 24 passed in 9.55s      ← 恰好红 C/D1/D2（无候选三条）
```

**变异分辨力矩阵**（三列互不串扰）：

| 变异 | A 真实·双尺度 | B 单尺度 | C 无尺度 | D1 unclaimed | D2 ink |
|---|---|---|---|---|---|
| M7 摘开项 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |
| 唯一值⇒自动执行 | 🟢 | 🔴 | 🟢 | 🟢 | 🟢 |
| 无候选⇒不开项 | 🟢 | 🟢 | 🔴 | 🔴 | 🔴 |

### 验收 5 既有 43 条逐条仍绿 + 新增条数逐条有出处

- 43 条（m4 22 + m3 21）在下面两份读数里全绿：`27 passed`（m4，22 既有 + 5 新）与受影响子集 `154 passed`（m2 33 + m3 21 + m4 27 + m56 73，逐文件与已知基线对上）。
- 新增 5 条逐一见 §三表格；无参数化（`grep def test_` 即全量）。

### 验收 6 生产代码零 diff

```
$ git diff -- src/agent/correction/wall_compiler.py | wc -c
0
```

### 验收 7 改动路径（⛔ 未提交，交主控）

```
M  tests/test_o22m4_wall_compiler.py        （+5 条锁 + 2 个夹具 helper + 1 个换 claim helper + docstring 段）
M  AI_agent/logs/reviews/execution/2026-09-01_o22m4_rework_execution.md（本执行档）
```

工作树上另有一份 untracked `AI_agent/logs/reviews/verdict/2026-09-01_o22m56_rework_crossreview_gpt.md`——**GPT 席模块 5/6 复审的产物，不在我的写面，未触碰**，仅如实记录。

### 受影响子集（显式路径，`-n 6`）

```
$ python -m pytest tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py \
    tests/test_o22m4_wall_compiler.py tests/test_o22m56_decision_loop.py -q -n 6
154 passed in 14.11s
```

⭐ 其中 m56 的 73 条正是消费 `open_items` 的下游锁——本批改动未破坏任何一个消费者。

---

## 五、哨兵两次读数

| 时点 | sha256 |
|---|---|
| 开工自检 | `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |
| 交件前（终验） | `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |

两次相同；全程未跑任何写 `site-packages` 的命令。

---

## 六、我认为派工单哪里写错了（或值得记的偏差）

1. **「`counterface_state` 的两种取值各一份更好」——实际是三种**。设计稿原本两值，被模块 2 跨审 N-1 推翻成三值（`evidence_contract.py` L254 起写明，`ink_present_unpromoted` 必须带 pixel witness）。派工单与裁决都沿用「两种」。本席按**三种全覆盖**处理：`not_in_observations` 由 A/B/C（adapter 真实产出）覆盖，D1/D2 补另两种（属 §六「夹具字段取值——只记不停」层的裁量）。
2. **「跑全部 43 条」未说明是哪两个文件**。43 = m4 22 + m3 21 需回裁决 §一.1 反推；建议今后此类读数直接点名文件清单（本档 §二已补）。
3. **非错误、但值得后来者知道的坑**：repo 默认 `addopts = -n auto` 会令一切「同进程 wrap」式探针**静默失效**（全 0 假读数 + rc=0），必须显式 `-n0`。复核方当年用改源码式探针不受影响；任何想复刻 wrap 式测量的人会先撞这个。

---

## 七、最薄弱的一处 + 请复核方重点打哪里

**最薄弱**：D1/D2 是「adapter 产物上手换 claim」的夹具——今天**没有任何生产 adapter 会产出** `observed_unclaimed` / `ink_present_unpromoted` 这两种取值（adapter 只机械产默认值，evidence_adapters.py 注释写明第三种要等 producer 发结构）。所以 D 锁的是「这两种枚举值**一旦合法出现**，编译行为正确」（validate 全绿作前提），**不是**「生产链路会产出它们」。后者是模块 3/producer 侧的领地，不在本单。

**请重点打**：
1. **B 对设计稿 §6.1 的解读**：「筛成唯一」严格说是模块 5 decision-packet 阶段的概念，模块 4 层面没有「筛」这个动作；我把它落成「所有候选共享同一厚度值（数值唯一、只剩符号自由度）」。这个等价是否成立，请独立判断。
2. **第四种变异**：本档只做了派工单点名的三种。复核方自造的变异里，值得试「`_compile_single_face` 候选悄悄混入 `SNAP_TO_DECLARATION`」「counterface_state 分叉出不同编译行为」——按 §三的断言面，前者会被 A 的候选集合同断言抓红，后者 D1/D2 与 C 共用 `_assert_axis_item_open_not_silent` 应当全红；若没有，那是我的锁有洞。
3. **A 决策半边与 preview 的关系**：`decided` 的中线断言 `pos+0.24/2` 与候选 preview 的重算是同式——若认为这是「复读」而非独立重算，请指出（legacy 侧同型测试是我抄的范式）。

---

## 八、交付

- 代码：`tests/test_o22m4_wall_compiler.py`（⛔ 未提交，交主控）
- 本执行档即 §七 交付物
- 探针/变异脚本为一次性测量（全文已抄录于 §二/§四，可按原文复现），不入仓库
