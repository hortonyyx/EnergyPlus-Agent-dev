# 执行日志 · 立面判卷绑定生成（GLM 施工，2026-08-22）

派工单：`AI_agent/logs/reviews/request/2026-08-22_elevation_score_bindings_dispatch.md`
施工席位：GLM（glm-5.3）。最终状态：**已完成可交付部分 + ⛔ S1 升级上报（含新发现的 Va 结构阻塞）**。

---

## 0. 一页结论

- **§二 八条前提全部独立复核成立**（逐条见 §1，附行号与实测输出）。无 S2 触发。
- **S1 比派工单写的更严重**：不只是"审计字段选哪个"。Va 在
  `facade_applicability.py:460-465`（派工单未提及的一道校验，P3 之外）**逐 opening 宿主层**比对
  `binding.source_footprint_fingerprint == floor.source_footprint_fingerprint` 与
  `binding.along_origin == 该层该族 extent 端点`。sm25 的 F1/F2 指纹不同（`36fb…` vs `fbfc…`）、
  East 的两层期望 along_origin 分别为 `-0.0` 与 `-3.55e-15` ⇒ **单条立面绑定在结构上不可能
  同时满足两层 ⇒ sm25 六图判分在 S1 拍板前不可达（锁 1 的 sm25 段被阻塞）**。
  四个选项与后果（含本发现后的重新评估）见 §3，**等用户拍板**。
- 已交付：生成器立面分支（不特化 sm25：**sm24 与手工参照 5/5 逐字段一致**）、锁 2（Va sign
  反转拒收 + judge 端到端 rejected）、锁 3（镜像可见性门，**真实夹具好绿/坏红都实测响过**）、
  锁 4（neuter 摘接线实测）、锁 5（全量，见 §7）。10 个永久锁测试
  `tests/test_elevation_score_bindings.py` 全绿。
- 未动：`facade_convention`、`elevation_score.py` 投影公式、识图产物、gt（§八 全部遵守）。

---

## 1. §二 八条前提的独立复核（全部成立）

| # | 结论 | 证据（实测） |
|---|---|---|
| P1 | ✅ 成立 | `src/agent/judge/elevation_score.py:102-103`：`a = binding.along_origin + binding.sign * lo`、`b = … + sign * hi`（派工单写 103-105，实际 102-108，公式逐字一致） |
| P2 | ✅ 成立 | `facade_convention.py` docstring 明写「The judge-owned score-bindings module is a permitted CONSUMER of this module」；`FACADE_WORLD_AXIS`/`FACADE_BASE_SIGN` 只在这一处定义（docstring 记载此前四处手抄、真出过一次镜像 bug） |
| P3 | ✅ 成立 | `facade_applicability.py:349-353`：`expected_sign = facade_convention.resolve_sign(...)`，`binding.sign != expected_sign or frame_hash 不符 → _fail("va_projection_frame_invalid")`。锁 2 测试实测拒收（§4） |
| P4 | ✅ 成立 | `window_sources.py:1211`：`origin = lo if sign == 1 else hi`；(lo,hi) 取自 1203 行该族段 `world_along_interval` 并集（派工单写 1209，实际 1211，机制一致） |
| P5 | ✅ 成立 | §六 命令实测：gt 有 4 个立面视图（East/North/South/West，各 `floor_ids=(F1,F2)`、`direction_semantics="building_axis"`、`projection_surface_key="ps_<id>"` 与段 `projection_surface_keys` 对得上）；段字段齐全（`facade_family/outward_normal/world_along_interval/source_footprint_fingerprint/projection_surface_keys` 全在） |
| P6 | ✅ 成立 | 实测 manifest：4 条 elevation 均 `direction_semantics="building_axis"` 且 `building_view_direction` 已填；gt `north_axis_deg=None`、`coordinate_frame="building_axis_world_m"`；`score_schema.py:169-180` 校验器强制 `manifest_building_axis ⇒ orientation/adapter 必须双 None`（行号精确匹配） |
| P7 | ✅ 成立 | `score_inputs.py:137-179`（`validate_score_view_bindings_against_gt`）只校验层号存在、gt_source_view_ids 可达且 kind/floor_ids/facade_family 匹配、源引用可达——**不比对指纹**。⚠️ 但注意 P7 字面为真的同时，**Va 侧 460 行有另一道逐层指纹相等校验**（见 §2）——P7 只描述了 judge 入口加载层，不是判卷全链 |
| P8 | ✅ 成立 | `python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py` 退出码 0：sm25+sm24 两栋楼 8/8 立面 predicted==observed 且与 `facade_convention` 声明一致（East (y,+1) / North (x,-1) / South (x,+1) / West (y,-1)）⇒ 填 `mirrored=False`/`local_x_positive="image_left_to_right"` 是**有据选择**，已在生成器代码注释里写明依据 |

