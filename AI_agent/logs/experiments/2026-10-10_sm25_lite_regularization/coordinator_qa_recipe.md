# sm25 Lite 最终协调与立面回叠配方

本文只整理本轮已冻结工具契约和四份已验收立面 artifact 的校准值，不读取 GT，也不执行模型、协调工具或运行目录写入。以下命令只能在当前 `delegate` 进程退出、`writer.lock` 释放后执行。

## 固定入口

协调、返工、交付及 finalizer 均在活动运行的冻结树 `D:\EnergyPlus-Agent-worktrees\lite-sm25-run-20261010` 中执行，不能在主树打开一个同名但不同位置的 run。参数文件先由项目经理保存到冻结树对应实验目录；不修改冻结代码或配置。完成并归档回主树后，才在主树执行独立评价。

```powershell
. ./scripts/activate_windows.ps1
$Python = ".\.venv\Scripts\python.exe"
$Dispatch = "AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py"
$Finalize = "AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/finalize_manual_dispatch.py"
$Config = "AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json"
$Run = "AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1"
```

`manual_dispatch.py tool` 的统一形式是：

```powershell
& $Python $Dispatch tool --config $Config --name <工具名> --arguments <参数JSON>
```

参数文件应放在本实验目录中并经项目经理审核。活动 `delegate` 持有非阻塞独占 writer lock；此时不要调用 `tool`、`status` 或 finalizer，也不要直接改 `events.jsonl`、checkpoint、reader record 或 BIM 运行文件。

## 组装与审核顺序

首轮组装使用现有 [args_assemble_initial.json](args_assemble_initial.json)，它显式选择本轮六份交付：

```powershell
& $Python $Dispatch tool --config $Config --name assemble_from_readers --arguments AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/args_assemble_initial.json
```

组装结果中的 `candidate` 是后续所有命令的当前候选。不要从目录编号猜候选。

- `status=assembly_review_required`：读取同一响应中的 `assembly_review.review_id` 和全部 `changes[].change_id`。用 `review_role_assembly` 提交恰好一条对应每个 change ID 的非空、基于本轮证据的理由，然后用相同六任务参数重新调用 `assemble_from_readers`。已审计的规整项不会要求确认，不要伪造决定补齐列表。
- `status=assembly_delivery_blocked` 或 review `status=blocked`：不能用 review 接受。修复陈旧/未验证 lineage，或对具体 reader 问题做同 run 局部返工，再重新组装。
- `position_review.delivery_blocking=true`：调用 `role_state` 的 `{"position_details":true}` 查看项目；对要求决定的 ID 再用 `{"position_decision_id":"..."}` 取得两侧原图证据。超过 30 cm 的决定必须通过 `edit_bim` 的独立 `position_decision` batch 提交所需 `view_ids`，之后重新调用 `assemble_from_readers`。`reread_*` 仍保持阻塞，应走具体 reader 局部返工。

`review_role_assembly` 参数形状如下；值只能来自刚返回的当前 review：

```json
{
  "review_id": "CURRENT_REVIEW_ID",
  "decisions": [
    {
      "change_id": "CHANGE_ID_FROM_CURRENT_REVIEW",
      "reason": "对照本轮 reader artifact 与当前 source 后确认该变化的具体理由"
    }
  ]
}
```

工具要求 decisions 不重不漏地覆盖当前 review 的全部 change ID。若 source 或 reader 引用已经变化，旧 review ID 会被拒绝，应重新组装并审核新比较。

## 四立面 overlay 参数

`view_elevation_candidate` 的精确参数是：

```text
candidate: string
facade: North | South | East | West
image: 原图的精确文件名
horizontal_anchors: 恰好两个 [原图像素位置, 世界米坐标]
z_anchors: 恰好两个 [原图像素位置, 绝对 Z 米坐标]
basis: 非空的观测依据
```

North/South 的横向世界坐标是 world x，East/West 是 world y；它不是“距图片左缘”的局部距离。Z 是绝对 Z，不是距本层楼面的高度。两个轴都要求像素和世界值各自不同。以下值逐项复制自本轮 accepted artifact 的 `x_calibration` 与 `z_calibration`，顺序和正负方向保持原样。将四个 JSON 中唯一的 `CURRENT_CANDIDATE` 换成最终当前候选；其余字段不要按生成几何重新拟合。

North：artifact `86eae30f7beba2e22620d56ff7b11e2e170563e98cd7338202a553ea1d737815`

```json
{
  "candidate": "CURRENT_CANDIDATE",
  "facade": "North",
  "image": "North_view.png",
  "horizontal_anchors": [[441.0, 25.0], [2285.0, 0.0]],
  "z_anchors": [[308.0, 7.2], [839.0, 0.0]],
  "basis": "Accepted elevation_north artifact 86eae30f7beba2e22620d56ff7b11e2e170563e98cd7338202a553ea1d737815; exact saved x_calibration and absolute-z calibration endpoints."
}
```

South：artifact `01ecffe428614ef22f4d717222e36df6352931479b00cf7e3bcdca5e706f8519`

