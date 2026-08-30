# 跨家族裁决书 · ②-1c（AnswerCompiler 双形式 + 依赖闭包 + 出口全检）

- **日期**：2026-08-30 · **审阅方**：GLM 家族（交换审）· **施工方**：GPT 家族
- **请求书**：[`../request/2026-08-30_o21c_crossreview_glm.md`](../request/2026-08-30_o21c_crossreview_glm.md)
- **送审对象**：`407fa44` · **基线 `88ea056`** · 一律以 `git diff 88ea056..407fa44` 为准。
  全部变异/攻击实验在 `git archive 407fa44` 的 **/tmp/o21c_review 副本**上跑（本审**未动主树任何被审文件**，
  真实答案根 `case_tests/test_baseline/gt/` 零字节写入；假答案根一律经 `monkeypatch ac.REPO_ROOT` 构造）。
  审毕时主树 HEAD `667d2ec`、`src/`/`tests/` 相对 407fa44 **零 diff**（实测 `git diff 407fa44..667d2ec --stat -- src/ tests/ scripts/ case_tests/` = 空）。

---

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 条 · 不阻断 7 条）

A1 的攻击**成立**（自洽伪造三件套全绿放行、伪造几何直接流入编译答案——实测数字见 §一），
但它是**派工单盘面上已如实标 ⛔ 未做的 sol 返工条①**，且执行记录的措辞没有冒领外部锚
（它说的是「单边 schema-valid 篡改会红」，这句话实测为真）。按请求书 §A1 自己给的判定框架，
这不构成本单阻断；本裁决给出「已兑现 / 仍空着」的分工边界重述（NF-1）。
A2/A3/A4/A5/A6 逐一实测：**没有发现一道门量错了自己声称的量**；A3 那道锁在真实数据上 no-op
（与主控读数一致），但我实测该病今天**结构上不可达**（清空全部判断性 readouts 后编译输出逐位不变），
并给出严格更强的替代锁形态（NF-4）。受影响子集 23 文件两遍 **471 passed / 1 xfailed** 一致。

---

## 〇、独立复核记录（全部命令在 /tmp/o21c_review，除注明外）

| 项 | 我方读数 | 对照 |
|---|---|---|
| 受影响子集 23 文件（主树 `-n auto` ×2） | **471 passed / 1 xfailed**（221s / 222s） | 主控全量 3378 绿 ✅（未重跑，席位纪律） |
| 真实 `gt/` 下 facts 目录 | **0 个**（`find …/gt -name facts -type d` 空） | 与请求书 A2 一致 ✅ |
| staging 三件套键名含 `basis` | as_measured/as_signed/revisions **各 0 个**（递归扫键名） | 与主控读数一致 ✅ |
| `as_signed` 值侧 `wall_axis` 4 处 | 全是诊断代码名 `"tarch_wall_axis_snapped"`（`grep -o` 实测），非 basis 载体 | —— |
| promote_gt_v3 与 facts | `grep -c facts gt_promotion.py` = **0**；staging 只写 `gt.json`/`renders`/`review` | A2.1 ✅ |
| request_sha256 复算 | sm25 `ae272a73f6331e3a…` MATCH · sm24 `ae0fec087ef2a048…` MATCH；`gt_sources/` 本单零改动 | 验收 10 ✅ |
| NF-2/NF-3 前提 | diff 中零并发写/retry 新增（grep thread/retry/concurrent/asyncio 增行 = 0） | 前提成立 ✅ |
| 范围外文件 | diff 18 文件全部落在 src/tests/scripts/case_tests/AI_agent 预期清单内 | ✅ |

---

## 一、A1 · ⭐⭐⭐ 出口全检验的是**自洽**，不是**权威**（攻击成立，判定不阻断）

**攻击**（/tmp 副本，`monkeypatch ac.REPO_ROOT` 指向假答案根）：
取合成三件套，把 north 内面 `A3.const 57600 → 58300`（**7 cm**）、`wall-north.face_lo` 同步、
partition 与 `A9/AA` 的 `along_max` 同步拉长（否则 `derive_as_signed` 的 wall↔face 对账先红——
伪造者完整重算即可通过），重算 `revisions.as_measured_content_sha256`，重新 `derive_as_signed`，三件写入假答案根。

