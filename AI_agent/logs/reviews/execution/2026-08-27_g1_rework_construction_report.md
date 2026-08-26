# 返工施工报告 · G1：零豁免复现门

- **日期**：2026-08-27　**施工席位**：GPT 家族 sol
- **worktree**：`/tmp/ep_g1`　**分支**：`wt/08.27_gt_raw_layer`
- **开工自检**：HEAD `06dd513`；主树未触碰；禁区 diff 为 0
- **结论**：未命中停下上报触发器。ack/index 输入方案实测不削弱几何分辨力。

## 1. 做了什么

1. 删除 `_pointer_is_signature_dependent`、`SIGNATURE_DEPENDENT_POINTERS`、
   `HUMAN_REVIEW_GATE_IDS` 及整张豁免清单；复现结果不再过滤任何 JSON 指针。
2. 复现前重算 `review_index.files` 的规范摘要，核对
   `review_index.inventory_sha256 == review_ack.review_index_sha256`；再把已验证的
   `review_ack.json` 与 `review_index.json` 连同签字 DXF 一起复制进临时转换目录。
3. 晋升后的 `gt.json` 会合法改变 `verification` 与 `content_sha256`，所以其字节哈希不等于
   index 中的 candidate。复现门现在反解这两个允许变化并重算
   `candidate_gt_sha256`，证明其余语义（含 generator 指纹）仍来自签字 candidate。
4. `gates` 重键前检查 list 长度与唯一 id 数量；重复 id 响亮返回
   `content_mismatch`，指针为 `/gates`。
5. F-3 选择把 `vg_implementation_sha256` 升为 fatal。理由：它精确覆盖 correction 四件，
   复核实测四件全在转换 import 闭包且无闭包外噪声；extractor/validator 仍为 advisory。

## 2. R1–R8 逐条实测读数

| # | 实测读数 | 结果 |
|---|---|---|
| **R1** | 旧豁免符号 `rg` **0 命中**；未改动 sm25：`status='reproduced'`，`differing_pointers=()`；index 规范摘要 = index 声明 = ack 签值 = `49065597f8dac66d0c3d7eefe71633e9435abc0e430a6319c8d09c3b711d2019`。 | ✅ |
| **R2** | 边厚度 `0.12→0.13`：`content_mismatch`，只指名 `/zones/0/edges/0/thickness_m`。G6 首个 near-threshold face 的 `area_m2` `2.544→2.545`：`content_mismatch`，只指名 `/gates/G6/evidence/views/0/evidence/near_threshold_faces/0/area_m2`。 | ✅ 分辨力未退化 |
| **R3** | `converter_sha256` `539615abee77…→139615abee77…`：`status='implementation_drift'`，`drifted_fingerprints=('converter_sha256',)`，`differing_pointers=()`。 | ✅ 两种红分开 |
| **R4** | 在 `gates` 末尾追加一个重复 G1：`status='content_mismatch'`，`differing_pointers=('/gates',)`。 | ✅ |
| **R5** | 选择 **VG 升 fatal**。当前/签字 VG = `8e45fd15b4dfbae05492bdb60584ad722359ddcee0895fd7d2c202155c9d4a9d`；模拟当前实现首位漂移为 `1e45…`：`implementation_drift`，`drifted_fingerprints=('vg_implementation_sha256',)`，`differing_pointers=()`。 | ✅ |
| **R6** | 最终全量 `python -m pytest -q -n 6`：**3046 passed / 13 xfailed / 0 failed**，211 warnings，**498.25 s**。起点 commit 为 3042，本单新增 4 条测试。 | ✅ |
| **R7** | 见下节五次逐项 neuter；每次整份 raw-layer 测试均为 **1 failed / 10 passed**，且只红对应锁。 | ✅ |
| **R8** | 原 A1：zones **29**，edges **136**，basis `wall_axis 90 / outer_skin 46`，thickness `0.12×78 / 0.24×58`。原 A6：对原 7 条测试，摘 `_diff_pointers` ⇒ **1 failed / 6 passed**，仅 A3 红；摘 fatal 指纹判定 ⇒ **1 failed / 6 passed**，仅 A4 红。 | ✅ 原占位符已补真值 |

定向最终复跑：`tests/test_gt_raw_layer.py tests/test_gt_discipline.py` =
**23 passed / 0 failed**。

## 3. R7 neuter 逐条定向

| neuter | 整份 `tests/test_gt_raw_layer.py` 读数 | 唯一红项 / 错误退化 |
|---|---:|---|
| N1 摘掉临时目录中的 ack/index 复制 | 1 failed / 10 passed | 仅未改动树复现锁红；重新出现 **15** 个签字相关差异指针 |
| N2 不重算 `files` 规范摘要、只信 index 自报值 | 1 / 10 | 仅签字链篡改锁红；篡改 index 被错误放行为 `reproduced` |
| N3 摘重复 gate id 长度检查 | 1 / 10 | 仅 R4 红；重复 gate 被错误放行为 `reproduced` |
| N4 把 VG 降回 advisory | 1 / 10 | 仅 R5 红；VG 漂移被错误放行为 `reproduced` |
| N5 摘晋升件反解 candidate hash 校验 | 1 / 10 | 仅签字链篡改锁红；篡改 VG 的晋升件错降为 `implementation_drift`，而非签字链不可用 |

原 A6 独立补测：

- 内容比较 neuter（`_diff_pointers → []`）：原 7 条 **1 failed / 6 passed**，只红 A3；
  厚度篡改错误变为 `reproduced`。
- 实现漂移优先判定 neuter（`_fatal_fingerprints → []`）：原 7 条 **1 failed / 6 passed**，
  只红 A4；实现漂移错误归为 `content_mismatch`，指针 `/converter_sha256`。

所有 neuter 均以补丁临时施加并逐次恢复；恢复后的定向集与最终全量均为绿。

## 4. 文件与边界

- 修改：`src/agent/judge/gt_raw_layer.py`
- 修改：`tests/test_gt_raw_layer.py`
- 新增：本施工报告
- 未碰：`src/agent/pipeline.py`、`src/agent/reading/`、`src/validator/data_model.py`、
  `src/validator/checks/kernel.py`、`tests/test_f95_*`、`tests/test_f13_*`、任何 gt/签字产物、
  判分口径与容差。未跑 case，未产 reading/correction 产物。

## 5. 我认为最可能塌的地方

1. **最高概率仍是 request 可得性**：签字 request 只在
   `AI_agent/logs/experiments/**/request.json` 可找到；目录被清理时会响亮降级为
   `inputs_unavailable`，不会假绿，但复现门会失去可用性。
2. **晋升语义若将来扩展**：当前反解锁只允许 promotion 改 `verification` 与
   `content_sha256`。未来合法 promotion 若新增可变字段，本门会 fail closed 为
   `inputs_unavailable`，需要同步升级，不会静默放行。
3. **仍有已声明归因盲区**：`gt_extraction.py`、`gt_manifest.py`、`gt_schema.py`、
   `tarch_converter_schema.py` 在转换闭包内但没有精确签字指纹；它们的漂移会被响亮抓为
   `content_mismatch`，但归因仍可能不是 `implementation_drift`。
4. **单 case 证据**：所有复现与篡改实测集中在 `sm25-L_anchor`。
