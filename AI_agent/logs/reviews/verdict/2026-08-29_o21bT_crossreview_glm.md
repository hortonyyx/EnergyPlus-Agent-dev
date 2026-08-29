# 跨家族裁决书 · ②-1b-T（事实层暂存区的进出门）

- **日期**：2026-08-29 · **审阅方**：GLM 家族（跨家族审）· **请求书**：[`../request/2026-08-29_o21bT_crossreview_glm.md`](../request/2026-08-29_o21bT_crossreview_glm.md)
- **送审对象**：`5b836ee`（主）+ `4487249`（补记）· **基线**：`291533f` · 一律以 `git diff 291533f..4487249` 为准（4 文件：`src/agent/judge/gt_facts_staging.py` +67/−25 · 新增 `tests/test_gt_facts_staging_gate.py` 200 行 · `tests/test_gt_facts_staging_sm25.py` +2/−2 · 执行记录 md）。

---

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 条 · 不阻断 5 条）

三件（R1 写前 verify / R2 读后 verify / R3 公开面收窄）都按单施工、
8 项验收我逐条独立复核通过；施工方自报的最薄弱处（A1）经 20 维实测**有牙**；
主控看出的 A2 缺口**属实但实害被 R2 结构性封死**。
我另击穿一条**新错误形态**（case 路径穿越，见 F-1）——今天实害为零（answer root
尚无 facts 目录、无消费者），不构成本单阻断，但**必须在 ②-1c / 晋升接缝单之前修**。

---

## 〇、独立复核记录（不信任何 RESULTS，全部重跑）

| 项 | 我方读数 | 与主控/施工方对照 |
|---|---|---|
| 受影响子集三文件 | `52 passed`（跑**两次**：12.77s / 14.03s，稳定） | 与执行记录 §三#6 相同 |
| 权威全量 3330/13/0 | 未重跑全量（席位纪律：不占 15 分钟全量；子集两连绿 + diff 边界清晰——改动只落在 `gt_facts_staging` 一个模块及其直接消费者） | 采纳主控读数，标注**未独立复现** |
| 验收 7（签字件逐位不变） | `request.json` = `e635ab11…93df`、`request_as_measured.json` = `55305752…77f6`，与执行记录贴值**逐位一致**；两文件均不在 diff 文件清单 | ✅ |
| 验收 8（阈值未动） | `git diff 291533f..4487249 -- src/agent/judge/tarch_normalize.py src/agent/judge/as_measured.py` 输出 **0 行**；`AXIS_SNAP_MAX_DEVIATION_M = 0.006`（`tarch_normalize.py:130`）现状未变 | ✅ |
| 验收 5（门是新代码给的） | 两层独立验证：① 基线 `291533f` worktree（/tmp）+ 新测试文件 ⇒ **7/7 全红**；② **当前代码**上把 `verify_as_signed_reproduction` 砍成 no-op ⇒ R1 放行篡改 trio 落盘、R2 **静默读走**手改磁盘（const 偏移 +1 读回成功）——门被砍即失效，且我的复验用的是**真实 sm25 形状**，强于施工方的合成夹具 mock | ✅（施工方 mock 自测成立，本审补强） |

①的诚实解读：基线上的 7 红全部是 `AttributeError: no attribute '_FACTS_STAGING_ROOT'`（改名所致），本身只证明「测试依赖新代码存在」；真正证明「门在干活」的是 ②。

---

## 一、findings

### 阻断（0 条）

无。

### 不阻断（5 条）

**F-1 · ⭐⭐⭐ 新错误形态：`case` 参数路径穿越——写出口可移到任意目录，**含 answer root**（A3 实测的副产物）**

- **形态**：`_facts_staging_dir(case)`（`src/agent/judge/gt_facts_staging.py:89`）对 `case` 零校验。
  `Path` 拼接两条经典穿越全部生效，且走的是**公开 API 的合法调用形态**（verify 也跑了、也过了、IDE/类型检查全绿）——不是「绕过门」，是「门没装门框」：
  - 相对穿越：`write_facts_candidate("../gt/sm25-L_anchor", …)` ⇒ 落点
    `case_tests/test_baseline/gt/sm25-L_anchor/facts/`——**正是模块 docstring 第 4–5 行自己声明 ⛔ 只有 `promote_gt_v3` 可写的 ANSWER ROOT**。未签字候选被一次合法调用直接种进答案根，R1/R2/R3 三道门全绿放行。
  - 绝对路径：`write_facts_candidate("/tmp/任意位置", …)` ⇒ `Path("/a") / "/b" = "/b"`，staging 前缀被整个吞掉。
- **实测**（/tmp 复刻仓库布局，未碰主树 answer root）：
  `case='../gt/sm25-L_anchor'` → 落点 `case_tests/test_baseline/gt/sm25-L_anchor/facts/`，三件套齐全；
  `case=绝对路径` → `/tmp/e5_abs_*/anywhere/facts/`，三件套齐全。
