# 2026-08-27（夜后半场）· 签字 request 找回 + 复现门可用面实测

> **归属**：①-2′「裁判事实包垂直切片」**第 1 步**（还原并核对签字 candidate）+ **第 2 步的前提核实**。
> **执行**：orchestrator 亲手（只读探针，⛔ 未改任何仓库文件；下面每条都是实跑读数，不是推断）。
> **为什么先做这一步**：第 2 步要派工改 `src/agent/judge/`，而它的题面直接抄自 **F-111**。
> 按硬纪律「派工单里的分类句要当【可能错的前提】写」+ [[stop-and-report-catches-dispatcher-errors]]，**先核前提**。
> 结果：**F-111 的前提两半都错**，若照原样发单就是第 39 次派工方题错。

---

## 一、⭐⭐⭐ 结论：F-111「sm24 的签字 request 已不可寻」——**推翻**

**它一直都在**，而且逐位命中：

| | |
|---|---|
| 文件 | `tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json` |
| 内容重算 `request_sha256` | `ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2` |
| `review_ack.json` 里的签字值 | `ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2` |
| 判据 | ⭐ **内容重算**，即 `find_signed_request` 自己声明的唯一权威（"Location therefore carries no authority"）|

⇒ **它就是真件**，不是相似件。同目录还躺着 **`manifest.json`（17432 B）**——正是第 2 步要落盘的另一件。

### 门为什么找不到它：两处窄，**都在门这一侧**

`gt_raw_layer.py:294-302` 的 `find_signed_request`：

1. **搜索根** = `REPO_ROOT/AI_agent/logs/experiments`（`gt_raw_layer.py:267`）
   —— 而这个目录按 `logs/README.md` 的纪律**就是"过程痕迹、可清理"**。
   ⇒ **信任根被放在了一个项目自己声明为可丢弃的地方。**
2. **文件名** 必须字面是 `request.json`（`rglob("request.json")`）
   —— 真件叫 `request_v3_calibrated.json`。

⇒ **不是「归档没做」，是「门只往一个可丢弃的目录里、按一个固定文件名找」。**

---

## 二、⭐⭐ 找回 request **不足以**让 sm24 可用（这条决定派工范围）

只读探针（进程内替换 `find_signed_request`，仍只信内容重算；⛔ 未改仓库文件）：

```
sm24 在【request 可达】假设下 -> implementation_drift
moved fingerprints: converter_sha256, vg_implementation_sha256
```

| fatal 指纹 | 记录 | 当前 HEAD | |
|---|---|---|---|
| `converter_sha256` | `37aa5f5020b27db1…` | `539615abee77a636…` | ⛔ 漂移 |
| `judge_config_sha256` | `843466dde0623e15…` | 同 | ✅ |
| `vg_config_sha256` | `ad3aeeb910ebe41a…` | 同 | ✅ |
| `vg_implementation_sha256` | `60cab9e6d61d93a4…` | `8e45fd15b4dfbae0…` | ⛔ 漂移 |

⭐ **`vg_implementation_sha256` 这条与缺陷登记里早就写着的一条完全对上**
（「sm24 的 `vg_implementation_sha256` 记 `60cab9e6`，干净 HEAD 算出 `8e45fd15`」，
且当时已注明**答案内容实测逐字段一致 ⇒ 历史成绩仍可信**、**由用户重签**）。

⇒ **sm24 要真正回到「可用面」，需要两件、缺一不可**：
**(a) 门能找到那份 request**（代码，可派工）+ **(b) 用户重签 sm24**（人，08-20 已允诺，未做）。
⛔ **只做 (a) = 把 `inputs_unavailable` 换成 `implementation_drift`**，读数仍然不是绿的
—— 但那是**诚实且信息量更高**的红（说的是"树动了"，不是"资料没了"）。

---

## 三、今天的复现门读数（本批 ② 动手【之前】的基线）

| case | 状态 | 备注 |
|---|---|---|
| **sm25-L_anchor** | ✅ **`reproduced`** | 每个内容字段从签字 DXF + 签字 request 重新派生，**零 JSON 指针相异**；advisory 漂移 `extractor_sha256` |
| **sm24_anchor** | ⛔ **`inputs_unavailable`** | 报错逐字点名两处窄（搜索根 + 文件名）|
| sm21_anchor | —— | 无 `review/` 目录，本就不在复现门覆盖面内 |

⭐ **这份 sm25 绿是有时效的**：按 **F-110**，一体改一动 `correction/schema.py`，它就会转 `implementation_drift`。
⇒ **本表即「② 开工前最后一次两份都诚实」的基线读数**，之后再看到红先对照 F-110。

---

## 四、对派工的影响（写进派工单，⛔ 不要照抄 F-111 原文）

1. 题面从「**找回丢失的归档**」改成「**门的搜索面窄在两处，且信任根放在了声明可丢弃的目录**」。
2. 第 2 步的动作因此是**两件**：把真件（request + manifest）落进 **case-owned 持久路径**，
   **并把门的查找面改成认这个路径**。⛔ 只搬文件不改门 = 门照样找不到。
3. **⛔ 不许把「位置」变成权威** —— 现行设计（内容重算，位置不承权）是对的，**改的是去哪儿找，不是凭什么认**。
4. 必须在派工单里显式写明：**sm24 修完预期是 `implementation_drift` 而不是绿**，
   并把"重签"作为**用户动作**单列，⛔ 不许施工方为了让门变绿去动指纹。
   （同族 [[acceptance-bar-must-not-be-written-from-the-result]]：判据不能写成"跑绿"。）
5. F-111 的登记条目要改写：**可用面 1/2 这个读数对，归因错**。

---

## 五、复现方法（任何人可重跑，⛔ 不依赖本文）

```bash
# ① 找出哪份 request 是真件（全仓，含 tests/fixtures）
python - <<'PY'
import pathlib, sys; sys.path.insert(0,".")
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, compute_request_sha256
for c in sorted(pathlib.Path(".").rglob("request*.json")):
    if ".git" in c.parts: continue
    try: print(compute_request_sha256(TarchConversionRequestV1.model_validate_json(c.read_bytes()))[:16], c)
    except Exception: pass
PY

# ② 今天的复现门读数
python - <<'PY'
import sys; sys.path.insert(0,".")
from src.agent.judge.gt_raw_layer import verify_raw_layer_reproduction
for case in ("sm25-L_anchor","sm24_anchor"):
    print(case, verify_raw_layer_reproduction(case).status)
PY
```

**环境**：主树 `/workspaces/EnergyPlus-Agent-dev`，HEAD `3e2b794`，工作树干净；
editable `.pth` = `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`（指向主树，与 08-27 权威全量记录一致）。