- **`read_facts_for_compilation` 全绿放行**（无任何 raise）。
- **伪造几何直接流入编译答案**：form A 的 `F1-left/F1-right` 顶边 `58800 → 59150`（+350 = 厚度变化半宽），
  counts 两边完全相同（`projected_zones: 2, na_zones: 0`）——**没有任何 NA 提示差异**。
- `compile` 的 `_assert_inputs_belong_together` 五查哈希同样不拦：攻击者**保留原 `source_dxf_sha256`
  与 `request_sha256`** 即通过（那五查是「三件套 vs request 互相」，不是「vs 磁盘签字件」）。

**对三问的回答**：① `verify_as_signed_reproduction` 量得准（逐字节重derive比较，单边篡改实测三方向全红，
见 A2.3）；② ⭐ 它量的「三件套互相」这个整体**可以整体被换掉**——伪造者整套重算即换；③ 没锁的方向 =
**对外部信任根（原始 DXF / `gt_sources/` 签字 request / converter 指纹）的再对照**，一行都没有。
为什么没有：sol 返工条①（外部获授权指纹锚）在派工单盘面上标 ⛔ 未做——**不是忘了锁，是这一半没开工**。

**F-146「已实现」的重述（NF-1 详见下）**：
- ✅ **已兑现**：答案根读侧的**内部自洽全检**——三件套任何一个被单独动、或任一 hash 链断裂，读侧必红；
  且不关心 bytes 怎么进来的（这正是比入口收窄强的那一半）。
- ⛔ **仍空着**：对伪造者整套重算的防线。它必须与「facts 进答案根的**任何**动作**同期**落地，
  否则出口全检是一道「格式正确的伪造也能过」的门。

**文字核对**（请求书要求先判这条）：执行记录 §二.1 写「入口外写入的 schema-valid 篡改会红」——
实测为真（单边篡改三方向全红）；`gt_facts_staging.py` docstring 更新明确写出口检「不关心 HOW bytes arrived，
only whether what is there NOW reproduces」。**没有冒领外部锚。** banner 短语「出口全检已实现」
单独读容易读宽，由本裁决的重述收口。

## 二、A2 · 出口全检今天零真实流量 + 回退支跨根 + 三方向篡改

1. **零流量属实**：`gt/` 下 0 个 `facts/`（实测）；`promote_gt_v3` 的 staging 目录只建
   `renders/`、`review/`、写 `gt.json`（`grep -c facts gt_promotion.py` = 0）。
   ⇒ 今天唯一真实读路径 = `answer_compiler.py:1030-1031` 的 staging 回退；
   答案根那一支只有三条合成夹具锁在跑。判：**「没跑到那一段」而非「没尺子量」**——门存在、
   可观测（测试里红绿皆可），但生产流量为零，且**目前不存在任何会把 facts 送进答案根的代码路径**
   （promote 不知道 facts 存在）。它是为未来接的保险丝：**将来扩 promote 或人工落 facts 时，
   这道门才开始有真实流量，而那时外部锚必须已经在**（与 NF-1 绑定）。
2. **回退支跨根（实测坐实）**：`monkeypatch ac.REPO_ROOT` 指向不存在的根后
   `read_facts_for_compilation("sm25-L_anchor")` 依然**成功返回真实数据**——回退调用的
   `gt_facts_staging.read_facts_candidate` 用的是 gt_facts_staging 自己未 patch 的根。
   今天三条 exit_gate 测试都先建了 facts 目录、不走回退 ⇒ **无现存污染**；生产不 patch ⇒ 咬不到。
   判：测试隔离瑕疵（NF-3）。
3. **三方向篡改（实测）**：`as_measured`（face const +1）/ `revisions`（magnitude 0.1mm→9.9mm）/
   `as_signed`（along_max −1）**各自单边篡改全部红**（`AsSignedReproductionError`）。
   原测试只锁了第三方向，我补齐前两个方向：**全红，无缺口**。

## 三、A3 · basis-scrub 锁：真实载体不存在 ⇒ no-op，但病今天结构上不可达（替代形态已实测）

