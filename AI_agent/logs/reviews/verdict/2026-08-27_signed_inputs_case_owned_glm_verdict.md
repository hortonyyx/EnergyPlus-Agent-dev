# 跨家族复核裁决 · 签字输入落进 case-owned 持久路径（F-111 修法）

- **被审 commit**：`60cc4ca` `08.27_SignedRequestMovesIntoCaseOwnedPath_GateFollowsItThere`
- **复核方**：GLM（跨家族）· 2026-08-27
- **环境**：主树 `/workspaces/EnergyPlus-Agent-dev`，未建 worktree；未跑任何写 site-packages 的命令
- **树哨兵**：复核全程结束时 `src/agent/judge/gt_raw_layer.py` = `bb38ab49dd6401ff2737…a61c`、
  `tests/test_gt_raw_layer.py` = `3b9d1e7aff88feabdf…4feb`，均与 `60cc4ca`/`3fe0d29`/`HEAD` 三处 blob 逐位相同；
  `git status` 干净。四个变异实验全部还原后核对（见 §四）。

## 裁决：**APPROVE-WITH-FINDINGS**（0 阻断 · 4 不阻断）

---

## 一、独立核对读数（全部本人实跑，未采信任何转述）

| # | 项 | 命令/方法 | 读数 | 判定 |
|---|---|---|---|---|
| 1 | 被审代码 = 权威全量所测代码 | `git show 60cc4ca:<f>` / `3fe0d29:<f>` / `HEAD:<f>` 三处 `sha256sum` | src=`bb38ab49…`、tests=`3b9d1e7a…` 三处全同；`60cc4ca..HEAD` 只加 `AI_agent/logs/` 文档 | ✅ 主控权威读数测的正是被审代码 |
| 2 | sm24 request 真件 | HEAD blob 重算 `compute_request_sha256` | `ae0fec087ef2a048…ac8a2` 逐位命中 `review_ack.json`；与 `tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json` **字节一致** | ✅ |
| 3 | sm25 request 真件 | 同上 | `d738d0ac230f21ae…a135` 逐位命中；与 `logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/request.json` **字节一致** | ✅ |
| 4 | ack 字段表 | 读 HEAD blob | 恰 8 字段：`decision / near_threshold_confirmed / overlay_sha256 / request_sha256 / review_index_sha256 / reviewer / signed_at / source_dxf_sha256`，**确无 manifest 锚** | ✅（§4.1 的事实基础） |
| 5 | 复现门 sm25 | `verify_raw_layer_reproduction("sm25-L_anchor")` | `reproduced`（advisory：`extractor_sha256`）—— 未退化 | ✅ 与派工单 §四 预写一致 |
| 6 | 复现门 sm24 | 同上 | `implementation_drift`（`converter_sha256` + `vg_implementation_sha256`）—— **红得诚实** | ✅ 与预写一致；非绿、也非 `inputs_unavailable` |
| 7 | 有没有人动指纹 | `git show 60cc4ca --stat` | 恰 4 文件（2 request + src + tests），`gt/<case>/` 签字件零改动 | ✅ |
| 8 | 6 把新锁基线 | `pytest tests/test_gt_raw_layer.py -q` | **17 passed**（11 旧 + 6 新） | ✅ |
| 9 | 调用面 | 全仓 grep `find_signed_request\|REQUEST_SEARCH_ROOT`（含 .md） | 唯一调用者在模块内 `gt_raw_layer.py:514`；`REQUEST_SEARCH_ROOT` 零残留 | ✅ 施工方排查属实 |
| 10 | 独立全量 | `python -m pytest -n 6 -q`（后台，全程未动树） | **3130 passed / 13 xfailed / 0 failed**，984.97s，exit 0 | ✅ 与施工方自报、主控权威读数一致；`3130 = 3124 + 6` 算术对 |
| 11 | `.pth` 哨兵 | 开工前 / 跑测前 / 跑测后 三次 `sha256sum` | 三次同为 `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`，内容为主树 | ✅ |

