# 接线问题统筹摸排 · 第一轮（2026-08-08）

> 立项依据 = [plan.md「六之八」](../../../plan.md)（用户 2026-08-07 定：登记，下轮启）。
> 本轮由 orchestrator 亲跑，**零 LLM 成本、只读、零生产码改动**。
> 工具在 [`tools/`](tools/)，四个脚本都可复跑（纯静态 AST 分析、确定性）。
>
> ⚠️ **本目录被 `.gitignore:7` 的 `20*_*/` 规则吞掉**，报告与脚本是
> `git add -f` 强制入库的 —— **这正是 F-8 那个坑的同型**，摸排自己当场撞了一次（见 §10）。
> 四份 JSON 原始产物（`exposure/gates/subtract/single_source.json`，共约 180 KB）
> **有意不入库**：它们是脚本的确定性派生件，跑一遍就能重生成。

## 0. 本轮做完了什么 / 没做什么（先说边界）

| 步骤 | 状态 | 说明 |
|---|---|---|
| 1 枚举暴露面 | ✅ 完成（下游 + correction） | 机械 AST 提取 |
| 2 枚举门 | ✅ 完成 | 355 个 raise 点全量提取并分类 |
| 3 相减 | ✅ 完成，**但机械判据有噪声、已逐条实看修正** | 见 §3 |
| 4 语义轴 | 🔶 **部分**：在步骤 3 的候选上做了，未对全部 89 个写入参数逐个做 | 见 §4 |
| 5 单一来源审计（轴 B） | ✅ 机械扫描完成，72 组重复已收敛到 3 组真候选 | 见 §5 |
| F-16 worked example | ✅ **已定性** | 见 §6 |

**⛔ 本轮不含**：任何修法施工、任何下游 prompt 改动（权属见 §8）。

## 1. 盘子的真实形状（与立项时的估计有出入，需更正）

立项登记写的是「11 个 LLM 接口出口 + 19 个拒绝点」。实测后要更正两处：

**① 下游 9 个节点的暴露面不是「字段」，是「工具参数 schema」。**
它们是 ReAct agent（[`react.py`](../../../../src/agent/react.py)），模型看见的是
`llm.bind_tools(tools)` 生成的参数 schema + 节点 system prompt + specs 文本三样东西。
这与 correction draw（结构化输出、看 JSON Schema）**形态不同，修法也不同** ——
F-15 用的 `producer_facing_json_schema` 机械剥除**在下游用不上**，下游要在工具定义侧动。

```
10 个工具工厂 / 55 个工具 / 95 个参数（其中写入侧 89 个）
```

**② 拒绝点是 355 个不是 19 个**，但绝大多数不是「拒绝模型输出」：

| 类别 | 数量 | 说明 |
|---|---|---|
| 显式 `category="model_draw_error"` | 18 | 判定为模型的错 ⇒ 归档重抽 |
| 显式 `category="input_integrity_error"` | 39 | 判定为输入的错 ⇒ 硬崩 |
| 无 category（内部不变量 / 格式校验 / hash 自校验） | 298 | **多数模型触发不到，步骤 3 不得记为保护** |

⚠️ 另有 `WindowHostResolutionError.category` 是**按每条 conflict 的 `fallback_action` 自归类**推导的
（[`window_host.py:399`](../../../../src/agent/correction/window_host.py)），不在上面 18/39 的字面统计内。
这正是 memory 记过的「自归类设计必须逐点审计」那套机制，本轮未重审。

## 2. ⭐ 三个节点可以整体排除出射程（好消息，缩小盘子）

`construction` / `material` / `schedule` 三个节点的 prompt 与工具**完全不碰几何**，
产出的是材料热工参数、层次组合、时间表 —— 全属不变量 #1 里「LLM 该做的物理语义」。

⇒ **同族缺陷（模型看得见但不该它管）在这三个节点上射程为零。**

