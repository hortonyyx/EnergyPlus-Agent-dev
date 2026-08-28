# 跨家族复核裁决 · B4-②a（affine 数值门 + 两把结构锁，`2757cb6`）

- **日期**：2026-08-29 · **复核**：GLM 跨家族席位 · **施工**：Claude 执行档 · **基线**：`e638655`
- **题面**：`AI_agent/logs/reviews/request/2026-08-29_b4_2a_numeric_gate.md`
- **裁决**：**APPROVE-WITH-FINDINGS · 0 阻断 · 5 不阻断（+3 观察记行）**

---

## 0. 我独立复现的硬事实（全部本机实测，非转述）

| 项 | 实测 | 与主张对照 |
|---|---|---|
| 全量（`-n 6`、无 `-m`、17:06） | `3195 passed, 13 xfailed, 212 warnings`，exit 0 | ✅ 与主控权威读数逐字一致 |
| `.pth` 前后哨兵 | `58f547fa…`（两次，主树） | ✅ |
| 三份签字哈希重算 | sm25 req `d738d0ac…`、sm24 req `ae0fec08…`、sm24 man `c40cbc8b…`，均 == 存储值 == 派工单前缀 | ✅ 逐位不变 |
| `PlanFrameCertificateV1` preimage | 钉在 `tests/test_affine_space_contract.py:293`（`05a29dc3…`），本提交未碰该文件、测试在跑 | ✅ |
| `tarch_normalize.py` 字节 | `git show e638655:…` 与工作树 sha256 两算相同 = `539615ab…` | ✅ 与 commit message 所报一致 |
| 范围 | `--numstat` 六文件，逐字同派工单 | ✅ |
| 三个受影响测试文件 | `64 passed`（29.5s） | ✅ |
| 上轮 F-E 教训核验 | 两份 request 各 **8 个 `Affine1D`** 槽、`|scale|` 全 = 0.001 | ✅ 满存货属实 |

复核环境说明：工作树 HEAD = `036ab89`，它与 `2757cb6` 的 diff **只含 `AI_agent/` 文档**（`--numstat` 实测），src/tests 逐字节相同 ⇒ 工作树上跑的一切探针就是被审代码。复核全程只读，唯一写入 = 本文件。

---

## 1. 五问逐条

### 问 1 ⭐⭐「单侧自锚」的门形状 —— **采纳，形状对；但「什么都没丢」要加一个限定**

**蕴含关系我按代数推了，并实测**：单侧式绿 ⇔ `|det_req| = mpu_req²` 且 `|det_man| = 1`
（manifest 槽被钉 `source_metre→world_metre`，其预测**不消费任何 mpu**）。两式相除恰得
`|det_req| = |det_man| × mpu_req²` —— 即派工单的成对式（锚在 request 层、用 request 自己的
mpu，如派工单 §一「在 `TarchConversionRequestV1` 层加检查」所规定）。**不存在「成对红而单侧绿」
的输入**，除非把成对式改锚在 manifest 的 mpu 上且两文档 mpu 不一致——派工单从未这么规定，
且实测两份文档 mpu 相等（0.001）。反向不成立（成对绿 ⊬ 单侧绿：`|det_man|=4, |det_req|=4·mpu²`
成对绿、单侧红）⇒ **单侧严格强于被规定的成对**。

**覆盖面实测**：成对式的对照物全仓签字锚点上 **1 对**（sm24）；测试夹具
`tests/fixtures/sm24_review/bundle_07_25` 另有一对（req `m00=0.001` vs man `m00=1.0`，mpu 同
0.001——commit message「ONE fixture in the whole repository」少算了这对，小误不改结论）；
**sm25-L = 0 对（`manifest.json` 实测不存在）**。单侧式在 sm25-L 上 **10 个被检槽**、全仓 **20 个**。
按「锁的牙只跟着夹具存货走」，改单侧是对的。

**限定（= 下面 F-A2 的出处）**：单侧式只能检查「两端空间钉得出的量级」——线性部分。
**翻译分量（offset）没有空间钉死的量级，单侧式结构性不可表达**；而成对式本来可以载一条
实测成立的不变量：manifest 的 `m02/m12` 与 request **逐位相等**（`_build_manifest` 逐字照抄，
sm24 实测 `-23.0576/-26.5652` 两侧全同）。所以精确的说法是：**相对被规定的成对式什么都没丢；
相对「成对式还能扩展成什么」，丢的是 offset 一整类**。