S1 事实核实（§六+补测）：F1 全层指纹 `36fb25250aad…`、F2 全层 `fbfc5e046f79…`；F2 段
p1.x=14.999999999999996、p2.x=-3.552713678800501e-15（与 F1 差 3.55e-15 m）；层内一致、跨层不同；
每族两层 world_along_interval 数值上仅差 `-0.0` vs `-3.55e-15`（East）或数值相等（North/South/West，
`-0.0==0.0`）。派工单描述与仓库现实一致。

---

## 2. ⛔ 上报升级：S1 是判卷链的结构阻塞（新事实，派工单未覆盖）

锁 1 sm25 段验证时实测撞上（完整 traceback 见 §6 A 组命令输出）：

```
src/agent/correction/facade_applicability.py:461 in derive_opening_claim_applicability
    if binding.source_footprint_fingerprint != floor.source_footprint_fingerprint:
        _fail("va_projection_frame_invalid", input_id=source, floor_id=opening.floor_id)
```

随后 462-465 行还有第二半：
```python
extent = (min/max …该 floor 该族段…)          # 逐层计算
expected_origin = extent[0] if binding.sign == 1 else extent[1]
if binding.along_origin != expected_origin:   # 严格 ==，无容差
    _fail("va_projection_frame_invalid", …)
```

这条链路是：`gt_to_va_visibility(gt)` 把 gt 转成逐层 `FloorVisibilityLedgerV1`（每层带自己的指纹）→
`derive_reference_ledger` → `derive_opening_claim_applicability` 内对**每个 gt opening 的宿主层**执行上
述相等比较。sm25 立面视图覆盖 F1+F2 ⇒ 同一条绑定对 F1 的 opening 要求指纹=`36fb…`、对 F2 的 opening
要求=`fbfc…`，**无单值可满足**；East 立面还有第二重：两层期望 `along_origin` 为 `-0.0` 与
`-3.55e-15`（不同浮点值），同样无单值可满足。

⇒ **"多层立面 + 层间浮点残量"不仅让指纹字段难填，而是让当前 Va 的 per-floor 严格相等校验在结构上
无法消费任何立面绑定**。这不是生成器能解决的——任何 17 字段取值都过不了这道门。
（对照：校正环的同类推导 `window_sources.py:1204-1207` 在这种情况下显式 raise
`direction_binding_ring_incompatible`，fail closed；Va 判卷侧同样 fail closed，只是错误以
`FacadeApplicabilityInvariantError` 形态进入 `score_service` 后被记为 scorer internal failure →
`not_applicable`，比 rejected 更难看见。）

**因此锁 1 的「sm25 判分 c2_scored」在 S1 拍板前不可能达成**。我按纪律没有绕过去（也没有改 Va、
没有改 gt、没有放水判卷语义）。sm25 的 `judge_score_bindings.json` 已回滚到 HEAD（平面-only、判分
`rejected` 的现状），不留会让判卷变成 internal-failure 的半成品 sidecar。

---

## 3. ⛔ S1 可选处置与各自后果（不拍板，报回来）

> 白话版（供呈用户）：sm25 两层楼的外轮廓在图纸上完全一样，但计算机里两层数字有小数点后 15 位的
> 噪声（0.0000000000000035 米），于是两层的"指纹"（一串校验码）完全不同。立面图是一张画两层的，
> 绑定单上却只有一个指纹格子。更要紧的是：判卷程序还要求这张绑定单的指纹和"每一层"的指纹都严格
> 相同、沿墙起点和每一层的起点都严格相同——所以这不是"格子填哪个"的问题，是"判定程序把浮点噪声
> 当成了两层真不一样"。四个选项：

