# 交叉审裁决 · F-12 / F-9 / F-13 三摊合审（**验证性审阅**）

- **日期**：2026-08-07 · **席位**：**GLM-5.2**（跨家族，谁写谁不批 —— 三摊全由 Claude 侧 Sonnet 施工）
- **工作区**：主工作树，基点 = **`950cdbf`**（开工 HEAD，自查：`git log --oneline -1` = `950cdbf 08.07_WrapUp_EndToEnd_TrustworthyNumbers_F13r1_Passed`）
- **任务类型**：验证性审阅（给定 finding 清单验锁真绑 / false-lock），⛔ 非探索性
- **边界遵守**：⛔ 零生产码/测试改动、零 commit/push/add、零门放宽、case_tests/ 未跟踪目录只读未碰；neuter 在 `/tmp/glm_xreview`（一次性 worktree，显式基点 `950cdbf`，验完 `git worktree remove --force` 销毁）；探针在 `/tmp/glm_{f13,f9}_probe.py`；全程只读 git（零抢锁）。

## 独立全量基线（GLM 亲跑，非采信 orchestrator 数字）

```
python -m pytest -q -n auto   →   2255 passed, 10 xfailed, 0 failed (382.03s)
```

与 orchestrator 轻门（F-13 裁决书 §2）报告的 **2255 / 10 / 0 逐字一致**。`test_zone_agent`（F-14 候选）本次未红。

---

## TL;DR

| 摊 | 结论 | finding |
|---|---|---|
| **F-13 r1** 内核产出规范顶点顺序 | **APPROVE（附 1 MAJOR）** | 修法核心对（单一实现两处共用）、垂直面端到端 79/0 + EP 0 severe 已坐实；**但 lock2 对水平面（楼板/天花/屋顶）退化为自指恒等锁 + 水平面无端到端对账 ⇒ 起笔角正确性零覆盖（回归缺口，当前实现对）** |
| **F-9** 窗宿主解析接线 + 分类 | **APPROVE（附 1 MINOR）** | category 取值域**封闭**（独立证实）；锁真绑（真实入口端到端 + 自带 neuter）；覆盖不对称 = MINOR |
| **F-12** 下游提示词改照抄 | **APPROVE（附 1 MINOR）** | 提示词消除根因、WWR 推导确已移除；prompt 锁可被无害改写绕过（已实证），但 `VERTEX_FRAME_DRIFT` 行为门兜底 |

**MAJOR/BLOCKER 列表**：**0 BLOCKER / 1 MAJOR**（F-13 lock2 水平面覆盖缺口）/ 2 MINOR（F-9 覆盖不对称 · F-12 prompt 锁可绕过）。

**§2.2 那个判断（恒等锁≠正确性锁）—— 部分同意**：
- ✅ **核心洞察同意**：恒等锁（lock1）证明「两套规范已统一」、不证明「规范对」——成立。我独立用探针复现了 orchestrator 的「换方向 neuter」结论。
- ⛔ **但「lock2 那四条断言首顶点等于手算值、守正确性」不同意**：**只有垂直墙一条**（`test_f13:202` 断言 `canonical[0]==[1,0,2]`）是手算值锁；**楼板/天花/窗三条**（`:217/:231/:244`）只断言 `top_left_corner_index(canonical,normal)==0`，是**自指恒等锁**，挑错角仍绿（探针 Part B 实证：楼板起笔点从正确的 `[0,0,0]` 变错角 `[0,3,0]`，断言仍 `==0`）。**裁决书 §3 这句陈述与代码事实不符。**

**§2.3 那个判断（category 取值域封闭）—— 同意**：独立探针证实（第三值被 Literal 拒 / 空集被构造器拒 / 两值 round-trip / 返回类型 = 两值 Literal）。

---

## F-13 r1（路线①）：**APPROVE（附 1 MAJOR）**

