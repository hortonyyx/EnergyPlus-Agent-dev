# B1 投影桥 · 执行档（两轮合并交件）

- **施工**：GLM 家族（2026-09-02 第一轮撞 5h 窗口中断，2026-09-03 第二轮续完）
- **任务书**：[`../request/2026-09-02ad_B1_projection_bridge_core_dispatch.md`](../request/2026-09-02ad_B1_projection_bridge_core_dispatch.md)
- **权威口径**：[`../../proposals/correction_projection_bridge.md`](../../proposals/correction_projection_bridge.md) v7
- **提交清单**（本轮四笔，均在 `wt/09.02aj_b1_bridge`）：
  - `4c2d738` 桥核心 838 行（第一轮）
  - `439259a` 验收 1/2/6 + gate①（第一轮）
  - `895af3a` 主控代交的 WIP 夹具（第一轮中断件，本轮由同一席位续完）
  - `1b06c6a` 生产加载器修正 + 10 锁 · `8380fd9` 接线（executor sink + pipeline 投影）
  - `a47a61e` o22m7 终点锁改写为新契约
- ⚠️ **本单未过审不得收口**（任务书排期裁定）；交件即挂起。

## 〇、停报检查（§七）—— **零触发，逐条对账**

- **A②（改已落库/已签字产物的哈希或基线）**：未发生。证据：本轮源码与测试的全部改动 =
  五个路径（`git diff 895af3a..HEAD --stat -- src tests` 原文：
  `decision_executor.py +12` · `projection_bridge.py +167/−81 区` · `pipeline.py +231` ·
  `test_b1_projection_bridge_production_loader.py +373（新）` · `test_o22m7_evidence_wiring.py +170`，
  外加本档 md）；gt / as_measured / 判分侧**零触碰**。
  既有链上消费者契约未动：`run_decision_loop` 返回类型不变（新参数默认 None）、
  `run_correction_evidence_chain` 返回类型不变（新参数默认 None）、`evidence_chain` 默认仍 False
  （`test_evidence_chain_switch_defaults_off` 原样绿）。**全量 3702 绿零红**本身即基线哈希类锁
  （含 tarch reproducibility / gt_promotion 等逐字节复现锁）未被扰动的机械证据。
- **A①/A③**：未发生（§四禁令逐条见 §三）。
- **B 层记录（记下继续）**：
  1. 任务书 §四之二 引的锁行号 `test_o22m7_evidence_wiring.py:361` 在改写后移动（该测试被重写，
     新契约锁在 415、纪律锁在 470 行）——预期内。
  2. 生产帧读数与 gt 有差（16 vs 15 面 / 316.70 vs 279.26 m² / 16 vs 0 悬端）——见 §六之二是
     **量出来的读数**，未对账（对账属 B5 端到端；本单 §五#6 的对账按任务书钉在**夹具世界**完成）。
  3. 上一轮写的几何式宿主判定 `_resolve_opening_host` 被删除——它在全仓**零调用零测试**
     （grep 实测），且实测在生产数据上 87 个 opening 只解出 11 个（见 §四之二）。删的是死代码，
     接替者是引用式解析（实测 23/23 面唯一归属）。

## 一、命令原文 + 输出原文（权威跑测）

环境自证与 pytest **同一条命令**（任务书 §五#8；`__file__` 承重，`.pth` 只记不停）：

```
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('projection_bridge:', m.__file__); print('pipeline:', p.__file__)" && python -m pytest tests/ -q -n 6 -p no:cacheprovider
projection_bridge: /tmp/b1_bridge_glm/src/agent/correction/projection_bridge.py
pipeline: /tmp/b1_bridge_glm/src/agent/pipeline.py
3702 passed, 13 xfailed, 211 warnings in 484.43s (0:08:04)
```

闭合：上一轮主控权威读数 **3690 passed / 13 xfailed** → 本轮 **3702 = 3690 + 12**
（生产加载器锁 +10；o22m7 −1 旧终点锁 +3 新锁）。

