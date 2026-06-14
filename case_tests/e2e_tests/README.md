# e2e_tests — 两步法 0–5 管线端到端测试语料库

> 本目录 case 走当前主线：**0_reading 识图（半人工 / 未来 VLM）→ `run_pipeline`（1_correction 校正 → 几何确定性内核 2_modelling+3_split_pairing → 4_mep 物理 → 5_intakeoutput 装配）→ 9 subagent 下游 → InterZone 门 → EnergyPlus**。完整流程见 [AI_agent/guides/new_case_guide.md](../../AI_agent/guides/new_case_guide.md)。
>
> 退役的单步多模态语料归档在 [`../../backup/tests_history/SmallOffice/`](../../backup/tests_history/SmallOffice/)。

## 标准 case 目录结构（2026-06-14 规范）

> 参考实现：[`sm20_anchor/`](sm20_anchor/)（首个按此标准组织的 case）。**各阶段具体产出什么文件待 2026-06-15 起逐环节约束**；下方注释为当前已知产物（可能调整）。

```
<case>/
├── llm.yaml                           # per-case 模型组合（case 根；--init-llm-config 生成）
├── case_data/                         # 素材（输入）：图纸 + 元信息
│   ├── {1f,2f,…}_view.png / {N,S,E,W}_view.png / supp_plan.png   # 源图纸
│   └── testdata_prompt.json           # 元信息（楼层数 / 用途 / 城市 …；图纸路径指向本目录）
├── 0_reading/                         # 阶段0 识图产物：{…}_view.json + *_render.png/svg + reading_summary.md
├── 1_correction/                      # 阶段1 校正(LLM)+确定性核：correction_geometry(_snapped).json + corrections.json + correction_raw.txt
├── 2_modelling/                       # 阶段2 几何内核：building_geometry.json + kernel_gate_report.json
├── 3_split_pairing/                   # 阶段3 切配：geometry_specs.md（序列化 zone/surface/fenestration specs）
├── 4_mep/                             # 阶段4 物理(LLM)：mep_output.json + mep_raw.txt
├── 5_intakeoutput/                    # 阶段5 装配：权威 intake_output.json + contract_issues.json
└── EP/                                # IDF 相关输出：temp_*.idf/.yaml + idf_plan.png + intake_output.json 副本
    └── EP_run/                        # 仿真输出：eplusout.* + ep_console.log + run_idfonly.log
```

> **代码路由已接通（2026-06-14）**：`run_full_pipeline` 读 `case_data/testdata_prompt.json`（缺则回退 case 根 = 旧 case 兼容）、IDF 落 `EP/`、EP 仿真落 `EP/EP_run/`。sm20_anchor 已按新标准组织，可直接跑。
>
> 实验产物目录（`output_*` / `*_pre` 等）按 [CLAUDE.md §5.9.E](../../AI_agent/CLAUDE.md) 惯例不入库（.gitignore 排除）。

## 规则文档来源

几何规则在代码（`src/agent/geometry/`，确定性、不靠 prompt）；校正/物理规则在唯一 skill 库 [`../../skills/intake_pipeline/`](../../skills/intake_pipeline)（`1_correction/` 校正、`4_mep/` 物理），运行时由 `src/agent/pipeline.py` 按阶段加载。**case 目录不再放规则副本**——规则随主线 skill 库演进，不在 case 内复制。

## 当前 case

| case | 状态 | 备注 |
|---|---|---|
| `sm20_anchor/` | 🆕 待跑 | sm20 素材的干净 anchor，**首个按 2026-06-14 标准结构组织**（case_data/ + 0–5 + EP/EP_run）。待 2026-06-15 跑出规范 baseline |
| `smalloffice_20/` | ✅ 干净 anchor | 3 层 19 区 / 16 窗；首个两步法 EP cleanly anchor（2026-05-12）|
| `smalloffice_21/` | ✅ 干净 anchor | 2 层异图 14 区 / 100 面 / 15 窗；首个异图端到端（2026-05-28）|
| `smalloffice_21_pre/` | 实验 | 干净手搓输入版（不入库）|
| `smalloffice_22/` | ✅ | 第 3 个干净 anchor + per-case 模型配置验证 |
| `smalloffice_23/` | ✅ | 单层 9 区 / 11 窗，EP 干净跑通 |

## 与归档单步语料（`backup/tests_history/SmallOffice/`）的关系

- 旧单步 corpus 保留作历史 baseline / anchor 数据；`smalloffice_20/output_new/intake_output.json` 是单步 anchor（POC 对比用）。
- 新建 case 默认进本目录，走两步法 0–5 管线。
