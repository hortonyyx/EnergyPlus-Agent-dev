# T4-a 返工 1 执行档（GLM 施工席）

- 日期：2026-09-04 · 派工单：[`2026-09-04o_T4a_rework1.md`](../request/2026-09-04o_T4a_rework1.md) · 上一轮裁决：[`2026-09-04h`](../verdict/2026-09-04h_T4a_v2_crossreview_gpt.md)
- 工作目录：`/tmp/t4a_rework_glm` · 分支 `wt/09.04o_t4a_rework` · 基点 `a91a1524`
- 本轮提交（4 笔，逐小步）：
  - `544ffecb` R3 恒真断言
  - `0de00a4f` R1+R2 解析 seam + 牙 + 拆借壳（生产）
  - `22f5ea5f` R1 锁测试（电池 + identity 钉 + 6 演示）
  - `82987887` R4 交件档更正

---

## 〇、开工自检（命令原文 + 输出原文）

```bash
cd /tmp/t4a_rework_glm && pwd && git log --oneline -1 && git status --porcelain
```

```text
/tmp/t4a_rework_glm
a91a1524 T4-a v2 execution report: obligation field shipped, 3781 = 3778 + 3
A  AI_agent/logs/reviews/request/2026-09-04o_T4a_rework1.md
A  AI_agent/logs/reviews/verdict/2026-09-04h_T4a_v2_crossreview_gpt.md
```

⚠️ 运维披露：两份预置 staged 文档（派工单 + 裁决档）随第一笔提交 `544ffecb` 入库——它们是本轮材料、属本分支历史，但严格说那笔提交不该捎带；已在此登记，后续未再发生（其余三笔均逐路径 add、提交前核过 `--cached --numstat`）。

## 一、§三 六条逐条对账

### #1 ⭐⭐⭐ 「债→行 的解析被扩成一对多」这个方向有锁 —— ✅

锁 = **`tests/test_t4a_rework1_resolution_lock.py`（28 项）**，三层互证：

| 层 | 形态 | 内容 |
|---|---|---|
| **电池**（行为锁） | `test_near_miss_obligations_are_refused_on_every_entry`（**19 项参数化**） | 从**活键集生成**近错族（大小写 / 空白 / 前缀切位 / 后缀 / 分隔符变形），每个经 `model_construct` 绕过 schema（扩法作用的真实运行面），断言在**三个入口**（seam / `assert_obligations_backed` / `redeemable_debt_ids`）全部响亮 `OBLIGATION_UNBACKED` |
| **identity 钉** | `test_every_live_key_resolves_to_exactly_its_own_row` + `test_retirement_never_follows_a_row_the_registry_does_not_hold` | 每个活键解析结果**恰好是** `(键, registry[键])`；销账永不跟随注册表不持有的行 |
| **生产牙**（结构锁，R1 生产侧） | seam 三牙 + import 两牙 | 载体钉 `type() is dict`（`DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT`）、键型钉 `type(key) is str`（`DEBT_REGISTRY_KEY_NOT_PLAIN_STR`）、claimant 计数牙（`DEBT_TYPE_AMBIGUOUS`，债侧） |

**扩法演示（验收 #1 的「造出那种扩法 ⇒ 锁必须红」，全部进程内安装、`finally` 恢复、恢复后自证）**：