B1 定向：

```
$ python -m pytest tests/test_b1_projection_bridge_acceptance.py tests/test_b1_projection_bridge_fixtures.py tests/test_b1_prime_failopen_defaults.py tests/test_b1_projection_bridge_production_loader.py -q -n 6
41 passed in 3.02s
$ python -m pytest tests/test_o22m7_evidence_wiring.py -q -n 6
29 passed in 4.76s
```

## 二、§四之二：终点锁的改写（甲 · 本轮主缺口）

**接线前实测**（主控核出的缺口，我复认）：`run_correction(evidence_chain=True)` 无条件抛
`EvidenceChainTerminal` —— 桥存在但没接上，sm25 端到端仍走不通。

**接的线**（`8380fd9`）：
1. `run_decision_loop` 新增 `compilation_sink`（默认 None，零行为变化）：outcome 只带哈希、
   桥要墙，sink 在 `outcome()` 闭包**单一收口**处把最终墙编译产物递给消费者，每个出口都过。
2. `run_correction_evidence_chain` 新增 `projection=`（`EvidenceChainProjection`）：
   outcome 落盘后，**仅当 success** 才解引用 bundle 的 opening_claims → 生产加载器 →
   `project_cut_lines` → `projection_envelope.json` 落盘；失败记链路名 `project` 后原样上抛。
3. `run_correction(evidence_chain=True)`：success ⇒ 读回 envelope、**消费侧绑定校验**
   （`source_resolved_sha256 == outcome.final_provisional_sha256`，对不上=投影失败），
   返回 `envelope.geometry`；非 success ⇒ `EvidenceChainTerminal`（新前提，见下来历表）。
   z 必须 caller 声明（`evidence_chain_z_floor_m` / `ceiling_height_m`，缺了响亮 ValueError，
   消息点名 B2 拥有 sourcing）——桥不造 z，接线也不造。

**锁的来历对账（任务书 §四之二 逐条要求）**：

| 旧锁量的那件事 | 现在谁在量 |
|---|---|
| 「桥不存在 ⇒ **任何** outcome 都没有成品可返回」⇒ `pytest.raises(EvidenceChainTerminal)` | **前提的 success 半边已消亡**：`test_switch_on_returns_the_projected_geometry` 量正向契约（返回 geometry、envelope 落盘、`footprint_provenance="derived_from_walls"`、绑定 outcome 最终哈希、route 读数） |
| 「⛔ 不许发明 CorrectedGeometry / 不许回退 pasted-JSON 腿」 | `test_switch_on_without_success_terminates_loudly_no_product`：非 success ⇒ Terminal、盘上无 envelope、booby trap（贴 JSON 腿被碰即炸）原样保留 |
| 「消息携带 as-measured success/exit_reason」 | 同上锁，断言原文逐字携带 |
| （新增）「桥不造 z」 | `test_switch_on_without_declared_z_is_a_loud_value_error` |

⛔ 旧锁**没有删除后重造**——是在原位改写（git 可查：`a47a61e` 是对同一测试的替换），
docstring 里写明 lineage。

## 三、§四禁令对账

- 洞口→窗合成（B4）：未做。生产加载器只把 opening span 变**切割线**（§一四步之①），`windows=[]`。
- 多楼层装配（B2）：未做。z 从 caller 参数进（锁里用 gt 的楼层 meta，测试侧读数）。
- as-drawn 立面腿（B3）：未做。
- outer_skin 实现：未做（`PROJECTION_BASIS_UNIMPLEMENTED` 响亮）。
- 非正交：零动作（`_validated_axis` + `_run_axis` 是上一轮已有的局部化判定，本轮未扩）。
- gate① 加延伸合法性门：未加（4b 双向对账在夹具世界，见 §五）。
- F-153/F-157/F-158、`as_measured.py` 生产逻辑：未动。
- `pip install -e .`：未跑（全程 `python -c "import …; print(m.__file__)"` 自证落本树）。
- `git add -A`：未用（每笔 `git add` 明确路径 + `--numstat` 过目）。
- 分段提交：四笔独立成立。

