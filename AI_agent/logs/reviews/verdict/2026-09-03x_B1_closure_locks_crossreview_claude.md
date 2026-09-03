# 裁决 · **B1 收口补锁** 跨家族审

- **日期**：2026-09-03（第三程）· **复核方**：**Claude 家族（orchestrator 亲审）** · **施工方**：**GPT 家族**
- **合规**：谁写谁不批 ✅（GPT 施工 / Claude 审，跨家族）· 审恒升一档 ✅
- **任务书**：[`2026-09-03n`](../request/2026-09-03n_B1_closure_locks_dispatch.md)
- **审阅对象**：`965303b` · `743abb6` · `02e6367`（合并点 `4dbf1de`）
  净 diff = `src/agent/pipeline.py` 18/1 · `tests/test_b1_projection_bridge_production_loader.py` +117 · `tests/test_o22m7_evidence_wiring.py` 106/1
- **复核树**：`/tmp/b1_locks_review_claude` @ `431c44b`（⛔ 未动主树）
- **施工方自述**：[执行档](../execution/2026-09-03n_B1_closure_locks_execution.md) —— ⭐ **只当线索**，下列红绿**全部是我自己跑的**

---

# ⭐ 结论：**APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 3**

**四把新锁我逐把做了变异实测，全部有牙，恢复后树净。** T3 的做法尤其对（见 §三）。
三条 findings 都**不阻断合并**，但 **N-1 是真缺口**，且它的修法几乎免费。

---

## 一、我自己的实测（命令原文 + 输出原文）

### 基线（环境自证与 pytest 同一条命令）

```
$ cd /tmp/b1_locks_review_claude && python -c "import src.agent.pipeline as p, src.agent.correction.projection_bridge as b; print('PIPELINE',p.__file__); print('BRIDGE',b.__file__)" && python -m pytest -n0 -p no:cacheprovider -q <四个目标>
PIPELINE /tmp/b1_locks_review_claude/src/agent/pipeline.py
BRIDGE   /tmp/b1_locks_review_claude/src/agent/correction/projection_bridge.py
17 passed in 2.80s
```

### 四把锁的牙（⭐ 每次变异后都 `git checkout` 恢复并核 `git status --porcelain` 为空）

| 变异 | 摘掉什么 | 结果 |
|---|---|---|
| **M-T1** | 消费侧哈希绑定校验（`pipeline.py` 那段 `if envelope.source_resolved_sha256 != …`）| `FAILED …::test_switch_on_rejects_a_tampered_projection_binding` ✅ 红 |
| **M-T2** | 生产声明 `resolution_m=0.0` → `0.0218`（`pipeline.py:1241`）| `FAILED …::test_switch_on_returns_the_projected_geometry` ✅ 红 |
| **M-T3** | 宿主唯一性拒绝（`projection_bridge.py:681` 的 `if len(owners) != 1` → `if not owners: continue`）| **4 failed**，含**两把新锁** `test_mixed_thickness_opening_with_{no_owner,two_owners}_is_loud` ✅ 红 |
| **M-T4** | strict+degraded 那道门（`pipeline.py:1443-1456`）| `FAILED …::test_strict_profile_rejects_real_degraded_projection_before_judge` ✅ 红 |

**恢复后**：`git status --porcelain` 四次均为空。

---

## 二、逐条对派工单 §四 六条验收

| # | 规则 | 判 | 依据 |
|---|---|---|---|
| **1** | 每条新锁都有牙 | ✅ | §一 四条变异，**我自己跑的**，4/4 红、恢复后树净 |
| **2** | T3 的新锁在**真产物**上有没有存货，要说清 | ✅ **做得对** | 见 §三 |
| **3** | T4 已有明确归属 | ✅ | 判归 B1 并在 `run_correction` 返回 geometry 前强制，未走 A 层停报 —— ⚠️ 但见 **N-2** |
| **4** | B1 既有 24+12 条不退化 | ✅（**间接**）| 权威全量 `3717 passed / 0 failed` @ `861176e`，而 `4dbf1de` 是它的祖先，收工账「+6（B1 收口补锁）」逐位闭合。⛔ **我没有独立重数 24+12**，此条按全量兜底 |
| **5** | 全量绿（`-n 6`）| ✅（**间接**）| 同上。⚠️ **我没有重跑** —— GPT 席位此刻正在同机跑全量，再起一路 `-n 6` 会撞出**假红**（同机多路竞争已咬过人）。既有权威读数已覆盖这三笔提交 |
| **6** | 你自己再造一种不同形的攻击，新锁也要红 | ✅ **按字面成立** | 施工方 M2b「数值不动、只抹掉来源声明」确是不同形且红。⚠️ **但我自己造的那条走了另一根轴，没红** ⇒ **N-1** |

---

## 三、⭐ 值得记一笔的一处做对（⛔ 不是客套）

`test_real_sm25_host_inventory_is_unique_but_has_no_refusal_stock` ——
施工方**主动把「真产物在拒绝方向上零存货」写成了一条具名的锁**，
而不是拿合成夹具全绿交差。这正是本项目吃过亏的那条：
**⛔ 别问「有没有对照物」，要问「它声称覆盖的每种量各自有没有被量到」。**
拒绝方向的牙由「强制混合墙厚」的合成夹具提供（M-T3 实测两把新锁都红），
成功方向由真产物提供 —— **两个方向各自有存货，且分别说清了来源。**

