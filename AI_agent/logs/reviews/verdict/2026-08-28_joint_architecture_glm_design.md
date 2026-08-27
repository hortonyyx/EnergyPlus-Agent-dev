# GLM 共同出案 · ReferenceFactsV1 / AnswerCompiler 四题 + 对题面的攻击

- **日期** 2026-08-28 · **出稿** GLM（共同作者席位，⛔ 非审阅）· **题面** [`../../reviews/request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md` §十](../request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md)
- **只读过没动树**；未 commit；未跑全量；未 pip install。
- **核了什么**：10.2 的 A/B/C/D **四条全部实核**（命令级复现见 §1），外加 7 条题面没写的实测发现。
- **一句话总主张**：四道题里 **Q12 的选项框架被实测数据直接推翻**（现行 gt 本身就是逐边混合基准的产物，「整层 profile」与「逐边 basis」不在一根轴上）；**Q11 比 Q12 更急**（静默 1000× 无门可见 vs 形态错会被判分红）；**Q10 的机制仓里已经跑着**（G1 三明治，照抄+补盲点即可）；**Q13 的关键是拆锚**不是加门。

---

## §1 读数复核（A/B/C/D 全核 + 加码发现）

### A｜✅ 复核成立（签字 request 里有尺子的签字锚）

`case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json` 实测：六个 raster（2 平面 + 4 立面）**全部**带 `pixel_to_source_m`，**每个恰 3 条 `calibration_controls`**，全部锚 DXF entity handle + role（`footprint_sw` / `datum_lo`…），与 manifest 侧值**逐位相同**（`m00=0.02163887614351203` 两侧一致）。F-115 的更正成立。

### B｜✅ 复核成立，⭐ 但题面**说轻了**——陷阱在同文件内部，不只跨文件

| 来源 | `plan-F1` 的 `world_from_source_m.m00` | `m02` |
|---|---|---|
| 签字 request（`PlanViewIntentV1`） | **0.001**（= `metres_per_unit`，吃 **native** 坐标） | 30.469 |
| manifest（2026-08-20 review_bundle，`PlanViewBindingV1`） | **1.0**（吃 **source-metre**） | 30.469 |

