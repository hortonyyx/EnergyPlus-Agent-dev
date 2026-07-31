# 2026-07-31 识图链路断点施工记录

> 执行席：sol（CONSTRUCTION）  
> 派工单：`AI_agent/logs/reviews/request/2026-07-31_reading_chain_gaps_dispatch.md`  
> 基线：`1997 passed / 10 xfailed / 0 failed`

## 边界与禁区

- 不改 `src/agent/judge/**`、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md`。
- G-1 gate① 与 G-2 residual fail-closed 均只量影响面，不代主控裁决。
- G-3 只加「合并长线视图」，原候选不删、不筛、仍可达。

## G-1 · `scale_origin` 生产者合约

### 影响面实测（gate①，待主控裁决）

口径：只数 Git 已跟踪的 `case_tests/**/{0_reading,phase1}/*.json`，且 JSON
同时满足 `image_kind == "plan"` 与 `strokes` 为 list；这与 gate① 的单视图
产品输入口径一致，排除 `*_checks.json` / judge packet / prescan sidecar。

- 既有主产品：**38** 份 plan reading JSON。
- `scale_origin` 含有非 null `world_x_m/world_y_m`：**29/38**。
- 缺 key / null / 对 judge 不可用：**9/38 = 23.7%**（九份均是整个 key 缺失，无「有 key 但半缺」情形）。
- 若现在把 gate① 改为 INVARIANT block：这 **9** 份历史产品会新增阻断；
  其余 **29** 份不受影响。本席未改 `src/validator/checks/reading.py`。

九份受影响产品分布：

- `sm21_anchor/run_2026-07-01_sonnet_e2e_r1`：2
- `sm21_anchor/run_2026-07-01_sonnet_e2e_r2`：2
- `sm21_anchor/run_2026-07-02_sonnet_flow_e2e`：2
- `sm21_anchor/run_2026-07-05_haiku_downgrade`：2
- `sm24_anchor/run_2026-07-07_haiku_cv_probe`：1

### 施工

- `guide.md` §1/§2/§6：plan 视图必须声明 `scale_origin`；明确
  `world_x_m/world_y_m` = plan-local `(0,0)` 的世界米坐标，全局唯一原点 =
  整栋投影最大边界 SW 内角，禁每层本地原点；加 JSON 样例与 self-check。
- `pen_library.md`：把标定结果落入顶层 `scale_origin` 定为 plan 必做 container action。
- per-run directive 待主控同步：`session_kickoff.md:4-6` 的
  `Do no spatial-topology reasoning and no world placement`
  需改成「不做 topology placement；plan 仅例外声明 `scale_origin`」，否则与新主合约相冲。

### 锁与 neuter

| 锁 | 定点破坏 | 实跑变红测试 | 还原后 |
|---|---|---|---|
| `test_plan_scale_origin_is_a_locked_reader_instruction_contract` | `guide.md` §1 把 `Every plan view` 定点改为 `Every plan sketch`，使必填指令契约断开 | `tests/test_reading_schema.py::test_plan_scale_origin_is_a_locked_reader_instruction_contract` | 实跑 `1 failed`；还原后 `tests/test_reading_schema.py` = `10 passed` |

## G-2 · 标定可靠性

待施工。

## G-3 · 预扫共线长线视图

待实测确认根因后施工。

## 最终验证

待填。
