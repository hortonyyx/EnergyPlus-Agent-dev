# 审阅单 · 硬隔离脚手架批（sol 升一档交叉对抗审）

> 主控 Opus 5 · 2026-07-31 · 收件人 = sol（GPT 侧顶档）
> 被审对象 = GLM-5.2 的施工：`78967eb` S1 / `c42de85` S2 / `f2a4efb` S3 / `c9974fd` S4 + 返工 r1
> **谁写谁不批**：GLM 施工，你审，跨家族。**只审不修。**

---

## 1. 这批在修什么

2026-07-30 sm24 端到端跑测第一次尝试。**硬隔离识图机制（2026-07-08 落地）第一次在真实 case 上跑**，
撞出四个脚手架缺陷。同一轮里，识图质量从 2026-07-07 的**同模型同工具 8/8 满分掉到 1/8**，
判为**机制退化而非模型能力**。本批修的就是嫌疑机制 —— 所以它不是体验优化，是识图质量的直接杠杆。
（历史实证：2026-06-25 已坐实「脚手架退化 = 墙退化主因且可恢复」。）

派工单（含验证过的事实 A–K 与死骨架）：
[`2026-07-31_isolation_scaffold_construction_dispatch.md`](2026-07-31_isolation_scaffold_construction_dispatch.md)
返工单 r1：[`2026-07-31_isolation_scaffold_rework_r1.md`](2026-07-31_isolation_scaffold_rework_r1.md)
执行日志：[`../execution/2026-07-31_isolation_scaffold_glm.md`](../execution/2026-07-31_isolation_scaffold_glm.md)

改造前基线 `f98d248` = 全仓 **1786 passed / 10 xfailed / 0 failed**。

---

## 2. 你要重点打的地方

这批**同时放松和收紧了一个安全边界**，所以最大的风险是「放松那半做过头、收紧那半是假的」。

### A · 守卫的净效果必须更严，不是更松（最高优先级）

S2 把守卫拆成两半：
- **收紧**：新增写保护 —— Write/Edit 只许落 `out/**` 与 `requests/**`。
  这堵的是主控预扫发现的**真逃逸面**：改造前子代理可以直接覆写 `tools/run_cv_probe.py`
  （Bash 白名单唯一放行的可执行文件），然后用合法命令执行任意代码。
- **放松**：路径类禁词（`DENY_TOKENS` / `~` / `..`）不再扫散文内容。
  返工 r1 进一步改成**按参数角色**判定：`content` / `new_string` / `old_string` 整个免扫。

**请你活体验这八条安全性质在改造前后都仍然 deny**（派工单 §3-S2 列的验收红线）：
读 `gt.json` / `case_tests` 路径 / 越界绝对路径 / 越界 symlink / 非白名单命令 /
`python -c` / 复合 shell token / 请求 JSON 内含禁词。
**任何一条变成 allow 即交付失败。**

并请你自己找**新的逃逸面**：写保护的允许集是 `out/**` + `requests/**`，
想想有没有办法从这两个目录里绕出去（符号链接、`..` 组合、请求 JSON 里塞路径、
`_path_arg` 的 `resolve(strict=False)` 语义、大小写、非规范化路径……）。
主控只验了六条正/负例，覆盖面肯定不全 —— **这块是派给你的探索性部分**。

### B · 施工方自己登记的五条边界，请独立判它们是否被低估

GLM 在 review-ask 里如实登记了五处「照骨架做、未自行加宽」的边界（这是正确纪律，不是问题）。
但**主控已经证实其中一条被低估了**：S2b 原按「整串 `_looks_like_path`」实现，
主控实测发现 content 里同时出现一个 `/` 与一个禁词就仍被拒 —— **一个日期 `2026/07/31` 就够**，
于是发了返工单 r1 改成按参数角色。

⇒ 请你用同样的标准审剩下四条，判断哪些同样被低估：
① `settings.json` 加 `requests/**` 写权限（施工方判为「为可用做的最小一致改动，非放松」）；
② S3 嵌套检测只查末级目录名 ∈ {`cv_evidence`, `prescan`}，末级是 stem 的套娃不被拦；
③ S3 锁 #2 的 neuter 做在 oracle 侧（关掉 `_is_run_prescan_path`）而非改 CLI 落点布局；
④ S4 多件检测扫 `*_view.json`，未来 `expected_output_id` 若不以 `_view` 结尾会漏。

### C · 假锁

施工方给了每个 Slice 的 neuter 自查表。**请抽验，不要采信。**
在 `/tmp` 克隆里做定点破坏、真跑、对账它声称变红的测试名。
本项目在这一点上栽过至少三次（2026-07-22 九门 7 门假锁 / 2026-07-27 连续三轮 false-lock）。

重点抽这几把：
- S1 的样板件正例/负例（摘掉拷贝调用是否真红）+ **kickoff 路径与 staging 实际落点的一致性锁**
  （它必须真去 stat 文件，不能是硬编码字符串比对）；
- S2 的写保护负锁（`Write tools/run_cv_probe.py` ⇒ deny）；
- S4 的「聚合零内容改动」「缺件必红」「多件必红」。

### D · S1 的溯源完整性

F-2 的**主要价值**不是「让子代理能读到样板件」，而是**让它进 `MANIFEST.json`**
——07-30 主控手工补入的那份不在 MANIFEST 内，导致 merge 的溯源清单漏记该件。
请确认 build 后样板件确实在 MANIFEST 里、且 hash 与仓库源一致，
并确认 `_assert_manifest_clean` 的污染检查**没有为此被放宽**。

---

## 3. 纪律

1. **只审不修**：发现问题写裁决书，不动生产码。
2. **活体探针优先于读码**：本项目的经验是活体探针能抓到静态审漏掉的必崩缺陷。
3. **`/tmp` 里克隆做破坏**，不要在主工作树里 neuter。
4. **不碰** `case_tests/test_baseline/gt/**`。
5. 本轮另一席位（sol 自己）在改 `src/agent/judge/**` —— 那是你自己的另一批，
   审这批时**不要混进去**；若全仓跑出 judge 侧失败，单独报给主控。
6. 裁决书落 `AI_agent/logs/reviews/verdict/2026-07-31_isolation_scaffold_sol.md`，
   结论用 APPROVE / APPROVE-WITH-CHANGES / REWORK，finding 按 BLOCKER/MAJOR/MINOR/NIT 分级。
7. 回主对话只给 terse 简报，不贴 diff。
