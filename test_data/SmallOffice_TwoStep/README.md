# SmallOffice_TwoStep — 两步法识图建模测试语料库

> 与 [`../SmallOffice/`](../SmallOffice/) 并列。该目录里的所有 case **使用两步法 intake**（phase1 矢量化重绘 → phase2 拓扑建模），而 `SmallOffice/` 走旧的单步多模态 intake。

## 缘起

2026-05-12 sm_20 POC 验证：
- F3 corridor 窗 z 修正（B1 残留 slip） — 两步法两条路径都准 / 单步 anchor 错
- DeepSeek 两步法全链路 EP cleanly 跑通（0 severe / 9 warning）
- 架构通透性 + 识图泛化 + 微调可行性同时验证

详见 [`smalloffice_20/compare/diff.md`](smalloffice_20/compare/diff.md) + [AI_agent/floorplan_redraw_strategy.md](../../AI_agent/capability/floorplan_redraw_strategy.md) §9。

## 标准 case 目录结构

```
<case>/
├── *_view.png / supp_plan.png         # 源图纸
├── testdata_prompt.json               # 元信息（楼层数 / 用途 / 城市 ...）
├── phase1_prompt.md                   # phase1 启动 prompt（粘进新 Claude Code 会话）
├── phase2_prompt.md                   # phase2 启动 prompt（同上）
├── vector_schema_v*.md                # phase1 矢量 JSON schema（运行时本地副本）
├── phase2_rules.md                    # phase2 规则（运行时本地副本）
├── phase1_vector/                     # phase1 产物（每图一份 JSON + SVG + summary）
├── phase2_intake/{opus,deepseek}/     # phase2 产物（intake_output.json 等）
├── output_<llm>/                      # run_full_pipeline 下游 + EP 产物
├── step6_<llm>.log                    # 下游链路日志
└── compare/diff.md                    # 路径间三方对比（含 anchor 一步法）
```

## 标准 schema / rules 来源

每个 case 的 `vector_schema_v*.md` 和 `phase2_rules.md` 是运行时**本地副本**，记录该次跑用的版本（audit anchor）。**演进版本** 在 [`../../skills/energyplus_mcp_twostep/`](../../skills/energyplus_mcp_twostep/) 维护，新建 case 时从 skill 复制最新版到 case 目录。

## 当前 case

| case | 状态 | 备注 |
|---|---|---|
| `smalloffice_20/` | ✅ POC validated 2026-05-12 | 19 zones / 16 windows / F2 北 4 不对称窗 + F3 通长窗 + F3 corridor 窗。OpenStudio 几何视察 PASS。DeepSeek 路径 EP cleanly；Opus 路径 EP fatal (phase2_rules v1.3 修复) |

## 与旧 corpus（`SmallOffice/`）的关系

- 旧 corpus 仍保留作 anchor + 历史 baseline 数据。`smalloffice_20/output_new/intake_output.json` 是单步 anchor（POC 对比用）
- 新 corpus（本目录）是两步法的工作区，后续新建 case 默认进这里
- 等两步法成为主线后，`SmallOffice/` 历史 case 可逐步迁移过来重跑
