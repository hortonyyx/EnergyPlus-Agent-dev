# R1 批 B · r1 交叉对抗审两路 · orchestrator 裁定 + r2 必修清单

- **日期**：2026-08-03
- **裁定方**：orchestrator（端到端主控）
- **输入**：[路 1 · R1-5（terra 产出）](../verdict/2026-08-03_reading_ruler_r1_crossreview_claude_r15.md) REWORK（0 B / 3 MAJ / 3 MIN / 2 NIT）·
  [路 2 · GLM 六条 + P-3…P-9](../verdict/2026-08-03_reading_ruler_r1_crossreview_claude_glm.md) REWORK 窄 r2（0 B / 2 MAJ / 3 MIN / 2 NIT）
- **两路均为 Claude 侧子代理（Opus 档）**，互不通气、范围互斥；施工方 = terra / GLM ⇒ 「谁写谁不批」满足。
- **两路各自独立全量**：**2089 passed + 10 xfailed 零红**（与 orchestrator 轻门逐数字一致）。

---

## 0. 总裁定

| 路 | 审阅席判定 | **orchestrator 裁定** |
|---|---|---|
| 路 1（R1-5，terra） | REWORK | **维持 REWORK**（MAJOR-1 / MAJOR-3 必修；MAJOR-2 降为债） |
| 路 2（六条，GLM） | REWORK（窄），并把一个裁定权交回 | **降为 APPROVE-WITH-CHANGES** —— F-1 属**已披露的欠规格边界**，**归责 orchestrator，不记施工席缺陷**；F-2 仍必修 |

**⇒ 合并成一次 r2**（4 条必修 + 2 条债），**不派两轮**。

---

## 1. ⭐ 先认自己的账：orchestrator 轻门有盲区

r1 轻门我判「锁真绑」，依据是把 `step_orchestrator.py` 两处 `effective_run_policy(run_dir)` 换回 `RunPolicy()`
⇒ 恰好红 2 条、零连带。**结论没错，但覆盖不全。**

**R1-5 的正文实现是 `run_stage.py:1689 _policy_with_frozen_tier`**（`cmd_run` / `cmd_judge` / `cmd_flow` 三个入口都调它），
而我 neuter 的那两处是**几何签字门**这个旁支。

**orchestrator 独立复现（`/tmp` 克隆，主工作树零改动）**：把该函数体改回一行 `return policy`（= 精确回退 r0 缺陷形态）
⇒ `test_run_stage_flow` + `test_reading_ruler_r1_batchB` + `test_orchestrate_baseline` + `test_step_orchestrator`
+ `test_isolation` + `test_execution_foundation` 六文件 **343 passed 零红**；
路 1 审阅席另在克隆内跑了两轮**全仓**对照，失败集合与基线逐条相同。
全仓搜索佐证：**零个测试引用 `_policy_with_frozen_tier`。**

**⇒ 教训（与项目已有两条同族，登记进 memory 与 plan.md）**：
> **neuter 选点必须覆盖「派工单正文点名的那处实现」，不能只挑自己最先想到的调用点。**
> 「摘掉 A 红了 ⇒ 锁真绑」只证明 A 有锁，**不证明这条派工单的正文有锁**。
> 本项目此前两条是「锁绿 ≠ 锁真绑」与「哨兵判据不得落在第一个匹配上」——**本条是第三条同族**。

---

## 2. 裁定一：路 2 的 F-1 属已披露边界 ⇒ 不记施工席缺陷

**事实**：施工执行日志 §6.5 末段逐字写着 ——

> **登记同族债（不越界）**：`_parse_capability_profile` 对非法值仍是 warn+None（capability 拼错也静默降
> rectangular），派工单 R1-2 只点 run_profile，故本条**只改 run_profile**。……**若 orchestrator 要求对称，
> r1 后续可扩到 capability。**

**orchestrator 独立核实属实**（`run_config.py:193-203` 仍 warn + `return None`；
`run_policy_freeze.py:209` 又 `capability_profile or "rectangular"` 兜一次静默默认）。

**⇒ 裁定**：施工席**停下上报、不越界**，正是派工单要的行为；**我没答复才是缺口**。
按本项目已有教训「**边界写窄就被实现得同样窄**」，责任在派工方。
**F-1 记为 orchestrator 漏答，不计入施工方评分；但它必须在 r2 修掉**（理由见下）。

