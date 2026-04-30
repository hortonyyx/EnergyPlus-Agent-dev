# Token 优化方案

> **目的**：把单 case token 消耗压到 Opus 单会话稳定可完成、且为开源模型上下文窗口（16k–64k 实际可用）留余量。
> **背景**：[CLAUDE.md §7.7 / §7.8](CLAUDE.md)。

---

## 0. 架构变化（2026-04-28；2026-04-29 二次修正）

Claude Code harness 已切换到 **deferred MCP 架构**：

- **Session 启动只预载 9 个核心工具**（Agent / Bash / Edit / Glob / Grep / Read / Skill / ToolSearch / Write）
- 其余 100+ 工具（含全部 79 个 EnergyPlus MCP + 系统工具如 TodoWrite / WebFetch + claude.ai 账户级 connector）**按需通过 `ToolSearch` 取 schema**，不预占 context

### 0.1 `/context` 各分类是否计入 `Tokens used`（2026-04-29 实测修正）

比对 `2026-04-27_sm_15_post_p0/context.txt` 与 `2026-04-29_sm_16_multifloor_v1/context.txt` 后确认：

| 计入 Total（真实预算） | 不计入 Total（display-only / 预留区） |
|---|---|
| System prompt | MCP tools (deferred)（旧 36k） |
| System tools | System tools (deferred)（旧 19k） |
| MCP tools (loaded) | Autocompact buffer（33k） |
| Memory files / Skills | Free space（~800k） |
| Messages | |

**真实计入 Total 的 harness 仅 ~24k**（不是先前认为的 55k 或 100k）。验证：sm_15 / sm_16 两次 `8.9 + 11.8 + 2.4 + 0.1 + 0.6 + Messages ≈ 显示的 Total`。

**直接影响**：
| 旧判断 | 新架构 + 修正口径下状态 |
|---|---|
| 早期 §2.4 "harness ~100k 是真实下限" | 全错；真实 ~24k |
| 2026-04-28 修订的"新 harness ~55k" | 仍偏高；把 autocompact 算进去了 |
| §2.5.A `deniedMcpServers` 禁 claude_ai_* | **No-op**（deferred 工具不计 context） |
| §2.5.D MCP 工具 description 压缩 | **No-op**（schema 按需加载） |
| sm_15 pre_p0 221.3k 基线 | **不可与新数据直接比**；新 anchor 选 `2026-04-29_sm_16_multifloor_v1`（164.3k） |
| "关掉无关 MCP server 省 ~20-36k" | **作废**（deferred 行本就不计 Total） |

→ 后续优化只剩一条路：**减 messages**（messages 段在 sm_15/16 两案例都稳定占 ~140k，是 86%+ 的真实预算）。harness 已无可榨空间。

---

## 1. 占用问题清单（messages 段）

按量级降序排列，单 case 几何阶段（sm_15 = 14 zones / 84 surfaces / 12 windows）的实测/估算：

| # | 问题 | 量级 | 根因 |
|---|---|---|---|
| **P1** | 单次 `update_surface` 返回完整 Surface dump（含 4 顶点 JSON），84 次累积 | ~63k | MCP CRUD 工具默认全量回吐 |
| **P2** | 84 次 `update_surface` 逐次调用，每次都吃 history 累积 | ~25k | MCP 无 batch 接口 |
| **P3** | LLM 在 IDF 导出步骤手写 80+ 行 inline Python（含 4 条修复补丁） | ~3-5k | export_idf 流程未脚本化 |
| **P4** | `validate_config` 几何阶段返回 96 条占位 Construction 引用错误（每条 ~40 chars） | ~3k | 错误列表无截断、无聚类 |
| **P5** | Blank facade 仍然附图视觉理解（sm_15 East/West 各 ~1.4-2.5k 视觉 token） | ~3-5k | skill 未区分 with_windows / blank |
| **P6** | 顶点 JSON 长形式 `{"x":0,"y":0,"z":0}`（每 zone 4 点 ×~25 token） | ~2-3k | Pydantic 仅接受 dict |
| **P7** | `claude_ep.md` ASCII 平面图（~30 行 × 80 char） | ~2k | skill 强制要求 |
| **P8** | 默认 6 surface 全部 `Outdoors`，84 次中绝大多数为修正 boundary（地/顶/内墙） | ~15k 间接 | `create_zone` 不做邻接推断 |
| **P9** | 中途掉线后 history 重灌 | ~+30k 偶发 | 长链路稳定性 |

> **不再讨论**：MCP 工具 description 累积（旧 ~16k）、claude_ai_* connector（旧 ~20k）—— 已被 deferred 架构淘汰。