### ⭐⭐ 补完后的结论：轴 A 在下游的覆盖率 = **9/9（100%）**，本轮已收官

机械确认（`grep -l build_react_agent src/agent/nodes/*.py`）：**恰好 9 个 LLM 节点**。
`intake` / `cross_ref` / `validate` / `simulate` 四个**根本不是 LLM 节点**
（纯派发与代码校验，零 prompt、零工具、零 `create_llm`）⇒ **不在轴 A 射程内**。

| 节点 | 本轮结论 |
|---|---|
| `zone` | ✅ **已闭 —— 且是全项目唯一的正面样板**（prompt + 工具侧拒绝 + 段尾 normalizer 三层）|
| `surface` | ✅ 已闭（F-12 改逐字照抄，且**有漂移门在真量**）|
| `fenestration` | ⭐ **A-1 命中**（`multiplier`）；顶点侧已闭（F-12 同批）|
| `construction` / `material` / `schedule` | ⭕ **射程外**（完全不碰几何，纯物理语义）|
| `hvac` | ✅ 干净（纯物理语义，参数全是引用完整性）|
| `lights` / `people` | 🔶 **A-2 弱命中**（绝对值路径要模型自己乘面积）|

⇒ **立项时的「剩 7 个从没人看过」现已全部看完。** 轴 A 下游侧本轮收官，
剩余工作在 correction draw 侧（步骤 4 全量语义轴）与轴 B。

## 3. ⛔ 步骤 3 的机械判据有噪声 —— 如实登记（这条本身是方法论产出）

[`subtract.py`](tools/subtract.py) 用两个机械判据初筛：
「prompt 有没有提到这个参数名」×「有没有门约束它」。**结果 0 条候选，是假的。**

两个判据各有一类错：

- **门判据假阳性**：它把 `multiplier: int = Field(1, ge=1)` + `raise ValueError("Multiplier must be at least 1.")`
  算成了「有门」。但那是**范围校验不是语义门** —— 它管的是「值合不合法」，
  不是「值该等于什么」。⇒ 与 memory 里「非 None ≠ 成功」同型：**断言写在合法性上等于没断言。**
- **prompt 判据假阴性**：`create_surface(name=...)` 被判「prompt 没提」，
  但 prompt 里写的是 "Surface **names** are deterministic public names from surface_specs"。
  token 匹配抓不到复数与自然语言指代。

**⇒ 修正后的判据（下一轮沿用）**：机械初筛只用来**排序**，
「有门」必须落到**具体那一行在约束什么**，逐条实看。25 条初筛结果人工全看完，成本约十分钟。

## 4. 轴 A 结论：真命中收敛到 1 个，另有 1 个弱命中

### ⭐ A-1（真命中）· `create_fenestration(multiplier)` —— F-15 第一堵的完整同型

```
src/agent/tools/fenestration_tools.py:19    multiplier: int = 1
src/agent/tools/fenestration_tools.py:38    "multiplier: Number of identical copies (>= 1)."
```

- **模型看得见**：是工具参数，且 docstring 主动解释了它的语义。
- **不该它管**：几何内核逐窗建面，`fenestration_specs` 里有几扇窗就是几扇窗；
  内核产物**通篇不提 multiplier**（`grep` 在 `geometry/specs.py` / `intakeoutput.py` / `state.py` 零命中）。
- **提示词一个字没提**：`FENESTRATION_SYSTEM_PROMPT` 全文无 multiplier。
- **门只有范围校验**：`ge=1` + "must be at least 1"，**没有任何门比对它是否等于内核意图的 1**。
- **⛔ 漂移门看不见它**：`output_coordinates.py` 的 `_vertex_drift_issues` /
  `_live_idf_vertex_drift_issues` **只比顶点坐标**，`multiplier` 零覆盖。

