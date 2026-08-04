# R1 批 C · r1 返工派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-04（北京时间 11:55，非高峰；⚠️ 14:00 起 3x）
- **派工方**：orchestrator · **施工席**：GLM（续做）
- **前置**：HEAD `d0e33ef`，全仓 **2106 passed + 10 xfailed 零红**（轻门与交叉审各自独立复跑，逐字一致）
- **上游**：[交叉审报告](../verdict/2026-08-04_reading_ruler_batchC_crossreview_claude.md)（**判定 = REWORK：1 BLOCKER / 3 MAJOR / 3 MINOR / 2 NIT**）·
  [轻门](../verdict/2026-08-04_reading_ruler_batchC_orchestrator_lightgate.md) ·
  [批 C 派工单](2026-08-04_reading_ruler_batchC_and_r2c_rest_dispatch.md)（纪律与禁止清单继续有效）

---

## 0. 先说清楚：你的锁一条不假，问题是「只在一条路上修好了」

交叉审对你的锁的结论是**正面**的：**八处独立 neuter 全部「摘掉即红、零连带、走真实入口、断言落具体产物字段」，零假锁**，与 orchestrator 轻门台账逐条吻合。
六次证伪失败（approve-review 无旁路 / O-4 无合法 annotation 误拒 / r2c-3 四条断言互斥可区分 …）**反向坐实**你的实现。

**但判定仍是 REWORK，因为核心缺陷与批 B 是同一句话**：

> **修好的是「在硬隔离那条布局上生效」，没修好的是「在所有真实路径上都生效」。**

**⚠️ orchestrator 的轻门也漏了这一条**（我的七处 neuter 全部用隔离 fixture，没走盲重读恢复路径）——**这是我的盲区，不是你多做错了什么**。

---

## 1. ⛔ BLOCKER（必须最先修）

### B-1 · O-1 让「盲重读恢复路径」渲染归零，并**反过来拒批一个健康的 run**

- **位置**：`scripts/tool_scripts/run_stage.py:690`（`(json.loads(out_text) or {}).get("views") or {}`）
  + `:717`（`"status": "complete" if (view_records and not any_failed) else "unavailable"`）
- **失败链（orchestrator 已独立核实）**：
  1. judge 打回 ⇒ 盲重读；`judge_rubric.md:57` 与 CLI 自己打印的提示（`run_stage.py:2039`）
     **都命令读图器写 flat `0_reading/*_view.json`**，那条路的 attempt `output.json` **不是 `{"views": {...}}` 形状**；
  2. ⇒ `views` 解析为空 ⇒ `view_records` 为空；
  3. ⇒ **空集被判成 `unavailable`**（`view_records and ...` 对空 dict 为假）；
  4. ⇒ `cmd_approve_review` 以「at least one view failed to render」**拒绝一个完全健康的 run**。
- **对照**：**同一份输入在 `079ce17`（O-1 之前）渲得出两张 PNG** ⇒ **这是 O-1 引入的回归**，不是既有缺陷。
- **要求**：
  ① **渲染器要认两种真实布局**（attempt aggregate `{"views": {...}}` **与** flat `0_reading/*_view.json`），
     ⛔ 不许只认一种；② **「没有图可渲」与「渲染失败」必须是两个状态**
     —— 空集不得等同于失败；③ 阻断只能由**真正失败**触发。
- **锁**：一条**走盲重读恢复路径**（flat 布局）的锁 —— 渲染产出图、状态非 `unavailable`、`approve-review` **放行**；
  **摘掉「认 flat 布局」的实现必须红**。⛔ 这条锁不许用隔离 fixture。

---

## 2. ⛔ MAJOR（三条）

### M-1 · 读不出 attempt 的 `output.json` 时零 artifact、状态 `missing`、放行
- **位置**：`run_stage.py:805` 那个 stage 级 `except`
- **失败场景**：产物损坏/读不出 ⇒ **不落任何 failure artifact**、状态 `missing` ⇒ 与「pre-O-1 历史 run」**不可区分** ⇒ approve-review 放行。
- **要求**：读取失败必须落**机器可读的 failure artifact** 且状态**可与 `missing` 区分**。**摘掉即红的锁。**

### M-2 · 发给读图器的第一条指令仍写着旧命名规则（O-3 白改了一半）
- **位置**：`src/agent/execution/isolation.py:694` 生成的 `kickoff_prompt.md` 仍写 `<name>_view.json`
- **失败场景**：O-3 把这条推导从 `session_kickoff.md` 删了，**但读图器收到的第一条指令还在教它这么拼名字**
  ⇒ 图名以 `_view` 结尾的 case 依旧必踩。**这是 O-3 的正文诉求没落全。**
