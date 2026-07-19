# B6 词汇批 施工派工单（terra 施工 → Opus 子代理审 → 主控轻门）
2026-07-19 · Opus 主控 · C2 收官路径 · **机械词汇批**（无细稿→对抗审；派工单即规格）

## 0. 分工 & 流程（用户 07-19 拍额度侧=terra 施工）
- 施工：**terra**（GPT 侧）。
- 施工审：**Opus 子代理**升一档（独立上下文、活体探针）。
- 主控轻门：Opus 独立全量 pytest + 亲核 diff。
- 谁写谁不批（terra 写 → Opus 审，跨厂商交叉）。
- 基线：当前 **1427 passed + 9 xfailed**（`git HEAD = 2b044a8`，工作树须干净起步）。

## 1. 本批范围 = B6 **词汇 only**，做到「跑测之前」为止、**不实跑 sm25-L**
依据：[proposals/c2_full_unlock_design.md](../../proposals/c2_full_unlock_design.md) B6 行「词汇(外轮廓 polyline/翼分界/虚线四负例)」+ §T'/A-08（line 56）+ plan.md 07-19 用户定收尾路线。

**目标**：给 0_reading 补一套词汇 + 两个可选 schema 字段 + 负例测试锁，让识图**能表达** L 形凹角外轮廓、两翼分界、以及虚线（隐藏/上层投影）观测——**不真跑图**（sm25-L 素材尚未入仓，由用户与主控另做）。

**明确不越界**（本批一律不碰）：
- ❌ 不跑 sm25-L / 任何端到端；不产 case_data / gt。
- ❌ 不改 1_correction / 几何内核 / 装配对这些词汇的**消费**（消费在 sm25-L 实跑时验，属下一轮）。
- ❌ 不动任何现有 golden / baseline；不改现有 pen 语义。
- ❌ 不引入 legacy 回归（legacy reading 视图须原样加载）。

## 2. 三施工项（设计决策主控已钉死，照实现）

### 项 1 — Stroke 新增 `line_style` / `visibility`（`src/agent/reading/schema.py`）
在 `class Stroke` 增两个**可选**一等字段（默认 `None`）：
```python
line_style: Literal["solid", "dashed", "dash_dot", "unknown"] | None = None
visibility: Literal["visible", "hidden"] | None = None
```
- 语义（写进 Stroke docstring）：二者是**图面-局部识别属性**（image-local recognition attributes），**非拓扑/世界字段**。`visibility="hidden"`（或 `line_style="dashed"`）= 观测为虚线/剖切面以上（隐藏或上层投影）。**下游禁把 hidden 观测提升为实体 Window**——那是 correction 阶段的合同、在 sm25-L 实跑时强制；本批只提供**词汇 + 记录纪律**，reading 阶段忠实记录即可。
- 已核：这两名**不在** `_FORBIDDEN_STROKE_KEYS`（gate① `_no_topology_fields` 不会误拒）；`extra="allow"` + 默认 None ⇒ legacy 产物加载不变。
- `src/agent/reading/__init__.py` 导出无需变（Stroke 已导出）。**核** `legacy.py:migrate_view` 无需合成这两字段（默认 None 即可），但须加 legacy 往返测试证明（见项 3）。

### 项 2 — 0_reading skill 词汇（`skills/intake_pipeline/0_reading/reading_guide.md`）
纯文档（skill = 英文纯当前版本 spec，禁时间戳/版本号/changelog）。加三处：

**2a. 平面外轮廓 polyline（L/U 非方形）** — 新增一张 card 或在 `wall` card（§D）下补一节：
- 识别不变量：非方形平面的**整条外包络环**（ordered outer ring），关键新线索 = **凹角（concave corner / reflex vertex）**——方形无、L/U 有。
- 表达方式：**已有 schema 即可**——外轮廓可作**连成环的 `wall` 段**，或作**单条 `wall` pen + `polyline` geometry**（`geometry.kind="polyline"`, `points=[[x,y],...]`；gate① 已合法，无需改 schema/linter）。二者皆可，凹角顶点须在环上如实出现，不得抹平成方形。
- 不替代逐墙 tracing；这是**整体包络**词汇。

