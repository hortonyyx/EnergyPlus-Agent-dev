# plan.md 活表 ⇄ 代码 通查对账（2026-09-07 第九程，主控实测）

> **起因**：用户当面顶了一句「一体改还没动吗？跑不了吗？你查一下呢」。
> 主控此前的状态汇报是**读 plan.md 的 `⏭/🔶/⛔` 标记**得出的，⛔ 不是查代码得出的 —— **那句汇报是错的**。
> ⇒ 本档 = 逐条拿代码验一遍的读数，**每条都给命令或文件:行**。

## 0. 一句话

**plan.md 的活表严重滞后于代码。** sol 的「六条阻断」里**只剩 1 条真没做**；
②-1 整个包（活表写着「⛔ 现在不能开工」）**已经完整落地**；两个标着「⛔ 未过审」的提交**早在主线祖先里**。

⭐ **真正的缺口不在实现，在【生产入口没接线】** —— 见 §3。

---

## 1. sol 六条阻断（2026-08-28 架构对抗审给的「施工前最小返工清单」）

| 条 | plan.md 写的 | **实测** | 证据 |
|---|---|---|---|
| ① facts 编译器要**外部获授权指纹锚** | ⛔ 未做 | ⛔ **确实未做** | `verify_as_signed_reproduction`（`gt_revisions.py`）只重算 `content_sha256` 自比，**不读任何外部锚** ⇒ 即 **F-149** |
| ② 定义**投影前**的 `ReferenceFactsV1` | 🔶 方案已成文·施工未做 | ✅ **已落地**（换名） | 落地名 = **`AsMeasured*V1` 家族**（`as_measured.py:468-823`：FaceLine/Wall/Opening/Ring/Footprint/BoundaryEdge/…）。`grep ReferenceFactsV1` 零命中 ⇒ **名字没兑现，东西兑现了** |
| ③ authority root 与 as-received 观测根**分名** | 🔶 方案已成文 | ✅ **已落地** | `as_measured.py:1221 derive_as_measured_request(signed_request, as_received_dxf)` |
| ④ affine 改 **domain/codomain 双端空间合同** | ✅ 2/3 | ✅ **全落地** | 独立模块 `src/agent/judge/affine_space.py`（`domain_space`/`codomain_space` wire fields） |
| ⑤ 新增 edge **`boundary_condition`** | ⛔ 未做（= F-121） | ✅ **已落地** | `as_measured.py:624 AsMeasuredBoundaryEdgeV1` · `answer_compiler.py:125 boundary_condition: Literal[...]` |
| ⑥ **作废半径 = 依赖闭包** | 🔶 口径已定·施工未做 | ✅ **已落地** | `certifier.py:75 dependency_closure()` · `answer_compiler.py:309 dependency_closure_version` / `:382 DEPENDENCY_CLOSURE_VERSION` |

⇒ **六条里只剩 ① 一条真没做，而活表把它们整体当成「②-1 不能开工」的理由。**

---

## 2. 四步活表逐条

