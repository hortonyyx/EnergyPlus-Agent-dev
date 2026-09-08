# 2026-09-08e 补窗归档：WIP 与停报

状态：**未完成验收，按派工单「题错停报」停止后续施工。**

工作目录 `/tmp/w1_windows_claude`，分支 `wt/09.08_windows`，起点
`7c61cb97a58698d4aa3e613a58795e4b68d4a4f2`。完整读过派工单；正文旧基点
`c7513af9` 由用户本轮明确指定的 `7c61cb97` 覆盖。

代码 WIP 已先提交：`5ff0e8c1`。只暂存两个明确路径，commit 前已查看
`git diff --cached --numstat`：

```text
14  12  src/agent/correction/chain_replay.py
30   0  tests/test_w3_chain_replay_lock.py
```

## 一、停报：你以为是 X，实际是 Y，证据是……

### 1. producer 对齐之后，还有归档器与重放返回阶段的结构冲突

你以为有窗候选的归档剩下的是 producer 字节重建差异；实际 producer 已可以完全相等，
但归档器仍把 **as_drawn 的 finalize 后状态** 当成 **宿主解析前状态** 使用。

证据来自真实编译、投影、造窗、finalize 和 `StageRunner.record`，只固定模型决策：

- `chain_replay.py:299` 返回 `finalize_as_drawn_chain_geometry(...)`，其中已经执行
  `apply_window_host_resolutions`，追加了 31 条 `window_host_resolution`。
- `stage_runner.py:369` 取该结果的 `.geom`；`:434` 把它的 corrections 全部作为
  候选 corrections 必须保留的前缀。
- 实测候选 corrections = 31，重放 corrections = 31，两者都是宿主解析记录。
- `stage_runner.py:480` 算出的候选后缀长度为 **0**；`:481` 要求它等于
  `audit_rows` 的数量 **31**。即使修好下面的类型差异，仍是 `0 != 31`。
- 后续逐窗审计也把 `replayed.windows` 作为解析前的 original 值来源；因此不能只
  改一个后缀长度判断来放行。

当前最先报错的是 `stage_runner.py:436 writer_core_projection_drift`：逐字段 diff
还发现 **62 处纯容器类型差异**。每条 corrections 的 `source_ids`、`tolerance_names`
在已归档字节重新加载的候选中为 `list`，在内存重放中为 `tuple`，元素及顺序相同。
来源是 `window_host.py:1062` 的 `audit.model_dump()`，以及候选的 JSON 往返。

这不意味着两份 producer 结构上无法一致——它们已实测一致；冲突发生在之后的
writer 输入阶段约定。下一步需要明确：as_drawn writer 用哪个经过重放认证的
宿主解析前状态核验 original/prefix，又如何绑定 finalize 后的候选。
本次没有调整 writer 的比较、删除审计条目或跳过 gate。

### 2. 任务 B 的空 corrections 前提已经过时，当前是错误依赖声明被宿主记录掩盖

你以为 `_make_draw_fn` 的 `relied=True` 与 as_drawn finalize 的空
corrections/conflicts 正在导致审计报错；实际补上窗之后，finalize 会生成
**31 条 corrections、0 条 conflicts**。

在冻结的 `run_win_e2e` 输入上调用生产 `_draw_correction_as_drawn`，显式保留
`relied=True`，实测返回：

```json
{
  "check_id": "correction.audit_completeness",
  "status": "pass",
  "evidence": {"audit_entries": 31}
}
```

`run_stage.py:1217` 的 `relied = td_path.exists()` 仍然存在；as_drawn 几何构造没有
接收 testdata_text，expected_zones 仅进入结果检查。故「文件存在等于几何依赖」仍是
错误声明，只是当前宽泛的审计条目检查被宿主记录满足了。不能把这次 pass 报作 B 已修复，
也不能伪造一条 correction 来代表不存在的 testdata 改写。

当前归因到 0_reading 的载体可查：marker 内冻结的 reading 字节与身份哈希、
`chain_provenance` 的逐层编译/源字节绑定、窗的逐字段 provenance，以及宿主解析审计。
它们的含义不同于「根据 testdata 修正了 reading」。本次未修改 B 的实现。

## 二、已完成的 producer 逐字段定位与 WIP 修复

诊断在仓库外的临时脚本中进行，复制 `run_win_e2e` 到临时目录；没有改动用户已有的
运行目录。生产 `_draw_correction_as_drawn` 仍执行真实多层协调、造窗、marker、finalize
与检查；仅把每层链的模型阶段替换为读取既存投影产物，协调继续读取其冻结 cut_lines
和 compilation。重放从 marker 与 provenance 的冻结输入独立推导。

