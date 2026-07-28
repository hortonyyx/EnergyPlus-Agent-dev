# 审阅单 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」施工批（GLM-5.2 验证性对抗审）

> **审阅方 = GLM-5.2**（GLM 侧）/ **施工方 = sol**（GPT 侧，谁写谁不批）/ **轻门 = 主控 Opus 5**。
> **你的任务 = 验证性对抗审**：不是重新设计，是**逐条查「声称是否等于实况」**、**查锁是否真绑**。
> 你的能力画像里这类任务是强项（结构化清单验锁达顶档）；**探索性猜测不是本单要的**。

---

## 0. 一句话背景

判卷器此前有三处立足点靠隐含假设：**谁有资格判红**（执行顺序 / 错误文案决定）、**有没有多收钱**（两个浮点总量相减）、**两个坐标凭什么算同一个**（来源身份丢失后靠距离反推）。本批把三者换成**可复算的证书**。**该批此前已连续三轮被判 REWORK**，故本轮验收标准极严。

---

## 1. 材料（全部已入库）

| 材料 | 路径 |
|---|---|
| **施工基线（唯一权威，1380 行累计式自包含）** | [proposals/judge_arbitration_and_provenance_plan_sol.md](../../../proposals/judge_arbitration_and_provenance_plan_sol.md) |
| **派工单 + 主控五道轻门裁定（§8–§12）** | [request/2026-07-28_judge_arbitration_construction_dispatch.md](2026-07-28_judge_arbitration_construction_dispatch.md) |
| **施工执行日志（含 neuter 自查表 / DoD 自评 / D-1 / D-2）** | [execution/2026-07-28_judge_arbitration_sol.md](../execution/2026-07-28_judge_arbitration_sol.md) |
| **sm24 正门逐行 diff + 机器比较证书** | `AI_agent/logs/reviews/execution/artifacts/judge_arbitration_slice4/comparison/` |
| 设计轮审轨（背景，不必通读） | [GLM 设计审](../verdict/2026-07-28_judge_arbitration_design_glm.md) · [主控终审](../verdict/2026-07-28_judge_arbitration_design_controller_final.md) |

**提交范围**：`cce6e83`（批前基线）→ `67b9c00`（施工末态）。中间 Slice 提交：`7071892`/`d20daef`（S0）· `c59e4bc`/`a4ee2dc`（S1）· `0b62a49`/`8556918`（S2）· `2193748`/`11f061b`（S3）· `67b9c00`（S4）。

**主控已独立复跑的数字（你须独立复算，不得采信）**：全仓 `1782 passed, 10 xfailed, 0 failed`；批前基线 `1725 passed`。

---

## 2. 验收基准（逐条判定，每条给「成立 / 不成立 / 无法判定」+ 证据）

**基准一 = 设计稿 §10 的 16 条 Definition of Done。** 施工方在执行日志 §34 给了 16 行自评、全部标 PASS。**逐条独立验，不得采信自评。**

**基准二 = 设计稿各节的机械验收锁与指定 neuter**（§3.6 C / §4.6 A / §5.8 B）。

**基准三 = 派工单 §8–§12 的全部主控裁定**（共 10 条欠规格裁定 + 1 条主控独立发现的必修项）。**这些与设计稿同等约束力**，逐条验是否落地。

---

## 3. 命脉命题（**这几条不成立即 REWORK**，请优先且用活体探针验）

