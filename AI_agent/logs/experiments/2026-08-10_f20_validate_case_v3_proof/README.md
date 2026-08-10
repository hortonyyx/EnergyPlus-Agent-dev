# F-20 调查：`validate_case` 重建几何时不传窗宿主凭证 ⇒ v3 路径彻底堵死

- **日期**：2026-08-10 · **席位**：Claude 侧 Sonnet（执行档，只调查不施工）
- **性质**：调查 + 选项对比，**零生产码改动，零 LLM 成本**
- **可复跑脚本**：[`probe_f20.sh`](probe_f20.sh)（只读，所有改动只发生在 `mktemp -d` 出的临时目录，运行完自动清理；可重复执行）
- 本报告里每一条结论后面都标了证据来源：文件:行号、git 提交号、或 `probe_f20.sh` 里的编号小节

---

## §0 防假调查自检（动手前先答）

**1. 证据是读盘/跑脚本量出来的，还是从代码形状推出来的？**
全部是读盘 + 跑脚本量出来的：`git log -S` / `git show` / `git blame` 找提交原文；`sha256sum` 比对字节；
在 `/tmp` 里对一份真实产物的只读副本跑 `validate_case(...)` 拿真实返回值；对同一份副本做篡改再跑一遍看结果变不变。
零处使用"代码形状看起来应该是……"这类推理性断言。

**2. "只读 stage 根"设计的理由，是从当前源码猜的，还是从引入它的提交读到的？**
是从提交读到的，而且是**两次独立读到，对应两个不同的历史决定**（详见 Q1）：
① `06d01a0`（2026-06-16）"never bind an approval to stale/garbage bytes"——这是**校验一致性**的理由；
② `963d952`（2026-06-16）"a distinct filename … cannot masquerade as, or clobber, the audit manifest"——这是**不覆写审计账本**的理由。
两条都不是"避免新耦合"，也不是"没人敢用"。原始设计意图（`0d267bf`，06-15 立项 M0-M4）是"非侵入式离线审计面"——
能对**任何**在盘上的 run 目录跑,不要求这个 run 目录一定经过后来才出现的 manifest/attempts 机制。

**3. "某测试没覆盖 v3"是怎么数的？**
`grep -c "validate_case(" <file>` 确认该文件确实调用 `validate_case`，再 `grep -c 'schema_version.*3\|"3"'` 和
`grep -c -i "correction_b5\|b5_v1"` 数 v3/B5 命中。凡命中数非零的都手工打开上下文核实是否真的在构造 v3 correction 输入
（不是"文件名形状像"就算数——`probe_f20.sh` §10 的确切命令见下，过程中我曾在 `test_run_pipeline_self_checks.py` 里抓到一次
"window_host_proof"字符串命中,打开一看是给**旧版 legacy 内核检查签名**的 monkeypatch fake,`window_host_proof=None` 且断言
它必须是 None——与 v3/B5 真实场景无关,已排除,不计入"覆盖"）。

---

## Q1（最高优先）｜"只读 stage 根"在为哪份契约服务

### 结论：两条独立的历史设计决定,都不是"advisory 没人敢用"那类理由,都可原文引用

**证据链（`git log -S` + `git show`，见 `probe_f20.sh` §1）：**

`correction_geometry_snapped.json` 这一读取行,自 `validate_case` 模块诞生（`0d267bf`,2026-06-15,
"6.15_ValidationArchM0toM4"）起从未被其他提交改动过（`git log -S"correction_geometry_snapped.json" -- validation_run.py`
只命中这一个提交）。这个模块本身,连同它要读的 manifest/attempts 机制,是**同一个提交同时建立的**——
build plan 原文（[`AI_agent/archive/pipeline_validation_build_plan.md:128`](../../archive/pipeline_validation_build_plan.md)）写明
`validate_case` 是"**M4 capstone**",定位是"非侵入式跑全段 gate①、不动 `run_pipeline`"。
decision_log 里事后也有一句更直白的定性（`decision_log.md:32`）："`validate_case` 是与 inline 生产门**并列的离线审计面**"。

