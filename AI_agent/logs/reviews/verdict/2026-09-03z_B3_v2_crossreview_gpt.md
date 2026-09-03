# B3 as-drawn 立面腿 v2 · GPT 跨家族复核裁决

- 日期：2026-09-03
- 审对象：`git diff 431c44b..917df4b`
- 工作树：`/tmp/b3_review_gpt`，detached `917df4b`
- 施工方：GLM；复核方：GPT

## 裁决

**REWORK / 阻断 3 / 不阻断 1**

本体的数据承载、来源引用、楼层线谓词、真入口接线和全量回归均成立；但三条明确验收没有闭合：T6 的主锁在第四契约变异后仍为绿、T5-b 没有拒绝“尺寸链总长与外皮跨度不符”、两把 T7 锁中只有一把能在去掉 `fixed_responses` 后变红。

## 阻断项

### B-1 · T6-d 的第四契约变异没有打到主锁

`tests/test_o22m1_as_drawn_producer_types.py:446` 的 `_wire_sets` 把 `CONTRACTS` 放在默认参数里，定义时即绑定旧 tuple；主锁在 `:471` 调 `_wire_sets()`，因此运行时给 `vector_contract.CONTRACTS` 塞入第四个 `ADAPT` 契约时，主锁仍读取旧值。常驻变异测试 `:502` 没有调用主锁，而是显式传入变异后的 tuple 后重新写了一遍预期相等式。

独立变异输出：

```text
MAIN_LOCK=GREEN_AFTER_FOURTH_ADAPT_MUTATION
RESTATED_MUTATION_ASSERTION=RED
```

这正是同仓参照锁 `tests/test_o22m7_evidence_wiring.py:644-647` 明文警告的默认参数失效形态。`_ADAPTING_WIRES` 的登记理由、契约集合精确对账、入口存在且 callable、公开 `adapt_*` 面反向对账，本身已经达到“有意登记的规则”门槛；阻断点不是登记表手写，而是 T6-d 没证明“那把主锁”会红。

返工判据：主锁必须从调用时的真实 `vector_contract.CONTRACTS` 取值；第四契约转 `ADAPT` 后，直接运行主锁应抛 `AssertionError`，变异测试不得靠另抄一条断言自证。

### B-2 · T5-b 的“尺寸链总长 vs 外皮跨度”拒绝门缺失

任务书 T5-b/验收 #5 明列三类坏输入，其中包括“尺寸链总长与外皮跨度对不上 ⇒ 具名错误”。当前 `src/agent/correction/evidence_adapters.py:546-558` 明确把这半条推给 B4；实际 `_require_chain_closed`（`:564-606`）只核 `sum(values_mm) == cum_mm[-1] == overall_mm`，并不与外皮/结构跨度对账。执行档不能单方面改写本单的验收归属。

独立变异以真实 east 字节为底：保持 x 尺寸链内部闭合，把总长整体改为 21m，结构线所示跨度仍约 19.9954m。结果：

```text
SPAN_MISMATCH=ACCEPTED chain_m=21 structure_span_m=19.9954
```

因此“坏输入响亮失败”没有三项闭合。返工应实现有来源、无猜测的等值门并配常驻负例；若设计上确须由 B4 承担，应先由派工方正式修改本单验收，不能以执行档说明替代。

### B-3 · 两把 T7 锁并非都能阻止 `fixed_responses` 被移除

正向锁 `tests/test_b3_elevation_leg.py:494-532` 明确断言 `response_source.startswith("fixed_responses")`，该断言有牙：去掉 `fixed_responses`、用本地假 provider 避免出网后，独立变异得到：

```text
MUTATION_WITHOUT_FIXED_RESPONSE_SOURCE=model:correction_decision
RESPONSE_SOURCE_ASSERTION=RED
```

反向锁 `:535-563` 虽传了 `fixed_responses=[]`，但没有 `response_source` 断言；把该实参删除后仍然为绿，因为 `UNWIRED` 在 provider 选择之前已经抛出：

```text
NEGATIVE_LOCK_WITHOUT_FIXED_RESPONSES=GREEN
```

故复核单要求的“把它改回不给 `fixed_responses` ⇒ 必须红”只对一把成立，执行档“两个锁都在锁内断言 response_source”的陈述也与源码不符。返工需让两把锁都机械守住免模型出口；反向锁若因失败发生在 route 生成前不能读 `response_source`，可用等价的调用参数/模型座位 booby-trap，但去掉 `fixed_responses` 的变异必须红。

## 不阻断项

### N-1 · 执行档的 T0 测试计数说明写错，算术结果仍正确

执行档称 T0 文件“def 数 27、collect 27、无参数化展开”。独立计数为 T0 文件 **18 个** `def test_`，参数化展开后是 **27 个测试项**；当前文件是 20 个 `def test_`、29 个测试项。总量等式仍正确，不影响回归结论，但执行档应更正证据文字。

## P-1 ～ P-4 重点判断

### P-1 · T6 是规则还是名单

**登记形态判为规则，但变异牙口不合格。** `_ADAPTING_WIRES` 不是只把旧断言集合加大：它记录 contract→入口、解释 elevation 线为何有意，并与 disposition 表、入口 callable、公开 `adapt_*` 面双向精确对账；旧测试名也已改为真实规则名。可是第四契约变异只打红了重抄断言，主锁仍绿，故 T6 总体未通过，见 B-1。

### P-2 · T7 是否真走 `pipeline.py` 入口

**通过。** 两把锁均调用 `pipeline.run_correction_evidence_chain` 并喂真实 east 字节，而不是把直接 adapter 调用当最终证据。目标三文件实测 `115 passed`。把分支条件置为不可达后，再调用正向入口锁得到：

