# GPT 跨家族设计答复 · 识图与校正一体化（2026-08-25）

- **对应求解单**：[`../request/2026-08-25_reading_correction_unification_design_ask.md`](../request/2026-08-25_reading_correction_unification_design_ask.md)
- **性质**：设计求解答复，⛔ **不是裁决**，⛔ 不构成拍板。定位 = **给 sol 那次架构讨论备料的方案池**。
- **通道**：codex MCP，`sandbox=danger-full-access`，只读边界（它自述未写未改任何文件）。会话 thread `01a03478`。
- **本文是 orchestrator 的转录**（结构与结论逐条保留，出处行号照抄它给的）。

> ⚠️ **求解单本身有疏漏（orchestrator 的错）**：本轮的求解单与
> [`2026-08-26_reading_correction_joint_architecture_discussion_sol.md`](../request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md)
> （上一轮已写给 sol 的讨论稿）大量重叠，而且**重写时把上一轮已经写对的字段写漏了**
> —— 那份稿子 §二 正确列出了 `hypotheses.{opening_candidates, opening_types}`，本轮求解单漏掉。
> **GPT 第一条就抓住了它。** 两份文件今后并存，⛔ 各自定位见开头，不得当成同一份。

---

## 一、它对题设的核验（3 处校正 + 1 处措辞）

| # | 题设怎么写的 | 实际 | 出处 |
|---|---|---|---|
| 1 | 窗引用约束在 `pipeline.py:455-456` | 完整约束跨 **451–461**；计数在 **512**；**真正追加拦截问题在 557** | `src/agent/pipeline.py` |
| 2 | `hypotheses` 字段表（求解单版） | ⛔ **不完整** —— 实物还有 **`opening_candidates`** 与逐洞口的 **`opening_types`**；生产者 `as_drawn_v2.py:617`，实物 `sm25_1f_v2.json:16527` 起。**不纳入新接口 ⇒ 门窗语义仍断线** | 见左 |
| 3 | 「结构零接线」 | ⛔ **只能理解为「零类型化语义接线」**。提示词收集器**实际会读目录里所有 JSON**（`pipeline.py:91-106`），而识图门只检查 `*_view.json`（`evidence_preflight.py:229`）⇒ 真实形态是「**新产物可能被当原始文本塞给模型，却绕过类型化识别与识图门**」 | 见左 |
| 4 | 「量级差 700 倍」 | 60.3/0.088 实为 **685 倍**；「700」只能算量级取整 | kernel probe README:147-148 |

⭐ **第 3 条比原说法更危险**：不是"喂不进去"，是"**可能悄悄喂进去且绕过门**"。

## 二、⭐⭐ 它证伪的那条前提（本轮最有价值的一条）

> **被证伪的**：「新识图只有两条面线，因此校正接口应当直接吃两条面线。」

**最短证伪，不需要跑任何代码**：`sm24_1f_v2.json:24320` 有 **4 个 `solid_band_walls`**
（一条实心带自己就是一堵墙——本项目指南 `reading_correction_split_guide.md:90` 自己写着「一堵墙不一定是两条线」）。
⇒ **任何只接受「两条面线」的接口，会在合法输入上丢掉这 4 堵墙，或被迫伪造不存在的第二张面**，
两者都违反题设自己的信息保真要求。

**它给的修正**（保留「⛔ 不许在识图侧塌成中线」这个判断不变）：

> correction 直接吃**带原始引用的多形态墙证据**；**中线或其他出模基准只在 correction 内由代码派生**。

墙证据的变体：`paired_faces` · `solid_band` · `single_face`（确认是墙面但另一面缺失）·
`axis_trace`（旧识图给的中线）· `ambiguous` / `non_wall`（保留但不进墙几何）。

## 三、接口设计要点

- **契约判别器显式化**：现有判别器只识别 `reading_views_v2`（`src/agent/reading/contract.py:23,33`），
  新入口必须显式增加 `as_drawn_plan_v2`，**未知类型响亮失败**。
