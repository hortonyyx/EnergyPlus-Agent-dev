# Haiku 对比重跑执行日志 — 4 轮 pilot 打回后止损（2026-07-09，Fable5 主控）

run = `case_tests/e2e_tests/sm21_anchor/run_2026-07-09_haiku_prescan_triage/`（配置见其 run_config.yaml）。
目标 = 验证 prescan 候选收窄（`20749ff`）的效率收益，质量守 07-07 满分带。
**结果 = pilot 4 轮未过审，预算（3 轮 review）用尽止损；效率批本体阳性、暴露隔离协议两个结构缺口。**

## 轮次记录（全部 Haiku 4.5 冷启，spawn_isolated_reader 硬隔离，一次性 `-p` 会话）

| 轮 | 行为 | 判定 |
|---|---|---|
| r1 | 零 CV 调用、纯目测 27 strokes、dims anchor 全 null | 打回（纪律违规=07-07"首抽散漫"复现）|
| r1.5 | 重 spawn 未指向 feedback.md → 会话对打回无感知 | 主控 kill（暴露缺口 #5）|
| r2 | 纪律全改（标定×2、prescan 消费、引用齐）但**只描 4 道外墙**、内墙/窗塞进 uncaptured；标定坏（两锚隐含 ~60 vs ~110 px/m，硬平均 71） | 打回（完整性+标定残差）|
| r3 | 补了 19 墙 22 dims 但**坏标定原封没动**、窗=0（自判"窗归立面"）、走廊带 7 根 y∈[3,5] 短墙疑幻觉 | 打回（清单式最后一轮）|
| r4 | 窗出来 6 扇但宽度 1.4m/位置错；重标定仍坏（60 vs 45 px/m，真值 ~92=07-07 实测 92.7）；r3 幻觉墙原样保留、点名的 crop 复核未执行 | **止损**（预算尽，质量低于地板）|

**行为模式**：Haiku 每轮只机械满足 feedback 点名项、丢其余上下文；标定系统性锚错（疑锚文本行非延伸线 tick），
且"重推导所有坐标"类全局指令从不执行。

## 效率数据（本轮真正要测的东西）

- **✅ prescan 收窄本体阳性**：pilot 阶段 CV 调用 2–6 次（07-08 gpt54mini pilot=86 次）；候选表 519 行（收窄前 825）；
  axis_summary 被消费（r2 起 note 引用峰候选）。**"逐段 crop 核验"的成本源确实被砍掉了。**
- **❌ 新主导成本 = 无状态重 spawn 循环**：5 会话共 **~1.03M 新 token**（in 3.3k + out 248k + cache_write 778k；
  cache_read 19.6M 另计），pilot 都没过——对照 07-07 全程（含 1 轮返工+全 6 图）0.4–0.6M。
  每轮打回 = 全场冷启重来 ~0.25M，无会话连续性。

## 结构结论（A/B 拆解）

07-07 Haiku 满分的两根拐杖，在 07-08 硬隔离协议下**都不在了**：
1. **开场指令**（per-run directive：cv_toolbox required + measure-before-draw）——现 kickoff 是 manifested 通用文案，
   spawn 无 directive 槽；本轮是 skill-doc 自驱（对 gpt54mini 够、对 Haiku 不够）。
2. **连续交互会话**（07-07 走 Agent tool 多轮，judge 反馈在上下文里）——现协议只有一次性 `-p` + feedback 文件
   + 全量重 spawn，弱 VLM 在无状态循环里拉不回来。

→ **收窄配方没问题，隔离协议的弱模型适配是缺口**。修法（并入明日 Codex 批）：
- spawn verb 加 `--directive <file>`（spawn 时附加到 prompt、落 provenance，不改 manifested kickoff）；
- feedback.md 存在时 spawn 自动在 prompt 附指针（缺口 #5）；
- 评估 staging 内 `--resume` 会话连续性支持（缺口 #6，改动最大、可后置）。
- 复跑验证：修好 directive 槽后按 07-07 directed 模式重跑本实验（预算另拍）。

## 附

- staging = /tmp/ep_isolation/sm21_anchor_2lfp7xkr（tmp，产物不入库；被拒 pilot JSON 未 merge，attempts 零污染）。
- run 目录保留 run_config.yaml + 0_reading/prescan/ 留档（triage 预扫产物本身有效、可复用于下次重跑）。
- 同场发现缺口 #4（`_copy_prescan`⊥守卫互斥）见 plan.md 当前焦点 ③。
