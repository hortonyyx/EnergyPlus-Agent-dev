# R1 批 B · r2-3 / r2-4 裁定 + r2b 续派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-04（北京时间 04:20）
- **裁定 / 派工方**：orchestrator（端到端主控）
- **施工席**：**GLM**（同一席位续做；02:12–03:03 那轮已落 r2-1 / r2-2）
- **前置状态**：HEAD `25b94dc`。全仓 **2094 passed + 10 xfailed 零红**（施工方自报，orchestrator 轻门待做）。
  **未 push · gt/testdata 零触碰 · 管理文档未动**（orchestrator 已只读核实）
- **上游**：[r2 派工单](2026-08-04_reading_ruler_r1_batchB_r2_dispatch.md) ·
  [交叉审两路裁定](2026-08-03_reading_ruler_r1_crossreview_ruling_and_r2.md) ·
  施工执行日志 `## 7`（[glm](../execution/2026-08-03_reading_ruler_r1_batchB_glm.md)）

---

## 0. 先说结论：你两条停下上报**都成立**，而且 r2-3 你还漏证了半条（对你有利）

**⭐ 停下上报是对的，不伪造锁是对的。** r2-1 / r2-2 已验收（轻门另做）。
下面两条裁定**推翻我自己 r2 派工单里的对应要求** —— 出题方的假设过时了，不是你没修好。

---

## 1. r2-3 裁定：**采纳 (iii)** —— 它确实是恒空操作，但处置不是「收口」，是**把假 docstring 变成真话**

### 1.1 orchestrator 独立核实：你的结论成立，且**判卷路那条腿你没证，我证了**

你论证的是 `cmd_run` / `cmd_flow` 上冗余。**我核实属实**（`run_stage.py:1958` 注释自陈
"provisioning happen here, BEFORE any attempt/manifest write."，`_manifest_for_attempts` 在
`_policy_with_frozen_tier` **之前** ⇒ 冻结档恒等于当次 resolved 档 ⇒ override 恒空）。

**但三个调用点里还有第三个 `cmd_judge`（`:2046`），你没分析。** 我查了，结论对你有利：
- `cmd_judge` 的 policy 来自 **`args.run_profile` / `args.capability_profile`**（argparse 默认 `exploratory` / `rectangular`），
  **完全不读 `run_config`**；且该路注释自陈 **"NEVER provisions"** ⇒ **没有 drift 门**。
  ⇒ 这条路本来是唯一可能带散度走到 `_policy_with_frozen_tier` 的路；
- **但它的 policy 只喂 `submit_verdict`，而 `submit_verdict` / `_verdict_outcome` 只读
  `policy.budget.per_stage_draws` 与 `policy.reading_runner_available`，从不读档位**
  （`step_orchestrator.py:241, 266, 410-411`；这一点在 r1 轻门里已核实、terra 也主动披露过）
  ⇒ **override 在这条路上同样是空操作。**

**⇒ 三处调用全是恒空操作。你的实证成立，我补齐了第三处。**

### 1.2 但它不是「无害的冗余防御」——它的 docstring 在**声称自己在守**

`run_stage.py:1690-1696` 逐字写着：

> "Replace the locally assembled tier with the run's frozen tier. …
> **every correction/modelling/grade/check consumer gets the frozen capability + run profile.**"

**这句话今天是假的**（它没有替换任何东西，因为传进来的已经是冻结档）。
**这与 r2-4 的 G-4 假注释是同一族**：**一个模块声称自己在守某个不变量，而它其实没在守。**
**⇒ 本项目今晚第二次撞见同一形状**（前面还有：自评字段 / CV 证据 / access_log / 立面方向 /
`_dimension_derived_refs` 被 `seen` 跳过 —— 这已是第七、第八次）。

### 1.3 ⛔ 必做（r2-3 改判为「改代码 + 引用既有锁」，**解除原派工单「不许改生产码」的限制**）

1. **`cmd_run` / `cmd_flow` 两处调用 + 函数本体：删除。**
   理由写进执行日志：**档位一致性由三处真守卫保证** ——
   ① R1-1 的 `_resolve_run_profiles`（config-wins）让 `_make_policy` 直接带冻结档；
   ② provisioning 的 drift 门（散度在到达此处前就 raise，你已实跑证明）；
   ③ R1-5 的 `effective_run_policy`（approve_geometry / record_baseline / baseline 记账那条线）。
2. **`cmd_judge` 那一处：不要删，改成「档位来自冻结记录」并内联。**
   现状是**用 argparse 默认档伪造了一个档位**（`exploratory` / `rectangular`），这条路又没有 drift 门。
   今天无害只因为**当前唯一消费者不读档位**——这是**运气，不是保证**。
   改法：judge 路的 policy 档位取自 `resolve_frozen_run_policy(run_dir)`（取不到 ⇒ 标 legacy），
   **并在注释里写明「本路当前无 tier 消费者，此处只保证来源正确」**。
