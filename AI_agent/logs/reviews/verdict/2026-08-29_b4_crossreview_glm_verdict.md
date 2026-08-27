# 跨家族复核裁决 · B4-① affine 两端空间合同

- **日期**：2026-08-29 · **复核方**：GLM（跨家族）· **施工方**：Claude 执行档 · **被审 commit**：`dc8821b`（分支 `08.23_AsDrawnReading`）
- **依据**：原派工单 + `git show dc8821b` + 本席位独立跑出的输出（未读施工方自述）
- **裁决**：**APPROVE-WITH-FINDINGS — 0 阻断 / 5 不阻断**

---

## 〇、总读数（全部本席位独立复现）

| 项 | 读数 |
|---|---|
| 权威全量（`python -m pytest -n 6`，无 `-m`） | **`3167 passed, 13 xfailed, 212 warnings in 980.80s` · `PYTEST_EXIT=0`** |
| `.pth` 前后哨兵 | `58f547fa…` 两次同值，内容 = `/workspaces/EnergyPlus-Agent-dev`（主树） |
| 算术 | 3167 − **21**（新文件单跑 `21 passed in 11.49s`）= 3146，与派工方事实清单一致 |
| 签字哈希（盘上 = 重算，逐位相同） | sm25 request `d738d0ac230f21ae…` · sm24 request `ae0fec087ef2a048…` · sm24 manifest `c40cbc8bb566e4d8…` |
| 反空转（不 pop 的摘要，走真代码路径） | sm25 request `8d844bc6d5d4ece0…` · sm24 manifest `8a69ac33af7c4f98…` · sm24 request `9b8aa61ff092…` —— 三者均 ≠ 签字值 ⇒ strip 承重 |
| 存量 | sm25 仅 request、sm24 request+manifest、sm21 两样皆无（`ls gt_sources/{sm25-L,sm24,sm21}_anchor/`）——与 §三 更正版一致 |
| 范围 | `git diff --numstat dc8821b~1 dc8821b` = 256/52/14/24+1/35/310 六文件，与事实清单逐字相同；§〇 禁区（tarch_normalize.py、标定门、F-129、事实层、整数坐标）零触碰 |
| 四个字段位接线 | `tarch_converter_schema.py:706`（dxf_native→world）`:782`（pixel→source_metre）+ `gt_manifest.py:152`（source_metre→world）`:207`（pixel→source_metre），全部经 `bind_affine_spaces` |

复核全程零工作树写入（变异测试经 pytest 插件在内存打补丁，插件与日志在 `/tmp/b4_review/`，不触树）；全量跑测期间未修改任何文件。

---

## 一、五问逐答

### 问 1 ⭐⭐ `Affine2DV1` 类属性、不上线 —— **决定成立，今天的事实面全部核实为真；但「第二生产者出现」那一刻没有任何锁会红**

- **「唯一生产者」实测为真**：`Affine2DV1(` 全仓唯一构造点 = `reading_typed_adapter.py:241`（`_plan_frame` 内）；`_plan_frame` 唯一调用点 `:451`；`apply_affine_2d` 三个消费点（`:543/:544/:585`）全部喂 `frame.affine`；`score_schema.py:629` 只读平移分量（空间无关）。
- **「10 份 score_vs_gt.json」实测为真**：`grep -rl transform_sha256 case_tests --include=score_vs_gt.json | wc -l` = **10**。类属性不进 `model_dump` ⇒ `preimage_sha256` 逐位不动（锁 `test_affine2dv1_spaces_stay_off_the_wire` 钉死字面值 `05a29dc3…`，绿）。
- **但将来第二个生产者会静默拿错两端、零锁变红**（内存演示，不改树）：
  ```python
  foreign = Affine2DV1(xx=0.01, xy=0.0, x0=0.0, yx=0.0, yy=0.01, y0=0.0)  # 真实语义 pixel→world
  apply_affine_2d(foreign, (137.0, 902.0))   # -> (1.37, 9.02)，静默接受
  ```
  类属性仍宣称 `reading_plan_local_metre→world_metre`，三把相关锁全绿。⇒ 见 **F-B**（不阻断：配套「生产者计数结构锁」或届时改 wire 字段，登记即可）。

