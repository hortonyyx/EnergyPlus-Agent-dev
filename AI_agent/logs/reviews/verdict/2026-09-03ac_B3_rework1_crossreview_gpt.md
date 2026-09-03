# B3 立面腿返工 1 · GPT 跨家族复核裁决

- 日期：2026-09-03
- 审对象：`git diff 917df4b..wt/09.03v_b3_r2`
- 工作树：`/tmp/b3_review_gpt`，detached `4c3d451`
- 上一轮：`REWORK / 阻断 3 / 不阻断 1`
- 施工方：GLM；复核方：GPT

## 裁决

**APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 2**

上一轮的三条阻断均已关闭。派工方把“尺寸链总长 == 平面侧外皮跨度”改归 B4，**技术判据正确**：单份立面产物没有类型化的平面外皮跨度，而立面结构线只是像素/拟合观测，四份真实产物与尺寸链的差值也确实非零，不能冒充零阈值等值门。

本轮用 `EvidenceDebtV1` 把未核的跨视图等式带入 bundle，足以关闭 B3 的本轮责任；它不等于该等式已获证。B4 真正接手时仍必须实现跨产物等值门，并在不符时响亮失败。

## 上轮三条阻断逐条复核

### B-1 · 已关闭

`tests/test_o22m1_as_drawn_producer_types.py:446` 的 `_wire_sets` 已去掉默认参数；主锁在 `:478` 显式读取调用时的 `vector_contract.CONTRACTS`，常驻变异锁在 `:529-533` monkeypatch 后直接调主锁，没有再抄一遍断言。

独立变异读数：

```text
B1_REAL=GREEN
B1_MUTATION=RED evidence chain quietly grew: {..., 'contract_smuggled_fourth_wire'} ...
```

另用 AST 扫描 `src/` 与 `tests/` 中引用大写模块名的默认参数，并与测试中的 `monkeypatch.setattr` 目标交叉。仓内存在很多有意固化的常量默认值；交叉只命中 `DEFAULT_GT_DIR` 一族，相关测试要么 patch 另一模块，要么把 patch 后的值显式传入。**未发现第二个“patch 运行时模块属性，但被测主锁仍读 def 时旧值”的同型漏口。**

### B-2 · 已关闭（按本轮正式改判）

`src/agent/correction/evidence_adapters.py:751-781` 为每个立面 bundle 生成唯一的 `other_known_missing` 债：

- `debt_id` 稳定地点名 `elevation_chain_span_unchecked` 及输入身份；
- `channel is None`，因而不是任何通道的豁免；
- `affected_refs` 指向本产物的 `/calibration`；
- 债随 `evidence_debts` 入哈希、随 bundle travel，不再只存于源码注释。

独立用 east 真实字节将 x 尺寸链改为内部仍精确闭合的 21m，adapter 按新边界接受它，同时产出一条 span 债：

```text
SELF_CLOSED_21M=ACCEPTED
CHAIN_M=21.0
STRUCTURE_SPAN_M=19.9954
SPAN_DEBT_COUNT=1
```

这个读数说明缺口被如实记账，**不是** B3 暗中把等式当作成立。其结构化 owner 与 ref validator 弱点见 N-1/N-2。

### B-3 · 已关闭

两把 T7 锁都安装了模型座位 booby-trap。正向锁仍断言 `response_source.startswith("fixed_responses")`；反向锁由于在 route 生成前就抛 `UNWIRED`，改用入口 kwargs 捕获断言 `fixed_responses == []`。

在仓外临时副本上分别删除两处实参，两条均真实运行 `pytest -n 6`：

```text
正向删参：AssertionError: MODEL SEAT OCCUPIED ...
FORWARD_EXIT=1

反向删参：AssertionError: ... kwargs seen: ['out_dir'] ...
NEGATIVE_EXIT=1
```

因此上轮“反向锁删参仍绿”的阻断已翻红关闭。变异只发生在 `/tmp` 临时副本，未修改本工作树代码。

## 对派工方改判的正面回答

### 1. “需要平面输入”的理由成立吗？

**成立，改归 B4 是对的。**

四份立面产物的顶层键只有 `calibration/dimension_witnesses/structure_lines/openings/...`，没有“平面外皮跨度”这个类型化量。用垂直结构线的 `max(pos_m)-min(pos_m)` 作为替代量，四面独立实测为：

| 立面 | 尺寸链总长 | 结构线跨度 | 差值 |
|---|---:|---:|---:|
| east | 20.0000m | 19.9954m | 4.6mm |
| west | 20.0000m | 19.9997m | 0.3mm |
| north | 25.0000m | 24.9982m | 1.8mm |
| south | 25.0000m | 24.9935m | 6.5mm |

更重要的不只是数字非零：`structure_lines` 表达的是立面墨迹观测，不是类型化的平面外皮。即使某一张图偶然数值相等，也不足以把该观测升格为 outer-skin 证据。因此 B3 内部没有可作的零阈值“同一事实”等值门；引入容差反而会变成未签字阈值。

