# 交叉审阅裁决书 · 接线摸排第一轮三摊（GLM-5.2 · 验证性审阅）

> 席位：GLM-5.2（验证性审阅，跨家族「谁写谁不批」——三摊由 Claude 侧 Sonnet 施工）。
> 审阅基点：`15ea05d`（`08.08_interface_sweep_round1_three_fixes_f16_multiplier_failopen`）。
> 当前 HEAD `23aed2e` 经核实**只改 2 份审阅文档**（本 brief + design），不涉生产码；跟踪文件工作树干净。
> 审阅单：[`request/2026-08-08_interface_sweep_round1_crossreview_brief_glm.md`](../request/2026-08-08_interface_sweep_round1_crossreview_brief_glm.md)。
> 硬纪律兑现：⛔ 只审不修、⛔ 零 commit/push、破坏性探针全在 `/tmp/xrv_glm`、主控侧全程只读。

## 总判定：**APPROVE**（0 BLOCKER / 0 MAJOR / 0 MINOR / 2 NIT）

A/B/C 三组 **17 条命题全部成立**。其中 5 条⭐承重命题（A4 / A5 / A6 / B2 / C3）我均用**自己的探针**独立验证为真绑，**未采信施工方自述、也未采信 orchestrator 裁定**。审阅单 §3 特别点名的两处 orchestrator 自评薄弱（A5 四把双向属性锁的 neuter 方向、C3 确认偏差），我换了自己的方向各复判一次，结论一致。清单外另登记 2 条 NIT 级观察（非阻断）。

---

## 独立全仓数字

```
2323 passed, 10 xfailed, 0 failed   (406.43s, -n 8, EXIT=0)
```

与审阅单声称的 `2323 passed / 10 xfailed / 0 failed` **逐字一致**。
基线 `4b77513` = 2289；三摊净增 34（摊一 24 + 摊二 3 + 摊三 7）= 2323，零回归。
⚠️ 跑测纪律兑现：`-n 8`（非 `-n auto`）、以汇总行 + 退出码为准；本次顺利跑完未见 98% 静默中断。

---

## A 组 · 摊一 F-16（`floor` 派生 + 嵌套标记机制）

### A1 · `floor` 从 v3 producer schema 剥除 + v1 字节不变 —— **成立**

- v3 `producer_facing_json_schema(CorrectedGeometryV3)` 的 `WindowV3` properties =
  `[facade, floor_id, id, provenance, room, span, z]` —— **`floor` 与 `facade_segment_id` 均被剥除，`floor_id` 保留**。
- v1 `producer_facing_json_schema(CorrectedGeometry)` 的 `Window` properties 仍含 `floor`（v1 不剥）。
- **v1 producer schema 字节不变**（硬证据，`/tmp/xrv_glm` 内 `git checkout 4b77513 -- vocab.py schema.py` 重 dump 对比）：
  `15ea05d` 版 = 2758 bytes，`4b77513` 版 = 2758 bytes，`diff` 为空 ⇒ **BYTE-IDENTICAL**。
  机制论证：vocab.py 改动仅新增认 `CORRECTION_DRAW_DERIVED` 标记参与剥除，而 v1 (`CorrectedGeometry`/`Window`) 无任何 DERIVED/FORBIDDEN 标记字段，故剥除集合对 v1 恒为空。

### A2 · 模型填 `floor`（即使值正确）必拒，code + category 正确 —— **成立**

自构造合法 v3 载荷（`floor_id="F1"`/`name="Level 1"`，真实 F-16 碰撞形态）喂 `parse_correction_draw`：

```
parse_correction_draw(payload 带 floor="Level 1", V3)
  → WindowResolverInputError  code='producer_window_floor_populated'  category='model_draw_error'
```

即便填的 `floor="Level 1"` 与派生值**完全一致**，b2 raw-payload 门仍在 `model_validate` 之前拒（门查的是「模型有没有填」，不是「值对不对」）。
重试引导通道亦通：`_MODEL_DRAW_ERROR_GUIDANCE["producer_window_floor_populated"]` 存在，`retry_guidance_for_correction(V3)(exc)` 返回非空且提及 `floor` ⇒ **非裸 ValueError，能拿到纠错话术**（F-15 教训已落实）。

