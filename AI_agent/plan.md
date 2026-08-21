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
| 2 | 转换器多层化 | ✅ 08-20 |
| 3 | 立面洞口载体方言层（F-65）| ✅ 08-20 |
| 4 | 用户填 testdata | ✅ 08-20（580 m² · Office · 14/15 热区）|
| 5 | **写 sm25 转换请求 + 六图像素标定** | ✅ **已完成**（`build_request.py` 确定性生成，零手抄）|
| 6 | 平面侧三处缺陷修复（面对面厚度证据 / 非凸内外判定 / 跨层轮廓浮点比较）| ✅ **已完成** |
| 7 | **跑转换器出候选包** | ✅ **已出**（G1–G5·G7·G8·G9 全绿，零 BLOCK 诊断）|
| 8 | **用户看叠图签字（G10）** | ⏸ **等用户** ← **就差这一步** |
| 9 | 带签名重跑 + 晋升入库 | ❌ |
| 10 | Sonnet 读图六张 | ❌ |
| 11 | 跑 0–5 管线 = **真正验到 C2** | ❌ |

**候选包**：[`logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/`](logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/)
· `content_sha256 = 6c36d9e8…`（主控与施工席**两次独立构建逐位相同**；GLM 审后由 `785f8273…` 修正而来）
· 签字要看的：`gt/renders/overlay_*.png`（6 张）+ `overlay_plan.svg`
· 立面 **31 窗 + 3 门**（西 4+2 · 南 7 · 北 8 · 东 12+1）· 分区 F1 **14** / F2 **15**

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
| **⭐ 新 F-65** | **立面窗提取只认 `LINE`，`window_selector.entity_types` 从不被读取**（`tarch_normalize.py:1694` 硬编码 `dxftype()=="LINE"`）。sm25 立面窗全是 `INSERT`(17 个 `$EWDLib$00000533`)+`LWPOLYLINE`(14) ⇒ **静默产 0 窗**，另有 17 条 `door_block_drift` 误报（窗块走了门那条路）。F-64 同族（零产出不报红）。实测应得 **31 扇窗 + 3 樘门**（东 12 · 北 8 · 南 7 · 西 4；门：东双开 1 + 西 2）| ✅ **本轮已修**（sol 施工 · GLM 跨家族审 APPROVE · 主控权威全量 3 次 2937 绿）|
| ~~F-66~~ | ~~东立面两门块重合~~ **⛔ 我报错了，已撤回**：拿插入点当外包框的代理量，实算 matrix44 变换后两块**相邻不重叠**（x 64727–65527 / 65527–66327）= 一樘 1600 宽双开门，现行 union 平铺逻辑正好合并它 | **撤销**（[[proxy-mistaken-for-the-thing]]）|
| **⭐ 新** | **立面诊断码迁移**：门图层上块名不在任何规则里的 INSERT，旧报 `door_block_drift`、现报 `tarch_elevation_entities_unconsumed`（门仍 G3 红，仅码变）| **知悉即可**；下游若按诊断码分诊需更新对照 |
| **⭐ 新** | `module_union_min_gap_m` 若声明值 ≤ 量化容差，「小于声明值必红」的区间退化为空 | **登记不做**（现实声明 0.5 m ≫ 容差；加下界属补围栏，§0.1）|
| **⭐ 新 R-3** | **非方形外包导致 gt 内外墙基准对不齐**：内墙走**中轴**、外墙走**外包**，Z 形/退台上两者在拐角处必然错位 | **登记**（2026-08-21 用户令）→ 归**出模专项**解决，本轮不动 |
| **⭐ 新 R-4** | **立面「前后关系轮廓线」**：C2 落地后非方形建筑的立面出现进深台阶线（sm25 西立面距左端 6000 那条竖线 = 西向墙面在 y=14 处从进深 0 退到 5 m）。数据**已在 gt 里**（每立面族 `boundary_segments` 各带进深坐标）| **① 叠图已画** ✅（2026-08-21，绿线 + `depth a→b` 标注，与图纸自身那条线重合）· **② 显式元素 + 判卷计分仍缺** → 归 C2/判卷专项 |
| **⭐ 新 R-5** | **⛔ 全项目没有统一的房间类型词表**：gt 侧 `gt_schema.py:234 role: str`、pipeline 侧 `correction/schema.py:201 role: str = "office"` **都是自由字符串无枚举**；唯一的词表是叠图渲染器里那个**配色字典**（`office/meeting/corridor/reception/lobby`），两边谁都没引用它 ⇒ **表述不一致已是现实** | **登记**（2026-08-21 用户令）：建一套**全量房间类型表**，gt 与 pipeline 都从这里选；**下一个 case 落地** |
| **⭐ 新** | **房间类型（role）sm25 全为 `unspecified`**：叠图着色用的是 orchestrator 目视判定，**只进 `review_annotations`、不进 gt**。用户 2026-08-21：**下一个 case 起由用户填房间类型，届时 orchestrator 提醒** | **登记 + 提醒项** |
| **⭐ 新 F-67** | ⛔ **一个角部歧义洞口作废整份判卷，且长得跟「什么都没读对」一模一样**（F-64 家族）。sm25 1f 实测：15 个平面洞口里 **14 个候选唯一**，**1 个**在 `(15,20)` 转角处同时落进东墙 `x=15` 与北墙 `y=20` 的容差 ⇒ `reading_typed_score.py:410` 的处置是**把该组件的全部观测移除** ⇒ 平面频道 `not_applicable` ⇒ **37 条分段行全 miss**。sm24 是矩形，永远产生不了「两面外墙在转角同时入容差」⇒ 该路径从未被走到 | ✅ **已修**（sol 施工）：作废半径由**整个组件**缩到**单个观测**；⭐ **分母不动**（gt 派生，歧义观测无资格删 gt 目标——此处主控原写「移出分母」被 sol 推翻）；频道只汇总 disposition=`score` 的组件。4 把新锁含「歧义观测进分子必红」。实测：37 全 miss → **31 完整 / 15 miss / 1 多画**，`denominator_sha256` 逐字节不变 |
| **⭐ 新 F-68** | **`judge_score_bindings.json` 全仓没有生成器** —— sm24 那份是手工产的；sm25 一判卷就撞「required judge sidecar(s) are missing ⇒ v3 scoring layer was skipped」，**权威判卷被静默跳过**（跑测照常报 gate① 绿）| ✅ **已补** `scripts/tool_scripts/build_score_view_bindings.py`（平面已支持；⚠️ 立面绑定尚未实现，遇到时响亮报错而非产半份文件）|
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

