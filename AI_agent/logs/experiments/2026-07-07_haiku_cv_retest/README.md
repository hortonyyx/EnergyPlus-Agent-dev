# Haiku 4.5 复测 — CV 工具箱北极星判决性实验（2026-07-07）

**问题**：经典 CV 工具箱（C0+C1，"量而非看"）能否把弱 VLM 从能力地板下捞起来？（体检 B2 验收实验；排队单②）

**设计**：三点单变量对照。

| 臂 | run | 脚手架 | reading 模型 |
|---|---|---|---|
| 对照（地板） | `run_2026-07-05_haiku_downgrade` | 完全恢复版，无工具箱 | Haiku 4.5 |
| **本次（处理臂）** | `run_2026-07-07_haiku_cv_retest` | 同上 + CV 工具箱（唯一 diff） | Haiku 4.5 |
| 参考（天花板） | `run_2026-07-02_sonnet_flow_e2e` | 完全恢复版，无工具箱 | Sonnet 5 |

- **单变量验证**：`git diff 860e346..723b0f9 -- skills/intake_pipeline/0_reading src/agent/reading` = 6 个新文件 +944 行（cv_toolbox.md / cv_toolbox 包 / kickoff 1 行指针），既有脚手架内容零改动。内容哈希：skill `139bfe8bd322c30b→d4c8a9bf6f53d1d8`、reading src `d3b4247a97abba3f→02eecb894a77a503`。
- **同 case**（sm21_anchor 满家具双层图）、**同判卷尺**（默认容差，与两臂 sidecar 一致）、**同隔离协议**（冷启子代理只喂 case_data 图+testdata+skill，禁 gt/attempts/judge 产物；prompt 级隔离，硬隔离仍在 backlog）。
- **⚠️ A/B 口径注记**：kickoff 中工具箱是 "Optional"；本 run 的 spawn 指令把它升为**必用（量了再画）**。判决性问题="拐杖用上了能不能托底"，非"弱模型会不会自己捡拐杖"。故本臂口径=「工具箱可用+指令要求使用」。脚手架文件零改动，指令全文记 run llm.yaml/run_config.yaml provenance。
- **judge② 差异声明**：编排/judge = Fable 5（对照臂为 Opus 4.8）。权威判据是确定性 gt 判卷（score_reading_vs_gt + render_grade），judge② 仅定性/路由，不影响 A/B。
- **配置（用户 2026-07-07 拍）**：Haiku ×1 · 推到 correction+几何内核（不跑 4_mep/EP）· J0 on + 盲重抽 ladder 放开（预算 3）· 不 record_baseline · 完事接 C2 B1。

**对照臂成绩（地板）**：平面墙 0/9 · 平面窗 0/7 · 立面窗 0/15（17 extra）· 过度分割 +9 · 四立面 ambiguous；仅外框 8/8 + 楼层线对。
**参考天花板（Sonnet 5）**：9/9 · 7/7 · 15/15 complete · 0.0m。

## 过程记录（滚动）

- pilot r1（1f 平面）：工具箱调用链正常（profiler/CC/calibrator/sidecar 全落），但**流程不合格打回**——标定错锚（用墙线端点非尺寸链 tick，Y 残差 0.90m、外框量成 14.52×8.90 vs testdata 15×8）、内墙 19 道（候选未经 crop_zoom 逐条核验=头号失败模式复现）、windows/dimensions/ocr/provenance 全空。已按 SOP pilot 审查点发返工指令（纯流程合规反馈，无 gt 泄露）。
- pilot r2（返工后，orchestrator 亲核盘上产物 + 亲跑 gate①）：**达标放批量**。标定改从尺寸链 tick 锚（92.6945 px/m，残差 +0.9mm/−1.7mm），外框回到 15.00×8.00；墙 10 道（44 候选拒收全留痕 overlay_logger、8 门愈合）；窗 7 扇双通道钉位（CC 间隙 vs 链值 1px 内吻合）；尺寸 32 条 verbatim。gate① `check_reading_view`：14 pass / 3 N/A / 1 非阻塞 FAIL（`dimension_chain_closure`=overall 与 segments 拆了 chain_id 的记账问题，已令批量前修正）。**中途插曲**：子代理会话额度 5am UTC 断限一次，恢复续跑；恢复段 0 工具调用只补报告，产物经盘上时间戳核实为断限前真实写入。
- 批量放行（2f + 四立面，逐图独立标定，立面走 storey_line_profiler + 区域限定 CC）。

## 结果（reading vs gt 坐标对账，判卷权威判据；attempt 001，J0 已判 pass 入账）

