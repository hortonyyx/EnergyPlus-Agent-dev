# 裁决 · T4-a v2 跨家族审（GPT 家族复核席）

- 日期：2026-09-04
- 施工方：GLM 家族
- 复核方：GPT 家族
- 审对象：`git diff e5b0d7d5..a91a1524`
- 工作树：`/tmp/t4a_review_gpt`，detached `a91a1524`

## 一、裁决

**REWORK · 阻断 1 / 不阻断 4**

阻断只有一条：验收 #6 没有保住 `DEBT_TYPE_AMBIGUOUS` 原来那道独立的债侧牙。旧触发在“单值 `obligation` + 普通 `dict` + 精确索引”下确实结构性不可达；但施工方改挂的“两行共享 premise”量的是 **premise → 注册行** 歧义，不是旧牙量的 **一张债 → 多注册行/多处理器** 歧义。该表在 import 审计时先报 `DEBT_REGISTRY_PREMISE_AMBIGUOUS`，真实 synthesis 查门时先报 `PREMISE_GATE_AMBIGUOUS`；只有绕过这两层、手造 `ExecutedRedemption` 直调 `redeemable_debt_ids`，才会报新借壳的 `DEBT_TYPE_AMBIGUOUS`。所以“旧触发不可达”成立，“新触发等价承载”不成立；明确要求不得拆的第三道资产已被改成另一道牙的重复出口。

这不表示当前健康表会静默把一张合法债交给两个处理器：T3 的精确键结构已经把该状态消掉。阻断来自任务书对既有三道牙的明确保留要求，以及失去对将来重新引入 alias / normalization / 一对多解析时的那条独立回归锁。

### 开工自检原文

命令：

```bash
cd /tmp/t4a_review_gpt && pwd && git log --oneline -1 && git status --porcelain
```

输出：

```text
/tmp/t4a_review_gpt
a91a1524 T4-a v2 execution report: obligation field shipped, 3781 = 3778 + 3
A  AI_agent/logs/reviews/request/2026-09-04h_T4a_v2_crossreview.md
```

## 二、原始任务书 §四七条逐条对账

| # | 判定 | 独立复核结论 |
|---|---|---|
| 1 | **通过** | `DebtObligationV1` 在 `evidence_contract.py:502` 是单值 `Literal`，字段在 `:539` 必填且可为 `None`。我没有复用施工测试的构造器写法，而用 `model_validate` 独立喂大写别名、前后空格和 bytes；均在 `obligation` 处以 `literal_error` 拒绝，缺字段以 `missing` 拒绝。这里的大写与空白别名是点名例子以外的同形输入。 |
| 2 | **通过** | `opening_synthesis.py:546` 按 `debt.obligation` 精确取行，`:562-565` 再核 executed key 与 row identity。两条完全无旧前缀的债、只要 obligation 正确，均被识别；两条历史前缀债、obligation 为 `None`，均不识别；绕过 schema 塞错误 obligation 时响亮 `OBLIGATION_UNBACKED`，没有退回前缀。全 `src/` AST 找到 33 个 `startswith` call，债对象 receiver 为 0；`opening_synthesis.py` 仅 `:369` 的 key-space 检查。 |
| 3 | **通过，带 N-1** | 删除当前唯一注册行，standalone 和直连销账均报 `OBLIGATION_UNBACKED`；import 域审计报 `DEBT_REGISTRY_OBLIGATION_UNCOVERED`。所以不是恒绿门。但摘掉新 runtime check 后同形输入仍以 `KeyError` 响亮，premise 查找仍以 `PREMISE_GATE_UNWIRED` 响亮；今天域和表都是同一个单值，真实第二义务存货为 0。详见 §四。 |
| 4 | **通过** | `ElevationSourceIdentity.binds` 的基点/终点代码块 SHA-256 同为 `1ebb01cd...`；销账中 `executed.source.binds(ref) for ref in debt.affected_refs` 的去注释语义块 SHA-256 同为 `e21e1d...`。当前文件行号为 `opening_synthesis.py:451-459` 与 `:568-570`。diff 中 `affected_refs` 的增删只发生在模块散文措辞，绑定实现未改。 |
| 5 | **通过** | 我用 AST 盘完 `src/` 的全部 10 个 `EvidenceDebtV1(` mint 点：唯一非 `None` 是 `evidence_adapters.py:767` 的 span 债，值为 `elevation_chain_spans_whole_building`；其余 9 点均显式 `None`，无缺字段。值域恰好一个值，与唯一真实非空 mint 一一对应。 |
| 6 | **失败（阻断 B-1）** | `DEBT_REGISTRY_HANDLER_MISSING` 用 `None`、整数 `17` 两种非 callable 均响；`DEBT_REGISTRY_PREFIX_AMBIGUOUS` 用较短键、较长键两种同形输入均响。但 `DEBT_TYPE_AMBIGUOUS` 的新触发不是旧语义的等价形态：同 premise 多行时合法债仍只有一个 exact hit；import 与真实 execution lookup 先由既有 premise 牙响，只有直调销账才见该码。详见 §三与证据 G。 |
| 7 | **通过** | 规定命令、`-n 6`、`-p no:cacheprovider`；两个 `__file__` 都在本工作树；exit 0；summary 为 `3781 passed, 2 skipped, 13 xfailed`。diff 新增恰 3 个非参数化测试函数，故 `3778 + 3 = 3781`，skip/xfail 逐位不变。 |

