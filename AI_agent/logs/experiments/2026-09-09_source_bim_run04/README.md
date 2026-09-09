# 独立源 BIM 生成：提交后复现

实现 `d6fd8732`。[三案例与分区对照](index.html) · [实际 source flow 查看](flow_sm21_bim/viewer.html) · [报告与文件摘要](report.json)。

```bash
python scripts/tool_scripts/diagnose_source_bim.py --out AI_agent/logs/experiments/2026-09-09_source_bim_run04
```

本目录已存在，复现须选新的输出目录。原始输入、旧 run、GT 不改写。新输出的完整边界不做 EP 切配，没有热工物性；显示投影的网格片不作为物理隔断。

全部复用历史校正；sm24 辅助模型和 sm25 走廊决定保留人工参与。sm21 14 空间/15 窗，sm24 旧反例 11 空间/11 窗、辅助 8 空间/11 窗/1 门，sm25 29 空间/31 窗/29 门。已建门窗三维顶点保留。sm24 两个候选仍有独立分区差异；sm25 两组未建门继续阻塞；sm21/sm25 外边界参考面差异待核对。

真实 CLI flow 只复用 reading/correction，未创建旧 Stage 2–5 或人工确认。源几何通过不等于图纸保真通过，报告分开列出；GT 只在生成完成后的评价端读取。模型/solver 调用均为 0，未完成原图冷启动、浏览器 WebGL 验证、编辑或 EP 适配。

223 项相关测试及调试详情见 [工作记录](../../worklog/2026-09-09_source_bim_pipeline.md)。
