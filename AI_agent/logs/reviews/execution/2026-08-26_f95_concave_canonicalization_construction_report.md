# F-95 顶点规范化毁凹多边形 · 施工报告

- 日期：2026-08-26
- 施工席位：GPT 家族
- worktree：`/tmp/ep_f95`
- HEAD：`d91eb99`（detached HEAD）
- 状态：**施工完成，未 commit / push**

## 1. 开工与路径自检

```text
/tmp/ep_f95
d91eb99
# 多模态输入 Agent 项目管理文档

> **本文件 = 项目最基础的根文件**，每次会话/换主控模型时首加载，作用是**简要说明项目结构 + 当前开发状态**。
AI_agent/logs/reviews/request/2026-08-26_f95_concave_canonicalization_dispatch.md
/tmp/ep_f95/src/validator/data_model.py
```

`src.validator.data_model` 全程从本 worktree 解析，未从主树解析。

## 2. 缺陷独立复现（修前）

因原矩阵脚本硬编码主树路径，没有原样运行它；改用 cwd 位于 `/tmp/ep_f95` 的 `python - <<'PY'`，并在同一进程打印模块来源。结果：

| 形状 | 顶点 | 修前面积 | 规范化后面积 | 输出 valid | 顶点集 | 结论 |
|---|---:|---:|---:|---|---|---|
| 矩形 | 4 | 80.000 | 80.000 | True | 相同 | OK |
| 单凹角 L | 6 | 84.000 | 84.000 | True | 相同 | OK（假绿控制） |
| U | 8 | 76.000 | 70.000 | True | 相同 | **CORRUPTED** |
| Z | 8 | 68.000 | 68.000 | True | 相同 | OK（极角单调凹形） |
| 梳形 | 12 | 66.000 | 59.000 | True | 相同 | **CORRUPTED** |
| sm25 走廊 | 14 | 97.731 | 226.457 | True | 相同 | **CORRUPTED** |

独立复现与派工读数一致。损坏后多边形仍 `is_valid=True`；变的是边邻接与面积，不是顶点集。

## 3. 实现

### 3.1 单一共享规范化实现

`src/validator/data_model.py::canonicalize_ring_vertices` 现明确接收**有序简单平面环**：所给顺序就是权威边邻接，只允许：

1. 用环的 Newell 等价法向与 `normal_vector` 点积决定是否整体反向；
2. 循环旋转到 `top_left_corner_index` 给出的 `UpperLeftCorner`。

两步都保持顶点集合和无向边集合，且不再按质心极角重排。函数 docstring 已删除不可能兑现的 `any input order, including scrambled / self-intersecting` 承诺，并写明有序简单环合同与不可从点集猜邻接的原因。

kernel 与 validator 仍共用这一个函数：

- `src/agent/geometry/build.py` 对 surface/window 调用它；
- `GeometrySchema._sort_vertices_clockwise` 委托它；
- `src/validator/checks/kernel.py` 的独立窗重算同样调用它。

没有拆出第二套排序/规范化算法，F-13 单一实现不变量保留。

### 3.2 非简单环响亮拒绝

按给定法向选择稳定二维投影（丢弃法向绝对值最大的坐标轴），检查所给环是否简单。自交、重复点、零面积等非简单输入抛 `ValueError`，稳定错误名前缀为：

```text
canonicalize_ring_vertices.non_simple_ring
```

蝴蝶结实测上下文：

```text
canonicalize_ring_vertices.non_simple_ring: ordered simple ring required
(vertex_count=4, reason='Self-intersection[1 1]')
```

非法零向量另用 `canonicalize_ring_vertices.invalid_normal` 响亮拒绝。

### 3.3 F-13 文字合同同步

F-13 四份合法矩形夹具的变量由误导性的 `scrambled` 改为 `ordered_different_start`；只改命名，不改输入或断言。`data_model.py`、`build.py`、`checks/kernel.py` 中仍称“重新推导 ring order”的旧说明也已改为“保持邻接，仅规范绕向与起点”。

### 3.4 离线矩阵装机路径

`concave_canonicalization_matrix.py` 删除硬编码 `/workspaces/EnergyPlus-Agent-dev`，从脚本自身位置推导 repo root，并在导入后断言 `src` 文件位于该 root。标准运行方式改为从 worktree 根执行 `python -m ...`。

