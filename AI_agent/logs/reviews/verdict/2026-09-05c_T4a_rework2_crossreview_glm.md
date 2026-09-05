# 裁决 · T4-a 返工 2 跨家族审（GLM 家族复核席）

- 日期：2026-09-05
- 施工方：Claude 家族施工席
- 复核方：GLM 家族复核席
- 审对象：`git diff df57f9a3..90c9e644`（三笔：`8cd7df01` 源+锁 · `4d0b99ad` 执行报告+docstring 中和 · `90c9e644` 钉最终读数）
- 工作树：`/tmp/t4arw2_review_glm`，detached `90c9e644`
- ⚠️ 声明：本线前两轮为本复核方家族所做，本轮施工方为 Claude 家族；本裁决只按派工单判据判，未对前两轮做法作任何偏袒或加严。

## 一、裁决

**APPROVE-WITH-FINDINGS · 阻断 0 / 不阻断 3**

派工单的唯一阻断性要求——把「**所有成功解析输入的集合 == live key 集合**」这个性质本身立成锁（出口全检，⛔ 不是入口收窄）——已经成立，且是**我方独立复现**成立的：

- 新增出口 `_resolve_backed_obligation` 对**原始** `debt.obligation` 做「载体是精确 plain dict · 值是精确 plain str · 值是注册表精确键」三道判断，**先于且独立于**可被替换的 seam；两条销账路径（`assert_obligations_backed` / `redeemable_debt_ids`）全部改走它；
- **上一轮的原反例（seam 外挂与活键无字面相似的兼容映射）在已修树上双入口响亮拒**（我用自选 alias 串 + 直接属性赋值的安装方式独立重造，`BACKING_REFUSED=OBLIGATION_UNBACKED` / `REDEEM_REFUSED=OBLIGATION_UNBACKED`，且 `SEAM_ACCEPTS_ALIAS=...` 证明变异确实生效）；
- **红锚成立**：同一探针跑在旧源 `df57f9a3` 上 `BACKING=PASS` / `REDEEMED=(...)`（缺陷真实存在），且新 10 项锁在旧源上 **5 failed**（4 项 R1 `DID NOT RAISE` + 1 项 R3），与施工方自报逐字一致——分得清「锁有牙」与「变异没生效」；
- **换同形输入**：我自设三条与施工方四条**均不同形**的扩法（吞一切拒绝回落首键 / 命名空间前缀剥除 / 注册表 `__missing__` 载体），三条全部被双入口响亮拒（前两条 `OBLIGATION_UNBACKED`，载体方向 `DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT`），证明锁的是**这一类**；
- **锁的断言主语全是性质**（`OBLIGATION_TYPE_NOT_PLAIN_STR` / `OBLIGATION_UNBACKED` / 规则生成的 `foreign not in ...` / `widened_key == canonical`），AST 级提取三个新测试函数的全部断言表达式，**零**扩法名字面量。

对施工方自报最薄弱处的正面裁定（复核指令点名要求）：**诚实边界，登记不追加是正确处置；但自报对该边界的表述有一处画宽了**（详见 §四——「把消费者替换成信任 seam 的旧版本」这个方向实测**恰恰被 R1 抓住**，真实盲区只剩「瞬时 monkeypatch 且不留源码痕迹」这一对任何行为锁都不可见的形态）。已记为不阻断 finding #1，防止后人引用该自报时高估缺口。

### 开工自检原文

命令：

```bash
cd /tmp/t4arw2_review_glm && pwd && git log --oneline -1 && git status --porcelain
```

输出：

```text
/tmp/t4arw2_review_glm
90c9e644 T4-a rework2: pin authoritative full-suite readout to final HEAD 4d0b99ad
```

（`git status --porcelain` 空输出，树干净。）

## 二、三件必做

### #1 原反例复现（自己重造，⛔ 未照抄施工方交件写法）

