# B4 洞口合成 · GPT 跨家族复核裁决

- 日期：2026-09-03
- 审对象：`git diff afa467e..wt/09.03ag_b4`
- 工作树：`/tmp/b4_review_gpt`，detached `4ea103d`
- 施工方：GLM；复核方：GPT

## 裁决

**REWORK / 阻断 2 / 不阻断 3**

先把本单最容易混在一起的两件事拆开：**真实四立面 0 对，本身不构成本轮返工理由**。在七条书面验收没有要求真实产物必须形成正配对的前提下，不能事后把派工方漏写的验收追罚给施工方；区间等式、拒绝不猜和双侧完备性都已实现。当前 `REWORK` 来自两条与 0 对无关、且直接击穿 T4-b/T4-c 的债务链反例：注册表 handler 没有驱动处理，及一次立面合成会销掉其他立面的真实债。

## 阻断项

### B-1 · 注册表的 handler 值不参与执行，T4-b 的“对应到处理器”仍是装饰性接线

`src/agent/correction/opening_synthesis.py:215-217` 把前缀映射到字符串 `span_equality_gate`；但实际控制流是：

- `:572-576` 无条件硬调用 `span_equality_gate`；
- `:258-272` 的 `redeemable_debt_ids` 只看 `debt_id.startswith(prefix)`，完全不读取注册表的 handler；
- `:232-238` 的注册表自检只要求该名字指向“任意 callable”，不核它就是本债的兑现处理器，更不调用它。

独立运行时变异把 handler 改成签名、语义都不相干但确实存在的 `grid_units`，自检仍通过，债仍被销：

```text
WRONG_HANDLER_ACCEPTED= grid_units
RETIRED= ('debt_elevation_chain_span_unchecked_input_east',)
```

因此“删掉 description 里的 B4 仍接线”这个窄判据虽绿，但它只证明**不读字样**，没有证明注册表的“处理器”一栏真的承重。验收 #4 的标题规则“债的接线是结构”及任务项 T4-b 尚未完成。

返工门：注册表选中的处理器必须真正驱动该债的兑现，或改成等价的、单一来源的可执行接线；把该前缀指向错误的现存 callable 后，必须响亮失败或至少不得销账。不能再用“名字存在且 callable”代替执行关联。

### B-2 · 销账没有绑定本次立面/源，真实的外立面债会被误销

`redeemable_debt_ids` 对传入序列中所有命中前缀的债一律返回；`synthesize_openings` 没有把当前 `elevation_doc` 与债的 `affected_refs.input_id`、源 hash 或 facade 身份关联。用 B3 真实 East/West 字节各自产生一张合法债，再只运行 South 的等式门，得到：

```text
CURRENT_FACADE= South
AUTHENTIC_FOREIGN_DEBTS=
  [('debt_elevation_chain_span_unchecked_input_east', ['input_east']),
   ('debt_elevation_chain_span_unchecked_input_west', ['input_west'])]
RETIRED=
  ('debt_elevation_chain_span_unchecked_input_east',
   'debt_elevation_chain_span_unchecked_input_west')
```

这不是恶意冒用前缀，而是两个真实生产者实例；South 通过并不能证明 East/West 已兑现。它直接反驳产物字段注释和执行档所称的 “per product、per facade”，击穿 T4-c/验收 #5。

返工门：销账必须绑定“本次门实际核过的那一个源实例”；混入至少两张其他 facade 的真实债时，只能销当前实例，其他债原样保留。具体用现有 `affected_refs`、显式 source identity 还是经授权的新结构，由派工方签字；本席不要求施工方擅改 `EvidenceDebtV1` schema。

## §二三问正面回答

### 1. 真实四立面 0 对是不是可接受？在既有七条验收下 B4 算不算完成？

**是：仅就“0 对”这件事和既有七条规则形态而言，可接受，B4 在这一部分算完成。**

我独立跑真实四立面得到：