## 4. 扩充后的夹具矩阵全表（修后）

命令：

```bash
cd /tmp/ep_f95
python -m AI_agent.logs.experiments.2026-08-25_kernel_probe_from_gt.tools.concave_canonicalization_matrix
```

模块来源：`/tmp/ep_f95/src/validator/data_model.py`。

| 形状 | 顶点 | 输入面积 | 输出面积 | 顶点集 | 边集 | 绕质心极角单调 | 结果 |
|---|---:|---:|---:|---|---|---|---|
| 矩形 | 4 | 80.000 | 80.000 | same | same | True | OK |
| 单凹角 L | 6 | 84.000 | 84.000 | same | same | True | OK |
| U | 8 | 76.000 | 76.000 | same | same | False | OK |
| Z | 8 | 68.000 | 68.000 | same | same | True | OK |
| 梳形 | 12 | 66.000 | 66.000 | same | same | False | OK |
| U（反向绕向） | 8 | 76.000 | 76.000 | same | same | False | OK |
| U（不同起点） | 8 | 76.000 | 76.000 | same | same | False | OK |
| sm25 走廊 | 14 | 97.731 | 97.731 | same | same | False | OK |
| 自交蝴蝶结 | 4 | — | — | — | — | — | **按预期 REJECT** |

矩阵末行：

```text
all ordered simple rings preserved; non-simple ring rejected
```

Z 是明确的“极角单调但凹”夹具；U、梳形和 sm25 是真正能抓 F-95 的极角非单调夹具。

### 为什么不存在“极角非单调但凸”的合法夹具

对任意非退化凸多边形，全部顶点的算术平均是所有顶点的严格正权凸组合，因此位于多边形内部。从一个凸多边形内部点发出的每条射线只在边界上离开一次；沿边界连续走一圈时，射线方向也只能单向转一圈（换起点只改变 `2π` 断点，换绕向只改变单调方向）。因此顶点绕该内部质心的极角必单调；连续共线边界点也不会制造反向角步。故不存在满足题意的非退化凸简单多边形。

## 5. 乱序点集：拒绝还是不可判别

结论分两层：

1. **所给顺序形成自交/非简单环**：可判别，现实现响亮拒绝。
2. **某个“相对未知原形为乱序”的排列碰巧又形成另一个简单环**：不可判别。实测把 U 的同一顶点集按质心极角排列，所得环仍 `is_valid=True`，但面积为 70 而不是 76。没有外部原始边邻接时，系统无法知道 70 面积的合法简单环“本来想表达”76 面积的 U。

因此合同以**所给顺序为权威邻接**：非简单顺序拒绝；形成简单环的顺序按它实际描述的环接受。全仓生产调用方都提供有序环，所以不需要新增拓扑信任根。

## 6. 新锁与红/绿分辨力

新增 `tests/test_f95_concave_canonicalization.py` 六把锁。用 fresh Python 进程把共享函数及 kernel 引用变异回修前质心极角算法，运行整份新测试；结果为 **4 failed / 2 passed**。恢复新实现后为 **6 passed**（也包含在后续子集与全量中）。

| 锁 | 修前变异读数（红） | 修后读数（绿） | 红方向是否正确 |
|---|---|---|---|
| U 共享函数面积/顶点/边 | 面积 `70 != 76` | 面积 76，顶点/边相同 | 是：直接命中形状损坏 |
| 真实 kernel Floor/Roof | 生产路径读到 `65 != 76` | Floor/Roof 均 76、8 顶点、边相同 | 是：命中真实调用路径；旧非传递比较器还会随起点产生不同坏形 |
| 自交蝴蝶结拒绝 | `DID NOT RAISE` | 按稳定错误名拒绝 | 是：命中收窄后的输入合同 |
| 同一 U 的双绕向/不同起点收敛 | 三份 canonical 输出不相等 | 三份逐数组相等且边集不变 | 是：旧比较器对起点/绕向不稳定 |
| 独立绕向证明 | PASS | PASS | 非 F-95 discriminator；专锁既有绕向合同 |
| 独立 UpperLeftCorner 证明 | PASS | PASS | 非 F-95 discriminator；专锁既有起点合同 |