⇒ **后果**：模型给某扇窗填 `multiplier=3`，EnergyPlus 按 3 扇窗算得热，
**全链路零阻断、全仓测试全绿、EP 0 severe、漂移门 0 条**。
这正是 08-07 那条「三绿齐不等于对」的形状 —— 且**唯一能穿透它的动作（量物理量）目前只量了顶点与宽高，不量 multiplier**。

**⚠️ 未实测**：本轮**没有**跑真链路验证模型真的会填非 1 值。这是**结构性风险的坐实，不是缺陷发生的坐实**。
按项目纪律（探针 ≠ 锁、假设不得当事实），定性为**高优先级候选**，不记为已发生的缺陷。

**同族但已被覆盖的两个**（如实区分，不凑数）：
- `create_zone(multiplier)` —— prompt **有**提（"multiplier is 1 unless the description explicitly duplicates a typical floor"）
  ⇒ 属 prompt 覆盖。但按项目已立的结论「**prompt 不是防线**」，它仍是同一盘子里的弱项。
- `SurfaceSchema.multiplier` —— schema 里有（`data_model.py:966`），但 `create_surface` **没有暴露这个参数**
  ⇒ 模型碰不到 ⇒ **不是候选**。（正面案例：暴露面比 schema 窄，就是有效的「让它看不见」。）

### 🔶 A-2（弱命中）· lights/people 的「绝对值」计算方法

`create_light(design_level_calculation_method)` 允许 `'LightingLevel'`（绝对 W），
`create_people(number_of_people_calculation_method)` 允许 `'People'`（绝对人数）。
选这两条路，模型就**必须自己拿楼板面积去乘** —— 而面积是几何内核算过的、模型手里没有权威值。
prompt 用 "Typical office LPD 8-12 W/m^2" 引导走 `Watts/Area`，但**没有禁止**绝对值路径。

⇒ 语义轴命中（要产出它需要做代码已做过的推导），但后果是**物理载荷偏差不是几何错**，
且 EnergyPlus 侧 `Watts/Area` 本就由 EP 自己按面积算 ⇒ **严重性远低于 A-1**。登记，不排期。

### ✅ 已闭合的确认（对照组，证明摸排判据能认出「已修好」）

- `surface` 的顶点：prompt 已改逐字照抄（F-12），且**有漂移门在量**（A 层 + B 层）⇒ 已闭。
- `facade_segments` / `facade_segment_id` / `north_axis`：已打 `CORRECTION_DRAW_FORBIDDEN`
  并从给模型的 schema 机械剥除（F-15）⇒ **模型看不见了** ⇒ 已闭。
- `create_zone` 的 frame 四字段：**三层防护**（换 prompt + 工具侧 `_reject_if_nonzero` + 段尾无条件 normalizer）
  ⇒ 全项目**唯一**做到「不只告诉它别碰，还让它碰不到」的样板。**A-1 的修法应照抄这个形态。**

## 5. 轴 B 结论：72 组重复收敛到 3 组

[`single_source.py`](tools/single_source.py) 机械扫出 **72 组**跨文件重复的字面量集合。
**绝大多数是 `Literal[...]` 类型标注**（North/South/East/West 出现 27 处）——
类型系统本身在强制同步，**不是 F-15② 那种危险重复**，不登记。

F-15② 的真实特征是：**一处数据驱动 / 一处硬编码，且没有任何机制保证同步，漂了静默出错。**
按此收敛出 3 组：

### B-1 · `RunProfile` 档位清单 —— ⛔ **初判过重，已当场查证并下修（如实登记）**

四档清单确实在 4 个文件里独立声明 5 次（`policy.py:34` / `run_config.py:88` /
`run_policy_freeze.py:55` 与 `:56` **同文件内两遍** / `checks/schema.py:42`），
四者之间无 import 关系。**但逐条查证后，这组重复不是 F-15② 那种危险重复：**

- **加档位会硬崩不会静默漂移**：判定侧 `checks/schema.py:42` 是 `Literal[...]`，
  若有人只给 `run_config.py` 加第五档，pydantic 校验当场拒 ⇒ **类型系统兜住了**。
