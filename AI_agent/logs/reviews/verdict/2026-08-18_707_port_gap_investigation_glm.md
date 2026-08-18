# 排查报告 · 707 reading 模式移植缺口（GLM 独立排查）

**执行方**：GLM 席位（glm-5.3）　**日期**：2026-08-18
**派工单**：[`../request/2026-08-18_707_port_gap_investigation_glm.md`](../request/2026-08-18_707_port_gap_investigation_glm.md)
**性质**：read-only 排查（零仓库改动；破坏性/行为验证全部在 `/tmp/g707` 假 staging 中完成，已清理）
**参照系**：`1595981`(07-02 Sonnet) / `723b0f9`(07-07 Haiku) / `ebddada`(07-08 gpt-5.4-mini)，HEAD=`0fd8eaa`（已核实）

---

## 〇、一句话总结

**按 §4 判据（三份成功里一致、今天相反）严格筛下来，唯一满足的大项是 guard 层及其派生的调用摩擦，不是「硬隔离壳整体」，也不是会话形态**——因为第三份成功（ebddada / gpt-5.4-mini 9/9）**已经跑在 spawn_isolated_reader 的 staging 里**（只是 codex 不走 guard），且**冷启一次性 spawn 就拿到过 9/9**。派工单把 O-3（隔离壳整体）和 O-1（会话形态=唯一未测大变量）的范围都写宽了。

---

## 一、⭐ 证伪清单（交付优先级 1）

### P-1 · O-3「硬隔离壳整体 07-07 时根本不存在 ⇒ 嫌疑」——**表述过宽，需拆成两半**

事实链（全部可查）：

1. 隔离壳首次进仓 = `df6f249`（07-08 08:37，`git log --follow isolation.py` 首条）。
2. 第三份成功 `run_2026-07-08_gpt54mini_cv_retest` 的 `llm.yaml`（run 目录内）逐字写着：
   - `Scaffold state : git HEAD ebddada (clean tree at run start)`；
   - `Isolated via clean-room staging (spawn_isolated_reader build; ... cwd=staging)`；
   - **`the Claude Code PreToolUse guard layer does NOT apply to codex — isolation here is L1 physical staging + cwd + danger-full-access`**；
   - `pilot(1f) reviewed by orchestrator before batch (pilot门 kept — Haiku needed one打回)`。

⇒ 按 §4 判据拆分：

| 子项 | 07-02 | 07-07 | 07-08 | 今天 | 判据 |
|---|---|---|---|---|---|
| 物理 staging（gt 排除） | 无(prompt级) | 无(prompt级) | **有** | 有 | ⛔ 不满足（三份不一致） |
| wrapper `run_cv_probe.py` | 无(工具不存在) | 无(直接调 cv_probe.py) | **有** | 有 | ⛔ 不满足 |
| **guard 层(PreToolUse)** | 无 | 无 | **无(codex 不走)** | **有(1329 行)** | ✅ **满足** |

附带：派工单写「共约 2199 行」，今天实测 isolation 1179 + guard 1329 + run_cv_probe 373 = 2881 行（数字过时，不影响结论）。

### P-2 · O-1「会话形态是唯一还没被单独测过的大变量」——**「唯一」不成立**

三份成功的会话形态并不一致：

| run | 会话形态 | 打回 |
|---|---|---|
| 07-02 Sonnet | orchestrator 会话内 Agent tool 子代理，attempts=1 一次成 | 无 |
| 07-07 Haiku | 同上 + **同会话多轮打回（7 轮）** | 有 |
| 07-08 gpt-5.4-mini | **codex exec 冷启 spawn**，attempts=1，pilot 由 orchestrator 审后 batch | 未记录打回 |

⇒ **冷启一次性 spawn 拿到过 9/9（07-08）**，「冷启 vs 同会话」按 §4 判据不满足「三份成功里都在」。O-1 作为「复现 07-07 目标形态的定义内缺口」仍然成立（G-2），但**不是唯一未测大变量**：guard 摩擦同样从未被单独测过（历抽都是 guard 在场跑的，无一对照臂）。07-08 冷启成功时在场的两个补强——prescan 前置、guard 不适用——今天一个被撤（D1）、一个在场，这两个变量在 07-08 与今天之间是**绑定翻转**的。