| 选项 | 做法 | 后果 / 代价 |
|---|---|---|
| a) 量化后再哈希 | 指纹与 along 比较都先量化（如 1e-6 m 网格）再比 | **阈值是一个新的领域参数**，需要用户签字选值（参照 memory：silent-default-threshold——"量化到 1e-6"等价于把界限设成 1e-6，没人签过字）。改动面：指纹生成处（gt 生成器或判卷侧重算）+ Va 460/464 的两个严格 `==`。gt 文件可不重签（判卷两侧同函数重算即可），但 gt 里的原字段与判卷用的规范化指纹从此是两个口径 |
| b) 允许每层一个 | schema 把 `source_footprint_fingerprint`/`along_origin` 改 per-floor 结构 | 最"诚实"（如实表达两层各自的原值），但动 judge schema + Va schema + 全部消费方，改动面最大；且**没有解决** Va 比较的浮点严格性——将来 gt 生成器任何残量还会在别处爆 |
| c) 判卷侧自算规范化指纹 | 判卷链（`gt_to_va_visibility` 与绑定生成器）都从 footprint 顶点**重算**一个确定性规范化指纹（例如排序顶点+round(x,9)+哈希），gt 文件不动 | 仍是"选一个量化精度"（同 a 的阈值问题），但范围收在判卷侧、gt 不动；与 a 的区别只是改哪一侧。Va 的 along 比较（464 行）仍需同步给容差或统一改用"跨层并集 extent"（我的生成器已经用跨层并集，可作参照口径） |
| d) 判定 gt 生成器缺陷、重签 gt | 修 gt 生成器使多层同 footprint 的指纹逐位一致（或先量化再签），重新产出 sm25 gt | **动 gt = 动答案文件**（gt 铁律敏感，须用户拍板 + 重跑该 gt 相关全部判分记录）；治根——缺陷登记（plan.md「跨层 footprint 用浮点逐位相等比较」）就是这族；sm24 单层不受影响 |
| （过渡，已实现、未拍板） | 生成器 `--elevation-fingerprint-union-pending-s1`：指纹 = 各层指纹有序集合的 canonical sha256 | **零参数、不选层、可从 gt 复算**，但它只是绑定文件自身的审计值——**过不了 Va 460 行**（两个层指纹谁都不等于集合哈希），所以它只让"绑定文件能产出"，不能让 sm25 判分通过。留着作为拍板前的显式合法出口，防多层 case 静默走岔 |

**推荐（供参考，不是拍板）**：d（治根、且缺陷本就登记在案）或 c+Va 比较统一改跨层并集口径（不动 gt、
不动 schema）。**等用户拍板。**

---

## 4. 交付物与五把锁的实测

### 交付物 1：生成器立面分支（`scripts/tool_scripts/build_score_view_bindings.py`）

- `world_axis`/`sign` **只来自 `facade_convention` 函数调用**（§三硬约束，未手抄表）。
- `along_origin = (lo if sign==1 else hi) + 0.0`，(lo,hi)=该族全部覆盖层段的 `world_along_interval`
  并集（与校正侧同取法；`+0.0` 仅把 `-0.0` 记号规范化为 `0.0`，不改数值）。East 实际产出
  `-3.552713678800501e-15`——这是 gt F2 段 lo 的**原值**，如实保留。
- `mirrored=False`/`local_x_positive="image_left_to_right"`：代码注释写明 P8 依据
  （verify_mirror_convention.py 8/8、两栋楼、exit 0；normalize_mirror_flag 拒绝猜 unknown）。
- S1 fail closed：多层指纹不一致 ⇒ 默认 `SystemExit`（错误信息含各层指纹全文 + S1 提示）；
  `--elevation-fingerprint-union-pending-s1` 为显式过渡出口（§3 表末行）。
- `direction_semantics != "building_axis"` 的条目**响亮报错**（需要 reviewed direction sidecar，
  本工具不产）——不为 sm25 特化、对未来 true_azimuth 案不猜。

### 锁 1（正向）

- **sm24 段 ✅（实测）**：CLI
  `python scripts/tool_scripts/run_stage.py artifacts sm24_anchor run_2026-08-02_sonnet_full_unsup 0_reading`
  → `kind: c2_scored`，`channel: elevation applicable`（xy+z 双组件），`window_elevation_geometry
  44.0/44.0 pass`（walls_complete/no_extra_walls 的 fail 是该 reading 自身历史成绩，与本轮无关）。
  且生成器对该 run 重产 5 条绑定与**手工产的已知好参照逐字段一致（5/5 IDENTICAL，含 4 条立面）**——
  推导正确性有独立参照背书。
- **sm25 段 ⛔ 被 S1 阻塞**（§2）。生成器侧已就绪：默认 fail closed（实测 exit=1、错误含两层指纹）；
  旗标路径实测产出 6 条（2 plan + 4 elevation），East 绑定字段实测值见 §6 B 组。

