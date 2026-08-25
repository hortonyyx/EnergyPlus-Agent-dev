# 尺寸基准 + 墙厚方向定案（2026-07-08 用户 ratify + 同日双口径修订，待设计轮细化）

> 状态：**方向已拍板，未开工**。排 C2 B4（gt schema v-next）附近批次；动手前出正式设计文档过 Codex 双审。
> 缘起：sm21/sm24 判卷"外包缩一圈"复盘（栅格碾偏 + 判卷口径错配已按 W4/W5 修掉，见
> [logs/reviews/execution/2026-07-08_render_parity_and_grading_frame_execution.md](../logs/reviews/execution/2026-07-08_render_parity_and_grading_frame_execution.md)）。

## 1. 问题结构（用户 2026-07-08 陈述）

- 标注基准不定：一条尺寸可能参照**轴线 / 外皮 / 内皮**，一图混标；立面天然给外皮（两端）。
  ⇒ 识别再准，每道墙也带 ≤1 个墙厚的**基准不确定度**——是仲裁问题不是精度问题。
- 墙厚经常**根本不标注**；非工程图纸里墙厚甚至是艺术化表达（不按比例），像素量也不可信。
- gt 带墙厚（CAD 权威），与产物口径天然有差 ⇒ 影响判卷。

## 2. 定案方向一（同日修订为双口径）：锚定与出模分离，单一内部表示 + `zone_frame` 出模选项

> **修订（2026-07-08 晚，用户提议 + Fable 盘整）**：sm21 Haiku run 证明"墙厚全读准+四周按墙轴线取
> zone 净值"的轴线框全链可用且判卷全绿——直接舍弃可惜。定案改为**保留双口径**：
> - **锚定层不变**：外包永远锚外皮多源证据（立面+总链+gt），防漂移地基，与出模无关。
> - **出模层做成选项** `zone_frame: axis | exterior`（名字可再定）：内部单一权威表示携带
>   外皮外包(观测)+墙轴线(观测/导出)+每墙厚度证据，出模时按配置投影周边 zone 边界到轴线或外皮
>   （厚度已知时两口径互为无损换算，差=周边一圈 t/2）。
> - **不做两条管线**：判卷/渲染用一个 frame-aware 换算函数（现 W5 的 t/2 换算泛化保留，不退役）。
> - 配置进 run_config.yaml 跑前配置项（上线版=输入选项）；默认倾向 axis（证据足档保真最高、
>   现行已验证），厚度仅 prior 档时出 advisory 建议 exterior，**不静默自动切换**。
> 下文原"切换到外皮框"的表述按此理解（外皮框=exterior 出模档，不再是唯一目标口径）。

### 原方向一表述：规范口径 = 「外皮外包 + 内墙轴线」混合框（gt 同款）

- **外包按外皮**：平面总链、四立面宽度、gt footprint 三路独立证据直接可观测——锚最强、符合直觉（用户："优先保持外包一致性，按立面最大范围"）。
- **内墙按轴线**：对分两室、与 gt zone tiling 边界天然重合、内核配对现口径。
- 收益：判卷零换算（现 W5 的 t/2 shim 退役）、reading↔correction↔gt 三方同框、立面窗落位/facade
  frame cross-check 天然自洽、与 EP 常见建模惯例一致（外墙面积略大于中心线口径，口径一致即可）。
- 迁移：schema 语义变更 ⇒ 走 B0 schema_version 机制（v3 或 frame 字段），内核/判卷/渲染跟随。
- 误差结构改善：从"每墙 ≤1t 随机"变为"外包锁死、内墙 ≤t/2 且笔笔有审计"。

## 3. 定案方向二：墙厚拆两个角色，各归其位（用户方案 + 本轮盘整）

**关键解耦：几何要的不是"真实墙厚"，是"基准换算量"；物理要的才是真实厚度。**

| 角色 | 谁用 | 何时 | 精度需求 | 来源阶梯 |
|---|---|---|---|---|
| **几何换算**（基准归一到规范框） | 1_correction | 早（影响 cell 坐标） | 低（错 ≤t/2 在容差内），一致性要求高 | 见 §4 阶梯 |
| **物理属性**（构造层厚度+材料→U 值/热质量） | 4_mep（统一环节给每 surface 赋值） | 晚（不影响几何） | 影响能耗 | **输入端补充**（用户勾选/自然语言提取）> 图读 > prior |

- 回答用户"厚度处理是否要提前"：**拆开后不用提前**。几何那半本来就在 correction（且新框下需求大幅缩小，见 §4）；物理那半留 MEP/输入端。EP surface 是零厚度面，构造厚度在材料层——物理厚度**不需要回写几何**；两者不一致时可做 advisory 一致性 flag（二阶小量）。
- reading 侧（用户拍）："**能读就读，跟其他一样标置信度，作为墙的一个属性**"——墙厚证据
  （厚度 tick / 链缝隙 / 双线带像素宽）进 A0 证据模型，带 grade+confidence，不做判断只做记录。
