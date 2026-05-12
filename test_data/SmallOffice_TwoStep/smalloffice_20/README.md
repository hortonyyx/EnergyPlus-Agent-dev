# smalloffice_20 — 两步法 POC anchor

> 2026-05-12 跑出。原 case `SmallOffice/smalloffice_20/` 的同素材复用版本，用两步法跑。架构通透性 + 识图泛化 + 微调可行性的硬证据。

## 验收 PASS 项

| 验收项 | 结果 |
|---|---|
| Phase 1 矢量化质量（7 图 + SVG 人工核验）| ✅ 高（含 F2 北 4 不对称窗 + 4 立面 facade_axis_note 正确）|
| Phase 2 拓扑建模（19 zones / 16 windows / cross-floor split-pairing）| ✅ Opus / DeepSeek 双路径都 PASS Pydantic |
| L3 IDF 生成 | ✅ Opus / DeepSeek 双路径都通过 9 subagent |
| L4 EP simulate | ✅ DeepSeek 路径 EP `Completed Successfully` / 0 severe / 9 warning / 8.49s 全年 |
| L4 EP simulate (Opus 路径) | ❌ Fatal: InterZone construction asymmetry（**phase2_rules.md v1.3 已加 InterZone single-construction 硬约束**） |
| F3 corridor 窗 z 修正 | ✅ 两步法两条路径都给 z=[8.20,10.60]；anchor 单步给 z=[8.20,9.60]（错）|
| OpenStudio 几何视察 | ✅ 用户视察 PASS |

详见 [`compare/diff.md`](compare/diff.md)。

## 如何复现

### Phase 1（识图）

新开 Claude Code 会话（Opus 4.7），粘 [`phase1_prompt.md`](phase1_prompt.md) 内容。产物落 `phase1_vector/`。

### Phase 2（拓扑建模）

两条路径并行可跑：

- **Opus 路径**：另起 Claude Code 会话，粘 [`phase2_prompt.md`](phase2_prompt.md)。产物落 `phase2_intake/opus/`
- **DeepSeek 路径**：`python Tool_scripts/run_phase2_deepseek.py --case test_data/SmallOffice_TwoStep/smalloffice_20`。产物落 `phase2_intake/deepseek/`

### Step 6（下游 + EP）

```powershell
python scripts/run_full_pipeline.py smalloffice_20 --intake-from phase2_intake/opus/intake_output.json --output-subdir output_opus
python scripts/run_full_pipeline.py smalloffice_20 --intake-from phase2_intake/deepseek/intake_output.json --output-subdir output_deepseek
```

> 注：`run_full_pipeline.py` 当前硬编码 case 在 `test_data/SmallOffice/<case>`，跑前需调整 `--case-root` 或临时软链。Two-step 主线落地时需顺手修。

## 关键 artifacts

| 路径 | 作用 |
|---|---|
| [`phase1_vector/*.json`](phase1_vector/) | 7 张图各 1 份矢量 JSON（描摹层）|
| [`phase1_vector/*.svg`](phase1_vector/) | 矢量 JSON 渲染后的 SVG（人工核验对照原 PNG）|
| [`phase1_vector/phase1_summary.md`](phase1_vector/phase1_summary.md) | phase1 总结 + 4 立面 local↔world 翻译公式 |
| [`phase2_intake/opus/intake_output.json`](phase2_intake/opus/intake_output.json) | Opus 两步法终产物（38.8 KB）|
| [`phase2_intake/opus/self_check.md`](phase2_intake/opus/self_check.md) | Opus phase2 §7 自检（9/9 PASS）|
| [`phase2_intake/opus/phase2_followup_notes.md`](phase2_intake/opus/phase2_followup_notes.md) | Opus 暴露的 10 条 phase2_rules schema gap |
| [`phase2_intake/deepseek/intake_output.json`](phase2_intake/deepseek/intake_output.json) | DeepSeek 两步法终产物（25.9 KB）|
| [`phase2_intake/deepseek/thinking.txt`](phase2_intake/deepseek/thinking.txt) | DeepSeek 17 KB reasoning 思路（thinking enabled）|
| [`output_deepseek/eplusout.err`](output_deepseek/eplusout.err) | EP cleanly 完成日志（0 severe / 9 warning）|
| [`output_opus/eplusout.err`](output_opus/eplusout.err) | EP fatal（construction asymmetry，已修规则）|
| [`compare/diff.md`](compare/diff.md) | 三方对比详表 |