## 2026-08-20 补 · ⭐ **立面洞口「载体方言层」落地（F-65）· sm25 立面阻断解除**

### 一、撞出与修掉的东西

**F-65**：立面洞口提取把「图怎么画」烤死在代码里 —— `window_selector.entity_types`
**全文从未被读取**（`tarch_normalize.py:1694` 硬编码 `dxftype()=="LINE"`）。
sm25 立面窗全是 `INSERT`(17)+`LWPOLYLINE`(14) ⇒ **静默产 0 窗**（F-64 同族）。
连带查出**门也走不通**：旧约定要求洞口轮廓是闭合 LWPOLYLINE，而 sm25 门块里那条
LWPOLYLINE 是**未闭合的门扇轮廓**（比洞口窄 60、矮 30），真洞口是外框 4 条 LINE。

**修法四块**（sol 施工 · 三个工作包 · GLM 跨家族审）：
① 请求级**载体规则表**（门窗共用：图层 + 实体类型 + 块名 + 块指纹 + 块内逐句柄 role）；
② **一张注册表 + 三个 resolver**（直线组 / 闭合多段线 / 图块），`dict[kind, fn]` 是唯一分派点；
③ ⭐ **清点对账门**：规则声明过的图层上、框内每个实体必须被消费 / 显式忽略，**否则 G3 红并逐句柄点名**；
④ 旧请求走**纯翻译层**（旧字段 → 规则表），**执行只有一条路**，sm24 签字 hash 一字节未动。

### 二、⛔ 派工方（orchestrator）又写错一条前提

派工单 §3 D2#4 写「门的多模块合并语义保持不变是安全的」——**错**。旧聚类是「同 z 带就并簇」，
sm25 西立面两樘门同带、相距 **9440 mm** 会被硬并 ⇒ 必红；而直接改成「只有接触才并」，
sm24 那条「100 mm 缝必红」的 must-red 会**从红变绿** = 放宽既有判据。

**主控裁决**：合并策略进请求声明（`same_band_strict_union` 旧请求用 / `touching_rect_union` sm25 用），
且 `touching_rect_union` **必须配一个无默认值的声明间距** `module_union_min_gap_m`（sm25 = 0.5 m），
同带未接触但间距**小于**该值 ⇒ 必红。
⇒ 理由：「接触就合并」是声明；**「不接触就一定是两樘」是沉默的推断**，它把「多远算两樘」偷偷设成 0。
该值定位同 `wall_thickness_range_m`：**领域参数，不是容差**。
⇒ **本轮第 4 次「停下上报」，4/4 全是派工方题错，累计 16/16。**

### 三、验收（三方独立，⛔ 不互相采信）

