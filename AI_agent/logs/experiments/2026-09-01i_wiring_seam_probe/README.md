# 探针 · 接线缝的真实状态（2026-09-01 · orchestrator）

**目的**：给「接线单」核实前提。派工单里的每个前提必须是**我自己量过的**，
⛔ 不是从 banner 或设计稿转引（同族 [[citing-someone-elses-fact-does-not-transfer-responsibility]]）。

- **树**：`08.23_AsDrawnReading` · HEAD `1303e8a` · 工作树干净
- **导入自证**：`evidence_adapters.__file__ = /workspaces/EnergyPlus-Agent-dev/src/agent/correction/evidence_adapters.py`
  （⭐ 承重不变量按 [CLAUDE.md §5#8.6](../../CLAUDE.md)，`.pth` 哈希只是代理量）
- **输入**：`case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/0_reading/1f_view.json`（真实产物，68155 bytes）
- 逐行输出 → [`probe_output.txt`](probe_output.txt)

## 一、量到了什么

| 环节 | 实现 | 真实 sm25 上的读数 |
|---|---|---|
| ① `adapt_legacy_reading_view` | ✅ 在 | **22 条 wall_claims** |
| ② `compile_wall_ir` | ✅ 在 | **22 堵墙 / 22 条待裁决**（全部 `legacy_basis_unknown`）· `completion=degraded` · 4 条残余债 |
| ③ `build_decision_packet` | ✅ 在 | 出包成功，`packet_hash=e5cf8afd…` · 22 待裁决 · 44 条 entity→source · 2 条一致性结果 |
| ④ 模型那一拍 | ⛔ **零实现** | 全仓没有任何提示词产出 `CorrectionDecisionResponseV1`；`run_decision_loop` 今天只被夹具喂 |
| ⑤ 投影桥 | ⛔ **零实现** | `CorrectedGeometryProjectionEnvelopeV1`（已过审设计稿 §5.4）全仓 `grep` 零命中 |

## 二、⭐ 三条结论（都改写了 banner 里的说法）

1. **「接线」不是翻一行开关，但也远没有 banner 说的那么空** —— 五步里**前三步今天就在真实 sm25 上跑通了**。
   缺的是**明确的两块**：模型那一拍 + 投影桥。
2. **新链在生产侧零消费者**：`grep` 全仓 `src/` + `scripts/`，
   `evidence_contract|evidence_adapters|wall_compiler|decision_schema|decision_executor` **只被 `tests/` 引用**。
   `pipeline.py:452` 至今是把识图 JSON 原文贴进提示词。
3. ⭐ **喂料现状**：`case_tests/` 下 **368 份 `*_view.json` 全是旧格式**（`strokes`）；
   新格式（`as_drawn_plan`）产物全仓**只有实验目录里 sm24 一层**。
   ⇒ 今天要端到端，**只能走 legacy adapter**（设计稿 §9.1 第 7 步「新旧源都走 bundle」正是这么写的），
   拆旧腿是**后面另一单**（guide §十之二 第 4 条：拆单排在模块 5/6 之后，且要新格式夹具顶上）。

## 三、⛔ 这次探针【没有】证明什么

- ⛔ 没证明 ④⑤ 做完就能端到端 —— 后面还有确定性核、几何内核、judge 一整段没走过。
- ⛔ 没证明 `degraded` / 22 条 `legacy_basis_unknown` 是**对的**读数；它只说明**链路通、且响亮地报告了自己的残缺**。
- ⛔ 只跑了 sm25 的 `1f` 一张图，⛔ 不是整个 case。