## 二、三条红线（请求单 §六#1）

1. **位置永远不承权 —— 未破。** M2 变异（删掉 `compute_request_sha256` 比对、返回首个解析成功的候选 ⇒ 位置变权威）实测
   红 `test_f111_d` + `test_f111_e` 两把，与施工方自报「2 把」精确一致。`find_signed_request` 的 docstring 把
   「why we believe」与「where we look」分得很清楚，代码与文档一致。
2. **fail-closed 未弱化 —— 未破。** case 目录缺件 ⇒ 响亮 `inputs_unavailable`（`test_f111_c` 实跑 + 我在回退腿探针的对照组里同样见到）；
   无跳过、无警告降级、无默认信任盘上件。
3. **不许为变绿动指纹 —— 未破。** 见 §一#6/#7：sm24 的红如实保留为 `implementation_drift`，`review_ack.json` 分毫未动。

## 三、⭐⭐ 请求单 §六#2 的回答：骗过全部 6 把锁的错误形态 —— **找到了，实测骗过**

**形态：以「向后兼容」为名，把旧搜索根作为回退腿加回来**（case 目录找不到时，回退到
`AI_agent/logs/experiments` 整树 `rglob("request.json")`）。

这是最真实的回归方向，不是稻草人：派工单 §3.2 当时就把「保留原搜索根还是移除它」列为两个可接受选项；
将来任何人（或任何模型）以「兼容旧 case」为由加回这条腿，完全说得通。

**实测**（变异后跑 `pytest tests/test_gt_raw_layer.py -q`）：**17 passed，6 把新锁零红。**

**为什么骗得过** —— 我逐份量了 logs 下的存货：

| | logs 下能重算出签字值的件数 |
|---|---|
| sm24（`ae0fec08…`） | **0** |
| sm25（`d738d0ac…`） | **4**（`2026-08-20_sm25_conversion_request/request_v3.json`、`…/review_bundle/request.json`、`2026-08-22_gt_coordinate_snap_glm/t2_review_bundle/request.json`、`2026-08-23_gt_rebuild_on_head/t2_review_bundle/request.json`） |

`test_f111_c` 的牙只咬「能到达 **sm24 字节副本**的 widening」—— 它在 `tests/fixtures/`，所以
widening 到 tests/fixtures 会红（施工方实测 reds-4 方向，我复现 reds **c/d/e** 3 把）；
但 **logs 方向恰好是它唯一没牙的方向，因为 sm24 在那里本来就一份都没有**。
c/d/e 三把都是 None-断言（断言「找不到/被拒」），它们分不清「**因为拒绝**而 None」与「**因为根本没去那个方向找**而 None」。

**实害不是理论**（只读探针，进程内 monkeypatch，未改仓库）：在回退腿变异下，构造 sm25 的
`gt_sources` 拷贝（只含 DXF、无 request）⇒ 门从 `AI_agent/logs/experiments` 捞到真件 ⇒ 照常 `reproduced`。
即：**信任根的可得性重新挂回项目自己声明可清理的目录，且全仓零锁看见** —— 这正是 F-111 承重的那一半，静默复活。

**附带**：`test_f111_c` 的 docstring 写 "or any future 'let's also look over there' widening -- turns
this red" —— 这个声称对本单最核心的 logs 方向**实测不成立**。这属于
[[design-doc-described-what-code-never-implemented]] 的微型形态：叙述的分辨力 > 实际的分辨力。

**便宜修法**（下轮做即可，本单不必返工）：给 `test_f111_c` 加一个 **sm25 变体**——sm25 的
`gt_sources` 拷贝（只 DXF）+ 断言 `find_signed_request` 返回 None。因为 sm25 在 logs 下有 4 份真件，
回退腿形态下这条会红（我的探针已证明该形态下 sm25 能从 logs 捞到件）。**一把锁锁「搜索根面」，
比锁 glob 名字对症** —— 施工方自陈的「放宽 glob 没分辨力」空洞与这是同一个洞的两半。

