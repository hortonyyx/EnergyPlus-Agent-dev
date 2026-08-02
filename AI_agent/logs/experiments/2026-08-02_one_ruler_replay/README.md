# 2026-08-02 · 同一把尺子回放：07-07 老产物 vs 08-02 新产物 + 立面通道恒零缺陷

- **主控**：Opus 5
- **零代码改动**（生产码未动；本轮全部是离线重判 + 两次「只改一个字段」的对照实验）
- **缘起（用户 2026-08-02）**：
  > 「之前既然能做到稳定全对，那一定是有正确的做法的，不应该是现在这个水平，
  > 我还是觉得不是能力波动，应该是机制出问题了。」

---

## 0. 一句话结论

**用户的判断被硬数据坐实，而且比预想的更严重：**

1. **07-07 那份老产物，用今天的生产尺子重判 = 墙真的全对**
   （内墙 57.86/57.86 · 外轮廓 60/60 · **多画 0 m**），而今天 Sonnet 全卷是 92.1 % + 多画 6.77 m。
   **⇒「量纲不可比」这条挡箭牌今天被拆掉了**：同一把 v3 尺子、同一份 GT、同一套容差、同为全卷五张。
2. **⛔ 新查出的机制缺陷 M-7（本轮最重）：立面通道对任何产物恒为零。**
   读图器按 `guide.md` 老老实实写 `facade.mirrored = "unknown"`（该值是 guide 明列的合法值），
   判卷适配器把 `"unknown"` 映射成 `None`、与 binding 的 `false` 一比不相等，
   **判定为「帧向不一致」并把该立面的所有观测整批丢弃**（`retain_as_miss`）。
   四张立面全部中招 ⇒ 平面说 complete、立面被判 miss ⇒ 聚合成 `conflict` ⇒ 开口全项 0 分。
   **只把这一个词从 `"unknown"` 改成 `false`（几何一个数不动）：两份产物的窗都变成 11/11 全 complete。**
   ⇒ 08-02 上一份报告里「窗是墙之外唯一的真缺口」「平面窗连续三轮全崩」**结论作废**，那是尺子砸的。

---

## 1. 实验设置（可复现）

| 项 | 值 |
|---|---|
| 尺子 | 今天的生产 v3 typed 路由：`scripts/tool_scripts/score_reading_vs_gt.py --typed-elevation-json … --bindings … --gt-file … --view-manifest …` |
| GT | `case_tests/test_baseline/gt/sm24_anchor/gt.json`（`reference_ledger_sha256 = 72f866b9…`） |
| bindings / view_manifest | 取自 `run_2026-08-02_sonnet_full_unsup/_run/`（**全卷五张，无减卷**） |
| 容差 | 判卷配置默认档，与 08-02 记录 run 相同 |
| 产物 A（老） | `run_2026-07-07_haiku_cv_probe/0_reading/attempts/001/output.json`，sha256 `ef2bc074a4b1458c…`（已核：与该 run 顶层五个 `*_view.json` 逐字节同源，未被改过） |
| 产物 B（新） | `run_2026-08-02_sonnet_full_unsup/0_reading/attempts/001/output.json`，sha256 `dbf3341ceafc8c36…` |
| 自校验 | 用同一条命令重判产物 B ⇒ **53.31/57.86 与已落盘的 `score_vs_gt.json` 逐字相同** ⇒ 调用姿势正确 |

两份产物的 `identify_reading_contract` 都是 `reading_views_v1` ⇒ 同一契约，可以进同一把尺子。

### 1.1 一处必要的等价改写（老产物）：补 `scale_origin`

老产物**原样**进今天的尺子 ⇒ **十项判据全 0.00**（`walls_complete 0/57.86`、`boundary 0/60`、
甚至 `no_extra_walls` 因为分母 0 而 `not_applicable`）。原因不是画得差：
**`scale_origin` 这个字段是 07-31 才立的契约**（`68fd6d0` / `13cc33a`），07-07 的产物只有等价信息写在
`calibration_note` 自由文本里，而 gate② 只从 `scale_origin.world_x_m/world_y_m` 重建 local→world 帧。