### A3 · 模型不填 `floor` → 代码派生，值正确 —— **成立**

```
CorrectedGeometryV3.model_validate(不填 floor)  → windows[0].floor == "Level 1"  (派生自 by_id["F1"].name)
windows[0].floor_id == "F1"  (name != id，正是 F-16 碰撞的混淆点)
经 parse_correction_draw 全程(含 b2 门) → 通过, floor 派生为 "Level 1"
```

### A4 ⭐ · v1 路径完全不受影响 —— **成立**（独立构造 v1 载荷，非只看测试）

```
v1 Window.floor required?  True        v1 Window 有 floor_id?  False
v1 带 floor="F1" → parse_correction_draw 通过, windows[0].floor="F1"
v1 不带 floor   → ValidationError  (floor 仍必填, loc=['windows',...])
```

`WindowV3.floor` 覆写（`str | None` + DERIVED 标记）只活在 `WindowV3` 上；基类 `Window.floor: str` 原样必填。子类覆写不渗透父类必填约束。

### A5 ⭐ · 双向属性锁 ×4 —— **成立**（我换了 neuter 方向）

审阅单 §3#1 要求「换你自己的 neuter 方向」。orchestrator + 施工方用的方向是**接线层**（把 parse.py/window_sources.py 的标记遍历改回硬编码字段名）。我换成**命题字面方向**——运行时增删 `field_info.json_schema_extra` 标记，看真实 `parse_correction_draw` 门是否跟着反应（两方向互补：一个测「门依赖标记遍历」，一个测「门跟着标记走」）：

| 方向 | 操作（monkeypatch 标记） | 门反应 | 命题 |
|---|---|---|---|
| 1 | 删 `floor` 的 DERIVED | 带 floor 载荷 → **通过**（门停拒） | ✓ 停止拒绝 |
| 2 | 给普通字段 `room` 加 DERIVED | 带 room 载荷 → 拒, code=`producer_window_floor_populated` | ✓ 开始拒绝 |
| 3 | 删 `facade_segment_id` 的 FORBIDDEN | 带 seg 载荷 → **改由 schema `ValidationError("unknown facade_segment_id")` 拒**（typed 门停拒，控制权转交） | ✓ typed 门停止 |
| 4 | 给普通字段 `room` 加 FORBIDDEN | 带 room 载荷 → 拒, code=`producer_segment_ref_prefilled` | ✓ 开始拒绝 |

四方向全通过 ⇒ **锁的是「门跟着标记走」的性质本身，不是某个字段名**。
关键判别点：方向 2 命中 DERIVED 路径 code（`..._floor_populated`），方向 4 命中 FORBIDDEN 路径 code（`..._ref_prefilled`）⇒ **两个 marker 各走 parse.py 里自己的独立循环**，命题 A6 的「必须两个标记」在接线层得到二次印证。实验后标记已恢复并校验。

### A6 ⭐ · DERIVED 与 FORBIDDEN 必须是两个标记 —— **成立**（命脉，独立验证理由）

命题给的理由：「派生字段在 `model_validate` 成功后总是被填充 ⇒ post-construction 的『是否非空』检查会对每个合法 v3 draw 误触发」。我模拟「合并成一个 FORBIDDEN 标记」：

```
合法 v3 draw (floor 已派生 = "Level 1") → 正常 _producer_preflight: 通过 ✓
给 floor 打 FORBIDDEN (模拟合并) 后, 同一个合法实例:
  → _producer_preflight 误拒  code='producer_segment_ref_prefilled'
```

`_producer_preflight` 收到的是**已验证实例**，`floor` 此刻恒非 None；若把它也收进 `nested_draw_forbidden_fields` 做「非空」检查，则**每一个带窗的合法 v3 draw 都会被拒**——这会把链路打死，不是「少覆盖一点」。**理由真实成立，分岔是必要的，不是命名偏好。**

