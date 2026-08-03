# R1 批 B · r2c 收尾派工单（施工 = GLM · 全部是锁强度，不改生产码行为）

- **日期**：2026-08-04（北京时间 06:00）
- **派工方**：orchestrator · **施工席**：GLM（同席位第三轮）
- **前置**：HEAD `26a14cb`，全仓 **2095 passed + 10 xfailed 零红**（orchestrator 轻门 + Claude 侧交叉审各自独立复跑，三方一致）
- **上游**：[交叉审报告](../verdict/2026-08-04_reading_ruler_r1_batchB_r2_crossreview_claude.md)（**判定 = APPROVE-WITH-CHANGES，本单只收其 findings**）·
  [轻门](../verdict/2026-08-04_reading_ruler_r1_batchB_r2_orchestrator_lightgate.md) ·
  [r2b 裁定](2026-08-04_reading_ruler_r1_batchB_r2b_ruling_and_dispatch.md)（判据与边界继续有效）

---

## 0. 先说清楚：**r2/r2b 的生产码零缺陷，本单四条全是「锁绑的不是它自称绑的东西」**

交叉审逐条证伪失败四次（删除安全 / judge 路无新问题 / 篡改面真消失 / 三态无洞），
**反向坐实你 r2+r2b 的实现是对的**。本单只修**锁强度**与**注释真实性**。
⛔ **不改任何生产码行为**（F-1 那两行是「取值来源」的修正，不改对外行为）。

---

## 1. ⛔ 必修（4 条）

### r2c-1（MAJOR）记账那条锁绑的是调用方开关，不是冻结档位

- **位置**：`tests/test_orchestrate_baseline.py:44-83`（锁）+ `scripts/tool_scripts/record_baseline.py:539-545`（取值）
- **实证**：把 `record_baseline` 的 `effective_run_policy(...)` 换回自搓 `RunPolicy(require_ep=require_ep)`
  ⇒ **全仓 2095 条零红**（orchestrator 与交叉审各自独立复现）。
  **根因**：`baseline["run_policy"]` 那五个字段**全部取自 `frozen`**（`resolve_frozen_run_policy` 那一行），
  与喂给 `validate_case` 的 `policy` **零数据依赖** ⇒ 头部断言证明不了「冻结档位真的进了校验」。
  而该锁的 docstring 正声称自己会红。
- **仓库里有正确写法作对照**：`src/agent/execution/step_orchestrator.py:494-495`（`approve_geometry`）
  把**溯源 ← frozen / 档位 ← effective** 拆开了。**照它改。**
- **要求**：① 让 `baseline["run_policy"]` 的**档位两字段取自 `policy`（effective）**、溯源字段仍取 `frozen`；
  ② fixture 里放一条**只在 `regression` 下阻断、`exploratory` 下不阻断**的检查，
  使「档位是否真的进了 `validate_case`」在 `baseline["blocking"]` 上可见；
  ③ **neuter 验证**：换回自搓 `RunPolicy` ⇒ **必须红**，并如实登记红了哪几条、有无连带。

### r2c-2（MINOR）两条 geometry 锁改写后丢光了 check-id 行断言

- **位置**：`tests/test_run_stage_flow.py:1084-1157`
- r2 派工单 §2.2 要的是「**头部字段 + 具体 check-id 行**」两者都断言；r2b 改写后**只剩头部字段**。
- **要求**：补回具体 check-id 行断言（形态照 R1-1c 那条），**不得**放宽既有断言。

### r2c-3（MINOR）一条恒真断言，分辨力 0

- **位置**：`tests/test_orchestrate_baseline.py:106-109`
- `require_ep=False` 下 `downstream.build` 对「冻结 regression」与「legacy」**都不出现** ⇒ 该断言两边都成立。
- **要求**：改成能分辨两者的断言（例如断言 legacy 侧的档位标记，而不是断言一个双方都没有的行）。

### r2c-4（MINOR）r2-1 新增的 `capability_profile_not_declared` 守卫零锁

- **位置**：`src/agent/execution/run_policy_freeze.py:168-173`
- 交叉审 neuter ⇒ 摘掉后 302 passed 零红；**且该守卫可达**
  （`provision_run_policy(..., capability_profile=None)` 实跑会抛）。你在 commit message 里已如实披露过。
- **要求**：补一条锁（直接调 `provision_run_policy` 即可，**本条不要求走 CLI** —— CLI 侧确实不可达，
  这是「防未来 resolver 回归」的结构守卫）。

---

## 2. 登记为债，⛔ 本轮不做

- **F-2**（`tests/test_orchestrate_baseline.py:160` 注释误述「frozen tier still consumed」）：**顺手改掉注释即可**，不必补锁。
- **N-1**（judge 路 run-policy 漂移在同一命令下两种出口：`return 2` vs traceback）：**前置存在、不计本批**，归 R2 backlog。
- **Q-8 措辞**（「外部信任根」判据把信任根钉死在单一文件，而仓库已有第二个信任根 = view manifest）：
  **归 orchestrator 改判据措辞**，不派你。

---

## 3. 纪律（不重复全文，只列硬的）

- 每条都要**摘掉即红、零连带**的锁，**neuter 自查如实登记**；**「全仓绿」不构成锁真绑的证据**。
- 断言落**具体 check-id 行 + `checks.json` / `baseline` 头部字段**，⛔ 不得落在「返回值存在 / 总数变了」。
- ⛔ 不 push · ⛔ 不碰 `case_tests/test_baseline/gt/**` 与 sm24 `testdata_prompt.json` · ⛔ 不读 GT ·
  ⛔ 不做批 C / D / R1.5 · ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档。
- 做完一件存一件、每条改完即本地 commit（`8.04_R1BatchB_r2c_<条目>_<英文标签>`）。
- 中间轮跑受影响子集；**交付前跑一次全仓 `pytest -q -n 6`**（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。
  **基线 = 2095 passed + 10 xfailed 零红。**
- **再遇欠规格边界继续停下上报** —— 你今晚两次都做对了，两次都改了 orchestrator 的题。

## 4. 交付

执行日志续写 `## 9. r2c（交叉审 findings 收尾）` 段（⛔ 别覆盖 `## 7` / `## 8`）。
完工信号 = 该段写完 + 每条已本地 commit + 全仓结果贴进日志。
