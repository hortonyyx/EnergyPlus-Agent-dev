# 定案 · sm24 验收准入门：v3 判卷对 null `scale_origin` 的静默零分（GLM 执行席）

- **日期**：2026-08-20 · **执行**：GLM（工程档） · **派工单**：`reviews/request/2026-08-20_sm24_judge_plan_frame_dispatch_glm.md`

## option 0 的回答（先行）：**不成立，不能只换 run-profile**

机制上成立：merge 侧 `check_reading_stage` 消费冻结档位（`isolation.py:823-831`），regression 下
`plan_scale_origin_usable` FAIL ⇒ BLOCK ⇒ attempt 只归档不被接受——「入口响亮拦下」是真的。

**但它拦死的正是本批要的产物**：读图器侧 null 是合法常态——skill 明文「leave null rather than
guess」（`guide.md:91-101`）；实测 07-07 sm24 靶子产物、08-19 Sonnet/GPT 两臂好产物 `scale_origin`
**全是 null**。regression 档下这些产物全在 merge 被拒，盲重抽（judge 出口零信息）后依旧按指令留
null ⇒ budget 耗尽、**sm24 两格零产出**——比静默零分更坏。顺带收紧面（实测核对
`schema.py` 档位表）：`calibration_axes_agree` + 6 条 evidence 检查同升 BLOCK，当前 HEAD 上
merge 全绿无实测样本，额外跑死风险。**⇒ 必须动判卷端，零代码改动的路不存在。**

## 选了什么：判卷端「响亮化 + strict 档 fail-closed」，不动分数语义

- **信号**（`reading_typed_score.py`）：plan 通道存在 `plan_frame_unavailable` NA 时，score_criteria
  追加一条 `reading.plan_frame_declared` = FAIL（eligible=True、分母 1.0、na_reasons 计数）。
  读分数的人不再需要翻中层证书才能分辨「帧未声明」与「画错」。
- **fail-closed**（`score_service.strict_payload_violation_reason`，被 `run_stage.py` 判卷入口与
  `score_reading_vs_gt.py` CLI 两处消费）：golden/regression 下对该信号 commit-then-raise
  `TopLevelNotApplicableError("plan_frame_unavailable")`（对齐整份 NA 的既有模式）；exploratory/dev
  照常出分、带标记。**gate① 档位口径一个字没动。**

## 否掉的选项

| 选项 | 理由 |
|---|---|
| option 0（换 regression 档） | 见上，拦死合法好产物，零产出 |
| disposition 改 `filter` | 派工单#2 前提**核实成立**：validator 由 cause_class 强制推导（`score_schema.py:700-706`）；且 filter=移出分母=读图器不填原点即逃掉整条通道 |
| 改分数算法（null 时平移对齐判分） | 派工单#3 前提成立：affine 是纯平移、07-07 产物坐标本就 (0,0) 起世界对齐，看似可行——但引入对齐判定语义+分数含义变化，超出「能跑能读」 |
| 指令端收回 MUST / 代码端推导原点 | 归专项（派工单#1 预判正确）；MUST 会直接挡掉 07-07 形式（其 sm24 产物就是 null） |

**第四节前提逐条**：#1/#2/#3 全部核实成立，无需改派；#4 的两处未核路径已由本单补核（见上）。

## 基线实测（修改前自证）与 neuter

- **修改前**（sm24 真实产物 07-27 attempt003，仅删 origin）：判卷 `c2_scored`、20 行全 miss、
  criteria 无任何 frame 条目、strict 不触发——三重静默坐实；declared 对照 5 complete/16 miss/11 extra 不变。
- **修改后**：同夹具出 `reading.plan_frame_declared fail`；miss 行不变（仍在分母，非逃分口）；
  declared 产物零影响（信号不误报）。
- **neuter A**（摘信号）：新锁 5/5 红，邻居 slice0/slice1/adapter 52 把全绿——零连带。
- **neuter B**（只摘 run_stage strict 接线、保信号）：恰好 strict×2 红（锁走真实
  `_grade_typed_attempt_artifacts` 入口，咬住接线），契约/soft 锁仍绿。

**锁**：`tests/test_reading_plan_frame_signal.py` ×5（契约 1 + strict 2 + soft 2）。
全仓 `pytest -n auto`（两次实测）：**改动前（干净 HEAD）2906 绿 + 14 xfail → 改动后 2911 绿 +
14 xfail**——增量恰为新锁 5，零回归。⚠️ 派工单写的基线 2835+14 是 2026-08-17 快照；分支 08-18/19
提交已把基线推到 2906（非本席改动）。

## 顺带发现（未动手）

1. **S1 验收臂冻结的 run_profile=exploratory（source=cli）**——sm24 两格若想要 strict 判卷，须在
   provision 时显式传 `--run-profile`；但按 option 0 结论，验收臂**不应**升 regression（拦死好产物），
   正确用法 = exploratory 跑 + 读 `plan_frame_declared` 信号走 pilot 审合法返工。
2. CLI（`score_reading_vs_gt.py`）的 strict 三行与 run_stage 同型但未被锁覆盖（subprocess 测试成本
   高）；锁覆盖的是 flow 判卷真实入口。
3. 帧缺失时 `no_extra_walls` 因无 observations 反而变 not_applicable（「少画显得更好」的边缘效应），
   retain_as_miss 语义的既有性质，不在本单范围。
4. 本批 sm24 读图器大概率产出 null origin（07-07 形式如此）；正式全通道分需 pilot 审引导读图器
   「cheap and confident 时声明 origin」（guide 本来就允许），这是 07-07 模式 pilot 门的分内事。
