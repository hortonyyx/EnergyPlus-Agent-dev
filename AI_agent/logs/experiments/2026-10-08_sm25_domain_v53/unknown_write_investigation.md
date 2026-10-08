# `plan_f1` 第三次 `trial_plan_bim` unknown-write 调查

调查日期：2026-10-09（Asia/Singapore）
运行：`sm25_role_v53`，`domain-v53-20261008` / `runtime-v1-20261007`
冻结提交：`b55d47e7c82bb306c7ea838f00985648eef94304`
范围：只读检查活跃运行产物，并在主仓库实验目录制作独立诊断副本；没有调用 work model、模型 API 或 MCP 工具，没有修改冻结代码、生产代码或活跃运行目录。

## 结论

第三次 `trial_plan_bim` 的 unknown-write 是一个可确定性复现的本地预处理代码异常：

```text
builtins.StopIteration
src/agent/runtime_roles/trial.py:149                    _reading_align
src/agent/geometry/plan_dimension_alignment.py:387      align_plan_to_dimensions
src/agent/geometry/plan_dimension_alignment.py:210      _snap_footprint
```

异常发生在 `build_plan_bim` MCP 调用之前。它不是 work model 的无效建模声明，也没有证据指向模型服务、MCP transport、资源耗尽或外部写入失败。

具体触发过程如下：

1. 第三次计划通过 `normalize_plan_fields`、`resolve_plan_lengths` 和 `resolve_plan_pixels`；三阶段分别得到 `aliases=0`、`bindings=0`、`bindings=0`。
2. 进入尺寸对齐时，轮廓仍全部由水平/垂直段组成：

   ```json
   [[281.0,300],[976,300],[976,963],[1439,963],[1439,1231],[513,1231],[513,1053],[513,973],[513.0,973],[513.0,588.0],[281.0,588.0]]
   ```

3. `chain_x_top` 的尺寸对齐先将第 5 段从 `x=513` 移到目标 `x=512.6`。该次逐段修改只移动了共享顶点的一侧，使相邻第 6 段暂时成为 `[512.6,1053] -> [513,973]` 的斜线。
4. `_snap_footprint` 仍按进入函数时的 `range(len(ring))` 逐索引处理，却每轮从已经变异的轮廓重新调用 `_segments`。`_segments` 只产生严格水平或垂直段，因此不再产生 `edge_index=6`。以下表达式没有结果，并抛出未捕获的 `StopIteration`：

   ```python
   next(row for row in _segments(plan["footprint_pixels"], closed=True)
        if row[0] == edge_index)
   ```

这说明输入轮廓在尺寸对齐入口处是正交的；使第 6 段失去正交性的是对齐器对前一段的局部变异。当前发现只解释本次 unknown-write，不能外推为该计划通过后续 Toolkit 编译或语义验收。

## 运行证据链

| 事件/产物 | 证据 |
|---|---|
| `event-000675` | 第三次 `trial_plan_bim` durable intent；`call_id=call_1794e298e1a64441961044bc`，`operation_key=sm25_role_v53:call_1794e298e1a64441961044bc`。调用参数整体 SHA-256 为 `1a25c93f04ab0f73d2e1aa05e87bd3e0069f0a667e17330380b84db1e060c846`。 |
| 调用前状态 | blob `80669aeef82abf824fa852f6748ca7c68b72eb391aa7d17f1e4b91f389929c35`。 |
| `event-000676` | 结果为 `unknown`，运行时只保存 `interrupted after durable intent; result not captured`，没有保存所捕获异常的类型或正文。duration blob `16784f84fbd20ff7b3219371e9dc7cba4c70ec6397316999d1ec576a17508ce1` 记录 `0.43800000000010186s`。 |
| `event-000677` | 状态检查 blob `74c0e3a6f2f7d147fb18201c10a1d3943f75ee261ea663e6d374c91f16820d05`，结论 `inconclusive`。 |
| `event-000678` | `plan_f1` 因 `unknown_write_outcome` 停止。 |
| 第三次计划 | `trial_workspace/trial_receipts/trial_003_plan.json` 已写入，SHA-256 `a2ceb00bf82b8dc8470a6c75409cc6ab1e6d30ad399997b32fd06e309cb045d0`。 |
| 未出现的产物 | 没有 `trial_003_unaligned_input.json`、`trial_003_aligned_input.json`、`trial_003.json` 或第三次候选产物。`PlanTrial.run` 在 `_reading_align` 完成后才写 aligned/unaligned 输入，再调用 `build_plan_bim`，所以本次尚未跨入 MCP 写工具。 |