**带 F-E 教训找新盲面**（「你我是否又只检查了一种形态」）：找到了，但都不在「成对 vs 单侧」这条轴上——
是 offset（F-A2）、同量级互换（F-A3）、第三族无数值门（F-A4）、dict 载体（观察 1）。详见问 3。

### 问 2 ⭐ 容差 `1e-9` —— **不是照结果凑的**

- **全仓 20 个被预测槽的相对偏差实测全部恰好 `0.0`**（三份签字载荷经 `model_validate` 后用
  `iter_affines` 逐槽算）。夹具对容差零敏感 ⇒ 任何 `[~1e-12, ~1e-4]` 的取值都全绿，
  `1e-9` 不是被结果逼出来的选择。
- **边界双向实测**（`m00` 相对扰动）：`1e-13` 绿、`5e-10` 绿、`1e-9` 红、`2e-9` 红、`1e-6` 红
  ——与「`1e-6` 必红」的反橡皮图章测试一致，且红绿分界确实落在声明值上。
- 余量结构成立：地板 = 双精度两三项乘积噪声 ~1e-16（7 个量级余量）；病灶最小步 = 整个 mpu
  因子 1e3/轴（≥4 个量级分离带）。中间无诚实形态占位——**唯一候选是未来的轻微各向异性标定
  （sx≠sy ⇒ det 偏差 ~1e-7 量级会被误伤）**，今天全仓无此形态（偏差全 0），记一行。

### 问 3 ⭐ 骗过新锁的真实错误形态 —— 找到 3 个不阻断 + 2 个观察（全部实测）

隔离手法说明：manifest 是签字件，直接篡改会先撞哈希。我**只中和哈希校验**
（`gt_manifest.compute_manifest_sha256 = lambda m: m.manifest_sha256`）来模拟「新鲜构建」
——正是 `_build_manifest` 回归的真实形态（先构建、后算哈希）。

**F-A2（不阻断 · 最强，与示范攻击同级危害）：offset-only 的 `/mpu` 回归漏网。**
- 对照（门是活的）：线性四项 ×1000（=除两次）⇒ **红**；×0.001（=忘除）⇒ **红**。
- 攻击：只把 `m02/m12` ×1000（偏 23 km，与被示范的 12264.66 m 同级）⇒ **绿**。
- 根因：`|det|` 对平移零敏感，且单侧式无「平移应是多少」的预测可讲。`_build_manifest` 今天
  「线性除 mpu、平移逐字照抄」（`tarch_normalize.py:2738-2741` 注释自证）——「把平移也除了」
  与「忘了除线性」是同编辑距离的回归形状，前者今天无锁。
- ⭐ 修法便宜且正好补在单侧式的短处上：**B4-②b 加一条成对 offset 相等腿**
  （实测两文档 offset 逐位相等，1 个夹具 sm24 ——存货薄但作为单侧式的补充而非主门成立）。
  派工单规定的就是 `|det|`（旋转不变），故此缺口是**题面固有**、不是施工偏差 ⇒ 不阻断。

**F-A3（不阻断）：同量级槽互换 / 剪切全绿。** sm25 plan-F1↔F2 仿射互换
（`m02` 差 55 m）绿；立面 along-affine 跨视图互换（offset 差 79 m）绿；`m01=0.5·mpu`
剪切（det 不变）绿；raster overlay0↔4 像素仿射互换（det 差 21 倍）绿（pixel 端设计上不预测）。
这是「**单位门不是几何门**」的诚实边界——两种表述（成对/单侧）都看不见，成因同 F-A2：
det 只有一个标量自由度。建议：**今后任何「affine 错误已被门住」的表述都限定为「单位/量级类」**
（防的是 12 km 级换算错，不是几何放错位）。

