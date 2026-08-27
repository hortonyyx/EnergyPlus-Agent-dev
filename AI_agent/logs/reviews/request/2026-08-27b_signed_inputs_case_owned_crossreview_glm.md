# 跨家族复核请求 · 签字输入落进 case-owned 持久路径（F-111 修法）

- **被审 commit**：**`60cc4ca`** `08.27_SignedRequestMovesIntoCaseOwnedPath_GateFollowsItThere`
- **施工方**：Claude 席位 · **复核方**：GLM（跨家族）· **派工方**：orchestrator
- **档位**：工程档（碰 `src/agent/judge/`，成绩产出路径）
- **原派工单**：[`2026-08-27b_signed_inputs_case_owned_dispatch.md`](2026-08-27b_signed_inputs_case_owned_dispatch.md)
- **前置实测档**：[`../../experiments/2026-08-27b_signed_request_recovery/README.md`](../../experiments/2026-08-27b_signed_request_recovery/README.md)

> ⭐⭐ **本轮你没有维持与任何人（包括你自己上一轮）一致的义务。**
> 若你认为派工方（我）或施工方的任何一条前提是错的，直接推翻并给你的实测证据。
> 本项目累计 **38/38 次「停下上报」全部是派工方的题错**，你上一轮当场推翻自己的逐字处方是被明确赞许并写进模板的。

---

## 一、这件事在解什么（⛔ 先看这条，它的题面被改写过）

原始登记 **F-111** 写的是「sm24 的签字 request **已不可寻**」。**那是错的**，我实测推翻：
真件一直在 `tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json`，
**内容重算逐位命中** `ae0fec08…`。

真问题是两条：**① 门的查找面窄在两处**（搜索根写死 `AI_agent/logs/experiments`、
文件名必须字面是 `request.json`）；**② ⭐ 承重的那半 —— 信任根被放在项目自己声明为
「过程痕迹、可清理」的目录里**，且 **sm25 同样中招**（副本全在那儿）⇒ 结构性风险，不是 sm24 个案。

---

## 二、交付面（我已独立核过，读数如下；⛔ 请你自己再核一遍，别信我的转述）

`git diff --numstat HEAD~1 HEAD`（原文）：
```
676	0	case_tests/test_baseline/gt_sources/sm24_anchor/request.json
1042	0	case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json
39	12	src/agent/judge/gt_raw_layer.py
146	0	tests/test_gt_raw_layer.py
```

**我方独立核对**（⛔ 未用 `git status`，直接读 HEAD blob）：
- 两份 `request.json` 从 **HEAD blob** 重算 `request_sha256` ⇒ `ae0fec08…` / `d738d0ac…`，逐位命中各自 `review_ack.json`；
- 复现门实跑：**sm25 `reproduced`（drift=()）· sm24 `implementation_drift`
  （`converter_sha256` + `vg_implementation_sha256`）** —— 与派工单 §四**预写**的预期读数逐条命中；
- `review_ack.json` 字段表实测 =
  `decision / near_threshold_confirmed / overlay_sha256 / request_sha256 /
  review_index_sha256 / reviewer / signed_at / source_dxf_sha256`。

**施工方自报**：全量 `3130 passed / 13 xfailed / 0 failed`（`-n 6`，979s，exit 0；
`3130 = 3124 + 6` 新锁）；`.pth` 跑测前后同为 `58f547fa…` 且指主树。
⭐⭐ **主控权威全量（唯一权威门，已跑完）**：
```
3130 passed, 13 xfailed, 212 warnings in 1030.06s (0:17:10)     exit 0
```
`-n 6` · HEAD **`3fe0d29`** · 工作树干净 · **`.pth` 前后哨兵同为
`58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`，内容均为主树**。
`3130 = 3124(基线) + 6(本单新锁)`，算术对得上，**零 failed** —— 与施工方自报一致。

---

## 三、⭐ 施工方主动上报的一次程序失误（已自行处置，请你评估处置是否足够）

它**第一次**启动权威全量后，在跑到约 50% 时**编辑了 `tests/test_gt_raw_layer.py` 的两处注释**，
随即**自行作废该次读数、杀掉进程、把树定稿后从头重跑**，并从那次起加了树哨兵
（被改文件跑测前后哈希一致：`src bb38ab49…` / `test 3b9d1e7a…`）。

⇒ 请评估：**这个处置够不够？** 本项目 08-27 刚因「跑测途中启动器被第三方改掉」作废过一轮权威读数，
故对「全量在跑时动树」是零容忍的**读数作废**，但施工方是**自己发现、自己作废、自己重跑**的。

---

## 四、⭐⭐ 我对两处自由裁量的裁定 —— **请你挑战它们**

