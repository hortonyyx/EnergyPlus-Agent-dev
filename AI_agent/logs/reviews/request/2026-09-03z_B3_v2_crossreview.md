# 复核单 · **B3 as-drawn 立面腿（v2）跨家族审**

- **日期**：2026-09-03（第三程）· **派工方**：orchestrator
- **复核方**：**GPT 家族**（⛔ **不得 GLM** —— GLM 是施工方）
- **工作目录（写死）**：`/tmp/b3_review_gpt`（detached @ `917df4b`）
- **⛔ 别写主树** `/workspaces/EnergyPlus-Agent-dev`。

## 一、审什么

| 项 | 值 |
|---|---|
| **净 diff** | `git diff 431c44b..917df4b` |
| **四笔分段提交** | `2cba7ca` T0 恢复（revert 那次回退）· `6df6660` T6 第三条线登记 · `e299a9d` T7 真入口接线 · `917df4b` T8 执行档 |
| **改动面** | `evidence_contract.py` 400/5 · `evidence_adapters.py` 287/6 · `pipeline.py` 35/6 · `vector_contract.py` 7/1 · `test_b3_elevation_leg.py` +563 · 另 4 个既有测试文件小改 |
| **任务书** | [`2026-09-03v`](2026-09-03v_B3_as_drawn_elevation_leg_dispatch_v2.md)（**十条验收，规则形态**）|
| **施工方自述** | [执行档](../execution/2026-09-03v_B3_as_drawn_elevation_execution.md) ⭐ **线索，非证据** |

> **⛔ 自述的地位**：只看**原始需求 + diff + 你自己跑出来的输出**。
> 凡它声称的读数，要么你自己复现，要么在裁决里标成「未复现」。

## 二、⭐ 本单的背景：**这份工作被回退过一次**

上一轮它交了 1190 行，因权威全量 **1 failed** 被整体回退 ——
`test_only_the_two_named_contracts_hold_wires` 断言 `adapting == {CONTRACT_AS_DRAWN_PLAN}`，
而立面契约转 `ADAPT` 后变成两个。**那把锁工作得完全正确，是这条线没走完最后一步。**
⚠️ 且**那一格是派工方（我）漏写进单子的**，⛔ 不是施工方的问题。

本轮 = **恢复那 1190 行（T0，机械 revert）+ 补两件新的**：
- **T6**：把第三条线**登记成有意的**（⛔ 不许只把断言里的集合改大）
- **T7**：⭐ **派工方复盘时发现的第二处不完整** —— `ADAPT` 会让台账印「已接线」，
  而真入口 `pipeline.py` 的 if/elif **没有立面分支**、无通用注册表 ⇒ **自称已接线而真入口抛 `UNWIRED`**。
  ⭐ 施工方**实测确认了这条**（分类器判 `as_drawn_elevation_v0` / `ADAPT`，真入口喂真字节确实抛 `UNWIRED`），并接上了分支。

## 三、⭐⭐⭐ 请重点打这四处

| # | 打哪里 | 为什么 |
|---|---|---|
| **P-1** ⭐⭐⭐ | **T6 是「规则」还是「名单」** | 任务书 T6-b 明令「⛔ 不许只把断言里的集合改大，必须写明为什么这条线是有意的」。⭐ 请判：改完之后，**第四个契约悄悄转 `ADAPT`，那把锁还会不会红**？（⛔ 别只读代码，跑一次变异）。另：T6-c 要求**锁的名字不能再说谎**（它叫 `only_the_TWO_named_contracts`，而现在 consuming 1 + adapting 2 = 三个）|
| **P-2** ⭐⭐ | **T7 的锁是不是真走了入口** | 任务书 T7-b 明令「⛔ 不许直接调 `adapt_as_drawn_elevation` 就算数」。请判它两把锁是否真从 `pipeline.py` 那个入口喂字节，且**摘掉分支 ⇒ 红成 `UNWIRED`** |
| **P-3** ⭐⭐ | **T4「楼层线的挑选是规则不是名单」** | 这是本单最容易偷懒的一处。任务书要求：换一份**层数不同**的合成立面 ⇒ 规则仍挑对，且 **⛔ 代码里不许出现 sm25 的具体标高（3.6 / 7.202）或「两层」这类常数**。⭐ 请自己 `grep` 一遍新增代码里的数字常量 |
| **P-4** | **T7-a 有没有越线** | 任务书只放开 `pipeline.py:1093-1120` 那**一处 if/elif 加分支**，其余任何地方不许动。施工方自报「该支自己的配套改动：函数内 import 两行、docstring 路由句、`UNWIRED` 的 `wired` 名单」——⭐ 请判这三小块**算不算越线** |

