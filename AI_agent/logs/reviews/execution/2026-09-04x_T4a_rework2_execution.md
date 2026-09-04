# 执行报告 · **T4-a 返工 2**：锁「成功解析输入集合 == live key 集合」（出口全检）

- **日期**：2026-09-04 · **施工方**：Claude 家族施工席 · **审**：GPT 或 GLM 家族（⛔ 不得 Claude）
- **工作目录**：`/tmp/t4a_rework2_claude` · **分支**：`wt/09.04x_t4a_rework2`（基于 `df57f9a3`）
- **本轮提交**：`8cd7df01`（源 + 锁一并，含预置的 request/verdict 两份材料）
- **派工单**：[`2026-09-04x`](../request/2026-09-04x_T4a_rework2.md) · **上一轮裁决**：[`2026-09-04v`](../verdict/2026-09-04v_T4a_rework1_crossreview_gpt.md)

---

## 〇、开工自检

命令：
```bash
cd /tmp/t4a_rework2_claude && pwd && git log --oneline -1 && git status --porcelain
```
输出（开工时）：
```text
/tmp/t4a_rework2_claude
df57f9a3 T4-a rework1 execution report: regression direction bought back, 3809 = 3781 + 28
A  AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md
A  AI_agent/logs/reviews/verdict/2026-09-04v_T4a_rework1_crossreview_gpt.md
```
两个被审模块的 `__file__` 全程落在本工作树（每次跑测前同一条命令核过）：
```text
/tmp/t4a_rework2_claude/src/agent/correction/evidence_contract.py
/tmp/t4a_rework2_claude/src/agent/correction/opening_synthesis.py
```

---

## 一、病灶与修法（一句话）

**病灶**：上一轮三层锁（19 项近错电池 + identity 钉 + 两道类型钉）量的都是「输入**长得像不像**活键」。
复核方在 seam 外挂 `"owner_b4" → 活键` 兼容映射，注册表仍是 plain dict、键仍全 str、identity 钉照旧成立
⇒ 28 项锁一条不红，而销账 binding 信任 resolver 返回的 canonical `(key,row)`，**没有再核原始 `debt.obligation`**
⇒ schema-bypass 的债被真的退休了。**没有一条锁量「所有成功解析输入的集合必须恰等于 live key 集合」。**

**修法（出口全检，⛔ 不是入口收窄）**：新增 `_resolve_backed_obligation`（`opening_synthesis.py`），
它**直接对不可变 plain-dict 注册表**复核**原始** obligation（成员 + 类型），**先于且独立于**那个可被替换的 seam；
`assert_obligations_backed` 与 `redeemable_debt_ids` 两条销账路径全部改走它。
seam（`redemption_row_for_obligation`）保持精确单值不动，只作「内层可扩点」，其返回值**不再决定成败**。

- **R1**：锁「成功 back/retire 的输入集合 == live key 集合」这个性质本身 —— 4 种 seam 扩法下 binding 一律拒。
- **R2**：binding 现在核原始值（成员 `in` plain dict + `type(obligation) is str`），schema-bypass 债响亮拒。
- **R3**：非阻断 #2（查询侧 str 子类偷混）**已在出口修掉**（`OBLIGATION_TYPE_NOT_PLAIN_STR`）；非阻断 #1（`MappingProxyType`）**登记不改**，理由见 §四。

---

## 二、⭐ 自证义务（三小节）

### #1 原反例复现 —— 证明新锁「现在会红（有牙）」且「变异确实生效（不是没跑到）」

#### (a) 逐字重造复核方的 `"owner_b4" → 活键` 兼容映射，跑在**已修**树上

> ⛔ `owner_b4` 仅作复核方原始探针串出现在本复现脚本里，**不进任何断言当靶子**（§二#3）。

