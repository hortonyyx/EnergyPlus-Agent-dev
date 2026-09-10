# 用现有入口跑 case

本文是现有工具的最短使用指引，不把正式评测流程当作每次探索的必经步骤。
已有 sm21/sm24 的历史 EP 成功产物，当前最新 sm25 尚未贯通，状态见 [路线与当前任务](../project/roadmap.md)。本页说明现有码的运行方法；原图自动入口为显式启用，当前实验结果见路线页。

## 最小 BIM Agent 实验入口（09-10）

独立于旧 `flow`，用已登录 Claude 订阅的 Sonnet 自主选择原图查看、量测、局部 Haiku 复核和源 BIM 生成/检查。当前支持输入目录中的 PNG；不要把 GT、历史生成图或辅助答案放进该目录。

```bash
python scripts/tool_scripts/run_bim_agent.py run \
  --images case_tests/e2e_tests/sm21_anchor/case_data \
  --out AI_agent/logs/experiments/<新的实验目录> \
  --scope '根据所给平面与立面生成保留房间、门窗和连通的可查看 BIM' \
  --timeout 900
```

输出目录须不存在。每个 `candidate_XX` 保存原方案、源 BIM、查看器和检查报告；`tools.jsonl`、订阅回执及流式记录说明真实执行过程。模型回复结束不代表已有候选；以实际保存的 `viewer.html`、`source_model.json` 及报告为准。源 BIM 的几何检查通过也不等于原图保真验收，独立对照须在生成结束后另做，不反馈 GT。

运行不使用付费 API 或默认回退，拒绝其他模型别名；六候选、两次局部复核和超时仅是本次实验预算。首次启动需 `alwaysLoad` 保证 MCP 工具在模型首请求前加载；工具清单、图片限制与生成接口已有离线 stdio 检查。主模型当前使用 medium effort；以回执中的实际版本为准。此入口未替换旧读图路径；实际质量与当前限制见 [任务页](../project/roadmap.md)。

从保存候选继续时，在以上命令加 `--resume-candidate <旧 candidate_XX 目录>`。输出仍须是新目录；只读取旧 `proposal.json`，在新 run 的 `seed/` 重建源 BIM 与检查，不读旧报告或 GT 对照。此次身份为 `saved_candidate_recovery`，不能记作新冷启动。模型可选择 `inspect_candidate`、`revise_bim` 和候选平面查看；局部门窗修改/删除须记录理由与来源，整体反射由代码统一变换房间与开口，并提示复核旧方向备注。

门窗更新会将新 `source_refs` 写回对象，旧来源保留在 before 审计；`changes.assumptions` 可显式替换对象假设，缺省则保留。独立 `source_model.json` 的 `generation.corrections` 同步保存完整修订历史，包括删掉开口的旧对象，源摘要随之重新计算。

局部变换仅支持当前 legacy v1/v2 方案；含显式围护声明、独立楼层 footprint 或额外方向元数据的整体反射会拒绝，避免漏改关联几何。它不是持久编辑界面，也不迁移完整源边界历史。

### BIM Agent 的开口回查

候选建成后，Agent 可先调用 `check_openings(candidate)` 取得当前源模型的实际开口清单，再在查看原始图片后以 `check_openings(candidate, review_json)` 提交回查。清单按楼层给出完整门、窗、空通道对象，按空间给出实际 ID 和计数；它不识别像素，也不从备注或自由文字推断门数。未建开口和不支持观察会单列提示，不能当作已建清单的一部分。

一份 `review_json` 只覆盖一个 `floor_id`、一个 `kind` 和一张输入图。`coverage: "complete"` 才声明该楼层/类别完整，`"partial"` 只能保存局部图证据，不能报告全层完整。每个 mark 只能代表一处独立开口或连接并对应一个 opening ID；室外开口只写室内空间。最小格式如下，坐标是原图像素框，示例不表示任何 case 的答案：

```json
{
  "floor_id": "F1",
  "kind": "door",
  "image": "plan.png",
  "coverage": "partial",
  "marks": [{
    "mark_id": "door-mark-1",
    "box": [12, 18, 40, 54],
    "opening_ids": ["door-id-1"],
    "space_ids": ["room-a", "room-b"],
    "basis": "visible",
    "note": "door arc and wall gap"
  }]
}
```

工具拒绝未知图片、越界或非有限像素框、错误字段和重复 mark ID；并报告多 ID mark、同 review 的重复开口 ID/像素框、未知 ID、漏列模型开口以及连接、类别和楼层不符。`inferred` 与 `uncertain` 会保留为待核，不冒称已见。结果保存到本次 run 的 `opening_reviews/`，绑定当前 `source_model_sha256` 和图像 SHA-256，并列出各房间的实际、对应和缺失 ID。候选修改后必须重新回查；没有 finding 只表示与这份供给观察一致，`drawing_fidelity` 仍为 `not_evaluated`，不能把模型自报观察当成 GT 或原图保真通过。

### 原图叠图与实际交付