```text
REAL_East:  pairs=0 unmatched_plan=34 unmatched_elev=13
REAL_West:  pairs=0 unmatched_plan=34 unmatched_elev=6
REAL_North: pairs=0 unmatched_plan=27 unmatched_elev=8
REAL_South: pairs=0 unmatched_plan=27 unmatched_elev=7
```

每一面都满足“paired + unmatched == 全部输入”，没有静默丢项。任务书七条没有“真实产物至少配出一对”或“预期正配对逐个闭合”的验收，所以 **0 对是派工方漏项暴露出的能力缺口，不是施工方违反既有验收**。

但这只表示规则实现按原单交付，不表示真实业务结果已经可用：真实产物没有一条配对，就没有一条真实 z 被合成进平面洞口。故应登记新的正向真实产物验收；当前整单仍因 B-1/B-2 而 `REWORK`，不是因 0 对返工。

### 2. 不锁“必须 0 对”的推理成立吗？

**成立。** 锁死 0 对会把 reading 当前的像素量化误差固化成契约；reading 精度或合法对齐转换改善后，正确结果反而会假红。现有双侧完备性锁是必要的拒绝守恒锁。

不过完备性只证明“没有丢”，不证明“合成产生了有用结果”。正确补法不是加一把“必须 0 对”锁，而是在对齐规则另行签字后增加真实产物的**正配对**验收，并继续保留“非等区间不猜”的负锁。

### 3. `edge_witnesses` 的两档数据归谁、现在做还是登记？

**归 correction 侧的 B4 后续（或由 B4 调用的独立对齐转换），不归 reading，也不应推给 B5；现在登记并另发有验收的单，不在本轮临时补阈值。**

依据有两层：

1. 既有 reading 原型在 `tools/as_drawn_elev.py:10-15,189-193` 已明确把“裸像素 + 最近刻度证据”交给 correction，并明确不在 reading 吸附；让 reading 改成只发吸附值会倒退证据边界。
2. 水平边对齐是“能否按等区间确认跨视图身份”的前置转换，属于 B4 的输入规范化；B5 是端到端接线，不应在那里首次发明几何身份规则。

派工方列出的 `535.8 / 20.3 ≈ 26.4` 成立。把四立面全部水平边展开后，读数更完整地表现为：68 条 x 边中 66 条位于 `0.0～33.9 mm`，East O01 两条为 `535.8 / 2163.7 mm`。这强烈支持“近刻度/远刻度可分”的研究方向，但仍**没有自动给出可泛化的判据**：近档内还包含 `0.0/6.8/13.5/13.6/20.3/27.1/33.9`，而 `nearest_tick_px` 只是“最近”，不等于该刻度在语义上必然定位此洞口边。

因此本轮不得让施工方拍一个 cutoff。后续单应先用 `dimension_refs` 与尺寸链拓扑证明“哪类刻度有资格定位洞口边”，再验证：合资格边转换到刻度的精确链坐标；不合资格边保持 raw/unmatched；全程无容差配对。B2 的楼层身份维度仍另算，不能让水平吸附替它消歧。

## P-1～P-5

| 项 | 判定 | 独立复核结论 |
|---|---|---|
| P-1 | **通过** | 比较落在 0.1 mm 整数网格；生产逻辑未见容差比较。独立输入 `24999.9 mm` 对 `25000.0 mm` 外皮得到 `ELEVATION_CHAIN_SPAN_MISMATCH`，`difference_grid_units=-1`。 |
| P-2 | **通过** | 四边厚度 `0.37/0.30/0.24/0.20` 夹具同时覆盖 x/y 两轴；每端分别取自己的 half-thickness，全局单一 half 变体会失败。 |
| P-3 | **窄判据通过，T4-b 总体失败** | description 完全无 `B4` 时仍识别、description 满是 `B4` 但前缀不对时不识别；但注册表 handler 不承重，见 B-1。 |
| P-4 | **通过** | `git diff --exit-code afa467e..wt/09.03ag_b4 -- src/agent/correction/evidence_contract.py` 为空；基点与终态文件 SHA-256 都是 `a5550ab6affb04e56b2788db2a0fc78a37e23541ca9c77de23979db5013319e2`。`EvidenceDebtV1` 确实一个字节没改，A 层停报属实。 |
| P-5 | **高风险** | 前缀没有 mint authority，任何生产者都可伪造该命名空间并被静默销账；而 B-2 证明无需恶意伪造，真实但不属于本立面的同前缀债已经会被误销。schema 升级仍按 A 层另行拍板，不在本轮擅做。 |

