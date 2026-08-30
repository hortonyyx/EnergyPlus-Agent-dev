# ②-1d 返工复审裁决 · GLM 跨家族（第二次）

- **日期**：2026-08-30 · **审阅方**：GLM 家族 · **返工方**：GPT 家族 · **请求方**：orchestrator
- **送审对象** = `0cd2858` · **基线** = `8442442`（一律以 `git diff 8442442..0cd2858` 核；
  代码面仅 `answer_compiler.py` + `tests/test_boundary_condition_facts.py` + staging 脚本 + 两份 md）
- ## 裁决：**REWORK**（阻断 **1** 条 · 不阻断 **4** 条）
- ⭐ 一句话：**三条「必须红」全部如实变红、正常 sm25 如实 100/100 绿——三个例子都修好了；
  但「这类缺陷」没有修好：exclusion 分支成了一个无界豁口，上一轮 B1 的病根句
  「门在自己的主声称上被无声绕过」在两个新形态下逐字复现，且其中一个形态
  就在 sm25 现有验收语料上以 4 个「既有 NA」的身份静默通过。**

---

## 〇、环境与读数复核

- 分支 `08.23_AsDrawnReading` · HEAD `52d500d`（=发单读数）· 工作树干净 ·
  `.pth` sha256 `58f547fa…43` 内容 `/workspaces/EnergyPlus-Agent-dev`（=发单读数，自己重量）。
- 本审全程只写 `/tmp/o21d_r2/`（`git archive 0cd2858` 副本）与本裁决书；
  上轮探针目录 `/tmp/o21d_rev/` 仍在且经 sha256 确认 = `8442442` 副本（`answer_compiler.py` 两侧同哈希 `08df2557…`）。
- 新副本受影响子集实跑：**29 passed in 3.92s**（`-n 6`，exit 0）= 执行档读数 ✅。
- ⚠️ **本轮自己踩了一次串台**：探针文件放在 `/tmp/o21d_r2`、在 `/tmp/o21d_rev` 里以
  `PYTHONPATH` 跑——`sys.path[0]`=脚本目录 ⇒ **旧树里跑的其实是新代码**（输出里出现
  `zones=29/30` 新字段才暴露）。把探针拷进目标目录重跑后读数才成立。
  跑法一律：`cd <副本目录> && PYTHONPATH=<副本目录> python <副本目录>/probe.py`。

## 一、返工三条（§一）

| # | 结论 | 证据 |
|---|---|---|
| ① 旧 commit 三形态仍复现 | ✅ | `8442442` 上独立重跑：E3 `passed=True paired=96` · E4 `passed=True paired=0` · E2c `passed=True paired=100`，与上轮裁决书逐位一致 |
| ② 新 commit 三红 + 只红该红的 | ✅ | E3 恰 1 条 `facts_boundary_ring_missing:plan-F1:cavity:19ce…:converter=F1-z3`；E4 = 2 条 `empty` + 25 条逐 cavity `ring_missing`（25 = F1 11 + F2 14，4 个 exclusion 不被升级）；E2c 恰 2 条且都指向 phantom；baseline `100/100 zones=29/29 exclusions=4` |
| ③ 换同形输入仍走不通 | ⛔ **命中两条** | 见下 §二 A1 与 E2c 同族——**L 形房间丢 ring 静默**（A1）与**幻觉 zone 藏进 NA cavity 全绿**（E2c 同族），均已实测 |

复现：`cd /tmp/o21d_r2 && PYTHONPATH=/tmp/o21d_r2 python probe_r1_mutations.py /tmp/o21d_r2`（两侧树各跑一遍）。

## 二、逐攻击面结论

### A1 · 同因失效 —— ⛔ **成立，且比施工方自报的更重：不是「未来风险」，是 sm25 现在时**（见 §三 B1'）

施工方自报的原话是「如果**未来**出现『原始 cavity 仍有效、producer 与复算同因漏掉 logical ring』的共同模式，它可能被归入 exclusion」。实测三层：