`overlay_candidate(candidate, image, floor_id, x_anchors, y_anchors, basis, box?)` 将当前源平面画回原图。每轴锚点沿用 `map_pixels` 的两组 `[原图像素位置, 世界米]`，`basis` 写明尺寸来源与墙面基准；可用 `box` 按原图坐标裁看细节。支持轴对齐平面，旋转/透视没有自动校正。品红表示源边界，橙色表示门/空通道，绿色表示窗；完整分辨率叠图和坐标侧车保存于 run 的 `image_overlays/`。标定和原图保真仍未独立评价，工具可按需调用。

模型用 `finish_bim(candidate)` 选择最终保存候选，生成 run 的 `delivery.json` 与 `delivery.html`。摘要直接引用源几何检查和回查状态，不解释模型最后文字；旧源回查单列，未查或需跟进也可交付查看。后续仍可继续修订或重新选择，结束时刷新所选候选的实际回查。没有显式选择时保留最新已保存源（没有新候选时可保留 seed），并明确标记系统回退，不冒称模型已选定或已经通过。运行结束后还会写入本次调用正常结束/中断、实际错误消息和耗时；有源但没有查看器时不宣称已有可查看输出。

### 生成后的独立参照诊断

共用 [evaluate_bim_agent.py](../../scripts/tool_scripts/evaluate_bim_agent.py) 在本次生成结束后比较 seed（若有）及保存候选，复用既有分区与窗比较器，不改容差。默认新建 `run/evaluation/`，已有输出会拒绝覆盖；复核旧结果可指定新的 `--out`。

```bash
python scripts/tool_scripts/evaluate_bim_agent.py \
  --run AI_agent/logs/experiments/<本次运行> \
  --reference-case sm21_anchor \
  --modelling-task reconstruction \
  --reference-scope '提供了全部平立面；独立参照只在生成结束后使用'
```

受控缺信息实验使用 `--modelling-task partial_inference`，并在 `--reference-scope` 说明哪些输入给了生成、哪些只留在评价侧。原始完整参照差异照常保存，但**没有提供的内部格局不按还原任务判漏房/错分区**；已有外形、立面等约束仍须核对，推断合理性与源简化另评。工具不自动决定整案通过，分区结果也不验证门洞连通、跨层挑空或像素语义。GT 和本报告不得送入生成输入目录。

分区支持现有 v2/v3 参照；窗评分目前只接旧 v2 参照。遇到 v3（如 sm24）会保留分区报告并明确窗匹配 `not_evaluated`，数量不当匹配成绩，不将 v3 强压成旧格式。实际立面窗差仍需用原图或后续 typed 评分接线核对。

## 1. 准备独立 run

- 素材放 `case_tests/e2e_tests/<case>/case_data/`，用 `testdata_prompt.json` 提供声明；新实验放 `<case>/run_<说明>/`，不覆盖旧 run。
- 观测放 `<case>/<run>/0_reading/*_view.json`。当前 as-drawn 接受 plan v2 + elevation v0；缺立面会报 `ELEVATION_EVIDENCE_MISSING`，混用 legacy/as-drawn 会报 `CORRECTION_MIXED_CONTRACTS`。
- 默认 `flow` 仍核验已有 `*_view.json`。需要从原图启动时，显式加下面的 `--reading-model` 和完整校正模型配置；自动入口复用隔离读图及原有合并检查。
- 上游 reading 复用隔离查看、[reading_toolbox.py](../../scripts/tool_scripts/reading_toolbox.py) 和 [reading 工具](../../src/agent/reading)。记录模型和人工处理。不能把 GT 编译结果当成无答案读图。
- 复用历史 reading 要标明来源；它可用于工程诊断，不等于本次冷启动识图。
- 新输入若不满足现有契约，明确缺口；混合输入/体量的降级能力尚待开发。
- GT 留在评测侧；生成执行器只看本次原始输入与声明。

## 原图自动启动（显式选择订阅模型）

先准备新 RUN 与无密钥 `LLM.yaml`：

```yaml
intake_correction:
  provider: claude_subscription
  model_name: claude-sonnet-4-6
  timeout_seconds: 600
correction_decision:
  provider: claude_subscription
  model_name: claude-sonnet-4-6
  timeout_seconds: 600
```

```bash
python -m scripts.tool_scripts.run_stage --budget-draws 1 flow CASE RUN --target source-bim --bim-out NEW_SOURCE_DIRECTORY --reading-model haiku --reading-timeout 900 --llm-config LLM.yaml --judge off
```

`--reading-model` 支持 haiku/sonnet，对应显式固定版本；自动校正当前要求上述 Claude 订阅 provider，Haiku/Sonnet 为允许档位，不接 API key 或 base URL。本机须有已登录订阅的 Claude CLI，环境按订阅路径隔离，不继承 API 端点/密钥或全局 DeepSeek 配置。校正 CLI 禁用工具与 MCP，只接收文本 JSON 请求；订阅估算用量不等于实际账单。

`--budget-draws 1` 限制 stage 抽取轮数；旧校正函数仍可在一轮内对格式/调用失败做最多 3 次同模型请求，各次分别留档。这不等于全程只调用一次模型。

