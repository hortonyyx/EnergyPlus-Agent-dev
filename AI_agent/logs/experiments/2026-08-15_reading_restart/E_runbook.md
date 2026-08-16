# E 组 runbook —— 单变量实验：撤掉 A3「能力封口」

> **状态：✅ E1 已跑完**（2026-08-16 03:00–03:11Z，`SPAWN_EXIT=0`）。
> **结论：⛔ 假说证伪，但换来一条更有信息量的观测** ——
> 能力**真的被用了**（自写脚本 ×1 + `python -c` ×3），
> **但一次都没用来量图**：三次 `-c` 全是校验自己输出的 JSON 是否合法，
> 唯一那个脚本里坐标是**硬编码**的、内墙注着 `estimated from visual inspection`。
> **工作模式一点没变**：仍只量 1/6 张图，墙 **0/9**。
> 结果详见本文件 §6 与 [README.md「追加：E 组」](README.md)。
>
> 配置已冻结（`run_config.yaml` 先于 provision 落盘）。
> 变量、口径限制、判读三岔全部写在
> [`case_tests/e2e_tests/sm21_anchor/run_2026-08-16_reading_restart_E1_uncapped/run_config.yaml`](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-08-16_reading_restart_E1_uncapped/run_config.yaml)。
> 本文件只写**怎么跑**，⛔ 不重复写变量定义。

## 0. 这一跑要回答什么

`lever_inventory.md` 把剩余杠杆排到第一位的是 **A3 = guard 的命令层封口**：
07-07 那次拿 9/9 时读图器可以随手写 python 算；今天 `python -c` 与任何自写脚本
都是 DENY。这与用户 2026-08-02 已经拍过板的隔离原则**直接冲突且至今未落地**。

本跑把它落地，观察工作模式是否切换。

| | 07-07 | A1 | A2 | B1 | C1 | C2 | **D1** | **E1 预期方向** |
|---|---|---|---|---|---|---|---|---|
| 平面墙 | **9/9** | 3/9 | 1/9 | 2/9 | 0/9 | 0/9 | **2/9** | ↑ |
| 量了几图 | 6/6 | 1/6 | 1/6 | 6/6 | 1/6 | 1/6 | **1/6** | ↑ |
| crop_zoom | **55** | 0 | 0 | 0 | 2 | 1 | **6** | ↑ |
| CV 调用 | 92 | 6 | 2 | 24 | 5 | 4 | **10** | ↑ |
| **自写代码** | 有（无 guard） | ⛔封 | ⛔封 | ⛔封 | ⛔封 | ⛔封 | ⛔封 | **← 本跑唯一直接测量的量** |

⭐ **最有信息量的一岔不是「分数回来」，是「给了能力它一次都不用」** —— 那说明
杠杆不在权限而在别处，下一个单变量应转向 A1 会话形态。

## 1. 跑之前必须成立的前提（逐条核）

- [x] guard 新策略**行为验证 20 条全过**（⛔ 不接受形状匹配）：正向 7（`-c`/自写脚本/
      除法/比较/分号/cat/prose 词）· 边界 8（`-c` 读 gt · 脚本读 gt · **import 面**泄漏 ·
      网络 · 子进程 · `$HOME` · cat gt · 脚本在 out/ 外）· held 3（prescan CLI · 管道 · Read 仓库）
      · 阴性对照 2（wrapper 仍可用 · 移除脏文件后同一命令放行）
- [x] 沙箱内**真的能跑通**：`python out/measure.py` 用 numpy+PIL+scipy 读图成功（rc=0）
- [x] `_run/directive.md` 与 D1 逐字相同（`cmp` 已验）
- [x] run_config 先于 provision 落盘
- [ ] ⛔ 本跑期间**不跑全仓 pytest**（F-30 / 08-13 ④）
- [ ] ⛔ 席位**不跑 editable 安装**（F-31）
- [ ] orchestrator ⛔ 不开图纸、⛔ 不写 feedback、⛔ 不打回（lane = autonomous）

## 2. 命令序列