### 问 2 反空转 —— **成立，已抽验**
用 pytest 插件把 `REQUEST_VERSIONS_WITHOUT_SPACE_BINDING` / `MANIFEST_VERSIONS_WITHOUT_SPACE_BINDING` 在内存里置空（等价于「没加 pop」），21 条中 **12 红**，含三个哈希锁，且断言读数即上表三个 unstripped 摘要（sm25 `8d844bc6…` 与施工方报的前缀吻合）。manifest 侧另有一层：`GtExtractionManifestV1` 模型内自检哈希，strip 失效时**加载即红**。

### 问 3 ⭐ 找到一种真实骗锁形态 —— **「剥掉声明的裸系数换槽」：全绿通过，Δ=12264.7 m**（= F-A，本轮最重要发现）

派工单指名的真货对（sm24 同名 `world_from_source_m`，request `m00=0.001` vs manifest `m00=1.0`、平移逐字节相同、`mpu=0.001`）——把 manifest 那份**剥掉 `domain_space/codomain_space`** 后塞进 request 的 native 槽：

```python
bare = {k: v for k, v in manifest_affine.model_dump(mode="json").items()
        if k not in ("domain_space", "codomain_space")}
payload["plan_views"][i]["world_from_source_m"] = bare
TarchConversionRequestV1.model_validate(payload)     # -> 通过，无任何报错
affine_spaces(intent2.world_from_source_m)           # -> ('dxf_native', 'world_metre')  ← 按槽位盖章
# clip 角点：correct=(-10.78, -7.76)  attacked=(12253.88, 18775.57)  Δx=12264.7 m
```

三个槽位同形全过：request 平面槽（如上）、manifest 平面槽（子模型 `PlanViewBindingV1.model_validate`，`m00=0.001` 被盖成 `source_metre→world`）、request overlay 槽（`m00×1000=21.64` 被盖成 `pixel→source_metre`）。**对照**：同一换法只要**保留声明**，两把锁立刻红（`requires source_metre -> world_metre but the affine declares dxf_native -> world_metre`）⇒ **牙只随声明走，盖章按槽位、内容盲**。且这不是合成场景：迁移期签字件本身就不带声明（这正是 strip 存在的原因），`tarch_normalize._build_manifest:2741` 今天构造的仍是**裸 `Affine2D`**。详见 F-A。

### 问 4 13/4/1 自评 —— **两族锁的牙经内存变异实测，分类与实测相符**
（说明：未读施工方自述，「⭐ 今天这个 payload 静默通过」具体指哪条无从对号，以下用变异矩阵替代，覆盖面更强。）

| 变异（内存插件，不改树） | 结果 |
|---|---|
| M1+M2 strip 打哑（两排除集合置空） | **12 红 / 9 绿**（三个哈希锁、两个反空转锁、tripwire、manifest 加载链、bind 直测等全红） |
| M3 bind 打哑（**两个父模块都打**——影子模块教训） | **7 红 / 14 绿**（两个换槽拒绝、compose 两把、a2dv1 参与、1000x、bind 直测） |
| 未变异 | **21 passed** |

两族正交：M3 下三个哈希锁保持绿（无盖章⇒无 space 键⇒strip 空转），M1+M2 下牙族多数因依赖声明而红——各自有牙、互不顶替。两变异并集 14 条红过、7 条两变异下均绿（inventory / 灾难量级文档 / undeclared / half-declared / a2dv1-declares / off-wire / apply-transforms——不变量与健全性锁，与其「非判据」类定位一致）。