**F-A4（不阻断）：第三族 affine（`score_schema.Affine2DV1` / `PlanFrameCertificateV1`）没有数值门。**
`grep require_affine_magnitudes src/` ⇒ 恰好两个调用点（request 根 + manifest 根）。该族两端由
ClassVar 钉死 `reading_plan_local_metre→world_metre` ⇒ `|det|` 应恒 = 1，但无人查：
`_plan_frame`（唯一生产者）今天硬编码 `xx=yy=1.0`，若内部数值回归（或经 `model_validate` 直接造
det≠1 的证书）——生产者计数锁绿（计数仍 1）、类型门绿（声明对）、**数值零覆盖**。
⭐ 这正是 **F-E 一族之隔的同一病形：「在场、在用、无覆盖」**——F-B 派工只要求计数锁（已交付），
故不阻断；**建议 B4-②b 把 `require_affine_magnitudes` 也接进 `PlanFrameCertificateV1`**
（该族 gain=1 不需要 mpu；ClassVar 声明不进 `model_dump` ⇒ preimage 仍逐位不变，接线签名安全）。

**观察 1（记行）：`iter_affines` 不下钻 dict 载体。** 实测：dict 载 2 个 affine 发现 **0**，
list 载发现 1。今天零存货（三份签字件原始 JSON 计数 31 = 校验后触达计数 31，全部到达），
但 docstring「新槽位加上当天就被覆盖」在 `dict[str, Affine…]` 形态上不成立——那恰是
`self-consistent-gates` 一族「覆盖声明跟着我想到的载体走」的口子。加两行 dict 分支即闭。

**观察 2（记行）：`model_copy(update=…)` 绕过全部 validator 包括本门**（pydantic v2 语义）。
HC-02 测试就在用它翻 mpu（`test_tarch_converter_p1_geometry.py:455`）。`grep model_copy src/`
今天无人对 request/affine 这么用（`bind_affine_spaces` 自己的 stamp 拷贝不改数值）⇒ 现状无害；
若未来有代码经 `model_copy` 改 mpu 或 affine，门静默失效。在门 docstring 加一句警示即可。

**生产者锁的别名逃逸（归入 F-B 锁的已知边界，记行）**：`make = Affine2DV1; make(…)`
AST 计数器看不见（实测：`_construction_sites` 对该文件返回 `[]`）——但该文件文本仍点名类型，
**广度半（子串扫描 `test_only_the_declared_modules_may_name_affine2dv1`）抓得住**；只有动态构造
（`getattr`/字符串拼接）两者皆逃。防「手滑的第二生产者」这一 F-B 原始威胁模型下足够。

### 问 4 两处既有夹具改动 —— **都不是放水，一处还严格变强**

- **`test_tarch_converter_p1_geometry.py::_request`（aff 跟随 mpu）**：0.01 调用者
  （`test_s0_units_undeclared_on_scale_mismatch`）的病灶是**单位标签失配**——诊断判据实读
  `native_units + metres_per_unit + header_insunits`（`tarch_normalize.py:287-290` context 字段），
  **不读 affine** ⇒ 探针原样保留；默认调用者数值逐位不变（0.001→0.001）。
- **`test_gt_raw_layer.py::test_f111_d`（篡改字段换成 `min_room_area_m2`）**：旧探针
  （mpu→0.002）在新门下建不出来，施工方**没有静默删腿**，而是升格为显式断言
  （`pytest.raises(ValidationError, match="abs_det")`——「被拒」写进记录）；替换探针刻意选
  良构字段（3.0 是合法值）⇒ **只有哈希重算能裁决**（正是该测试「Only the recomputation
  decides」的本意），并带 no-op 防伪证（先断言篡改后哈希确实变了）。强度严格不降反升。
- 两文件**测试函数集合零增零删**（AST 对比父提交：21/21、23/23）。
- 残留一句（不阻断）：今后「mpu 在哈希预像中」不再被任何测试直接锁定（旧探针隐式锁过）；
  需要同时拆掉数值门又把 mpu 摘出预像才会失守——连锁假设，记行。

### 问 5 `pixel` 端降级 —— **显式，非静默**