- **今天实害 = 0 的证据**：`case_tests/test_baseline/gt/` 下 `find -name facts` 计数 **0**（gt 只有 `gt.json`/`renders`/`review`），AnswerCompiler 不存在，`promote_gt_v3` 不读 facts。但 gt 重签之后 AnswerCompiler/load_gt 将读 `gt/<case>/facts/`——届时这份「看起来合法」的目录就是现成的污染点。
- **修法方向（一行级）**：`write/read_facts_candidate` 入口校验 `case` ∈ 合法 case 名（白名单或「禁止 `/`、`\`、`..`、非 [A-Za-z0-9_\-]」），不匹配即 raise。**列为 ②-1c / 晋升接缝单的前置必办。**
- 复现：见附录 E5。

**F-2 · A1 缺口属实，但实测**有牙**——真实形状的牙本次补齐，建议固化**

- 施工方自报「6/7 门用合成夹具、真实形状只 1 条往返」属实：合成 = 1 view / 0 revisions；真实 sm25 = 2 views / 446 face_lines / 5 条全 unsigned revisions / 115KB。
- **按「它声称覆盖的每种量各自有没有被量到」逐维实测（20 维，真实 sm25 形状，磁盘手改后走 `read_facts_candidate`）**：
  - as_signed 六维（const / along_min / 删 face_line / derivation 哈希 / case 名 / openings / walls）→ **全红**；
  - as_measured 五维（const / source_dxf_sha256 / converter_readouts / walls / openings）→ **全红**；
  - revisions 五维（detail 改字 / 逆序 / 换 as_measured 哈希 / 删记录 / 改 target.handle）→ **全红**；
  - 18 红里 14 个 `AsSignedReproductionError`、4 个 `ValidationError`——即真实形状上还有**schema 层第二道防线**（walls/openings 交叉校验，`gt_revisions.py:364` 一族），施工方没提，双保险。
  - 2 绿均无害/已知：T14 字节层非规范化（indent=2，对象等价，读出对象不变——设计边界）；T15 重造自洽（见 F-3）。
- **结构原因**（为什么覆盖面出乎意料地完整）：`content_sha256` = 整份 dump 哈希、`derivation` 含整份 revisions 哈希、as_signed 比对 = canonical bytes 逐字节——三文件环环相扣，**任何单文件篡改必断链**。这正是 E4 里门后失败也全红的同一机制。
- 建议：在 `tests/test_gt_facts_staging_sm25.py` 固化 2–3 条真实形状篡改回归（T1/T6/T9 即可覆盖三文件各一维）。低成本，防未来 schema/canonical 演进在真实形状走不同分支时合成夹具集体失明。

**F-3 · 「复现门 ≠ 真值门」：重造自洽的三件套三道门全绿（已知设计边界，给 ②-1c 的提醒）**

- 实测（T15）：改 as_measured 的 const +1 → 同步 revisions 哈希 → `derive_as_signed` 重派生 → 三件全写盘 ⇒ `read_facts_candidate` **GREEN**，改过的 const 被读回。任何人可用公开 API 把一份**内容改过的测量事实**写成「合法」staging——staging 无写入者认证，读门只保证自洽、不保证真实。
- 这是设计内的（staging 无签字、真值归签字流），**不构成本单缺陷**；但 ②-1c 的 `AnswerCompiler` 将直接消费这里——在 gt 重签落地之前，staging 的信任级别 = 0，编译产物不得记成绩。

**F-4 · A2：「零残留」只覆盖门前失败；门后失败留残缺 staging，但全部被 R2 拦死，无一静默**

- 实测（注入 `OSError(28)` 到第 N 次 `_write_atomic`，5 组合，真实 sm25 形状）：

  | 注入点 | 起始状态 | 磁盘残留 | read 结果 |
  |---|---|---|---|
  | 第 1/2/3 次写失败 | 空目录 | 孤儿 0/1/2 个 json | **红**（FileNotFoundError） |
  | 第 2 次写失败 | 已有旧 trio | 新旧混合三件 | **红**（`…revisions_do_not_target…`） |
  | 第 3 次写失败 | 已有旧 trio | 新旧混合三件 | **红**（`…does_not_reproduce…`） |

- **结论**：主控的质疑成立——verify 通过后写到一半确实留残缺/混合目录，「零残留」的宣称范围只到门前；但**没有任何一种中途失败形态能被读门静默放行**（哈希链条结构性断链）。本单要防的「残缺 staging 被当真货」实际发生路径为零。
- 两个轻微尾巴：① 验收 #1 的措辞应理解为「**verify 失败** ⇒ 零残留」，不宜外推到写中途失败；② `_write_atomic`（`gt_facts_staging.py:93`）在 `write_bytes` 成功而 `replace` 前崩溃会留 `*.json.tmp` 孤儿，read 不受影响、成功重写也**不会清理**它——记录在案即可。

**F-5 · A3 的文档表述过强 + 正解方向：消费侧门，不是入口收窄**

- 施工方承认「防不住完全绕开」是对的、如实的。但 docstring「未来晋升**在类型/API 层没有**拷目录这条路」实测**过强**——今天两条路都通：
  - `gfs._facts_staging_dir(case)` + `shutil.copytree`（3 行，实测拷出三件套）：下划线只挡**发现性**不挡**可达性**（自家 `tests/test_gt_facts_staging_sm25.py:18` 就在 import 私有名）；
  - F-1 的 case 穿越：连「绕」都不需要，公开 API 本身可把出口移过去。
- **判断**：作为工程档、单仓单进程的治理，R3 的性价比是合理的（把捷径从「顺手 import」逼成「自己文件里明面造路」= 代码审查可见）。**更结构性且不靠词法匹配的做法存在**：把 R2 的同构 verify 挂到 **answer root 的 facts 读侧**（未来 `gt/<case>/facts/` 的消费者入口）——「入口收窄」永远防不住绕行，「**出口全检**」才防得住：无论晋升怎么拷（拷目录、硬编码路径、乃至 F-1 的穿越写入），读出时不过复现门就不能用。这与 R2 的设计哲学完全同构，建议写进晋升接缝单。

---

## 二、A1–A4 逐条结论

- **A1（⭐⭐⭐ 夹具存货方向）**：**有牙**。施工方报对了薄弱处，但实测覆盖面完整（20 维全红 + schema 第二道防线 + R1 真实形状拒写零残留 2 方向实测）；缺的是「固化」不是「牙」⇒ F-2，不阻断。
- **A2（门后失败）**：**质疑成立、实害为零**。残缺/混合目录确实产生（5 组合实测），但 read 全红无一静默——哈希链条结构性兜底 ⇒ F-4，不阻断。
- **A3（R3 边界）**：① 边界可接受（承认如实，工程档下性价比合理）；② 有更结构性做法 = **answer root 读侧同构 verify**（F-5）；③ 实测：**能走到拷目录**（下划线直取 3 行），且发现更强变体 **F-1 穿越写入**。
- **A4（下游代价）**：**可忽略、无环**。真实 sm25（115KB）实测两次：`read_facts_candidate` 全程 **24–25 ms/call**，其中 verify **8.5–8.8 ms**（≈2.0× 纯 parse 的 4.3–4.5 ms，占全程 35–37%）。AnswerCompiler 合理模式（一次编译一次读）下完全无感；即使逐 view 读也只 2×25ms。import 链单向：`gt_facts_staging → gt_revisions → {as_drawn, as_measured, gt_schema, tarch_converter_schema}`，**无任何回边** ⇒ 无循环依赖。**方向**（给 ②-1c，⛔ 本轮不动代码）：编译器生命周期内**缓存 read 出的三对象**（缓存在门后是安全的——缓存的是已过门对象，重放不绕门）；⛔ **禁分层校验/快慢两档**——那会制造第二信任级，恰是「缓存是第二个入口」的老坑。

---

## 三、本审我方实测清单（全部可复现，脚本在 /tmp/o21bT_review/，主树零写入）

| # | 实验 | 结果 |
|---|---|---|
| E1 | 受影响子集三文件 ×2 次 | 52 passed ×2 |
| E2/E2b | 真实 sm25 形状篡改矩阵 20 维 | 18 红（14 verify / 4 schema）+ 2 绿（T14 无害、T15 设计边界） |
| E3 | 真实形状 R1 拒写+零残留（as_signed 篡改 / revisions 逆序） | 2/2 拒绝且目录未创建 |
| E4 | 门后失败注入（ENOSPC × 5 组合） | 残留确实存在；read 5/5 响亮红，0 静默 |
| E5 | A3 绕过：公开面 import * / `_facts_staging_dir`+copytree / `../gt/…` 穿越 / 绝对路径 | 公开面无 Path ✅；其余 3/3 通 |
| E6 | A4 计时 ×2 次 | 24.0–24.5 ms/call 全程；verify 8.5–8.8 ms（2.0× parse） |
| E7 | 基线 worktree + 新测试 7 条 | 7/7 红（AttributeError 型） |
| E7b | 当前代码砍 verify ⇒ 重放 R1/R2 负向 | R1 放行落盘、R2 静默读走（门在干活的直接证据） |

主树 `git status` 跑前跑后皆空；真实 staging 目录全程只读。

---

## 四、给下一单（②-1c / 晋升接缝）的移交清单

1. ⛔ **前置必办**：`case` 名校验（F-1）——一行级修复，越晚修消费者越多。
2. answer root 的 facts 读侧挂同构 verify（F-5 的消费侧门）。
3. AnswerCompiler 生命周期缓存三对象；⛔ 禁分层校验（A4）。
4. 真实形状篡改回归固化 2–3 条进 `test_gt_facts_staging_sm25.py`（F-2）。
5. staging 信任级别 = 0 的口径写进 ②-1c 派工单（F-3：编译产物在重签前不得记成绩）。
