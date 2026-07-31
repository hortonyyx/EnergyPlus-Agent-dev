# 主控裁定 · 识图类型化判卷细稿（U-01 – U-15）+ 两条主控独立发现

> 主控 Opus 5 · 2026-07-31
> 对象 = [`proposals/reading_typed_scoring_plan_sol.md`](../../../proposals/reading_typed_scoring_plan_sol.md)（sol，1738 行）
> 依据 = [问题书](../request/2026-07-31_reading_typed_scoring_brief.md)
>
> **本文与设计稿同等约束力。** 施工方须把每条裁定并入设计稿正文（累计式自包含），
> 不得以「裁定书里说过」替代正文。

---

## 0. 对细稿的总评

**通过，附 15 条裁定 + 2 条主控独立发现的必改项。**

细稿把两条通道的**不对称性**认到了点子上（立面 = 适配活、平面 = 帧契约活），
§2 的行为矩阵九行逐条对应 C1/C2，`not_applicable` 被明确定义为**成功的测量结果**而非失败——
这正是 R-4 的正确落法。§13.3 主动把两处「要改现有断言」的地方挑出来请裁而不是偷偷改，纪律正确。

**最有价值的动作 = §14 上报 15 条欠规格边界、无一自行降级为假设。**
这是本项目至今最有效的治理动作（2026-07-28 首次出现，本轮第二次）。

---

## 1. 主控独立发现（细稿未覆盖，必改）

### D-1 · 全仓唯一的「识图 E2E」是拿答案当被测物

主控独立核实 `tests/test_c2_b4b_phase_d.py:159-176`：

- `segments` 直接来自 `gt.floors[].boundary_segments`；
- `openings.world_along_interval` 直接来自 `gt.openings`；
- `elevation_observations.local_x_interval` 是**拿 GT 值反解绑定变换**算出来的（`:162-163`）。

⇒ **被测物 = 答案本身**，该测试在计分逻辑上不可能红。
这与 2026-07-27 的 C-1′ 裁定同族（「答案分母成为产品输入的函数 = 尺子被被测物变形」）。

**裁定**：细稿 §13.3 第 1 条的方向对，但结论要修正得更准：

1. 该测试的**实质断言是 run-stage ↔ CLI 字节一致（parity）**，用 GT 回声当输入对 parity 目的**是成立的**
   ⇒ **不判它错、不删、parity 断言保留**。
2. 但它**不构成识图判卷覆盖**。必须在测试文件内加一行注释写明「本 fixture 是 GT 回声，
   仅用于 parity，不度量任何计分逻辑」，并**改名**使其不再被读作识图 E2E。
3. **必须新增**一个用真 `{"views": ReadingView}` 形状的识图判卷 E2E（可直接用
   `run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json` 作夹具形状来源）。
4. 该新 E2E **禁止**从 GT 反解任何产品坐标。

### D-2 · sm24 现场存在真实的 local_x 帧冲突，且有 4/4 的可辨识签名

主控实测（命令见 §4）：

| input | binding.local_x_positive | binding.sign | product.local_x_positive |
|---|---|---|---|
| East_view | image_left_to_right | +1 | image_left_to_right |
| South_view | image_left_to_right | +1 | image_left_to_right |
| **North_view** | image_left_to_right | **−1** | **image_right_to_left** |
| **West_view** | image_left_to_right | **−1** | **image_right_to_left** |

产品**恰好在 binding `sign = −1` 的那两个立面**声明了反向，相关性 4/4。
而 `ReadingView.facade.local_x_positive` 的 schema 注释明写
*"Purely in-image: along which screen direction local-x increases. A constant convention string —
intentionally NOT east/west"*（`src/agent/reading/schema.py:98-102`），
`guide.md:334` 与 `:387` 口径一致（`no world axis / sign here`）。

⇒ **识图模型把世界向感塞进了一个 image-local 字段**。这是一处**真实的产品缺陷**，
且它使产品与 binding 对「产品的数在哪个帧里」这件事**实质性地不一致**。

**这条直接推翻细稿 U-10 的建议**（见 §2 U-10）。

---

## 2. 逐条裁定

### U-01 · 平面 local→world 帧的权威 — **采纳建议，加两条**

