# R1 批 B · r1 交叉对抗审（路 1／共 2）· 被审 = R1-5（terra 产出）· 审 = Claude 侧子代理

- **日期**：2026-08-03
- **派工方**：orchestrator（端到端主控）
- **审阅席**：**Claude 侧子代理（Opus 档）**。⚠️ 原计划派 GLM，**用户 08-03 拍板改走 Claude 侧**（本单据此改派）。
  施工方 = terra（GPT 侧），审方 = Claude 侧 ⇒ **「谁写谁不批」满足，跨家族**。
- **性质**：**对抗审**。你的任务不是确认它做了，而是**尽力证伪它真的做到了**。
- **另一路并行**：R1-1…R1-4 / R1-6 / R1-7（GLM 产出）由另一个 Claude 子代理审
  （[路 2 审阅单](2026-08-03_reading_ruler_r1_crossreview_claude_glm.md)）。**两路互不通气，不要去审对方的范围。**

---

## 0. 一句话背景（不含答案，只给事实）

reading（识图）环节最近所有分数都不可信。已查明**不是模型退化，是判卷这把尺子和运行政策本身坏了**：
`run_config.yaml` 声明 `regression`(fail-closed) + `orthogonal_polygon`，实际落盘的 `checks.json` 头部却是
`exploratory` + `rectangular`；那一轮 gate① 本来抓到 5 条 fail，按 exploratory 算 = 0 阻断、按 regression 算 = 4 条 blocker
⇒ **严格档若真生效，那份产物会被当场拒收**。

批 B 就是修这条。r0 落库后两轮审（orchestrator 轻门 + sol 交叉审）**独立收敛到同一句话**：

> **修好的是「机制存在」，没修好的是「机制在所有真实路径上都生效」。**

⇒ REWORK（6 MAJOR + 1 MINOR）⇒ r1 七条全部返工完成。**你审的是 r1 里最大的那一条 = R1-5。**

**⛔ 硬约束：批 A/B/C 三批全绿之前，本项目不得发布任何新的识图分数或「识图变好/变坏」的结论。**
这次审阅是那条约束的解除条件之一 —— **放水的代价是后面一整批实验白跑。**

---

## 1. 被审对象

| commit | 内容 |
|---|---|
| **`c56cbe1`** `8.03_R1BatchB_r1_R1-5_FrozenPolicyAcrossGeometryAndBaseline` | **本单唯一施工 commit**。7 文件：`scripts/tool_scripts/record_baseline.py` / `scripts/tool_scripts/run_stage.py` / `src/agent/execution/approval.py` / `src/agent/execution/run_policy_freeze.py` / `src/agent/execution/step_orchestrator.py` / `tests/test_orchestrate_baseline.py` / `tests/test_run_stage_flow.py` |
| `22f8f14` | 同一位施工席的执行日志（`AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md` 的 R1-5 段）|

**基线**：orchestrator 独立全量 `pytest -q -n 8` ⇒ **2089 passed + 10 xfailed 零红**（工作树干净、无 `-m` 过滤）。

**R1-5 的原始要求（[r1 返工派工单](2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md) §1）**：

> 冻结的政策只接到 reading checker，没成为整个 run 的政策。
> `cmd_run/cmd_flow` 之后的 correction / modelling / grade 仍消费局部 `policy`
> （`run_stage.py:254-309, 612-627, 1303-1323`）；typed scoring 的严格拒绝也由局部 `run_profile` 决定
> （`:1413-1420, 1455-1473`）；`record_baseline.py:485-503` **重新构造 `RunPolicy`** 且 capability 默认 `rectangular`。
> ⇒ **同一个 run 内，检查、判卷、记账可以各认各的档。**
> S-2 立项时写的是「让声明、发卷、合并、检查、落盘证明成为**同一个事务**」——现在只做到了「检查」这一环。

**锁的要求（派工单 §3）**：每条要有**摘掉即红、零连带**的锁；**锁必须走真实入口**（⛔ 不许把 `None` 直接喂内部函数绕过 argparse 默认值）；
**断言落在具体 check-id 行 + `checks.json` 头部字段**，⛔ 不得落在「返回值存在 / 总数变了」。

---

## 2. 本项目在这类审阅上栽过的坑（**请当作已知失效模式来找**）

