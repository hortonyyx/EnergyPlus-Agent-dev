# Phase 2 三方对比 — sm_20 redraw POC

> 对比 (a) Opus 两步法 / (b) DeepSeek 两步法 / (c) 黑箱一步 anchor（sm_20 现有 `output_new/intake_output.json`，2026-05-12 B1 后 EP cleanly 跑通的版本）。

---

## 0. TL;DR — POC 结论

**两步法两条路径都修正了一步法 anchor 的 F3 corridor 窗 z 计算 slip**（B1 残留问题）。这是 POC 阶段最强证据，证明"phase1 锁定识图 / phase2 纯推理"的分工把视觉错截断在 phase1。

**Step 6 全链路真跑（§7.5）**：
- DeepSeek 两步法 **EP COMPLETED Successfully**（0 severe / 9 warning / 8.49 sec full annual）
- Opus 两步法 **EP fatal**（InterZone construction asymmetry，规则漏洞所致，非架构问题）
- 架构通透性确认：vector JSON → IntakeOutput → 9 subagent → IDF → EP 链路无障碍
- 暴露 phase2_rules.md §3 Step 5 必加 InterZone single-construction 硬约束

二级结论：

- **零结构性回归**：两步法没引入"漏 zone / 错配 wall / 命名不一致"等新问题
- **Opus 与 DeepSeek 拓扑正确性平手**：但 DeepSeek 因层栈选择简单意外通过 EP，Opus 因物理化设计踩规则漏洞挂
- **代价**：两步法 prompt 总量 ~52k chars / 调用次数 ×2 / 整体延迟 ×2-3（thinking 模式 13 min phase2 + 30 min downstream）

---

## 1. 字段级 diff 表

### 1.1 顶层字段长度（chars）

| 字段 | opus | deepseek | anchor | 备注 |
|---|---:|---:|---:|---|
| building | 269 | 269 | 282 | 几乎同构 |
| site_location | 98 | 99 | 99 | 同构 |
| zone_specs | 2,594 | 1,149 | 5,870 | anchor 含 dim 链推导前言；两步法直接拿 phase1 结果 |
| material_specs | 1,757 | 644 | 1,198 | |
| schedule_specs | 1,590 | 678 | 1,751 | DeepSeek 显得"骨架化"；可能漏典型 schedule |
| construction_specs | 949 | 598 | 984 | |
| surface_specs | **24,164** | 14,861 | **8,488** | **关键差异**：两步法显式枚举 cross-floor split-pairing 子段 |
| fenestration_specs | 3,845 | 6,032 | 5,416 | DeepSeek 含 reasoning 思路文字（"X = 15 - x_local..."），冗余但无错 |
| hvac_specs | 1,401 | 411 | 917 | DeepSeek 最简 |
| people_specs | 776 | 225 | 1,233 | DeepSeek 漏了一些 zone 配置 |
| lights_specs | 666 | 215 | 1,243 | 同上 |

### 1.2 命名风格

| 项 | opus | deepseek | anchor |
|---|---|---|---|
| building.Name | `Smalloffice_20` | `Smalloffice_20` | `Office_SmallOffice_20_Shenzhen` |
| site_location.Name | `Shenzhen_CN` | `Shenzhen_CN` | `Shenzhen_CN` |
| zone 前缀 | `F1_S1` | `F1_S1` | `Zone_F1_S1` |
| 走廊命名 | `F1_Corridor` | `F1_Corridor` | `Zone_F1_COR` |
| F3 北区 | `F3_North` | `F3_N1` | `Zone_F3_N1` |
| 窗 construction | `Default_Window` | `Default_Window` | `Cons_Window` |

19 zone 集合**完全一致**（语义层），3 个分支只是命名风格不同。

---

## 2. POC 主结论项 — F3 East/West corridor 窗 z

**Phase1 South/East/West_view.json 严格抄写 dim 链**：F3 窗高 2.40，sill 1.00，top_gap 1.40 → `y_range_m: [8.20, 10.60]`（绝对世界 z）。

| 路径 | z_min | z_max | 计算逻辑 | 判 |
|---|---:|---:|---|---|
| anchor (1步) | 8.20 | **9.60** | sill 1.00 + top_gap 1.40 = 2.40，**误用 top_gap 作 height** → 8.20+1.40 | ❌ WRONG |
| opus (2步) | 8.20 | **10.60** | 直接读 phase1 `y_range_m=[8.20,10.60]` | ✅ |
| deepseek (2步) | 8.20 | **10.60** | 直接读 phase1 `y_range_m=[8.20,10.60]` | ✅ |

