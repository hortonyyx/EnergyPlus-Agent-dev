# 执行档 · 模块 2 第三方向：通道声明 `absent`，包里却带着这条通道的载荷

- **日期**：2026-09-01 · **施工方**：Claude 家族施工席 · **审**：跨家族（GPT 或 GLM）
- **派工单**：`../request/2026-09-01_o22m2_absent_with_payload_dispatch.md`（含 2026-09-01 排工补丁）
- **起飞基线**：`a6990be`（`git log --oneline -1`），工作树在我起飞时干净
- **写面**：`src/agent/correction/evidence_contract.py`（+187/−50）·
  `tests/test_o22m2_evidence_contract.py`（+324/−0）· 本执行档
- ⛔ **未 `git add` / 未 `commit`**，交主控。

---

## ⚠️ 先说三件必须让复核方知道的事

### (1) 我**没有**复用孤儿 diff 的任何一段（交件项 ④）

`AI_agent/logs/experiments/2026-09-01_glm_quota_orphan_o22m2_absent/orphan.diff` 我**读了 README，
⛔ 没有打开 `orphan.diff` 的内容**，全部从头实现。故本档**没有「复用论证」一节** —— 不是漏写，是不存在。
（README 已写死「线索非证据」，而我不需要线索：派工单 §二 已经给出方向，且我下面走的是一条它没点名的第三条路。）

### (2) 中途撞到一条**不属于我写面**的红，已按纪律隔离并证明与我无关

- 时间点：我第一次跑 `m2+m3+m4` 三件套时。
- 红：`tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open`
- 处置：先 `git status --porcelain` ⇒ 当时 `wall_compiler.py` 与 `test_o22m4_wall_compiler.py`
  **都被 GLM 席改着**（模块 4 第二轮返工在飞）。
- **归属证明**（⛔ 不是推测）：把**我自己那一个文件**还原到 HEAD（`git checkout -- src/agent/correction/evidence_contract.py`，
  ⛔ 没有用 `git checkout -- .`）后**同一条测试仍然红、错误逐字相同** ⇒ 与我的改动无关。
  随后把我的版本从 scratchpad 拷回。
  ```
  $ git checkout -- src/agent/correction/evidence_contract.py && git status --porcelain
   M src/agent/correction/wall_compiler.py
   M tests/test_o22m4_wall_compiler.py
  $ python -m pytest -n 6 -q tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
  E       AssertionError: the axis item vanished from open_items -- a silent auto-execute path closed it (F-1's mutation does exactly this)
  E       assert 0 == 1
  FAILED tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
  1 failed in 5.70s
  ```
- **后来它自己好了**：GLM 席继续落件后，同一条测试在我这里连跑两次全绿（见验收 7）。
  ⇒ 这是**在飞席位的中间态**，⛔ 我没有碰它、⛔ 没有把它记成回归。
- ⚠️ **本档的验收 7 读数因此是「跨席位窗口内」的读数**，权威全量仍归主控。

### (3) ⭐⭐⭐ 我做了一个**承重的语义判断**，请复核方**优先攻它**

派工单 §二 推荐的字面配方是「通道 → 载荷成员映射，非空 ⇔ present、空 ⇔ absent」。
**照字面做会当场违反禁令 1 + 禁令 2 + 验收 7**，因为：

> `tests/test_o22m4_wall_compiler.py::test_unselected_dangling_candidate_is_caught_by_compiler_walk`
> 里的 `_hand_built_artifact` 造的包是 **walls=`absent` + 0 条 wall claim + 3 条 `non_wall` disposition**，
> 并且写着 `validate_evidence_bundle(art)  # premise: module 2's layer passes it`。
> 同形状也是**模块 3 已收口的 adapter 的真实输出**（`evidence_adapters.py`：`if claims:` present `else:` absent，
> 而 disposition 台账照样是满的）。

⇒ **我的判断**：`face_dispositions` 是**源产物的面线台账**（不变量 2 强制「每条 as-drawn 面线恰好一条」，
**与 walls 腿产没产出无关**），只有 **`claimed_wall`** 那一行才是 walls 通道在说话。
一份「每条面线都是 non_wall」的产物 = **诚实的 walls-absent 跑 + 满台账**。

⇒ 所以「谁算载荷」被我写成**显式的、逐成员的判据**（`_payload_row_witnesses`），
⛔ 不是「成员列表非空」。这句判断**写进了模块 docstring 供攻击**。
**若复核方判我这句错**，那么正解就是**停下上报**（因为那时任务项与禁令 1/2 真的自相矛盾），⛔ 不是我改 m3/m4。

