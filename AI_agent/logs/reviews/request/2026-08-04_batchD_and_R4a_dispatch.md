# 批 D（判卷图恢复）+ R4-a（成绩分账）派工单（施工 = Claude 侧执行档子代理 · 审 = sol）

- **日期**：2026-08-04（北京时间 13:10）
- **派工方**：orchestrator · **施工席**：**Claude 侧执行档子代理，在独立 git worktree 里作业**
  （⚠️ 主工作树 14:27 起有 GLM 在做批 C 剩余四条，**两边不得并发写同一棵树**）
- **审阅席**：**sol（GPT 侧）** —— 用户 2026-08-04 指定。施工 = Claude ⇒ **「谁写谁不批」满足**。
- **前置**：HEAD `f254c56`，全仓 **2115 passed + 10 xfailed 零红**（orchestrator 独立复跑）
- **上游**：[plan.md R4-a](../../plan.md) · [批 B/C 派工单](2026-08-03_reading_ruler_r1_batchBC_dispatch.md)（批 D 的由来 = M-2）·
  `AI_agent/CLAUDE.md` §1.5 #7（**成绩记账口径，本单 R4-a 的唯一权威定义**）

---

## 0. 为什么这两条现在做

- **批 D**：判卷图是**用户唯一能独立看懂产物好坏的东西**。现在 v3 路径画了平面多边形、
  但**丢了立面板与图例、标签互压** ⇒ 用户只能听 orchestrator 转述数字。
  **它是 R2（重建基线）的硬前置**：不修好，任何「识图变好/变坏」的结论用户都没法自己验。
- **R4-a**：它决定**后面所有实验的成绩记在谁头上**。不先做，R6 四臂实验跑完又会出现「成绩记错人」
  —— 本项目已经因此把「Haiku 独立满分」误记过一次。**便宜、且必须在实验之前。**

---

## 1. 批 D · 判卷图恢复（六 panel + 图例）

### 病灶
`scripts/tool_scripts/render_grade.py`：
- **legacy 路径**（`_draw_plan_panel:564` / `_draw_elevation_panel:836` / `:917-927` 的多 panel 布局）
  画的是**两层平面 + 四立面的几何叠图带图例**；
- **v3 typed 路径**（`render_typed_grade:1127`）只画平面多边形、**没有立面 panel**，
  且标题/状态行与标签**互相压盖**（M-2 原始描述：「标签互压的柱状图」）。
- ⇒ 现在跑出来的 `grade.png` **看不出立面对错**。

### 要求
1. **v3 typed 路径恢复六 panel 布局**：两层平面 + 四个立面（North/South/East/West），
   **每个 panel 有标题**、**整图有图例**（颜色 = 判定档、画法 = 类别，沿用既有约定）。
2. **⛔ 不得回退到 legacy 渲染器**（它按矩形变换，v3 是多边形）—— 要在 typed 路径里补上立面 panel。
3. **标签不得互压**：panel 尺寸/间距按内容自适应；文字超框要么换行要么缩字号，**⛔ 不许裁掉**。
4. **⛔ 不得读产品的 mirror / local-x 声明**（`render_typed_grade` 的 docstring 已写死这条边界，保持）。
5. 若某个立面在 GT 里不存在 ⇒ 该 panel 画成**明确的「无此立面」占位**，⛔ 不许静默省略
   （省略会让「漏画」看起来像「没考」）。

### 锁
- **L-D1**：给一个含两层 + 四立面的 GT + payload ⇒ 产出图**包含 6 个 panel 的标题文本**且
  **画布尺寸足以容纳**（断言具体像素区间或 panel 计数，⛔ 不许只断言「返回了 Image」）。
- **L-D2**：某立面在 GT 中缺失 ⇒ 出现「无此立面」占位，**不是少一个 panel**。
- **L-D3**：图例存在且**列出全部判定档**。
- 每条配 neuter（摘掉对应实现即红、零连带）。

---

## 2. R4-a · 成绩分账（`reading_mode` 溯源块）

### 现状
**全仓零引用**（`grep -rn "reading_mode" src scripts` 无命中）⇒ 从零开始。

### ⭐ 记账口径（**唯一权威 = CLAUDE.md §1.5 #7，逐字照抄，⛔ 不许自行归纳**）
- **两条正式 lane**：
  - **`autonomous`** = 目标 VLM + 冻结工具箱、**零 `reading-agent`** ⇒ 北极星、长期目标；
  - **`controlled`** = 有 `reading-agent` 在场 ⇒ **当前批次的验收 lane**。
    **completely 算真实工程成功，但⛔ 不得记成「弱模型独立满分」。**
