# R1 批 C（安全交付面）· orchestrator 轻门

- **日期**：2026-08-04（北京时间 11:25）
- **被审对象**：`6e06ecf` → `d0e33ef`（施工 = **GLM**，两轮：O-3/O-4 一轮 + O-1 独立窗口一轮）
- **性质**：orchestrator 轻门 = **唯一权威门**。本文覆盖批 C 全部三条 + r2c 收尾。
- **上游**：[派工单](../request/2026-08-04_reading_ruler_batchC_and_r2c_rest_dispatch.md) ·
  [批 B/C 原派工单 §3](../request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md) ·
  [施工执行日志](../execution/2026-08-04_reading_ruler_batchC_glm.md)

---

## 0. 总判定：**批 C 三条全部落地，轻门通过**

| 条目 | 修的是 | commit | 状态 |
|---|---|---|---|
| **r2c-3 / r2c-4 / F-2** | 恒真断言 · 零锁守卫 · 注释误述 | `f7a4991` + `d145023` | ✅ |
| **O-3** | 文件命名契约自相矛盾（图名以 `_view` 结尾的 case 必踩） | `d246c90` | ✅ |
| **O-4** | 注释锚点撑爆画布（3.3 亿像素）+ 无像素预算 | `079ce17` | ✅ |
| **O-1** | **07-08 起每轮识图零渲染**（flat glob 与隔离产物布局错开） | `d0e33ef` | ✅ |

**独立全量**（orchestrator 自跑 `pytest -q -n 6`，工作树仅含 orchestrator 自己的文档改动、⛔ 无 `-m` 过滤）：

```
2106 passed, 10 xfailed, 177 warnings in 444.08s (0:07:24)
```

**2096（批 B 末）→ 2106，净增 10 条锁、零回归。**
⚠️ 上一轮全量出现过 1 红 = `tests/test_zone_agent.py::test_zone_agent_creates_two_zones`
（**跑真实 OpenAI 调用、`APITimeoutError`**；该文件最后改动在 `6d37934`「6.23_DeterministicNaming」，与本批无关）
⇒ **环境红、非确定性**；本轮网络通过、恢复绿。**如实登记，不写成「一直全绿」。**

---

## 1. ⭐ 独立 neuter 五处（覆盖批 C 每条正文实现）

**方法**：`/tmp` 克隆（HEAD `d0e33ef`），每次只改一处 → 跑受影响子集 → `git checkout -- .` 复原（每轮验证零残留）。

| # | 摘掉哪一处实现 | 红了哪几条 | 连带 | 判定 |
|---|---|---|---|---|
| **N-a** | `render_vector_to_png._collect_points` 恢复把 OCR anchor 纳入画布（= O-4 病灶原状） | `test_L51_pixel_ocr_anchor_does_not_blow_up_canvas`、`test_L52_pixel_vs_metric_ocr_anchor_canvas_unchanged` | 零 | ✅ 真绑 |
| **N-b** | 摘掉 `MAX_CANVAS_SIDE_PX` / `MAX_CANVAS_PIXELS` 硬限 | `test_L51_over_budget_structural_canvas_is_refused_not_clamped` | 零 | ✅ 真绑（⭐ 该轮耗时 **12s → 71s**，因为它真的去画那张巨图了 —— **预算有效性的旁证**） |
| **N-c** | `isolation._load_isolated_views` 的 extra-stem 检查置空（= O-3 病灶原状） | `test_merge_per_image_extra_is_rejected`、`test_merge_per_image_view_suffix_misapplied_is_rejected` | 零（两条同源 extra hook） | ✅ 真绑 |
| **N-d** | `run_policy_freeze` 的 `capability_profile_not_declared` 守卫短路（r2c-4） | `test_R1_5_new_run_without_capability_profile_fails_closed` | 零 | ✅ 真绑（**交叉审此前实测为零锁，本轮已补上**） |
| **N-1** | `_finalize_reading_renders` 的 status 恒写 `"complete"`（= best-effort 吞错） | `test_L41_render_failure_records_unavailable_not_complete` | 零 | ✅ 真绑 |
| **N-2** | `_reading_render_status` 恒返回 `"complete"`（守卫失明） | 上条 + `test_L41_failed_render_blocks_review_approval` | 零（同源） | ✅ 真绑 |
| **N-3** | `_render_reading_attempts` 直接 `return []`（= 回到 flat glob 时代） | `test_L40_isolation_aggregate_renders_per_attempt_with_hashes`、`test_L40_render_stage_reading_branch_reads_attempts_not_stage_root` | 零 | ✅ 真绑 |

**⇒ 七处 neuter 全部「摘掉即红、零连带」，无假锁。**
⚠️ 我自己有一次 neuter 脚本写坏了模块（16 红 + 2 error），**该结果作废并重做为精确单行替换**（如实登记）。