- **原始几何不复制成"方便字段"**，只建 `observation_id → 原产物 JSON pointer` 的稳定索引 ⇒ 避免再造 R-6。
- **`spacing_m` 必须由代码从被引用面线重算**；产物里的配对候选只作缓存与审计，⛔ 不作不可复核事实。
- **洞口走同一模式**：原始空档与墨迹组件属观测，`opening_types` 属感知判断；代码只查引用、覆盖、互斥，⛔ 不重新识别门窗。
- **旧识图不伪造两张墙面**：旧墙笔画映射为 `axis_trace`，旧 `window` 笔画映射为洞口语义声明，原 stroke 引用保留。
- **出口仍可沿用 `CorrectedGeometry`**（`correction/schema.py:234` 本来就是收束后的世界坐标几何）
  ⇒ ⛔ 没必要把两面墙一直推到 modelling；必须保真的是 **correction 输入侧**的证据与派生链。
- ⚠️ 它点出的现状距离：**当前提示词仍要求模型直接填世界坐标**（`pipeline.py:365,369,383`）
  ⇒ 目标不是"换提示词字段"，而是把 correction **拆成代码编译器 + 决定模型 + 代码执行器**。

## 四、三拍循环：数据结构与「真歧义」判据

现有 `corrections`/`conflicts`/`unsupported` 只是自由字典列表（`correction/schema.py:243`），⛔ 承载不了循环协议。

**待裁决包**：`packet_hash` · `input_artifact_hashes` · `solver_revision` · `round_token` ·
`provisional_geometry` · `entity_to_observation_trace` · `auto_actions` · `open_items[]` ·
`consistency_results` · **`whole_building_review`** · `previous_decision_hashes`

**每个 `open_item`**：`item_id` · `scope`/`affected_entity_ids` · `kind` · `phenomenon`（**机器重算出的事实**）·
`evidence_refs` · `hard_constraints` · `candidates[]` · `why_not_auto_resolved` · `dependencies`/`exclusions`

**每个候选**：`candidate_id` · **`symbolic_operation`（只能是操作枚举，⛔ 不含坐标）** · `preconditions` ·
`predicted_effects` · `cost_vector` · `reversibility` · `preview_geometry_hash`

⭐ **成本是向量不是加权分**（观测位移 / 声明残差 / 拓扑改动 / 跨层不一致 / 下游退化风险 / 信息丢失），
**只做 Pareto 支配，⛔ 不现场发明权重**。

**真歧义判据**：硬约束筛完唯一 ⇒ 自动执行并记账 · 某候选在全部成本维度支配其他 ⇒ 自动执行并记账 ·
剩多个互不支配且**产生不同拓扑/等价关系/基准** ⇒ 真歧义 · **无可执行候选 ⇒ 也是真歧义**
（类型 `unsupported_or_reperceive`，⛔ 不许随便选最近值）· 只有数值残差且处置由已签规则唯一决定 ⇒ **不是**歧义。

⭐⭐ **强制的 `whole_building_review` 不能省**：模型回复除选候选外，必须能对整栋 provisional geometry
给 `accept` 或**新的结构化 finding**。理由 = 那三个真错（走廊幻墙 / Z 形未分段 / 内墙画穿）**逐条都局部合法**
⇒ **只让模型回答代码预先列出的局部歧义，会原样漏掉这三类错误。**

**收敛/退出**：无未决项 + 一致性通过 + 模型对同一 provisional hash 总体接受。
无进展 / 决策循环 / 陈旧 packet hash / 轮次预算耗尽 ⇒ **响亮退出并留残余清单**，⛔ 不许把最后一次草图当成功产物。

## 五、60.3 mm 该怎么吸收 + 怎么证明吸收了

**位置**：墙语义证据装配完成之后、房间成形/跨层切分/现有确定性吸附之前。

**规则**（⛔ 不是"偏差小于阈值就合并"）：
① 代码生成「墙段等价候选」（同轴 + 厚度相符 + 沿墙连续关系相符 + 上下层拓扑可对应）
② 代码提出至少「保持原位」与「视作同一设计轴」两个处置并报告后果 —— **纯坐标不足以决定**
（引 `plan.md:279`：结构判据已实测大量误报）
③ **模型**总体裁决是否表达同一设计轴
④ 裁决为同轴后**目标坐标由代码算**：有尺寸链/基准就服从它；否则取观测组的**稳健代表值**，
**优先已有观测坐标，⛔ 避免平均出图上不存在的新轴**；仍并列则重新送模型，⛔ 不暗定优先级
⑤ 执行时**两张墙面整体同量平移，保持实测面间距**；⛔ 墙厚模数化是另一项操作，
不许把「位置吸附」与「厚度吸附」揉进一个阈值