1. **机制确认**：门的 ring 完整性复算 `derivable_by_cavity` 用 `derive_boundary_edges(view, min_room_area_m2=0.0)`（[`answer_compiler.py:1046`](../../../../src/agent/judge/answer_compiler.py#L1046)）——**与生产者同一个函数**。
   0.0 只抹掉了面积这一个失败维度；junction-fragment / owner≠1 型吞 ring 与面积无关 ⇒ 同因。
   端到端小世界（`probe_r3_same_cause.py`，诚实生产者 + 诚实转换器，两面 L 形搭接墙围 0.52 m 管井）：
   **24 m² 的 L 形房间**，生产 `derive(5.0)` 与门 `derive(0.0)` **同因导不出 ring** ⇒ 门记
   `EXCLUSION … reason=facts_cavity_has_no_logical_boundary_ring` ⇒ **该形态分辨力 = 0**，
   与 sm25 那 4 个「天然 NA」在观测上**完全不可区分**。
2. **sm25 活体**（本轮新读数）：被认领的 3 个 exclusion cavity 面积 = **88.27 / 28.68 / 70.34 m²**
   （全部 ≫ 5 m² 生产阈值；未认领的 no-ring cavity 全是 0.058 m² 墙垛碎屑），边界贴墙率
   **400/400、401/401、400/400 采样点全部距墙带 ≤ 4 cm**——它们是**被墙完全围合的真实空间**，
   「天然 NA、本就无 ring 可导」的辩解不成立。⇒ **「够大且围合却导不出 ring」不是零真实存货，
   它正在本批验收语料上发生，并被层契约 §5.2 记为「既有 NA cavity」静默放行。**
   （上轮裁决书转述的「4 个既有 NA cavity」同样是未量过的口径——上轮我未量其面积/贴墙率，责任在我。）
3. **反向假红并存**：管井腔 0.27 m² < 5.0 阈值 ⇒ 生产者按设计不落 ring，门用 0.0 重导后**要求它落**
   ⇒ `facts_boundary_ring_missing` 红（probe_r3 同一次运行实测）。即重导阈值**既不等于生产阈值、
   也不独立于生产者**：设计行为被判红，同因丢失被判绿——而常态化的假红会掩护真正的静默。

⇒ A1 请求书的问法（「同因失效时还剩什么分辨力」）**问对了**，但「未来才出现」的框定错了——
正确的问法是：**「exclusion 集合里的每一个，你拿得出『它天然导不出 ring』的独立证据吗」**
——一个都拿不出，判据与生产者同函数。

### A2 · 验收 3「真实路径」锁量的是什么 —— **✅ 锁真实有效，但它量的是上游量**（不阻断，N1'）

扰动扫描（`probe_r4_spike.py`，sm25 真实数据，顶点 `[50000,40000]` 上移）：
**0.5 / 1.0 / 2.0 / 5.0 m 四档全部红，红项集合完全一致**：
`facts_boundary_footprint_unusable` + `facts_boundary_edges_empty:plan-F1` + 14×`not_unique` + 14×`unclaimed`。

- ① 红的是**新断言**（`unusable` 的 try/except 分支 + `empty` 非空断言），`paired=56` 前后不变 ⇒ 不是逐边对账红的 ✅。
- ② 0.5 m 就红、与 2/5 m 红在同一条断言 ✅。
- ③ **它红的是「footprint 变了」**：0.5 m 起多边形即自相交 invalid ⇒ 边消失只是下游。
  这条锁是「footprint 有效性检测器」，不是「丢边检测器」；**footprint 仍有效时的丢边（A1 形态）不在其覆盖内**。
  层契约 §5.1 的表述（「覆盖的是生产路径把整层 boundary edges 静默清空后门必须红」）与实测一致，没有冒充 ✅。

### A3 · N4 接线 —— **✅ 成立且响亮**（不阻断，N2'）

- 接线位置：`build_sm25_facts_staging.py` 的 `main()`，在 `write_facts_candidate` **之前**
  `reconcile_boundary_basis(...).assert_consistent()` ⇒ 失败抛 `BoundaryBasisMismatchError`、脚本崩溃、
  **三件套不落盘**——是崩溃不是 diagnostic ✅。
- 双保险成立：CI 锁（`test_boundary_condition_facts.py`）经 `read_facts_for_compilation` 读的
  **就是 staged trio** ⇒ 即使有人绕过 producer 手改 staged 数据，锁也红。
- 边界：producer 是 **sm25 专用一次性脚本**（ANCHOR 与 5 个 DXF 句柄硬编码）；sm24/未来语料
  没有对应接线（层契约 §5.3 只写了 sm25 这一处）。登记即可。

### A4 · 验收 3b 诚实度 —— **① ✅ 合成如实标注；② ⛔ 命中，但比「零存货未登记」更重**（并入 B1'）

- ① multi-exterior 分支：层契约 §5.1 明写「零真实存货」「⛔ 该夹具不是、也不得被描述成真实语料覆盖」；
  锁名/docstring/契约三处一致 ✅。
- ② 「还有没有别的分支零存货没登记」——**问对方向，但正确类别不是「零存货」而是
  「有存货且存货的定性错了」**：exclusion 分支在 sm25 上有 4 条真实存货，被定性为「既有 NA cavity」，
  实测是 88.27/28.68/70.34 m²、边界 100% 贴墙的围合空间（见 A1-2）。**比零存货更危险：
  零存货是「没行使过」，这里是「行使了且读数被误读」。**

### A5 · 禁令核对 —— **✅ 独立复核成立**

- `git show --name-only 0cd2858` = 5 文件（层契约 md / staging 脚本 / 执行档 md / `answer_compiler.py` /
  `test_boundary_condition_facts.py`）⇒ ① 答案根 `case_tests/test_baseline/gt/` **零条目** ✅
  ② o22m1 孤儿归档在 `90e0429`（本单之前），`0cd2858` 本身没碰任何并行席位的东西 ✅。
- 验收 5 复核：`git diff 8442442..0cd2858 -- src tests` 只有 `answer_compiler.py`（+123）与
  `test_boundary_condition_facts.py`（+139）⇒ `tarch_normalize.py` / `as_measured.py` 整文件零 diff，
  两列判据锚点未动 ✅（与主控读数一致）。
- 五把新锁名全部在 diff 中亲见 ✅（不必重复主控）。

---

## 三、Findings

### 阻断（1 条）

**B1' · exclusion 分支是无界豁口：「cavity ∉ derive(0.0) 重导」一律视为天然 NA——判据与生产者同因、
无面积合理性、无一 cavity 多 zone 唯一性 ⇒ 门的主声称「converter zones 全有去向（29/29）」
是一个可被污染的虚假完整性读数。** 三个已实测的穿透：

1. **E3 同形·真实成因**：L 形房间（两面 L 形搭接墙围管井的楼层）上生产者与门重导同因吞 ring ⇒
   exclusion 静默（`probe_r3_same_cause.py`：`EXCLUSION F1-z-east … facts_cavity_has_no_logical_boundary_ring`）。
   合成变异（手删 stored ring）红了；**上一轮裁决书点名的真实成因（probe4 形态）在修后依然走不通**。
2. **E2c 同形·真实藏身处**：幻觉 zone 不平移 50 m，而是塞进 z4/z5 **共用的 NA cavity** ⇒
   `passed=True, paired=100, zones=30/30`，幻觉被具名 exclusion 吸收（实测，脚本见复现命令）。
   50 m 外的真空红了，「导不出 ring 的大 cavity」这个**更容易的藏身处**开着——且现成容器有 3 个。
3. **sm25 现存货被误读**：88.27 / 28.68 / 70.34 m²、边界 100% 贴墙的三个围合空间正以
   「既有 NA cavity」身份静默通过验收。它们与「真实缺陷导致的导不出」在门的观测里是同一个值。

返工要求（**仍纯门侧，⛔ 不许改任何一列的值**），以下每个变异**必须红**、正常 sm25 的合法存量仍须有合法出口：
① 幻觉 zone 塞进 z4/z5 共用 NA cavity ⇒ 红（E2c 同族第三条「必须红」）；
② 诚实小世界（`probe_r3` 夹具或等价 L 形房间 + 如实转换器）不得静默绿——至少：
   **cavity 面积 ≥ `request.min_room_area_m2` 而进 exclusion 的，必须红或要求带独立证据的显式登记**
   （⚠️ 这条会让 sm25 现有 3 个 exclusion 自己变红——**先核清它们的真实性质再定登记口径**，
   ⛔ 不许把断言阈值调到恰好容纳现状了事）；
③ 层契约 §5.2 把这 3 个 cavity 的实测性质（面积、贴墙率）写清，⛔ 不得再以「既有 NA cavity」一笔带过。
复现（探针已留档）：
`cd /tmp/o21d_r2 && PYTHONPATH=/tmp/o21d_r2 python probe_r3_same_cause.py`（形态 1+反向假红）·
`… python probe_r5_halluc_in_na.py`（形态 2，幻觉进共用 NA cavity）·
面积/贴墙率读数见 §二 A1-2（heredoc 已随探针目录留档）。⚠️ 修 B1' 时须同步对齐
0.0 vs 生产阈值的语义（见 N3'），否则②会与管井假红纠缠。

### 不阻断（4 条）

- **N1'（A2）**：验收 3 真实锁量的是「footprint unusable ⇒ 整层清空」上游量；0.5–5 m 全档同断言红。
  锁本身有效且契约表述如实，但**不是丢边检测器**；与 B1' 同根，B1' 修复覆盖「footprint 仍有效的丢边」后此条自然收口。
- **N2'（A3）**：N4 接线成立（producer 写盘前崩溃式 assert + CI 锁读 staged trio 双保险）；
  但 producer 是 sm25 专用一次性脚本，**未来语料的 staging producer 需自带同款接线**——层契约登记一句即可。
- **N3'（假红方向）**：门重导 `min_room_area_m2=0.0` ≠ 生产 `request.min_room_area_m2` ⇒ 对生产者
  **按设计**丢弃的 <5 m² 腔体报 `ring_missing`（probe_r3 管井实测）。fail-loud 不危险，但真实管井语料上
  会成常态噪音并掩护通道甲；随 B1' 一并对齐语义（per-case 传入生产阈值，或对 < 阈值腔体走另一条具名通道）。
- **N4'（N1–N5 处置核对）**：N1（四档落库存货如实化）✅ · N2（5_000 待签、未发明新数）✅ ·
  N3（列举式锁登记）✅ · N4（staging 接线）✅ · N5（未新增静默出口）✅——执行档 §四逐条属实。
  唯一遗漏是 B1'（exclusion 本身），施工方在 §八自报了它但把它框成「未来风险」。

---

## 四、攻击面勘误（请求书邀请的第 ⑧ 次）

- **A1 问对了，框错了时态**：「如果未来出现……可能被归入 exclusion」⇒ 实测不是未来，sm25 现在就有 3 个活体。
  正确问法：**「exclusion 集合里的每一个，拿得出『天然导不出 ring』的独立证据吗」**。
- **A4② 的类别要挪半步**：比「零存货未登记」更危险的类别是**「有存货且存货被误读」**
  （multi-exterior 是前者，exclusion 是后者）。登记口径不能只扫「零存货分支」。

## 五、两份请求书的并集对账（⚠️ 点名一条缝）

本单 = ②-1d 返工（reconcile 门）；模块 1 = as-drawn 生产者类型。**缝里有一块两份都没派**：
`derive_boundary_edges` 为什么吞掉 88 m² 围合空间的 ring（junction-fragment / owner 判定的生产侧根因）——
本单禁改 `as_measured.py`，模块 1 改的是生产者类型不是 derive。⇒ 建议主控把
「derive 在 sm25 上吞掉 3 个大面积围合空间的 ring」**登记为事实层已观测缺陷**（F 编号归主控），
否则它还会被下一轮「既有 NA」口径吞掉。B1' 返工本身仍纯门侧，不依赖生产侧先修。

## 六、给主控的一句话

三条必须红如实变红、失败半径如实收敛、禁令与诚实度全部过关——施工质量不差，两个新穿透里
有一个还是施工方自己点名的方向。唯一阻断与上一轮同根：**门把「导不出 ring」的判据交还给生产者本人**，
于是「NA 容器」成了无限容量的静默面——合成变异打不进去的地方（共用 cavity、L 形房间），
恰是真实语料今天的形态。返工仍纯门侧、量小；但②会先让 sm25 的 3 个「既有 NA」现出原形，
这是特性不是副作用，别让施工方用调阈值把它压回去。
