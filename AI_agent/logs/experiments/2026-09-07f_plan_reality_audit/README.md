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