**这句定位不是空话——它有一个至今仍在生效的真实后果**：本仓库现存 **5 个 run 目录完全没有 `_run/run_manifest.json`**
（`sm20_anchor/run_2026-06-15_baseline`、`sm21_anchor/run_2026-06-16_opus_e2e`、
`run_2026-07-01_sonnet_e2e_r1`/`_r2`、`run_2026-07-09_haiku_prescan_triage`；命令见 `probe_f20.sh` §9),
其中前两个正是 `tests/test_validation_run_baseline.py` 当前使用的 **golden 正基线**（`sm20_anchor's golden RUN`
`sm21_anchor: 2-floor golden RUN`,该文件顶部注释可查）。`load_run_manifest()` 对这些目录返回 `None`
（已实测,§1 输出 `load_run_manifest on sm20 golden anchor -> None`）。**这意味着"非侵入、不强制要求 manifest 存在"
这条设计,今天仍在保护 2 个仍在用的 golden 测试基线,不是历史包袱。**

再往细看,"只读 stage 根"具体是两句不同注释、两次不同提交引入的,不能合并成一句话：

① **`validation_run.py:304-306`**（"never bind an approval to stale / unchecked bytes"）
—— 引入提交 `06d01a0`（2026-06-16,"6.15_ValidationFixReverify"）。提交原文：

> "High 1 (remaining): validate_case still passed BAD/stale on-disk 2/3 artifacts and bound an approval
> digest to those unchecked bytes. … validate_case reconciles the committed building_geometry.json +
> geometry_specs.md against the deterministic rebuild from snapped correction geometry — a mismatch blocks
> … The geometry digest is computed ONLY after the on-disk 2/3 artifacts pass consistency and 2_modelling
> passes, so an approval can never bind to stale/garbage bytes."

**这条的真实用途 = 防止 approval 签给一份陈旧/被篡改的 `building_geometry.json`**，做法是用
"从 `1_correction/correction_geometry_snapped.json` 重建的几何"去核对磁盘上的 2/3 产物是否一致
（`kernel.artifact_consistency`）。**它从来没有讨论过"要不要走 manifest 拿 accepted attempt"这件事**——
因为写这条注释的时候（06-16）,manifest/attempts 系统昨天（06-15）才刚被建出来,而
`load_verified_accepted_correction` 这个"信任根加载器"要到 **一个月后的 07-19**（`e645d63`,B5 Phase D）才出生。
即"是否耦合 manifest"这个问题在 06-16 根本不存在选项,这条注释回答的是另一个问题。

② **`validation_run.py:324-326`**（"A validation SUMMARY — NOT the M0 audit manifest … distinct filename
so it cannot masquerade as, or overwrite, run_manifest.json"）—— 引入提交 `963d952`
（2026-06-16,"6.15_ValidationFixCodexReview"）。提交原文：

> "H2: write_reports no longer fabricates/overwrites the M0 audit run_manifest.json. It writes a distinct
> validation_manifest.json (a summary), so it cannot masquerade as, or clobber, the append-only-attempt-backed
> audit manifest."

**这条管的是 `validate_case` 自己的输出**（它写 `validation_manifest.json` 不能覆盖/冒充 `run_manifest.json`),
**不是它的输入**。F-20-A 引用的正是这条注释,但它回答的问题是"我这次跑完写的东西会不会把审计账本冲掉",
不是"我这次跑之前要不要先读审计账本"。

**⇒ 结论：F-20-A 说"『只读 stage 根』是有意设计,不是疏忽"这句话本身没错,但它把两个不同的"有意"焊在了一起**——
一个是"digest 只能算在校验过的字节上"（真实存在、今天仍然对，且与"读不读 manifest"无关）,
一个是"我的输出文件名不能撞审计账本"（真实存在、今天仍然对，且与"读不读 manifest"也无关）。
**"validate_case 不读 run_manifest.json 来解析 accepted attempt"这件事本身,没有任何一次提交的原文专门论证过**——
它是"非侵入式离线审计面"这个更大设计选择的**副产品**,而这个更大选择今天仍有 2 个真实 golden 基线依赖它。

