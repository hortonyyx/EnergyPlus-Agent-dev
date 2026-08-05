# 派工单（Claude 侧 Sonnet 子代理）· F-7 接口修法 —— `source_ids` 语义改为观测编号

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：Claude 侧 Sonnet 5 子代理，**独立 git worktree**
- **范围**：**只做本单**。F-2c 收口已另派 GLM 席位在主工作树并行开工。
- **前序调查**：[`../execution/2026-08-05_f7_claim_links_interface_gap_glm.md`](../execution/2026-08-05_f7_claim_links_interface_gap_glm.md)（GLM 已查完，结论可信，下方 §1 已转述全部要点，**不必重查**）

> **⚠️ 并行席位纪律**：GLM 席位正在主工作树改 `src/agent/correction/window_sources.py` 的**另一处区域**
> —— 它把 `identify_reading_contract` 从 `src/agent/judge/` 搬到 `src/agent/reading/`，只动该文件**约 505–520 行的 import 块**。
> 你在**独立 worktree** 里工作，改的是 `_claim_links`（约 621 行）附近 + `pipeline.py` + 错误分类。
> **⛔ 不要碰 import 块、不要碰 `verify_reading_stage_root_against_accepted_attempt`、不要碰 `src/agent/judge/`。**

> **⚠️ 派工方自述**：本轮我（orchestrator）已经出错四次，其中**两次就是关于 F-7 的**（我预设是「残留产物」和「走 F-4 重试通道」，双双被证据推翻）。
> **本单里凡是与代码实情不符的地方，一律停下上报，不要硬做。**「停下上报」在本项目是记功不是记过。

---

## 1. 病灶（已由调查坐实，直接照此开工）

### 1.1 死点

`_claim_links`（`src/agent/correction/window_sources.py:621`）要求校正段的 LLM 在
`window.provenance[claim].source_ids` 里填 **locator**：

```python
def source_locator(*, input_id: str, observation_id: str, output_sha256: str) -> str:   # :253
    return SOURCE_LOCATOR_PREFIX + canonical_sha256({
        "input_id": input_id, "observation_id": observation_id,
        "output_sha256": output_sha256, "schema": "window_source_locator_v1",
    })
```

其中 `output_sha256` = **识图产物文件字节的 sha256**。

### 1.2 为什么模型永远给不出

四条证据合围（调查方逐条 grep 坐实）：

1. **模型物理上算不出**：抽签时拿不到识图产物字节，算不出 `output_sha256`。
2. **prompt 从没提过**：`_build_correction_messages`（`src/agent/pipeline.py:329`）正文
   grep `source_id|locator|src:|offer` **零命中**；correction skill 文档（`A0_contract.md`/`A3_arbitration.md`）
   只讲 `ns[]`（perception/dimension id）。
3. **prompt 结构上产不出目录**：`_build_correction_messages` 的签名只有
   `vector_dir / testdata_text / feedback / evidence_debt / target` —— **不接收 manifest、不接收 reading artifacts**。
4. **locator 目录基建是生产孤儿**：`build_window_source_offer`（`window_sources.py:400`）全仓只被
   `tests/test_c2_b5_source_routing.py` 调用，`src/`/`scripts/`/`skills/` 零调用。

### 1.3 测试为什么一直是绿的

B5 夹具**手搓真 locator**：`test_c2_b5_parent_and_verts.py:171/203`、
`test_c2_b5_source_routing.py:54/60/224/342` 都是现算 `source_locator(...)` 塞进 `source_ids`
⇒ 消费侧与夹具自洽、测试永绿；**真实 LLM 抽签永远没有 locator ⇒ 必崩。**

**⇒ 这是 F-5 的双胞胎**（F-5 = 四个测试文件的夹具集体照抄了实现的错拼写 `x_range` vs 契约 `x_range_m`）。
本项目对这一族缺陷的治理教训：

> **消费某个契约的测试，其夹具必须钉到契约的单一来源（机械导出），⛔ 不许手抄字段名 / 手搓合规形态。**

### 1.4 模型的行为是合理的

真实 sm21 识图产物的 window stroke id 就是 `S1`..`S12`（`1f_view.json` 17 strokes / 7 window）。
模型把能看到的 observation id（`S11` 等）填进 `source_ids` —— **它用唯一能引用真实源的方式在引用真实源。**
错在消费者要的是模型给不出的东西，且没有代码层做映射。

### 1.5 ⛔ 已被排除的两条路（不要再走）

