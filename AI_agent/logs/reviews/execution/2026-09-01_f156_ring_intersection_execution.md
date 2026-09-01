# 执行档 · **F-156**：边界环角点改「相邻支撑线求交」 —— ⛔⛔ **停下上报，未施工**

- **日期**：2026-09-01 · **施工方**：**Claude 家族施工席** · **派工单**：
  [F-156 实现单](../request/2026-09-01_f156_ring_from_intersection_implementation.md)
- **基线**：`a6f5383`（派工 prompt 指定）· 派工单正文写的是 `636ce56`
- **结论**：⛔ **停报**。命中派工单 §四硬要求 1 与 §六「必停」，另有**两条派工单未预见的承重级阻断**，
  其中**两条是机械可证的**（不是判断题）。
- ⭐ **`src/` 零改动、`case_tests/` 零改动、基线未重做**（见 §七 证据）。

---

## 一、开工自检（⛔ 逐条跑命令，不靠记忆）

```
$ git log --oneline -1
a6f5383 09.01e_DispatchThreeSeats_Baseline3601_ConcurrencyClauses
$ git status --porcelain
(空)
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/.../_editable_impl_energyplus_agent.pth
```
✅ 三条全对上。派工单点名的四份文档 + 探针 `ls` 全部存在。

---

## 二、§一 承重前提：**逐位复现成功**

```
$ timeout 900 python AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection/probe.py
...
TARGET plan-F1 cavity:8bd127719198fd63 valid=True explain=Valid Geometry vertices=24 area_m2=88.265600 expected_m2=88.27 delta_m2=-0.004400 interval_misses=0
TARGET plan-F2 cavity:495501ce9b36f0f3 valid=True explain=Valid Geometry vertices=16 area_m2=70.339200 expected_m2=70.34 delta_m2=-0.000800 interval_misses=0
HEALTHY count=25 all_baseline_edges_4=True all_rebuilt_vertices_4=True all_valid=True all_interval_misses_0=True
MISALIGNED_0P1MM plan-F1 cavity:04e1293098b1a95a alive=True explain=Valid Geometry vertices=8 area_m2=28.683212 interval_misses=0
```
⇒ **§一 四行读数与派工单逐位相同。前提这一侧没有问题，问题在别处。**

---

## 三、⛔ 阻断 A（**机械可证**）：`answer_compiler` 有一道 **facts/converter 边数必须相等** 的硬门，
## 而求交环的边数与答案侧的边数**对不上** —— 而 `answer_compiler.py` **不在我的写面**

`src/agent/judge/answer_compiler.py:1185`（原文）：
```python
            if len(zone.edges) != len(facts_edges):
                structural.append(
                    f"boundary_edge_count_mismatch:{view.view_id}:{cavity_id}:"
                    f"facts={len(facts_edges)} converter={len(zone.edges)}")
```
`structural` 非空 ⇒ `audit.passed=False` ⇒ `tests/test_boundary_condition_facts.py` 直接红。

**实测三个腔的两侧边数**（命令与原样输出见 §十 附录 A/B）：

| 腔 | 面积 m² | 求交环顶点数（F-155 实测） | 答案侧 converter zone | converter `edges` |
|---|---|---|---|---|
| `cavity:8bd127719198fd63` | 88.2656 | **24** | `F1-z0` | **16** |
| `cavity:495501ce9b36f0f3` | 70.3392 | **16** | `F2-z0` | **12** |
| `cavity:04e1293098b1a95a` | 28.6832 | **8** | `F1-z4` **和** `F1-z5` | **4 + 4** |

⇒ 三个腔**没有一个**边数对得上。差额恰好是**墙端头小折段**（0.12 m 级的 jog）：
答案侧走的是 **wall_axis 轮廓**，事实侧走的是 **clear-span 轮廓**，两者的折角数不同。
⛔ **这不是「改期望数值」能解决的**（验收 8 允许的是 `paired_edges` 这类读数变化），
它是**每腔逐边配对**的结构性失败，修法必然落在 `answer_compiler._boundary_pairing` /
`reconcile_boundary_basis`，或答案侧转换器 —— **两者都不在派工单 §十 给我的写面里**。

---

## 四、⛔ 阻断 B（**机械可证 + 推翻了 §一 结论 1**）：
## 28.68 那个腔在**答案里是两间房**，求交环把它焊成了一间