- 该行为**是已知的、写在代码注释里的设计**（`src/validator/checks/reading.py:628` 明写
  "a silent zero that reads exactly like a bad drawing"），并且 gate① 有 `reading.plan_scale_origin_usable`
  在 `golden`/`regression` 档硬拒。**不作为新缺陷登记。**
- 但它正是**为什么此前没人能把老产物重新量一遍**——回放老件必然得到「全 0」，看上去像老件很烂。

回放时补的值取自**产物自己的** `calibration_note`：
`origin = SW outer corner @ px(248,878)`、`envelope 10.00 × 20.00 m` ⇒ `world_x_m = 0.0, world_y_m = 0.0`，
与 08-02 新产物声明的 `scale_origin` 完全一致（两份产物 stroke 包围盒都是 `0..10 × 0..20`）。
**几何一个数没动。**

---

## 2. 结果一：同一把尺子下，老产物墙面全对

| 判据 | **07-07 Haiku + CV（老做法）** | **08-02 Sonnet 全卷无监督（今天）** |
|---|---|---|
| `walls_complete`（内墙） | **57.86 / 57.86 = 100 %** | 53.31 / 57.86 = **92.1 %** |
| 线段行状态 | **20 行全 `complete`（精确命中，零 within_tolerance）** | 6 `complete` + 12 `within_tolerance`（偏 0.06–0.07 m）+ **3 `miss`（4.55 m）** |
| `boundary_complete`（外轮廓） | 60 / 60 `pass` | 60 / 60 `pass` |
| `no_extra_walls`（多画） | **0 m（无多画，分母 0）** | **6.77 m（8 行 `extra`）** |
| `window_plan_geometry` | 22 / 22 `pass` | 22 / 22 `pass` |

**今天丢的 92.1 % 不是丢在那 0.06 m 上**（那 12 段在容差内、照样计入通过），
**是丢在漏画的 3 段上**：`(4.18,3.44)-(5.82,3.44)` 1.64 m、`(5.82,3.44)-(5.82,4.94)` 1.50 m、
`(5.82,4.94)-(10.0,4.94)` 1.41 m —— 右下那个小房间的三面墙整体没画；外加多画 6.77 m。

### 2.1 两份产物的做法差别写在 provenance 里

| | 07-07（老） | 08-02（今天） |
|---|---|---|
| 平面墙 stroke 数 | **14** | 10 |
| provenance | **`dimension_derived` 13 / `seen` 1** | **`seen` 10 / 10** |
| 每条的 `dimension_refs` | 最多 12 条，含 8/11/6/12 这种成串引用 | 最多 2 条 |
| CV 证据文件 | **38 份**（其中平面 19 份） | 38 次探针 / 198 条访问记录 |

老产物是**从尺寸链算出每一条墙的坐标**（所以精确落在 DXF 导出的 GT 上、零偏差）；
今天是**看着画**（`seen`），于是整体偏 0.06 m（≈120 内墙半厚，正是 07-08 就登记、至今未收口的
「尺寸基准 = 轴线还是墙面」），并且漏了一个房间、多画 6.77 m。
**⇒「量而非看」这条老结论在产物层面是成立的，而且今天这轮没做到。**

### 2.2 ⚠️ 但「无监督全对」仍然没有被证明

老 run 的 `llm.yaml` 溯源逐字写着：Haiku 4.5 + CV 工具箱 · **prompt 级隔离**（硬隔离 07-08 才落，在这次识图之后）·
**2 轮 rework（纪律 1 次 + schema 1 次）** · judge off · 当时 sm24 **还没有 GT**（人工肉检验收）。

**⇒ 可以断言的是：「正确的做法存在，并且它产出的东西按今天的尺子是全对的」**（用户的原话成立）。
**不能断言：「那份全对是零监督拿到的」**——它吃了两轮返工。两件事互不矛盾，
下一步要复现的是**那条做法**（逐条从尺寸链推导 + 逐候选放大核验），不是那次监督。

---

## 3. 结果二：⛔ M-7 立面通道对任何产物恒为零

### 3.1 现象