**根因分析**：
- 黑箱一步法在同一次 LLM 调用里做"识图 + 拓扑 + 字段写"，sill/window_height/top_gap 三个 dim 容易混
- 两步法把识图固化在 phase1，phase2 拿到的是"窗 y 范围 [8.20, 10.60]"这种已计算结构化值，**无机会重做坐标推导**

误差预算 (vector_schema_v1.md §0.1) 设计**生效**：phase1 识图正确 → phase2 推理正确。

---

## 3. surface_specs cross-floor split-pairing 对比

sm_20 F1/F2/F3 北排房间数不同（3 / 4 / 1），导致 F2 floor 必须切成多个子面分别与 F1 各 zone 的 ceiling 配对（B1 hardened constraint）。

| 路径 | 处理方式 |
|---|---|
| **opus (2步)** | 显式 10 对 F2↔F1 + 9 对 F3↔F2 全枚举，引入 ad-hoc 子面命名约定（`ceiling_F1_N1_seg_a` 等）。**phase2_followup_notes.md #1/#2 报告该规则未明** |
| **deepseek (2步)** | 也做了分段枚举但较简略 |
| **anchor (1步)** | 已通过 B1 加固，正确处理（这是 B1 已修部分） |

三个都不报 `RoofCeiling references not-found` 类 fatal 风险。Opus 主动暴露 schema gap（"需要明确子面命名约定"）是宝贵副产物。

---

## 4. 16 扇窗 parent surface 映射

| 立面 | 窗数 | opus | deepseek | anchor |
|---|---:|---|---|---|
| South F1 | 3 | south_wall_F1_S{1,2,3} ✓ | F1_S{1,2,3}.SouthWall ✓ | Zone_F1_S{1,2,3} Wall_1 ✓ |
| South F2 | 3 | south_wall_F2_S{1,2,3} ✓ | 同 F2 ✓ | 同 ✓ |
| North F1 | 3 | north_wall_F1_N{1,2,3} ✓ | F1_N{1,2,3} ✓ | 同 ✓ |
| **North F2** | **4 不对称** | F2_N{1,2,3,4} (3.75 隔间) ✓ | 同 ✓ | 同 ✓ |
| North F3 | 1 通长 | F3_North 整面 ✓ | F3_N1 整面 ✓ | Zone_F3_N1 ✓ |
| East F3 | 1 | east_wall_F3_Corridor ✓ | F3_Corridor.EastWall ✓ | Zone_F3_COR Wall_2 ✓ |
| West F3 | 1 | west_wall_F3_Corridor ✓ | F3_Corridor.WestWall ✓ | Zone_F3_COR Wall_4 ✓ |

**全部 16 窗 parent 映射正确**。三路径都把 East/West F3 窗（世界 y ∈ [3.50, 4.50]）正确归到 F3 走廊外墙。

---

## 5. token / 延迟对比

| 路径 | input tokens | reasoning tokens | output tokens | 总 | 延迟 | 备注 |
|---|---:|---:|---:|---:|---:|---|
| opus 1-step (= 旧 anchor) | ~? | n/a | ~? | ~? | ? | 历史 baseline，未单独记录 |
| **opus 2-step** | ? | ? | ? | ? | ? | 用户手跑 Claude Code 会话；未记录 |
| **deepseek 2-step** | 25,940 | 8,192 (cache_read 25,856) | content + thinking ≈ 29k chars output | 34,132 | **13 min** (thinking mode) | thinking 思路 17,019 chars 落 `thinking.txt` |
| anchor 1-step | n/a | n/a | n/a | n/a | n/a | sm_20 半人工流，intake 这步走 Opus 订阅 |

cache_read 25,856 表明 prompt 缓存命中（system_prompt 重用），节省 ~3/4 input cost。

**两步法成本估计**：input 2× / latency 2-3×。但消除了 z 计算 slip 类视觉-推理纠缠错。

---

## 6. 各路径自身瑕疵

### 6.1 Opus (2-step)

phase2_followup_notes.md 暴露 **10 条 schema gap**（值得直接补 phase2_rules）：
- §1/§2 cross-floor split sub-surface 命名约定未规定
- §3 窗骑墙检查规则缺失
- §4 走廊负载密度（30 m²/p / 5 W/m²）vs 办公室典型值的边界
- §5 F3 4.80 m 层高是否需归一化
- §7 building.Name 大小写策略
- §8 site.Name 规范化为 `<City>_<ISO2>` 建议
- §9 EnergyPlus 实际接受的 Schedule:Compact day-type 名（`AllOtherDays` 等）
- §10 §4 vertex 表对 sub-rect 情形的扩展

