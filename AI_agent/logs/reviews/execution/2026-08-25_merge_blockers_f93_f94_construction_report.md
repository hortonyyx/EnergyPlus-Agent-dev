# 施工交件报告 · 清合并阻塞（F-93 / F-94）

- **派工单**：[`../request/2026-08-25_merge_blockers_f93_f94.md`](../request/2026-08-25_merge_blockers_f93_f94.md)
- **席位**：Claude 家族执行档（用户 2026-08-25 指定「施工走 Claude 侧」）
- **交件 commit**：**`b3e0a32`** `08.25_F93MergeBlockerClearedBothLocksReanchoredToTheResignedGt`
- **复核**：GLM 跨家族 → [`../request/2026-08-25_merge_blockers_crossreview_glm.md`](../request/2026-08-25_merge_blockers_crossreview_glm.md)
- ⛔ **本文是施工席位自述，按 §5#8「一律以 `git diff` 为准」** —— 凡自述与 diff 冲突以 diff 为准。
  orchestrator 已机械核对的部分在文末单列。

## 0. 开工自检

| 项 | 结果 |
|---|---|
| `pwd` | `/workspaces/EnergyPlus-Agent-dev` ✓ |
| 开工时 HEAD | `a464be4` ✓ 与派工单预期一致 |
| 分支 | `08.23_AsDrawnReading` ✓ |
| 读派工单 | ✓ 完整读 |
| 读 `CLAUDE.md` | ⚠️ **席位主动披露的疏漏**：不是开工前读的，是**中途补读**（§0 / §5#8 / §5#12）。补读后确认范围限制与角色矩阵无冲突 |
| 复跑确认 4 项红 | `1 failed, 12 passed, 3 errors` ✓ 与派工单预期一致 |

## 1. F-93 1-a 陈旧锁 — **选了派工单建议的路（不删锁）**

给锁一份**真正满足前提**（两层指纹真不一致）的合成 gt，让它先自证前提再断言；
改为直接调生产函数 `_elevation_binding_fields`（不再走 CLI 子进程），与紧邻的姊妹锁（extent 分歧）同手法。

```diff
-def test_generator_fails_closed_on_sm25_multi_floor_fingerprint(tmp_path):
-    result = _run_builder(SM25_RUN, SM25_GT, out=out)
-    assert result.returncode != 0
+def test_generator_fails_closed_on_sm25_multi_floor_fingerprint():
+    gt = SimpleNamespace(floors=[... fingerprint "a"*64 ..., ... fingerprint "b"*64 ...])
+    with pytest.raises(SystemExit) as excinfo:
+        _elevation_binding_fields(entry, gt, views)
+    assert "S1" in str(excinfo.value) and "fingerprints" in str(excinfo.value)
```

## 2. F-93 1-b 陈旧夹具 — ⭐ **走了派工单没给的第三条路**

夹具内**现场**调真实生成器 `build_score_view_bindings` 对**当前 gt** 重建绑定，
全程只写 `tmp_path`，**从不写回历史 run**。

- 避开 (a) 改历史 run 文件的代价；
- 避开 (b) 换被测对象的代价 —— **T1 `output.json` 的 sha256 保持 `6b4aa33c…` 不变**。

```diff
-    for name in ("view_manifest.json", "judge_score_bindings.json", "reading_exam_scope.json"):
-        shutil.copyfile(SM25_RUN / "_run" / name, metadata / name)
+    for filename in ("view_manifest.json", "reading_exam_scope.json"):
+        shutil.copyfile(SM25_RUN / "_run" / filename, metadata / filename)
+    fresh_bindings = build_score_view_bindings(SM25_RUN, SM25_GT, None)
+    (metadata / "judge_score_bindings.json").write_text(...)
```

⚠️ **两处断言的期望值被改动**（⭐ 这是复核单的头号攻击面）：

```diff
-        ("plan_openings", 1), ("plan_segments", 1),
+        ("plan_openings", 1), ("plan_segments", 1), ("plan_segments", 1),
-    assert len(ambiguous_ids) == 2
+    assert len(ambiguous_ids) == 3
```

以及「产物歧义不改变分母」那条子断言，从**比对 T1 历史 `score_vs_gt.json`**（用旧 gt 算的，resign 后
等于拿两份不同 gt 的分母比较，判据本身失效）改为**同一当前 gt 下的自证控制组**
（清空 `1f_view` 全部描边重判一次，两次分母必须相等；实测 `denominator_atoms` /
`denominator_sha256` 双双一致）。

## 3. 全量（席位自己跑的）

```
3014 passed, 13 xfailed, 212 warnings in 668.04s (0:11:08)
```

0 failed / 0 errors；基线 `3010 passed / 1 failed / 3 errors / 13 xfailed` ⇒ **3010+4=3014、xfailed 13→13 均对得上**。