| 方 | 做了什么 | 结果 |
|---|---|---|
| 主控 | 逐行审三个包 diff + **权威全量连跑 3 次** | **2937 绿 + 14 xfail**，零红零闪（基线 `32ab707` = 2917 + 14）|
| 主控 | **照新 schema 从零写 sm25 规则**、独立跑解析器 + 负向扰动 | 31 窗 3 门、台账零剩余；摘规则则逐句柄点名（北 2 · 东 14）|
| GLM | 每把锁自摘自还原 + 自建探针复现 sm24 四条老 must-red | **APPROVE**，0 BLOCKER / 0 MAJOR，3 MINOR + 2 NIT |

**GLM 最重一条已验**：四条老 must-red 仍各报 1 条 `door_structure_invalid`，**未被新门顶替**。
**F-1（L1 等价锁两侧同坏恒绿）已返工修掉**并自证（摘翻译层必红 / 还原必绿）。

### 四、⚠️ 本批**没有**证明的事

只证明了**解析器这一层**能从 sm25 提出 31 窗 3 门；**整条转换链尚未跑过 sm25**。
那要等完整转换请求（六视图仿射 + 像素标定）写出来。
勘察与可直接复用的规则 → [`logs/experiments/2026-08-20_sm25_elevation_carriers/`](logs/experiments/2026-08-20_sm25_elevation_carriers/)。

### 五、下一步（sm25 步骤 3 的真实工作量）

- **可机械导出**：六个视图框句柄与裁剪框 ✅ 已有 · 平面仿射 ✅（约定已从 sm24 反推对上：
  `m02 = -min_x×0.001`，原点 = 平面 WALL 外皮 SW 角）· 立面 datum 句柄 ✅（三条水平线，间距 3600）
- **需先跑平面段才能定**：立面 along 仿射的 `plan_lo/plan_hi`（L 形，不能直接取 [0,25]）
- **⛔ 真正费人工**：**六张图的像素标定**（`pixel_to_source_m` + 每图 ≥3 个控制点）——
  工具链只有「校验标定对不对」，**没有「帮你算标定」**；且图与视图框长宽比不一致，不能靠角点直接映射。

---

## 2026-08-21 · ⭐⭐⭐ **sm25 gt 候选包已产出，只差用户签字**

### 一、结果

**G1–G5 · G7 · G8 · G9 全绿，零 BLOCK 诊断**；G6/G10 红是**设计上就该人签**的两道
（G6 = 近阈值面待人工确认、G10 = 签字本身）。
候选包 → [`logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/`](logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/)
- `gt.json content_sha256 = 6c36d9e83f0cfdf49b5b769cac2facf66a63dcb0b0ef5d62513b47c3e82dcfbb`
  ⭐ **主控与施工席两次完全独立构建，逐位相同**
- 立面 **34 条 = 31 窗 + 3 门**（西 4+2 · 南 7 · 北 8 · 东 12+1）· 分区 F1 **14** / F2 **15**
- 主控**亲自看过** 1F 平面叠图与西立面叠图：分区标注齐全、红色外轮廓贴合 Z 形、
  窗门位置与图上洞口逐个重合、门 `z=[0.20,2.30]` 合理

### 二、⭐ 转换请求：唯一"要看图"的活已自动化

[`build_request.py`](logs/experiments/2026-08-20_sm25_conversion_request/build_request.py) **确定性生成**，零手抄坐标。
像素标定 = **白色线投影峰值 ↔ DXF 线位对齐**（平面 RANSAC / 立面全高全宽强峰）。
**自证**：四个立面由 x 轴与 y 轴**独立**算出的尺度互差 < 0.1%；第三条线的交比与图纸标注比值一致
（0.2000 vs 0.2 · 0.39994 vs 0.4 · 0.30020 vs 0.3 · 0.29993 vs 0.3）。
残差：平面 40+ 点 ≤ 2.7 px · 立面 6 点 ≤ 0.2 px。

### 三、修掉的三处转换器缺陷（sol 施工 · 待 GLM 跨家族审）

| 缺陷 | 实证 | 修法 |
|---|---|---|
| `_ray_thickness` 对 union 后的边界求交，射线在 T 接头拐进垂直墙链 | **连穿 11 个墙面**（0→980→…→14240）⇒ 量出 **14.24 m「墙厚」** | 新增 **face-pair 厚度证据**（平行面线 + 跨度重叠）+ **保留一次独立几何断言**（出口点必须落在对面面线上）|
| `_classify_openings` 用**非凸 footprint 的全局代表点**判内外 | 一扇 **8 m 宽真外窗**（两候选面距外环 240 vs 0）被判成内窗 ⇒ 外洞口 15 vs 外皮缺口 16 | 改为局部双面距离 |
| 跨层 footprint 用**浮点逐位相等**比较 | 两层并排画时残差 **3.55e-15 m** ⇒ **只要多层就永远过不去**；sm24 单层从未现形 | 几何等价比较（顶点数/顺序 + 逐顶点 ≤ 现有 `node_join`），⛔ 未新增也未放宽任何容差值 |

