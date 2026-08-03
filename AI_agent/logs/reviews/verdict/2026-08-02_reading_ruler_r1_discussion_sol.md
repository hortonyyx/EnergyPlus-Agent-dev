# reading 判卷尺可信化 R1：独立调查与修复方案（sol）

- 日期：2026-08-02
- 性质：独立调查与方案；未施工
- 范围：G-1…G-5，并判断 O-1…O-6 是否应纳入
- 结论状态：**当前尺子不可用于发布新的识图质量结论；修复边界应比 G-1…G-5 再宽一层，纳入可比性证明、历史迁移证明和视觉审计闭环。**

## 0. 先给结论

我看到的不是一个故障，而是三条彼此独立、最后叠成“尺子说谎”的断线：

1. **测量语义断线**：judge 在进入真实窗匹配前，用考生自报的 `mirrored/local_x_positive` 去否决整张立面。合法的 `mirrored="unknown"` 因而把全部立面窗变成 miss/conflict。窗匹配核心其实有分辨力，坏在前置归一化。
2. **运行事实与政策断线**：hard-isolation merge 没有接收、更没有冻结 `RunPolicy`，于是以函数默认值 `rectangular/exploratory` 跑 gate①。检查事实抓到了问题，严格政策没有执行。
3. **适用性与重放断线**：case metadata 未声明 `dimensioned` 时被压成 `false`；历史产物又缺少统一的契约、绑定和迁移证明。当前能“手工喂进去出一个数”，不等于已有可审计的同尺重判通道。

因此，G-1/G-2 共因，G-3/O-6 共因，G-4 是另一条 trusted-input 缺件；G-5 不是简单加一个 CLI，而是必须建立**冻结评价上下文 + 版本化迁移 + 可比性拒绝门**。

另有三处需要纠正问题书口径：

- `run_2026-08-02_sonnet_full_unsup/run_config.yaml:64,74-76` 只有 `capability_profile` 是机器字段；`run_profile=regression` 只是注释。当前 `RunConfig` 根本没有 `run_profile` 字段（`src/agent/execution/run_config.py:88-113,159-180`）。所以这里不是“两个结构化声明都被忽略”，而是“一个字段未传，另一个从未成为声明”。目标 G-3 仍然正确，但修复不能只补一次函数传参。
- 当前 sm24 产物并非“五张各抄 48–51 条尺寸”。实数是 `1f/E/N/S/W = 48/20/13/16/20`；五张都有非空尺寸，结论仍成立。把 `dimensioned` 全改为 true 的只读复算将 N/A 从 **31 降到 21**，不是把 31 条全部消灭。
- gate① 并非“分辨力为零”。同一份已落盘事实在 `exploratory/dev` 下 0 blocker，在 `golden/regression` 下准确得到四个 `dimension_chain_closure` blocker。坏的是政策接线，不是这四条检查没有信号。

---

## 1. 诊断：G-1…G-5 的病根与证据

### 1.1 G-1 · 分辨力 > 0 —— 窗通道不满足；墙和窗匹配核心并非都失灵

直接病根在 `src/agent/judge/reading_typed_adapter.py`：

- `:273-306` 的 `_facade_sense()` 把合法的 `"unknown"` 映射成 `None`；
- `:866-905` 将它和 reviewed binding 的布尔值比较，`None != False` 后，在读取 `strokes`（`:907`）之前整视图早退；
- 早退结果标成 `cause_class="trusted_frame"`，却用 `denominator_disposition="retain_as_miss"`，即 judge 自身没有采用 trusted binding 的问题被记成考生 miss；
- `src/agent/judge/reading_typed_score.py:865-965` 随后把无 observation 记为 miss，`:967-979` 再把 plan pass + elevation miss 融成 conflict。

这和公开入口自己的契约相反：`scripts/tool_scripts/score_reading_vs_gt.py:87-90` 明写产品的 mirror/local-x 声明“不读取，投影完全由 reviewed bindings 决定”。binding 本身已有严格的 case/GT/manifest hash 校验和 affine 自洽校验（`src/agent/judge/score_inputs.py:81-120`）。

我用真实 `run_2026-08-02_sonnet_full_unsup/0_reading/attempts/001/output.json`、真实 sm24 GT、同 run 的 manifest/bindings/config 做了不落盘的内存探针：

| 输入变体 | payload kind | existence/along/width | sill/head | `windows_placed` | `window_elevation_geometry` |
|---|---|---:|---:|---:|---:|
| 原样，四立面 `mirrored="unknown"` | `c2_scored` | 各 0 complete + 11 conflict | 各 11 miss | 0/11 fail | 0/44 fail |
| 仅将四处改成 `false` | `c2_scored` | 各 11 complete | 各 11 complete | 11/11 pass | 44/44 pass |
| 在上一变体再删除全部 window strokes | `c2_scored` | 各 11 miss | 各 11 miss | 0/11 fail | 0/44 fail |

最后一个变体很重要：它证明开口 matcher 在越过错误早退后确实能区分好/坏产品。G-1 的准确诊断是**开口归一化入口将多种产品压成同一个“零观测”状态**，不是整个评分核没有分辨力。

当前测试不只是漏锁，还在锁住错误行为：

- `tests/test_reading_typed_adapter.py:51-79` 期待部分真实立面因帧向而 N/A；`:81-144` 靠改产品声明让它恢复并检查 disagreement witness；
- `tests/test_reading_typed_scoring_slice0.py:254-326` 明确期待 local-x disagreement → N/A/retain-as-miss。