- 主控读数复核一致：三件套**键名含 `basis` = 0**；值侧 4 处 `wall_axis` 全是诊断代码名。
  ⇒ scrub 在真实数据上是 no-op，`with/without_basis` 的唯一差异 = 测试自种的 diagnostics blob。
  这道门对存量**恒绿**。
- **但**（三问②③的回答）：A3.1「真实载体」= `converter_readouts` 的判断字段
  （`diagnostics`/`gates`/`unresolved_opening_carriers`/`face_groups_with_a_split_const`/
  `jamb_cap_bands_missing_a_face_line`/`axis_snapped_lines`）——没有一个叫 basis。
  A3.2「别的方向」我做了**比 scrub 强一个量级的反事实**：把真实 sm25 as_signed 的上述判断字段
  **全部清空**（schema 的对账 validator 挡住了更激进的清空——这本身是道好门），form B 编译输出
  **逐位不变**（zones/openings/counts/derivation 全同；F1 `11 projected`、F2 `14 projected`）。
  ⇒ 「编译器偷吃 converter 坍缩判断」今天**结构上不可达**：`_classify_boundary` 确实只吃几何。
  另有 `test_rule_5` 锁住「form B 输出依赖 `_classify_boundary` 返回值」的分辨力方向。
- **A3.3 有牙替代形态（已验证可行，建议下单替换或加一条）**：把我刚跑的反事实写成锁——
  「真实 sm25 上清空全部判断性 readouts 字段 ⇒ 编译输出逐位不变」。它覆盖**任何名字**的载体，
  而不是键名含 `basis` 的载体。验收 2 的意图（编译器不吃现成判断）实际已结构性成立，
  该改写的是锁的形态，不是编译器。

## 四、A4 · band 并集 == direct 全集：**结构的**，不是语料的（判：恒等式 + 回归方向有牙）

`_build_wall_bands`（`tarch_normalize.py:655-681`）成员**只从** `cap_handles_v/h` 取
（「多出 direct 集合」方向结构上不可达）；而 `caps_v` 与 `cap_handles_v` 在
**同一行语句块同步写入**（`tarch_normalize.py:621-622`），每个 direct entry 必被遍历收进某 band
（「丢失」方向不可达）。⇒ 恒等式成立是遍历面的数学后果。
锁的剩余分辨力 = 防**未来**改 partition（按厚度过滤 band、跳 span）丢 handle——这正是它该干的活；
`assert direct` 非空防零存货（F-147 形状），sm24+sm25 各参数化、两遍绿。
facts 侧 transport 保真（`jamb_cap_bands` 序列化不丢 handle）由
`test_facts_adapter_reproduces_the_live_as_received_question_book_and_score` 的
**ledger 整体逐位相等**间接锁住（含 `would_be_excluded_by_converter_length_rule` 计数，sm25 两 view）。
反事实锁（清空 bands 只改审计数、targets 逐位不变）也在。**此面通过。**

## 五、A5 · 闭包六条：分母是参照侧；恒等式判定 + 变异实测

1. **`coverage_expected` 来源**：zone 期望 = `plan_view.zone_intent.expected_count`
   （`answer_compiler.py:389`，**request = 已签字件**，参照侧 ✅）；
   reading 真正对外的分母 = `denominator_from_facts` 的 targets，输入 = 签字后的 as_signed + request 参数
   （参照侧 ✅）。**不违反** [[invalidation-blast-radius-must-be-scoped]]。
   ⚠️ 唯一产品侧分母：`opening_geometry` 的 expected = `len(view.openings)`（facts 自数）——
   但这是编译答案的自述指标，不是判分分母；判分 opening 分母 = `opening_targets`（facts 派生）。可接受。
2. **恒等式判定**：`coverage_na = expected − available` 与 `available` 由同段代码产出
   （`answer_compiler.py:960-996`）⇒ 构造点恒等。validator 的牙 = 手搓 `MetricResultV1` 绕过生产者时
   （实测三种不一致行全拒：`shrank_denominator` ×2、`status_disagrees` ×1）。
   **防「编译器虚报 available」的是行为锁**：/tmp 变异（`projected` 计数在存在 NA zone 时 +1）
   ⇒ `test_rule_1`、`test_rule_3`、`test_1b_real_sm25` 等 **4 条测试红**（4 failed / 10 passed）。
   分工成立，非缺陷。