---

## 一、承重前提复现（派工单 §一，⛔ 我自己跑的，不是转引）

自检三条：

```
$ git log --oneline -1
a6990be 09.01q_M4Rework2Dispatch_FixtureMustBuildTheTargetQuantityItself
$ git status --porcelain          # (起飞时)
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  ...
```

在**未改动的树**上，用测试自己的 `_tiny_artifact()`：

```
BASELINE wall_claims=2 face_dispositions=4 opening_claims=1
channel_status = [('dimensions', 'absent'), ('elevation_openings', 'absent'),
                  ('plan_openings', 'present'), ('room_roles', 'absent'), ('walls', 'present')]
BASELINE validate: PASS
walls         -> absent+missing_channel debt; payload wall/disp/open=(2, 4, 1): PASS (let through)
plan_openings -> absent+missing_channel debt; payload wall/disp/open=(2, 4, 1): PASS (let through)
```

⇒ **§一 的两条读数逐字对上**（2 / 4 / 1，五行 channel_status 逐行相同，两个反例都放行）。

---

## 二、改了什么

### 2.1 `src/agent/correction/evidence_contract.py`

| 新增/改写 | 是什么 |
|---|---|
| `CHANNEL_PAYLOAD_MEMBERS`（新，已进 `__all__`） | ⭐ **一张显式表**：`walls -> (wall_claims, face_dispositions)`、`plan_openings -> (opening_claims,)`。取代原来的 `_CHANNELS_WITH_PAYLOAD_MEMBERS` 常量（**已删除，全仓零引用**） |
| `_channel_payload_rows(bundle, channel)`（新） | 该通道**每一行**载荷（含台账全部行）—— B-1 源闭合的射程，**与今天逐字等价** |
| `_payload_row_witnesses(member, row)`（新） | ⭐ **哪一行才算「这条通道产出了」**：`face_dispositions` 只有 `claimed_wall` 算，其余成员每行都算 |
| `_channel_witness_rows` / `_channel_has_payload`（改写） | 由上面两个派生，⛔ 不再是手写的 `if channel == "walls"` 分支 |
| `_assert_channel_payload_closure`（**改写为双向对账**） | ⭐⭐⭐ 见下 |
| `_payload_row_source_ids`（新） | 逐成员的「身份住哪」规则；**未登记的成员 ⇒ `PAYLOAD_MEMBER_WITHOUT_SOURCE_RULE` 响亮**，⛔ 不是静默空集 |
| `_channel_payload_source_ids`（改写） | 改成由表 + 上一条派生；**行为与今天等价**（射程仍是全部台账行） |
| `_assert_channel_source_closure` | **只把常量名换掉**，逻辑一行未动 |

⭐ **函数名 `_assert_channel_payload_closure` / `_assert_channel_source_closure` 与签名【故意保持不变】** ——
既有 F-1 / B-2 / B-1 三条锁是**按名字 monkeypatch 摘除**它们的（`lambda b: None` / `lambda b, f: None`），
改名会让既有锁假绿/假红。⛔ 这不是迁就，这是不许动既有断言的直接后果。

**新的对账逻辑（⛔ 不是镜像分支）**：

```python
    rows_by_channel = {s.channel: s for s in bundle.channel_status}
    for channel in CHANNELS:                       # ← 走【通道域】，不是走声明行
        status = rows_by_channel.get(channel)
        witnesses = _channel_witness_rows(bundle, channel)   # ← 不分 state，先量
        if status is None:
            raise ... "CHANNEL_STATUS_MISSING"
        if witnesses:
            if status.state != "present":
                raise ... "CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD"
            continue
        if status.state == "present" and channel not in zero_payload:
            raise ... "PRESENT_CHANNEL_WITHOUT_PAYLOAD"
```

⇒ **整个函数体里没有任何一处 `if status.state != "present": continue`**（那正是前两轮共同的开头）。
`state` 变成**被推导出来的对账结果**。

**本轮一共钉住三个载体**（⭐ 派工单只点名了第一个）：

