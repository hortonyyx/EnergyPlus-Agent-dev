# run_2026-08-13_post_blocker1_e2e — 工程缺陷勘察跑（⛔ 非成绩跑）

**测什么**（用户 2026-08-13 定）：拿之前好的识图产物，跑后面完整的端到端，回答**「工程上还差哪些问题」**。
口径与冻结条件见同目录 [run_config.yaml](run_config.yaml)（先于 provision 落盘）。

- **基线**：`da2245d`（今日三摊：F-22 BLOCKER-1 印章→proof · MAJOR-C1 标注语义 · F-24/A1/F-25）
- **识图**：`run_2026-08-11_continuous_e2e/0_reading` **逐字节复制**（6 个 view + summary，`cmp` 逐件校验一致）
- **命令**：`flow sm21_anchor run_2026-08-13_post_blocker1_e2e --from 1_correction --judge off --geometry auto --with-ep`
- **真实退出码 = 30**（⚠️ 后台通知里的 "exit code 0" 是外层壳的，不可信）；**重跑下游一次，退出码仍 30**

## 结果一览

| 段 | 结果 |
|---|---|
| 1_correction | ✅ deterministic_pass（footprint `[0,15]×[0,8]` = 外皮框，F-17 后的正确形态）|
| 2_modelling | ✅ 100 面 / 15 窗 / 14 区 |
| 3_split_pairing | ✅ gate① 零 block 零 flag，几何门 auto 签发 |
| 4_mep | ⚠️ **attempt 001 崩、002 过**（见下 §2）|
| 5_intakeoutput | ✅ |
| 下游 9 subagent | 🔴 **确定性崩在 `surface` 节点**（见下 §1）⇒ **无任何 EP 产物** |

## 1. 🔴 下游 `surface` 节点确定性崩溃（当前唯一的真断链）

节点序 `construction → surface → fenestration`；日志打印的是**已完成**节点，最后一个是 `construction`
⇒ 崩在 **`surface`**（要建 100 个面，工具调用最密集的一段）。

```
✗ EP downstream run failed: BadRequestError: Error code: 400 -
  "An assistant message with 'tool_calls' must be followed by tool messages responding to
   each 'tool_call_id'. (insufficient tool messages following tool_calls message)"
```

- **确定性**：连跑两次，**逐字同一错误、同一位置**（⛔ 不是抽风）。
- **归因（已机械核实）**：本日提交**下游一行没动**（`da2245d` 只碰 correction/judge/execution/scripts）；
  `src/agent/graph.py` / `src/agent/react.py` 上次改动是 `299149c`。且**同样的输入 08-11 跑通过**
  ⇒ 变化来自仓库之外（provider 行为）或长循环下的既有脆弱点。
- **⛔ 更要紧的是没有韧性**：4_mep 有**段级重试**（001 崩→002 过，自愈）；
  下游那一整段**没有等价的重试/降级**，一个 provider 400 直接让整条 flow 退 30、EP 零产物。
- react 循环本身用 LangGraph 标准 `ToolNode` 且 `parallel_tool_calls=False`
  ⇒ 「N 个调用少回结果」的不变量在正常路径上是维持的 ⇒ **机制尚未定位，不得声称已定位**。

## 2. ⚠️ 4_mep attempt 001：裸 Python 异常被当成校验结果

```
mep.idf_parse  error  MEP fragment parse failed:
  TypeError: unsupported operand type(s) for //: 'int' and 'NoneType'
```

解析器崩在整除上（某字段为 `None`），报成 `status=error` 而**不是结构化拒绝**。
attempt 002 通过 ⇒ **自愈掩盖缺陷**：在一次「全绿」的跑里没有人会看见它。
（同族：F-17 收口时把 cell 环失败改走结构化拒绝。）

## 3. ⚠️ gate① 报告声称的档位与本 run 冻结的策略不一致，且两者之间没有绑定

- `_run/run_policy.json`：**`run_profile: "exploratory"`, `source: "structured_config"`**（我的声明被正确读到并冻结）
- 但逐份 gate① 报告：`1_correction/002`（方位增强那次写入）与 `3_split_pairing` 写的是 **`regression`**，其余写 `exploratory`
- **且每一份报告的 `run_policy_sha256` / `run_policy_source` 都是 `null`** ⇒ 报告没有绑定策略

**三个 run（08-09 / 08-11 / 08-13）模式完全一致** ⇒ **结构性、早已存在，⛔ 不是今天引入**。
为什么要紧：两档严格度不同（exploratory 警告续行 / regression 失败即停）
⇒ **「这两段实际按哪一档跑的」今天无法从产物回答**。

## 4. ✅ 几何这条线是干的（顺手第三次证实一条判据）

与 08-11 那份对账：**460 个顶点（400 面 + 60 窗）逐位同序完全相同**，面/窗/区计数全同、`geometry_contract` 全同。
`geometry_checkpoint_digest` **不同**（`6e767d58…` vs `3409f90b…`），唯一原因 =
校正 LLM 把两个房间从 `Conference` 改叫 `Meeting`。
⇒ **判几何必须比顶点，digest 不是几何判据**（本条按 run_config 事先写好的验收条件执行）。

## 5. ✅ 摊 A 的「正向」证据首次在真实 run 上拿到（sol 第四轮点名要的）

- 契约 `correction_b5_orientation_v1`（= 所有真实 run 用的那个）
- accepted 账本 artifact 集合出现**第 7 件 `deterministic_core_proof`**
- 判卷侧车：**`declared=True, trusted=True`**，identity = `outer_skin_exterior_centerline_interior`
- `scorer_schema = "11"` ⇒ **本仓第一份新版判卷缓存**

## 6. ⚠️ 而这第一份缓存正好落在 sol 刚发现的 fail-open 上

sol 第四轮反例 A：先有 `trusted=True` 缓存 → 删掉 proof → 解析器明确返回「无 proof」→
**缓存照样输出 `trusted=True`、判卷函数零调用**（缓存判据在 proof 解析**之前**）。
⇒ 本 run 之后，这个洞从「结构性缺口」变成**盘上真实存在的一份可命中缓存**。

## 7. 摊 C 观测量在真实跑上如实说了「不知道」

`1_correction/annotation_basis.json`：四条边各 `Δ=0.120 m`，全部
`reconcilable_nonzero_displacement`（「非零且容差内，标注法未知」）。
`0.12 → 0.0` / `14.88 → 15.0` / `0.12 → 0.0` / `7.88 → 8.0`。

⇒ 与「标注/墙厚/出模」专项直接相接：**产物里那个 identity 串已经写着
`outer_skin_exterior_centerline_interior`（= 外墙按外皮、内墙按轴线）**，
也就是**约定已经作为一个名字存在**，只是**没有墙厚数值、也没有任何东西校验它**。

## 口径限制

- ⛔ 本 run 的判卷结论**不得当作签收依据**：sol 第四轮 = CHANGES REQUIRED，`BLOCKER-1` 仍开
  （run-local 可变账本不算外部信任根 + 上述缓存 fail-open）、`MAJOR-F24` 仍开。
- ⛔ 本 run 未记正式成绩（`record: false`），识图为复用 ⇒ **不产生任何识图成绩**。
- ⛔ 下游崩溃的**机制未定位**（只定位到节点与确定性）。