命令原文：
```bash
python - <<'PY'
from unittest.mock import patch
from pydantic import ValidationError
import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import ArtifactPointerV1, EvidenceDebtV1
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0
key = next(iter(osm.DEBT_REDEMPTION_REGISTRY)); alias = "owner_b4"
real = osm.redemption_row_for_obligation
def compat(name): return real({alias: key}.get(name, name))
base = {"debt_id":"review_arbitrary_alias", "kind":"other_known_missing",
        "channel":None, "affected_refs":(), "description":"review"}
try: EvidenceDebtV1.model_validate({**base, "obligation":alias})
except ValidationError as exc:
    print("SCHEMA=" + next(e for e in exc.errors() if e["loc"] == ("obligation",))["type"])
source = osm.ElevationSourceIdentity("review_input", CONTRACT_AS_DRAWN_ELEVATION_V0, "a"*64)
ref = ArtifactPointerV1.model_validate({"input_id":source.input_id,
    "source_contract_id":source.source_contract_id,
    "source_output_sha256":source.source_output_sha256, "json_pointer":"/calibration"})
debt = EvidenceDebtV1.model_construct(**{**base, "affected_refs":(ref,)}, obligation=alias)
executed = osm.ExecutedRedemption(key, osm.DEBT_REDEMPTION_REGISTRY[key], source)
with patch.object(osm, "redemption_row_for_obligation", new=compat):
    print("SEAM_WIDENED_ACCEPTS=" + repr(compat(alias)[0]))   # mutation took
    try: osm.assert_obligations_backed([debt]); print("BACKING=PASS")
    except osm.OpeningSynthesisError as e: print("BACKING_REFUSED=" + e.code)
    try: r = osm.redeemable_debt_ids([debt], executed=executed); print("REDEEMED=" + repr(r))
    except osm.OpeningSynthesisError as e: print("REDEEM_REFUSED=" + e.code)
PY
```
输出原文（**已修树**）：
```text
SCHEMA=literal_error
SEAM_WIDENED_ACCEPTS='elevation_chain_spans_whole_building'
BACKING_REFUSED=OBLIGATION_UNBACKED
REDEEM_REFUSED=OBLIGATION_UNBACKED
```

对比复核方 `2026-09-04v` 在 `df57f9a3` 上的原文（同一脚本）：`BACKING=PASS` / `REDEEMED=('review_arbitrary_alias',)`。
⇒ **同样的兼容映射，现在被响亮拒（`OBLIGATION_UNBACKED`）、债不再退休。**
`SEAM_WIDENED_ACCEPTS=...` 一行证明 **seam 确实被扩宽、`compat(alias)` 真的解析成活键** —— 拒绝来自 binding 的出口全检，**不是变异没生效**。

#### (b) 把新锁跑在**改动之前**的 `opening_synthesis.py` 上 —— 必须变红

> 目的：区分「锁有牙」与「变异没生效」（派工单 §二#1）。绿锚 = 新锁在**已修**树上全绿（见 §三#1 的 `38 passed`）；
> 红锚 = 把**源**回退到 `df57f9a3`、**只留新锁**，新锁必须红。

命令原文：
```bash
cp src/agent/correction/opening_synthesis.py <scratch>/opening_synthesis_fixed.py
git checkout df57f9a3 -- src/agent/correction/opening_synthesis.py
python -m pytest -q -n 0 -p no:cacheprovider \
  tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input \
  tests/test_t4a_rework1_resolution_lock.py::test_query_side_str_subclass_obligation_is_refused_at_the_exit
cp <scratch>/opening_synthesis_fixed.py src/agent/correction/opening_synthesis.py   # 立即恢复
```
输出原文（源=`df57f9a3`）：
```text
FAILED ...::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[external_compat_table-external_compat_table]
FAILED ...::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[prepended_normalisation-prepended_normalisation]
FAILED ...::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[one_to_many_silent_pick-one_to_many_silent_pick]
FAILED ...::test_widened_seam_cannot_make_the_binding_back_a_non_key_input[unicode_nfkc_fold-unicode_nfkc_fold]
FAILED ...::test_query_side_str_subclass_obligation_is_refused_at_the_exit
5 failed in 0.93s
```
失败原因均为 `Failed: DID NOT RAISE OpeningSynthesisError` —— 旧 binding 信任 seam、把非 key 输入 back 了。
恢复后源码 diff 与提交一致（`git diff --stat`：`91 insertions(+), 18 deletions(-)`）。