| # | 载体 | 换掉它会发生什么 | 锁 |
|---|---|---|---|
| 1 | `state` 的**取值** | 声明 absent、载荷照走 | `CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD` |
| 2 | ⭐ `state` 那一**行的存在** | 干脆不声明这条通道 ⇒ 若循环走声明行，**同一批载荷照样出去** | `CHANNEL_STATUS_MISSING` |
| 3 | ⭐ **哪些行算载荷** | 只认 `wall_claims` ⇒ legacy 源上「0 claim + 1 条 `claimed_wall` 台账行」可声明 absent | `_payload_row_witnesses` + 上面那条码 |

**新错误码 3 个**：`CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD` · `CHANNEL_STATUS_MISSING` ·
`PAYLOAD_MEMBER_WITHOUT_SOURCE_RULE`。既有码一个没改名、没删。

### 2.2 ⚠️ 一处**行为收紧**，必须点名（复核方请判它可不可接受）

`_channel_has_payload` 从「`wall_claims` **或** `face_dispositions` 非空」收紧为「witness 行非空」。
⇒ **walls=`present` + 0 条 claim + 只有 `non_wall` 台账行**，今天放行、改后 `PRESENT_CHANNEL_WITHOUT_PAYLOAD`。
- **方向**：这与 F-1 立门时的意图**同向**（它要杀的就是「walls 说 wired 其实什么都没产」）。
- **实测无人踩**：全部夹具与模块 3 adapter 都不产这个形状（下表是我量的，⛔ 不是推断）：

```
m2/_built sm25_1f_v2.json  walls=present  claims= 22 disp= 49 claimed_wall= 44 openings_n= 85 rows=5
m2/_built sm25_2f_v2.json  walls=present  claims= 22 disp= 46 claimed_wall= 43 openings_n= 87 rows=5
m2/_built sm24_1f_v2.json  walls=present  claims= 12 disp= 98 claimed_wall= 20 openings_n= 87 rows=5
m2/_tiny                   walls=present  claims=  2 disp=  4 claimed_wall=  3 openings_n=  1 rows=5
m2/_legacy                 walls=present  claims=  1 disp=  0 claimed_wall=  0 openings_n=  0 rows=5
m2/_empty                  walls=present  claims=  0 disp=  0 claimed_wall=  0 openings_n=  0 rows=5
```
（`rows=5` 那一列同时是 `CHANNEL_STATUS_MISSING` 不会误杀任何既有夹具的实测依据。）

### 2.3 `tests/test_o22m2_evidence_contract.py`：新增 7 条锁（33 → 40）

| 锁 | 管什么 |
|---|---|
| `test_r3_absent_channel_may_not_carry_its_payload` | §一 两个反例，**先绿后红自证** |
| `test_r3_honest_absent_channels_are_not_killed` | 反方向不误杀（三条无载荷通道 + walls 真空跑 + ⭐ **满台账零 claim**） |
| `test_r3_zero_payload_channel_exit_survives` | 合法出口 `present + zero_payload_channel(walls)` |
| `test_r3_a_deleted_channel_row_is_not_a_third_state` | ⭐ 同形输入 #1：删掉声明行 |
| `test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload` | ⭐ 同形输入 #2：legacy 源上台账行独自当载荷 |
| `test_r3_every_payload_bearing_bundle_field_is_declared` | 表 vs 包类型的**对账门**（新字段没登记即红） |
| `test_r3_a_mapped_member_without_a_source_rule_is_loud` | 扩表没教身份规则即红 |

⭐ **每条锁的夹具都【自证目标量】**（今天下午那条纪律）：断言行为**之前**先分别断言
①「这一行真的写着 absent / 这一行真的不存在」②「包里真的还有 N 条这条通道的正向载荷」，
且 **② 是测试文件自己算的**（`_measured_walls_payload` / `_measured_openings_payload`），
⛔ **没有反过来问被测模块「你觉得有没有载荷」**。
错误码的 `payload_row_count` 也被拿去和这个独立读数比，所以计数是承重的、不是装饰。

⭐ **绿锚锚在本锁自己那一段**：三条正向锁除了整体 `validate_evidence_bundle(...)`，
还**单独直调 `evidence_contract._assert_channel_payload_closure(bundle)`** ——
⛔ 没有 `assert <整份审计通过>` 当唯一绿锚。

⭐ **判据写成规则不写成现状名单**：`test_r3_every_payload_bearing_bundle_field_is_declared` 的规则是
「包上**每个 list 字段**要么映射到某条通道、要么在 `not_payload` 里带理由登记」——
⛔ 不是「今天这三个字段必须叫这三个名字」。

---

