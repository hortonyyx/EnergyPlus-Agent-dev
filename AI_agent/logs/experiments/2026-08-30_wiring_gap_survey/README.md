# 走查：**as-drawn 产物到 correction 之间到底缺什么**（2026-08-30 · orchestrator 实测）

- **为什么做**：CLAUDE.md §2 banner ⑤ 的第 ④ 件；且 banner 自己点名
  「**本批目标的另一半仍未动，而且现在有数**」——本走查就是去把那个「有数」变成**逐格可指的**。
- **写法口径**：**目标态当主体、现状只作状态标记**，每格 ✅/🟡/❌ **且能指到 file:line**
  （记忆条 `write-docs-target-state-first-with-status-marks`）。
- **HEAD**：`8abd6e0` · 所有读数为本轮实测，⛔ 无一条转引。

---

## 一、⭐⭐⭐ 一句话结论

> **闸门只有一行，但闸门后面的五个模块一个都不存在。**
> ⇒ ⛔ **今天把那一行从 `KNOWN_NOT_CONSUMED` 改成消费，是【有害】的**，
> 因为它会让 as-drawn 产物以**未类型化的裸文本**被贴进 correction 的 prompt ——
> 那正是 **F-97** 修掉的那件事。**先造模块 2–6，再动那一行。**

---

## 二、目标态：一条 as-drawn 产物走到 correction 要经过的九步

| # | 目标态该有的东西 | 今天 | 出处（实测） |
|---|---|---|---|
| 1 | reading 产出 as-drawn v2 三层产物 | ✅ | `src/agent/reading/as_drawn/as_drawn_v2.py` `assemble()` |
| 2 | 产物有**生产者自己的类型** | ✅ 绿件 · 🟡 **未过审**（GLM 在飞）| `src/agent/reading/as_drawn/schema.py` `AsDrawnPlanV2`（②-2 模块 1，`bff77de`）|
| 3 | detector **按类型**认出它 | ✅ | `src/agent/reading/vector_contract.py` `_detect_as_drawn_plan`（模块 1 交付）|
| 4 | ⭐ **闸门**：它的 disposition 是「可被 correction 消费」 | ❌ | 同文件 `CONTRACTS`：`as_drawn_plan → KNOWN_NOT_CONSUMED`（下方 §三 实测表）|
| 5 | correction 侧的**证据契约类型**（模块 2）| ❌ **文件不存在** | 应在 `src/agent/correction/evidence_contract.py` |
| 6 | **legacy / as-drawn 双 adapter**（模块 3）| ❌ **文件不存在** | 应在 `src/agent/correction/evidence_adapters.py` |
| 7 | **wall_compiler**：ref resolve / 切段 / 中线·候选·厚度 IR（模块 4）| ❌ **文件不存在** | 应在 `src/agent/correction/wall_compiler.py` |
| 8 | **决定 packet 与 response**（模块 5）+ **决定执行器**（模块 6）| ❌ **两个文件都不存在** | 应在 `src/agent/correction/decision_{schema,executor}.py` |
| 9 | correction 的提示词**不再要求中线基准** | ❌ **逐字未动** | `src/agent/pipeline.py:367` `"world-frame, wall-centerline, ..."` · `:370` `"put every coordinate in one world frame at wall CENTERLINE"` |

**模块编号来自已过审的 ②-2 设计稿 §十**（`AI_agent/logs/reviews/verdict/2026-08-30_o22_evidence_contract_gpt_design.md:577-583`），
⭐ 其中 **模块 7 = 「as-drawn 指向新 adapter 的一行注册」** —— 正是上表第 4 行那道闸门。

实测（`ls src/agent/correction/`）：
```
❌ evidence_contract.py 不存在   ❌ evidence_adapters.py 不存在   ❌ wall_compiler.py 不存在
❌ decision_schema.py 不存在     ❌ decision_executor.py 不存在
```

---

## 三、⭐ 闸门的实测读数（第 4 行的证据）