这些测试必须反转/替换；只新增一条 `unknown` 测试而保留旧契约，会留下两套互斥真理。

### 1.2 G-2 · 诚实回答不得判零 —— 不满足，而且不能用 `unknown → false` 糊住

规范证据是明确的：

- `skills/intake_pipeline/0_reading/guide.md:343-359` 将立面定义在 image-local frame，`mirrored` 合法值含 `unknown`；
- `:354-356` 禁止 reader 声明 world axis/sign/base，世界落位归 correction；
- schema 同样接受 `unknown`（`src/agent/reading/schema.py:93-104`）。

所以 `unknown` 不是格式残缺，更不是 `false` 的低置信别名，而是**对一个信息上不可知事实的弃权**。当前比较 `None` 与 binding 布尔值，语义上是把“未声明”误成“声明相反”。

但这里还有比“忽略两个字段”更细的边界：

- `mirrored` 涉及图像与世界立面的关系，世界解释只应来自 reviewed binding；产品值不得改变投影、适用性或分母。
- `local_x_positive` 是产品几何的 **image-local 参数化说明**。规范允许 left-to-right 和 right-to-left。如果真有一个产品用右向左坐标并同步把 `[a,b]` 写成 `[L-b,L-a]`，judge 不能简单忽略这个说明后按左向右解释，否则会放过当前冤判，却制造一种新的真错判。

因此，G-2 的完整目标不是“`unknown` 特判放行”，而是：**world placement 只认 binding；合法的 image-local 参数化先确定性归一到 binding 的 canonical local frame；任何产品声明都不得把题目过滤为 N/A。**

### 1.3 G-3 · 声明什么档位就执行什么档位 —— 不满足；根因是政策没有成为隔离事务的绑定输入

flat-flow 路径会把 policy 传入检查；hard-isolation 路径不会：

- `src/agent/execution/policy.py:34-45` 的默认值正是 `rectangular/exploratory`；
- `src/agent/execution/isolation.py:273-349` 的 `merge_isolated_output()` 没有 policy 参数，`:349` 调 `check_reading_stage(...)` 时也不传 profile；
- `src/validator/checks/view_manifest.py:27-48` 的 checker 默认同样是 `rectangular/exploratory`；
- `scripts/tool_scripts/spawn_isolated_reader.py:55-63,90-95` 的 merge CLI 没有 profile 入口。

真实 checks 头部因此恰好落成默认值。对同一组已落盘检查事实只改政策复算：

- exploratory/dev：0 blocker；
- golden/regression：四个 blocker，精确为 `1f/East/North/South.reading.dimension_chain_closure`；
- 第五个 `stroke_dimension_consistency` 仍是 flag，这与其注释“advisory only，真实墙也可能恰落尺寸位置”（`src/validator/checks/reading.py:829-832`）一致，不应为了凑 5 个 blocker 盲升硬门。

仅给 `merge_isolated_output(..., run_profile=...)` 加参数还不够：CLI 可以撒谎、build 与 merge 之间配置可以漂移、checks 头部也无法证明它和当初发卷的是同一政策。病根是 policy 没进入 hard-isolation 的 hash-bound transaction。

### 1.4 G-4 · 该考的题必须真的考 —— 不满足；缺失声明被静默压成 false

信任链如下：

1. `case_data/testdata_prompt.json:1-14` 没有顶层 `dimensioned_views`，plan 项也没有 `dimensioned`；
2. manifest builder 在 `src/agent/execution/view_manifest.py:783-880` 将缺失最终压成 bool false；schema `RequiredViewEntry.dimensioned` 本身只有 bool（`:344-359`），无法保存“未声明”；
3. merge checker 从 manifest 取 dimensioned stems（`src/validator/checks/view_manifest.py:60-65`）；
4. `src/validator/checks/reading.py:478-495` 因 false 将每图的 `dimensions_present` 与 `dimension_p1a_fields` 记 N/A。

这不是产品通过少填 `dimensions[]` 直接控制的，真正控制者是 trusted case metadata；但 trusted metadata 缺件被错误地解释成了“已确认不带尺寸”。

只读复算的精确结果：

| trusted `dimensioned_stems` | pass | N/A | fail | regression blocker |
|---|---:|---:|---:|---:|
| 空集（当前） | 60 | 31 | 5 | 四个 closure |
| 五张全 true | 70 | 21 | 5 | 同四个 closure |

被重新激活的正好是 5 个 `dimensions_present` + 5 个 `dimension_p1a_fields`，且本产物这十项全 pass。其余 21 个 N/A 中，`dimension_derived_refs` 仍有 5 个，因为产品没有任何 `provenance="dimension_derived"` stroke；这是真正无对象可查，不应强改 pass/fail。另有 door-heal、plan-only/elevation-only 等合法 N/A。

所以 G-4 要守的不是“尽量少 N/A”，而是**每个 N/A 的 authority 与 denominator disposition 正确**：

- 只有 trusted input 明确证明该能力/题目不存在，才可 filter；
- trusted input 未声明，在 strict run 应阻断配置，不得等同 false；
- product 内容缺失/错误不得 filter，只能保留在分母中记 miss/fail；
- 确实没有待查对象（例如零个 `dimension_derived` stroke）的 object-conditional N/A 可以保留，但要有机器原因。

judge gate② 已有一部分正确架构：`reading_typed_score.py:657-684` 只为 trusted-input `filter` 移除分母，产品内容分支通常 `retain_as_miss`。本批不应把 gate① 的 `dimensioned` 修复误做成“所有 N/A 一律计 miss”。

