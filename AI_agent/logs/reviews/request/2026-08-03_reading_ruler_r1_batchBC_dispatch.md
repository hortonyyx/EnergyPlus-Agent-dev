# R1 修尺子 · 批 B + 批 C 派工单（施工 = GLM · 施工审 = GPT/sol）

- **日期**：2026-08-03
- **派工方**：orchestrator（端到端主控）
- **施工席**：GLM（`scripts/glm_code.sh`）
- **审阅席**：GPT 侧（sol，交叉对抗审；写稿的不审自己的稿）
- **性质**：本单**累计式自包含**——新执行者只读本单 + 单内点名的文件即可施工，不需要读被覆写的旧稿。

---

## 0. 一句话背景（为什么此刻做这个）

reading（识图）环节的分数最近全部不可信。已查明的原因不是模型变差，而是**判卷这把尺子和运行政策本身坏了**：

- 判卷层把读图器诚实写的 `mirrored:"unknown"` 当成「帧向冲突」，**整张立面在读坐标之前就被丢弃** ⇒ 已由**批 A 修复并落库**（`b8f9a8d`，全仓 2055 绿 + 10 xfail、零红）。
- **声明的严格档从未真正执行**：`run_config.yaml` 里写着 `regression`（fail-closed）+ `orthogonal_polygon`，实际落盘的 `checks.json` 头部却是 `exploratory` + `rectangular`。那一轮 gate① **本来抓到了 5 条 fail**，按 exploratory 算 = **0 阻断**，按 regression 算 = **4 条 blocker** ⇒ 严格档若真生效，那份产物会被当场拒收。**这是批 B。**
- **交付面三条断链**：07-08 起识图**每轮零渲染**（用户看不到任何产物图）；文件命名契约自相矛盾；OCR 锚点写成像素坐标后 gate① 零阻断放行，渲染器据此分配了一张 **3.3 亿像素**的 PNG（打不开）。**这是批 C。**

**⛔ 硬约束：批 A/B/C 三批全绿之前，本项目不得发布任何新的识图分数或「识图变好/变坏」的结论。**

---

## 1. 权威依据（本单的上游，冲突处以本单为准）

| 文件 | 作用 |
|---|---|
| `AI_agent/logs/reviews/verdict/2026-08-02_reading_ruler_r1_discussion_sol.md` | sol 的诊断与修复方案（S-2 / S-3 / O-1 / O-3 / O-4 + §4 验收锁表） |
| `AI_agent/logs/reviews/request/2026-08-02_reading_ruler_r1_construction_dispatch.md` | 批 A 派工单 + orchestrator 逐条裁定（§1.2 U-1…U-7、§1.3 明令禁止清单、§3 U-4 源图证据与用户签字） |
| `AI_agent/logs/reviews/execution/2026-08-02_reading_ruler_r1_batchA_terra.md` | 批 A 执行记录（已落库，本单以其为基线） |
| `AI_agent/CLAUDE.md` | 项目根文件：架构、术语、不变量（尤其 §1.5 #4 gt 铁律、#7 环节控制边界） |

**术语**（全项目唯一口径）：**orchestrator** = 端到端主控 · **`reading-agent`** = 识图环节内部的调度 · **`reading-worker-agent`** = 实际读图产出观测的 VLM。本单不涉及后两者的设计。

---

## 2. 批 B · 运行政策冻结 + 适用性 fail-closed

### 2.1 S-2 · 把 `EffectiveRunPolicy` 变成硬隔离的**冻结输入**

**病灶**：政策（跑哪个档位）是在「发卷 → 收卷 → 检查 → 落盘」这条链上**各处各自拼默认值**的，所以声明与实际执行可以不一致，而且事后无法证明当时 CLI 到底传了什么。

**要改成**：让「声明、发卷、合并、检查、落盘证明」成为**同一个事务**。