**它今天还在防什么？**——防的是"如果必须有 manifest 才能跑,老的/手搓的/`--intake-from` 之类的 run 目录会直接报错
而不是被审"。它没有在防"篡改"——这恰恰是 Q3 要害的地方：**stage-root 直读路径本身对篡改零抵抗力**（见 Q3 的
篡改实测）。这条设计从"要不要有 manifest"这个问题上是安全帽,从"篡改"这个问题上完全不是盾牌,
`F-20-B`/`F-20-C` 提到的"耦合 manifest"担忧,答的其实是后一个问题,不是前一个。

**⛔ 我没能证实的部分**：`802822f`（07-06,把 `build_geometry(geom)` 改成 `build_geometry(geom, capability_profile=profile)`
的那次提交）本身的 commit message 只字未提"要不要给它接窗宿主凭证"——那时 `window_host_proof` 这个参数还不存在
（07-18 才加）。所以 F-20 §1 表格里"调用方写法 07-06"这句只是**时间戳事实**（这行代码最后一次被有意修改是那天），
不代表 07-06 那次提交"选择了"不传 proof——**它没得选，proof 这个概念当时还不存在**。这点原派工单没写清楚，这里补上。

---

## Q2｜v3 重建到底缺哪些件，每件在盘上的哪里

**实测表**（针对 `run_2026-08-09_f18_e2e_verify`，命令见 `probe_f20.sh` §4；byte-level sha256 见同节）：

| 件 | stage 根（`1_correction/`） | attempt 目录（`1_correction/attempts/001/`） | `_run/` |
|---|---|---|---|
| `output.json`（= v3 correction geometry） | ✅ 镜像为 `correction_geometry_snapped.json`（sha256 逐字节相同） | ✅ `output.json` | — |
| `feature_states.json` | ❌ **不存在** | ✅ | — |
| `window_resolver_inputs.json` | ❌ **不存在** | ✅ | — |
| `window_hosts.json` | ❌ **不存在** | ✅ | — |
| `audit.json` | ✅ 镜像为 `corrections.json`（sha256 逐字节相同） | ✅ | — |
| `view_manifest.json` | — | — | ✅ `_run/view_manifest.json` |
| `run_manifest.json`（含 accepted_attempt + 六件套哈希） | — | — | ✅（但 `validate_case` 从不读它，见 Q1/F-20-A） |
| `0_reading/*.json`（原始识图产物，proof 重验要用） | ✅（就在 run 根 `0_reading/`，不在 attempt 里） | — | — |

