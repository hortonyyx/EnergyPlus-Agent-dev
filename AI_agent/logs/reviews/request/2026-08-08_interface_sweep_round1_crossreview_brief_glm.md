# 交叉审阅单 · 接线摸排第一轮三摊（GLM-5.2 · 验证性审阅）

> **席位选择理由**：本单是**验证性审阅**（给定 finding 清单、验锁真绑、防 false-lock）——
> 按能力画像这是 GLM-5.2 的强项（达 Fable 级）。**⛔ 不是探索性审阅**，不要求你去无线索处找未知缺陷。
> **谁写谁不批**：三摊由 Claude 侧 Sonnet 施工 ⇒ 本审必须跨家族。

## 0. 你的工作边界

- **只审不修。** 发现问题写进裁决书，⛔ 不要改生产码或测试。
- 破坏性探针（neuter）**只在 `/tmp` 副本里做**，⛔ 不许污染工作树。
- ⛔ 不要 commit、不要 push、不要动 `AI_agent/` 下的管理文档。
- 工作树当前**未提交**（orchestrator 统一提交），基点 = `d61c2fe` + 两席工作树改动。

## 1. 背景（一句话）

2026-08-08 接线摸排第一轮（[报告](../../experiments/2026-08-08_interface_sweep/README.md)）
产出三摊修法，本单请你验证它们**真的绑住了、且没有假锁**。

三份施工日志：
- 摊一 F-16：[`execution/2026-08-08_f16_floor_derivation_claude.md`](../execution/2026-08-08_f16_floor_derivation_claude.md)
- 摊二/摊三：[`execution/2026-08-08_multiplier_and_failopen_claude.md`](../execution/2026-08-08_multiplier_and_failopen_claude.md)
- 设计基线：[`request/2026-08-08_interface_sweep_round1_fixes_design.md`](2026-08-08_interface_sweep_round1_fixes_design.md)

## 2. 命题清单（逐条判定：成立 / 不成立 / 无法判定 + 你的证据）

### A 组 · 摊一 F-16（`floor` 派生 + 嵌套标记机制）

- **A1**：`WindowV3.floor` 现在**从给模型的 JSON Schema 里被剥除**（`vocab.producer_facing_json_schema`），
  且 **v1（`CorrectedGeometry`）的 producer schema 字节不变**。
- **A2**：模型若在 draw 里填 `floor`（**即使填的值是正确的**），门必须拒，
  错误码 `producer_window_floor_populated`，且 category 是 `model_draw_error`（⇒ 能拿到重试引导，不是裸 ValueError）。
- **A3**：模型不填 `floor` 时，代码从 `by_id[floor_id].name` 派生填充，值正确。
- **A4 ⭐承重**：**v1 路径完全不受影响** —— v1 没有 `floor_id`，`floor` 仍是必填。
  请独立构造 v1 载荷验证，**不要只看测试**。
- **A5 ⭐承重（双向属性锁 ×4，本摊的命脉）**：
  取消 `floor` 的 DERIVED 标记 ⇒ 门**停止**拒绝 · 给普通字段加 DERIVED ⇒ 门**开始**拒绝 ·
  取消 `facade_segment_id` 的 FORBIDDEN 标记 ⇒ 门**停止**拒绝 · 给普通字段加 FORBIDDEN ⇒ 门**开始**拒绝。
  **锁的是「门跟着标记走」这个性质本身，不是某个字段名。**
- **A6 ⭐承重**：`CORRECTION_DRAW_DERIVED` 与 `CORRECTION_DRAW_FORBIDDEN` **必须是两个标记**，
  施工方的理由是「派生字段在 `model_validate` 成功后总是被填充 ⇒ post-construction 的『是否非空』检查
  会对每个合法 v3 draw 误触发；唯一可观察『模型有没有填』的点是 raw payload」。
  **请独立验证这个理由**（例如：把两者合并成一个标记，看 `_producer_preflight` 是否真的开始误拒合法 draw）。