1. `RunConfig` 新增**结构化** `run_profile`；CLI 可在**创建 run 时**写入，但**对已 provision 的 run 不得临时覆盖**；配置与 CLI 冲突**直接报错**，不得静默取其一。
2. 在 build/provision 阶段**一次性**解析 `capability_profile + run_profile + validation/review 相关开关`，落为 canonical `_run/run_policy.json`（或纳入 RunManifestV2 的 `run_inputs`），带 schema / version / content hash。
3. isolation 的 `binding.json` **绑定 policy hash**；merge 时**重验 policy 未漂移**，然后把**同一个 typed `EffectiveRunPolicy`** 传给 `check_reading_stage`。flat-flow 也调用**同一个 resolver**，不再各自拼默认值。
4. `checks.json` 头部记录 **effective profiles + policy hash + source**（`structured_config` / `legacy_replay`），而不是像现在只记两个没有来源的字符串。
5. strict/golden 对**缺失 / 非法 / 漂移**的 policy **fail-closed**；历史只读 replay 可以显式标 `legacy_defaulted=exploratory`，**但不得冒充 regression**。

**已被 sol 否决、⛔ 不许采用的替代做法**：
- merge CLI 加 `--run-profile regression`（调用者可在**收卷时**改口径）；
- merge 时重新读 `run_config.yaml`（发卷后配置可漂移）；
- 正式 run 继续让缺失 profile 静默默认 exploratory。

### 2.2 S-3 · 适用性（`dimensioned`）声明 fail-closed

**病灶**：`dimensioned` 是**考卷属性**（这张图有没有尺寸标注），现在却被静默压成 `false`，导致「该考的题没考」——sm24 五张图明明带完整尺寸链，`_run/view_manifest.json` 里却**全是 `dimensioned:false`**，于是 31 条 N/A 里尺寸类占了大头。

**要改成**：

1. trusted case metadata 对**每个 required view** 明确声明 `dimensioned: true|false` **及其来源**；新的 regression/golden run 缺失时 **provisioning 失败**，错误码 `dimensioned_applicability_unknown`，**不得产出一个 false manifest**。
2. manifest wire **必须保留 `unknown` 与 `false` 的差异**，或在生成 manifest 前就拒绝 `unknown`；**不得再用 bool 默认折叠**。推荐带 `state + authority/source_hash` 便于审计 N/A 来源。
3. **sm24 五张图的 `dimensioned=true` 已由用户签字**（见 §2.3）。据此为**未来的 run** 生成新 manifest。
4. 历史 replay 如需修正错误 applicability，走**版本化、reviewed、hash-bound 的 replay overlay**，sidecar 同时记 base manifest hash 与 overlay hash。
5. 抽象一条全局 N/A 不变量：`product_content` 来源只能 `retain_as_miss` / `fail`；只有 **trusted-input 的真实不可考性**才可 `filter`；trusted 配置为 `unknown` 时在 strict 下是 **blocker**，不是 N/A。

**已被 sol 否决、⛔ 不许采用的替代做法**：看到产品 `dimensions[]` 非空就设 true（考生控制考题）· 所有 PNG 默认 true（冤枉真正无尺寸的图）· 原地改历史 manifest。

### 2.3 sm24 五图 `dimensioned=true` —— **用户已签字，可写入**

orchestrator 已逐张查看 `case_tests/e2e_tests/sm24_anchor/case_data/` 五张源图并对尺寸链做闭合验算，**用户 2026-08-02 签字裁定五张全部 `dimensioned = true`**：

| 图 | 尺寸链（源图读取） | 闭合验算 |
|---|---|---|
| `1f_view` | 顶 `540+1600+2520+4800+540` · 底 `540+1500+2500+900+2520+1500+540` · 底第二层 `4180+1640+4180` | **= 10000 ✓**（两条独立水平链互证）· 总高标注 **20000** |
| `North_view` | 底 `540+4800+2520+1600+540` · 左竖 `1100+2400+1000` · 右竖 `1900+2400+200` | **= 10000 ✓ / 4500 ✓ / 4500 ✓** |
| `South_view` | 底 `540+1500+2500+900+2520+1500+540` · 竖 `1700+1800+1000` · 中 `1900+2400+200` | **= 10000 ✓ / 4500 ✓ / 4500 ✓** |
| `East_view` | 底 `5700+1600+1540+4800+740+1200+2380+1500+540` · 左竖 `1900+2400+200` · 右竖 `1700+1800+1000` | **= 20000 ✓ / 4500 ✓ / 4500 ✓** |
| `West_view` | 底 `540+1500+2380+1200+1740+1500+1220+1500+3080+4800+540` · 左竖 `1700+1800+1000` · 右竖 `1100+2400+1000` | **= 20000 ✓ / 4500 ✓ / 4500 ✓** |