**镜像机制的根源**（[`stage_runner.py:560-563`](../../../src/agent/execution/stage_runner.py#L560)）：

```python
if is_correction_write:
    # Convenience copies are promoted only after gate acceptance.
    (stage_dir / "correction_geometry_snapped.json").write_text(out_text, encoding="utf-8")
    (stage_dir / "corrections.json").write_text(_to_json(output_obj.audit_payload), encoding="utf-8")
```

**只有这两个文件被镜像到 stage 根，`feature_states.json` / `window_resolver_inputs.json` / `window_hosts.json`
三个 B5 专属文件从来没有被镜像过**——这不是这个 run 特有的巧合，是 `stage_runner.py` 里唯一的镜像逻辑就只写这两行。
`VerifiedWindowHostProof` 需要的恰恰是后三者中的两个（`window_resolver_inputs.json` + `window_hosts.json`，
外加 `output.json`，见 [`build.py:37-45`](../../../src/agent/geometry/build.py#L37)），
所以**即使 `validate_case` 愿意"多读几个 stage-root 文件"，今天 stage 根上物理上也凑不出一份完整的 proof 素材**——
必须去 attempts 目录拿（Option ②"镜像更多文件到 stage 根"因此不是"改一行"，而是要新增至少 3 处镜像逻辑）。

---

## Q3｜两条改法的防篡改强度到底差多少（岔口重描）

### 岔口的准确描述（推翻上一轮 plan.md 里的措辞）

不是"① 耦合 manifest（新耦合）vs ② 多一处副本（新副本）"——F-20-B/C 已经证明这两个副作用本来就存在
（`load_verified_accepted_correction` 已有 7 个生产调用点、镜像机制本来就在写两个文件）。**真正的岔口是**：

- **选项①**：`validate_case` 在能找到 `_run/run_manifest.json` 时，改走 `load_verified_accepted_correction(run_dir=, manifest=)`
  取得 proof（对没有 manifest 的旧 run 走原样的 legacy 行为，见下方"第三条路"）。
- **选项②**：把 `feature_states.json` / `window_resolver_inputs.json` / `window_hosts.json` 也镜像到 stage 根
  （在 `stage_runner.py:560` 那两行旁边再加三行），`validate_case` 继续直接读 stage 根，从不碰 manifest。

### 攻击面实测（`probe_f20.sh` §7/§8，我自己动手验证，没有直接采信派工单的"proof 会自校验"）

**实测①：只篡改 stage-root 的一个非几何字段（`windows[0].room`），不碰 attempt 目录、不碰 manifest**——
`1_correction` 的 17 项检查里，**除了本来就因缺 proof 而 FAIL 的那两项，其余全部 PASS/NOT_APPLICABLE**，
包括 `correction.facade_frame_cross_check`（这是几何一致性的主力检查，我第一次用改窗跨度 5 米的篡改试探时
它确实会 FAIL，但换成只改 `room` 这个纯标签字段后，它照样 PASS）。**⇒ 今天的设计（也是选项②的设计），
对"篡改一个不影响几何校验的字段"零抵抗——不是因为 proof 机制弱，是因为 proof 机制根本没被摆在这条防线上；
挡不挡得住纯粹看运气（篡改是否恰好撞上另一条无关的几何检查）。**

**实测②：同样的篡改（改一个字段），但改在 attempt 目录的 `output.json` 上，走 `load_verified_accepted_correction`**——

```
EXPECTED: load FAILED — ValueError - accepted 1_correction output.json hash does not match manifest record
```

**逐字节哈希绑定，100% 必中，不依赖"篡改是否恰好影响几何"。**

**⇒ 结论：选项①比选项②在防篡改上是严格更强的，不是"强度不同各有取舍"，是选项②在这件事上基本等于没有防线**
（它唯一的防线来自其他检查偶然命中，选项①的防线是密码学哈希比对,类型不同,强度也不同)。
这一点原派工单的提示"proof 是自校验的… 但请自己验证",我已亲手验证：proof 自校验的是 `window_hosts.json`
的 claims 内部是否与几何一致（`_reverify_window_host_proof` 重算 claims），**不是** stage-root 的 `output.json`
是否等于 accepted attempt 的 `output.json`——这是两件不同的事,选项②不会自动获得选项①的哈希绑定。

### 轴 B 风险（同一事实两处声明,各自漂）

**选项②会新增轴 B 风险，选项①不会。** 选项②要在 `stage_runner.py:560` 旁边新增 3 处镜像写入，
这样 `output.json`/`feature_states.json`/`window_resolver_inputs.json`/`window_hosts.json` 四个文件
**每个都会有两份物理拷贝**（attempt 目录 + stage 根），今后任何touch这段写入逻辑的改动都必须**同时**改五处
才能保持同步（现在 `stage_runner.py` 只镜像两个文件都已经是手写的，不是自动生成的）——这正是
`06d01a0`（06-16）修的那个 bug 的同型：**"磁盘 2/3 产物可能与重建结果不一致"，本质就是"同一份东西存了两份，
一份没跟着更新"。选项②是在制造第二个这种缺口，只是换了一层（1/2_modelling → 1_correction 的 B5 素材）。**
选项①不涉及任何新副本——`validate_case` 只是多了一条"如果 manifest 在,就用它去读 attempts 目录里唯一的那份"的
读取路径，没有新写入、没有新副本。

### legacy blast radius 实测（`probe_f20.sh` §9）

`load_run_manifest()` 对 `sm20_anchor/run_2026-06-15_baseline`（golden 正基线,`test_validation_run_baseline.py`
当前在用）返回 `None`。**如果选项①被不加区分地实现成"validate_case 一律要求 manifest 存在才能继续"，
这两个 golden 正基线测试会当场变红**（`sm20_anchor` 和 `sm21_anchor/run_2026-06-16_opus_e2e` 各一个）。
**这是选项①必须避免的 blast radius，不是选项①本身有缺陷——只要做成"manifest 存在则走它、不存在则退回今天
的 legacy stage-root 行为"这种条件分支，就不会触发。**这个条件分支的写法在同一个文件里已经有一次先例
（`validation_run.py:163-168`：`_run/view_manifest.json` 不存在时标 `NOT_APPLICABLE("run predates the view
manifest wire")`，存在时才校验)——**这不是要发明新模式，是照抄这个文件里已经用过一次的模式。**

