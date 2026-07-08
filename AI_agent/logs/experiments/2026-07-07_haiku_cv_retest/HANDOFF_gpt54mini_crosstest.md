# 交接单：GPT-5.4-mini 弱模型交叉测试（下一场，Opus 主控盯 Codex/子代理执行）

- **决策**（用户 2026-07-07 拍）：sm21+sm24 两 case Haiku 线验收收口后，reading VLM 转 **gpt-5.4-mini** 交叉测试。双目的：①弱模型迁移性验证（配方是否 Haiku 特调）②读图开销挪出 Anthropic 池。
- **Fable 5 已备好的全部前置**：CV 工具箱判决性阳性（本目录 README）、E 批已落地（prescan 宏工具+纪律固化 skill+前置化 SOP，`logs/reviews/{request,verdict,execution}/2026-07-07_reading_cv_efficiency_*`，517 绿）、判卷 harness 即标准验收协议。

## 实验设计（预登记，主控照跑）

- **假设**：配方分层论——确定性工具+流程纪律+验收 harness 模型无关；会漂移的只有残留 VLM 职责（语义判定/读数/schema 写作/指令跟随）。交叉测试判据=gpt-5.4-mini 在同 harness 下能否达到 Haiku 同级（sm21 判卷满分带）。
- **sm21 正式卷**：run 名建议 `run_2026-07-XX_gpt54mini_cv_retest`。协议同 `run_2026-07-07_haiku_cv_retest`（run_config.yaml/llm.yaml 照抄改 models.reading + provenance；判卷尺默认容差不动）。**注意 E 批后脚手架基线已变**（prescan 前置化 SOP + skill 纪律已固化，skill 哈希与 07-07 Haiku run 不同）——这是**预期内的新基线**，provenance 如实记；若要严格对齐 Haiku 口径可另跑不用 prescan 的对照，但**不必**（交叉测试测的是"当前最佳配方×新模型"）。
- **sm24 探针卷**：同 07-07 探针协议（reading-only、无 gt、人工肉检+自洽）。
- **历史参考**：gpt-5.4-mini 2026-06-23 无工具箱旧卷（`run_2026-06-23_gpt54mini_reading`：平面干净但 South-F2 四窗并两窗 + 2f 漏 1 隔墙）——本次重点看这两个旧失败点是否被工具箱修复（窗 CC+链值双通道应直接命中它）。

## 执行要点（操作层）

1. **接入方式**：gpt-5.4-mini 经 **codex CLI 喂图**（本容器网络通 OpenAI 侧；Anthropic Agent tool 只有 Claude 系）。坑备忘：`echo "" |` 喂 stdin EOF（memory `sm21-dualmodel-round`）；codex MCP 工具无图片参数，用 Bash 直跑 codex CLI `-i <png>`，或者 codex 会话内让它自己以多模态读本地图（验证哪种能真看到图再开跑）。
2. **spawn prompt**：复用 07-07 Haiku 的协议模板（本目录 README 有要点；完整 prompt 在主控 transcript，核心=kickoff+隔离规则+pilot 先行；E 批后 cv_toolbox.md 已自声明 required，prompt 不必再加 measure-before-draw 指令——**这正是要验证的固化效果**）+ **E3 前置化**：spawn 前主控先跑 `cv_probe.py prescan-plan/prescan-elevation` 把 candidates.json+综合 overlay 给进输入（new_case_guide §2.1/附录A 已更新）。
3. **pilot 门必须保留**（1f 先行、主控审后放批量）——Haiku 两案实测 pilot 打回是配方组成部分；打回参考清单：标定锚必尺寸链 tick、残差≤1px、单一 px→m 公式留痕、候选逐条 crop 核验、完整性、anchor=flat list。
4. **跑前向用户拍配置**（memory `pre-run-config-confirmation`，别跳）。
5. **效率计量**：记录 token/工具往返数/返工轮数，与 Haiku 基线对比（README 效率段）——E 批收益的验收数据。
6. **判卷**：flow → gate① → J0（gt 对账权威）；成绩三分支：满分带=迁移性成立+开源 VLM 验收提前案通过；部分崩=定位漂移层（语义判定 vs 读数 vs schema 写作，per-criterion 对账可分离）；全崩=配方有 Haiku 特调成分，回查 spawn/纪律依赖。
7. **OCR 触发器挂在此**（E4 定案）：若 gpt-5.4-mini 标定锚/读数系统性失败 → 轻量数字 OCR 提级（先 advisory）。

## 顺延事项（不阻塞交叉测试）

- ~~sm21 Haiku run 的 correction+内核推进~~ **✅ 2026-07-08 容器内跑完**（DeepSeek 可达翻案后）：correction 首抽 J1 pass（judge 判据=score_correction_vs_gt 五项全 pass，grade 全绿零红，边界走 gt `wall_thickness_m` 中心线→外皮换算）→ 内核全净 → 停几何门待 approve。交叉测试的 sm21 对照数据链完整。
- 开源/国产 VLM api 首次验收（用户已知悉建议提前；等交叉测试结论后拍）。
- C2 B1（Cell.polygon）排队单顺延。