修复前完整递归 diff 共 **31 处**，全部为 `$.windows[i].floor`，无其他字段差异：

| 下标 i | 生产 marker | 重放 |
| --- | --- | --- |
| 0, 3, 5, 7, 8, 10, 11, 13, 15, 17, 19, 21, 23, 28, 29 | `"1f"` | `null` |
| 1, 2, 4, 6, 9, 12, 14, 16, 18, 20, 22, 24, 25, 26, 27, 30 | `"2f"` | `null` |

两边 windows 长度都为 31。`populate_as_drawn_windows` 用 `model_copy(update=...)`
填窗，没有重新执行全模型校验。生产 marker 的 `_assemble_verified_resolver_inputs`
会运行 `CorrectedGeometryV3.model_validate`，通过 `_v3_integrity` 从 floor_id 补齐
window.floor。重放原来在执行这一构造前就比较字节。

WIP 把重放已有的 marker 构造移到字节比较之前，从 **独立重放的 producer** 构造 marker，
再比较它的完整 `producer_draw_canonical_bytes`。没有读取候选 producer 来代替推导，
没有排除字段或允许误差，`!=` 拒绝仍保留。另移除了函数内遮蔽顶部导入的
`load_core_tolerances`，造窗使用本次 replay 的同一 tol。

实测 SHA-256：

```text
生产：      76844ad7235e86e9bf747e4d7a00c03b649b2d1b989bc2f381dd2235ef6539b2
修复前重放：3f4aeb4fe1436c465a5d32786769a09b69f1db68975036ecc668597dff9c2b0f
修复后重放：76844ad7235e86e9bf747e4d7a00c03b649b2d1b989bc2f381dd2235ef6539b2
```

修复后的 producer 差异数 = 0；直接比较两边 finalize 结果的 JSON 字段，差异数也为 0。
后者不等于通过 writer：writer 比较的是 JSON 加载后的候选与内存重放，且要求解析前后
审计前缀/后缀的阶段关系，如上所述。

W3 测试夹具补上生产同一个造窗步骤，增加归档 `output.json` 的 windows = 31 与
floor 名称断言。它现在诚实暴露 writer 的下一处失败，没有把无窗归档当作成功。

## 三、跑测与验收读数

全部使用 `/opt/venv/bin/python`；没有运行 `uv run`，没有同步共享环境。

```bash
cd /tmp/w1_windows_claude
PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -m pytest -n 6 -q tests/test_w3_chain_replay_lock.py tests/test_w1_flow_routing.py tests/test_w7_as_drawn_windows.py
# 修改前：12 failed, 16 passed in 7.29s

PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -m pytest -n 6 -q tests/test_w3_chain_replay_lock.py tests/test_w7_as_drawn_windows.py
# WIP 后：11 failed, 6 passed in 7.55s
```

两次选择的测试集不同，不能据此声称少了一个失败。WIP 后 7 个 W3 测试都在建立
有窗候选的共同前置归档处报 `writer_core_projection_drift`；各自后续的篡改断言尚未到达，
故不能声称这些拒绝回归已经验证通过。另外 4 个 W7 失败在基线已存在，夹具仍使用
`snap_footprints_to_reference` 只替换 ring，导致二层 cells 与 ring 不共享边界，
报 `n_cells_matched: 0`。W1 的基线失败使用合成小楼几何配真实窗源，也尚未处理。

`git diff --check` 通过。完整测试套件未运行；因题目前提变化停报，未进入全量前的 B
提交触发点。开始写本交件之前已完成代码 WIP 提交，满足阶段切换及 C 触发点。

**指定验收文件**
`case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/1_correction/attempts/001/output.json`
**仍不存在**。因此它的 windows 长度没有可报告读数；本次离线复现的 31 不冒充
生产 flow 归档验收。没有启动新的带凭据 flow，也没有修改或暂存已有的未跟踪运行目录。
临时诊断脚本和输出用完删除，证据摘要保存在本交件中。

## 我这次最薄弱的一处

我验证了冻结输入上的 producer 全字段一致，并把新的归档冲突定位到了具体字段和
前后阶段约定，但尚未交出完整的有窗归档修复。修复后测试仍红，B 未改，全量与带凭据
flow 未跑；当前提交只能作为可审阅的 WIP，不能作为验收通过或字节锁全部回归通过的证据。
