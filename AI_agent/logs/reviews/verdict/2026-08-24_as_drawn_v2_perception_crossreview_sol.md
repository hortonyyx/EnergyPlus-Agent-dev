# 跨家族三审裁决 · as-drawn v2 + perception

- **被审对象**：`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/` 的代码、产物与实证档
- **审阅方**：gpt-5.6-sol 家族三审
- **日期**：2026-08-24
- **前置材料**：三审请求书、一审 REJECT、二审 REJECT、`reading_correction_split_guide.md` 均已全文阅读
- **限制遵守**：未改 `src/`、未改 `case_tests/`、未改 gt，未 commit / push

## 总裁决：**REJECT**

本轮要进入 B 步，至少必须同时满足四条：

1. 没有已实证的高分假绿；
2. 所有被评分器消费的观测都能由原图独立重算；
3. perception 的正向表态、弃权与 completeness 有不可绕过的验收语义；
4. gt 的可评分分母、切段规则及多画规则已经机器化定义。

当前四条均未满足。头条反例是：**同一堵墙的两个面真实少读 1.2 m，只需在未被任何无-gt 门重算的 gap profile 中谎报“这里有门窗墨”，六道无-gt 门全绿，gt 侧又从 89.2 回到诚实产物的 94.6**。这直接击穿当前判据组合，不能进入不可逆 gt。

下面每项都明确标出「实测」或「推断」。除明确写为推断者外，数字均由本轮命令重新产生。

---

## Q1：新的真实作弊形态 —— **把漏读的真墙错报成洞口，并伪造未重算的 gap profile**

### Finding 1（⭐⭐⭐，实测）：1.2 m 真墙缺口可被 `ink_by_family.span_ratio` 原样桥回

这不是再做一次“一条线中间漏读”，也不是“一像素桥接”。新的错误链是：

1. reading 在 sm25 1F 的内墙 `L012 + L013` 两个面上都漏掉世界坐标 `[11.4, 12.6] m`，即 **1.2 m** 真墙；
2. 同一 reading 又把这段错认成门窗断口，在评分器真正消费的 v2 字段
   `gaps[*].ink_by_family[F3].span_ratio/span_m` 中写入假证据；
3. `reverse` 只查剩余 `runs_px` 是否压在真墨上，`recompute` 不重算 gap，opening-role 门只累加产物自报的 `on_line`，forward 又用全图 **8%** 总量阈值；
4. 因而局部少掉两条 1.2 m 面线，只把 forward residue 从 **2.77%** 推到 **3.72%**，六门仍全绿；gt 重建则相信假 gap 并把墙桥回。

现实错误形态是常见的：门窗色层、坐标框或 gap/组件关联错位后，**一段未读到的墙被误归因成洞口**。当前 schema 把 gap profile 放在唯一可评分的 observations，却没有一条门从原图重算它。

我新增了可跑变异：

- `tools/crossreview_mutate_v2.py`
- `missing_wall_middle`：只挖掉两个面的 1.2 m 真墙，作为受损对照；
- `fake_opening_over_missing_wall`：挖同一段，并在**真实 v2 字段**写假 opening profile；
- 产物及报告落在 `out/*_CROSS_*`。

复现：

```bash
cd /workspaces/EnergyPlus-Agent-dev
EXP=AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype

python3 "$EXP/tools/crossreview_mutate_v2.py" \
  "$EXP/out/sm25_1f_v2.json" \
  "$EXP/out/sm25_1f_CROSS_missing_wall.json" missing_wall_middle
python3 "$EXP/tools/crossreview_mutate_v2.py" \
  "$EXP/out/sm25_1f_v2.json" \
  "$EXP/out/sm25_1f_CROSS_fake_opening.json" fake_opening_over_missing_wall

python3 "$EXP/tools/checks_as_drawn_v2.py" \
  "$EXP/out/sm25_1f_CROSS_missing_wall.json" "$EXP/tools/cfg_1f_full.json" \
  "$EXP/out/sm25_1f_CROSS_missing_wall_checks.json"
python3 "$EXP/tools/checks_as_drawn_v2.py" \
  "$EXP/out/sm25_1f_CROSS_fake_opening.json" "$EXP/tools/cfg_1f_full.json" \
  "$EXP/out/sm25_1f_CROSS_fake_opening_checks.json"

python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_missing_wall.json"}' \
  "$EXP/out/sm25_1f_CROSS_missing_wall_gt.json"
python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_fake_opening.json"}' \
  "$EXP/out/sm25_1f_CROSS_fake_opening_gt.json"
```

实测对比：