| 包 | plan.md 写的 | **实测** | 证据 |
|---|---|---|---|
| **①-2** G1 派生审计件 | ⏳ 返工已交件 `ef41a39` · **⛔ 未过审** | ✅ **早已在主线祖先** | `git merge-base --is-ancestor ef41a39 HEAD` ⇒ 真 |
| **①-5** 语义升格计分 | ⏭ | 🟡 **一半** | `reading_grade.py:246` C5 洞口身份**已计分**；E5 door/window KIND 今天诚实 `null` 并写明原因，**升格归 J-5** |
| **①-6** F-89 立面跨两层整份丢 | ⏸ 挂起（「服务 legacy，② 会换掉」） | ✅ **已修** | ② 确实换掉了：`elevation_grade.py:46` 明写「跨两层整面判、⛔ 禁按楼层过滤」，锁在 `tests/test_elevation_grade.py` |
| **①-7** F-98 浮点末位 | 观察项 | 🟡 该族已处理 | `as_measured.py:84` 明写 F-98 家族的处置 |
| **②-0** F-97 消费对账 | ⏳ 返工已交件 `f2a8ccf` · **⛔ 未过审** | ✅ **早已在主线祖先** | `git merge-base --is-ancestor f2a8ccf HEAD` ⇒ 真；`vector_contract.py` 的 `Disposition`/`classify_vector_json` 在跑 |
| **②-1** AnswerCompiler(profile) | ⏭「② 的第 1 号包」· **⛔⛔ 现在不能开工** | ✅ **完整落地** | `answer_compiler.py:100 OutputProfile{FORM_A_AXIS, FORM_B_EXTERIOR_SKIN}` · `:365 class AnswerCompiler` |
| **②-2** correction 吃六形态墙证据 | ⏭ 一体改本体 | 🟡 **5/6 形态 + 提示词未改** | `evidence_contract.py` 有 `paired_faces`/`solid_band`/`single_face`/`ambiguous`/`non_wall`；**`axis_trace` 全 src 零命中**（只在测试名 `test_legacy_outer_skin_stroke_does_not_become_axis_trace` 里，且该测试断言它**不该**产生 ⇒ 疑似有意去掉，**但 plan.md 没登记这个决定**）。两句 `wall-centerline`（`pipeline.py:405/408`）**仍在**，但它们属 **legacy 腿**（`_build_correction_messages`），新链不用；`wall_compiler.py:115` 反而有 `IDENTITY_BAN = "IDENTITY_AS_CENTERLINE"` |
| **②-3** F-87 门窗身份逐洞口外置 | ⏭ | ⛔ **未做** | 全 src 只有 `reading_grade.py:21` 一句注释提及 |
| **②-4** 吸附分辨率跟 gt 走 | ⏭ 随 ②-2 | ✅ **已落地** | `answer_compiler.py:46/983/997 snap_to_ingest_resolution`（= A-11） |

---

## 3. ⭐⭐⭐ 真正的缺口：一体改**实现了、跑通过**，但**生产入口没接**

### 3.1 它确实跑过，而且是真模型

[`2026-09-02b_m7_evidence_chain_run`](../2026-09-02b_m7_evidence_chain_run/README.md)：
喂真实新格式产物 `sm25_2f_v2.json` → `run_correction_evidence_chain(profile='exploratory', round_budget=3)`
（**不传 `fixed_responses`**）⇒ **deepseek-v4-pro 真模型拍板**，`_run/evidence_chain_route.json`
记 `response_source=model:correction_decision`；**185.8 s · 2 轮 · success=True**，22 个待裁决项全裁完。

### 3.2 但三个入口里只有一个走新腿，而那一个生产零调用者

```
pipeline.py:1692   run_multifloor_correction  → evidence_chain=True   ✅ 新腿
pipeline.py:2344   run_pipeline               → 不传 evidence_chain   ⛔ 旧腿
run_stage.py:457   flow CLI                   → 不传 evidence_chain   ⛔ 旧腿
```

`grep run_multifloor_correction` 的**唯一调用者 = `tests/test_b2_multifloor_assembly.py`** ⇒
**生产侧零调用、CLI 零接线。**

⇒ **今天要走新路跑一个 case，只能像 09-02 那样手写脚本直调；`flow` 到不了它。**
⭐ 这正是第七程给 **J-3-d1** 判过的形状（「是保险丝，不是通车的路」），
且 plan.md 的 **E-b** 行已经写着「E-a′ 落地后必须回来补一条经真入口的端到端锁」——
**E-a′ 已于第七程合并（`512498e1`）⇒ 那个前置已经解除，但没人回来做。**

---

## 4. 这次对账本身的方法论

⛔ **主控此前的状态汇报读的是文档标记，不是代码。** 一条一条看下来，
**错的方向是单一的：文档一律【滞后】，从没有【超前】** —— 即产物比叙述更完备。
这与 [[design-doc-described-what-code-never-implemented]] 记的形态**正好相反**，
⇒ ⭐ **该记忆要补上反向形态**：「叙述比产物更合规」是一种，
「**产物跑到叙述前面、于是拿旧题面去派工**」是另一种，**后者会让人去修早就修好的东西**。

⭐ **判别法则**：管理文档里每一条 `⏭ / 🔶 / ⛔ 未做`，问一句
**「这条我最后一次【拿代码】验它是什么时候？」** 答不上来 ⇒ 它是**印象**不是**状态**。