原图根据已冻结的视图清单复制到隔离目录，读图从自己的工具及输入开始，无逐图人工停点。仅启动一次；已有已接受读图则复用，存在失败/未接受产物或启动记录则停止，保留结果供定位。默认 900 秒超时，运行报告在 `_run/automatic_reading.json`；其中链接隔离输出、调用记录和检查。失败不靠丢图、换模型或再抽一次自动掩盖；重试应明确新实验或已有受控恢复入口。

`--llm-config` 现从 flow 启动时覆盖整个主干，退出时恢复调用者环境。优先级为显式参数、`EP_AGENT_LLM_CONFIG`、run/case/global 配置。已有 run_config 的 judge/scope 设置仍生效（如 `judge: {mode: off}`、`scope: {stages: [0_reading, 1_correction]}`），不要把裸 `judge: off` 当作同一格式。

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

明确整面/局部开敞或未知围护时，先导出基准 BIM，按其中的源边界 ID 与 `source_model_sha256` 准备声明，再在新的源目录生成：

```bash
python -m scripts.tool_scripts.run_stage bim CASE RUN --out NEW_ENCLOSURE_DIRECTORY --enclosure-input ENCLOSURE.json
```

`flow --target source-bim` 同样接受 `--enclosure-input`。声明格式及三种可复制例见 [受控场景](../logs/experiments/2026-09-09_source_enclosure_run05/README.md)，契约见 [共同模型](../design/model.md#显式实际围护09-09-v3-增量)。声明必须绑定当前基准摘要；改变上游后需重新核对，旧声明不会自动套用。原始声明、副本摘要及应用记录随源输出保存。unknown 允许生成带告警的可查看几何，报告同时标记围护信息不完整。`source_bim_v3` 当前不进入 EP；显式 `legacy-ep` 加围护声明也会拒绝。

离线复现三种表达（历史几何 + 明确标注的人工例，不调用模型/求解器）：

```bash
python scripts/tool_scripts/diagnose_source_enclosure.py --out AI_agent/logs/experiments/NEW_ENCLOSURE_RUN
```

直接查看源文件也可运行 `python scripts/tool_scripts/render_geometry_viewer.py SOURCE_DIR/source_model.json --out NEW_VIEWER.html`。HTML 依赖现有 Three.js CDN；本轮未做浏览器渲染验收，附图仅为声明侧面的正投影检查。

从 v2 BIM 接 EP 分叉，不回读 correction，也不调用模型：

```bash
python -m scripts.tool_scripts.run_stage backend-ep --source SOURCE_DIR/source_model.json --physics-template PHYSICS.idf --zone-bindings ZONE_BINDINGS.json --out NEW_EP_DIRECTORY --with-ep --epw data/weather/Shenzhen.epw
```

共同主干连同 EP 分叉一次执行：

```bash
python -m scripts.tool_scripts.run_stage flow CASE RUN --target ep --bim-out NEW_SOURCE_DIRECTORY --physics-template PHYSICS.idf --zone-bindings ZONE_BINDINGS.json --backend-out NEW_EP_DIRECTORY --with-ep --judge off
```

物性模板只含材料、构造、作息、负荷、理想负荷系统和仿真设置，包含旧 Zone/墙面/窗等几何会拒绝。`ZONE_BINDINGS.json` 是源空间 ID → 模板所用热区名的完整一对一映射；现成示例见 [sm21 输入](../logs/experiments/2026-09-09_ep_branch_sm21/inputs/zone_bindings.json)。一房一热区、最低层接地、未知北向取模板值均记录为后端假设；源有北向时优先使用，坐标以 Relative + 全零 zone 变换输出。外窗、理想负荷模板及显式关闭门已跑通，已知敞开门/空通道仍明确阻塞。未加 `--with-ep` 只导出，报告为 `exported/not_run`，不能当成仿真成功。保存源快照、物性/绑定、EP 几何、源映射、检查、IDF 和运行报告；输出目录须新建。跨 case 目录的 RUN 请传绝对路径。见 [本轮证据](../logs/experiments/2026-09-09_ep_branch_sm21/README.md)。

含门时，为 `backend-ep` 或 `flow --target ep` 增加 `--opening-policy POLICY.json`，按源开口 ID 指定 `{"state":"closed","construction":"Diagnostic_Door","reason":"本次仿真明确假设关闭"}`。所有门都须非空理由；未知状态只在后端按假设关闭，不改源 BIM，已知敞开和空通道不能被该策略覆盖。模板中须有同名不透明构造；内门双侧的子面相互引用并保留源门映射。接口与完整示例见 [物性契约](../design/ep_physics_contract.md)。

含门案例复现（历史辅助 sm24，使用明确的实验物性假设；省略 `--with-ep` 只导出）：

```bash
python scripts/tool_scripts/diagnose_ep_doors.py --out AI_agent/logs/experiments/NEW_EP_DOORS_RUN --with-ep
```

原图自动入口已经接线；是否成功生成及保真必须看具体实验。未显式启用该入口的默认 flow 仍复用预先生成观测。全局 LLM 配置仍含 DeepSeek；新生成调用必须明确选择已授权通道。

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