`tests/test_o21d_exclusion_gap.py:57` 自己的注释就写着：
```
CAVITY_SHARED = "cavity:04e1293098b1a95a"      # plan-F1, 28.68 m², hosts z4 AND z5
```
实测答案侧两间房的多边形（§十 附录 B 原文）：
```
F1 F1-z4 F1-r4 edges 4 ring_pts 4 area_m2 16.2324 valid True
     [(8.94, 5.88), (8.94, 9.9999), (5.0, 9.9999), (5.0, 5.88)]
F1 F1-z5 F1-r5 edges 4 ring_pts 4 area_m2 16.2332 valid True
     [(5.0, 9.9999), (8.94, 9.9999), (8.94, 14.12), (5.0, 14.12)]
```
⇒ **答案在 y=9.9999 m 处把它切成两间**（那正是 0.1 mm 错位的那道中间墙带，
事实层读数 `x const=100630 / 99430`，两条线之间就是墙体）。

而 F-155 的求交环给出的是**一个 8 顶点、`is_valid=True`、28.683212 m² 的整环** ——
`is_valid` 真、面积也真，**但形状是错的：它把两间房通过一条 0.1 mm 的缝焊成了一间。**

⭐⭐⭐ 两条推论，请主控裁定：
1. **派工单 §一 结论 1「F-153『两个病别当一个修』已被推翻」——【不成立】。**
   28.68 那个（形态 B）在旧表示下丢，在新表示下变成**错的形状**。
   「活了」≠「对了」。F-153 那条判定对形态 B 依然有效。
2. **派工单验收 1 的判据本身会放行这个错答案** ——
   它写的是「环 `is_valid=True` 且面积与 28.68 对得上」，上面这个错环**两条全过**。
   这正是 [[proxy-mistaken-for-the-thing]]：`is_valid` 与面积都是代理量，
   本体是「**它和答案里的房间是不是同一批房间**」。
   ⚠️ 这也是 #57「别拿边数当判据」那条教训的**同族第二形态**：换成 valid+面积仍然是代理量。

---

## 五、⛔ 阻断 C（**设计缺口**）：墙端头边**无法在现有事实模型里诚实表达**，而它**证明是躲不掉的**

### C-1 · 病灶定位：三个腔死在 `owner_count=0`，且**全部**是墙端头小折段
```
$ python <scratchpad>/dump_segs.py              # 完整输出见 §十 附录 C
== plan-F1 cavity:8bd127719198fd63 segs=60
    8 axis=x const=160000 [61600,98800] len=37200 owners=1
    9 axis=y const=98800 [160000,161200] len=1200  owners=0      <- 墙端头
   10 axis=x const=161200 [98800,100000] len=1200  owners=0      <- 墙端头
   11 axis=y const=100000 [161200,197600] len=36400 owners=1
   ...（另 8 段同型；F2 6 段；28.68 那腔 1 段）
```
⇒ 现在的 `_boundary_owners` 要求「同轴墙带的**某个面**在此 const 上、且**沿墙覆盖有正重叠**」。
端头段落在墙带的**端线**上（沿墙重叠恰为 0），故 `owners=0` ⇒ `reason=owner_count` ⇒ 整腔判丢。

### C-2 · 端头段**不能丢**（实测，⛔ 不是口味问题）
我实测了「把无主端头段丢掉、让相邻两条面线延伸求交」这条更干净的路：
```
$ python <scratchpad>/probe_dropjog.py
plan-F1 cavity:8bd127719198fd63 src_area=88.265600
   ALL_RUNS  n=24 valid=True area=88.2656
   DROP_JOGS n=14 valid=True area=88.1504
plan-F1 cavity:04e1293098b1a95a src_area=28.683212
   ALL_RUNS  n=8  valid=True area=28.683212
   DROP_JOGS n=7  err=parallel:('x', 100630, 52401, 88800):('x', 99430, 52401, 88800)  <- 结构性失败
plan-F2 cavity:495501ce9b36f0f3 src_area=70.339200
   ALL_RUNS  n=16 valid=True area=70.3392
   DROP_JOGS n=10 valid=True area=70.2528
```
⇒ 28.68 那腔一丢端头，**相邻两条支撑线变成平行**（`x:100630` 与 `x:99430`），求交无定义 ——
**环根本造不出来**。⇒ **端头线必须留作支撑线**，F-155 探针的形态是唯一走得通的。