---

## 2. 解决方案对应关系

| 问题 | 方案 | 状态 |
|---|---|---|
| P1 工具返回值膨胀 | MCP CRUD 默认 ack-only（list_all 返名字数组、create/update 返 `{"name"}`、read/get 保留全量 dump） | ✅ 已做（§3.1） |
| P2 逐次调用 | 加 `update_surfaces_batch` + `create_fenestration_surfaces_batch` | ✅ 已做（§3.2） |
| P3 inline Python | `Tool_scripts/export_idf.py` 外置 + 5 条补丁固化 | ✅ 已做（§3.3） |
| P4 validate 错误列表 | 错误截断 + 按类型聚类 + 可选 verbose | 📋 计划做（§4.1） |
| P5 blank facade 视觉浪费 | testdata_prompt.json 加 `facade_status`，skill Step 1 跳图 | 📋 计划做（§4.2） |
| P6 顶点 JSON 长形式 | Pydantic union type 接受 `[x,y,z]` | 📋 计划做（§4.3） |
| P7 ASCII 平面图 | skill 改为可选 / 移到 `_floor_plan_ascii.txt` 子文件 | 📋 计划做（§4.4） |
| P8 boundary 默认 Outdoors | `create_zone` 自动 boundary 推断（按楼层 + 邻接关系） | 📋 计划做 P1（§4.5） |
| P9 长链路掉线 | P1+P2+P8 合计后单 case ≤ 50k，自然缓解 | 间接 |

---

## 3. 已做（带实测）

### 3.1 ✅ MCP CRUD 默认 ack-only（2026-04-27）

**改造**：[src/mcp/tools/base.py](../src/mcp/tools/base.py) 模板 3 处 + [src/mcp/api/core.py](../src/mcp/api/core.py) `create_zone` 特例 1 处，共 ~10 行。

| 操作 | 改前 | 改后 |
|---|---|---|
| `create_*` | 完整 instance dump（~1.5-3 KB） | `{"name": <name>}`（~30 字节） |
| `update_*` | 同上 | 同上 |
| `list_*` | `[完整 dump, ...]` | `[<name>, ...]` |
| `read_*` / `get_*` | 完整 dump | **保留**（LLM 主动 get 即等价 verbose） |
| `delete_*` | 不变 | 不变 |
| `create_zone` 特例 | 完整 + 6 surface | `{"name": ..., "surfaces_created": [6 名字]}` |
| `workflow.*` | 不变（export/load/validate/run/summary 的 data 都是必要载荷） |

**实测**：单次 update_surface 响应 ~3000 字节 → ~30 字节，84 次累计 -~250 KB context ≈ **-60k token / case**（超原估 50k）。

**备份**：`MCP_history/2026-04-27_mcp_pre_ack_only/`

---

### 3.2 ✅ MCP batch 接口（2026-04-27）

**最终范围**：仅 2 个 batch（**不做** `create_zones_batch`）。理由：几何复杂度集中在单个 `create_zone`（自动生成 N 个 surface，N 可变 + 失败回滚），批量化收益不抵 partial-success 状态机复杂度；热区合并后 zone 数封顶 10-30，单调用足够。

| 工具 | 落地 |
|---|---|
| `update_surfaces_batch` | ✅（最热，sm_15 = 84 次） |
| `create_fenestration_surfaces_batch` | ✅（与 surface batch 共享代码模式） |
| ~~`create_zones_batch`~~ | 不做 |

**实现**：[src/mcp/api/envelope.py](../src/mcp/api/envelope.py) 末尾追加 ~120 行 inline 循环（base.py 不动），返回 partial-success 语义：
```json
{"success": true, "message": "Batch update_surface: 84 succeeded, 0 failed.",
 "data": {"count": 84, "succeeded": [...], "failed": [{"name": "X", "error": "..."}]}}
```

**3 类失败模式回归通过**：不存在的目标 / 缺 `name` / 字段值非法 → 各项独立失败，其余继续。

**Skill 同步**（关键纪律）：[energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) Step 3/4 + [open_model 版](../skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md) Step 7/8 改为强约束 "USE THE BATCH TOOL — one call only"，open_model §0 hard constraint #4 显式说明 "一次 batch 调用 = 一次 tool call"。MCP 工具总数 77 → 79。

**预计节省**（线性 ROI）：

| 案例规模 | surface 数 | batch 节省 |
|---|---|---|
| sm_15 当前 | 84 | -25k |
| 中型办公（预估） | ~150 | -65k |
| 多层不规则（预估） | ~280 | -155k |

**备份**：`MCP_history/2026-04-27_mcp_pre_batch/` + `Skill_history/2026-04-27_energyplus_mcp_pre_batch/`