| sm25 1F 产物 | 真正少读 1.2 m 墙 | 假 gap profile | 无-gt 六门 | forward unclaimed | opening share | gt 侧 |
|---|---:|---:|---|---:|---:|---:|
| 诚实 | 否 | 否 | 6/6 绿 | **2.77%** | **0.9783** | **94.6** |
| 受损对照 | 是 | 否 | **6/6 绿** | **3.72%** | **0.9783** | **89.2** |
| 作弊 | 是 | 是 | **6/6 绿** | **3.72%** | **0.9788** | **94.6** |

把作弊 1F 与诚实 2F 合并重跑整栋，仍为诚实整栋的 **93.3 / 75 targets**：

```bash
python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_fake_opening.json","F2":"'$EXP'/out/sm25_2f_v2.json"}' \
  "$EXP/out/sm25_CROSS_fake_opening_gt.json"
# overall_ok_pct=93.3, exterior=100.0, interior=91.5
```

### Finding 2（⭐⭐，实测）：现有 `punch_middle_one_pixel` 的 0.0 / 0.0 没打到消费者

当前变异写：

```python
{"opening_ink": {"on_line": 1, "span_ratio": ...}}
```

但 `_extent()` 只读：

```python
g["ink_by_family"][fen_family]["span_ratio"]
```

复现静态路径：

```bash
rg -n 'opening_ink|ink_by_family|span_ratio' \
  AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/reconstruct_check_v2.py
# 变异写 opening_ink；消费者读取 ink_by_family
```

我把同一单像素探针移到评分器真正读取的 schema 后，整体分数仍是 sm25 **0.0**、sm24 **0.0**，所以 README 的两个分数本身能复算；但“单像素动不了 span 判据”这个解释不成立。真实 schema 下已有大量 gap 被一个像素推过 `OPENING_SPAN_MIN=0.10`：

```bash
EXP=AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype
python3 "$EXP/tools/crossreview_mutate_v2.py" "$EXP/out/sm25_1f_v2.json" \
  "$EXP/out/sm25_1f_CROSS_one_pixel_schema.json" one_pixel_actual_schema
python3 "$EXP/tools/crossreview_mutate_v2.py" "$EXP/out/sm25_2f_v2.json" \
  "$EXP/out/sm25_2f_CROSS_one_pixel_schema.json" one_pixel_actual_schema
python3 "$EXP/tools/crossreview_mutate_v2.py" "$EXP/out/sm24_1f_v2.json" \
  "$EXP/out/sm24_1f_CROSS_one_pixel_schema.json" one_pixel_actual_schema
python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_one_pixel_schema.json","F2":"'$EXP'/out/sm25_2f_CROSS_one_pixel_schema.json"}' \
  "$EXP/out/sm25_CROSS_one_pixel_schema_gt.json"
python3 "$EXP/tools/reconstruct_check_v2.py" sm24_anchor \
  '{"F1":"'$EXP'/out/sm24_1f_CROSS_one_pixel_schema.json"}' \
  "$EXP/out/sm24_CROSS_one_pixel_schema_gt.json"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out')
for n in ('sm25_1f','sm25_2f','sm24_1f'):
 d=json.load(open(p/f'{n}_CROSS_one_pixel_schema.json'))
 fen=d['hypotheses']['family_roles']['assignment']['fenestration']
 rs=[g['ink_by_family'][fen]['span_ratio'] for f in d['observations']['face_lines']
     for g in f['gaps']]
 print(n, sum(x >= 0.10 for x in rs), max(rs))
PY
# sm25_1f 42 0.5
# sm25_2f 36 0.333333
# sm24_1f 76 0.25
# 两次 reconstruct 的 overall_ok_pct 均为 0.0
```

实测 `span_ratio >= 0.10` 的 gap 数分别为：sm25 1F **42**、sm25 2F **36**、sm24 **76**；最大单像素 `span_ratio` 分别为 **0.5 / 0.333333 / 0.25**。整体仍为 0 分，只是因为其余长缺口已经把每个 gt target 压到阈值下，不能据此宣称每个单像素都不承重。

**必须修**：所有被 gt 尺子消费的 `gap.span_m/len_px/ink_by_family.{on_line,span_ratio,nearest_px,by_distance_px}` 都要由原图、family mask 和组件归属独立重算；变异必须写消费者真实 schema，并验证分支命中数。

---

## Q2：哪些数对不上

### 基线（实测）

```bash
cd /workspaces/EnergyPlus-Agent-dev
python3 AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/run_all.py
```

本轮完整重跑成功。请求书 / README 的主表数字大部分对得上：