⭐ **施工方自报最薄弱处**（供你参考，⛔ 不是让你据此下裁决）：
「T7-b neuter 锁靠**常量重绑定**模拟摘分支 —— 若将来分支改写法（dispatch 表 / 字面量比较）它会**静默失效**。」
它还点名希望你打：**T5-b 的 B4 归属论证** · **T7-a 那三小块是否越线** · **登记表是否达到「规则非名单」门槛**。

## 四、⛔⛔ 一条事故，请你**独立核实它的边界**

施工方在执行档里**主动自报**：T7-a 加分支后的**两次验证无意出网** ——
两次调 `run_correction_evidence_chain` 都没给 `fixed_responses` ⇒ decision loop 走 provider 模式
**真调了模型**（约 6 次），产物落在 `/tmp/b3_t7_probe*`、未进仓库。

⭐ **它把教训转成了锁的形态**：两把新锁全部走 `fixed_responses` 免模型出口，
并在锁里断言 `response_source` 以 `fixed_responses` 开头。

**⭐ 请你核实两件事**（⛔ 别只信自述）：
1. **仓库里现在还有没有任何测试会真调模型** —— 尤其 `tests/test_b3_elevation_leg.py` 那 563 行。
   ⭐ 判据 = 跑全量时门（`ep_no_billed_gate`）有没有拦到、有没有测试因此 failed。
2. **那两把锁的 `response_source` 断言真的有牙吗** —— 把它改回不给 `fixed_responses` ⇒ 必须红。

## 五、验收（照任务书 §六 十条逐条报）

`0` 恢复的就是当初那份 · `1` 四份立面产物全走分类器 · `2` z 与楼层标高可指回冻结字节 ·
`3` 楼层线是规则不是名单 · `4` bundle 逐位可复现 · `5` 坏输入响亮失败 ·
`6` 第三条线被签字 · `7` 「已接线」在真入口兑现 · `8` 单外对撞规则自己走过一遍 · `9` 全量绿。

**全量基线** = `3717 passed / 2 skipped / 13 xfailed / 0 failed`（exit 0）。
B3 必然**增加**条数 ⇒ 请核**逐位闭合**：`3717 + <T0 恢复带回> + <T6/T7 新增> = 你的读数`。

## 六、⚠️ 环境

1. ⛔ 不要跑 `pip install -e .`。承重不变量 = `m.__file__` 落在你自己目录里，**与 pytest 同一条命令**：
   ```bash
   cd /tmp/b3_review_gpt && \
   python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)" && \
       python -m pytest -q -n 6 -p no:cacheprovider
   ```
2. **并行一律 `-n 6`**，⛔ 不用 `-n auto`。⭐ **判假红看有没有 summary 行**；没有就是同机竞争，重跑、⛔ 不记回归。
   ⚠️ **此刻另有一个 Claude 席位在同机跑 F-158 返工**，请预期竞争。

## 七、⛔ 明确不做

⛔ 不要改代码（你是复核方，发现问题写进裁决，⛔ 不代施工）·
⛔ 不碰 `ep_no_billed_gate.py` / `pyproject.toml` / `tests/conftest.py`（**F-158 返工正在同时进行**，会撞）·
⛔ `git add -A` · ⛔ 动主树。

## 八、裁决

写进 `AI_agent/logs/reviews/verdict/2026-09-03z_B3_v2_crossreview_gpt.md`：
结论 `APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` + **阻断 N / 不阻断 M**；
§三 P-1～P-4 逐条给判断；§四 两件核实结果；§五 十条逐条报。
⭐ **凡你没能复现的，明写「未复现」**，⛔ 不许拿施工方自述凑裁决。