### 1.5 G-5 · 修前/修后和六件离线重判 —— “阻断后仍可评分”已有底层能力，但六件同尺闭包尚不存在

先回答问题书的关键问题：**严格 gate① 拒收不必然导致 reading gate② 无分。**

- `scripts/tool_scripts/run_stage.py:1352-1359` 只限制未 accepted 的 correction；注释和代码都明确 reading attempts 继续进入 scorer；
- `:1462-1474` 遍历所有数字 attempt；
- 标准 `run/flow` 在 outcome 之后仍调用 grade artifacts（`:1787-1834,1961-2045`）。

但这不等于 G-5 已满足：hard-isolation 的标准 merge CLI 只调用 `merge_isolated_output` 并打印 attempt 路径（`spawn_isolated_reader.py:55-63`），不会自动触发上述 grade pass。严格修好后，attempt 会“已归档、未 accepted”，是否出分取决于之后是否另走 run-stage 的 grade 路径。R2 不能依赖这种隐式调用顺序。

我按问题书描述定位六件后，得到以下输入闭包：

| 件 | 仓库候选 | 原始契约/视图 | 当前 replay 闭包 |
|---|---|---|---|
| 07-07 老件 | sm24 `run_2026-07-07_haiku_cv_probe` | 旧式顶层 `{stem:view}`，5 图；plan 无 `scale_origin` | 无本 run 的 view manifest/bindings；需显式 wrap + scale migration |
| 08-02 全卷 | sm24 `run_2026-08-02_sonnet_full_unsup` | `reading_views_v1`，5 图 | GT/manifest/bindings 齐 |
| 08-01 Sonnet 减卷 | sm24 `run_2026-08-01_sonnet_pathref_s1` | `reading_views_v1`，2 图 | 有 scoped sidecars |
| W5 d1 | sm24 `run_2026-08-01_haiku_w5_scoped_d1` | `reading_views_v1`，2 图 | 有 scoped sidecars |
| W5 d2 | sm24 `run_2026-08-01_haiku_w5_scoped_d2` | `reading_views_v1`，2 图 | 有 scoped sidecars |
| 07-08 GPT-5.4-mini | 仓库唯一候选为 sm21 `run_2026-07-08_gpt54mini_cv_retest` | 旧式顶层 `{stem:view}`，6 图 | 无 v3 manifest/bindings；GT 是另一 case 的 legacy v2 |

这里有一个问题书没有覆盖的硬矛盾：前五件是 sm24，唯一 07-08 mini 是 sm21。两份 GT identity 分别为：

- sm24：schema 3 / `GroundTruthV3` / content `dd32135d…`；
- sm21：schema 2 / `LegacyGroundTruthV2` / content `44f73fd…`。

因此按当前仓库事实，**六件不能放进一张声称“同 GT”的表**。要么缺了一份未入仓的 sm24 GPT-5.4-mini 产物，要么 R2 必须按 case 分表，不能把 sm21 和 sm24 称为同一考卷。

此外，“同一 score 代码”也不自动等于“同尺”：scoped 三件当前 sidecar 使用子集 binding，denominator hash 与全卷不同。我的只读探针证明可用 08-02 的完整 sm24 evaluation bundle 对这三份两图产品评分，缺失三图会留在完整分母里；这才是全卷横比口径。原 scoped 分数仍可单列，但不可与 full score 混为一列。

---

## 2. 修复方案：改什么、为何这样改、否决了什么

### S-1 · 建立 reading frame normalization v2（修 G-1/G-2）

**改什么**

1. 删除 `reading_typed_adapter.py:873-905` 这种“产品声明与 binding 不同 → 整视图 N/A”的评分行为。产品帧声明永远不能改变 applicability/denominator。
2. `mirrored` 只作为非承重审计信息保存；世界投影只用 reviewed binding。`unknown`、缺失、true、false 均不得直接触发丢观测。
3. 对 `local_x_positive` 明确一份可执行契约：它只解释产品自身 image-local 数值参数化，不提供 world placement。preferred 实现是给 reviewed binding 增加 hash-bound 的 canonical local domain/facade span；right-to-left 合法产品先做 `x_canonical = L - x_product`，再用 binding 投影。这样“左向右 `[a,b]`”和“右向左 `[L-b,L-a]`”归一后完全相同。
4. 若团队不愿支持两种参数化，则必须发新 schema 版本，规定几何恒用 left-to-right canonical x，并给所有旧合法 right-to-left 产品做显式迁移；不能一边保留 guide 的合法值、一边评分时忽略。
5. bump `reading_adapter`/helper version 和 score identity，保证旧 cache 失效；sidecar 保留 raw declaration hash、采用的 canonicalization rule 和 binding transform hash，但不把审计 finding 当 score rejection。

**为什么**

它同时守住两边：诚实 `unknown` 不再被杀；真正把坐标按另一方向编码的合法产品也不会被误解释。产品若谎报 local-x，则归一后的几何自然错位并记 miss，而不是通过控制 N/A 逃题。

**否决的替代方案**

- `unknown` 直接当 `false`：否决。它把弃权伪装成事实，继续奖励猜测。
- 只把 `unknown` 当 wildcard，仍对显式 mismatch 整图 N/A：否决。显式合法参数化仍会被罚，而且产品仍能控制 applicability。
- 对 mirror/local-x 两字段一律忽略、数字始终按 left-to-right：作为长期方案否决，除非同时版本化收紧规范；否则会错判真正使用 right-to-left 数值的合法产品。
- 在 aligned/flipped 中择优取高分：否决作为默认 judge 规则。它用 GT 帮产品选择朝向，可能掩盖真实的坐标语义错误。只有 reviewed binding 决定 world placement，不能按得分择优。