### C-3 · 但端头边**没有诚实的证据可填**
候选唯一性我查过了，**不需要任何容差、不需要取最近线**：每一段无主端头段
**恰好有 1 个**端头归属候选（`probe_supports.py`，§十 附录 D）。所以「找得到」不是问题。
问题在**填什么**：`BoundaryConditionEvidenceV1`（`as_measured.py:317`）结构上要求

| 字段 | 约束 | 端头边的实情 |
|---|---|---|
| `raw_face_const` / `opposite_face_const` | 一对**平行面** | 端头**没有配对的对面**；勉强填「墙段另一端」= 把**墙长**当对面 |
| `thickness_units` | `= abs(far-near)` 且 **> 0** | 会变成**墙的长度**（几米～十几米），字段名叫 thickness ⇒ [[observation-named-as-fact-travels-as-fact]] |
| `cavity_side_face_line_ids` / `far_side_face_line_ids` | 各 **min_length=1** | 端头线上**没有任何笔画**（`face_line_ids_lo/hi` 都在长边上）|
| `boundary_condition` 的推导 | 出口射线法 | 端头的外法线**沿墙长方向**，射线要穿越整条墙（实测约 9.6 m）才出材料，
落点是与本腔无关的另一个房间 ⇒ 判成 `interzone` 就是**凭空造事实** |

⇒ 无论怎么填都是**在承重位置上编一个数**。这是一个**模型层的设计决定**
（加 `method` 字面量？加端头专用证据类型？还是根本不让端头成为 edge？），
**派工单 §二 的任务清单里没有把它派给任何人**，而它的每个选项都会被跨家族审判成
「施工方自行扩路」。⇒ 按 [[dispatch-options-list-is-itself-a-hidden-premise]]，我停报。

---

## 六、②-1d 那条锁的形态判定（派工单验收 9 / §四）

**判定：⛔⛔ 名单式，且【尚未】按 ②-1d 单 §九 改成规则+读数两半。**

`tests/test_o21d_exclusion_gap.py:89`（HEAD `a6f5383` 原文，`sed -n 88,104p` 亲验）：
```python
def test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger():
    ...
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
    by_cavity = {(e.view_id, e.facts_cavity_id): e for e in audit.exclusions}
    assert all(e.evidence == "registered_ring_loss" for e in audit.exclusions)
    assert all(e.registered_loss_reason == "owner_count" for e in audit.exclusions)
    # 88.27 / 28.68 / 70.34 m² -> the three known-defect rooms, in units².
    assert by_cavity[("plan-F1", CAVITY_88)].registered_loss_area_units2 == 8826560000
    assert by_cavity[("plan-F1", CAVITY_SHARED)].registered_loss_area_units2 == 2868321200
    assert by_cavity[("plan-F2", CAVITY_70)].registered_loss_area_units2 == 7033920000
```
逐个点名那 3 个腔 + 逐个断言登记面积 + `all(... == "owner_count")` +
`(29, 29)` 全额账 —— **判据钉住了缺陷本身的存在**（题错 #58 的形状）。
本单一旦让它们不再是 exclusion，这条锁**必红**，且 `test_deregistering_a_live_cavity_reddens...`
（同文件 105 行起）也会跟着红。

⇒ 派工单 §四说「本单施工时那条锁应当已经改好；若还没改，停下上报」——
**它没改。** ⛔ 我没有动那个文件（不是我的写面）。

---

## 七、我做过的事 + 证据（⛔ 零施工）

| 项 | 命令 | 读数 |
|---|---|---|
| `src/` 与 `case_tests/` 我的写面零改动 | `git diff --stat -- src/agent/judge/as_measured.py case_tests tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py tests/test_o21d_exclusion_gap.py` | **空输出**（交件前最后一个动作之后重核）。⚠️ 全树 `git status` 里出现的 `tests/test_o22m4_wall_compiler.py` 及两份 md 是 **GLM 席 / GPT 席在飞的产物**，整场一直在变，⛔ 非我所改、未碰 |
| 未跟踪文件 | `git status --porcelain` | `?? AI_agent/logs/reviews/verdict/2026-09-01_o22m56_rework_crossreview_gpt.md` = **GPT 席**的裁决 md |
| 受影响子集（⭐ 零改动锚点，`-n 6`） | `python -m pytest -n 6 -q tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py tests/test_o21d_exclusion_gap.py` | **`91 passed in 19.71s`**（exit 0）|
| 基线三件套 | 未触碰 | ⛔ 未重做，⛔ 未签 revision |
| ⛔ 全量 pytest / `-n auto` / `pip install -e .` | 未跑 | — |