- 输入端补充 = 新证据源 `user_input`（勾选/NL 提取），排证据阶梯最高档——正好是未来输入模态的接缝，schema 加槽位即可（符合复杂度可扩展铁律）。

## 4. 未标注/不可信墙厚的几何侧解法（新框下需求本身就塌缩了）

规范框换成「外皮外包+内墙轴线」后，几何真正需要墙厚的场景只剩一种：

| 场景 | 需要墙厚？ | 解法 |
|---|---|---|
| 外包（总尺寸/立面） | **不需要** | 外皮直接可观测，锚死 |
| 内墙尺寸按轴线标（工程图常态，轴网） | **不需要** | 轴线即规范位 |
| 内墙按内皮标（净距链） | 需要 t/2 换算 | **链算术可导出**：总尺寸−净距和=墙带和（sm21 未标注 120 带就是这么恢复的），不用"读"墙厚 |
| 无链、艺术化墙、像素不可信 | 需要兜底 | **prior 阶梯**：`user_input` > 链算术导出 > 图读 tick（干净 CAD 档才可信，非按比例图纸像素测量=capability 声明外，直接降 prior）> 类型 prior（如外 240/内 120）——一律记 corrections[] 带 evidence_grade，判不出基准=conflict 不硬猜 |

兜底档的几何误差 ≤t/2 且**不污染外包**（外包已独立锁死）——正是用户说的"在允许范围内"，但处理方式统一、有审计。

## 5. 设计轮要出的东西（排队单）

1. schema：内部单一权威表示（外皮外包+轴线+每墙厚度证据槽位，wall attribute + evidence grade + `user_input` 源）+ schema_version 迁移
2. correction 规则：基准分类程序（链闭合/墙带/半厚整数倍三证据）+ 换算审计 rule_id
3. `zone_frame: axis | exterior` 出模选项：run_config 接线 + 内核周边边界投影 + frame-aware 判卷/渲染换算函数（W5 泛化保留）+ 厚度 prior 档 advisory + gt 墙厚字段语义复核
4. MEP 侧 per-surface 厚度+材料赋值环节的接口（输入端补充进来的挂点）
5. 迁移与回归：sm20/sm21 anchors 重derive 对账（axis 档应与现行为字节级一致=天然回归基线）

---

## ⭐ 2026-08-19 收进本专项：`scale_origin`（读图器的世界原点申报）

**它为什么属于这里、不属于 reading**：`scale_origin` 要求读图器申报
「整栋**跨层**投影最大边界的**内**角」——判「内角」就必须判**墙厚 / 内外皮**，
而墙厚基准正是本专项尚未定案的题（`zone_frame: axis|exterior`）。
⇒ 它把一个未解决的尺寸基准问题，转嫁成了读图器的一项必填申报。

**沿革**：
- 好版本（07-07 / 07-08）`guide.md` §1 明写 **"the reading stage does NO world placement"**，
  两份满分产物**都没有这个字段**。
- `68fd6d0`（2026-07-31）把它变成**每张平面图必填**，且扩散到 5 处（kickoff 非可议项 / §1 / §2 schema
  注释 / §6 自检清单 / pen_library）——**方向与好版本的禁令相反**。
- `0ae4b93`（2026-08-17）退回 **SHOULD**（同图可见参考点 · 拿不准留 null · 省略不算自检失败）。
  起因是 orchestrator 写的「两份好 reading 都没有它」**事实错**（两份都有 world-placement 禁令，
  且 `git show 723b0f9:guide.md` 零提及 ⇒ 从来不是成文规则）。

**⛔ 遗留的真问题（本专项要答）**：
1. 退回 SHOULD 后，**"拿不准留 null" 会撞上 v3 判卷的 `retain_as_miss`**
   ⇒ 整条 plan 通道按 miss 计（详 [reading 专项 §9.4](../capability/reading/improvement_methodology.md)）。
   **这是 sm24 验收的准入门**，且碰判卷 = 工程档、作者不得是 orchestrator。
2. 世界原点到底该由**谁**定：读图器申报（现状，需判墙厚）/ correction 段推导 / 代码从尺寸链确定性求解？
   ⇒ 与本专项的 `zone_frame` 定案是同一个决定的两面。


---

## ⭐⭐⭐ 2026-08-27 实测更新：**「出模形式」现在不是配置出来的，是【读图证据够不够】涌现出来的**

