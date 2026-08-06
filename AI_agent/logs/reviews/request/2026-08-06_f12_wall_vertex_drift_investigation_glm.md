# 调查单 · F-12：下游重建的墙顶点与内核 snapshot 不一致

> **⚠️「调查单」—— ⛔ 不写病因假设、⛔ 不写修法、⛔ 不写验收条件。⛔ 只调查，不改生产代码。**

- **日期**：2026-08-06 · **席位**：GLM-5.2，主工作树 · **基点**：`6.15_ValidationArchM0toM4` @ `756e821`

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 756e821
git status --short       # 期望：4 个 case_tests 未跟踪目录 + 本单 + 证据目录
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```
⛔ 绝不 `git add -A`。

## 1. ⛔ 安全边界

- 触发下游图**必带 `timeout`**、⛔ 不接 `| tail`（DeepSeek 按量计费）
- ⚠️ 现在跑真链路会**先跑满 surface/fenestration/hvac/people/lights（约 10 分钟）**，
  然后在 `validate` 撞 F-12 并因熔断（4 轮）中止 —— **代价不低**
- ✅ **优先找不烧钱的离线路径**（§3 给了三份现成证据），跑真链路前先问自己：这一步非跑不可吗

## 2. 现象（**已验证事实**）

F-11 修好后第一次跑通全部下游节点（13 个：`intake·material·zone·schedule·cross_ref_foundations·
construction·surface·fenestration·hvac·people·lights·cross_ref_complete·validate`），
在 **`cross_ref_complete` / `validate`**（**正确位置**，几何已建完）报出：

```
output-coordinates[VERTEX_FRAME_DRIFT]: 'Z01_W1' vertices differ from the pre-E4 snapshot
```

**⭐ 形态（orchestrator 已统计，你可自行复核）：**
- **44 条，全部是墙（`_W*`）**
- **楼板 `_Floor` / 天花 `_Ceiling` / 窗 `FenestrationSurface` —— 零漂移**
- **14 个区全中**（Z01–Z14）
- **错误类型只有 `VERTEX_FRAME_DRIFT` 这一种**
- 措辞是 **`vertices differ from`**（面存在、顶点对不上），**不是** F-11 那个 `missing from ConfigState`

**⚠️ 这是门在正确位置抓到的问题，⛔ 不是门坏了。** E4 契约门就是为守不变量 #1
（**代码做所有几何，LLM 不碰几何**）而设的。

## 3. 现成证据（**三份，全部离线可读，零成本**）

```
# ① 我们交出去的（内核产出）
case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json
    → surface_specs（15865 字符的 IDF 文本，内核造的面）

# ② 契约里冻结的期望顶点
case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/output_coordinate_snapshot.json
    → records（115 条，字段 object_type / name / zone_or_parent / vertices）

# ③ 那次真链路跑的完整日志（已入仓）
AI_agent/logs/experiments/2026-08-06_f12_wall_vertex_drift/downstream_run.log   （530 行）
```

**⇒ ①②之间是否已经不一致，是可以完全离线判定的。** 先做这一步再决定要不要烧钱跑真链路。

相关代码：`_vertex_drift_issues`（`src/validator/output_coordinates.py:794`）·
下游 surface 节点（`src/agent/nodes/` 下）· 图拓扑 `src/agent/graph.py`。

## 3.5 ⭐ Q2 已由 orchestrator 离线判定（**已验证事实，可自行复核；⛔ 这不是假设**）

**结论：内核产出与契约 snapshot 完全一致 ⇒ 分界不在本项目侧，顶点是在下游重建时被改掉的。**

复现（纯读盘、零 LLM、约 2 秒）：解析 `intake_output.json` 的 `surface_specs`
（格式 = 散文 + 项目符号，每行 `- <名> (<属性>): (x,y,z)-(x,y,z)-…`），与 `output_coordinate_snapshot.json`
的 `records[].vertices` 逐面比对（浮点 round 到 3 位）：

```
snapshot = 115 条  = 100 个 BuildingSurface + 15 个 FenestrationSurface(*_Win1)
surface_specs 解析 = 100 个面（⚠️ 不含窗，窗在 fenestration_specs）
共有 100 面 → 逐字节相同 100 · 不同 0
```

**⇒ Q2 答案：①→② 一致。⛔ 不要再花代价重查这一步。**
**⇒ 剩下 Q1（漂移长什么样）与 Q3（为什么只有墙）需要「下游实际建出来的顶点」——
那次真链路日志里没有顶点数据（只有 `created successfully`），run 目录也无落盘（跑到 validate 就熔断中止）。
⇒ 需要一次定向重跑；⚠️ 建议只驱动 `surface` 那一段（一次 LLM 调用，约 4 分钟），
⛔ 不必重跑整条下游（约 10 分钟且末尾必撞熔断）。**

**⇒ ⚠️ 责任边界变得关键**：按 CLAUDE.md §3，下游 9 subagent 的 **prompt 演进归协作者维护**
（本地有完整可跑代码，但 prompt 不归本项目）。**Q6 因此升级为必答项**。

## 4. 边界

⛔ 不改任何 `src/` `scripts/` `skills/` `tests/` · ⛔ 不 commit 不 push · ⛔ 绝不 `git add -A` ·
⛔ 不碰 `case_tests/` 未跟踪目录 · ⛔ **不放宽 `_vertex_drift_issues` 或它的容差** ·
✅ 一次性脚本放 `/tmp` · ✅ 可读 git 历史

## 5. 请你回答的（交付物）

1. **⭐ 漂移到底长什么样？** 取几个代表面，把**三方顶点并排列出来**：内核 `surface_specs` 里的 /
   snapshot 里的 / 下游最终建出来的。**是平移？是顺序不同？是数量不同？是精度？** 给具体数字。
2. **⭐ 分界在哪一步？** ①→② 就已经不一致，还是①②一致、下游重建时才变的？**这决定了责任方完全不同。**
3. **⭐ 为什么只有墙？** 楼板/天花/窗零漂移是**最强的线索**——解释这个不对称。
4. **⭐ 定性 + 2–3 个修法选项及后果代价**（含"什么都不改会怎样"）。**⛔ 不要动手修。**
5. 是否与 F-5/F-7/F-10/F-11/墙 3 同族？是哪一种形状？
6. ⚠️ **附带**：若查明是下游 subagent 在重新推导几何，**请明说它违反的是不变量 #1 的哪一条边**
   （这关系到修法该落在本项目侧还是协作者维护的 prompt 侧 —— 见 CLAUDE.md §3 责任范围）。

## 6. 证据纪律（硬要求）

> ⛔ **不接受「我看了 / 我读了」** —— 每条结论给**可独立重跑的命令 / 路径+行号 / 具体数字**。
> ⛔ 涉及「顺序 / 对称 / 方向」的判断，先证明载荷本身有分辨力
> （08-05 有一份调查栽在这条上：拿一张左右完全对称的图去判方向）。

## 7. 交付

日志落 `AI_agent/logs/reviews/execution/2026-08-06_f12_wall_vertex_drift_investigation_glm.md`；**先落骨架再补**。

## 8. 停下上报（**记功不记过**）

本轮至今 **8 次「停下/如实上报」，8 次都是派工方（我）的题错了**
（最近一次 = 我把「≤300s」和「五个 subagent 都跑到」写成了不可同时满足的条件）。
本单事实与你看到的不符 / 提法有问题 / 真相与本单框架不兼容 ⇒ **立刻停下上报**。