### 问 5 换同形输入 —— **2-D 覆盖面内成立；立面（Affine1D）确实仍走不通（施工方自报属实）**
- sm25 request：6 个 `RasterOverlayIntentV3.pixel_to_source_m` 全部盖章 `pixel→source_metre`；同形攻击（裸 1000× 系数）静默通过（F-A 第三槽）。
- manifest 侧 `RasterOverlayBindingV1` 有校验器，但 sm24 manifest **0 个** raster binding——无签字真货可撞。
- **换槽必须红**的唯一同形验证只可能在 sm24（唯一 request+manifest 双件锚点）成立——已成立（问 3 对照）。
- **立面 `Affine1D` 同病未治**：类型 = `source_axis/scale/offset` + 仅 `scale≠0` 校验（`gt_manifest.py:76-85`），四个字段位（`gt_manifest.py:168/169`、`tarch_converter_schema.py:717-718/746-747`）零空间标注，唯一校验是两轴不共线。潜伏态：sm24 manifest **0 个**立面视图、request 侧 4 个（`scale=±0.001=mpu`，实测）⇒ 今天没有签字的两侧碰撞对；哪天 manifest 签了立面，1000× 碰撞即成真。⇒ F-E。

---

## 二、§一两条派工方题错的复核

1. **v4 fail-open：实质属实，计数差一。** `tarch_normalize.py` 中 `request_version` 共 **6 处**（`!= 3` 早退 @`2562-2563` 即 `_validate_raster_intents` 开头 + `== 3` 门 @`2792/2895/3138/3272/3504`），非复核单所写 7 处。外围数值错，记行不阻断。**替代方案（排除集合 + tripwire）判为够用**：模拟给 Literal 加 `4` 而不动集合 ⇒ 子集断言变 False（红）；残余 = 「顺手把 4 也加进排除集合」能让 tripwire 复绿而空间仍未进签名——tripwire 强迫的是**触碰**而非**决定**，可接受（真正的绑签归 B4-②）。
2. **字段位更正属实**：四个位置（`world_from_source_m`×2 + `pixel_to_source_m`×2），manifest 侧在 `PlanViewBindingV1`；四者均已接线（上表）。施工方按更正后的现实完成，无遗漏位。

---

## 三、§四施工方新报两条的判定

1. **成立（两个实质半句都实测）**：`converter_sha256()` = `sha256(tarch_normalize.py 自己的字节)`（`tarch_normalize.py:798-800`）。内存翻转 `_converter_sha256_now`（等价改一个注释字符：`539615ab…`→`ee77c15f…`）⇒ `test_gt_raw_layer.py` **恰好 5 红**（a2/a3/r2/r4/r5）——「5 条」计数逐字对上；而本单改的 `tarch_converter_schema.py`（62,549 B）与 `gt_manifest.py`（15,330 B）**不在指纹内**（构造上不可能进）。⇒ **F-D（不阻断）**：单文件指纹是**既有设计**（本 commit 未动它），空间合同的宿主文件对溯源指纹不可见；建议与 B4-② 重签一并加宽。
   - 顺带（范围外、先在、零测试触达）：真 `gt/sm24_anchor` 晋升件在当前树上 `verify_raw_layer_reproduction` 返回 `implementation_drift`（converter+vg 双漂）；`tarch_normalize.py` 哈希在 `5a8fb2c/6ae582a/dc8821b` 三点相同（`539615ab…`）⇒ 漂移**先于本 commit 存在**，与本单无关。
2. **成立**：见问 5 / F-E，`Affine1D` 零空间标注、潜伏态。

---

## 四、Findings