- **声明侧的静默降级已于 08-04 修好**（`_parse_run_profile` / `_parse_capability_profile`，
  R1-2 与 r2-1）：present-but-invalid 现在 **fail-closed 抛错**，
  docstring 明写此前「一个 typo 就把声明的严格档静默降级到 CLI 默认 exploratory」。

**⇒ 更正**：本报告初稿把 08-02 的 P0 断线二（声明 regression、落盘 exploratory）
挂到这组重复上，**方向指偏了** —— 那条路径已被 08-04 那批堵上。**撤回该关联。**

### ⭐⭐ B-1′（查证过程中撞出的真问题，比原候选更尖锐）· 严格档是 **fail-open** 的

两处独立的 fail-open，都不是"清单漂移"而是"默认值选错了方向"：

```
src/validator/checks/schema.py:182   run_profile: RunProfile = "exploratory"   ← 函数默认参数
src/validator/checks/schema.py:253   run_profile: RunProfile = "exploratory"   ← 模型字段默认
src/validator/checks/schema.py:55    _EVIDENCE_BLOCK_PROFILES = {"golden", "regression"}
```

- **① 默认档 = 最宽松档**：调用链上任何一环忘记传 `run_profile`，
  就静默按 `exploratory`（不阻断）判 —— **传递断点的后果是放水，不是报错**。
- **② 阻断集合是白名单**：`:231`/`:238` 判的是 `run_profile in _EVIDENCE_BLOCK_PROFILES`。
  将来若新增一个比 regression 更严的档位，它**不在集合里 ⇒ 默认不阻断** ——
  **新增的严格档默认是不严格的**。同形的白名单在 `_PLAN_FRAME_BLOCK_PROFILES` /
  `_OCR_ANCHOR_BLOCK_PROFILES` / `_DIMENSION_ENDPOINT_BLOCK_PROFILES` 共 4 处。

⚠️ **两条都是结构性 fail-open 的坐实，不是「已发生事故」的坐实**；②
需要「有人加新档位」才会触发，属潜伏形态。**登记，未排期。**

### B-2 · `{image_left_to_right, image_right_to_left}` 11 处

用户 2026-08-02 已拍板**钉死 left-to-right**，`local_x_positive` 降为「历史可加载、判卷永不读取」的废弃字段。
⇒ 11 处仍在声明一个已废弃的二元选项 = **清理债**，不是活缺陷。登记。

### B-3 · `{facade_visibility_v1, floor_footprint_v1}` 4 处 feature 名单

`facade_applicability.py` / `feature_state.py`×2 / `window_host.py` 各硬编码一份。
形状同 F-15②（特性开关清单多处声明），但**本轮未查证它们是否已经漂了**。登记待查。

## 6. ⭐⭐⭐ F-16 已定性 —— 是同族，但是一个**新变种**

上轮登记的报错：
```
window W-F1-N1: floor must match referenced floor name
（模型写 floors[0].id="F1" / name="Level 1"，窗引用 "F1"，门要求匹配 name）
```

### 根因不是「id/name 挑错」，是**「这扇窗在哪一层」这个事实有四处独立声明**

| # | 声明处 | 谁写 | 形式 |
|---|---|---|---|
| 1 | `Window.floor` （[`schema.py:97`](../../../../src/agent/correction/schema.py)） | **模型** | 楼层 **name** 字符串 |
| 2 | `WindowV3.floor_id` （`schema.py:244`） | **模型** | 楼层 **id** 字符串 |
| 3 | `rank[floor_id]` （[`window_sources.py:1008`](../../../../src/agent/correction/window_sources.py)） | 代码 | 按 `z_floor` 排序算出的序号 1..N |
| 4 | `row.floor_ref` （`window_sources.py:988`） | reading 产物 | manifest 里那张平面图声明的楼层号 |

