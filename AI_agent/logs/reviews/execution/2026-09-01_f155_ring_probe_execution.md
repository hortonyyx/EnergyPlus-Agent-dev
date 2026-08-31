# F-155 支撑线求交判别实验执行档

- 日期：2026-09-01
- 席位：GPT 家族施工席
- 派工：`2026-09-01_f155_ring_from_supportline_intersection_probe.md`
- 性质：只读判别实验；未改 `src/`、`case_tests/` 或既有测试

## 一、开工自检

### 1. HEAD

命令：

```bash
git rev-parse HEAD
```

原样输出：

```text
58bb59f28d785139b48df642783db2c4db7ab537
```

### 2. §一独立复现

不是转引主控读数，也没有贴回 `endcap_attempt.diff`。探针重新实现精确端头判据，
只在内存中临时替换 owner/classifier，执行后在 `finally` 恢复。运行命令与完整输出见
§二。关键原样输出：

```text
CONTROL plan-F1 total_edges=88 losses=1
CONTROL_RING plan-F1 cavity:8bd127719198fd63 edges=44 valid=False explain=Self-intersection[110000 159400]
CONTROL_LOSS plan-F1 cavity:04e1293098b1a95a area_m2=28.683212
CONTROL plan-F2 total_edges=91 losses=0
CONTROL_RING plan-F2 cavity:495501ce9b36f0f3 edges=35 valid=False explain=Self-intersection[168500 40000]
```

同一输出中 F1 的 11 个、F2 的 14 个健康腔均各 4 边且 `Valid Geometry`。因此
§一读数由本席独立复现，未触发停报。

### 3. 指定四文件基线

命令：

```bash
pytest -n 4 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py
```

开工原样输出：

```text
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /workspaces/EnergyPlus-Agent-dev
configfile: pyproject.toml
plugins: langsmith-0.7.33, xdist-3.8.0, anyio-4.13.0
created: 4/4 workers
4 workers [84 items]

........................................................................ [ 85%]
............                                                             [100%]
============================= 84 passed in 20.59s ==============================
```

## 二、探针方法与原样输出

事实输入是 `build_as_measured` 产出的 `view.walls`、`view.openings` 与 footprint。
每个矩形事实贡献两条长边支撑线和两条精确端头支撑线；每条线都保留
`axis + const + along interval`。腔 polygon 只用来给循环拓扑顺序，入选支撑线必须被
事实目录的有限区间完整覆盖；相邻角点只由两条异轴线求交，不传播原 span 端点。

命令：

```bash
python AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection/probe.py
```

原样输出：

```text
=== F154_ENDPOINT_CONTROL ===
CONTROL plan-F1 total_edges=88 losses=1
CONTROL_RING plan-F1 cavity:04b8b99e62970cbb edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:0c7cd1f86b273bce edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:165160ca16361798 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:19ce2896d9112b53 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:431c2f0028190f75 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:6d7673d578be2be4 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:8bd127719198fd63 edges=44 valid=False explain=Self-intersection[110000 159400]
CONTROL_RING plan-F1 cavity:993887da41ec74a9 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:c7136b4c7889bf5e edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:c921d630f76ca4ef edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:d3ec10fb0854f71e edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F1 cavity:f8f1ffee6f811b8d edges=4 valid=True explain=Valid Geometry
CONTROL_LOSS plan-F1 cavity:04e1293098b1a95a area_m2=28.683212
CONTROL plan-F2 total_edges=91 losses=0
CONTROL_RING plan-F2 cavity:1286a0618098162c edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:40db0541085c478f edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:495501ce9b36f0f3 edges=35 valid=False explain=Self-intersection[168500 40000]
CONTROL_RING plan-F2 cavity:4c2f154dbec2d821 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:578c4a55097de953 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:5e3a2e1732ecfd29 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:77a6c1cd439c2a51 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:80cfefab8ece9fe8 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:9a0d999723b21128 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:9f6222de6c1cb0dd edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:ab0321fda3b93fc9 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:b7a7218654f78e86 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:c05a27776af4446e edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:efadf6e8a5eb2516 edges=4 valid=True explain=Valid Geometry
CONTROL_RING plan-F2 cavity:f4ae00d4959f5348 edges=4 valid=True explain=Valid Geometry
=== SUPPORT_INTERSECTION_EXPERIMENT ===
REBUILT plan-F1 cavity:8bd127719198fd63 supports=24 vertices=24 valid=True explain=Valid Geometry area_m2=88.265600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:c921d630f76ca4ef supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=17.108000 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:993887da41ec74a9 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=17.544800 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:19ce2896d9112b53 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=28.028000 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:04e1293098b1a95a supports=8 vertices=8 valid=True explain=Valid Geometry area_m2=28.683212 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:431c2f0028190f75 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=7.061600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:0c7cd1f86b273bce supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:04b8b99e62970cbb supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:c7136b4c7889bf5e supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:6d7673d578be2be4 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:f8f1ffee6f811b8d supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:d3ec10fb0854f71e supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.188000 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F1 cavity:165160ca16361798 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=28.464800 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:495501ce9b36f0f3 supports=16 vertices=16 valid=True explain=Valid Geometry area_m2=70.339200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:b7a7218654f78e86 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=17.108000 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:ab0321fda3b93fc9 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=17.544800 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:4c2f154dbec2d821 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=13.795600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:5e3a2e1732ecfd29 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=29.120000 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:1286a0618098162c supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=13.795600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:f4ae00d4959f5348 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=17.326400 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:578c4a55097de953 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=7.061600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:9a0d999723b21128 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:efadf6e8a5eb2516 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:c05a27776af4446e supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=6.843200 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:77a6c1cd439c2a51 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=7.061600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:9f6222de6c1cb0dd supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=13.795600 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:40db0541085c478f supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=14.232400 source_symdiff_m2=0.000000 interval_misses=0
REBUILT plan-F2 cavity:80cfefab8ece9fe8 supports=4 vertices=4 valid=True explain=Valid Geometry area_m2=13.686400 source_symdiff_m2=0.000000 interval_misses=0
=== REQUIRED_SUMMARY ===
TARGET plan-F1 cavity:8bd127719198fd63 valid=True explain=Valid Geometry vertices=24 area_m2=88.265600 expected_m2=88.27 delta_m2=-0.004400 interval_misses=0
TARGET_SUPPORTS plan-F1 cavity:8bd127719198fd63 x:142400[2400,88800] y:2400[142400,197600] x:160000[2400,98800] y:98800[160000,161200] x:161200[98800,100000] y:100000[161200,197600] x:197600[77600,147600] y:110000[60000,197600] x:60000[110000,111200] y:111200[57600,60000] x:57600[111200,247600] y:247600[2400,57600] x:2400[173600,247600] y:210000[2400,38800] x:38800[208800,210000] y:208800[38800,40000] x:40000[52400,208800] y:52400[2400,78399] x:57600[52400,88800] y:88800[57600,60000] x:60000[88800,90000] y:90000[60000,140000] x:140000[88800,90000] y:88800[140000,142400]
TARGET plan-F2 cavity:495501ce9b36f0f3 valid=True explain=Valid Geometry vertices=16 area_m2=70.339200 expected_m2=70.34 delta_m2=-0.000800 interval_misses=0
TARGET_SUPPORTS plan-F2 cavity:495501ce9b36f0f3 x:142400[2400,88800] y:2400[142400,197600] x:160000[2400,147600] y:110000[60000,160000] x:60000[110000,111200] y:111200[57600,60000] x:57600[111200,247600] y:247600[2400,57600] x:40000[52400,247600] y:52400[2400,78399] x:57600[52400,88800] y:88800[57600,60000] x:60000[88800,90000] y:90000[60000,140000] x:140000[88800,90000] y:88800[140000,142400]
HEALTHY count=25 all_baseline_edges_4=True all_rebuilt_vertices_4=True all_valid=True all_interval_misses_0=True
MISALIGNED_0P1MM plan-F1 cavity:04e1293098b1a95a alive=True explain=Valid Geometry vertices=8 area_m2=28.683212 interval_misses=0
```

