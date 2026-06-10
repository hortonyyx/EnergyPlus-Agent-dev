# Review request — 0–5 管线完整体检（找硬伤）

- **创建**：2026-06-10（Opus 4.8 主开发）
- **执行者**：Fable 5（交叉模型审阅，预计 2026-06-11 接手）
- **类型**：full-pipeline audit（机制级硬伤排查，**不是** capability 升级）

---

## 1. 目标

在 **smalloffice_20**（3 层）和 **smalloffice_21**（2 层）两个案例上，把 **0–5 阶段管线**完整跑一遍，确认它能**稳定、无错地端到端跑通**，并找出任何**硬伤**——即机制级 / 正确性级缺陷（会导致崩溃、产出错误几何、契约违背、门误判/漏判、EP 失败的问题）。

**明确区分**：
- ✅ **本 audit 要找的**：硬伤（bug、契约缺口、门盲区、坐标/尺寸错误、跨案例不一致、崩溃、EP fatal/severe、确定性环节的逻辑错误）。
- ❌ **本 audit 不要做的**：6 个子环节各自的 capability 升级建议（识别精度、zonification 粒度、MEP 先验丰富度等）。这些**先不管**，但若顺手发现，请记到配套文档 [`pipeline_0-5_capability_upgrade_suggestions.md`](../../architecture/pipeline_0-5_capability_upgrade_suggestions.md)（见 §6），不要在本 audit 里展开修。

## 2. 背景（2026-06-10 当天进展）

今天三个 commit（都在 `main`，未 push）：
- `04e7dbe` 确定性 schedule 完整性门（[src/validator/schedules.py](../../../src/validator/schedules.py)）——根因：不完整 `Schedule:Compact`（漏 `AllOtherDays`）让容器 EP 25.1.0 **段错**（之前误判为"环境问题"）。
- `fd3d4bf` 1_correction 稳定性硬化（[src/agent/pipeline.py](../../../src/agent/pipeline.py) `_call_json_llm` 重试 + 窗完整性自检）——根因：sm21 "0 窗" **不是内核 bug**，是 1_correction（DeepSeek）偶发抽风（漏窗 / 非法 JSON）。
- `5e2f881` 新增 sm23 案例（单层，已 EP 跑通）。

**已知状态**：
- **sm21**：今天端到端实证跑通 —— 14 区 / 100 面 / 15 窗 / InterZone `pair_issues=0` / **EP Completed Successfully, 0 severe**。算干净 anchor。
- **sm23**：单层，EP Completed Successfully（0 severe），但 zonification 粒度有瑕疵（走廊被切两段、南排粗分）——属 capability，不在本 audit。
- **sm20**：3 层，0–5 重构后**尚未在新架构验证过**（它的 `0_reading/` 是较早的矢量，schema 兼容性本身就是一个 audit 点）。**这是本次重点。**

## 3. 审阅范围（六环节 + 装配 + 门 + EP）

权威接线见 [architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)。逐环节体检：

| 阶段 | 模块 | 硬伤关注点 |
|---|---|---|
| 0_reading | （半人工矢量，已存盘）| sm20 旧 schema 与当前 `0_reading/guide.md` 是否兼容；矢量是否被 1_correction 正确消化 |
| 1_correction (LLM) | [pipeline.py](../../../src/agent/pipeline.py) `run_correction` | 稳定性（重试是否够；窗自检是否误判/漏判）；坐标归一/规范化是否引入错误；2 层/3 层的 z 分层合成 |
| 确定性核 | [correction/deterministic.py](../../../src/agent/correction/deterministic.py) | 栅格吸附是否破坏真实几何；碎片守卫；窗钳制 |
| 2_modelling | [geometry/modelling.py](../../../src/agent/geometry/modelling.py) `build_zone_volumes` | cell→体块；同层 cell 重叠守卫；造面正确性 |
| 3_split_pairing | [geometry/split_pairing.py](../../../src/agent/geometry/split_pairing.py) | 互逆配对；跨层切分；面积/法向/共面 |
| 几何序列化 | [geometry/specs.py](../../../src/agent/geometry/specs.py) | surface/窗序列化；0 窗时的显式声明；construction 词汇表接缝 |
| 4_mep (LLM) | [pipeline.py](../../../src/agent/pipeline.py) `run_mep` | schedule 完整性（现有门兜底）；material↔construction split；契约引用完整 |
| 5_intakeoutput | [intakeoutput.py](../../../src/agent/intakeoutput.py) | 装配；`validate_contract`（逐 token 查 construction 定义）是否有漏 |
| 下游装配 + 门 | [mcp/tools/workflow.py](../../../src/mcp/tools/workflow.py) + [validator/interzone.py](../../../src/validator/interzone.py) + [validator/schedules.py](../../../src/validator/schedules.py) | InterZone 门盲区（同立面误配、覆盖洞）；schedule 门；窗挂错宿主墙 |
| EP | [runner/runner.py](../../../src/runner/runner.py) | EP fatal/severe；warning 是否都无害 |

