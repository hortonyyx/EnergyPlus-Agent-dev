# GT 候选 → 标准答案 受控转正通道 细稿

> 日期：2026-07-26
> 性质：bounded feature spec；累计式、自包含；只设计，不含实现
> 适用主线：天正转换器产出的 GT v3 候选包 → 人核签字 → `case_tests/test_baseline/gt/<case>/` 标准答案
> 状态标记：`[S]` = 直接采纳；`[M]` = 主控已裁决并写明理由，施工者不得自行改判
> 出稿：主控（Opus 5）。**主控非本批施工方**；本稿即施工契约，GLM 侧核验清单据此另出。

---

## 0. 裁决摘要

### 0.1 本批要交付的能力

一条**可测试、可复现、fail-closed** 的通道，把转换器产出的 GT v3 **候选**（`status="candidate"`）连同人核证据转成受保护根下的**标准答案**（`status="human_verified"`）：

```text
①  源 DXF + request  ──run_p2_conversion──▶  候选包（GT + 渲染 + 审计表 + review_index）
                                              ↑ 状态 BLOCKED：G6 近阈值待人确认 / G10 无签名
②  人看图核对  ──sign CLI──▶  review_ack.json（绑 源图hash / request hash / review_index hash）
③  同一输入 + ack  ──run_p2_conversion 重跑──▶  十门全过、status=PASS、产物逐字节等于 ①
④  PASS 产物 + ack  ──promote API──▶  case_tests/test_baseline/gt/<case>/{gt.json, renders/, 证据}
⑤  load_gt_document(case) 读得到 human_verified 答案
```

### 0.2 为什么本批必须先做「可复现」