---

## 2. 施工方两项自行裁定（已披露，orchestrator 核实后采纳）

1. **渲染失败不阻断纯数值 gate①，只阻断人工 review 批准**。
   理由 = 渲染是交付面（给人看图），不该污染 gate① 的数值判定；failure artifact = `render_manifest.json`。
   **⇒ 采纳**：与派工单「是否阻断纯数值 gate① 可另定，但必须留下机器可见的 failure artifact」一致。
2. **`"missing"`（无 manifest，例如 pre-O-1 的历史 run）不阻断，只有「试过且失败」(`unavailable`) 才阻断**。
   **⇒ 采纳**：这是向后兼容的正确做法，且 `missing` / `unavailable` 两态**可区分**
   （不是把历史 run 伪装成 complete）。

---

## 3. 边界合规

| 项 | 结论 |
|---|---|
| `gt/**` 与 sm24 `testdata_prompt.json` 零字节改动 | ✅ `git diff --name-only` 零命中 |
| 未读 GT（L-40 fixture 自造合成 aggregate） | ✅ |
| 未 push | ✅ |
| 未动 `AI_agent/` 下除施工方自己两份执行日志外的管理文档 | ✅（工作树里的 CLAUDE.md / decision_log / plan / lightgate 改动是 **orchestrator 自己的**） |
| stash 处理 | ✅ 用 `apply` 取回、**未 pop**，stash 仍在 |
| 未顺手做批 D / 批 E / R1.5 | ✅ |

---

## 4. 下一步

1. **Claude 侧子代理交叉对抗审批 C**（施工 = GLM ⇒ 审 = Claude，「谁写谁不批」满足；本批不启 GPT 侧）。
2. 交叉审若无 BLOCKER ⇒ **批 C 收口 ⇒ 批 A/B/C 三批全绿**
   ⇒ **⛔「不得发布识图分数 / 变好变坏结论」这条硬约束随之解除**。
3. 然后是 **R1.5（坐标来源改造 = 接口层强制测量）**，问题书已就绪。
   **⛔ 纪律：不得先跑新基线再补方向证据**（否则「方向错」与「画错」混成同一个低分）。

---

## 5. ⛔ 交叉审改判本轻门（2026-08-04 11:50）：**REWORK · 1 BLOCKER**，且 orchestrator 轻门有同一处盲区

[交叉审报告](2026-08-04_reading_ruler_batchC_crossreview_claude.md) 判定 **REWORK（1 BLOCKER / 3 MAJOR / 3 MINOR / 2 NIT）**。
**orchestrator 已逐条独立核实，全部属实**，本轻门 §0「轻门通过」**据此改判为不通过**。

### 5.1 ⭐ 我的盲区（与批 B 那次同族，本夜第二次）

**BLOCKER 的形状与批 B 完全一样**：

> **修好的是「在硬隔离那条布局上生效」，没修好的是「在所有真实路径上都生效」。**

**我的七处 neuter 全部使用隔离 fixture**（`attempts/NNN/output.json` 那条布局），
**没有一处走「judge 打回 ⇒ 盲重读」的恢复路径**（flat `0_reading/*_view.json`）
⇒ 我验出的「七处摘掉即红、零连带」全部成立，**但它们证明的是同一条路**。

**⇒ 纪律升级（写进 r1 派工单 §4 首条）**：
> **neuter 不仅要覆盖「派工单正文点名的实现」（08-04 凌晨那条教训），
> 还要覆盖「会踩到该缺陷的每一条真实路径」。**
> 「七处都红」若七处走的是同一条路，证明力等于一处。

### 5.2 核实结论（三条最硬的，orchestrator 亲核）

| finding | 核实 |
|---|---|
| **F-1 BLOCKER** `run_stage.py:690` + `:717` | ✅ 属实。空 view 集合被 `view_records and not any_failed` 判为 `unavailable` ⇒ **盲重读路径渲染归零 + 反过来拒批一个健康 run**；同一输入在 `079ce17`（O-1 前）渲得出两张 PNG ⇒ **O-1 引入的回归** |
| **F-3 MAJOR** `isolation.py:694` | ✅ 属实。生成给读图器的 `kickoff_prompt.md` **逐字仍写 `<name>_view.json`** —— 正是 O-3 从 `session_kickoff.md` 删掉的那条推导，**且它是读图器收到的第一条指令** ⇒ O-3 的正文诉求没落全 |
| **F-4 MAJOR** `render_vector_to_png.py:150-154` + `checks/reading.py` | ✅ 属实。gate 侧对 OCR anchor **零检查**（该文件仅 `_ROOM_LABEL_BASES` 一处无关命中）⇒ **3.3 亿像素曾是坏 anchor 的唯一信号，移走症状却没补检测 ⇒ 坏数据比原来更难发现** |

