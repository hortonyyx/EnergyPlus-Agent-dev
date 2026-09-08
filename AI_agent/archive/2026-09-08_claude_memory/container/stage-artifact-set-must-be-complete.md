---
name: stage-artifact-set-must-be-complete
description: 2026-08-15 用户重申（规矩 2026-07-03 就写过、一直没执行）：跑到哪个环节就出齐哪个环节的全套产物；reading = 每张 render 图 + grade 图
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9d92b917-9cde-4300-9937-0407cec6a78f
  modified: 2026-08-15T12:52:50.369Z
---

**2026-08-15 用户重申**（起因：orchestrator 跑完 A1/A2/B1 三轮 reading，
只出了 JSON 与分数表，render 图与 grade 图都是用户追问后才补渲）：

> 「跑测每个环节该有的产物得出全啊，每次测试不管走多少环节，该有的产物都不能省略。
> reading 的产物是需要有每个的 reading 图以及 grade 图。之前的不用管了，之后都需要按这个。」

**⭐⭐ 关键：这不是新规矩，是既有契约没被执行 —— 别再当成「没规定」去重新讨论。**
用户当场提示「这个应该之前约束过」，一查两处白纸黑字：

- `AI_agent/architecture/pipeline_stage_contracts.md:142`（0_reading 产物登记）：
  `{Nf,*}_view.json` / `reading_summary.md` / `reading_checks.json`（应补）/
  **`*_render.png`（线框，供人/judge 对图）**
- `AI_agent/guides/new_case_guide.md:56`（2026-07-03 `7.03_FlowCleanupBatch` 定）：
  **per-attempt 留痕 —— 每个 `attempts/NNN/` 都出自己的 `score_vs_gt.json` + `grade.png`，
  accepted 的 promote 到 `<stage>/grade.png` + `report/eyeball/0_reading_grade.png`**

**为什么 08-15 那三轮没出（两个独立原因，都要记）**：
1. **orchestrator 自己在 run_config 写了 `judge: mode: off`**（理由「判卷跑完离线做」）
   ⇒ **关掉的正是产 `grade.png` + `score_vs_gt.json` 的那条路**。
2. **硬隔离 merge 路径没有这个生产者** —— `spawn_isolated_reader.py merge` 只归档
   `output.json` + `checks.json`；渲染与判卷挂在 `flow` 路径上
   ⇒ **走隔离壳的 run 结构上就出不齐产物**。
   （= 本项目第 N 次「契约写了、某条路径上零机器消费者」。）

**How to apply**：
- 跑完一个环节**立刻**出齐产物再汇报，⛔ 不要等用户问。
- ⛔ 别再随手写 `judge: mode: off` —— 先确认关掉之后 grade 件由谁补。
- ⚠️ **grade 图必须读 gt** ⇒ 按不变量 #4 只能由 judge 侧产出（gate①/执行器绝不 import gt）。
  render 图不读 gt，执行器侧就能出，不受此限。
- 补出 grade 的真实写入口 = `scripts/tool_scripts/run_stage.py:_grade_attempt_artifacts`
  （legacy 路线）；⚠️ `score_reading_vs_gt.py --out-dir` 走的是 v3 C2 路线、要
  `--gt-file/--view-manifest/--bindings/--judge-config` 四件，**不是同一条路**（F-38）。
- 相关 [[gt-standard-artifact-checklist]]（缺件即红，同一条思路）·
  [[phase1-output-conventions]]（更早的同族约定：SVG + PNG + `_source.png`）·
  [[artifacts-into-repo-not-tmp]] · [[judge-gt-authoritative-images-auxiliary]]
