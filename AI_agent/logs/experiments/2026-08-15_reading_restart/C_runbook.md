# C 组 runbook —— 单变量实验：回滚 cv_toolbox.md 的三条「省 crop」纪律

> **状态：✅ 两抽已跑完（C1 15:36–15:42Z · C2 15:44–15:51Z，均 EXIT=0）。**
> **结论：⛔ 假说证伪** —— 墙 0/9 与 0/9、crop_zoom 2 与 1、量了 1/6 张图，工作模式没变。
> 结果与后续变量排序见 [README.md「追加：C 组」](README.md)。
> 本文件保留为执行手册（下一个单变量实验照抄命令序列即可，只换 run 名与变量）。

## 0. 这一跑要回答什么

08-15 四轮（A1/A2 autonomous 两抽 · B1 恢复 review 环）把杠杆收窄到一处：
`skills/intake_pipeline/0_reading/cv_toolbox.md` 的 Disciplines 段在 07-07 之后
新增的三条「省 crop」纪律。本跑把那三条回滚到 07-07 原文，**其余一切不动**。

| | 07-07 基准 | A1 | A2 | B1 | **C1/C2 预期方向** |
|---|---|---|---|---|---|
| 平面墙 | **9/9** | 3/9 | 1/9 | 2/9 | ↑ |
| **crop_zoom** | **55** | 0 | 0 | 0 | **↑（核心观测量）** |
| cv 调用 | 92 | 6 | 2 | 24 | ↑ |
| 量了几图 | 6/6 | 1/6 | 1/6 | 6/6 | 6/6 |

判读口径写在两份 run_config 的 `acceptance.interpretation` 里（三岔：分数回来 / 只有
crop_zoom 回来 / crop_zoom 仍是 0）。

## 1. 跑之前必须成立的前提（逐条核）

- [x] `cv_toolbox.md` Disciplines 段 = 07-07 原文 + 三处刻意保留/修正
      （跨轴出口一句 · long_structural_lines 一条 · F-40 词表修正）——
      核法：`diff <(git show 891356d:skills/intake_pipeline/0_reading/cv_toolbox.md) skills/intake_pipeline/0_reading/cv_toolbox.md`
- [x] 两份 run_config.yaml 已**先于 provision** 落盘，且除抽次标记外逐字相同
- [x] `_run/directive.md` 与 A1/A2 逐字相同（`cmp` 已验）
- [ ] ⛔ 本跑期间**不跑全仓 pytest**（F-30 / 08-13 ④：并行会污染，且真链路跑撞过 EACCES）
- [ ] ⛔ 席位**不跑 editable 安装**（F-31）
- [ ] orchestrator ⛔ 不开图纸、⛔ 不写 feedback、⛔ 不打回（lane = autonomous）

## 2. 命令序列（每抽一遍，C1 跑完再跑 C2）

```bash
CASE=case_tests/e2e_tests/sm21_anchor
RUN=run_2026-08-15_reading_restart_C1_cropdiscipline      # 抽 2 换成 C2_...

# ① provision（run_config 已在位，此步之后策略被冻结）
python scripts/tool_scripts/run_stage.py provision sm21_anchor "$RUN"

# ② 建隔离工作区 → 打印 staging root
STAGING=$(python scripts/tool_scripts/spawn_isolated_reader.py build \
            --case-dir "$CASE" --run-dir "$CASE/$RUN")
echo "$STAGING"

# ③ 冷启读图器（headless，clean-room + guard）
python scripts/tool_scripts/spawn_isolated_reader.py spawn \
    --staging-root "$STAGING" \
    --model claude-haiku-4-5-20251001 \
    --directive "$CASE/$RUN/_run/directive.md" \
    --execute 2>&1 | tee "$CASE/$RUN/_run/spawn_C1.log"

# ④ ⭐ 抢救 CV 证据（F-35 未修：merge 不带走 cv_evidence，只带 *_view.json + summary）
#    ⚠️ 证据是 out/<label>/cv_evidence/ 两层，必须**保留 label 目录**——
#       直接 cp out/*/cv_evidence 会把六个同名目录拍平互相覆盖（A1 那份的结构即为证）
DEST=AI_agent/logs/experiments/2026-08-15_reading_restart/C1_cv_evidence
mkdir -p "$DEST"
for d in "$STAGING"/out/*/; do
  [ -d "$d/cv_evidence" ] && cp -r "$d" "$DEST/"
done
find "$DEST" -maxdepth 1 -mindepth 1 | wc -l   # 0 = 整轮没量过，本身就是结论

# ⑤ merge 回 run 目录
python scripts/tool_scripts/spawn_isolated_reader.py merge \
    --staging-root "$STAGING" --run-dir "$CASE/$RUN"

# ⑥ ⭐ 补产物（用户 08-15 拍板 #3：每张图的 render + grade 图一个都不能省）
#    judge: off 关掉的正是产 grade 的那条路；F-39 未修 ⇒ 缺件不会红，只能靠这一步
python scripts/tool_scripts/run_stage.py artifacts sm21_anchor "$RUN" 0_reading
```

## 3. 两抽都跑完之后（⛔ 不许在 C1 与 C2 之间做）

**为什么卡这个顺序**：`score_reading_vs_gt` 读 gt。不变量 #4 + §1.5 #7 ——
「接触 gt 之后不得把任何结论送回同一个 run」。两抽配置已冻结且逐字相同，
先跑完再一起判，就不存在「看了 C1 的分再动 C2」的口子。

```bash
# 过程指标（真正的判据，不是判卷器）
python AI_agent/logs/experiments/2026-08-15_reading_restart/process_metrics.py \
    "$CASE/run_2026-08-15_reading_restart_C1_cropdiscipline/0_reading" \
    "$CASE/run_2026-08-15_reading_restart_C2_cropdiscipline/0_reading"

# 判卷（离线侧车，⛔ 不回流给执行环节）
python scripts/tool_scripts/score_reading_vs_gt.py \
    "$CASE/run_2026-08-15_reading_restart_C1_cropdiscipline/0_reading" \
    --case sm21_anchor --run-profile exploratory
```

## 4. 已知会绊脚的坑（都是本仓自己记过的）

- **F-40 已在本跑前修掉**（`pixel-measured` 非法词）。若 gate① 仍因 provenance 拒图，
  说明还有第三份文档在教非法值 ⇒ 记下来，别当场改文档重跑（那就毁了单变量）。
- **F-34 未修**：跨轴标定校验有两种绕过（拆两次单轴调用 · 根本不调那个工具）。
  若读图器又绕过去，**如实记，不干预** —— 这一跑不修它。
- **F-36 未修**：全仓有一条真红 `test_b2_prescan_reproduction`（与识图无关，
  `dc7b239` 带进来的）。⛔ 别在本跑期间跑全量去验它。
- **判分别误读**：07-07 基准自带 6 条 `dimension_chain_closure` FAIL（非阻断）
  ⇒ **满分 ≠ 全绿**，别把「有 fail」当退步。
- **gate① 收下 ≠ 能用**：B1 那份 2/9 的产物也被 `exploratory` 档 accept 了。

## 5. 跑完要落的账

- 本文件同目录补一节 `C 组结果`（三岔判读走哪一岔）；
- `plan.md` 顶部加 2026-08-15 续节；若结论改变杠杆定位，同步改 memory
  `reading-quality-lever-is-crop-budget-not-review-ring`；
- 新登记 **F-41**：`scaffold_fingerprints` 的算法从未记录在仓内任何位置
  ⇒ 旧三份 run_config 里的值不可复算、不可比对。C 组起改为在 run_config 内写明配方
  （⛔ 与旧值不可比）。
