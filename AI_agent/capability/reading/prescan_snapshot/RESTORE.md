# prescan 代码快照 + 恢复说明

> **⛔ prescan 是【延后】不是【放弃】**（用户 2026-08-19 明确：
> 「prescan这条路不是说放弃了，是统一收到 reading 专项到时候一起考虑，这些方案和代码也不要丢了呀」）。
>
> 2026-08-19 把它从活代码里摘掉，是为了终结它 **08-15 → 08-19 的半死状态**——
> 实现还在、而 `run_cv_probe.ALLOWED_TOOLS` 已不列它 ⇒ **读图器根本调不到，只有 orchestrator 能前置**。
> 三者（放回授权表 / 保持 orchestrator 前置 / 删掉）里，那个半死状态是最差的一个。
> **本目录保证「删掉」这一步不损失任何方案与代码。**

## 一、快照内容（全部取自 `0cfa289`，删除前最后一个提交）

| 文件 | 原路径 | 行数 | 说明 |
|---|---|---|---|
| `recipes_with_prescan.py` | `src/agent/reading/cv_toolbox/recipes.py` | 904 | **主体**：`_prescan` / `prescan_plan` / `prescan_elevation` + 全部候选生成机器（line band / cc box / **tick** / long-line 合并 / 覆盖记账 / overlay 绘制 / 可复算 JSON 落盘）+ 6 个 `prescan_*` 配方常量 |
| `cv_probe_with_prescan.py` | `scripts/tool_scripts/cv_probe.py` | 350 | 两个子命令 `prescan-plan` / `prescan-elevation` + `_reject_nested_prescan_out_dir`（F-1 套娃路径防护）+ dispatch |
| `test_cv_toolbox_with_prescan.py` | `tests/test_cv_toolbox.py` | 746 | 含被删掉的 **419 行** prescan 用例：schema / kind 视图无损可寻址 / overlay 只画结构层 / 有界分段不跨全图 / 幂等 / 跨输出根逐字节一致 |
| `isolation_prescan_fragments.py` | `src/agent/execution/isolation.py` 三处 | 52 | `_copy_prescan`（前置候选拷进 staging）· `_is_run_prescan_path`（拷贝白名单唯一放行 `run_*/` 的例外）· kickoff 里介绍预扫产物的段落 |

⚠️ 快照是**整文件**（除 isolation 片段），因为 prescan 与其宿主文件的其余部分交织；
恢复时按下表取差集，⛔ 不要整文件覆盖回去——宿主文件此后还有别的改动。

## 二、恢复方式（两条，任选）

**A · 直接从 git 取**（权威，零漂移）：

```bash
git show 0cfa289:src/agent/reading/cv_toolbox/recipes.py
git show 0cfa289:scripts/tool_scripts/cv_probe.py
git show 0cfa289:tests/test_cv_toolbox.py
git show 0cfa289:src/agent/execution/isolation.py
# 删除这一笔的完整 diff：
git log --oneline --all -- src/agent/reading/cv_toolbox/recipes.py
```

**B · 用本目录快照**（不必做 git 考古；内容与 A 逐字节相同，`sha256` 见下）。

## 三、恢复时必须一并处理的六处（否则会回到半死状态）

1. `run_cv_probe.ALLOWED_TOOLS` 加回 `prescan-plan` / `prescan-elevation` —— **不加回它，读图器仍调不到。**
2. `guard.py` 的 `PROBE_DIRECT_PARAM_KEYS` 加回 5 个键：
   `capability_profile` / `no_cc` / `min_strength` / `min_line_len_px` / `label`。
3. `run_cv_probe.BOOLEAN_FLAG_KEYS` 加回 `no_cc`。
4. `isolation._assert_rel_allowed` 恢复 `run_*/` 子树的 prescan 例外（否则前置候选拷不进 staging）。
5. `tests/test_substrate_sweep_policy.py`：`test_g8_dead_keys…` 的期望值、
   `test_g8_wrapper_boolean_flag_keys…` 的期望值、`test_f53b_unknown_tool…`（现用不存在的工具名钉 **F-56**，
   历史上曾以 prescan 为载体）三处要一起重定。
6. `tests/test_gt_discipline.py::test_prescan_stays_deleted_until_the_reading_专项_decides_otherwise`
   —— **这把哨兵就是为了拦住「无决定的悄悄恢复」**，恢复时应连同专项的决定记录一起改写它，⛔ 不要直接删。

## 四、⭐ 恢复前先读这两条实测结论

1. **预扫候选被消费、但在产物里不可见**：2026-08-19 的 P1 臂 transcript 里 `prescan` 出现 **676 次**，
   最终产物引用 `candidate_id` **0 次**；07-08 那次同样是 0。
   ⇒ **「用没用预扫」在产物上不可观测，只有 transcript 分得开。** 恢复时应一并解决可观测性。
2. **`tick_candidate` 是它最有价值的产物**：预扫对 1f 产出 **234 个 tick_candidate**（亚像素，如 `493.1994`），
   而 [reading 专项 §9.1](../improvement_methodology.md) 的根治修法「标定锚只收 `candidate_id`」
   **正需要一个机器检出的 tick 来源**。⇒ **prescan 恢复与根治修法很可能是同一件事，应合并考虑，⛔ 不要分开决策。**

## 五、决策归属

放回授权表 / 保持 orchestrator 前置 / 不恢复 —— **三选一归 reading 专项**，
见 [`../improvement_methodology.md` §9.6](../improvement_methodology.md)。

## 六、快照 sha256

```
16bc7e49b2c08a28547659d706ebbdb10d6db4f14243272f648c74c3dfcf59b8  cv_probe_with_prescan.py
0c9a3d0ff82d41523c1fad6ad37aaa5c1f3c830789bcf6639a32f5467ad007c2  isolation_prescan_fragments.py
1c3f7586366b483f2109af27bdce3634f56f2e7dd50ef24cde3bc2b6d504ebd9  recipes_with_prescan.py
e78a5fbec38458991338c0a82837cc82ac598cf140f9fd6c1115f8af17d6b428  test_cv_toolbox_with_prescan.py
```