写入时**必须同时记录**：source image sha256 + reviewer `hortonyyx` + 日期 `2026-08-02` + 依据（尺寸链闭合验算，见上表）。

**⚠️ 两条限制**：
- **⛔ 只为将来的 run 生成新 manifest，不得原地改历史 run 的 `_run/view_manifest.json` 或 RunManifest。**
- **⚠️ 改 `case_data/testdata_prompt.json` 会改变 `case_metadata_sha256`** ⇒ **先核实波及面**（老工作区还能不能 merge、已签字的 sm24 GT 信任链是否受影响）。**发现波及信任链即停下上报，不得自行决定。**

### 2.4 批 B 验收锁（每条一个主 mutation lock，摘掉即红、零连带）

| 锁 | fixture / 变异 | **必须断言** | 摘掉什么会红 |
|---|---|---|---|
| **L-10** isolation policy truth | 构造 regression + orthogonal 的 isolation fixture，复用当前那 5 条 fail 事实 | `checks.json` 头部**精确**为 `regression`/`orthogonal` + policy hash；attempt 被 filed 而**非 accepted**；blocker **恰为四条 closure** | merge 未消费 `EffectiveRunPolicy` |
| **L-11** exploratory 对照 | **同字节**产品、同检查，只把**发卷前**的 policy 设为 exploratory | 0 blocker、头部 `exploratory`；**事实行与 L-10 逐字相同** | disposition 没有真的按 profile 走 |
| **L-12** policy drift | build 之后改 run policy/config，再 merge | 在**创建 attempt 之前**以 `run_policy_drift` 拒绝 | policy hash 绑定 / 重验 |
| **L-13** missing strict policy | 新 regression run 删掉结构化 `run_profile` | provisioning **失败**，**不得**默认成 exploratory | strict fail-closed resolver |
| **L-20** applicability unknown | 新的正式 case 缺某 required view 的 `dimensioned` 声明 | provisioning 以 `dimensioned_applicability_unknown` 失败；**不得**落一个 false manifest | 缺失→false 折叠 |
| **L-21** sm24 dimension activation | reviewed 的 sm24 applicability 五图 true + 当前产品 | `dimensions_present` 5 条 pass、`dimension_p1a_fields` 5 条 pass；**这十行不再 N/A**；**其他 check-id 的结果逐项不变**；四条 closure **仍 block** | manifest / checker 的 applicability 接线 |
| **L-22** product cannot set exam | 固定 trusted `true`，分别清空 / 填充产品的 `dimensions[]` | manifest / applicability / denominator **不变**；空数组使 `dimensions_present` **fail/block，不是 N/A** | 从产品反推 `dimensioned` |
| **L-23** truly un-dimensioned | trusted `false` 的无尺寸 fixture | 两项 N/A，**带 source hash / reason**；不阻断 | `false` 被误当 `unknown`/`true` |

---

## 3. 批 C · 安全交付面（渲染 / 命名 / 像素预算）

### 3.1 O-1 · aggregate 自动渲染（**07-08 起零渲染，优先级最高**）

**病灶**：`scripts/tool_scripts/run_stage.py:615-648` 只 glob `0_reading/*_view.json`，而硬隔离的正常产物落在 `attempts/NNN/output.json`（`isolation.py:344-380`）——**两条布局天然错开**，于是每轮识图都渲不出图，用户看不到任何产物。

