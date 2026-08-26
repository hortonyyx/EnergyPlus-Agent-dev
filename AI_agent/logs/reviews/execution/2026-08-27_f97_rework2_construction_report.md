# 施工报告 · F-97 契约判别器【第二轮返工】（Claude 家族）

- **日期**：2026-08-27　**施工席位**：Claude 家族　**复核席位（已定）**：GLM 家族（⛔ 我不审自己）
- **worktree**：`/tmp/ep_f97`　**分支**：`wt/08.27_f97_contract`　**起点**：`f2a8ccf`
- **交件提交链**：`8f9728f`（主修）→ `f30f89e`（我自己 4 把假锁的返工）→ ``41a568a``（最后 1 把假锁）
- **派工单** → [`../request/2026-08-27_f97_rework2_dispatch.md`](../request/2026-08-27_f97_rework2_dispatch.md)
- **返工依据** → [`../verdict/2026-08-27_f97_rework_glm_verdict.md`](../verdict/2026-08-27_f97_rework_glm_verdict.md)

> **本报告累计式自包含**：⛔ 不引用「上一轮不变」，需要的前提都在文内复述。

---

## 〇、开工自检（三问全对，⛔ 未触发停下上报）

| # | 要求 | 实测 |
|---|---|---|
| ① | HEAD == `f2a8ccf` | `f2a8ccf 08.27_F97Rework_DeclaredSchemaNeverFallsBackToLegacy_AndTheLedgerGoesFirst` ✅ |
| ② | `grep -c '' AI_agent/CLAUDE.md` == 447 | `447` ✅ |
| ③ | `AI_agent/guides/reading_correction_split_guide.md` 存在 | 存在（28128 B）✅ |
| 附 | 4 份 orchestrator untracked md | 4 份全在，⛔ 未删未提交 ✅ |

---

## 一、改了什么

| 文件 | 改动 |
|---|---|
| `src/agent/reading/vector_contract.py` | BLK-A 后置规则 · `_declares_unregistered_schema` 的 `isinstance` 前置 · `_classify_one`（`is_file()` 边界 + `OSError` + `UnicodeDecodeError` + 兜底网）· 非字符串声明的 reason 措辞 · 纪律 #5 改写 + 新增纪律 #6 |
| `src/agent/pipeline.py` | `run_pipeline_artifacts` 函数开头调 `_preflight_vector_contracts` · `_write_vector_contract_ledger` 兑现 never-raises · 两处 docstring 的假断言改写成真话 |
| `tests/test_f97_vector_contract.py` | R5 / R6 / R7 三组共 **43 条**新锁 |

⛔ 未动任何第四个文件。⚠️ 派工单 §四 写「不要动 `src/agent/pipeline` 以外的模块」，
而 §二 BLK-A / BLK-C 的逐字要求全部落在 `src/agent/reading/vector_contract.py`（不在 `src/agent/pipeline` 里）——
按 §五(b) 记为外围口径冲突，我按「只碰 F-97 这几个模块、别游荡」执行（详见 §七#3）。

### 1.1 BLK-A —— 后置规则，⛔ 双命中没塌

```python
    matches = [spec for spec in CONTRACTS if spec.detect(raw)]
    if len(matches) == 1:
        only = matches[0]
        if only.contract_id == CONTRACT_READING_VIEW_LEGACY and "schema" in raw:
            return ContractDecision(CONTRACT_UNKNOWN, None,
                "declares schema=... but matches no registered contract's key set, "
                "so it is a malformed declaration, not an undeclared legacy view; ...")
        return ContractDecision(only.contract_id, only.disposition, None)
```

⭐ **`len(matches) == 1` 是这条规则的全部安全性所在**：真·双命中（已登记值 + 该契约键集 + legacy 结构）
是 `len(matches) == 2`，**根本进不到这一句**，仍走 AMBIGUOUS。

⛔ 派工单点名「上一轮第一版就在这儿塌过一次（写『有 `schema` 键就不是 legacy』）」——
那个写法是改 `_detect_legacy_reading_view`，会把双命中打成单命中。
**本轮没有动那个函数的那一句**，而且**专门加了一条变异（N7）把那个塌法原样写回去**，
用红集**证明**三条 AMBIGUOUS 守卫真的会红（§四）。⛔「我没塌」不能只是我的自述。

⚠️ 覆盖面：`_detect_legacy_reading_view` 里原有的「未登记声明 ⇒ 不是 legacy」**保留不动**，
所以「未登记值」走 R1 老路（reason 点名那个值），「已登记值 + 键集不满足」走新后置规则。
返工要求原文「不匹配**任何**已登记契约」的两半都落地了。

### 1.2 BLK-B —— 提到组合入口最前面

`run_pipeline_artifacts` 的第一件事（在 `parse_testdata_text` 之前）：

```python
    _preflight_vector_contracts(
        vector_dir, None if out_dir is None else out_dir / "1_correction"
    )
```

⚠️ **没有用 `_stage("1_correction")`** —— 那会在拒绝之前把 `1_correction` 目录建出来，
而 `tests/test_run_stage_flow.py:572,585` 正好断言「此刻它还不该存在」。账本写入只用 `.parent`，目录本身用不上。
（第一版我写的确实是 `_stage(...)`，全量绿；是我自己回头查「有没有人拿这个目录的存在当信号」时抓到的，见 `f30f89e`。）