我的安装方式 = **直接模块属性赋值 + finally 恢复**（施工方交件与上一轮 GPT 裁决均用 `patch.object` + `dict.get` 闭包）；alias 串自选 `old_manager_moniker`（与活键 `elevation_chain_spans_whole_building` 零词元重叠）。

**已修树（90c9e644）**命令原文：

```bash
python - <<'PY'
from pydantic import ValidationError
import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import ArtifactPointerV1, EvidenceDebtV1
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0
canonical = sorted(osm.DEBT_REDEMPTION_REGISTRY)[0]
alias = "old_manager_moniker"
assert alias not in osm.DEBT_REDEMPTION_REGISTRY
try:
    EvidenceDebtV1.model_validate(dict(debt_id="glm_probe_alias",
        kind="other_known_missing", channel=None, affected_refs=(),
        description="glm probe", obligation=alias))
except ValidationError as exc:
    print("SCHEMA=" + next(e for e in exc.errors()
          if e["loc"] == ("obligation",))["type"])
src_identity = osm.ElevationSourceIdentity("glm_input", CONTRACT_AS_DRAWN_ELEVATION_V0, "b"*64)
ref = ArtifactPointerV1.model_validate(dict(input_id=src_identity.input_id,
    source_contract_id=src_identity.source_contract_id,
    source_output_sha256=src_identity.source_output_sha256,
    json_pointer="/calibration"))
debt = EvidenceDebtV1.model_construct(debt_id="glm_probe_alias",
    kind="other_known_missing", channel=None, affected_refs=(ref,),
    description="glm probe", obligation=alias)
executed = osm.ExecutedRedemption(canonical,
    osm.DEBT_REDEMPTION_REGISTRY[canonical], src_identity)
real_seam = osm.redemption_row_for_obligation
def compat_shim(name):
    return real_seam(canonical if name == alias else name)
osm.redemption_row_for_obligation = compat_shim
try:
    print("SEAM_ACCEPTS_ALIAS=" + repr(osm.redemption_row_for_obligation(alias)[0]))
    try: osm.assert_obligations_backed([debt]); print("BACKING=PASS")
    except osm.OpeningSynthesisError as e: print("BACKING_REFUSED=" + e.code)
    try: print("REDEEMED=" + repr(osm.redeemable_debt_ids([debt], executed=executed)))
    except osm.OpeningSynthesisError as e: print("REDEEM_REFUSED=" + e.code)
finally:
    osm.redemption_row_for_obligation = real_seam
try: osm.redemption_row_for_obligation(alias); print("RESTORED=GREEN_UNEXPECTED")
except osm.OpeningSynthesisError as e: print("RESTORED_SEAM=" + e.code)
osm._assert_registry_well_formed(); print("RESTORED_AUDIT=PASS")
PY
```

输出原文：

```text
SCHEMA=literal_error
SEAM_ACCEPTS_ALIAS='elevation_chain_spans_whole_building'
BACKING_REFUSED=OBLIGATION_UNBACKED
REDEEM_REFUSED=OBLIGATION_UNBACKED
RESTORED_SEAM=OBLIGATION_UNBACKED
RESTORED_AUDIT=PASS
```

**红锚（旧源 `df57f9a3`）**：为不动审对象工作树，我用 `git worktree add /tmp/t4arw2_redanchor df57f9a3 --detach` + 拷入新版测试文件（审后已 `git worktree remove`，主树 `git status --porcelain` 保持空）。同一探针在旧源上输出：

```text
SCHEMA=literal_error
SEAM_ACCEPTS_ALIAS='elevation_chain_spans_whole_building'
BACKING=PASS
REDEEMED=('glm_probe_alias',)
```

旧源上跑本轮 10 项新锁（`__file__` 已自证落红锚树）：