---

## 四、不阻断 findings

### ⭐⭐ N-1（最值钱）：绑定校验量的是**声明**，不是**载荷**

**规则声称的**：设计稿 §四「envelope 哈希对不上 ⇒ 投影失败」，
docstring 写「**a filed envelope cannot swap the wall compilation it binds**」。

**实际量的**：`envelope.source_resolved_sha256`（**envelope 自己带的一个字段**）
`!=` `outcome.final_provisional_sha256`。
⇒ 它证明的是「**这份文件自称派生自 X**」，**⛔ 没有任何东西验证 `envelope.geometry` 真的是 X 投影出来的**。

**我造的攻击（不同轴）**：**不碰**声明字段，只换载荷 —— 删掉 `geometry.floors[0].cells` 里的一间房。

```
PROBE: {'claim_before': '5be561a0…0d59', 'cells_before': 16, 'cells_after': 15,
        'face_count_field_left_at': 16, 'completion_field': 'degraded'}
     -> returned cells = 15
```

⇒ **`run_correction` 原样返回了 15 间，零报错。** 一间房凭空消失而绑定校验全绿。
⚠️ 更要紧的是：那份 envelope 当时**自相矛盾** —— 它自己带的 `face_count` 停在 **16**，载荷只有 **15**。

**⭐ 修法几乎免费、且零阈值**：envelope **已经**带着 `face_count`，
而消费侧只把它**抄进读数**（`pipeline.py:1266`）、**从不与自己要返回的载荷对账**。
加一句 `len(envelope.geometry.floors[0].cells) == envelope.face_count` 就能拦下我这条。
⛔ 但请注意这只堵住我这一种；**根上的问题是「哈希绑的是声明不是字节」** ——
真解是让 `source_resolved_sha256` **对 geometry 的规范字节计算**，消费侧重算一遍。

**病族**：[[gate-measures-right-but-carrier-gets-swapped]] 第 ② 问 ——
「**它量的那个东西能不能被换掉**」。这里被换掉的是**信任的载体**：
门量的是文档的自述字段，而受保护的是同一份文档的载荷。
⛔ **加严哈希算法碰不到这个方向。**

> **归属建议**：登记为 B1 的第 7 条 debt（⛔ 不要塞进本单补丁 —— 本单已过审，
> 且真解要碰投影桥的产出格式，属实质改动，须另派 + 换人审）。

### ⭐ N-2：strict 这道门在**今天的任何一条路上都够不着**

| 我量的 | 读数 |
|---|---|
| 全仓 `evidence_chain_profile="strict"` 出现次数 | **1 次**，就在施工方新写的那把锁里（`tests/test_o22m7_evidence_wiring.py:556`）|
| `run_correction` 的两个生产调用点 | `pipeline.py:2162` · `scripts/tool_scripts/run_stage.py:457` —— **两处都不传 `evidence_chain=True`，也不传 profile** |
| 签名默认值 | `evidence_chain: bool = False` · `evidence_chain_profile: str = "exploratory"` |

⇒ 硬规则**实现了也锁住了**，但**没有任何现存路径能触发它**。
⚠️ **派工单 T4 描述的那个洞**（「生产帧恰好 degraded ⇒ 当前无门拦它往下走」）
**对今天每一个调用方来说仍然原样成立** —— 它们走 exploratory，而 exploratory **按设计就允许 degraded 通过**。

⛔ **这不是施工方的错**：任务书要的是「实现设计稿 §四那条 strict 规则」，它照做了。
**缺的是「谁在什么时候把 strict 打开」** —— 这是接线，不在本单范围。
> **归属建议**：**B5**（端到端 + 生产帧对账 F-1）。请在 B5 的单里写死：
> **交 judge 那一步必须以 strict 进入**，否则这道门永远是摆设。
> 病族 = [[two-kinds-of-latency-no-ruler-vs-never-reached]] 的第二种：**没跑到那一段**。

### N-3：T4 那把锁是**混合态**，「strict 端到端」全仓零测试

锁的做法是 monkeypatch 把上游 `profile` 从 `strict` 换成 `exploratory` 跑出真 degraded envelope，
再交给请求 strict 的消费侧。⭐ **施工方自己在执行档 §六 把这一点标成了最薄弱处，我确认这个自评准确**，
并且它**没有伪造 envelope**（用的是真产物跑出来的），这是对的选择。

我补一句它没说的：**因此「strict 从头到尾走一遍」这件事，全仓没有任何一条测试做过。**
与 N-2 是同一件事的两面 ⇒ 一并归 B5。

---

## 五、⛔ 我没做的事（诚实标注）

- **没重跑全量** —— 理由见 §二 #5（同机竞争会造假红）。按既有权威读数兜底。
- **没独立重数「24+12 条」** —— 按全量兜底。
- **N-1 的「真解」我没实现也没验证** —— 我只验证了缺口存在（实测）与一条廉价补丁的可行性（推理，**未实测**）。

---

## 六、给下程的一句话

**四把锁都是好锁，T3 的存货登记是范本。**
真正要带走的是 **N-1**：⭐ **一道门如果拿「被保护对象自己声明的字段」当判据，
它保护的就是那个声明，不是那个对象。**