### 证据 A：#1 闭枚举与同形越界

命令：

```bash
python - <<'PY'
from typing import get_args
from pydantic import ValidationError
from src.agent.correction.evidence_contract import EvidenceDebtV1, DebtObligationV1

legal, = get_args(DebtObligationV1)
base = {
    'debt_id': 'review_enum_probe',
    'kind': 'other_known_missing',
    'channel': None,
    'affected_refs': (),
    'description': 'independent enum probe',
}
print('DOMAIN=', tuple(get_args(DebtObligationV1)))
for label, value in [
    ('CASE_VARIANT', legal.upper()),
    ('TRAILING_SPACE', legal + ' '),
    ('LEADING_SPACE', ' ' + legal),
    ('BYTES_ALIAS', legal.encode()),
]:
    try:
        EvidenceDebtV1.model_validate({**base, 'obligation': value})
    except ValidationError as exc:
        err = next(e for e in exc.errors() if e['loc'] == ('obligation',))
        print(f'{label}=REJECT type={err["type"]} input={err["input"]!r}')
    else:
        print(f'{label}=ACCEPT_UNEXPECTED')
try:
    EvidenceDebtV1.model_validate(base)
except ValidationError as exc:
    err = next(e for e in exc.errors() if e['loc'] == ('obligation',))
    print('MISSING=REJECT type=' + err['type'])
else:
    print('MISSING=ACCEPT_UNEXPECTED')
print('LEGAL=', EvidenceDebtV1.model_validate({**base, 'obligation': legal}).obligation)
print('NONE=', EvidenceDebtV1.model_validate({**base, 'obligation': None}).obligation)
PY
```

输出原文：

```text
DOMAIN= ('elevation_chain_spans_whole_building',)
CASE_VARIANT=REJECT type=literal_error input='ELEVATION_CHAIN_SPANS_WHOLE_BUILDING'
TRAILING_SPACE=REJECT type=literal_error input='elevation_chain_spans_whole_building '
LEADING_SPACE=REJECT type=literal_error input=' elevation_chain_spans_whole_building'
BYTES_ALIAS=REJECT type=literal_error input=b'elevation_chain_spans_whole_building'
MISSING=REJECT type=missing
LEGAL= elevation_chain_spans_whole_building
NONE= None
```

### 证据 B：#2 两方向、各两条同形输入

命令：

```bash
python - <<'PY'
from typing import get_args
from src.agent.correction.evidence_contract import DebtObligationV1, EvidenceDebtV1
import src.agent.correction.opening_synthesis as m
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0

obligation, = get_args(DebtObligationV1)
sha = 'a' * 64
source = m.ElevationSourceIdentity('review_facade', CONTRACT_AS_DRAWN_ELEVATION_V0, sha)
row = m.DEBT_REDEMPTION_REGISTRY[obligation]
executed = m.ExecutedRedemption(obligation, row, source)

def debt(debt_id, value):
    return EvidenceDebtV1.model_validate({
        'debt_id': debt_id,
        'kind': 'other_known_missing',
        'channel': None,
        'affected_refs': ({
            'input_id': 'review_facade',
            'source_contract_id': CONTRACT_AS_DRAWN_ELEVATION_V0,
            'source_output_sha256': sha,
            'json_pointer': '/calibration',
        },),
        'description': 'constructed independently for review',
        'obligation': value,
    })

renamed = [
    debt('invoice_alpha_unrelated', obligation),
    debt('ELEVATION_PROMISE_WITHOUT_OLD_PREFIX', obligation),
]
historical = [
    debt('debt_elevation_chain_span_unchecked_exact', None),
    debt('debt_elevation_chain_span_unchecked_second_shape', None),
]
print('RENAMED_VALID_OBLIGATION=', m.redeemable_debt_ids(renamed, executed=executed))
print('HISTORICAL_PREFIX_NONE=', m.redeemable_debt_ids(historical, executed=executed))
invalid = EvidenceDebtV1.model_construct(
    debt_id='debt_elevation_chain_span_unchecked_bypassed_schema',
    kind='other_known_missing', channel=None, affected_refs=(),
    description='bypass only to probe runtime matching criterion',
    obligation='elevation_chain_spans_whole_building_v2',
)
try:
    m.redeemable_debt_ids([invalid], executed=executed)
except m.OpeningSynthesisError as exc:
    print('HISTORICAL_PREFIX_WRONG_OBLIGATION=', exc.code, exc.context['obligation'])
else:
    print('HISTORICAL_PREFIX_WRONG_OBLIGATION=CONNECTED_UNEXPECTEDLY')
PY
```

