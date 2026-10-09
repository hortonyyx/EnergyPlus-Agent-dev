# domain/kernel 修复报告

日期：2026-10-09（Asia/Singapore）

## 范围与边界

- 迭代范围：`domain/kernel`，修改平面尺寸对齐、墨线对齐及其定向检查。
- 工作基线：`48309caf`；分支 `dev/role-kernel-20261009`。
- 原始证据：主仓库只读副本 `AI_agent/archive/local_backup/sm25_v53/sm25_role_v53` 及上一轮归档的 unknown-write 诊断输入。
- 没有调用 work model、模型 API、MCP server、DeepSeek、Claude 或 Paratera；没有修改 runtime、runtime_roles、roles、guidance、全局管理文档或版本注册；没有删除墙体，也没有放宽编译、拓扑或最小边长检查。
- Python 复用主树 `.venv/Scripts/python.exe`；`PYTHONPATH` 指向本工作树，`PYTHONUTF8=1`、`OPENBLAS_NUM_THREADS=1`。导入路径已回读为本工作树下的两个目标模块。

## 修复前证据

三份失败声明均从主仓库只读归档加载；SHA-256 与上一轮诊断记录一致。

| 对象 | 输入 SHA-256 | 修复前确定性结果 |
|---|---|---|
| `plan_f1 / trial_003` | `a2ceb00bf82b8dc8470a6c75409cc6ab1e6d30ad399997b32fd06e309cb045d0` | `_reading_align` 在尺寸对齐中抛出 `StopIteration`。先移动一段轮廓后，相邻共线子段暂时变成斜线，`_segments` 不再返回其原索引。 |
| `plan_f1b / trial_002` | `13c7ffea0f0a2cbd3950e65c32b01df5eb22a0363f35b4557e8cd0c6d7d757b4` | 原始 `p_cor_s` / `p_rooms_e` 接头只差 `0.05 px`；墨线与尺寸规整后竖墙端点仍在 `y=582.6`，横墙移到 `y=587.5`，形成 `4.9 px` 脱接。 |
| `plan_f2b / trial_005` | `061329a3952d4d32c2e9d198707f9099c430370b2687bf20cdd7f092d79c3ad1` | 原始轮廓 edge 2 长 `13.8 px`；墨线把两侧竖边推向同一位置，尺寸对齐随后得到长度 `0` 的 edge 2，并触发 `footprint segment 2 is degenerate`。 |

这些重放均停在本地纯处理或严格预编译阶段，没有写入原运行目录。修复前另外存在的悬空墙、读图误差和其他 dangle 不属于本包，不能以本包消失或编译通过来宣称整层已修好。

## 实现

1. `move_straight_wall` 现在将由连续共线子段和重复顶点构成的同一轮廓侧作为整体移动。共享顶点不会只改一侧，因此规整不再自己制造斜边。
2. 墨线与尺寸对齐在逐边处理时使用显式查找失败回执。若输入或前序结果出现非正交边，会记录具体 edge 的 rejection，不再让裸 `StopIteration` 逃逸成 runtime unknown-write。
3. 每次轮廓移动前保存已有非零边的轴向、方向和长度。移动后必须保持正交、方向不反转、边不消失；原先达到 kernel `min_edge_length_m` 的有效边也不得被压到该下限以下。失败时整次边移动回滚并留下原因。
4. 墨线和尺寸移动墙线时，按预编译同一口径使用 `max(5 cm, 3 px)`、上限 `30 cm` 的逐轴物理容差识别近接头。随动只改变墙线移动的法向坐标，不扭斜相交墙；后续严格预编译仍负责其余接头修订。

没有减少声明对象，也没有更改房间 seed、opening host 或既有附着要求。轮廓移动仍须通过简单 polygon、无内环、对象在轮廓内、原有 partition/opening 附着保持等检查。

## 修复后原始声明重放

| 对象 | 修复后结果 | 保持项 |
|---|---|---|
| `plan_f1 / trial_003` | `_reading_align` 正常返回 `strict_compile_failed`，不再抛异常。 | 输出轮廓全部正交，Shapely polygon 有效；已有其他声明错误仍以可见严格编译失败保留。 |
| `plan_f1b / trial_002` | `p_cor_s` 为 `[287,587.5]→[696,587.5]`；`p_rooms_e` 顶端为 `[694.7508710801394,587.5]`，落在横墙范围内。 | 目标接头重新相交，所有 partition 仍正交；没有靠删除墙或放宽 dangle 检查通过。整层仍因其他原始缺陷返回 `strict_compile_failed`。 |
| `plan_f2b / trial_005` | edge 2 保持 `13.752 px`，零长轮廓边为 `0`；试图把它压到 kernel 最小边长以下的移动被拒绝并记录。 | 轮廓全部正交、polygon 有效；原有其他 dangle 仍使整层 `strict_compile_failed`，但不再报告本轮制造的 degenerate edge。 |

## 检查

新增 3 项缺陷回归：近接头随墙移动不被放大、含连续共线段和重复顶点的轮廓保持正交、有效短台阶不得被压到 kernel 最小边长以下。既有对齐测试与下游平面规整、分区、开口及角色提交相关检查一并执行。

```text
tests/test_plan_reader_alignment.py
18 passed

tests/test_plan_reader_alignment.py
tests/test_plan_regularization.py
tests/test_plan_partition.py
tests/test_plan_opening_integration.py
tests/test_role_compiled_plan.py
tests/test_role_plan_submission_short.py
tests/test_role_plan_revisions.py
127 passed
```

命令统一使用 `pytest -n 0 -p no:cacheprovider --basetemp <worktree>/AI_agent/archive/local_backup/kernel-repair-pytest`。`git diff --check` 通过；三个改动 Python 文件由 `compileall` 验证通过。主环境未安装 `ruff`，因此没有把 lint 结果冒充为已执行。

## 剩余风险

- 三份原始声明修复后仍严格编译失败，原因是本包外的原始悬空墙、读图或格式问题；本报告只证明三项 kernel 自造缺陷已被消除，不能外推为平面稿、整案或房间语义通过。
- F2 台阶得到保留，因为把它缩到 `0.10 m` 以下会违反当前 kernel 配置。台阶本身是否应由读图员删除仍是读图判断，kernel 不替代该判断。
- 本包没有运行 work model、角色小测或整案，因此真实行为和质量影响须由项目经理在后续已批准的小测中验证。
