# 两步法 intake 架构图示（汇报用）

> 配合 [`floorplan_redraw_strategy.md`](floorplan_redraw_strategy.md) §9 POC 结果使用。

---

## 1. 总览（Mermaid，多数 markdown viewer 直接渲染）

```mermaid
flowchart TB
    %% ===== Inputs =====
    IMG["🖼️ 图像<br/>平面 × N + 立面 × 4"]
    META["📄 testdata_prompt.json<br/>楼层 / 用途 / 城市"]

    %% ===== Phase 1 =====
    subgraph P1["Phase 1: 矢量化重绘（视觉翻译）"]
        direction TB
        VLM["🧠 多模态 LLM<br/>当前 Opus 4.7 → 未来微调小 VLM"]
        SCH[("phase1_vector_schema<br/>strokes + pen 词典")]
    end

    %% ===== Middle artifact =====
    VEC["📐 矢量 JSON × N<br/>strokes[pen+geometry] + dimensions + ocr_texts"]
    SVG["🎨 SVG 渲染<br/>← 👤 用户人工核验入口（30 min/case）"]

    %% ===== Phase 2 =====
    subgraph P2["Phase 2: 拓扑建模（纯文本推理）"]
        direction TB
        TLM["🧠 文本 LLM（无需 VLM）<br/>Opus / DeepSeek thinking → 未来微调小 LLM"]
        RUL[("phase2_rules<br/>11 字段推导顺序 + 命名 + vertex 合成")]
    end

    %% ===== Final =====
    IO["📦 IntakeOutput Pydantic<br/>11 字段（building / site / 9×_specs）"]

    %% ===== Downstream (unchanged) =====
    subgraph DS["下游（架构不变）"]
        direction LR
        SUB["9 subagents<br/>(DeepSeek V4 pro)"] --> IDF["IDF"] --> EP["EnergyPlus simulate"]
    end

    %% ===== Edges =====
    IMG --> VLM
    META --> VLM
    SCH -.约束.-> VLM
    VLM --> VEC
    VEC --> SVG

    VEC --> TLM
    META --> TLM
    RUL -.约束.-> TLM
    TLM --> IO

    IO --> SUB

    %% styling
    classDef phase fill:#e8f4ff,stroke:#1976d2,stroke-width:2px
    classDef artifact fill:#fff4d6,stroke:#bfa600,stroke-width:1px
    classDef inspect fill:#d6f0ff,stroke:#0288d1,stroke-width:1px,stroke-dasharray:4 2
    class P1,P2 phase
    class VEC,IO artifact
    class SVG inspect
```

---

## 2. ASCII 备用（无 Mermaid 渲染环境）

```
┌─────────────────────────────────────────────────────────────────┐
│  输入                                                            │
│  🖼️ 图像（平面 × N + 立面 × 4）   📄 testdata_prompt.json       │
└────────┬──────────────────────────────┬─────────────────────────┘
         │                              │
         ▼                              │
┌─────────────────────────────────────┐ │
│ Phase 1: 矢量化重绘（视觉翻译）       │ │
│ ─────────────────────────────────── │ │
│ • 多模态 LLM (Opus 4.7 → 小 VLM)    │ │
│ • 约束: phase1_vector_schema        │ │
│   (strokes + pen 词典)              │ │
└────────┬────────────────────────────┘ │
         │                              │
         ▼                              │
   📐 矢量 JSON × N                     │
   (strokes[pen+geometry] +             │
    dimensions + ocr_texts)             │
         │                              │
         ├──→ 🎨 SVG 渲染               │
         │     ← 👤 用户人工核验         │
         │       (30 min / case)        │
         │                              │
         ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: 拓扑建模（纯文本推理，无需 VLM）                          │
│ ─────────────────────────────────────────────────────────────── │
│ • 文本 LLM (Opus / DeepSeek thinking → 小 LLM)                  │
│ • 约束: phase2_rules (11 字段推导顺序 + 命名 + vertex)            │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
   📦 IntakeOutput Pydantic（11 字段）
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 下游（架构不变）                                                  │
│   9 subagents (DeepSeek)  →  IDF  →  EnergyPlus simulate         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 与单步法对比

```mermaid
flowchart LR
    subgraph OLD["旧 单步法"]
        direction TB
        I1[图像 + 文本] --> M1["多模态 LLM<br/>(同时做识图+拓扑+输出)"] --> O1[IntakeOutput]
    end

    subgraph NEW["新 两步法"]
        direction TB
        I2[图像] --> M2["VLM<br/>(纯描摹)"] --> V[矢量 JSON] --> M3["文本 LLM<br/>(纯拓扑)"] --> O2[IntakeOutput]
        V -.->|人工 SVG 校验| V
    end

    classDef step fill:#fff4d6,stroke:#bfa600,stroke-width:1px
    class OLD,NEW step
