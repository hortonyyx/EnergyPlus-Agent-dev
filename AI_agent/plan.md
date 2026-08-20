# 行动清单（活计划）

> **职责**：只放**还没做完的事**和**当前一轮的日更**。**体量纪律 = [CLAUDE.md §0.5](CLAUDE.md)（唯一权威）**：
> ⛔ 不放历史叙述——做完的、翻篇的一律搬 [`logs/worklog/`](logs/worklog/)（见文末 §归档）；
> **本文 >900 行 或 出现上一轮日更 ⇒ 收工时当场搬**（§5#12 第 ② 步）。
> 当前状态看 [CLAUDE.md §2](CLAUDE.md) · 历史决策看 [decision_log.md](decision_log.md) ·
> 架构看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) ·
> 标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。

---

## 当前焦点（2026-08-20）

> **第一目标（用户 08-18 定）= 恢复到 07-07 的 reading 水平。** ⭐ **2026-08-20 已达成一格。**
> 判断法则见 [CLAUDE.md §0.1](CLAUDE.md)：不做这件事，下一次跑测能不能跑起来、结果能不能读？能 ⇒ 登记，不做。

### ✅ 已达成：07-07 水平在当前基座上复现

`run_2026-08-20_acceptance_sonnet_S1`（Sonnet 5 × sm21 全 6 图，**工程档 n=1**）：
**9/9 平面墙 · 7/7 平面窗 · 15/15 立面窗 · 最大偏移 0.0 m · 首抽零返工** —— 与 07-07 靶子逐项相同。
⇒ **「07-07 那个形态在当前代码上还灵不灵」这个问题，答案是灵。** ⛔ n=1 工程档，不作正式成绩。

⚠️ **但满分掩盖了一处几何缺陷**（用户肉眼发现，orchestrator 已坐实）：
外墙落在实测像素中心线（内缩 0.11–0.12 m）、窗仍落在标称尺寸链位置 ⇒ **两个基准不一致**；
判卷只比对由分区边界派生的内隔墙、**从不比对外轮廓坐标** ⇒ 零代价。
**全档 + 四条登记 → [reading 专项 §10](capability/reading/improvement_methodology.md)。**

### 🔻 GPT 那格未达标（不下「退化」结论）

`run_2026-08-20_acceptance_gpt54mini_G1`：7/9 · 5/7 · 立面 6/15。1f pilot 过（4/4·3/3·0.09 m），2f 与四立面塌。
**失效机制已实测**：撞上跨轴分歧告警后**把两轴拆成两次单独调用把告警消掉**（同族 F-63）——
而这是 orchestrator 的返工要求「两轴必须一次给全」**教出来**的
⇒ [[rule-without-legal-exit-breeds-invention]]，**prompt 挡不住，只有工具层能**。
⛔ **不下「GPT 退化」结论**：至少三个变量未控（提示词含不含 measure-before-draw / 返工轮数 / effort 档），
且退化集中在 2f 与立面，而历史树对照**只跑过 1f** ⇒ **缺「GPT × 历史树 × 全案」那一格**，登记归 reading 专项。

### ⏭ 下一步（用户 08-20 定）= 拿 Sonnet 推 sm25，至少验证一次 C2 批的效果

| # | 步骤 | 状态 |
|---|---|---|
| 1 | 素材入仓 | ✅ 08-04 |
| 2 | 转换器多层化 | ✅ **本轮落地**（sol 施工 · GLM 审 · 主控轻门全仓连跑两次 2917 绿）|
| 3 | **写 sm25 的转换请求**（~16KB 逐视图选择器/仿射/裁剪框/标定控制点/`label_role_map`）| ❌ **无工具，得写；下一轮第一件事** |
| 4 | 用户填 6 个 `TODO_` + 定房间名/角色口径 | ⏸ 等用户（DXF 里零房间名）|
| 5 | 跑转换器出候选包 → 用户看叠图签字（G10）| ❌ |
| 6 | 晋升入库 | ❌ |
| 7 | Sonnet 读图六张 | ❌ |
| 8 | 跑 0–5 管线 = **真正验到 C2** | ❌ |

⚠️ **第 3 项大部分可机械导出**：08-04 勘察已从 DXF 提出六个视图框句柄与图名
（`37B` 1f / `380` 2f / `382` 西 / `384` 南 / `386` 北 / `388` 东），裁剪框与仿射可从框算。
真正要人定的只有**角色映射**与**关键尺寸**。