---

## Q4｜改法之外还有没有第三条路

**有，而且它和"该不该耦合 manifest"是两个独立的维度，可以叠加在选项①或②之上：**

现状（[`validation_run.py:253-256`](../../../src/agent/execution/validation_run.py#L253)）：

```python
except Exception as e:  # noqa: BLE001 — recorded as a blocking error report
    geometry_consistent = False
    res.reports["2_modelling"] = _error_report("2_modelling", profile, run_profile,
                                                f"kernel build failed: {e}")
```

这个 `try` 块从 `build_geometry(...)` 一路包到 S3 的 `geometry_specs.md` 比对（第 210-252 行），**任何异常
都会被压成同一句"kernel build failed: {e}"**，不区分"内核真的有 bug"和"proof 结构性拿不到"。
今天恰好因为异常消息里带了原始 `ValueError` 的文本（"v3 build requires VerifiedWindowHostProof"），
人眼还能看出是哪种情况，但这是偶然的——如果哪天这条消息被改了措辞，诊断信息就丢了。

**第三条路 = 在这个 `except` 之外，专门侦测"这是 v3/B5 但拿不到 proof"这一种情况，给它一个独立的 check_id
和 NOT_APPLICABLE/BLOCK 状态**（例如 `2_modelling.window_host_proof_unavailable`），而不是让它落进
"kernel build failed"这个大而化之的错误桶。**这件事和选择①还是②无关——不管选哪个改法，只要拿 proof
这一步可能失败（比如 manifest 存在但某个 hash 对不上），都应该有这么一个专门出口，不然故障永远伪装成
"内核坏了"。** 这与 F-9 那次登记的教训同型：现在的失败信息把根因藏住了。

---

## Q5｜为什么 2345 绿一条没抓到

**数法（`probe_f20.sh` §10，逐条给出确切命令）**：先用 `grep -rl "validate_case(" tests/*.py` 找出**全部**调用
`validate_case` 的测试文件——这一步比派工单多找到 2 个文件（派工单只列了 3 个）：

```
tests/test_validation_run_baseline.py   (18 处调用)
tests/test_run_stage_flow.py            (4 处调用)
tests/test_check_parity.py              (1 处调用)
tests/test_reading_ruler_r1_batchB.py   (1 处调用)   ← 派工单未列
tests/test_run_pipeline_self_checks.py  (2 处调用)   ← 派工单未列
```

对这 **5 个文件**（不是 3 个）逐一 `grep -c 'schema_version.*3\|"3"'` 和 `grep -c -i "correction_b5\|b5_v1"`：
**全部为 0**。`test_run_pipeline_self_checks.py` 里有 2 处 `window_host_proof` 字符串命中，打开看是
`_patch_kernel_check_non_pairing_blocker` 里一个 monkeypatch 假 `check_kernel`，签名里带
`window_host_proof=None` 并断言它必须是 `None`——这是给**旧内核检查签名**站桩用的假函数，从不构造真实
v3 几何，与 B5 proof 场景无关，**已排除，不计入覆盖**。

**⇒ 结论比派工单更完整：不是 3 个文件 0 覆盖，是全部 5 个调用 `validate_case` 的测试文件 0 覆盖。**
这解释了为什么 2345 绿一条抓不到——`validate_case` 这条路径上，从没有任何测试构造过一个
`schema_version="3"` 的 accepted correction 去跑它。

**最便宜的正向锁长什么样**：不需要新造夹具机制。`tests/test_c2_b5_artifact_trust.py` 里已经有一个现成的
`_accepted(tmp_path)` 辅助函数（第 39-66 行），它用 `StageRunner(tmp_path, manifest).record(...)` 把一份真实
（程序化构造的）v3/B5 correction 写成一个货真价实的 accepted attempt，外加 `_run/view_manifest.json` 和
`0_reading/*.json`。**最便宜的锁 = 导入这个辅助函数（或搬一份到 validate_case 的测试里），调用它拿到
`tmp_path`，再调 `validate_case(tmp_path, policy=RunPolicy(capability_profile="orthogonal_polygon"))`，
断言 `res.reports["2_modelling"]` 里不出现"VerifiedWindowHostProof"这句话。** 今天这行断言会失败
（因为 F-20 尚未修），这正是"回归用例必须自证前提"那条纪律要的效果——先证明它在今天会红。

---

## Q6｜真实产物能否当夹具

**体积**：整个 run 目录 2.0M（`0_reading` 424K + `1_correction` 676K + `2_modelling` 176K +
`3_split_pairing` 52K + `_run` 24K + `manual_review` 692K + 其余）。**`manual_review` 里是人核用的
渲染图，机器夹具不需要，砍掉后约 1.3M。** 作为一条测试夹具体积完全可以接受。

**08-09 登记的坑，我重新实测并且比原登记的范围更大**：

```
EXPECTED: parse_correction_draw rejects the real artifact as-is — WindowResolverInputError :
producer_segment_ref_prefilled: {}
```

**第一个拦下它的不是 `floor` 字段，是 `facade_segment_id`**（`windows[*].facade_segment_id` 被标记为
`CORRECTION_DRAW_FORBIDDEN`）。完整清单（用 schema 自己的标记表现查，不是靠猜)：

