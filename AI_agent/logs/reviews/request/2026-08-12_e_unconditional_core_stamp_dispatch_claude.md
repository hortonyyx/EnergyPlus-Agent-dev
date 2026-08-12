# 施工单 · 摊 E — 修 F-22 **BLOCKER-1**：确定性核盖【无条件】印章 + 判卷验印

- **日期**：2026-08-12 · **席位**：Claude 侧 Sonnet · **审**：GPT 侧 sol（完工后派）
- **来源**：[sol 复审裁决书](../verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md) BLOCKER-1 **未关闭**，
  orchestrator 已独立复现。**用户 2026-08-12 已拍板修法（见 §2）。**
- **⛔ 并行席位**：另一席位（摊 C+D）**只动 `tests/`**。
  **你的文件所有权** = `src/agent/correction/deterministic.py` + `src/agent/correction/schema.py` +
  `src/agent/judge/correction_score.py` + 你自己新建/修改的测试。
  ⛔ **不要动 `tests/test_c2_b4b_phase_d.py`**（摊 D 的）。
  **⛔ 绝对不要执行 `git checkout` / `stash` / `clean` / `commit` / `reset`**（工作树里有别人的未提交改动）。

---

## 第 0 步（**先做这个**）· 防假验证自检

在你打算插入印章的位置写**一句必抛异常**，跑你打算用的验收命令，**确认它真的抛了**。
不抛 ⇒ 验收路径不经过那里 ⇒ **停下上报**。

> ⚠️ orchestrator 今天上午自己就栽在这一步的反面：写了个 neuter 探针，
> **BEFORE 就是 0 条结果**（用错了集合名 + 少传一个参数），差点据此误判「未接线」。
> **⇒ 你的每个探针都必须先自证「我看得见目标」，再去断言目标变没变。**

---

## 1. 缺陷（sol 抓、orchestrator 已独立复现）

判卷要判「这份产物的坐标量到墙外皮还是墙中线」（差 0.12 m）。
现在的判据 = `correction_score.py::_is_trusted_output_convention`，**只看 `schema_version == "3"`**。
源码注释自己写着 **"`schema_version` is used as the capability_profile proxy"** —— **这个 proxy 不成立**：

| run | `schema_version` | run_config `capability_profile` | 实际 footprint |
|---|---|---|---|
| `run_2026-08-09_f17_e2e_verify` | `3` | `orthogonal_polygon` | **`[0.12,14.88]` 中线框** |
| `run_2026-08-11_continuous_e2e` | `3` | `orthogonal_polygon` | **`[0,15]` 外皮框** |

**版本号一样、配置逐字一样，坐标框不同** —— 差别在**中间修好了 F-17**。
⇒ 08-09 那份今天被判 **五项全 `pass`**，而它每条外边实际差 0.12 m。

> ⭐ **修 bug 从来不改版本号 ⇒ 同一个版本号必然横跨修复前后。
> 版本号是「我是什么形状」的声明，不是「产生我的代码有没有那个 bug」的证明。**

---

## 2. ✅ 用户拍板的修法（照此施工，⛔ 不要自行改口径）

**让确定性核在产物上盖一个【无条件】的「我跑过、版本是 X」印章**，判卷改为**验这个印章**。

- **⛔ 不要历史白名单**（用户明确否掉）。
- **✅ 接受代价**：现有产物（含 `continuous_e2e`）都没有印章 ⇒ **会被拒判，需重跑一次才重新有分数**。
  **这是预期结果，不是缺陷。**
- **⛔ 不要加第二套换算分支**（换算开关仍归「标注/墙厚/出模」专项）。
- 拒判走**已有的 fail-closed 路径**（`boundary=None` + 空 wall segments + 追加 `unsupported_output_convention`
  证据 + provenance 进侧车），⛔ 不要新造一套拒判机制。

---

## 3. ⛔⛔ 一个必须避开的坑（orchestrator 已实测，**这是本单最重要的一段**）

**自然想法**：「看产物 `corrections[]` 里有没有 `deterministic_core.envelope_atomic_transform` 记录」
当作 post-transform 证据。**⛔ 这条不成立。**

`src/agent/correction/envelope_transform.py:586`：
```python
if not intents:
    return EnvelopeTransactionResult(before, False, None, (), None)   # ← 早返回，不留任何记录
```
⇒ **图纸本来就按外皮标注时，核什么都不用改 ⇒ 合法产物同样没有记录。**
**orchestrator 已逐个查过：今天所有 `deterministic_core.*` 记录全部是有条件的，一条无条件的都没有。**