### 锁 2（约定锁，实测两次拒收）

- Va 侧（P3，真实入口 `derive_opening_claim_applicability`）：构造 sign 反转（`_frame_hash` 重算保持
  自洽）的绑定 → `FacadeApplicabilityInvariantError: va_projection_frame_invalid`；正确 sign 对照通过。
  = `tests/test_elevation_score_bindings.py::test_va_rejects_flipped_sign_through_real_entry`。
- judge 侧端到端：篡改 `judge_score_bindings.json` 的 East sign（并重算 `content_sha256` 以直达 sign
  校验）→ 判分 `kind=rejected, error_code=score_direction_unresolved`。
  = `test_judge_side_rejects_tampered_sign_end_to_end`。
  （不重算 content_sha256 的裸篡改也会 rejected：`score_view_binding_invalid`——整体哈希门，附验。）

### 锁 3（镜像可见性门，⭐新判据，真实夹具上响过）

- 实现：`reading_typed_score.elevation_mirror_flip_witnesses` + `assemble_reading_score` 内并入
  structural criterion `reading.elevation_mirror_visible`（与 `reading.plan_frame_declared` 先例同构）；
  `score_service.strict_payload_violation_reason` 扩 strict 档 fail-closed 理由
  `elevation_mirror_disagreement`。
- 机制：对每条立面绑定，取该 input 全部立面窗观测的 world 中心到「gt 同族同层窗中心」的最近距之和
  （as_is）；再把观测关于 **gt 该族段并集中点 C** 整体反射算同一 cost（flipped）。若
  `flipped <= as_is - opening_match_center_tol_m`（0.40 m，**既有判卷容差，不引入新阈值**）⇒ FAIL
  criterion。反射中心只取自 gt 段 extents，独立于产物与绑定声明的 along_origin；窗列对称时两侧
  cost 相等 ⇒ 门静默（对称不携带方向证据，正确不误伤）。
- **好夹具全绿（真实 sm24 08-02 run 产物+真 gt，真实判分入口）**：无 mirror criterion，strict=None。
- **坏夹具报红（同真实产物，East 3 窗 local_x 整体反射 x→20−x）**：
  `reading.elevation_mirror_visible / fail / {East_view: 3}` + strict
  `elevation_mirror_disagreement`。实测命令与输出见 §6 C 组。
- 收录判据（同 reading_process_metrics：好的全绿+至少一份坏的红）**满足**。

### 锁 4（neuter，摘接线不是摘机制，两处实测）

- 镜像门：monkeypatch `reading_typed_score.elevation_mirror_flip_witnesses`（**判卷链实际调用的
  名字**）为常空 → 同一坏夹具不再出现 mirror criterion（检测函数本体未动）。实测输出见 §6 D 组；
  永久锁 `test_mirror_gate_neuter_removes_the_wiring`。
- Va sign 门：patch `facade_applicability._validate_bindings` 为透传 → 反转 sign 的绑定不再被拒。
  = `test_va_neuter_removes_the_sign_wiring`。

### 锁 5（全量）

- 见 §7（跑测命令、结果、与基线 2996 passed / 13 xfailed 的对账）。

### 永久锁清单（`tests/test_elevation_score_bindings.py`，10 条全绿）

正向（sm24）/镜像绿/镜像红/镜像 neuter/Va 拒收/Va neuter/judge 端到端拒收/生成器复刻手工参照
（含 sign==facade_convention 断言）/生成器 S1 fail closed/生成器旗标产 6 条+过渡指纹可复算断言。

---

## 5. 遵守的边界（§八）

- 未改 `facade_convention`、未改 `elevation_score.py` 投影公式、未改任何识图产物、未改任何 gt。
- 过程中我跑分产生的 run 产物改动（score_vs_gt/grade.png/renders）与 sm25/sm24 sidecar 覆写已全部
  `git checkout --` 回滚；最终工作树只有：生成器、`reading_typed_score.py`、`score_service.py`、
  新测试文件。
- 不为 sm25 特化的证据：生成器对 sm24（单层）无需任何旗标直接产出且与手工参照一致；sm25 的多层
  分歧走显式 S1 出口而非硬编码。

## 6. 实测命令与输出（摘）

