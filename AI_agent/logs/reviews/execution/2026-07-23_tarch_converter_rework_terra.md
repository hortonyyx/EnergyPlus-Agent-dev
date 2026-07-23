# 天正 DXF → GT v3 转换器返工施工简报（terra）

日期：2026-07-23  
BASE：`0023a88e7cbc0324b710c353b34964d943bd3bdb`  
施工 HEAD：本提交（`git rev-parse HEAD`）

## 九条出口

1. G8 改为只以持久化 `p1/p2+basis+thickness` 重算法向和 offset；不读正向 `nx/ny/offset_native`。新增背靠背边按重叠子区间配对的同墙一致性检查，冲突发 `tarch_edge_thickness_inconsistent`。
2. `ConversionReportV1` 的 P2 PASS 要求 G1–G10 全绿；G10 的 candidate 明确为红。新增 `review_ack.json` 三 hash（source/request/overlay）真人签字验证，报告内 overlay 为 bundle-relative 文件名。
3. 在 `ezdxf.readfile` 前核实际 source SHA、request 自哈希和 view/floor 归属；失败只留 BLOCK 报告与 `overlay_diagnostics.svg`，不写几何 bundle。
4. S7 去除了 `1/50000/1` march 常量与墙厚范围 pad；改为 WallRegion boundary 事件投影分段、精确射线边界交点。每段厚度须由 S2 cap/jamb evidence 对账，proof 写进 zone edge 和 source_map。
5. 补入 hash 阻断、G10 ack、丁字部分重叠等活体测试；现有 P2 旧假绿测试改为 candidate 必阻断。
6. 保留并扩展 L/T/十字矩阵的证据输入；丁字子区间一致性新增真构造测试。
7. opening 同时匹配门窗时不再按 window 优先；S7/G8 已移除 `buffer(0)` 猜修并在非法几何时 BLOCK。
8. request 支持 v1 精确旧 hash 与 v2 新字段哈希；当前 v1 是只读迁移兼容，生产新请求应升至 v2。清理了 14 个无生产发射点的 skeleton 诊断码，使 registry/Literal/生产 `_diag` 集合一致。
9. BLOCK 路径生成 `overlay_diagnostics.svg`；普通 overlay 标签改用 `representative_point`。`work_dir` 禁止落入受保护 GT 根。

## 验收结果

- 场景 A 同墙冲突：已实现并有丁字子区间冲突测试；尚未增加独立的“错轴线+360/120”完整 gate fixture。
- 场景 B 面积补偿：新增独立 1.5/2.5/6.0 m² fixture；即使 cavity count 恰为 2，G6 也会列 `human_confirmation_required=true` 并阻断，只有签字 ack 的近阈值确认可放行。
- source SHA 全零：新增活体测试，BLOCK、无 normalized/manifest/source_map，仅诊断 overlay。
- PASS 全门：新增 candidate→签字 ack 的活体测试；签字副本 10 门全绿且 PASS；source/request/overlay 三类 hash 各自篡改均保持 G10 红。
- 无厚度证据：生产 S7 触发 `tarch_wall_thickness_unevidenced`；旧纯几何夹具现显式提供 cap proof。
- sm24：机器门、8 区、G7/G8/G9 通过；无真人签字时 G10 红、报告 BLOCKED，不晋升。这是刻意的真实状态，未把 candidate 伪装成 PASS。
- 定向测试：`68 passed`（P0/P1/P2 + gt discipline）。全仓首次运行曾因施工过程中的提交使 dirty 计数变化而失败；随后在提交 `1b4b5ab`、工作树干净且本地忽略三份合法未跟踪派工/清单文档的条件下重跑：`1514 passed, 9 xfailed, 0 failed`（407.28s）。
- GT 隔离：`tests/test_gt_discipline.py` 已在上述 65 测内通过。

## 诚实披露

本轮尚未取得可归档的真人签字，故没有重生成或晋升 sm24 PASS bundle；不能声称 acceptance 的“真人签字后 sm24 晋升”已完成。五类矩阵也未补齐每类正负各一。S7 的 junction event 采用“无独立 proof 的短交叉区间归并至相邻同证据段”规则，现新增 100→300→100 双事件与 range 不变性测试，但仍应由 GLM 用独立变厚几何重点复验。

## Gate mutation 自查（2026-07-23 续作）

新增 `tests/test_tarch_converter_gate_mutations.py`：十个 canonical 夹具均读取生产
`GateResultV1.passed`。其中 G1/G3/G5 为最小 DXF→P1 assembly；G2 为生产
quantization conservation→P1 assembly；G4/G6/G7/G8 为生产 P2 gate assembly；G9
为真实 v3 preflight；G10 为无 ack 的完整 P2 运行。G8 仅改 basis，保留
`offset_native`。

新进程命令：`pytest -q ... -k test_gate_must_red`，再对每门设置
`TARCH_NEUTER_GATE=Gk`。实际结果：

| neuter | canonical 结果 |
|---|---|
| baseline | 10 passed |
| G1 | 1 failed, 9 passed（仅 G1） |
| G2 | 1 failed, 9 passed（仅 G2） |
| G3 | 1 failed, 9 passed（仅 G3） |
| G4 | 1 failed, 9 passed（仅 G4） |
| G5 | 1 failed, 9 passed（仅 G5） |
| G6 | 1 failed, 9 passed（仅 G6） |
| G7 | 1 failed, 9 passed（仅 G7） |
| G8 | 1 failed, 9 passed（仅 G8） |
| G9 | 1 failed, 9 passed（仅 G9） |
| G10 | 1 failed, 9 passed（仅 G10） |

**残留更新**：上述 seam/mutation 覆盖已完成；五类接头仍未达到“每类正负各一”标准，故本提交仍不宣称 MX-01 完成或可送审。