| 演示 | 扩法 | 谁红 | 实测 |
|---|---|---|---|
| M1 归一化 | seam 包一层 strip+casefold 重试 | **电池**：同一探针函数 `_refusal_gone` 从拒翻成收 ⇒ 电池必红 | `_refusal_gone("  "+K.upper()+"  ") == True`（健康态为 False） |
| M2 兼容旧名 | compat 表 `{'K_legacy': K}` | **电池**：`K_legacy` 探针停止被拒 | 同上 |
| M3 一对多 resolver | 收集前缀命中、排序、**静默选一个**（旧 debt_id 前缀世界的失败形状在 obligation 上还魂） | **电池**：截断探针 `"elevation_chain_spans"` 停止被拒 | 同上 |
| M4 别名（松等键） | 不碰 seam：`str` 子类键、loose `__eq__` 一行认多名 | **生产牙**：seam/销账 `DEBT_TYPE_AMBIGUOUS` + import `DEBT_REGISTRY_KEY_NOT_PLAIN_STR` | 三处全部实测触发 |
| M5 载体 swap | 不碰 seam 不碰键：`dict` 子类 `__getitem__` 别名回退（**过 `isinstance`**） | **生产牙**：`DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT`，三入口全拒 | 实测触发；`isinstance(carrier, dict) == True` 亦在测试里印出（牙用 `type() is dict` 的原因） |
| M6 精确键重定向 | 只收精确键但指向别的行 | **identity 钉**（电池红不了——诚实边界）：钉的断言在变异下 `AssertionError`；销账 binding 同时保持债务 open | 实测触发 |

### #2 ⛔ 没有为了让锁能红而把缺陷造回去 —— ✅

- 精确键 + 闭枚举 + 单值查找**原样保留**：seam 内部就是 `obligation in DEBT_REDEMPTION_REGISTRY` + `DEBT_REDEMPTION_REGISTRY[obligation]`（`opening_synthesis.py:481-551`）；`DebtObligationV1` 与 `evidence_contract.py` **零改动**（`git diff a91a1524..HEAD --stat`：只动 `opening_synthesis.py` + 两个测试文件）；10 个 mint 点未动（`evidence_adapters.py` 不在 diff 里）。
- 演示里的扩法全部**进程内安装、`finally` 恢复**，每个演示末尾重跑健康断言；生产代码不含任何别名/归一/兼容表/多候选路径。
- B4 源绑定零变动（同口径三点对照，`binds` 块与销账 guard 块 SHA-256 在 `e5b0d7d5` / `a91a1524` / `HEAD` 逐位同一）：

```text
BASE binds 1ebb01cd6362097e   V2 binds 1ebb01cd6362097e   HEAD binds 1ebb01cd6362097e
BASE guard e21e1d5179d1e872   V2 guard e21e1d5179d1e872   HEAD guard e21e1d5179d1e872
```

（guard 块取法与裁决档证据 E 完全一致，哈希值可直接对上裁决档原文。）

### #3 两个错误码不再指同一件事 —— ✅

| 码 | 管哪个方向 | 现在在哪 |
|---|---|---|
| `DEBT_REGISTRY_PREMISE_AMBIGUOUS`（import）+ `PREMISE_GATE_AMBIGUOUS`（runtime） | **premise → 注册行** 的唯一性（执行侧按 premise 查行） | 原位未动（`_assert_registry_well_formed` / `redemption_row_for_premise`） |
| `OBLIGATION_UNBACKED` | 债的义务无行 = 空头承诺 | seam 内（`:527`），三个入口继承 |
| `DEBT_TYPE_AMBIGUOUS` | **债 → 注册行/处理器** 的唯一性（**回到债侧**，旧 debt_id 前缀世界同名牙的方向） | **只**在 seam（`:536`）：claimant 计数 ≠ 恰一 plain-str 键即红；`redeemable_debt_ids` 里的 premise 借壳块**已删除** |

改写后的 `tests/test_b4_opening_synthesis.py:878-912` 在**同一张变异表**（两行共享一 premise）上钉死分账：import 牙红 `DEBT_REGISTRY_PREMISE_AMBIGUOUS`、真执行入口红 `PREMISE_GATE_AMBIGUOUS`、债侧销账**不**红 `DEBT_TYPE_AMBIGUOUS`（按精确键正常销账）。

### #4 上一轮六条通过项不退化 —— ✅

