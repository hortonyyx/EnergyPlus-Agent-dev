# 2026-05-07_sm_16_newarch_v4pro_no_sim_v1

## 本次目的

新架构（半人工 intake + DeepSeek 自动下游）首次能完整产出可被 OpenStudio 打开的 IDF 的 baseline。
此前 2026-05-07_sm_16_newarch（同日早些）首跑 v4-flash 时下游漏建 window construction 导致 0 fenestration；
切回 v4-pro 后所有期望的 material / construction 全部建出，本 run 即修正后产物。

## 异常 / 失败点

1. **East / West 立面走廊 zone 漏窗**（intake fenestration_specs bug）—— 用户用外部 LLM 还原 intake JSON 后核对发现 IDF 与 intake 一致，bug 出在 intake 识图阶段，没把"走廊 zone 触 E/W 外墙"识别为应开窗。属于 [architecture.md §4.3](../../../../AI_agent/architecture.md) 🎯 主作用面，是后续 plan B 优化目标
2. **fenestration_specs 内部数字不一致**：summary line 写"Place 21 windows total"，但细数列出仅 16；fenestration_agent 自报"16 by my count, though user mentioned 21"。同 1 的另一面，intake 数字算错
3. **closure validator 42 warnings**：12/19 zones 含 T-vertex 不闭合点，按 [B0' 临时放宽决策](../../../../AI_agent/plan.md) 接受，待 idfpy 切换时整体清理
4. **OpenStudio 导入对话框** "Some portions of the IDF file were not imported. Only geometry, constructions, loads, thermal zones, and schedules are supported"——预期内，OpenStudio IDF 导入只支持 5 类，HVACTemplate / Output:Variable 等被跳过，不影响 EnergyPlus 仿真本身

## 与上一 anchor 的差异观察

无可直比 anchor — 本 run 是 `pipeline_version=halfmanual_v1` 第一桶。
若未来与 `yaml_to_idf_v1`（旧 Opus 全流程）对比：
- counts: 19/135/16 vs 旧 sm_16 的 19/114/?（旧 IDF surfaces 数低，与本 run 差 21 — 可能因 T-vertex 未切分；待 OpenStudio 视察确认）
- token：half-manual 流的 token 计量需新方案，`/context` 不再是单一权威源（Opus 在用户另一会话 + 下游走 DeepSeek API），README §4.1 / §4.3 流程待按半人工架构升级，本 run 暂留 `tokens.total=null`

## 下次改进候选

1. **B4 CoT 优化**：intake_node prompt 增加"识别走廊是否触外墙 → 触则开窗"步骤；同时强化"自检 fenestration 数字一致性"（避免 21 vs 16 这种 summary/detail drift）
2. **per-node 模型策略**：本 run 实证 lights/people/hvac 在 v4-flash 下也能跑通；surface/construction/fenestration 必须 v4-pro。可在 [llm.yaml](../../../../src/configs/llm.yaml) 加 per-node section 节省 token
3. **Token 计量方案升级**：[test_baseline/README.md §4.3](../../README.md) 现行流程基于旧单会话流；半人工流下需要 ① Opus 端 /context（用户主动粘） ② 下游 DeepSeek API usage 字段从 trace 收集 ③ 总和才是真"任务 token"。建议 token_optimization.md 加一节
4. **后续真跑 simulate**：当前 `--no-simulate` 停在 IDF；待用户 OpenStudio 视察通过后摘 flag 真跑 EP，看 closure 放宽是否会引入其他 fatal