```json
{
  "candidate": "CURRENT_CANDIDATE",
  "facade": "South",
  "image": "South_view.png",
  "horizontal_anchors": [[376.5, 0.0], [2221.5, 25.0]],
  "z_anchors": [[296.0, 7.2], [827.5, 0.0]],
  "basis": "Accepted elevation_south artifact 01ecffe428614ef22f4d717222e36df6352931479b00cf7e3bcdca5e706f8519; exact saved x_calibration and absolute-z calibration endpoints."
}
```

East：artifact `aa4166537e4b684aa553a19b37e37a8ba88ddbb3594fae39f84035ba64083766`

```json
{
  "candidate": "CURRENT_CANDIDATE",
  "facade": "East",
  "image": "East_view.png",
  "horizontal_anchors": [[312.0, 0.0], [1787.0, 20.0]],
  "z_anchors": [[272.0, 7.2], [802.0, 0.0]],
  "basis": "Accepted elevation_east artifact aa4166537e4b684aa553a19b37e37a8ba88ddbb3594fae39f84035ba64083766; exact saved x_calibration and absolute-z calibration endpoints."
}
```

West：artifact `77c68e855ae5259ad498bfe8daaa88c6459da8fbd717568b8044384792b0b099`

```json
{
  "candidate": "CURRENT_CANDIDATE",
  "facade": "West",
  "image": "West_view.png",
  "horizontal_anchors": [[521.0, 20.0], [1998.0, 0.0]],
  "z_anchors": [[330.0, 7.2], [862.0, 0.0]],
  "basis": "Accepted elevation_west artifact 77c68e855ae5259ad498bfe8daaa88c6459da8fbd717568b8044384792b0b099; exact saved x_calibration and absolute-z calibration endpoints."
}
```

每次调用会把 clean original 和当前 source overlay 一起返回，并在 `bim/elevation_reviews/review_NNNN.json` 保存记录。它只投影当前 source，不改几何，也不宣告图纸一致。检查彩色开口库存、楼层线、上下沿和明显错位；若发现实质问题，只对具体对象走同 run 局部返工或有证据的编辑。任何局部返工、重新组装或编辑产生新候选后，应在该新候选上重做受影响立面；最终应让四个 facade 最新的 review 记录都来自最终候选。

## 开口检查、finish 与 finalizer

四立面回叠完成后，对同一当前候选调用一次完整开口检查：

```json
{
  "candidate": "CURRENT_CANDIDATE"
}
```

工具名为 `check_openings`。它返回实际 opening inventory、`height_coverage`、`facade_counts` 和现有 review 的状态。仅需快速复核高度时可以用：

```json
{
  "candidate": "CURRENT_CANDIDATE",
  "heights_only": true
}
```

不要为了得到“通过”而构造 `review_json`；该字段只用于已有原图 mark 观察的结构化复核。若候选、参数和依赖完全不变，role wrapper 会复用前次检查并返回保存的结论指针。

在以下条件满足后调用 `finish_bim`：当前 assembly review 已清空或确认、无 stale lineage、position review 无 pending/reread、四立面最新回叠对应当前候选、开口库存与高度覆盖没有需要修复的实质问题。参数为：

```json
{
  "candidate": "CURRENT_CANDIDATE"
}
```

`finish_bim` 会写 `bim/delivery_selection.json`、`bim/delivery.json` 和 `bim/delivery.html`，但它不证明图纸正确。它在 role wrapper 中还会重新执行 assembly 与 position guards；被拒绝时应处理返回的具体阻塞项，不要绕过。

所有 reader 和协调工具都停止后，再收口根生命周期：

```powershell
& $Python $Finalize finalize --config $Config --status completed
```

finalizer 会再次拒绝活动 reader。它可能依据已选候选重写最终 delivery 摘要，因此应在所有检查、回叠与 `finish_bim` 之后运行。

## `evaluate_run` 对回叠记录的读取约定

公共评价必须等本轮交付和 finalizer 完成后再执行；届时它会读取 GT，本文件准备阶段未读取 GT：

```powershell
& $Python scripts/dev/evaluate_run.py $Run --case sm25 --out AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1/dev_evaluation
```

`--out` 目录必须尚不存在。未给 `--candidate` 时，评价器从 `bim/delivery.json` 读取交付候选。对每个 facade，它按文件名顺序扫描 `bim/elevation_reviews/*.json`，选择最后一条含 `anchors` 或 `transform` 的记录；显式 overlay 记录优先使用 `anchors.horizontal` 与 `anchors.absolute_z`。随后评价器用交付候选的 `source_model.json` 和该校准重新渲染 `overlays/elevation_<Facade>.png`，并把所用 review 文件名写入 `overlays/index.json`。

因此最终核对两点：

1. `overlays/index.json` 四个 facade 都没有 `no calibration`，且 `calibration` 指向各 facade 最后一次显式回叠记录。
2. 若 `finish_bim` 前后候选发生变化，或之后又做过局部返工/编辑，先对最终候选重做四立面回叠，再 finish/finalize/evaluate；不要把旧候选生成的最后一条 review 当成当前稿的视觉审核。

公共评价会对运行输入、delivery、所有 candidate source 和 GT 在执行前后做哈希守卫，并写入独立的新输出目录。其 overlay 是开发侧复核产物，不会回灌 reader 或改变交付几何。