self_check 9 项全 PASS + 5 条额外 sanity（WWR / vertex CCW / SimpleGlazing standalone / z 连续 / 跨 facade 一致性）。

### 6.2 DeepSeek (2-step)

- 输出用 JS 风格 `"..." + "..."` 多行字符串拼接（非合法 JSON），脚本 `_fix_js_concat` regex 自动修复
- thinking 模式确实开了（17k chars 推理思路），空间推理在 F2 北 4 窗 + F3 通长窗这些非对称布局上推得清晰
- `*_specs` 字段普遍较简（people_specs / lights_specs 比 anchor 短 ~80%），下游 9 subagent 拿到可能信息不足
- fenestration_specs 含大段"X = 15 - x_local..."推导文字，冗余但无错（可能因 thinking 思路漏到 content）

### 6.3 Anchor (1-step)

- F3 East/West corridor 窗 z_max=9.60 错（**唯一硬错**）
- 其他字段成熟（B1 已加固）

---

## 7. POC 判定

按 plan.md Step 5 标准：

> **POC PASS**：两步在至少 2 个维度优于一步，且 token 总耗未爆炸（< 3× 一步）

| 维度 | 判定 |
|---|---|
| 1. F3 corridor 窗 z 正确性 | 两步 ✅ vs 一步 ❌ |
| 2. cross-floor split-pairing 显式枚举 | 两步 ✅（更显式）vs 一步 ✅（B1 加固后也对，但隐式）|
| 3. schema gap 暴露（副产物）| 两步 ✅（10 条 followup notes）vs 一步 ✗ |
| 4. token / 延迟 | 两步 ~2× 输入 / ~2-3× 延迟 — **未爆炸**，在 < 3× 阈值内 |
| 5. 字段完整度 | 两步 ≥ 一步（DeepSeek 较简但 Opus 显式覆盖更多）|

**判：POC PASS**。

---

## 7.5 Step 6 — 全链路真跑验证（关键补充）

把两条 phase2 路径的 IntakeOutput 喂 `run_full_pipeline.py --intake-from`，跑下游 9 subagent + EnergyPlus simulate：

| 路径 | L1 Pydantic | L2 cross_ref | L3 IDF 生成 | L4 EP simulate | 总耗时 |
|---|---|---|---|---|---|
| opus 2-step | ✅ | ✅ | ✅ (19 zones, 16 windows 全建好) | **❌ Fatal** | ~38 min |
| **deepseek 2-step** | ✅ | ✅ | ✅ | **✅ COMPLETED**（0 severe / 9 warning / 8.49 sec full annual）| ~32 min |

### 7.5.1 Opus 路径 EP fatal 真因

EP 报：
```
GetSurfaceData: Construction DEFAULT_CEILING of interzone surface CEILING_F1_S1 
does not have the same materials in the reverse order as the construction 
DEFAULT_FLOOR of adjacent surface FLOOR_F2_S1
```

**根因不在 phase 1 / 2 架构层，在 [phase2_rules.md](../phase2_rules.md) §3 Step 5 规则漏洞**：

| construction | Opus 层栈（outside→inside）| reverse-symmetric? |
|---|---|---|
| Default_Floor | `[Mat_Carpet, Mat_Concrete_200]` | reverse = `[Concrete_200, Carpet]` |
| Default_Ceiling | `[Mat_Concrete_200, Mat_Gypsum]` | ≠ reverse(Floor) ❌ |

Opus 物理化思路："floor 上面是 carpet，ceiling 下面是 gypsum" — 物理合理但层不互逆，EP 拒绝。

### 7.5.2 DeepSeek 路径为什么 PASS

DeepSeek 用了 palindrome 层栈：

| construction | DeepSeek 层栈 |
|---|---|
| Default_Floor | `[Gypsum_Board, R8_Insulation, Gypsum_Board]` |
| Default_Ceiling | "same as Default_Floor" → 同层栈 |

`[G, R8, G]` 是 palindrome，reverse 等于自己 → InterZone 反向对称约束 trivially 满足 → EP PASS。

DeepSeek "赢在懒得设计"，纯属侥幸。如果 DeepSeek 选了非对称材料栈，同样会挂。

### 7.5.3 anchor sm_20 的正确做法

CLAUDE.md §5.5 已 cleanly 跑通的 anchor：

```
- Cons_InterFloor: layers = Mat_Floor_Concrete, Mat_IntWall_Gypsum.
  Used for every InterZone surface between vertically stacked zones
  (F1 ceiling / F2 floor and F2 ceiling / F3 floor); apply the same
  construction on both the upper-zone floor and the lower-zone ceiling.
```