采纳「严格结构化 `scale_origin.world_x_m/world_y_m` + 忽略 `note` 自由散文 +
缺失/畸形 ⇒ 平面 NA + 无隐式恒等回落」。

**加 (a)**：帧必须落成**显式可替换的仿射记录**（`PlanFrameCertificateV1`），
即使当前系数是恒等也不许写成隐含恒等 —— 不变量 #6。
**加 (b)**：声明的原点**非零时必须计数并在证书与 grade 板上可见**。
理由 = 产品声明自己的帧，等于产品控制尺子的零点；一个整体平移但内部自洽的误读会拿满分。
现阶段不禁止（那会误伤合法情形），但**必须可见**，不许静默生效。
（对标 2026-07-28 C-3 的「有意 NA + 可见性计数」打法。）

### U-02 · 立面竖向基准与多层归属 — **采纳多层 NA，但 z 基准改为「引用已裁定的项目约定」**

多层 binding ⇒ `elevation_floor_partition_unresolved` NA、禁按列表位置推断、禁向 GT 拟合：**采纳**。

**但单层的 z 基准不得写成裸 `+0`**。主控实测：sm24 **五个视图（含四个立面）的
`scale_origin.world_z_m` 全为 `null`** ⇒ 若按「必须声明否则 NA」，窗高度量当场全灭。

**裁定**：z 变换落成 `VerticalDatumCertificateV1`，系数来源三选一并**记进证书**：
1. 视图声明了非空 `world_z_m` ⇒ **声明优先**，`source="product_declared"`；
2. 未声明 ⇒ 取 **z = local_y + 0**，`source="project_convention_2026_07_25"`
   —— 依据是用户 2026-07-25 亲自裁定的「地面线 = 室内地面 ±0.000」，
   **这是已裁定的项目约定，不是施工方的假设**；
3. binding 多层 ⇒ NA（见上）。

`source` 字段必须进证书 hash，且 `project_convention_*` 的使用**必须计数可见**。

### U-03 · 计分线版本 — **采纳 v9，但限定爆炸半径**

采纳「新建严格 sidecar v9 / artifact-contract v2，v8 降为 cache miss，
禁把新契约塞进自由形式 `score_criteria`」。

**限定**：v9 对 correction 通道必须是**纯附加**——
correction 的对外可见判分值在 v8/v9 下必须**逐字节相同**。
交付时须给一份 **D-1 式对照**：用现有 correction v3 夹具，
改造前后 `public_rows` / `wall_criteria` 的 SHA-256 逐条比对，
`blocking_change=false`。（对标 2026-07-28 D-1 口径。）
correction 的公开判分若有任何一位变化 ⇒ 本 Slice 验收不通过。

### U-04 · NA 粒度 — **采纳**

per-input / per-component 能力，逐 claim 过滤；仅当无任何 component 可测才顶层 NA；
歧义只降级它影响的那个 component。与 C2 一致。

### U-05 · 平面墙 `rect` 语义 — **不采纳「整个视图 NA」，改逐笔画**

细稿建议「任一可见平面墙 rect ⇒ 该视图的 plan-segment component 整个 NA」。
**否决**：一条畸形笔画灭掉整条平面通道，会在复验轮上直接让我们**失去这批要救的那把尺子**，
且与 U-04 刚裁的「歧义只降级受影响部分」不自洽。

**改为**：
1. `line` / `polyline` 照常消费；`rect` 墙笔画 = **不可测观测**，逐笔画剔除，**不参与匹配的任何一侧**
   （既不算覆盖、也不算多画）。
2. 被剔除的数量落成 sidecar payload 的**一等字段** `unmeasurable_observations`，
   并**渲染到 grade 板上**。计数 > 0 时人核必然看见。
3. 该视图的 plan-segment component **仍为 applicable**，其余笔画照常计分；
   未被覆盖的答案目标照常算 miss（这是诚实的：判卷器在说「这 N 笔我量不了，用我量得了的那些，
   这些目标没被覆盖」）。

### U-06 · 平面开口图元与宿主 — **采纳**

§7.4/§7.5 顶点投影 + 单向全局目标指派；不吃 `facade_segment_id` 输入；**宿主 claim 恒 NA**。
理由成立：识图按设计就是 topology-light，强解宿主等于发明拓扑。

### U-07 · 立面非矩形窗 — **采纳**

line/polyline 取有限 x/y 界；退化区间照常计分；畸形区间令该 source component NA。

