# 执行日志 · F-12 调查：下游重建的墙顶点与内核 snapshot 不一致

> **调查单**：`AI_agent/logs/reviews/request/2026-08-06_f12_wall_vertex_drift_investigation_glm.md`
> **席位**：GLM-5.2（调查席）· **基点**：`6.15_ValidationArchM0toM4` @ `756e821` · **日期**：2026-08-06
> **边界遵守**：⛔ 零生产码/测试改动 · ⛔ 零 commit/push/`git add -A` · ⛔ 未碰 `case_tests/` 未跟踪目录（仅只读）· ⛔ 未放宽 `_vertex_drift_issues` 或容差 · ✅ 一次性脚本全在 `/tmp/f12_*.py`

---

## 0. 开工自检（§0）

| 检查 | 期望 | 实测 |
|---|---|---|
| `git log --oneline -1` | `756e821` | `756e821 08.06_f12_downstream_wall_vertex_drift_registered` ✅ |
| `pwd` | `/workspaces/EnergyPlus-Agent-dev` | 一致 ✅ |
| `git status --short` | 4 个 case_tests 未跟踪目录 + 本单 | 一致（另：证据目录 ③ 已入仓故不在 untracked，见下）✅ |

自检通过，未停。

---

## 1. TL;DR（六问一句话）

1. **Q1 漂移形态**：①②**逐顶点完全一致**（100/100）。drift 门比的是 ②snapshot vs ③下游 ConfigState。③的精确顶点**零成本途径全部穷尽**（trace 不落盘 / issue detail 不打印 / 熔断未产 IDF），故"平移 vs 顺序"无法离线区分；但零成本可排除"数量不同"（墙全 4 顶点）与"精度不同"（snapshot 量化 2dp 会抹平）。**最可能 = 顶点顺序（CCW/起点）或系统性坐标偏移**，需最小烧钱探针定论（方案见 §8）。
2. **Q2 分界**：**①→② 没有偏差**（snapshot 忠实冻结内核几何）；不一致发生在 **②→③，即下游 surface 节点重建几何时**。⇒ **责任方 = 下游③，不在本项目侧 5_intakeoutput**。
3. **Q3 为什么只有墙**（机械证明）：**24 个 exterior 墙 100% 漂移 + 20 对 interzone 配对墙"每对一个漂移一个不漂移"（20/20 分裂）**；Floor/Ceiling（水平面、z 单值、x/y=footprint 矩形）与 Window（fenestration_specs 给裸顶点 + prompt 命"照抄不重算"）几何最简/被指示照抄。**唯独 surface.py 的 prompt 制度性地命 LLM 丢弃 surface_specs 已写死的墙顶点、改用 zone_specs 重算**——只有墙被"重新推导几何"，所以只有墙错。
4. **Q4 修法**：见 §7（3 选项 + 什么都不改的后果）。⛔ 未动手。
5. **Q5 同族**：与 **F-11 最同族**（都是下游 LLM 节点对几何的处理偏离内核），但形状不同：F-11=漏建（missing）、F-12=建了顶点错（differ）。与 F-5/F-7/F-10（本侧接口拼写/签名错位）**不同族**。F-12 的新形状 = **本侧 prompt 制度性地把几何推导交给 LLM**，比 F-11 偶发漏建更系统性。
6. **Q6 不变量#1 违反边**：违反"**代码做所有几何（建模+切配）+ 装配**"中的**建模**边——墙顶点生成（由 zone_specs 的 z_floor/ceiling_height 推 z、由 footprint/specs 推 x/y）被 `surface.py` 的 system prompt 交给 LLM，而非代码。修法落点有张力（见 §7/§9）。

**关键取舍**：本调查**未烧钱跑真链路**。决定责任方的 Q2 与触不变量违反的 Q6 已被零成本证据决定性回答；Q1 的"顺序 vs 平移"精确区分不改变责任方与修法方向，烧钱探针方案交派工方拍板（§8）。

---

## 2. 证据清单（全部离线可读，零成本）