- sm25 1F：**49 faces / 374 candidates / 22 pairs**；
- sm25 2F：**46 / 303 / 21**；
- sm24：**98 / 1185 / 8**；
- gt：sm25 **93.3**、sm24 **100.0**；
- `extend_runs_full`：sm25 **97.3**；sm25 1F reverse **49** 条违规、最差 **0.0127**；
- opening share：sm25 1F **0.9783 ≈ 97.8%**、sm24 **0.8028 ≈ 80.3%**；家具 gap 墨 **7 / 4832 = 0.145% ≈ 0.14%**；
- 立面：诚实 **24/24**，`clear_runs/shrink_runs/shift_lines` 均 **0/24**，`drop_vertical` **12/24**，spray/duplicate 仍 **24/24** 且 unpredicted **72/24**。

以下陈述与当前实测不符。

### Finding 3（实测）：无-gt 判据不是“五条”，是 **六条**

请求书问 Q1 时写“五条”，README §二标题与文件表也两次写“五条”；当前 `checks_as_drawn_v2.py` 的报告固定产出 **6** 项。

```bash
python3 - <<'PY'
import json
p='AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_checks_v2.json'
d=json.load(open(p))
print(len(d['checks']), [x['check'] for x in d['checks']])
PY
# 6 [...]
```

### Finding 4（实测）：perception 坏夹具不是“5 种，4 种红”，当前是 **5/5 至少一门红**

`call_the_windows_furniture` 加新门后也已红，因此请求书 §2.1 的“5 种，4 种红”是旧计数；README 的逐行表反而是当前形态。

```bash
python3 - <<'PY'
import json
p='AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/RESULTS_v2.json'
d=json.load(open(p))['perception_neuters']
bad={k:any(v=='red' for v in x.get('gates',{}).values()) for k,x in d.items() if k!='honest'}
print(bad, sum(bad.values()), '/', len(bad))
PY
# {...五项均为 True...} 5 / 5
```

### Finding 5（实测）：“诚实产物抓到 4 条面线复用”在当前一键结果中是 **0**

请求书 §一#3 写“新对账门在诚实产物上抓到了 4 条面线被卖两次”。当前三个诚实产物：sm25 1F reconcile 绿、sm25 2F 绿、sm24 degraded，三者 `violation_count` 都是 **0**；当前 `RESULTS_v2.json` 没有 4 条复用的诚实夹具。

```bash
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out')
for n in ('sm25_1f','sm25_2f','sm24_1f'):
 d=json.load(open(p/f'{n}_checks_v2.json'))
 c=next(x for x in d['checks'] if x['check'].startswith('pair_hypothesis'))
 print(n, c['status'], c['violation_count'], len(c.get('face_claimed_twice',[])))
PY
# sm25_1f green 0 0
# sm25_2f green 0 0
# sm24_1f degraded 0 0
```

若“4”来自被当前 perception 替换前的旧代码替身产物，应明确标成历史发现，不能写成当前 `run_all.py` 的数。

### Finding 6（实测）：最大重算偏差不是 0.004 px，“差 400 倍”也不成立

按当前 `check_self_consistency` 同一公式，对三份诚实产物逐边重算：最大值在 sm25 2F `L027`，为 **0.004834727 px**，按三位小数应为 **0.005 px**；1.5 px 门与它的比值是 **310.26 倍**，不是 400 倍。

```bash
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out')
worst=(None,None,-1)
for n in ('sm25_1f','sm25_2f','sm24_1f'):
 d=json.load(open(p/f'{n}_v2.json')); mp=d['observations']['calibration']['mm_per_px']/1000
 for f in d['observations']['face_lines']:
  c0,c1=f['support_cols_px']; s=1 if f['constant_world_axis']=='x' else -1
  want=sorted((f['pos_m']+s*(c0-f['pos_px'])*mp,f['pos_m']+s*(c1-f['pos_px'])*mp))
  e=max(abs(a-b) for a,b in zip(f['edges_m'],want))/mp
  if e>worst[2]: worst=(n,f['id'],e)
print(worst, 1.5/worst[2])
PY
# ('sm25_2f', 'L027', 0.004834726991565184) 310.2553675971667
```

### Finding 7（实测）：README“没有一条判据恒红或恒绿”与变异矩阵不符

对 README 所说的 sm25 1F 六种 self-neuter：

- `opening_role_matches_where_the_ink_sits`：**6/6 绿**；
- `pair_spacing_explicable_by_callouts`：**6/6 绿**；
- reconcile：**5 绿 / 1 红**。