**哨兵两次读数**（开工前 / 交件前，均为原文）：
```
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  .../_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  .../_editable_impl_energyplus_agent.pth
```
且 `cat` 内容为 `/workspaces/EnergyPlus-Agent-dev` ⇒ **指向主树，未被改指**。

探针脚本一律落在会话 scratchpad（⛔ 未落仓库根、⛔ 未落 `src/`）：
`dump_baseline.py` / `dump_segs.py` / `probe_supports.py` / `probe_dropjog.py` / `probe_excl.py` / `probe_zones.py`。
若主控要保留，我可以按要求搬进 `AI_agent/logs/experiments/`。

---

## 八、我认为派工单哪里写错了（验收 ⑥）

1. ⭐⭐⭐ **§一 结论 1 是错的**：「一次换表示治好了 F-153 的两个病」不成立。
   28.68 那个只是**造出了一个 valid 的错形状**（答案是两间房，见 §四）。
2. ⭐⭐⭐ **验收 1 的判据会放行这个错答案**（`valid` + 面积仍是代理量）。
   建议改成：**求交环必须与答案侧该腔的 converter zone 一一对应，且逐边可配对**。
3. ⭐⭐ **§二任务清单缺了最硬的一项**：墙端头边的 `boundary_condition` / 证据怎么填（§五 C-3）。
   这是模型层设计决定，不写进单子就必然由施工方私自拍板。
4. ⭐⭐ **§十写面划得比任务小**：任务要求三个腔「活过来」，
   而让它们活过来必然触发 `answer_compiler.py:1185` 的边数门与配对逻辑，
   那个文件**不在写面里**（§三）。任务项与写面自相矛盾。
5. ⭐ **§四的假设没兑现**：②-1d 的锁至今是名单式（§六）。
6. ⭐（只记不停）**跑测并行度写了两个数**：§三禁令 5 写 `-n 4`，§十纪律 2 写 `-n 6`。
   我按 §十（后写、且是并发条款）跑的 `-n 6`。
7. ⭐（只记不停）**交件文件名两处不一致**：§七 写 `<日期>_f156_ring_intersection_execution.md`，
   派工 prompt 写 `2026-09-01_f156_execution.md`。我按派工单（权威）取名。

---

## 九、我建议的下一步（⛔ 主控裁定，我不自行开工）

按依赖顺序，三件事都得先有人拍板：
1. **28.68 那个腔到底该出一个环还是两个环？** 答案说两间房。
   若是两间，求交重建**必须先能沿那道 0.1 mm 缝把腔切开** —— 这是一条 F-155 没做过的实验。
2. **端头边的证据形态**（§五 C-3）：新证据类型 / 新 `method` / 还是端头只进环几何不进 edge？
3. **facts↔converter 逐边配对的口径**（§三）：clear-span 环 24 边 vs wall_axis 环 16 边，
   谁向谁靠？这一步必然要动 `answer_compiler.py`，需要重新划写面（很可能要单开一张单）。

**我自认最薄弱的一处**：§三、§四 是机械可证的（读的是断言原文和答案侧多边形原文）；
**§五 C-3 是判断题** —— 我论证的是「现有证据模型没有诚实的填法」，
若复核方认为某种填法可接受（例如端头边一律 `boundary_condition="unknown"` +
新增 `method="facts_wall_endcap_v1"` 并把 `thickness_units` 的含义按 method 分叉），
那 C-3 就不是阻断，只是一个需要签字的设计决定。**希望复核方重点打这一处。**

---

## 十、附录 · 原样输出（⛔ 不转述，全部是命令直出）

### 附录 A · 当前排除账 + 答案侧 zone 边数（`probe_excl.py`）
```
$ python <scratchpad>/probe_excl.py
passed True paired_edges 100 converter_zones 29 accounted 29
EXCL plan-F1 cavity:8bd127719198fd63 F1-z0 registered_ring_loss owner_count 8826560000
EXCL plan-F1 cavity:04e1293098b1a95a F1-z4 registered_ring_loss owner_count 2868321200
EXCL plan-F1 cavity:04e1293098b1a95a F1-z5 registered_ring_loss owner_count 2868321200
EXCL plan-F2 cavity:495501ce9b36f0f3 F2-z0 registered_ring_loss owner_count 7033920000
excluded zone ids {'F2-z0', 'F1-z5', 'F1-z4', 'F1-z0'}
ZONE F1 F1-z0 edges 16
ZONE F1 F1-z4 edges 4
ZONE F1 F1-z5 edges 4
ZONE F2 F2-z0 edges 12
```
⭐ 注意第 2/3 行：**同一个 `cavity:04e1293098b1a95a` 被两个 converter zone 各自排除一次。**