修前 U 的 70→76 失败方向与独立复现完全一致；production 变异的 65 进一步暴露旧 `cmp_to_key` 比较关系并非全序，同一顶点集在不同输入起点下会得到不同坏形。这些锁不是 `test_lshape_polygon_clean` 那类假绿。

## 7. 两条既有契约的独立证明

### 7.1 绕向与 `normal_vector` 一致

`test_winding_contract_is_independently_observable_on_concave_ring` 输入原本朝 `+Z` 的 U 环，要求法向 `DOWN=(0,0,-1)`。测试用独立实现的闭环叉积和重新求环法向，并断言规范化后与 `DOWN` 点积严格大于 0；该输入必经整体反向，不依赖被测函数内部状态。

### 7.2 起点为 UpperLeftCorner

`test_upper_left_contract_is_independently_observable_on_concave_ring` 将同一 U 环滚动到另一顶点开始，要求 `UP=(0,0,1)`。对向上水平面，观察坐标手算为 view-up=`+Y`、view-right=`+X`，所以左上角唯一是 `(0,10,0)`；测试直接断言输出首点等于该手算值，没有调用 `top_left_corner_index` 生成期望。

F-13 的垂直墙、Floor、Ceiling/Roof、Window 四类既有合同锁也继续全绿。

## 8. 测试输出

### 8.1 F-13 强制停下门

```text
tests/test_f13_kernel_canonical_vertex_order.py
8 passed in 9.75s
```

### 8.2 F-95 + F-13 + geometry kernel 首轮

```text
23 passed in 11.36s
```

### 8.3 扩宽受影响集

覆盖 F-95、F-13、geometry kernel、checks kernel、B5 parent/verts、kernel guards、pipeline kernel wiring、surface/fenestration converter：

```text
136 passed in 13.32s
```

### 8.4 全量

命令：`cd /tmp/ep_f95 && python -m pytest -n auto`

```text
1 failed, 3034 passed, 13 xfailed, 211 warnings in 359.80s (0:05:59)
```

唯一失败：

```text
tests/test_zone_agent.py::test_zone_agent_creates_two_zones
openai.OpenAIError: The api_key client option must be set ...
```

这是派工单预先声明的缺 `OPENAI_API_KEY` 环境红项，与 F-95 无关。其余 3034 项通过。

### 8.5 静态检查

- `git diff --check`：通过。
- `python -m py_compile`（全部改动 Python 文件）：通过。
- 环境未安装 ruff：`/opt/venv/bin/python: No module named ruff`；遵约未安装依赖、未改 `/opt/venv/**`。

## 9. 本单派工方错在哪里

本轮第 35 条成立：派工单一方面提示“输入本来就是有序环，只需反向+旋转”，另一方面要求“规范化前已自交的乱序输入”在无损矩阵中全绿；更深处是现函数 docstring 还白纸黑字承诺 `any input order, including scrambled / self-intersecting`。仅凭无邻接点集不可能唯一恢复任意凹多边形，该书面合同本身不可实现。

另有两处已一并修正：现成矩阵硬编码主树导入路径，违反独立 worktree 验收；矩阵旧说明称“除 L 外全坏”，也与矩形/Z 的实际 OK 读数矛盾。

派工方后续拍板把合同收窄为“有序简单环；非简单环响亮拒绝”，且已核实全仓生产调用方无人依赖旧虚假承诺，本施工据此完成。

## 10. 改动清单与范围审计

- `src/validator/data_model.py`：共享保序规范化、非简单环拒绝、契约文档。
- `src/agent/geometry/build.py`：同步共享实现说明；调用关系不变。
- `src/validator/checks/kernel.py`：同步共享实现说明；调用关系不变。
- `tests/test_f95_concave_canonicalization.py`：F-95 六把新锁。
- `tests/test_f13_kernel_canonical_vertex_order.py`：四个合法环夹具变量正名。
- `AI_agent/logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py`：路径修复与矩阵扩充。
- 本报告。

未碰 `src/agent/judge/**`、`src/agent/pipeline*`、`state.py`、`src/agent/correction/**`、gt、配置容差或 `/opt/venv/**`；未运行 case；未 commit / push / stash / 切分支。