### P-3 · §4「三份规则文档三次成功期间一字未动」——**指认必须说死**

逐 blob 哈希（`git rev-parse <c>:skills/.../0_reading/<f>`）：

| 文件 | 1595981 | 723b0f9 | ebddada | 0fd8eaa |
|---|---|---|---|---|
| guide.md | 142157df | 142157df | 142157df | 5e1e065e |
| reading_guide.md | 447ecb80 | 447ecb80 | 447ecb80 | 93d60b3a |
| pen_library.md | c778d781 | c778d781 | c778d781 | eb888d50 |
| session_kickoff.md | ceb97c20 | **458a7e6c** | **20085c14** | 9186c104 |
| cv_toolbox.md | **不存在** | 19d33e41 | **f3d54a38** | 8a4f708c |

「一字未动」只对 guide/reading_guide/pen_library 成立。kickoff 与 cv_toolbox 在成功窗口内**每两份之间都变过**。若把「三份」读成 kickoff+cv_toolbox+guide，会推出「kickoff 演进不是变量」的假结论。（08-16 行为清单 §〇 的表格记的是正确口径，派工单转述时丢了限定词。）

### P-4 · §1 表格小证伪

07-08 那份的成绩是**墙 9/9 · 平面窗 6/7 · 立面 15/15**（其 REPORT.md「AGENT conclusion」原文），不是 7/7。「三模型两家族都拿过 9/9」限于墙指标；平面窗指标只有 07-02/07-07 满分。

### P-5 · E-2 的口径限定（排除本身维持）

`1f_view.png` 内容 sha256 两端一致 ✅（`git show 723b0f9:... | sha256sum` = `ac620916...` = 工作树；case_data 全目录零 diff）。但严格口径下「输入」还含**模型看到的帧**：F-51 后 staging 预缩放，07-07 时模型看到 provider 错帧、今天看到对齐帧——方向是修复，仅提醒表述。

### §2 其余各条的核验结果

| # | 结论 | 证据 |
|---|---|---|
| E-1 | ✅ 维持 | H1/H2 run_config 与 07-07 同为 `claude-haiku-4-5-20251001`。同 ID 服务端快照漂移无法从仓内证伪，但被三模型论据覆盖 |
| E-2 | ✅ 维持 | 见 P-5 |
| E-3 | ✅ 维持 | gt 进仓 `2217393`=2026-07-26（git show 实测）；sm24 07-07 run 早三周且 38 次 CV 调用 |
| E-4 | ⚠️ 范围过宽 | C1/C2 只回滚了「省 crop 纪律」文本；cv_toolbox.md 的**调用形态一节**（`python scripts/tool_scripts/cv_probe.py` 直调 → `python tools/run_cv_probe.py --tool` wrapper）从未被回滚测试。E-4 应收窄为「纪律文本维度已排除」 |
| E-5 | ✅ 维持 | B1 打回修覆盖不修分数；派工单已自带 O-1 警告 |
| E-6 | ✅ 维持（且已过时） | 「零次用于测量」早被 F-49 推翻；本轮行为验证 F-49 修法已通（见 §三 C5） |

---

## 二、⭐ 移植缺口清单（交付 2，按 §4 判据筛过）

### G-1 · guard 层及其派生调用摩擦 —— **唯一满足「三成功一致(皆无)、今天相反」的大项**（把握：高）