```text
FAILED tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[external_compat_table-external_compat_table]
FAILED tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[prepended_normalisation-prepended_normalisation]
FAILED tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[one_to_many_silent_pick-one_to_many_silent_pick]
FAILED tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[unicode_nfkc_fold-unicode_nfkc_fold]
FAILED tests/test_t4a_rework1_resolution_lock.py::test_query_side_str_subclass_obligation_is_refused_at_the_exit
5 failed, 5 passed in 1.10s
```

（失败均为 `Failed: DID NOT RAISE OpeningSynthesisError`；R2 的 5 项在旧源上绿——旧 binding 经 seam 也拒域外串，与 R2 锁的语义一致，不构成异常。）**双锚闭合：缺陷在旧源上真实存在且被退休，新锁在该世界上红，在已修树上绿。**

### #2 换同形输入（自设三条，与施工方四条均不同形）

施工方用的四形：外挂兼容表 / strip+casefold 前挂 / 前缀收集静默选一 / NFKC。我的三条：**(A) 吞一切拒绝回落首键**（任何 `OpeningSynthesisError` 都回落 `sorted(registry)[0]`）、**(B) 命名空间前缀剥除**（接受 `"ns#"+key`）、**(C) 注册表 `__missing__` 载体**（`dict` 子类对任意未知键回落活行）。每条先自证 foreign 不在注册表、再自证变异在扩宽层生效、再断言双销账入口：

输出原文：

```text
A_swallow_all:MUTATION_TOOK=True
A_swallow_all:backing_REFUSED=OBLIGATION_UNBACKED
A_swallow_all:redeem_REFUSED=OBLIGATION_UNBACKED
B_ns_strip:MUTATION_TOOK=True
B_ns_strip:backing_REFUSED=OBLIGATION_UNBACKED
B_ns_strip:redeem_REFUSED=OBLIGATION_UNBACKED
C_missing_carrier:MUTATION_TOOK=True
C_missing_carrier:backing_REFUSED=DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT
C_missing_carrier:redeem_REFUSED=DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT
RESTORED_SEAM=OBLIGATION_UNBACKED
RESTORED_AUDIT=PASS
```

三条全拒 ⇒ 锁的是**类**，不是实例。

### #3 查靶子（断言里不得出现具体扩法名字）

AST 级提取本轮三个新测试函数的全部断言**表达式**（`node.test`，不含 message 位）：

```text
ASSERT_LITERALS_MATCHING_WIDENING_NAMES = []
test_widened_seam_cannot_make_the_binding_back_a_non_key_input:619: foreign not in osm.DEBT_REDEMPTION_REGISTRY
test_widened_seam_cannot_make_the_binding_back_a_non_key_input:633: widened_key == canonical
test_widened_seam_cannot_make_the_binding_back_a_non_key_input:637: caught.value.code == 'OBLIGATION_UNBACKED'
test_widened_seam_cannot_make_the_binding_back_a_non_key_input:640: caught.value.code == 'OBLIGATION_UNBACKED'
test_schema_bypassed_obligation_outside_the_domain_is_refused_loudly:682: caught.value.code == 'OBLIGATION_UNBACKED'
test_schema_bypassed_obligation_outside_the_domain_is_refused_loudly:685: caught.value.code == 'OBLIGATION_UNBACKED'
test_query_side_str_subclass_obligation_is_refused_at_the_exit:717: alias in osm.DEBT_REDEMPTION_REGISTRY
test_query_side_str_subclass_obligation_is_refused_at_the_exit:722: caught.value.code == 'OBLIGATION_TYPE_NOT_PLAIN_STR'
test_query_side_str_subclass_obligation_is_refused_at_the_exit:725: caught.value.code == 'OBLIGATION_TYPE_NOT_PLAIN_STR'
```

`owner_b4` 全 tests/+src/ 的 grep 命中仅一处：`tests/test_o22m2_evidence_contract.py:2165`，为 `ee86f5e1`（两轮前的 T4-a T3+T4）引入的 schema 闭枚举测试「an arbitrary free string」**输入样例**（断言主语是 `pytest.raises(ValidationError)`），本轮 diff 未触碰该文件——非本轮新增、非断言靶子，不违禁令（记不阻断 #3 备查）。R1 的参数化 `label` 只出现在 assert 的 message 位，不进断言条件。

