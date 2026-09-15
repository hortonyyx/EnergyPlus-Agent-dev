# 用现有入口跑 case

本文是现有工具的最短使用指引，不把正式评测流程当作每次探索的必经步骤。
已有 sm21/sm24 的历史 EP 成功产物，当前最新 sm25 尚未贯通，状态见 [路线与当前任务](../project/roadmap.md)。本页说明现有码的运行方法；原图自动入口为显式启用，当前实验结果见路线页。

## 最小 BIM Agent 实验入口（09-10）

独立于旧 `flow`，用已登录 Claude 订阅的 Sonnet 自主选择原图查看、量测、局部 Haiku 复核和源 BIM 生成/检查。支持输入目录中的 PNG，以及显式提供的建筑基础声明 JSON；不要把 GT、历史生成图或辅助答案放进图片目录。

**09-14 新增 `--building-input 文件.json`。** 该文件原字节复制为运行目录的`building_input.json`；`inputs.json`保留原声明、散列与图面关联，模型通过`inputs`取得。用途、位置、面积、层数等按原字段提供；`thermal_zones`明确为后端分区声明，不自动解释成源物理房间数。声明与图证冲突需模型说明取舍，接口本身不判真。

声明中的路径只按文件名关联到本次PNG清单，保留未提供图面的状态，不据路径读取额外文件。省略该参数仍只枚举PNG，不自动读取邻近JSON；`source_input_mode`与`input_contents`记录实际提供内容，`input_mode`继续区分原图起跑和`--resume-candidate`恢复。局部Haiku观察仍只获得父模型选择的图片和问题，不自动继承整案声明。此前run15等仅原图成绩不变，见[收工核对](../logs/worklog/2026-09-14_focused_guidance_session_close.md)。开发可按研究目的限定输入，详见[产品目标](../project/goal.md#建筑基础声明作为输入09-14-用户确认)。

**09-14 可选像素墙网入口 `build_plan_bim(image, plan_json)`：** 模型用原图像素声明楼层矩形外轮廓、完整物理隔墙折线、门窗端点、两轴像素/米锚点和假设，代码围合所有房间并确定开口两侧空间。详细契约和可执行合成例由 `get_bim_reference("plan_partition")` 返回。仅单层、矩形楼层外轮廓；内部空间可非矩形。真实相交线由代码分段，缺口/悬线/重叠/越界、跨多个宿主的开口明确拒绝，不自动补墙、吸附或裁门。不支持内窗。空间种子仅指定已有区域的名称/用途，不按房间数切分，未命名区域全部保留。

每次原始 JSON 保存在 `plan_drafts/draft_*/plan.json`，编译失败也保留输入/错误，成功时另存像素到源空间/开口映射，源文件绑定这些声明与图像散列。导出后自动登记同一标定，返回实际源平面和原图回叠，后续普通修订继续复用。它是按需几何能力，并不判断墙与家具或标定是否正确，也不替代其他楼层；不完整开口/未看立面必须留在 `unresolved`。

编译前还保存`draft_view.png/json`：原始像素墙线/门窗带ID和端点叠回原图，侧车绑定原JSON/图像散列并列出不能画的项目。失败时MCP实际返回这张声明草图与原错误；成功仍返回原有源图，草图仅留档。草图明确`draft_only`、保真未评价，不创建候选/源标定，不补线或裁门。JSON解析失败则保留原文并明确无法画图；不能把草图当成已建房间或修复成功。

```bash
python scripts/tool_scripts/run_bim_agent.py run \
  --images case_tests/e2e_tests/sm21_anchor/case_data \
  --building-input case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json \
  --out AI_agent/logs/experiments/<新的实验目录> \
  --scope '根据所给平面与立面生成保留房间、门窗和连通的可查看 BIM' \
  --timeout 900
```

输出目录须不存在。每个 `candidate_XX` 保存原方案、源 BIM、查看器和检查报告；`tools.jsonl`、订阅回执及流式记录说明真实执行过程。模型回复结束不代表已有候选；以实际保存的 `viewer.html`、`source_model.json` 及报告为准。源 BIM 的几何检查通过也不等于原图保真验收，独立对照须在生成结束后另做，不反馈 GT。

独立proposal入口的`geometry.windows`只接窗；显式`kind`若不是`window`，会保留原proposal并一次报告所有类别冲突，不生成改类后的源。门和空开口应放`geometry.openings`，使用`space_id`、`p1/p2`和`z`，室外另一侧为`other_space_id:null`。无kind的既有窗格式仍可用。该校验修复run16暴露的“三外门被生成为窗”，没有自动修正原候选或改变旧flow。

运行不使用付费 API 或默认回退，拒绝其他模型别名；六候选、两次局部复核和超时仅是本次实验预算。首次启动需 `alwaysLoad` 保证 MCP 工具在模型首请求前加载；工具清单、图片限制与生成接口已有离线 stdio 检查。主模型默认使用medium effort，可显式加`--effort low`，仅支持low/medium，不改变Haiku设置；实际档位与模型版本以回执为准。此入口未替换旧读图路径；实际质量与当前限制见 [任务页](../project/roadmap.md)。

`review_detail(question, images, timeout_seconds=120)` 由总 Agent 自选局部问题、原图和15–240秒时限，可不调用。每次只把选中的原图副本与原样问题放入独立只读目录 `detail_XX/`；局部 Haiku 不获得主任务 scope、seed、候选、其他原图或旧评价，也不能再次派工或改 BIM。图像与输入清单保存摘要，父目录保留对应请求、流记录和回执；局部成本随主调用汇总一次。文件隔离不清洗问题文本，主模型若在问题里带答案，仍可能影响观察。

09-13 已把实际局部截止时间写入子清单后再计算摘要：取240秒上限与父任务剩余时间（预留45秒收尾）中较短者，拷图耗时也计入。子任务的 `inputs` / `view_image` 现在可显示递减剩余时间；只读提示提醒及时交付并标明未核范围。此前局部观察即使有外层超时，工具仍显示 null，见[真实反例与修复](../logs/worklog/2026-09-13_reconstruction_partition_and_reading.md)。随后两墙局部返工已实际收到剩时并在215.94秒结束，但修正观察仍不可用；这不证明时间反馈使识读可靠，见[后续实跑](../logs/worklog/2026-09-13_reconstruction_annotation_recovery.md)。

09-13 细节查看已支持 `view_image(..., display_scale=4)`：默认1保持原呈现，显式1–8倍按最近邻显示，长边最多1600。`box_original_pixels` 仍是原图框，实际倍率及 `original_pixels_per_returned_pixel` 按最终尺寸返回；`coordinate_grid=false` 可去掉辅助网格。显示缩放不修改原图、不改变 `pixel_profile` 量测输入，也不作为识读正确证明。Sonnet（含只读局部观察）默认medium，可按订阅helper的`effort`参数选low；Haiku保持不传effort，原始实验回执中的旧设置不回写。

`view_pixel_region_overview(name, background_rgb, tolerance=60, min_pixels=500, max_regions=40, include_border=false)`可先在整图查看编号像素区域，再将所选候选的`seed_pixel`原样交给`view_pixel_region`。总览及过滤/截断说明保存于`pixel_region_overviews/`，JSON坐标始终是原图像素。模型应结合整图位置判断候选是房间背景、家具还是尺寸区；过滤掉的候选不代表建筑对象不存在。父/只读工具均可用，不能修改BIM。实现与实际限制见[区域定位](../design/reading_correction.md#09-13-后续先定位区域再判读边界)。

单次局部观察实际取请求时限与主任务剩余时间减45秒中较短者；不足15秒观察预算时不启动。09-13起MCP工具默认120秒，可明确选择更短或最长240秒；直接helper调用仍默认240秒以保留独立观察脚本的既有范围。超时、进程失败和未完成回答须按返回的完成状态处理，局部文字仍只是待核线索，没有自动重试或模型回退。主任务的原图保真验收与这些工具执行状态分别记录。

`map_dimension_chain` 可将模型读出的连续尺寸累计为米制分段坐标，支持 mm/m、指定起点和反向累计，并报告与给定总长的闭合差。模型/Haiku 可按需使用；工具只做算术，不识读数字，不判断段的门窗身份，也不以总长相等证明标注正确。输入、结果和实现摘要随新 run 保存。

从保存候选继续时，在以上命令加 `--resume-candidate <旧 candidate_XX 目录>`。输出仍须是新目录；只读取旧 `proposal.json`，在新 run 的 `seed/` 重建源 BIM 与检查，不读旧报告或 GT 对照。此次身份为 `saved_candidate_recovery`，不能记作新冷启动。模型可选择 `inspect_candidate`、`revise_bim` 和候选平面查看；局部门窗修改/删除须记录理由与来源，整体反射由代码统一变换房间与开口，并提示复核旧方向备注。

门窗更新会将新 `source_refs` 写回对象，旧来源保留在 before 审计；`changes.assumptions` 可显式替换对象假设，缺省则保留。独立 `source_model.json` 的 `generation.corrections` 同步保存完整修订历史，包括删掉开口的旧对象，源摘要随之重新计算。

局部隔墙修订可在 `revise_bim` 的操作列表中使用：

```json
{"op":"move_shared_wall","space_ids":["room_a","room_b"],"coordinate_m":3.5,
 "reason":"原图量测支持共享隔墙的新位置","source_refs":["plan.png: 墙线与尺寸依据"]}
```

代码从两个同层矩形空间的完整共边推导方向与原墙位，同时更新两侧边界，保持两空间合起来的范围和ID；真正宿主在该共墙上的两空间间门/通道随墙平移。其他门窗及楼层保留世界坐标，若改后失去宿主，仍由正常生成检查指出，不能静默丢掉。原方案不变，前后房间和随墙开口写入修订审计；旧源摘要的开口回查不延续到新源。操作不判断新位置是否读图正确。

这项局部操作拒绝多边形、非完整共边、显式围护声明、退化或非法坐标；这些情况仍可由模型保留可靠内容后提交完整方案。它不拆房/并房，不替代原图对照，也不强制任何固定复核流程。

09-13新增`reshape_spaces`处理已有空间的批量局部改形：

```json
{"op":"reshape_spaces","spaces":[{"id":"room_a","polygon":[[0,0],[3,0],[3,2],[0,2]]}],
 "reason":"原图支持此局部轮廓","source_refs":["plan.png: 对应墙段证据"]}
```

相邻受影响空间须在同批列出；代码只替换指定polygon并计算x/y包围盒，不改其他空间/楼层，也不移动、缩放或重挂门窗。需要改变宿主上的门位时在同一次`revise_bim`明确加入`update_opening`，原宽高默认保留；正常生成器仍会拒绝重叠/脱宿主。操作不增删空间，拒绝显式围护声明以及非空墙基准/尺寸证据，避免留下已失效的关联；复杂解释由模型处理，代码不猜正确墙位。实际效果见[协调式恢复记录](../logs/worklog/2026-09-13_reconstruction_coordinator.md)。

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

单张立面可另加 `facade: "North"|"South"|"East"|"West"`，此时 complete 只指该层、该类开口在该立面的完整观察。方向按源宿主外墙几何确定，不从文件名猜；其他面、内门或方向未知开口明确列为范围外。所有实际外墙方向都需完整观察，包含明确 `marks: []` 的零开口立面，才能合并成整层完整；没有 facade 保持原平面回查含义。交付 JSON 和 HTML 保留逐面状态。

工具拒绝未知图片、越界或非有限像素框、错误字段和重复 mark ID；并报告多 ID mark、同 review 的重复开口 ID/像素框、未知 ID、漏列模型开口以及连接、类别和楼层不符。`inferred` 与 `uncertain` 会保留为待核，不冒称已见。结果保存到本次 run 的 `opening_reviews/`，绑定当前 `source_model_sha256` 和图像 SHA-256，并列出各房间的实际、对应和缺失 ID。候选修改后必须重新回查；没有 finding 只表示与这份供给观察一致，`drawing_fidelity` 仍为 `not_evaluated`，不能把模型自报观察当成 GT 或原图保真通过。

### 原图叠图与实际交付

`overlay_candidate(candidate, image, floor_id, x_anchors, y_anchors, basis, box?, reuse_on_revision=True)` 将当前源平面画回原图。每轴锚点沿用 `map_pixels` 的两组 `[原图像素位置, 世界米]`，`basis` 写明尺寸来源与墙面基准；可用 `box` 按原图坐标裁看细节。支持轴对齐平面，旋转/透视没有自动校正。品红表示源边界，橙色表示门/空通道，绿色表示窗；完整分辨率叠图和坐标侧车保存于 run 的 `image_overlays/`。

默认将本次模型选择的标定追加到 `overlay_calibrations/`。同一原图/楼层取最新显式登记，其他图面独立；后续 `build_bim` / `revise_bim` 保存新候选后自动复用这些锚点，返回实际新叠图及源/图像摘要、标定来源和触发动作。自动投影返回整图缩略图，细节可再次显式裁看；不随墙位自动拟合。`reuse_on_revision=False` 只生成本次查看图，不更新已有登记。投影失败通过 `projection_errors` 明示，已保存 BIM 保留。交付区分当前源与旧源投影、未登记视图的楼层及失败；登记和收到图片都不证明标定正确或模型已正确核验。模型应据原图反馈判断是否修订，并用 `set_notes` 保存实际假设和未解决项。此反馈当前接在实验 BIM Agent 入口，效果见 [本轮记录](../logs/worklog/2026-09-10_overlay_feedback.md)。

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

## 09-14 参数化方案与探索性Opus

独立run_bim_agent的`build_parametric_bim`工具按显式模板/实例展开空间与窗列，参数由`get_bim_reference('parametric')`提供；`inspect_parametric_plan`读取已保存的紧凑声明以供修订。原始声明单存parametric_drafts，展开方案仍进入同一源BIM出口。逐层轮廓可以通过JSON保存/恢复；不自动补墙、推断开口或裁剪失败跨距。

普通运行默认Sonnet。只有任务中明确获准的探索可使用`--exploratory-opus`切到现有Claude订阅Opus，本轮Voimatalo已获用户许可。该开关不是付费API/DeepSeek授权，不作自动回退。模型原始回执、输入条件与实际输出分别报告，真实示例及准备脚本见[迁移输入](../logs/experiments/2026-09-14_voimatalo_transfer_setup/README.md)。

开口清单现在允许同标高不同翼楼记录和连续高空间的门连接，按两侧空间与实际高度检查。在各关联楼层/空间组可见同一开口，全局仅计一次，不能直接相加分组数量。

### 原始GLB输入与内部观察（09-14续推）

同一实验入口可用`--mesh ORIGINAL.glb`直接提供原始三维资产，`--images`变为可选；至少提供其中一种。原GLB原样保存在run/assets/input.glb，输入摘要与声明可核；`inspect_mesh`、`view_mesh`、`measure_mesh_pixels`和`view_mesh_observation`仅对本次获准资产可见。图片目录为空时不会先生成固定截图包。普通图纸运行及只接收局部原图的子任务不会因此取得原网格访问权限。

`view_mesh`方位角指相机所在方向（0=局部+x、90=+y），仰角90为俯视；可指定旋转、观察目标、米制范围和三角面中心选区。输出最长边1200像素，按视图物理比例调整另一边并保持两个方向每像素米数一致，`measure_mesh_pixels`使用该视图resolution_px原分辨率查询可见表面，背景不返回虚构坐标。每次相机参数及选区都留档，判读依据引用mesh_observations记录。几何查询不自动识别房间或可靠墙位。

本程真实运行入口与辅助边界见[原网格实验准备](../logs/experiments/2026-09-14_voimatalo_native_mesh_setup/README.md)。Opus沿用本次任务的探索授权，仍不作为常规产品默认档。

续推实跑后修正：独立指定米制宽高时，视图不再被固定画幅拉伸；两选点另返回坐标差与水平朝向，仍不证明所选点属于同一条墙边。大规模`finish_bim`回执保留状态、数量、未建项、假设及未核范围摘要，详细开口/立面/回查清单保留在delivery.json；原图小案例回执保持。实际大案已通过MCP重放，源与报告事实不变，避免原18.4万字符回执被CLI截断。


### 网格方向、坐标关系与源叠图（09-15）

`inspect_mesh_directions(yaw_degrees=0, bounds=None, face_ids=None, max_plane_tilt_degrees=15)`只查询本次原GLB，按旋转后坐标中的三角形质心选区、按偏离竖直面角度过滤。方向是局部+X逆时针模180°的表面水平迹线，已经含查询yaw，**不是要施加的yaw**；平行但不同位置的面会同档。完整结果见`mesh_evidence/`，MCP返回前10档详细记录、未详列面积及全档紧凑分布。像素量测同时返回命中面法向/倾斜，防止将屋顶点当同一墙边。图片输入的独立子任务不会因此取得网格或候选访问。

`set_candidate_mesh_frame(candidate, yaw_degrees, translation_m, reason, source_refs)`绑定本次原网格SHA256，创建新候选；公式为源坐标=R(yaw)×原GLB经节点变换后的[X,-Z,Y]+translation_m。数值几何保留，原网格相对位置改变；房间、外形、门窗和高度错误不会随坐标声明自动消失。直接`build_bim`可提供同字段`mesh_frame`，局部`revise_bim`继续保留它，几何模板生成后也可用此工具登记。不能从相机旋转隐式继承坐标；旧备注需显式修订。

`overlay_mesh_candidate(candidate, observation, floor_id=None, exterior_only=True)`在既有原网格视角上绘制实际源边：品红墙、绿窗、橙门，源背面也显示，按楼层/视角降低重叠。保存于`mesh_overlays/`；返回图片及简短摘要，完整逐对象坐标/像素映射在旁文件。图像不自动拟合候选，不改变源数据，不证明模型已正确回查。`measure_mesh_pixels(..., candidate=...)`可将实际命中点转换到该候选保存的坐标系。未保存frame或引用不符会拒绝。

大案核坐标可先调用`inspect_candidate(candidate, include_geometry=False)`取得备注、楼层和检查；需要改具体空间时再读完整方案。使用普通`run --mesh ... --resume-candidate ...`明确记录旧候选恢复，不能报告冷启动生成。实际参数及新旧范围见[09-15实验准备](../logs/experiments/2026-09-15_voimatalo_frame_setup/README.md)。


首轮实跑后补充：`inspect_candidate(..., floor_id="...")`可按楼层读取；回执过大时自动提供摘要。`read_candidate_items(candidate, collection="cells"|"windows"|"openings", floor_id=None, offset=0, limit=20)`按页返回准确原方案条目，读取`next_offset`直到null才能宣称完整。`check_wall_dimensions`的墙宿主清单增加`floor_id/offset/limit`（默认30，上限50），不改变显式墙面尺寸换算。未查完的部分须保留，不能拿部分页面覆写整案。

外部源墙叠图按精确接触区域扣除，保留墙上未与邻空间接触的外露片；这是显示派生，不生成源隔墙。方向统计留下90°/180°歧义时，要用整栋不对称形状和原坐标基线叠图核准，不可把错转当成可用平移补偿的误差。

## 连续跨层源空间的覆盖声明（09-15）

直接源方案的 `geometry.floors[].spanning_space_ids` 可引用另一源分组中已定义的连续空间ID。例如两层各有本层房间，同时各声明 `["CORE"]`；另一个分组只定义一次贯通两层的 `CORE`。各层声明轮廓包含核心占地，本层房间不与核心重叠。入口核引用存在、覆盖本层全高及完整平面覆盖；不增加中间楼板，不自动推断核心位置或门。省略或空列表保持旧行为。

当前由共同源出口和Voimatalo开发装配实际验证，尚未做Sonnet迁移或EP贯通。按标高筛选的通用楼层视图可能不包含从更低处开始的连续空间；核源体或实际高度剖切，不用补源楼板修显示。契约见[共同模型](../design/model.md)，可重放实例见[本次探路](../logs/experiments/2026-09-15_voimatalo_developer_walkthrough/README.md)。
