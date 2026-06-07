# 审阅请求：correction 层 A0 契约（脊柱首篇）

- **日期**：2026-06-07
- **发起**：主开发 Agent（Claude Opus）+ 用户
- **类型**：skill 文档审阅（partA 校正约束集逐篇落地第 1 篇；A0 是脊柱，A1–A4 全依赖它）
- **希望审阅模型**：另一模型（Codex / Gemini）

---

## 1. 背景

partA 校正约束集设计已审过定稿（[recognition_modeling_capability.md §5](../../../capability/recognition_modeling_capability.md) + [上一轮 review](../review/2026-06-07_partA_correction_constraint_set_review.md)，8 条 finding 全采纳）。现按落地序逐篇写 skill 文档库，**本篇 = A0 契约**（脊柱：容差·证据·审计·校验 schema + method profiles + 上游输入契约）。A0 定稿后才写 A1-min+A2。

A0 直接回应上一轮 review 的 **finding 1**（A0 不能只是常数表，必须定义 evidence/conflict/correction/validation 结构化契约，否则 A1/A2/A3 各发明审计口径）。

---

## 2. 审阅对象

- [skills/energyplus_mcp_twostep/correction/A0_contract.md](../../../../skills/energyplus_mcp_twostep/correction/A0_contract.md)（主审）
- [skills/energyplus_mcp_twostep/correction/README.md](../../../../skills/energyplus_mcp_twostep/correction/README.md)（子目录结构 + 运行时 + header 约定）

上下文（理解设计意图）：
- [recognition_modeling_capability.md §5](../../../capability/recognition_modeling_capability.md)（partA 定稿设计）
- [上一轮 partA review](../review/2026-06-07_partA_correction_constraint_set_review.md)（A0 推荐形态在 "Recommended Document Shape - A0"）
- [zonification review](../review/2026-06-07_zonification_approach_review.md)（method profiles 的 perimeter_core/use_grouped_rooms/room_identity 来源）

skill 库口径：**英文纯当前版本 spec**，不放时间戳/版本日志/决策史/案例引用。

---

## 3. 关注点（请重点挑战）

1. **A0 作脊柱是否够**：A1（坐标归一化）/A2（正则吸附）/A3（仲裁补全）/A4（先验）真能全部只引用 A0 的 schema、不必各自再造审计口径吗？有没有 A1–A4 会用到、但 A0 没定义的字段/概念？
2. **证据模型**：6 级 evidence grades + confidence + data-priority ladder（§1）——分级干不干净？`inferred_topology` 排在 `estimated_stroke` 之下合理吗？confidence 与 grade 解耦对不对？
3. **审计四类事件**（§2 normalization/correction/conflict/unsupported）边界清不清？`corrections[]`/`conflicts[]`/`unsupported[]` 三个 schema 字段够用吗（漏了什么定位/复现必需字段）？"硬日志规则"（§2.1）够硬吗？
4. **conflict types**（§3 六类）是否覆盖；有无该有的第七类。
5. **tolerance classes**（§4）：分类对不对、absolute-grid vs relative-error 的切分对不对；标 *provisional/pending* 的常数（SNAP_GRID/MIN_EDGE_LENGTH/GAP_CLOSE/AXIS_JITTER/PERIMETER_DEPTH）等检索包回填——这种"先占位待校准"在 spec 里可接受吗，还是该用别的表达？
6. **method profiles**（§5）：三档严格度划分对不对；"A3/A4 在 perimeter_core 下保守、room_identity 下全力，A1/A2 全档适用"是否准确（呼应 finding 7）。
7. **上游输入契约**（§6）+ **降级策略**：legacy 无 provenance 的 JSON 降置信运行 + 多吐 conflict，这条够不够、会不会过松。
8. **validation schema + fail/continue 策略**（§7）：硬失败项（重叠/未声明洞/退化边/containment）vs 相对容差通过项——切分对不对；漏了什么校验项。

---

## 4. 验收标准（review 文档应给出）

- **Verdict**：A0 是否可作脊柱定稿、进入 A1-min+A2？
- 逐条回应 §3 八个关注点（同意/反对/补充 + 证据）。
- 缺字段/缺概念清单（A1–A4 会用但 A0 没给的）。
- 输出落 [../review/2026-06-07_correction_A0_contract_review.md](../review/)（命名对齐本 request）。

---

_本 request 与对应 review 均 git 跟踪。A0 定稿后续写 A1-min+A2（同批）。_