两份产物（一份墙 100 %、一份 92.1 %）的**窗口判据逐字相同**：

```
existence 11/11 conflict · along 11/11 conflict · width 11/11 conflict · sill 11/11 miss · head 11/11 miss
windows_placed 0/11 fail · window_elevation_geometry 0/44 fail
```

`claim_summaries` 的哈希在两份产物之间**完全一致**（`017788ac96bcc5cf`）
⇒ **开口通道对产物质量的分辨力 = 0**（gate① 分辨力=0 的同族第六例，只不过这次在判卷层）。

### 3.2 根因（一行）

`src/agent/judge/reading_typed_adapter.py:273 _facade_sense` 把 `mirrored: "unknown"` 映射为 `None`；
同文件 `:873` 拿它与 binding 的 `mirrored=False` 比较，`None != False` ⇒ 进
`elevation_local_x_sense_disagreement` 分支 ⇒ `_na_components(..., denominator_disposition="retain_as_miss")`
**在读 strokes 之前就 return**，该立面的窗一条都不进匹配。

判卷 sidecar 里的证人逐条自证——**分歧只在 mirrored 这一项**：

```json
{"source_input_id": "South_view",
 "binding_local_x_positive": "image_left_to_right",
 "product_local_x_positive_effective": "image_left_to_right",   ← 一致
 "binding_mirrored": false,
 "product_mirrored_raw": "unknown", "product_mirrored_effective": null,   ← 唯一分歧
 "reason": "elevation_local_x_sense_disagreement"}
```

### 3.3 三处互相打架的口径

| 位置 | 说法 |
|---|---|
| `skills/…/0_reading/guide.md:351` | `mirrored` — `true` \| `false` \| **`unknown`**（**合法值**） |
| `guide.md:355` | 读图器**不得**声明世界轴 / 符号 —— 世界落位是 correction 的活 |
| `scripts/tool_scripts/score_reading_vs_gt.py:87` | *"Product-provided mirror/local-x declarations **are not read**; projection is entirely from reviewed bindings."* |
| 实际代码 | 不但读了，而且**读到 `unknown` 就把整张立面的观测扔掉** |

⇒ 读图器**照文档做**（写 `"unknown"`、把镜像留给 correction 判）**就一定被判零**。
两份产物的 `orientation_evidence` 都明写「图上没有左右罗盘标注，`mirrored=unknown` 是诚实而非假设」。

### 3.4 判决性对照（只改这一个词）

把两份产物四张立面的 `facade.mirrored` 从 `"unknown"` 改成 `false`，**其余一个字节不动**，重判：

| | 老 07-07 | 新 08-02 |
|---|---|---|
| `elevation_local_x_sense_disagreements` | 4 → **0** | 4 → **0** |
| `windows_placed` | 0/11 fail → **11/11 pass** | 0/11 fail → **11/11 pass** |
| `window_elevation_geometry` | 0/44 fail → **44/44 pass** | 0/44 fail → **44/44 pass** |
| existence / along / width / sill / head | 全 conflict/miss → **各 11/11 `complete`** | 同左 |
| 墙面各项 | **不变** | **不变** |

**⇒ 两份产物的窗本来就是全对的**（例如 North 立面窗 local `[0.54, 5.34]`，
按 binding `along_origin=10, sign=-1` 投影 = `[4.66, 9.46]`，与 GT 目标区间**逐字相同**）。

### 3.5 波及范围（结论回收）

- **08-02 上一份报告 §1.2「窗是墙之外唯一的真缺口 / 平面与四个立面互相矛盾」——收回**：
  不是产物矛盾，是「缺观测」被编码成了「有分歧」。
- **07-30 / 08-01 / W5「平面窗 0/11 连续三轮全崩」——需要按本条重判后再下结论**。
- 该分支属 `cause_class="trusted_frame"` 却 `retain_as_miss` ⇒ **判卷器自己的口径问题被记到被测者头上**。

---

## 3.6 ⛔ 追加（同日晚，核 GPT 侧报告 §3.6 时查出）：gate① 这次**有**分辨力，是档位没进去