### A7 · `envelope_transform.py:324/529` 与 `window_host.py:689(现703)` 未改是正确边界 —— **成立**

`git show 15ea05d --stat` 确认 **envelope_transform.py 本 commit 零改动**。逐处核实这些硬编码 `facade_segment_id` 检查的用途，**全部不是 draw 合约门**，故不该改成遍历标记：

| 处 | 用途 | 该不该改 |
|---|---|---|
| `envelope_transform.py:324` | B2b 信封变换**结束**硬门（候选几何不能已带 Vg 绑定） | 否（阶段后置） |
| `envelope_transform.py:529` | B2b 事务**开始**前置（已绑定的不能进变换） | 否（阶段前置） |
| `window_host.py:703`(原689) | `resolve_window_hosts` **入口**前置（传入 geom 不能已带绑定） | 否（阶段前置） |
| `window_host.py:981` | resolver **apply 循环**前置（绑前 window 不能已带） | 否（阶段前置） |
| `schema.py:471` | `_v3_integrity` 引用完整性（seg_id 必须引用存在的 segment） | 否（schema 不变量） |

它们追责的是「内核自己的处理顺序有没有被破坏」，与「模型 draw 时是否非法填」是两件事。命题边界判断正确。

---

## B 组 · 摊二（`create_fenestration` 的 `multiplier`）

### B1 · `multiplier` 从参数表移除，模型无途径设置 —— **成立**

```
create_fenestration.args = [building_surface_name, construction_name, name, surface_type, vertices]
→ "multiplier" not in args ✓
```

内省的是 LangChain `@tool` 自己声明的 schema（非手抄清单）。全仓 `make_fenestration_tools` 唯一调用点 = `nodes/fenestration.py:49`（AgentState 绑定），无其他暴露面。

### B2 ⭐ · schema 仍默认 1 + standalone MCP 工具 multiplier 原样保留 —— **成立**

- `FenestrationSurfaceSchema.multiplier`（`data_model.py:966`）= `Field(1, alias="Multiplier", ge=1)` ⇒ **default=1**，行为不变。
- standalone MCP 工具 `src/mcp/api/envelope.py:931 create_fenestration_surface` **仍保留 `multiplier: int = 1`**（docstring + 传 `FenestrationCreateInput`）——这是**不同的函数**（FastMCP `@mcp.tool` 注册，供人/他 agent 直接建模），其 `multiplier` 是 EnergyPlus `Multiplier` 字段的合法用法，**未被误伤**。施工方前置调查结论（无合法非 1 用法于 `create_fenestration`）成立。

### B3 · 锁3「摘掉不红」自陈成立 —— **成立**（实测）

`/tmp/xrv_glm` 还原 `multiplier` 参数后跑 `test_a1` 三条锁：

```
test_created_fenestration_multiplier_always_one            PASSED  (锁3, neuter 后仍绿)
test_create_fenestration_call_site_cannot_pass_multiplier  FAILED  (锁2, 真绑)
test_create_fenestration_tool_schema_has_no_multiplier_field FAILED (锁1, 真绑)
```

**施工方自陈成立**：锁3 测的是「不传 multiplier → 落盘==1」的**默认回退行为**，与「参数是否摘除」无关（还原参数后调用方仍不传 ⇒ 默认 1 ⇒ 落盘 1 ⇒ 绿）。
**但锁3 不是装饰性**：它守护的是 `FenestrationSurfaceSchema.multiplier` 默认==1 这个**底层不变量**——若有人改 schema 默认值，锁3 会红。摊二修法（摘参数）的核心守护是锁1（接口）+ 锁2（调用路径夹带无效），三条合起来才构成完整证据链。施工方诚实披露了 neuter 形态，无假锁。

---

## C 组 · 摊三（严格档 fail-open）

### C1 · 默认值改 regression 后生产调用点零行为变化 —— **成立**（独立枚举）

