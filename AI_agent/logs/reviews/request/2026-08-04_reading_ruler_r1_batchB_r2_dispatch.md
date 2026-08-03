# R1 批 B · r2 返工派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-04（北京时间）
- **派工方**：orchestrator（端到端主控）
- **施工席**：**GLM**（`scripts/glm_code.sh`），额度 ~02:10 CST 复位；**非高峰档（2x）**，别拖到 14:00–18:00（3x）
- **前置状态**：批 B r1 = `48e41b6`（HEAD，已推 origin）。全仓 **2089 passed + 10 xfailed 零红**
  （orchestrator 轻门 + 两路交叉审各自独立复跑，三方逐数字一致）
- **性质**：**返工轮（r2）**。[批 B/C 原派工单](2026-08-03_reading_ruler_r1_batchBC_dispatch.md) ·
  [裁定](2026-08-03_reading_ruler_r1_batchBC_ruling.md) · [r1 返工单](2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md)
  的**全部边界与禁止清单继续有效，本单只加不减**。
- **上游裁定（冲突处以它为准）**：[交叉审两路裁定 + r2 清单](2026-08-03_reading_ruler_r1_crossreview_ruling_and_r2.md)

---

## 0. 先说清楚三件事

### ① 你的 r1 做得是合格的，本单不是「又没修好」

两路交叉对抗审（均为 Claude 侧 Opus 档，互不通气）对你 r1 六条的结论是：

- **11 个实现钩子逐一 neuter，全部「摘掉即红、零假锁」，与你执行日志的自报逐条吻合、零夸大**；
- **R1-1 / R1-2 / R1-7 的锁真的走了 `cmd_flow`** ⇒ **r1 派工单 §3「锁必须走真实 CLI 入口」这条纪律，你这次做到了**
  （对照 r0：13 条锁无一走 `cmd_run`/`cmd_flow`）；
- G-3 / G-4 / G-6 / P-3 / P-4 / P-5 / P-6 / P-9 全部成立，其中 **G-4（四态不折回 bool）与 P-6（产品内容不能决定考卷）
  是审阅席证伪失败**的两条 —— 反向坐实。

**⇒ 你那一路的判定已由 orchestrator 从 REWORK 降为 APPROVE-WITH-CHANGES。**

### ② r2-1 这条是 orchestrator 欠你一个答复，不是你的缺陷

你在执行日志 §6.5 末段主动写了：

> 登记同族债（不越界）：`_parse_capability_profile` 对非法值仍是 warn+None（capability 拼错也静默降 rectangular），
> 派工单 R1-2 只点 run_profile，故本条只改 run_profile。……**若 orchestrator 要求对称，r1 后续可扩到 capability。**

**你停下上报、不越界，正是派工单要的行为；我没答复才是缺口。** 现在答复：**要求对称，见 r2-1。**

### ③ 本单四条里有两条来自另一位施工席（terra）写的 R1-5

`r2-3` / `r2-4` 修的是 terra 那一条的缺口，**不是你的活出了问题**。派给你是因为「返工全部归口一席」，别误判成自己上一轮漏做。

---

## 1. ⛔ 必修（4 条，全部由 orchestrator 独立核实属实）

> **顺序：r2-1 → r2-2 → r2-3 → r2-4**（先小后大）。做不完就**停下上报**，不要硬塞。

### r2-1（MAJOR）`capability_profile` 拼错一个字母仍静默降 `rectangular`

**这是批 B 立项事实的另一半。** 立项那句话是：「声明 `regression` + `orthogonal_polygon`，实跑 `exploratory` + `rectangular`」。
r1 修好了前一半（`run_profile` 拼错 ⇒ fail-closed），**后一半原样存活**。

- `src/agent/execution/run_config.py:193-203`（`_parse_capability_profile`）：非法值仍 `warnings.warn(...)` + `return None`
  ⇒ 落回 CLI/默认；
- `src/agent/execution/run_policy_freeze.py:209`：`capability_profile or "rectangular"` **又静默兜一次默认**。

**后果**：`capability_profile: orthogonal_polygone`（拼错一个字母）⇒ 静默降 `rectangular`，
而冻结件照样标 `source=structured_config` / `legacy_defaulted=false` ⇒ **看起来像一次正常的严格档冻结**。
**且 capability 决定 correction 走 v2 还是 v3 schema** ⇒ 影响面不止判卷严格度。

**要求**：与你 r1 已落地的 `_parse_run_profile` **完全对称，同一条规格**——
present-but-invalid ⇒ **新 run provisioning fail-closed（raise）**；absent（`value is None`）⇒ 仍返回 `None`、CLI/legacy 权威；
**历史只读 replay 不受影响**（`_declared_policy` 自读 YAML 的那条路照旧容忍并标 legacy）。
`run_policy_freeze.py:209` 那个 `or "rectangular"` 兜底要一并处理：**新 run 不得靠它兜**（legacy replay 可保留）。