**要改成**：由 attempt finalization / merge **共用同一个 renderer** 读取 aggregate `views`，把图写到 `attempts/NNN/renders/<expected_output_id>.png`，记录 **source output hash + render helper version + 每图状态/hash**。accepted 根目录下的别名只能是**便利副本，不能是唯一证据**。

**渲染失败不得继续伪装成「肉检材料齐全」**：对要求人工 review 的 run，应阻断 `review_complete`；是否阻断纯数值 gate① 可另定，但**必须留下机器可见的 failure artifact**。

### 3.2 O-3 · 精确输出文件名（低成本 P0）

**病灶**：`session_kickoff.md:51` 的通则 `<name>_view.json` 与同文件 `:57-65` 的示例表格自相矛盾；真正的规则在 `view_manifest.py`，对已经以 `_view` 结尾的 stem 是 identity ⇒ **图名以 `_view` 结尾的 case 必踩，读图器照通则做就会被拒收**。

**要改成唯一规范**：**只按 staging `input_inventory.json` 给出的 `expected_output_id` 写 `<expected_output_id>.json`**。静态表格只能作**非规范示例**，不得再次推导名字。

### 3.3 O-4 · OCR 锚点 / 3.3 亿像素（安全 P0 + 语义 P1）

**根因链**（已完整查明）：
- `src/agent/reading/schema.py:119-129` 的 `ocr_texts` **完全 untyped**；
- `guide.md:269-272` 的示例看起来是 metric local anchor，但 `Dimension.anchor` 的注释写的是 pixel（schema `:65-81`）⇒ **坐标载体语义不统一**；
- validator 只查 typed `room_labels` 的 anchor（`src/validator/checks/reading.py:212-318`），**不查 OCR**；
- renderer 把 OCR anchor 纳入画布 extent（`render_vector_to_png.py:50-77`），且在 `Image.new` 之前**没有任何像素预算**（`:85`）⇒ 真实产物 `1f_view/T1=[360,450]` 把一张约 10×20 m 的图撑爆成 3.3 亿像素。

**两层修复**：
- **立即（本批必做）**：renderer 的画布**只由结构几何 / 显式 trusted metric bounds 决定**，**annotation 不得扩张画布**；在分配之前**硬限** width / height / total pixels。
- **P1（本批不做，登记）**：把 OCR schema 版本化为显式 `anchor_m` 与 `anchor_px`（或 `{frame, point}`），legacy `anchor` 在 strict 下**不得猜单位**。

metric annotation 要按 trusted canvas bounds + 合理 margin 检查，越界 flag/block；pixel anchor **不进入 metric transform**。**⛔ 绝不能「clamp 之后放行」——那会隐藏坏数据。**

### 3.4 批 C 验收锁

| 锁 | fixture / 变异 | **必须断言** | 摘掉什么会红 |
|---|---|---|---|
| **L-40** aggregate render | isolation 只产出 `attempts/001/output.json`，根目录**没有** `*_view.json` | 生成 expected set 的 per-attempt renders；**每图的 source hash / render hash 齐全** | flat glob 依赖 |
| **L-41** render failure visibility | 向 renderer 注入异常 | review status 明确为 unavailable/blocked，**不得显示 complete** | best-effort 吞错 |
| **L-50** exact output id | source `foo_view.png`，inventory 的 expected 为 `foo_view` | **只接受** `foo_view.json`；`foo_view_view.json` **被拒**；kickoff 生成的文本引用的是 exact id | 文档再自行拼 `_view` |
| **L-51** OCR resource guard | 10×20 m 结构 + OCR metric anchor `[360,450]` | gate 报 frame/bounds 错；renderer 在 `Image.new` **之前**拒绝或改用 bounded canvas，**像素预算不超限** | annotation extent / 资源门 |
| **L-52** OCR frame separation | 同一段文字分别用 `anchor_px` 与合法 `anchor_m` | pixel anchor **不改变** metric canvas；metric anchor 按 trusted bounds 绘制 | 坐标载体重新混用 |

---

## 4. ⛔ 明令不许做的事（边界写死 —— 本项目三次栽在「边界写窄就被实现得同样窄」）