1. **「锁绿 ≠ 锁真绑」**（栽过两次）：① W4 那条锁断言 `score_vs_gt is not None`，而判卷器**拒绝时产出的侧车也不是 None**
   ⇒ 锁一直绿着、判卷其实是拒的，施工自查 / 主控轻门 / GLM 对抗审**三道关全漏**；② r0 的 L-13 直接把 `None` 传给内部函数、
   **绕过 argparse 默认值** ⇒ 摘掉实现仍绿。**⇒ 断言必须落在 `checks.json` 头部字段与具体 check-id 的行上。**
2. **「边界写窄就被实现得同样窄」**：本项目连续多轮 REWORK 的共同结构 = 机制选对、边界留给施工方猜。
3. **「探针 ≠ 锁」**：临时脚本验过一次不等于回归里有守卫。
4. **「机制写了、没接线」**（第 N 次）：`provision_run_policy` 的 `context` 参数曾**全仓零生产调用者传参**。
   **凡看到新增参数 / 新增字段，先问「谁真的传它 / 谁真的读它」。**
5. **「raise ≠ 没落盘」**：fail-closed 若发生在写盘之后，磁盘上已留下可用产物 ⇒ 绕过它只需无视报错继续走。

---

## 3. 承重命题（**逐条给 成立 / 不成立 / 无法判定 + 证据**）

> 证据 = 文件:行 + 你实际跑的命令与输出摘录。**「读代码看起来没问题」不是证据。**

### T-1（最高权重）R1-5 的两条新锁**真绑**，且零连带

orchestrator 轻门已做过一次 neuter：把 `step_orchestrator.py` 里两处 `effective_run_policy(run_dir)` 换回 `RunPolicy()`
⇒ 恰好红 `test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers` 与
`test_R1_5_approve_geometry_uses_frozen_policy_check_headers` 两条、零连带，POST-RESTORE 全绿。

- **要你做的不是复述**：**对 `c56cbe1` 新增的每一条测试逐条做独立 neuter**（不止那两条），
  记录「摘掉哪一处实现 ⇒ 恰好红哪几条 / 有无连带 / 有没有摘掉实现仍然绿的假锁」。
- **重点找**：有没有**一处实现被多条锁覆盖，而其中某条锁其实空转**；
  有没有哪条锁的断言其实落在「字段存在 / 数量变了」而不是具体 check-id 行。

### T-2（最高权重）冻结政策真的覆盖了**整个 run**，不是又挑了几个点接上

派工单点名的面：`correction` / `modelling` / `grade`（`run_stage.py:254-309, 612-627, 1303-1323`）、
typed scoring 严格拒绝（`:1413-1420, 1455-1473`）、`record_baseline.py:485-503`、几何签字门（`step_orchestrator.py`）。

- **要你证伪的形式**：**找出一条仍在消费局部 / 默认 `RunPolicy` 而能影响判定的路径** —— 找到一条 T-2 即不成立。
  建议做法：全仓搜 `RunPolicy(` 构造点、`run_profile` / `capability_profile` 的所有读点，
  逐个判「它是不是判定面（改变阻断 / 改变判卷严格度 / 改变落盘记账）」。
- **施工方主动披露了一处判断取舍**（`submit_verdict` / `_verdict_outcome` 保留 `policy or RunPolicy()`，
  理由 = draw budget 与 reread availability 属运行期操作旋钮、不是档位政策）。orchestrator 已核实成立。
  **请你独立复核这条披露**，并回答：**同族的「运行期旋钮 vs 档位政策」还有没有别处被归错类**。

### T-3 `record_baseline.py` 这条记账路径不再自己重造档位

原缺陷：`record_baseline.py:485-503` 重新构造 `RunPolicy` 且 capability 默认 `rectangular`。

- **核**：现在它从哪里取？取不到时的行为是什么（**fail-closed 还是静默兜底**）？
  兜底是否会**冒充**一次正常的严格档记账（本项目底线：**legacy 默认档不得冒充 regression**）？
- **要你证伪的形式**：构造一个 run 目录，使 baseline 记账落盘的档位与 gate① 实际执行的档位**不一致**。

### T-4 `GeometryApproval` 的加固是真加固，不是新的一层未验证记录