- **位置**：`src/agent/execution/isolation.py:981-997`（PreToolUse hook 接线，引入 `df6f249` 07-08）+ `isolation_templates/guard.py` 全文（claude -p 路径自 07-31 脚手架批起全面生效；`SCRIPT_EXEC_ALLOWED_FILES` 执行面引入 `f6f2c46` 08-16）。
- **摩擦量化（本轮首次逐抽出数，access_log.jsonl 实测）**：三份成功 deny=0；08-15/16 各抽 A1=7、A2=6、B1=21、C1=6、D1=5、E1=3（allow 32–110）；H2 三轮 deny=18（扣 3 条 orchestrator 自污染探针后 15），`>` 重定向单项 **11 次、三轮反复撞**。
- **因果链（为什么它可能影响「量不量图」）**：07-07 的 55 次 crop_zoom 是高频小步试探的产物；每次 deny = 一整轮试错 turn 报废 + 挫败累积。B1 抽 deny 率 16% 时模型照样把覆盖从 1/6 打回后修到 6/6，说明 deny 不直接封路——但**没有任何一抽测过 deny=0 的今天形态**，该变量从未单独隔离。
- **⛔ 判据满足 ≠ 已证因果**。它与「工具在文档写的形态下真的可用」(O-2/F-49/F-60 系) 是同一条执行面的两面。
- 子项：G-1a `>`/`|` 拒绝中 `>` 无 hint（`guard.py:1158-1160`，hint 只配了 `|`）；G-1b `grep` 不在 `READ_ONLY_COMMANDS`（H2 r3 撞 1 次）。

### G-2 · 07-07 会话形态（同会话多轮打回）无等价物（把握：高，但**不满足三成功判据**，见 P-2）

它是「复现 07-07 模式」的**定义内缺口**：H2 的 `claude -p` ×3 冷启重入 = 07-08 形态，不是 07-07 形态。评估见 §四。

### G-3 · prescan 前置（不满足判据，登记一句）

07-08 有（`candidates.json` ×9 前置 + 仅 19 次标准工具调用 + 大量自命名 sidecar），07-02/07-07 无。三份不一致 ⇒ 按判据出局。但注意 07-08 的成功形状与 prescan 深度绑定，D1 只证「撤了不足以恢复」，不证「无关」。

### 已修回的旧缺口（不列）

pilot 停等门（kickoff `0fd8eaa` line 84-95 已恢复，H1/H2 实测停下等审 ✅）、scale_origin 必填（已退 SHOULD）、跨轴 raise（已改合法出口）。

---

## 三、⭐ 第三条 F-49/F-60 同族缺陷（交付 3；行为验证于 /tmp 假 staging，非静态推断）

先说核查结论：**cv_toolbox.md 全部 7 条调用示例按 guard 当前判据逐条走查，全部放行**（含 line 36-40 的内联 `--anchors-json '[...]'`——F-49 已由 `e0367e1`(08-16) 的 `JSON_OR_PATH_KEYS` 修复，C5 实测 allow；line 96 `-c` 示例、line 101 脚本示例亦通）。同族缺陷不在示例里，在示例之外：

### N-1 · `python -c` 代码里的领域词触发 command 级全量 DENY_TOKENS——**同一行代码，文件里合法、-c 里违法**（把握：高，已行为验证）

- **实测**：`python -c 'print(1)  # grade line at 0.000'` → **deny "forbidden token: grade"**；把同一行写进 `out/m.py` 再 `python out/m.py` → **allow**。
- **机理**：`guard.py:1172-1178` `_check_bash` 第一步对整条 command 用**全量** `DENY_TOKENS`（含 `grade`/`attempts`/`verdict`，:239-249）做子串扫描——`-c` 程序文本就在 command 里；而文件体通道用的是 `EXEC_DENY_PATH_TOKENS`（:262-264，**已剔除这三个领域词**，注释自己写明「grade line = 室外地坪线」是本项目合法词汇）。
- **与 F-60 的关系**：F-60 修的是「文件体被 `..`/`~` 误伤」；N-1 是「-c 代码被 grade/attempts/verdict 误伤」——**同一轮修复只改了文件体通道，command 通道没跟着改**，双标是结构性的。
- **为什么像「模型偷懒」**：cv_toolbox.md:96-97 明确教读者用 `-c` 做单行像素探测、:107 说引号内 `>/<` 工作正常，但**没有任何文档警告这三个词在 -c 里会拒**。立面测量恰恰最常说 grade line（F-4 时代已撞过同词）。模型被拒后的产物与「没想到要量」同形。

### N-2 · out/ 下任一**非脚本**文本文件含 EXEC_DENY token → 全部脚本执行被毒死（把握：高，已行为验证）

