# 阶段 0：接口 × 样例及验收证据

本表为 Astra 自评，正式验收文件仍由 Opus 维护。
六个 JSON 在 `tests/fixtures/harness_stage0/`，从三个脚本离线重建：
`extract_sources.py`、`map_history.py`、`build_samples.py`。
最后一个脚本只生成阶段 0 片段，不调用模型或现有 BIM 工具。

## 接口 × 样例

R=`reconstruction.json`，P=`partial_inference.json`，F=`full_inference.json`，
M=`mixed_inputs.json`，C=`evidence_conflict.json`，S=`simplification.json`（含 fine/coarse 和真实 Sol 失败）。
✓ 表示实际对象经 Pydantic 校验；— 表示本例无需重复。通用接口均在 R 与 P 出现。

| 接口/入口文件 | R | P | F | M | C | S | 定位 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 核心引用、父子身份、六层版本；`refs/events` | ✓ | ✓ | — | — | — | — | `events.events`，最终内联请求带实际本地图像字节 |
| 请求、响应、五种思考、用量；`events` | ✓ | ✓ | — | — | — | — | `request/response/usage-summary`；五种变体另由核心测试和历史签名/缺失覆盖 |
| 工具全参、原始/所见返回；`events` | ✓ | ✓ | — | — | — | — | `read/write-unknown/write-applied` |
| 生命周期、状态读取；`events/validation` | ✓ | ✓ | — | — | — | — | `inspect-write/retry-write/inspect-resume/resume` |
| 预算预留、结算；`budget` | ✓ | ✓ | — | — | — | — | 主任务/子任务/摘要/重试四笔总账，缺 usage 的结算不写0 |
| 上下文、图片移出/取回；`events` | ✓ | ✓ | — | — | — | — | `compact/remove/retrieve` |
| 外层 MCP 派工/返回；`events` | ✓ | ✓ | — | — | — | — | `dispatch/return`；operation 真实历史另见 Sol |
| 角色、模型绑定、只读白名单；`roles` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `roles/model_bindings`；未运行模型验证范围为空 |
| 需求、四类依据与继承；`evidence` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `building.requirements/evidence` |
| 冲突双方；`evidence` | ✓ | ✓ | — | ✓ | ✓ | ✓ | 两层尺寸冲突/重复规则与已验收例外 |
| 计算链；`evidence` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `building.calculations`；原值、换算、规整、保存 |
| 声明、范围、模型/代码边界；`declarations` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 三个旧工具入口；楼层/跨层/翼/对象组 |
| 重复与例外；`declarations` | ✓ | ✓ | — | ✓ | ✓ | ✓ | R 两层对应隔墙，P 成对门和单门例外 |
| 方案、关系、功能假设；`declarations` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `hypotheses`，均标 hypothesis；用户功能要求另列 |
| 保存版本；`declarations` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 内部模型内容哈希与实际文件哈希分开 |
| 带图证据包、定位返回、单层草案；`tasks` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 原像素框、坐标关系、源版本、三栏返回 |
| 三类检查和保存核查；`quality` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `checks`；只声称检查所列片段 |
| 规整/实质保护；`quality` | ✓ | ✓ | — | ✓ | ✓ | ✓ | R 6厘米建议；P 保留真实门位例外、无编辑 |
| 覆盖与未完成项；`quality` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `coverage`；S 包含真实失败对象和未完成项 |
| 总表、依据影响反查；`bundle` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `evidence_change_demo` 实际替换依据后重算反查 |

推理任务的分工、功能/关系/方案结构仍是待验证假设；共同格式可用不代表这种分工已在工作模型上有效。

## A–J 自评与检查入口

| 条件 | 自评 | 主要证据 |
|---|---|---|
| A 三线共用 | 满足（阶段0格式） | 上表；`test_common_interfaces_are_used_by_reconstruction_and_inference`；F 不依赖图纸/网格字段。 |
| B 事件 | 满足 | `test_valid_factories_cover_request_response_recovery_role_and_budget`、`test_thinking_states_are_distinct_and_usage_missing_is_not_zero`、`test_adapter_image_bytes_and_recovery_state_are_the_recorded_bytes`。 |
| C 历史映射 | 满足 | run99/Sol 各6事件；`test_run99_preserves_actual_stream_order_full_messages_and_per_message_usage`、`test_sol_bridge_maps_dispatch_operation_tool_return_and_missing_receipt`。 |
| D 依据需求 | 满足 | `test_sm25_anchor_math_matches_documented_six_centimetre_difference`、`test_changed_inherited_evidence_reaches_declarations_and_model_versions`；建筑测试含坏换算、断链反例。 |
| E 声明 | 满足 | `test_declaration_wraps_only_existing_tools_and_separates_field_ownership`，六例使用三个原入口；内部工具 JSON 留原工具负责。 |
| F 角色证据包 | 满足（格式/离线拒绝） | 只读越权/推荐自动换模反例；`test_localized_results_separate_seen_interpreted_uncertain_and_refuse_stale_apply`；未下发图片同样拒绝。 |
| G 检查规整覆盖 | 满足（片段） | `test_sm25_normalization_uses_real_f2_target_and_persisted_snapshot`、语义变更五组反例、`test_fine_failure_cannot_pass_as_rationale_or_unapproved_coarse_merge`；真实窄部不能进入规整。 |
| H 恢复预算 | 满足（契约） | `test_write_cannot_bypass_recovery_by_omitting_retry_link`、重试改工具/全参反例、已写/不明状态拒重试、预算预留与估算反例。 |
| I 范围 | 满足 | `changes.txt`；冻结目录、Agent/project/brief 无 diff；未运行模型/API、运行器或规整算法。 |
| J 验证 | 满足 | `validation.json` 与 `validation.txt`；核心 import 方向及实际模块路径检查。没有修改旧共享模块，因此无相关旧测试新增要求。 |

## 历史映射与缺口

材料级映射见 [source_mapping.md](source_mapping.md)。事件级字段映射和缺口见
[history/README.md](../../../../tests/fixtures/harness_stage0/history/README.md)。
历史原文件逐个核 SHA-256，消息保留原始消息对象；运行累计用量单列，未混入单条响应。
CLI 启动参数不是最终网络请求；CLI 可见 tool_result 不是原始 MCP 返回；Sol bridge reply
不是模型实际所见的充分证明。缺失均保留，不补造。

所有 complete 事件轨迹是离线格式示范，固定时间、测试用量及故障注入均不是本次或历史实际运行。
真实照片待用户选案；混合输入的跨实验对象对应仍未核实；整案运行没有发生。

## 实际验证与复现

最终全套为 **86 passed in 11.52s**，Python 3.12.13、pytest 9.0.3、4 个 worker。
原始输出见 `validation.txt`；`validation.json` 保留实际命令、时间和被测文件哈希。
三个生成器的确定性检查已包含在测试中，历史文件只读。

```bash
mkdir -p .stage0_tmp/tmp
TMPDIR=$PWD/.stage0_tmp/tmp PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  tests/test_harness_core_contracts.py tests/test_building_contracts.py \
  tests/test_harness_stage0_boundaries.py tests/test_harness_stage0_history.py \
  tests/test_harness_stage0_provenance.py tests/test_harness_stage0_samples.py \
  -n 4 -s --basetemp=$PWD/.stage0_tmp/pytest-review
```

`-s` 避免此共享容器中的捕获临时文件问题；现有 F-158 门禁保持启用。
最终范围核查见 `scope_check.json`，完整 diff 文件名单见 `changes.txt`。