```bash
python3 - <<'PY'
import json
p='AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/RESULTS_v2.json'
d=json.load(open(p))['plans']['sm25_1f']['self_check_neuters']
for gate in ('openrole','spacing','reconcile'):
 vals=[x[gate] for x in d.values()]
 print(gate, {s:vals.count(s) for s in set(vals)})
PY
# openrole {'green': 6}
# spacing {'green': 6}
# reconcile {'green': 5, 'red': 1}
```

另有一项不是“数值对不上”，但违反 README 开头的追溯承诺：`1.480 px`、参数扫描、sm24 立面“每面 4 个”、F-86 的 `170 px` 与候选修法 **94.7 / 5 个洞口**、立面 opening **34/34** 都不在 `RESULTS_v2.json`。这些数字本轮未判假，但不能称为由当前一条命令全部产出。

---

## Q3：perception 接口是否偷藏判断

### (a) 六桶本身谁在替模型做决定

**实测结论：当前三份 clean cfg 中，六桶没有一个由代码自动选答案。** `family_roles` / `wall_pairs` 从独立 perception 文件进入；其余四桶也原样搬入 hypotheses。三个 cfg 的 legacy `family_roles` / `wall_pairs` 均为 0 个。

```bash
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools')
for n in ('cfg_1f_full','cfg_2f_full','cfg_sm24'):
 d=json.load(open(p/f'{n}.json'))
 print(n, int('family_roles' in d), int('wall_pairs' in d), bool(d.get('perception')))
PY
# 三行均为：0 0 True
```

但接口有三处实质性问题：

1. **实测**：`non_wall_face_lines`、`unpaired_wall_faces`、`solid_band_walls`、`ambiguous_face_lines` 的 value/reason 完全不消费，只把 key 放进 set。README 所说“不是墙，并说明是什么”没有 gate。
2. **实测**：gt 重建器完全不消费 `wall_pairs` 与四个面线桶；它在 `_best_interior()` 中自行从所有 observation 重配任意两条线，或自行把 0.05–0.50 m 宽组判成 filled band。这与“hypotheses 不直接评分”一致，但它也意味着这些 perception 决定没有被当前 gt 证据验证。
3. **代码路径推断**：`cfg.setdefault('family_roles', ...)` / `setdefault('wall_pairs', ...)` 允许 legacy cfg 在 perception 文件存在时静默优先。当前三个 cfg 没触发，但接口应改成 perception 为唯一来源，发现双源就报冲突，而非设优先级。

### (b) 哪些“认”仍留在代码或根本没拎出来

1. **实测 + 代码路径**：`_extent()` 看到“被命名为 fenestration 的族”在 gap 中 `span_ratio >= 0.10`，就自动认定墙贯穿的是洞口并桥接；Finding 1 已证明这个代码判断可把 89.2 桥回 94.6。
2. **实测 + 代码路径**：`opening_role_matches_where_the_ink_sits` 用“gap 墨最多的族且份额 >= 0.50”硬判 fenestration role。它是对 perception 的启发式语义裁决，不只是引用/几何对账。当前 sm25 1F 的 argmax 份额为 **0.9783**，swap 后该门红且 gt **94.6 → 51.4**。
3. **实测**：墙配对 / 实心带判断在评分端被代码重做。把 49 条面线全部宣称为非墙后，gt 重建仍自行得到 **27 个 straddling_pair**，1F 总分仍 **94.6**。
4. **接口缺项（代码结构推断）**：指南明确把“这洞是门还是窗”归 reading 模型，但六桶没有任何 per-component / per-gap 的 opening identity 与 door/window 类型桶。当前代码只做“足够 fenestration 墨 ⇒ 可桥接”的二值判断；门窗分类既没被完整外置，也没有可评分产物。

### (c) “全塞 ambiguous”能否绕过

**能绕过 syntactic completeness；当前不是红，只是 degraded，而且 `violation_count=0`。** 其余五门全绿，gt 不变。

```bash
EXP=AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype
python3 "$EXP/tools/crossreview_mutate_v2.py" "$EXP/out/sm25_1f_v2.json" \
  "$EXP/out/sm25_1f_CROSS_all_ambiguous.json" all_ambiguous
python3 "$EXP/tools/checks_as_drawn_v2.py" "$EXP/out/sm25_1f_CROSS_all_ambiguous.json" \
  "$EXP/tools/cfg_1f_full.json" "$EXP/out/sm25_1f_CROSS_all_ambiguous_checks.json"
python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_all_ambiguous.json"}' \
  "$EXP/out/sm25_1f_CROSS_all_ambiguous_gt.json"
# 49/49 ambiguous；5 green + 1 degraded；degraded violation_count=0；gt=94.6
```