### #2 ⭐⭐ 换同形输入 —— 自设**两条以上**同形不同扩法，证明**这一类**都会红

R1 锁 `test_widened_seam_cannot_make_the_binding_back_a_non_key_input` 是**按扩法参数化**的，
每个扩法都在 seam 上装一个「让某个**与活键无字面相似 / 或字面越界**的输入解析成活键」的窗口，然后断言 binding 仍拒：

| 扩法 label | 形态 | foreign 输入（seam 层被接受） |
|---|---|---|
| `external_compat_table` | **复核方的反例本体**：外挂兼容表 | `"compat_owner_of_the_span_debt"`（⛔ 与活键零字面重叠）|
| `prepended_normalisation` | resolver 前挂 `strip()+casefold()` 归一化 | `"  " + KEY.upper() + "  "` |
| `one_to_many_silent_pick` | 收多个前缀候选后 `sorted()[0]` 静默选一 | `KEY[:len//2]`（真前缀）|
| `unicode_nfkc_fold` | 键做 unicode NFKC 归一 | KEY 的**全角**变体（码点不同）|

四条各自都：① 先断言 foreign **不在**注册表（真·非 key）；② 装扩法后断言 `redemption_row_for_obligation(foreign)` **在 seam 层解析成活键**（变异生效）；
③ 断言 `assert_obligations_backed` 与 `redeemable_debt_ids` **都响亮 `OBLIGATION_UNBACKED`**。

命令原文 + 输出原文（已修树，`-n 0`，只跑这一条参数化 + R2 + R3）：
```bash
python -m pytest -q -n 0 -p no:cacheprovider \
  "tests/test_t4a_rework1_resolution_lock.py::test_widened_seam_cannot_make_the_binding_back_a_non_key_input" \
  "tests/test_t4a_rework1_resolution_lock.py::test_schema_bypassed_obligation_outside_the_domain_is_refused_loudly" \
  "tests/test_t4a_rework1_resolution_lock.py::test_query_side_str_subclass_obligation_is_refused_at_the_exit"
```
```text
..........                                                               [100%]
10 passed in 0.79s
```
（4 扩法 + 5 foreign schema-bypass + 1 查询侧子类 = 10，全绿；红锚见 §二#1(b)。）

### #3 ⛔ 未把 `"owner_b4"` 写进任何断言当靶子

R1/R2 锁的断言主语一律是 **`caught.value.code == "OBLIGATION_UNBACKED"`**（性质），扩法的 foreign 串是
**参数/驱动**，且都是自设的（`compat_owner_of_the_span_debt` 等），⛔ 无一处 `assert ... == "owner_b4"` 或以该串为靶。
机械核：
```bash
grep -n "owner_b4" tests/test_t4a_rework1_resolution_lock.py src/agent/correction/opening_synthesis.py || echo "NO_OWNER_B4_IN_SRC_OR_LOCK"
```
```text
NO_OWNER_B4_IN_SRC_OR_LOCK
```

---

## 三、验收（逐条对派工单 §三）

### #1 ⭐⭐⭐ 「成功解析输入集合 == live key 集合」有锁 —— **通过**
- §二#1 复现（已修树拒、旧树该锁红）+ §二#2 四条扩法全红/全绿双锚。
- 锁断言里**不出现任何具体扩法名字当靶**（性质断言 `OBLIGATION_UNBACKED` / `OBLIGATION_TYPE_NOT_PLAIN_STR`）。
- 形式 = **行为 + 直接成员出口全检**，**不依赖枚举输入**（对无界前像，用「原始值直接查不可变 plain dict」这一后置条件替代枚举）。

### #2 ⭐⭐ schema-bypass 的债不能被静默退休 —— **通过**
`test_schema_bypassed_obligation_outside_the_domain_is_refused_loudly`：5 个 `model_construct` 造的域外 obligation（含空串、纯数字、反转活键），**无扩法**下 `assert_obligations_backed` 与 `redeemable_debt_ids` 均响亮 `OBLIGATION_UNBACKED`（见 §二#2 输出）。R2 的正面修法 = binding 核**原始** `debt.obligation`（`opening_synthesis.py` `_resolve_backed_obligation`）。

