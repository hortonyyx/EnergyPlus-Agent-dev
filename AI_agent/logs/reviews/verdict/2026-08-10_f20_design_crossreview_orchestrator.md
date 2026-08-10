# orchestrator 对抗审 · F-20 修法设计稿（sol 出稿）· **第一轮**

- **日期**：2026-08-10 · **审阅人**：orchestrator（Opus，Claude 侧顶档）
- **被审对象**：[`proposals/f20_validate_case_v3_proof_design.md`](../../../proposals/f20_validate_case_v3_proof_design.md)（355 行，`gpt-5.6-sol` / effort max）
- **方向**：GPT 侧产物 → Claude 侧对抗审（与 08-09 F-9 那次**方向相反**，「谁写谁不批」照旧成立）
- **本轮裁决**：**初审通过（继续走）**，0 BLOCKER / 0 MAJOR。⚠️ **这是第一轮、未审满**，剩余项见 §4。

---

## 1. ⭐ 最重要的一条：设计稿抓到了**调查报告漏掉的第三种状态**，且该状态真实存在

调查报告（Claude 侧 Sonnet）把岔口描成 **「有账本 / 无账本」二分**，
并据此推荐「有账本 ⇒ 走 `load_verified_accepted_correction`」。

**设计稿指出这是错的**：账本本身有 **V1 / V2 两种 wire**（`b14af01`，07-11，
「StageRecord V1·V2 wire 分立…v1 run 拒新」），V1 是 **grandfathered legacy**。

**orchestrator 独立复核 —— 命题成立，且代价是真的**：

```
盘上 run_manifest.json 的 manifest_version 分布：
    V1 : 11 份
    V2 : 22 份
```

而 `load_verified_accepted_correction` 的**第一件事**（`output_coordinates.py:380`）就是：

```python
raise ValueError("output-coordinate contract requires a RunManifestV2 (v1 runs are legacy-only)")
```

**⇒ 若按调查报告的二分法施工，这 11 个 V1 run 目录会当场抛异常** ——
它们今天是能被审的（走 stage-root 离线审计面），改完就废了。
**这是一条 MAJOR 级的漏检，由跨家族出稿这一步抓出来。**

⭐ **方法论兑现**：这正是「谁写谁不批」要防的东西 —— 调查方与轻门方（orchestrator）都是 Claude 侧，
两轮都没看出「账本存在」不是一个二值事实。**与 08-09 sol 抓 orchestrator 的那次同型，只是方向反过来了。**

---

## 2. 已独立复核成立的其它命题

| # | 命题 | 复核 |
|---|---|---|
| ① | `06d01a0` 讲的是 approval digest 不得绑陈旧字节，**没有禁止读 accepted attempt** | ✅ 与 orchestrator 08-10 轻门的独立结论一致 |
| ② | `963d952` 管的是输出文件名，不管输入来源 | ✅ 同上 |
| ③ | `2885a84`：v3 无条件要求 proof，且 legacy **明确禁止**接收 proof | ✅ `build.py:207-210` 两条 raise 俱在 |
| ④ | 三个消费口都要接凭证（`check_correction` / `build_geometry` / `check_kernel`） | ✅ 三处签名均有 `window_host_proof` 参数（`checks/correction.py:92`、`build.py:204`、`checks/kernel.py:63`） |

**⭐ 设计稿做到了请求书 §5#3 那道功课**：它没有删除或推翻任何现存标记／注释／镜像机制，
而是逐条列出 8 个提交的原文用途（含调查报告没查的 `b14af01` / `bac689b` / `e645d63` / `15ea05d`）。
**这正是 F-9 设计稿 BLOCKER-3 的反面样板。**

---

## 3. 设计上明确赞同的三处

1. **fail-closed 贯彻到底**：V2 分支一旦开始，**任何**失败都不得回退 stage-root
   （逐字写了「不得 `except: use snapped`、不得把 proof 置空后继续」）——
   与 08-08 刚翻正的两处 fail-open 同纪律。
2. **`FAIL` 与 `ERROR` 分层**：磁盘载荷触发的可预期拒绝记 `FAIL`，
   权限/IO/检查器自身未知异常记 `ERROR`，两者在 INVARIANT 层都 BLOCK。
   ⇒ 回答了 Q4「现在的 `except Exception` 把根因藏住」那条。
3. **新增独立 check_id `correction.accepted_artifact_trust`**，
   不再让结构性取证失败伪装成 `kernel build failed`。

---

## 4. ⚠️ 本轮**未审**的部分（如实登记，⛔ 不得当成已通过）

**本轮只审了 §0–§2.2 与契约考古，以及上面那条 V1/V2 命题。以下未审：**

1. **§4 的 8 把锁**（L1–L8）逐把是否真绑、夹具怎么来、自证前提怎么写 —— **完全未审**。
   ⚠️ 这是本项目历次交叉审抓 MAJOR 最集中的地方（08-09 sol 抓的就是「headline 锁根本不是锁」）。
2. **§3 改动清单**是否与 §2.2 的状态表逐行对得上 —— 未逐行对账。
3. **§2.5**（`--intake-from` / `DOWNSTREAM_ONLY`）与 **§2.7**（施工顺序 / 危险中间态）—— 未审。
4. **§6 建筑复杂度可扩展性复核**（铁律 #6）—— 未审。
5. sol 自陈的四条「没能确定」（修后完整集成未实跑 · 真实 1.3 MB run 未跑绿 ·
   加载器缺稳定细粒度错误码 · 未枚举全部 V2 legacy 的两份 correction 是否一致）
   —— **照单收下，⛔ 不得在施工单里当成已证事实**。

**⇒ 结论：设计方向可以采信并据以继续，但⛔ 现在还不能据本稿直接派施工。**
第二轮必须把 §4 那 8 把锁审完 —— 那是最贵的一段。

---

## 5. 派工方错误率与记账

- **调查报告（Claude 侧 Sonnet）的二分法漏检**：不记施工席的账 ——
  派工单（orchestrator 写）本身就是按二分法描述岔口的，施工席是照题作答。
  **⇒ 派工方错误率 14/14。**
- **⭐ 本轮登记一条正面样板**：跨家族出稿在**第一轮**就抓出同家族两道工序都没看出的状态遗漏，
  为「设计稿不该由 orchestrator 亲手出 + 必须跨家族」这条纪律提供了第二例实证
  （第一例 = 08-09 sol 判 F-9 稿 REWORK）。