| v2 通过项 | 凭证 |
|---|---|
| 闭枚举 | `evidence_contract.py` 零改动；`test_o22m2_evidence_contract.py:2143` 原样绿（全量内） |
| 接线不靠前缀（两方向） | `test_b4_opening_synthesis.py:1120` 原样绿；AST 复扫：全 `src/` 33 个 `startswith`，**债 receiver = 0**（与裁决档证据 C 同数） |
| 无处理器响亮 | `test_b4_opening_synthesis.py:1179` `test_unbacked_obligation_fails_loudly` 三入口全绿（现在三入口都过 seam，牙更集中） |
| 没碰源绑定 | 见 #2 的三点哈希对照 |
| 枚举面 = 今天需要的 | mint 点盘点未变（`evidence_adapters.py` 不在 diff 内；裁决档证据 F 的 10 点仍成立） |
| B4 三道牙仍有牙 | `test_registry_rows_are_wiring_not_decoration`（`:723`）逐道重造触发全绿：HANDLER_MISSING（`:795`）、PREFIX_AMBIGUOUS（`:874`）、TYPE_AMBIGUOUS 的牙**搬到债侧**后由 M4 演示承载（方向修正是本轮 R2 的内容本身，不是退化） |

### #5 零恒真断言 —— ✅

改前（`tests/test_b4_opening_synthesis.py:1131`）：

```python
assert "debt_" not in renamed.debt_id[:2] or True  # renamed, not prefixed
```

改后：

```python
assert not renamed.debt_id.startswith("debt_")  # renamed, not prefixed
```

改前恒真（5 字符子串进不了 2 字符切片，再 `or True` 双保险）；改后有牙（夹具若回退成 `debt_` 前缀 id 即红）。**同型自查**：v2 本轮加的全部断言（`test_b4_opening_synthesis.py` 两条 + `test_o22m2_evidence_contract.py:2143` 一条）逐条过了一遍，`or True` / `and False` / 恒真比较**仅此一处**；新增锁文件内的断言全部带可失败条件（M1–M3/M6 的 `_refusal_gone` 断言本身就是「断言扩法下锁会红」的反向牙）。

### #6 全量绿 · 逐位闭合 —— ✅

命令 = 派工单 §三 原文（环境自证与 pytest 同一条）：