⇒ 本件上三段一致指向 16.0600，一段 15.9996 ⇒ 应整体平移到一致轴，
**而不是当前实现产生的 16.03**（现行值与审计见 `kernel_round16/correction_snapped.json:3405`）。
**0.088 mm 走另一条规则**（同墙连续段接缝闭合，依据连续段/共同端点/量具不确定度自动闭合），⛔ 与跨层等价规则不同。

**怎么证明吸收了** —— 成对反事实：原样保留 15.9996/16.0600 的输出**必须不通过** ·
收束为统一设计轴的**必须通过** · 只改墙厚不改轴位的**仍须失败** · 平移后破坏原面间距的**也须失败**。

⭐ **它对 orchestrator 的一处更正（成立，已接受）**：
> 「标准答案抹平后就永远判不出来」**说得过头**。归一化 target **恰恰能**区分「未吸收」与「已吸收」；
> **真正不能做的是只保存归一化 target、覆盖掉原始层**，从而无法证明原图曾存在偏差及变换依据。

⇒ orchestrator 此前对用户的措辞（「gt 要是把 6 厘米抹平就永远判不出来」）**漏写了「只有一层」这个前提**，
已按此更正；随后给出的三层方案本来就规避了该问题，结论方向不变。

**判分前置**：`GroundTruthV3` 只有 zones/boundary segments/openings（`judge/gt_schema.py:164-222`），
但转换报告类型**已经有逐边 `basis` / `thickness_m` / `offset_m`**（`judge/tarch_converter_schema.py:1096`）
⇒ **应把这类原始记录正式晋升为 judge 侧原始层**，⛔ 不是重新手填一张平滑后的 polygon。（= 已登记的 R-6）

## 六、施工次序（先动接缝，⛔ 不先改识图量具、不先改下游造面）

1. **契约判别器 + 双适配器**（旧 `ReadingView` → `axis_trace`；新产物保面线/实心带/单面/歧义变体）
   验收：三份新基线可识别且原始层哈希不变 · 历史 `*_view.json` 仍可走 · 未知/混装契约必须失败
2. **改来源目录与完备性门**：现窗口目录只遍历 `stroke.pen == "window"`（`correction/window_sources.py:313`）
   ⇒ 改成消费统一洞口语义声明，同时保留旧 stroke 适配
3. **correction 内部墙证据 IR + provisional compiler**（纯代码、影子运行，⛔ 先不接模型）
   验收：`sm24` 的实心带不会消失 · 任意派生轴可反查原面线 · **产物中不存在被当成识图事实的中线**
4. **类型化待裁决包 + 模型决定契约**
   验收：模型输出任何坐标**schema 拒绝** · 陈旧 packet hash 拒绝 · 用固定裁决夹具验证那三类错
   **经总体通道进入下一轮**，⛔ 不许用现场 LLM 成功率替代契约验收
5. **代码执行器 + 有限循环**（同输入同决定 ⇒ 相同几何与审计）
6. ⭐ **先建独立判尺、再实现正规化**：gt 原始层 + 显式等价声明 + 派生 target 先落，再实现 60.3 mm 的处置；
   验收用第五节的反事实矩阵，并**证明 0.088 mm 走的是不同规则 id**
7. **切全链与历史回归**：先 sm25，再 sm24 与旧识图案例；
   最终验收**分别报告**识图忠实度 / 校正正确性 / 显式降级，⛔ 不许只报「全流程跑完」

⚠️ 它点名的现实阻塞：**F-90（楼层 id 映射）**不修 ⇒ correction 判分整份拒绝
（`plan.md:168`）⇒ 不阻塞前面的契约/循环验收，但**不修就不能宣称最终 correction 成绩成立**。

---

## 七、orchestrator 的处置意见（⛔ 待用户与 sol 讨论后定）

1. **第二节那条证伪接受**：`solid_band` 是实物（sm24 有 4 个），「correction 吃两条面线」这个说法**要改**成
   「吃带原始引用的**多形态**墙证据」。⭐ 这条**要带进 sol 那次讨论**，因为它改的是我方倾向本身。