```
FORBIDDEN fields (must be stripped for front-door replay): {'windows': ('facade_segment_id',)}
DERIVED fields (must be stripped for front-door replay):   {'windows': ('floor',)}
```

**即：如果要把这份真实产物重放进"模型刚画完、走 `parse_correction_draw` 原始产出校验"这条前门路径，
需要对每个 window 剥离 `facade_segment_id` 和 `floor` 两个字段（不是只有 `floor` 一个）**，这两个都是
schema 明确标记的封闭集合（不是开放式排查），成本很小。

**但这条前门路径不是唯一选项，很可能也不是必要的**：Q5 提到的 `_accepted()`/`StageRunner.record()` 模式,
走的是"直接把一个已经通过 `model_validate` 的 `CorrectedGeometryV3`/`FinalizeResult` 对象交给
`StageRunner.record()`"，**完全不经过 `parse_correction_draw` 的原始 payload 校验**，因此也不会撞上
`facade_segment_id`/`floor` 这两个字段的封禁。如果只是要让 `validate_case` 在这份真实几何上重新走一遍，
用 `ensure_corrected_geometry()`（`validate_case` 自己用的加载器）读取本来就没问题——我在 Q3 的篡改实验里
已经这样读取过整份真实文件很多次，从未触发这两个封禁。**⇒ "落盘文件不能直接重放"这条坑,只在"想让它假装
是模型刚画出来的新草稿"这条路径上才存在;只是当"已被接受的历史几何"直接喂给 validate_case 或
`StageRunner.record()`,不受影响。**

**⛔ 我没能证实的部分**：我没有实际搭建一个完整的"用这份真实产物构造出 `_run/run_manifest.json` +
`1_correction/attempts/001/*` 六件套"的端到端可跑通夹具（即没有真正把 Q5 提议的锁跑绿过一次）——
这需要修一部分生产码（或至少验证 Q4/Q1 选定的修法）之后才能真正验证"这份真实产物能通过 validate_case
而不报错"，而派工单明确禁止修生产码。我只验证了它今天会以什么方式失败、以及构造/剥离字段这两件事各自的
可行性，没有验证"修完之后它真的会绿"。