---

### 3.3 ✅ `Tool_scripts/export_idf.py` 外置（2026-04-27）

**改造**：根目录新建 [Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py)，CLI `python Tool_scripts/export_idf.py <case_dir>`，含 **5 条补丁**（比原计划多 1 条）：

| 补丁 | 说明 |
|---|---|
| **0（新增）** | `convert_all` 之前预置 1 个 NoMass Material + 3 个占位 Construction（`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`）。**不加这条 fenestration 会被 FenestrationConverter 静默丢失** |
| 1 | RunPeriod None 字段补默认 |
| 2 | warmup days 默认值 |
| 3 | InterZone Surface → Adiabatic + Int_Wall（几何阶段 no-op，幂等） |
| 4 | Schedule:Compact None 字段（几何阶段 no-op） |

**Skill 同步**：[export_idf.md](../skills/energyplus_mcp/export_idf.md) 重写为薄文档，主 skill Step 5c + open_model Step 10 改为单行 Bash。

**实测**（sm_15 冒烟）：fenestration **0 → 12**（补丁 0 收益），LLM 不再产出 inline Python。

**节省**：3-5k / case + 修复 fenestration 静默丢失（隐性收益）；**风险 0**。

---

## 4. 计划做（**整体冻结至 idfpy + MCP 重写之后**）

> ⚠️ **2026-04-29 排期决定**：§4.1-§4.5 主体降 token 工作 **冻结**，等 [idfpy_embed.md](idfpy_embed.md) P2（协作者主导的 MCP 全线重写）落地后再重评估并实施。
>
> **理由**：
> 1. P2 会大量重写 / 删除现有 MCP 工具签名（CRUD 体系会被 idfpy `idf.validate()` + `to_dict()` 取代），现在做的 §4.1（validate 截断）、§4.3（顶点短形式）等改动**大概率被推翻或迁移成本翻倍**。
> 2. sm_16 实测（[CLAUDE.md §7.11](CLAUDE.md)）已证明在 `update_surfaces_batch` 加持下，复杂度 +36% 仅吃掉 +0.5% token；说明 §3 三档 P0 已经把 messages 段压到接近 batch 化的天花板。
> 3. 距离开源模型可承受区间还差一道**会话切分**工程（phase A 出 `claude_ep.md` → 关会话 → phase B 调 MCP，每段 ≤50k），这道工程也应在 idfpy 切完后再设计 — 否则 phase B 跑的是即将作废的 MCP。
> 4. messages 段 140k 占 86% 才是真正大头，但其中 ~80k 是图像视觉 + skill 文档（不在本节范围），单纯压 §4.1-§4.5 至多再省 10-15k，对开源模型迁移仍不够。
>
> **以下 §4.1-§4.6 保留作为 idfpy 切换后的候选清单，按 ROI 排序，不再视为短期路线**。

### 4.0 冻结期内只做的事

- 维护当前 §3 三档 P0（不回退）
- 任何 token 测量必须按 §0.1 的真实口径，不再混用 deferred / autocompact
- baseline anchor 升级为 `2026-04-29_sm_16_multifloor_v1`（164.3k，3 层 + 19 zones，比 sm_15 anchor 更能反映规模上限）

---

### 4.1 📋 `validate_config` 错误截断（P0 之后首选）

**目标**：解决 P4。

**改造**（[src/mcp/api/workflow.py](../src/mcp/api/workflow.py) `validate_config`）：
- 原：返回完整 `errors: [...]`
- 新：`errors_count: 96, errors_first_n: [前 5 条], errors_by_type: {"placeholder_construction": 96}, errors_truncated: true`
- 可选 `verbose=true` 取全量

**节省**：-3k / case
**工作量**：30 分钟（~20 行）
**风险**：0

---

### 4.2 📋 Blank facade 跳图

**目标**：解决 P5。

**改造**：
1. `testdata_prompt.json` 加字段：`facade_status: {south: "with_windows", north: "with_windows", east: "blank", west: "blank"}`
2. skill Step 1 加规则：`facade_status=blank` 的方向**不附图**，直接登记 0 个 fenestration
3. 同步 [new_case_guide.md](new_case_guide.md) 案例规范

**节省**：-3-5k / case（Opus 视觉 token；Continue/开源场景每 attachment 14k 上限被释放，节省更大）
**工作量**：1 小时（skill + JSON schema 文档）
**风险**：低

---

### 4.3 📋 顶点 JSON 短形式

**目标**：解决 P6。

