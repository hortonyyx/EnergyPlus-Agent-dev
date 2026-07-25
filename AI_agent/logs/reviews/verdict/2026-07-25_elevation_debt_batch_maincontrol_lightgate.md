# 2026-07-25 立面批「六笔债」— 主控轻门记录

主控：Opus 5（Claude 侧）｜施工：Claude 侧 Opus 执行档子代理｜跨家族对抗审：GLM-5.2（另出裁决书）
基线：`e13efd3`（1556 passed / 10 xfailed）
轻门 = **独立全量复跑 + 亲核关键 diff + 独立验真交付物（量化）+ 目检**，**不含亲手修**（发现问题一律打回施工方）。

> **边界说明（2026-07-25 主控自订正）**：必红自查表的 **neuter 复现**本轮**不由主控亲手做**——① 协作规约把「探针 / 实验执行」列为实质改动、一律派执行档，主控亲手 neuter 属越界；② 该复验已作为**命脉专项 X-01** 写进 GLM 核验清单（抽 6 格逐格复现，任一格失败即 REWORK），由**跨家族**审阅方做才是真正的独立验证，主控自做既越界又与之重复。本记录**不声称**主控复验过自查表。

---

## 1. 独立全量复跑（三轮，均由主控自己跑，非采信施工方报数）

| 轮次 | 对应状态 | 结果 |
|---|---|---|
| r1 | 首轮交付 | `1577 passed, 10 xfailed`（与施工方报数逐字一致） |
| r2 | FIX-1 + FIX-2 后 | `1578 passed, 10 xfailed` |
| r3 | FIX-3 后（最终） | `1579 passed, 10 xfailed` |

零 failed、xfail 数全程不变（10）、相对基线 **+23 测试、零回归**。

## 2. 亲核 diff（逐处读实现，非只看简报）

- **WI-1 §6.5 postcheck**：确认 `_run_g9_v3_preflight` 改为**返回** `extract_gt_v3` 的文档（原先丢弃），`_verify_pairing_consistency` 按 generated handle 反查、比 view/opening/kind/z/refs 基数，`tarch_elevation_pairing_drift` 死码接线。z 容差 `1e-9` 的论证成立（mm 量化步长下方约 6 个数量级、浮点噪声上方约 6 个数量级，两侧都留足）。`_converter_elevation_z` 被审计行与门**共用**——人核看到的数就是门比较的数，这是本条的要点。
- **真 bug（施工方在做 §9.3 时发现并修）**：原 `_v3_elevation_records` 只校验 `floor_datums[0]`，**第二个 datum 是死输入**；两个 datum 推出不同 offset 时第一个静默获胜。已改为逐个校验、任一不合即 BLOCK。合同 §9.3 明列该变异，属真缺口。
- **WI-4 墙厚证据链**：`_outer_skin_thickness_m` 只取 `basis == outer_skin` 的边，要求**每条都带厚度证据且值全体一致**，否则返回 `None`；extractor 只**搬运** manifest 声明值、不量不兜底。实测 12 条外墙边全 240mm 全带 `wall_cap_or_opening_jamb` 证据 ⇒ 0.24。fail-closed 方向正确。
- **渲染层**：`_pixel_for_world_plan` / `_pixel_for_world_elevation` / affine 系数**逐字未改**（diff 中只有调用点）；改动全在 draw-only 与合成层。`DIM` 与 legacy `overlay_plan`/`overlay_elev` 未动，v3 走独立的灰度基底。
- **R-01 sm21 基线锁**：读实现确认是**真锁**——重新生成 sm21 六张 legacy overlay，与 committed 基线**逐像素**比较（`(fresh != reference).any(-1).sum() == 0`）。

## 3. 主控独立验真（不采信施工方数字，自己量）

- **校准根因**（详 `logs/experiments/2026-07-25_overlay_diag/DIAGNOSIS.md`）：07-24 平面控制点各向异性 **1.92%**（等比截图物理不可能）⇒ 判定为受信人工输入错误，**与 GT 无关**；GT 对图纸自带尺寸链（10000/20000/4180/1640/8060/4940/2940/4060）**逐项精确吻合**，8 区精确铺满 200.00 m²。
- **修复后对齐**（在交付图上量 GT 框边 vs 原图窗框墨迹中心线）：

  | 立面 | 命中 | 最大偏差 |
  |---|---|---|
  | South | 4/4 | 1.0 px |
  | East | 6/6 | 1.0 px |
  | North | 4/4 | 0.5 px |
  | West | 10/10 | 1.5 px |

  平面 footprint 四边残差 3.5 px → **0**，各向异性 1.92% → 0.121%。
