# 批 C · r3 返工派工单（施工 = Claude 侧执行档 · 累计式自包含）

- **日期**：2026-08-04（北京时间 20:15）
- **上游**：[sol 独立复核](../verdict/2026-08-04_batchC_r2_and_batchD_R4a_review_sol.md)
  （**REWORK：1 BLOCKER / 2 MAJOR / 1 MINOR**）· [orchestrator 轻门](../verdict/2026-08-04_batchC_r2_orchestrator_lightgate.md)
  · [r2 派工单](2026-08-04_batchC_r2_dispatch.md)（边界继续有效）
- **基线**：全仓 **2148 passed + 10 xfailed 零红**（主树，退出码 0；sol 独立复跑逐字一致）

---

## 0. 先说清楚：这轮不是「你没做」，是「判据没有分辨力」

sol 的核心证伪**orchestrator 已独立复核属实**：

- 测试 fixture 用 **2×2 px** 的合成源图（`tests/test_checks_reading_correction.py:1237` `_write_x2_case(image_size=(2,2))`）
  ⇒ `[360,450]` **被人为保证越界**；
- **真实源图**：`sm24/1f_view.png = 790×1111`、`East_view.png = 2639×931`、`North_view.png = 2890×1651`
  ⇒ `[360,450]` **落在界内 ⇒ 整道 regression gate 放行原始坏载荷**。

**⇒ mutation 变红只证明「代码用了这个 tuple」，不证明「这个 tuple 有分辨力」。**
**orchestrator 的轻门也漏了这一条**（我 neuter 见红即判真绑，没检查 fixture 是否退化）——**记账在我，不在你。**

**⇒ 新纪律（本轮起，写进所有派工单）**：
> **锁的 fixture 必须用真实量级**。判据类检查（bounds / 阈值 / 容差）**必须在仓库真实数据量级上验证有分辨力**，
> ⛔ 不得用「刚好让断言成立」的退化 fixture。

---

## 1. ⛔ BLOCKER · B-1：可信 bounds 把源图**像素**宽高当成**米制** reading 坐标的上下界

- **位置**：`src/validator/checks/reading.py`（`_ocr_anchors_in_bounds` / `_dimension_endpoints_in_bounds`
  消费 `trusted_image_bounds`）+ `src/agent/execution/view_manifest.py:1334 resolve_view_pixel_bounds`
- **实测（sol，主树只读，`run_profile=regression`）**：
  ```
  1f_view.reading.ocr_anchors_in_bounds        status=pass evidence={"bounds": [0.0, 790.0, 0.0, 1111.0]}
  1f_view.reading.dimension_endpoints_in_bounds status=pass evidence={"bounds": [0.0, 790.0, 0.0, 1111.0]}
  ```
  ⇒ **量纲错配**：reading 坐标是**米**，bounds 是**像素**；真实图幅（790–3000 px）远大于坏载荷数值（360/450）
  ⇒ **这个检测放行了它被造出来要抓的那个案例。**

### 要求（骨架给方向 + 必须回报选择理由）

**必须做到两件事**：
1. **量纲一致**：米制 reading 坐标只能与**米制**上界比较；
2. **判据来源仍须是被评判方写不了的**（decision_log §5.14）。

**两条候选路线，⛔ 选哪条要在执行日志给理由**（也可提出更好的第三条，但必须先停下上报）：
- **(a) 米制上界**：用外部可信来源推出该视图的米制范围（例如源图像素尺寸 × 已冻结的标定比例）。
  ⚠️ **风险**：标定/`scale_origin` 目前是产品自己写的 ⇒ **若比例来自产品，等于又回到「考生自己填」** ——
  若走这条，必须说明比例的信任根在哪。
- **(b) 单位异常判据（不依赖外部米制上界）**：判「这个坐标的量级相对本视图其余米制几何是否荒谬」
  （例如锚点数值比结构轮廓范围大一个数量级以上）。⚠️ 这是**内部一致性**判据、不需要外部根，
  但要说明它为什么不会误伤合法的大建筑。

**锁（硬要求）**：
- **必须用真实量级 fixture**：直接使用仓库 `case_data` 里真实源图的尺寸量级（790–3000 px），
  ⛔ **不得再用 2×2 px**；
- 断言 **`[360,450]` 这个原始坏载荷在 regression 档被 block**，且落在**具体 check-id 行**上；
- 另配一条**合法产物不被误伤**的对照锁；
- neuter 摘掉实现 ⇒ 必须红。

---

## 2. ⛔ MAJOR

### M-1 · `reading_mode` 冻结过晚 ⇒ controlled 跑完可改配置、再由同一入口正式记成 autonomous
- sol 实测：controlled 执行**之后**修改配置，`flow --record` 会把它**正式记成 autonomous**。
- **⇒ 这正是 R4-a 要堵的「成绩记错人」原洞，没堵上。**
- **要求**：`reading_mode` 必须在**识图执行时点**冻结（与 run policy 同族：声明→冻结→事后不可改），
  事后改配置**不得**改变已记账的 lane；配摘掉即红的锁（走真实 `flow --record` 入口）。

### M-2 · 源图不可解码时静默回落产品自算 bounds，coverage 仍通过
- sol 实测：hash / manifest 都合法但**图片本身解不开**时，resolver **按 stem 静默漏掉** trusted bounds
  ⇒ 回落产品自算 ⇒ 产品字段重新接管判定基准，而 `reading.view_manifest_coverage` **仍然 pass**。
- **要求**：可信来源**取不到 = fail-closed**（严格档 block、机器可读原因），
  ⛔ 不得静默降级；历史 legacy 路径若要保留容忍，必须**显式标记且不得冒充**。配锁。

## 3. MINOR

- **批 D 标签仍重叠/截断**，且 sol 实测**删掉五类标签后新增测试仍 `5 passed`** ⇒ 那几条锁没绑住标签内容。
  **要求**：补断言到**具体标签文本 / 具体 panel 计数**，并真正修掉重叠与截断。

## 4. 纪律（逐条照做）

- **⭐ 本轮新增（最重要）**：**判据类检查的 fixture 必须用真实量级**；
  **neuter 变红只证明「实现被调用」，必须另证「判据有分辨力」**（给一条真实量级的正例 + 反例）。
- 每条锁「摘掉即红、零连带」+ neuter 自查如实登记；锁走**会踩到该缺陷的真实路径**。
- ⚠️ `/tmp` 克隆里跑 neuter 必须 `PYTHONPATH=$PWD`；⚠️ 探针脚本必须逐字命中目标；
  ⚠️ **判命令成败用 `cmd > log 2>&1; echo $?`**，⛔ 不要用 `| tail`（管道吞退出码）。
- **⭐ 交付顺序（前几轮反复栽）**：**每条改完立刻 commit → 再跑完整全仓 → 再回报**。
  ⛔ 不许「改完等全量再提交」然后停下。
- ⛔ 不 push · ⛔ 不读 GT 答案数字 · ⛔ 不碰 sm24 `testdata_prompt.json` · ⛔ 不做 R1.5/R2 ·
  ⛔ 不动 `AI_agent/` 下除自己执行日志外的管理文档。
- 跑测 `pytest -q -n 4`（⛔ 不许 `-n auto`、⛔ 永远不许加 `-m`）。**基线 2148 passed + 10 xfailed 零红。**
- **遇欠规格边界停下上报**（B-1 的路线选择尤其：若两条都不成立，停下说明为什么）。

## 5. 交付
续写批 C 执行日志新 `## 9. r3` 段。
