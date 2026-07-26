# 派工单：GT 候选 → 标准答案 受控转正通道（2026-07-26）

- **施工方**：terra（gpt-5.6-terra, high）— GPT 侧执行档
- **审阅方**：GLM-5.2 照主控另出的结构化清单做验证性对抗审（谁写谁不批，跨家族）
- **主控**：Opus 5（出稿 + 轻门 + 最终由主控亲自执行对 sm24 的转正写入）
- **唯一施工契约**：[`AI_agent/proposals/gt_promotion_path_spec.md`](../../proposals/gt_promotion_path_spec.md)（累计式自包含；本派工单不复述其内容，冲突以细稿为准）

---

## 1. 一句话任务

仓库现在**没有**把 GT 候选转成标准答案的实现路径；本批建这条路径，并先把它的地基——「同一张图跑两次结果逐字节相同」——做实。

## 2. 分两阶段交付，第一阶段必须先回报再继续

### 阶段 A（先做、先报）= 细稿 §2 WP-1 可复现

1. **第一步是实证不是修改**：连续两次 `run_p2_conversion`（同源图、同 request、同配置），`cmp` 增广 DXF，把差异**逐处定位**（头变量名 / 实体 / 字段），写进执行日志。已知起点是 `$TDUPDATE`/`$TDCREATE`/`$FINGERPRINTGUID`/`$VERSIONGUID`，**但这不是穷尽清单**——若还有句柄顺序、集合遍历序、临时文件名、浮点格式化等非确定源，一并定位。
2. 按细稿 §2.3 消除，落 §2.4 五条锁。
3. **回报**：把实测非确定源清单 + 两次跑的字节比对证据 + 「可复现化后的 GT 与用户已验收版（`content_sha256 = a1f996f9...`）的逐字段语义 diff」发回主控（细稿 §7 第 5 项）。**预期只有 `generator.manifest_sha256` 与 `content_sha256` 变；若语义有任何其它变化，立即停手上报，不要自行判断"无害"。**

> 阶段 A 的 diff 结果决定要不要请用户重签，所以必须先报。

### 阶段 B = 细稿 §3–§5（WP-2 / WP-3 / WP-4）

主控确认阶段 A 后继续。三块可一次做完，但**必红锁不许留到最后补**——每块的锁与实现同批落。

## 3. 使能 seam（避免在验收纪律上卡轮次）

- 门变异 seam 已存在：`tarch_normalize._apply_test_neuter` + 环境变量 `TARCH_NEUTER_GATE`（[`tarch_normalize.py:143`](../../../src/agent/judge/tarch_normalize.py#L143)）；一一绑定的样板见 [`tests/test_tarch_converter_gate_mutations.py`](../../../tests/test_tarch_converter_gate_mutations.py)（`test_gate_k_is_one_to_one_bound`）。**本批新增的 promote/签署侧前置校验不走这个 seam**，用常规做法：把被测门的判定改成恒真（monkeypatch 或临时源码变异，fresh process），确认**只有**对应用例变红。
- sm24 真源图夹具可直接复用：`tests/test_tarch_converter_p2_geometry.py` 的 `SM24_SOURCE` + `_sm24_request`；staging 纪律用 `tmp_path`（转换器强制 staging 输入，见 `assert_staging_input`）。
- GT 规范字节/内容 hash 用既有 `canonical_gt_v3_bytes` / `compute_gt_v3_content_sha256`，**不要自己拼 JSON**。
- 验签**必须**直调既有 `_verify_human_review_ack`，不得另写一套（细稿 §5.2 第 2 条）。

## 4. 验收纪律（本批的命脉，上两批都栽在这）

1. **neuter 自查表**是交付物之一：每条必红锁 → neuter 什么 → 哪条用例变红 → 是否**只**红该条。表里每一格都要是你**实际跑过**的结果。
2. **诚实披露优于伪装完成**：做不完、或某条锁 neuter 后没变红（= 假锁），照实写并说明，不要伪造表格、不要用"逻辑上显然"代替实跑。项目里 PARTIAL 但诚实的交付被主控当正面样板，伪造的自查表则直接 REWORK。
3. 全仓零回归：当前基线 **1583 passed / 10 xfailed / 0 failed**。跑全量，把原始输出尾部贴进执行日志。
4. 不得放宽任何既有容差、断言、xfail 口径来让新测试变绿。

## 5. 禁区（细稿 §6 的摘要，冲突以细稿为准）

- 不改 `gt.py` 验证状态策略、不放宽 `write_gt_v3_candidate` 保护、不动转换器十门判定与几何/立面算法。
- 不碰 `case_tests/test_baseline/gt/sm21_anchor/**`、`gt_sources/**`、`case_data/**`（sm21 资产逐字节不得变）。
- **不得实际把 sm24 写进 `case_tests/test_baseline/gt/`**——转正写入由主控在轻门后亲自执行。你只交付能力 + 测试。
- 不改 `.gitignore`。

## 6. 交付物

1. 生产代码（细稿 §7 第 1 项）
2. 测试（§2.4 / §3.2 / §4.2 / §5.5 全部必红锁）
3. neuter 自查表
4. 执行日志 `AI_agent/logs/reviews/execution/2026-07-26_gt_promotion_path.md`
5. 阶段 A 的实证材料（§2 第 3 步）

## 7. 汇报格式

回主控时只给：① 做了什么（按 WP 分节）② 完整 neuter 自查表 ③ 全量测试原始输出尾部 ④ 未竟项与已知风险 ⑤ 你认为最脆的一处及理由。**不要长篇自述实现过程**——审阅方只看原始需求 + diff + 测试输出。