## 三、逐条验收读数（⛔ 全是实测输出原文）

### 验收 1 — §一 两个反例从放行变响亮，且先绿后红自证 ✅

改动前（§一 复现，见上）：两条都 `PASS (let through)`。改动后同一脚本：

```
walls         -> absent+missing_channel debt; payload wall/disp/open=(2, 4, 1): RAISED CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD
plan_openings -> absent+missing_channel debt; payload wall/disp/open=(2, 4, 1): RAISED CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD
```

锁内部的「先绿」= 把 `_assert_channel_payload_closure` monkeypatch 成 `lambda b: None` 后
`validate_evidence_bundle(art)` **不抛** ⇒ 洞是**在这棵树上复现的**，不是从派工单抄的。

### 验收 2 — 反方向不误杀 ✅

`test_r3_honest_absent_channels_are_not_killed` 绿。它覆盖：
`dimensions` / `room_roles` / `elevation_openings` 三条真空 absent · `_empty_artifact` 的 walls 真空跑 ·
⭐ **walls absent + 4 条满台账 0 条 claim**（模块 3 adapter / 模块 4 夹具的真实形状）。
⭐ 这条**不是恒绿**：变异 M3（见下）让它变红。

### 验收 3 — 合法出口保留 ✅

`test_r3_zero_payload_channel_exit_survives` 绿；既有 `test_b2_...` 里那半也照旧绿。

### 验收 4 — neuter 对撞：**16 → 20**，原 16 条逐条原样 ✅

方法：一个 pytest 插件在 `pytest_configure`（早于测试模块 import）把
`evidence_contract.validate_evidence_bundle` 换成 `lambda a: None`。

```
=== BEFORE count: 16  AFTER count: 20 ===
--- diff (before -> after) ---
16a17,20
> test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload
> test_r3_a_deleted_channel_row_is_not_a_third_state
> test_r3_a_mapped_member_without_a_source_rule_is_loud
> test_r3_absent_channel_may_not_carry_its_payload
```

⇒ **原 16 条一条不多一条不少、逐条原样**（`diff` 只有 append，没有任何 `<` 行）。
⭐ **BEFORE 的 16 是我在 HEAD 版文件上现跑的**，⛔ 不是引用派工单的数。
⭐ 另外 3 条新锁在 neuter 下**仍绿是对的** —— 它们是正向/对账锁，本来就不靠 `validate_...` 抛错。

### 验收 5 — 换同形输入自证（⛔ 非 §一 那两个）✅ **两种**

- **#1 删掉声明行**：把 `walls` 那一行从 `channel_status` 里删掉，载荷原样不动。
  改动前：`validate_evidence_bundle` 放行（锁里的 BEFORE 分支实测）。改动后：`CHANNEL_STATUS_MISSING`。
  ⭐ 这条是**载体从「`state` 的值」换成「`state` 这一行的存在」** —— 只做验收 1 会漏掉它。
- **#2 legacy 源上，0 条 claim + 1 条 `claimed_wall` 台账行 + walls 声明 absent**。
  改动前放行（as-drawn 的 claim↔disposition 闭合对 legacy 源看不见它）。改动后
  `CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD`，且 `context["payload_rows"] == ["face_dispositions"]`。
  ⭐ 这条是**载体换成「哪些行算载荷」**。

### 验收 6 — `content_sha256` 未变 ✅（改动前 / 改动后逐份贴出）

```
                     BEFORE (HEAD)                                                    AFTER (my tree)
sm25_1f_v2.json      baee53ae35a6f7004530ad0a1bf3850f96ae846f1cdcc5ddb5a721306cf3d173  (同)
sm25_2f_v2.json      7947fa0ce6efce588836e00a287d6523085ae8259b9457ec27e9ce66d786510a  (同)
sm24_1f_v2.json      3b109fa03749910fc2bffc6e381a29e8e5a03e97ce362bea9ec60a0e5ee08c43  (同)
tiny                 dbecb4fc2eb11a9dd1112250dca2ee05214b8bb2b9c2f8cf441a48d27e57f8c6  (同)
legacy               d4cc07e46c13f63a044c21c2b085b57c7bb815b371400c16be9872dff852c161  (同)
empty                02935b9566f01c7cb6b2d46396569a60f47b4022a4ccd1de26c9a4d1d519ab9b  (同)
```