```bash
cd /tmp/t4a_rework_glm && \
python -c "import src.agent.correction.evidence_contract as c, src.agent.correction.opening_synthesis as o; print(c.__file__); print(o.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

输出原文（首两行 + summary；exit 0，summary 行存在）：

```text
/tmp/t4a_rework_glm/src/agent/correction/evidence_contract.py
/tmp/t4a_rework_glm/src/agent/correction/opening_synthesis.py
3809 passed, 2 skipped, 13 xfailed, 211 warnings in 488.66s (0:08:08)
```

闭合：**`3809 = 3781 + 28`**（基线 `a91a1524` = 裁决档独立复现过的 `3781 passed / 2 skipped / 13 xfailed`）；28 = 新文件收集数（实测 `28 tests collected`）= 19（电池参数化）+ 9（非参数化）；`2 skipped / 13 xfailed` 逐位不变。机械核（同裁决档方法）：

```text
git diff --unified=0 a91a1524..HEAD -- tests | grep -E '^\+def test_|^-def test_'
→ +10 个 def（全部在新文件），-0 个 def
```

## 二、⭐ R1 正面论证：这把锁在「有人扩成一对多」的方向**为什么会红**

**方向定义**（裁决档 §三原文）：「将来若有人重新引入 obligation 别名 / 大小写归一 / 兼容旧名 / 一对多 resolver，使一张债可能得到**多个候选行**」。

**为什么必然红**——按扩法的**存在目的**论证，不按点名名单：

1. **凡扩法，必改变「可解析集 = 精确键集」这个签名性质。** 别名/归一/兼容表/多候选 resolver 之所以值得写，就是为了让某个**非精确键**的 obligation 也能解析到行（否则它是死代码）。而电池锁的恰是这个签名性质：**每个从活键集生成的近错探针必须被响亮拒绝**。M1/M2/M3 是实测证据：装上扩法的瞬间，电池**自己的探针函数**（与绿路径同一函数，不是复制品）从「拒」翻「收」——电池在该方向红是构造性的，不是概率性的。
2. **扩法若不放宽可解析集（只重定向精确键），identity 钉红。** M6 实测：电池对它不红（诚实边界），但 `seam(k) == (k, registry[k])` 的钉在变异下当场 `AssertionError`；且销账 binding（`row is not executed.row` → 保持 open）保证重定向期间也没有错误销账。
3. **扩法若不碰 seam 代码（换载体 / 换键型），生产类型牙红。** 一张精确键的债要得到多候选，只剩两条不碰 seam 的路：载体换成多值映射（`type() is dict` 拒，M5 实测含 `isinstance` 伪装）、键换成松等 `str` 子类（claimant 计数牙 + import 键型钉拒，M4 实测三处触发）。**这正是「让那条路在类型层不存在」**：只要载体是 plain dict、键是 plain str，多候选状态在该结构下不可表示。
4. **对「换写法绕过」的回答**（派工单 R1 提示的 ⚠️）：主牙是**行为锁**（探针走真实入口观测可解析集），没有任何词法面可绕——不存在「换个写法就不匹配」的字符串模式。唯一「绕过」= 删锁本身，而这对任何锁都成立，不在锁的威胁模型内。
5. **边界（诚实声明）**：如果扩法被写成**永不产生任何可观测效果**的死代码（既不放宽可解析集、不重定向、不动载体与键型），行为锁看不到它——但那一刻也没有任何债能得到多个候选行（该状态仍不可表示），与裁决档「不是缺陷挡锁，是违规态在当前类型下不可表示」同一边界。扩法一旦产生可观测效果（这是它存在的意义），上面 1–3 之一必红。

**「今天不可表示所以不用锁」为什么不是本锁的形态**：本锁不试图在今天喂进一张多候选债（裁决档已证不可构造）；锁的是**表示层本身**（载体类型 / 键型 / 可解析集 / 解析恒等），扩法必须先改表示层才能让违规态可表示，而表示层的每一面都被钉住。

## 三、§五 登记（⛔ 本轮不做）

- **N-1**（`OBLIGATION_UNBACKED` 今天零未来值存货，域只有一个值 ⇒ mutation-only 冗余 fail-fast）：**登记**。与 M5/M4 依赖的运行时牙同族；待第二个枚举值出现时一并重估。
- **N-2**（`DEBT_REGISTRY_PREFIX_AMBIGUOUS` 在精确键下已成语义遗留牙，限制未来合法命名多过保护接线）：**登记**。本轮**未拆未改**（`test_b4:874` 触发原样保留）；按派工单要求，等 R1 落地后由派工方一并重估——R1 现已落地，N-2 的重估请求随本档交回。

## 四、最薄弱一处

**电池的近错族是规则生成的、但仍是有限族**：M1–M3 证明的是「电池生成的每个变形族里锁有牙」，而一个**接受完全不在这些族里的字符串**的别名（例如 compat 表写 `{'span_gate': row}`）不会让电池红。它今天不构成实害的原因是闭环的另一端——`DebtObligationV1` 闭枚举使任何真实 mint 的债**带不上**这种串（只有 `model_construct` 绕过能造出来，而绕过债又过不了销账 binding 的 `key != executed.obligation`，最多被静默保持 open）。也就是说这一面的防线是**枚举 schema + 销账 binding**，不是电池本身；若将来有人既加任意串别名、又扩枚举域收容它，防线上限就落在 identity 钉与 import 域牙上。这是我认为复核方最可能挑战、且我只能以「闭环多层」而非「单锁完备」来辩护的位置。
