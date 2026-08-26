# 派工单 · G1：gt「原始层」变成可读、可复现的一层

- **日期**：2026-08-27　**施工席位**：**Claude 家族**（独立 worktree）　**审阅席位**：**GLM 家族**（⛔ 谁写谁不批）
- **档位**：工程档（碰 `src/agent/judge/` = 成绩产出路径）⇒ **审恒升一档**
- **起点 commit**：`ed0ba09`（分支 `08.23_AsDrawnReading`）

## 〇、你的工作目录（⛔ 写死）

```
/tmp/ep_g1        ← 已建好的 worktree，分支 wt/08.27_gt_raw_layer，起点 ed0ba09
```

- ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev`（主树）改任何文件、不许在主树跑全量。**
  主树上同时还有两个别的席位在跑（一个改 `src/agent/pipeline.py`、一个在审 `src/validator/`）。
- 跑测：在你的 worktree 里 `python -m pytest -q -n auto`（`pythonpath=["."]` 会取**你这棵树**的 `src`）。
  ⛔ **裸跑脚本会静默串到主树代码**（共享 venv 的 editable `.pth` 硬编码主树 = 已登记 F-94 / 债 D-2）
  ⇒ 一律 `python -m <module>` 或 pytest。
- 开工自检：`git -C /tmp/ep_g1 log --oneline -1` = `ed0ba09`；`grep -c '' AI_agent/CLAUDE.md` = **447**。
  对不上就停下上报。

## 一、这件事在盘面上的位置（读懂再动手）

用户 2026-08-26 定的四步：**① 把判分修好 → ② 按新方案改造 reading+correction 的 harness →
③ 产出新产物 → ④ 一步步验证**。当前在 **①**，而 ① 里 **gt 侧一步没动**。

用户同日第 12 条口径（原话转述）：**gt 分三层** ——
**原始层**（忠实转录、含图纸自身的偏差）+ **不规整清单**（显式产出）+ **派生答案层**
（换一种出模形式只需重新派生、**不必重新签字**）；**来源空间的答案从 DXF 机械生成，⛔ 不人工标注**。

⭐⭐ 且已定：**gt 修正是 reading/correction 一体改的【前置】，不是后续。** 本单是这条前置的第一块。

⛔ **本单与任何 case 的 reading/correction 产物无关**。旧 sm25 产物已被用户判为「不再作验收对象」。
本单只碰 **gt 生成侧与 gt 读取侧**。

## 二、orchestrator 已核实的事实（⛔ 请你独立复核；发现任何一条不成立 ⇒ 停下上报）

1. **原始层的数据已经在盘上了。**
   `case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json` 里，**29 个 zone 共 136 条边**，
   每条都带 `basis`（`wall_axis` 90 条 / `outer_skin` 46 条）+ `thickness_m`（0.12 共 78 / 0.24 共 58）
   + `offset_m` + `source_handles`（真 DXF 句柄）+ `thickness_evidence`。
   ⇒ 已登记的 **R-6**「量了、用掉了、存盘时扔了」这句话**需要更正**：
   **实际是「存盘了，但没有任何判分路径读它，而且它不在人工签字覆盖范围内」。**
2. **它没有被签字覆盖。** `src/agent/judge/tarch_review_bundle.py` 的 `_RUNTIME_BUNDLE_FILES`
   **显式把 `conversion_report.json` 排除在 `review_index.json` 的 files 清单之外** ⇒
   人工签字 `review_ack.json` 覆盖不到它。
3. **签字链本身是完好的**：`review_index.json` 的 `inventory_sha256`
   与 `review_ack.json` 的 `review_index_sha256` 我实算过，**一致**（`490655...`）。
   ⚠️ 注意它签的是 **files 清单的规范化摘要**，不是 `review_index.json` 这个文件自身的 sha256。
4. `src/agent/judge/gt.py:load_gt` 是**唯一合法的 gt 读取口**（gt 铁律，CLAUDE.md §1.5#4：
   gate① / 执行器**绝不 import**，只有 gate② judge 与人可读）。
5. `src/agent/judge/as_drawn/denominator.py` 已经在做「**从转换器自己的收集通道**（`run_p1_plan_view`）
   取出这张图上所有墙面线，按 D1–D5 规则得到可评分目标」，⛔ 且刻意不第二次重新定义「什么是墙线」。
   但它是**每次现算**的，没有作为一层落盘。

## 三、要做的三件

### G1-a　原始层的读取 API

在 `src/agent/judge/` 下给出一个**原始层读取入口**（命名你定，但要与 `load_gt` 同一把锁：
只有 gate② judge / 人可 import；⛔ 不得被 gate① 或执行器 import）。
返回 **typed** 对象（复用已有的 `ZoneEdgeReportV1` / `ConversionReportV1` 就好，
⛔ 不要新造一份平行 schema），至少能拿到：逐 zone 逐边的 `p1/p2/basis/thickness_m/offset_m/source_handles`。

### G1-b　⭐⭐ 机械复现门（本单的真正价值所在）

因为这一层**不在人工签字里**，它的可信度只能来自「**从已签字的源 DXF 机械复现得到同样的内容**」。
⇒ 写一道**复现门**：从 `review/source.dxf`（其 sha256 已被 `review_ack.json` 签过）
+ 冻结的 `request.json` / `manifest.json` 重跑转换器，与盘上的 `conversion_report.json` **逐字段比对**。
不一致 ⇒ **响亮失败，并指名是哪条边的哪个字段**。

⛔ **比内容字段，不比字节。** 已登记事实：转换器输出依赖 Python 哈希随机化 ——
同输入同代码跑两次，**规范化 DXF 的字节与 `content_sha256` 戳会不同**，但**答案内容跨 5 个种子恒定**。
⇒ 比字节必然假红。

⭐ **两种红必须能分开**：
- 「**实现漂移**」（转换器代码变了 ⇒ 复现出来的东西与盘上不同，但盘上那份仍是当初正确的）
- 「**内容不一致**」（同一实现下复现不出来 ⇒ 盘上那份可疑）

⚠️ 如果你发现这两种红在现有信息下**分不开**，停下上报 —— 那可能是我题面要求过多。

### G1-c　把「未被签字覆盖」变成显式声明

现在「这一层没有人工签字」这件事，只有读 `_RUNTIME_BUNDLE_FILES` 的代码才能知道。
⇒ 让读取口在返回原始层时，**显式带上它的信任根是什么**（= 复现门的结论 + 被签字的源 DXF sha），
而不是让下游默认「从 gt 目录读出来的就是签过字的」。
⛔ 降级（复现门没跑 / 跑不通）必须**显式**，⛔ 不许静默当成通过
（同族教训：`grep … || echo 通过` 把「文件不存在」读成「检查通过」）。

## 四、⛔ 明确不做（超出即停下上报）

- ⛔ **不改 `gt.json`**，不改 `review_index.json` 的签字文件集合，**不重签**（重签是用户的动作）。
- ⛔ **不碰 `src/validator/data_model.py` / `src/validator/checks/kernel.py` /
  `tests/test_f95_*` / `tests/test_f13_*`** —— F-95 正在跨家族审，动了那轮审就作废。
- ⛔ **不碰 `src/agent/pipeline.py`** —— 另一个席位正在改 F-97。
- ⛔ 不改任何判分口径、容差、评分规则。
- ⛔ 不做 G2（面线集合落盘 + 不规整清单）—— 那是下一单，等本单的 API 形状定了再排。
- ⛔ 不去跑任何 case、不产 reading/correction 产物。

## 五、验收判据（每条我都自查过「什么情况下它会不通过」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| A1 | 在 sm25 上，原始层读取 API 返回 **136 条**带 basis 的边，basis 直方图 = `wall_axis 90 / outer_skin 46`，厚度直方图 = `0.12×78 / 0.24×58` | 读错文件、或把 `basis=None` 的厚度变化 step 边也算进来了 |
| A2 | 复现门在**未改动**的树上跑 **绿** | 转换器本身不确定，或复现输入没冻死 |
| A3 | ⭐ **分辨力实测**：把 `conversion_report.json` 的**临时副本**里任意一条边的 `thickness_m` 从 `0.12` 改成 `0.13`，复现门必须**红**，且**指名那条边** | 门只比总量/哈希、不逐边比 ⇒ 抓不住单点篡改 |
| A4 | ⭐ 两种红可区分：故意让实现哈希漂移一位，门报的是「实现漂移」而**不是**「内容不一致」 | 两种失败被压成同一个空白（同族：缺席会把多种原因压成同一个信号）|
| A5 | 全量绿：`python -m pytest -q -n auto`，**三数报出来**（`test_zone_agent.py` 缺 API 凭据是已知环境坑，不算回归）| 有回归 |
| A6 | ⭐ **neuter 实测**：摘掉你新加的门，你新加的锁必须**红**，且**只红它**（定向变红）| 锁没接到真实入口 / 恒绿 |

⛔ **A5 不得单独作为通过标志** —— 全量在缺陷存在时也曾全绿（F-95 就是：凹多边形被毁一个月，
已有的 L 形锁没有分辨力，因为 L 形恰好是无损的那一半）。

## 六、⛔ 停下上报触发器（任一命中就停，⛔ 不许自行扩路）

1. §二里 orchestrator 陈述的**任何一条事实不成立**（⭐ 尤其第 1 条那些计数）；
2. ⭐ 你发现除本单给的做法外，还有**严格更优**的第三条路
   —— **这条明确算触发器**：派工单的选项清单本身就是个没人签字的前提；
   本项目「停下上报」累计 **35 次全部是派工方（我）题错**，你顶回来是正常产出不是失败；
3. 要动 §四「明确不做」里的任何一项才能完成；
4. **复现门跑不通，且原因指向转换器本身不确定** —— 那是另一个缺陷，不是本单；
   ⛔ **不许为了让它一致去调任何参数或容差**。

## 七、⚠️ orchestrator 自认的最弱一点（请优先证伪）

**我假设「从 `review/source.dxf` + 冻结的 request/manifest 能确定性重跑出同一份 conversion_report 的内容字段」——
我没有实跑验证过。** 这是本单最可能塌的地方。
若跑不出来，请把**实际差异**摆出来停下上报（§六#4），⛔ 不要为了让它一致去调参数。

## 八、交件形式

1. 施工报告写到你 worktree 的
   `AI_agent/logs/reviews/execution/2026-08-27_g1_gt_raw_layer_construction_report.md`：
   ⛔ 只写**做了什么 + 每条判据的实测读数 + 你自己认为最不确定的地方**；⛔ 不写长篇心路。
2. 在你的分支上 `git commit`（message 仿 `08.27_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响）。
   ⛔ 不要 push、不要合并回主分支 —— 由 orchestrator 审完再定。
3. 把施工报告全文 + `git show --stat` 贴回给 orchestrator。