[M] **③ 是转换器既有设计的强制环节，不是可选项**：清除 G6 近阈值 pending 的**唯一**路径是「G10 签名通过且 `near_threshold_confirmed=true`」，且该清除发生在 `run_p2_conversion` **一次运行之内**（[`tarch_normalize.py:2446-2452`](../../src/agent/judge/tarch_normalize.py#L2446)）。人签字必然发生在第一次跑之后 ⇒ **必然要带签名重跑一次**才能拿到 `status=PASS`。

[M] 而当前重跑**不可复现**：增广 DXF 每次保存写入新的时间戳/GUID（`ezdxf` 头变量 `$TDUPDATE`/`$TDCREATE`/`$FINGERPRINTGUID`/`$VERSIONGUID`，保存点 [`tarch_normalize.py:1793`](../../src/agent/judge/tarch_normalize.py#L1793) 与 [`:1808`](../../src/agent/judge/tarch_normalize.py#L1808)）→ 增广 DXF 字节变 → `manifest.source_dxf_sha256` 变 → `manifest_sha256` 变 → GT `generator.manifest_sha256` 变 → GT `content_sha256` 变 → **与人签的 `review_index` 声明值不符 ⇒ 签名当场失效**。

⇒ 不做可复现，③ 与 ② 互相否定，通道无法闭合。**本批把可复现作为地基一并交付**，而非留作后续债。

[M] **不接受的替代方案**（施工者不得改走）：
- ✗ 让 promote 自己另写一套「以 ack 清 G6/G10」的判定：判定口径与转换器十门分叉，等于在最高信任资产上引入第二把尺子。
- ✗ 让 promote 接受 `status=BLOCKED` 的报告：转正前提就是十门全过，放宽即假绿。
- ✗ 手工拼装 `gt.json`（改 status + 手算 hash + 拷文件）：零测试、零可复现，正是本项目 2026-07-25 刚查出的治理教训（交付物由未入库代码产出）在最高价值资产上的重犯。

### 0.3 本批不做（明确非目标）

[S] 不改 `load_gt_document` 的 `human_verified` 策略；不放宽 `write_gt_v3_candidate` 的受保护路径拒绝（[`gt_schema.py:673/701`](../../src/agent/judge/gt_schema.py#L673)）——promote 是**另一条**带更强前置条件的独立写路径，不是把候选写入器的门拆掉。
[S] 不改任何 GT 语义、几何算法、转换器十门判定逻辑、立面处理。
[S] 不碰 sm21 既有资产（`gt/sm21_anchor/**` 逐字节不得变）。
[S] 不做 v3 判卷侧墙厚口径接线（另一条债，跑 sm25-L 前接）。
[S] 不做 `§9.2 frame/title 六格`（另一批，「先补门再补锁」）。

---

## 1. 现状事实（施工前必须认的地基，均已由主控实地核过）

| 事实 | 位置 | 含义 |
|---|---|---|
| 候选写入器**拒绝**写受保护根，且只肯写 `status=candidate` | `gt_schema.py:673-701` | 现有 API 无法产出标准答案 |
| 案例读取器**只认** `human_verified` | `gt.py:95` | 候选无法被判卷消费 |
| 全仓**无任何代码**把 candidate 翻成 human_verified | 全仓 grep | 转正通道缺失 = 本批要建的东西 |
| G10 验签机制**已存在且 hash-bound** | `tarch_normalize.py:2240-2292` | 不重写、直接复用 |
| G6 近阈值只能由 G10 签名清除，且在同一次运行内 | `tarch_normalize.py:2446` | 强制「签后重跑」 |
| `review_index.json` 的生成算法**只存在于未入库实验脚本** | `logs/experiments/2026-07-25_sm24_gt_review/build_bundle.py` | 签名的绑定根不可由仓库代码复现 |
| 候选包整目录被 `.gitignore:7`（`20*_*/`）忽略 | `.gitignore` | 用户签收的那批文件不在版本控制内 |
| sm21 既有惯例 = 答案 + `renders/` 8 张图全部入库 | `git ls-files case_tests/test_baseline/gt/` | sm24 转正应产生同构目录 |
| sm24 当前报告 `status=BLOCKED`，G6/G10 红、其余八门绿 | `logs/experiments/2026-07-25_sm24_gt_review/conversion_report.json` | 与 0.1 的 ① 一致，符合预期 |

---

## 2. WP-1：转换可复现（地基）

### 2.1 交付定义

[S] **同一 源 DXF + request + 配置 + 代码**，连续两次 `run_p2_conversion` 到同一内容的 work_dir，必须满足：

1. 增广 DXF **逐字节相同**；
2. `manifest_sha256`、GT `content_sha256`、`conversion_report` 中所有 hash 字段相同；
3. 由该 GT 渲染出的 7 张 PNG **逐字节相同**；
4. `review_index.inventory_sha256` 相同。

[S] 报告/产物中**允许**存在的唯一非确定字段：无。若发现确有不可消除的时间戳（如报告自身记录的生成时刻），必须**显式排除在所有 hash 绑定之外**，并在稿中登记为已知例外——不得以"差异无害"为由留在被 hash 的字节里。

### 2.2 已知非确定源（起点，不是穷尽清单）

[S] `ezdxf` 保存时写入的 `$TDUPDATE`/`$TDCREATE`/`$FINGERPRINTGUID`/`$VERSIONGUID`。

> **2026-07-26 施工方实测结果**（已回灌本稿）：实际变化的是 `$TDCREATE`、`$TDUPDATE`、`$VERSIONGUID`，外加 **`OBJECTS/DICTIONARYVAR/WRITTEN_BY_EZDXF` 里的 ezdxf 写入时间**（本稿原清单未列，属"起点不是穷尽清单"生效的实例）。实测**未**变化：`$FINGERPRINTGUID`、`$TDUCREATE`、`$TDUUPDATE`、`$HANDSEED`、实体数量与句柄顺序。
[S] 施工方**必须先实证**（第一步就做）：跑两次、`cmp` 增广 DXF、把差异字节定位到具体头变量/实体，把**实测清单**写进执行日志。**禁止**凭上述四项猜完事——若还有其它非确定源（句柄分配顺序、集合遍历序、临时文件名、浮点格式化），一并定位并消除。

### 2.3 修法约束

[S] 钉死的取值必须是**输入的确定性函数**，不得写死为常量以外的"当前时间"。推荐：`$TDCREATE`/`$TDUPDATE` 取固定纪元值；两个 GUID 由「源图 hash + request hash」派生（同输入同 GUID、不同输入不同 GUID）。
[S] 钉死点必须**只在转换器写增广 DXF 的路径上**，不得全局 monkeypatch `ezdxf`，不得影响读取任何既有 DXF。
[S] 不得为了让字节相同而**跳过或简化**任何几何/门逻辑。

### 2.4 必红锁

- `R1-1` 两次转换增广 DXF 逐字节相同（正例）。
- `R1-2` 把钉死逻辑 neuter（恢复写当前时间）→ `R1-1` 必须变红。
- `R1-3` **不同**源图 / 不同 request ⇒ 派生 GUID 必须不同（防"钉成同一常量"的假绿）。
- `R1-4` 两次转换 GT `content_sha256` 相同、7 张 PNG 逐字节相同。
- `R1-5` 既有 DXF 读取路径不受影响（既有转换器测试全绿即算，不新增）。

---

## 3. WP-2：候选包组装 + review_index 生成，提升为入库生产代码

### 3.1 交付定义

[S] 新增权威实现（建议 `src/agent/judge/tarch_review_bundle.py` + 一个 `scripts/tool_scripts/` CLI），提供：

- `build_review_bundle(...)`：跑转换 → 写 `gt/gt.json`、`gt/renders/*.png`、`manifest.json`、`conversion_report.json`、`opening_elevation_audit.json`，全部**先写兄弟临时目录、最后一次原子 rename**（沿用现行 §7.2 做法）。
- `build_review_index(files) -> dict`：产出 `tarch_review_index_v1`。

[S] **inventory 公式必须与现行完全一致，不得"顺手改进"**：文件项 `{"path","sha256"}` 按 `path` 排序，
`inventory_sha256 = sha256(json.dumps(files, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8") + b"\n")`。
理由：用户已对该公式产出的值完成一次人核；改公式等于让所有既有签名口径失效。

[S] index 必须含 `inventory_algorithm` 字段（公式的可读声明），与实际实现一致。

### 3.2 必红锁

- `R2-1` 对固定的一组文件重算 inventory = 冻结期望值（fixture 内自建文件，不依赖本地实验目录）。
- `R2-2` 篡改包内**任一**文件一个字节 → inventory 变（逐文件参数化，含 PNG）。
- `R2-3` 文件项少列一个 / 多列一个 → inventory 变。
- `R2-4` 文件项顺序打乱 → inventory **不变**（排序生效）。
- `R2-5` 把排序 neuter → `R2-4` 变红。
- `R2-6` 两次 `build_review_bundle` 产出的 index 相同（与 WP-1 联锁）。

---

## 4. WP-3：签署工具（人签文件的产生）

### 4.1 交付定义

[S] CLI（建议 `scripts/tool_scripts/gt_review_sign.py`）：输入 = 候选包目录、reviewer、签署时间；输出 = 该目录下 `review_ack.json`（`HumanReviewAckV1`，[`tarch_converter_schema.py:928`](../../src/agent/judge/tarch_converter_schema.py#L928)）。

[S] **所有 hash 一律由工具从磁盘现算**，`source_dxf_sha256` / `request_sha256` / `review_index_sha256` / `overlay_sha256` **不得**接受命令行传入。理由：人签的语义是"我看了这批文件"，让人抄 hash 等于把绑定根交给复制粘贴。

[S] 签署前置校验（任一不满足即拒绝出签，非 warning）：
1. `review_index.json` 存在、可解析、`schema == "tarch_review_index_v1"`；
2. **逐文件重算 sha256 与 index 声明相符**（即包自签署时刻起未被改动）；
3. 重算 `inventory_sha256` 与 index 声明相符；
4. `conversion_report.json` 中除 G6/G10 外**八门全绿**（其余门红说明这份包压根没资格给人看）；
5. 若报告 G6 存在 `near_threshold_faces` 非空，则**必须**显式给出 `--confirm-near-threshold`，否则拒签并打印那些面的面积与位置。

[S] `decision` 只允许 `"approved"`；本工具不产生"拒绝"文件（拒绝 = 不签，重做包）。
[S] 已存在 `review_ack.json` 时**拒绝覆盖**（要重签先显式删除，避免静默改签）。

### 4.2 必红锁

- `R3-1` 正例：合法包 → 出签 → 该 ack 能让 `_verify_human_review_ack` 通过（直接调用现有函数验，不另写判定）。
- `R3-2` 包内任一文件被改动后签署 → 拒签（前置 2）。
- `R3-3` index 的 `inventory_sha256` 被改 → 拒签（前置 3）。
- `R3-4` 报告有近阈值面而未给 `--confirm-near-threshold` → 拒签；给了 → `near_threshold_confirmed=true`。
- `R3-5` 八门中任一门为红 → 拒签。
- `R3-6` `review_ack.json` 已存在 → 拒绝覆盖。
- `R3-7` 每条前置**逐条 neuter** → 对应用例变红（防"门写了但没绑"）。

---

## 5. WP-4：受控 promote

### 5.1 接口

[S] `promote_gt_v3(bundle_dir: Path, *, case: str, gt_dir: Path = DEFAULT_GT_DIR) -> PromotionResult`
（建议落 `src/agent/judge/gt_promotion.py`）+ 一个薄 CLI。

### 5.2 前置校验（**全部 fail-closed，任一不满足即 raise，不写任何字节**）

1. `conversion_report.status == "PASS"` 且**十门全绿**（逐门检查，不看汇总字段一个数）；
2. `review_ack.json` 存在、`decision == "approved"`，且经**现有** `_verify_human_review_ack`（或其等价直调）验签通过——**不得另写验签逻辑**；
3. `ack.review_index_sha256 == review_index.inventory_sha256`；
4. 包内**逐文件**重算 sha256 与 index 声明相符；
5. 候选 GT：`load_gt_file` 全量校验通过、`schema_version == 3`、`verification.status == "candidate"`、`case` 与目标一致、`content_sha256` 重算自洽、且等于 `review_index.candidate_gt_sha256`；
6. 目标 `gt_dir/<case>/` **不存在**（已存在即拒绝——不覆盖已签答案；覆盖需人显式移除旧答案）；
7. `gt_dir` 必须是受保护 GT 根或测试显式指定的根；**不得**接受任意路径（防把标准答案写到别处伪装成已转正）。

### 5.3 转正动作

[S] 在内存中由候选 GT 派生已核验文档，**只允许改动三处**：
- `verification.status` → `"human_verified"`
- `verification.reviewer_id` → `ack.reviewer`；`verification.reviewed_on` → 由 `ack.signed_at` 取日期
- `verification.methods` → 记录本批实际使用的方法（`direct_gt_render`、`overlay_on_original_drawing`、`human_source_comparison`）

然后用既有 `canonical_gt_v3_bytes` **重算并写入** `content_sha256`。

[S] **语义不变式（本批最重要的一条锁）**：转正后的文档，除上述 `verification.*` 与 `content_sha256` 外，与候选文档**逐字段完全相同**。几何、洞口、区、墙厚、generator hash 一律不得被 promote 触碰。

### 5.4 落盘布局（与 sm21 惯例同构 + 证据）

```text
case_tests/test_baseline/gt/<case>/
  gt.json                      # human_verified，content_sha256 已重算
  renders/                     # 7 张：gt_plan / gt_elev / overlay_{1f,South,North,East,West}
  review/
    review_index.json          # 签名绑定根
    review_ack.json            # 人签
    opening_elevation_audit.json
    review_annotations.json    # 人给的房间用途注记
    conversion_report.json     # 十门全绿的证据
```

[S] 不入库：源 DXF / 增广 DXF / manifest（源件已在 `gt_sources/<case>/`；增广件可由 WP-1 之后从源图复现）。
[S] 写入必须**原子**：先建兄弟临时目录写全，再一次 rename 成目标目录；任何中途失败不得留下半个目录。
[S] 写入后**自校**：重读 `load_gt_document(case, gt_dir=...)` 必须成功返回 `human_verified` 文档，且 `gt.json` 字节等于写入时的规范字节；自校失败即回滚（删除已 rename 的目录）并 raise。

### 5.5 必红锁

- `R4-1` 正例全链：候选包 → 签 → 带 ack 重跑 PASS → promote → `load_gt_document` 读得到；转正前读同一根返回 `None`。
- `R4-2` **语义不变式**：转正 GT 与候选 GT 的 `model_dump` 除 `verification.*`/`content_sha256` 外逐字段相等。
- `R4-3` 把 promote 改成顺手动一个几何值（neuter）→ `R4-2` 变红。
- `R4-4` 无 ack → 拒。
- `R4-5` ack 的 `review_index_sha256` 不符 → 拒。
- `R4-6` 包内任一文件被改 → 拒（逐文件参数化，至少覆盖 gt.json 与一张 PNG）。
- `R4-7` `status != PASS`（或任一门红）→ 拒。
- `R4-8` 候选 GT 已是 `human_verified` → 拒。
- `R4-9` GT `content_sha256` 与重算不符 → 拒。
- `R4-10` case 名与目标不符 → 拒。
- `R4-11` 目标目录已存在 → 拒，且**原目录字节不变**。
- `R4-12` 原子性：在写入中途注入异常 → 目标根下**不留任何新文件/目录**。
- `R4-13` 自校 neuter（跳过重读校验）→ 需有用例证明该门真绑（例如写入后人为损坏字节应被自校抓住）。
- `R4-14` 上述每条前置**逐条 neuter** → 对应用例变红。
- `R4-15` sm21 既有资产在整批测试运行后逐字节不变。

---

## 6. 禁区（越界即 REWORK）

[S] 不得修改：`gt.py` 的验证状态策略、`write_gt_v3_candidate` 的保护逻辑、转换器十门判定、几何/立面算法、判卷 scorer、`case_tests/test_baseline/gt/sm21_anchor/**`、`gt_sources/**`、`case_data/**`。
[S] 不得放宽任何既有容差或断言以让新测试变绿。
[S] 不得把候选包目录从 `.gitignore` 里放出来（入库的是**转正后**受控目录，不是实验目录）。
[S] 不得在本批内实际执行对 sm24 的转正写入——**转正由主控在轻门通过后亲自运行 CLI**（写受保护根的动作不下放）。

---

## 7. 交付物

1. 生产代码：WP-1 钉死点、WP-2 bundle/index 生成、WP-3 签署 CLI、WP-4 promote API + CLI。
2. 测试：§2.4 / §3.2 / §4.2 / §5.5 全部必红锁；全仓零回归（现基线 **1583 绿 + 10 xfail**）。
3. **neuter 自查表**：每条必红锁 → neuter 什么 → 哪条用例变红 → 是否只红该条。**诚实披露未竟项，禁止伪造**（对标 B4b Phase D / 07-25 立面债批的正面样板）。
4. 执行日志：`AI_agent/logs/reviews/execution/2026-07-26_gt_promotion_path.md`，含 WP-1 §2.2 的**实测非确定源清单**与两次跑的字节比对证据。
5. **实证（供主控向用户请签）**：可复现化之后重跑产出的 GT，与用户 2026-07-25 已验收的那份（`content_sha256 = a1f996f9…`）**逐字段语义 diff**；7 张 PNG 与已验收版的比对结果（相同或差异说明）。**不得为了"看起来没变"而回避报告真实差异。**

   [M] **允许变化集合（主控 2026-07-26 裁定，经实地核对）= 恰好三处**，全部是「增广 DXF 字节变了」的直接派生，非几何/语义变化：
   - `content_sha256`（文档自身指纹）
   - `generator.manifest_sha256`
   - `sources[0].content_sha256` — 实测该字段值等于 `manifest.source_dxf_sha256`（均为增广 DXF 的字节 hash，sm24 上同为 `aef4ee96…`），与上一项同源同因。

   [S] 除这三处外，diff 必须**逐字段全等**，且证明方式必须是**字段级机械比对**（解析后递归比对 / 排除三字段后的规范字节相等），不得以目测或抽样代替。任何第四处差异 = 立即停手上报主控，不得自行判定"无害"。

---

## 8. 已知遗留（本批不解，登记）

- [M] **「可复现」的准确口径 = 同代码 + 同输入 ⇒ 同字节，不是跨代码版本的绝对复现**（主控 2026-07-26 核实）：GT 的 `generator.{extractor,validator,vg_implementation}_sha256` 绑定的是**九个源码文件的字节**（[`gt_schema.py:731`](../../src/agent/judge/gt_schema.py#L731)，含 `gt_extraction.py`/`gt_schema.py`/`gt.py`/`facade*.py` 等），故这些文件任一改动都会改变 GT 的 `content_sha256`。
  - 对本批**无害**：签字 → 重跑 → 转正在同一份代码下一次完成；且「签字与重跑之间若有人改了这九个文件」会导致重跑产物与 index 不符 → **fail-closed 拒绝**，这是正确行为而非缺陷。
  - 长期含义：已转正的标准答案在未来涉及这九个文件的改动后，**不再能由源图重新推导出同一指纹**。因此签名的可验证性口径必须是「拿转正落盘的那批文件重算 hash 对签名」，而**不是**「从源图重新推导同一份」——本稿 §5.4 把签名证据一并落进受控目录正是为此。

- 若 WP-1 之后 GT 内容指纹变化，用户 2026-07-25 的签名失效，**需重签一次**（图与语义不变）。这是可复现化的必然代价，主控已裁定接受。
- `review_index` 只绑文件字节，不绑"人看懂了什么"；语义正确性仍由人核 + 审计表承担。
- 覆盖式重签（同一 case 出第二版答案）本批不支持，只支持"人显式删除旧答案后重新转正"。