## 七条验收逐条

| # | 判定 | 复核结论 |
|---|---|---|
| 1 | **通过** | T2 为整数等式门；差一个 0.1 mm 网格单位即具名失败，未见容差常数参与比较。 |
| 2 | **通过** | 四边异厚夹具覆盖两轴，并证伪全局偏移。 |
| 3 | **通过** | 只按整数世界区间相等分桶；差 1u、无对、同区间多义均拒绝，不作最近/顺序兜底。 |
| 4 | **失败** | description 字样删除锁通过，但注册表 handler 不驱动处理，错误的现存 callable 仍可自检通过并销账，见 B-1。 |
| 5 | **失败** | 当前 facade 通过会销掉其他 facade 的真实债，未做到“该债被该门兑现后才销”，见 B-2。 |
| 6 | **通过** | `ELEVATION_CHAIN_SPANS_WHOLE_BUILDING` 单一具名；一跨立面以 `ELEVATION_CHAIN_SPAN_MISMATCH` 响亮失败并带两侧读数。 |
| 7 | **通过** | 定向 20 项和全量均绿；计数逐位闭合，见下。 |

## 不阻断项

### N-1 · 真实正配对验收漏项

真实四立面 0 对没有违反旧单，但使“洞口合成”在真实数据上的有效性未获证。归派工方补一条后续验收，不能倒签为本轮施工缺陷。

### N-2 · `edge_witnesses` 数据派生对齐待立项

两簇距离是值得继续的实证；归 B4/correction 后续，先证明刻度资格再转换。当前只登记，不加任何未签阈值。

### N-3 · `EvidenceDebtV1` 的 obligation/owner 结构化仍待主控拍板

施工方按 A 层停报，没有越权改 schema，处置正确；但 debt-id 前缀仍只是命名空间约定，无法强制 mint 权。该架构债不因本轮两个局部返工门而自动关闭。

## 测试与计数

所有 pytest 均使用 `-n 6`，未运行 `pip install -e .`。

```text
模块路径：/tmp/b4_review_gpt/src/agent/correction/evidence_contract.py
B4 定向：20 passed in 2.78s
全量：3776 passed, 2 skipped, 13 xfailed, 211 warnings in 449.99s
全量 exit：0
```

`git diff afa467e..wt/09.03ag_b4 -- tests` 只新增 `tests/test_b4_opening_synthesis.py`；该文件恰有 20 个 `def test_`，无参数化 decorator，既有测试未改。因此：

```text
3756  主控合并树权威基线
+  20  本单新增、非参数化测试
=3776  本席全量实读
```

施工方自报的 `+20` 和三项总数均核实成立；耗时读数不同不影响闭合。

## 未复现

- 施工档 M1/M2/M3b/M4/M5 的备份—改文件—还原原流程：**未复现**。本席没有改代码，改用定向测试、运行时内存变异和独立输入反例取证。
- “仅凭现有 `edge_witnesses` 已可无阈值地产生完整正确配对”：**未复现**。目前只复现了显著分簇，尚无签字的刻度资格规则。
- 施工方全量耗时 `442.80s`：**未复现**；本席同数结果耗时 `449.99s`。

复核过程未修改项目代码；只新增本裁决文件。主控预置并已暂存的复核请求单保持不动。