**机制上也必然不变**：改动只在**校验器**里，`CorrectionEvidenceBundleV1` 的字段、`_sorted_bundle`、
`finalize_bundle` 一个字符没动；新表是**模块常量**，⛔ 不进包、⛔ 不进 `canonical_bytes`。

### 验收 7 — 三个模块测试全绿 ✅（⛔ `-n 6`，不是 `-n 4`，按排工补丁并发条款）

```
$ python -m pytest -n 6 -q -p no:cacheprovider tests/test_o22m2_evidence_contract.py \
      tests/test_o22m3_evidence_adapters.py tests/test_o22m4_wall_compiler.py
--- run 1 ---
91 passed in 11.33s
--- run 2 ---
91 passed in 10.97s
```

顺手把下游 m5/6 也跑了（它 import 本模块）：

```
$ python -m pytest -n 6 -q tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py \
      tests/test_o22m4_wall_compiler.py tests/test_o22m56_decision_loop.py
164 passed in 19.28s
```

`grep -rl evidence_contract tests/` 只有这 4 个文件 ⇒ **受影响子集已跑全**。
⛔ **没有跑全量**（另两席在写树）。

### 验收 8 — 改动路径全清单（⛔ 未提交）

```
$ git diff --numstat -- src/agent/correction/evidence_contract.py tests/test_o22m2_evidence_contract.py
187	50	src/agent/correction/evidence_contract.py
324	0	tests/test_o22m2_evidence_contract.py
```

加上本执行档 `AI_agent/logs/reviews/execution/2026-09-01e_o22m2_absent_execution.md`（新增）。
`git status --porcelain` 里另外两项（`tests/test_o22m4_wall_compiler.py`、
`AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/`）**是 GLM 席的，⛔ 我没碰**。

---

## 四、新锁的变异实测（交件项 ③）

方法：逐条把新门**声称保护的那句**删掉/反掉，跑 `tests/test_o22m2_evidence_contract.py`（40 条），
每次跑完自动还原。**每条变异都必须红，且红在该红的那条锁上。**

```
### M1 re-add the early-continue on a non-present state (the round-1/2 shape)
  summary: 2 failed, 38 passed in 7.15s
  RED: test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload
  RED: test_r3_absent_channel_may_not_carry_its_payload

### M2 walk the DECLARED ROWS instead of the channel domain
  summary: 1 failed, 39 passed in 7.38s
  RED: test_r3_a_deleted_channel_row_is_not_a_third_state

### M3 every payload row witnesses (drop the ledger distinction)
  summary: 2 failed, 38 passed in 9.78s
  RED: test_r3_absent_channel_may_not_carry_its_payload
  RED: test_r3_honest_absent_channels_are_not_killed

### M4 no ledger row ever witnesses (walls payload == wall_claims only)
  summary: 2 failed, 38 passed in 8.45s
  RED: test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload
  RED: test_r3_absent_channel_may_not_carry_its_payload

### M5 an unmapped payload member gets a silently empty source set
  summary: 1 failed, 39 passed in 8.68s
  RED: test_r3_a_mapped_member_without_a_source_rule_is_loud

### M6 drop face_dispositions from the walls row of the map
  summary: 3 failed, 37 passed in 7.23s
  RED: test_r3_a_claimed_wall_ledger_row_alone_is_walls_payload
  RED: test_r3_absent_channel_may_not_carry_its_payload
  RED: test_r3_every_payload_bearing_bundle_field_is_declared

[restored original]
```

⭐ **三条值得点名的读数**：
- **M1** = 把前两轮那句 `if state != "present": continue` 加回来 ⇒ 立刻红 ⇒ **本轮修的确实是那条缝**。
- **M3** 红的是「**不许误杀**」那条 ⇒ 反方向的绿**不是恒绿**（[[gate-with-only-negative-assertions-is-unobservable]] 的反面）。
- **M4** 同时红两条 ⇒ 「哪些行算载荷」这个判断是**双向承重**的：放松会误杀（M3），收紧会漏（M4）。
- **六次变异里，既有 33 条锁一条都没红** ⇒ 新门没有和既有断言纠缠。

---

## 五、哨兵两次读数（交件项 ⑤）

```
开工前：58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
交件前：58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
```
两次相同。⛔ 全程没有跑过 `pip install -e .` 或任何写 `site-packages` 的命令。

---

## 六、我认为派工单哪里写错了（交件项 ⑥）