输出原文：

```text
RENAMED_VALID_OBLIGATION= ('ELEVATION_PROMISE_WITHOUT_OLD_PREFIX', 'invoice_alpha_unrelated')
HISTORICAL_PREFIX_NONE= ()
HISTORICAL_PREFIX_WRONG_OBLIGATION= OBLIGATION_UNBACKED elevation_chain_spans_whole_building_v2
```

### 证据 C：#2 全 `src/` 的 `startswith` 机械核

命令：

```bash
python - <<'PY'
import ast
from pathlib import Path
calls=[]
for path in Path('src').rglob('*.py'):
    tree=ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr=='startswith':
            calls.append((str(path), node.lineno, ast.unparse(node.func.value)))
print('STARTSWITH_CALLS_IN_SRC=', len(calls))
print('DEBT_RECEIVER_CALLS=', [(p,n,r) for p,n,r in calls if 'debt' in r.lower()])
print('OPENING_SYNTHESIS_CALLS=', [(p,n,r) for p,n,r in calls if p.endswith('opening_synthesis.py')])
PY
```

输出原文：

```text
STARTSWITH_CALLS_IN_SRC= 33
DEBT_RECEIVER_CALLS= []
OPENING_SYNTHESIS_CALLS= [('src/agent/correction/opening_synthesis.py', 369, 'other'), ('src/agent/correction/opening_synthesis.py', 369, 'key')]
```

这证明债匹配已零 `startswith`；同时施工档所称“全 `src/` 只剩两处”不是事实，见 N-3。

### 证据 D：#3 当前牙、摘牙对照与未来域方向

命令：

```bash
python - <<'PY'
from typing import get_args
from src.agent.correction.evidence_contract import DebtObligationV1, EvidenceDebtV1
import src.agent.correction.opening_synthesis as m

obligation, = get_args(DebtObligationV1)
debt = EvidenceDebtV1.model_validate({
    'debt_id': 'review_unbacked_probe', 'kind': 'other_known_missing',
    'channel': None, 'affected_refs': (), 'description': 'review',
    'obligation': obligation,
})
row = m.DEBT_REDEMPTION_REGISTRY[obligation]
executed = m.ExecutedRedemption(obligation, row, None)
print('TODAY_DOMAIN=', sorted(m._OBLIGATION_DOMAIN))
print('TODAY_REGISTRY=', sorted(m.DEBT_REDEMPTION_REGISTRY))
m.assert_obligations_backed([debt])
print('HEALTHY_BACKING=PASS')

del m.DEBT_REDEMPTION_REGISTRY[obligation]
try:
    for label, call in [
        ('DELETE_STANDALONE', lambda: m.assert_obligations_backed([debt])),
        ('DELETE_REDEEM', lambda: m.redeemable_debt_ids([debt], executed=executed)),
        ('DELETE_IMPORT_AUDIT', m._assert_registry_well_formed),
        ('DELETE_PREMISE_LOOKUP', lambda: m.redemption_row_for_premise(row.premise)),
    ]:
        try:
            call()
        except m.OpeningSynthesisError as exc:
            print(label + '=' + exc.code)
        except Exception as exc:
            print(label + '=' + type(exc).__name__)
        else:
            print(label + '=GREEN_UNEXPECTED')
    original_check = m.assert_obligations_backed
    m.assert_obligations_backed = lambda debts: None
    try:
        m.redeemable_debt_ids([debt], executed=executed)
    except Exception as exc:
        print('NEUTERED_RUNTIME_CHECK=' + type(exc).__name__)
    else:
        print('NEUTERED_RUNTIME_CHECK=GREEN_UNEXPECTED')
    finally:
        m.assert_obligations_backed = original_check
finally:
    m.DEBT_REDEMPTION_REGISTRY[obligation] = row

original_domain = m._OBLIGATION_DOMAIN
m._OBLIGATION_DOMAIN = frozenset((*original_domain, 'future_second_obligation'))
try:
    m._assert_registry_well_formed()
except m.OpeningSynthesisError as exc:
    print('FUTURE_DOMAIN_WITHOUT_ROW=' + exc.code + ' obligation=' + exc.context.get('obligation', ''))
else:
    print('FUTURE_DOMAIN_WITHOUT_ROW=GREEN_UNEXPECTED')
finally:
    m._OBLIGATION_DOMAIN = original_domain
PY
```