- **要求**：改成按 `input_inventory.json` 的 `expected_output_id` 写名（与 O-3 唯一规范一致）。**配摘掉即红的锁。**

### M-3 · 移走了症状，没补上检测（O-4 只交付一半）
- **位置**：`scripts/tool_scripts/render_vector_to_png.py:150-154` + `src/validator/checks/reading.py`（gate 侧对 OCR **零检查**）
- **事实**：派工单「本批必做」是四件（画布只由结构几何决定 ✅ / 硬限像素 ✅ /
  **metric annotation 按 trusted bounds 检查、越界 flag 或 block ❌** / **pixel anchor 不进 metric transform ❌ 未验证**）。
- **失败场景**：**3.3 亿像素那次爆炸，曾经是坏 anchor 的唯一信号**。现在把 OCR 移出画布 ⇒ 不再爆炸，
  **但也没有任何地方报告它坏了** ⇒ **坏数据被彻底掩盖**（比原来更难发现）。
- **要求**：gate① 侧补 OCR anchor 的 frame/bounds 检查（越界 **flag**，档位严格时 block），
  并给出机器可读原因。**⛔ 不许 clamp、不许静默丢弃。配摘掉即红的锁。**

---

## 3. MINOR（三条，能一起做就一起）

- **N-1**（`test_reading_renders.py:185-190`）：docstring 声称锁住 `missing` 分支，**实测把 `missing` 改成阻断后五条锁全绿**
  ⇒ 该分支零锁。**要么补锁、要么改掉那句声称**（⛔ 不许留「声称在守其实没守」——本项目已栽四次）。
- **N-2**（L-50）：与既有 `test_merge_per_image_extra_is_rejected` 共用同一 hook、**零增量约束力**；
  **O-3 真正新增的命名规范目前零锁** ⇒ 补一条直接锁「按 `expected_output_id` 写名」的。
- **N-3**（`render_vector_to_png.py` `MAX_CANVAS_SIDE_PX=8192` + 固定 45 px/m）：
  **单边 >182 m 的建筑永远渲不出**（实测 200×20 m 被拒，而它只占总像素预算的 1/5）⇒ **撞不变量 #6（复杂度可扩展性）**。
  **要求**：改成「先按预算自适应缩放比例、真的超了才拒」，或明确分离「结构合法但太大」与「anchor 坏了」两种拒绝原因。
  ⛔ 仍不许 clamp 掉坏数据。

---

## 4. 纪律（继续有效，只列硬的）

- **⭐ 本轮首要纪律：每条锁必须走「会踩到该缺陷的那条真实路径」**
  —— B-1 的锁⛔不许用隔离 fixture；**这正是本轮 BLOCKER 与批 B 的共同病根**。
- 每条「摘掉即红、零连带」+ neuter 自查如实登记；**「全仓绿」不构成锁真绑的证据**。
- ⚠️ **环境坑（交叉审登记，照做）**：容器 editable `.pth` 指向主仓库，
  **在 /tmp 克隆里跑 neuter 必须 `PYTHONPATH=$PWD`**，否则会解析回主仓、等于没做。
- ⛔ 不 push · ⛔ 不读 GT · ⛔ 不碰 sm24 `testdata_prompt.json` · ⛔ 不做批 D/E/R1.5 ·
  ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档（工作树里 CLAUDE.md / decision_log / plan / 两份 lightgate 的未提交改动**是 orchestrator 的**）。
- 做完一件存一件、即时本地 commit（`8.04_BatchC_r1_<条目>_<英文标签>`）。
- 顺序：**B-1 → M-1 → M-2 → M-3 → N-1/N-2/N-3**。做不完停下上报，⛔ 不要硬塞。
- 交付前跑全仓 `pytest -q -n 6`（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。基线 **2106 passed + 10 xfailed 零红**
  （⚠️ `tests/test_zone_agent.py::test_zone_agent_creates_two_zones` 跑真实 OpenAI 调用、可能网络超时红，与本批无关）。
- **遇欠规格新边界继续停下上报** —— 你前几轮三次都做对了。

## 5. 交付
续写 `AI_agent/logs/reviews/execution/2026-08-04_reading_ruler_batchC_glm.md` 的新 `## 4. r1 返工` 段（⛔ 别覆盖既有段）。