3. **规则 4 边界**：歧义判据 = `unresolved_opening_carriers`（converter 产品侧判定，**签字时人过目**）
   ∨ `carrier_wall_ids` 空；半径显式写死在该 NaRecord 的 `affected_metrics=["opening_geometry"]`
   （`answer_compiler.py:917-923`），ring 不受牵连（rule_4 测试锁 counts 双 available）。
   「局部」半径是**显式声明**的（rule 枚举 + affected_metrics 字段），不是实现冒出来的。通过。

## 六、A6 · 记账与禁令核对

1. **独立确认**：`answer_compiler.py` 与 `as_drawn/denominator.py` **都不 import** `reading_grade`
   （grep 零命中）；真正的覆盖来自 `tests/test_denominator_from_facts.py:15` 直接 import。
   执行档那句因果更正属实。删 allowlist 方向诚实。
2. **下游后果（含对请求书问法的一处修正）**：实测 `uncovered_allowlist` 在 `affected_tests.py` 的
   **选择逻辑里零消费**（加载进 rules 后只有 `full_scope` 被 `is_full_scope_path` 用）；
   删条目前后 `--changed src/agent/judge/as_drawn/reading_grade.py` 的子集**一字不差**，都是
   `tests/test_denominator_from_facts.py` 一个文件。⇒ 请求书「删 allowlist 使半径缩小」的表述
   **问错了机制**（该条目不参与选择）；正确的问法是「reading_grade 的测试覆盖是什么」。
   答案：全仓唯一 import 它的测试 = 本单新增的**同分锁**，它对「frozen 与 live 双侧同错」**不敏感**
   （grade 打分逻辑单边退化不会红）。⇒ `grade()` 至今**无独立行为锁**，②-2 判分单必须补
   （NF-6）。同分锁的价值（frozen==live）真实存在，方向是改善。
3. **验收 10**：`compute_request_sha256` 独立复算 sm25/sm24 均 MATCH（§〇表），`gt_sources/` 零改动。

---

## 七、Findings 汇总

### 阻断（0 条）

无。

### 不阻断（7 条）

| # | 内容 | 证据 |
|---|---|---|
| **NF-1** | ⭐⭐⭐ 出口全检 = 自洽检 ≠ 权威检：整套重算的伪造三件套全绿放行，7 cm 几何改动直接流入 form A 答案（58800→59150）。外部锚（DXF/gt_sources/指纹再对照）为零，且 `compile` 五查是「三件套 vs request 互相」。**必须**与「facts 进答案根的任何动作」同期落地外部锚；执行记录未冒领（单边篡改红实测为真） | §一；`/tmp/o21c_review/a1_attack.py` |
| **NF-2** | 出口全检今天**零真实流量**：`gt/` 零 facts 目录，promote 不知道 facts 存在（grep=0）。门是未来保险丝；「已实现」≠「已在真实路径生效」，banner 引用时勿读宽 | §二.1 |
| **NF-3** | 回退支跨根：patch `ac.REPO_ROOT` 后 staging 根不跟随（实测 patch 到不存在根仍读到真实 sm25 数据）。今天三条 exit_gate 测试均不走回退，无污染；生产不受影响。将来写「答案根为空」类测试时先 patch `gt_facts_staging` 的根 | §二.2 |
| **NF-4** | basis-scrub 锁在真实数据 no-op（三件套零 basis 键），量不到它声称的量；但该病结构上不可达（清空全部判断性 readouts ⇒ form B 输出逐位不变，实测）。**建议**把该反事实写成锁替换/并列——覆盖任何名字的载体，严格强于 scrub 键名 | §三 |
| **NF-5** | `available+NA==expected` 是构造点恒等式；validator 只对手搓行有牙（三种不一致行实测全拒），防虚报靠行为锁（变异实测 4 红）。分工成立，记录备查 | §五.2 |
| **NF-6** | `reading_grade.grade()` 无独立行为锁：唯一测试 import 者是本单同分锁，对双侧同错不敏感；且 allowlist 条目在 affected_tests 选择逻辑中零消费（删它对子集零影响——请求书 A6.2 的机制表述需按此修正）。②-2 判分单补行为锁 | §六.2 |
| **NF-7** | `read_facts_for_compilation` 的调用契约缝：它回三件套**不回 request**，request 由调用方自备且五查只对「三件套 vs request」。将来接线时须定「request 从哪读、谁验它就是 gt_sources 那份」——归 NF-1 外部锚的同一半 | §一 |