### U-08 · manifest input ID 与 GT source-view ID 分离 — **采纳**

`source_input_id` 与 binding 的 `gt_source_view_ids` 分开，目标兼容性取集合交集，
Va/source 行用 input ID。当前的 `OpeningObservation.source_view_id` 把两者混为一谈，确属缺陷。

### U-09 · 一层多张平面图 — **采纳（v1 NA）**，加计数

不做 union / best-of / 重复计费，该层平面 component NA。sm24 一层一图，无当期影响。
**加**：NA 须走 §U-04 的 per-component 通道并计数可见。

### U-10 · 产品朝向元数据与 binding 冲突 — **⛔ 不采纳，改判**

细稿建议：「reviewed binding 独家控制坐标；产品不符只是 gate② 元数据发现，**不产生 NA**」。

**否决。** 依据 = §1 的 D-1（应为 D-2）实测：sm24 现场 4/4 存在该冲突。
按细稿建议执行，**北立面与西立面的窗会被静默镜像**，产生系统性坐标错误，
而该错误在分数上表现为「识图模型把窗画错了」——**这正是本批要根治的那个陷阱**
（07-30 那轮 1/8 在量出来之前一直被归到模型头上）。

**改判**：
1. **坐标权威仍在 reviewed binding**（这条采纳，F5 信任边界不动）。
2. 但产品与 binding 在 `local_x_positive` 或 `mirrored` 上不一致时，
   **该 input 的立面 component 判 NA**，reason = `elevation_local_x_sense_disagreement`，
   并附**证人**（两边的声明原值）。
3. 理由 = 此时判卷器**确实不知道产品的数在哪个帧里**，两种解释都自洽；
   按 R-4，「量不量得了」的权威在判卷、且**只许说 unsupported**。
   静默选一边 = 用数值反推意图，正是 2026-07-27 C-2 明令禁止的。
4. **不得**用「产品坐标投影后落在合理范围内」之类的数值检验来消歧 —— 那是向 GT 拟合。

**配套（不在本批施工范围，登记为跟进债）**：识图侧把世界向感写进 image-local 字段
是一处真实产品缺陷，应由识图批修（guide 措辞 / gate① 校验）。修好后本 NA 自动消失。

### U-11 · 手搓扁平 payload 的兼容 — **采纳，并入 D-1 处置**

run-stage 拒绝扁平形状为 `unsupported_reading_contract`：**采纳**。
「替换那个假 E2E fixture」**按 §1 D-1 的四条执行**（保留 parity 断言 + 加注释 + 改名 + 另加真 E2E），
不是简单替换。

### U-12 · 平面内外墙与 extra 分类 — **采纳**

拓扑只由答案侧目标带；未匹配的产品笔画是无拓扑的通用 extra；**禁**推断产品的 exterior 标志。

### U-13 · 能力过滤 vs 参考完整性 — **⚠️ 采纳机制，但必须按成因二分（本裁定最重要的一条）**

细稿说「unsupported source 既不供正向分母证据、也不供负向完整性证据」。
**照此实现会开一个假绿杠杆**：产品只要让某个 source 变成 unsupported，就能**缩掉自己的分母**。
这与 2026-07-27 C-1′ 裁定正面冲突（「答案原子与分母必须是答案字节的纯函数」）。

**裁定 —— 按 unsupported 的成因二分，二者行为相反**：

| 成因 | 例 | 分母处置 |
|---|---|---|
| **(i) 受信输入侧** | binding 缺失 / 多层 binding / 该视图类型本就不在能力域 | **可以**从分母中移除（是受信输入与判卷能力的纯函数，产品改不动） |
| **(ii) 产品侧** | 笔画畸形、rect 墙、几何不可解析、区间畸形 | **绝不**移除分母。目标留在分母里照常算 miss，不可测数量按 U-05 计数可见 |

#### ⚠️ U-13 更正（主控自纠，2026-07-31 同日）

**原表把「U-10 的帧冲突」列进了 (i) 受信输入侧 —— 那是主控写错的，现更正为 (ii) 产品侧。**