### S-2 · 把 EffectiveRunPolicy 变成 hard-isolation 的冻结输入（修 G-3/O-6）

**改什么**

1. `RunConfig` 新增结构化 `run_profile`；CLI 可以在创建 run 时写入，但对已 provision 的 run 不得临时覆盖。配置与 CLI 冲突直接报错。
2. 在 build/provision 阶段一次性解析 `capability_profile + run_profile + validation/review relevant switches`，落为 canonical `_run/run_policy.json`（或纳入 RunManifestV2 的 run_inputs），带 schema/version/content hash。
3. isolation `binding.json` 绑定 policy hash；merge 重验 policy 未漂移，然后把同一个 typed `EffectiveRunPolicy` 传给 `check_reading_stage`。flat-flow 也调用同一 resolver，不再各自拼默认值。
4. `checks.json` 头部记录 effective profiles、policy hash、source（structured config/legacy replay），而不是只记录两个没有来源的字符串。
5. strict/golden 对缺失、非法或漂移 policy fail-closed；历史只读 replay 可以显式 `legacy_defaulted=exploratory`，但不得冒充 regression。

**为什么**

这使“声明、发卷、合并、检查、落盘证明”成为同一事务。只补 merge 参数不能阻止 build/merge 间漂移，也无法证明 CLI 当时传了什么。

**否决的替代方案**

- merge CLI 加 `--run-profile regression`：否决，调用者可在收卷时改口径。
- merge 时重新读 `run_config.yaml`：否决，发卷后配置可漂移。
- 继续让缺失 profile 静默默认 exploratory：正式 run 否决；只允许明确标记的 historical replay。

### S-3 · 适用性声明 fail-closed，历史采用版本化 overlay（修 G-4）

**改什么**

1. trusted case metadata 对每个 required view 明确声明 `dimensioned: true|false` 及来源；新 regression/golden run 缺失时 provisioning 失败，错误码应是 `dimensioned_applicability_unknown`，不得产一个 false manifest。
2. manifest wire 必须保留 `unknown` 与 false 的差异，或在生成 manifest 前拒绝 unknown；不能再用 bool 默认折叠。推荐带 `state + authority/source_hash`，便于审计 N/A 来源。
3. 根据问题书给定的源图事实，经一次 source-image/human review 后，把 sm24 五图的声明补为 true，并为未来 run 生成新 manifest。**不要原地改历史 `_run/view_manifest.json` 或 RunManifest。**
4. historical replay 如需修正错误 applicability，使用 versioned、reviewed、hash-bound replay overlay，sidecar 同时记录 base manifest hash 与 overlay hash。
5. 抽象一条全局 N/A invariant：`product_content` 只能 `retain_as_miss/fail`；只有 trusted-input 的真实不可考性可 `filter`；trusted 配置 unknown 在 strict 下是 blocker，不是 N/A。

**为什么**

`dimensioned` 是考卷属性，不是考生答案属性。产品是否抄了 dimensions 可以佐证排查，却不能反过来决定自己是否要考。

**否决的替代方案**

- 看到产品 `dimensions[]` 非空就设 true：否决，考生控制考题。
- 所有 PNG 默认 dimensioned=true：否决，会冤枉真正无尺寸图。
- 原地修历史 manifest：否决，会破坏已冻结 hash/RunManifest 信任链，也让修前结果不可复现。

### S-4 · 建立只读 OfflineReadingReplayV1（修 G-5）

**改什么**

新增一个明确的离线 judge 工具/服务，不依赖 attempt accepted 状态，不修改历史 run、attempt、RunManifest 或 GT。输入是：

- raw product bytes + product contract；
- frozen evaluation bundle：GT、base/effective manifest、score bindings、tolerance config、evaluation scope；
- scorer/adapter/helper versions；
- 可选的 versioned migration chain。

输出写到独立 replay 目录，至少分开两轴：

- `gate1_disposition = accepted|rejected|not_replayed`，含 exact blocker ids/profile/policy hash；
- `gate2_status = c2_scored|not_applicable|rejected`，必须检查 payload `kind`，不能以对象非 None 代替成功；
- score rows/claim summaries 与完整 identity；
- `ruler_key`，包含 GT content hash、base/effective manifest hash、binding hash、tolerance hash、evaluation-scope/denominator hash、adapter/scorer/helper versions；
- 独立的 `product_preparation_provenance`，包含 raw/post hashes、迁移规则与审签状态。

R2 表格生成器只有 ruler key 相等，且每行 product preparation 都被证明为无损迁移或明确审签的等价适配，才允许并排标“同尺”；ruler key 不等则拒绝或明确分组。迁移规则本来就可能因旧契约而不同，不能要求其 hash 相等，但必须逐行展示，不能藏进 ruler key。对 sm24 的 scoped 三件，应同时给：

1. `original_exam_scope` 结果（回答“当时实际考了什么”）；
2. 公共 full-five-view evaluation 结果（回答“放在同一整卷上表现如何”）。

公共 full 评价里缺失的三图是产品未作答，应保留为 miss，不能 filter N/A。