---

## 岔口重描对比表

| | 选项①：`validate_case` 有 manifest 时走 `load_verified_accepted_correction`（无 manifest 时退回今天行为） | 选项②：把三个 B5 文件也镜像到 stage 根，`validate_case` 继续只读 stage 根 |
|---|---|---|
| **防篡改强度** | 逐字节 sha256 与 manifest 记录绑定，任何篡改必被抓（已实测：改一个非几何字段的 attempt 文件 100% 被拒） | **无绑定**——只有"篡改恰好撞上另一条无关几何检查"才会被发现（已实测：改 `room` 字段全绿通过） |
| **轴 B 风险** | 无新副本（只多一条读取路径） | **有**——四个文件各自多一份物理拷贝，未来任何 touch 写入逻辑的改动必须同时改 5 处才能保持同步，与 `06d01a0` 修的 bug 同型 |
| **legacy blast radius** | 若不加区分地强制要求 manifest，会打红 2 个 golden 正基线（`sm20_anchor`/`sm21_anchor` 各一）；**加"manifest 不存在则退回原行为"分支即可避免**（本文件已有先例：`view_manifest.json` 的处理） | 无 blast radius（legacy 走 `is_b5=False` 分支，proof 本来就该是 None，不受影响） |
| **实现成本** | 中——`validate_case` 需要 `load_run_manifest(run_dir)` + 条件分支 + 调 `load_verified_accepted_correction`；`0_reading` 与 `_run/view_manifest.json` 已经在 stage 根 / `_run/` 上，不需要额外搬运 | 中——需要在 `stage_runner.py:560` 附近新增至少 3 处镜像写入，且要保证这三份镜像"促成/晋升(promote)"的时机与两个已有镜像一致（只在 accept 之后才写） |
| **需要几把锁** | 1 把正向锁（v3 accepted attempt → `validate_case` 不报 proof 缺失） + 1 把 legacy 回退锁（无 manifest 的 run 走原行为不受影响，即 golden 基线不变红) | 1 把正向锁（同上） + 1 把"三份镜像与 attempt 目录逐字节一致"的锁（否则镜像本身可能悄悄漂移，需要单独的一致性检查） |
| **与既有代码风格的一致性** | 高——复用本文件里已有的"manifest 存在则用、不存在则 NOT_APPLICABLE"模式（`view_manifest.json`），复用已有 7 个生产调用点都在用的同一个受信加载器 | 中——`stage_runner.py` 目前只镜像 2 个文件是特例（为了 `validate_case` 的历史某个需求），再加 3 个会让"哪些文件被镜像"这件事更难一眼看懂为什么 |

---

## 推荐 + 需要用户拍板的点（大白话）

**背景**：现在项目里有一套"审计员"代码（`validate_case`），它的工作是拿一个跑完的项目文件夹，
自己重新算一遍几何，跟文件夹里已经算好的结果对一对，看有没有被人动过手脚或者算错。这个审计员在 6 月中旬
出生的时候，故意设计成"不管这个文件夹是怎么来的，我都要能审"——包括很老的、没有走过后来才建的"记账系统"
的文件夹。这个设计到今天还有用：仓库里还有两份很老的标准答案文件夹，正是靠这条设计才能被继续测试用。

**问题**：7 月中旬，项目给"窗户装在哪面墙上"这件事加了一道新的安全锁（叫"窗宿主凭证"），规定只要是新版本
的几何（v3），审计员在重新计算之前，必须先拿到这份凭证，不然不让过。但是"审计员该去哪里拿这份凭证"这件事，
当时没人接上——负责重算的那行代码到今天都还是"不给凭证"，所以审计员一碰到任何 v3 产物就直接报错，
整条新版本的审核路径完全走不通（连人工手动确认也走不通，因为人工确认和自动确认走的是同一段代码）。