`run_correction` 里那次 `_preflight_vector_contracts` **保留** —— 它仍是一个独立真实入口，
第二次写账是同内容幂等覆写。

### 1.3 BLK-C —— 边界，⛔ 不是更长的 except 元组

```python
def _classify_one(vector_dir, name) -> tuple[ContractDecision, str | None]:
    path = Path(vector_dir) / name
    try:
        if not path.is_file():
            return _unintelligible(name, "not a readable regular file (...)")
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc: ...      # 「not valid UTF-8」
    except OSError as exc: ...                 # 「unreadable file: <类型>」
    except Exception as exc: ...               # 兜底网
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc: ...    # 措辞逐字沿用旧版
    except Exception as exc: ...               # 兜底网
    try:
        return classify_vector_json(raw), None
    except Exception as exc: ...               # 兜底网
```

三条设计理由，**全部是判据③ 实测逼出来的，不是我预判的**：

1. **`is_file()` 是边界不是第四个 except**。`0_reading/p.json` 是个 **fifo** 时，
   `read_text` **不抛异常，直接挂死** —— 我第一次跑判据③ 探针就撞上了，**工具 2 分钟超时**才停。
   ⛔ 挂死没有任何 `except` 接得住。`is_file()` 一条规则同时挡住 目录 / 断链符号链 / 符号链环 / fifo。
2. **`_declares_unregistered_schema` 先 `isinstance(..., str)`**（返工要求逐字）。
3. **兜底网**：返工要求的字面处方是「捕 `OSError` 与 `UnicodeDecodeError`」，
   而判据③ 实测到 **20 万层嵌套 JSON ⇒ `json.loads` 抛 `RecursionError`**，
   它**既不是 `OSError` 也不是 `UnicodeDecodeError`** ⇒ **照处方改完这一条仍然会崩**。
   这正是 [[lexical-guard-cannot-be-completed]]：按异常类型枚举防线，和按文件名模式枚举防线，是同一种形状，永远补不完。

⚠️ 兜底网带显式前缀常量 `UNEXPECTED_FAILURE_PREFIX = "unexpected classifier failure"`，
**每条点名路径的锁都断言这个前缀「不在」reason 里** —— 否则兜底网会替被测机制把测试撑绿，
摘掉那个机制照样不红（[[neuter-proves-wiring-not-discriminating-power]]）。N3 / N4a / N4b 的红集证明这道防线有效。

### 1.4 第四种「never raises 为假」：账本自己的写盘（返工要求里没有，判据③ 撞出来的）

`_run` 已经是个**文件**时，`run_meta_path(..., for_write=True)` 的 `mkdir` 抛 `FileExistsError`（`run_meta.py:20`），
从 `_write_vector_contract_ledger` 里冒出去 ⇒ 带毒文件的 `run_correction` 死在 `FileExistsError` 上，
**F-b 的点名失败被 F-c 的存储失败一起带走了**。

裁决书原文点名的正是「`ledger_for` 的 never raises **与** `pipeline.py:731-732` 注释
『`_write_vector_contract_ledger` never raises』**均**为假」⇒ 两个承诺都在被审范围内。
改法：写盘失败记 `logger.warning` 后返回 `None`，**分类的响亮判决照常落地**。
（账本丢在不可写的 run 目录上没救；把点名失败**也**一起丢掉是净损失。）

---

## 二、⭐⭐⭐ 三格判据 —— 三条阻断逐条读数

判据① / ② 用同一份探针文件（**每条都断言缺陷存在**）：`scratchpad/f97probe/test_grid1_repro.py`，11 条。

- **在 `f2a8ccf` 上：`11 passed`** ⇒ 三条阻断**全部复现**（⛔ 没有触发「复现不出来 ⇒ 停下上报」）。
- **在修复后：`10 failed, 1 passed`** ⇒ 10 条断言缺陷的全部不再成立；
  唯一仍绿的是 `test_blkB_positive_control_non_view_name_is_named_and_ledgered`
  —— 它断言的是**正确行为**（同一毒文件改名 `mystery.json` 走正确路径），本来就该绿。

### BLK-A｜已登记值的畸形声明仍回落 legacy 并被静默消费

| 格 | 读数 |
|---|---|
| ① `f2a8ccf` 复现得出 | `{"schema": <v>, "image_label":"1f", "image_kind":"plan", "strokes":[合法 stroke]}`，三个已登记值 `as_drawn_plan_v2` / `as_drawn_plan_v0` / `as_drawn_elevation_v0` **全部** ⇒ `reading_view_legacy / consume`。经 `_build_correction_messages` 实测：**声明串原文出现在 human 提示词里**。 |
| ② 新 commit 复现不出 | 三值全部 ⇒ `unknown / None`，reason 点名所声明的值。 |
| ③ 换同形输入 | 见下表。 |

**③ 我按什么方向找的**（⛔ 不是抄派工单清单）：把「声明」这件事拆成四个正交轴，问
**「哪些组合会落在已登记契约之间的缝里」**——
**(A) 值登记 / 未登记 · (B) 键集完整 / 残缺 · (C) 值是字符串 / 不是 · (D) 声明在顶层 / 在嵌套里**。
阻断只占 `A=登记 × B=残缺 × C=字符串 × D=顶层` **一个格**；其余格是「改法容易顺手打坏」的地方。