三道门在维持它们互相一致：
`#1==#2`（`schema.py:303`）· `#3==#4`（`window_sources.py:1013`）· 立面 z 区间反推的层 `==#2`（`:1019`）。

**成因是 schema 演进的双轨残留**：base `Window` 用 name 关联（v1 形态，`floor: str` 必填），
v3 新增 `floor_id` 作主键，**两者并存**，靠一道门维持一致。
模型每建一扇窗要写两个指向同一层的字段、**写法还不同**，且要让它们与两个它看不全规则的派生量（#3/#4）自洽。

### ⇒ 定性

- **是同族第七次**，但**不是**「模型看得见但不该它管」（楼层归属确实该模型管）；
- **是轴 B 的第三种形态**：前两种是「代码 vs 代码」（F-13）与「schema vs 门」（F-15②），
  **这次是「模型输出内部的两处声明」**。
- ⭐ **plan.md「六之八」的方法里没有这一格** —— 轴 B 的定义要从「同一约定的多处声明」
  扩写为**「同一事实的多处声明，含模型输出内部」**。⇒ 建议改 plan。

### 修法方向（⛔ 未施工，且不像 F-15 那样一行标记）

让模型**只声明一次**（保留 `floor_id`），`floor` 改为由代码从 `by_id[floor_id].name` 派生填充。
**⚠️ 不能简单打 `CORRECTION_DRAW_FORBIDDEN`**：`floor` 在 base `Window` 上、是 v1/v2 也在用的必填字段
⇒ 动它要处理 schema 版本兼容，**是设计不是补丁**。

## 7. 本轮方法论产出（三条）

1. **「有门」必须落到那一行在约束什么** —— 范围/格式校验（`ge=1`、枚举、非空）**不构成保护**。
   本轮机械判据正是栽在这里（§3），与 memory 的「非 None ≠ 成功」同型。
2. **暴露面比 schema 窄，本身就是有效防线** —— `SurfaceSchema` 有 `multiplier` 而
   `create_surface` 不暴露它，模型就碰不到。**这是「让它看不见」的最省事形态**，值得作为默认设计习惯。
3. **轴 B 要扩写**：同一事实的多处声明，**包括模型输出内部的冗余表示**（F-16）。

## 8. ⛔ 权属发现（对下一轮排期有实际影响）

CLAUDE.md §3 out-of-scope① 的原文是下游 9 subagent 的 **「prompt 演进」** 归协作者。
**工具定义（`src/agent/tools/`）不是 prompt** ⇒ 在本项目权属内。

**且已有先例**：`zone_tools.py` 的 `_reject_if_nonzero` 就是本项目自己加的工具侧硬门（E4 契约）。

⇒ **A-1 的修法可以完全走工具侧**（把 `multiplier` 从 `create_fenestration` 参数表摘掉，
或加工具侧拒绝），**不碰任何下游 prompt、不触发权属阻塞**。

## 9. 下一轮的入口（按价值排序）

| # | 事项 | 成本 | 说明 |
|---|---|---|---|
| 1 | **F-16 设计**：楼层归属的四处声明收敛到一处 | 中，需设计 | **卡着 1_correction 当前跑不通**，价值最高 |
| 2 | **A-1 修法**：`create_fenestration(multiplier)` 照 `zone_tools` 三层形态处理 | 小 | 权属内、走工具侧，不碰下游 prompt |
| 3 | **B-1′ 修法**：严格档 fail-open 两处（默认档 + 阻断白名单） | 小 | 潜伏形态，但修法便宜 |
| 4 | 步骤 4 全量语义轴（89 个写入参数逐个过） | 中 | 本轮只在候选上做了 |
| 5 | cross_ref / validate 两个节点（本轮未看） | 小 | 补齐「9 个节点」覆盖 |
| 6 | B-3 查证 feature 名单四处是否已漂 | 零成本 | |

