# 用现有入口跑 case

本文是现有工具的最短使用指引，不把正式评测流程当作每次探索的必经步骤。
当前完整 case 尚未跑通，状态见 [plan.md](../plan.md)；本轮清理只检查命令帮助与离线测试。

## 1. 准备独立 run

- 素材位于 `case_tests/e2e_tests/<case>/`，新实验放独立 `run_<说明>/`，不覆盖旧 run。
- 按当前输入契约准备 `0_reading` 产物及需要的 view manifest / run metadata。
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

下例中的 `CASE` / `RUN` 替换为已准备的素材与新 run 名，命令可能调用配置中的模型：

```bash
python -m scripts.tool_scripts.run_stage --run-profile exploratory --capability-profile orthogonal_polygon flow CASE RUN --to 1_correction --judge off --geometry auto
python -m scripts.tool_scripts.run_stage --run-profile exploratory --capability-profile orthogonal_polygon flow CASE RUN --to 5_intakeoutput --judge off --geometry auto
```

`--judge off` 是探索时跳过评分判断，不会把坏几何变成合格产物，也不会解除全部结构检查。
需要评分判断时用 `--judge stop`，按实际停止原因提交 verdict；不要求所有探索 run 都评分。
需要下游仿真时增加 `--with-ep`，报告按需加 `--record --orchestrator <执行者标识>`。
读取 CLI 实际错误/停止原因后处理最短阻塞，避免靠反复重跑整个流程猜测。

## 3. 看产物判断进度

检查各阶段的 `attempts/NNN/output.json`、`checks.json` 和对应几何图。
至少核对外形/楼层、房间或分区、窗、来源/假设及未完成阶段。
`accepted` 数量、exit code 或单测全绿都不能替代对模型内容的检查。
当前例子 `run_win_e2e` 有 31 窗，但在 `2_modelling` 短边检查停止，不能称整案完成。

## 4. 结束本次实验

写简短 README：目的、输入来源、代码提交、命令/配置、模型调用与否、输出路径、发现和未完成范围。
重要且可共享的产物入 Git；大体积产物保存在明确持久目录并留索引；临时日志不作为唯一证据。
未完成的实验也保留结果，不要求为了归档先修完所有问题。

正式比较成绩时另行检查 GT、输入隔离和评分口径。当前研发默认探索档，正式成绩不会自动由探索结果晋升。
更完整的旧操作步骤只供查询：[历史手册](../archive/2026-09-08_pre_takeover/guides/new_case_guide.md)。