### 缝隙对账（请求书 §三 要求点名）

两份单子切分清楚；我补一条**双方都没写**的缝 = NF-7（读接口的 request 配对契约）。
correction 侧（②-2）、edge boundary_condition（②-1d）、F-128/F-132 维持范围外裁定。

---

## 八、方法论备注（三问逐门）

| 门 | ①准不准 | ②量的东西能否被换掉 | ③没锁的方向与原因 |
|---|---|---|---|
| `verify_as_signed_reproduction`（读侧） | 准（逐字节重derive） | **能**：整套重算即换（A1 实测） | 对外部信任根的锚——没开工（返工条①），非「一加就红」 |
| scrub-basis（验收 2） | 对存量不适用（零载体） | 载体可换名——但今天结构不可达（清空判断面输出不变） | 「非 basis 命名通道」；替代反事实形态已验证（NF-4） |
| band 并集 == 全集 | 准 | band 构造可被未来改丢 handle | 「多出」方向：结构不可达（成员只从 direct map 取） |
| coverage 恒等 validator | 准（手搓行全拒） | available 本身可虚报 | validator 对生产者恒真；由行为锁补（变异 4 红实测） |
| affected_tests | 准 | —— | allowlist 零消费（实测），条目增删不改变子集 |

**对派工单攻击面本身的判定**：六个攻击面问法全部成立且有效——A1/A3/A5 都被实测推进出比请求书预判更完整的结论；唯 A6.2 的机制表述（「删 allowlist 使半径缩小」）与工具实际语义不符，已在 §六.2 给出正确问法。本项目派工方题错累计 48/48 的统计在本单**未再 +1**。

---

## 九、可复现命令清单（均在 /tmp/o21c_review，除注明外）

```bash
git -C /workspaces/EnergyPlus-Agent-dev archive 407fa44 | tar -x -C /tmp/o21c_review && cd /tmp/o21c_review

# A1 自洽伪造攻击（exit gate 全绿 + 几何流入答案 + 三方向单边篡改全红）
python a1_attack.py

# A2.2 回退支跨根
python -c "import src.agent.judge.answer_compiler as ac; from pathlib import Path; \
  ac.REPO_ROOT=Path('/tmp/nonexistent'); print(ac.read_facts_for_compilation('sm25-L_anchor')[0].source_dxf_label)"

# A3 真实载体扫描 + 判断面清空反事实
grep -c basis case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/*.json   # 0
python - <<'EOF'   # 清空 diagnostics/gates/unresolved_opening_carriers/face_groups_with_a_split_const/
                   # jamb_cap_bands_missing_a_face_line/axis_snapped_lines ⇒ 编译输出逐位不变
...（脚本见裁决过程，断言 zones/openings/counts/derivation 全等）
EOF

# A5 变异（虚报 projected +1）⇒ closure/profiles 4 failed（rule_1/rule_3/1b_real_sm25 等）
sed -i 's/projected = sum(zone.vertices is not None for zone in zones)/& + (1 if any(z.vertices is None for z in zones) else 0)/' src/agent/judge/answer_compiler.py
python -m pytest tests/test_answer_compiler_closure.py tests/test_answer_compiler_profiles.py -n auto | tail -2
git -C /workspaces/EnergyPlus-Agent-dev archive 407fa44 src/agent/judge/answer_compiler.py | tar -x -C /tmp/o21c_review   # 恢复

# A6 allowlist 前后对照（子集一字不差）
git -C /workspaces/EnergyPlus-Agent-dev show 88ea056:scripts/tool_scripts/affected_tests_rules.yaml > scripts/tool_scripts/affected_tests_rules.yaml
python scripts/tool_scripts/affected_tests.py --changed src/agent/judge/as_drawn/reading_grade.py | tail -1

# 受影响子集（主树，两遍）
python -m pytest -p no:cacheprovider -q <23 文件，见请求书> -n auto   # 471 passed / 1 xfailed ×2
```

—— GLM 跨家族审阅席位 · 2026-08-30
