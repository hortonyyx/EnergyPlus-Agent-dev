# 交接 · 管线重构为 0–5 阶段架构（活任务，跨会话）

> **状态（2026-06-09 v2）**：Step 1–7 完成并提交（Step 1 `29845ea`；Step 2 `6117f58`；Step 3 `945c54c`；Step 4 `600f7d0`；Step 5 `a978009`；Step 6 `763ee97`；Step 7 docs）。**Step 8（sm21_pre e2e 复测）待做** —— 唯一剩余项，需 DeepSeek API + 下游全跑。fork (a)（序列化→下游誊写）已选定实现；fork (b) 记录待后续整合再议。
> **首读**：本文 + [pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md)（架构 spec，**已更新到新实态**）+ [split_pairing_kernel_reference.md §7](../reference/split_pairing_kernel_reference.md)（切配落地状态）+ [rules_md_split_map.md](../architecture/rules_md_split_map.md)（rules.md 拆解 + 口径）。

---

## 1. 目标 + 锁定命名

把两步法管线重构成**有序 6 阶段**（用户 2026-06-09 定）。核心原则：**LLM 只做 感知 + 校正判断 + 物理语义；代码做 所有几何（建模+切配）+ 装配。**

```
0_Reading       识图        LLM/VLM        → 矢量 JSON
1_Correction    校正        LLM判断+确定性核 → CorrectedGeometry(cells)
2_Modelling     建模·几何   确定性(zonification 插这) → 几何建筑模型
3_Split-pairing 切配·仿真   确定性          → EP合法仿真几何
4_MEP           物理挂载    LLM/模板        → 材料/时间表/HVAC
5_Intakeoutput  产契约      确定性装配      → IntakeOutput（我方边界；下游 9 subagent 消费、不归我管）
```

⚠️ **硬约束**：Python 模块名不能数字开头。编号命名只用于 **skill 目录 / 输出目录 / 文档章节 / 概念**；**代码模块**用 `reading/correction/modelling/split_pairing/mep/intakeoutput`（无数字前缀）。

---

## 2. 已完成（都在 commit `29845ea`，main，未 push）

- **Step 1 命名脚手架**（DeepSeek 审 APPROVE）：skill 目录 `phase1→0_reading` / `phase2/PartA-correction→1_correction` / `phase2/priors/mep.md→4_mep/mep.md`；`phase2.py` 路径全更新；**行为不变、36 测过**。`phase2/rules.md` **暂留原位**（Step 2 拆）。
- 优先级 #2 三项（partA 待完善）：
  - **#2.1** 确定性核容差外置 [`src/configs/correction.yaml`](../../src/configs/correction.yaml) + [`correction/config.py`](../../src/agent/correction/config.py)；聚类后吸 `SNAP_GRID`(50mm)、窗户分级(10mm+钳父墙)，消簇均值 mm 级值。
  - **#2.4** 连接性补缝 [`deterministic.py`](../../src/agent/correction/deterministic.py) `_close_to_boundary`：内墙落 footprint 内侧 ≤300mm 自动封口（A0 老值 100→300）。
  - **#2.2** MEP 去混合：rules.md Step7 默认值→ [`4_mep/mep.md`](../../skills/energyplus_mcp_twostep/4_mep/mep.md)（DRAFT 种子），phase2b 加载。
- **审阅工具** [`Tool_scripts/deepseek_review.py`](../../Tool_scripts/deepseek_review.py)：容器内 DeepSeek 审阅 CLI（deepseek MCP 在容器不可达，用此代替；已验证可用）。
- sm21_pre 完整跑（组织化布局 `phase2/{partA,partB}`+`EP_run`）+ [`render_corrected_geometry.py`](../../Tool_scripts/render_corrected_geometry.py)（phase2a 产物可视化）。

---

## 3. ★确定性几何内核（已建成 + 门验证，**尚未接主链**）

[`src/agent/geometry/`](../../src/agent/geometry)（`build.py` shapely **多边形原生** 造面+切配，`to_idf.py` 产 eppy 面跑真门）：
- `build_geometry(CorrectedGeometry) -> BuildingGeometry`（zones + 面 + 窗 + 切配；含重叠守卫）。
- **6 个单测对标 InterZone 门全 0 issue**（[`tests/test_geometry_kernel.py`](../../tests/test_geometry_kernel.py)）：单层多房、两层对齐、**两层错配切分**、**退台**、**L 形多边形**、重叠标记。
- 这就是 **2_Modelling + 3_Split-pairing** 的实现（现揉在一个 build.py，Step 3 拆两模块）。

---

## 4. 剩余步骤（DeepSeek 对计划的 5 findings 已折入）

每步：**备份 → 实现 → `deepseek_review.py` 审 → commit**；严重问题停下问用户；历史测试不改。

