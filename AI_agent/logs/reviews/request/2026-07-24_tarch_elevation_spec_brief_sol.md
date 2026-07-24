# Brief：请 sol 出「天正命名立面处理」设计细稿

**日期**：2026-07-24 · **主控**：Opus 4.8
**出稿方**：sol（GPT 侧 gpt-5.6-sol·次高档·熟转换器）
**审**：Opus 子代理升一档对抗审细稿（Claude 侧·谁写谁不批）→ 主控裁定 → 之后 terra 施工 + Opus 审施工
**性质**：细稿（bounded feature spec）。**累计式自包含**（每版全文累计，禁「vN 不变」引用已覆写正文——见教训 spec-must-be-cumulative）。

---

## 0. 背景 / 缺口（已由主控查实）

天正→GT v3 转换器 P0–P2 + 返工已 CLOSED（GLM APPROVE）；洞口按位置挂载修复已过（`2b7affad`）。**但转换器只处理平面、完全没处理立面**：
- `TarchConversionRequestV1.elevation_views`（`tarch_converter_schema.py:593`）+ `ElevationViewIntentV1`（`:546`）**契约里有**，但 **`grep elevation_views` 在 `tarch_normalize.py` 生产码零命中**——`_build_manifest`（`:1646`）只塞平面 view（`"views":[pv]`），`request.elevation_views` 从未被读。**这是 sol 自己在 P0–P2 裁决里点名的 D8 病（声明字段不参与计算），本次落在立面上。**
- 后果：sm24 gt 只有平面（8 区 + 14 外墙洞口 x 位置），**无窗高 z / 无立面 render / 无 overlay**，做不成 sm21 那样。

**sm24 DXF 事实**（主控实测）：`edge` 层 5 个视图框 = `1f平面图` + **`北立面`/`南立面`/`西立面`/`东立面`**；`E_WINDOW` 层 **49 个立面窗**。**立面是命名的** ⇒ 立面归哪面**由图名直接给**，**不需要 C2.1 的「按几何猜立面归属」匹配引擎**（那是 sm26 起、本细稿明确不做）。

**验收总标准（用户定）**：sm24 gt 做成和 `case_tests/test_baseline/gt/sm21_anchor` 一样的交付形态（gt.json + renders/ 含立面），用户检查通过即锁定为答案。

---

## 1. 细稿要交付什么（设计，不写代码）

设计「转换器命名立面处理」全链，让 v3 提取能算出窗 z + 立面 overlay/render。至少把这些**真设计点钉死**（每点给判据 + fail-closed 边界 + 必红夹具思路）：

1. **立面框几何**：`ElevationViewIntentV1` 需要哪些输入（clip box / facade_family / source 轴映射 / z 基准）？立面框本地坐标 →（沿墙 world along 位置, world z 区间）的**映射规则**。**z 基准在哪**（图里 z=0 对应楼层标高？还是窗台标注？）——这是最容易埋雷的点，要有确定性来源，禁猜。
2. **立面窗抽取**：从 `E_WINDOW` 层在每个立面框内抽窗矩形 → 每窗的（沿墙位置, z_lo, z_hi）。多实体拼一个窗怎么合并？证据不足/畸形怎么 fail-closed？
3. **立面窗 ↔ 平面洞口 链接**：按 **facade_family + 沿墙 x 位置**把立面窗链到平面洞口（转换器已产的 14 个 exterior openings）。链接判据 + 容差 + **歧义/落单 fail-closed**（一个平面窗对不上任何立面窗、或对上多个 → 阻断，不发明 z）。**内门 7 个是判卷盲区（不在 gt），立面窗里有对应的怎么处理**要说清。
4. **emit `ElevationViewBindingV1`**：查清 `gt_manifest.py:126` 的 `ElevationViewBindingV1` + `ElevationOpeningEvidenceV1`（`opening_entities`）需要哪些字段，转换器 `_build_manifest` 怎么从上面的结果构造它们，塞进 manifest `views`。
5. **下游 v3 提取立面路径**：查清 `extract_gt_v3`（`gt_extraction.py`，处理 `elevation_views` / `opening_entities` → 窗 z 那段，约 :693-720+）**现有实现是否真能吃转换器 emit 的立面绑定**——**吸取洞口挂载的教训:G9 预检 ≠ 完整提取**，细稿必须要求 e2e 验证（sm24 立面真跑通 extract_gt_v3 → 窗有 z）。若发现 v3 提取立面路径本身也有缺口（像 opening-host 那样），细稿要点出并纳入施工范围。
6. **render / overlay**：`render_gt.py` / `render_gt_overlay.py` 产 `gt_elev.png` + `overlay_{East,North,South,West}_view.png`（对齐 sm21 renders/ 那套）需要什么输入,是否现成。

## 2. 纪律 / 约束

- **fail-closed / 禁猜 / 禁伪造 z**：这是答案生成器,静默错 z 比崩溃危险。任何链接歧义/z 无确定来源 → 阻断 + 最小冲突集,不发明先验。
- **gt 铁律**：转换器不被 gate①/执行器/reading/correction import;不动 gt.json 铁律路径语义、不动 v2 legacy。
- **优先扩转换器（emit 立面绑定）+ 复用 v3 提取现有立面消费**;只有确证 v3 提取立面路径有缺口才动它,且说明。
- **范围**：只做**命名立面**（facade 由图名给）。**不做 C2.1 未命名立面匹配引擎**（sm26 起）。窗**无 z 证据时的 assumed-z 补齐也不在本细稿**（那是 C2.1「缺立面补」）——sm24 立面齐全,应能真算 z。
- **接缝**：为未来 C2.1（未命名匹配 / assumed-z）留槽,别烤死「立面必命名」到无法扩(建筑复杂度可扩展性铁律 #6)。

## 3. 交付

细稿落 `AI_agent/proposals/tarch_elevation_spec.md`（累计式自包含·标 `[S]` 采纳/`[M]` 待主控裁）。出稿后 Opus 子代理升一档对抗审 → 主控裁定 → terra 施工。
先通读:`tarch_normalize.py` 的 `_build_manifest` + S3 洞口解析、`tarch_converter_schema.py` 的 `ElevationViewIntentV1`、`gt_manifest.py` 的 `ElevationViewBindingV1`/`ElevationOpeningEvidenceV1`、`gt_extraction.py` 的立面/opening z 段、sm21 gt.json 的立面字段(windows 带什么)、DXF 立面框(可用主控 bundle `logs/experiments/2026-07-24_sm24_gt_review/` 的 source.dxf)。中文。
