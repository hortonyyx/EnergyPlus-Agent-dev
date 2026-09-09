# Stage 2 源模型确认与恢复：离线验证

代码提交：`76aad9fe77c9d30946453a973faff99ce1d08a15`。查看 [汇总入口](index.html)、[执行报告](report.json) 和 [文件验证](artifact_validation.json)。

```bash
python scripts/tool_scripts/diagnose_source_checkpoint.py --out AI_agent/logs/experiments/2026-09-09_m1_source_checkpoint_run01
```

本次独立 run 复用 sm21 `run_2026-07-02_sonnet_flow_e2e` 的历史 reading/correction；reading 沿用原检查，correction 用当前检查重验，再由当前代码执行 Stage 2。输入摘要保存在接受记录中，原 run 不修改。sm25 仅复制前一程辅助候选及诊断，不重新判图或生成模型。

- sm21：14 空间、无已记录的未建/未支持观测。正常 Stage 2 执行后停在确认；直接执行 Stage 3 在确认前被拒绝。以 `diagnostic:auto`、`policy=auto` 明确记录模拟确认后，正常自动定位 Stage 3 并确定性通过；Stage 0/1/2 输出摘要均未改变，源确认仍有效。
- sm25：29 空间、2 条未建门记录。仅生成带状态的查看快照，确认被拒绝，未产生 geometry_approval.json。源映射通过不代表开口完整，两个短边问题仍保留在检查记录。
- `manual_review/geometry_viewer.html` 是当前快照索引；子目录保存不可变 HTML、源模型、显示几何和检查依据。sm21 建模刚完成但尚未写入接受记录时的预览也保留，不能用它代替已接受版本确认。

未调用模型、judge 或 EnergyPlus；不是冷启动成绩，也不是用户人工确认。未验证持久编辑、完整图纸正确性或浏览器 WebGL 交互。HTML 内脚本语法、链接和当前快照摘要已验证，具体数量见文件验证报告。源到下游开放门洞适配不在本程范围。