### 附录 B · 答案侧四个 zone 的多边形（`probe_zones.py`）
```
$ python <scratchpad>/probe_zones.py
F1 F1-z0 F1-r0 edges 16 ring_pts 18 area_m2 99.9344 valid True
     [(8.94, 14.12), (8.94, 5.88), (5.0, 5.88), (5.0, 3.94), (20.94, 3.94), (20.94, -0.0), (25.0, -0.0), (25.0, 6.0), (15.0, 6.0), (15.0, 5.88), (11.06, 5.88), (11.06, 20.0), (9.94, 20.0), (9.94, 16.06), (0.0, 16.06), (0.0, 14.0), (5.0, 14.0), (5.0, 14.12)]
F1 F1-z4 F1-r4 edges 4 ring_pts 4 area_m2 16.2324 valid True
     [(8.94, 5.88), (8.94, 9.9999), (5.0, 9.9999), (5.0, 5.88)]
F1 F1-z5 F1-r5 edges 4 ring_pts 4 area_m2 16.2332 valid True
     [(5.0, 9.9999), (8.94, 9.9999), (8.94, 14.12), (5.0, 14.12)]
F2 F2-z0 F2-r0 edges 12 ring_pts 14 area_m2 79.5252 valid True
     [(8.94, 14.12), (8.94, 5.88), (5.0, 5.88), (5.0, 3.94), (25.0, 3.94), (25.0, 6.0), (15.0, 6.0), (15.0, 5.88), (11.06, 5.88), (11.06, 16.06), (-0.0, 16.06), (-0.0, 14.0), (5.0, 14.0), (5.0, 14.12)]
```
（浮点尾数为便于阅读做了截断显示；判断只用到「几间房 / 切在哪 / 几条边」这三件事，未依赖末位。）

### 附录 C · 三个丢环腔的**全部无主段**（`dump_segs.py`，只截 `owners=0` 的行）
```
plan-F1 cavity:8bd127719198fd63 (segs=60)
    9 axis=y const=98800  [160000,161200] len=1200 owners=0
   10 axis=x const=161200 [98800,100000]  len=1200 owners=0
   30 axis=x const=60000  [110000,111200] len=1200 owners=0
   31 axis=y const=111200 [57600,60000]   len=2400 owners=0
   40 axis=x const=38800  [208800,210000] len=1200 owners=0
   41 axis=y const=208800 [38800,40000]   len=1200 owners=0
   51 axis=y const=88800  [57600,60000]   len=2400 owners=0
   52 axis=x const=60000  [88800,90000]   len=1200 owners=0
   58 axis=x const=140000 [88800,90000]   len=1200 owners=0
   59 axis=y const=88800  [140000,142400] len=2400 owners=0
plan-F1 cavity:04e1293098b1a95a (segs=16)
   10 axis=y const=52401  [99430,100630]  len=1200 owners=0
plan-F2 cavity:495501ce9b36f0f3 (segs=48)
   20 axis=x const=60000  [110000,111200] len=1200 owners=0
   21 axis=y const=111200 [57600,60000]   len=2400 owners=0
   41 axis=y const=88800  [57600,60000]   len=2400 owners=0
   42 axis=x const=60000  [88800,90000]   len=1200 owners=0
   46 axis=x const=140000 [88800,90000]   len=1200 owners=0
   47 axis=y const=88800  [140000,142400] len=2400 owners=0
```
⇒ **17 段，无一例外全是 1200 / 2400 单位（0.12 / 0.24 m）的墙端头小折段。**
其余 107 段全部 `owners=1`。