## 四、§五验收八条

| # | 规则 | 读数（命令原文见 §一） |
|---|---|---|
| 1 | cells 互不重叠且并集=footprint，**零阈值** | `test_1_cells_tile_the_footprint_zero_threshold` F1/F2 绿。布尔谓词 + 逐对交面积精确 0；实测减法噪声 −5.7e-14 被绕开（不设「对浮点加法的容差」） |
| 2 | 相邻房间共面逐顶点相等 | `test_2_rooms_share_inner_walls_vertex_for_vertex` F1/F2 绿（断顶点集，⛔ 不断哈希） |
| 3 | 改厚度边界不动，判据=环带空 | 3a（环带空 ⇒ 增厚 cells 逐顶点不变）/ 3b（一致重画同）/ 3c（环带非空 ⇒ 允许变，负向钉住「这不是缺陷」）全绿；夹具 #3 的输入**未**用于本条 ✅ 方向（任务书明禁） |
| 4 | 无法成环=0 有界面 ⇒ 整层响亮；悬端只登记 | 4a：异常码 `NO_BOUNDED_FACES_AFTER_EXTENSION` 绿；4b：真悬端（远离一切垂直墙带）进 debt + `degraded`、面数交 gt 对账 |
| 4b | 延伸两失效方向由 **双向** gt 对账兜底 | 两形状分开锁：S3 形（幻影接骨）⇒ 红 **①计数** + **③无主面**（`test_4b_ghost_wall_red_where`）；计数相等化攻击（幻影墙 + 杀一条延伸 ⇒ 14=14，① 通过）⇒ 红 **②zone 配不上** + **③无主面**，且**同输入上单向无界版实测 GREEN**（盲区被钉成读数，`test_4b_counts_equalised_attack_red_only_on_2_and_3`）；质心距界=基线分布派生（5×基线最大对距），面积差只作 readout |
| 5 | 判分对桥缺陷有分辨力 | `test_5_dropping_a_room_changes_the_verdict`：桥里丢一个房间 ⇒ 判分必变（monkeypatch 实测） |
| 6 | 对签字 gt 双向逐位对账 F1 14 / F2 15 | `test_6_signed_gt_reconciliation_two_directional`（夹具世界，基准=冻结 `gt.json`，⛔ 非判分侧读数）：F1 14 / F2 15，①计数②一对一③无主面三向全绿，同时面积差非零（readout 与门分离被钉住） |
| 7 | 单视图产物到 V3 过 gate① | gate① 逐项（夹具世界，两视图同形）：`cell_polygon_contract / coverage / nondegenerate / zstack_continuity / zone_count_tripwire` 全 ok=True；`footprint_provenance="derived_from_walls"` 在产物里可读；B3 按构造恒真由此字段可读 |
| 8 | 全量绿（-n 6） | 3702 passed / 13 xfailed / 0 failed（§一原文） |

## 五、§六夹具五件套（每件改前红改后绿）

| # | 夹具 | 锁 | 读数 |
|---|---|---|---|
| 1 | 0.1 mm 余数 | `test_fixture1_remainder_one_unit_both_versions_cut_14`（52401 带缺陷 / 52400 修复两版）+ `test_fixture1_red_before_tolerance_zero_is_a_loud_zero_face_layer`（自证前提：容差为 0 时该夹具本红） | 两版都 14 面 |
| 2 | 2 units 余数 | `test_fixture2_two_unit_remainder_still_red` | 该红的仍红（容差没吃掉真异常） |
| 3 | 厚度报错（120→240） | `test_fixture3_misreported_thickness_goes_red_at_reconciliation` | gt 对账红（⛔ 不拿它验 #3 ✅ 方向） |
| 4 | 漏 opening | `test_fixture4_dropped_opening_two_redundant_channels` | 双通道都红 |
| 5 | 摘一堵墙 | `test_fixture5_removed_wall_red_at_reconciliation_only` | 静默丢房间、悬端可为 0、对账红（W2 的复刻） |
| 混排 | 90/150/300/370 | `test_smix_thicknesses_are_the_mandated_mix` | 同图四厚度 |