输出原文：

```text
TODAY_DOMAIN= ['elevation_chain_spans_whole_building']
TODAY_REGISTRY= ['elevation_chain_spans_whole_building']
HEALTHY_BACKING=PASS
DELETE_STANDALONE=OBLIGATION_UNBACKED
DELETE_REDEEM=OBLIGATION_UNBACKED
DELETE_IMPORT_AUDIT=DEBT_REGISTRY_OBLIGATION_UNCOVERED
DELETE_PREMISE_LOOKUP=PREMISE_GATE_UNWIRED
NEUTERED_RUNTIME_CHECK=KeyError
FUTURE_DOMAIN_WITHOUT_ROW=DEBT_REGISTRY_OBLIGATION_UNCOVERED obligation=future_second_obligation
```

### 证据 E：#4 源绑定代码块前后机械同一

命令：

```bash
git diff --unified=0 e5b0d7d5..a91a1524 -- src/agent/correction/opening_synthesis.py src/agent/correction/evidence_adapters.py | rg -n "^[+-].*(affected_refs|binds)" || true
python - <<'PY'
import hashlib, subprocess
path='src/agent/correction/opening_synthesis.py'
base=subprocess.check_output(['git','show',f'e5b0d7d5:{path}'], text=True)
cur=open(path).read()
for label,text in [('BASE',base),('HEAD',cur)]:
    start=text.index('    def binds(self, ref: ArtifactPointerV1) -> bool:')
    end=text.index('\n\n\n@dataclass', start)
    block=text[start:end]
    print(label, hashlib.sha256(block.encode()).hexdigest())
    print(block)
PY
```

输出原文：

```text
64:-actually passed for that product AND the debt's ``affected_refs`` name
85:+has actually passed for that product AND the debt's ``affected_refs``
BASE 1ebb01cd6362097e56b2b6589c0c07426a5c067b1c4175880639ccc3ad829d7e
    def binds(self, ref: ArtifactPointerV1) -> bool:
        """Does this ref point INTO the source instance this identity
        names?  (Any json pointer inside it -- B3's span debt points at
        ``/calibration``, exactly the node the gate reads.)"""
        return (
            ref.input_id == self.input_id
            and ref.source_contract_id == self.source_contract_id
            and ref.source_output_sha256 == self.source_output_sha256
        )
HEAD 1ebb01cd6362097e56b2b6589c0c07426a5c067b1c4175880639ccc3ad829d7e
    def binds(self, ref: ArtifactPointerV1) -> bool:
        """Does this ref point INTO the source instance this identity
        names?  (Any json pointer inside it -- B3's span debt points at
        ``/calibration``, exactly the node the gate reads.)"""
        return (
            ref.input_id == self.input_id
            and ref.source_contract_id == self.source_contract_id
            and ref.source_output_sha256 == self.source_output_sha256
        )
```

上面 `64` / `85` 是 `git diff` 文本被 `rg -n` 编的输出序号，**不作为文件行号引用**；本裁决表中的生产文件行号另由下文最终行号核验命令取得。

另对销账 guard 去掉注释后取 SHA-256。命令：

```bash
python - <<'PY'
import hashlib, subprocess
path='src/agent/correction/opening_synthesis.py'
texts={'BASE':subprocess.check_output(['git','show',f'e5b0d7d5:{path}'], text=True),'HEAD':open(path).read()}
for label,text in texts.items():
    start=text.index('        if executed.source is None or not any(')
    end=text.index('        redeemed.append(debt.debt_id)', start)
    block=text[start:end]
    semantic='\n'.join(line for line in block.splitlines() if not line.lstrip().startswith('#'))
    print(label, hashlib.sha256(semantic.encode()).hexdigest())
    print(semantic)
PY
```

