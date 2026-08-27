# 派工单 · ①-2′ 第 2 步：签字输入落进 case-owned 持久路径（含 F-111 改写）

- **日期**：2026-08-27（夜后半场）
- **派工方**：orchestrator（Claude 主控）
- **施工席位**：待用户拍板
- **复核席位**：待用户拍板（**跨家族**，⛔ 与施工方不同厂商）
- **基线 commit**：主树最新 HEAD（父提交 `3e2b794`；该提交**只加了本单与实测档两份文档，`src/`/`tests/` 一行未动**）
- **⭐ 工作目录 = 主树 `/workspaces/EnergyPlus-Agent-dev`**（⛔ **不要另建 worktree**：
  共享 venv 的 editable `.pth` 硬编码主树，非主树里跑测会**静默串台**、产出假绿。这是已登记的债 D-2，本单不碰它）
- **⛔ 并行提醒**：orchestrator 同期在跑只读实验，**只写 `AI_agent/logs/experiments/2026-08-27c_*`**。
  你提交时**逐路径 `git add`，⛔ 不许 `git add -A`**（曾扫走过并行席位的半成品）
- **档位**：**工程档**（碰 `src/agent/judge/`，属成绩产出路径）⇒ gate① + 全量绿 + 跨家族审

---

## 〇、⛔ 先读：**这张单的题面是被改写过的，原始登记 F-111 的前提已被实测推翻**

**实测档 → [`../../experiments/2026-08-27b_signed_request_recovery/README.md`](../../experiments/2026-08-27b_signed_request_recovery/README.md)**

| F-111 原文这么写 | 实测 |
|---|---|
| 「sm24 的签字 request **已不可寻**」 | ⛔ **错**。它在 `tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json`，**内容重算逐位命中** `ae0fec08…` |
| 「`logs/experiments` 是它**唯一栖身处**」 | ⛔ **错**。真件从来不在那儿；同目录还有配套 `manifest.json` |
| 「复现门可用面 = 2 份里的 1 份」 | ✅ **这个读数对**，但**归因错** |