## 四、变异矩阵（全部本人亲手跑，全部已还原）

| 变异 | 形态 | 红的锁 | 结论 |
|---|---|---|---|
| M2 | 去掉内容重算 ⇒ 位置变权威 | **d、e** | 施工方自报「2 把」准确 |
| M-back | 纯回旧根（删新搜索面） | **a、b、f** | 「查找面改了」这半被抓住 |
| M-wide | 搜索面加 `tests/fixtures/sm24_review` 腿 | **c、d、e** | c 的牙 = 到达 sm24 字节副本的 widening（施工方自报 reds-4，我实测 3 把，外围差异只记） |
| **M-fallback** | **加 logs 回退腿（向后兼容）** | **0 —— 17 passed** | ⭐ 主发现（§三） |

⇒ **6 把锁每一把都有本人亲手的变红读数**（a/b/f ← M-back；c ← M-wide；d/e ← M2 与 M-wide），
但锁阵对「logs 方向的 widening」整体失明。

还原核验：四次变异后 `src/agent/judge/gt_raw_layer.py` 哈希回到 `bb38ab49…`（= HEAD blob），
`git status` 干净，基线 17 passed。

## 五、请求单其余各问

**§三 程序失误处置 —— 足够。** 可核的证据链：被污染那次读数未被用于任何判据；重跑发生在定稿树上
（`3fe0d29` 的 src/tests blob = `60cc4ca`，§一#1）；主控独立权威全量复核过（3130/13/0，带 `.pth` 前后哨兵）；
施工方从那次起加了树哨兵，其自报值 `src bb38ab49 / test 3b9d1e7a` 与我实测的 HEAD blob 逐位一致。
补充一点：50% 时编辑的只是测试文件注释，pytest 已收集的模块不会重新读盘，那次读数「碰巧」可能未受污染——
但零容忍口径下**作废是唯一正确处置，不该去赌这个碰巧**。它赌对了方向。

**§4.1 不拷 manifest —— 同意，且确认不必并入本单。** 我核到的 ack 字段表（§一#4）确实没有 manifest 锚；
把一个无法用签字重算验证的文件放进信任路径，恰是红线 1 要防的形态。第二个消费者
（`raster_overlays[].pixel_to_source_m` 判分标定）的风险真实存在，但 08-27d 实验档 §六已独立登记且给出了
「不能照搬修法」的技术论证（先回答这把尺子自己的信任根是什么）。**并入本单 = 用错误的方法修对的问题。**

**§4.2 移除旧根不留回退 —— 同意，且我的变异实验反向加固了这个判断。** 「留着回退就验不了自己的改动」
（sm25 的绿无法区分新旧路径）理由成立；我补的实测：调用面复核属实（§一#9），签名变化使任何漏网的动态调用
会 TypeError 而非静默，全量绿排除了这个面。

**§五#1（glob 放宽无分辨力）—— 同意是真空洞、同意不补。** 放宽到 `*.json` 后 fail-closed 仍在（解析失败跳过、
哈希不匹配拒绝），`gt_sources/<case>/` 是 git 跟踪的个位数文件目录，F-112 族的畸形文件进不来。按 §0.1 判断法则
登记不做是对的。但注意它与我的主发现是同一个洞的两半：**真正该锁的是「搜索根面」而不是「glob 名字」**（§三修法）。