| 形态（我造的） | `f2a8ccf` | 修复后 | 判 |
|---|---|---|---|
| v2 + `strokes`，**零** as-drawn 键 | legacy/**consume** | unknown（点名 `as_drawn_plan_v2`）| 缺陷·已修 |
| v2 + 仅 `observations` + `strokes` | legacy/**consume** | unknown | 缺陷·已修 |
| v2 + `observations`+`declarations`（缺 `hypotheses`）+ `strokes` | legacy/**consume** | unknown | 缺陷·已修 |
| plan_v0 + 仅 `wall_bands` + `strokes` | legacy/**consume** | unknown | 缺陷·已修 |
| elev_v0 + 仅 `openings` + `strokes` | legacy/**consume** | unknown | 缺陷·已修 |
| `schema='AS_DRAWN_PLAN_V2'`（全大写）| unknown | unknown | 本就正确 |
| `schema=' as_drawn_plan_v2'` / `'as_drawn_plan_v2 '` / `'as_drawn_plan_v2\n'` | unknown | unknown | 本就正确 |
| `schema='as-drawn-plan-v2'`（连字符）| unknown | unknown | 本就正确 |
| `schema=''` | unknown | unknown | 本就正确 |
| `schema=null` | unknown，**但 reason 写「declares no `schema` field」** | unknown，reason 改成「declares a non-string schema=None (NoneType)」 | **措辞错·已修** |
| `{"meta": {"schema": v2}, "strokes": [...]}`（嵌套声明）| legacy/consume | legacy/consume | **未改 · 见 §六#4** |
| v2 + 三键**齐全** + `strokes`（真·双命中）| AMBIGUOUS | AMBIGUOUS | ⭐ 守住 |
| plan_v0 + 两键齐全 + `strokes` | AMBIGUOUS | AMBIGUOUS | ⭐ 守住 |
| elev_v0 + 两键齐全 + `strokes` | AMBIGUOUS | AMBIGUOUS | ⭐ 守住 |

⭐ 大小写/空白/连字符那一组**本来就是对的**（走 R1 未登记路径）。这条读数有独立价值：
它说明**「把 schema 值 normalize 一下再比对」是错的修法** —— 那会把 `AS_DRAWN_PLAN_V2` 静默认成
`as_drawn_plan_v2`，等于替产物决定它声明了什么。⛔ 我没有那么做。

### BLK-B｜`run_pipeline` 在分类/ledger 之前自己解析 `*_view.json`

| 格 | 读数 |
|---|---|
| ① `f2a8ccf` 复现得出 | `1f_view.json = [1,2,3]` 走 `run_pipeline_artifacts` ⇒ `AttributeError: 'list' object has no attribute 'get'`，抛点 `src/agent/reading/legacy.py:108`，途经 `pipeline.py:1368`，**账本不存在**。非法 JSON ⇒ `JSONDecodeError`，抛点 `legacy.py:177`，同经 `:1368`，**账本不存在**。**正对照**：同一毒文件改名 `mystery.json` ⇒ `UnconsumableVectorFile`（经 `pipeline.py:694`）+ **账本在盘**。 |
| ② 新 commit 复现不出 | 两条均 ⇒ `UnconsumableVectorFile`（经新 preflight），点名 `1f_view.json`，**账本在盘**、`consumed == []`。 |
| ③ 换同形输入 | 见下表。 |

**③ 我按什么方向找的**：⛔ 不问「什么毒文件能崩」，而问
**「这个函数在调 `run_correction` 之前，一共有几处会去读 `0_reading` 的东西，各自的第一个崩点在哪」**。
方法 = 对 `src/` 全仓 grep `glob("*` / `load_reading_view` / `discover_vector_files`，再对每条路造一个能走到它的输入。

| 形态 / 路径 | `f2a8ccf` | 修复后 |
|---|---|---|
| `[1,2,3]` 当 `*_view.json` | `AttributeError` @ `:1368`，无账 | 点名 + 有账 |
| 非法 JSON 当 `*_view.json` | `JSONDecodeError` @ `:1368`，无账 | 点名 + 有账 |
| **非法 UTF-8 当 `*_view.json`** | `UnicodeDecodeError` @ `:1368`，无账 | 点名 + 有账 |
| **`2f_view.json` 是个目录** | `IsADirectoryError` @ `:1368`，无账 | 点名 + 有账 |
| **`2f_view.json` 是断链符号链** | `FileNotFoundError` @ `:1368`，无账 | 点名 + 有账 |
| **`backup.json`（非 view 名）是个目录** | `IsADirectoryError` @ `pipeline.py:669`（账本写入体内），无账 | 点名 + 有账 |
| ⭐ **v3 profile（`orthogonal_polygon`）+ 一份完全正常的 legacy 视图** | `WindowResolverInputError: observation_reference_catalog_unavailable` @ `window_sources.py:627`，经 **`pipeline.py:1411`**，**无账** | 同样的失败，**账本在盘** |
| `run_pipeline`（非 `_artifacts` 的那层包装）| 同 `[1,2,3]`，无账 | 点名 + 有账 |

⭐⭐ **`:1411` 这一格最值得看：它根本不需要毒文件。**
一份**完全合法**的 `0_reading` 在 v3 profile 下就会死在 catalog 上，而 F-c 承诺的账**一行都没有**。
⇒ **F-c 破的不只是「输入形态」这个轴，还有「那次 run 因为什么原因失败」这个轴**（见 §七#2）。

⭐ **关于 `:1376`：我复现不出它当「第一个崩点」，而且这不是我没找到 —— 它结构上被 `:1368` 遮住了。**
凭据：`:1368` 的 `compute_reading_report_from_vector_dir`（`evidence_preflight.py:229-230`）
**没有任何 try/except**，且 glob 模式与 `:1376` **逐字相同**（`sorted(vector_dir.glob("*_view.json"))`），
调的是同一个 `load_reading_view`。⇒ 任何能杀死 `:1376` 的载荷，**必然先杀死 `:1368`**。
派工单要求「`:1376` / `:1411` 那两条路各来一次」——`:1411` 我用载荷走到了；
**`:1376` 我改用结构性锁覆盖**（R6 的两条顺序锁），⛔ 而不是编一个走不通的载荷来凑格子。

**「还有没有第四个解析入口」的普查结果**（全仓 grep）：

| 位置 | 判 |
|---|---|
| `pipeline.py:92` `discover_vector_files` | 只 glob 名字不读内容，是排序键 |
| `pipeline.py:528` `_reading_window_stroke_count` | 在 `run_correction` 体内（`:765`），**在 preflight 之后**。⚠️ 但它自己 `except (JSONDecodeError, OSError)` —— 漏 `UnicodeDecodeError`（它是 `ValueError` 不是 `OSError`），且对非对象会 `AttributeError`。**同一个错误的第二份拷贝**，今天被 preflight 挡在前面。未改，记入 §六#5 |
| `pipeline.py:1378` / `evidence_preflight.py:229` / `window_sources.py:841` | 组合入口的三个消费者，**已全部被 preflight 前置** |
| `correction/envelope.py:403,584` | 在 correction 之后，不在本承诺范围 |
| `execution/validation_run.py:253,281,315` | **另一个编排入口**（validate_case 的 0_reading 自检），不在 1_correction 消费链上。⛔ 未擅自扩范围，记入 §六#8 + §七#2 |
| `execution/isolation.py:968,1434` | reading 环节自己的产出目录，不是 correction 的输入 |

### BLK-C｜「ledger 永不抛」前提不成立

| 格 | 读数 |
|---|---|
| ① `f2a8ccf` 复现得出 | `schema=[]` ⇒ `TypeError: unhashable type: 'list'` @ `vector_contract.py:117`；`schema={}` ⇒ `TypeError: unhashable type: 'dict'` 同一行；非法 UTF-8 ⇒ `UnicodeDecodeError` @ `<frozen codecs>:322`；`backup.json` 是目录 ⇒ `IsADirectoryError [Errno 21]` @ `pathlib.py:1013`。四者账本**均不存在**；经真实 `run_correction` 同样无账。 |
| ② 新 commit 复现不出 | 四者全部 ⇒ `ledger_for` 正常返回，对应文件一行 `unknown/error` + 具体 reason；经 `run_correction` ⇒ 点名 + 账本在盘。 |
| ③ 换同形输入 | 见下表。 |

**③ 我按什么方向找的**：问
**「`glob('*.json')` 交回来一个名字，如果它背后不是一个『可读的、UTF-8 的、能 parse 的普通文件』，操作系统会还我什么」**。
四个轴：**(a) 不是普通文件 · (b) 是普通文件但字节解不开 · (c) 解得开但 parse 不了 · (d) parse 得了但判别器自己炸**。

| 轴 | 形态（我造的） | `f2a8ccf` | 修复后 |
|---|---|---|---|
| a | 目录名叫 `d.json` | `IsADirectoryError` | 一行 `unknown/error`「not a readable regular file」 |
| a | **断链符号链** | `FileNotFoundError [Errno 2]` | 同上 |
| a | **符号链环** | `OSError [Errno 40] Too many levels of symbolic links` | 同上 |
| a | **名字在清单里但文件已消失**（TOCTOU；`ledger_for` 的 `names` 由调用方给）| `FileNotFoundError` | 同上 |
| a | ⭐ **fifo 名叫 `p.json`** | **不抛异常，`read_text` 挂死**（探针跑到工具 2 min 超时）| 同上，**立即返回** |
| b | `b"\xff\xfe\x00"` | `UnicodeDecodeError` | 一行「not valid UTF-8」 |
| b | **UTF-16-LE BOM 产物** `b"\xff\xfe{\x00}\x00"` | `UnicodeDecodeError` | 同上 |
| b | **单个 latin-1 字节** `b'{"a": "caf\xe9"}'` | `UnicodeDecodeError` | 同上 |
| c | ⭐ **20 万层嵌套 JSON** | `RecursionError: maximum recursion depth exceeded while decoding a JSON array` | 一行 `unknown/error`，reason 带兜底网前缀 + `RecursionError` |
| d | `schema=[]` / `schema={}` | `TypeError: unhashable` | 一行「non-string schema」 |
| d | **`schema=3` / `schema=true`** | **不崩**（int/bool 可哈希，走未登记路径）| 同左 |
| — | ⭐ **`_run` 已经是个文件** | `FileExistsError` @ `run_meta.py:20`；带毒文件时 `run_correction` 死在这，**点名失败也没了** | 记 warning，**`UnconsumableVectorFile` 照常抛出** |
| — | 账本路径已经是个目录 | `IsADirectoryError` @ `pipeline.py:674` | 同上 |

⭐ 三条最有信息量的读数：

1. **fifo 是挂死不是崩** —— 比裁决书举的三种都糟（没有异常、没有超时、没有账），
   而且它证明**「把 except 元组加长」这个修法方向本身不够**，必须有 `is_file()` 这道边界。
2. **`RecursionError` 不在返工要求的处方里** —— 照字面处方改完，这一形态仍然会崩。
   ⇒ 兜底网不是「顺手加固」，是判据③ 逼出来的。
3. **`schema=3` / `schema=true` 本来就不崩** —— 只有 list/dict 不可哈希。
   ⇒ 阻断只占 (d) 轴的一半；若按「是 list 或 dict 就特判」去修，就是把代理量当成了它代表的东西
   （[[proxy-mistaken-for-the-thing]]）。实际改法 `isinstance(..., str)` 覆盖整个 (d) 轴。

### ⭐ 判据③ 的额外产物：我的改动**顺带关掉了 GLM 记的 N-A 漂移方向之一**

不改源码、只用 monkeypatch 演示两个漂移方向（GLM 在 `f2a8ccf` 上测过同样两条）：

| 漂移 | `f2a8ccf`（GLM 读数）| 修复后（我的读数）|
|---|---|---|
| 只加 `ContractSpec`、值没进 `DECLARED_SCHEMA_VALUES` | 原 AMBIGUOUS 文件**静默塌成单判**（丢纪律 #4）| `future_contract/known_not_consumed` —— **仍然塌，未改善** |
| 只把值加进集合、没加 spec | **B-01 经漂移重开**（声明了已登记值 + `strokes` ⇒ 照样被消费）| ⭐ **`unknown/None`** —— **不再静默消费** |

⇒ N-A（第二处手写清单无机械对账）**仍在**，但**唯一会产生「静默消费」的那个方向已经被后置规则堵死**，
剩下的方向只丢失歧义报告、不丢失 fail-closed。N-A 按派工单 §四本轮不做，此处只记读数。

---

## 三、新增的锁（43 条）

| 组 | 条数 | 入口 |
|---|---|---|
| **R5**（BLK-A）| 17 | 7 判别器直调（三值 × 残缺键集）· 3 `_build_correction_messages`（**真实入口**）· 3 `classify_vector_dir`（门函数本体）· **3 双命中 AMBIGUOUS 守卫（三值全覆盖，旧 R2 只覆盖 v2）** · 1 真实 `run_correction` + 盘上账本 |
| **R6**（BLK-B）| 9 | 3 真实 `run_pipeline_artifacts` 负例（非对象 / 非法 JSON / 非法 UTF-8）· 1 `run_pipeline` 包装层 · 3 文件系统形态走组合入口 · 1 **点名式顺序锁** · 1 ⭐ **消费者无关的顺序锁** |
| **R7**（BLK-C）| 17 | 9 形态 × `ledger_for` 不抛 + 具体 reason · 1 TOCTOU · 1 **fifo 不挂死**（SIGALRM 围栏）· 1 兜底网可达（`RecursionError`）· 2 真实 `run_correction` 形态锁 · 1 目录经 `run_correction` · 2 恶劣 run 目录 |

⭐ **R6 的两条顺序锁是本轮我认为最有价值的一条设计**：

- **点名式**（`test_r6_ledger_is_on_disk_before_every_view_consumer`）：spy 包住
  `compute_reading_report_from_vector_dir` / `load_reading_view` / `build_observation_reference_catalog_from_run`，
  断言**每一个被调用的那一刻账本已经在盘**，并断言调用顺序。
- ⭐ **消费者无关式**（`test_r6_no_reading_file_is_read_before_the_ledger_is_on_disk`）：
  拦 `Path.read_text` / `Path.read_bytes`，断言**任何一处读 `0_reading` 里的文件、且调用栈不经过
  `vector_contract.py` 的，都发生在账本落盘之后**。
  **第四个消费者接上去当天就会被抓，⛔ 不需要配夹具、也不需要有人想起来加 spy。**

⚠️ 第一版我给点名式那条写的 docstring 说「第四个消费者接上去当天就会被抓」——
**那句话我的代码兑现不了**（spy 只认识三个名字）。这是
[[design-doc-described-what-code-never-implemented]] 的形状：**我产出的叙述比我产出的东西更合规**。
`f30f89e` 里改掉了措辞，并**补上真正兑现那句话的锁**。

---

## 四、A-neuter：9 个变异逐条摘掉，每个跑全量 `-n 6`

⚠️ 变异**全部在源码侧**，测试文件一字未动；每次跑完 `git checkout --` 还原并 `status --porcelain` 核净（9/9 `TREE CLEAN`）。
⚠️ 变异脚本 `scratchpad/neuter/apply.py` 对每个锚点做 `assert s.count(old) == 1`
⇒ **锚点没命中会当场 assert 失败，⛔ 不存在「变异其实没生效却报了绿」**。

**被审对象 = 最终提交；`passed + failed` 恒 = 3113。**

| # | 摘掉什么 | summary 行（逐字）| 红集 |
|---|---|---|---|
| **N1** | BLK-A 后置规则 | `14 failed, 3099 passed, 13 xfailed, 211 warnings in 361.87s (0:06:01)` | R5 的 14 条（7+3+3+1）。⭐ **3 条 AMBIGUOUS 守卫仍绿**（正确：守卫与后置规则彼此独立，由 N7 覆盖）|
| **N2** | `run_pipeline_artifacts` 的 preflight | ``9 failed, 3104 passed, 13 xfailed, 211 warnings in 367.19s (0:06:07)`` | `**R6 全部 9 条**（含收紧后的 `directory_named_non_view`）—— ⭐ 收紧前它在这次变异下是绿的，见下文对账` |
| **N3** | `isinstance(..., str)` 前置 | `3 failed, 3110 passed, 13 xfailed, 211 warnings in 368.81s (0:06:08)` | 两条不可哈希形态 + 1 条 `run_correction` 形态锁。⭐ `schema=null` 仍绿（正确：`None` 可哈希，不走 TypeError；由 N8 覆盖）|
| **N4a** | `is_file()` 边界 | `6 failed, 3107 passed, 13 xfailed, 211 warnings in 362.19s (0:06:02)` | 目录 / 断链 / 符号链环 / TOCTOU / **fifo** / 目录经 `run_correction` |
| **N4b** | `OSError` / `UnicodeDecodeError` 两个 except | `4 failed, 3109 passed, 13 xfailed, 211 warnings in 364.86s (0:06:04)` | 三条字节解不开的形态 + 1 条 `run_correction` 形态锁 |
| **N5** | `json.loads` 外的兜底网 | `1 failed, 3112 passed, 13 xfailed, 211 warnings in 371.00s (0:06:11)` | `RecursionError` 那条 |
| **N6** | 账本写盘的 `OSError` 守卫 | `2 failed, 3111 passed, 13 xfailed, 211 warnings in 363.25s (0:06:03)` | 两条恶劣 run 目录锁 |
| **N7** ⭐ | **复现「上一轮塌过的那个写法」**：`_detect_legacy_reading_view` 里把 `if _declares_unregistered_schema(raw)` 换成 `if "schema" in raw` | `6 failed, 3107 passed, 13 xfailed, 211 warnings in 371.75s (0:06:11)` | **3 条新 AMBIGUOUS 守卫 + 3 条旧的**（`test_r2_registered_schema_plus_legacy_is_still_ambiguous` · `test_b3_double_match_reports_ambiguity_instead_of_picking_one` · `test_b3_ambiguous_file_fails_loudly`）|
| **N8** | 非字符串声明的 reason 分支 | `4 failed, 3109 passed, 13 xfailed, 211 warnings in 370.82s (0:06:10)` | 3 条 nonstring 形态（含 `null`）+ 1 条 `run_correction` 形态锁 |

⭐ **N7 是本轮 neuter 里我最看重的一条**：派工单点名「别再塌」，而「我没塌」只是我的自述；
N7 把那个塌法原样写回去，用红集**证明**三条 AMBIGUOUS 守卫真的会红。

### ⭐⭐ 43 把锁的红集对账 —— 以及它抓到的**我自己的 5 把假锁**

把 9 次红集并起来，逐把追问「摘掉哪个机制它会红」：

| 组 | 条数 | 被哪个变异红过 |
|---|---|---|
| R5 | 17 | N1（14）+ N7（3）= **17/17** |
| R6 | 9 | N2（9）= **9/9** |
| R7 | 17 | N3(3) ∪ N4a(6) ∪ N4b(4) ∪ N5(1) ∪ N6(2) ∪ N8(+1 `null`) = **17/17** |
| **合计** | **43** | **43/43 ⇒ 每一把锁都至少在一个变异下红过** |

**到这一步是分三次做到的，中间两次都是我自己的错：**

1. **第一次对账（`8f9728f`，7 个变异）：33/42 覆盖。** 逐条追问剩下 9 把，发现
   **5 把是我写的假锁** —— TOCTOU 锁只断言 `disposition == "error"`；两条 `run_correction` 形态锁
   和目录锁只断言「账本在盘」。**这些断言兜底网自己就能满足** ⇒ 摘掉它们要守的机制，它们照样绿。
   ⇒ `f30f89e`：全部改成断言**具体 reason** + 断言 reason 里**没有**兜底网前缀。
2. **第二次对账（`f30f89e`，8 个变异）：41/43。** 剩两把：
   - `nonstring_schema_null` —— 归属于**我加了但从没 neuter 过的机制**（非字符串 reason 分支）⇒ 补 **N8**，覆盖。
   - `directory_named_non_view` —— 见下。
3. **第三次（最终提交）：43/43。**

### ⭐ 最后那一把（`directory_named_non_view`）的定性：**真的没有分辨力，不是变异没生效**

派工方要求把这两种情况分开，并要**变异自己报出它确实生效了**。逐条：

- **变异确实生效**：同一次 N2 变异下，**同一个参数化函数的另外 2 个参数
  （`directory_named_view` / `dangling_symlink_view`）都红了**
  ⇒ 变异到位、这个测试函数本身被执行到了，绿的只是这一个参数。
  （加上 `apply.py` 的 `assert s.count(old) == 1` 锚点断言，两侧都排除了「变异没打到」。）
- **为什么真的不红**：`backup.json` **不匹配 `*_view.json`**，组合入口的三个消费者根本不读它；
  摘掉 hoist 之后它照样被 `run_correction` **自己的** preflight 接住
  ⇒ 「抛了 `UnconsumableVectorFile` + 账本在盘」这个断言**由两条独立机制各自都能兑现**。
- **⇒ 该收紧，不是该删**。实测出的判别点：

  | 观测量 | 修复后 | 摘掉 hoist（N2）|
  |---|---|---|
  | 抛 `UnconsumableVectorFile` | ✅ | ✅（`run_correction` 接住）|
  | 账本在盘 | ✅ | ✅（`run_correction` 写的）|
  | ⭐ `out_dir/0_reading/reading_checks.json` 存在 | **否** | **是**（`:1368` 先把 reading report 落了盘）|

  ⇒ 改成断言 **`out_dir/0_reading/reading_checks.json` 不存在** —— 即
  **「拒绝必须发生在 reading report 之前，⛔ 不是之后」**。这才是这条锁真正要守的东西。
  见最终提交 `41a568a`；⭐ 它在 N2 下**由绿转红**（N2 红集 8 → 9），见 §四 的 N2 行。

⭐ 这三轮对账的方法论教训，比三条阻断本身更值得记：
**neuter 的验收不能只看「有没有红」，要看「每一把新锁分别在哪一次红过」；
从没红过的锁必须逐把给出理由，而「理由」只有两种合法形态 ——
①「它是守卫，由另一个变异覆盖」（⇒ 补那个变异），②「它没有分辨力」（⇒ 收紧或补锁）。**

---

## 五、全量

| 跑次 | 对象 | summary 行（逐字）| 退出码 |
|---|---|---|---|
| 基线 | `f2a8ccf` | `3070 passed, 13 xfailed`（**GLM 实测，本轮我未重跑**）| — |
| 干净树 A | `8f9728f` | `3112 passed, 13 xfailed, 211 warnings in 359.99s (0:05:59)` | 0 |
| 干净树 B | `f30f89e` | `3113 passed, 13 xfailed, 211 warnings in 357.39s (0:05:57)` | 0 |
| 干净树 C | 最终提交 | ``3113 passed, 13 xfailed, 211 warnings in 361.12s (0:06:01)`` | `0` |

⚠️ **基线口径我据实说明**：`3070` 是 GLM 在 `f2a8ccf` 上的读数，**我没有重跑**。
我核的是**算术与恒等**：3070 + 42 = 3112 ✓、3070 + 43 = 3113 ✓，
且 9 次 neuter 的 `passed + failed` **恒等于 3113** ✓。

**A-兼容面**：`test_r3_every_real_sidecar_still_parses_as_the_producer_type`（`==43`）与
`test_r3_all_real_legacy_views_still_consumed`（`==328`）两条硬断言 **未动、原值通过**，
在 9 次 neuter + 3 次干净全量共 12 次跑测里**全绿**。
⇒ BLK-A 的收紧（顶层带 `schema` 却不满足任何已登记键集 ⇒ 不再 consume）
在**全仓 `0_reading` 语料上零命中**。

---

## 六、⭐ 我认为最可能塌的地方

> 派工单：「自陈不确定 ≠ 已处理 —— 识别出弱点就当场修掉，修不掉写清为什么」。
> 每条都标了【已修】/【未修 + 为什么】。

1. **【已修】我自己写的 5 把锁没有分辨力**（§四）。
   这是本轮我犯的最实的一个错，而且是**红集对账**抓到的，⛔ 不是我读代码读出来的。

2. **【已修】点名式顺序锁的 docstring 超出了它的实现**（§三）。补了消费者无关的那条。

3. **【已修】`_stage("1_correction")` 的建目录副作用**（§一.1.2）。

4. **【未修 · 记名】⭐ `{"meta": {"schema": ...}}` 这类嵌套声明仍被当 legacy 消费。**
   为什么不修：契约的定义是「**顶层** `schema` 字段」，嵌套里出现同名键在语义上不是一次声明；
   要改就得先定义「**什么算一次声明**」，那是契约数据面的事（和 N-A 一起另开单）。
   ⚠️ 风险：如果将来某个生产者把声明包进信封（`{"meta": {...}, "views": {...}}`），
   这条缝会**立刻变成 BLK-A 的翻版**。
   **这是我认为本轮最可能在下一轮被判成缺陷的一条。**

5. **【未修 · 记名】`pipeline.py:528` `_reading_window_stroke_count` 是同一个错误的第二份拷贝。**
   它 `except (JSONDecodeError, OSError)` —— 漏 `UnicodeDecodeError`，且对非对象 JSON 会 `AttributeError`。
   今天它被 preflight 完全挡在后面（两个入口都是），所以够不着。
   为什么不修：修它要么复用判别器（超出本轮范围），要么**再抄一遍 except 清单**（正是本轮判定为错误方向的修法）。
   ⚠️ 风险：**它是「preflight 一定跑在前面」这个不变量的隐藏消费者**；
   哪天有人给 `run_correction` 加一条绕过 preflight 的分支，它会第一个静默现形。

6. **【未修 · 记名】兜底网可能替真 bug 背锅。**
   缓解：reason 里点名异常类型 + 文件名，该文件成为 offender（响亮），
   且 `UNEXPECTED_FAILURE_PREFIX` 被每条点名锁断言「不在」。
   ⚠️ 残余风险：真实 run 里出现一行兜底网的账，读的人可能读成「这份文件坏了」而不是「我们的代码坏了」。

7. **【未修 · 记名】消费者无关那条锁依赖 `pipeline.py` 里 `load_reading_view` 仍是函数内 import。**
   若有人把它提到模块级，monkeypatch 就不生效 —— 但那样点名式锁的 `seen` 列表会对不上而**变红**（fail closed），
   ⛔ 不会静默失效。

8. **【未修 · 记名】`validation_run.py:281` 是另一个会解析 `0_reading` 的编排入口。**
   F-97 的承诺按原文不覆盖它（不在 1_correction 的消费链上）。⛔ 我没有擅自扩范围。
   但 GLM 给的病根句「**所有**会碰 `0_reading` 的入口」按字面读是覆盖它的
   ⇒ **这是范围口径分歧，请复核方裁一下**（见 §七#2）。

---

## 七、⚠️ orchestrator 题面写错的地方

**承重级题面错：0 处，⛔ 未触发停下上报。** 派工单 §六自认可能错的五处，逐条给结果：

1. **§六#1「行号我一个都没自己核过」—— 我全核了，一个不差。**
   `pipeline.py:1368`（`compute_reading_report_from_vector_dir`）· `:1376-1379`（`load_reading_view` 列表推导）·
   `:1411`（`build_observation_reference_catalog_from_run`）· `:1414`（`run_correction`）·
   `reading/legacy.py:108`（`_is_legacy` 里 `view.get("facade_axis_note")` 那行）·
   `pipeline.py:731-732`（"`_write_vector_contract_ledger` never raises" 注释）·
   另外我自己定位的 `vector_contract.py:117`（frozenset 判成员 = `TypeError` 抛点）。
   §〇 的环境读数（HEAD / 447 行 / 4 份 untracked / 基线 3070）也全部对上。
   **三条阻断在 `f2a8ccf` 上全部复现得出**（11/11 探针绿）⇒ ⛔ 没有触发 §五 1(a)。

2. **§六#2「病根句可能仍不完整」—— 自认属实，我给一条更全的。**
   现句：「F-c 的『失败必留账』要在**所有**会碰 `0_reading` 的入口、与**所有**输入形态下成立。」
   实测两处它没盖住：
   - **`:1411` 那格根本没有「有问题的输入」** —— 一份完全正常的 `0_reading` 在 v3 profile 下失败，也一行账没有。
     ⇒ 还有第三个轴：**那次 run 最终因为什么原因失败**。
   - **账本自身写盘失败**会把 F-b 的点名失败一起吃掉 ⇒ 还有第四个轴：**F-c 的存储失败不得吃掉 F-b**。

   建议写法：
   > **F-b 的点名与 F-c 的留账，要在所有会碰 `0_reading` 的入口上、对所有输入形态、
   > 不论那次 run 最终因什么原因失败、且在账本自己写不进去的时候，都各自独立成立。**

   ⚠️ 同时这句话里的「所有入口」按字面读会把 `validation_run.py:281` 也包进来（§六#8），
   而它不在 1_correction 的消费链上 —— **口径请复核方裁定**。

3. **§四「不要动 `src/agent/pipeline` 以外的模块」与 §二的返工要求字面冲突**（外围事实，按 §五(b) 记下继续）：
   BLK-A / BLK-C 的逐字要求全部落在 `src/agent/reading/vector_contract.py`，那不在 `src/agent/pipeline` 里。
   我按「只碰 F-97 这几个模块、别游荡」理解，实际只动 3 个文件。

4. **§六#3「③ 的『自己造』方向是随手写的提示、不保证最有产出」—— 属实，我换了方向。**
   方向本身写在 §二的三个「我按什么方向找的」段里。照抄清单会漏掉的至少有三样：
   **fifo 挂死**、**`RecursionError`**、**v3 catalog 无毒文件也无账**。

5. **§六#4「N-A…N-E 会不会其实是同一个根」—— 不是同一个根，但 N-A 与我的改动有耦合，读数见 §二末。**
   结论：N-A 仍在，**但唯一会产生「静默消费」的漂移方向已被后置规则堵死**。⛔ 本轮未做 N-A 本身。

6. **§六#5「§〇 读数是发单前最后一刻重跑的」—— 我实测与 §〇 完全一致**（4 份 untracked / 447 行）。

7. **⚠️ 环境观察（不是题面错，但请 orchestrator 看一眼）**：
   `/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth` 的内容现在是
   **`/tmp/ep_f97`**（mtime `Aug 26 11:52`），**不是主树**。
   ⇒ 「裸跑脚本会静默串到主树」这条纪律**当前方向是反的**：
   在这个 worktree 里裸跑是安全的（cwd 优先），**在主树里裸跑才会串到 `/tmp/ep_f97`**。
   ⛔ 我**没有改动它**。

---

## 八、交件时的工作树状态

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework2_dispatch.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md

(= orchestrator 留的 4 份 md；本报告与源码/测试均已提交)
```

- 提交：`8f9728f`（主修）· `f30f89e`（4 把假锁返工）· ``41a568a``（最后 1 把假锁）· 本报告
- 探针与方法留存**在仓库外**：
  - `scratchpad/f97probe/test_grid1_repro.py` —— 判据①②，11 条断言缺陷存在的探针
  - `scratchpad/f97probe/explore.py` / `explore_b.py` / `explore_c.py` / `fifo.py` / `na_drift.py` / `why_green.py` —— 判据③
  - `scratchpad/neuter/apply.py` —— 9 个变异锚点（含 `assert s.count(old) == 1` 生效断言）+ 逐次 log
- ⛔ 4 份 orchestrator 的 untracked md 未删未提交。