### 设计审 — APPROVE
- `canonicalize_ring_vertices` / `top_left_corner_index` 逐字节提取为模块级纯函数（`data_model.py:1047` / `:1086`），校验器两方法一行委托（`:1338` / `:1363`），内核 `build_geometry` 在定稿处调**同一份**函数（`build.py:78` 面 / `:84` 窗）⇒ **单一实现、两处共用**，符合派工单硬约束，避开「造第三套规范」的陷阱。
- 法向自参照 Newell（`build.py:75/81`）合理：内核绕向早由 `_orient` 保证，无需复刻校验器 Delaunay/interior-points 推导；退化面（`norm<1e-9`）跳过（`:76/:82`）。
- 既有测试处理合规（`a3458cc` diff 亲核）：`c2_b5_legacy` fixture 仅重算 `build`/`spec` 两键哈希，**`output`/`audit` 逐字节不变**（⇒ 改动范围确实只在顶点序）；`parent_and_verts` 一处窗口 verts 同点集同绕向、仅起笔点从 `[1,0,1]` 挪到左上角 `[1,0,2]` + 附手算推导。**非删断言。**

### 锁真绑 — APPROVE
- lock1（恒等：内核产出喂真实入口 `SurfaceConverter.validate`/`FenestrationConverter.validate` 后字节不变 + change counter==0）、lock3（change counter 触发 + 修复非规范输入）、neuter（monkeypatch 撤内核 `_canonicalize_bg_vertices` → lock1 7/7 红）均**真绑目标**。
- §5 派工方第 11 次出错（`--intake-from` 跳过修复段 = 假验证温床）：施工席顶住未照做、改走真实代码路径 —— 做得对。裁决书 §7 补跑的防假验证自检（新件 `Z01_Ceiling` 左上角索引 0、非规范面 0/115；旧件 索引 2、104/115）数字与当初 B 层漂移 104 逐一闭合，采信。

### ⛔ MAJOR-1：lock2 对水平面退化为恒等锁 + 水平面零端到端对账

**事实（代码行号）**：lock2 四条里，**只有垂直墙**断言手算首顶点：
- `test_f13:202` 墙 → `assert np.array_equal(canonical[0], np.array([1.0,0.0,2.0]))` ✅ 手算值
- `test_f13:217` 楼板 → `assert top_left_corner_index(canonical, normal) == 0` ⚠️ 自指
- `test_f13:231` 天花 → `assert top_left_corner_index(canonical, normal) == 0` ⚠️ 自指
- `test_f13:244` 窗 → `assert top_left_corner_index(canonical, normal) == 0` ⚠️ 自指

**为什么 `top_left_corner_index(canonical,normal)==0` 是恒等**：`canonicalize_ring_vertices`（`:1081-1083`）末步就是 `np.roll(sorted_points, -top_left_index)`，roll 后 `canonical[0]` 必然是 `top_left_corner_index` 挑的那个点；而 `top_left_corner_index` 基于质心相对坐标的 lexsort（`:1107-1114`）是**排列无关**的，对 roll 后的点集再判必返回 0。⇒ **该断言与挑角对错无关，是数学恒等式。**

**独立实证（`/tmp/glm_f13_probe.py`，可重跑）**：
```
Part B — 用 EVIL picker（对水平面挑对角的错角，排列无关）：
  floor:   lock2 assert with EVIL picker -> True  (canonical[0]=[0,3,0]  ← 错角！原应为 [0,0,0])
  ceiling: lock2 assert with EVIL picker -> True  (canonical[0]=[0,0,3]  ← 错角！)
  wall:    lock2 assert with EVIL picker -> True  (canonical[0]=[1,0,2]  ← evil 不动垂直面)
⇒ 楼板/天花的起笔点被改成对角错角，lock2 仍全绿。
```
**当前实现正确**（Part C 手算：楼板 normal=(0,0,-1) 朝下，viewer 自下往上看，world_up=(0,-1,0)/right=(1,0,0)/up=(0,-1,0)，左上角 = y 最小 & x 最小 = `[0,0,0]`，与 `canonicalize_ring_vertices` 输出逐点一致）⇒ **非当前缺陷，是回归保护缺口。**

**端到端也不覆盖水平面**：裁决书 §7.2 ③ 宽高对账「**垂直面(墙+窗) 79 判对/0 判错**」——判据「真实高=z 跨度、真实宽=水平跨度」只对垂直面成立；总面 115 − 垂直面 79 = **36 个水平面（楼板/天花/屋顶）零宽高对账**。

⇒ **水平面「左上角起笔客观正确性」完全无正确性锁覆盖**（lock1 恒等 · lock2 楼板/天花恒等 · lock3 恒等 · 端到端对账不覆盖）。将来若 `top_left_corner_index` 对水平面改坏（如 `:1095-1099` 的 world_up 分支选错），**所有锁 + 端到端对账全绿 = 假绿**，且恰好落在 orchestrator 自己承认犯过错的「楼板法向朝下」面型（裁决书 §7.1 自承用俯视直觉误判 18 个楼板）。

