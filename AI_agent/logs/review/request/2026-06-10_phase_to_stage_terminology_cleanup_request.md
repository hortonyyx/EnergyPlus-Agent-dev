# 审阅请求 · phase1/phase2 → 0–5 阶段名 全盘清理是否干净

> 发起：主开发 Agent（Opus），2026-06-10。审阅模型建议：Codex。
> 关联 commits（main，已 push）：`fc31ea5`（skill 库改名 + 5_intakeoutput + 退役单步库）、
> `0558146`（术语全盘清理主体）、`faa7b2e`（审阅 nit）、`d9a7779`（工作树清理）。
> 背景：用户要求把旧称 **phase1/phase2/phase2a/phase2b** 全部改成 **0–5 阶段名**，
> 「不要混用」。本请求让 Codex 复查**是否已清理干净、有无错漏/断链/回归**。

## 0. 命名对照（验收基准）

| 旧称 | 新名 |
|---|---|
| phase1（识图） | **0_reading** / "the reading stage" |
| phase2a（校正） | **1_correction** / "the correction stage" |
| core（确定性核） | 确定性核（1_correction 内） |
| phase2b 几何 | **2_modelling + 3_split_pairing**（代码内核） |
| phase2b 物理 | **4_mep** |
| phase2b 装配 | **5_intakeoutput** |
| `src/agent/phase2.py` | `src/agent/pipeline.py` |
| `run_phase2` / `run_phase2a` | `run_pipeline` / `run_correction`（`run_mep` 不变） |
| `run_phase2b` + `_build_phase2b_messages` | **已删除**（内核硬错改 raise、无 LLM 回退） |
| `discover_phase1_files` / `_load_partA` | `discover_vector_files` / `_load_correction_docs` |
| llm.yaml `intake_phase2` | `intake_correction`（+ 可选 `intake_mep`/`intake_reading`；删死的单步 `intake` 段） |
| state `phase1_vector_dir` / `phase2_debug_dir` | `reading_vector_dir` / `pipeline_out_dir` |
| CLI `--phase1-from` | `--reading-from` |
| `run_phase2_deepseek.py` | `run_pipeline_deepseek.py` |
| 产物 `phase2a_geometry*` / `phase1_summary.md` | `correction_geometry*` / `reading_summary.md` |
| reading 输入目录 `phase1_vector/` | `0_reading/` |
| 测试 `test_phase2_kernel_wiring` / `test_intake_twostep` | `test_pipeline_kernel_wiring` / `test_intake_pipeline` |
| skill `intake_pipeline/phase2/rules.md` | **删除**（几何→代码、物理→4_mep；归档 Skill_history） |

## 1. 审阅范围

1. **代码 / 配置 / 测试零残留**：`src/`、`scripts/`、`tests/`、`Tool_scripts/`、`src/configs/*.yaml`
   不应再有 phase1/phase2/phase2a/phase2b/run_phase2/intake_phase2/phase1_vector/phase2_debug 等旧称。
   - **例外（故意保留，请确认这是对的）**：`src/agent/graph.py` 与 `src/agent/nodes/cross_ref.py`
     里的 "phase 1/2/3" 指**下游 9 个 subagent 的执行波次**（zone/material/schedule = 第一波），
     是与 intake 阶段**不同的概念**、且属协作者下游代码——本次刻意未改。
2. **改名正确且完整**：`pipeline.py` 的编排链（run_correction→核→几何内核→序列化→run_mep→装配→契约校验）
   逻辑无误；`_section()` 回退链（`intake_<stage>` 缺则回 `intake_correction`）正确；
   删 `run_phase2b` 后内核硬错走 raise（`materialize_kernel_geometry` 仍返回 `(None, err)`）安全。
3. **无断链 / 悬空符号 / 坏 markdown 链接**：全仓库（含 AI_agent/ 文档）不应有指向已删文件/符号
   （`run_phase2b` / `phase2/rules.md` / `phase2.py`）的有效引用；不应有我之前误造的
   `](.../intake_pipeline/ (rules.md retired...))` 这类括号入 URL 的坏链。
4. **活文档已改到阶段名**：`skills/intake_pipeline/`（README + 各 `spec.md` + `0_reading/*` 提示词 +
   `1_correction/README`）、`guides/new_case_guide.md`（流程/布局/§5.4/附录 A；附录 B 已标废弃）、
   `architecture/pipeline_stage_contracts.md`（含 legacy-fallback 错述已修 + 术语 banner）。
5. **历史叙述的处理是否可接受**：dated 决策记录（`capability/*`、`plan.md`、几条 architecture/reference、
   `rules_md_split_map.md`、CLAUDE §5.x、`logs/downstream_agent_changes.md` 旧条目）**保留旧称作时间点记录**，
   但顶部加了**术语对照 banner**（旧称→阶段名映射）。请判断这种「活文档改、历史记录加 banner 不重写」
   的取舍是否合理、banner 是否到位。

## 2. 关注点（重点找这些）

- 任何**漏改**导致运行期会断的旧引用（import 已删模块、读已删 skill 文件、读旧 state 字段、用旧 CLI flag）。
- `llm.yaml` 段名改了之后，per-case 配置（`smalloffice_22/llm.yaml`、模板）是否一致；`_section` 回退是否会
  在 `intake_mep` 缺失时正确回到 `intake_correction`。
- 删 `run_phase2b` 是否留下孤儿引用 / 文档仍宣称有 LLM 回退（我修了 contracts 两处，请确认没漏）。
- 产物文件名改了之后，文档里描述的 on-disk 布局是否同步（`correction_geometry*` / `reading_summary.md` /
  `0_reading/` / 阶段子目录）。
- `test_data` 里改名的 reading 目录（sm20/21/22 的 `0_reading/` + `reading_summary.md`）是否完整、
  代码 `run_correction` 读 `reading_summary.md` 能对上。

## 3. 相关文件（入口）

- 核心：[src/agent/pipeline.py](../../../src/agent/pipeline.py)、[src/agent/nodes/intake.py](../../../src/agent/nodes/intake.py)、
  [src/agent/state.py](../../../src/agent/state.py)、[scripts/run_full_pipeline.py](../../../scripts/run_full_pipeline.py)、
  [src/configs/llm.yaml](../../../src/configs/llm.yaml)、[Tool_scripts/run_pipeline_deepseek.py](../../../Tool_scripts/run_pipeline_deepseek.py)
- skill 库：[skills/intake_pipeline/](../../../skills/intake_pipeline)
- 活文档：[guides/new_case_guide.md](../../guides/new_case_guide.md)、[architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)
- 快速自查命令（建议先跑）：
  ```bash
  grep -rniE "phase ?1|phase ?2|phase2a|phase2b|run_phase2|intake_phase2|phase1_vector|phase2_debug" \
    src/ scripts/ tests/ Tool_scripts/ src/configs/*.yaml | grep -vE "graph.py|cross_ref.py"
  # 期望：空（仅下游波次的 graph/cross_ref 例外）
  python -m pytest -q        # 期望：52 passed
  ```

## 4. 验收标准

- **PASS**：上面自查命令为空（除 graph/cross_ref 下游波次例外）；52 测通过；无悬空引用/坏链；
  活文档一致用阶段名；历史记录加了术语 banner。
- 如发现**漏网的旧称 / 断链 / 运行期会断的引用 / 文档与代码不一致**，按 High/Medium/Low 分级列出，
  附 file:line + 证据 + 建议修法，落到 [`review/review/2026-06-10_phase_to_stage_terminology_cleanup_review.md`](../review/)。
