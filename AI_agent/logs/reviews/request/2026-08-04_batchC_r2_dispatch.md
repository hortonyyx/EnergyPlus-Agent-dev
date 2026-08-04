# R1 批 C · r2 返工派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-04（北京时间 16:00）
- **前置**：HEAD 已含批 C r1 七条 + 批 D/R4-a 合并。**批 C 未收口。**
- **上游**：[r1 交叉审](../verdict/2026-08-04_reading_ruler_batchC_r1_crossreview_claude.md)
  （**APPROVE-WITH-CHANGES：0 BLOCKER / 2 MAJOR / 3 MINOR / 2 NIT**）· [r1 派工单](2026-08-04_reading_ruler_batchC_r1_rework_dispatch.md)（边界继续有效）

---

## 0. 先说清楚：上轮 BLOCKER 你确实修好了

交叉审**真 CLI 驱动六条真实路径**（flat-flow 直跑 / 五图健康 flat-flow / `resample` 盲重读 /
真实历史隔离 merge 聚合件 / pre-O-1 重渲 / 错名），**无一复现**；
「健康 run 被反过来拒批」**证伪失败**；**12 处 neuter 零假锁**；**N-2 的裁定它也证伪失败**（维持不补）。

**本单两条 MAJOR 不是 B-1 复发，而是 M-3 / N-3 这半边交付得不完整。**

---

## 1. ⛔ 必修（2 条，均须在批 C 收口前闭掉）

### X-1（MAJOR·**本批引入的回归**）N-3 删掉了「像素化尺寸端点」的最后一个探测器

- **位置**：`scripts/tool_scripts/render_vector_to_png.py:107-126`（拒绝条件改成只看米制单边）
  + `:65-80`（`_collect_points` **仍把 dimension 端点算进画幅**）
  + `src/validator/checks/reading.py:319`（`_ocr_anchors_in_bounds` **只查 `ocr_texts`**）
- **orchestrator 已独立复现（逐字对上交叉审的数字）**，载荷 = 10×8 m 结构 + 一个像素化尺寸端点 `from=[360,450]`：

  | 版本 | 结果 |
  |---|---|
  | `d0e33ef`（N-3 之前） | `CanvasBudgetExceeded: canvas 16560x20385 (337575600 px)` ← **3.3 亿像素那个签名** |
  | `57d47ea`（N-3 之后） | **静默渲出 `6373×7845`，零报警** |
  | gate① `regression` 档 | `blocking: []`，尺寸类检查全 `not_applicable` |

- **⇒ 失败场景**：读图器把尺寸标注端点写成像素坐标 ⇒ **渲染器不再报（以前会报）、gate① 从来没报过**
  ⇒ 交给人看的是一张降档失真的垃圾图，**没有任何机器可读信号说它坏了**。
  **这是上轮 F-4 判词的逐字复刻：「移走症状没补检测」，只是换了个字段。**
- **要求**：**gate① 的 bounds 检查覆盖 dimension 端点**（与 `ocr_texts` 同规格：越界 flag、严格档 block、机器可读原因）。
  ⛔ 不许靠「把渲染器改回固定缩放」来解决 —— N-3 拆掉的是一条烤死假设（交叉审 P-8 判它合格），**不要回退**。
- **锁**：上表那份载荷 ⇒ gate① **给出非空 blocking**（严格档）；`neuter` 摘掉 dimension 端点检查 ⇒ **必须红**。

### X-2（MAJOR）M-3 的可信画幅由**被测方自己写的字段**决定

- **位置**：`src/validator/checks/reading.py:333`（`bounds = _image_bounds(view)`）· `:369 _image_bounds`
  · `:405-417 _explicit_image_bounds` · `src/agent/reading/schema.py:120`（`extra="allow"`）
- **失败场景（交叉审实测 fail/blocking=True → pass/blocking=False）**：产品只要**再写一个像素化 dim 端点 /
  一条乱伸的 stroke / 一个未声明的 `image_bounds` extra 字段**，就把可信画幅撑大到包住那个坏 anchor
  ⇒ **M-3 当场失效、不再阻断**。
