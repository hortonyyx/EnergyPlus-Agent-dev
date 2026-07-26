# 返工派工单 r2：测试提速 + 受影响子集映射表（2026-07-26）

- **施工方**：GPT 侧 terra（续同一循环的返工，免重拍派工表）
- **来源**：① GLM-5.2 验证性对抗审裁决书 `AI_agent/logs/reviews/verdict/2026-07-26_test_speedup_and_affected_map_glm.md`（APPROVE-WITH-CHANGES：0 BLOCKER / 1 MAJOR / 2 MINOR）② 主控轻门 r2 findings（本单 R-01/R-02/R-05）
- **基线**：主控轻门独立并行全仓 = `1669 passed, 10 xfailed, 0 failed/error`（261s）；HEAD 仍 `2217393`，全部改动在工作树
- **主控已自行处置（不在你范围）**：GLM MAJOR-1（越界改 `AI_agent/guides/codex_execution_protocol.md`）= 主控收回该文件主权、亲自复核并修正其中两处过于乐观的耗时数字。**你本轮不得再碰 `AI_agent/**` 下除本执行日志以外的任何文件。**

---

## R-01（MUST）`--since` 那条锁现在是环境依赖的弱锁

**事实**：`tests/test_affected_tests_map.py::test_since_uses_committed_range_only` 断言 `changed_since("HEAD") == []`。它今天能承重，**只因为工作树恰好脏着 6 个已跟踪文件**：

```
git diff --name-only HEAD        → 6 个文件   （两点语义，含未提交改动）
git diff --name-only HEAD...HEAD → 0 个文件   （三点语义，只看已提交范围）
```

本批一 commit、树变干净后，两种语义都返回 0 ⇒ 该断言退化为**永真空锁**，谁把三点改成两点它都不会红。这是项目反复抓的「锁没绑在门上」同型问题。

**出口**：锁自己造证据，不依赖被测仓库的工作树状态。做法自定，建议：`tmp_path` 里 `git init` 造一个仓库 → 一个**已提交**改动 + 一个**未提交**改动 → 断言 `changed_since(<base>)` 只含已提交那个、不含未提交那个。
**验收**：把 `changed_since` 里的 `f"{ref}...HEAD"` 临时改成 `ref`（两点）→ 该锁**必须变红**；实跑截图进 neuter 自查表。

## R-02（MUST）子集命令会吐出非测试文件，且与全仓触发器口径自相矛盾

**事实**：`affected_tests.py --changed <任意 hub 模块>` 输出的 pytest 命令里含 `tests/b4b_contract_fixture.py`、`tests/b5_test_helpers.py`。这两个不是测试文件（`python -m pytest tests/b5_test_helpers.py` → `no tests ran`），而且它们**已经**在规则表 `full_scope` 里（改它们即回落全仓）——一边当全仓触发器、一边当子集运行目标，口径矛盾。附带风险：若某次过滤后子集只剩这类文件，pytest 退出码 5（no tests ran）会被误读。

**出口**：选中集合只保留 pytest 真会收集的测试文件（当前口径 = `tests/` 下 `test_*.py`）；helper 仍可作为**图上的中转节点**（不得因此断掉 `test → helper → src` 的传递链）。过滤后若集合为空 ⇒ 回落 `SCOPE: FULL` 并给原因，**不得**输出空的 pytest 命令。
**验收**：① 任一 hub 模块的输出不含这两个文件 ② 现有传递链锁（经 helper 的那些）仍绿 ③ 新增锁：删掉过滤即红。

## R-03（SHOULD）GLM MINOR-1：`resources.files` 动态注入盲区要写进清单

`src/agent/execution/isolation.py` 用 `resources.files(<模块名>).joinpath(<变量短名>)` 动态读 `isolation_templates/{guard,run_cv_probe}.py` 写进 staging，静态图抓不到（模块名是点分、文件名是变量短名）。

