# 调查单 · F-11：下游 LangGraph 死循环 + foundations 阶段校验尚未存在的面

> **⚠️「调查单」——⛔ 不写病因假设、⛔ 不写修法、⛔ 不写验收条件。⛔ 只调查，不改生产代码。**

- **日期**：2026-08-06 · **席位**：GLM-5.2，主工作树 · **基点**：`6.15_ValidationArchM0toM4` @ `9b6a7ff`

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 9b6a7ff
git status --short       # 期望：4 个 case_tests 未跟踪目录（含 run_2026-08-06_wall3_a_retest）
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```

## 1. ⛔⛔ 安全边界（最重要，先读）

**这条链路会无限循环并持续调用 DeepSeek —— DeepSeek 是按量计费（真金白银）。**
orchestrator 已实犯：一次跑了 **1 小时 40 分、约 400 圈**才发现。

- ⛔ **任何触发下游图的命令都必须带 `timeout`**（建议 ≤180s）
- ⛔ **不许**不带超时地跑 `scripts/run_full_pipeline.py`
- ⛔ **不许**用管道接 `| tail`（会缓冲掉全部进度日志 —— orchestrator 就是这么瞎了 100 分钟）
- ✅ 优先用 §3 的**探针**（抓到即 `SystemExit`，一次 pass 约 20 秒）

## 2. 现象（**已验证事实**，每条附复现方式；⛔ 这些是事实不是假设）

用今晚 5_intakeoutput 首次产出的 intake 跑下游：

```bash
timeout 150 python scripts/run_full_pipeline.py sm21_anchor \
  --intake-from run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json \
  --output-subdir run_2026-08-06_wall3_a_retest --no-simulate > /tmp/f11.log 2>&1
```

**观察到的节点序列，每 ~16 秒重复一次，永不终止：**
```
intake → material → zone → schedule → cross_ref_foundations → validate → intake → ...
```
**`surface` / `fenestration` / `hvac` / `people` / `lights` 五个 subagent 一次都没跑过。**

**已核实的代码事实**（orchestrator 亲查，你仍应自行复核）：
1. `src/agent/graph.py:52` `_route_after_foundations` = `"validate" if state.validation_errors else "construction"`
2. `src/agent/_share.py:7` `MAX_RETRIES = 0`
3. `src/agent/nodes/validate.py:41` 重试分支条件 `state.retry_count < state.max_retries`
4. `validate.py` 被拒分支：`goto="intake"`，`retry_count: 0`，`validation_errors: decision.get("errors", [])`
5. `src/agent/runner.py:145` `auto_approval` 有错时返回 `{"approved": False, "feedback": ...}` —— **无 `"errors"` 键**
6. `src/agent/nodes/intake.py:52` 短路条件 = `state.intake_output is not None and not state.validation_errors`
7. `cross_ref_foundations_node` 实测返回 **115 条** `output-coordinates[VERTEX_FRAME_DRIFT]: BuildingSurface:Detailed '<面名>' in the snapshot is missing from ConfigState`

## 3. 复现探针（抓到即停，**一次 pass ≈ 20 秒**）

```python
# /tmp/f11_probe.py —— 打印 cross_ref_foundations 的实际错误后立即退出
import sys; sys.path.insert(0, '/workspaces/EnergyPlus-Agent-dev')
import src.agent.nodes as nodes, src.agent.graph as graph
_orig = nodes.cross_ref_foundations_node
def spy(state):
    out = _orig(state)
    errs = (out.get("validation_errors") if isinstance(out, dict)
            else getattr(out, "validation_errors", None)) or []
    print(f"错误条数: {len(errs)}")
    for e in errs[:20]: print("  -", e)
    raise SystemExit(0)
nodes.cross_ref_foundations_node = spy; graph.cross_ref_foundations_node = spy
import runpy
sys.argv = ["run_full_pipeline.py", "sm21_anchor",
            "--intake-from", "run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json",
            "--output-subdir", "run_2026-08-06_wall3_a_retest", "--no-simulate"]
runpy.run_path('/workspaces/EnergyPlus-Agent-dev/scripts/run_full_pipeline.py', run_name="__main__")
```
同样的写法换成 hook `src.agent.runner.auto_approval` 可拿到 validate 那一侧的 interrupt payload。

## 4. ⚠️ orchestrator 的未验证猜测（**不是结论，⛔ 不要当前提，可推翻**）

- 08-05 探针 B 用**6 月的 intake** 跑下游是成功的（EP `0 Severe`）。我**猜**它没踩这条是因为那份 intake 的
  `coordinate_mode` 与今天这份不同（今天日志写 `world_legacy`，5_intakeoutput 另写了
  `output_coordinate_contract.json` / `output_coordinate_snapshot.json` 两个侧车）。**完全没验证。**
- 探针 B 产物在 `case_tests/e2e_tests/sm21_anchor/probe_b_2026-08-05_legacy_intake/`。

## 5. 边界

⛔ 不改任何 `src/` `scripts/` `skills/` `tests/` · ⛔ 不 commit 不 push · ⛔ 绝不 `git add -A` ·
⛔ 不碰 `case_tests/` 未跟踪目录 · ✅ 一次性脚本放 `/tmp` · ✅ 可读 git 历史（`git log -L` / `-S` 很有用）

## 6. 请你回答的（交付物）

1. **⭐ `cross_ref_foundations` 为什么要在 foundations 阶段校验 surfaces？** 查它的设计意图与历史
   （`git log -S` / `-L`）：是**路由顺序错了**、还是**这道校验放错了层**、还是**它本来就该在这里而输入不该带 snapshot**？
   **给判据，不给印象。**
2. **⭐ 那个循环在什么条件下能终止？** 逐条走通 §2 里的 1–6 条，说明**存不存在任何一条能让它退出的路径**。
   如果不存在，明确写「结构上不可能终止」。
3. **⭐ 2–3 个修法选项，每个写清后果与代价**（含"什么都不改会怎样"）。**⛔ 不要动手修。**
4. **它是不是与 F-5/F-7/F-10/墙 3 同族**（接口错位 / 测试绿而真链路崩 / 被前面的墙遮蔽）？是就说明是哪一种形状。
5. **⚠️ 附带**：这条链路跑飞时**零错误输出**（`auto_approval` 不打日志）。这算不算独立的一条缺陷？你的判断。

## 7. 证据纪律（硬要求）

> ⛔ **不接受「我看了 / 我读了」作为结论依据** —— 每条结论给出**可独立重跑的命令 / 文件路径+行号 / 数字**。
> ⛔ 凡涉及「方向 / 对称 / 顺序」的判断，先证明载荷本身有分辨力。

## 8. 交付

日志落 `AI_agent/logs/reviews/execution/2026-08-06_f11_downstream_loop_investigation_glm.md`；先落骨架再补。

## 9. 停下上报（**记功不记过**）

本轮至今 **7 次「停下上报」，7 次都是派工方（我）的题错了**。
本单事实与你看到的不符 / 提法本身有问题 / 真相与本单框架不兼容 ⇒ **立刻停下上报**。