- **⇒ 这是本项目反复栽的「考生自己填的字段决定这道题考不考」**（`_dimension_derived_refs` 被 `seen` 跳过 = 同族第 N 次）。
- **⭐ 要求（骨架给死，⛔ 不下放给你猜 —— 两种做法后果相反）**：
  > **可信画幅只能取自「先于本次运行就已固定、且被评判方写不了」的第二处记载**
  > —— 即 **`case_data` 源图的真实像素尺寸 + 已冻结的图像指纹**（`view_manifest` 里那份，R1-6 已让它与真实图像字节核对）。
  > **⛔ 不得从产品自己的 `strokes` / `dimensions` / 任何 extra 字段推导画幅。**

  这条与用户 2026-08-04 拍板的判据**是同一条**（[decision_log §5.14](../../decision_log.md)）：
  **只有有外部信任根的东西才配当判定依据。**（交叉审独立给出同一骨架 ⇒ 双向印证。）
- **锁**：产品写入越界 anchor + 试图用上述三种手段撑大画幅 ⇒ **仍然 block**；neuter 摘掉「画幅取自源图/指纹」⇒ 必须红。

---

## 2. ⚠️ 需你判断后回报（不许自行降级，也不许默默照做）

- **X-4**：`spawn_isolated_reader.py:55-60` + `run_stage.py:2329` —— **merge 从不渲染** ⇒ 状态 `missing`
  ⇒ **一张图都没有的 run 被 `approve-review` 直接放行**（交叉审在真实 run 上实测 `✓ review approved`）。
  orchestrator 此前采纳的裁定是「`missing` 不阻断（pre-O-1 历史 run 向后兼容）」，
  但交叉审指出**覆盖面不止历史 run，而是每一个新隔离 run**。
  **你要回答**：`missing` 该不该在「新 run」上阻断？如何与历史 run 区分（有无可靠判据）？**给理由，orchestrator 裁。**

## 3. MINOR（能一起做就做，做不完登记）

- **X-3**：`_fit_scale` 的 `total_fit` 项**摘掉全绿 = 零锁**；且 `L-51` docstring 声称守「pixel budget」，
  实际触发的是**米制单边帽** ⇒ **「声称在守其实没守」第 7 次**。补锁 + 改正 docstring。
- **X-5**：`run_stage.py:2331-2340`（M-1 的 reason surface 删掉全绿）· `:817-819`（manifest 损坏 ⇒ 从阻断静默变放行、全绿）——各补一条锁。
- **NIT**：`MAX_CANVAS_SIDE_PX` 同时当**像素**上限与**米**上限（单位双关）⇒ 拆成两个具名常量。

## 4. 纪律（继续有效，只列硬的）

- 每条锁「摘掉即红、零连带」+ neuter 自查如实登记；**「全仓绿」不构成锁真绑的证据**。
- **锁必须走会踩到该缺陷的那条真实路径**；断言落**具体 check-id 行 / 具体产物字段**。
- ⚠️ 克隆里跑 neuter 必须 `PYTHONPATH=$PWD`；⚠️ **neuter/探针脚本必须逐字命中目标**
  （orchestrator 今天两次、交叉审一次栽在这）。
- ⚠️ **⛔ 别用 `cmd 2>&1 | tail` 判成败** —— 管道会把退出码换成 `tail` 的 0，
  **交叉审今天差点因此在错误的克隆上做完整轮 neuter**。要判成败就看 `${PIPESTATUS[0]}` 或不接管道。
- ⛔ 不 push · ⛔ 不读 GT · ⛔ 不碰 sm24 testdata · ⛔ 不做批 D/E/R1.5 · ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档。
- 做完一件存一件即时 commit（`8.04_BatchC_r2_<条目>_<标签>`）；交付前跑全仓 `pytest -q -n 6`
  （⛔ 不许 `-n auto`、⛔ 永远不许加 `-m`）。**基线以你实跑为准并如实报**（主树现含批 D/R4-a 合并 + 一条待修的 affected-map 白名单红，那条**不归你**）。
- 续写批 C 执行日志新 `## 8. r2` 段。**遇欠规格边界停下上报。**