- **A7**：`envelope_transform.py:324/529` 与 `window_host.py:689` **未被改动**是正确的边界判断
  （它们查的是不同字段、服务不同用途）。

### B 组 · 摊二（`create_fenestration` 的 `multiplier`）

- **B1**：`multiplier` 已从 `create_fenestration` 的参数表移除，模型**没有任何途径**设置它。
- **B2 ⭐承重**：`FenestrationSurfaceSchema.multiplier` 仍默认 1，行为不变；
  且 **standalone MCP 工具 `src/mcp/api/envelope.py:922 create_fenestration_surface` 的 `multiplier` 原样保留**
  （MCP 用户的合法用法未被误伤）。
- **B3**：施工方自陈其中一把锁「摘掉不红」并声明那是按设计如此（锁的是默认回退行为、不是删除本身）。
  **请判定这个自陈是否成立** —— 若你认为那把锁其实是装饰性的，直接说。

### C 组 · 摊三（严格档 fail-open）

- **C1**：`run_profile` 默认值由 `exploratory` 改为 `regression` 后，
  **所有生产调用点行为零变化**（它们都显式传 `run_profile`）。请独立枚举生产调用点验证。
- **C2**：`_EVIDENCE_PERMISSIVE_PROFILES` / `_PLAN_FRAME_PERMISSIVE_PROFILES` 的白名单方向翻转后，
  **既有档位的判定结果逐一不变**，只有「未来新增档位」的默认行为从"不阻断"变成"阻断"。
- **C3 ⭐承重 + ⚠️ 这是 orchestrator 自己出错、被施工席顶回来的一条**：
  `_OCR_ANCHOR_BLOCK_PROFILES` / `_DIMENSION_ENDPOINT_BLOCK_PROFILES` **保持不翻转**是正确的。
  理由：它们的值是 `frozenset()` 空集 = 对所有档位都不阻断 = **2026-08-04 用户拍板的永久 advisory**
  （底层 median/MAD 启发式双向都会误判，结构性修法归 R1.5）。
  **请独立验证「翻转它们会产生错误后果」这个判断** —— 即：若照 orchestrator 原指令翻转，
  是否真的会让一个已知会误判的启发式开始阻断正确的建筑。
  施工方还加了一把锁钉住这个决定（防止以后被人"顺手补完"）—— **请验证那把锁真绑**。

## 3. ⭐ 请你特别用力的两处（orchestrator 自评薄弱）

1. **A5 的四把双向属性锁**：其中 2 把是**轻门抓出缺锁后补的**
   （原 22 把锁全部只走 DERIVED 路径，FORBIDDEN 的嵌套路径零保护）。
   orchestrator 已独立复验「改回硬编码 ⇒ 恰好这 2 条红、零连带」，
   **但请你换你自己的 neuter 方向再验一次** —— 我和施工方用的是同一个方向。
2. **C3**：这条是 orchestrator 的判断错误被施工席纠正的，
   **我在裁定时可能有确认偏差**（倾向于接受纠正我的人）。请你独立判，不要采信我的裁定。

## 4. 已知数字（供你对账）

- 基线（`d61c2fe`）：**2289 passed / 10 xfailed / 0 failed**
- 三摊后：**2289 + 10（摊二三）+ 24（摊一）= 2323**（orchestrator 最终全仓复核中）
- orchestrator 中途独立全量（补锁前）：**2321 passed / 10 xfailed / 0 failed**

**请给出你自己独立跑的全仓数字**，⛔ 不许只写「与声称一致」。

## 5. 交付

裁决书写到 `AI_agent/logs/reviews/verdict/2026-08-08_interface_sweep_round1_crossreview_glm.md`：
逐条命题判定 + 你的探针与实际输出 + BLOCKER/MAJOR/MINOR/NIT 分级 + 独立全量数字。

**⭐ 清单外的自主发现同样欢迎**（08-01 那次你在清单外抓到过一条同族假锁，价值很高），
但请与清单内判定分开列。