**为什么不能只登记为债**：批 B 的立项事实是「声明 `regression` + `orthogonal_polygon`，实跑 `exploratory` + `rectangular`」——
**这两半都是本批要修的病灶**。r1 只修了前一半；**后一半（capability 拼错静默降 `rectangular`）原样存活**，
而 capability 决定 correction 走 v2 还是 v3 schema ⇒ **批 B 不修完它，立项理由就没兑现。**

---

## 3. r2 必修清单（4 条）

> 顺序 = 先小后大；每条都要**摘掉即红、零连带**的锁，**且锁必须走真实 CLI 入口**（r1 已达标，别退步）。

### r2-1（MAJOR，源自路 2 F-1）`capability_profile` 拼错一个字母仍静默降档

- **位置**：`src/agent/execution/run_config.py:193-203`（`_parse_capability_profile` warn + None）
  + `src/agent/execution/run_policy_freeze.py:209`（`capability_profile or "rectangular"` 二次静默兜底）
- **要求**：与 r1 已落地的 `_parse_run_profile` **对称** —— present-but-invalid ⇒ **新 run provisioning fail-closed**；
  absent 仍 CLI/legacy 权威；历史只读 replay 不受影响。**两个字段从此同一条规格。**
- **锁**：走 `cmd_flow`，`capability_profile: orthogonal_polygone`（拼错）⇒ raise，且**冻结之前**失败
  （`_run/run_policy.json` 与 `run_manifest.json` 均不存在）；另配一条 absent 对照锁。

### r2-2（MAJOR，源自路 2 F-2）冻结记录的 `source` 是硬编码常量 ⇒ 「带来源」名存实亡

- **位置**：`src/agent/execution/run_policy_freeze.py:210`（`source="structured_config"` 写死）
- **事实（orchestrator 核实）**：全仓只可能产出两个值 —— 新 run 一律 `structured_config`、replay 一律 `legacy_defaulted`
  ⇒ **纯 CLI 冻结、以及被拼错降档的冻结，都会标成「来自结构化配置」**。
  连带使 R1-1b 的 `assert record.source == "structured_config"` **恒真**（= 一条空转断言）。
  二阶后果：纯 CLI 冻结的 run **永远不做漂移复验**。
- **要求**：`source` 必须真实反映来源（至少区分 `structured_config` / `cli` / 混合）；
  相应修正那条恒真断言；漂移复验的适用面按真实来源判。

### r2-3（MAJOR，源自路 1 MAJOR-1）R1-5 主干实现 `_policy_with_frozen_tier` 零回归守卫

- **位置**：`scripts/tool_scripts/run_stage.py:1689`（定义）+ `:1946` / `:2046` / `:2143`（三个入口）
- **失败场景**：任何人把它改回 `return policy`，correction / modelling / grade / typed-scoring **立刻全退回读 CLI 档**
  （= r0 被判 MAJOR 的原状），而**全仓一条测试都不会红**。
- **要求（派工单 §3 原文，本条只是它没被执行）**：补一条走**真实 CLI 入口**（`cmd_run` 或 `cmd_flow`，
  ⛔ 不许直接调内部函数绕过 argparse）的锁：构造冻结档 = `regression`/`orthogonal_polygon`
  而 CLI/`run_config` 给 `exploratory`/`rectangular` 的 run，断言落盘 `checks.json` **头部字段**
  + **某条只在严格档才出现的具体 check-id 行**。**摘掉 `_policy_with_frozen_tier` 必须红。**
- ⚠️ **本条是纯补锁，不改生产码行为**（路 1 已证实实现本身是对的、四个被点名的面确实都接上了）。

### r2-4（MAJOR，源自路 1 MAJOR-3）`context` 已成判定面，但漂移面没跟着扩 + 免责声明变成假注释

- **位置**：`src/agent/execution/run_policy_freeze.py:22-30`（G-4 免责声明）
  vs `:292-294, 326-335`（`effective_run_policy` 消费 context）vs `src/agent/execution/validation_run.py:120`
- **事实（orchestrator 核实）**：G-4 那段注释写着把 context 排除在漂移检测外的**理由**是
  「they do not affect reading-check blocking」；R1-5 之后 `effective_run_policy` 把 `require_ep` 喂进 `validate_case`，
  **它会增删一条 fail-closed 的必需件（`downstream.build`）** ⇒ **该理由已不成立**。
  路 1 审阅席在 `/tmp` 实跑过篡改：改 `run_policy.json` 的 context 值再**自行重算 `content_sha256`**（该哈希是 payload 自身哈希、
  不绑外部信任根）⇒ **校验与漂移复核照常通过**，于是 baseline 头部显示严格档、却漏记了阻断行。
  ⚠️ 精确划界：几何签字门**不受影响**（只读 `geometry_digest` / `geometry_approved`）。
