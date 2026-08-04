# 批 C · r2 返工 + 批 D/R4-a 合并 · orchestrator 轻门

- **日期**：2026-08-04（北京时间 17:40）
- **被审对象**：
  - **批 C r2**：`58f9179` → `f7cc1ff`（4 commit）—— 施工 **GLM 起手（撞额度只留半截）→ 用户拍板转 Claude 侧接手做完**
  - **批 D + R4-a**：`794b47a` / `8336bd5` / `b8ff69f`（经两个 merge 落主线）—— 施工 Claude 侧执行档
- **性质**：orchestrator 轻门 = **唯一权威门**

---

## 0. 总判定：**两批全部落地，轻门通过**

| 条目 | 修的是 | commit | 状态 |
|---|---|---|---|
| **X-1（MAJOR·本批引入的回归）** | 自适应缩放删掉了「像素化**尺寸端点**」的最后一个探测器 | `7de68cb` | ✅ |
| **X-2（MAJOR）** | 可信画幅由**被测方自己写的字段**决定 ⇒ 检查可被产品绕开 | `7de68cb` | ✅ |
| **X-3 / X-5 / NIT** | `total_fit` 零锁 · render manifest error surface / 损坏即放行 · 单位双关 | `066fff4` / `f7cc1ff` / `32db683` | ✅ |
| **R4-a** | `reading_mode` 成绩分账（两条 lane + dev 职能） | `794b47a` | ✅ |
| **批 D** | 判卷图恢复六 panel + 图例 + 缺失立面显式占位 | `8336bd5` | ✅ |
| 白名单更新 | `render_grade.py` 已有覆盖 ⇒ 诚实白名单条目过期 | `b8ff69f` | ✅ |

**独立全量**（orchestrator 自跑 `pytest -q -n 6`，**不接管道以保住退出码**）：

```
EXIT=0
2148 passed, 10 xfailed, 205 warnings in 471.15s (0:07:51)
```

**2089（批 B 末）→ 2148，本日净增 59 条锁、零回归。**

---

## 1. ⭐ 独立 neuter（覆盖两条 MAJOR 的正文实现）

`/tmp` 克隆（`PYTHONPATH=$PWD` 钉死，否则 editable `.pth` 会解析回主仓 = 等于没做）。
⚠️ 克隆基线固有 1 条环境红（`test_partition_on_window_jamb_real_restore_reading_r2_flags_four`，缺未跟踪输入），
**已从下表「红了哪几条」中剔除**。

| # | 摘掉哪一处实现 | 红了哪几条 | 连带 | 判定 |
|---|---|---|---|---|
| **N-1** | `checks/reading.py` 的 `_dimension_endpoints_in_bounds(...)` 调用（= X-1 病灶原状） | `test_dimension_pixel_endpoint_out_of_bounds_blocks_acceptance[regression]`、`[golden]`、`..._only_flags_under_lenient`、`test_dimension_endpoint_in_bounds_and_margin_tolerated_passes`（**4 红**） | 零 | ✅ 真绑 |
| **N-2** | `checks/view_manifest.py:92` `trusted_bounds_by_stem = resolve_view_pixel_bounds(...)` → `{}`（= 回落产品自算） | `test_trusted_bounds_from_case_data_survive_all_three_inflation_tricks`（**1 红**，该锁一次覆盖三种撑大手法） | 零 | ✅ 真绑 |

⚠️ **如实登记**：N-2 我第一次写的正则**没命中调用点**（脚本自己 assert 失败），**该轮结果作废**、重做为逐字精确替换。
**这是本日第三次探针脚本自身出错**（前两次：一次改坏模块得 16 红 + 2 error、一次替换到无关字符串得零红）
⇒ **纪律已固化：neuter 脚本必须逐字命中目标；「零红」在确认脚本真改到东西之前不得当结论。**

---

## 2. X-2 的修法与用户判据逐字对齐（本轮最值得记的一点）

实现的 docstring 写明：可信画幅**只**来自 view manifest 的 `resolve_view_pixel_bounds`
（keyed by 已冻结、R1-6 指纹核对过的 `image_sha256`）；
**产品自己的 `strokes` / `dimensions` / 任何 `extra` 字段（含 `image_bounds` 逃生口）从不被查看**。

**这与用户 2026-08-04 拍板的判据是同一条**（[decision_log §5.14](../../decision_log.md)）：
> 只有「先于本次运行就已固定、且被评判方写不了」的第二处记载，才配当判定依据。

**⭐ 三方独立收敛**：交叉审给出的骨架、用户拍板的判据、施工方最终的实现 —— 三者是同一句话。

⚠️ **保留了一条降级路径**（无可信来源时回落产品自算，供直接单元调用与无 manifest 的 legacy run）
⇒ **已作为 S-1 的主攻方向交给 sol**：请证伪「产品能否自己触发这条降级」。

---

## 3. 施工过程如实登记（三席接力，两次额度中断）

| 席位 | 时段 | 产出 |
|---|---|---|
| GLM | 16:00–16:24（**当日第三次撞 5h 上限**，19:27 复位） | 零 commit，只留 NIT 半截（已由 orchestrator `git stash push -m batchC-r2-wip-glm-nit-unit-pun-split` 保存） |
| Claude 侧执行档 | 接手 | 四条全落、**每条即时 commit**（前两轮该席位连续两次停在「等全量再提交」，本轮派工单写死顺序后已纠正） |
| Claude 侧执行档（批 D/R4-a） | 并行（独立 worktree） | 两条落地；白名单那条**又停在等全量**，由 orchestrator 看清 diff 后代为提交 |

**⇒ 运维教训**：**「改完 + 等全量跑完再提交」是本日反复出现的中断损失点**
—— 派工单必须写死「**每条改完立刻 commit → 再跑全量 → 再回报**」。

---

## 4. 边界合规

| 项 | 结论 |
|---|---|
| `gt/**` 与 sm24 `testdata_prompt.json` 零字节 | ✅ |
| 未读 GT | ✅ |
| 未 push | ✅ |
| 未动 `AI_agent/` 下除各自执行日志外的管理文档 | ✅（工作树里那些是 orchestrator 自己的） |
| GLM 半截未提交工作 | ✅ **未被扫走**，已 stash 具名保存 |

---

## 5. 下一步

1. **sol 交叉对抗审**（用户 08-04 指定；施工 = Claude ⇒ 审 = GPT 侧，跨家族满足）
   —— 审阅单：[2026-08-04_batchC_r2_and_batchD_R4a_review_sol.md](../request/2026-08-04_batchC_r2_and_batchD_R4a_review_sol.md)
2. 若无 BLOCKER ⇒ **批 C 收口 ⇒ 批 A/B/C 三批全绿 ⇒ 「不得发布识图分数」的硬约束解除**。
3. 之后按用户 08-04 定的队列：**收 sm21（E1 模式）→ 收 sm24（⛔ 需用户授权 + 真人签字重签 GT 侧车）
   → 做 sm25 GT + 收 sm25（C2 收官，⛔ 需素材入仓）→ 转攻 reading**。
   **⛔ 遗留待办**：X-4（merge 从不渲染 ⇒ 一张图都没有的 run 被 approve-review 放行）
   —— 原要求施工席判断后回报，**GLM 撞额度未答、接手席未覆盖 ⇒ 仍未裁定，登记结转**。