## 六、本轮新量的事实（接线前实测，全部可复算）

### 六之一、生产加载器两处修正（`1b06c6a`，先量后改）

1. **90° 转置**：墙编译器 `constant_world_axis` 是**常轴**词汇（"x" ⇒ pos 是 X 坐标、沿线变
   Y），`CutLineV1.axis` 是**走向**词汇（"y" 分支才把 pos 放 X 上；gt facts 同走向词汇）。
   旧加载器直抄常轴名 ⇒ 整层转置，实测（真 2f 生产线段并集包围盒）：
   **旧映射渲染 x 跨 20.03 / y 跨 24.98，正确映射渲染 x 跨 24.98 / y 跨 20.03**，
   对 gt 签字 footprint x∈[0,25] y∈[0,20] —— 取向锁（`x_extent − y_extent > 4`）抓的正是它。
   夹具世界两侧词汇一致，故上一轮 24 锁全绿没照见它。修法 = `_run_axis()` 显式映射 +
   两套词汇在接缝处写死在 docstring。转置不改面数/面积（同构变换），故下面六之二的读数在
   修正前后一致；它错的是**坐标落位**（B2 多层装配必炸处）。
   ⚠️ B 层更正一条：commit `1b06c6a` 的说明里写的包围盒数字 `[0.12,0.12,24.88,19.88]` 是
   **夹具世界**的渲染读数、被我误植为生产帧实测（方向判断对、数字来源错）——本档此处的
   20.03/24.98 vs 24.98/20.03 才是生产帧实测。
2. **宿主解析改引用式**：几何带判据（|中线−面|≤半厚）在真 2f 上 87 个 opening 只解 11 个，
   76 个失败分两类：①墙自覆盖**排除** opening 缺口 ⇒ span 卡在同墙两段之间（2 候选）；
   ②中线是派生 `(a+b)/2` ⇒ 相切边界差 1 ulp（实测 +4.3e-16，0 候选）。引用图
   （墙的 `source_refs` 认领 face）实测 **23/23 面恰好唯一归属** ⇒ 改为引用解析、零容差零几何，
   0 主/2 主响亮（`OPENING_HOST_UNRESOLVED`）。被替换的几何判定全仓零调用零测试，已删。

### 六之二、生产链端到端读数（真 sm25 2f，all-KEEP 决策，z 取 gt）

```
faces=16  completion=degraded  extensions=34  gaps=34  dangling=16  total=316.70 m²  min=5.253  碎片(<1m²)=0
```

- 16 悬端里 **~3 个 ulp 级**（−1.4e-17 / 0.000），**13 个厘米级**（+1.1e-2 ~ +3.3e-2 与
  −1.1e-2 ~ −5.5e-2 两族）⇒ **不是容差问题，是真几何差**（as-drawn 墙集与 gt facts 墙集不同构）。
- **N-3 生产声明**：`resolution_m=0.0`，source 串写明「as-drawn *_m 浮点米、无声明量化」。
  刻意**不用** calibration 里声明的 `m_per_px`（0.0218 m）：它会把厘米级真差异吸掉
  （判据从结果反推 ⛔）。这是判断题，供复核方攻击（见 §八）。
- ⚠️ 与 gt 的差（16 vs 15 面 / 316.70 vs 279.26 m²）**未对账**：夹具世界的对账（§五#6）
  是任务书钉的那次；生产帧对账归 B5。all-KEEP 是我的驱动、不是模型决策——真实模型跑出的
  墙集会不同。

## 七、同作者变异自证（谁写谁不批的缺失半边，我自己先摘）

