# 派工单（GLM 席位）· F-2c + F-7 返工 r1 —— sol 对抗审 REWORK 的四条 MAJOR

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2，**主工作树** `/workspaces/EnergyPlus-Agent-dev`（分支 `6.15_ValidationArchM0toM4`）
- **上游**：[sol 对抗审](../verdict/2026-08-05_f2c_f7_crossreview_sol.md) = **REWORK（1 BLOCKER / 4 MAJOR）**
- **⚠️ 并行席位**：另有一个 Claude 侧席位在**独立 worktree** `.claude/worktrees/f7-manual` 做 F-9 只读调查。
  **⛔ 你不进那个目录。⛔ 提交时逐文件 `git add`，不许 `git add -A`。**

> **⚠️ 派工方自述**：本轮我已出错七次，且**这次审阅证伪了我自己的一条结论**（详 §0.2）。
> **本单里凡是与代码实情不符的地方，一律停下上报，不要硬做。**
> 本轮六次「停下上报」六次都是我的题错了 —— 在本项目这是记功不是记过。

---

## 0. 先读懂两件事

### 0.1 sol 的审阅有一个必须计入的限制

sol 侧容器沙箱坏了（`bwrap: No permissions to create a new namespace`）⇒
**它的定向 pytest 一条都没跑起来** ⇒ **五条结论全部建立在读码之上，不是实测**。

- **MAJOR ①②③ orchestrator 已独立核实属实**（下方各条注明了核实方式）；
- **MAJOR ④ 未经任何人实测** ⇒ **本单要求你先实测再决定改法**（见 §4）。

### 0.2 ⭐⭐ 本次审阅最贵的一条：一条新纪律（直接决定 §1 怎么做）

orchestrator 在轻门里做了三格 neuter（禁用翻译 / 一律判模型错 / 一律判输入错），
每格恰好红它自己那条锁，据此下了结论「分类判据双向分辨力已验证」。**sol 证伪了这条结论的泛化范围。**

> **我验证的是「分类机制有分辨力」，不是「每个抛出点的归类是对的」。**
> 两者之间还隔着约 40 个抛出点，**一个都没审**。

**⇒ 本项目 08-04 教训又长一层，本单起生效**：
- 旧版：**neuter 变红只证明「实现被调用了」，不证明「判据有分辨力」。**
- **新增：分辨力实测只证明「机制能分辨」，不证明「每个抛出点分得对」。**
  **⇒ 凡「由抛出点自行归类」的设计，必须逐点审计归类正确性；机制级 neuter 不能替代。**

---

## 1. MAJOR ② —— 逐点审计全部 `category` 归类（⭐ 本单最重要，先做）

**sol 给的反例（orchestrator 已核实属实）**：`src/agent/correction/window_sources.py` 的 `_check_floor_order` 首行

```python
if refs != list(range(1, len(refs) + 1)) or len(refs) != len(producer.floors):
    raise WindowResolverInputError("manifest_floor_ref_non_contiguous", category="input_integrity_error")
```

`producer.floors` **是模型的输出**。模型少写/多写一层 ⇒ 归成 `input_integrity_error` ⇒ **硬崩、不归档、不重抽**。
而这是最典型的「模型抽签写错」。

**要做的**：

1. **逐点审计** `window_sources.py`（约 40 处）+ `finalize.py`（2 处）+ `parse.py`（2 处，另见 §3）
   的**每一个** `raise WindowResolverInputError(...)`，判定其 `category` 是否正确。
   **判据 = 这个条件是由「模型这次抽签写的内容」决定的，还是由「上游产物/manifest/哈希」决定的。**
   ⚠️ 注意**复合条件**：像上面那行 `A or B`，A 是上游、B 是模型 ⇒ **必须拆开**，各归各的。
2. **产出一张审计表**（写进执行日志）：抛出点行号 · 触发条件的决定方 · 原 category · 判定 · 是否改。
3. **修掉所有归错的**。
4. **⛔ 不许「统一改成某一类」了事**；**⛔ 不许靠字符串匹配错误消息判类**（分类必须留在抛出点）。

**锁**：至少给「模型输出楼层数不符」这一格加一条锁，断言它**被归档为失败 attempt 并重抽**（不是硬崩）。
**⭐ 锁必须落在真实入口**：断言落到具体错误类别 / 具体 attempt 记录，⛔ 不许落在「不是 None」「总数变了」。

---

## 2. MAJOR ① —— catalog 静默回退升为前置条件

`build_observation_reference_catalog_from_run`（`window_sources.py:489`）在 view manifest 或任一识图产物
不在盘上时**返回 `None`**（清单不注入 prompt）。docstring 自陈「advisory only，执法侧独立重算，
缺清单只削弱引导、不削弱契约」。

**该辩解在正确性上成立，但可用性上不成立**（orchestrator 请求书 §6 主动请 sol 打的就是这条，sol 判定成立）：
清单缺失 ⇒ 模型无引导 ⇒ 必然填错 ⇒ 归档重抽 ⇒ **空转烧完重抽预算，且报错看不出真因**
—— 与本批 F-3/F-4 栽过的「静默降级 → 两段之后炸 → 报一句看不懂的话」同型。

