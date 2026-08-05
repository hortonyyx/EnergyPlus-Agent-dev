# 派工单 · sm21 端到端撞出的判卷缺陷（legacy v2-GT 判卷路径）

- **日期**：2026-08-04 夜
- **派工方**：orchestrator（Opus 5）
- **施工席**：GLM-5.2（本单）
- **审阅席**：Claude 侧子代理（施工完成后由 orchestrator 启动；**谁写谁不批**）
- **缘起**：用户 08-04 晚「先跑 sm21 端到端……有问题就修好（主要调 GLM 侧，GLM 修，你启子代理审）」
- **前置状态**：HEAD `a5ba378`，全仓实测 **2158 passed / 10 xfailed / 0 failed**（本单开工前 orchestrator 独立跑过）

---

## 0. 一句话

**跑 sm21 时判卷层一张卷子都没批，却报了「walls_complete = pass / windows_placed = pass / no_oversplit = pass」。**
根因是判卷的 legacy 分支不认识今天读图产物的外层信封 `{"views": {...}}`，
再叠加「分母为 0 判 pass」⇒ **没批 ≡ 全对**。

---

## 1. 事实与证据（orchestrator 已独立实测，可复现）

判卷有两条路径：**typed v3**（GT `schema_version=3`，如 sm24）与 **legacy**（GT `schema_version=2`，如 **sm21**）。
今天要收的 sm21 走 legacy。

读图产物的当前信封是 **ReadingViews v2**：`{"views": {"1f_view": {...}, "2f_view": {...}, ...}}`
（`src/agent/execution/isolation.py:612` 组装，`src/agent/judge/reading_typed_adapter.py:60 identify_reading_contract` 认它）。
**typed 路径认得，legacy 路径不认得。**

`scripts/tool_scripts/run_stage.py:1236 _score_reading_attempt_output` 把 `output` 的**每个顶层键当成一张图的 stem**：

```python
for stem, view in sorted(output.items()):        # ← 今天只有一个键: "views"
    if not isinstance(view, dict) or view.get("image_kind") not in (None, "plan"):
        continue                                  # "views" 的值是 dict、无 image_kind ⇒ 不跳过
    floor_name = floor_name_for_image(stem, gt)   # stem == "views" ⇒ None
    if floor_name is None:
        evidence.append({... "unmatched_reading_view" ...}); continue
```

⇒ `scores == {}`。

然后 `src/agent/judge/score_policy.py:227 reading_score_criteria` 在**空 scores** 上算出：
`total_walls = 0 ⇒ missed_walls = 0 ⇒ wall_status = "pass"`；
`total_windows == 0 ⇒ window_status = "pass"`；`missed_boundary = 0 ⇒ boundary "pass"`；
`extra_walls == 0 ⇒ no_oversplit "pass"`。

### 决定性 A/B（同一份**已知满分**的历史产物，唯一变量 = 信封）

用 `case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/attempts/001/output.json`
（07-07 那份实测 9/9 · 7/7 的产物，**扁平**形状）跑今天的 `_legacy_score_attempt_output`：

| 喂进去的形状 | 批到几张 | 平面墙 | 平面窗 | headline 判据 |
|---|---|---|---|---|
| **扁平**（07-07 原样） | 2 | **9/9** | **7/7** | 全 pass ✅ 正确 |
| **包一层 `{"views": …}`**（今天的信封） | **0** | 0/0 | 0/0 | walls/windows/oversplit **仍报 pass** ⛔ |
| 今晚 Haiku 产物（原样 = 带信封） | **0** | 0/0 | 0/0 | 同上 ⛔ |
| 今晚 Haiku 产物**手工脱信封** | 2 | **0/9** | **0/7** | severe ✅ 正确 |

（第 4 行同时说明：**读图质量本身另有问题**，那不归本单，本单只修判卷。）

⚠️ 现存的唯一安全网是 `score_evidence_completeness`（`score_policy.py:363`）因为
`"views"` 这个键映射不到楼层而报了 severe —— **它是撞巧命中的**，
不是「没批到卷子」这件事本身的检查：evidence 为空时它根本不出现。

---

## 2. 要修的两条（都要修，缺一不可）

### F-1a · legacy 判卷路径必须消费当前读图信封