**出口**：① 规则表里这两条 allowlist 的理由各补一句「经 `resources.files` 动态注入 staging，`test_isolation` 在隔离 staging 内执行其副本；静态图无法捕获该动态耦合，故按 no-cover 兜底 FULL」 ② 规则表头部注释登记「`resources.files` / 点分模块名这类动态耦合是已知盲区，后果 = allowlist 被迫膨胀，但 fail-closed 回落全仓、不漏跑」。纯文档，不改判定逻辑。

## R-04（SHOULD）字符串边不许经由测试文件中转 —— 这是子集真正能变便宜的关键

**事实**（GLM MINOR-2 + 主控实测）：对枢纽模块，子集≈全仓：

| 改动 | 选中测试文件数（共 93） |
|---|---:|
| `src/agent/pipeline.py` | 86 |
| `src/agent/judge/gt.py` | 87 |
| `src/validator/schedules.py` | 88 |
| `scripts/tool_scripts/cv_probe.py` | 87 |

根因不全是真耦合：字符串边把「**生产模块的字符串里出现测试文件路径**」也连进了图（例：`src/agent/judge/gt.py` 的字符串含 `tests/test_gt_discipline.py`），于是产生 `test_X → … → gt.py → tests/test_gt_discipline.py → cv_probe.py` 这种**经测试文件中转**的伪路径，把互连团整体拉进子集。

**出口**：加方向约束——**目标在 `tests/` 下的边，只有当来源也在 `tests/` 下时才参与传递**（保住 `test → helper`，掐掉 `生产 → 测试` 的桥）。
**前置证据（必须先给，再动手）**：全仓 grep 证明没有生产模块**真的**读取/执行某个测试文件（`subprocess`/`open`/`read_text`/`import` 指向 `tests/`）。若存在真例外，**列出来并保留那条边**，在执行日志里说明。
**验收**：① `cv_probe.py` 子集显著收缩（预期个位数）、`pipeline.py` 子集明显下降 ② 覆盖门 `uncovered == allowlist` 仍严格相等（若因此有模块变 uncovered，**不得**偷偷加 allowlist——回来找主控裁）③ fail-closed 五条不变 ④ 新增锁固定「生产→测试 字符串边不产生传递选中」，neuter 即红。
**这条若做不动就诚实标 PARTIAL 交回**，不要硬凑。

## R-05（NIT）两处代码噪音

- `affected_tests.py::package_for_path`：`if parts[-1] != "__init__": parts.pop()` / `else: parts.pop()` 两支完全相同 = 死分支，合并。
- `tests/test_affected_tests_map.py:82`：`assert any(len(...) >= 2 for _ in [None])` 的推导式包装无意义，直接断言。

---

## 跑测与交付纪律

- **中间轮**：只跑受影响子集（本批改的是映射工具本身 ⇒ 至少 `tests/test_affected_tests_map.py`；改到过滤逻辑就把 `affected_tests.py --changed` 自己算一遍并把「跑测声明」贴进日志）。
- **交付前**：跑一次**全仓**（默认并行即可），原始输出尾部进执行日志——这是审阅方判零回归的唯一依据。基线 `1669 passed + 10 xfailed + 0 failed/error`，本轮预期为该数加新增锁条数。
- **neuter 自查表 = 交付物**：每条新锁 → neuter 哪一行改成什么 → 哪条用例变红 → 是否**只**红该条。**临时改动一律在 `/tmp` 的副本里做**（本轮 GLM 在工作树里 neuter，与主控轻门撞了时间窗；工作树必须随时可跑）。
- **不要 commit**；不改 `src/`；除已授权的 `test_mcp_stdio.py`（timeout）与 `test_e4_relative_north_axis_e2e.py`（fixture 隔离）两处外，不动任何测试的断言/容差/期望值；不加 skip/xfail/retry/xdist_group。
- 执行日志续写 `AI_agent/logs/reviews/execution/2026-07-26_test_speedup_and_affected_map.md`（新开「返工 r2」节）。
- 回主对话只给简报：改了哪几个文件 / 测试计数 / 每条出口的结论（DONE / PARTIAL + 缺什么）/ **审阅需求（review-ask）**：你自己没把握或做了取舍的地方，没有就写 none。