- **⚠️ 另有一个 dev 期开发者职能（`tool_invention`）——它不是 lane、不产生正式成绩。**
  ⛔ **不许把它并列成第三条 lane**（用户 2026-08-02 晚当面更正过一次，此前记成「三条并列 lane」是错的）。

### 要求
1. **落盘 `reading_mode` 溯源块**（随 reading 阶段产物一起，进已有的 provenance/manifest 体系，
   **由你判断挂在哪最合适并在执行日志说明理由**），至少含：
   - `lane`: `autonomous` | `controlled`（⛔ 只有这两个合法值）
   - `dev_function`: bool（是否属 dev 期 tool-invention 职能 ⇒ **该轮跑测不作为正式成绩**）
   - `reading_agent`: `{ model, sees_images: bool, rework_rounds: int } | null`
   - `reading_worker_agent`: `{ model, effort }`
   - `toolbox_version`、`isolation_profile`
2. **报告按 lane 分账**：`report/REPORT.md`（`report_assembly.py`）里，识图分数**必须带 lane 标注**；
   `dev_function=true` 的轮次**必须显式标注「不作为正式成绩」**。
3. **⛔ 缺失即 fail-closed**：新 run 若产不出 `reading_mode`，**不得静默按 autonomous 记**
   （那正是「成绩记错人」的原始形态）。**⛔ 也不得反过来把历史 run 判成违规** —— 历史无此块 ⇒ 标 `legacy_unknown`、
   **不得冒充任何一条 lane**（与项目已有的「legacy 不得冒充严格档」同规格）。

### 锁
- **L-R1**：`controlled` 的 run ⇒ 报告里该分数**带 controlled 标注**；把 lane 改成 `autonomous` ⇒ 断言变化（**证明标注不是装饰**）。
- **L-R2**：新 run 缺 `reading_mode` ⇒ **fail-closed**（走真实入口，⛔ 不许直接喂内部函数）。
- **L-R3**：历史 run（无该块）⇒ 标 `legacy_unknown`、**不冒充 lane**、不阻断只读回放。
- **L-R4**：`dev_function=true` ⇒ 报告显式标「不作为正式成绩」。
- 每条配 neuter。

---

## 3. 纪律（本项目今天用血换来的，逐条照做）

1. **每条锁「摘掉即红、零连带」**，neuter 自查如实登记。**「全仓绿」不构成锁真绑的证据。**
2. **⭐ 锁必须走「会踩到该缺陷的那条真实路径」** —— 今天的 BLOCKER 就是「只在一条布局上修好了」。
3. **断言落在具体产物字段 / 具体 panel / 具体 check-id 行**，⛔ 不得落在「返回值存在 / 总数变了 / 不是 None」。
4. ⚠️ **环境坑**：容器 editable `.pth` 指向主仓库 ⇒ **在 /tmp 克隆里跑 neuter 必须 `PYTHONPATH=$PWD`**，否则解析回主仓、等于没做。
5. ⚠️ **neuter 脚本必须逐字精确命中目标实现**；**「零红」在确认脚本真的改到东西之前不得当结论**（orchestrator 今天两次栽在这）。
6. ⛔ **不读 GT 里的答案数字**（`case_tests/test_baseline/gt/`）——**判卷渲染器读 GT 结构是它的正常职责**，
   但**你本人不得把 GT 答案抄进 fixture**；fixture 自造。
7. ⛔ 不 push · ⛔ 不碰 sm24 `testdata_prompt.json` · ⛔ 不做批 C / R1.5 / R2 ·
   ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档。
8. **做完一件存一件、即时本地 commit**（`8.04_BatchD_<标签>` / `8.04_R4a_<标签>`）。
9. **遇欠规格边界停下上报**，⛔ 不得自行降级为假设。

## 4. 跑测与交付

- 全仓 `pytest -q -n 4`（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。**基线 = 2115 passed + 10 xfailed 零红**
  （⚠️ `tests/test_zone_agent.py::test_zone_agent_creates_two_zones` 跑真实 OpenAI、可能网络超时红，与本批无关）。
- 执行日志新建 `AI_agent/logs/reviews/execution/2026-08-04_batchD_R4a_claude.md`：
  每条含 设计 → 改动清单（文件:行）→ **neuter 自查** → 受影响子集结果 → 缺口/披露。
- **顺序：R4-a（小、且是 R6 的前置）→ 批 D（大）。** 做不完停下上报，⛔ 不要硬塞。