⭐ **`ThicknessEvidenceKind` 声明六种证据、原先只实现第 2 种**（靠门窗洞口封边）
⇒ **一道整条无洞口的墙永远拿不到厚度证据**。用户当场指出「这个从 dxf 里读不出来吗」——
**能读**（`1449`/`144A` 两面线间距精确 240.000），⇒ 主控原提的「人工签字覆盖」作废，改走 face-pair。

### 四、⛔ 四处「肉眼看不出但实际差一点点」（用户当场指出这在建筑图纸里很常见）

| # | 位置 | 量级 | 处置 |
|---|---|---|---|
| 1 | 图纸：`13AD`/`13AE` 一堵 120 墙偏离水平 | **5.808 mm**（= 图上 **0.27 像素**）| **用户授权修 DXF**；5 条线吸附到图纸自身已有的精确坐标；原件存 `sm25-L_t3_as_received.dxf`；**核实 916 图元一个不少、句柄集合相同、恰好 5 条线变坐标** |
| 2 | 我的请求：世界原点未吸附到转换器的 0.1 mm 网格 | **11.858 µm** | 已修（原点吸附同一网格）|
| 3 | 代码：跨层轮廓浮点逐位相等 | **3.55e-15 m** | 已修（几何等价比较）|
| 4 | 我的请求：沿墙比例用除法算出来 | **1–2 个 ULP** | 已修（按契约直接写 `±metres_per_unit` 常量，只算 offset）|

⇒ **用户口径**：「先接受有一点不对，直接把 dxf 改对，先跑再说，这个在 gt 里声明一下；
后续再看这种情况怎么处理，因为其实这种肉眼看不出来、但是实际错了一点点的在建筑图纸里还挺常见的。」
⇒ **登记：图纸微小不精确的通用处置策略**（待专项）。

### 五、⭐ 我这一晚错了 6 次，全靠施工席停下上报捞回来（累计 21/21）

| 我说什么 | 实测推翻 |
|---|---|
| 「sm24 没有相邻 wall face」 | sm24 同样 43 面、50 对共享边界；差别在于没有射线落在 `outer_skin↔wall_axis` 转换接头 |
| 「改成逐 wall face 取最近穿出」 | 单个 S4 face 本身就是 T 形，只会把 14240 换成 **980/2080** |
| 「从 WallBand 取厚度」 | 那道墙**根本没有 band**（无洞口 ⇒ 无 cap 证据）|
| 「A_room 调到 5.0 就好」 | 分对了房间数，却暴露下游墙厚证据全崩（探路才发现）|
| zone_id 直接抄 sm24 的 `z0..z13` | 两层撞 14 个；GT 合同要求**全局唯一** |
| 「立面 scale 那行精确比较是缺陷」 | **反了**：比的是两个声明值，该逐位相等；是我用除法算出了 1–2 ULP 误差 |

### 五之二、⭐⭐ GLM 跨家族审：**REWORK**，靠跨版本重建抓到两条谁都没看见的东西

裁决 [`verdict/2026-08-21_sm25_plan_side_glm_verdict.md`](logs/reviews/verdict/2026-08-21_sm25_plan_side_glm_verdict.md)
= 零 BLOCKER，三修有效、七把锁 neuter 全过、容差四项全过、全仓与主控逐位一致。**但两条 MAJOR：**