### 附录 D · 无主段的归属候选唯一性（`probe_supports.py`）
```
$ python <scratchpad>/probe_supports.py
== plan-F1 cavity:8bd127719198fd63 ccw=False
  seg  9 axis=y const=98800 [160000,161200] owners=0 endcap_owners=1 [('x', 160000, 161200)] propagated_face=1 [('y', 98800, 100000)]
  seg 10 axis=x const=161200 [98800,100000] owners=0 endcap_owners=1 [('y', 98800, 100000)] propagated_face=1 [('x', 160000, 161200)]
  seg 30 axis=x const=60000 [110000,111200] owners=0 endcap_owners=1 [('y', 110000, 111200)] propagated_face=1 [('x', 57600, 60000)]
  seg 31 axis=y const=111200 [57600,60000] owners=0 endcap_owners=1 [('x', 57600, 60000)] propagated_face=1 [('y', 110000, 111200)]
  seg 40 axis=x const=38800 [208800,210000] owners=0 endcap_owners=1 [('y', 208800, 210000)] propagated_face=1 [('x', 38800, 40000)]
  seg 41 axis=y const=208800 [38800,40000] owners=0 endcap_owners=1 [('x', 38800, 40000)] propagated_face=1 [('y', 208800, 210000)]
  seg 51 axis=y const=88800 [57600,60000] owners=0 endcap_owners=1 [('x', 57600, 60000)] propagated_face=1 [('y', 88800, 90000)]
  seg 52 axis=x const=60000 [88800,90000] owners=0 endcap_owners=1 [('y', 88800, 90000)] propagated_face=1 [('x', 57600, 60000)]
  seg 58 axis=x const=140000 [88800,90000] owners=0 endcap_owners=1 [('y', 88800, 90000)] propagated_face=1 [('x', 140000, 142400)]
  seg 59 axis=y const=88800 [140000,142400] owners=0 endcap_owners=1 [('x', 140000, 142400)] propagated_face=1 [('y', 88800, 90000)]
== plan-F1 cavity:04e1293098b1a95a ccw=False
  seg 10 axis=y const=52401 [99430,100630] owners=0 endcap_owners=1 [('x', 99430, 100630)] propagated_face=0 []
== plan-F2 cavity:495501ce9b36f0f3 ccw=False
  seg 20 axis=x const=60000 [110000,111200] owners=0 endcap_owners=1 [('y', 110000, 111200)] propagated_face=1 [('x', 57600, 60000)]
  seg 21 axis=y const=111200 [57600,60000] owners=0 endcap_owners=1 [('x', 57600, 60000)] propagated_face=1 [('y', 110000, 111200)]
  seg 41 axis=y const=88800 [57600,60000] owners=0 endcap_owners=1 [('x', 57600, 60000)] propagated_face=1 [('y', 88800, 90000)]
  seg 42 axis=x const=60000 [88800,90000] owners=0 endcap_owners=1 [('y', 88800, 90000)] propagated_face=1 [('x', 57600, 60000)]
  seg 46 axis=x const=140000 [88800,90000] owners=0 endcap_owners=1 [('y', 88800, 90000)] propagated_face=1 [('x', 140000, 142400)]
  seg 47 axis=y const=88800 [140000,142400] owners=0 endcap_owners=1 [('x', 140000, 142400)] propagated_face=1 [('y', 88800, 90000)]
```
⭐ 两条读数值得注意：
1. `endcap_owners` **17 段全部恰好 = 1** ⇒ 归属是唯一的，**不需要容差、不需要取最近线**。
2. ⭐⭐ **`seg 10`（28.68 那腔）的 `propagated_face=0`** ——
   它的 const 是 `52401`，而旁边那道墙的面在 `52400`（差 **1 个单位 = 0.1 mm**）。
   ⇒ 「把面线延长穿过接头」这条更诚实的路**在这一段上根本无解**，
   只有「端头线」这条路走得通。这也再次说明 **0.1 mm 错位那个病并没有被换表示治好**，
   它只是被换成了另一种表现形式（见 §四）。

### 附录 E · 当前基线状态（供重做基线时对照，本单**未**重做）
```
$ python <scratchpad>/dump_baseline.py
VIEW plan-F1 edges=44 losses=2 cavities_with_edges=11
VIEW plan-F2 edges=56 losses=1 cavities_with_edges=14
  LOSS cavity:04e1293098b1a95a reason=owner_count area_m2=28.683212 owner_count=0
  LOSS cavity:8bd127719198fd63 reason=owner_count area_m2=88.265600 owner_count=0
  LOSS cavity:495501ce9b36f0f3 reason=owner_count area_m2=70.339200 owner_count=0
```
⇒ 合计 **100 条边**（= `paired_edges == 100`）、**3 条 loss**、**25 个健康腔各 4 边**。