### 5.3 反向坐实（施工方的锁没有问题）

交叉审**八处独立 neuter 全部「摘掉即红、零连带、走真实入口、断言落具体产物字段」，零假锁**，
与本轻门 §1 台账逐条吻合；**六次证伪失败**（approve-review 无旁路入口 / 八锁无假锁 /
O-4 无合法 metric annotation 误拒 / `1_correction` 分支无连带 / r2c-3 四条断言互斥可区分 / 受保护件零触碰）。
**⇒ REWORK 的是覆盖面，不是实现质量。**

### 5.4 处置
**已派 r1 返工**（[派工单](../request/2026-08-04_reading_ruler_batchC_r1_rework_dispatch.md)，施工仍为 GLM）。
r1 落库后重跑轻门（**neuter 必须包含盲重读恢复路径**）+ 再次交叉审。**批 C 未收口 ⇒ 三批全绿的硬约束仍未解除。**

---

## 6. r1 返工中途轻门（2026-08-04 12:50）：**已落 3 条，全部真绑；剩 4 条未做**

**施工席 12:31 第二次撞 GLM 5 小时额度上限**（14:25 复位）⇒ r1 七条只落了前三条。
**orchestrator 不等复位，先对已落部分做轻门**（不占施工席额度，且能提前暴露问题）。

| commit | 条目 | 内容 |
|---|---|---|
| `fdb31c0` | **B-1（BLOCKER）** | 渲染同时认两种真实布局（aggregate `{"views":…}` 与 flat `{stem: view}`）+ **空图集落成新的 `empty` 状态、不再当渲染失败** |
| `484852a` | **M-1** | 产物读不出 ⇒ 落机器可读 failure manifest（`unavailable`，与 `missing` 可区分） |
| `f254c56` | **M-2** | 发给读图器的 kickoff 指令改为按 `expected_output_id` 命名，并**明写**「⛔ 不要给 PNG 名加 `_view`」 |

**独立全量**（orchestrator 自跑 `pytest -q -n 6`，⛔ 无 `-m`）：

```
2115 passed, 10 xfailed, 177 warnings in 375.96s (0:06:15)
```
**2106 → 2115，净增 9 条锁、零回归、零环境红。**

### 6.1 独立 neuter 四处（⭐ 本轮起：neuter 必须走「会踩到该缺陷的那条真实路径」）

⚠️ 按交叉审登记的环境坑，克隆内一律 `PYTHONPATH=$PWD`（否则 editable `.pth` 会解析回主仓、等于没做）。

| # | 摘掉哪一处实现 | 红了哪几条 | 连带 | 判定 |
|---|---|---|---|---|
| **N-1** | 形状识别只认 aggregate（= B-1 病灶原状） | `test_L40_flat_flow_blind_reread_renders_and_approves`（**该锁自己走真实 flat 恢复路径、非隔离 fixture**） | 零 | ✅ 真绑 |
| **N-2** | 空图集又判回 `unavailable`（= 反向拒批健康 run 的那一半） | `test_L41_empty_view_set_is_not_render_failure` | 零 | ✅ 真绑 |
| **N-3** | 失败 manifest 不落盘（M-1） | `test_L41_unreadable_output_records_failure_artifact_not_missing`、`test_L41_render_loop_survives_catastrophic_attempt` | 零 | ✅ 真绑 |
| **N-4** | kickoff 文案精确回退到 `<name>_view.json`（M-2） | `test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix` | 零 | ✅ 真绑 |

**⇒ 已落三条全部「摘掉即红、零连带」，且 B-1 的锁确实走的是盲重读那条真实路径**（= 我上一轮的盲区已被覆盖）。

⚠️ **如实登记：N-4 第一次我写歪了**（正则替换命中无关字符串 ⇒ 零红），**该结果作废**，重做为逐字精确回退后才得上表结论。
**这是本日第二次 orchestrator 的探针脚本自身出错**（前一次是 16 红 + 2 error 那次）
⇒ **纪律：neuter 脚本必须逐字精确匹配目标实现，且「零红」在确认脚本命中之前不得当结论。**

### 6.2 未做（等 14:25 额度复位后续派）
**M-3**（gate① 侧补 OCR anchor frame/bounds 检测 —— 「移走症状没补检测」那条）·
**N-1**（`missing` 分支零锁）· **N-2**（L-50 零增量约束力、O-3 命名规范本身仍零锁）·
**N-3**（`MAX_CANVAS_SIDE_PX` 撞不变量 #6：单边 >182 m 的建筑永远渲不出）。

**⇒ 批 C 仍未收口；三批全绿的硬约束仍未解除。**