**⛔ 明确不做**：消除转换器哈希序依赖 / DXF 字节确定化 / 重建可复现性体系（用户 08-20：
「gt 不用做得太复杂，本来就是 dev 期的东西，能做出一个正确的 gt 最重要」）· 再动 guard 围栏 · 补围栏/补审/补锁。

---

## 未闭合缺陷登记

| 编号 | 内容 | 状态 |
|---|---|---|
| **⭐ 新** | **转换器输出依赖 Python 哈希随机化**：同输入同代码跑两次，规范化 DXF 字节与 `content_sha256` 戳不同（实测固定 `PYTHONHASHSEED` 即稳定）。**答案内容跨 5 个种子恒定** ⇒ gt 正确性不受影响 | **登记不做**（用户 08-20 拍板）；已由新锁钉住「内容跨种子稳定」 |
| **⭐ 新** | **已签字答案的溯源戳与现行代码不一致**：sm24 的 `vg_implementation_sha256` 记 `60cab9e6`，干净 HEAD 算出 `8e45fd15`（07-27 后那四个 `correction/` 文件被改过 4 次）。⭐ **但答案内容实测逐字段一致 ⇒ 历史成绩仍可信** | sm24 由用户重签（用户 08-20 允诺）；⚠️ 重签时须认真看新叠图（渲染实测差 3–4% 像素）|
| **⭐ 新 R-1** | **判卷对外轮廓是瞎的**（gt 无 `walls`，只比对分区派生的内隔墙）| → [reading 专项 §10](capability/reading/improvement_methodology.md) |
| **⭐ 新 R-2** | 读图器**墙/窗基准不一致** | → 与「尺寸基准+墙厚方向」专项**合并决策** |
| F-62 · N-1 / N-2 | guard 词法围栏同族缺陷 | **未修**（`observe` 档下影响归零）|
| F-63 | 跨轴门抓不住拆轴规避 | ⭐ **本轮活体复现**（GPT 主动拆轴消警）；修法归 [专项 §9.1](capability/reading/improvement_methodology.md) |
| F-64 | gate① 对「零产出」是瞎的 | 登记 |
| ~~v3 判卷 null `scale_origin`~~ | ~~sm24 准入门~~ | ✅ **本轮已解**（`f2ea22e`，GLM 施工）|
| — | 全链无门校验「note 里的换算式 ↔ 笔画坐标」一致性 | ⭐ 确定性可查、成本低 |
| — | 读图器会自发产出**清单外文件**（`_validated_1f_view.json`）| 本轮由 merge 门拦住并归档；登记 |

**复审债**：甲-5 · 丙-1 / 丙-2（同前）。**本轮新增零复审债**——转换器批已由 GLM 跨家族审 + 主控轻门。

---

## 本轮日志（2026-08-19）

## 本轮日志（2026-08-20）

## 2026-08-20 · ⭐⭐⭐ **07-07 水平在当前基座上复现（Sonnet 满分）· 转换器多层化落地 · 三条判据修正**

### 一、reading 两格验收

| 格 | 结果 | 形式 |
|---|---|---|
| **Sonnet 5 × sm21 全 6 图** | ✅ **9/9 · 7/7 · 15/15 · 0.0 m，首抽零返工** | A 打底 + B 校验（1f 砸 20 次 crop_zoom 定尺子，标定 −0.03%）|
| gpt-5.4-mini × sm21 全 6 图 | ❌ 7/9 · 5/7 · 立面 6/15 | 平面纯尺子驱动、零尺寸引用；**撞警后拆轴消警** |

**成本实况**（此前无处记载）：Sonnet 读 1 张平面图 ≈ **$7.32**；读到第 4 张烧穿一个 5 小时会话窗口
（429 `session limit`），重置后 `--resume` 原会话续跑完成。⇒ **全案 reading 要按窗口排期。**

### 二、转换器多层化（sm25 前置）

**sol 施工 · GLM 跨家族审 · 主控轻门**。全仓 **2911 → 2917 绿 + 14 xfail**，连跑两次零红零闪。
- 立面开洞按 **z 归层**（此前 `_assign_elevation` 38 行函数体里 `_z` 只在解包行出现、从未被引用
  ⇒ **归层全链零竖向判别**，单层看不见、两层窗上下对齐必歧义）；单层歧义判定未放宽。