> ⭐ **「没有记录」= 「没跑过核（不可信）」+「跑了但没事干（完全可信）」两件事被压成同一个空白。**
> **这正是印章必须【无条件】的原因** —— 它要证的是**「来过」**，不是「有事可做」。
> （这个毛病 2026-08-12 当天已在三个不同子系统各现形一次。）

⇒ **印章必须在确定性核的入口/出口无条件写下**，与「有没有实际修改」完全解耦。

---

## 4. ⚠️ 两个必须先查证再动手的风险（⛔ 不许假设，要实测）

1. **加字段会不会打坏既有哈希 / 批准链？**
   本项目吃过大亏：往内核报告加一行 ⇒ `geometry_checkpoint_digest`（`hash_obj(kernel_check_report)`）
   全变 ⇒ **所有历史几何批准一次性失效**（F-20）。
   ⇒ **动手前先查清 1_correction 产物的字节进了哪些哈希 / digest / cache 身份**，并在报告里列出来。
   查法建议：`grep -rn "sha256\|hash_obj\|content_sha256"` 顺着 correction 产物的消费口走一遍。
   **若发现会连带失效，停下上报，⛔ 不要自行决定「反正历史产物本来就要重跑」。**
2. **这个改动会让多少既有测试转红？**
   判卷开始拒判无印章产物 ⇒ 凡是拿真实/夹具产物评分的测试都可能变。
   ⇒ **如实报数字和清单。⛔ 绝不许靠放宽守卫把它们弄绿** —— 那就是把刚修的 BLOCKER 又打开。
   **当前基线 = 2515 passed / 10 xfailed / 0 failed。**

---

## 5. 锁（每把都要自证前提）

**必须有的四把**（名字你定，语义不许少）：

| # | 锁 | 判据 |
|---|---|---|
| 1 | **pre-flip 真实产物被拒判** | 用 `run_2026-08-09_f17_e2e_verify` 那份真实产物 ⇒ 必须拒判。**先断言「修法前它确实被判成五项全 pass」**（自证前提）|
| 2 | **⭐ 零位移的合法产物仍被信任** | 构造/取一份「核跑过但什么都没改」的 v3 产物 ⇒ **必须信任**。这把锁专防 §3 那个坑。**造不出来请停下上报，⛔ 不许跳过这一格** |
| 3 | **无印章 ⇒ fail closed** | 印章缺失 / 字段为 `None` / 印章版本不认识 ⇒ 都必须拒判，**且拒判不能长得像「全对」** |
| 4 | **印章是承重的不是注释** | 把印章值改成 `bogus` ⇒ 判卷行为必须变（这是 sol 上一轮点名的自测判据）|

- **⛔ 恒等锁不算正确性锁**：不许只断言「字段非 None」「两边相等」。
- **⚠️ 遮蔽自查**：「我这个夹具里，有没有第二条防线会先于目标门把这个变异拦下？」
- **neuter 至少两个方向**，且**必须覆盖接线**：判据 = **把印章的产出中和掉，判卷跟不跟着变**。
  ⛔ **不许用 grep / AST 形状匹配判接线**（昨天正是这条把 orchestrator 带沟里：
  某函数用两次条件取反等价实现了同一个 XOR，形状匹配抓不到，而它并非死代码）。

---

## 6. ⛔ 硬纪律

1. **⛔ 派工方错误率 14/14** —— 本单里凡描述**岔口 / 分类 / 数量 / 位置**的句子
   （「所有 `deterministic_core.*` 都是有条件的」「`envelope_transform.py:586`」「只看 `schema_version`」），
   **都可能是错的前提**。**发现前提错请停下上报。**
   过去 14 次「停下上报」**全部**是派工方的题错了 —— **包括本单来源的这一条**（是 sol 停下上报抓出来的）。
2. 验锁 neuter **只在 `/tmp` 做**（可用 pytest 插件式 runtime monkeypatch，零源码改动），做完还原。
3. 跑测：交付前跑一次全仓，日志与退出码用**独立新文件名**，判跑完**看 `N passed` 汇总行**。
4. 改 `src/` 前先备份到 `backup/src_history/2026-08-12_f22_blocker1/`。

## 7. 输出

执行记录落 `AI_agent/logs/reviews/execution/2026-08-12_e_unconditional_core_stamp_claude.md`，含：
改了什么 / 四把锁各自绑什么 + 自证前提的实测 / **§4 两个风险的查证结果（哈希连带面 + 转红清单）** /
neuter 两个方向的结果 / 全仓汇总行 / **未验证项与不确定判断（如实列出）**。