理由：`facade.local_x_positive` / `mirrored` 是**产品字节**。产品只要声明一个与 binding 冲突的
向感，就能让自己那张立面被判 NA 并**摘出分母** ⇒ 这正是 U-13 本身要封的那个假绿杠杆。
且**不是假想**：sm24 现有识图已在四个立面中的两个（North / West）声明了冲突，
按原表执行，第一次真跑就会静默摘掉一半立面分母。
项目口径「**放水比冤枉危险**」在此适用 —— 宁可冤枉，不可放水。

**更正后的行为**：U-10 的帧冲突仍然
① 令该 input 的立面 component 判 NA（不出正分）、② 附证人、③ 计数可见，
但 **④ 该 input 的答案侧立面目标留在分母里、照常算 miss**。
`trusted_frame` 这个类别可以保留用于**报告粒度**，但**不得**因此获得分母过滤权。

**并强化 U-13 的强制锁**：两份产品字节流除了几何畸形之外，**还必须允许在
`facade.local_x_positive` / `mirrored` 上取反**，断言分母仍**逐字相同**。
这把锁直接杀死该杠杆；原稿把这两个字段固定住（"under the same trusted/frame declarations"）
恰好把杠杆排除在锁的覆盖面之外。

**登记**：本条与 2026-07-28 的 MAJOR-1 同型 —— **主控自己把边界写窄/写错，就会被精确地实现得同样错**。
施工方 sol 是严格照原表执行的，**不计其问责**；主控在 Slice 0（仅锁、无实现）阶段自查发现并更正。

**硬锁要求**：必须有一把锁钉住「能力过滤后的分母是**受信输入 + 能力判定**的纯函数，
与产品坐标字节无关」——做法 = 同一组受信输入下，喂两份产品字节（一份正常、一份把所有笔画改畸形），
断言**两次的分母逐字相同**。这把锁红不了就说明二分没落地。

### U-14 · 意外缺陷的失败分类 — **采纳，加 profile 分档**

产品/能力与判卷歧义 → NA；受信输入或守恒失败 → rejected；意外 `Exception` → 顶层 NA
`scorer_internal_failure` + 堆栈只进 judge 日志；**禁**重分类为产品失败。**采纳**。

**加**：`scorer_internal_failure` **必须计数且响亮**，绝不静默吸收；
且按 `run_profile` 分档 —— `exploratory` 走 warn 续行，**`golden` / `regression` 必须 fail-closed（raise）**。
对标 2026-07-20 F4-1 已确立的同型口径。

### U-15 · NA 的流程/CLI 语义 — **采纳，同样加 profile 分档**

NA 写 sidecar + PNG、正常返回、CLI exit 0、gate② 看证据自己判、不因判卷没尺子而杀掉下游：**采纳**。
**加**：与 U-14 同一分档 —— `golden`/`regression` 下的顶层 NA 必须 fail-closed。
理由 = 正式跑测不允许「没量到」被当成「量过了没事」。

---

## 3. 施工前置

1. 把 §1 D-1/D-2 与 §2 全部 15 条裁定**并入设计稿正文**（累计式自包含，禁「见裁定书」）。
2. 并入后**不需要**再回主控审一轮，直接进 Slice 0；
   但**任何一条裁定你认为无法实现或与另一条冲突** ⇒ **停下上报**，禁自行取舍。
3. Slice 顺序不变，「先落会红的锁」优先。
4. U-13 的纯函数锁、U-05 的计数字段、U-10 的 NA + 证人、U-03 的 D-1 式对照
   —— 这四项是**本批验收的命脉**，缺一即 REWORK。

## 4. 主控探针（可复现，审阅方可独立复跑）

```bash
# D-2：binding 与产品的 local_x 帧声明对照
python -c "
import json
b=json.load(open('case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json'))
r=json.load(open('case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json'))
for it in b['bindings']:
    if it.get('kind')!='elevation': continue
    p=(r['views'].get(it['input_id']) or {}).get('facade') or {}
    print(it['input_id'], it['local_x_positive'], it['sign'], '|', p.get('local_x_positive'))
"

# U-02：world_z_m 现状（全 null）
python -c "
import json
r=json.load(open('case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json'))
for k,v in r['views'].items(): print(k, (v.get('scale_origin') or {}).get('world_z_m'))
"

# F4：legacy 尺子对 v3 硬拒
python -c "
from src.agent.judge.gt import load_gt
try: load_gt('sm24_anchor')
except Exception as e: print(type(e).__name__, e)
"
```