**要做的**：**v3 目标（`schema_version == "3"`）下，清单不可导出 ⇒ 明确失败**，
错误信息要指名道姓说清缺哪个文件、该由哪一段产出。**非 v3 路径行为不变。**

**锁**：缺 manifest / 缺某张识图产物 各一格 ⇒ 明确失败且错误信息含缺失路径；齐全那格 ⇒ 正常注入。

---

## 3. MAJOR ③ —— `parse.py` 两处分类标注是**死的**

`src/agent/correction/parse.py:87/91` 的
`WindowResolverInputError("producer_segment_ref_prefilled" / "producer_resolver_audit_prefilled", category="model_draw_error")`
**永远到不了** `run_stage.py:411/422` 的分类分流。

**orchestrator 已核实的路径**：`parse_correction_draw` 只被 `_schema_only_correction_validator`（`pipeline.py:587`）
与 `_make_correction_validator`（`:611`）调用，二者都是喂给 `_call_json_llm` 的 validator
⇒ 异常被内层重试循环吞掉 ⇒ 最终包成 `RuntimeError(f"{prefix}: failed after N attempt(s)")`。

**要做的（orchestrator 倾向 (b)，但先看你的判断）**：

- **(a)** 让分类可达：使 `WindowResolverInputError` 穿透 validator 到外层。
  **风险**：会绕过内层重试，改变既有重试语义 —— 需评估是否与 F-4 冲突。
- **(b)** **承认内层重试就是这两处的归宿**：删掉那两处 `category` 标注所暗示的「会被外层分类」预期，
  改成明确注释说明它走内层盲重试通道；**并评估**：内层重试耗尽后包成 `RuntimeError` 硬崩，
  是否也该归档为失败 attempt（若是，这是另一条口径，**停下上报请裁，不要自行扩大范围**）。

**⛔ 不许保留现状的死标注** —— 死标注比没有标注更坏（它让人以为分类覆盖到了）。

**锁**：无论选哪条，都要有一条锁**钉住实际路径**（而不是钉住意图），
使得「以后谁把它改回死标注」必红。

---

## 4. MAJOR ④ —— F-2c 镜像：**先实测，再决定改法**

sol 读码判断（**无人实测**）：
> F-2c mirror 写入未处理 stage root 的**陈旧 `*_view.json`**，且 **accepted pointer 先于 mirrors 落盘**；
> 干净 tmp fixture 掩盖了真实前态下的"先接受、下一段再崩"。

**要做的**：

1. **先构造真实前态实测**：stage root **已经存在**一批陈旧/多余的 `*_view.json`（例如上一轮留下的、
   或比 accepted 多一张），再跑隔离 merge，看会发生什么。
   **⛔ 不许用干净 tmp fixture 下结论** —— sol 指的正是这一点。
2. **再核落盘次序**：`merge_isolated_output` 里 `save_run_manifest`（写 accepted 指针）与写 mirrors 的先后，
   以及中途失败会留下什么状态。
3. **实测结果决定改法**：若 sol 说的成立 ⇒ 修（例如先写 mirrors 再落 accepted 指针 / merge 前清理 stage root
   的陈旧 `*_view.json`，**清理范围要保守、要有锁**）；**若不成立 ⇒ 明确写「sol 的 MAJOR ④ 不成立，证据是……」**。
   **推翻它和修好它一样有价值。**

---

## 5. BLOCKER —— 不在本单范围

sol 的 BLOCKER =「真实 sm21 `1_correction` accepted attempt 未产生」。
**事实属实**（orchestrator 轻门 §5 已自认），但其直接原因是**下一道墙 F-9**
（`resolve_window_hosts` 拒收），**不是这两批的实现错**。F-9 的只读调查已另派席位并行进行。

⇒ **本单 ⛔ 不碰 F-9、⛔ 不改口径绕过这个 BLOCKER**；它作为**出口条件继续持有**，随 F-9 一并解。

---

## 6. 验收与交回

1. **全仓一次**（`-n auto`，**⛔ 不加 `-m` 过滤**）。基线 = HEAD `ca5e26c` 的 **2212 绿 / 10 xfail / 0 红**。
   ⚠️ **必须在主工作树跑**：干净检出会因 **F-8**（`.gitignore` 挡掉 619 个含测试活输入的文件）红 5 条，
   那 5 条与本单无关。
2. **每条新锁双向 neuter 实测**，输出原样贴进执行日志。
   **⭐ 复读 §0.2 的新纪律**：机制级 neuter **不能**替代逐点审计。
3. **提交粒度**：§1 一个提交、§2+§3 一个提交、§4 一个提交（若 §4 判定不成立则只交调查结论）。
   **⛔ 逐文件 `git add`，不许 `git add -A`。⛔ 不要 push。**
4. 执行日志落 `AI_agent/logs/reviews/execution/2026-08-05_f2c_f7_rework_r1_glm.md`，含：
   状态 · **§1 的逐点审计表** · 各条 diff 摘要 + 落库 SHA · **双向 neuter 实跑输出** ·
   **§4 的实测证据（含推翻 sol 的情形）** · 全仓尾巴三个数。
5. **做完一件存一件**，先落骨架再补（容器 OOM 会带走会话，本项目实犯过两次）。