1. **⛔ 不得把 `stroke_dimension_consistency` 升为硬门**。四条 closure 阻断已足够验证政策档位；该检查源码自陈 advisory、要求人看图，**未做假阳性调查前升门 = 扩大误拒**。
2. **⛔ 不得原地修改**历史 `_run/view_manifest.json` / RunManifest / 历史 attempt / GT。历史修正一律走**版本化、可审签、hash-bound 的 replay overlay**。
3. **⛔ 不得以「当前样例转绿」为验收。** 每条守卫必须有**摘掉即红**的锁（零连带）。
   ⚠️ 既有教训：`score_vs_gt is not None` 那条锁**绿着，而判卷其实是拒的** ⇒ **断言必须落在 `payload.kind` 与具体分数行上**，不得落在「返回值存在」上。
4. **⛔ 不得让产品内容决定考卷**：`dimensioned` 是考卷属性，不许从产品的 `dimensions[]` 非空反推。
5. **⛔ 不得把 `dimensioned` 的修复做成「所有 N/A 一律计 miss」**——object-conditional 的 N/A（例如「零个 `dimension_derived` stroke」）是合法的，要保留且带机器可读的原因。
6. **⛔ 不得读 GT**（`case_tests/test_baseline/gt/`）。项目铁律：gt 只有 gate② judge 与人可读，gate①/执行器绝不 import。施工时如需 fixture，自己造，不得从 GT 拷数字。
7. **⛔ 不得顺手做批 D（typed grade 六 panel 恢复）与批 E（离线重判工具）**——已明确移出本批。
8. **⛔ 遇到欠规格的边界必须停下上报，不得自行降级为假设。** 本项目连续三轮 REWORK 的共同结构就是「机制选对、边界留给施工方猜」。
9. **⛔ 删除 / 覆盖 / push 需单独授权**（提交到本地分支可以，**不要 push**）。

---

## 5. 交付要求

### 5.1 切片与顺序

**批 B 与批 C 分开做、分开提交、分开审**（一个改执行信任事务，一个改交付面，性质不同）。

**顺序：先批 B → 停下写执行日志 → 再批 C。**

### 5.2 每批的交付物

1. **代码改动**（本地提交，不 push）。
2. **执行日志**落 `AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batch<B|C>_glm.md`，必须包含：
   - 改动清单（逐文件一句话说明为什么改）；
   - **neuter 自查表**：每条锁**临时摘掉其唯一对应的实现改动**，跑同一组锁，记录「恰好红哪一条 / 有无连带」，**然后恢复工作树**。⚠️ 要区分「锁绿」与「锁真绑」——**前者不算数**；
   - 全仓测试结果（见 5.3）；
   - **已知缺口的诚实登记**（例如 O-4 的 P1 部分本批不做）。
3. **「我当时的意思是……」不是可接受的交付说明。**

### 5.3 测试

- 中间轮只跑受影响子集；**交付前必须跑一次全仓**。
  ⚠️ 上一轮有一条真缺陷**只在全仓才抓得到**（施工方差点漏掉）。
- **当前基线：2055 passed + 10 xfailed，零红**（批 A 之后）。
- 全仓默认并行 `-n auto`；**⚠️ 本机内存只有 16 G**，`-n auto` 会起 16 个 worker（每个 350–700 MB），叠加其它席位会 OOM ⇒ **请用 `-n 6` 或 `-n0`**。（并行与串行的节点集合已被机械证明逐字节相等；**⛔ 但永远不许加 `-m` 过滤**。）

### 5.4 会话纪律（本项目当日两次栽过）

- **做完一件存一件、先落骨架再补**——不要攒到最后一次性写。会话被回收过两次，两次都是攒着写，结果零交付、同样的活白做两遍。
- 骨架里的「暂定结论」**不得当最终结论汇报**。

---

## 6. 审阅安排

- **施工审 = GPT 侧（sol）交叉对抗审**，升一档，写稿的不审自己的稿。
- **orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑每一条 neuter**，是唯一权威门。
