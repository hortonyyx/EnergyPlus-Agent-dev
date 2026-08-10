# orchestrator 轻门 · F-20 调查（Claude 侧 Sonnet 出品）

- **日期**：2026-08-10 · **裁决人**：orchestrator（Opus）· **被审对象**：
  [`experiments/2026-08-10_f20_validate_case_v3_proof/README.md`](../../experiments/2026-08-10_f20_validate_case_v3_proof/README.md)
  + `probe_f20.sh`
- **性质**：调查单（零生产码改动）⇒ 轻门 = **独立复核承重命题 + 补测缺失的对照**，不是 diff 审
- **裁决**：**PASS**（0 BLOCKER / 0 MAJOR / 2 NIT，均已在本裁决内当场处理）

---

## 1. 独立复核的承重命题（⛔ 未采信施工席自述，逐条自己量）

| # | 命题 | orchestrator 独立复核 |
|---|---|---|
| **①** | `06d01a0` 的 "never bind an approval to stale/garbage bytes" 讲的是**approval digest 只能算在校验过的字节上**，与「读不读 manifest」无关 | ✅ **原文属实**。自己 `git show -s` 读了全文：该条修的是「validate_case 曾把 approval digest 绑到未经校验的磁盘 2/3 产物上」，做法是拿 snapped 重建去核对磁盘产物。**通篇未讨论 accepted attempt 解析。** |
| **②** | `963d952` 的 "cannot masquerade as … run_manifest.json" 管的是 `validate_case` **自己的输出文件名**，不是它的输入 | ✅ **原文属实**：「write_reports no longer fabricates/overwrites the M0 audit run_manifest.json … writes a distinct validation_manifest.json」。确系输出侧。 |
| **③** | 5 个 run 目录完全没有 `_run/run_manifest.json`，其中 2 个是 `test_validation_run_baseline.py` 在用的 golden 正基线 | ✅ **完全属实**。独立枚举得同样 5 个；`tests/test_validation_run_baseline.py:24` = `run_2026-06-15_baseline`、`:213` = `run_2026-06-16_opus_e2e`，两者均在无账本之列。 |
| **④** | stage 根只镜像 2 个文件；proof 所需的三个 B5 件**从未被镜像** | ✅ **属实**。`stage_runner.py:560-563` 是全文件唯一镜像逻辑，只写 `correction_geometry_snapped.json` 与 `corrections.json`。 |
| **⑤** | 选项②对「篡改一个不影响几何的字段」零抵抗；选项①逐字节哈希绑定必中 | ✅ **亲自重跑探针复现**：stage 根改 `windows[0].room` ⇒ 17 项检查无一变化；attempt 目录同样改动 ⇒ `ValueError: accepted 1_correction output.json hash does not match manifest record`。 |
| **⑥** | 探针的比较是否公平（两侧篡改的不是同一个文件） | ✅ **设计是对的**：两侧各篡改**在该方案下当权威的那一份**（选项②权威=stage 根，选项①权威=账本绑定的 attempt）。这不是苹果比橘子。 |

---

## 2. NIT-1（精度）：加载器出生日期写错，结论不受影响

报告写 `load_verified_accepted_correction` 「要到 07-19（`e645d63`, B5 Phase D）才出生」。
**实测：该函数生于 `ccb396e`（2026-07-14）**；`e645d63`（07-19）加的是它的 **B5 签发分支**。

⇒ 承重论证（「06-16 时这个选项还不存在」）**不受影响**（07-14 仍晚于 06-16）。仅精度问题，本裁决更正。

## 3. NIT-2（已由 orchestrator 当场补测）：Q3 §7 缺「未篡改」对照

原探针 §7 只打印**篡改后**的检查清单，靠「看起来全 PASS」推出「篡改不可见」——
**这是推断，不是测量**（正是「回归用例必须自证前提」那条纪律要防的形态）。

**orchestrator 补跑对照**（干净副本、同样格式）：

```
未篡改：17 项 —— window_host_resolution FAIL · evidence_debt_coverage FAIL · 其余 PASS/N_A
篡改后：17 项 —— 逐条完全相同
```

⇒ **「篡改不可见」由推断升级为实测**；同时确认 `evidence_debt_coverage` 那条 FAIL
**是先前就有的、与篡改无关**（报告称「两项 FAIL 都是本来就有的」，属实）。

## 4. ⭐ orchestrator 另外查到的一条：探针 §6 里有一条**假阳性**

探针 §6 的 blocking 清单里有：

```
reading.view_manifest_coverage — view manifest drift (content_sha256 mismatch ...)
```

**这是探针自己复制 run 目录造成的假阳性**：orchestrator **原地**（未复制）跑同一个 `validate_case`
⇒ `reading.view_manifest_coverage` **PASS**。

⇒ **⛔ 谁复用这份探针都必须知道这条**，否则会以为真实产物存在 manifest 漂移问题。
同族于本项目反复出现的「观测通道本身不可信」。**建议在 `probe_f20.sh` §6 就地加一行注释。**

---

## 5. 结论与采信

**报告的四条核心结论 orchestrator 全部独立复核成立，予以采信**：

1. **Q1 的关键更正成立**：orchestrator 上一轮把「只读 stage 根」的理由记成一句话是**焊错了** ——
   那是两次不同提交、两个不同的「有意」，且**都不是在论证「不要读账本」**。
   「不读账本解析 accepted attempt」是**「非侵入式离线审计面」这个更大设计的副产品**，
   而那个更大设计**今天仍有 2 个真实 golden 基线依赖它**（这才是活着的理由）。
2. **岔口必须重描**：不是「新耦合 vs 新副本」（两者本来都已存在），而是
   **「① 有账本时改走已有的哈希绑定加载器（对无账本的旧 run 保留今天的行为）」
   vs 「② 再镜像 3 个文件到 stage 根、继续不碰账本」**。
3. **防篡改强度不是「各有取舍」**：选项②在这件事上**基本等于没有防线**（实测）。
4. **选项②新增轴 B 风险、选项①不新增**（②要新增 3 处手写镜像 ⇒ 四个文件各两份物理拷贝）。

**⇒ 采信施工席的推荐（选项①，条件分支形态）作为设计输入**，
但**⛔ 设计稿不由 orchestrator 亲手写**（08-09 F-9 教训：同一个人同一个盲区），
按用户已拍板的排工交 **sol（GPT 侧）出稿 → Claude 侧对抗审**。

**⛔ 施工席如实标注的三项「没能证实」照单收下，不得在设计稿里当成已证事实**：
① 修完后完整夹具是否真能通过（不碰生产码就测不了）·
② `load_verified_accepted_correction` 独立调用点的精确个数（数到 7，派工单写 6，未追查是否有传递性重复）·
③ 未重跑全仓 2345（按派工单当既定前提）。

**⭐ 派工方错误率更新：13/13** —— 本单派工单里 orchestrator 写错两处（测试文件数「3 个」实为 **5 个**；
把两条不同提交的理由焊成一句话），**均由施工席查实更正**。
另有一处派工单本身就写对了（`window_host_proof` 概念 07-18 才出现，故 07-06 那次调用「没得选」），
施工席主动补上了这层限定 —— **登记为施工席比派工稿更准的第二例。**
