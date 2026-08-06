# 执行日志 · F-8 收口：4 文件入仓 + 干净环境验证 + 机械检查立项

- **派工单**：本轮派工 prompt（施工席，无独立 request 文件；权威依据 = 上一席位的调查日志
  `AI_agent/logs/reviews/execution/2026-08-06_f8_and_max_retries_scoping_claude.md`）
- **席位**：Claude 侧 Sonnet 子代理
- **基点**：`27c0935`（分支 `6.15_ValidationArchM0toM4`，主工作树；⚠️ 与调查单记录的 `dfbd62a` 不同——
  主树在调查完成后又推进了 4 个提交（F-9/F-13 相关），`dfbd62a` 仍是 `27c0935` 的祖先，本单在 `27c0935`
  上收口，不影响入仓的 4 个文件本身）
- **开工自检**：`git log --oneline -1` = `27c0935` ✓；`pwd` = `/workspaces/EnergyPlus-Agent-dev` ✓；
  `git status --short` 只有 4 个已知 `case_tests/` 未跟踪目录 ✓（未触碰它们）

---

## 一、入仓的 4 个文件

以调查日志给出的精确清单为准（逐字节核对，全部一致）：

| # | 路径 | 字节 | `.gitignore` 命中行（`git check-ignore -v` 实测） |
|---|---|---|---|
| 1 | `AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings/sonnet_r2/1f_view.json` | 22,221 | `.gitignore:7:20*_*/` |
| 2 | `case_tests/e2e_tests/smalloffice_21_pre/phase1/1f_view.json` | 12,090 | `.gitignore:287:case_tests/e2e_tests/smalloffice_21_pre/` |
| 3 | `case_tests/e2e_tests/smalloffice_21_pre/phase1/2f_view.json` | 11,697 | `.gitignore:287:case_tests/e2e_tests/smalloffice_21_pre/` |
| 4 | `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/EP/EP_run/eplusout.end` | 97 | `.gitignore:275:eplusout.*` |

**合计 46,105 B ≈ 45.0 KB，4 个文件**（与调查日志核算一致）。

操作：逐个 `git add -f <path>`（⛔ 未用 `git add -A`），入仓前后 `git status --short` 通读确认：
只有这 4 个文件从 untracked/ignored 变为 staged（`A`），4 个已知 `case_tests/` 未跟踪目录未被触碰。
未改任何测试代码、未改 `.gitignore`。

---

## 二、干净环境验证（前 3 红 / 后 0 红）

### 验证方法（避开调查日志记录的 venv 陷阱）

本机共享 venv（`/opt/venv`）是 hatchling editable install，其 `.pth` 硬编码主工作树绝对路径
`/workspaces/EnergyPlus-Agent-dev` ⇒ 在 worktree 里跑 `subprocess` 会解析到**主树**的 `src/`，
不是 worktree 自己的 `src/`。修法 = 显式 `PYTHONPATH=<clean_worktree>`（让 worktree 自己的 `src/`
先于 site-packages 被解析，等价于「真的在这份检出上 `uv sync`」的效果）。

### 步骤 1：入仓前（在入仓前的提交上建 worktree，验证真红 3 条）

```bash
git worktree add /tmp/f8closeout/pre_wt <PRE_COMMIT_SHA> --detach   # 显式基点=入仓前 HEAD，非默认分支
cd /tmp/f8closeout/pre_wt
PYTHONPATH=/tmp/f8closeout/pre_wt python -m pytest \
  tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four \
  tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor \
  tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean -q
```
（输出见下方「实测记录」）

### 步骤 2：入仓后（在含 4 文件的新提交上建 worktree，验证转绿）

```bash
git worktree add /tmp/f8closeout/post_wt <POST_COMMIT_SHA> --detach   # 显式基点=收口提交，非默认分支
cd /tmp/f8closeout/post_wt
PYTHONPATH=/tmp/f8closeout/post_wt python -m pytest \
  tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four \
  tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor \
  tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean -q
```
（输出见下方「实测记录」）

### 实测记录

（待填 —— 见下方执行记录）

### 清理

```bash
git worktree remove /tmp/f8closeout/pre_wt --force
git worktree remove /tmp/f8closeout/post_wt --force
rm -rf /tmp/f8closeout
```

---

## 三、主工作树全仓数字

```bash
cd /workspaces/EnergyPlus-Agent-dev
python -m pytest -q
```

（待填 —— 见下方执行记录）

---

## 四、机械检查（选项 A/B）立项

**⛔ 未实现，只登记。** 已写入 `AI_agent/plan.md` 「七、结转」表格新增一行（F-8 那行下方），
内容摘要：
- **选项 A**：AST 静态扫描测试文件路径字面量 + 逐个 `git check-ignore`，pre-commit/PR 级快门，
  heuristic（漏动态拼接路径）、需维护豁免白名单，成本低。
- **选项 B**：CI 加「全新检出 + 全仓测试」影子任务，零遗漏（连本次撞见的 venv/editable-install
  假象也一并捕获），成本较高（几分钟量级 + 独立算力）。
- **建议**：两者不互斥，A 做日常快门、B 做合并前/每日权威门。
- **要防的复发形态**：新增测试依赖了被 `.gitignore` 挡住的文件 ⇒ 本机全绿、新克隆/CI 必红，
  且没人会主动发现（本批 3 条真红潜伏了一到两个月）。

---

## 五、Commit

（待填 SHA）