**定级理由**：MAJOR（非 BLOCKER，因当前实现对 + 垂直面已端到端验证 + 不阻断合并）；非 MINOR（直接落在请求书 §2.2 核心关注点 · 裁决书明确陈述与事实不符 · 是「零覆盖」非「弱覆盖」）。
**建议（不阻断当前合并）**：给 lock2 楼板/天花/窗补手算首顶点断言（仿 `:202` 垂直墙的 `canonical[0]==<手算值>`）；楼板手算值本审已给（`[0,0,0]`，Part C）。这与项目招牌教训「恒等锁≠正确性锁、必须另配手算值锁」一致 —— F-13 在垂直面兑现了这条，水平面漏了。

---

## F-9 窗宿主解析接线 + 分类：**APPROVE（附 1 MINOR）**

### §2.3 category 取值域封闭 — **APPROVE（独立证实）**

独立探针 `/tmp/glm_f9_probe.py`（可重跑）：
```
Test 1: fallback_action="SOME_THIRD_VALUE"  → BLOCKED by Literal schema (ValidationError)
Test 2: WindowHostResolutionError(())        → BLOCKED by ctor (ValueError: requires typed conflicts)
Test 3: needs_input → model_draw_error ; invariant → input_integrity_error  (round-trip ✅)
Test 4: category 返回类型 = WindowSourceErrorCategory = Literal["model_draw_error","input_integrity_error"]
        (window_sources.py:72)
```
- `fallback_action` 钉死两值（`window_host.py:320`），`fallback` 变量三处来源（`:1032/:1035/:1038`）均为 `invariant_no_geometry_commit` 字面量、else 分支 `raise RuntimeError`（`:1040`）；
- 构造器硬拦空集（`:388-389`）；`category`（`:419-421`）穷举两分支、无兜底默认。
⇒ **取值域封闭、无空集漏洞、无兜底默认。orchestrator 判断成立。**

### 锁真绑 — APPROVE
`python -m pytest tests/test_f9_window_host_crash.py -q` → **8 passed**。锁形态好：
- Lock1 真实入口 `_draw_correction`（stub LLM 边界、跑全下游异常处理）验不崩 + 归档 blocked draw（非 `FinalizeResult`）+ 消费真实 4 个 window_id；
- 自带 neuter `test_real_crash_run_neuter_...`：monkeypatch `category=input_integrity_error` → `pytest.raises(WindowHostResolutionError)` 崩溃重现（证明绑 run_stage routing）；
- Lock3 envelope_transform PRE 对称：non-invariant fold 为 `EnvelopeTransformRejected`（`:228-235`）+ invariant 仍 raw raise（`:238-278`）。

### MINOR-1：覆盖不对称（同意 orchestrator 定性）
「不变量级冲突必须硬崩」这一侧，端到端锁（`test_real_crash_run_neuter`）是通过 **monkeypatch 强制 category** 覆盖 routing 的，**不是「真实 invariant 冲突自然产生 → 端到端崩」的完整链路**；该侧目前靠单测（category 属性 4 条）+ envelope_transform 层锁（`test_pre_transform_invariant_conflict_still_raises`）守。
**风险**：若某 throw site 误把本应 `invariant_no_geometry_commit` 的冲突标成 `needs_input_no_geometry_commit`，`category` 会误判为 `model_draw_error` → 该不变量违反被**静默归档重抽**（假绿），单测（只测 category 属性逻辑）抓不住 throw-site 误标。
**等级 MINOR**：概率低（fallback_action 是 throw site 显式赋值，code review 可控），且 run_stage routing（input_integrity_error→崩）已被端到端覆盖。登记跟进债，不阻断。

---

## F-12 下游提示词改照抄：**APPROVE（附 1 MINOR）**

### §2.4 提示词消除根因 + WWR 移除 — **APPROVE**
- `surface.py:18-35` 现命令「transcribe vertices verbatim from surface_specs — do NOT recompute」；`do not use zone_specs' z_floor/ceiling_height to compute vertex Z`（`:28-30`）；用户消息 `ZONE_SPECS`（仅名字/邻接）+ `SURFACE_SPECS`（权威顶点照抄，`:100-106`）。
- `fenestration.py:18-20` 明确「do NOT derive vertex coordinates from a window-to-wall ratio (WWR)」——**WWR 推导指令确已移除**，fenestration_specs 携带完整顶点照抄。
- 注释（`surface.py:91-99`）如实说明旧「derive Z from zone_specs」指令是 `VERTEX_FRAME_DRIFT` 漂移根因。根因消除方向正确。

