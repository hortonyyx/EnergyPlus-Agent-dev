# F-9 路线②设计稿 v2 · 对抗审裁决（orchestrator / Claude 侧 Opus 5）

> 日期：2026-08-10 · 受审稿：`AI_agent/proposals/f9_route2_evidence_citation_design.md`（v2，882 行）
> 出稿席：`gpt-5.6-sol` / effort max · 审阅席：orchestrator（跨家族，谁写谁不批）
> 基点：`cb1ce62`，全仓 2361 passed / 10 xfailed / 0 failed（本轮独立复跑）

## 裁决

**APPROVE-WITH-CHANGES** — **1 MAJOR / 2 MINOR / 0 BLOCKER**

v1 的 3 BLOCKER + 5 MAJOR + 1 MINOR **逐条已解**（见 §1 核对表）。设计可施工，
但**必须先补 MAJOR-1 再出施工单** —— 它压在真实产物上 2/15 扇窗，不是未来假设。

## 审阅方法

只读。**不采信出稿方自述**，改为对承重命题做机械测量：用 F-20 刚修好的官方入口
`load_verified_accepted_correction` 加载全项目**唯一一份 v3 真实产物**
（`run_2026-08-09_f18_e2e_verify`），以**生产代码本身**
（`materialize_current_ring_va_elevation_bindings` + `ViewProjectionFrame`）复算全部 15 扇窗的
平面/立面两路观测。零 LLM 成本、零生产码改动、未跑全仓。

---

## 1. v1 失效点是否已解（逐条核对）

| v1 findings | v2 处理 | orchestrator 核实 |
|---|---|---|
| **B1** 派生与校验同源 ⇒ 恒真式 | span 唯一来自 **plan authority**；elevation 只作独立佐证，不参与数值仲裁（§0/§5.3/§5.4） | ✅ 结构上非恒真：两路观测来自不同 view、不同坐标系 |
| **B2** 派生入口写错 + marker 做不了外部派生 | 明确 `existence` 驱动 + `along`/`host` 同一 plan source；raw→authenticated→hydrated→full 四阶段合同显式切断阶段环（§4.4/§5.1/§8.1） | ✅ 与现行 `_claim_links` 一致 |
| **B3** 提权 advisory | advisory 保持非权威，enforcement **在类型上**拒绝（§1.3/§6.3）；§12.2 专列「Advisory 隔离」锁 | ✅ 且锁矩阵要求先自证 0.12 m 差存在 |
| **M1** 漏 `facade.py::_CONVENTION` | §6.1 单源含全部四处 | ✅ **实测确为 4 处**：`facade.py::_CONVENTION` + `window_sources.py` / `facade_applicability.py` / `judge/score_inputs.py` 三份 `_BASE_SIGN` |
| **M2** S1–S4 不可独立验收 | 改 `S0→S1→S2 shadow→S3 detector→S4 原子 cutover`，逐步写明验收性与原子边界（§10） | ✅ |
| **M3** 发明模型算不出的 `src:` wire | 两层分离：model-facing `view/obs` + 内部 authenticated locator（§4.2/§5.2） | ✅ **实测真实产物用的正是 `1f_view/S11` 形态** |
| **M4** binding 与「各层 footprint 相同」绑死 | 拆 view datum 与 floor/z-band scope（§7.1–7.3） | ⚠️ 方向对，**但 z 轴留了口子 ⇒ 见 MAJOR-1** |
| **M5** 锁摘掉修法仍全绿 | §12 锁矩阵 15 行，内化项目七条锁纪律，含**遮蔽**与**两边皆空**两条 | ✅ 本项目迄今最完整的一份锁规格 |
| **m1** 「不许分支」措辞 | 改为「一处公开投影入口 + 一份 elevation 公式」，保留合法 channel dispatch（§6.3） | ✅ |

---

## 2. Findings