## 4. 怎么跑

每个案例（在容器内，DeepSeek 走全局 `src/configs/llm.yaml`）：

```bash
# sm21（已知能跑通，作对照基线）
python scripts/run_full_pipeline.py smalloffice_21 \
  --base-dir test_data/SmallOffice_TwoStep --reading-from 0_reading \
  --output-subdir output_fable_audit

# sm20（重点：3 层，新架构首验）
python scripts/run_full_pipeline.py smalloffice_20 \
  --base-dir test_data/SmallOffice_TwoStep --reading-from 0_reading \
  --output-subdir output_fable_audit
```

- 中间产物落 `<case>/output_fable_audit/pipeline_out/{1_correction,2_modelling,3_split_pairing,4_mep,5_intakeoutput}/`，IDF + EP 产物落 `<case>/output_fable_audit/`。
- 1_correction 是长 DeepSeek 调用（thinking-on，2–6 分钟），后台跑。
- 容器 EP = `25.1.0`（`.env` 的 `ENERGYPLUS_EXE`），runner 传 `-x`（ExpandObjects，IDF 含 HVACTemplate）。
- 注意 1_correction 的随机性：若某次抽风，重试应兜住；如果反复失败，记录现象（这本身是稳定性数据点）。

## 5. 验收标准

1. **sm21 + sm20 各自端到端跑通**：InterZone 门 `pair_issues=0`、schedule 门 0 issue、EP `Completed Successfully` 0 severe；或**精确定位**阻塞它的硬伤（落到哪一阶段、什么根因）。
2. 产出**硬伤清单**（分级 High/Medium/Low + 证据 + 建议修法），落到 `AI_agent/logs/review/review/2026-06-11_pipeline_0-5_full_audit_review.md`（§6#14 格式）。
3. 特别确认这几个已知风险点是否真咬：
   - InterZone 门的**覆盖洞盲区**（两侧都标 Outdoors/Adiabatic 的"内部边界"，门查不到）——sm20 3 层更可能暴露。
   - 窗挂错宿主墙 / 跨层切配把外墙切碎导致窗 `_find_parent_wall` skip（见 [modelling.py](../../../src/agent/geometry/modelling.py) `attach_windows`）。
   - 3 层 z-stack 在 1_correction 的合成正确性。

## 6. 配套：capability 升级建议文档

[`architecture/pipeline_0-5_capability_upgrade_suggestions.md`](../../architecture/pipeline_0-5_capability_upgrade_suggestions.md) 是各环节 capability 升级建议的活文档（已起骨架）。本 audit 中**顺手发现的 capability 想法**记进那里，不在本 audit 展开。硬伤仍走本 request → review 闭环。

## 7. 相关文件

- 接线：[pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)
- 主链：[src/agent/pipeline.py](../../../src/agent/pipeline.py) / [src/agent/correction/](../../../src/agent/correction) / [src/agent/geometry/](../../../src/agent/geometry) / [src/agent/intakeoutput.py](../../../src/agent/intakeoutput.py)
- 门：[src/validator/interzone.py](../../../src/validator/interzone.py) / [src/validator/schedules.py](../../../src/validator/schedules.py)
- 装配 + EP：[src/mcp/tools/workflow.py](../../../src/mcp/tools/workflow.py) / [src/runner/runner.py](../../../src/runner/runner.py)
- 今日交接：[CLAUDE.md §5.11](../../CLAUDE.md) + [memory sm21-ep-anchor-two-real-defects]
