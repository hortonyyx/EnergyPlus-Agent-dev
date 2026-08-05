# 派工单 r3 · F-4：correction 的内层重试是**盲的**，一个系统性 schema 误解就能把整条链打死

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **施工席**：GLM-5.2（承接 `4a11097` → `fb78e74` 的同一席位）
- **基线**：工作树 @ `fb78e74`（上一单的三条已落库，待审阅席复验）

---

## 1. 现象（orchestrator 实跑，两次烟测各一次）

拿 07-07 那份**已知满分**的 sm21 识图产物跑全链路（`run_2026-08-05_smoke_downstream_r2`，
`--judge off --with-ep`），**0_reading 过了**（0 block / 6 flag / accepted），
然后 **1_correction 三次抽签全废、整条链当场死**：

```
attempt 1–2: windows.<N>.provenance
             Value error, window provenance keys must be opening-claim vocabulary
attempt 3  : north_axis.note
             Extra inputs are not permitted [type=extra_forbidden]
⇒ RuntimeError: correction: failed after 3 attempt(s)
```

⚠️ **同一份输入在几小时前的第一次烟测里 correction 一次就过**（产的是合法 v3）。
⇒ 这不是必崩，是**抽签方差**；但一旦模型形成系统性误解，现在的机制会**必然烧光预算然后把管线打死**。

## 2. 根因（已定位到行）

`src/agent/pipeline.py:236-282 _call_json_llm`：重试是**盲重试**——
校验失败后把错误写进 `*_parse_error.txt`，然后**原样再调一次同样的 messages**：

```python
except Exception as e:
    last_err = e
    ... (out_dir / f"{prefix}_parse_error.txt").write_text(...)   # 写盘
    if attempt < attempts:
        logger.warning("... rejected ({}); retrying", e)
        continue                                                   # ← 模型永远不知道错在哪
```

⇒ 模型若不知道 `north_axis` 禁止 extra key、或不知道 window provenance 的合法词表，
**三次都会犯同一个错**，然后 `RuntimeError` 冒到顶把 flow 打死。

**⚠️ 这不违反「重做 = 盲重抽」那条纪律**：那条管的是 **judge② 的评语不得回灌**。
这里是**同一次 draw 内部的 schema 校验器**，`run_stage.py:313` 的注释本来就写着
*"Inner retry handles ONLY schema/format robustness"* —— 只是**没实现**。
回灌的内容必须**严格限定为格式/词表**，⛔ 不得包含任何几何内容、gt、上游判语。

## 3. 要修（两条，都要）

### F-4a · 内层重试必须把**校验器的报错**带回给模型（格式类信息，仅此一类）

- 重试时在 messages 末尾追加一条**机器生成**的纠正消息，内容只允许来自：
  ① pydantic 的 `ValidationError` 文本（字段路径 + 错因）；② 该字段的**合法取值/词表**（从 schema 取，不是人写）。
- ⛔ 严禁把上游产物、testdata 之外的任何内容、或人工提示塞进去。
- ⛔ 严禁把「上一版模型输出的具体数值」当范例回灌（那会把一次坏抽签固化）。
- 该通道**只在 schema 校验失败时**开启；transport 错误（超时/断流）仍是原样盲重试。

### F-4b · 合法词表要在**第一次**就写进 prompt，而不是等它猜错

- `windows[].provenance` 的 opening-claim 词表、`north_axis` 的允许字段集，
  应由 schema **机械导出**后拼进 correction 的 system prompt（`_build_correction_messages`），
  ⛔ 不许在 prompt 里手抄一份（第二份词表 = 第二把尺子，本项目已犯过）。

## 4. 锁（同前两单标准）

1. **F-4a**：构造一次「第一抽违反 schema、第二抽合法」的场景（stub LLM），断言
   ① 第二次调用的 messages **确实多了那条纠正消息**且内容含字段路径；
   ② transport 错误路径**不**追加纠正消息（两格实测：schema 失败 vs 网络失败）。
2. **F-4b**：断言 system prompt 里的词表**与 schema 机械导出的集合逐元素相等**
   （⇒ schema 改了、prompt 自动跟着改；写死一份就红）。
3. **摘掉即红** + 自己跑 neuter，红了哪几条、有没有连带，原样写进简报。
4. 全仓三数字；基线以 `fb78e74` 的实测为准（上一单简报里的数字请自己复算一遍，别抄）。

## 5. 交付

- commit（`08.05_<英文标签>`，⛔ 不 push，⛔ 只 add 自己改的文件——工作树里有 orchestrator 的未跟踪 run 产物）；
- 简报 `AI_agent/logs/reviews/execution/2026-08-05_correction_blind_retry_glm_r3.md`（含 neuter 原始输出 + 诚实披露）。

## 6. 边界

- ⛔ 不碰识图侧、不碰 gt、不碰判卷语义、不放宽 `CorrectedGeometryV3` 的 schema
  （**修的是「怎么告诉模型」，不是「把门开大」**）。
- 有异议就停下上报。

---

## 7. ⭐ 追加证据（orchestrator 08-05 第三次实跑，**扩大了 F-4a 的覆盖面**）

同一份输入的第三次烟测，correction 又是 **3/3 全废**，但错的是**第三类**：

```
attempt 3/3: WindowResolverInputError: producer_segment_ref_prefilled: {}
（src/agent/correction/parse.py:87 — B5 producer draw 不许自己填 windows[].facade_segment_id）
```

**⇒ 三次实跑撞到三类不同的系统性误解**：
① `windows[].provenance` 词表不对（pydantic）· ② `north_axis.note` 多余键（pydantic）·
③ `facade_segment_id` 本不该由 producer 填（**不是 pydantic，是 `WindowResolverInputError`**）。

**因此 F-4a 的回灌通道必须覆盖两个校验族，不能只做 pydantic**：
- **pydantic `ValidationError`** ⇒ 字段路径 + 错因 + 该字段合法取值；
- **`WindowResolverInputError` / `ValueError` 这类带 symbolic code 的**（如
  `producer_segment_ref_prefilled` / `producer_resolver_audit_prefilled` / `correction draw schema_version …`）
  ⇒ **code 本身就是最好的回灌内容**，但现在它连 payload 都是空的 `{}`，
  模型只会看到一个自己看不懂的词 ⇒ **每个 code 要配一句机器可取的「这条规则是什么」**
  （建议：在抛出点旁维护 code→一句话说明的表，⛔ 不许在 prompt 里手抄第二份）。

⚠️ **已排除回归**：`parse.py` 未被 `fb78e74` 触碰（该提交只动 run_stage/isolation/stage_runner/pipeline 四处）。
这是本来就有的校验，只是以前没人连着跑三次撞见。