### #3 ⛔ 没有为让锁能红而把缺陷造回来 —— **通过**
- 契约 / mint 代码零改动：
```bash
git diff --exit-code a91a1524..HEAD -- src/agent/correction/evidence_contract.py src/agent/correction/evidence_adapters.py && echo CONTRACT_AND_MINT_CODE_DIFF=NONE
```
```text
CONTRACT_AND_MINT_CODE_DIFF=NONE
```
- seam `redemption_row_for_obligation` 本体**未加**任何归一化/别名/多候选逻辑（精确 membership + 精确 index + claimant 计数原样）。本轮源码新增行里出现 `normal/alias/casefold/strip` 等词的**全部是 docstring 叙述**（描述「⛔ 不做归一化」），无一是可执行逻辑：
```bash
git diff HEAD~1..HEAD -- src/agent/correction/opening_synthesis.py | grep -E "^\+" | grep -Ei "startswith|casefold|\.strip\(|\.lower\(\)|alias|\.get\("
```
（命中项经逐行核，均为 `"""..."""` / 注释内的说明文字。）新增的 `_resolve_backed_obligation` 只做 `type() is dict` / `type() is str` / `in` 三种精确判断，⛔ 无归一化。

### #4 上一轮已通过的不退化 —— **通过**
- 闭枚举 / 接线不靠前缀（两方向）/ 无处理器响亮 / B4 源绑定 / 枚举面 / B4 三道 import 牙：本轮**只**动 `assert_obligations_backed` / `redeemable_debt_ids` 两个函数体 + 新增一个私有 helper；`_assert_registry_well_formed`、`redemption_row_for_premise`、`redemption_row_for_obligation`、源绑定 `ElevationSourceIdentity.binds`、mint 面均未触碰。
- **上一轮那 28 项锁仍全绿**，且本文件现共 **38 项**（28 + 10 新）全绿：
```bash
python -m pytest --collect-only -q -p no:cacheprovider tests/test_t4a_rework1_resolution_lock.py | tail -n 1
python -m pytest -q -n 0 -p no:cacheprovider tests/test_t4a_rework1_resolution_lock.py tests/test_b4_opening_synthesis.py | tail -n 1
```
```text
38 tests collected in 0.87s
62 passed in 0.94s
```
⚠️ **口径说明**：为让我的 binding 修法与旧 M-demo 自洽，`_refusal_gone` 收窄为 **seam 作用域**（改名 `_refusal_gone_at_seam`）——
因为 M1/M2/M3 装的是 **seam-only** 扩法，用来证明**seam 电池**的牙；binding 不再信任 seam（正是本轮修法），
故「seam 被扩宽 ⇒ 三入口全接受」这个旧前提**不再成立**（这正是修好的标志）。binding 的独立牙由新 R1 锁承担。
28 项的**语义与通过性**未退化（近错电池、identity 钉、M1–M6 demo 逐条仍绿）。

### #5 零恒真断言 —— **通过**
本轮新增断言全部形如 `assert caught.value.code == "..."` / `assert foreign not in ...` / `assert widened_key == canonical`，无 `assert True` / `or True` / `and False` 形态。§二#1(b) 的红锚（旧源下 5 条 `DID NOT RAISE`）即证明这些断言**可失败**、非恒真。

### #6 全量绿、逐位闭合 —— **通过**
命令原文（环境自证 + pytest 同一条）：
```bash
python -c "import src.agent.correction.evidence_contract as c, src.agent.correction.opening_synthesis as o; print(c.__file__); print(o.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```
输出原文（末行 + `__file__`）：
```text
/tmp/t4a_rework2_claude/src/agent/correction/evidence_contract.py
/tmp/t4a_rework2_claude/src/agent/correction/opening_synthesis.py
3819 passed, 2 skipped, 13 xfailed, 211 warnings in 481.58s (0:08:01)
```
**逐位闭合**：基线 `3809 = 3781 + 28`（`df57f9a3`，复核方独立复现过）；本轮新增 10 项（4 R1 参数化 + 5 R2 参数化 + 1 R3 查询侧）
⇒ `3819 = 3809 + 10`；`2 skipped / 13 xfailed / 0 failed` 与基线逐位一致。两个 `__file__` 均落本工作树。