### F-A（不阻断 · 本轮最重要 · 问 3 的答案）盖章按槽位、内容盲；裸系数进错槽全绿，原始病灶现场未接检查
**缺陷陈述**：空间合同的牙只作用于「已带声明的对象」；一切以裸系数进入的路径（签字件 JSON、payload 拷贝、`Affine2D(**六浮点)` 构造）由槽位盖章，无任何数值交叉校验。`tarch_normalize.py` 全文 `require_affine_spaces`/`affine_spaces(` **零调用**（7+ 个消费点裸读字段名），`_build_manifest:2732-2744` 仍是「散文注释 + 手工 `/mpu`」且产出裸 `Affine2D`——算术回归（多除/漏除 `mpu`）会静默通过；唯「对象直换」（`manifest_affine = affine`）现在会被 binding 拒绝（本 commit 的真实增益）。
**可复现**：上文问 3 三段脚本（request 平面槽 Δ=12264.7 m；manifest 平面槽 `m00=0.001` 盖成 `source_metre`；overlay 槽 `m00=21.64` 盖成 `pixel→source_metre`）；`grep -n "require_affine_spaces" src/agent/judge/tarch_normalize.py` → 0 行。
**为何不阻断**：派工单 R1/R2/R3（声明式合同、compose 响亮失败、保签字）全部交付且实测有牙；数值校验从未在派工范围；docstring 的迁移告白（「保护代码路径、不保护签字产物」）方向诚实，只是未写明「按槽位盖章」这一限界。
**建议**（登记 B4-②，非返工）：在 `TarchConversionRequestV1` 层加数值一致性检查——同名两槽的 `|det|` 相差 `mpu²`（sm24/sm25 = 1e6 倍），旋转不变、五行代码、不进任何签名 payload；可同时捕获裸系数换槽与 `/mpu` 算术回归两形态。

### F-B（不阻断 · 问 1）`Affine2DV1` 类属性决定今天成立，但「唯一生产者」不变量无 tripwire
第二生产者出现 ⇒ 静默拿错两端、零锁红（上文内存演示）。建议：加一把「构造点计数 = 1」的结构锁（仓内有先例），或在出现第二生产者的同一 PR 里改成 wire 字段。

### F-C（不阻断 · §一.1）tripwire 的牙是「强迫触碰」不是「强迫决定」
模拟加 `4` 只动 Literal ⇒ 红；同时把 `4` 加进排除集合 ⇒ 复绿而空间仍未进签名。本单范围内可接受（v4 根本未引入，绑签归 B4-②）；B4-② 动手时须把「新版本必须带空间进签名或显式声明不进」写成机制而非集合成员。

### F-D（不阻断 · §四.1）converter 指纹单文件覆盖
实测见 §三.1。既有设计，本 commit 未使之变差；建议 B4-② 重签时把 `tarch_converter_schema.py`/`gt_manifest.py` 纳入实现指纹（转换行为确实依赖它们）。

### F-E（不阻断 · §四.2 / 问 5）`Affine1D` 同病未治、当前潜伏
四个字段位零标注；sm24 manifest 无立面真货故今天无签字碰撞对。施工方自报属实、派工单未列（R1 只点名 `Affine2D`+`Affine2DV1`）。登记 B4-②。

---

## 五、验收对照（派工单 §三）

1. **签字不变（最硬）**：✅ 三份盘上=重算逐位相同（§〇 表）；「三份」经存量核实为 sm25 request + sm24 request + sm24 manifest，sm21 无件已在测试与文档中说明。
2. **类型门有牙（真货夹具）**：✅ 换槽用 sm24 真对、保留声明即红（两方向都验）；变异 M3 下 7 红证明牙来自本改动。
3. **`Affine2DV1` 已覆盖**：✅ 类属性参与 `affine_spaces`/`compose_affine`/`apply_affine_2d`，`apply_affine_2d` 拒绝外来仿射（`test_affine2dv1_participates`，M3 下红）。
4. **逐把锁**：✅ 以变异矩阵替代口述（问 4 表）。
5. **全量**：✅ `3167 passed, 13 xfailed` · exit 0 · `-n 6` 无 `-m` · 汇总行原文见 §〇；`.pth` 哨兵 `58f547fa…` 前后同值。
6. **范围**：✅ 六文件 numstat 与事实清单一致，禁区零触碰。

**裁决：APPROVE-WITH-FINDINGS（0 阻断 / 5 不阻断）。** F-A 是本轮方法论上最值钱的一条——「牙齿随声明走」这个限界应当进 B4-② 的题面，而不是等它咬人。