每次变异：改源码 → `python -c "import …; print(m.__file__)"` + pytest **同条命令** → 记红 → `git checkout --` 还原。

| 变异 | 摘掉的判断 | 红的锁（实测原文） |
|---|---|---|
| M1 | 轴向映射（直抄常轴=回到转置 bug） | **5 红**：`test_axis_mapping_constant_to_run[x-y,y-x]`、`test_axis_mapping_mutant_transposes…`、`test_opening_borrows_the_unique_owner_walls_own_numbers`、`test_production_chain_on_real_sm25_2f_unrotated` |
| M2 | 宿主唯一性（多主取第一个，不响亮） | **2 红**：`test_opening_with_no_owner_wall_is_loud`、`test_opening_with_two_owner_walls_is_loud`。⚠️ 真产物 e2e **不红**（真数据恰好全唯一主）——该判断只有合成响亮锁守 |
| M3 | 「非 success 不出成品」纪律整块删除 | **1 红**：`test_switch_on_without_success_terminates_loudly_no_product`（成功路径锁不红，方向正确） |
| M4 | sink 接线（链不递墙） | **1 红**：`test_switch_on_returns_the_projected_geometry` |
| M5 | §9.1 墙内缺口补线（永不补） | **1 红**：`test_fixture4_dropped_opening_two_redundant_channels`。⚠️ 只此一把锁守 §9.1 |
| M6 | 端点延伸规则（全关） | **23 红**（gt 对账族大面积红：fixture1/3/5、4b 幻影墙、#5 判分分辨力、acceptance#2、生产 e2e） |

结论：接线四个关键判断（M1–M4）各有锁咬住且方向正确；桥核心两条（M5/M6）牙数不对称——
M6 咬得死，M5 只有单锁。

## 八、我自己认为最薄弱的一处 + 请复核方重点打哪里

**最薄弱 = §六之二的「生产链读数未对账」整块。** 我把生产链接通了、修了两处实测缺陷、
envelope 如实 degraded——但 **16 vs 15 面、316.70 vs 279.26 m²、16 vs 0 悬端这三个数
没有任何一个被解释到归因**。可能的成因至少三个互相缠绕：all-KEEP 决策 ≠ 模型决策；
**as-drawn 墙集与 gt facts 墙集本就不同构（实测计数：生产 22 墙/87 opening 候选 vs
gt facts F2 53 墙/30 opening——as-drawn 把更多段并进了多段墙、其 opening 候选里混着
厘米级量化缺口）**；引用式宿主解析把 87 个候选全放进了切割线（gt facts 世界只有 30 个
opening 且规模下限更干净）。
**这是「跑通了」和「对了」之间的整片暗区**，而它恰好是 B5 之前没人再看的部分。

**希望重点打的四处（按优先级）**：
1. **生产读数三差异的归因**——哪怕只做一次双向对账把红点名列出来，也比我现在「如实登记未对账」强。
2. **N-3 生产 resolution=0.0 的选择**——我拒绝 m_per_px 的理由（会吸掉厘米级真差异）本身没被
   反向检验：0.0 也会把 3 个 ulp 级悬端登记成 debt（假阳债务）。两头都是判断，我选了保守侧。
3. **M2/M5 的单锁面**——宿主唯一性与 §9.1 契约各只有合成/单件锁守，真产物端到端 pin
   （face_count==16）恰好测不到这两个判断（M2 实测不红）。若复核方认为承重，补锁便宜。
4. **sink 这个接缝形状**——outcome 只带哈希、墙从闭包收口递出，是本轮我发明的形状；
   有没有更不该绕的约束（比如 success 与 sunk 产物的一致性在类型层不可分）值得被挑战。

## 九、⚠️ 未过审状态重申

本档是交件，⛔ 不是收口声明。跨家族审（非 GLM、非 Claude 主控）待运维恢复后进行；
在此之前 B1 不得宣布完成、不得在其上开 B2。