**锁**（走真实 `cmd_flow`）：① `capability_profile: orthogonal_polygone` ⇒ raise，且失败发生在**冻结之前**
（断言 `_run/run_policy.json` 与 `run_manifest.json` **都不存在**）；② absent 对照锁 ⇒ 不 fail-closed、CLI 兜底冻结成功。
**形态照抄你 r1 给 `run_profile` 写的那两条即可**（那两条审阅席验过是真锁、走真入口）。

### r2-2（MAJOR）冻结记录的 `source` 是硬编码常量 ⇒ 「带来源」名存实亡

`src/agent/execution/run_policy_freeze.py:210`：`_build_record(..., source="structured_config", ...)` **写死**。

**orchestrator 核实**：全仓只可能产出两个值 —— 新 run 一律 `structured_config`、replay 一律 `legacy_defaulted`（`:259`）
⇒ **纯 CLI 冻结（`run_config.yaml` 里根本没声明、靠 `--run-profile` 兜的那种）也会被标成「来自结构化配置」**；
被拼错降档的冻结同理。

**三个后果**：
1. 原派工单 §2.1 #4 要的「冻结记录**带来源**」变成一个常量 ⇒ 规格未实现；
2. 连带使 R1-1b 的 `assert record.source == "structured_config"` **恒真** = 一条空转断言；
3. **二阶后果**：纯 CLI 冻结的 run **永远不做漂移复验**（漂移复验按来源判适用面）。

**要求**：`source` 必须真实反映来源，**至少区分**「结构化配置声明」/「CLI 兜底」/「两者混合」三态
（命名你定，写进执行日志）；同步修正那条恒真断言；**漂移复验的适用面按真实来源判**。

**锁**：一条走真实 CLI、`run_config.yaml` **不声明** run_profile/capability、只用 `--run-profile` 的 run
⇒ 断言冻结件 `source` **不是** `structured_config`；另一条声明齐全的 ⇒ 断言是结构化来源。**摘掉实现必须红。**

### r2-3（MAJOR）R1-5 主干实现零回归守卫 —— **纯补锁，不改生产码行为**

`scripts/tool_scripts/run_stage.py:1689 _policy_with_frozen_tier`（定义）+ `:1946`(cmd_run) / `:2046`(cmd_judge) / `:2143`(cmd_flow)。

**这是 R1-5 派工单的正文实现**（「让冻结的档位成为整个 run 的档位」），但 **R1-5 交付的两条锁钉的是几何签字门与 baseline 记账这两个旁支**。

**已证实**：把函数体改回一行 `return policy`（= 精确回退 r0 缺陷形态）⇒
**orchestrator 独立复现：六个最相关测试文件 343 passed 零红**；审阅席另在克隆内跑两轮**全仓**对照，
**失败集合与基线逐条相同**；全仓搜索：**零个测试引用 `_policy_with_frozen_tier`**。

⚠️ **实现本身是对的**（审阅席证伪失败：四个被点名的面 correction / modelling / grade / typed-scoring 确实全接上了）。
**⛔ 本条不许改生产码逻辑，只补锁。**

**锁（走真实 CLI 入口，⛔ 不许直接调内部函数绕过 argparse）**：
构造一个**冻结档 = `regression` / `orthogonal_polygon`、而 CLI 与 `run_config` 当次给 `exploratory` / `rectangular`** 的 run，
经 `cmd_run` 或 `cmd_flow` 跑到一个会落 `checks.json` 的阶段，断言：
① 落盘 `checks.json` **头部字段** = `regression` / `orthogonal_polygon`（不是 CLI 那档）；
② **某条只在严格档才出现的具体 check-id 行**（disposition = block）。
**摘掉 `_policy_with_frozen_tier` 必须红**，且要在执行日志里如实登记 neuter 结果。

### r2-4（MAJOR）`context` 已成判定面，但漂移面没跟着扩；且 G-4 免责声明已成假注释

- `src/agent/execution/run_policy_freeze.py:22-30`（G-4 免责声明）**明文写着**把 context 排除在漂移检测外的**理由**是
  「they do not affect reading-check blocking」；
- 但 R1-5 之后 `effective_run_policy`（`:292-294, 326-335`）**从 context 取** `confirmation_policy` / `judge_enabled` /
  `validation_scope` / `require_ep`，而 `src/agent/execution/validation_run.py:120` 里 **`require_ep` 决定
  `downstream.build` 是否成为 fail-closed 的必需件** ⇒ **那个理由已经不成立**。