旧式 flat `{stem:view}` → `{"views": ...}` 可以是无损 migration。07-07 的 `scale_origin` 则不是纯 wrap：自由文本解释必须成为具名、版本化 migration rule，记录 raw/post hashes、证据出处与 reviewer；若不能机械证明，状态应是 `migration_requires_review`，不能偷偷补完后称原样重判。

**为什么**

这把生产 gate 的“是否接收”与 judge 的“这份固定答案得多少分”解耦，同时保持两者都可见。严格拒收不应为了历史对照而放水，评分也不应因为拒收而消失。

**否决的替代方案**

- 临时把 regression 降成 exploratory 再评分：否决，篡改 gate① 事实。
- 覆盖历史 output/manifest 补字段：否决，破坏原件和 hash 证据。
- 复用每个 scoped run 自己的 binding/denominator 后直接横比：否决，分母不同。
- 只断言 `score_vs_gt is not None`：否决；`rejected/not_applicable` 同样有侧车。

### S-5 · 将 O-1/O-2/O-3/O-4/O-5 纳入可信尺边界

#### O-1 自动 render：纳入，优先级高

`scripts/tool_scripts/run_stage.py:615-648` 只 glob `0_reading/*_view.json`；isolation 正常产物在 `attempts/NNN/output.json`（`isolation.py:344-380`），两条布局天然错开。修法应由 attempt finalization/merge 共用 renderer 读取 aggregate `views`，把图写到 `attempts/NNN/renders/<expected_output_id>.png`，记录 source output hash、render helper version、每图状态/hash。accepted 根目录别名只能是便利副本，不能是唯一证据。

render 失败不能继续伪装成“肉检材料齐全”。对于要求人工 review 的 run，应阻断 `review_complete`；是否阻断纯数值 gate① 可另定，但必须有机器可见 failure artifact。

#### O-2 typed grade：纳入，且不只是排版问题

legacy renderer 仍有 plan + 四立面路径（`scripts/tool_scripts/render_grade.py:912-1009`）；typed renderer `:1127-1240` 只画 GT floor polygon/boundary/opening，再在底部堆 claim rails。它没有拿到 normalized candidate geometry，`:1243-1254` 的入口也只传 GT/identity/payload。当前“绿色开口”不能被理解成候选几何叠图；标签轨在 `:1183-1213` 高密度重叠只是表象。

修法是扩展 renderer 输入为 judge 已认证的 normalization certificate/observation rows（绝不重新读产品 mirror），恢复 floor panels + 四 facade panels：GT、normalized candidate、miss/extra/match 在各自空间位置叠画；claim summary 放独立表区。`validate_typed_render_totality` 不应只证明 GT target/claim 有一个 audit 字符串，还应覆盖每个 scored/missed/extra observation，并指出 panel/primitive id。

#### O-3 文件名：纳入，低成本 P0

`session_kickoff.md:51` 的 `<name>_view.json` 与 `:57-65` 示例冲突；manifest 真正规则在 `view_manifest.py`，plan/elevation 对已有 `_view` 的 stem 是 identity。修成唯一规范：**只按 staging `input_inventory.json` 给出的 `expected_output_id` 写 `<expected_output_id>.json`**。静态表只能作非规范示例，不能再次推导名字。

#### O-4 OCR anchor / 3.3 亿像素：纳入，安全 P0 + 语义 P1

根因链完整：

- `src/agent/reading/schema.py:119-129` 的 `ocr_texts` 完全 untyped；
- guide 示例 `guide.md:269-272` 像 metric local anchor，但 `Dimension.anchor` 注释又写 pixel（schema `:65-81`），坐标载体语义不统一；
- validator 只查 typed `room_labels` anchor（`src/validator/checks/reading.py:212-318`），不查 OCR；
- renderer 把 OCR anchor 纳入画布 extent（`render_vector_to_png.py:50-77`），在 `Image.new` 前无像素预算（`:85`）。真实 d2 产品 `1f_view/T1=[360,450]` 因而把约 10×20m 图撑爆。

两层修复：立即让 renderer 的画布只由结构几何/显式 trusted metric bounds 决定，annotation 不得扩张画布，并在分配前硬限 width/height/total pixels；随后把 OCR schema 版本化为显式 `anchor_m` 与 `anchor_px`（或 `{frame,point}`），legacy `anchor` 在 strict 下不得猜单位。metric annotation 要按 trusted canvas bounds + 合理 margin 检查，越界 flag/block；pixel annotation 不进入 metric transform。绝不能“clamp 后放行”，那会隐藏坏数据。

#### O-5 exam scope：机制本身不是 bug，但正式测量边界必须收紧

冻结/守卫/hash 应保留。问题是 scoped run 是不同考试，而且输入减少会改变识图质量，不能作为 full-run 基线。建议：

- golden/regression 的官方 reading baseline 禁止 subset，或强制标成 `partial_diagnostic`、不得 promotion；
- exploratory 可收窄，但所有 score/grade/表格显著显示 scope 与 denominator hash；
- R2 使用独立的 evaluation scope，不回写原 production exam scope。

### S-6 · O-6 中不要顺手把 advisory check 升硬门

profile 接通后四个 closure 已会阻断，足够验证 G-3。`stroke_dimension_consistency` 的当前算法只是“墙是否恰落尺寸累计位置”的低置信信号，源码明确要求 J0 看图。未做源图假阳性调查前，把它加入 EVIDENCE_BLOCK_IDS 会扩大误拒；这不属于本轮必要修复。

---

## 3. 风险与副作用

### 3.1 真实缺陷会不会被放过