```

| 维度 | 旧 单步法 | 新 两步法 |
|---|---|---|
| LLM 调用 | 1 次（多模态） | 2 次（VLM + 文本 LLM）|
| 中间产物 | 无（黑箱）| 矢量 JSON（人工可校验）|
| 误差归因 | 视觉错 + 推理错纠缠 | **识图错 ⇿ 推理错可分离** |
| 微调可行性 | 单一 (图, IntakeOutput) 大目标 | 拆 (图, 矢量 JSON) + (矢量 JSON, IntakeOutput) 两数据流 |
| 图风格泛化 | prompt 硬编码制图规范 → 风格切换易失效 | phase1 schema 是制图规范，可独立扩展 |

---

## 4. 误差预算分离（两步法核心收益）

```mermaid
flowchart TB
    subgraph E1["📷 Phase 1 误差（看图）"]
        e1a[尺寸读错]
        e1b[笔触遗漏]
        e1c[坐标偏移]
        e1d[立面 x 轴方向搞反]
    end

    subgraph E2["📐 Phase 2 误差（不看图，只读 JSON）"]
        e2a[zone 拓扑判错]
        e2b[surface 配对错]
        e2c[命名跨字段漂移]
        e2d[坐标系翻译错]
    end

    E1 -->|被矢量 JSON 锁定| LOCK[("📐 矢量 JSON<br/>frozen")]
    LOCK -->|phase2 不看图|无法回溯
    E2 --> 无法回溯["⚠️ phase2 没机会出视觉错"]

    classDef err1 fill:#ffe0e0,stroke:#c62828
    classDef err2 fill:#fff3e0,stroke:#ef6c00
    class E1 err1
    class E2 err2
```

**关键含义**：sm_20 POC 实证 — anchor 单步法的 F3 corridor 窗 `z_max = 9.60`（**视觉错与推理纠缠**）；两步法两条路径都给 `z_max = 10.60`，因为 phase1 已把"窗高=2.40 / sill=1.00 / top_gap=1.40"识图层面锁定为 `y_range_m: [8.20, 10.60]`，phase2 没机会重做坐标推导。

---

## 5. 微调路径

```mermaid
flowchart LR
    subgraph T1["Phase 1 微调"]
        D1["(图, 矢量 JSON) 对<br/>分布近 VLM 预训练<br/>schema 强约束输出"]
        --> M1["小 VLM<br/>Qwen2.5-VL / DeepSeek-VL"]
    end

    subgraph T2["Phase 2 微调"]
        D2["(矢量 JSON, IntakeOutput) 对<br/>从 anchor 批量生成<br/>纯文本任务"]
        --> M2["任意文本 LLM<br/>可 sub-billion-param"]
    end

    T1 -.->|独立迭代不阻塞| T2

    classDef tune fill:#e8f5e9,stroke:#2e7d32
    class T1,T2 tune
```

两数据流**互不阻塞**，phase2 甚至不需要 VLM —— 这降低了开源模型 pivot 的硬件门槛。

---

## 6. 关键 artifacts（可放进汇报附录）

| 文件 | 角色 |
|---|---|
| [`skills/energyplus_mcp_twostep/phase1_vector_schema.md`](../skills/energyplus_mcp_twostep/phase1_vector_schema.md) | Phase 1 输出格式契约 |
| [`skills/energyplus_mcp_twostep/phase2_rules.md`](../skills/energyplus_mcp_twostep/phase2_rules.md) | Phase 2 推理规则 |
| [`Tool_scripts/render_vector_to_svg.py`](../Tool_scripts/render_vector_to_svg.py) | 人工校验工具（矢量 JSON → SVG）|
| [`Tool_scripts/run_phase2_deepseek.py`](../Tool_scripts/run_phase2_deepseek.py) | Phase 2 自动跑批脚本 |
| [`test_data/SmallOffice_TwoStep/smalloffice_20/`](../test_data/SmallOffice_TwoStep/smalloffice_20/) | POC anchor 全套 artifacts |
| [`test_data/SmallOffice_TwoStep/smalloffice_20/compare/diff.md`](../test_data/SmallOffice_TwoStep/smalloffice_20/compare/diff.md) | 三方对比详表 |

---

_2026-05-12 — 配合 5.12_TwoStepIntakePOC_NewMainline commit_