**能拿到凭证的地方现在只有一处**：项目里专门给"接受"下来的记录留了一个文件夹，装着凭证需要的三份材料。
审计员目前压根不去看那个文件夹，只看旁边一个"方便拷贝"的位置——而那个"方便拷贝"的位置，恰好没人把这三份
材料拷过去（只拷了另外两份不相关的材料）。

**两个选项**：
- **选项①（推荐）**：让审计员去看那个正式的"记录"文件夹，但只在这个文件夹存在的时候才这样做——
  老的、没有这个文件夹的项目，审计员还按老办法审，不受影响。
  好处：这个"记录"文件夹里的每一份材料都绑了一个防伪校验码，谁篡改了任何一个字都会被立刻抓到。
  代价：需要改审计员的代码，让它多一步"先看看有没有记录文件夹，有就去读，没有就按老办法"。
- **选项②**：不改审计员的代码，改成把那三份材料也复制一份放到审计员本来就在看的那个"方便拷贝"位置。
  好处：审计员自己的代码完全不用动。
  代价：实测过，这样做**基本没有防伪能力**——我复制了一份材料到那个"方便拷贝"位置后又偷偷改了一个字，
  审计员完全没发现，跟没改一样通过。而且以后这份材料要更新的时候，两份拷贝必须一起改，
  漏改一份就会重新製造"两份记录各说各话"的隐患（项目历史上正好因为这类问题栽过一次跟头，就是这套审计员
  最早被建出来时修的那个 bug）。

**我的推荐 = 选项①。** 理由：它更安全（有真正的防伪能力），不会破坏两份还在用的老测试基线（只要加一个
"没有记录文件夹就按老办法"的判断，这个判断项目里已经用过一次一模一样的写法，不是发明新东西），
而且不会制造"materials 存两份、以后必须记得一起改"这种新的隐患。选项②表面上代码改得更少，
但换来的是一个几乎没有实际效果的安全措施，还埋了一个新坑。

**需要用户拍板的点**：
1. 是否同意走选项①（推荐），而不是选项②？
2. 除了修这个"拿不到凭证就报错"的问题之外，要不要顺手把"报错信息说不清楚到底是内核真的坏了、
   还是仅仅是凭证没拿到"这件事也一起修掉（本报告 Q4，是个独立的小修法，不影响选①还是选②）？
3. 是否同意"这个真实产物（`run_2026-08-09_f18_e2e_verify`）瘦身后（去掉人核用的渲染图，约 1.3M）
   可以入库做回归测试夹具"，还是希望改用 Q5 提到的"程序化构造的最小夹具"（体积更小，但不是真实产物）？
   两者不互斥，可以都要。

---

## 我没能证实的部分（宁可留白）

1. **Q1**：`802822f`（07-06）那次提交本身，commit message 完全没提"proof"或"是否要接凭证"——因为那时
   `window_host_proof` 参数还不存在。所以不能说 07-06 那次"选择了不传 proof"，只能说那行代码最后一次
   有意修改的日期是那天，"选择"这个词不成立（详见 Q1 结尾）。
2. **Q6**：没有实际搭出一个完整可跑通的"真实产物 → 六件套 accepted attempt → `validate_case` 通过"端到端
   夹具并跑绿——这需要先落地 Q1/Q4 的修法，而派工单明确不许我碰生产码，所以这一步只做到"验证了失败模式
   和字段剥离的可行性"，没有验证"修完之后真的会绿"。
3. **没有重新跑全仓 2345 条测试**——派工单 §0 给定的全仓基线（2345 passed/10 xfailed/0 failed）我视为已核实
   的既定事实，直接复用，没有重新花时间跑一遍（跑这一遍也不会改变 Q1-Q6 任何一条结论）。
4. **`load_verified_accepted_correction` 生产调用点数量**：派工单 F-20-B 说"已有 6 处"，我数出来是 **7 处**
   （`output_coordinates.py` ×2、`correction_audit.py` ×1、`scripts/tool_scripts/run_stage.py` ×4）——
   我没有进一步去确认这 7 处里是否有些互相调用导致"实际独立入口"少于 7，只是给出 grep 到的调用表达式计数，
   如果需要精确的"独立入口数"需要再逐个读调用关系。