**A · S1 结构阻塞的现场**（sm25 判分，绑定=6 条过渡版）：
```
$ python scripts/tool_scripts/run_stage.py artifacts sm25-L_anchor run_2026-08-22_orchestrator_handson_H2_fullcase 0_reading
…
  File "src/agent/correction/facade_applicability.py", line 461, in derive_opening_claim_applicability
    _fail("va_projection_frame_invalid", input_id=source, floor_id=opening.floor_id)
FacadeApplicabilityInvariantError: va_projection_frame_invalid: {'input_id': 'South_view', 'floor_id': 'F1'}
RuntimeWarning: typed scorer internal failure; emitted not_applicable
```

**B · 生成器两路径**：
```
$ python scripts/tool_scripts/build_score_view_bindings.py --run-dir <sm25run> --gt <sm25gt>            # 默认
East_view: 'East' facade floors ['F1', 'F2'] carry DIFFERENT footprint fingerprints
['36fb25250aad8972d33ca451b8be45165065aac68bbeb60c522eefb0568a9ab6',
 'fbfc5e046f79633f3c183a8609aa3a4c48b2d72cd9f5d9fd9200be9cfb9f7f06']; … NOT yet ratified — refusing
to pick one. (interim escape: --elevation-fingerprint-union-pending-s1)        # exit=1

$ … --elevation-fingerprint-union-pending-s1
{"bindings": ["1f_view","2f_view","East_view","North_view","South_view","West_view"],
 "content_sha256": "c1690d6f9acddec33046d8d65d08eee870d7139f55dbfdc7db24a18a01623974", …}   # exit=0
# East_view: sign=1, world_axis=y, along_origin=-3.552713678800501e-15,
#            mirrored=false, local_x_positive=image_left_to_right, floor_ids=[F1,F2]
```

**C · 锁 3 好绿坏红**（真实 sm24 产物经 `score_typed_attempt` 真实判卷入口）：
```
好（原产物）:  kind: c2_scored   MIRROR CRITERIA: NONE
坏（East 3 窗 x→20−x）: mirrored strokes in East_view: 3
  MIRROR CRITERIA: [('reading.elevation_mirror_visible','fail',{'East_view': 3})]
  strict violation: elevation_mirror_disagreement
```

**D · 锁 4 neuter**：
```
摘接线（patch elevation_mirror_flip_witnesses → ()）后同一坏夹具:
  neutered mirror criteria: NONE   strict violation: None
```

**E · 全部锁测试**：
```
$ python -m pytest tests/test_elevation_score_bindings.py -q -n0
10 passed in 12.92s        # 对 HEAD 手工参照亦然（回滚后复跑）
```

## 7. 锁 5 全量对账

```
$ python -m pytest -q -n auto                      # 第一次（改动后）
1 failed, 3005 passed, 13 xfailed in 656.24s
  FAILED tests/test_affected_tests_map.py::test_every_production_module_is_mapped_or_honestly_allowlisted
```

失败不是判卷回归，而是「无覆盖豁免清单」锁：`build_score_view_bindings.py` 原先没有任何直接测试
（豁免条目：exercised through the real scoring path rather than a CLI test）；本轮
`tests/test_elevation_score_bindings.py` 直接以 subprocess 跑了该 CLI 四次 ⇒ 它从「无覆盖」变
「已覆盖」⇒ 豁免条目失效 ⇒ 锁红（`uncovered == set(allowlist)` 不再成立）。处置：从
`scripts/tool_scripts/affected_tests_rules.yaml` 删除该条目（豁免必须诚实反映现状——锁的行为正确）。

```
$ python -m pytest tests/test_affected_tests_map.py tests/test_elevation_score_bindings.py -q -n0
25 passed            # 修复后两文件合跑
$ python -m pytest -q -n auto                      # 修复后完整全量（最终）
3006 passed, 13 xfailed in 833.73s (0:13:53)
```

对账结论：**3006 passed / 13 xfailed = 基线 2996 + 本轮新增 10 条，零回归、零失败。**

---

## 8. 给复核席位（GPT/codex）的提示

- 本轮源码 diff：`scripts/tool_scripts/build_score_view_bindings.py`（立面分支+S1 出口）、
  `src/agent/judge/reading_typed_score.py`（镜像门+接线）、`src/agent/judge/score_service.py`
  （strict +1 理由）、`tests/test_elevation_score_bindings.py`（新增）。
- 复现最短路径：`python -m pytest tests/test_elevation_score_bindings.py -q -n0`。
- 判卷语义未放水：好产物判分产物与改动前逐字节一致（mirror 门零触发时不新增 criterion）。