- **已实跑证实**：把 `<run>/_run/run_policy.json` 里 `context.require_ep.value` 由 `true` 改成 `false`
  **并自行重算 `content_sha256`**（该哈希是 payload 自身的哈希、不绑任何外部信任根）⇒ **校验与漂移复核照常通过**
  ⇒ baseline 记账**静默不再把缺失的 EP 产物记成阻断行**，而头部仍显示 `regression`。
- ⚠️ **精确划界**：几何签字门**不受影响**（只读 `geometry_digest` / `geometry_approved`）。**受影响的只有 baseline 记账这一面。**

**要求 —— 二选一，⛔ 不接受「只改注释」**：
- **(a)** 把 context 里**真正是判定面**的项纳入 `policy_hash` / 漂移复核；
- **(b)** 把 `effective_run_policy` 对 context 的消费**收回**，只从冻结档位 + 当次显式入参推导。

**⚠️ 选哪条要在执行日志里给理由**（这是本单唯一需要你做判断的地方）。
无论选哪条，`:22-30` 那段注释都要改写成实况 —— **一个模块的不变量声明变成假的，比字段本身可篡改更危险**。

**锁**：断言「篡改 context 判定面字段并重算哈希 ⇒ 被拒 / 或不再影响判定」，落在具体行为上，不得落在「字段存在」。

---

## 2. 锁的纪律（**r1 你做到了，r2 别退步**）

1. **锁必须走真实入口**：r2-1 / r2-2 / r2-3 的锁**必须经过 argparse / CLI 命令函数**。
   ⛔ 不许像 r0 的 L-13 那样把 `None` 直接喂内部函数 —— 那条锁绕过了真实 CLI，所以**绿着而缺陷还在**。
2. **断言落在具体 check-id 行 + `checks.json` 头部字段**，⛔ 不得落在「返回值存在 / 总数变了 / 字段非空」。
3. **每条都要「摘掉即红、零连带」**，逐条做 neuter 自查并**如实登记**（摘掉哪一处 ⇒ 恰好红哪几条 ⇒ 有无连带）。
   ⚠️ **「锁绿」≠「锁真绑」**；**「全仓 2089 绿」不构成任何锁真绑的证据**（本轮已被三处零锁实现证明）。
4. **⭐ 本轮新增纪律（orchestrator 自己栽的跟头，写进来让你避开）**：
   **neuter 选点必须覆盖「派工单正文点名的那处实现」**，不能只挑自己最先想到的调用点。
   「摘掉 A 红了 ⇒ 锁真绑」只证明 A 有锁，**不证明这条派工单的正文有锁**。

---

## 3. 边界（继续有效，逐条不得违反）

- ⛔ **不 push**。⛔ **不碰 `case_tests/test_baseline/gt/**` 与 sm24 `testdata_prompt.json` 任何字节**。⛔ **不读 GT**。
- ⛔ **不原地改历史 manifest / attempt / GT**；⛔ 无「当前样例转绿」式验收；⛔ 不从产品 `dimensions[]` 反推。
- ⛔ **不把 `stroke_dimension_consistency` 升硬门**（该文件本轮完全不该被碰）。
- ⛔ **不顺手做批 C / 批 D / R1.5**。批 C 的半截 28 行仍在 `git stash`（`batchC-wip-render-pixel-budget`），**本轮别取**。
- ⛔ **不动 `AI_agent/` 下除你自己执行日志以外的任何管理文档**（CLAUDE.md / plan.md / decision_log.md 归 orchestrator）。
- **再遇欠规格边界，停下上报** —— 前三次你都做对了，**r2-1 正是那样被接住的**。

---

## 4. 交付

- **执行日志**：续写 `AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md` 的新 **`## 7. r2 返工`** 段
  （⛔ 别覆盖 r0 / r1 的记录）。每条含：设计 → 改动清单（文件:行）→ **neuter 自查** → 受影响子集结果 → 缺口/披露。
- **做完一件存一件、先落骨架再补、每修完一条即本地 commit**（message 仿 `8.04_R1BatchB_r2_<条目>_<英文标签>`）。
  **⚠️ 额度中断过两次，攒着写 = 白做。**
- **跑测**：中间轮跑受影响子集；**交付前跑一次全仓 `pytest -q -n 6`**
  （⛔ 不许 `-n auto`〔内存〕，⛔ **永远不许加 `-m` 过滤**）。**基线 = 2089 passed + 10 xfailed 零红。**
- **完工信号**：执行日志 `## 7` 段写完 + 本地 commit 落完 + 全仓结果贴进日志。

**下一步（你不用管，告知以便理解定位）**：orchestrator 轻门（独立全量 + 亲核 diff + **独立复跑每一条 neuter，
且选点必须覆盖本单正文点名的实现**）→ Claude 侧子代理交叉对抗审（本批不再启 GPT 侧）→ 之后才是批 C。
