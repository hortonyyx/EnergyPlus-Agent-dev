# B4a 细稿 r1 交叉审判词（Fable 最高档，2026-07-14）

**对象**：`AI_agent/proposals/c2_b4a_detail_spec.md` v1（sol 次高档出稿，1387 行）。
**审向**：GPT 侧稿 → Claude 侧最高档审（谁写谁不批）。
**方法**：全文逐节精读 + 几何声明手工复算 + 盘上实码/资产六项机械事实核查（记录见文末）。

## 总裁决：APPROVE-WITH-CHANGES

**severity 计数**：BLOCKER 0 · MAJOR 1 · MINOR 1 · NIT 2。零架构级 finding；改动均为有界文字修订，v2 并入后即可放行分 Phase 施工。

## 逐条 findings

### B4A-F1 —— MAJOR：loader 的语义校验层次与容差来源未定，profile 演进会引爆存量资产

§6.2 说 loader 对 "JSON decode、schema、semantic、hash 错误均 fail closed"，但 `load_gt_document`/`load_gt_file` 签名不收任何 tolerance/config 参数；`validate_gt_v3` 却要求显式 `tolerances`，且 §7.2.1 要求 "generator 内 tolerance 与实际调用的 profile 逐字段完全相等"。§7.2.5 已写 Vg 重算用"存档 tolerance"，但 loader 侧仍有三种自然读法：
(a) loader 全量语义校验、容差取 `doc.generator.tolerances`（自包含）；
(b) loader 现场解析 judge_gt.yaml/correction.yaml 当前 profile 再校验——**将来 profile v2 一出，所有存量 verified GT 的 §7.2.1 相等断言全炸**，被迫资产级重生成；
(c) loader 只做结构+hash，语义校验全留给显式调用方。
今天 configs 静止、三种实现全测试全绿，分歧只在未来 profile bump 时爆——正是细稿审要拆的雷。
**要求**：v2 明确写死——① 两个 loader 各自跑哪几层校验；② 语义层（含 Vg 重算）一律使用 `doc.generator.tolerances`（自包含，存量资产跨 profile 演进自验证）；③ "与实际调用 profile 逐字段相等"的断言只发生在 build 时（`extract_gt_v3` 末段自检传入当轮 resolved profile），load 路径不与"当前仓库 config"比对。

### B4A-F2 —— MINOR：GT visible_intervals 与生产 Vg 同源的循环性须显式登记进 §15.1

§10.5/§7.2.5 用与生产侧完全相同的 `vg_for_direction` 派生并重验 GT 边界段——GT 的可见区间"真值"定义上就是 Vg 的输出。judge 拿它对账时只能抓输入（footprint/画法）漂移，抓不到 Vg 自身的 bug。缓解已在稿内（human overlay 四项签收 §15.2、`vg_implementation_sha256` 溯源），此设计本身合理（可见性是派生几何非观察证据）。
**要求**：在 §15.1 的 B4b 稳定输入清单里加一行显式声明：visible intervals 是 Vg 派生量、非独立观察真值，B4b 为可见性类 claim 设计判分政策时不得把它当独立证据源；独立性由 verified 门的人工 overlay 签收提供。

### B4A-F3 —— NIT：§5.1 `WorldInterval = {"lo": ..., "hi": ...}` 伪记法

会被误读成又一个 model 定义。改为指向 §5.2 的 `GtWorldIntervalV3` 即可。

### B4A-F4 —— NIT：§10.7 "唯一一个 floor interval" 措辞

改为"z 必须恰好落入该 view 声明楼层集中**一个**楼层的竖向区间（跨层即 fail），该楼层即 evidence floor"，消除"view 只许声明一层"的误读（多层 full elevation 是合法态）。

## review-ask R1–R5 裁决（主控）

| ID | 裁决 |
|---|---|
| R1 | **采纳稿建议**：B4a 不搬 `sm21_anchor/source.dxf`；迁移到 `gt_sources/` 另开 data-only 资产批，**不留兼容 symlink**；该批上排工表时用户可见。 |
| R2 | **采纳**：0.400m 冻结为 profile v1 候选门限；sm25/26 实图到盘后按 review 出 profile v2 调整，禁 CLI 临时 override。 |
| R3 | **采纳**：B4a 不自动量测指北针角度；manifest 数值 + human overlay。实图若需自动量测另提小批（带角容差 + A0 登记）。 |
| R4 | **采纳**：维持 fail-closed 只接图形导出稿——与既有 CAD→gt 判定（天正对象需图形导出）一致。 |
| R5 | **采纳**：loader 只 dual-read 盘上 v2/v3；缺版本/v1 fail-closed。历史 checkout 如需支持先收录原字节 fixture 另审。 |

## 事实核查记录（主控亲核，全过）

1. **sm21 v2 资产形状 vs LegacyV2 模型**：顶层 17 键（含 10 个下划线元数据键）、floor/zone/window-group/opening/door 字段逐一吻合；`schema_version` 为 JSON 整数 2。
2. **v2 语义强断言可满足**：两层 zone 面积和均 = 120.0 = W×D，逐对矩形零重叠 ⇒ 精确铺满（无缝无叠），§6.1 tiling 校验不会炸真实资产。
3. **前置门符号全在盘**：`facade_visibility.vg_for_direction`/`VisibilityTolerances`、`footprint.footprint_fingerprint`、`config.load_core_tolerances` 均存在。
4. **容差静态关系成立**：correction.yaml 实值 `facade_visibility_{depth,endpoint}_epsilon_m = 1e-9` << 0.001 node-join。
5. **同构声明成立**：correction `FacadeSegment` 十字段是 `GtBoundarySegmentV3` 的严格子集（GT 多 boundary_loop_id/plural keys/wall_thickness/source_refs），B4b 可无损适配调 Va。
6. **API/CLI 现状声明属实**：`gt.py` 的 DEFAULT_GT_DIR/gt_path/case_gt_dir/has_gt/load_gt 与稿一致；`render_gt.py` 现 CLI = positional gt + `--out-dir`；§14.6 引用的既有回归测试文件全部存在（`test_gt_schema.py` 为标注新增）。
7. **合成夹具几何声明手工复算成立**：L 案 6 边 CCW、N/E 各双深度且投影仅端点相接（全可见）；U 案南 notch 底 depth=3 可见、notch 两侧边 E/W 完全隐藏——与 §12.2/§12.3 声明逐条一致。

## 正向确认（登记留痕）

- 累计式自包含达标：wire 全字段、签名、算法、错误码、测试矩阵、Phase 切分全部在稿内。
- gt 铁律与依赖方向正确（judge 可 import correction 公开纯函数，反向永禁；discipline scan §14.4 锁）。
- 可扩展性铁律达标：per-floor footprint/holes/多 elevation view 槽位全预留、C2 profile fail-closed 显式错误码，无烤死假设。
- 不自动提升 + 三类 protected roots + candidate 水印 + human_verified 联合门（§15.2）设计完整。
- 零 golden/资产扰动、合成先行、`north_axis_deg` 严格沿用 E4 语义（`(-sinθ, cosθ)` 手核正确）。