| # | 命题 | 什么算不成立 |
|---|---|---|
| M-1 | **不存在第二条严重性路径**：计分路径上所有 identity 类 `ScoreContractError` 的严重性**均由 `certify_and_arbitrate_request` 决定** | 找到任一绕过仲裁器的本地定案点 ⇒ 不成立。**这是本批第一次和第三次 REWORK 的原型（R2-B1 / R3-B1）** |
| M-2 | **`reason` 永不参与严重性判定**，只作展示 | 找到任何按 reason 字符串决定红/NA 的分支（含白名单换皮）⇒ 不成立 |
| M-3 | **豁免位 `exact_error_context` 被三把锁封闭**（只能来自 `_raise_score_input_contract` / 该 helper 只用于 `typed_score_input_contract` / 该路径严重性仍由仲裁器决定） | 任一锁可被 neuter 而不变红，或能构造新调用点设该位且全仓不红 ⇒ 不成立。**此条是主控轻门独立发现，非施工方自报** |
| M-4 | **来源身份贯穿到底**：不存在「传了 source key 又退回 `raw float -> rep`」的旁路；**legacy float 通道已物理删除** | 全仓仍能找到 float 分支进入身份聚类 ⇒ 不成立 |
| M-5 | **守恒是结构性判据**（区间原子 owner 重数），不是两个浮点总量比较；**`extra` 结构上不可能为负** | 找到 `length − covered` 式回流、或能构造负 extra ⇒ 不成立 |
| M-6 | **答案原子与分母是答案字节的纯函数**（尺子不被被测物变形） | 同一答案配不同产品得到不同原子/分母 ⇒ 不成立 |
| M-7 | **sm24 已签字答案零字节改动** | 受保护树任一 hash 变化 ⇒ 直接失败 |
| M-8 | **真实 sm24 对外可见判分零变化**：`public_rows.jsonl` 与 `wall_criteria.jsonl` 的 baseline/new SHA-256 相同 | hash 不等、或存在未被 exact 证书解释的 row/status/pairing/criterion/denominator 变化 ⇒ 不成立 |

---

## 4. 点名复核项（主控已看过，要你独立再看一遍）

1. **DoD #16「每个指定 neuter 实跑」**：执行日志声称 Slice 1/2/3/4 全部 neuter 在 `/tmp` 实跑并记录真实红数。**抽查至少 6 个**，自己在 `/tmp` 副本重跑，核对红数与声称是否一致。**本批 r1 栽过一次「自查表声称大于实况」。**
2. **施工方自查出的两处假锁**（执行日志 §27）：B-L5 入口预排序遮蔽 accumulator neuter / B-L7 整数夹具对旧减法不敏感。**验证其修法真的让 neuter 变红**（这两处是施工方自己抓的，正因如此更要独立复核）。
3. **D-1 的执行边界**（派工单 §12.1）：因历史 accepted 产物早于 B5 proof wire，D-1 走的是 **reading 正门**而非 correction 正门。**验证主控裁定的三条实质要件确实满足**：两侧输入逐字节相同 / 两侧都走真实 `score_typed_attempt` / 无手造 `PlanSegment` 绕过 scorer。
4. **§9.2(1) 裁定**：「候选归并会坍缩已声明边」是 C-3 **之前**的独立结构 witness——验证其判定**不随门的执行顺序改变**。
5. **helper 身份**精确为 `b4b_segment_score_v3_ic1`、无 v2 union 残留、identity contract `"1"` 交叉验证。

---

## 5. 纪律

1. **只审不改**：不得修改任何生产码或测试。neuter **只在 `/tmp` 副本**做，做完还原。
2. **独立复算**：数字一律自己跑，不采信执行日志与主控的任何数字。
3. **活体探针优先于读码推断**：能构造输入证伪的，就构造输入。
4. **每条判定必须给证据**（命令 + 输出片段），不接受「看起来正确」。
5. **不得改 `AI_agent/CLAUDE.md`**（07-26 有审阅方越界改管理文档被判 MAJOR 的先例）。
6. 裁决书落 `AI_agent/logs/reviews/verdict/2026-07-28_judge_arbitration_construction_glm.md`，格式：结论（APPROVE / APPROVE-WITH-CHANGES / REWORK）+ 逐条判定表 + BLOCKER/MAJOR/MINOR 分级 + 每条的复现步骤。

---

## 6. 给你的提示（本批历史，帮你定位高危区）

- 三轮 REWORK 的**共同结构**是「机制选对、边界留给施工方猜」。本轮把边界写进了设计稿本体 + 主控裁定，**所以你要查的是「边界是否真的被执行」，而不是「边界定得对不对」**（后者已过审）。
- 本批出现过的假绿形态，按出现顺序：① 一条产品墙同时覆盖两道答案墙拿满分；② 多画一条 5e-10 斜边就让真拓扑破洞降级为「量不了」；③ reason 白名单让白名单外的真红被洗成 NA。**验的时候优先构造这三类的变体。**
- 施工方本轮**主动上报 10 处欠规格边界、自查出 2 处假锁**，姿态良好；但**姿态不是证据**——请照常严格。