- 机制在 [`tarch_normalize.py:2741`](../../../../src/agent/judge/tarch_normalize.py#L2741) 显式 `affine.m00 / mpu`，`:2732-2739` 注释写明两个域。两处字段**同名同类型 `Affine2D`**。
- ⭐⭐ **加码发现 B-1（题面没有）**：我用 controls 实测了 `pixel_to_source_m` 的输出域 ——
  `affine(pixel_point)` = `dxf_native × 0.001`，即输出 **source-metre**（例：`(281.85,1234.92) → (-30.469, 28.214)` = native `(-30469.0, 28213.6)` ×0.001，三个 controls 全对上）。
  ⇒ **`pixel_to_source_m` 的输出与 manifest 的仿射（×1.0）配套，与它自己所在 request 文件里的 `world_from_source_m`（吃 native、×0.001）域不匹配**。
  字段名链 `pixel_to_source_m → world_from_source_m` 读起来完美连续（source_m → source → world），**恰好就是错 1000× 的那条路**。题面说「只有『从哪份文件读到就用哪份』的消费者会静默错」——错；**拿同一份签字文件内部最自然的字段链接力，就是 1000×**。
- ⭐ **加码发现 B-2**：manifest 的 `raster_overlays` **没有 `calibration_controls`**（实测 keys 仅 5 个）——锚只活在 request 里。这本身没错（request 才是信任根），但意味着「任何锚在 controls 上的门」必须读 request，不能读 manifest。

### C｜✅ 复核成立，⭐ 但「口径」与 B 的「陷阱」是两件相邻而不同的事

[`denominator.py:107-121`](../../../../src/agent/judge/as_drawn/denominator.py#L107) 逐字确认：吃签字 DXF + 签字 request，注释「用 request 自己的 source→world 仿射，⛔ 别乘 metres_per_unit 然后祈祷」。
⚠️ 它之所以对，是因为它喂给仿射的 `geo.wall_lines` 是 **native 域**坐标 —— 这条口径防的是「**你拿着 native 坐标、自己手乘 mpu**」；B 防的是「**仿射本身有两个域**」。两个都真，但 C 的样板抄不回 B 的场景：将来任何消费者拿到的坐标若是 source-metre 域（例如从 raster 链下来的），「用 request 自己的仿射」反而就是错 1000×。**C 是「喂对口粮」，B 是「仿射有两条血统」——混同这两条，就会把 C 的注释当成 B 已有解。**

### D｜✅ 复核成立，⭐ 且拿到 Q12 的决定性实弹

`gt/sm25-L_anchor/review/conversion_report.json`：29 zone / 136 边，逐边 `basis` 全非空，分布 **`wall_axis` 90 · `outer_skin` 46**，逐边携带 `p1/p2/thickness_m/offset_m/thickness_evidence/source_handles` —— 与题面一致。
⭐⭐⭐ **加码发现 D-1（本轮最重要的一条实测）**：**29/29 个 zone 全部是逐边混合 basis**（纯 basis 的 zone = 0；例：`F1-z0` 的边序 `wall_axis, wall_axis, outer_skin, …`）。
⇒ **现行唯一保留的出模形式「外墙外包 + 内墙中轴」，在数据上是逐边属性，不是层属性。**
⭐ **加码发现 D-2**：29 个 zone 的 `role` **全部 `'unspecified'`** —— 「这条边是外墙还是内墙」目前**只能从 basis 反推**，而 basis 是转换器判定后的产物。Q12 任何「角色→基准」规则的第一输入，现在没有独立列（见 §2 Q12 与 §3-6）。

### 补充核

- `deterministic.py:924-925`：`authoritative_envelope is None → return geom` —— 静默不做投影的通道现役存在（banner ③-3 属实）。
- `gt_raw_layer.py:43-76`：复现门已实现「指纹先查、提前返回」+ `implementation_drift` / `content_mismatch` 两红分离 + 已声明 4 文件指纹盲点（`gt_extraction.py` 等，漂移会被误归因成 content_mismatch）。
- 10.1 表「像素空间判别实验通过 ⇒ 两侧一起换单位即可」——见 §3-7：那个「单位」与 B 的「单位」不是一个东西。

---

## §2 对 Q10–Q13 的答案

### Q10｜信任根链：「不签字、只靠可复现」够不够？

**主张：够，但题面把立信机制说弱了 —— 立信的不是「可复现」这个性质，而是 G1 已经落地的三明治：① 输入签字（已有）＋ ② 派生实现指纹（先查、提前返回）＋ ③ 内容重算比对。ReferenceFactsV1 不签字、但必须携带指纹并照抄这套门。**

「答案变了 vs 实现漂移分不分得开」—— **在 gt 侧已经分开了**（`implementation_drift` vs `content_mismatch`，`gt_raw_layer.py:43-54` 逐字写着「fingerprint check runs FIRST and returns early, so a drifted tree can never be reported as a suspect artefact」）。ReferenceFactsV1 的答案链同构：

| 变化 | 指纹 | 内容 | 归因 |
|---|---|---|---|
| 实现换了（F-110 本批常态） | 变 | 变 | `implementation_drift` =「树动了」的正确红，不重签 |
| 实现没换但盘上 facts 被动过 | 同 | 异 | `content_mismatch` = 产物可疑 |
| 输入重签（gt 修正批） | — | — | 走 request 晋升流程，facts 整份重新派生 |

**四个必须补的件**（不做就是题面担心的「没有立信能力」）：
1. **指纹组精确到派生闭包**，⛔ 不继承 gt_raw_layer 已声明的 4 文件盲点（`gt_extraction.py`/`gt_manifest.py`/`gt_schema.py`/`tarch_converter_schema.py` 恰恰是本批主战场 —— 盲点+主战场重叠 = 归因错误成常态）。
2. **facts 永远纯派生、无人工通道，写死**。人工修订只走 request 的 `TarchOverrideV1`（形态已有）。一旦有人能直接改 facts，复现立信整个失效 —— 这是「不签字」能成立的唯一前提。
3. **facts schema 加语义版本**，答案键 = `(case, facts_version, profile)` 三元组。指纹二分覆盖不了「同一 profile 名在 v1/v2 facts 上指不同东西」的语义漂移；成绩记录不带 facts_version 一定会串台。
4. **派生器确定性要重测**（PYTHONHASHSEED / dict 序 / 浮点）：G1 实测过 tarch_normalize 对 hash seed 免疫，但 ReferenceFactsV1 的编译器是新代码 —— 同指纹跑两次出两个 facts 的话，`content_mismatch` 会哭狼。

**它在什么情况下是错的**：
- 若未来出现「facts 需要人工微调而不能重派生」的正当场景（如 DXF 本身矛盾、转换器无解），复现立信失效，那时必须回到给 facts 逐版签字 —— 我的方案靠「把这类场景全部推回 request overrides」挡住，挡不住（出现 override 表达不了的修订）时我的主张作废。
- 若指纹组永远画不准（Python import closure 漂移），`implementation_drift` 退化成「经常红但说不清谁动了」→ 狼来了 → 真 content_mismatch 被当 drift 放过。**门的红必须携带具体指纹 diff**（哪个文件、旧 hash→新 hash），让人 10 秒分得清 —— 这个 UX 不做，三明治名存实亡。

### Q11｜B 那条 1000× 怎么根治？

**主张：三层，但权重与题面倾向相反 —— 改名（让拿错的行为当场崩）＞ 数据自带域 ＞ 门（唯一覆盖 JSON 边界的那层）；phantom type 只当进程内的便宜第一道，不指望。**

1. **改名 + 域进数据（根治层）**：
   - request 侧 `world_from_native_m`，manifest 侧 `world_from_source_metre_m` —— 同名陷阱的直接根除。改名的价值不是可读性，是**让存量错误代码 AttributeError 而不是静默算错**（「从哪份文件读就用哪份」靠人小心的时代结束）。
   - `Affine2D` 加必填 `source_unit: Literal["native", "source_m"]`（B-1 证明：域不随文件走、随值走 —— raster 链与 plan 链在同一文件里域不同）。
   - ⚠️ 项目特有的代价要点名：改字段名 ⇒ 已签 manifest 内容变 ⇒ 全部 gt 复现门红。这是「树动了」的正确红（同 F-110），但要走 `manifest_version` 1→2，旧件按旧版验，且要让用户预先知道这不是回归。
2. **门（跨进程/跨文件唯一真防线，题面问的就是这段）**：**域一致性对账门，锚在 controls 的物理事实上** —— 取 request 的 `calibration_controls`（entity handle → dxf 原生坐标，`request_sha256` 绑定），对任何 pixel→world 完整链，用**消费者实际要用的那条仿射链**把 `pixel_point` 推到 world，与独立直算（`dxf_native → ×metres_per_unit 的世界换算`）对账，**硬上限 = 数值噪声级（1e-6 m 量级），不是领域容差**。
   - 这条门锚在签字输入的物理坐标上，不锚任何产物自报 ⇒ 它不是「自己重算自己的谎」（Q13 的判据提前用上）。
   - 实测可行性：我已用 B-1 的数据手验 —— 若误把 request 仿射接在 raster 链后，对账残差 ~30 m 量级（平移项的二阶），立红，无容差博弈空间。
   - 落点：所有 pixel→world 消费统一过一个 helper，门挂在 helper 里 —— 不枚举消费者，枚举必然漏。
   - 配套：`controls.dxf 坐标 ↔ 签字 DXF 实体坐标重取`的一致性也要进同一条门（controls 是「锚」的凭据，凭据本身没人验的话锚可以是谎的 —— 这是我没把握的第 2 条，见 §4）。
3. **类型层**：`NewType("WorldFromNative", Affine2D)` 之类的进程内防线可做，但如题面自曝，JSON 边界看不见 —— **不要把根治寄托在它身上**。

**它在什么情况下是错的**：
- 改名会一次性打断所有现役消费者（包括我还不知道的脚本/测试）。若存在「读这个字段」的隐藏消费者面（仓外脚本、历史实验档），改名成本比预估大 —— 但按「崩好过静默错」的口径，崩出来正是收益，除非崩在**跑成绩的当口**。
- 若 sm21/sm24 的 request 是旧 schema 无 `source_unit`，门对旧件只能 `not_attempted`（显式），不能静默绿 —— 旧件覆盖面为零时这道门在过渡期是纸的。

### Q12｜逐边 basis 与整层 profile 怎么共存？（⭐ 本轮我对题面攻击最重的一题）

**主张：选 (c)，并且 (a)/(b) 的共同前提 ——「profile 与逐边 basis 是同一层上的竞争者」—— 被 D-1 的实测直接推翻：29/29 zone 本来就是逐边混合 basis 的，「外墙外包+内墙中轴」这个唯一保留的出模形式就是逐边混合的产物。二者不在一根轴上：**

- **逐边 `basis` = 测量事实**（这条边是从外皮面线量的还是从墙轴线量的）。归 `ReferenceFactsV1`，是被引用的证据，⛔ 不是出模参数。
- **profile = 折叠规则**（角色→输出基准的映射），作用于事实之上：
  - `exterior` = {外墙边→outer_skin，内墙边→wall_axis}（= 现行 gt 形态，**名字叫 exterior 但内墙并不 exterior** —— 这个命名要在设计文档里拆穿，否则每个新读者都会重新误解一次）；
  - `axis` = {所有边→wall_axis}；
  - 新出模形式 = 新映射，不是新管线（合不变量 #6 的接缝要求）。
- **AnswerCompiler 输出基准 = profile(边角色, 边 basis 事实)，纯函数**。profile 要求的基准在某条边上无事实支撑时（`exterior` 下的内墙边没有外皮面），fallback **写进 profile 定义**（内墙恒 wall_axis），⛔ 不留给编译器猜、也不 skip。
- **banner「投影必须是整层事务」的正确落法 = 失败整层，不是基准整层**：任何一条边因证据不足无法定输出基准 ⇒ **整层 `unprojectable`**（整份 NA、响亮），⛔ 不许「这条边跳过、其余照出」。这与「每条边可以有不同基准」毫不冲突。**Q12 题面把「整层」从『失败模式』滑读成了『基准选择』，才造出 (a)/(b) 两难** —— envelope.py:520 防的是 x 轴 accepted / y 轴 skipped 的**静默半成品**，从来没有说基准必须整层统一。

**为什么不选 (a)/(b)（各自的真害）**：
- (a)「整层统一基准重投影」：统一 outer_skin ⇒ 内墙没有外皮面，要么伪造第二张面（题面 §三 亲自毙过的伪造）要么 NA；统一 wall_axis ⇒ 产不出现行 gt 形态、外墙系统性小 t。**且「覆盖逐边 basis」= 把 136 条边里量出来的事实扔掉 —— 与 R-6「量了、用掉了、存盘时扔了」同形**（gt 转换器扔过一次厚度，这里要再扔一次基准）。
- (b)「尊重逐边 basis、profile 只挑边参与」：profile 退化成过滤器 ⇒ 出模形式又变回「facts 里恰好有什么就出什么」—— banner ③-3 点名要死的形态（「出模形式是读图证据涌现出来的」）；且「哪些边参与」一旦可逐边跳，静默半成品从 x/y 轴搬到了墙边轴。

**R-3 连问的回答：不消失、也不藏 —— 记账。**「内墙中轴+外墙外包」在拐角的错位是这个出模形式的**定义性几何后果**（gt 对 gt 它是 0；gt 自己就是这个形态）。两条面线都在的 as-drawn 事实让错位量**第一次可精确计算**：拐角两侧基准不同 ⇒ 衔接位移 = 两基准之差。修法不是消灭而是写进 banner ④ 已有的**不规整事实表**：每处基准跳变记 `{边对, 位移量, 方向}`，门做**双向对账**（产物里每个台阶都在表里 × 表里每个台阶都在产物里），锚在 facts 顶点，⛔ 不锚产物自报。Z 形/退台「一堵墙跨内外角色变化」正是这个记账的一等场景。
（对照：选 (a) 是把 R-3 **藏进统一基准**里 —— 台阶没了是因为整层换了尺子，错位变成全楼系统性 t 偏差，判分对 gt 时反而大面积红 —— 藏 = 更响的错。）

**它在什么情况下是错的**：
- **角色列缺失是本方案现役软肋**（D-2：role 全 unspecified，只能从 basis 反推，basis 是判定产物，判定错则 profile 无从纠正且无独立门可见）。方案依赖「facts 新增显式边角色列 + 判定证据」—— 这不是题面 10.2-D 说的纯接线活，是新测量判定。若用户裁定「不要新增判定、就以 basis 为准」，我的折叠规则退化成 (b) 的一个特例，R-3 记账的「角色跳变」信号也就没了来源。
- 「失败整层」在 136 边规模上偏脆（一条烂边打掉整层成绩 —— invalidation-blast-radius 老坑）。我坚持整层（出模形式是起跑前选定的成绩口径，半成品成绩比没有更有害），但必须给诊断模式留合法出口：编译器可另产 per-edge 状态表供人看，⛔ 它不进成绩。**这条不写进设计文档，压力下一定会有人把 NA 悄悄改成 skip。**
- 「外墙边」判定边界我没逐边审（转角 return 边、jamb 边算哪类）—— 见 §4-1。

### Q13｜metamorphic 门怎么写才不是「自己重算自己的谎」？

**总原则（从 band_collapse 与「阈值≠重算」两次翻车提炼）：metamorphic 门验的是『实现不骗』，不是『事实正确』。它的一切锚必须来自被验证对象之外（签字输入或物理事实）；锚里只要有一项来自被验证对象自身，那条门就退化成重算自洽 —— 产物可以一边撒谎一边全绿。落地动作是『拆锚』，不是『加门』。**

逐条审 banner 三条（题面问「各自锚在谁给的坐标/孔径上、有没有哪条是产物报多宽就算多宽」——答案是：**三条按 banner 的笼统写法全都可能堕落成那样，必须按下述拆开**）：

**门1「两投影只差声明的 t/2」——三个锚必须拆开，每个单独指定来源：**
- `t` 锚 **facts 的 `thickness_evidence`**（有 `proof_handles` 回溯签字 DXF）。⛔ 若实现成「读产物自报 thickness 再验差值=自报值/2」= 100% 报多宽算多宽（band_collapse 同形）。
- **位移边集合**锚 **facts 的外墙边集合**（编译器与产物都不许参与定义）。
- 断言**逐边**：`|P_exterior(e) − P_axis(e)| = thickness_facts(e)`，方向 = 边法向。⛔ 聚合均值会被正负抵消骗过。
- ⚠️ 覆盖边界必须写明：两个投影都出自同一编译器，此门验编译器自洽，**不覆盖 facts 本身错**（转换器量错 t 时两投影一起错、门1 全绿）。它挡不住 facts 撒谎 —— 与「EP 0 Severe ≠ 物理对」同类的误用陷阱，要印在门的 docstring 上。

**门2「往返可恢复」——单独存在时牙最小，是三条里最可能成为仪式的：**
- 结构性盲区：偏移方向做反（+t/2 写成 −t/2）的实现，往、返**两次同错负负得正**，照样恢复 ⇒ 方向错误对它不可见。它只防量化/舍入不可逆。
- 有牙的写法：往返的两个位移用**声明的**仿射（`P_ext = shift(P_axis, +t/2·n̂)` 且 `P_axis = shift(P_ext, −t/2·n̂)`），⛔ 不是「跑两遍编译器、比较相等」——后者连浮点噪声都抓不住。
- 本质上门2 是门1 的推论（门1 带方向断言时门2 几乎冗余）——保留它的理由只剩「抓数值路径上的不可逆」，**别把它当独立防线宣传**。

**门3「缺资料整份 unprojectable」——唯一锚在输入存在性上的，最像真门，但有两个堕落形态：**
- 「缺不缺」⛔ 不能由编译器自判（「我不缺」= 自证）。判据来自 facts 的显式缺失字段（逐边 `thickness_evidence` 缺失 / 逐轴 envelope skipped），且缺失本身要独立可观测。
- 只有正向断言 = 接没接上不可观测（恒绿结构）。**必须带分辨力夹具三件套**：真缺 thickness 的 fixture ⇒ NA；全的 ⇒ 出答案；**只缺一条边的 ⇒ 整层 NA**（第三件同时验 Q12 的整层性 —— 一件夹具验两道设计）。
- **补一条 banner 没列的一致性门**：unprojectable 的层，产物里**不许有任何已投影坐标漏出**（「这层 NA 但窗户有坐标」= 红）。`deterministic.py:924` 那个 `return geom` 的静默路径就是这类漏出的现役通道 —— 门3 不带检漏，半成品从正门拦住了还会从窗户进。

**它在什么情况下是错的**：
- 逐边硬等式在存档量化（QUANT=4，0.1 mm）下有舍入残差，需要 1e-4 m 量级数值上限 —— 但这个上限是**存档精度的噪声带**，不是领域容差，docstring 里要写明依据，否则又立一个没人签字的阈值（silent-default-threshold 前科）。
- 非正交墙（未来 case）下「边法向」与 t/2 位移方向的关系未验证（见 §4-4）；profile 将来多于两个时，门1 要写成「投影−基准定义」的通用式，否则每个新 profile 手搓一对门。

---

## §3 对题面的攻击（前提哪里站不住 / 清单漏了什么路）

1. ⭐⭐⭐ **Q12 的 (a)/(b) 选项清单犯了本项目登记过的老病，且能被一份现成产物推翻**：两选项共享的前提「profile 与逐边 basis 同层竞争」被 D-1 直接证伪（29/29 zone 混合 basis；现行 gt 形态只能由逐边基准产出）。虽给了 (c) 出口，但 (a)/(b) 的措辞把「profile=投影参数」框死，把搜索空间锚在错框架里。正确框架：**basis=事实、profile=折叠规则、整层性约束失败模式**。
2. ⭐⭐ **10.2-B 把陷阱范围说窄了**：「只有跨文件消费者会静默错」→ 实测**同文件字段链就是陷阱**（B-1：`pixel_to_source_m` 输出 source-metre，与同文件 `world_from_source_m`（吃 native）域不匹配，名字上接得最顺的链恰好错 1000×）。这改变 Q11 修法：只改两份文件的两处字段名不够，同文件内的域标注与整链对账门才是主防线。
3. ⭐ **A 与 B 被当成两条并列事实，实为一条**：F-115 修正后的结论「真问题只是消费者指错了文件」仍是文件层归因 —— 消费者之所以会指错，根因就是同名两域（B）。当两条并列修，会修出「把 consumer 指对文件」的补丁而漏掉「域不进数据 ⇒ 每个未来消费者重蹈」的结构病。
4. ⭐ **Q10 的「不签字、靠可复现」把仓里已落地的机制说弱了**：立信≠「可复现」三个字，= G1 三明治（输入签字+指纹先查+内容重算）。题面的担忧（答案变了 vs 实现漂移分不开）在现役机制下已有解，真正要设计的是指纹组精确性与「facts 无人工通道」的写死（§2 Q10）。
5. ⭐ **Q13 引 banner 三条门时没拆锚**：「两投影只差声明的 t/2」一句话里藏三个不同来源的锚（t / 位移边集合 / 方向断言）。前两次翻车的共同病理都是锚滑进产物自报 —— 不拆开写，第三次翻车只是时间问题。拆锚比加门重要。
6. ⭐ **10.2-D 的「不缺测量、不缺人工标注、不缺 schema」有一处不实**：缺「边的内/外角色」这一列（D-2：role 全 unspecified）。Q12 任何折叠规则的第一输入现在没有独立来源 —— 这是新增判定+证据，不是接线活。题面把它归入「缺的只是谁把它落进事实包」会低估工作量与设计含量。
7. ⭐ **优先级排序我认为反了**：题面把 Q12 标为「最容易埋雷」。我的排序 **Q11 ≥ Q13 > Q12 > Q10**：Q12 错了是形态错，判分对 gt 会响亮红（看得见、纠得回）；Q11 错了是 1000× 静默错且无任何门（看不见），且正踩在 ②-1「两个表示一起换单位」的必经动作上 —— **10.1 表「判别实验通过 ⇒ 两侧一起换单位即可」里那个「单位」是产物自报标定，B 的「单位」是判分侧仿射的输入域，不是一个东西**；判别实验验证了尺子不随产物标定动，没验证尺子自己换单位不引雷。带着 10.1 的成功结论去做 ②-1，会在 B 上踩得更实。
8. （轻）**题面 §十开头说「四条硬事实直接决定 ②-1 怎么设计」**——但四条里 A/C/D 都是「可行侧」证据，只有 B 是「危险侧」；②-1 的设计约束应当从 B 反推（先定域机制，再定换单位动作），而不是从 A/C/D 正推（先定流程，把 B 当路上要绕的一颗雷）。次序不同，产物结构不同。

---

## §4 我自己最没把握的地方（供 sol 当靶子）

1. **Q12 折叠规则的角色二分边界没逐边审**：「外墙边=outer_skin、内墙=wall_axis」来自对现行 gt 的逆向；46 条 outer_skin 的构成（转角 return 边、洞口 jamb 边、厚度突变 joint 边各算哪类）我只抽样了 controls 的 3 个点，没做 136 边逐边角色审计。若存在「外墙边但量的是轴线」的合法混合，折叠规则要加第三类。
2. **Q11 对账门的锚本身可能没人验**：controls 的 `source_point_dxf` 与签字 DXF 实体坐标的一致性，当前没有任何门在验（request_sha256 绑的是 request 文件整体，不是「controls 写的坐标=DXF 里的坐标」）。我把它加进对账门（controls↔DXF 实体重取），但依赖 ezdxf 按 handle 重取的稳定性 —— sm21/sm24 两份老 DXF 我没实测。若重取不稳，锚的这一层要降级为「签字时人工核过一次」。
3. **Q10 的狼来了风险没解**：F-110 期间复现门常红 + ReferenceFactsV1 的门也常红 ⇒「红=树动了」成为背景噪声后，真 `content_mismatch` 被习惯性放过的概率有多大，我没有数据。我提的红必须带指纹 diff 是直觉方，不是被验证过的 UX。
4. **非正交/斜墙下 Q13 门1 的「方向=边法向」断言**：sm25 全正交，L 形转角处两端边正交但衔接边的 t/2 位移方向与「法向」的关系我没推导；若需要特判，「放宽」正是门退化的起点 —— 这条我给不出既严格又不假红的断言式，是四题里唯一我没有完整答案的技术点。
5. **我对 10.2-D「banner 已定死 conversion_report 不是原始层」的接受**：我全盘采信了「签字 DXF+签字 request 才是原始层」这个前提并据此设计 —— 若这个前提本身错（例如 request 里某些事实其实来自 conversion_report 的回填），我的 Q10 信任根链整体上移一层，全部答案的根部要重审。sol 若要攻，从这里下手最省力。

---

## 附：本稿的复核命令（sol 可直接重放）

```bash
# B：两份文件的同名仿射
python3 -c "
import json
req=json.load(open('case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json'))
print([ (p['id'],p['world_from_source_m']['m00'],p['world_from_source_m']['m02']) for p in req['plan_views']])
m=json.load(open('AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json'))
print([ (v['id'],v['world_from_source_m']['m00'],v['world_from_source_m']['m02']) for v in m['views'] if v.get('kind')=='plan'])"
# B-1：pixel_to_source_m 的输出域 = native × mpu
python3 -c "
import json
req=json.load(open('case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json'))
ro=[r for r in req['raster_overlays'] if r['id']=='raster_plan-F1'][0]; a=ro['pixel_to_source_m']
for c in ro['calibration_controls']:
    px=c['pixel_point']; out=[a['m00']*px[0]+a['m01']*px[1]+a['m02'], a['m10']*px[0]+a['m11']*px[1]+a['m12']]
    print(out, [v*0.001 for v in c['source_point_dxf']])"
# D-1/D-2：逐边 basis 混合 + role 全空
python3 -c "
import json
cr=json.load(open('case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json'))
print(sum(1 for z in cr['zones'] if len({e['basis'] for e in z['edges']})>1), '/', len(cr['zones']))
print({z['role'] for z in cr['zones']})"
```