而且有更强的同类绕过：**49/49 全塞 `non_wall_face_lines`，六门全绿，gt 仍 94.6**。

```bash
python3 "$EXP/tools/crossreview_mutate_v2.py" "$EXP/out/sm25_1f_v2.json" \
  "$EXP/out/sm25_1f_CROSS_all_non_wall.json" all_non_wall
python3 "$EXP/tools/checks_as_drawn_v2.py" "$EXP/out/sm25_1f_CROSS_all_non_wall.json" \
  "$EXP/tools/cfg_1f_full.json" "$EXP/out/sm25_1f_CROSS_all_non_wall_checks.json"
python3 "$EXP/tools/reconstruct_check_v2.py" sm25-L_anchor \
  '{"F1":"'$EXP'/out/sm25_1f_CROSS_all_non_wall.json"}' \
  "$EXP/out/sm25_1f_CROSS_all_non_wall_gt.json"
# 6/6 green；reconcile violation_count=0；gt=94.6
```

建议把一条“完备性”拆成三条不同性质的 gate：

1. **语法覆盖**：每条 face 恰好落一个互斥桶；这是当前已有的最低层。
2. **有效认知覆盖**：明确报告 `positive_wall_faces / non_wall / ambiguous / total`；B 步前预先定义 ambiguity budget，超过即 **red**，不能是 `degraded + 0 violations`。阈值必须在冷启样本上定，不能用当前污染 perception 回填。
3. **独立语义评分**：一旦 gt 分母定义，ambiguous 按 abstention / missed denominator 计；`non_wall` 必须有受限 reason taxonomy、证据引用，并以 gt 或抽样审计验证。只要求“写一个字符串”仍可全塞 non-wall。

同时增加 per-gap/component 的 `opening_hypotheses`（component id、所属 wall face/pair、door/window/ambiguous、证据），禁止评分器用 aggregate gap ink 自动替模型完成这一步。

---

## Q4：不能进入 B 步；最小前置项

### 1. 定义机器化可评分分母与双向计分

必须在动 gt 前写清并实现：

- 哪些 source primitive / normalized run 是 reading 必须画的正目标；
- jamb cap、文字笔画、家具、洞口边、实心带两边分别如何进入或排除；
- 共线连续墨何时是一条、何时必须切段，target identity 如何稳定；
- 少画、错位、错切、重复、多画各如何计分；
- plan 与 elevation 同一口径，不能让 elevation `spray_lines` 的 **72** 条额外线只挂旗标仍得 24/24。

没有这条，gt as-drawn 层连“应存哪些答案”都未定义，任何 schema 写入都是先固化偶然实现、后补语义。

### 2. 关闭本轮 gap 假绿，并让变异命中真实消费者

最低验收是：本裁决的 1.2 m 作弊产物不能再与诚实产物同为 **94.6 / 六门全绿**；gap 的坐标、像素跨度、family profile、组件归属全部由原图独立重算。`punch_middle_one_pixel` 必须改写 `ink_by_family` 而非无人读取的 `opening_ink`，并记录实际进入 bridge 分支的 gap 数。

### 3. 冻结 perception 契约，而不是只冻结六个桶名

最低包括：

- perception 是唯一输入源，cfg 双源冲突响亮失败；
- per-gap/component 的 door/window/ambiguous 识别显式外置；
- `ambiguous` 有阻塞预算，`non_wall` 不能成为全绿逃生桶；
- 用从未看过 gt 分数的冷启隔离读图器跑至少 sm25 + 一种异方言，报告认知覆盖与弃权；当前主控手工 perception 只能保留为探索证据，不能作能力验收。

以上三项是最小组。F-86、sm24/sm21 立面坐标、进深台阶第二栋正例、一对一真实夹具仍应继续解决，但它们不是本裁决为“能否开始写 gt as-drawn 层”再额外扩张出的前置清单；第 1 项会规定其答案形态，第 2、3 项先保证这套形态不会被当前判据假绿证明。

---

## 本轮文件改动

仅在允许的 experiments 与 verdict 范围新增：

- `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/crossreview_mutate_v2.py`
- `out/sm25_1f_CROSS_missing_wall*`
- `out/sm25_1f_CROSS_fake_opening*` 与 `out/sm25_CROSS_fake_opening_gt.json`
- `out/*_CROSS_one_pixel_schema*`
- `out/sm25_1f_CROSS_all_ambiguous*`
- `out/sm25_1f_CROSS_all_non_wall*`
- 本裁决文件

未修改任何既有生产源、case、gt 或官方判据；未 commit / push。