- **实测**：`out/notes.md` 写一行 `reference: https://example.com/method` → 之后 `python out/clean.py`（完全干净的脚本）→ **deny**；删掉笔记 → **allow**。
- **机理**：`guard.py:931-986` `_scan_reader_authored_code` 扫 out/ + requests/ 下**所有**可解码文本文件，撞 `EXEC_DENY_NETWORK/DYNAMIC/IMPLICIT_PATHS`（:306-341，含 `https://`、`os.environ`、`expanduser`…）任一 token 即整体拒绝。F-60 修法收窄了 `..`/`~` 两个正则（:427-469），但**「扫描面=全部可写文件 × 拒绝效果=全部脚本」的范围-效果错配原样保留**。
- **触发面**：cv_toolbox.md:104 鼓励「write any output under out/」——测量笔记、自 dump 的中间 JSON、带参考链接的 markdown 都是合法落盘物。写笔记的人不会想到笔记杀了脚本执行面。（F-60 修后的 `_token_reason` 会指名文件与行，可定位性比 F-60 原版好，但因果仍极隐蔽。）

### N-3 · `>` 拒绝无可操作提示（把握：高；归 G-1a）

H2 三轮 11 次 `>`，hint 字段为空（`guard.py:1158-1160` 只给 `|` 配了「express the pipeline in Python」）。文档 :107 写了 no redirection，但 11 次实测证明拒绝消息本身不指路时模型不回头读文档。同族判据：合法意图缺合法出口的引导。

### N-4 · batch envelope 严格形态（弱，登记不立案）

H2 ×3、B1 ×3 次撞 `{"requests":[...]}` 形态；有 usage 模板可操作 ✅，属学习成本。

### 顺带核对（未发现新问题）

- sidecar 记录的 `overlay_path` 等绝对路径位于 `/tmp/ep_isolation/<staging>` 内（isolation.py:220），`_lexical_check` 的 `_under` 判 staging 内 → 不触发 DENY，**工具自身输出不会毒执行面**。
- 工具依赖（numpy/PIL/scipy）在隔离 spawn 下可用——H1/H2 有真实 sidecar 产物为行为证据。

---

## 四、O-1 会话形态改造代价评估（交付 4；只评估，未动一行）

### 路线 A（推荐）：staging 内 `claude -p --resume <session_id>`（CLI 2.1.198 已支持 `-r/--resume`）

- **改动点**（全部在 isolation.py / spawn_isolated_reader.py，**不动 guard**）：
  1. `spawn_command()`（isolation.py:553-572）：首轮加 `--output-format json` 捕获 `session_id`，落盘到 staging 兄弟的 `.audit` 目录（与 access_log 同侧，reader 不可见——`_audit_dir` 规则 isolation.py:384/guard.py:384 已有）。
  2. 新增 `resume_command(staging_root, session_id, message)`；`write_feedback()`（isolation.py:314）保留（feedback.md 通道向后兼容）或改为构造续会话消息，`check_feedback_text` 污染闸门原样套用。
  3. kickoff 文案（0fd8eaa 版 line 91-95「You will be resumed / feedback.md 是唯一审查通道」）改成与 resume 语义一致的表述。
  4. transcript 归档：`-p` stdout 只有最后一条消息（H2 四之二实测）；resume 会话的完整 jsonl 落在 `~/.claude/projects/<staging-cwd-slug>/`，需 spawn 侧每轮拷出进 run 目录，并处理 `*.log`/jsonl 被 .gitignore 吞的问题（H2 已踩，改名 `_transcript.md` 入库）。
- **与污染隔离的张力**：**没有新张力**——settings/cwd/guard 全不变（同一 `isolation_settings.json`，hook 每轮进程重跑，`_EXECUTED_CODE` 累加器每进程一次的语义不变）；gt 仍物理不在 staging；反馈内容仍过词法闸门。增量暴露 = 反馈留在模型上下文内可被引用——这正是 07-07 已被接受的形态。
- **代价**：每轮全上下文计费（高于冷启重读文件）；session_id 生命周期管理；工作量小时级。
- **风险**：若 resume 与 `--settings` 组合有 CLI 层怪癖（未实测），回退路线 B。