| 维度 | Haiku 4.5 无工具箱（07-05 对照） | **Haiku 4.5 + 工具箱（本次）** | Sonnet 5 基线（07-02） |
|---|---|---|---|
| 平面墙 | 0/9（+9 过度分割） | **9/9 complete·max_offset 0.0m** | 9/9·0.0m |
| 平面窗 | 0/7 | **7/7 complete** | 7/7 |
| 外框 boundary | 8/8 | **8/8** | 8/8 |
| 过度分割 | +9 | **0** | 0 |
| 立面窗 | 0/15（17 extra） | **15/15 全 complete·0 miss·0 extra** | 15/15 complete |
| 立面朝向 | 四立面 ambiguous | N/E/W ambiguous（同基线已知 backlog，归 correction 仲裁） | South aligned 余 ambiguous |

score_criteria 五项全 pass（walls_complete/windows_placed/boundary_complete/no_oversplit/elevation_windows_placed）。judge② 肉检 grade.png 与 scorer 一致（全绿零红）。gate① 唯一 flag=六图 `dimension_chain_closure`（未标注 120mm 墙带段被诚实留白的良性 advisory）。

## 裁决

**分支① 成立——判决性阳性**：CV 工具箱把 Haiku 4.5 从全线归零拉到与 Sonnet 5 基线**逐项相同的满分成绩单**。"量而非看"是弱 VLM 的关键杠杆；测量链全程可审计（tick 锚→92.6945 px/m 残差<2mm→逐元素测量→窗 CC 间隙 vs 尺寸链双通道互证）。

**三条如实限定（都记在 run provenance）**：
1. **工具箱使用是被指令要求的**（measure-before-draw），非弱模型自发采用——A/B 口径=「可用+指令要求」。若靠 kickoff 里 "Optional" 一行，Haiku 大概率不会自己捡（r1 连标定锚都选错）。→ **修法方向：把 measure-before-draw 从 per-run 指令固化进 skill（对弱模型档）**。
2. **需要一轮 pilot 审查+返工**（r1 错锚+量了不筛 → 流程纪律拉回）。编排层的 pilot 门是配方的一部分，弱 VLM 一次抽干净还做不到。**失败模式已从"看错"（感知）迁移为"量了不筛/锚错"（流程）——后者可被确定性检查/纪律托住，前者不能。这是工具箱价值的本质。**
3. prompt 级隔离（硬隔离仍 backlog）；无污染旁证=r1 以非 gt 形态出错（14.52×8.90）+ 全坐标带像素测量链。

**OCR 判据（数据驱动裁定，用户 2026-07-07 拍的决策程序）**：Haiku 尺寸 verbatim 转录在干净 CAD PNG 上基本无错（1f/2f 链闭合精确 15.00/8.00；J0 criterion "number copied wrong" pass）→ **OCR 维持 Phase C 不提级**。

## 过程中抓到的真 bug（额外收获）

- **pipeline.py import 回归（M1 `fea6981` 引入）**：`run_correction` 调 `compute_evidence_debt_from_vector_dir` 但该名字被 M1 重写 import 块时漏掉 → 真实 run 一进 correction 就 NameError；509 绿没盖住（无测试走 `evidence_debt is None` 路径）。**已修**（import 补回）+ **Codex 已补回归测试** `tests/test_pipeline_evidence_debt_import.py`（stub LLM 边界、走真 evidence-debt 分支；单测过，全 suite 509+1 绿）。
- **环境注记**：本容器网络仅白名单 Anthropic API（DeepSeek 000/fake-IP 段），correction(DeepSeek) 无法在容器内推进 → **本 run 停在 0_reading judge_pass，correction+kernel 待宿主侧续跑**：
  **⚠️ 更正（2026-07-08 实测翻案）**：容器内 DeepSeek 已可达（`api.deepseek.com` 200 OK + deepseek-v4-pro 正常回复，.env key 生效）——07-07 的"不通"是当日临时故障或网络配置后来变更。correction 续跑**不再需要宿主侧**。
  **✅ 续跑完成（2026-07-08）**：correction（DeepSeek 首抽）gate① 0 block 0 flag → score_correction_vs_gt 五项全 pass（墙 9/9·窗 7/7·边界 8/8〔中心线→外皮换算后零缩圈〕·立面窗 15/15 全 complete）→ J1 judge_pass（verdict_004）→ 2_modelling/3_split_pairing 首抽全净 → 停几何门待用户 approve。**Haiku+CV 工具箱线至此全链贯通到内核**。产物走当日新规格：grade.png + zones_1F/2F.png。`python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests --date 2026-07-07 flow sm21_anchor run_2026-07-07_haiku_cv_retest --judge stop --to 3_split_pairing --geometry required`。顺带发现 `tests/test_zone_agent.py` 有真网络依赖（此环境必挂,pre-existing）。