**改造**：Pydantic 顶点字段加 union type
```python
Vertex = Annotated[
    Union[Dict[str, float], Tuple[float, float, float]],
    BeforeValidator(...)  # 自动归一为 dict
]
```
LLM 可写 `[[0,0,0],[5,0,0],[5,8,0],[0,8,0]]`（每点 ~8 token vs ~25 token）。

**节省**：-2-3k / case
**工作量**：1 天（Pydantic + validator + skill 强约束改写）
**风险**：中（LLM 不一致使用、batch 错误信息可读性下降）

---

### 4.4 📋 `claude_ep.md` ASCII 平面图瘦身

**目标**：解决 P7。

**两个选项**：
- **轻**：skill Step 2 标注 "ASCII floor plan 可选" → LLM 倾向跳过
- **折中**：让 LLM 写到 `output/_floor_plan_ascii.txt` 单独文件，不进 claude_ep.md 主文（LLM 不会回头读子文件）

**节省**：-2k / case
**工作量**：30 分钟
**风险**：中（人工 review 体验下降，折中方案可缓解）

---

### 4.5 📋 P1 改动：`create_zone` 自动 boundary 推断

**目标**：解决 P8（最大杠杆，但风险最高，单列 P1）。

**当前**：`create_zone` 默认 6 surface 全 `Outdoors + Default_Construction` → 84 次 update_surface 中绝大部分是修正 boundary。

**改造逻辑**：
- F1 zone 最低面 → `Ground + Default_Ext_Wall`
- 顶层 zone 最高面 → `Outdoors + SunExposed + Default_Ext_Wall`（屋面）
- 与已存在 zone 共面的 wall → `Adiabatic + Default_Int_Wall`
- 其余 wall → `Outdoors + SunExposed + Default_Ext_Wall`

**预计**：14-zone 案例下，update_surface 从 84 次砍到 ~10-20 次（只剩边角内墙修正） → 配合 §3.1+§3.2 再省 ~15k。

**工作量**：~100-150 行（邻接判断 + 几何 coplanar 检测）+ skill Step 3 表格重写为"只覆盖偏离自动推断的 case"
**风险**：中-高
- 浮点等于、CCW 顶点排序、coplanar 检测易引入 bug
- 必须单元测试覆盖：单层 / 多层 / 退台 / 挑空

**为什么 P1**：风险高且 §3.1+§3.2 完成后单 case 已可控，本阶段非必需；为本地开源模型部署准备。

---

### 4.6 ✅ 新 harness 下 anchor 已建立（2026-04-29）

**背景**：旧 anchor sm_15 pre_p0 = 221.3k 是基于已废弃 harness（§0），不可与新数据比较。

**已完成**：
- `2026-04-27_sm_15_post_p0` (163.4k) — 单层 14/84/12 案例
- `2026-04-29_sm_16_multifloor_v1` (164.3k) — 3 层 19/114/16 案例 ← **当前主 anchor**

两次 anchor 在不同复杂度上 total 仅差 0.9k（+0.5%），证明 §3 三档已逼近 batch 化天花板。

---

## 5. 综合预估（按 §0.1 真实口径，messages 段）

> ⚠️ 下表所有 §4.x 节省都是 **idfpy 切换后** 的预估；P2 期间 MCP 重写完成前不实施。

| 状态 | 单 case messages 段 | 备注 |
|---|---|---|
| 旧 harness anchor（pre_p0，已废） | ~199k messages | 不可比 |
| 新 harness anchor sm_15 post_p0 | **141.1k messages**（实测） | §3 三档落地 + 单层 |
| 新 harness anchor sm_16 multifloor_v1 | **140.2k messages**（实测） | §3 三档落地 + 3 层 |
| idfpy 切换后 + §4.1 | -3k | 错误列表截断 |
| idfpy 切换后 + §4.1 + §4.2 | -6-8k | + blank facade |
| idfpy 切换后 + §4.1-4.4 | -10-13k | + 顶点短形式 + ASCII 瘦身 |
| idfpy 切换后 + §4.1-4.5 | -25-28k | + 自动 boundary 推断 |
| 上述 + 会话切分 phase A/B | 各段 ≤50k | 开源模型可承受区间 |

**目标**：开源模型可上路的不是把单段压到 50k 以下（idfpy + §4.1-§4.5 仍达不到），**而是把流程切成 phase A/B 两段会话**，两段独立各 ~50k。这道切分必须在 idfpy 落地后设计，因为切分点（"几何描述完毕 → 调 MCP"）依赖 idfpy 的中间格式 (epJSON)。

---

## 6. 实施顺序建议（2026-04-29 重排）

### 6.1 短期（idfpy 切换前 — 即现在到 P2 完成）