### 2. 改成显式债够不够？

**对关闭 B3 责任足够，对关闭整个系统缺口不够。**

B3 本轮交付的是窗的 z 半和楼层标高，没有消费立面 x 跨度去完成平面↔立面水平配对。所以该未核等式不能由 B3 的单源适配器证明，也不应伪造一个阈值门。此处用随产物走的债保留了未竟事实，不是把“已验证”贴给它。

但 B4 不得把这条债当作证据或豁免；它必须以平面外皮的类型化跨度和立面尺寸链总长做无参数等值对账，并在成功时显式解债、失配时阻断。

## 不阻断项

### N-1 · “归 B4”只被自由文本锁住

`EvidenceDebtV1` 只有 `debt_id/kind/channel/affected_refs/description`；本轮的债类型只能通过 `debt_id` 的 `debt_elevation_chain_span_unchecked_` 前缀机械识别，而所有者 B4 只存在 `description`。独立删掉 owner 文字、重算合法 bundle 哈希后：

```text
OWNER_TEXT_REMOVED=GREEN
```

这的确是“锁住字样，不是结构”。**本席本轮不判阻断**，因为：

1. 现在没有任何生产逻辑从 `description` 解析 B4 后改变决策，因此它尚未承重；
2. 缺口的存在、债的类型家族与输入身份已由 `EvidenceDebtV1` + 稳定 `debt_id` 进入产物，B4 可针对该稳定债类型接线，不需要解析 description；
3. 本轮正式范围明令使用现有证据债机制，而 owner/义务类型的 schema 升级会影响所有已有债，不应由 B3 适配器单方发明。

不阻断不等于免做：**B4 开工前/同时应把 obligation 类型或 owner 结构化，并用注册表将该债类型精确对应到 B4 处理器；`"B4" in description` 不能成为 B4 的生产判据。**

### N-2 · `other_known_missing.affected_refs` 未由 validator 通用校验

`validate_evidence_bundle` 只对 `ambiguous_face` 收集 ref，只对 `zero_payload_channel` 做 scoped-ref 身份校验；对本轮 `other_known_missing` 债的 ref 无通用解引用门。独立把该 ref 改成 `/calibration/definitely_missing`、重算哈希后：

```text
DANGLING_OTHER_DEBT_REF=GREEN
```

实际风险判为**中等**：当前 adapter 的四份真产物锁确实手工解引用到 `/calibration`，因此本生产者现状变异会红，不阻断本轮；但外部载入/篡改后的 bundle 或第二个 `other_known_missing` 生产者可携带悬空 ref 仍通过 validator。在 B4 开始依赖 `affected_refs` 完成解债前，应把“凡存在的 debt ref 都须指向本 artifact 的冻结源且 RFC-6901 可解”收进 validator，测试只作生产者的第二道防线。

## §五七条验收

| # | 判定 | 复核结论 |
|---|---|---|
| 1 | 通过 | 第四个契约转 `ADAPT` 后，直接调主锁真的抛 `AssertionError`。 |
| 2 | 通过 | 主锁调用时读 `vector_contract.CONTRACTS`；未发现第二个相同 monkeypatch/def-time 漏口。 |
| 3 | 通过，带 N-1/N-2 | 缺口已是 bundle 中入哈希的显式具名债；owner 与通用 ref 校验仍需 schema/validator 后续。 |
| 4 | 通过 | 两把 T7 锁分别删除 `fixed_responses` 均失败，exit 1。 |
| 5 | 通过 | 执行档已明确更正“两把都断言 response_source”的错误及 T0 的 18 def / 27 collect 口径。 |
| 6 | 通过 | 目标三文件 `120 passed`；数据承载、来源引用、楼层线谓词、T7 公开入口及 `UNWIRED` 反向锁均未退化。 |
| 7 | 通过 | 全量 `3753 passed / 2 skipped / 13 xfailed / 0 failed`，exit 0。 |

测试数逐位闭合：

```text
3748  上一轮复核基线
+   4  test_span_equality_gap_travels_as_a_named_debt[四立面]
+   1  test_the_span_debt_is_a_property_of_the_family_not_the_fixture
= 3753
```

`tests/test_b3_elevation_leg.py` 由 29 项增到 34 项；B-1/B-3 只改写原测试，未增减项数。

## 独立测试摘要

所有 pytest 都使用 `-n 6`，未运行 `pip install -e .`。

```text
模块路径：/tmp/b3_review_gpt/src/agent/correction/evidence_contract.py
目标三文件：120 passed in 6.01s
全量：3753 passed, 2 skipped, 13 xfailed, 211 warnings in 566.18s
全量 exit：0
```

全量有完整 summary，慢尾为同机竞争下的耗时，不是假红。

## 未复现

施工方在中间 commit `7c63216` 上的第一次全量耗时，以及其“退回无 span 债 adapter 后 5 failed”的原样 neuter 流程，**未复现**；本席没有用这两条自述作为裁决证据。本单其余关键验收均已独立复现。

复核过程未修改项目代码；只新增本裁决文件。
