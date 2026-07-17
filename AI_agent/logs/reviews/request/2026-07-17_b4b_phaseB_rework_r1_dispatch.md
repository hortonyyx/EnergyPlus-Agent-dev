# B4b Phase B 返工 r1 派发（terra 执行档，2026-07-17）

**背景**：B4b Phase B 经 Opus 子代理升一档审 = **ACCEPT-WITH-REWORK**（裁决 [2026-07-17_b4b_phaseB_review_r1.md](../verdict/2026-07-17_b4b_phaseB_review_r1.md)）。**头号结论正面**：伪 ledger 已在 reading/GT + reference/absence 轴真替换成真实 typed-GT+Va+completeness 路径（5 活体探针坐实核心信任根/恒真式/守恒为真、Va 唯一引擎坐实、禁区全 CLEAN）。主控已亲核两 MAJOR = CONFIRMED（点名的 5 个函数在 tests/ **零引用**、host 靠常量 `host_results` 喂入、interior 两 raise 零触发）。

**扣点 = correction/product/host 轴 + interior partition + reading adapter 全 shipped-untested**（补完接了代码、没补测试）。本轮 = **补真实路径测试到未测轴**。

## ⚠️ 关键提醒：这些分支从没执行过
点名的函数/分支在测试里从没跑过（真 resolver 分支、interior 反向配对、reading adapter）。**补真测试很可能暴露这些路径里的真 bug**。若某测试暴露真 bug：**修生产码 + 在简报明确登记**（这是合理的——这些路径从没被验证过，本轮就是来验证的）。但修生产**只限本批新增的 correction/interior/host/reading-adapter 路径**；若发现须改 Va（`facade_applicability.py`）/Phase A 稳定件/禁区才能过 → **停止报 blocker**，不擅改。

## 返工项（逐条闭合）

### MAJOR-1（必闭）：correction 段提取 + §8.4.1 host resolver 零覆盖
`opening_claim_score.py:70 resolve_correction_window_host`、`:95 build_correction_host_resolver`、`segment_score.py:118 extract_correction_plan_segments` 在 tests/ 零引用；host claim 全靠常量 `host_results={target.id:"complete"}` 喂入（test:160/174/186），真 resolver 分支（`host_resolver is not None`，opening_claim_score.py:415）从不进入。补：
- **correction 段提取真断言**：`extract_correction_plan_segments` 走真实 correction observation 输入（typed，参照 reading/GT 轴已建的真实 fixture 模式），断提取结果精确（段几何/家族/span），成功 + 负轴（畸形/歧义输入 raise）都测。
- **host resolver 端到端**：构造真实 correction window + multi-zone 平面，经 `build_correction_host_resolver` 产 resolver、**传进 `score_plan_claims(host_resolver=...)` 让真 resolver 分支执行**（不再喂常量 host_results），断 §8.4.1 精确共线邻接解析正确；负轴（0 相邻 room / 多相邻 room → `score_product_segment_unresolved` raise）触发并断码。
- `resolve_correction_window_host` 的 span 轴判定、same_line 精确等式在真实数据下命中（防"轴判反/永不命中恒 miss"——审点名的失败场景）。

### MAJOR-2（必闭）：interior partition 提取 + reading typed adapter 零覆盖
`extract_gt_plan_segments` 的 interior 反向配对分支（segment_score.py:86-107）+ 两 raise（`exterior_interior_topology_conflict`/`invalid_interior_edge_pair`）从不触发（唯一 fixture 单 zone/层无内墙）；`coerce_plan_observations`（reading typed adapter，segment_score.py:141）零引用。补：
- **多-zone GT/correction fixture**（共享内墙）触发 interior 反向配对，断 interior target 精确（owners/reverse 归组正确、不漏不重）；两不变量 raise 各造反例触发并断码。
- **`coerce_plan_observations` 真断言**：reading typed observation → 内部结构，走真实 dispatch 路径，断转换正确 + 畸形输入行为。

### MINOR-1（闭）：B1 headline 恒真式改真提取
`test_b4b_b1_actual_concave_segments_are_not_bbox_or_fixed_four_sides`（test:78-87）的 `actual` 半段是手搓 ring 边列表自证——改成走真实生产提取（`extract_*_plan_segments`）产的 actual 段再断非 bbox/非固定四，让它真锁生产凹形拓扑（当前只靠 sibling 测试覆盖 exterior）。

### MINOR-2（闭）：declaration-deletion 守恒改真重推
`test:190-201` 的 `before`/`after` 读同一 immutable 对象、`before==after` 是 x==x 空转。改成：product declaration 删除后**真实重推 reference ledger**（独立 Va 调用），断 reference denominator 逐字节/逐值不变、而 product 侧确实变——让 guard 真能防"product 数据串进 reference 路径"的回归。

### MINOR-3（闭）：`bind_correction_window_segment` 成功路径
当前只测 ambiguous/empty raise（test:126-136）；补成功分支 `declared_segment_binding`/`temporary_unique_span_binding`（opening_claim_score.py:63-66）真断言。

### NIT（可闭，顺手）
- **NIT-1**：`derive_product_ledger`（opening_claim_score.py:213）补一条真断言（与 absence ledger 孪生 passthrough，一条即可）。
- **NIT-2**：真-Va 测试的 GT view id 与 manifest input_id 恰相等（fixture 巧合）——补一个 view id ≠ input id 的 fixture，区分性验证 `source_view_to_input` 映射真实分支。

## 硬边界
- 不 commit；不改管理文档（本 dispatch 与执行简报除外）。
- 生产改动**只限**本批新增 correction/interior/host/reading-adapter 路径（且仅当补测暴露真 bug）；`facade_applicability.py`(Va)/Phase A 稳定件/production schema/view_manifest/run_stage/render_grade/gt/golden/B5-B6 **一行不改**——必须改才能过则停止报 blocker。
- 合成 fixture 只进 pytest tmp/测试代码；gt 铁律生产零 judge import 保持。
- **全量 pytest 不用你跑**（主控轻门的活）；你只跑定向组确认绿、记 passed 数。

## 交付
1. 工作树内测试补齐（+ 若暴露 bug 的生产修，不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseB_construction_brief.md` **追加「返工 r1」节**（逐项 MAJOR-1/2 + MINOR-1/2/3 + NIT 修法 + 新测试名 + **补测是否暴露真 bug 及修法** + 定向 passed 数 + 本轮改动文件）。
3. terse report：各项闭合状态 / 新增测试数 / 补测暴露的 bug（有则列明修法，无则注明）/ 定向 passed / 偏差。

审向：**主控轻门**（返工主要测试侧 + 可能的小生产修，主控独立全量 + 抽查关键新断言活体自证 + 裁决；若补测暴露非平凡生产改动，再起 Opus 子代理定向复审）。