- 若简单忽略 `local_x_positive`，真正按 right-to-left 编码的产品会被误判；S-1 的参数化等价归一专门避免这一点。
- 若产品谎报 local-x，S-1 不给 N/A：它会产生错误位置并正常 miss，所以没有放水通道。
- `mirrored` 不再作为 score input，可能少一个“产品自报与 trusted world frame 不同”的提示；可保留 audit finding，但不得改变分母。真正的 world placement 仍由 binding hash、sign/origin/affine validation 守住。
- dimensioned=true 不会让坏尺寸自动通过：空 `dimensions[]` 会在 `reading.py:497-510` fail；本次四个 closure 仍 block。N/A 从 31→21 是恢复考试，不是提分。
- 不应把所有 N/A 改 miss。真正输入不可见、target kind unsupported、无待查对象仍应诚实 N/A；关键是 authority 分类和分母处置。

### 3.2 历史可重判性

- 新 adapter/helper/version 必须进入 score identity，否则旧 cache 会伪装成新尺结果。
- 07-07 的 scale-origin 补全是最大历史风险。`calibration_note` 虽含等价信息，但从自由文本提取仍是一次解释行为；必须保存 raw、rule、postimage 和 reviewer。无法证明时不可给“原样同尺”标签。
- scoped 三件改用 full evaluation 会显著降分，因为未给三张图；这是换成共同考卷的预期，不应误写成模型在当时 scoped 任务中“漏交”。表格必须同时显示 original/full 两种口径。
- 07-08 mini 目前是 sm21，不可与 sm24 共用 GT。若强塞进一张表，最大的风险不是数值偏一点，而是重建出一条不存在的纵向结论。

### 3.3 GT 与信任链

- S-1/S-2/S-4 都不需改 GT。
- S-3 改的是 case applicability metadata/新 manifest，不是 GT；但它会改变 gate① applicability 和可能的 judge denominator，必须像 GT 一样 hash-bound、versioned、reviewed。
- sm21 若要进入同一 C2 v3 ruler，需要另行把 legacy GT v2 升级为 human-verified v3。这是 GT 治理工作，不能伪装成普通 adapter 修复，也不应在本 R1 未经签字施工。
- 历史 `_run`、attempt 和已签字 GT 必须只读；所有修后解释写独立 replay bundle。

### 3.4 运行政策与兼容性

- fail-closed policy 接通后，许多历史/当前产物会 filed-but-unaccepted，这是正确结果。下游 correction 不能消费它们；offline judge 可以评分，但界面必须同时展示 gate① reject。
- `RunConfig` 过去以 soft degrade 保历史兼容（`run_config.py:1-5,131-155`）。新正式运行需 fail-closed，但历史查看/重放要有显式 legacy mode，不能一刀切让旧目录无法读取。
- policy 绑定到 build 后，临时改 YAML 不再影响已发卷；这是预期，但需要给用户明确的“新建 run/重新 provision”工作流。

### 3.5 渲染与资源安全

- 硬像素预算可能拒绝真正的大场地平面，故预算应以像素/内存为最终资源门，并允许 trusted 显式 scale/bounds，而不是写死“建筑不得超过 100m”。
- annotation 不扩画布后，越界文字可能被裁；必须同时落 `annotation_out_of_bounds`，不能静默消失。
- grade renderer 不能从 raw product 重算坐标；只能消费 judge certificate，否则视觉图会和数值尺使用两套变换。

---

## 4. 验收锁：每条守卫具体断言什么

以下每个编号应有一个主 mutation lock；避免在多处重复锁同一谓词，才能做到“摘掉该守卫恰好一红、零连带”。