```text
GREEN_ENTRY_LOCK_AFTER_BRANCH_NEUTER=RED:EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED
```

绿锁里的 `_round0_elevation_packet` 会直接调用 adapter 以构造绑定哈希，但被测动作仍是公开 pipeline 入口；摘分支时公开入口确实红，故不构成替代测试。T7 接线本身通过；免模型锁的双锁牙口另见 B-3。

### P-3 · T4 楼层线挑选有无 sm25 常数

**通过。** 生产谓词位于 `src/agent/correction/evidence_contract.py:863-887`：只选择 `constant_quantity == "z"` 的所有结构线；adapter 与 validator 共用该函数。不同层数、混合层高的合成立面锁均通过。新增生产代码 grep 未发现 `3.6`、`7.202`、`3600`、`7202`。

生产代码确有 `MIN_FLOOR_LEVELS = 2`（`evidence_contract.py:584`），其含义是整栋立面至少要有“地面 + 一个上界”的退化门；它不参与从 sm25 的三条水平线里点名挑选，也不等于“两层建筑”常数，本席不判为 T4 名单化。

### P-4 · T7-a 是否越线

**不判越线。** `pipeline.py` 的净改动只有同一 `run_correction_evidence_chain` 函数中的：路由 docstring、分支所需的两个函数内 import、新 elevation `elif`、以及 UNWIRED 诊断中的 wired 列表。import 是分支可运行的必要接线；docstring 与 wired 列表只让同一入口的说明/错误上下文跟真实路由一致，没有增加第二条行为路径。未发现该函数之外的 pipeline 改动。

## 模型调用事故边界核实

### 1. 默认测试套件是否还会真调模型

**未发现默认套件中的真实模型调用。** 独立全量固定 `-n 6`，exit 0：

```text
/tmp/b3_review_gpt/src/agent/correction/evidence_contract.py
3748 passed, 2 skipped, 13 xfailed, 211 warnings in 458.56s (0:07:38)
PYTEST_EXIT=0
```

另设 `EP_NO_BILLED_LOG` 收集所有 worker 的门记录，共 8 条，逐条都来自 F-158 自测对 TEST-NET `192.0.2.1:80` 的预期拦截；没有 B3 测试或 provider 路径。B3 两把新增锁分别显式传 `fixed_responses=[...]` 与 `fixed_responses=[]`。

仓库仍有两个显式 `@pytest.mark.live` 测试，其中 `tests/test_zone_agent.py:133` 是真实模型集成路径；它们默认被排除，对应本次 `2 skipped`，不属于默认全量的意外调用。施工方所述历史约 6 次模型调用本席**未复现**，也未拿其自述作为裁决证据；本席只裁当前仓库边界。

### 2. `response_source` 断言是否有牙

**一把有牙，另一把不存在该断言且去参变异不红。** 正向锁的结论和输出见 B-3；反向锁虽当前不会触达模型，但没有守住“以后不许删掉 `fixed_responses=[]`”这项源码性质，故需返工。

## 十条验收逐项

| # | 判定 | 独立复核结论 |
|---|---|---|
| 0 | 通过 | `git diff --exit-code 59a682b 2cba7ca -- <T0 八文件>` 空输出，exit 0；用 T0 提交树比较，避免把后续 T7 对 B3 测试文件的合法改动误算进去。 |
| 1 | 通过 | east/west/north/south 四份真产物均由分类器判为 `as_drawn_elevation_v0 / ADAPT` 并进入 adapter；B3/T6/T7 目标集 115 passed。 |
| 2 | 通过 | 四立面全部 opening z 与 floor level 的引用解回冻结字节，validator 也重算值与来源一致性；目标锁通过。 |
| 3 | 通过 | 楼层谓词为所有 `constant_quantity == "z"`；不同层数/不同层高合成立面通过；无 sm25 具体标高常数。 |
| 4 | 通过 | 四立面同字节双跑的 bundle 与 `content_sha256` 一致；目标锁通过。 |
| 5 | **失败** | z 缺失、链不闭合会具名失败；但尺寸链总长与外皮跨度不符仍被接受，见 B-2。 |
| 6 | **失败** | 登记理由和命名通过；第四 `ADAPT` 契约变异没有打红主锁，见 B-1。 |
| 7 | 通过 | 真字节从 pipeline 入口出 outcome；分支不可达时正向锁红为 UNWIRED。双锁免模型牙口问题单列 B-3。 |
| 8 | 通过 | 独立 grep 了契约 id、两个通道、`ADAPT` 集合持有者及 adapter 入口；活动代码/测试中的既有名单均已同步，未发现第八处过期名单。 |
| 9 | 通过 | 全量 3748 passed / 2 skipped / 13 xfailed / 0 failed，exit 0。 |

测试数逐位闭合：

```text
3717 基线
+ 27  T0：新 B3 文件 18 个 test def，经参数化展开为 27 项
+  2  T6：原 1 把锁替换为 3 把，净增 2 项
+  2  T7：正向入口锁 + UNWIRED 锁
= 3748
```

## 复核命令摘要

所有 pytest 均使用 `-n 6`，未执行 `pip install -e .`。主要独立读数：

```text
目标三文件：115 passed in 5.44s
当前 B3 collect：29 tests collected
全量：3748 passed, 2 skipped, 13 xfailed, 211 warnings
全量 exit：0
```

写裁决前工作树除主控预置并已暂存的复核请求单外无其它状态项；复核过程未修改项目代码。
