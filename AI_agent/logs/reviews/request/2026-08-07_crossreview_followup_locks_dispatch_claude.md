# 施工单 · 交叉审 follow-up：补两处**正确性锁**（仅测试，⛔ 不动生产码）

- **日期**：2026-08-07 · **派工方**：orchestrator（Opus 5）· **席位**：Claude 侧 Sonnet 子代理
- **工作区**：主工作树，开工时 HEAD 应为 `950cdbf` 或更新
- **来源**：GLM-5.2 交叉审 [`verdict/2026-08-07_f12_f9_f13_crossreview_glm.md`](../verdict/2026-08-07_f12_f9_f13_crossreview_glm.md)
  （0 BLOCKER / 1 MAJOR / 2 MINOR，三摊均 APPROVE；本单修其中两条）

## 0. 开工自检

```bash
git log --oneline -1
git status --short   # case_tests/ 下若干未跟踪 run 目录属已知，⛔ 不要碰、不要 add
```

---

## 1. 任务一（MAJOR-1）：`tests/test_f13_kernel_canonical_vertex_order.py` 的 lock2 **水平面/窗退化成了自指锁**

### 事实（orchestrator 已亲自复核代码，非转述）

| lock2 | 现有断言 | 是不是正确性锁 |
|---|---|---|
| 垂直墙 `:202` | `canonical[0] == [1.0, 0.0, 2.0]`（**手算值**）+ `top_left_corner_index(...) == 0` | ✅ 是 |
| 楼板 `:217` / 天花 `:231` / 窗 `:244` | **只有** `top_left_corner_index(canonical, normal) == 0` | ⛔ **不是** |

后三条把 `canonicalize_ring_vertices` 的**输出**喂回它**内部用来挑起笔点的同一个函数**
⇒ **自指**：两边一起错时照样绿。GLM 探针已实证（把楼板起笔点改成错角，lock2 仍全绿）。

**⚠️ 当前实现是对的**（GLM 手算楼板首顶点 = `[0,0,0]` 与实现一致）
⇒ 这是**回归保护缺口**、不是当前缺陷。**⛔ 不要去"修"实现。**

### 要做的

给**楼板 / 天花(屋顶) / 窗**三条各补一条 **`canonical[0] == <手算值>`** 的断言，与垂直墙那条同形。

**⭐⭐ 手算值的来源纪律（本单最重要的一条）**：
- **⛔ 不许把实现跑一遍、把输出抄进断言** —— 那还是自指，等于什么都没加。
- ✅ 必须**从约定本身推导**：读 `top_left_corner_index` 的定义，写清这个面型下
  「朝外看」时 `右` 与 `上` 各是哪个方向向量，再据此推出哪个顶点是左上角。
  **把推导过程写成注释**（垂直墙那条 `:200-201` 已有范例）。
- ⚠️ **楼板的朝外法向朝下**（`(0,0,-1)`）⇒「从外面看」是**从下往上看**，
  左上角与俯视直觉**相反** —— orchestrator 本轮在这里实际错过一次，**这正是最需要锁的地方**。
- ✅ 推导完再跑一次确认与实现一致；**若不一致 ⇒ 立刻停下上报**（那意味着实现真有问题，
  比补锁重要得多，⛔ 不要自行改任何一边去凑）。

### 顺带（同一文件，低成本）
端到端的宽高对账**只覆盖垂直面**（79/115，36 个水平面被判据排除，因为 `~Width`/`~Height`
对水平面语义不同）。⇒ **⛔ 本单不要求补端到端水平面对账**（成本高、判据需另设计），
但请在执行日志里**如实登记这条仍未覆盖**。

---

## 2. 任务二（F-12 MINOR）：给 `VERTEX_FRAME_DRIFT` 行为门补**单元锁**

### 事实

F-12 的锁（`tests/test_f12_surface_prompt_transcribe.py`）**全是 prompt 字符串正则锁**。
GLM neuter B 实证：注入一句**换了措辞但语义仍命令 LLM 重算**顶点的话
（例："for each wall you may independently derive vertex Z values from the owning zone's
floor elevation and storey height as a check"）⇒ **5 条锁全绿，绕过。**

⇒ prompt 正则锁只能当「防倒退到具体旧措辞」的信号。**真正的防线是 `VERTEX_FRAME_DRIFT` 行为门**
（`src/validator/output_coordinates.py`：`_vertex_drift_issues` + `_live_idf_vertex_drift_issues`），
**而那道门目前只有端到端实证、没有单元锁。**

### 要做的

新增单元锁（放哪你定），至少覆盖：
1. **顶点与快照一致 ⇒ 门不报**（阴性对照，防止锁恒红）。
2. **顶点偏离快照（哪怕只是起笔点旋转）⇒ 门报 `VERTEX_FRAME_DRIFT`**，
   断言落到**具体 check-id / 具体面名**，⛔ 不许「数量变了 / 不是 None」。
3. 若成本可控，把 `_vertex_drift_issues`（ConfigState 侧）与 `_live_idf_vertex_drift_issues`（IDF 侧）
   **两条路径都覆盖**；只覆盖一条也可以，但**在日志里说明覆盖了哪条、另一条为何没覆盖**。

⚠️ **不要为了写锁去改生产码的签名或行为。** 若发现结构上无法从单元层驱动该门 ⇒ **停下上报**。

---

## 3. ⛔ 边界

- ⛔ **只改 `tests/`，不改任何生产代码**（`src/`、`scripts/`、prompt 一律不动）。
- ⛔ **不放宽任何门、不改容差、不改 `GlobalGeometryRules` 声明**。
- ⛔ 不碰 `case_tests/` 下未跟踪目录。⛔ 不 push。⛔ 不许 `git add -A`，逐个文件 add。
- ⚠️ `git commit` 若撞 `index.lock`（IDE 后台跑 `git status`）：等释放再重试，⛔ 不许手动删锁。
- 一次性脚本放 `/tmp`。

## 4. neuter 自验（硬纪律）

两个任务各自 neuter：
- 任务一：把**实现**里挑左上角的逻辑改成挑错角（病灶本体，`/tmp` 一次性 worktree 里做），
  确认**新补的手算断言变红**（⚠️ 若只有自指断言红、手算断言没红，说明你的手算值是抄来的，重做）。
- 任务二：把门的比较改成恒不报，确认新锁变红。
- 两次都要**逐字节复原**并在日志里写清红了几条、红在哪。

## 5. 验收

- 全仓零回归：主工作树基线 **2255 passed / 10 xfailed / 0 failed**。
- 执行日志 `AI_agent/logs/reviews/execution/2026-08-07_crossreview_followup_locks_claude.md`。
- 可 `git commit`（`08.07_crossreview_followup_correctness_locks`），⛔ 不 push。

## 6. 停下上报（**记功不记过**）

本轮 **11 次「停下上报」，11 次全是派工方（orchestrator）的题错了**。
本单事实与你看到的不符、或手算值与实现不一致、或结构上做不到 ⇒ **立刻停下如实上报，⛔ 不要硬凑。**