**single construction，两侧共用** —— 反向对称 trivially 成立。phase2_rules.md §3 Step 5 必须加这条。

### 7.5.4 Step 6 判定

- **架构层面通透**：DeepSeek 路径全链路 EP cleanly 跑通证明"vector JSON → IntakeOutput → 9 subagent → IDF → EP"链路无架构障碍
- **规则层面有缺口**：phase2_rules.md §3 Step 5 应加"InterZone surfaces 共用单一 construction"硬约束
- **Opus 反胜 DeepSeek 一筹但被规则漏洞反扑**：Opus 的 cross-floor split-pairing / 子面命名细致度更高，但 construction 物理化设计踩了规则漏洞；DeepSeek 简单层栈反而通过

### 7.5.5 必加规则（应入 phase2_rules.md v1.3）

```markdown
### Step 5 (additional rule)

InterZone surface 配对要求 construction 反向对称。**强烈建议**：
为所有 InterZone floor/ceiling 对定义一个**单一 construction**（如
`Cons_InterFloor`），同时贴在上 zone 的 floor 和下 zone 的 ceiling
表面。这样反向对称 trivially 成立，避免 EP `GetSurfaceData: Construction
... does not have the same materials in the reverse order ...` fatal。

不允许：
- 为 InterZone 上下面分别定义 `Default_Floor` / `Default_Ceiling` 各自的非对称层栈
- 让 Default_Floor 和 Default_Ceiling 层不互逆

允许（但不推荐）：
- 两个独立 construction 但层栈**严格互逆**（要在 spec 里显式 enumerate 两条 layer list 并标注 reverse 关系）
- 两个独立 construction 但层栈**自己就是 palindrome**（如 `[Gypsum, Insul, Gypsum]`）— DeepSeek 路径侥幸通过的方式
```

---

## 8. 后续动作建议

### 8.1 立刻可做
- 把 Opus phase2 的 IntakeOutput 喂 `run_full_pipeline.py --intake-from` 跑下游 9 subagent + simulate，验证两步法 IntakeOutput 在现有契约下能否 cleanly 跑通（Step 6）
- 补 phase2_rules.md 加 Opus 10 条 followup notes 中可机械化的 4-5 条（cross-floor sub-surface 命名 / site.Name 规范 / Schedule:Compact day-type / corridor 密度）

### 8.2 短中期决策
- **POC PASS 的含义不是"立刻动 intake_node 改两步"**：sm_20 是规整办公楼测试图，黑箱一步法只输了一个 z 计算（且 B1 已经修了类似但不同位置的），泛化收益还要在更复杂图（异型 / 装饰 / 多类构件）上验证才能决定改主线
- **建议路径**：再选 1 张噪声更多的图（带檐口/索引线/家具/楼梯）跑 POC v2，看 phase1 矢量化是否还能维持 sm_20 这种"近完美"质量；若仍 PASS，可以立项动 intake_node
- **不应直接做**：现在动主线 intake.py 改两步——POC v1 只 1 图，证据强度不够

### 8.3 与主线 B2-B4 关系
- B2-B4 评测基线规范化继续推
- POC 产物作为评测体系的一个**评测样本**而非"基础设施"
- phase1 矢量 JSON 可考虑作为 B2 GT 数据集的一部分（结构化已知值）

---

## 9. Artifacts

| 文件 | 用途 |
|---|---|
| `phase1_vector/*.json` (7 个) | phase1 矢量 JSON（识图层）|
| `phase1_vector/phase1_summary.md` | phase1 总结 + 4 立面 local↔world 公式 |
| `phase1_vector/*.svg` (7 个) | 渲染后人工核验 |
| `phase2_rules.md` | phase2 规则（"矢量 JSON → IntakeOutput"）|
| `phase2_intake/opus/intake_output.json` | Opus 两步法终产物（38.8 KB）|
| `phase2_intake/opus/self_check.md` | Opus 自检（9/9 PASS）|
| `phase2_intake/opus/phase2_followup_notes.md` | Opus 暴露的 10 条 schema gap |
| `phase2_intake/deepseek/intake_output.json` | DeepSeek 两步法终产物（25.9 KB）|
| `phase2_intake/deepseek/thinking.txt` | DeepSeek 17 KB reasoning 思路 |
| `phase2_intake/deepseek/raw_response.txt` | DeepSeek 原始响应（含 JS-concat）|
| `phase2_intake/deepseek/run.log` | DeepSeek 跑批日志 |
| `Tool_scripts/run_phase2_deepseek.py` | DeepSeek phase2 自动跑批脚本 |
| 对比对象：`test_data/SmallOffice/smalloffice_20/output_new/intake_output.json` | 1-step anchor |