## 三、判别答案

**求交重建能拼拢。** F1/F2 走廊分别得到 24/16 顶点，Shapely 均报
`Valid Geometry`；面积为 88.265600 / 70.339200 m²，相对派工方四舍五入读数
88.27 / 70.34 m² 的差为 -0.004400 / -0.000800 m²。更强的核对是两者相对事实源腔
对称差都恰为 0.000000 m²，且所有角点都落在相邻两条有限支撑区间内。

双向对撞也通过：25 个健康腔仍全部 valid、仍全部 4 顶点；28.683212 m² 的
0.1 mm 错位腔也活了，成为 8 顶点 valid 环。后者只记不判。

确信度：**高（约 0.9）**。最薄弱处是循环拓扑顺序仍由事实层算出的 cavity component
提供；实验已经证明线位、有限区间和角点不依赖旧 owner/端点拼接，但尚未证明仅凭一袋
无序 wall supports 就能唯一恢复 cavity 的环序。复核方应重点攻击这里：换一种不读取
`cavity.exterior` 顺序的拓扑追踪，是否仍得到同一 24/16 顶点环。

## 四、零触碰与回归

开工时主树已存在他席位改动，其中当时 tracked 的受保护树差异为：

```text
 src/agent/reading/as_drawn/schema.py | 23 ++++++++++++++++++-----
 1 file changed, 18 insertions(+), 5 deletions(-)
```

收尾时，派工方已预告的另一席位又并发写入 `answer_compiler.py`。命令：

```bash
git diff --stat 58bb59f -- src/ case_tests/
git diff --name-only 58bb59f -- src/ case_tests/
git status --short src case_tests AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection AI_agent/logs/reviews/execution/2026-09-01_f155_ring_probe_execution.md
```

收尾原样输出：

```text
 src/agent/judge/answer_compiler.py   | 106 ++++++++++++++++++++++++++++-------
 src/agent/reading/as_drawn/schema.py |  23 ++++++--
 2 files changed, 104 insertions(+), 25 deletions(-)
src/agent/judge/answer_compiler.py
src/agent/reading/as_drawn/schema.py
 M src/agent/judge/answer_compiler.py
 M src/agent/reading/as_drawn/schema.py
?? AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection/
?? AI_agent/logs/reviews/execution/2026-09-01_f155_ring_probe_execution.md
?? src/agent/correction/decision_executor.py
?? src/agent/correction/decision_schema.py
```

因此派工单要求的 `git diff --stat 58bb59f -- src/ case_tests/` 在共享脏树上不可能为空；
schema 差异在本席开工前已存在，compiler 差异由已预告的并发席位在实验期间写入，
correction 两文件也在开工 status 中已经存在。本席新增文件仅位于指定 experiment 目录
和本执行档，没有写 `src/`、`case_tests/` 或既有测试。

末次四文件回归仍使用 `-n 4`，原样尾读数：

```text
created: 4/4 workers
4 workers [84 items]

........................................................................ [ 85%]
............                                                             [100%]
============================= 84 passed in 24.42s ==============================
```

对本席三文件运行 `git diff --check -- ...`，原样输出为空。