## 三、派工单 §三 六条逐条对账

### #1 ⭐⭐⭐ 「成功解析输入集合 == live key 集合」有锁 —— **通过**

§二#1 双锚 + §二#2 三条自设同形全部变红（binding 双入口响亮拒）；锁形式 = 出口全检（对无界前像用「原始值直接查不可变 plain-dict」的后置条件替代枚举），不依赖枚举输入；断言零扩法名（§二#3）。派工单列的三种已知无效解（往近错族加变形 / 再加类型钉 / 把 `owner_b4` 写黑名单）一个都没走。

### #2 ⭐⭐ schema-bypass 的债不能被静默退休 —— **通过**

独立探针（自选域外值 `glm_selfchosen_out_of_domain_value`，不在 R2 的 5 个参数值内，`model_construct` 造债、无扩法）：

```text
BACKING_REFUSED=OBLIGATION_UNBACKED
REDEEM_REFUSED=OBLIGATION_UNBACKED
```

R2 锁（5 参数化：dissimilar/numeric/empty/path_like/first_live_reversed，值为规则生成且收集期自证不撞键）随 38 项全绿。R2 走的是「让它核原始值」的正面修法，不需要豁免论证。

### #3 ⛔ 没有为让锁红而把缺陷造回来 —— **通过**

- `git diff --stat df57f9a3..90c9e644 -- src/` 仅 `opening_synthesis.py`（+92/−18）；`evidence_contract.py` + `evidence_adapters.py`（契约 + 10 个 mint 点）`--exit-code` 零 diff（`CONTRACT_AND_MINT_CODE_DIFF=NONE`）。
- seam 本体（`redemption_row_for_obligation`，现 :481-551）**零改动**：精确 membership + 精确 index + claimant 计数原样；生产代码里对该 seam 的调用点仅剩**定义处 + helper 末尾**两处（grep 实证），即销账路径上 seam 只经出口到达。
- 新增行中含 `alias/casefold/normalis*` 等词的 5 处命中经逐行核全为 docstring/注释/错误消息文本，无一可执行归一化；helper 本体只做 `type() is dict` / `type() is str` / `in` 三个精确判断 + 一次 seam 调用。

### #4 上一轮已通过的不退化 —— **通过**

- 上一轮点名的四把行为锁独立点跑 `4 passed`（闭枚举 / 接线不靠前缀 / 无处理器响亮 / 注册表行是接线不是装饰）。
- AST 扫 `startswith` 与上一轮裁决**逐字一致**：`STARTSWITH_CALLS_IN_SRC=33`、债 receiver 0、`opening_synthesis.py` 内仅 :420 的 `other`/`key`（注册表审计排序，非接线）。
- B4 源绑定：diff 中 `def binds` / `affected_refs` / `source_output_sha256` 零触碰（grep 空）。
- **上一轮那 28 项锁仍全绿**：本文件现收集 **38 tests**（= 28 + 10 新），与 `test_b4_opening_synthesis.py` 同跑 `62 passed in 1.04s`。
- ⭐ **`_refusal_gone` → `_refusal_gone_at_seam` 的谓词收窄（施工方已主动披露）——我裁定正当**，理由三条：① 电池本体 `test_near_miss_obligations_are_refused_on_every_entry` **未收窄**（diff 零触碰，仍断言 seam + 双 caller 三入口全拒），收窄的只是 M1/M2/M3/M6 demo 里「扩法是否生效」的**度量谓词**；② 旧谓词（三入口全接受才叫 refusal gone）在「binding 恒拒非键」的新世界里恒 False，不收窄会假红——「binding 不再跟 seam 走」正是本轮修好的性质；③ binding 侧该性质由**更强的** R1 直接断言（双入口响亮拒 + 变异生效自证），不是裸露。记不阻断 #2 备案。