### MAJOR-1｜沿墙轴有 typed datum 声明，**z 轴一个都没有** —— 而 z 是真实产物里 2/15 扇窗的**唯一**判别依据

**位置**：§5.2 步骤 5、§5.3 条件 2/3/6、§7.1 `ElevationProjectionScopeV1`、§7.2。

**设计现状**：沿墙（local x）方向被处理得很严 —— §7.2 显式声明
`datum_mode="view_global_projected_envelope"`，并规定未声明时抛 typed `projection_datum_unresolved`、
**绝不猜**。**而 local z → world z 的对应关系全稿没有任何一句规定**：§7.1 的 scope 里写了
`z_band_id + world_z_interval`，§5.3 条件 6 要求「floor/z scope 与 window 一致」，
**但「一条立面笔画属于哪个 scope」如何判定，没有定义**。

**为什么这次是承重的（实测，不是推理）**：真实产物的 East 立面有两条笔画，
**沿墙区间逐位相同、只有高度不同**：

```
East_view/S3   local_along [3.40, 4.60]   local_z [4.00, 5.80]   ← 二层
East_view/S4   local_along [3.40, 4.60]   local_z [1.00, 2.80]   ← 一层
```

对 `win_f1_E1`，两条候选到其 plan 区间的端点距离**都是 0.0000 m**
⇒ §5.3 条件 3「最优与次优距离之差大于 ambiguity epsilon」**当场为 0 ⇒ 不满足**
⇒ 一份**完全正确**的产物会被判 `position_evidence_insufficient`。
`win_f2_E1` 同理。**15 扇窗里 2 扇（13%）的判定完全依赖这条未定义的规则。**

**⚠️ 更隐蔽的一层**：本产物的 `local_z` 恰好**就是世界 z**（S4 的 `[1.00,2.80]` 与一层窗世界 z 相同）。
⇒ 实现者随手写「local_z 即 world z」**在今天会碰巧全对**，于是这条隐含约定
**永远不会被任何测试发现**，直到某份 reading 按层归零 z 为止 ——
**这正是本项目「一个事实多处声明 / 约定没有承载物」那一族的标准形状**。

**要求的改法**：给 z 轴一份与 §7.2 对称的显式声明 ——
`z_datum_mode`（如 `world_z` / `floor_local_z`）+ 未声明时 typed 拒绝 + scope 归属规则写死；
§12.2 的「Pair positive」行必须补一格夹具：**同 view、同 along、仅 z 不同的两条笔画**，
断言各自只与自己那层的 plan 配上，且**去掉 z scope 后该锁必红**。

### MINOR-1｜0.300 m 容差的立论基础，在**今天的产物上已经归零** ⇒ 阈值本身不可观测

§5.3 冻结 `window_evidence_pairing_tol_m = 0.300`，立论是外皮/centerline 的 0.12 m 基准债。
**该量级引用属实**（实测 `envelope_reconcile_tol_m` 与 `facade_frame_cross_check_tol_m` **都恰是 0.300**）。
§12.3 的 oracle 用 `tests/fixtures/f9_window_host_crash/` 老夹具算出 `d = 0.12`，**也算对了**
（老 ring `[0.12,14.88]` ⇒ origin 14.88）。

**但今天的产物上，15/15 扇窗的 `d` 全部恰为 `0.0000 m`** —— F-17 修法把 ring 变成 `[0,15]`，
基准差整体消失。⇒ 在现代产物构成的夹具上，**这个常量取 0.001 还是 3.0 没有任何区别**，
一把只用现代夹具的正向锁**对任何 `tol ≥ 0` 都绿**。这与 §12.1 第 7 条
（「hash/集合相等前断言双方非空」）是同一族问题的另一个面。

**要求**：§12.2「Pair positive」必须**同时**钉两个 regime —— 老夹具（`d=0.12`，证明带内非零可通过）
与现代产物（`d=0`，证明零差不被特判），并补一格**跨阈值对照**（如 `0.29` 放行 / `0.31` 拦下），
否则阈值本身零分辨力。