输出原文：

```text
BASE e21e1d5179d1e872d5c76da75a2daf1002f990dced3f3f79f3ddcf466f2e08cb
        if executed.source is None or not any(
            executed.source.binds(ref) for ref in debt.affected_refs
        ):
            continue
HEAD e21e1d5179d1e872d5c76da75a2daf1002f990dced3f3f79f3ddcf466f2e08cb
        if executed.source is None or not any(
            executed.source.binds(ref) for ref in debt.affected_refs
        ):
            continue
```

### 证据 F：#5 全部生产 mint 点盘点

命令：

```bash
python - <<'PY'
import ast
from collections import Counter
from pathlib import Path
rows=[]
for path in sorted(Path('src').rglob('*.py')):
    tree=ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'EvidenceDebtV1':
            values=[kw.value for kw in node.keywords if kw.arg == 'obligation']
            rows.append((str(path), node.lineno, ast.unparse(values[0]) if values else '<MISSING>'))
for path,line,value in sorted(rows):
    print(f'{path}:{line}: obligation={value}')
print('TOTAL_MINTS=', len(rows))
print('VALUE_COUNTS=', dict(sorted(Counter(value for _,_,value in rows).items())))
PY
```

输出原文：

```text
src/agent/correction/evidence_adapters.py:338: obligation=None
src/agent/correction/evidence_adapters.py:469: obligation=None
src/agent/correction/evidence_adapters.py:501: obligation=None
src/agent/correction/evidence_adapters.py:517: obligation=None
src/agent/correction/evidence_adapters.py:528: obligation=None
src/agent/correction/evidence_adapters.py:767: obligation='elevation_chain_spans_whole_building'
src/agent/correction/evidence_adapters.py:801: obligation=None
src/agent/correction/evidence_adapters.py:817: obligation=None
src/agent/correction/evidence_adapters.py:949: obligation=None
src/agent/correction/evidence_adapters.py:967: obligation=None
TOTAL_MINTS= 10
VALUE_COUNTS= {"'elevation_chain_spans_whole_building'": 1, 'None': 9}
```

`rg -n "EvidenceDebtV1\\(" src --glob '*.py'` 同时核到恰好上述 10 个调用点，没有 AST 筛选漏掉的属性式 mint。

### 证据 G：#6 三牙及载体搬移

命令：