### #5 零恒真断言 —— **通过**

对改动测试文件做上一轮同款 AST 扫描 + 新增行文本扫：`VACUOUS_ASSERT_SUSPECTS=[]` / `ADDED_ASSERT_TEXT_SCAN=NO_MATCH`。且红锚（旧源 5 × `DID NOT RAISE`）即这些断言可失败的直接证据。

### #6 全量绿、逐位闭合 —— **通过**

规定命令（环境自证 + pytest 同一条）输出原文：

```text
/tmp/t4arw2_review_glm/src/agent/correction/evidence_contract.py
/tmp/t4arw2_review_glm/src/agent/correction/opening_synthesis.py
3819 passed, 2 skipped, 13 xfailed, 211 warnings in 489.12s (0:08:09)
```

exit 0、summary 行存在；**按实际收集数核**：resolution-lock 文件 `38 tests collected`，新增 10 = 4（R1 参数化）+ 5（R2 参数化）+ 1（R3）；`3819 = 3809 + 10`，`2 skipped / 13 xfailed / 0 failed` 与基线逐位一致；与施工方自报的两次读数（同 HEAD 行为等价 + 最终 HEAD）一致。两个 `__file__` 均落本工作树。

## 四、对「拦不住替换 binding 消费者」的正面裁定

**裁定：诚实边界；显式登记、不追加，是正确处置。但自报对该边界的表述有一处画宽了（不阻断 #1）。**

我用三个实验把边界量出来（均为进程内 monkeypatch + finally 恢复，树零改动）：

| 变异形态 | R1 在场时 | 证据 |
|---|---|---|
| seam 扩宽（本轮反例形态，源码层或运行时持续） | **红** | §二#1 已修树探针 + R1 测试本体 |
| 消费者被替换成信任 seam 的旧版（**源码层**） | **红** | 红锚 worktree = 该世界，4 项 R1 `DID NOT RAISE` |
| 消费者被替换（**运行时持续** monkeypatch） | **红** | EXP-1：`EXP1_R1=RED:Failed` |
| helper `_resolve_backed_obligation` 被 patch 成 seam 直通（运行时持续） | **红** | EXP-2：`EXP2_R1=RED:Failed`（R1 调消费者，消费者查模块全局 helper，拿到被换版本 ⇒ 放行 ⇒ DID NOT RAISE） |
| **瞬时 monkeypatch（跑锁前恢复、不留源码痕迹）** | **不可见** | EXP-3：锁不在场时同变异 `EXP3_BACKING=PASS` / `EXP3_REDEEMED=('glm_boundary',)`——缺陷回来 |

由此：

1. 自报原话「如果有人把 `redeemable_debt_ids` / `assert_obligations_backed` **自身**替换成信任 seam 的旧版本……出口全检就绕过去了」**不准确**：该方向（源码层 = 红锚；运行时持续 = EXP-1）恰恰是 R1 锁定的方向——这正是新锁相对旧 28 项锁买回的分辨力本身。
2. 真实盲区只剩最后一行：**瞬时 monkeypatch 且不留源码痕迹**。它对**任何**行为锁结构上不可见；要锁它只能上 AST 结构锁（断言消费者调用 helper），而派工单 §一 R1 提示已明示那条路会回到「换个写法绕过去」的老问题。且该形态当前无生产发生面：`src/` 全树 grep 实证这些符号（`assert_obligations_backed` / `redeemable_debt_ids` / `_resolve_backed_obligation` / `redemption_row_for_obligation` / `DEBT_REDEMPTION_REGISTRY`）**零赋值替换、零 patch.object/patch.dict**，只有定义、调用与 docstring。
3. 因此「登记为边界、不追加」符合科研档分寸（工程上无发生面、理论上锁不死）；但边界描述应收窄为上面第 2 条的一句话，防止后人引用自报原话高估缺口、或误以为「换掉消费者」是现实可行的绕法。