---

## 5. 覆盖面（⛔ 如实登记，第一版报告曾把局部说成全部）

⚠️ **主控第一次汇报本次通查时说「文档全部对齐现状」，那是错的** —— 当时只验了 8 条。
用户追问「文档现在已经更新对齐了吗」后重新清点，如实如下。

| | 数 |
|---|---|
| plan.md 带状态的条目 | **142** |
| 判为仍开着的 | **~93**（去重后） |
| **本轮实测过的** | 活表 9 条 + sol 6 条 + F-148 + F-131 + W-1/W-2 接线面 ≈ **19 条** |
| **未复验的** | **~76 条** F- 债务清单（登记日多在 2026-07~08） |

### 一次失败的尝试，值得记

先写了个**机械分流**：从每条正文抽反引号里的标识符，去 `src/` 验存在性。
**结果几乎全是 ✓，零分辨力** —— 因为「标识符还在」回答不了「缺陷还在不在」。
⇒ ⭐ **同族 [[gate-measures-a-proxy-not-the-thing-it-guards]]：那把尺子看不见要问的量。**

**换成有分辨力的尺子**：按「**谁负责退休它**」筛 —— 很多债当初写的是
「⏭ 归 ②-1 / 随 B4 / 随 A-11 一并」，而**那些包后来都合并了**。
⇒ 一次筛出 **17 条过期高危**，其中抽验的 F-148 **确已修**（`angle_deg` 是真字段 + transport + 对账锁），
F-131 **确未修**（chromaticity 仍是唯一判别特征）。⇒ **两个方向都出现过，所以必须逐条验、⛔ 不能整批推定。**

### 结构性修法（已落地）

plan.md 顶部加了 **验证戳** 一节：把每条状态分成 ✅🔬实测 / 🟡📋登记时为真 / ⚪❓仅印象 三档，
并写死「⛔ 不许拿 🟡/⚪ 档直接当派工题面」。**下次读这份文档的人，能分清哪条是状态、哪条是印象。**


---

## 6. 17 条「过期高危」逐条复验结果（2026-09-07 补做）

| 档 | 数 | 条目与依据 |
|---|---|---|
| ✅🔬 **实测已修** | 6 | **F-136**（守恒式已改走 `all_wall_handles`，`as_measured.py:1041`）· **F-148**（`angle_deg` 真字段 `:820` + transport `:2431/:2473` + 对账锁 `:934/:963`）· **F-150**（窄 scrub 锁在 `8442442a` 删除，**同一提交**换上 `test_r4_clear_every_converter_judgment_readout_and_renamed_carrier_has_teeth` = 「锁任何名字的载体」）· **F-144**（已固化成 `test_o21bs_r4…`）· **B4-②**（`require_affine_spaces`）· **B4-②b**（`_build_manifest`）|
| ⛔🔬 **实测仍开** | 3 | **F-137**（`_ledger_identity` 仍无 thickness/face_lo/face_hi 重算校验）· **F-131**（`pens.py` 仍以 chromaticity 为唯一判别特征）· **F-134**（`src/agent/correction/` 侧零命中 ⇒ pipeline 那半未实现）|
| 🟡📋 **未逐条读** | 8 | F-122 · F-125 · F-119 · F-132 · F-146 · F-138 · F-120 · F-142 —— **只验了标识符存在性**，⛔ 没读它守的是不是原来那件事 |

### ⭐⭐⭐ 这次复验最重要的一条结论

**两个方向都出现了**：6 条早就修好而文档还挂着，3 条真的还开着。
⇒ **⛔ 永远不能整批推定** —— 既不能说「文档滞后所以都修好了」，也不能说「文档写着开就是开」。
**只有逐条验。**

### 顺带发现（已登记 G-g）

`as_measured.py:125` 的**模块 docstring 仍写着旧守恒等式**，而 `:1041` 的实际校验早已改走
`all_wall_handles`。⇒ **同一份文件里，叙述滞后于代码** —— 与本程主线教训同形，
说明「文档滞后」**不只发生在管理文档，也发生在源码 docstring 里**。
⚠️ 这一条尤其危险：docstring 常被当成契约来读。