三层显式：① `space_unit_metres` 对 pixel **返回 `None` 而非 1.0**，docstring 写明理由
（像素尺寸属于栅格不属于图纸，沉默不得读作单位尺度）；② `expected_affine_magnitude` 文档化
`None` = 不可预测；③ 专门测试锁住「被跳过的恰是 raster affines，且它们**真的会挂掉朴素预测**
（skip 是承重的不是装饰）」。且 bind 按槽盖章 ⇒ 非 raster 槽声明 pixel 会挂
`AffineSpaceMismatch`，**载荷无法自我豁免进 pixel 免检区**。缺口（记行）：运行时无被跳过
计数/痕迹——由 `predicted == 19`（测试）+ 本审全仓 20（含 manifest）传递性钉住，够。

---

## 2. 派工方公式写错的处置（「先知道三件事」#1）—— **处置正确**

派工单 §四.1「比值 1e6 = mpu²」的算术标签写错：实测 sm24 真货对 `det 1e-6 vs 1.0`，
**`mpu² = 1e-6`，1e6 是 `mpu⁻²`**（比值）。但 F-A 的承重前提——「同名两槽 `|det|` 相差一个由
mpu 定死的因子」——**为真**，且施工方在真货上实算并把它连同更正一起写进了 test 0 的注释。
按分层触发器（承重前提错才停、外围数值错记一行继续），这是**外围数值错**：照抄错误标签实现
才会坏门，而实现端（gain=domain_unit/codomain_unit，det 期望 gain²）与红绿实测都证明门没被带偏。
停报反而过度触发。派工单累计题错 41 → **42**。

## 3. 上轮 F-E 裁决被推翻的教训（「先知道三件事」#3）—— 我的自检

上轮我以「sm24 manifest 0 个立面视图 ⇒ 今天无碰撞对」判 F-E 潜伏，被实测推翻（每份签字
request 就有 8 个 `Affine1D` 满存货）。病根 = 把「成对」当唯一检查形态。本轮我对新形状
「单侧自锚」做的对应检查：**不再问「有没有对照物」，改问「单侧式自己声明覆盖的每种量——
线性、平移、以及每个 affine 家族——各自有没有被量到」**，逐项去实测。结果：线性 ✓（20 槽
偏差 0.0 + 双向扰动）、平移 ✗（F-A2，结构性盲）、第三族 ✗（F-A4，根本没接线）、dict 载体 ✗
（观察 1）。这四格就是「你我还没想到的盲面」的完整清单——都已按严重度归位，无一需要阻断本单。

---

## 4. 裁决

**APPROVE-WITH-FINDINGS**。

- **0 阻断**：派工单三条（F-A/F-B/F-E）都按验收条目成立；签字逐位不变；`tarch_normalize.py`
  未碰；两处夹具改动无放水；全量独立复现同读数。
- **5 条不阻断 findings**（建议编号待 orchestrator 登记）：
  - **F-A2** offset-only `/mpu` 回归漏网（门在线性半边有牙、平移半边盲）⇒ B4-②b 补成对
    offset 相等腿；
  - **F-A3** 同量级槽互换/剪切全绿 ⇒ 表述边界：这是单位门不是几何门；
  - **F-A4** `PlanFrameCertificateV1` 族无数值门（F-E 病形一族之隔）⇒ B4-②b 接线（签名安全已核）；
  - **F-A5** docstring「127 affine slots」复现不出（签字件校验后 31 / tarch 载荷 82 / 全 json 最宽
    95）；实质主张（偏差恰 0.0）复现 ⇒ 改数或注口径；
  - **F-A6** commit message「ONE fixture」少算 bundle_07_25 夹具那对（成对式实为 2 对；
    sm25 仍 0 对，改单侧的决定不受影响）。
- **3 条观察记行**：dict 载体逃逸（今天零存货，补两行分支即闭）；`model_copy(update=…)`
  绕门（src 今天无人这么用，docstring 加警示）；生产者锁别名逃逸由广度半兜底（动态构造才全逃）。
- **B4-②b 题面建议**（从本轮 findings 收口）：offset 相等腿 + `PlanFrameCertificateV1` 数值门
  + `iter_affines` dict 分支，三件都是十行内的活，可并单派。

复核方法备注：本裁决只依据派工单 + `git show 2757cb6` + 本机实测（探针脚本为一次性
heredoc、未落盘、未改工作树；唯一写入 = 本文件）。施工方自述未读。