## 4. 「摘掉修复会变红」（含方向判断）

- **1-a**：把生成器的 fail-closed 判断临时短路成 `if False and (...)` ⇒
  `Failed: DID NOT RAISE <class 'SystemExit'>` / `1 failed in 3.67s`。
  **方向对** —— 红在「生成器不再 fail-closed」这一点上，不是红在无关断言。已还原源码（`git diff` 为空）。
- **1-b**：把夹具还原成照抄 T1 历史绑定 ⇒ `ScoreContractError: score_view_binding_invalid` /
  `1 passed, 3 errors in 5.05s`，**与最初四项红里 f67 部分的模式逐字一致**。已还原，重跑 `4 passed`。
- 席位自己的分辨力论证：「不只是变红，而是**红在与原始故障同构的位置/异常类型**上」。

## 5. F-94 候选方案（⛔ 只出方案，未碰 venv/装机配置）

根因（只读核查）：`.pth` 追加在 `sys.path` **末尾**；裸跑脚本时 `sys.path[0]` = 脚本自身目录（无 `src/`）
⇒ 落到 `.pth` 注入的主树路径 ⇒ 静默串台。
pytest 因 `pyproject.toml` 的 `pythonpath=["."]` **已安全**；
`run_stage.py` / `cv_probe.py` 等 **6/32** 脚本已有自举先例，其余 26 个（含 `guides/` 里 15 处文档化裸跑命令）没有。

| | 做法 | 多工作树 | pytest/裸跑 | 新席位重踩坑 | 代价 |
|---|---|---|---|---|---|
| **A** 扩展现有自举模式（6/32 → 全部）| ✓ 位置 0 插入压过 `.pth` | pytest 已安全 + 裸跑补齐 | ⚠️ 约定而非机制，新脚本忘写仍踩；可加「扫描裸跑脚本是否含自举行」的锁兜底 | 中：改 26 个文件，机械低风险；⛔ 不移除 `.pth`，交互式 `python -c` 仍会串台 |
| **B** 删 `.pth` + 强制 `-m` | ✓ 无全局偏置 | 裸跑从静默串台变**响亮** `ModuleNotFoundError`（方向对）| ✓ 无陈旧物可去 | 高：破坏 ≥15 处文档化裸跑命令，需系统性迁移 |
| **C** 按工作树设 `PYTHONPATH`/direnv | ✓（前提每次设对）| 两入口统一受益 | ✗ **最弱**，全靠人记得 source；direnv 自动化要碰 devcontainer，⛔ 同样需另走「先出方案」闸 | 中但脆 |

**席位倾向（仅供参考）**：A 最小代价可先落地（延续项目已有模式）；B 长期最干净但代价最大，建议回并稳定后单独排期；C 不推荐作主路径。三者不互斥。

## 6. ⭐ 与派工单说法不符之处（席位主动上报，**第 24 次**）

派工单把 1-b 定性为纯粹的「陈旧夹具指向了旧哈希」。**实测更深一层**：
sm25 gt 08-23 重签**几何本身也在浮点精度上变了**，使 T1 真实产物重判时**真多出一条**
support-line 并列歧义（外墙轴线 vs 0.12 m 外的内隔墙，落在 `plan_position_tol_m=0.30` 内
—— 已知「轴线 vs 外皮」半墙厚问题的又一现形）。
席位以**双向复现**核实：旧 gt 重建同一绑定 ⇒ 精确复现历史的 2 条；新 gt ⇒ 稳定 3 条
⇒ 差值 100% 来自 gt 内容变化，非本次改动引入。

---

## ⭐ orchestrator 的机械核对（⛔ 不是「审」，审归 GLM）

| 核了什么 | 结果 |
|---|---|
| `git show --stat b3e0a32` | ✅ **只含**两个 tests 文件（+41/-6、+101/-32）；⛔ 未碰 `src/` `scripts/` `AI_agent/` |
| `git status` | ✅ clean；未 push |
| 全量汇总行 | ✅ 读的是**同一份日志**（`scratchpad/full_suite_final.log`），逐字一致 |
| §6 那条上报的第 ① 步（gt 几何是否真变了）| ✅ **属实，且规模比席位自述更大**：`e982eba~1` vs 当前，F1/F2 外轮廓**各 8 顶点全部**改变、zone 顶点 **136 个全部**改变（`13.999999999999996→14.0` · `-3.55e-15→0.0` · `4.9999999999999964→5.0` · `16.06→16.060000000000002`）⇒ **一次全局浮点清理**。已登记为 **F-98**。|
| §6 那条上报的第 ② 步（双向复现）| ⛔ **orchestrator 未独立验证** ⇒ **已明确要求 GLM 去验**，并列为复核单的头号攻击面 |