**2b. 翼分界（wing division）** — 补一节（纯佐证词汇，无新 schema）：
- 识别：平面上明确标注的**两翼分界**（L/U 两肢相接处的分界标注/尺寸/轴线）。
- 记录：**仅当图上有明确翼分界标注时**，用现有载体记录（`dimension` / `grid-axis` 类 stroke / note）；无标注则**不发明**（几何上凹角已隐含分界）。对齐设计 line 66「仅有明确翼分界标注时立面可佐证/修正」。

**2c. 虚线 / 隐藏线处理** — 在 §B（线型语法）或 `window` card（§D）下补一节，配**四负例口径**：
- ① **实线可见**：实体窗 → `line_style="solid"` / `visibility="visible"`（或留 None）→ 正常窗观测。
- ② **虚线隐藏**：虚线窗/上层投影 → `visibility="hidden"`（`line_style="dashed"`）→ **不作实体窗**；忠实记录该 stroke（带 hidden 标记），**或**登记 `uncaptured` 一条 `{source_id, kind: "hidden_window_candidate", reason}`（对齐设计 A-08 line 56，供 conflict/audit）。
- ③ **虚线误读**：一条虚线不得被静默当作实线窗——有了 `line_style` 字段就如实记为 `dashed`，不得强转 `solid`。
- ④ **同位实虚重叠**：同一位置一实一虚 → 记为**两条独立 stroke**（唯一 id、各自 line_style/visibility），实线=实体、虚线=hidden，不得合并、不得互相吞。

### 项 3 — 负例测试锁（新测试文件，建议 `tests/test_reading_line_style_visibility.py`）
逐条独立测试（禁合并成一次断言总失败）：
- **四负例**各一测：①solid-visible 正常；②dashed-hidden 记为 hidden（字段往返 + 若走 uncaptured 则条目结构良好）；③dashed 保 `line_style="dashed"` 不被强转；④同位实虚 = 两独立 stroke，id 唯一、属性各异，gate① `check_reading_view` 的 unique-id/pen_kind/geometry 全 pass。
- **schema 往返**：带新字段的 Stroke 序列化/反序列化保值；**legacy 无字段**视图加载 + 序列化不变（默认 None、`migrated_from_legacy` 路径不受影响）。
- **外轮廓 polyline affordance 锁**：一个平面 `wall` pen + `polyline` geometry（含凹角，≥4 点）的 view 过 gate① `check_reading_view` INVARIANT 全 pass（锁住「polyline 外轮廓合法」这一既有能力，防未来回归）。
- **gate① 可选增强（若加）**：若你判断给 gate① 加一条 **CROSS_CHECK（flag，永不 block）** 标记「window 且 visibility=hidden/line_style=dashed」以便 review 可见 hidden 窗，则须配正/负两测（含此增强不改变现有 1427 绿）。**此增强非必需**——schema+skill+四负例已足；加则须证零回归。

## 3. 纪律（施工审必打，先做到位）
- **shipped-untested = 连续多批头号 MAJOR**：每条新词汇/字段/分支须有独立测试锁，四负例不缺项。缺一条即视为未交付。
- **禁 fail-open / 禁自指假绿**：测试断真值、不空跑；不得用现有总绿数冒充新覆盖。
- **诚实部分交付 > 藏假绿**（B4b Phase B 教训）：做不完就如实报未完成，别占位充数。
- **零 golden 改动**：现有 baseline/golden 一字不动；legacy reading 视图加载行为不变。
- **skill 库纪律**：`reading_guide.md` 保持英文纯当前版本 spec，不写时间戳/版本/缘起 case。

## 4. 全量测试归属
**terra 只跑本批 targeted tests**（codex 环境 ~30s 杀长进程，全量自验不可得）；**全量 pytest = 主控轻门唯一权威**，terra 不得以自跑总绿数作交付证据。

## 5. 交付回报
产出后回报：改了哪些文件（新增 / 修改对照）+ 三项各自测试落点 + targeted tests 结果 + **诚实标注哪些做完 / 未完 / 存疑**（尤其：是否加了 gate① 可选增强、legacy 往返是否已锁）。