3. **⛔ 不新增「断言未被消费的值」式的锁**（那正是本项目「记录了就以为守住了」的第二类假锁）。
   **登记为债 D-4**：若将来 judge 路出现读档位的消费者，**必须同时补锁**。写进执行日志。
4. **⭐ r2-3 的原始诉求落到这里**：核实并在执行日志**逐条引用** R1-1 那条既有锁
   （config 声明 `regression` ⇒ 经真实 CLI 落盘 `checks.json` 头部 = `regression` + 严格档 check-id BLOCK）
   **确实存在且真绑** —— **对它做一次 neuter 复跑并贴结果**。
   若发现它其实不绑，**停下上报**（那说明真正的守卫也是空的，性质立刻升级）。

---

## 2. r2-4 裁定：**采纳 (b)，并授权你改写受影响的 R1-5 锁**

### 2.1 判据（本项目已有、terra 立的、我在 r1 轻门批准过的那条线）

terra 在 R1-5 里主动划过一条线，我核实并采纳了：

> **draw budget 与 reread availability 属运行期操作旋钮，不是冻结的档位政策**，故不进冻结政策。

**你这次撞上的是同一条线的另一侧**：`require_ep` 来自命令行 `--with-ep`，
**`run_config.yaml` 里根本没有它** ⇒ **它没有外部信任根**。

**⇒ 统一判据（本裁定确立，写进执行日志）**：
> **只有在 `run_config.yaml` 里被声明的东西才有外部信任根，才配被冻结成「档位政策」并参与防漂移；
> 命令行传的运行期开关（`--with-ep` / draw budget / reread availability / judge 开关）属操作旋钮，
> 一律来自当次调用，不冻结、不据以判定。**

按此判据，**(a) 从一开始就不成立**（你的论证对：`content_sha256` 与 `policy_hash` 都能自行重算，
drift 的唯一外部根是 `run_config.yaml`，而 `require_ep` 不在其中 ⇒ 纳入哈希挡不住篡改，
只会制造「以为守住了」的第三层）。**这是我出题时的错误，不是你的。**

### 2.2 ⛔ 必做

1. **`effective_run_policy` 停止从 `context` 取判定值**（`require_ep` / `confirmation_policy` /
   `judge_enabled` / `validation_scope`）；档位仍取 `run_profile` / `capability_profile`（它们有外部根）。
   操作旋钮改为**由调用方按当次调用传入**。
2. **`context` 块保留为审计快照，但必须显式标注为非权威**（字段名或注释层面明确
   "audit snapshot — never authoritative, never consumed for decisions"）。
3. **改写 `run_policy_freeze.py:22-30` 的 G-4 免责声明**，写成实况 + §2.1 的判据。
   ⛔ 不许保留任何一句「这些开关不影响判定所以不进哈希」式的旧理由。
4. **✅ 明确授权：改写受影响的 R1-5 锁**（`test_R1_5_approve_geometry_*` /
   `test_R1_5_geometry_is_approved_*` 中断言「frozen context.require_ep=true ⇒ downstream.build 行」的部分）。
   **⚠️ 改写后必须仍然真绑**：把 `effective_run_policy` 的档位取值换回 `RunPolicy()` 全默认 ⇒ 这两条锁**必须仍然红**
   （这是 r1 轻门验过的性质，**不许在改写中丢掉**）。**neuter 复跑并贴结果。**
5. **补一条锁**：篡改 `_run/run_policy.json` 的 `context.require_ep` 并重算 `content_sha256`
   ⇒ **baseline 记账的阻断行不再随之改变**（= 篡改面消失）。**摘掉 (b) 的实现必须红。**

---

## 3. 纪律（继续有效，不重复原派工单全文）

- **锁必须走真实 CLI 入口**；断言落**具体 check-id 行 + `checks.json` 头部字段**；
  ⛔ 不得落在「返回值存在 / 总数变了 / 字段非空」。
- **每条 neuter 自查如实登记**（摘掉哪一处 ⇒ 恰好红哪几条 ⇒ 有无连带）。**「全仓绿」不构成锁真绑的证据。**
- **⭐ neuter 选点必须覆盖「本单正文点名的那处实现」**（这是 orchestrator 自己栽的跟头）。
- ⛔ 不 push · ⛔ 不碰 `case_tests/test_baseline/gt/**` 与 sm24 `testdata_prompt.json` · ⛔ 不读 GT ·
  ⛔ 不做批 C / D / R1.5 · ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档。
- **做完一件存一件、每条改完即本地 commit**（`8.04_R1BatchB_r2b_<条目>_<英文标签>`）。
- 中间轮跑受影响子集；**交付前跑一次全仓 `pytest -q -n 6`**（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。
  **基线 = 2094 passed + 10 xfailed 零红。**
- **再遇欠规格边界，继续停下上报** —— 你今晚两次都做对了，**两次都改了我的题**。

## 4. 交付

执行日志续写 `## 8. r2b（r2-3/r2-4 裁定后返工）` 段（⛔ 别覆盖 `## 7`）。
完工信号 = 该段写完 + 每条改动已本地 commit + 全仓结果贴进日志。