- `disposition()` 两个直接生产调用点：`evidence_preflight.py:116`、`orchestrate.py:85` —— **都显式传 `run_profile`**。
- `CheckReport(...)` 生产构造点：`check_correction/kernel/mep/reading` 全部 **`run_profile=run_profile` 转发**；`view_manifest.py:143`、`assembly.py:33` 也传。
- **唯一不传 `run_profile` 的生产点 = `assembly.py:60 check_ep_baseline`** —— 但它只产 `ep.end_present`(ERROR/INVARIANT)、`ep.completed`(INVARIANT)、`ep.zero_severe`(INVARIANT)、`ep.warning_threshold`(CROSS_CHECK) 四类检查，**全部走 ERROR/INVARIANT/CROSS_CHECK 分支，`disposition` 里无一查阅 `run_profile`** ⇒ 默认值 exploratory→regression 对它**零行为变化**。

> 附注（非缺陷）：命题括号「它们都显式传」对 `check_ep_baseline` 不严格——它在施工日志里已被诚实记录为「唯一吃默认值的点且不敏感」，与命题主旨自洽。同族跟进债：`check_*` 函数自己的 `run_profile: RunProfile = "exploratory"` 默认值未改（派工边界「两处都在 schema.py」之外），施工日志已登记。

### C2 · 白名单翻转后既有档位逐一不变，仅未来档位 FLAG→BLOCK —— **成立**

实跑 `disposition` 对 evidence / plan-frame 两类检查 × 5 档：

```
            evidence    plan_frame
exploratory  FLAG        FLAG       } 翻转前 {golden,regression}=BLOCK 一致
dev          FLAG        FLAG       }
golden       BLOCK       BLOCK      }
regression   BLOCK       BLOCK      }
hypothetical_5th  BLOCK  BLOCK      ← 翻转前 FLAG, 现 BLOCK (唯一变化)
```

4 个既有档位逐档与翻转前相同；只有假设的第 5 档从「不阻断」变「阻断」。命题成立。

### C3 ⭐ · OCR/dim-endpoint 不翻转正确 + 锁#10 真绑 —— **成立**（独立判，未采信 orchestrator 裁定）

审阅单 §3#2 明确预警「我在裁定时可能有确认偏差（倾向于接受纠正我的人）」。我独立复判如下，**不依赖 orchestrator 的最终裁定**。

**(a) 独立复现启发式假阳性**（C3 的硬证据）：同一栋合法 10×8m 建筑，两种合法编码喂 `_structural_metric_reference` + `_dimension_endpoints_in_bounds`：

```
(A) 4 条 line 编码       bounds=(-45,55,-36,44)   合法标注[9,7] → PASS
(B) 闭合 polyline 编码   bounds=(-5,5,-5,5)       合法标注[9,7] → FAIL  ← 假阳性!
(C) 真坏数据 [360,450]   (像素锚点, 10m建筑)      → FAIL  (正确抓坏数据)
```

闭合 polyline 重复起点作为终点，把 median 拉向角点 (0,0) 而非房间中心，MAD 坍缩，容忍带收缩到 [-7,7]——**房间内完全合法的公制标注被判出界**。同一检查既漏判（整体像素空间时）又会误判（合法闭合画法时）⇒ **双向不可靠**。因此「让它 advisory（永不 BLOCK）」是正确的；若翻转成 permissive whitelist，未来第 5 档会让这个已知误判的启发式去 BLOCK 一栋正确建筑（如 B 形态）。**施工席顶回 orchestrator、不翻转，判断正确。** 我的独立证据与结论与 orchestrator 最终裁定一致，但我有自己跑出来的假阳性复现，不是采信。

**(b) 锁#10 真绑**：monkeypatch 把 `_OCR_ANCHOR_BLOCK_PROFILES` 填入 `{hypothetical_stricter_profile}`（模拟「有人顺手翻转/补完」），则该档 OCR 检查从 FLAG → BLOCK，锁#10 断言「全档 FLAG」会失败 ⇒ **锁#10 真绑**，能感知这两处常量的任何「补完」。

---

## 清单外自主发现（与清单内判定分开列）

### E1 · producer schema 剥除后 `required` 一致性 —— **干净，无问题**（NIT 级核验，非 finding）