2. **第一节第 3 条要当缺陷登记**：「新产物可能被当原始文本塞给模型却绕过识图门」——
   这是**沉默的错误路径**，⛔ 比"喂不进去"严重。**待 orchestrator 独立复核后登记。**
3. **第五节对我的更正接受**，措辞已改（见该节末）。
4. ✅ **引用已逐条复核完毕**（2026-08-25，orchestrator 亲手，见下节）。

---

## 八、orchestrator 的逐条复核（2026-08-25，13 处引用）

**结论：12 处准确（含差 1–2 行的可接受偏移），1 处行号指错。** 整体可信。

| 它引的 | 复核结果 |
|---|---|
| `pipeline.py:451-461` 窗引用约束完整范围 | ✅ 准确（我原写的 455-456 只是其中两行）|
| `pipeline.py:512` 计数定义 · `:557` 真正拦截 | ✅ 准确（`_reading_window_stroke_count` 定义在 512；`if expected_window_strokes > 0 and not geom.windows:` 在 557）|
| `pipeline.py:365,369,383` 提示词要模型填世界坐标 | ✅ 准确，**且比它说的更要紧 —— 见下** |
| `reading/contract.py:23,33` 只识别 `reading_views_v2` | ✅ 准确（`READING_PRODUCT_CONTRACT = "reading_views_v2"`；`identify_reading_contract` 在 33）|
| `correction/window_sources.py:313` 只遍历 `pen == "window"` | ✅ 准确（313 是函数定义，**筛选在 321**：`if stroke.pen != "window": continue`）|
| `correction/schema.py:234` · `:243` 自由字典 | ✅ 准确（`CorrectedGeometry` docstring 自写 "centerline geometry primitives"；`corrections`/`conflicts`/`unsupported` 均为 `list[dict]`）|
| `as_drawn_v2.py:617` opening 字段生产者 | ✅ 准确（`opening_candidates` 在 617、`opening_types` 在 621）|
| `sm24_1f_v2.json:24320` 4 个 `solid_band_walls` | ✅ 准确（已独立确证）|
| `judge/gt_schema.py:164-222` | ✅ 准确 —— `GtZoneV3` 只有 `id/name/role/polygon/source_refs`，**确实没有任何厚度或基准字段** |
| `judge/tarch_converter_schema.py:1096` 逐边 basis/thickness/offset | ✅ 准确，**且比它说的更要紧 —— 见下** |
| `reading_correction_split_guide.md:90` | ✅ **逐字准确** |
| `kernel_round16/correction_snapped.json:3405` | ✅ 基本准确（snap 记录实际从 3406 起，差 1 行）|
| `reading_correction_split_guide.md:305`（称「先 sm25 再 sm24 的次序」）| ⚠️ **行号指错** —— 305 附近是「## 六、验收尺度」，不是次序。**结论本身仍成立**（次序是用户 08-25 定的，记在 CLAUDE.md §0.0 与 plan.md），只是出处引错。|

### ⭐⭐ 复核过程本身撞出的两条（比被复核的结论更有用）

1. ⭐⭐⭐ **「基准不同」的具体载体找到了：它写在 correction 的提示词正文里，不在 schema 里。**
   [`pipeline.py:365-369`](../../../src/agent/pipeline.py#L365) 逐字要求模型产出
   **"world-frame, `wall-centerline`, self-consistent room cells"**，并再次强调
   **"put every coordinate in one world frame at `wall CENTERLINE`"**。
   ⇒ 此前文档一直记成「旧 reading 自述唯一基准 = 墙中线」，**那是记错了归属** ——
   **是 correction 的提示词在要求中线**。⭐ 一体改必须动这两句字符串，
   而这也解释了为什么「让 correction 吃两条面线」不是加个适配器就完事。
2. ⭐⭐ **R-6 的修法比设想的近**：`ZoneEdgeReportV1` **已经是一个正式定义好的 schema 类型**
   （`p1` / `p2` / `basis` / `thickness_m` / `offset_m` / `derived_handle`），
   ⛔ **不需要重新设计记录格式** —— 缺的只是**把它晋升进 gt 的序列化**。
   ⇒ 「gt 保留逐边厚度」这件事的工作量应据此下调重估。