```bash
CASE=case_tests/e2e_tests/sm21_anchor
RUN=run_2026-08-16_reading_restart_E1_uncapped

# ① provision（run_config 已在位，此步之后策略被冻结）
python scripts/tool_scripts/run_stage.py provision sm21_anchor "$RUN"

# ② 建隔离工作区 → 打印 staging root
STAGING=$(python scripts/tool_scripts/spawn_isolated_reader.py build \
            --case-dir "$CASE" --run-dir "$CASE/$RUN")
echo "$STAGING"

# ③ 冷启读图器（headless，clean-room + guard v2）
python scripts/tool_scripts/spawn_isolated_reader.py spawn \
    --staging-root "$STAGING" \
    --model claude-haiku-4-5-20251001 \
    --directive "$CASE/$RUN/_run/directive.md" \
    --execute 2>&1 | tee "$CASE/$RUN/_run/spawn_E1.log"

# ④ ⭐ 抢救 CV 证据（F-35 未修：merge 不带走 cv_evidence）
#    ⚠️ 必须保留 out/<label> 层级，直接 cp 会把六个同名目录拍平互相覆盖
DEST=AI_agent/logs/experiments/2026-08-15_reading_restart/E1_cv_evidence
mkdir -p "$DEST"
for d in "$STAGING"/out/*/; do
  [ -d "$d/cv_evidence" ] && cp -r "$d" "$DEST/"
done

# ⑤ ⭐⭐ 本跑新增：抢救**读图器自己写的代码** + access_log
#    这是本跑唯一直接测量被撤变量的证据，且 F-35 同样不带走它
mkdir -p "$DEST/_self_authored"
find "$STAGING/out" "$STAGING/requests" -name '*.py' -exec cp --parents -t "$DEST/_self_authored" {} + 2>/dev/null
cp "$STAGING/access_log.jsonl" "$DEST/access_log.jsonl"
find "$DEST/_self_authored" -name '*.py' | wc -l    # 0 = 给了能力没用，本身就是结论

# ⑥ merge 回 run 目录
python scripts/tool_scripts/spawn_isolated_reader.py merge \
    --staging-root "$STAGING" --run-dir "$CASE/$RUN"

# ⑦ ⭐ 补产物（用户 08-15 拍板 #3；judge off 关掉了产 grade 的那条路，F-39 未修）
python scripts/tool_scripts/run_stage.py artifacts sm21_anchor "$RUN" 0_reading
```

## 3. 跑完之后（⛔ 判卷必须排在最后）

```bash
# ⭐⭐ 先做变量纯度 + 信息边界两项检查（run_config.acceptance.integrity）
python - <<'PY'
import json, pathlib
log = [json.loads(l) for l in pathlib.Path("<DEST>/access_log.jsonl").read_text().splitlines()]
print("total", len(log), "| deny", sum(e["decision"] == "deny" for e in log))
ran = [item for e in log for item in e.get("executed_code", [])]
print("executed_code entries:", len(ran))
for e in log:
    if e["decision"] == "deny":
        print("DENY:", e["reason"][:100])
PY
# 逐份读 _self_authored 下的脚本：① 有没有 import 到 prescan 实现（变量纯度）
#                                  ② 有没有指向答案的路径（信息边界）

# 过程指标（真正的判据）
python AI_agent/logs/experiments/2026-08-15_reading_restart/process_metrics.py \
    "$CASE/$RUN/0_reading"
# ⚠️ F-42 未修：该脚本少算 prescan ⇒ 报表里的 prescan 计数不可信（本跑 prescan 已撤，影响小）

# 判卷（离线侧车，⛔ 不回流给执行环节）
python scripts/tool_scripts/score_reading_vs_gt.py \
    "$CASE/$RUN/0_reading" --case sm21_anchor --run-profile exploratory
```

## 4. 已知会绊脚的坑

- **一抽不构成成绩结论**（本仓纪律：识图成绩至少两抽，同配置曾差 2.8 倍）。
  本跑先看过程指标；出现方向性变化必须补第二抽。
- **A 档未撤到底**：管道/重定向/`;` 仍拒（见 run_config「仍然拒绝」一节）。
  ⇒ 若无起色，只能写「撤到这一档不足以恢复」，⛔ 不能写「A3 不是杠杆」。
- **F-34 未修**：跨轴标定校验的两种绕过（拆两次单轴 · 根本不调）。复现就如实记，不干预。
- **F-36 未修**：全仓有一条真红 `test_b2_prescan_reproduction`，与识图无关。
- **gate① 收下 ≠ 能用**：B1/C1/C2 的低分产物都被 `exploratory` 档 accept 过。
- **判分别误读**：07-07 基准自带 6 条 `dimension_chain_closure` FAIL（非阻断）⇒ 满分 ≠ 全绿。

## 5. 跑完要落的账

- 本目录补一节 `E 组结果`（判读三岔走哪一岔）+ 更新 `lever_inventory.md` 的已排除/剩余表；
- `plan.md` 顶部加 2026-08-16 节；
- memory `reading-quality-lever-is-crop-budget-not-review-ring` 同步（其标题主张已自否，本轮若定位到杠杆需改写）；
- **F-45（本轮登记，未修）**：`cv_toolbox.md` 的四段调用示例写的是
  `python scripts/tool_scripts/cv_probe.py …`，而沙箱里唯一可执行的授权路径是
  `python tools/run_cv_probe.py …` ⇒ **随文档发给读图器的示例，在沙箱里逐条会被 DENY**。
  自硬隔离壳存在起一直如此。本轮**刻意不修**（改它=动第二个变量），
  但它是「摩擦」这一轴的实测材料，应在 A1 会话形态那一跑之前处理。

---

## 6. ⛔ E1 结果（2026-08-16）

### 6.1 数字