- 多层：单份 DXF + canonical 图层名 + **按 view clip / handle 钉死** 分层（提取器侧本就支持，零改动）。
- **sm24 答案内容实测逐字段零漂移** ⇒ 历史成绩仍可信。

### 三、⭐ 本轮三次「停下上报」全部是派工方的题出错（累计 15/15）

| 停工 | orchestrator 错在哪 | 撞出什么 |
|---|---|---|
| ① | 以为图层要按层区分 / 或拆两份 DXF | 正确形态本就存在（clip + selector）|
| ② | 改完后说「提取器侧不用动」 | **立面归层全链无竖向判别** |
| ③ | 要求「产物与签字答案逐字节相同」 | **该判据不可能成立**，且暴露签字答案溯源戳已失配 |

⇒ 派工单里那句「停下上报，我不会因为停工次数多而怪你」**是有回报的**：三条我一个都不会自己发现。

### 四、⛔ orchestrator 本轮四处实犯（全部记名）

1. **拿一次实测就确认了对同事席位的「虚报」指控。** GLM 判 sol 虚报（BLOCKER），我自己跑出同样的红
   ⇒ 当场对用户说「指控成立」。**继续验才发现那条测试是不确定的**（同树 6 次：1 绿 5 红；
   固定 `PYTHONHASHSEED` 则 6/6 稳定 ⇒ 哈希序依赖）⇒ **三方观测全真、无人说谎**，指控与 GLM 的定性均被推翻。
   ⇒ **判据：凡要下「某方报的数不对」，先重复跑再开口**（重复跑只花 90 秒）。同族 [[one-shot-acceptance-bar-kills-false-claims]]。
2. **返工文本自相矛盾**：既写「把新尺子换算进已画好的笔画」又写「不要重新描图」⇒ GPT 选了后者，
   产物逐字节未变。**它的选择在给定文本下是合理的。** ⇒ 顺带证明：**换尺子重算在当前产物形态下无法纯代码完成**
   （产物存米坐标而非像素锚点）——这是 [专项 §9.1](capability/reading/improvement_methodology.md) 根治修法迄今最具体的支持证据。
3. **中途取样判路线**：在 GPT 立面尚未开跑时量到「标定器 0 次」，据此判它走路线 B —— 实际只是**还没跑到**。
   同族 [[absence-conflates-causes-in-observables]]。
4. **把附记直接追加进已封存的裁定文件**（会改掉哈希、让封存不可验证）⇒ 已拆为独立附记文件并验证正文哈希还原。

### 五、⭐ 判据修正三条（已写入 [reading 总账 §四](capability/reading/good_reading_implementations.md)）

1. **扰动实验可当路线判据**：改尺子看坐标动不动（动 ⇒ 尺子驱动 = 路线 A）。便宜且决定性，⛔ 别再数 crop 次数。
2. **07-07 靶子不是「纯路线 A」，是两条路都走 + 逐笔对账**（17 次 crop + 17/17 笔画挂尺寸链）
   ⇒ 若要复刻 07-07，要复刻的可能是**「两个独立来源逐笔对账」**本身。
3. **`self_check` 说全画了 + `uncaptured` 非空 ≠ 自检说谎** —— 要看装的是拒收台账还是漏画自白。

### 六、其它落地

- **v3 判卷 null `scale_origin` 静默零分**已修（`f2ea22e`，GLM 施工 · orchestrator 审 + 自行复现两个 neuter）。
  ⛔ orchestrator 原提的「换严档位即可、零代码」被证伪：留空原点是**合法常态**
  （07-07 sm24 靶子 5 图全 null、guide.md:101 明写「拿不准就留 null」）⇒ 换档位会把好产物全拒收。
- `--vision-resize-tier` 默认 `none`、pilot 停等门、专用空 staging 根：本轮全部按 08-19 形态沿用。
- **读图器会写清单外文件**（`_validated_1f_view.json`）⇒ merge 门正确拦下，已原样归档不删除。

---

## 2026-08-19（已翻篇，逐字归档）