### 路线 B：orchestrator 会话内 Agent tool 子代理（07-07 原生形态）

零代码，但**放弃 guard + staging + access_log**（回 prompt 级隔离）——07-07 不可审计正是它的病史；08-16 口径接受的是 07-07 的「orchestrator 亲自审 + 多轮」形态，不等于放弃过程审计。且子代理继承主会话环境，无法像 `-p --settings` 那样强制挂 PreToolUse guard。**仅适合做一次性诊断抽，不适合做目标形态**。

### 路线 C：`claude -p --bg` + `claude agents`（2.1.198 支持）

后台 agent 可能是长会话的更优载体，行为面未验证，列为候选。

### ⭐ 与 G-1 的顺序建议

若先做 A 后做 G-1 的对照，两个变量仍缠在一起（resume 后 guard 摩擦照旧）。**更便宜的单变量顺序**：先跑一抽「宽松 guard 对照臂」（临时版 guard 只保留路径类 DENY + `_append_log`，去掉 shell 结构/命令 allowlist/参数配对/文件体扫描），观察 crop_zoom 频次与 1/6 病征是否变化——这一抽同时检验 G-1 与 N-1/N-2 的实际权重；之后再决定是否值得投入会话形态改造。**注意**：对照臂必须保留 `_append_log`，否则失去过程审计（这正是 guard 兼任的唯一审计记录者角色）。

---

## 五、无法确定项（明写，不补解释）

1. 07-08 那次各 CV 调用走 wrapper 还是直调 `tools/cv_probe.py`——staging 已销毁（/tmp），codex 无 access_log，cv_evidence 的 NNN 命名两种形态同源，**无法从仓内数据区分**。已确认的是：F-49 缺陷当时就在场（df6f249 版 `_request_to_argv` 的 `anchors_json` 走 `_resolve`），而那次标准 `px_m_calibrator` 调用仅 1 次 + 大量自命名 sidecar——它可能恰好绕开了雷区，不能反推「F-49 不影响」。
2. 同 ID 模型的服务端快照漂移——仓内无证据可判。
3. N-1/N-2 在历次 08-15/16 抽中**实际**触发过几次——本轮只核了 B1 与 H2 的 deny 明细（B1 的 21 条里无 grade/attempts/verdict 命中；H2 的 18 条里也无）；A1/A2/C1/C2/D1/E1 的逐条理由未逐抽展开，无法断言零触发。
4. `claude -p --resume --settings` 组合的实际行为——未实测（read-only 约束下不动仓库；下一批施工前应用小任务先验通道，对标 F-48 教训）。

---

## 六、证据索引

| 断言 | 位置 |
|---|---|
| 07-08 run 在 staging 内、无 guard、pilot 门保留 | `case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/llm.yaml`（Reading/Isolation/Scaffold state 段） |
| 隔离壳首次进仓 | `df6f249`（07-08 08:37），`git log --follow src/agent/execution/isolation.py` |
| 三份成功文档哈希表 | `git rev-parse <c>:skills/intake_pipeline/0_reading/<f>`（§一 P-3 表） |
| 好窗口 reading 路径零删 | `git diff --numstat 1595981 ebddada -- skills/intake_pipeline/0_reading/ src/agent/reading/` = +1279/−0 |
| 摩擦逐抽数字 | 各 run 目录 `**/access_log.jsonl`（grep decision 计数） |
| H2 三轮 deny 明细 | `run_2026-08-17_707mode_H2/_run/pilot_r{1,2,3}/access_log.jsonl` |
| N-1/N-2/C5/C6 行为验证 | /tmp 假 staging（guard.py 副本 + evaluate() 直调），已清理 |
| F-49 修复引入 | `e0367e1`（08-16），`JSON_OR_PATH_KEYS` |
| guard hooks 接线 | `isolation.py:981-997`；执行面 allowlist 引入 `f6f2c46`（08-16） |
| kickoff pilot 门已恢复 | `git show 0fd8eaa:skills/.../session_kickoff.md` line 84-95 |