- **要求**：**(a) 把 context 里真正是判定面的项纳入 hash / 漂移复核**，或 **(b) 把 `effective_run_policy` 对 context 的消费收回**
  （只从冻结档位 + 当次显式入参推导）。**⛔ 不接受只改注释的 (c)** —— 它只解决误导、不解决可篡改。
  施工方**选哪条要在执行日志里给理由**。

---

## 4. 登记为债，不在 r2 修（2 条）

- **D-2（路 1 MAJOR-2）`GeometryApproval` 四个新字段 = 零消费者 + 零锁**：删掉四行全仓零红。
  ⚠️ **它没有被声称成阻断项**（CLAUDE.md 措辞「事后可审」准确）⇒ **是真债，不是假锁**。
  出路二选一：补一条回归锁，或补消费者（`record_baseline` / `cmd_flow --record` 在
  `approval.run_profile != frozen.run_profile` 时拒绝或落 flag）。**归 R2 一并处理。**
- **D-3（路 2 F-3）L-13 的 `run_profile_not_declared` 在生产不可达**
  （`_resolve_run_profiles` 恒返回非 None），**且该锁一字未改、仍直喂 `None`**
  ⇒ r1 的「锁必须走真实入口」在这一条上**没有回溯适用**。**不构成新缺陷（是 r0 遗留），但要在 R2 前清掉。**

**其余 MINOR / NIT**（路 1 MINOR-1…3 + NIT-1/2；路 2 F-4…F-7）**全部转 R2 backlog**，逐条见两份审阅报告，本单不复述。

---

## 5. 两路的反向坐实（不是没发现问题就等于没价值）

- **路 1**：R1-5 交付的 **4 条锁全部真绑、零假锁、零连带**，断言落在 `downstream.build` 具体 check-id 行与 `CheckReport` 头部字段上
  ⇒ **明显吸取了「非 None ≠ 成功」那条教训**；且**四个被点名的面确实全接上了**，审阅席证伪失败。
  T-3（legacy 不能冒充 regression）、T-7（无烤死假设）成立。
- **路 2**：**11 个实现钩子逐一 neuter，全部「摘掉即红、零假锁」，与施工席自报逐条吻合零夸大**；
  R1-1 / R1-2 / R1-7 的锁**真走 `cmd_flow`** ⇒ **r1 派工单 §3「锁必须走真实入口」这条纪律，施工席这次做到了**。
  **P-3 真跑通过**（真实 `load_score_view_bindings` + sm24 签字 GT ⇒ 出分正常，已签字 GT 信任链未被打穿）——
  这正是上一轮「三方都验了机制、没人真跑一次」那个坑，这次**跑了**。
  G-3 / G-4 / G-6 / P-4 / P-5 / P-6 / P-9 成立，其中 G-4（四态不折回 bool）与 P-6（产品内容不能决定考卷）
  是审阅席**证伪失败**的两条 —— 反向坐实。

---

## 6. 边界与合规（两路交叉核实一致）

| 项 | 结论 |
|---|---|
| `gt/**` 与 sm24 `testdata_prompt.json` 零字节改动 | ✅ 两路独立确认 |
| 未读 GT 答案 | ✅ |
| 真实 sm24 / sm21 manifest `content_sha256` 逐字不变 | ✅（P-3 真跑验证） |
| `stroke_dimension_consistency` 未被升硬门 | ✅（七个 commit 完全没碰该文件） |
| 批 C 未顺手做 | ✅（半截仍在 `git stash`） |
| push | ✅ `HEAD == origin`，最后一次推 = **orchestrator 08-03 收工 ritual 整支推**，非施工席自推 —— **orchestrator 在此认领** |

---

## 7. 下一步

1. **r2 = 上述 4 条**（施工席待用户拍板；**⛔ 谁写谁不批 —— r2-3 / r2-4 源自 terra 的 R1-5，r2-1 / r2-2 源自 GLM 的六条**）。
2. r2 落库后 ⇒ orchestrator 轻门（**这次的 neuter 选点必须包含派工单正文点名的实现**）+ 交叉审。
3. **之后才是批 C**（渲染 / 命名 / 像素预算）。
4. **⛔ 约束不变**：批 A/B/C 三批全绿之前，不得发布任何识图分数或「识图变好/变坏」的结论。