| # | 步骤 | 风险 | 备注 |
|---|---|---|---|
| 2 | 拆 `phase2/rules.md`：几何规则→2/3 内核(多变代码) / 物理规则→`4_mep/` | 中 | **验证内核覆盖原 LLM 几何 edge case**（对标 sm20 的干净 IDF / 已知好几何）|
| 3 | 内核拆 `modelling` + `split_pairing` 两模块（split-pairing leg-agnostic 可复用）| 中 | |
| 4 | **接线**：`1_correction→2_modelling→3_split_pairing→产几何 specs`，喂进管线 | 中 | DeepSeek Med：缺显式接线步，补 |
| 5 | **解耦 phase2b → 4_MEP(LLM物理) + 5_Intakeoutput(确定性装配)** | **高·停下问用户** | DeepSeek High：**5 必须产出与下游消费 schema 一致的 IntakeOutput**→加契约校验。**集成岔口**：几何怎么进 `surface_specs`(str)——(a) 序列化成显式 surface_specs 让下游誊写 vs (b) 确定性直接造面绕过 surface_agent。**这俩要和用户定。** building/site 来源=testdata/LLM（非几何）|
| 6 | 输出目录重构 `0_reading/.../5_intakeoutput/` + `run_full_pipeline` runner 同步 | 低 | DeepSeek Low：renamer 必须同步改 runner |
| 7 | 全文档 + **口径 sweep**：一物多名统一（`Zone/adjacent_zone`(surface_specs) = `OBC=Surface/object`(IDF) = 切配(口语)；[geometry_first_zonification.md:55](../architecture/geometry_first_zonification.md) 等）| 中 | 用户已点名，末尾全盘扫 |
| 8 | 复测 sm21_pre | — | **先解 phase2a 重叠 defect**（见 §6）或用干净输入 |

---

## 5. 工作流约定（用户定，务必遵守）
1. **审阅**：deepseek MCP 容器内不可达 → 用 `python Tool_scripts/deepseek_review.py`（`--diff`/`--files`/stdin + `--context`）。**做前的计划 + 每步做完都审一遍**。
2. **commit**：节点 commit（仿 `<月.日>_<英文标签>`，body 含①改动②为何此刻③影响）。在 main 上提交（项目惯例），**不 push**（除非用户要）。
3. **备份**：动 `skills/`/`src/` 前 cp 到 `Skill_history/`/`src_history/<日期>_<reason>/`。
4. **严重问题停下问用户**。**历史测试不改**。实验产物（test_data 的 output/）按惯例不入库。

---

## 6. 关键发现 / 决策（带进新会话）
- **切配定性反转**（2026-06-09）：sm20/sm21 对照证明**一步出 LLM 切配做得对**（sm20 三层 7/8/4 更难也 0 门 issue、真切子面），**staged 退化**（12/26 issue）。根因 = staged 把跨层切配孤立成 LLM 机械记账。→ **切配收回我方、确定性做**（核之后吃 cells）。非"LLM 不能"、非信息变少。
- **sm21_pre 的 phase2a 几何 defective**：F1 `Office1/2/3 y[3,5]` 与 `Corridor y[3,5]` **重叠**、顶带 y[5,8] 空（phase2a 坐标 slip）。这是**校正质量问题、非内核 bug**；内核重叠守卫已标记。复测前需处理（修 1_correction 规则 or 用干净输入）。**注意**：之前误把 sm21_pre 渲染图读成"三条带"，实为"空顶带+走廊压办公"。
- **集成岔口（Step 5）**：surface_specs 是 free-text `str`，下游 LLM 消费。几何确定性化后怎么交接——序列化 vs 直接造面——**待和用户定**。
- 内核已证明在干净输入上 0 issue；瓶颈在 phase2a 几何质量（建模判断）+ 集成。

---

## 7. 待用户拍板（收工前未定）
1. 后续步骤**连着自动推进**（每步审+commit、Step5 停）还是**一步一停**看着走？
2. sm21_pre 的 **phase2a 重叠 defect** 现在顺手修，还是复测时用干净手搓输入、phase2a 质量另开？

---

## 8. 关键文件索引
- 内核：[src/agent/geometry/build.py](../../src/agent/geometry/build.py) · [to_idf.py](../../src/agent/geometry/to_idf.py) · [tests/test_geometry_kernel.py](../../tests/test_geometry_kernel.py)
- 校正核：[src/agent/correction/](../../src/agent/correction)（deterministic.py / config.py / schema.py）· [src/configs/correction.yaml](../../src/configs/correction.yaml)
- phase2 主链：[src/agent/phase2.py](../../src/agent/phase2.py)（run_phase2 = 2a→核→2b；待拆 2_modelling/3_split_pairing/4_mep/5_intakeoutput）
- 门：[src/validator/interzone.py](../../src/validator/interzone.py)（"对"的定义）
- skill：[skills/energyplus_mcp_twostep/](../../skills/energyplus_mcp_twostep)（0_reading/1_correction/4_mep/ + phase2/rules.md 待拆）
- 审阅：[Tool_scripts/deepseek_review.py](../../Tool_scripts/deepseek_review.py)
- 架构 spec：[pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md) §0.1（目标架构）/ §3.1（产物布局）