| # | 内容 | 主控处置 |
|---|---|---|
| **F1** | ⭐ diff 里有**派工单未声明的第四处行为变化**：`_append_plan_geometry` 的发射条件改用 `footprint.exterior.covers()`。shapely `covers` 在**共线**几何上浮点误判（`distance` 精确为 0 却 `covers=False`）⇒ sm24 六条**纯外轮廓边**被误发射 ⇒ GTV3_ZONE 19→25 ⇒ **sm24 重建 gt.json 76 处字段差异、`content_sha256` 变化**（几何内容零漂移，变的是生成句柄与溯源）| ✅ **已修**：换成**整边判定** `edge.difference(exterior.buffer(node_join)).length <= node_join`。实测 sm24 纯轮廓边差集 = 0、sm25 必须发射的延伸段 ≈ **119 mm**，稳定可分。⛔ GLM 已证伪 `distance<=1e-6`（sm25 那 23 条延伸段 distance 全是 0）|
| **F2** | face-pair **抢占** sm24 三条边的证据归因（38 全 cap/jamb → 35 + 3 face-pair）| ✅ **接受并显式声明**。⛔ 主控最初判「让 cap/jamb 优先」是**错的**：GLM 的 N3 反证显示这 3 条边**原本走 donor-collapse 借邻边的 cap 证据**，而 face-pair 是**本边自有的两条面线** ⇒ **自有证据取代借来的证据 = 归因更诚实**。已写进代码注释 |
| F3 (MINOR) | 主控要求的「独立几何断言」实为**簿记一致性重读**（与 binding 读同一份不可变数据，活链上结构性恒真）；真正防线是 S4/G8（GLM 挪 `146E` 四档 0.1/0.5/1.5/60 mm 全部 BLOCK）| ✅ 改名 `_face_pair_binding_is_consistent` + 注释如实写明，⛔ 不改逻辑 |

⭐ **真缺口 = 全仓 2946 把锁对 F1 全盲**：L1 只比对 `_ElevationRecord` 与规范化 DXF，
**从不比对最终的 `gt.json`**。⇒ 已补**跨代码改动的 gt.json 稳定性锁**
（sm24 走 `build_review_bundle` 全链重建、逐字段比冻结基线，只豁免已登记的溯源哈希链）；
**自证**：换回旧 `covers` 判据该锁必红（GTV3_ZONE 19→25）。

⚠️ **sm25 答案哈希因此变化**：`785f8273…` → **`6c36d9e8…`**（主控与施工席两次独立构建逐位相同）。
⇒ **幸好用户还没签**——签名绑哈希，签了就得作废重签。

### 五之三、⭐⭐⭐ C2 首考成绩（sm25-L 1f × Sonnet 5）

> 判卷器修好后的**权威分数**（主控独立复跑对账）。⛔ 探索档 n=1，**不作成绩**。

| 判据 | 得分 |
|---|---|
| **boundary_complete（外轮廓）** | **94.4%**（85.00 / 90.00）|
| walls_complete（全部墙） | 84.4%（87.51 / 103.64）|
| no_extra_walls | 多画 0.26 m |
| **windows_placed（窗放对）** | **8 / 15 = 53.3%** |
| window_plan_geometry | 53.3%（16 / 30）|

**⭐ 病灶定位：7 个 miss 全部集中在东墙 `x=15, y 6→20`**（那列 7 个小房间的外墙），
其余六面墙的窗 **8/8 全对**。而且这 7 个**不是乱画**：

| 读图器 | gt | 差 |
|---|---|---|
| 7.65–8.69 · 9.73–10.25 · 11.29–12.67 · 13.71–14.23 · 15.27–16.65 · 17.67–18.21 · 19.25–19.94 | 6.74–7.64 · 8.74–9.64 · 10.36–11.26 · 12.74–13.64 · 14.36–15.26 · 16.74–17.64 · 18.36–19.26 | **整组 +0.89 ~ +0.99 m** |

⇒ **2 米模数的节奏一个不差，整列沿墙锚点偏了约 0.95 m**（容差 0.4 m）⇒ 7 个全 miss。
**不是「看不清」，是「数对了、锚错了」。** 且该墙正是 **Z 形凹口那一面**——
它的位置要靠凹口定，不像别的外墙能直接贴图框边。⇒ **登记为 C2 待查项**。

**⛔ orchestrator 本轮两次判读失误**：
① 先说「效果一般证据上不成立」——那是**我挑了强的那半**（8 条外轮廓线）看，
完整快照下窗只有 53.3%，用户的直觉对了一半。同族 [[proxy-mistaken-for-the-thing]]。
② 「歧义观测移出分母」语义错，被 sol 推翻（分母是 gt 派生的）。
③ 新脚本**第二次**漏登记 `affected_tests_rules.yaml`，同一把锁抓我两回。

**过程纪律**：pilot 裁定在判卷**之前**写成并封存（`_run/pilot_r1/orchestrator_verdict.md`），
形态四条判据全过；merge 后产物哈希与封存件一致（`8b028d4d…`）。

### 六、顺带落地

- 新增 [`scripts/tool_scripts/gt_review_build.py`](../scripts/tool_scripts/gt_review_build.py)
  —— 补齐 `gt_review_{build,sign,rerun}` 三件套里**缺失的第一件**（此前只有测试在调 API）。
- ⚠️ 候选包**必须建在受保护根之外**（`gt_sources/` 下会触发 `tarch_staging_input_protected_path`）。

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