~~B-1 查证~~ **已在本轮当场做掉**（结论见 §5，初判被自己推翻并更正）。

## 10. ⛔ 摸排自己撞上 F-8 同型的坑（当场登记）

本报告写完后 `git status` 里**看不到它** —— `.gitignore:7` 的 `20*_*/`
把整个 `AI_agent/logs/experiments/2026-08-08_*/` 目录吞掉了。

若不处理，后果是：**plan.md 会引用一个不在版本库里的文件**，
换台机器 / 换主控模型就打不开 —— 与 F-8「测试依赖了被 gitignore 挡住的活输入」
**同一个坑的文档面**。已 `git add -f` 入库。

⇒ **登记为 F-8 防复发那条债的第二面**：既有的选项 A/B 都只盯**测试输入**，
盯不住**被文档引用的过程痕迹**。建议 A 方案的 AST 扫描扩一条：
**管理文档（plan.md / CLAUDE.md / decision_log.md）里的相对链接目标必须 `git ls-files` 命中。**

### ⛔⛔ 比上面更毒的一条（orchestrator 当场又栽了一次，实测）

**文件已经 `-f` 入库之后，后续每一次修改 `git add` 仍会被 `.gitignore` 拦下** ——
本轮实测：commit 后补写本节 19 行，`git add` 静默失败、`git commit --amend` 照常成功，
**`git status` 干净、`git log` 正常，但那 19 行根本不在 commit 里**（`git show HEAD:<file> | grep` 才照出来）。

⇒ **这不是「第一次入库要记得 -f」，是「以后每次改都要 -f」**，且失败形态是**静默的**：
命令返回 0、提交看起来成功。**任何落在 `20*_*/` 目录里的活文档都会反复中招。**

⇒ **修法建议升级**（原「扫描链接目标」不够）：把被文档引用的过程痕迹
**移出 `20*_*/` 命名空间**（例如 `AI_agent/logs/experiments/_tracked/<date>_<name>/`
并在 `.gitignore` 加 `!` 例外），从源头消除每次 `-f` 的人肉纪律。
⇒ 呼应项目既有结论：**「靠记得去做」不是防线，要让错误在机制上表达不出来。**

---

## ✅ 2026-08-09 已收口（且**修法比本节的建议更省**：不搬家，改规则）

**没有采用上面那条「移出命名空间」的建议** —— 查证后发现根因更浅：
`.gitignore:7` 那条 `20*_*/` 写于 2026-05-05（`e9d7a2b`），**当时只为挡协作者一份
LangSmith trace 归档 `20260414_192502/`**，却写成了**不限路径的「目录名形状」规则**。
今天实测：**`20*_*` 形态的目录在工作区一个都不存在了** ⇒ 该规则**挡不到任何它本来要挡的东西**，
只在误伤项目自己的过程痕迹。

⇒ 修法 = **把「按名字形状」改成「按位置」**：`**/backup/**/20*_*/`。
`backup/` 树下的变更前快照（~26 MB / ~1900 文件，git 历史可复现）照旧挡住；
`AI_agent/logs/**` 恢复正常可跟踪。**零迁移、零文档引用更新。**

**顺带查实**：原来那三条 `!` 例外**全部是死的** —— git 无法在已被排除的目录内再包含
（`!backup/Skill_history/` 只解禁目录本身，其 `20*_*/` 子目录照旧被排除，已实测），
且第三条 `case_tests/test_baseline/runs/` 指向的路径**根本不存在**。已删。
⇒ **本项目「声称在守、其实没守」这一族的又一例，这次在 `.gitignore` 里。**

**全档见** [`2026-08-09_f17_envelope_cross_axis_chamfer/README.md`](../2026-08-09_f17_envelope_cross_axis_chamfer/README.md)
同批收口记录（该批主线是 F-17 调查）。

> **本节这几行本身就是验收样本**：它们是用**不带 `-f` 的普通 `git add`** 入库的。