R1-5 超出要求，给 `GeometryApproval` 钉上 `run_policy_source` / `run_policy_legacy_defaulted` /
`run_profile` / `capability_profile` ⇒ 「一次人工签字绑定它是在哪个档位下签的」。

- **核**：这四个字段**有没有消费者**（谁读它、读了会不会改变任何判定）？
  还是又一条「记录了就以为守住了」的**第二类假锁**（= 本项目已犯过的形状）？
- **同族问题**：一份**旧的、无这四个字段的**已签字 approval 进来时会怎样？
  会被当作合法的 regression 签字吗？（**legacy 不得冒充严格档**。）
- **⚠️ 本条允许你判「机制正确但缺消费者 ⇒ 登记为债」**，但**必须写清楚它现在挡不住什么**。

### T-5 与另六条（GLM 侧）的**接缝**没有留下裂缝

R1-5 依赖 R1-1（`flow`/`run` 入口冻结）落下的 `_run/run_policy.json`。

- **核**：`effective_run_policy(run_dir)` 在**政策文件缺失 / 损坏 / 被手工改过**时的行为分别是什么？
  三种情况是否可区分？会不会静默回落到 `exploratory` 并**看起来像一次正常执行**？
- ⚠️ **只核接缝行为，不要去审 R1-1…R1-7 的实现本身**（那是路 2 的范围）。

### T-6 边界合规（逐条核，给证据）

① 未 push；② `gt/**` 与 sm24 `testdata_prompt.json` **零字节改动**；
③ 真实 sm24 / sm21 manifest 的 `content_sha256` 逐字不变（**已签字 GT 信任链，不可协商**）；
④ 未读 GT 答案；⑤ 未顺手做批 C / 批 D / R1.5；⑥ 欠规格边界有没有被自行降级为假设（施工方报 none —— 请挑战它）。

### T-7 复杂度可扩展性（不变量 #6）

冻结政策与 `GeometryApproval` 的 schema，在**非方形 / 退台 / 挑空 / 中庭**的将来会不会成为要推翻的假设？
**只要判断，不要求设计。**

---

## 4. 你可以做 / 不可以做

- ✅ 读全仓任意源码与测试；跑测试；读 `AI_agent/` 下任意文档与 git 历史。
- ✅ **破坏性探针（neuter 验锁）一律只在 `/tmp` 的克隆里做**：
  `git clone --local --no-hardlinks /workspaces/EnergyPlus-Agent-dev <你的 scratchpad>/probe`，在克隆里改、在克隆里跑。
- ⛔ **不改主工作树、不提交、不 push、不 stash**。发现要改的地方，写进审阅报告让施工方改。
- ⛔ **主仓库里只跑只读 git 命令**（`git log` / `git show` / `git diff`）；
  ⛔ **不要在主仓库跑 `git status`**（会抢 index 锁，本项目已因此卡死过一个施工席）。
- ⛔ **不读 GT 答案数字**（`case_tests/test_baseline/gt/`；铁律：gate①/执行器绝不 import，人与 gate② judge 才可读）。
- ⛔ 不要扩范围到批 C / 批 D / R1.5 / 路 2 的六条。

**跑测纪律**：`pytest -q -n 4`（⛔ 不许 `-n auto`〔内存〕，⛔ **永远不许加 `-m` 过滤**）。
基线 = **2089 passed + 10 xfailed 零红**。⚠️ 另一个审阅子代理可能同时在跑测，故限 `-n 4`。

---

## 5. 交付

报告落 **`AI_agent/logs/reviews/verdict/2026-08-03_reading_ruler_r1_crossreview_claude_r15.md`**，含：

1. **总判定**：APPROVE / APPROVE-WITH-CHANGES / **REWORK**（BLOCKER / MAJOR / MINOR / NIT 计数）。
2. **T-1…T-7 逐条**：成立 / 不成立 / 无法判定 + 证据（文件:行、命令与输出摘录）。
3. **逐锁 neuter 台账**：锁名 → 摘掉哪一处 → 红了哪几条 → 有无连带 → 是否假锁。
4. **清单外自主发现**（本项目历轮的最大价值常来自清单外）。
5. **你证伪失败的尝试也要写** —— 这些是反向坐实，价值不低于发现缺陷。
6. 独立全量测试结果（命令 + 尾部输出原文）。

**orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑 neuter，是唯一权威门；你的报告不是终裁，但 BLOCKER 一律先信。**