**§五#2（不结构性地防再犯）—— 自陈属实，我核了代码。** `promote_gt_v3`（`gt_promotion.py:74`）的拷贝清单是
`gt.json + renders + review 五件`，**无 request**；`build_review_bundle`（`tarch_review_bundle.py:150`）只把
request 写进评审 bundle 的 staging。⇒ 下一个 case 走完晋升流程后，其签字 request 仍只住在 bundle 目录
（历史上 = logs 下），复现门将 `inputs_unavailable`，直到有人再手工回填一次。按派工单 §3.1 的字面
（「这可能超出本单工期；若你判断它更对但更大，请停下上报」）施工方不欠交，其「加法不是替代」的归类也对。
**我不判派工方题错**：本单交付面（两份 case 回填 + 门改道 + 锁）在工程档口径下完整。
但把「结构上不可能」定为这类修法的验收线是更对的尺 —— 建议下一单一行改动：
`promote_gt_v3` 的拷贝清单加上 `request.json`（+ 一把「晋升后 case 目录里有可重算的 request」锁）。

**§五#3（gt_sources 持久性是推的）—— 属实。** `gt_sources/` 无 README；管理文档多处只把它列为「不得修改」的
保护根，「不得修改」≠「永不清理」。方向对（从「声明可丢」搬到 git 跟踪的测试基线资产树），差一份文字：
一行 README 或在 `gt/README.md` 里声明「`gt_sources/<case>/` 是签字输入的持久住所，与 `logs/` 不同类，永不清理」。

**备注（观察，非 finding）**：`test_f111_b` 只断言 `!= inputs_unavailable`，6 把新锁内部没有一把钉死
「sm24 的诚实红 = `implementation_drift`」；若有人把 drift 分支谎报成 `reproduced`，新锁不拦——
但 G1 旧锁 `test_a4` / `test_r5`（`tests/test_gt_raw_layer.py:163,180`）在合成夹具上断言
`status == "implementation_drift"` 精确值，该谎会红。旧锁补位成立，故不构成洞。

## 六、复核方自述（一次自查出的幽灵读数，如实记档）

扫 logs 存货时我先得了「sm24/sm25 均 0 hits」的读数，与逐文件诊断版「sm25 命中 4 份」直接矛盾。
原样重跑仍 0/0 ⇒ 不是环境幽灵，是脚本间真差异；`repr()` 逐位对比定位：**我手抄 sm25 哈希时把第 45 位
`f` 抄成了 `c`**（`…295a3f6de…` → `…295a3c6de…`）。此错属 [[grep-zero-hits-conflates-unused-with-nonexistent]]
登记过的「把读到的东西记成另一个东西」同族。本裁决所有关键比较均改为从 `review_ack.json` 程序化读取，
不手抄哈希。幽灵读数未进入任何结论。

## 七、findings 汇总

**阻断项：无。**

**不阻断项**：

1. ⭐ **6 把锁对「logs 方向的搜索面回宽」整体失明**（§三）：回退腿变异 17 passed 全绿 + 实害实测
   （sm25 从可清理目录捞件照常 `reproduced`）。根因 = `test_f111_c` 夹具选了 sm24（其在 logs 下 0 份），
   c/d/e 的 None-断言分不清「拒绝」与「没去找」。修法 = 加 sm25 变体，锁「搜索根面」而非 glob 名字。
2. `test_f111_c` docstring 声称的分辨力（"any future widening turns this red"）实测对 logs 方向不成立 ——
   叙述 > 实际（并入 1 的修复一并改）。
3. **结构性再犯窗口**（§五#2）：`promote_gt_v3` 拷贝清单无 `request.json`，下一个 case 必然重演
   「签字 request 只住可清理目录 ⇒ `inputs_unavailable` ⇒ 手工回填」。建议下轮一行改动 + 一把锁。
4. **`gt_sources/` 持久性无明文**（§五#3）：一行 README 的事，趁热写。

**结论**：改法方向正确、三条红线未破、两份 case 读数与预写预期逐条命中、独立全量绿、
变异实验证明锁阵对它要防的三个方向（位置承权 / 回旧根 / 面变宽-可达 sm24 副本）均有牙。
唯一实质缺口是锁阵对本单病灶方向（logs 回宽）的盲区 —— 已给便宜修法，不构成返工理由。

**APPROVE-WITH-FINDINGS。**