| 标记 | 路径 | 规模 | 角色 |
|---|---|---|---|
| ① | `case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json` | 29947 B，11 字段；`surface_specs`=**15865 字符** | 内核产出（几何源） |
| ② | 同目录 `output_coordinate_snapshot.json` | 115 records（100 BuildingSurface + 15 Fenestration） | E4 前冻结的期望顶点 |
| ③ | `AI_agent/logs/experiments/2026-08-06_f12_wall_vertex_drift/downstream_run.log` | 530 行 | 真链路日志（已入仓） |

可独立复核：
```bash
wc -l AI_agent/logs/experiments/2026-08-06_f12_wall_vertex_drift/downstream_run.log   # 530
python3 -c "import json;d=json.load(open('case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/output_coordinate_snapshot.json'));print(len(d['records']))"  # 115
```

---

## 3. 核心判定

### 3.1 drift 门到底比的是哪两方（澄清调查单措辞）

调查单 §3 把检查笼统指为 `_vertex_drift_issues（output_coordinates.py:794）`。**实际有两个独立 drift 比较**（`src/validator/output_coordinates.py`）：

- `_live_idf_vertex_drift_issues`（**定义 :781**，抛出点 :795/:802/:809/**:810**）—— 比 **live IDF** vs snapshot；文案带 `"live IDF {name} ..."` 前缀；仅当 `idf is not None`（step 7，:694）触发。
- `_vertex_drift_issues`（**定义 :816**，抛出点 :824/:830/**:837**）—— 比 **ConfigState** vs snapshot；文案 **`"{name} vertices differ from the pre-E4 snapshot"`**（**无 "live IDF" 前缀**）；step 6（:682，`include_vertex_drift=True`）触发。

日志③报错措辞（如 :213 `'Z01_W1' vertices differ from the pre-E4 snapshot`）**无 "live IDF" 前缀** ⇒ 命中的是 **`_vertex_drift_issues:837`（ConfigState vs snapshot）**。佐证：`validate.py:24` 调 `validate_output_coordinate_contract(state.config_state, contract, context)` **不传 `idf`**（默认 None）⇒ step 7 整段跳过，只跑 step 6。

⇒ **drift 门比的是 ②snapshot vs ③下游 ConfigState，根本不读①surface_specs。** 这一点决定了下面的责任判定。

### 3.2 ①②离线对账 → Q2 分界（决定性，零成本）

`/tmp/f12_recon.py` 把 ①surface_specs 的 NL 文本逐面解析顶点，与 ②snapshot.records 按 name 配对、逐顶点比较（量化 2dp）：

```
① surface_specs parsed faces : 100
② snapshot records total     : 115
①∩② matched                  : 100
  identical (①==②)           : 100      ← 全部逐顶点相同
  DIFFERENT (①!=②)           : 0
only in ② : 15 → 全是 *_Win1 窗（窗在 fenestration_specs，不在 surface_specs，正常）
```

**①② 100/100 逐顶点一致**（脚本可独立重跑：`python3 /tmp/f12_recon.py`）。同源性已由代码坐实：② 由 `build_output_coordinate_snapshot(bg)`（`src/agent/output_coordinates.py:697-718`，直接取 `bg.surfaces.verts` round 2dp），① 由 `serialize_geometry(bg)`（`src/agent/geometry/specs.py:269-307`）——**同源 `bg`**，故一致是必然。

⇒ **Q2：分界不在 ①→②。drift 门的 44 条 = ②(内核) vs ③(下游 ConfigState) 不一致 ⇒ 责任在 ③下游 surface 节点重建几何，不在本项目侧 5_intakeoutput 装配/序列化。**

### 3.3 ③下游 surface 节点 = 纯 LLM 驱动，prompt 命其重写墙几何 → Q6

`src/agent/nodes/surface.py`：
- `surface_agent`（:93-130）= `build_react_agent(llm=create_llm(node_name="surface"), ...)` —— **react agent，LLM（DeepSeek）逐个调 `create_surface` 建面**，不是代码确定性。日志③:48-60 连续 `Component 'Surface':'Z01_W1' created successfully` 即此。
- `SURFACE_SYSTEM_PROMPT`（:10-90）**第 29-31 行明令**：
  > "For every wall vertex you write: bottom z = z_floor of that zone; top z = z_floor + ceiling_height of that zone. Do NOT use a default 3 m floor height."

即 **prompt 指示 LLM 丢弃 surface_specs 里已写死的墙顶点、改用 zone_specs 的 z_floor/ceiling_height 自己重算 z**（x/y 则需 LLM 从 surface_specs 或 footprint 自行推断，prompt 未钉死来源）。

⇒ **Q6：这违反不变量#1「代码做所有几何（建模+切配）+ 装配」中的"建模"边**——墙顶点生成被交给 LLM。注意：即便 zone_specs 的 `z_floor=0.00, ceiling_height=3.00`（`zone_specs` 实测值）与 surface_specs 的墙 z（0.00/3.00）同源一致、z 重算本不该错，prompt 仍让 LLM "重新写整个顶点"，于是 x/y 与 CCW 顺序也由 LLM 推断 ⇒ 偏离内核几何。

### 3.4 Q3 不对称（机械证明）

`/tmp/f12_walls.py` 从 ① 提取全部 64 墙并标是否在日志③的 44 名单内：

| 类别 | 数量 | 漂移情况 |
|---|---|---|
| exterior 墙 | **24** | **24/24 = 100% 漂移** |
| interior(adjacent) 墙 | 40（=20 对互逆配对） | **20/20 对"每对一个漂移、一个不漂移"** |
| 合计漂移 | 44 | = 24 + 20 ✅ |

`/tmp/f12_pairs.py` 机械证实配对规律：
```
interior(adjacent) walls : 40 ; distinct pairs : 20
reciprocal (B.adj==A)    : 20/20      ← 20 对全部互逆
pair SPLIT (恰一漂移)    : 20/20      ← 20 对全部分裂
both-drift / neither     : 0 / 0
```

**为什么 Floor/Ceiling/Window 不漂移**（零成本代码+数据证据）：
- **Floor/Ceiling**（①实测）：水平面，z 单一值（Floor z=0.00、Ceiling z=3.00），x/y = zone footprint 矩形角点（zone_specs 直接给 `x[..], y[..]`）。即使 LLM 重算，几何高度确定、偏离概率极低。
- **Window**：`fenestration_specs` 给**裸顶点**（如 `Z01_W3_Win1: ... vertices: (1.00,7.65,2.60)-(3.40,7.65,2.60)-...`），且 `fenestration.py` 的 prompt（:10-46）命 **"transcribe verbatim / Create EXACTLY the windows listed"**——**照抄不重算**。
- **墙**：**唯一被 surface.py prompt 制度性地命"重新推导几何"的面类型**（垂直面、z 跨两值、x/y 非 footprint）。⇒ 只有墙错。

**`exterior 100% + 配对一对一` 的机制线索**（推断，需③定论）：exterior 墙无 adjacent 参考面，LLM 必须完全独立推导 x/y+顺序 ⇒ 全军覆没；interzone 配对中 LLM 似乎对"一方"照抄对、对"另一方"重推错。但**具体是顺序还是坐标偏移，必须看③**（§8）。

---

## 4. 六问逐条回答

### Q1 ⭐ 漂移长什么样？
- **已证**：①=②（内核与冻结值逐顶点相同）；drift 出在 ②vs③。
- **零成本可排除**：①②数量全是 4 顶点（`/tmp/f12_walls.py`：drift 墙 `n=4` for all 44）；精度差异被 snapshot 的 2dp 量化抹平（`output_coordinates.py:806` 与 `:833` 都 `round(c,2)`）。⇒ **不是数量、不是精度**。
- **剩余两种、无法离线区分**：顶点**顺序**（CCW 方向/起点不同，drift 门 `:835` 是顺序敏感的严格 `!=`）或**系统性坐标偏移**（x/y 抄错/平移）。规律性极强（exterior 全中、配对全分裂）更像**系统性偏差**而非随机值错，但"顺序 vs 平移"需③。
- **三方并排**：内核=②（一致，见 §3.2 脚本输出）；③下游建出来的精确顶点**无落盘**（见 §8），故本调查无法给出③的并排数字——这是 Q1 唯一未闭合处，已给最小烧钱探针（§8）。

### Q2 ⭐ 分界在哪一步？
**①②一致、下游重建才变**（§3.2）。责任方 = 下游③ surface 节点，不是本项目侧装配。

### Q3 ⭐ 为什么只有墙？
见 §3.4：**24 exterior 100% 漂移 + 20 配对全分裂**（机械证明）；Floor/Ceiling 几何最简、Window 被命照抄、唯独墙被命"重推导几何"。

### Q4 定性 + 修法选项（⛔ 未动手）
见 §7。

### Q5 同族？
与 **F-11 同族**（下游 LLM 几何行为偏离内核），形状 F-11=missing / F-12=differ；与 F-5/F-7/F-10（本侧接口拼写/签名错位）**不同族**。F-12 新形状 = prompt **制度性**地把几何推导交给 LLM（比 F-11 偶发漏建更系统）。详见 §6。

### Q6 违反不变量#1 哪条边？
**"代码做所有几何（建模+切配）+ 装配"的"建模"边**——`surface.py:29-31` 把墙顶点生成交给 LLM。详见 §3.3 / §9。

---

## 5. 事实复核（调查单 §2「已验证事实」独立核对）

| 调查单主张 | 复核 | 证据 |
|---|---|---|
| 44 条全墙 `_W*` | ✅ | 日志③:213-256 计 44，全 `_W*` |
| Floor/Ceiling/Fenestration 零漂移 | ✅ | `/tmp/f12_walls.py`：drift 集 = 24 ext + 20 int，无 Floor/Ceiling；窗在 fenestration_specs、44 名单无 `*_Win*` |
| 14 区全中（Z01-Z14） | ✅ | 44 名单覆盖 Z01-Z14 |
| 仅 `VERTEX_FRAME_DRIFT` 一种 | ✅ | `grep VERTEX_FRAME_DRIFT` 无其它 code |
| 措辞 `vertices differ from`（非 missing） | ✅ | 命中 `_vertex_drift_issues:837`，非 `:824` missing、非 `:830` host-changed |
| 门在正确位置（几何建完后） | ✅ | `cross_ref.py:56-60`（complete 默认 include_vertex_drift=True）+ `validate.py`；日志③:212 validate interrupt |
| 4 轮熔断中止 | ✅ | 日志③结尾 `InterruptLoopBreakerError: ... 4 consecutive time(s)`，未跑 simulate/EP |

---

## 6. Q5 同族判断详述

| 缺陷 | 形状 | 侧 | 与 F-12 关系 |
|---|---|---|---|
| F-5 | 窗源消费侧字段名错（契约 `x_range_m` vs 代码 `x_range`），夹具照抄错拼写 | 本侧 src/ 接口拼写 | 不同族 |
| F-7 | 残留产物/locator 消费侧错位 | 本侧接口 | 不同族 |
| F-10 | `check_mep()` 签名漂移（调用方加 `run_profile`、被调方没有） | 本侧签名错位 | 不同族 |
| F-11 | 下游 face 在 snapshot 有、ConfigState **missing**（下游 LLM 漏建面） | 下游 LLM 行为 | **最同族** |
| **F-12** | 下游 face 在、host 对、**vertices differ**（下游 LLM 重推导顶点偏） | 下游 LLM 行为（根因=本侧 prompt 把几何交 LLM） | — |

F-12 与 F-11 都是"下游 LLM 节点对几何的处理偏离内核几何"，根因同源（几何生成交给了 LLM）。区别：F-11=漏建（face 缺失），F-12=建了但顶点错（face 在、顶点不符）。**F-12 比 F-11 更能暴露根因**：F-11 可能被当成"LLM 偶发失误"，F-12 的 `exterior 100% + 配对全分裂` 证明是 **prompt 制度性地命 LLM 重推导**（`surface.py:29-31`）——是不变量#1 被设计违反，不是偶发。

> **「墙3」指代不明**：调查单 §5 Q5 列出的"墙3"未在 CLAUDE.md/plan/decision_log 中检索到既定定义；本次 run 目录名为 `run_2026-08-06_wall3_a_retest`（含"wall3"）。若"墙3"即指该 wall3 retest，则其就是本单本体；若指某个既有"墙3"缺陷，需派工方指明后再做精确比对。**此为提法待澄清项，不阻断本调查结论。**

---

## 7. Q4 定性 + 修法选项（⛔ 未动手）

**定性**：F-12 不是"门坏了"——门在正确位置（几何建完后的 cross_ref_complete/validate）正确抓到了不变量#1 被违反的真实后果。根因是 **surface 节点把墙几何建模交给了 LLM**，门于是如实报"下游建出来的墙 ≠ 内核冻结的墙"。

**修法选项**（仅调查，⛔ 不动）：

- **A（prompt 侧 / 协作者）**：改 `SURFACE_SYSTEM_PROMPT`，命 LLM **照抄** surface_specs 已写死的顶点（像 fenestration 那样 transcribe verbatim），禁止用 zone_specs 重算。
  - 后果：消除"重推导"这个根因；但仍是 LLM 抄坐标，顺序/精度风险残留（靠 drift 门兜）。
  - 代价：小。归属 = §3 out-of-scope①（下游 subagent prompt 演进 = 协作者），但 `surface.py` 在本地 src/，需与协作者协调权属。
- **B（本侧架构 / 重）**：把 surface 节点由 LLM react agent 改为**代码确定性建面**（直接从 IntakeOutput 的结构化几何建 BuildingSurface:Detailed，不经过 LLM），与 2_modelling 内核同精神。
  - 后果：从根上满足不变量#1"代码做几何"，顺序/精度问题消失；与"下游 9 subagent"既有分工（§3 out-of-scope①）冲突最大，需架构决策。
  - 代价：大；且 surface 节点是否仍归"下游 subagent"需拍板。
- **C（什么都不改）**：维持现状。
  - 后果：**任何走下游的 sm21/sm24 类 case 必在 validate 熔断**（44 墙 × 4 轮），永远到不了 simulate/EP。等于端到端链路在下游 surface 段硬死。不可接受作长期态。

**推荐方向（仅作调查建议，不构成施工）**：A 是最小代价消除根因；若要彻底满足不变量#1 则 B。两者都需先与协作者确认 surface 节点 prompt/架构的权属（§9）。

---

## 8. Q1 闭合所需的最小烧钱探针（交派工方拍板）

**为何本调查没烧钱**：调查单 §1/§3 反复要求"优先离线、烧钱前自问非跑不可吗"。零成本已决定性回答 Q2（责任方=③）与 Q6（违反不变量#1"建模"边）；Q1 的"顺序 vs 平移"精确区分不改变责任方与修法方向（A/B/C 三选项均不依赖该区分）。故把烧钱决策交回派工方。

**③精确顶点为何零成本拿不到**（已穷尽）：
1. issue 的 `detail={"snapshot":..., "actual":...}`（`output_coordinates.py:838`）只在内存；`cross_ref.py:28` 与 `validate.py:23` 只格式化 `issue.message`，**不打印 detail**。
2. `TraceCollector` 只 `export()` 到内存（`src/agent/trace.py:56,67`），`record_phase_trace` 不落盘；`run_full_pipeline.py` 无 trace 写盘代码 ⇒ LLM 的 `create_surface` 实参（=③）未持久化。
3. 日志③熔断于 validate（`InterruptLoopBreakerError`），**未跑 simulate/EP，无 IDF 落盘**；`_run/` 仅 5 个元数据 JSON，无 ConfigState 序列化。

**最小探针（任选其一，均需派工方授权 + 计 DeepSeek 成本）**：
- **P1（最小）**：跑下游到 surface+fenestration 完成（不必跑完 hvac/people/lights/validate 的 4 轮熔断），在 drift 门处 dump `config.surfaces` 的墙顶点，与 ② 并排。≈ surface+fenestration 两段 LLM 成本（< 整链 10 分钟）。
- **P2**：临时在 `_vertex_drift_issues` 把 issue detail 写一份 JSON 到 run 目录（**属改生产码，违本调查边界，须另立施工单**）后重跑。
- 目的都只是把 Q1 从"顺序或平移"缩到其一；**不改变 §7 任何修法选项**。

---

## 9. 责任范围张力（Q6 衍生，供拍板）

`src/agent/nodes/surface.py` **物理上在本地 src/**，但其 `SURFACE_SYSTEM_PROMPT` 属 CLAUDE.md §3 out-of-scope①（"下游 9 subagent 的 prompt 演进 = 协作者维护权"）。⇒ F-12 根因修法（选项 A 改 prompt / 选项 B 改架构）**权属有张力**：改的是本地文件，改的内容归"下游 prompt"。这正是 Q6"修法落本项目侧还是 prompt 侧"的要点——**需派工方/协作者裁定 surface 节点的几何建模职责究竟归谁**，再决定 A 还是 B、由谁施工。

---

## 10. 调查单提法校正（记功不记过）

框架完全成立（§5 全部复核通过），以下为不影响结论的细微提法偏差，如实登记：

1. **§3「surface_specs（15865 字符的 IDF 文本）」** → 实际是 **NL markdown 描述**（开头 "Surfaces (vertices CCW from outside, absolute world coordinates in meters)..."，每面 `- 名称 (类型,构造,邻接): (x,y,z)-(x,y,z)-...`），**不是 IDF 文本**。字符数 15865 正确。
2. **§3「`_vertex_drift_issues`（output_coordinates.py:794）」** → 函数**定义在 :816**；:794 是另一函数 `_live_idf_vertex_drift_issues` 内的抛出点。且 F-12 实际命中 `_vertex_drift_issues:837`（ConfigState 比较），**不是** live-IDF 比较（见 §3.1）。
3. **§2「措辞 vertices differ from（面存在、顶点对不上），不是 missing」** → 正确；补充：drift 门该函数有**三个**出口（:824 missing / :830 host-changed / :837 vertices-differ），日志只命中第三个，且 host 也未变（即面都在、宿主都对、纯顶点不符）。

---

## 11. 自检与可重跑命令索引

所有结论均可独立重跑（只读，零生产码改动）：

```bash
# §0 自检
git log --oneline -1                              # 756e821
git status --short                                # 4 case_tests 目录 + 本单

# §3.2 ①②对账（Q2）
python3 /tmp/f12_recon.py                         # 100/100 identical

# §3.4 不对称（Q3）
python3 /tmp/f12_walls.py                         # 24 ext 全漂移；drift=24ext+20int
python3 /tmp/f12_pairs.py                         # 20/20 reciprocal, 20/20 split

# 日志③事实
grep -c VERTEX_FRAME_DRIFT AI_agent/logs/experiments/2026-08-06_f12_wall_vertex_drift/downstream_run.log  # 176 = 44×4
```

代码定位（`src/`）：
- drift 门：`validator/output_coordinates.py:816-840`（`_vertex_drift_issues`）/ `:781-813`（live-IDF）/ `:580-702`（总入口）
- 触发链：`nodes/validate.py:9-27`（不传 idf）/ `nodes/cross_ref.py:56-60`
- 根因：`nodes/surface.py:93-130`（LLM react agent）+ `:29-31`（命 LLM 重算墙 z）
- 对照：`nodes/fenestration.py:10-46`（命照抄）/ `output_coordinates.py:697-718`（snapshot 来自 bg）