| | 07-07 | A1 | A2 | B1 | C1 | C2 | D1 | **E1** |
|---|---|---|---|---|---|---|---|---|
| 平面墙 | **9/9** | 3/9 | 1/9 | 2/9 | 0/9 | 0/9 | 2/9 | **0/9** |
| 平面窗 | **7/7** | 0/7 | 1/7 | 0/7 | 2/7 | 0/7 | – | **0/7** |
| 立面窗 | 15/15 | – | – | – | – | – | – | **1/15** |
| 外包边界 | – | – | – | – | – | – | – | **8/8 pass** |
| 量了几图 | 6/6 | 1/6 | 1/6 | 6/6 | 1/6 | 1/6 | 1/6 | **1/6** |
| crop_zoom | **55** | 0 | 0 | 0 | 2 | 1 | 6 | **3** |
| CV 调用 | 92 | 6 | 2 | 24 | 5 | 4 | 10 | **7** |
| 平面 `dimension_derived` | 35/35 = 100% | – | – | – | – | – | – | **8/44 = 18.2%** |
| **自写代码执行** | 有（无 guard） | ⛔封 | ⛔封 | ⛔封 | ⛔封 | ⛔封 | ⛔封 | **4 次** |

CV 调用明细：`crop_zoom` 3 · `wall_line_profiler` 2 · `px_m_calibrator` 1 · `window_cc_detector` 1。
全部落在 `1f_view` 一张图上。

### 6.2 ⭐⭐⭐ 本轮最该记住的一条：**能力被用了，但没用在测量上**

这是 run_config 写的三岔**之外**的第四种结果，也是本轮唯一的新信息。
F-44 修完之后 access_log 第一次留下了放行命令的原文，逐条读下来：

| 时刻 | 执行的代码 | 干了什么 |
|---|---|---|
| 03:04:22 | `out/measure_1f.py` | **坐标硬编码**（`PX_PER_M = 60.67`、`ORIGIN_X_PX = 275` 直接写死），
| | | 主体在 `print` 自己的假设；内墙一行注着 `estimated from visual inspection` |
| 03:06:10 | `python -c` | `json.load(out/1f_view.json)`，打印 stroke/dimension 计数 |
| 03:07:35 | `python -c` | `json.load(out/2f_view.json)`，打印 `valid` |
| 03:09:54 | `python -c` | 六个输出文件逐个 `json.load`，打印 ✓/✗ |

⇒ **三次 `-c` 全部是「校验我写出来的 JSON 合法吗」，零次是「这堵墙在哪」。**
⇒ 那个唯一的脚本，名字叫 `measure_1f.py`，实际做的是**把已经决定好的数字打印出来**。

**这与本仓已记过的判据同族**：「给了工具就会去量」是错的隐含假设
（见 memory `reading-cv-toolkit-methodology`）—— 今天证的是它的加强版：
**给了「随便写代码」这种最自由的能力，它拿去做自证，不拿去做测量。**

### 6.3 判读（按 run_config 的三岔）

走的是第三岔的变体：**能力被使用，但工作模式（量几张图、量不量）纹丝不动。**
⇒ **A3 不是那个杠杆**（在本档撤除深度下）。
⇒ 下一个单变量按 lever_inventory 排序应转向 **A1 会话形态**
（Agent tool 多轮 → headless `-p` 一次性）。

### 6.4 ⛔ 口径限制（不得省略）

- **一抽**。⛔ 不构成分数结论（本仓纪律：识图成绩至少两抽，同配置曾差 2.8 倍）。
  但「自写代码 4 次、零次用于测量」是**过程事实**，不受抽数限制。
- **A 档未撤到底**：管道/重定向/`;` 仍拒。3 条 deny 里**有 2 条正是这个**
  （`find … | head`、`ls … 2>/dev/null`）⇒ 摩擦确实还在，只是它挡的是**列目录**，
  不是测量。⇒ 严格说本轮证的是「撤到这一档不足以恢复」。
- **变量纯度 ✅**：access_log 与自写脚本里 **prescan 零出现** ⇒ D1 的变量守住了，
  本跑是干净单变量。
- **信息边界 ✅**：3 条 deny 无一条是够答案；66 条 allow 的 `executed_code`
  逐条核过，没有指向答案的路径。**这是第一次真的能做这项检查**（F-44 之前 allow 不留原文）。
- **gate① 又收下废品**：这份 0/9 的产物同样被 `exploratory` 档 accept。B1 教训第三次重演。

### 6.5 顺带的观测（未处理）

- **F-45 复现**：读图器第一条 CV 命令就写成 `python tools/run_cv_probe.py px_m_calibrator …`
  （子命令式），被 wrapper 以「参数必须成对」拒 —— 正是 `cv_toolbox.md` 示例里那种写法。
  ⇒ 文档示例与沙箱唯一合法形态不一致，**实测会烧掉一轮**。
- 读图器**主动去 `find` 整个 staging 目录**（被管道规则拒）⇒ 它在找 `input_inventory.json`，
  说明入口文档没把「文件在哪」讲清楚。归 A1/B 那两轴的材料。