### MINOR-1：prompt 正则锁可被无害改写绕过（行为门兜底）
F-12 锁（`test_f12_surface_prompt_transcribe.py`）**全是 prompt 字符串正则锁**（钉旧措辞），无行为锁。worktree neuter（`/tmp/glm_xreview`，基点 `950cdbf`，验完销毁）：
- **Neuter A**（改回旧措辞 `bottom z = z_floor`）→ `test_surface_prompt_does_not_command_z_floor_arithmetic` **变红** ✅（锁钉旧措辞）。
- **Neuter B**（注入换措辞但语义仍命令重算：「for each wall you may independently derive vertex Z values from the owning zone's floor elevation and storey height as a check」）→ test_f12 **5 全绿（绕过）** ⚠️。

⇒ **§2.4① 成立**：换个说法命令 LLM 重算，prompt 锁绕过。这是 prompt 正则锁的固有脆弱。

**但有行为门兜底（故 MINOR 非 MAJOR）**：`VERTEX_FRAME_DRIFT`（`output_coordinates.py:816` `_vertex_drift_issues` + `:781` `_live_idf_vertex_drift_issues`，TERMINAL check）逐顶点精确比较（round 2 位，`:835-839`）。snapshot 由 `build_output_coordinate_snapshot(bg)`（`:697`）从**内核 `bg`** 构造、非 ConfigState 自指；snapshot bytes 进 contract `geometry_snapshot_sha256` 且 `:1029-1030` hash 校验防篡改。⇒ 即使 prompt 被绕过、LLM 真重算墙顶点，下游 ConfigState 偏离内核 snapshot → `VERTEX_FRAME_DRIFT` 红。裁决书「漂移门 104→0」即此门抓墙漂移的实证。
**建议**：prompt 锁当「防倒退到具体旧措辞」的 code-review 信号即可，**勿当唯一防线**（真正防线是 `VERTEX_FRAME_DRIFT`）；可给 `VERTEX_FRAME_DRIFT` 补一个单元锁（构造 surface agent 重算墙的场景验红），让行为门有回归保护（目前行为门靠端到端 run 实证、无单元锁）。

---

## §2.5 三摊互相拆台 — **APPROVE（未拆台）**

- F-13 改内核顶点顺序 → F-12 命令下游**照抄**内核顶点 → 下游顺序随内核更新，**一致**。
- `VERTEX_FRAME_DRIFT` 的 snapshot 每次 run 由当次内核 `bg` 现场冻结（`:697`），**不跨版本**，不会因 F-13 改序而对旧 run 假红。
- F-12 测试是 prompt 正则锁，**不涉及具体顶点顺序**，不钉旧顺序。
- c2_b5 fixture 已合规更新（见 F-13 设计审），无夹具钉旧顺序。
⇒ **二者叠加无新不一致。**

---

## 停下上报说明

无。请求书陈述的事实与本审所见**基本一致**，审阅可正常完成。**唯一与既有裁决书陈述不符之处** = F-13 裁决书 §3「lock2 那四条断言首顶点等于手算的左上角值」—— 实际只有垂直墙一条（详见 MAJOR-1）。此为正常审阅 finding（已落 MAJOR-1），非「派工前提错致无法施工」，无需中断上报。

## 复现指引（可独立重跑）
- F-13 恒等性：`python /tmp/glm_f13_probe.py`（Part B 判决性：水平面挑错角仍 `==0`）
- F-9 封闭性：`python /tmp/glm_f9_probe.py`
- F-9 锁：`python -m pytest tests/test_f9_window_host_crash.py -q`（8 passed）
- F-12 neuter：`git worktree add --detach /tmp/glm_xreview 950cdbf` → 改 `src/agent/nodes/surface.py` 的 `SURFACE_SYSTEM_PROMPT` → `pytest tests/test_f12_surface_prompt_transcribe.py`（Neuter A 红 / Neuter B 绿）→ `git worktree remove --force`
- 全量：`python -m pytest -q -n auto`（2255/10/0）