⇒ **本单的真问题不是「归档丢了」，是两件事**：
1. **门的查找面窄在两处**：搜索根写死 `AI_agent/logs/experiments`（[`gt_raw_layer.py:267`](../../../../src/agent/judge/gt_raw_layer.py#L267)）
   + 文件名必须字面是 `request.json`（[`gt_raw_layer.py:296`](../../../../src/agent/judge/gt_raw_layer.py#L296)）。
2. ⭐⭐ **信任根被放在了项目自己声明为「过程痕迹、可清理」的目录里**（`logs/README.md`）。
   —— 这才是承重的那一半：**它今天没丢，但它躺在一个随时可以被合法删掉的地方。**
   ⭐ 注意 **sm25 同样中招**：它的签字 request 现在有 3 份副本，**全部在 `logs/experiments/` 下**。
   ⇒ 这不是 sm24 的个案，是**全部 case 共有的结构性风险**。

---

## 一、目标（一句话）

> **让复现门的签字输入住在 case 自己的持久路径里，并让门去那里找 —— 而「凭什么认它」这一条一个字都不许改。**

---

## 二、⛔ 三条不许动的红线

1. ⛔ **位置永远不承权。** 现行 `find_signed_request` 的注释写得很清楚：
   `The declared request_sha256 field is never trusted: it is recomputed from the request body`
   ⇒ **本单改的是「去哪儿找」，⛔ 不是「凭什么认」。** 任何把「在正确目录里」当作信任依据的改法**直接判 REJECT**。
2. ⛔ **fail-closed 行为不许弱化。** 找不到 ⇒ 仍必须是响亮的 `inputs_unavailable`，⛔ 不许退化成跳过、警告、或默认信任盘上件。
3. ⛔ **不许为了让门变绿去动指纹**（见 §四的预期读数）。

---

## 三、要做的事

### 3.1 定一个 case-owned 持久路径，并把真件放进去

**现状**（实测，供你判断，⛔ 不是给你的封闭选项表）：

| 路径 | 现在放着什么 | 是否已被门当作权威来源 |
|---|---|---|
| `case_tests/test_baseline/gt_sources/<case>/` | sm24：`source.dxf`+`normalized.dxf`+`manifest.json`+`source_map.json`+`conversion_report.json`；**sm25：只有两份 DXF**；sm21：只有 `source.dxf` | ✅ **DXF 已经从这里按内容哈希解析**（`GT_SOURCES_ROOT / case`）|
| `case_tests/test_baseline/gt/<case>/review/` | `review_ack.json` / `review_index.json` / `conversion_report.json` / 审阅标注 | ✅ 已是签字材料的家 |
| `tests/fixtures/sm24_review/bundle_07_25/` | ⭐ **sm24 的真 request + manifest** | ❌ 门看不到；且**测试夹具目录当信任根 = 与 logs 同病** |
| `AI_agent/logs/experiments/**` | sm25 的真 request ×3 | ⚠️ 门只看这里，**而这里声明可清理** |

⭐ **⛔ 上面不是「二选一」** —— 按 [[dispatch-options-list-is-itself-a-hidden-premise]]，
**如果你认为存在比这些都好的第三条路，走它并说明理由**。
一个已经想到、但**我没有验证过**的方向，供你证伪或采纳：
> **让「晋升/签字」这个动作本身就把 request+manifest 拷进答案树**，
> 于是未来的 case 结构上不可能再出现这个问题，现存两份 case 做一次性回填。
> —— 这可能超出本单工期；**若你判断它更对但更大，请停下上报**（见 §五）。

**必做**：无论选哪条路，**放进去的必须是经内容重算验证过的真件**，
⛔ 不许拷一份"看起来像"的（sm24 同目录另有两份 request 重算成 `35d8228c…` / `de20e741…`，**都不是**）。

### 3.2 把门的查找面改到那个路径

- 搜索面必须覆盖新的 case-owned 路径；
- **文件名约束要一并解决**（真件叫 `request_v3_calibrated.json`）——
  ⛔ 但请不要用"把 glob 放宽到 `*.json` 然后逐个试解析"来糊弄它，
  除非你能说明这在**大目录 + 畸形文件**下的代价（同族已知坑：F-112/F-113/F-114 那一串边界形态）。
- ⭐ **保留原搜索根还是移除它，由你判断并给理由**（保留 = 向后兼容但信任根仍有一条腿在可清理目录；
  移除 = 干净但可能让某些历史流程失效）。**两种我都接受，⛔ 但必须显式说你选了哪个、为什么。**

### 3.3 锁（⛔ 只锁契约与已咬过人的坑，见 CLAUDE.md §0.4#4）

至少要有**能变红**的锁，且每把都要能回答「不加这处改动，这门本来红不红」：

1. **真件在 case-owned 路径里 ⇒ 门找得到**（sm24 从 `inputs_unavailable` 脱离）。
2. **内容被改一个字节 ⇒ 门仍然拒绝**（证明位置没有变成权威）。
3. **真件不存在 ⇒ 仍然响亮 `inputs_unavailable`**，⛔ 不假绿。
4. ⭐ **同形输入验证**：放一份**哈希不匹配但文件名/位置全对**的 request 进去 ⇒ 必须被拒。
   （这条是本项目 08-27 固化的第三格判据的同形应用。）

---

## 四、⭐⭐ 预期读数（**先写在这里，⛔ 判据不许写成"跑绿"**）

| case | 改之前（今天实测）| 改之后**应当**是 |
|---|---|---|
| **sm25-L_anchor** | ✅ `reproduced` | ✅ **仍然 `reproduced`**（⛔ 本单不许让它退化）|
| **sm24_anchor** | ⛔ `inputs_unavailable` | ⚠️ **`implementation_drift`** —— ⭐ **这就是通过** |

**⛔ sm24 改完不会是绿的，这是预期不是失败。** 原因已实测：

| fatal 指纹 | 记录 | 当前 HEAD |
|---|---|---|
| `converter_sha256` | `37aa5f5020b27db1…` | `539615abee77a636…` ⛔ |
| `vg_implementation_sha256` | `60cab9e6d61d93a4…` | `8e45fd15b4dfbae0…` ⛔ |

它要变绿需要**用户重签 sm24**（08-20 已允诺、尚未做），那是**人的动作，不在本单范围内**。
⭐ 而且当年已实测**答案内容逐字段一致 ⇒ 历史成绩仍可信**。
⇒ 本单的成果是把 sm24 的红**从「资料没了」换成「树动了」** —— 后者是诚实且信息量更高的红。

---

## 五、⭐⭐ 停下上报触发器（**分层**，2026-08-27 固化口径）

**⛔ 承重前提错 ⇒ 立刻停下上报，别自行绕路：**
- 你复现不出 §〇 的任何一条（比如那份 request 在你手上**重算不出** `ae0fec08…`）；
- 你判断 3.1 的正确解在本单范围之外（例如必须改晋升流程）；
- 你发现「位置不承权」这条红线与要求做的事**存在真实冲突**；
- 本单的做法会让 **sm25 从 `reproduced` 掉下来**。

**外围数值/细节错 ⇒ 只记一行、继续做，⛔ 别为它停**：
- 我引用的行号、字节数、哈希前缀有出入；
- 某个文件的确切内容与我描述的略有不同；
- 你认为某把锁的措辞更好。

⭐ **累计 38/38 次「停下上报」全部是派工方（我）的题错** ⇒ 你觉得题面不对，**大概率是你对**。
且**本轮你没有维持与我一致的义务**。

---

## 六、交付面

1. 一个 commit（message 仿 `<月.日>_<英文标签>`），**diff 自解释**；
2. 主树**全量绿**（⚠️ 若同机有别的席位在跑，用 `-n 6`，⛔ 不用 `-n auto`）；
   ⛔ **绝对不许跑 `pip install -e .` 或任何写 `site-packages` 的命令**（venv 全机器共享，08-27 已因此作废过一轮权威读数）；
3. 跑测前后各记一次 `sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth`，**两次相同才算数**；
4. 两份 case 的复现门读数（对照 §四）；
5. 你对 3.1 / 3.2 两处**自由裁量**的选择与理由；
6. 一份「我最可能塌在哪」的自陈（供复核方当靶子）。