前两次失败属于正常、可见的格式反馈。`trial_002` 唯一问题是 `dimension_chains[1].tick_pixels` 数量少一个；第三次只修正了这一项，完整计划的其余顶层字段未变化。第三次随后通过格式、长度和像素绑定阶段，才触发上述对齐器异常。

运行时为何只能报告 unknown：`src/agent_runtime/loop.py` 对 non-idempotent write 在 durable intent 后捕获任意 `Exception` 或 `asyncio.CancelledError`，但 `_unknown_execution` 事件没有写入异常类型或安全化消息。因此原始 journal 无法单独区分取消、transport 异常和本地代码异常；本次通过落盘边界和确定性最小重放完成了分类。

## 独立诊断副本与最小重放

目录：`AI_agent/logs/experiments/2026-10-08_sm25_domain_v53/unknown_write_diagnostic/`

真正执行该失败路径所需的最小输入只有第三次 plan 和原图：

| 文件 | 字节 | SHA-256 | 用途 |
|---|---:|---|---|
| `trial_003_plan.json` | 10521 | `a2ceb00bf82b8dc8470a6c75409cc6ab1e6d30ad399997b32fd06e309cb045d0` | 精确计划输入 |
| `1f_view.png` | 451136 | `6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644` | 对齐使用的 admitted original |

另保存 `inputs.json`（`d8da47959ba8f080f78b762997fb29438a843f2daa30415882e777e8c1f539cc`）和 `reader_task.json`（`28e296852eea6cd9fa1de926d19d3e70261cee970fd01eb78775eec8aef6dc58`）作为来源证明。第三次 plan 没有实际 measurement-profile 绑定；`source_refs` 中出现的 `profile_003` 只是证据文本，重放过程没有读取 profile 文件。

`replay_probe.py` 只调用冻结代码的 normalize/resolve/alignment 纯处理路径，明确停止在 `build_plan_bim` 之前。它使用与原运行 launch receipt 相同的 Python：`C:/Users/Horton/Desktop/EnergyPlus-Agent-dev/.venv/Scripts/python.exe`。重放命令为：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.venv\Scripts\python.exe' -B `
  'C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\logs\experiments\2026-10-08_sm25_domain_v53\unknown_write_diagnostic\replay_probe.py'
```

预期退出码为 `1`，异常为 `builtins.StopIteration`。完整栈和变异后轮廓保存在 `replay_trace.txt`；输入、探针、栈、冻结代码哈希以及 before/after 状态哈希保存在 `manifest.json`。重放没有启动整套 runtime，没有调用 work model、模型 API 或 MCP server。

## 引入范围

`git blame` 将 `_snap_footprint` 第 197-212 行，包括失败的 `next(...)`，全部定位到提交 `4f9ef0a4743ae4640a2a6dbff85bf580fcebc8af`（`Q1 E-G: plan reader positions aligned to ink and dimension chains (role division)`，2026-10-08 03:19:55 +08:00）。该提交经 `b664052d` 合入，早于 `domain-v52` 的 sm25 运行和本次 `domain-v53` / G1 提交。因此：

- 缺陷存在于 v53 使用的冻结代码中；
- 它不是 v53/G1 本轮新引入，来源是更早的 Q1 尺寸对齐实现；
- 此前格式失败没有进入该有效尺寸链路径，所以未暴露此分支。

## 后续最小通用修复与测试边界（未实现）

修复应让 `_snap_footprint` 不再假定“逐段变异后，原始每个 edge index 仍能由严格正交 `_segments` 找到”。可采用以下任一等价的通用方案：

1. 在变异前基于稳定 ring 快照建立待处理边和目标，随后一次性更新共享顶点；或
2. 每次移动时同时维持相邻边的正交约束，并在当前索引不存在时生成结构化 rejection，而不是让 `StopIteration` 逃逸。

不建议只把 `next(...)` 改为静默跳过：这样会留下对齐器自己造成的斜边，掩盖几何损坏。

至少应覆盖：

- 一个外轮廓同一直线上含多个相邻子段，前一子段被尺寸 tick 移动、后一子段共享顶点；
- 轮廓含连续共线顶点和零长度重复顶点；
- x/y 两个方向都有尺寸链，且第一条链变异后第二条链继续处理；
- 对齐完成后每个外轮廓段仍为水平或垂直、polygon 有效、声明附着关系仍成立；
- 无法安全保持正交时返回可见失败回执，不产生 runtime unknown-write；
- runtime 的 unknown-write 事件至少保存安全化的异常类型和阶段，便于以后不经重放区分本地异常与取消/transport 失败。

当前没有实施修复，也没有重放会写入活跃路径的工具。后续若修复，应在新的离线工作区验证，再决定如何处置本次 `plan_f1`，不能把这份调查解释为整案或该计划已通过。