1. ⭐⭐⭐ **§二 推荐方向的字面配方与禁令 1/2 打架**（详见开头第 (3) 条）。
   「非空 ⇔ present」里的「非空」若指**成员列表非空**，则 `walls=absent + 满 non_wall 台账`
   会被判红 —— 而那正是**模块 3 已收口 adapter 的真实输出**和**模块 4 现役夹具写着
   `# premise: module 2's layer passes it` 的那份**。
   ⇒ 这是**第 (n) 次「派工单里的一句分类语是可能错的前提」**：
   派工单把「载荷」当成了原子概念，而它其实要再切一刀（**台账行 ≠ 通道产出**）。
   我按语义切了，⛔ 没有停报 —— 因为切完之后任务项与禁令**不再**打架；
   但**这一刀是我签的字，不是派工方签的**，故列为第一薄弱处。
2. **§二 的 ⛔ 明确不许①「只加一个 `if state == "absent"` 镜像分支」说得对但不够** ——
   真正会被换的第二个载体是**声明行的存在**（删行 ≠ 改值），派工单没点名。
   我加了 `CHANNEL_STATUS_MISSING`，但它**严格说超出了单子字面范围**，请复核方判是否接受。
3. **交件文件名两处不一致**：派工单排工补丁写 `2026-09-01c_o22m2_absent_execution.md`，
   我收到的入口 prompt 写 `2026-09-01e_...`。我按 **prompt 的 `e`** 写（当天已有 c/d 序号在用）。**只记不停。**
4. **并发条款两处不一致**：排工补丁写「Claude 席 = F-156、GPT 席 = 复审模块 4」，
   入口 prompt 写「GLM 席 = 模块 4 返工、GPT 席 = 复核 F-156」。
   我实测到的是**入口 prompt 那版**（`wall_compiler.py` + m4 测试在被写）。**只记不停**，但下次派工请对齐。
5. **验收 7 写 `-n 4`，排工补丁写「一律 `-n 6`」** —— 自相矛盾。我按 `-n 6`。**只记不停。**

---

## 七、我自认最薄弱的一处 + 希望复核方重点打哪里（交件项 ⑦）

### ⭐⭐⭐ 最薄弱：`_payload_row_witnesses` 里那句「只有 `claimed_wall` 算 walls 载荷」

这是**全轮唯一一处「我说了算」的语义判断**，而且它**同时决定了门的两个方向**：
放松 ⇒ 误杀模块 3 的诚实输出（M3 实测）；收紧成「只认 `wall_claims`」⇒ 漏掉 legacy 台账行（M4 实测）。
我给的论据是「不变量 2 强制每条面线一条台账行 ⇒ 台账是**源产物**的函数，不是 walls 腿的函数」。

**请重点打**：
1. ⭐ **有没有第四种「谁算载荷」的行**我漏了？具体：`ambiguous` 状态的台账行 ——
   我判它**不算** walls 载荷（reading 诚实弃权，walls 腿没产出）。
   若判它算，`walls=absent + 全 ambiguous 台账` 就是一个我现在放行的洞。**我没造这个夹具，这是缺口。**
2. ⭐⭐ **`_assert_channel_source_closure` 我一行逻辑都没动**，它仍以 `if status.state != "present": continue` 开头。
   我的论证是：absent 通道现在保证没有 witness 行，所以载荷出不去。
   **但 absent 通道仍可以带非 witness 行（`non_wall` 台账行）来自未声明源，而那条路仍然被 `continue` 跳过。**
   我**故意没堵**，因为堵了会当场红掉模块 4 那个夹具（`declared=()`，`payload={tiny}`）。
   ⇒ 请判：这是「不是我的载体、正确地留着」，还是**第四轮的入口**。
3. ⭐ **`covered_by_debt_ids` 与债的 `channel` 字段不对账**（既有缺口，⛔ 不是我引入的）：
   `walls` 的 absent 可以被 `dimensions` 的 `missing_channel` 债「覆盖」，校验器只查 debt_id 存不存在。
   我**没修**（不是我这一刀的载体，且怕碰既有绿）。**点名登记，请裁决要不要另立单。**
4. **`test_r3_every_payload_bearing_bundle_field_is_declared` 的 `not_payload` 名单**里有三个字段带理由。
   请判这三条理由站不站得住（尤其 `evidence_debts` —— 债本身算不算某条通道的「载荷」）。
5. `CHANNEL_PAYLOAD_MEMBERS` 我做成了**公开名**（进了 `__all__`）。若认为它该私有，说一声即可，⛔ 不承重。