担心点：vocab.py 删 FORBIDDEN/DERIVED 字段的 `properties` 但不更新 `required` 数组，可能留下「required 引用不存在 property」的悬挂。实测：

```
WindowV3 properties: [facade, floor_id, id, provenance, room, span, z]
WindowV3 required  : [facade, floor_id, id, span, z]
required - properties = ∅  (一致, 无悬挂)
```

`floor`/`facade_segment_id` 均为 optional（default=None），本就不进 required，剥除安全。**无问题**，仅作记录。

### E2 · `resolve_window_hosts` 的 floor-desync 检查用裸 `assert` —— **NIT**（非阻断观察）

`window_host.py:752` 用 `assert floor.name == window.floor, ...` 作为 post-construction 篡改的 defense-in-depth backstop。`assert` 在 `python -O` 下会被剥离。

- **实测它是 live code**（填补施工日志 neuter 表 #5「逻辑推导非实测」的空白）：构造合法 geom 后 `materialized.windows[0].floor = "not-the-real-floor-name"`，`resolve_window_hosts(...)` → `AssertionError: window w1: floor/floor_id desync despite schema derivation ...`。
- 项目当前**不用 `-O`**（全仓 grep `python -O`/`-O` 无命中），故 assert 生效。
- **不升级为 finding**：这是 defense-in-depth backstop，**primary 门是 `parse.py` 的 typed b2 门**（`WindowResolverInputError`，不受 `-O` 影响）。即便将来启用 `-O` 使这层 backstop 失效，primary 门仍守住。登记为观察：若项目未来启用 `-O`，此 backstop 静默失效（建议届时换成显式 `raise`）。

### E3 · `facade_segment_id` 字段名仍散布于多处生产码 —— **非 finding**（设计决策观察）

draw 合约门（`parse.py` / `window_sources._producer_preflight`）已统一到标记遍历（Step 1 修法），但 `facade_segment_id` 这个字段名仍硬编码在 `envelope_transform.py:324/529`、`window_host.py:703/981`、`schema.py:471`、`artifact_serialization.py:20` 共 ~6 处。

逐处核实（见 A7 表 + 序列化净化）：**全部是非 draw-合约用途**（阶段前置/后置、引用完整性、v1/v2 legacy 序列化净化 B5 字段），性质上就需要显式引用该字段，**不该**改成遍历标记（会把「阶段顺序检查」和「draw 合约检查」两种不同性质的东西混到一起）。这是正确的设计决策，**不构成漂移 bug**。仅登记：将来若 `facade_segment_id` 改名，这几处需手动同步（可接受的显式引用代价）。

---

## 审阅单 §3 两处「特别用力」的独立复判小结

1. **A5 四把双向属性锁**：我换成「运行时增删标记看门反应」方向（vs orchestrator/施工方的「改回硬编码」方向），4 方向全通过，两个 marker 各走独立循环。**无确认偏差风险——我用了不同的探针轴，结论独立成立。**
2. **C3**：我独立复现了启发式假阳性（闭合 polyline 编码的合法建筑被误判），证明翻转会让已知不可靠的判据在未来档位 BLOCK 正确建筑。**未采信 orchestrator「它对我错」的裁定**——我有自己跑出来的 (A)/(B)/(C) 三态对照证据。结论与 orchestrator 一致，但建立在独立证据上。

---

## 分级汇总

| 级别 | 数量 | 条目 |
|---|---|---|
| BLOCKER | 0 | — |
| MAJOR | 0 | — |
| MINOR | 0 | — |
| NIT | 2 | E2（assert 在 `-O` 下失效的 backstop 观察）/ E3（`facade_segment_id` 散布的设计决策观察） |

**结论：三摊修法全部成立，5 条承重命题独立验证为真绑，无假锁，全仓数字吻合。APPROVE。**

E1（required 一致性）经核干净，不计入 finding。E2/E3 均为「未来潜在陷阱」级观察，不影响本轮交付，建议登记入跟进债供未来批次参考（E2：若启用 `-O` 需把该 assert 换显式 raise；E3：`facade_segment_id` 改名时手动同步 6 处）。