> 本节由 orchestrator 夜班只读核查得出（⛔ 未改任何代码）。
> 它把用户 2026-08-26 第 2 条口径 ——「**出模就定两种，不变；两种成绩分开排；
> 相当于是两个答案，答案在起跑的配置就决定了**」—— 从「加个开关」重新定性成
> **「先把现在这条隐式决定路径拆掉」**。

### 一、`zone_frame: axis | exterior` 这个开关，至今**不存在**（实测）

`grep -rn zone_frame src/` 只命中 `src/agent/state.py` / `output_coordinates.py` / `nodes/zone.py` 里的
**EnergyPlus zone 原点归零**（`zero_zone_frames_with_audit`），**与本专项的出模基准同名不同物**。
⇒ §5 排队单第 3 条**一行未落地**。⚠️ 后续引用这个名字时先说清是哪一个，别再撞名。

### 二、⭐⭐ 真正在决定基准的是这条路径（三段，逐段实测）

1. `correction/finalize.py:124` 调 `extract_authoritative_envelope(vector_dir, footprint=geom, …)`
   —— **从 reading 产物目录里抽立面外包证据**。
2. `correction/envelope.py:520-530` 逐轴裁决：
   ```python
   elif not (has_overall_authority or has_opposite_view_agreement or has_same_view_stroke_agreement):
       axes[axis] = EnvelopeAxisResolution(axis=axis, status="skipped",
           reason="insufficient evidence: no corroborating facade envelope signal")
   ```
   ⇒ **证据不够 ⇒ 整条轴 `skipped`。**
3. `correction/deterministic.py:924` `if authoritative_envelope is None: return geom`
   + 逐轴 `status != "accepted"` 就 `continue` ⇒ **不投影**。

⇒ **结论：产物落在中线还是外皮，取决于这一抽 reading 的立面证据够不够。**
这正是 CLAUDE.md 08-26 banner ③(b) 记的「外皮支有机制但证据不够整条轴 skip，R0 即如此」的**机制层解释**，
⭐ 而且它是**代码侧属性**（换一份产物这条结论仍在），不随旧产物作废。

**为什么这是个必须先拆掉的形状**（⛔ 不只是「缺个开关」）：
- 用户要的是「**起跑的配置决定答案形式**」，现在是「**跑完才知道拿到哪一种**」；
- 两种成绩要**分开排**，而现在**同一次配置可能产出两种形式的混合物**（一轴 accepted、另一轴 skipped）
  —— 那既不是 axis 档也不是 exterior 档，**是第三种没人定义过的东西，且没有任何门会说它不对**；
- 同族教训 [[silent-default-threshold-behind-otherwise-conclusions]]：
  「证据不够就保持原样」= 把出模形式的默认值**偷设成 axis**，而这个默认**没有人签过字**。

### 三、gt 侧已经具备派生两种形式的原料（2026-08-27 实测）

`review/conversion_report.json` 里每条 zone 边都带 `basis`（`wall_axis` / `outer_skin`）+ `thickness_m` + `offset_m`
（sm25：136 条边，`wall_axis` 90 / `outer_skin` 46；厚度 0.12×78 / 0.24×58）。
⇒ **gt 的「派生答案层」按哪种出模形式派生，是可机械计算的**，⛔ 不需要重新签字
（正对用户口径 12 的「换出模形式只重新派生、不必重签」）。
⚠️ 但这一层目前**没有任何判分路径读它**、且**不在人工签字覆盖范围内**（详见 plan.md 2026-08-27 §二）
⇒ 已派 **G1** 单独解决。

### 四、⇒ ②-1 包（「冻结出模形式」）的形状，据此收窄为四件

1. **run_config 增一个出模形式声明**，跑前冻结、写进 run 的 provenance；⛔ 不给「自动/按证据决定」这一档。
2. **确定性代码按声明投影**（厚度已知时两口径互为无损换算，差 = 周边一圈 t/2）——
   ⛔ 投影发生在代码里，不在提示词里；correction 提示词那两句写死 `wall-centerline` 的字符串一并处理（②-2）。
3. **立面自动跟随**：`correction/finalize.py:139` 的 `facade_segments` 是唯一写入者且跑在 core-final ring 上
   ⇒ 平面投影对了立面会跟着对（08-26 已核实，此处只记指针）。
4. **判分侧核对声明一致**：产物自报的出模形式 ≠ 跑前冻结的那个 ⇒ **响亮失败**
   （与用户口径 9 对「吸附分辨率」的处置**同一个形状**：gt 声明 → 跑前抄进配置 → 判分侧核对，不一致响亮失败）。
   ⭐ 且必须记住 [sol]#2：**产品自报的东西不能用来换算它自己的答案** ——
   这里的「自报出模形式」只能作为**被核对的声明**，⛔ 不能作为判分器的换算依据。

⛔ **本节只是把 ②-1 的题面收窄，⛔ 不是已实现。** 落地要出正式派工单 + 跨家族审。