- 三臂判别跑完 · 病灶定位到「肯不肯把看放到放大镜后面」· 根治与 Haiku 回归打包归专项
- GPT 判别臂第一格：历史栈今天仍能出满分 reading（一轮返工，4/4 · 3/3）
⇒ 全文见 [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)

## 中期（粗）—— 能力升级（原 B5–B7）

按 **[capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md)** 的 C 阶梯推进（内核先行 + 守卫同步）：
- **C2 正交多边形 + 多平面立面**（含 shapely 覆盖完整性门提前落地）
- **C3 退台 / 挑空**（墙配对 by_floor → z 区间重叠驱动、切配扩到切墙）
- **C4 斜交墙**

并行支线：识图→建模质量主线见 [capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md)；再拓扑 leg（休眠）见 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md)。

---

## 远期 —— 开源模型 + Pivot（原 B8–B9）

- 部署 vLLM + Qwen2.5-VL / DeepSeek-VL；切 [llm.yaml](../src/configs/llm.yaml) `intake` section（A2 已就绪）；跑同一套评测横向对比。
- LoRA SFT（phase1=(图,矢量JSON) VLM / phase2=(矢量JSON,IntakeOutput) 纯文本，两数据流独立），holdout ≥ Opus 80% 后切默认 provider。
- 双阈值见 [reference/pivot_criteria.md](reference/pivot_criteria.md)。

---

## 分出去的独立模块（指针）

| 模块 | 文档 | 状态 |
|---|---|---|
| CAD→gt 满配答案 / CAD 输入模态种子 | [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md) | 设计待审，工具链就位 |
| reading 提升（诊断+Phase A/B/C+CV 工具箱方法论）| [capability/reading/improvement_methodology.md](capability/reading/improvement_methodology.md) | **已动工**（Phase A ✅ 落地）→ 统一管理文档；原 proposal 已折入并删（2026-07-03）|
| 0–3 复杂度升级路径（C2/C3/C4）| [capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md) | 骨架已立，随中期推进 |
| 再拓扑 leg（热区积木 zonification）| [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) | 强力支线·休眠·**Fable5 B3(07-06)已更新启动条件**（绑 C2 开工·stage 1.5·`method` run_config·比原设想更易落地，见其 §9）|
| 可编辑几何确认环节 | [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md) | DEFERRED，先讨论 |

---

## 搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者侧 MCP 全线重写交付。
- **token 优化**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换后大量 CRUD 工具消失再评估。
- **fenestration/construction SimpleGlazing 兼容性 prompt 修**：等 idfpy schema 原生覆盖（当前几何优先，不动 prompt）。
- **Sonnet 4.6 降级测试**（本环境够不到，需用户独立会话；**Haiku 4.5 降级测试已跑 ✅ 2026-07-05，见 N2b ③**）；**OpenStudio 几何验收**（用户人工，不卡代码）。

---

## 已完成（一行汇总，详见 [decision_log.md](decision_log.md)）

A 代码跑通 ✅ · B1 旧 skill 迁移恢复 ✅ · 两步法 POC + 切主线 + InterZone 门 + 正式指南 ✅ · 0–5 阶段重构（几何确定性化）✅ · EP 跑通 + schedule 门 ✅ · 完整体检 4H/3M/3L 全修 ✅ · 仓库整理 + 标准 case 布局 ✅ · 0–5 校验架构 M0–M4 ✅ · 新 baseline 方案 + 主 Agent 操作手册 + gt ✅ · 逐段 judge 编排 + 离线 3D 查看器 ✅ · CAD→gt 工具链 + gt 渲染 ✅

---

## 归档（过程痕迹，⛔ 非活文档）

| 归档 | 内容 |
|---|---|
| [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md) | plan 日更 2026-08-01 → 08-18（reading 重启七抽 · 基座普查 · 验收 3/3 · 下游断链 · F-22 批）|
| [`logs/worklog/2026-07_plan_log.md`](logs/worklog/2026-07_plan_log.md) | plan 日更 2026-07-31 + 原「当前焦点」章节正文（sm24 端到端 / 判卷器身份与度量批）|
| [`logs/worklog/2026-06_backlog_closed.md`](logs/worklog/2026-06_backlog_closed.md) | 原「近期（细）」整节（2026-06 批次，绝大多数已 ✅）|
| [`decision_log.md`](decision_log.md) | 里程碑与决策详档（历史决策的唯一归档）|