1. **冻结 §4.1-§4.5**（理由见 §4 顶部框）
2. **维护 §3 三档**：发现 batch 工具回归立即修
3. **任何新 case 走 §0.1 真实口径**：`tokens.total` 必须从 `/context` 直读，不接受估算
4. **观察期数据收集**：每个新案例（sm_17+）都跑 `baseline_record.py`，积累 messages 段 vs 规模的散点；为 idfpy 切换后 §4.x 的真实 ROI 提供对照基线

### 6.2 中期（idfpy P2 落地后启动）

1. **§4.6 重新跑 anchor**（在新 idfpy MCP 上跑 sm_15 + sm_16，对照旧 anchor）
2. **§4.1 validate 截断** — idfpy `idf.validate()` 接口不同，需重写但工作量仍小
3. **§4.2 blank facade 跳图** — 与 idfpy 解耦，可平行做
4. **Sonnet 4.6 降级测试** — 验证 §3 + §4.1 + §4.2 在 Sonnet 上能否稳定
5. **§4.3 / §4.4** 视 Sonnet 表现决定
6. **§4.5 自动 boundary 推断** — idfpy 已有 `surface.area` / `normal` / `centroid` mixin，自动推断改造路径**比旧 ConverterManager 路径短得多**；这是 idfpy 切换后最值得做的一项

### 6.3 长期（开源模型迁移启动前必做）

1. **会话切分工程**：phase A（vision + claude_ep.md + 标注图） → 关会话 → phase B（只读 ep.md 调 idfpy MCP 建模）
   - 每段 messages ≤50k，进入 Qwen3-30B-A3B 等小激活 MoE 的舒适区
   - 切分点的中间格式 = idfpy `to_dict()` epJSON，不需要 Skill 文档跨段重复
2. **Qwen3-235B-A22B / DeepSeek-V3 端到端基线**：22B+ 激活的模型可不切分；与切分方案对照 ROI

---

## 7. 验收标准

**§3 已通过**：
- §3.1：sm_15 加载 → list_zones=14 名字 / list_surfaces=84 名字 / update_surface 返 `{"name": ...}` ✓
- §3.2：MCP 工具总数 77 → 79，3 类失败模式独立隔离 ✓
- §3.3：sm_15 IDF 含 14 zones / 84 surfaces / 12 fenestration / 3 Construction / 1 Material ✓

**§4 整体目标**：
- sm_15 在新 harness 下单会话完成，total ≤ 130k（含 ~55k harness）
- IDF 产物对象计数与现有 anchor 一致
- OpenStudio 3D 视图几何完全一致

---

## 8. 与其他工作流的衔接

- **MEP 阶段 skill**：MEP 落地时 Materials / Schedules / People / Lights / HVAC 同样吃批量重复，本轮 §3.2 batch 接口可直接复用。
- **`AI_agent/eval/run_case.py`**（[plan.md](plan.md) P0）：评测脚本会跑 sm_0..sm_15 全集，单 case 优化让 Opus baseline 跑得起。
- **Sonnet / 本地开源迁移**：token 优化是这两条路能跑通的前提（开源模型上下文 16-64k + 长 tool-chain 稳定性差）。

---

_最后更新：2026-04-29（下半）— ①§0 二次修正（`/context` 各分类计入 Total 归类表，真实 harness ~24k 而非 ~55k，"关无关 MCP server"判断作废）；②§4 顶部加冻结框，§4.1-§4.5 主体降 token 工作整体推迟到 idfpy P2 完成后；③§4.0 新增冻结期内只做的事；④§4.6 标记完成（sm_15 / sm_16 双 anchor）；⑤§5 综合预估表加 idfpy 切换后限定语；⑥§6 实施顺序拆短期 / 中期 / 长期三段，长期含会话切分工程_

_2026-04-28 — 全文重写：①§0 记录 deferred MCP harness 架构变化（旧 §2.4 / §2.5.A / §2.5.D 全部失效）；②§1 占用问题清单 P1-P9 按量级排；③§2 问题↔方案↔状态对应表；④§3 已做（§3.1 ack-only / §3.2 batch / §3.3 export_idf 外置）含实测；⑤§4 计划做（§4.1 validate 截断 / §4.2 blank facade / §4.3 顶点短形式 / §4.4 ASCII 瘦身 / §4.5 自动 boundary / §4.6 重建 anchor）按 ROI 排；⑥§5 综合预估改用 messages 段（不再混淆 harness）；⑦§6 实施顺序 §7 验收标准 §8 衔接_

_历史变更：2026-04-27 §3.1 / §3.2 / §3.3 三档 P0 落地；2026-04-26 首版_