| 锁 | fixture / 变异 | 必须断言 | 摘掉什么会红 |
|---|---|---|---|
| L-01 honest mirror invariance | 真实五图 payload，分别置 `mirrored=unknown/true/false/缺失`，几何不变 | 四者 normalized world observations、denominator hash、claim rows、criteria 完全相同；均 `kind=c2_scored`；无 frame-disagreement N/A | mirror 重新参与 reject/投影 |
| L-02 local parameterization equivalence | 同一立面，left-to-right `[a,b]`；right-to-left `[L-b,L-a]` | 两者 canonical observations 和分数逐字相同；certificate 记录不同 raw rule | local-x canonicalizer 或 trusted span 被摘 |
| L-03 local declaration is not a cheat | 只翻 `local_x_positive`，不翻数值 | denominator 完全相同，但目标 observation 变 miss/extra；绝不 N/A/filter | 错误地完全忽略 local-x 数值语义 |
| L-04 G-1 contrast | 真实 good payload vs 删除一扇窗或平移超过 tolerance | good 五项各 11 complete；bad 的指定 target/claim 精确翻为 miss，其他 target 不变；两个 score hash 不同 | matcher/产品缺失被错误过滤 |
| L-05 obsolete contract removal | 反转现有 `test_sm24_local_x_disagreement...` fixture | mismatch 不再产生 `trusted_frame retain_as_miss`；旧 witness 不能决定 score | 旧早退分支残留 |
| L-06 adapter cache identity | 同 product/evaluation bundle，只改 adapter helper v1→v2 | identity 不同，旧 cache 被拒绝 | helper version 未入 hash |
| L-10 isolation policy truth | 构造 regression+orthogonal isolation fixture，复用当前 5 fail facts | checks 头部精确为 regression/orthogonal + policy hash；attempt filed、不 accepted；blocker 恰为四个 closure | merge 未消费 EffectiveRunPolicy |
| L-11 exploratory contrast | 同字节产品、同检查，只把**发卷前** policy 设 exploratory | 0 blocker、头部 exploratory；事实 rows 与 L-10 相同 | disposition 没真正按 profile |
| L-12 policy drift | build 后改 run policy/config，再 merge | 在创建 attempt 前以 `run_policy_drift` 拒绝 | policy hash binding/reverification |
| L-13 missing strict policy | 新 regression run 删 structured run_profile | provisioning fail，不得默认为 exploratory | strict fail-closed resolver |
| L-20 applicability unknown | 新 formal case 缺某 required view 的 dimensioned 声明 | provisioning 以 `dimensioned_applicability_unknown` 失败；不得落 false manifest | 缺失→false 折叠 |
| L-21 sm24 dimension activation | reviewed sm24 applicability 五图 true + 当前产品 | `dimensions_present` 5 pass、`dimension_p1a_fields` 5 pass；这十行不再 N/A；其他 check-id 的结果逐项不变；四 closure 仍 block | manifest/checker applicability wiring |
| L-22 product cannot set exam | 固定 trusted true，分别清空/填充产品 `dimensions[]` | manifest/applicability/denominator 不变；空数组使 `dimensions_present` fail/block，不是 N/A | 从产品反推 dimensioned |
| L-23 truly un-dimensioned | trusted false 的无尺寸 fixture | 两项 N/A，带 source hash/reason；不阻断 | false 被误当 unknown/true |
| L-30 blocked attempt still scores | regression fixture有一个确定 blocker，无 accepted record | replay 输出 `gate1=rejected` 且 `gate2_status=c2_scored`；明确断言 payload.kind、非零 denominator 和指定 score row | accepted 状态错误耦合 judge |
| L-31 acceptance independence | 同一 product/evaluation bundle，仅 accepted pointer 有/无 | gate② payload、claim/segment rows 与其 semantic hash 相同；完整 sidecar identity 只允许在 product accepted provenance 上不同 | scorer偷读 accepted 作为质量输入 |
| L-32 comparability refusal | 六行中任改 GT/binding/tolerance/evaluation scope/helper version 一项 | table builder 拒绝 `same_ruler=true`，指出首个不同 hash | 仅凭 case 名/非 None 横比 |
| L-33 legacy migration | old flat product + versioned wrap/scale migration | raw hash不变；post hash、rule id、evidence/reviewer齐；删 migration 后状态为 unsupported/requires_review，不得静默零分 | ad-hoc 补字段 |
| L-34 scope dual report | 两图产品分别按 original subset 与公共 full bundle评分 | 两个 scope/hash/denominator明确不同；full 中缺三图 retained-as-miss | scope 被静默复用/filter |
| L-40 aggregate render | isolation 只产 `attempts/001/output.json`，根目录无 `*_view.json` | 生成 expected set 的 per-attempt renders；每图 source/render hash齐 | flat glob 依赖 |
| L-41 render failure visibility | renderer 注入异常 | review status 明确 unavailable/blocked，不能显示 complete | best-effort 吞错 |
| L-42 typed grade spatial totality | 含 plan/elevation match、miss、extra 各一 | 每个 target 与 normalized observation 都在正确 panel 有 primitive；四 facade title齐；summary数字等于 payload | 立面/候选绘制或 audit-totality 被摘 |
| L-43 no label-over-geometry contract | 高密度 14 openings fixture | summary/labels 的布局 boxes 与 geometry panels 不相交；不是只做脆弱 PNG snapshot | claim rail 再压回几何区 |
| L-50 exact output id | source `foo_view.png`，inventory expected `foo_view` | 只接受 `foo_view.json`；`foo_view_view.json` 被拒；kickoff 生成文本引用 exact id | 文档再自行拼 `_view` |
| L-51 OCR resource guard | 10×20m 结构 + OCR metric anchor `[360,450]` | gate 报 frame/bounds 错；renderer 在 `Image.new` 前拒绝或用 bounded canvas，像素预算不超限 | annotation extent/资源门 |
| L-52 OCR frame separation | 同文字分别 `anchor_px` 与合法 `anchor_m` | pixel anchor 不改变 metric canvas；metric anchor按 trusted bounds绘制 | 坐标载体重新混用 |
| L-60 official scope | regression run 配 subset scope | 不得 promotion 为 official baseline（或 provisioning 拒绝）；exploratory 则明确 `partial_diagnostic` | scoped score冒充全卷 |

另建议对“当前好产品”加入一条顶层哨兵：墙 score 与窗 score 都必须同时非零且能被局部几何变异改变。它不能替代上述精确锁，但可防未来再出现一个通道整批早退而局部单测没有覆盖真实 envelope。

---

## 5. 优先级与批次

### P0：任何新的正式跑测/能力结论之前必须完成

1. **批 A（score contract）**：S-1 frame normalization v2、旧错误测试反转、helper/cache version bump、L-01…L-06。没有它，窗数字继续不可用。
2. **批 B（policy + applicability）**：S-2 EffectiveRunPolicy 冻结、S-3 dimension applicability fail-closed、L-10…L-23。没有它，“regression”与 N/A 仍不可证明。
3. **批 C（安全交付面）**：O-1 aggregate auto-render、O-3 exact output id、O-4 renderer 像素预算与 OCR 最小 strict schema、对应 L-40/L-41/L-50…L-52。O-4 有资源耗尽风险，不应后排。
4. **批 D（可视尺）**：O-2 typed grade 的候选/GT 六 panel 恢复与空间 totality。若只是后台开发探针可在 A/B 后跑；在对用户发布任何“识图变好/变坏”结论前必须完成。

