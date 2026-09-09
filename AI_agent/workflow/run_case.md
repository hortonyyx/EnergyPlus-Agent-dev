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

当前主线使用独立源 BIM 目标（`d6fd8732`）。在原图观测已准备好、并已核对上游模型配置时：

```bash
python -m scripts.tool_scripts.run_stage --capability-profile orthogonal_polygon flow CASE RUN --target source-bim --bim-out NEW_SOURCE_DIRECTORY --judge off
```

它执行/复用 reading、correction，然后直接生成源模型、显示投影和 HTML；不执行旧 Stage 2–5，不授予人工确认。输入仍经过已有阶段检查；`--judge off` 不等于解除结构检查。run 配置明确排除 correction 时会拒绝，`--with-ep`/旧 `--record` 不可与源目标混用。输出目录必须新建。

仅重建已有校正、不调用模型时，可用：

```bash
python -m scripts.tool_scripts.run_stage --capability-profile orthogonal_polygon bim CASE RUN --out NEW_SOURCE_DIRECTORY
```

默认核验已接受校正来源；`--candidate-attempt N` 显式查看指定候选，B5 候选仍核验输入证明，不伪造接受记录。保存 `source_model.json`（完整边界及关系）、`display_geometry.json`、`viewer.html`、`report.json`；局部几何可显示时，未建项仍保留并阻塞几何就绪。`source_geometry_ready` 只表示当前源几何检查状态，图纸保真默认未评价；独立分区报告必须另检。`flow` 默认目标为 `source-bim`，必须指定新的 `--bim-out`；重放旧 Stage 2–5 流程请显式加 `--target legacy-ep`（包括旧确认恢复、`--record` 用法）。

从这份 BIM 接 EP 分叉，不回读 correction，也不调用模型：

```bash
python -m scripts.tool_scripts.run_stage backend-ep --source SOURCE_DIR/source_model.json --physics-template PHYSICS.idf --zone-bindings ZONE_BINDINGS.json --out NEW_EP_DIRECTORY --with-ep --epw data/weather/Shenzhen.epw
```

共同主干连同 EP 分叉一次执行：

```bash
python -m scripts.tool_scripts.run_stage flow CASE RUN --target ep --bim-out NEW_SOURCE_DIRECTORY --physics-template PHYSICS.idf --zone-bindings ZONE_BINDINGS.json --backend-out NEW_EP_DIRECTORY --with-ep --judge off
```

物性模板只含材料、构造、作息、负荷、理想负荷系统和仿真设置，包含旧 Zone/墙面/窗等几何会拒绝。`ZONE_BINDINGS.json` 是源空间 ID → 模板所用热区名的完整一对一映射；现成示例见 [sm21 输入](../logs/experiments/2026-09-09_ep_branch_sm21/inputs/zone_bindings.json)。一房一热区、最低层接地、未知北向取模板值均记录为后端假设；源有北向时优先使用，坐标以 Relative + 全零 zone 变换输出。首版外窗和理想负荷模板已跑通，门/空开口仍明确阻塞。未加 `--with-ep` 只导出，报告为 `exported/not_run`，不能当成仿真成功。保存源快照、物性/绑定、EP 几何、源映射、检查、IDF 和运行报告；输出目录须新建。跨 case 目录的 RUN 请传绝对路径。见 [本轮证据](../logs/experiments/2026-09-09_ep_branch_sm21/README.md)。

真实原图 reading 自动调用尚未接通。当前全局 LLM 配置仍含 DeepSeek；新生成调用前必须显式选已授权通道，不能因新增 source 目标就直接使用默认模型。

本轮离线复现（含 sm24 错分区反例、历史辅助模型与 sm21 实际 source flow）：

```bash
python scripts/tool_scripts/diagnose_source_bim.py --out AI_agent/logs/experiments/NEW_SOURCE_BIM_RUN
```

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

## M0 离线源分区诊断

从仓库根运行 [诊断脚本](../../scripts/tool_scripts/diagnose_source_partitions.py)，输出目录必须是新的独立目录：

```bash
python scripts/tool_scripts/diagnose_source_partitions.py --out AI_agent/logs/experiments/NEW_SOURCE_PARTITION_RUN
```

它读取固定 sm21/sm24/sm25 历史产物、复用当前确定性内核和 sm25 已接受的 B5 证明，不调用模型或 EP、不修改旧 run。`index.html` 汇总历史与当前查看入口、分区/建模状态；`report.json` 保存输入哈希与具体证据。sm24 三墙 fixture 有明确人工分组，8 空间预览不建 11 扇窗（完整候选保留窗记录），不得报告为完整重建。sm21/sm25 缺独立分区参照时为 not_evaluated。

正常 Stage 2 会写 `source_model.json` 和 CLI 查看 HTML；生成查看结果本身不授予确认。

## Stage 2 源模型查看、确认与恢复

`flow CASE RUN --geometry required` 在 Stage 2 检查通过后停下，并打印不可变查看快照的路径及完整版本摘要。先打开 HTML 查看源房间、门窗、未完成项与检查记录，再将实际所看版本的摘要填入：

```bash
python -m scripts.tool_scripts.run_stage approve-geometry CASE RUN --actor YOUR_NAME --digest SOURCE_DIGEST
python -m scripts.tool_scripts.run_stage flow CASE RUN --geometry required
```

恢复从 Stage 3 继续，上游已接受产物不重抽。确认使用 run 的冻结检查策略；修改源输入、接受记录、检查或显示快照后，旧确认失效，须重新生成当前查看版本。查看页只显示摘要前 12 位，完整值以 CLI 或 run 下的 `_run/source_geometry_review.json` 为准。不能把未接受、来源不一致、有阻塞检查或未建/未支持观测的候选确认通过；这些候选仍尽可能生成带状态的查看页。旧 Stage 3 确认不会自动替代新源模型确认。

`--geometry auto` 沿用自动实验模式，明确记录 `flow:auto`，不表示用户看过或人工确认。源确认不证明 Stage 3 序列化、原图完整性或 EnergyPlus 已通过；持久编辑尚待接入。

离线验证可复用历史输入，在新目录重建 Stage 2、模拟确认并恢复 Stage 3，同时验证 sm25 未通过候选可查看且拒绝确认，不调用模型或 EP：

```bash
python scripts/tool_scripts/diagnose_source_checkpoint.py --out AI_agent/logs/experiments/NEW_SOURCE_CHECKPOINT_RUN
```