- **⛔ 「残留产物被消费」**：`correction_geometry.json`（`pipeline.py:679` 写）**无任何生产消费路径**读它；
  生产消费走 accepted attempt 归档。坏抽签也不可能成为 accepted（`_claim_links` 跑在 finalize/gate① 之前）。**已排除。**
- **⛔ 「走 F-4/F-6 的重试回灌通道」**：`FieldProvenance.source_ids: list[str]`（`correction/schema.py:125`）**无格式约束**
  ⇒ `['S11']` 过 pydantic ⇒ 不产 `ValidationError` ⇒ 而 `vocab.py:retry_guidance_for_correction` 只接
  `ValidationError`（`if not isinstance(exc, ValidationError): return None`）⇒ **通道永不开启**。**结构上行不通。**

---

## 2. 修法（用户 2026-08-05 已拍板：代码侧翻译）

**⭐ 契约语义变更（用户已认）**：`FieldProvenance.source_ids` 的语义
从「locator」改为「**模型看得见的观测引用**」。
locator 仍是内部唯一标识，**`_claim_links` 的严格校验一个字不放宽** —— 只是在它之前多一步确定性翻译。

**⛔ 明确否决的另一条路**：把算好的 64 位 locator 清单注入 prompt 让模型誊抄。
理由：抄长哈希脆，且 `output_sha256` 每 run 变、prompt 不可缓存。**不要做这条。**

### 2.1 引用形态定为 `<expected_output_id>/<observation_id>`

例：`1f_view/S11`。

- **为什么必须带图名**：观测编号**跨视图会重名**（`1f_view` 与 `2f_view` 都有 `S1`）。
- **模型看得见图名**：`_build_correction_messages` 已经按
  `f"\n[reading vector] {fname}:\n```json\n...\n```\n"` 逐个投喂识图 JSON（`pipeline.py:428`）。
- **等式已核**：`view_manifest.py:78 _family_expected_output_id` ⇒ `expected_output_id` 是
  `input_id` 或 `f"{input_id}_view"`；实际产物文件名就是 `1f_view.json` / `North_view.json` 等
  ⇒ **文件名去掉 `.json` == `expected_output_id`**。
  **请你自己再核一遍这条等式在 `RequiredViewEntry` 上真的成立**（`view_manifest.py:412`），不成立就停下上报。
- **⛔ 不接受裸 `S11` 让代码去猜哪张图**：歧义必须报错，**不许静默择一**。

### 2.2 翻译层

在 `_claim_links` 之前，把 `source_ids` 里的观测引用翻译成 locator。

- **映射表由 `_catalog(...)`（`window_sources.py:305`）已经建好的 rows 直接导出** ——
  每行 `SourceWindowV1` 都带 `source_input_id` + `observation_id` + `source_locator`。
  **⛔ 不许新建第二份词表、不许重算一遍 locator。**
- **向后兼容**：已经是合法 locator 的原样放行（B5 现有夹具与任何存量产物不受影响）。**这条要有锁。**
- 翻译不到（图名不存在 / 编号不存在 / 歧义）⇒ 抛**具名错误**，走 §2.4 的分类。

### 2.3 合法引用清单注入 prompt（机械导出）

- 从**同一个 `_catalog` 出口**导出「图名/编号 + 该来源允许声明哪些 claim」的人类可读清单，注入 correction prompt。
  （`build_window_source_offer` 已经在算 `allowed_claims_by_locator`，可复用它的算法出口 —— 但**输出换成观测引用形态**。）
- **⛔ 清单里不得出现 locator 的 64 位十六进制串**（模型不该见、也不该抄）。
- **⛔ 不许手抄字段名、不许手写第二份清单。**
- `_build_correction_messages` 需要新增入参才拿得到 manifest/readings —— **改签名可以，但调用点全找齐（含测试），
  ⛔ 不许留旧签名的静默回退分支**（静默回退 = 这条修法在真实路径上不生效，正是本项目反复栽的形状）。

### 2.4 失败口径（用户 2026-08-05 已拍板：分两类）

**现状**：`_claim_links` raise ⇒ `step_orchestrator.py:251` 的 `out, report = draw_fn(None)`
**异常直接穿出、硬崩 flow**，不归档为失败 attempt、不盲重抽。
对照 `correction_draw_issues`（`scripts/tool_scripts/run_stage.py:355`）返回 `CheckReport` ⇒ 归档重抽。

**定的口径**：

| 错因 | 处理 |
|---|---|
| **模型抽签写错**（引用编号不存在 / 歧义 / claim 与来源不匹配 / existence 缺失 / claim 权限不符 …）= 产出方的错 | **归档成一次失败 attempt + 盲重抽**，与 `correction_draw_issues` 一致 |
| **识图产物本身对不上**（artifact/manifest 哈希不符、`duplicate_source_*`、方向事实无效、目录与 manifest 集合不等 …）= 输入完整性的错 | **保持硬崩**，不重抽（重抽没用，且会掩盖真问题）|

