# 调查问题书 · 「上游给了指令不照做，被打回后就照做」——为什么？

- **日期**：2026-08-01 · **性质**：**只查不改**（用户明令：先不要改动，双方查清楚先汇报）
- **打法**：**双独立调查**（GPT 侧 sol + Claude 侧主控各自独立查 → 分别汇报 → 用户看两份）
- **⛔ 本文只给事实与线索，不给任何假设或解法方向**（避免污染独立性）

---

## 1. 要回答的问题（用户提出，原话口径）

> 为什么主控发现没做完、打回之后，Haiku 就规规矩矩做完了？**没有办法直接让它规规矩矩做完吗？**
> 整轮打回应该是**兜底机制**，不应该做成**依赖机制** —— 不能每次都「先随意做，反正不过关打回再做」，
> 这即使能做出结果，**效率上也不可接受**。
>
> 问题是不是收束到了：**Haiku 在打回指令下能做好，但直接给同样的指令就不做，而且它还承认自己没照章办事？**

**⇒ 要找的是这个落差的根因。不是要修法（这一轮不许改任何东西）。**

---

## 2. 已经核实的事实（均可复算，附取证方式）

### 2.1 「被打回后做好了」这一侧

**07-07 sm24 探针轮**（`case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/`），
模型 = Haiku 4.5，**该轮无预扫**（`0_reading/cv_evidence/*/` 下只有读图器自己按 001/002… 编号的工具产物，
**没有 `prescan/` 目录**）。

- **打回两次**（记录：[实验档](../../experiments/2026-07-07_haiku_cv_retest/README.md) 第 62–63 行 + 第 70 行）：
  - **r1（纪律）**：现象 = 标定 RMSE 86mm 锚粗 / **只描「主要墙」违完整性** / 窗未描 / px→m 换算自相矛盾。
    打回指令原文记载 = **「锚收紧到 ±1px、全墙完整描、单一换算公式留痕」**。
  - **r2（schema）**：51 条 `dimensions[].anchor` 写成自创 dict（schema 要 flat list）。
- **r2 产出**：14 道墙全部 px→m 算术留痕 · **38 个候选拒收并写明理由** · 11 扇窗双通道钉位 · 51 条尺寸 verbatim。
- **平面图上的工具调用 = 19 次**（`ls run_2026-07-07_haiku_cv_probe/0_reading/cv_evidence/1f_view/*.json`）：
  **crop_zoom 11 次** · window_cc_detector 4 · wall_line_profiler 2 · px_m_calibrator 1 · overlay_logger 1。
- 该轮成绩（同尺子：GT 八道分区线 · 容差 0.30 m）= **8/8**。

### 2.2 「直接给指令不做」这一侧

**08-01 W5 两抽**（`run_2026-08-01_haiku_w5_scoped_{d1,d2}/`），同模型，**减卷为两张图**
（1f_view 平面 + South_view 立面），有预扫，硬隔离，**零监督**（零 directive / 零 feedback / 零中途反馈）。

- **平面图上的工具调用**：**d1 = 5 次 · d2 = 1 次**（对比 07-07 的 19 次）。
- **成绩**：独立内墙命中 **d1 = 3/16 · d2 = 4/16**；按长度 d1 = 9.0 % · d2 = 24.8 %（分母 57.86 m）。
  **d2 命中的 4 段全部是同一条竖线 x=4.18**（尺寸链 `4180|1640|4180` 直接给出的值）。
- **两抽都读了全部五份指令文件**（`access_log.jsonl` 里 `session_kickoff.md` / `guide.md` ×2 /
  `reading_guide.md` / `pen_library.md` / `cv_toolbox.md` 均 allow）⇒ **「没看到规则」已被排除**。
- **`guide.md` 423 行、`session_kickoff.md` 92 行**（常规 Read 一次可读全）。
- **规则本来就在文档里**：`guide.md` §6 自检清单第二条原文 =
  *"every visible wall/window/wall_fill stroke is in the strokes array with the right pen field"*。
- **d1 自己在产物里承认没做完**（`out/1f_view.json` 的 `uncaptured` 字段，原文）：
  - *"Window openings shown as cyan lines - present in drawing but detailed window pen tracing **deferred to detailed pass**"*
  - *"Multiple dimension chains for interior details **not fully transcribed** in thi…"*
  d1 的 `reading_summary.md` 另有原文：*"Interior partitions traced via **visual inspection** rather than
  dimension derivation"*、*"time spent on perimeter and major divisions **left less capacity** for detailed interior mapping"*。
- **启动 prompt 里已经要求做完**（`spawn_isolated_reader.py spawn` 生成，可自行复现打印）：
  *"Work straight through to the end on your own: no reviewer will answer you mid-run.
  Finish the first plan image, run the guide's self-check against it, then do the remaining images and the summary."*

### 2.3 文档侧已经做过的两次「加强」

- **07-07 当天 E1**：把 CV 纪律固化进 `cv_toolbox.md`（自声明 clean-CAD required；kickoff 判定权移交）。
- **08-01 W1**（commit `15cfcb8`）：把「先标定再写米制坐标」提到 `session_kickoff.md` 的
  **Non-negotiables 清单**，并删掉「required or deferred 见那个文件」的间接层。

**两次加强之后，2.2 的行为依旧。**

---

## 3. ⚠️ 已知的未知（不许当成已知来推理）

1. **07-07 那轮的完整上游 prompt 没有落盘** —— 记录原文：*"完整 prompt 在主控 transcript"*
   （[HANDOFF](../../experiments/2026-07-07_haiku_cv_retest/HANDOFF_gpt54mini_crosstest.md) 第 16 行），
   该 transcript 已不存在。
   ⇒ **「当时上游是否已经在开工前就要求过『全墙完整描』」目前无从证实**。
   若你的结论依赖这一点，**必须标为未知**，不得假设任一方向。
2. 07-07 与 08-01 之间同时变了多项（有无预扫 / prompt 级隔离 vs 硬隔离 / 有无监督 / 全卷 vs 减卷）
   ⇒ **不是单变量对比**。
3. `access_log.jsonl` 记录的是路径放行决定，**不含读取的行范围** ⇒ 无法据此判断某一节是否被读到。

---

## 4. 请你交付什么

**只查不改。不许修改任何生产码、测试、文档；不许 commit；不许 push。**
破坏性/探索性操作一律在 `/tmp` 副本里做。

1. **根因假设清单，按你判断的可能性排序**。每条必须写：
   - 它主张的机制是什么；
   - **盘上有哪些证据支持它**（给命令与真实输出，不接受推理代替取证）；
   - **什么证据会证伪它**；
   - **能否便宜地验证**（如果能，写出具体怎么验，但**这一轮不要真的去跑改动**）。
2. **明确指出用户那个收束式提问的前提是否成立**：
   「同样的指令，事前给不做、事后给就做」—— 依 §3.1 的未知，这个前提**能不能被证实**？
   如果不能，说清楚缺哪一块证据。
3. **你认为最关键的一条**，以及**你没能查到的部分**。

**不要给修法方案**（用户明确要先看诊断）。若你强烈认为某个方向必须提，单列一节，标明是方向不是方案。

**回主对话只给简报**：假设清单（每条一行）+ 最关键一条 + 未能查到的部分。不要贴大段文件内容。