```bash
python - <<'PY'
from typing import get_args
from pydantic import ValidationError
from src.agent.correction.evidence_contract import DebtObligationV1, EvidenceDebtV1
import src.agent.correction.opening_synthesis as m

obligation, = get_args(DebtObligationV1)
row = m.DEBT_REDEMPTION_REGISTRY[obligation]
debt = EvidenceDebtV1.model_validate({
    'debt_id': 'review_type_probe', 'kind': 'other_known_missing',
    'channel': None, 'affected_refs': (), 'description': 'review',
    'obligation': obligation,
})
executed = m.ExecutedRedemption(obligation, row, None)
snapshot = dict(m.DEBT_REDEMPTION_REGISTRY)

def restore():
    m.DEBT_REDEMPTION_REGISTRY.clear()
    m.DEBT_REDEMPTION_REGISTRY.update(snapshot)

def code(call):
    try:
        call()
    except m.OpeningSynthesisError as exc:
        return exc.code
    except Exception as exc:
        return type(exc).__name__
    return 'GREEN'

try:
    for value in (None, 17):
        restore()
        m.DEBT_REDEMPTION_REGISTRY[obligation] = m.DebtRedemption(row.premise, value)
        print(f'HANDLER_{value!r}=' + code(m._assert_registry_well_formed))

    for alias in ('elevation_chain_spans', obligation + '_legacy'):
        restore()
        m.DEBT_REDEMPTION_REGISTRY[alias] = m.DebtRedemption('independent premise ' + alias, m.span_equality_gate)
        print('PREFIX_' + alias + '=' + code(m._assert_registry_well_formed))

    restore()
    m.DEBT_REDEMPTION_REGISTRY[obligation] = m.DebtRedemption('replacement premise', m.span_equality_gate)
    print('DUPLICATE_LITERAL_KEY_ROW_COUNT=', len(m.DEBT_REDEMPTION_REGISTRY))
    print('DUPLICATE_LITERAL_KEY_PREMISE=', m.DEBT_REDEMPTION_REGISTRY[obligation].premise)

    restore()
    case_alias = obligation.upper()
    m.DEBT_REDEMPTION_REGISTRY[case_alias] = m.DebtRedemption('case alias premise', m.span_equality_gate)
    exact_hits = [key for key in m.DEBT_REDEMPTION_REGISTRY if key == debt.obligation]
    print('CASE_ALIAS_EXACT_HITS=', exact_hits)
    try:
        EvidenceDebtV1.model_validate({
            'debt_id': 'case_alias_debt', 'kind': 'other_known_missing',
            'channel': None, 'affected_refs': (), 'description': 'review',
            'obligation': case_alias,
        })
    except ValidationError:
        print('CASE_ALIAS_SCHEMA=REJECT')
    else:
        print('CASE_ALIAS_SCHEMA=ACCEPT_UNEXPECTED')

    for alias in ('vertical_extent_confirmed', 'facade_chain_global_span'):
        restore()
        m.DEBT_REDEMPTION_REGISTRY[alias] = m.DebtRedemption(row.premise, m.span_equality_gate)
        exact_hits = [key for key in m.DEBT_REDEMPTION_REGISTRY if key == debt.obligation]
        print('SAME_PREMISE_' + alias + '_EXACT_DEBT_HITS=', exact_hits)
        print('SAME_PREMISE_' + alias + '_IMPORT=' + code(m._assert_registry_well_formed))
        print('SAME_PREMISE_' + alias + '_EXECUTION_LOOKUP=' + code(lambda: m.redemption_row_for_premise(row.premise)))
        print('SAME_PREMISE_' + alias + '_DIRECT_REDEEM=' + code(lambda: m.redeemable_debt_ids([debt], executed=executed)))
finally:
    restore()
print('RESTORED_KEYS=', sorted(m.DEBT_REDEMPTION_REGISTRY))
PY
```

输出原文：

```text
HANDLER_None=DEBT_REGISTRY_HANDLER_MISSING
HANDLER_17=DEBT_REGISTRY_HANDLER_MISSING
PREFIX_elevation_chain_spans=DEBT_REGISTRY_PREFIX_AMBIGUOUS
PREFIX_elevation_chain_spans_whole_building_legacy=DEBT_REGISTRY_PREFIX_AMBIGUOUS
DUPLICATE_LITERAL_KEY_ROW_COUNT= 1
DUPLICATE_LITERAL_KEY_PREMISE= replacement premise
CASE_ALIAS_EXACT_HITS= ['elevation_chain_spans_whole_building']
CASE_ALIAS_SCHEMA=REJECT
SAME_PREMISE_vertical_extent_confirmed_EXACT_DEBT_HITS= ['elevation_chain_spans_whole_building']
SAME_PREMISE_vertical_extent_confirmed_IMPORT=DEBT_REGISTRY_PREMISE_AMBIGUOUS
SAME_PREMISE_vertical_extent_confirmed_EXECUTION_LOOKUP=PREMISE_GATE_AMBIGUOUS
SAME_PREMISE_vertical_extent_confirmed_DIRECT_REDEEM=DEBT_TYPE_AMBIGUOUS
SAME_PREMISE_facade_chain_global_span_EXACT_DEBT_HITS= ['elevation_chain_spans_whole_building']
SAME_PREMISE_facade_chain_global_span_IMPORT=DEBT_REGISTRY_PREMISE_AMBIGUOUS
SAME_PREMISE_facade_chain_global_span_EXECUTION_LOOKUP=PREMISE_GATE_AMBIGUOUS
SAME_PREMISE_facade_chain_global_span_DIRECT_REDEEM=DEBT_TYPE_AMBIGUOUS
RESTORED_KEYS= ['elevation_chain_spans_whole_building']
```

两组不同 alias 给出相同结果，证明结论不是只对施工例子成立。

### 证据 H：#7 环境自证、全量与逐位闭合

命令严格为复核单 §五原文：