## sm24 泛化探针（同日，reading-only，无 gt 人工肉检）

- run：`case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/`。验证点=非方形内部布局 + **无标注构件像素直测口径**（标定后像素测量=测量非猜测，provenance 诚实标注 pixel-measured + 空 dimension_refs + 引用 sidecar）。
- pilot r1：同"首抽散漫"模式复现（标定 RMSE 86mm 锚粗、只描"主要墙"违完整性、窗未描、一处 px→m 换算自相矛盾）→ 已打回返工（锚收紧到 ±1px、全墙完整描、单一换算公式留痕）。**注**：此图分辨率 36.6 px/m（1px≈27mm），精度物理上限低于 sm21（92.7 px/m）。
- pilot r2：**内容达标**（标定 RMSE 9.2mm；14 墙全 px→m 算术留痕、38 候选拒收留理由；11 窗链值+CC 双通道；51 尺寸 verbatim 全链精确闭合；**无标注 H6 墙像素直测口径完美执行**=provenance 诚实+空 dimension_refs+引 sidecar；L 形走廊拓扑正确解析），但 **schema 违规打回一次**：51 条 `dimensions[].anchor` 写成自创 dict（schema 要求 flat list）→ 坐实"弱 VLM 残留短板含 schema 写作（纯机械翻译活）"，是 Phase B 双通道/schema 外包方向的直接证据。
- **收口（5/5 图）**：anchor 修正 loader 全过；四立面独立标定 RMSE 1.5-6.0mm 零 warning；立面 facade 块严格 image-local（mirrored=unknown+链序证据留给 correction 仲裁）；门组件 crop 核验全记 door 不混窗。gate① 五图 blocking 全空（唯一 flag=chain_closure 良性分组 advisory 同 sm21）。**探针结论：非方形内部布局对 reading+工具箱无实质新难度（行列投影对正交多边形天然适用），"部分构件无标注"由标定后像素直测正解；弱 VLM 首抽散漫+schema 写作错是跨 case 复现的稳定短板（流程纪律可拉回）。**

- **⚠️ 登记（2026-07-08 用户肉检）**：sm24 correction 把若干处**正确的 reading 值改偏了**（好 reading 被 correction 降级）。sm24 无 gt 暂无法逐项定位清单，**gt 补录后对账定位+解决**。旁注：07-08 探针推进轮 correction 首轮重抽即出两个坏 draw（cells 不铺满/闭环 ring），DeepSeek 在 sm24 上的 draw 方差明显高于 sm21，与该登记同向。

## 效率数据（E 批动机与基线）

- Haiku 成本：sm21 全程 ~0.4-0.6M tokens（1 轮返工）；sm24 全程 ~0.65M tokens/96 次工具往返（2 轮打回：纪律 1 + schema 1）。大头=返工整轮重来、交互式单工具循环+overlay 逐图回读、冷启固定成本。
- **E 批已落地（同日，Codex 审 APPROVE-WITH-CHANGES 6 findings 全采纳→执行→Fable 复核，510→517 绿）**：E1 纪律固化进 skill（cv_toolbox.md CV 特有纪律+指针不重复、自声明 clean-CAD required；kickoff 判定权移交）+ E2 prescan-plan/prescan-elevation 宏工具（**有界真实线段**候选表 `line_band_candidate`/`cc_box_candidate`/`tick_candidate` 机械中性命名、capability_profile 声明+不支持档显式 raise、真图冒烟 825 候选零全图跨度）+ E3 前置化 SOP（主控确定性跑 prescan→候选表+综合 overlay 进子代理输入；语义判定权完整留 VLM）。E4 OCR=方案(a)定案（VLM 挑锚读数；触发器=交叉测试暴露标定/读数失败）。审轨 `logs/reviews/{request,verdict,execution}/2026-07-07_reading_cv_efficiency_*`。**预期收益待 GPT-5.4-mini 交叉测试实测**（见 HANDOFF_gpt54mini_crosstest.md）。

## 下一场（用户 2026-07-07 拍）

**GPT-5.4-mini 弱模型交叉测试**（迁移性验证+省 Anthropic 额度），Opus 主控盯 Codex/子代理执行，完整交接单 = [HANDOFF_gpt54mini_crosstest.md](HANDOFF_gpt54mini_crosstest.md)。

## 产物

- run：`case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/`（cv_evidence/ sidecar 全程留痕）
- 判卷图 / score sidecar：`0_reading/grade.png` + attempts 内 per-attempt。