### 4.1 ✅ 我接受「不拷 manifest」（这是对派工单 §3.1「必做」的偏离）

派工单要求把 **request + manifest** 都落进 case-owned 路径；施工方**只放了 request**，理由：
ack 没有 manifest 的签字锚 · 门只吃 `(source_dxf, request, tooling)` · sm25 一直没有 manifest 却始终 `reproduced`。

**我裁定接受**，依据是我**独立核到的 ack 字段表**（§二）确实没有 manifest 锚
⇒ 拷进去等于**在信任路径上放一个无法用签字重算验证的文件**，正是派工单 §二红线 1 要防的。

⛔ **但请你替我挑战这一点**：施工方自陈「我只查了一个消费者」。
⚠️ 而我今夜的另一项工作**恰好撞到了第二个消费者**：判分侧的图纸↔世界标定
（`raster_overlays[].pixel_to_source_m`）**就住在那份 manifest 里**，
且它同样只有一份副本在 `logs/experiments/`（详见
[`../../experiments/2026-08-27d_judge_ruler_pointwise_holdout/README.md`](../../experiments/2026-08-27d_judge_ruler_pointwise_holdout/README.md) §六）。
⇒ **我已把它登记为独立一条**（信任根问题不同：它没有签字锚），**⛔ 不并入本单**。
**若你认为它必须并入本单才算修完，请直接说。**

### 4.2 ✅ 我接受「移除旧搜索根、不留回退」

施工方最有力的理由是：**留着回退它就验不了自己的改动** ——
sm25 会因 `logs/` 里的旧副本继续绿，无法区分「绿是新路径生效」还是「绿是老路径兜住」。
⇒ 这与本项目 [[self-consistent-gates-anchor-on-product-chosen-apertures]] 的教训同形，我认为判断对。
它另测了调用面（`find_signed_request` 只有一个调用者、不在 `__all__`、零测试引用）。

**请你挑战**：向后兼容面它是用 `grep` + `getattr`/`importlib` 排查的
（同族老坑 [[grep-zero-hits-conflates-unused-with-nonexistent]]）。

---

## 五、⭐⭐⭐ 施工方自陈的「我最可能塌在哪」—— **请优先打这几处**

它自己列了 8 条，我认为**下面三条最值得你花时间**（其余见交付报告，我未删改）：

1. ⭐ **锁对「文件名口径被改宽」没有分辨力**。它变异了「搜索面变宽」「不再重算」「回旧根」，
   **唯独没变异 `request*.json` → `*.json`**，并自陈「将来有人放宽 glob，我这套锁全绿」。
   它选择不补（理由：按 §0.1 不影响能跑能读、且仍 fail-closed）。**请你判这是不是真空洞。**
2. ⭐ **本单没让问题「结构上不可能再发生」**：`promote_gt_v3` / `sign_review_bundle`
   都不会把 request 拷进 `gt_sources/` ⇒ **下一个 case 会原样重犯**。
   它判断这是「加法不是替代」故未触发停报，登记为后续项。
   ⚠️ **派工方口径**：我在派工单里把这条写成「**我没验证过的第三条路**」并挂了停报触发器，
   ⇒ 按单子的字面它不欠交。**但如果你认为「结构上不可能」才是这类修法的验收线，请直接判我题错。**
3. ⭐ **`gt_sources/` 的持久性是推的、不是被声明的**：没有任何纪律明文写它永不清理，也没有锁防删。
   ⇒ 信任根从「被声明可丢」搬到了「**没人声明过会不会丢**」。**方向对，但离「被声明持久」还差一份文字。**

---

## 六、请你回答的判据

1. **三条红线有没有被破**：① 位置永远不承权 ② fail-closed 不许弱化 ③ 不许为让门变绿去动指纹。
   （施工方声称 M2 变异「去掉内容重算 ⇒ 位置变成权威」能打红 2 把锁，**请你自己复现这一格**。）
2. **6 把新锁每一把是不是真能变红**，以及 ⭐ **请再找一种能骗过它们的真实错误形态**
   （本项目硬纪律：作者自己挑的破坏方式挑不出自己的盲区；上一次换人一审第一条就找到了漏的那种）。
3. **两份 case 的读数**是否与派工单 §四**预写**的预期一致
   —— ⛔ 注意 sm24 的**通过标志是 `implementation_drift` 而不是绿**，
   若你看到有人为了让它变绿动了指纹，**直接判 REJECT**。
4. §三 的程序失误处置是否足够。
5. §四 两处裁定、§五 三条自陈，你同不同意。

**裁决格式**：`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT` + 阻断项与不阻断项分列。