```python
>>> from src.agent.reading.vector_contract import CONTRACTS
>>> for c in CONTRACTS: print(c.contract_id, '|', c.disposition.name)
reading_view_legacy    | CONSUME              ← ⭐ 全表【唯一】能进 correction 的
as_drawn_plan          | KNOWN_NOT_CONSUMED
as_drawn_plan_v0       | KNOWN_NOT_CONSUMED
as_drawn_elevation_v0  | KNOWN_NOT_CONSUMED
stage_check_report     | EXCLUDE
```
消费点：`src/agent/pipeline.py:424-427`
```python
vector_files = classify_vector_dir(vector_dir, discover_vector_files(vector_dir)).consumed
...
chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
```
⇒ **`.consumed` 里今天只可能有 legacy `*_view.json`**；as-drawn 产物**连 prompt 都进不去**。

⭐ **这一格是 🟡 还是 ❌，要分清缺的是「接线」还是「产物」**：
**缺的是产物（模块 2–6），不是接线** —— 接线只是那一行 disposition。

---

## 四、⭐⭐ 本批投入的账（`git diff --numstat $(git merge-base main HEAD)..HEAD`）

| 面 | 增/删 | 文件数 |
|---|---|---|
| `src/agent/judge` | **+6629 / −142** | 16 |
| `src/agent/reading` | +950 / −4 | 3 |
| **`src/agent/correction`** | **+129 / −0** | **2** |

⇒ ⭐⭐⭐ **correction 侧【零删除】** —— 本批口径要求「改吃多形态墙证据 + 改掉 `wall-centerline`」，
**零删除意味着一句旧口径都没被换掉**。且 banner 已核：那 129 行里 117 行是 **F-133** 一个不相干的修复。

---

## 五、⭐⭐⭐ 目标态里**还悬着、要拍板的三件**（本文的高潮章）

> ⛔ 这一节不是「现状差距」（那在 §二 已经逐格标完），
> 而是**即使把模块 2–6 全造出来，也仍然没人签过字的三件**。

### 悬案 ① · **旧腿留多久，谁保证两条腿不各自漂移**
设计稿要的是**双 adapter**（模块 3）⇒ **legacy 与 as-drawn 长期并存**。
⚠️ 本项目已有该形状的实犯：**F-130** = 「reading 现算 / correction 冻盘 ⇒ 一改转换器只有一边动」。
⇒ **要拍的**：双腿并存期间，**有没有一道门要求「同一份图走两条腿得到同一答案」**？
若没有，第二条腿就是下一个 F-130。（⛔ 派工方**不自己定**，因为这等于给本批加一道验收。）

### 悬案 ② · **`wall-centerline` 那两句删掉之后，prompt 换成什么**
指南已定死：⛔ **不许写转换层把两条面线塌成中线**（那是 reading 替 correction 做基准统一）；
中线**只允许在 correction 内部由代码派生**。
⇒ 但 `pipeline.py:367/370` 是**给模型看的自然语言**。**代码派生中线之后，那两句到底改成什么措辞**——
今天没有任何一份文档写了替换文本。⇒ **这是模块 4/5 的输入，不是它们的输出**，得先有人写。

### 悬案 ③ · ⭐ **本批的重心要不要显式从 judge 挪到 correction**
§四 的账是 **6629 : 129**。本批目标三件事里，「① 新分工 harness」「② 新分工判分」都在推进，
**「reading+correction 一体改」的 correction 那一半零删除**。
⇒ **要拍的**：下一轮是**继续把 judge 侧的债清完**（F-149 外部锚 / F-151 / ②-1d 返工），
还是**先把模块 2–6 造出来**让本批目标的另一半真正开动？
⚠️ 派工方的判断（⛔ 只是判断，不是决定）：**F-149 有硬排期约束**
（「外部锚必须与『facts 进答案根』的任何动作同期落地」），**但它今天零真实流量**；
而模块 2–6 是**本批目标的字面内容**。⇒ 倾向**先造模块 2–6**，F-149 与「promote facts」绑在一起延后。

---

## 六、复现命令

```bash
python -c "from src.agent.reading.vector_contract import CONTRACTS; [print(c.contract_id,'|',c.disposition.name) for c in CONTRACTS]"
for f in evidence_contract evidence_adapters wall_compiler decision_schema decision_executor; do
  test -f src/agent/correction/$f.py && echo "✅ $f" || echo "❌ $f 不存在"; done
grep -n "wall-centerline\|wall CENTERLINE" src/agent/pipeline.py
B=$(git merge-base main HEAD); for d in correction judge reading; do
  git diff --numstat $B..HEAD -- src/agent/$d | awk -v d=$d '{a+=$1;s+=$2;n++} END{print d": +"a" -"s" files="n}'; done
```