> 上表那次全量跑在 `8cd7df01`（源与最终 HEAD 行为等价，仅差一行 docstring）。
> 为使「已测状态 == 已提交状态」，在**最终提交 `4d0b99ad`**（git 工作树干净）上**再跑一次权威全量**，逐位相同：
> `3819 passed, 2 skipped, 13 xfailed, 211 warnings in 469.87s`，两个 `__file__` 同落本工作树。

---

## 四、R3 两条不阻断的处置

- **非阻断 #2（查询侧 str 子类偷混）：已修**。出口 `_resolve_backed_obligation` 加 `type(obligation) is str` 牙 ⇒
  一个 `visible="owner_of_span"`、`__hash__/__eq__` 指向活键的 `str` 子类（`in` 会被**反射相等**判成命中）在**查值前**即被
  `OBLIGATION_TYPE_NOT_PLAIN_STR` 拒。锁 = `test_query_side_str_subclass_obligation_is_refused_at_the_exit`
  （先 `assert alias in DEBT_REDEMPTION_REGISTRY` 证明偷混对裸 `in` 真有效，再证出口拒）。
- **非阻断 #1（`type() is dict` 拒绝更安全的 `MappingProxyType`、无合法只读出口）：登记不改**，理由三条：
  ① **承重不变量已搬到 binding 出口**（`obligation in DEBT_REDEMPTION_REGISTRY` 对任何**精确** `__contains__`/`__getitem__` 的载体都成立），
  `type() is dict` 现在是**冗余的纵深防御**，不是唯一承重点；② 注册表是模块级 plain dict，**今天没有任何生产路径**用只读代理，
  加 `MappingProxyType` 支路属「现在就泛化非正交输入」（[[extensibility-is-not-generalization-now]]，用户 09-02 校准）；
  ③ `MappingProxyType` 不暴露稳定的「底层 mapping 身份」API，要证「其底层是 plain dict」需引入脆弱内省，性价比为负。
  ⇒ 若将来真需只读载体，正解是在 binding 出口把成员判据与载体类型**解耦**，而非放宽 `type() is dict`。

---

## 五、⭐ 最薄弱一处（自陈）

**出口全检拦得住「换 seam」，但拦不住「换 binding 本身」。** `_resolve_backed_obligation` 直接读模块级
`DEBT_REDEMPTION_REGISTRY` 复核原始值，因此复核方那类「patch `redemption_row_for_obligation`」的攻击全被挡；
但如果有人把 `redeemable_debt_ids` / `assert_obligations_backed` **自身**替换成信任 seam 的旧版本、或把
`DEBT_REDEMPTION_REGISTRY` 整体换成一个 `__contains__` 说谎的对象（`type() is dict` 牙能挡后者的**子类**形态，
但挡不住「patch 掉 helper 函数」这种**直接替换消费者**的形态），出口全检就绕过去了。

这不是本轮反例的形态（复核方只 patch 了 seam），且「任意替换被测函数本身」在任何测试体系里都无法防死；
但它是本锁**语义边界的诚实位置**：本锁保证的是「**只要销账仍走 `_resolve_backed_obligation`**，成功输入集合就恰等于 live key 集合」，
⛔ 不保证「没有人把这条销账路径整段换掉」。要再进一步，得把「销账必经出口全检」这件事本身立成结构锁
（例如对 `redeemable_debt_ids` 的 AST 断言它调用了 `_resolve_backed_obligation`），但那又回到「换个写法能不能绕过」的老问题，
故本轮**显式登记为边界、不追加**（[[gate-measures-right-but-carrier-gets-swapped]] 的第 N+1 圈，留给需要时再收）。