## 五、R3 两条不阻断的处置复核

- **#2（查询侧 str 子类偷混）：已修，独立复现成立。** 我用自选 visible 串（`glm_visible_label`，非锁内 `owner_of_span`）的 `str` 子类（`__hash__/__eq__` 指向活键）独立探针：`RAW_MEMBERSHIP_FOOLED=True`（裸 `in` 确会被反射相等骗过——先证明危险真实），`BACKING/REDEEM_REFUSED=OBLIGATION_TYPE_NOT_PLAIN_STR`（出口在查值前按精确类型拒）。红锚中该项在旧源上红（旧 binding 放行子类键），双锚齐。
- **#1（`type() is dict` 拒 `MappingProxyType`、无合法只读出口）：登记不改，理由经核成立。** 三条理由中关键两条我机械核过：① 承重不变量确已移到 binding 出口的成员判断上，类型钉降为纵深防御；② 注册表语境生产零只读载体（`MappingProxyType` 在 `src/` 的唯一使用是 `judge/identity_provenance.py` 自己的常量表，与 `DEBT_REDEMPTION_REGISTRY` 无关）——加支路属「现在就泛化非正交输入」。将来若真需只读载体，「把成员判据与载体类型解耦」是比放宽 `type() is dict` 更正的出口。处置符合派工单 R3「能修则修、不修则逐条说明理由并登记」。

## 六、运维核对

- **分段提交兑现**：`8cd7df01`（源+锁+两份预置评审材料）/ `4d0b99ad`（执行报告 + docstring 中和）/ `90c9e644`（钉读数）三段；首笔 `--stat` 为 4 文件 962+/38−，除一行测试外只捎带预置材料，无夹带（与上一轮裁决对同型操作不记 finding 的先例一致）。无 `git add -A` 迹象。
- 提交 `4d0b99ad`「neutralise owner_b4 mention in docstring」经 grep 实证兑现：`src/` 里 `owner_b4` 零命中。

## 七、未复现项清单

1. **未独立复现基线拆解 `3781`**（`df57f9a3` 的上一轮全量组成）：沿用派工单固定基线与上一轮 GPT 复核席的独立读数 `3809`；本轮红锚 worktree 只点了 10 项新锁，未跑旧源全量。
2. **未在中间提交 `8cd7df01` / `4d0b99ad` 上跑全量**（施工方自报两次 `3819`，其一在 `4d0b99ad`）：我只在最终 HEAD `90c9e644` 上跑了权威全量。
3. **未独立重装 M1–M6 demo**：上一轮 GPT 裁决已独立重造过 M3/M5/M6；本轮 M1–M6 代码除谓词改名外零改动，随 `62 passed` 见绿，未逐个重装。
4. **未演示「全量跑期间持续 patch helper」**：该场景会制造与被测无关的假红，不做；其 R1 可见性已由 EXP-2（点跑 R1 + 持续 patch）等价覆盖。
5. 施工方交件 §二#1(a) 的对比引文（`df57f9a3` 上 `BACKING=PASS / REDEEMED=('review_arbitrary_alias',)`）未逐字重放，但同一缺陷面已由我的红锚探针（`BACKING=PASS / REDEEMED=('glm_probe_alias',)`）独立复现。

## 八、是否改过项目代码

**没有。** 复核期间审对象工作树 `git status --porcelain` 始终为空；所有探针为进程内 monkeypatch + finally 恢复（每次恢复后自证 `RESTORED`）；红锚用独立临时 worktree（`/tmp/t4arw2_redanchor`）承载、审后 `git worktree remove` 并确认主树干净。唯一新增 = 本裁决文件 `AI_agent/logs/reviews/verdict/2026-09-05c_T4a_rework2_crossreview_glm.md`。
