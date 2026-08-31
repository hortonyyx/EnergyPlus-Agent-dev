# 执行档 · ②-2 模块 3：`correction/evidence_adapters.py`（legacy / as-drawn 双 adapter）

- **日期**：2026-08-31 · **施工方**：GLM 家族（headless 席位）· **审**：GPT 家族（待派）
- **派工单**：[`../request/2026-08-31_o22m3_evidence_adapters_dispatch.md`](../request/2026-08-31_o22m3_evidence_adapters_dispatch.md)
- **基线**：`31f873d` · **口径**：设计稿 [`../verdict/2026-08-30_o22_evidence_contract_gpt_design.md`](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  §4.1/§4.2/§4.3/§5.2/§5.2.1/§8.3/§9.1 第 3 步
- **交付物**：`src/agent/correction/evidence_adapters.py`（新，约 470 行）、
  `tests/test_o22m3_evidence_adapters.py`（新，21 条测试）。
  ⛔ 未提交；⛔ 未动 `vector_contract.py` / `pipeline.py` / `judge/` / 任何既有文件与既有测试。

---

## 〇、一句话交付

**两个生产 adapter（吃冻结 bytes、返回已过不变量 1–8 的 bundle artifact）+ 模块 2 留下的
pin 的模块 3 一半接掉 + 模块 2 自报最薄弱处（present 无载荷）在构造面关闭。**
三条设计稿明令全部以机械方式落地：每面恰一处置（构造 + 共牙校验）、legacy basis 只认结构化
`geometry.basis`（note 一个字不读）、候选图只走全量解引用、**零自造配对**。

## ⛔ 一、停报项（§四「必停」触发）：验收 4 的归属错位，请主控裁决

**验收 4 的字面（「余段必须出现为 `single_face_fragment` 且回指原 claim」）在本单做不了，
我判断它归属模块 4，已按 pin 纪律显式处理 —— 两边都接了、没留缝，但需要主控确认这个改判。**

依据（设计稿三处一致）：

1. **§5.1** 的编译管线把切段列为 compiler 的第二步：
   `resolve refs → segment evidence（保留双面共同段与单面余段）→ derive support lines`；
2. **§十** 模块 4 的职责清单明写「ref resolve、**切段**、中线/候选/厚度 IR」；
3. **§9.1 第 4 步**（模块 4 的验收）明写「验证**双面余段不丢**、四堵 solid band 不丢」。

且**类型层没有槽位**：模块 2 的 bundle 只有四种 wall claim，claim 上 ⛔ 零几何值（模块 2 验收 4
的机械锁）——「哪一段是余段」本身是**计算结果**，只能落在 compiler 的派生 IR
（`ResolvedWallV1.resolved_along_intervals` 一侧），在 bundle 层为它造容器 = 在模块 3 里
补一个与模块 2 并行的表示，正是派工单 §〇 明令禁止的「两套语义」。

**我接住的模块 3 一半**（`test_acceptance_4_unequal_runs_stay_one_claim_with_full_evidence`
与 `test_acceptance_4_equal_runs_produce_no_fragment_claims`，⭐ 双向）：

- **不等长夹具**（A runs `[10,100]`、B runs `[10,40]`）：两面仍被**同一条** paired claim
  消费（⛔ 不因不等长拆成 single_face——那是 correction 翻 reading 的配对决定）；
  冻结 bytes 里两面的 runs 原样可解（没被拉伸/裁剪）；两 ref 各自带上
  `support_cols_px/runs_px/gaps` witness（§4.1 对 paired face 的必带清单，切段证据完整抵达）。
- **等长夹具**：恰一条 paired claim、kinds 集合 = `{paired_faces}`、处置恰 3 条 ——
  「无条件切碎」的错误实现在此必红。
- **改判落档**：`test_tail_segmentation_is_pinned_to_module_4` 以命名测试 + docstring 把
  「余段切分归模块 4」钉进代码库；并断言等长/不等长两种输入产出的 bundle **形态相同**
  （差异只应出现在 compiler 的切段输出；若在本层出现，说明本层在算几何）。

**请主控裁决**：确认 pin 改写为「验收 4 的切段半归模块 4」（我的处理），或给出模块 3 层的
实现口径。若确认前者，**模块 4 的派工单必须携带这条**（§9.2 测试表里
`test_paired_face_unshared_tail_survives_as_single_face_fragment` 即其验收）。

## 二、验收表逐条（命令 + 读数）

### 验收 1 · 三份真实产物逐份闭合

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py -k acceptance_1 -n 4 -q
```
**读数：3 passed。** 期望计数**从产物重算**（生产者五槽：pairs×2 + 四桶），⛔ 不从 adapter 回读：

| 产物 | 面线 | claimed | non_wall | ambiguous | 求和==面线 | claims 构成 |
|---|---|---|---|---|---|---|
| sm25_1f | 49 | 44 | 5 | 0 | ✅ 49 | 22（=22 pairs）|
| sm25_2f | 46 | 43 | 3 | 0 | ✅ 46 | 22（21 pairs + 1 single_face）|
| sm24_1f | 98 | 20 | 0 | 78 | ✅ 98 | 12（8 pairs + 4 solid_band）|

每份 bundle 返回前已过 `validate_evidence_bundle`（adapter 出口即验），测试再显式调一次。
sm24 的 4 个 solid band = 4 条 claim、无伪造 partner（附断言）。

### 验收 2 · 两份真实 legacy 产物全落 unknown

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py -k "acceptance_2 or legacy_structured" -n 4 -q
```
**读数：3 passed。** **前提先自测**（不是转引设计稿）：f9 的 10 条墙笔画 note 里
「外皮」与「中线」**同时存在**、sm22 的 note 含 `centerline`、两份 `geometry.basis` 键计数
= 0 —— 即「解析 note 必然给出 ≥2 种 basis」。此后：

| 产物 | wall traces | bases 集合 | basis_evidence_ref |
|---|---|---|---|
| f9 | 10 | `{unknown}` | 全 None |
| sm22 | 10 | `{unknown}` | 全 None |

f9 的 7 条 window 笔画**被点名**在 plan_openings 的 debt 描述里
（`"7 window/door stroke(s) present; walls-only adapter did not translate them"`），
⛔ 不是静默丢。另有一条锁证明 `unknown` 不是盲默认：合成的
`geometry.basis="centerline"` 会被**升格**并带 evidence ref；值在域外（`"middle"`）则
`LEGACY_BASIS_DECLARATION_INVALID` 响亮（不静默吞掉生产者的笔误）。

### 验收 3 · 模块 2 pin 接掉：未被选中的悬空候选从 PASS 变红

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py::test_acceptance_3_unselected_dangling_candidate_now_fails -n 4 -q
```
**读数：1 passed。** 破坏 = 把 sm25_2f 一条**未被选中**候选（存货实测 282 条 unselected /
303 candidates）的 `face_b` 改 `L999`。测试先证前提（今天说 yes 的两面：模块 1 类型 +
classifier 仍收；`L999` 不出现在任何 selected pair 与任何桶 ⇒ 模块 2 的解引用面碰不到它），
再断言 adapter 红 `PAIR_CANDIDATE_REFERENCES_UNKNOWN_FACE`（context 带 candidate_index 与
observation_id）。**控制组**：把该悬空候选从产物删掉后同一产物适配绿 —— 红的是悬空引用本身。
模块 4 一半（compiler 重算候选图时解引用）仍归模块 4，未动模块 2 的 pin 测试。

### 验收 4 · 余段保真（本单层）+ 切段 pin 给模块 4

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py -k "acceptance_4 or tail_segmentation" -n 4 -q
```
**读数：3 passed。** 见 §一。模块 3 层双向锁（不等长不拆对、等长零碎片）+ 切段显式 pin。

### 验收 5 · pairs 清空 ⇒ 绝不自造配对

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py -k "acceptance_5 or absent_pairs or empty_selection" -n 4 -q
```
**读数：3 passed。** 三个形态：

1. **真实产物形态**（sm25_2f：`pairs=None` + `ABSENT_NO_MODEL_SELECTION`、桶不动 ——
   实测生产者 `select_pairs` 在无感知输入时**正是**返回这个形状）：adapter 红
   `PAIRS_SELECTION_ABSENT`，context 带 `remedy=reperception_required`、
   `candidate_count=303`（⭐ 有的是可自造的料而没造）、`unaccounted_face_lines` 42 条。
2. **诚实覆盖形态**（合成：pairs=None 但每面都在桶里）：bundle 绿、**零** paired claims、
   2 条 single_face、带 `pairs_selection_absent` debt（channel=walls）—— compiler 的
   reperception 线索以结构化 debt 存在。
3. **空列表形态**（`pairs=[]` + 桶闭合）：合法产品（「选了且选了空」），绿、零 debt ——
   该词表保留给「没供给选择」。

### 验收 6 · 零接线自证

```bash
git diff --stat 31f873d -- src/agent/reading/vector_contract.py src/agent/pipeline.py src/agent/judge/   # 空输出
git status --porcelain -- src/agent/reading/vector_contract.py src/agent/pipeline.py src/agent/judge/    # 空输出
grep -n '"src/\|'"'"'src/\|`src/' src/agent/correction/evidence_adapters.py tests/test_o22m3_evidence_adapters.py  # 零命中（F-152）
```
**读数：三命令均零输出/零命中。** 行为面两条：干净子进程只 import 本模块 ⇒
`src.agent.pipeline` 不在 sys.modules（读数 False）；as-drawn disposition 仍
`KNOWN_NOT_CONSUMED`（与模块 1/2 同型的翻牌 pin，接线日须有意翻）。

### 验收 7 · 跑测与文件清单

```bash
python3 -m pytest tests/test_o22m3_evidence_adapters.py -n 4 -q
```
**读数：21 passed**，全程共 5 次全绿（6.22s / 6.50s / 6.32s / 6.35s，及 neuter 全部
还原后的复跑 6.39s，无 flaky）。
⚠️ 仓库 `pyproject.toml` 的 addopts 写死 `-n auto`——本单每次都显式 `-n 4` 覆盖
（第一次手跑漏带时吃了 auto，随即全部改显式）。**改/新建的全部文件**：

1. `src/agent/correction/evidence_adapters.py`（新）
2. `tests/test_o22m3_evidence_adapters.py`（新）
3. `AI_agent/logs/reviews/execution/2026-08-31_o22m3_evidence_adapters_execution.md`（本档）

**neuter 自证（摘门必红，四组）**：备份 → `if False:` 摘牙 → 对应测试 1 failed → 还原 →
21 passed。四组分别摘：候选图解引用（→ acceptance_3 红）· pairs 缺失分支
（→ acceptance_5 红）· legacy basis 值域检查（→ legacy_structured 红）· walls 通道条件化
（→ module2_weak_spot 红）。

## 三、我认为最薄弱的一处

**「诚实覆盖形态」下 `pairs_selection_absent` debt 与 walls= present 通道并存，而本层不锁
「debt 必须被下游消费」。** 模块 2 的类型只要求 absent 通道带 debt；present 通道带 debt
（部分墙证据在场、配对缺失）没有任何门管它的**去向**。设计稿把它交给 compiler
（§6.1：`pairs 缺失 → reperception_required`）——但那是模块 5/6 的表，**模块 4 的派工单
若不携带**，这个 debt 就是一个谁都可以无视的结构化字段，与「ambiguous 无 debt」被锁、
「debt 无人读」没锁正好构成同一个静默形状。次弱（记录）：`_require_contract` 只挡
「不是我的契约」，**单文件双契约**（hybrid）在 classifier 里判 AMBIGUOUS、到 adapter 这层
被 `ADAPTER_CONTRACT_MISMATCH` 收编 —— code 正确但把「歧义」这个更精确的事实降格成了
「错配」；沿用模块 2 校验器同一形状（那边对 hybrid 有专属 `AMBIGUOUS_CONTRACT_MATCH`）。

## 四、希望复核方重点打哪里

1. **打 §一的归属改判**：读设计稿 §5.1/§十/§9.1#4 三处原文，确认「切段归模块 4」；
   若您读出「模块 3 就该产 fragment」，请指出它落在哪个类型槽位 —— 那就是我的停报判断错。
2. **打「不自造配对」的分辨力**：验收 5.1 的红是「构造期拒绝」，一个把 pairs=None 静默
   视作空列表、然后靠桶闭合混过去的实现能否过我的测试？（我认为不能 —— 形态 2/3 断言了
   debt 的有与无 —— 但这条值得亲手打。）顺手打：候选图解引用是**构造期**牙，能不能绕开
   adapter 直接构造一个带悬空候选的 bundle 过校验器？（能 —— 那是模块 2 pin 的另一半，
   属模块 4 的重算面，不是本单的洞；请确认这个边界叙述成立。）
3. **打 legacy 的 note 不读声明**：在两份真实产物上，任何「note 里的中线/外皮词被
   代码消费」的路径都应不存在 —— 包括**间接**路径（例如从 note 决定 debt 措辞、
   排序、claim_id）。claim_id 的 canonical hash 只吃 refs（模块 2 函数），note 不进。

## 五、外围记录（只记不停，§四分层口径）

- **模块 2 测试文件注释与本单禁令的冲突**：模块 2 的 `test_acceptance_2` 注释与
  `evidence_contract.py` docstring 均写「(从散文) 派生第六态是 module 3 的活」。
  本单派工单禁令 3 禁止解析任何自由文本 ⇒ 我按禁令走：L012 落机械默认
  `not_in_observations`（与模块 2 钉的读数一致）。第六态的合法派生路径只剩
  「生产者开始发结构」—— 若主控想让模块 3 做，需要先给「什么文本形态算结构化证据」的
  判据，而那正是禁令堵死的路。**这不是不听上游的话，是两份口径打架、禁令新且明确。**
- **签名 sidecar（§8.3 的 `SignedLegacyBasisAssertionV1`）未实现**：无任何真实输入带它、
  派工单未点名；本单只认 `geometry.basis` 类型化声明。接线日补 verifier 时注意它必须
  绑定 §3.2 冻结 bytes 身份。
- `perception_source_ref` 的收紧（模块 2 外围记录托付）：as-drawn 有
  `hypotheses.perception_source` 时指它（三份真实产物都有该键），否则回落 `/hypotheses`；
  legacy 指整份文档（`""`）。
- legacy 源的 face_dispositions 恒空（§4.2 只管 as-drawn 面线；模块 2 校验器同判）。
- 一个夹具事故变成的正面读数：造「空墙产物」夹具时删了 face 忘删候选图，
  adapter 的全候选解引用**当场咬住** —— pin 的牙在合成路径也工作，已把这段写进测试注释。

## 六、可复现命令

```bash
# 本单唯一跑测入口（连跑四轮）
python3 -m pytest tests/test_o22m3_evidence_adapters.py -n 4 -q   # → 21 passed

# 零接线 + F-152
git diff --stat 31f873d -- src/agent/reading/vector_contract.py src/agent/pipeline.py src/agent/judge/  # 空
grep -n '"src/\|'"'"'src/\|`src/' src/agent/correction/evidence_adapters.py tests/test_o22m3_evidence_adapters.py  # 零命中

# neuter 四组（备份 → 摘牙 → 1 failed → 还原 → 21 passed）
cp src/agent/correction/evidence_adapters.py /tmp/m3_backup.py
# （对四段检查各改 if False: → 对应测试红 → cp 还原 → 21 passed；明细见 §二验收 7）
```

—— GLM 施工席位 · 2026-08-31