GPT 侧报告 [2026-08-02_reading_regression_controller_cv_investigation.md](../../reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md) §3.6.1
指出「hard-isolation merge 未传 `capability_profile` / `run_profile`」。**主控独立核实，后果比报告写的更重：**

- `run_config.yaml` 声明 `capability_profile: orthogonal_polygon`，CLI 承载 `run_profile = regression`（fail-closed）；
- 实际落盘 `attempts/001/checks.json` 头部 = **`capability_profile: rectangular` · `run_profile: exploratory`**；
- 该 run 的 gate① **本来就抓到了 5 条 fail**（`dimension_chain_closure` ×4：1f + East/North/South；
  `stroke_dimension_consistency` ×1），全部 `cross_check` 层；
- 用 `CheckReport.blocking()` 按两种档位各算一遍（只改档位、结果集不动）：
  **`exploratory` ⇒ 0 blocking · `regression` ⇒ 4 blocking**（四条 `dimension_chain_closure`）。

**⇒ 两条结论要改口径：**
1. **「gate① 对识图质量分辨力 = 0」不准确**（此前已「五次坐实」）。准确说法是
   **「严格档从未真正执行过」** —— 这一轮严格档若真的生效，产物会被**当场拒收**。
2. 它抓到的**正是** §2.1 那条：今天这轮的墙是 `seen` 画的、**尺寸链不闭合**；
   老产物 13/14 条 `dimension_derived`。**gate① 的信号与本轮 provenance 分析指向同一个病灶。**

同时证实报告 §3.6.2：`_run/view_manifest.json` 五张视图**全部** `dimensioned: false`
（而 sm24 图纸带完整尺寸链、产物自己就抄了 48–51 条 dimension）⇒
`dimensions_present` / `dimension_p1a_fields` / `dimension_derived_refs` 等在 31 条 N/A 里占大头。

---

## 4. 建议的下一步（未动手，待拍板）

1. **先修 M-7**（判卷层，属生产码 ⇒ 走施工席 + 升一档审，不由主控直接改）。修法有两个方向，
   建议**取后者**：
   - a) 把 `unknown`/缺失当作「产物未声明 ⇒ 以 reviewed binding 为准」放行；
   - b) **彻底兑现那句注释**：产物的 `mirrored` / `local_x_positive` 判卷侧根本不读，投影只认 binding
     （与不变量「世界落位归 correction」一致）。**必须配摘掉即红的锁**，
     且锁要断言「`unknown` 的产物照常出分」这一条。
2. **把 07-30 / 08-01 / W5 的历史产物按同一把尺子 + 修好的适配器全量重判一遍**——
   现有的「窗全崩」系列结论全部建立在这个缺陷上。
3. **墙侧的真差距**（今天漏一个房间 3 段 + 多画 6.77 m）才是剩下要解的题；
   对照组已经有了：老产物 13/14 条 `dimension_derived`、38 份 CV 证据。
4. **`scale_origin` 之外，回放老件应有一条正式通道**（现在要靠手工补字段），否则「拿历史达标件当对照」这件事
   每次都得重做一遍今天的活。
5. 「尺寸基准 = 轴线还是墙面」（07-08 登记至今）——今天又出现一次，12 段 0.06 m 全卡在这上面。

---

## 5. 证据

| 文件 | 内容 |
|---|---|
| `evidence/score_old0707_asis.json` | 老产物补帧后、`mirrored` 原样（`"unknown"`）的判卷 sidecar ⇒ 墙 57.86/57.86、窗全 conflict |
| `evidence/score_old0707_mirror_false.json` | 同上但 `mirrored=false` ⇒ 窗 11/11 全 complete |
| `evidence/score_new0802_asis.json` | 新产物原样重判（复现已落盘的 53.31/57.86，校验调用姿势） |
| `evidence/score_new0802_mirror_false.json` | 新产物仅改 `mirrored` ⇒ 窗 11/11 全 complete、墙不变 |
| `evidence/replay_input_old0707_framefilled.json` | 老产物 + 补 `scale_origin` 的回放输入（几何未改，补值出处见 §1.1） |