- **⛔ 分类必须落在错误类型上，不许靠字符串匹配错误消息判类。**
  建议给 `WindowResolverInputError` 加一个显式类别字段（或分出子类），**由抛出点决定** ——
  抛出点是唯一知道「谁的错」的地方。
- **⛔ 归档重抽那一类不许静默吞掉**：失败 attempt 要落盘、要能在 manifest 里看到重抽了几次。
- 逐个抛出点都要归类，**⛔ 不许用「默认归到某一类」兜底** —— 兜底等于没分类。

---

## 3. 验收（缺一不可）

### 3.1 锁

- **翻译层**：观测引用 → 正确 locator（正例）；图名不存在 / 编号不存在 / 跨视图歧义 三格分别报**各自的具名错误**；
  已是合法 locator 的原样放行（向后兼容那格）。
- **prompt 清单**：断言注入的清单**恰好等于 `_catalog` 出口导出的集合**（机械一致，不是「包含若干项」）；
  断言清单里**不含** `src:` 前缀 / 64 位十六进制串。
- **失败分类两格**：模型错那格 ⇒ **归档 + 重抽且 attempt 计数真的涨**；产物错那格 ⇒ **仍然崩**。

**⭐ 判据纪律（本项目 08-04 最贵的教训，两次栽在这上面）**：
> **neuter / mutation 变红只证明「实现被调用了」，不证明「判据有分辨力」。**
> 判据类检查必须**双向实测**（该红的红 + 该绿的绿），载荷用**真实量级 + 真实形状**，⛔ 不许用退化 fixture。
> **把双向 neuter 的 pytest 输出原样贴进执行日志。**

**⭐ 锁必须落在真实入口**：断言落到具体错误类别 / 具体 attempt 记录，
**⛔ 不许落在「不是 None」「总数变了」**（本项目出过两次「锁绿着缺陷还在」）。

### 3.2 ⭐ 真实产物跑通（最重要的一条，夹具自洽不算数）

用 **07-07 那份 sm21 识图产物**跑到 **1_correction 出 accepted attempt**：

```
case_tests/e2e_tests/sm21_anchor/run_2026-08-05_smoke_downstream_r2/
  0_reading/{1f_view,2f_view,East_view,North_view,South_view,West_view}.json
  0_reading/reading_summary.md
```

- **跑测一律 `exploratory` 档**（用户 08-05 定：「几个 gate 的门拦什么、几个档，C2 收官后一起过一下，**现在你确保不会拦端到端就行**」）。
- 走标准 SOP：`scripts/tool_scripts/run_stage.py` 的 `flow`，**⛔ 禁手搓、禁 `run_pipeline` 直连**
  （见 `AI_agent/guides/new_case_guide.md`）。跑一个**新的 run 目录**，不要污染上面那个。
- **这一步会真调 LLM**（correction 段）。若额度/网络失败，**停下上报**，不要伪造结果、不要改成 mock 通过。
- **这条是本单的核心验收**：F-5/F-7 这一族缺陷的定义就是「测试绿、真链路崩」，所以**只有真实产物跑通才算修好**。

### 3.3 全仓

`-n auto`，**⛔ 不加 `-m` 过滤**。基线 = HEAD `9fd8a9a` 的 **2193 绿 / 10 xfail / 0 红**。预期净增锁、零回归。

---

## 4. 提交与交回

- 在**你自己的 worktree 分支**上提交，message 仿 `08.05_f7_source_ids_observation_refs`，body 含 ①改动 ②为何此刻 ③影响。
- **⛔ 逐文件 `git add`，不许 `git add -A`**（本项目实犯过：`git add -A` 把并行席位的半成品扫进提交并推送）。
- **⛔ 不要 push、不要合回主分支** —— orchestrator 统一 merge。
- 执行日志落 `AI_agent/logs/reviews/execution/2026-08-05_f7_source_ids_sonnet.md`，含：
  状态（DONE / 停下上报 + 卡在哪）· diff 摘要 + 提交 SHA · **双向 neuter 的实跑输出** ·
  **§3.2 真实产物跑通的证据（accepted attempt 路径 + 那次 run 的目录）** · 全仓尾巴三个数。
- **做完一件存一件**，先落骨架再补（容器 OOM 会带走会话，本项目实犯过两次、同样的活白做两遍）。