- **镜像风险收窄**：North/East/West 三面窗位不对称，手性若反则窗会整体镜像、偏差为百像素量级——实测 ≤1.5 px ⇒ **三面可判定无镜像**。South 严格对称且两窗窗高相同（均 1.0–2.8），即便手性反，产出 GT **完全相同** ⇒ 该面残余风险在 sm24 上无实际后果。**人核剩余项因此收窄为：四条地面基准线 + 8 区房间用途。**
- **审计表独立 join**：14 行 × 18 字段；`opening_id` 与 GT `openings[]` **双向一致、无重复**；逐行 `z_interval` 与 GT 逐位相同（≤1e-9）、`host_zone_id` ∈ 8 区且等于 GT 值、`kind` 一致；表头 `candidate_gt_sha256` 与 `gt.json` 的 `content_sha256` **相等**（表绑它所描述的那份 GT）。host 分布 z0:2 z1:2 z2:1 z3:4 z4:2 z5:1 z6:1 z7:1 = 14；3 门 11 窗；z 取值恰 {[0.2,2.6], [1.0,2.8], [1.0,3.4]}。
- **review-index**：inventory 覆盖 **10 个文件**（gt.json + 7 图 + 审计表 + 房间用途注记），算法显式写进 index 自身。用户签的是整包，无游离件。

## 4. 主控打回的两条（施工方均已修 + 加锁）

- **FIX-1（轻门首轮抓）**：交付图上 **z4 无标签**。根因 = 标签锚点用 bbox 西北角，对 L 形 z4 该点落在 z5 内，且逐区交替绘制导致被 z5 填充覆盖 ⇒ 8 区只有 7 个有标签。**用户签的正是「8 区房间归属」，少一间即该人核门失效。** 修法 = polylabel 锚点（含 `contains` 校验、质心亦被证不安全）+ 两遍绘制（先全部填充、后统一标签）+ 3 条 neuter 自证 + 「渲染两次抑制标签求差」证明标签像素活到最终合成图（z4 331 px，此前 0）。
- **FIX-3（轻门二轮抓，主控判 MAJOR）**：审计表比 07-24 版**少三个字段**——`opening_id`、`plan_world_along_interval`（两者均为合同 §7.4 [S] **明文要求**）、`host_zone_id`。合同把逐 opening 表定为整面镜像残余风险的**强制 backstop**、明写「不是可省略的辅助信息」；缺 plan 侧区间则 §7.4.2 要求的人核动作**物理上做不了**，缺 opening_id 则表与 overlay **对不上号**（两套句柄空间）。修法 = 新增 `P2ConversionResult.elevation_document` 持有 G9 真实提取的 GT，审计行按 §6.5 同一条 generated-handle 链 join，字段取自权威文档而非二次推导；5 条 neuter 含**错误 join key** 一格（证明锁绑的是「join 正确」而非「字段存在」）。施工方并自查出第二处未被主控标出的退化（审计表原有 `{candidate_gt_sha256, manifest_sha256, rows}` 自绑定信封被降成裸列表）一并修复。

## 5. 主控裁定 / 登记

- **z5 房间用途裁定 `corridor`**（原 `lobby`）：z5 是 8 顶点 C 形中央交通空间（33.54 m²、含东入口），几何主体为交通；主控派工单中「z5 是南侧带门厅的小间」一句**为主控笔误**（该描述实指 z4）。施工方按 ID 施加、不自行改语义并把矛盾登记在案的处置正确。**最终以用户签字为准。**
- **登记跟进债（本批不修）**：
  1. **bundle hash 跨 run 不可复现**——`ezdxf` 每次保存写入新 `$TDUPDATE/$TDCREATE` 时间戳与 `$FINGERPRINTGUID/$VERSIONGUID`，经 augmented DXF 字节 → manifest hash → GT `content_sha256` 传导。后果：签字绑定的 GT **无法由重跑复现**（可验证性仍在：拿晋升后的文件重算 inventory hash 对签名即可；失去的是「从源图重新推导出同一份」）。修法草案（钉死时间戳/GUID，或改用 GT canonical 内容 hash 作绑定根）另开一批。
  2. **§9.2 frame/title 六格必红夹具未做**（施工方诚实交接）。且其中至少两格**是缺门不是缺锁**：`frame_entity_handle` 现仅检查存在性（`frame is None`）、不校验几何/bbox，「bbox 相同但 handle 指向第二框」无门可抓；「entity 跨 frame 边」未见校验。下批按**「先补门、再补锁」**立项。
  3. **07-24 交付物无法由仓库代码复现**（治理发现）：该批 overlay 的逐 opening 标注、审计表三字段、review-index inventory 算法**均只存在于未入库的本地改动**中。这解释了主控 07-24 逆向不出该 inventory hash。本批已把三者正式实现进 committed 代码。**纪律含义：交付物必须由 committed 代码可复现，否则等于该 [S] 项只存在于图里。**

## 6. 轻门结论

**通过，可进入跨家族对抗审。** 命脉（必红锁真绑、fail-closed 未放松、投影数学未动、sm21 基线逐像素不变）与交付物（对齐 ≤1.5 px、审计表可 join、整包绑定）均经主控独立验真。剩余风险交 GLM 照 `request/2026-07-25_elevation_debt_batch_glm_checklist.md` 逐条独立复验，重点 X-01（抽 6 格 neuter 复现，任一格失败即 REWORK）。
