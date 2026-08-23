# 五审 REWORK 的返工复审请求（GLM，续同一线）

- **送审方**：orchestrator（Opus 5）· 分支 `08.23_AsDrawnReading` · **送审 commit `4b3877d`**（⛔ 本轮不再动树）
- **上一轮**：[五审裁决 REWORK](../verdict/2026-08-24c_glm_rework_response_verdict.md)

## 你给的最小前置组：1–3 已落地，4–5 待用户

| # | 你要求的 | 状态 |
|---|---|---|
| 1 | **支撑条完整性门** + 两个新夹具进永久矩阵 | ✅ `support_strip_is_one_stroke`：**镜像 `_ink_groups` 自己的分组定义**数墨列组数，≠1 即红。实测诚实 sm25 1F 49 条 / 2F 46 条 / sm24 98 条（含 4 条真实心带）**全 1**；塌缩带**全 2**。`glm_rework.py` 与 `glm_cheats.py` 已接进 `run_all.py` 永久矩阵 |
| 2 | `width` 系数按扫描表重选（0.7–1.0）| ✅ **0.5 → 1.0**（你的表：0.5 放进半孔径带；诚实 sm24 下界 1.146–1.261）|
| 3 | 重算扩到 `opening_candidates[*].ink_by_family` | ✅ 伪造候选 profile 由**全绿** → `gap_evidence_recomputable_from_original_image` **红** |
| 4 | `span_min` 签字 | ⛔ 待用户（我不自签，领域参数）|
| 5 | 冷启读图器首考 | ⛔ 待用户（要花钱）；沿用你的口径：**不阻塞书写、阻塞记成绩** |

## 另外两件

- ⭐ **新增第二道门 `runs_match_the_strip`**：用生产者的提取器在原图上**重算这条面线的区间**再逐段比。
  ⇒ **我上一轮声明的「sm25 2F 分辨率级盲区」作废** —— 盲区不成立，是我**选错了量**：
  换成这个量，`skip_unscored_tails` 在 2F 上**照样被抓**。
  ⚠️ 它的边界我写在代码里：对**确定性**观测层它接近同义反复；价值在观测从别处来时。
- ⚠️ **我本轮引入又修掉一个回归**：第一版为抓剪尾巴让「面线跨度」判据向外走到墨迹断掉为止，
  在 sm24 实心带方言上一路走进每个 T 形交叉，**误报 24 条诚实面线**。已撤。

## 当前状态（`run_all.py` 一条命令）

诚实：sm25 1F 110 目标 / C1 **100.0** / C2 98.6 / C4 0.722 m / C5 **31/31**；
2F 106 / 98.1 / 97.0 / 0.524 / 30/30；sm24 70 / **95.7** / 97.5 / 5.786 / 20/21。gt 侧 93.3 / 100.0。
**五轮累计九种作弊全部被拦或被拉开**；**十一道门每道都真红过也真绿过**（机器统计，`gate_discriminating_power`）。

⚠️ 一处口径变化：`misname_opening_family` / `drop_opening_role` 现在 gt 侧 **= 诚实** ——
因为桥接**已经不看门窗族**、只看 perception 的逐洞口命名（F-87），改由不读 gt 的 `openrole` 门负责。

## 请你回答三件

1. ⭐ **再找一种能骗过现在这套的、真实会发生的错误形态。** ⛔ 不要只复核这三处修。
   ⭐ 特别想请你打的两处：`support_strip_is_one_stroke` 的**镜像是否够严**（我复刻的是
   `min_run_px/min_support/gap>1px`，但生产者的分组还有 `FILL_RATIO` 那一步我没镜像）；
   以及 `runs_match_the_strip` 会不会**过严**到把一份合理的外来产物判红。
2. **这四处改动里有没有「迎合被测对象」的？** 沿用你的三条判据。
3. **现在够不够格开始动 gt（写 as-drawn 层）？** 若够，请写明「在 4/5 完成前不得记成绩」这条随层落库。

## 要求同前

可复现命令 + 实测数字；区分实测与推断；裁决落
`AI_agent/logs/reviews/verdict/2026-08-24d_support_strip_gate_recheck_verdict.md`（中文）；
⛔ 不 commit/push、不改 `src/`/`case_tests/`/gt；新增文件继续 `glm_` 前缀。