```bash
cd /tmp/t4a_review_gpt && \
python -c "import src.agent.correction.evidence_contract as c, src.agent.correction.opening_synthesis as o; print(c.__file__); print(o.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

路径与最终 summary 原文：

```text
/tmp/t4a_review_gpt/src/agent/correction/evidence_contract.py
/tmp/t4a_review_gpt/src/agent/correction/opening_synthesis.py
3781 passed, 2 skipped, 13 xfailed, 211 warnings in 470.34s (0:07:50)
```

命令 exit 0，summary 行存在。新增测试机械核命令：

```bash
git diff --unified=0 e5b0d7d5..a91a1524 -- tests | rg '^\+def test_|^-def test_' || true
```

输出原文：

```text
NEW_TEST_DEFS:
+def test_obligation_not_prefix_is_the_wiring_criterion():
+def test_unbacked_obligation_fails_loudly(monkeypatch):
+def test_obligation_is_a_closed_enum_not_a_free_string():
```

所以 `3778 + 3 = 3781`；`2 skipped`、`13 xfailed` 与基线逐位相同。

## 三、复核单 §一：载体搬移三问正面回答

### 1. 原牙保护的语义外延；新形态是否全覆盖

旧 `DEBT_TYPE_AMBIGUOUS` 的外延很窄而明确：在销账侧，把一张债的结构化类型载体解析到注册表时，命中行数必须至多为一；若同一债同时命中两个 type-prefix 行，就不能确定哪一注册行、哪一 gate 对它负责，必须响亮。它保护的是 **debt carrier → redemption row/handler 的唯一性**。

新形态“两行声称同一 premise”保护的是 **execution premise → registry row 的唯一性**。这不是旧外延的一支，而是另一个映射方向；且这个方向在本单之前已经有两层牙：`opening_synthesis.py:358-366` 的 import `DEBT_REGISTRY_PREMISE_AMBIGUOUS`，以及 `:407-425` 的 runtime `PREMISE_GATE_AMBIGUOUS`。证据 G 显示：同 premise 多行时，每张合法债的 exact hit 仍只有一个，真实 execution lookup 先报 premise 歧义；`DEBT_TYPE_AMBIGUOUS` 只在绕过真实执行入口的直调中出现。

因此：**新形态没有覆盖旧牙外延；它重复覆盖了已经被锁住的另一个方向。** 当前旧语义之所以仍成立，是 T3 用精确键把违规状态从类型/容器结构上消掉，不是新 `DEBT_TYPE_AMBIGUOUS` 在承重。

反查“哪个方向没有锁”：如果以后重新引入 obligation alias、大小写归一、兼容旧名或一对多 resolver，使一张债可能得到多个候选行，现有名为 `DEBT_TYPE_AMBIGUOUS` 的常驻锁不会红，因为它只造重复 premise；这就是卖掉的独立回归方向。今天之所以不能给该方向加入真实当前输入，不是现有缺陷挡锁，而是当前精确 `Literal` + dict 结构确实使违规态不可表示。

### 2. 旧触发是否结构性不可达

**是，按当前受支持类型和普通 dict 语义，旧触发结构性不可达。** 我独立试了四类候选：

1. 同字面 key 写两次：dict 覆盖旧 row，row count 仍为 1；
2. 大小写 alias：合法小写债只有一个 exact hit，大写 obligation 又被 schema 拒绝；
3. 不同 key、同 premise：债仍只有一个 exact hit，歧义发生在 premise 查行方向；
4. runtime 增加另一普通 key：精确 `registry[debt.obligation]` 仍只返回一行。

所以施工方关于“旧字面触发死亡”的窄论断成立。我没有构造出一张**合法** `EvidenceDebtV1` 同时命中两个普通 dict 行。但这不替施工方后半句背书：它随后选择的 duplicate-premise 并不是一债多处理器的等价形态。

### 3. 换键买到什么、卖掉什么

买到的是实质改进：债的下游义务进入闭枚举；`debt_id` 可任意改名而不影响接线；历史前缀即使保留，只要 `obligation=None` 就绝不接线；前缀伪造、偶然碰撞和一债多前缀命中均被精确键结构消除。证据 B 的两组同形输入与证据 C 的 AST 扫描都确认了这一点。

卖掉的是 B4 rework1 已签字的一个**独立错误方向与回归资产**：`DEBT_TYPE_AMBIGUOUS` 不再观察债侧多匹配，而改成 premise 侧已有牙的重复出口。当前健康行为没有因此变成静默错误，但未来若接线语义扩成 alias/normalization/兼容表，旧病复发时没有原来的那把锁提示维护者。这正是验收 #6 明令不得顺手拆掉的资产，故为阻断。

## 四、复核单 §二 / §三结论与 findings

### §二：#3 是真牙还是恒绿门

结论：**是可观测的具名牙，但今天是 mutation-only 的冗余 fail-fast/诊断牙，不是当前库存下唯一阻止静默成功的安全牙。**

- 真牙部分：删唯一行后，`assert_obligations_backed` 和 `redeemable_debt_ids` 都稳定报 `OBLIGATION_UNBACKED`；把未来第二值加入域而不加行，import 审计稳定报 `DEBT_REGISTRY_OBLIGATION_UNCOVERED`。
- 非唯一承重部分：同一次删行中，摘掉新 runtime check 后直连销账仍 `KeyError`；synthesis 所走的 premise 查找仍 `PREMISE_GATE_UNWIRED`。所以“不加这处改动”并不会把这个状态放绿，只会失去更早、更准确的错误码。
- 库存：今天域只有一个值、表也只有同一个 key，生产 10 个 mint 中仅一张 span 类非 `None`，没有第二个“扩枚举忘接线”的现实量。未来方向只有我对 `_OBLIGATION_DOMAIN` 做的独立变异在量。

据此把验收 #3 判通过，因为任务书要求的“无处理器必须响亮失败”确实成立；同时登记 N-1，不能把它描述成今天已有第二义务存货在咬。

### §三：换同形输入仍守得住

- #1：除施工测试点名形状外，我另测大写 alias、前空格、后空格；均拒绝。
- #2：不是各测一个例子，而是两条无关 debt_id + 正确 obligation 都接线，两条历史前缀 + `None` 都不接线；schema-bypass 的错误 obligation 也没有回落到前缀。
- #6：handler 用 `None`/`17`，prefix 用较短/较长键，载体搬移用两组不同非前缀 alias；结果一致。正是第二组同形输入确认了问题不是施工方某一个 alias 的偶然现象。
- #5：AST 对全 `src/` mint 点盘点，10 点全部量到；不是只抽 span 例子。

### 不阻断 findings（4）

1. **N-1 · #3 今天零未来值库存。** 新 runtime 牙真能响，但不是删行状态唯一的失败原因；“防未来扩枚举”今天靠变异量，没有真实第二枚举值/mint。
2. **N-2 · `DEBT_REGISTRY_PREFIX_AMBIGUOUS` 变成语义遗留牙。** 它机械可触发，故按 #6 的字面保住了；但精确键下两个 obligation 互为字符串前缀并不产生匹配歧义，而且今天任何第二 key 先天在枚举域外。它现在会限制未来合法命名，而不是保护当前接线。
3. **N-3 · 施工档的全树 grep 自证不实。** 它声称全 `src/` 只剩两处 `startswith`；独立 AST 实读是 33 个 call。所幸债 receiver 为 0，所以验收 #2 的业务结论仍成立。
4. **N-4 · 常驻测试含恒真断言。** `tests/test_b4_opening_synthesis.py:1131` 的 `assert ... or True` 永远为真。下一行 `:1132` 的真实 `not startswith(...)` 与本席独立探针补足了该方向，所以不升级为阻断，但恒真句本身没有任何牙。

## 五、未复现项清单

1. **未复现施工方逐次提交时的中间树测试**（`cb66ba90`、`2a9d44b0`、`ee86f5e1` 各自 checkout 后跑测）。本单审对象是终点 diff；切换工作树会增加复核期间误动预置 staged 请求单的风险，且七条均可在终点独立验。
2. **未复现施工方全量耗时 `461.18s`。** 本席同命令耗时 `470.34s`；通过/skip/xfail 数和 exit 一致，耗时不是验收量。
3. **未复现一个合法当前债真正同时命中两个处理器。** 已试 duplicate key、大小写 alias、同 premise 多行、runtime 增键，均不能形成该状态；这项“未复现”本身就是 §一第 2 问的结论依据。
4. **未跑施工测试的摘源码—改文件—还原流程。** 复核纪律禁止改项目代码；我全部使用进程内变异并在 `finally` 恢复表/域/函数，随后全量测试通过且 git 状态未出现项目代码改动。
5. **未对真实 B3 四立面字节逐面重跑 retirement。** 本单 #4 只要求源绑定不被碰；我用基点/终点代码块哈希和销账 guard 哈希逐字核了这一点，没有把上一单已过审的真实字节行为扩大为本单新验收。

## 六、复核期间是否改过项目代码

**未改项目代码。** 未执行 `pip install -e .`，未写 `site-packages`，未进入或改动 `/workspaces/EnergyPlus-Agent-dev`。所有攻击均为单个 Python 进程内变异并恢复；本席只新增本裁决文件。主控预置且已 staged 的复核请求单保持原样。
