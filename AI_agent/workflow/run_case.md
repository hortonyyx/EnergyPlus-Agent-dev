# 用现有入口跑 case

本文是现有工具的最短使用指引，不把正式评测流程当作每次探索的必经步骤。
已有 sm21/sm24 的历史 EP 成功产物，当前最新 sm25 尚未贯通，状态见 [路线与当前任务](../project/roadmap.md)。本页说明现有码的运行方法，不代表已经具备从原图开始的无人值守入口。

## 1. 准备独立 run

- 素材放 `case_tests/e2e_tests/<case>/case_data/`，用 `testdata_prompt.json` 提供声明；新实验放 `<case>/run_<说明>/`，不覆盖旧 run。
- 观测放 `<case>/<run>/0_reading/*_view.json`。当前 as-drawn 接受 plan v2 + elevation v0；缺立面会报 `ELEVATION_EVIDENCE_MISSING`，混用 legacy/as-drawn 会报 `CORRECTION_MIXED_CONTRACTS`。
- 先从原始素材生成符合输入契约的 `*_view.json`、view manifest / run metadata。当前 `flow` 的 `_draw_reading` 只检查这些预先生成的观测，不调用视觉模型读原图；只有下面的 flow 命令还不能完成冷启动生成。
- 上游 reading 生成可从 [reading_toolbox.py](../../scripts/tool_scripts/reading_toolbox.py) 及 [reading 工具](../../src/agent/reading) 复用；它们仍需配置、观测准备和调用顺序，尚不能冒称一键生成入口。记录模型和人工处理。不能把 GT 编译结果当成无答案读图。
- 复用历史 reading 要标明来源；它可用于工程诊断，不等于本次冷启动识图。
- 新输入若不满足现有契约，明确缺口；混合输入/体量的降级能力尚待开发。
- GT 留在评测侧；生成执行器只看本次原始输入与声明。

## 2. 检查和推进

从仓库根运行；先看帮助与已有 run 状态：

```bash
python -m scripts.tool_scripts.run_stage --help
python -m scripts.tool_scripts.run_stage flow --help
python -m scripts.tool_scripts.run_stage status sm25-L_anchor run_win_e2e
```

用现有 provision 建立 manifest，无需手写；flow 也会按配置自动预配：

```bash
python -m scripts.tool_scripts.run_stage --run-profile exploratory --capability-profile orthogonal_polygon provision CASE RUN
```

先核对 run 里的 `run_config.yaml`：文件存在时，`judge_mode` 优先于 CLI `--judge`，`scope_stages` 还可能把默认终点 5 改为更早阶段。以下命令的停止位置要结合该配置判断。
若要固定整个 flow 的模型组合，启动此子进程时将 `EP_AGENT_LLM_CONFIG` 设为所选配置文件绝对路径。当前 `--llm-config` / run 的 `llm.yaml` 由下游 `_flow_ep` 才解析，并不会自动控制前面已经执行的 correction/MEP；没有环境覆盖时前段仍读全局配置。

执行前核对实际模型和回退配置；若会调用 DeepSeek，先取得用户对此任务/批次的明确同意。跑 case 的一般授权不包含 DeepSeek 专项许可；Claude、GLM 的现有订阅调用按 [模型约定](models.md) 自行安排。

下例中的 `CASE` / `RUN` 替换为已准备的素材与新 run 名，命令可能调用配置中的模型：

```bash
python -m scripts.tool_scripts.run_stage --run-profile exploratory --capability-profile orthogonal_polygon flow CASE RUN --to 1_correction --judge off --geometry auto
python -m scripts.tool_scripts.run_stage --run-profile exploratory --capability-profile orthogonal_polygon flow CASE RUN --to 5_intakeoutput --judge off --geometry auto
```

在没有 run 配置覆盖时，`--judge off` 是探索时跳过评分判断，不会把坏几何变成合格产物，也不会解除全部结构检查。
需要评分判断时用 `--judge stop`，按实际停止原因提交 verdict；不要求所有探索 run 都评分。
需要下游仿真时增加 `--with-ep`，报告按需加 `--record --orchestrator <执行者标识>`。
读取 CLI 实际错误/停止原因后处理最短阻塞，避免靠反复重跑整个流程猜测。

## 3. 看产物判断进度

检查各阶段的 `attempts/NNN/output.json`、`checks.json` 和对应几何图。
优先由 checks、judge 与可用 GT 自动核对外形/楼层、房间或分区、窗、来源/假设及未完成阶段，生成带对象定位的定性报告；人工只抽查代表结果和当前无法自动裁决的异常。细小偏差按 [评价原则](../design/evaluation.md) 处理，不要求每次人工逐房或逐顶点对账。
`accepted` 数量、exit code 或单测全绿都不能替代对模型内容的检查。
当前 case 的数量、失败和完整性风险见 [计划](../project/roadmap.md)。没有 expected 数量的 PASS 与 NA 项不能证明房间完整。

## 4. 结束本次实验

写简短 README：目的、输入来源、代码提交、命令/配置、模型调用与否、输出路径、发现和未完成范围。
重要且可共享的产物入 Git；大体积产物保存在明确持久目录并留索引；临时日志不作为唯一证据。
未完成的实验也保留结果，不要求为了归档先修完所有问题。

正式比较成绩时另行检查 GT、输入隔离和评分口径。当前研发默认探索档，正式成绩不会自动由探索结果晋升。
更完整的旧操作步骤只供查询：[历史手册](../archive/2026-09-08_pre_takeover/guides/new_case_guide.md)。