### MINOR-2｜请求书两处前提被出稿方纠正，登记为**派工方错误第 13/13**

sol 如实纠了两条，**均成立**：① 我写「工作树干净」而实际有一个未跟踪文件（就是那份请求书本身）；
② 我把兼容面描述成 v1/v2 两轴，**而仓库已有 historical v3 producer artifact V1** ⇒ 只写 v1/v2 会漏一类。
第二条有实质影响（会让施工单漏掉一整类兼容边界）。**⇒ 派工方错误率更新 13/13。**

---

## 3. orchestrator 机械测量：关掉出稿方 3 条自陈未验证项

sol 全程**未跑任何探针**（自陈，我核实其 log 属实），§14.3 列了 11 条未验证。本轮关掉 3 条：

| sol 的未验证项 | 实测结果 |
|---|---|
| 「未统计真实 v3 draw 中满足『唯一 plan + ≥1 elevation existence』的比例」 | ✅ **15/15 全满足**；`along`/`host` 也都恰好指向 existence 里那条唯一 plan；**零来源复用** ⇒ §5.1 规则不误伤现产物。模型是在**完全不知道这条规则**的前提下自然产出该形状的 |
| 「未对 corpus 测 0.300 m 的误拒率」 | ✅ **零误拒**（15/15 的 `d` 恰为 0.0000）；⚠️ 但由此暴露 MINOR-1 —— 无误拒是因为**根本没有样本落在 (0, 0.3] 带内** |
| 「未验证跨楼层同 x 的 pairing 行为」 | ⛔ **该情形不是假设，真实产物里已存在**（East 立面 S3/S4）⇒ 升级为 MAJOR-1 |

**⚠️ 口径**（与 F-20 那次同一条纪律）：以上测的是**今天盘上这一份语料**（1 个 case / 15 扇窗），
**不是**「代码保证」或「模型永远如此」的不变量证明。施工期的 targeted replay 仍须保留。

**顺带证实一条既有登记债**：结转表里「落盘产物不能直接重放、官方入口待做」属实 ——
本轮复算时 `WindowResolverInputsV1.model_validate(dict)` 因 tuple 严格校验直接失败，
必须绕 `model_validate_json` 才能重放。

---

## 4. 值得记账的正面项

1. **§12 锁矩阵是本项目迄今最完整的一份**：15 行逐行给出「夹具自证前提 / 正向+负向断言 / neuter 与遮蔽要求」，
   并把 08-10 刚换来的两条纪律（**遮蔽判别**、**两边皆空**）写成了通用条款 —— 出稿方是在新会话、
   仅凭请求书 §5 的七行表格内化的。
2. **§12.4 单列「防第二条防线遮蔽」的测试组织**，且给出了正确的证否姿势
   （伪造 detector PASS 后链路应能继续 ⇒ 反证 detector 真承重）。
3. **§5.3 末段主动划清了这道门证不了的事**（模型把 plan+elevation+room 成对置换时几何层无法分辨），
   并据此引入 `canonical_window_key`，**没有把门吹成能解决 identity** —— 这正是 v1 最缺的那种克制。

---

## 5. 结论与下一步

- **APPROVE-WITH-CHANGES**：MAJOR-1 必须在施工单出之前补进设计稿（z datum 声明 + 对应锁格）；
  MINOR-1 补两个 regime 的夹具要求；MINOR-2 已在本裁决登记，无需改稿。
- **⛔ 不得据当前稿直接施工**（差 MAJOR-1 那条规则，实现者必然自己发明一条）。
- 返工仍应由 **sol** 做（同一作者补自己的稿子属正常迭代；「谁写谁不批」约束的是**审**，本轮审已在 Claude 侧）。
- 返工后建议**再走一轮 orchestrator 轻门**，只核 MAJOR-1 那条规则是否可机械判定 + 锁格是否真绑。