批 A、B 应分提交/分审，因为一个改 judge 数学，一个改 execution trust transaction；但两批都绿之前不发布新分数。

### P0-R2：修尺验收后、重写历史结论前必须完成

5. **批 E（offline replay）**：S-4、L-30…L-34；先产六件 inventory/comparability report，再跑重判。若 07-08 mini 的 case 身份未裁定，只能先出五件 sm24 表，不能伪造第六行同 GT。
6. 对修前、修后各保存 ruler identity；同一 raw product 的 delta 必须能归因到 adapter/policy/applicability 哪一项，而不是只留最终 PNG/百分比。

### P1/P2：可后移，但不得混入本轮“顺手加严”

7. **P1**：OCR 全语料坐标迁移、trusted annotation bounds authoring 工具；official/full 与 partial diagnostic 的 UI/报告治理。
8. **P2**：调查 `stroke_dimension_consistency` 的假阳性率后再决定是否升级 blocker；改进 CV/reader 能力属于尺修好后的 R3+，不应和 R1 混批。

---

## 6. 无法判定、需要什么探针/裁定

### U-1 · 第六件到底是哪一份，当前无法判定

仓库中唯一匹配名称的 07-08 GPT-5.4-mini 是 sm21，不是 sm24。要完成“六件同 GT”，需要主控二选一：

1. 提供缺失的 sm24 GPT-5.4-mini 原始产物路径/hash；或
2. 承认 R2 按 case 分表，sm21 不标 `same_gt=true`。

若要把 sm21 也放到 C2 v3 尺下，还需单独的人签 GT v3 迁移与 bindings；没有这一步无法声称和 sm24 同一 score contract。

### U-2 · 07-07 `scale_origin` 迁移能否称“机械等价”，当前无法完全判定

自由文本含 px/m、SW origin、envelope，且已有手工回放显示补值后墙 score 合理；但“文本语句足以唯一确定 typed affine”尚无正式规则/锁。需要：

- 对 raw product、源图校准 sidecar、flat view 文件做三方 hash/数值核对；
- 写一个只读 migration dry-run，输出所有候选 affine；必须唯一；
- 由 reviewer 签 migration evidence。非唯一则只能标 reviewed adaptation，不能称原样。

### U-3 · 所有合法 right-to-left/mirrored 历史编码的真实语义，尚未做全语料调查

guide 允许两种 local-x，现测试 fixture 确有 right-to-left 声明；但尚未证明这些产品的数值是否真的随声明反射，还是只填错 metadata。施工前应只读扫描所有 reading artifacts：对每个立面收集 facade span、声明、window interval、可用 reviewed binding，并生成等价反射对照。这个调查决定 S-1 是直接支持双参数化，还是需要先迁移到 canonical schema；不能凭当前几个产品猜。

### U-4 · sm24 五图 `dimensioned=true` 的权威签字尚未在 metadata 中

问题书把“五图有完整尺寸链”作为已知事实，产品也有 48/20/13/16/20 条抄录；但产品不能成为考卷 applicability 权威。需要一次 source-image review，把每图 true/false 和 source image hash 写入 reviewed metadata/overlay。未签之前可以验证代码行为，不能用产品自证完成正式 backfill。

### U-5 · 四个 closure fail 是否等于“源图读错”，当前无法判定

代码事实只能证明产品声明的 dimension groups 缺件、不闭合或分组方式不满足规则；它抓到了可疑质量信号，足以在 regression 按既定 evidence policy 拒收。它不能单独证明图纸真值是什么。要归因“看着画、没真量”，需对四个 evidence payload 中的 `incomplete/mismatches/dimension_ids` 做原图 crop + 独立 OCR/J0 复核。第五个 stroke consistency 更不能直接当真缺陷。

### U-6 · OCR anchor 的精确合法边界尚无法从现契约判定

guide 的 OCR 示例像 metre，`Dimension.anchor` 注释却写 pixel，历史语料可能混用。立即加像素预算/annotation 不扩 canvas 无需等待；但 strict schema 的迁移规则、metric margin 和 pixel image bounds，需要先扫描全部 `ocr_texts/dimensions/room_labels` 的 anchor 分布并对若干源图核对。不能用一个固定“>100 就错”阈值替代坐标 frame。

### U-7 · O-2 的视觉验收标准需要产品裁定一项

数值上可以锁“六 panel + 全 observation totality + label 不压 geometry”；但是否还要同时展示原始 source crop、是否按楼层拆页、miss/extra 配色沿用哪套，需要人机界面裁定。无论选择哪种，renderer 必须只消费 judge-certified normalization，不能自行重算。

---

## 最终裁定

本轮不应把任务定窄为三处补线：`unknown` 特判、merge 多传两个字符串、sm24 flags 改 true。那会让当前样例转绿，却仍无法证明未来 run 的政策未漂移、合法 right-to-left 没被误判、历史迁移没有改题、六行表真的同尺。

正确边界是：

> **一把可信 reading 尺 = 可区分的 score semantics + hash-bound 的 gate policy/applicability + accepted 状态无关的只读重放 + 可比性拒绝门 + 与同一 normalization certificate 对齐的视觉证据。**

按此边界，G-1…G-4 都有确定修法；G-5 对五份 sm24 产物可实现，但第六份的 case/GT 身份在现仓库下不闭合，必须先取得上述 U-1 裁定，不能用推测补齐。