- **入口**：`scripts/tool_scripts/run_stage.py::_score_reading_attempt_output`
  以及 legacy 侧其余同源消费者 —— 至少还包括同文件里 `_legacy_score_attempt_output` 传给
  `score_reading_elevation_views(output, ...)` 的那个 `output`，以及 legacy 判卷图渲染
  （`_grade_attempt_artifacts` / `_render_all_attempt_grades` 一路）。**逐个查实，别只改一处。**
- **修法要求**：
  - **只在一个地方归一化**（拿 `identify_reading_contract` 判定，认出 ReadingViews 信封就取 `raw["views"]`，
    否则维持原扁平语义）—— ⛔ **不许在多个消费点各写一份脱壳逻辑**（第二把尺子）。
  - ⛔ **不得改动 typed v3 路径**的任何行为（sm24 那条线一字节不许变）。
  - ⛔ **不得改动 `case_tests/` 下任何既有产物**（历史 run 是证据）。

### F-1b · 「一张没批」永远不许读成 pass

- **入口**：`src/agent/judge/score_policy.py::reading_score_criteria`
- **判据（写死）**：**`scores` 为空** ⇒ `walls_complete` / `windows_placed` / `boundary_complete` /
  `no_oversplit` 一律**非 pass**，且 evidence 里写明原因（建议 `no_data`：「没有任何视图被判卷」）。
- **⚠️ 必须区分两件事**，别一刀切：
  - 「**GT 本来就没有窗**」⇒ 合法，维持现状（不是本单要改的）；
  - 「**一张卷子都没批到**」⇒ 非 pass。
- 判据只认 `scores` 是否为空这一个机械事实，不要发明启发式。

---

## 3. 锁的要求（本项目血泪，逐条硬性）

1. **每条修法必须有「摘掉即红」的锁**。⛔ 探针不算锁（探针不具回归效力）。
2. **⭐ neuter 变红只证明「实现被调用了」，不证明「判据有分辨力」** ——
   F-1b 属判据类，**必须四格实测**：
   | | 好产物 | 坏产物 |
   |---|---|---|
   | **带信封** | 判 pass | 判 severe |
   | **扁平** | 判 pass | 判 severe |
   外加第五格：**空 scores ⇒ 全部非 pass**。
3. **载荷必须真实量级 + 真实形状**：用 sm21 真实规模（2 层 · 9 段墙 · 7 个窗 · 15 个立面窗）构造夹具，
   ⛔ 不许用退化 fixture（2×2 之类）—— 08-04 已在这上面栽过。
4. **自己跑一遍 neuter**：把 F-1a 的归一化摘掉 ⇒ 恰好对应的锁红；把 F-1b 的判据摘掉 ⇒ 恰好对应的锁红；
   **零连带、零假锁**。把两次 neuter 的实测输出（红了哪几条）写进交付简报。
5. **全仓**：交付前跑一次 `python -m pytest -q -n auto`，报出 passed/xfailed/failed 三个数字。
   基线是 **2158 passed / 10 xfailed / 0 failed**，只许增不许减。

---

## 4. 交付物

1. 代码改动（`scripts/tool_scripts/run_stage.py` + `src/agent/judge/score_policy.py` + 新测试）；
2. `git commit`（信息仿 `08.04_<英文标签>`，body 写①改动②为何此刻③影响）；**⛔ 不要 push**；
3. 交付简报落 `AI_agent/logs/reviews/execution/2026-08-04_sm21_legacy_scoring_envelope_glm.md`，含：
   - 逐条改了什么、为什么这样修；
   - **两次 neuter 的原始输出**（哪条锁红了、有没有连带）；
   - 四格矩阵的实测结果；
   - 全仓三个数字；
   - **诚实披露**：没做到的、绕过的、不确定的（本项目对「诚实交接」有正面样板，伪造自查表是最重的问题）。

## 5. 边界

- ⛔ 不碰 typed v3 判卷、不碰 gt 文件、不碰 `case_tests/` 既有产物、不碰识图侧（读图质量另案）。
- ⛔ 不许为了让分数好看去动容差。
- **有异议就停下上报**：本项目 08-04 两次最高价值的修正都来自「施工席发现派工方的题出错了」——
  如果你认定本单的判据有问题，**写清理由停下**，不要硬凑一个假锁。
