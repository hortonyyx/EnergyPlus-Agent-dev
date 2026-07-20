# C2 整体落地质量横向体检报告

- **日期**: 2026-07-19
- **审计人**: Fable 5(受 Opus 主控委派,横向体检点射)
- **范围**: C2 全批次(B0–B6 + Vg/Va/B-M/B-O/B4a/B4b/B5)跨批次系统性复查;非单批重审
- **基线声明**: 1434 绿 + 9 strict xfail(分支 `6.15_ValidationArchM0toM4`,HEAD `5f94c6b`)
- **状态**: ✅ 完稿

---

## 0. 执行摘要

**整体健康度一句话**:C2 落地质量总体扎实——信任根 recompute 模式、Va 唯一引擎、frame preimage 冻结、schema 版本接缝、可扩展性铁律横向核查全部成立,全量 1434 绿 + 9 xfail 独立复跑吻合;但抓到 **4 个 MAJOR**(全部是「新接线漏网/老区未巡」型,无一是已审批次本体的算法 bug),其中两个直接卡 sm25-L 跑测路径。

**最重要 3 条**:

1. **F1-1 [MAJOR] B5 orientation 再入守卫漏网**(run_stage.py:452 只认 e4 契约不认 b5 契约)→ sm25-L 的 S5 只要走一次 blind-resample 或再入,flow 即崩(fail-closed 崩溃、非错值;1 行修法)。**必接**。
2. **F4-1 [MAJOR] v3 判卷断链**:`judge_score_bindings.json` 无生产者、SOP 零文档、缺失时**静默跳过整个 v3 判卷层**——sm25-L 若不补 bindings 素材+落位步骤,跑完全绿但没人判卷。**必接**。
3. **F5-1 [MAJOR·缺锁] C2 核心语义门「v3 逐层 footprint 一致」两层守卫全仓零负锁**(活体变异 ~230 targeted 零红;门本体活)——B5 时代「缺锁=未交付」的梳子没有回梳 B2 时代的老门,缺锁巡检存在批次年代盲区。
   (第 4 个 MAJOR = F2-1:reading→correction 仍消费 stage-root 镜像未绑 accepted attempt,是 2026-07-08 sm24 同族洞只修了一半;非 sm25-L 硬阻断,列跟进债之首。)

**sm25-L 就绪度裁决:GO-WITH-CAVEATS**(详 §4/§4b:3 件必接=F1-1 修 1 行 / F4-1 补 bindings 素材+SOP / F1-2 profile 配置纪律;2 件强烈建议=correction v3 计分 e2e 前置、`no_oversplit` 永久 NA 知情兜底)。

**焦点 5 活体抽查**:5 处变异(E4 relation / writer replay / B-M content hash / footprint 一致门×2 层)——前三处锁活且红数与各批判词逐一吻合,后两处零红=F5-1。工作树已恢复干净。

---

## 1. 焦点 1:批次间接缝一致性

### F1-1 [MAJOR] B5 orientation 再入接缝:`_ensure_orientation_enriched` 早退守卫漏认 `correction_b5_orientation_v1`

- **证据**:
  - `scripts/tool_scripts/run_stage.py:452` — 早退条件只认 `verified.ref.artifact_contract == "correction_e4_orientation_v1"`;
  - `src/agent/output_coordinates.py:165-168` — E4 契约本体两个 orientation 契约都认(`correction_e4_orientation_v1` + `correction_b5_orientation_v1`);
  - `src/agent/correction/orientation.py:396-402` — `finalize_orientation_enrichment` 的 `accepted_base_contracts = {"correction_b2_v1", "correction_b5_v1"}`,对 `correction_b5_orientation_v1` 基座 raise ValueError;`orientation.py:407-412` 对已填充 north_axis 也 raise。
- **故障模式**: B5 v3 run 首次 `flow --to 5_intakeoutput` 正常(b5_v1 → enrichment → b5_orientation_v1 → 装配)。**再入**(`--from 5_intakeoutput` 重跑 / 修 4_mep 后重装配 / `--with-ep` 复跑)时,accepted 契约已是 `correction_b5_orientation_v1`,守卫不早退 → 走 `resolve_orientation_from_run_dir` → `finalize_orientation_enrichment` 抛未捕获 ValueError(`_draw_assembly` 只捕 `OrientationNeedsInputError`,run_stage.py:526-528)→ flow 崩溃。
- **定性**: fail-closed 崩溃、非静默错值(万幸);但 sm25-L 实跑几乎必然踩到重装配路径。属「B5 Phase D 新契约接入、旧 stepwise 驱动守卫未同步」的典型新接线漏网。
- **测试缺口**: 全仓只有 `tests/test_output_coordinate_identity.py:314` 断言过 b5_orientation 契约(identity 链方向);`_ensure_orientation_enriched` 的「已 enriched B5 再入」路径零测试。
- **修法**(建议): run_stage.py:452 改为 `artifact_contract in ("correction_e4_orientation_v1", "correction_b5_orientation_v1")` + 一条再入回归测试。

### F1-2 [MINOR] `capability_profile` 只在 CLI 旗标、不入 `run_config.yaml`

- **证据**: `scripts/tool_scripts/run_stage.py:2120-2124`(`--capability-profile` 全局旗标,默认 `rectangular`);`src/agent/execution/run_config.py:88-110`(RunConfig 无 capability_profile 字段);`src/agent/execution/policy.py:43`(默认 rectangular)。
- **故障模式**: sm25-L 每次 flow 调用都必须手带 `--capability-profile orthogonal_polygon`;漏带则静默走 v1 rectangular target——L 形会被拆成多矩形 cell(退回 B1 之前的过度分区形态)而**全绿通过**(不会 fail)。与「跑前必确认配置」纪律相悖:run_config.yaml 已经承载 judge_mode/scope/models/grade,唯独这个决定 v1/v3 路由的关键开关靠人记。
- **修法**(建议): capability_profile 进 run_config.yaml(present 时覆盖 CLI),或至少 flow 在 case 有 v3 素材时告警。

### 核过为「对齐」的接缝(无发现)

- **Va = 唯一 applicability 引擎**:`src/agent/judge/opening_claim_score.py:3-4` 文档明示 + `:247/:255/:261` 三个 ledger(reference/product/absence)全部委托 `derive_opening_claim_applicability`,无第二实现;
- **frame hash preimage 冻结一致**:Va `_frame_hash`(`src/agent/correction/facade_applicability.py:324-330`)与 judge 侧 `_FRAME_KEYS` 九键(`src/agent/judge/score_inputs.py:35-38` + `frame_transform_preimage` :41-49)逐键相等,且 judge 侧经独立 `ElevationScoreViewBindingV1` 重验证非引 Va 私有 helper(B4b 设计意图落实);
- **SCORER_SCHEMA = "8"** 单值收敛(`src/agent/judge/score_schema.py:32`),v8 全身份 sidecar + grade.png 双 hash 绑定;
- **schema v1/v2/v3 路由**:`parse.ensure_corrected_geometry` 三版本统一入口,v2 只读 legacy,target 矩阵 rectangular→v1 / orthogonal_polygon→v3(`parse.py:33-58`);
- **E4 出口契约认两个 orientation 契约**(`output_coordinates.py:165-168`)——契约本体没漏,漏的是 run_stage 守卫(F1-1)。

### F1-3 [NIT·已知] `ElevationViewBindingV1` 同名两型仍并存

- `src/agent/correction/facade_applicability.py:103` vs `src/agent/judge/gt_manifest.py:126`。REC-C 已抓过并写进派工单(口径=known footgun),未合并。跨批读码时仍是误导源,建议 C2.1 顺手改名其一。

---

## 2. 焦点 2:信任根覆盖完整性

### 核过为「模式在位」的信任边界(无发现)

- **E4 verified loader 全重算**:`src/agent/output_coordinates.py:392`(output 双 hash 对账)/`:406-413`(六件 artifact_hashes 逐件重算)/`:603-604`(ref 字节重算)/`:1004,1029`(S5 消费侧重算);
- **判卷 sidecar v8 cache**:`score_schema.py:648-668` — cache 命中要求全身份严格相等 + grade.png 字节重算 hash 绑定;`commit_score_artifacts` :671-688 写侧同门;
- **score bindings 三重绑定**:`load_score_view_bindings` 绑 gt content hash + case_metadata hash + base manifest hash(run_stage.py:1345-1348 调用处);
- **view_manifest 唯一 emitter + 中途换 case 硬 raise**(`view_manifest.py:886-907`);
- **B5 writer replay/totality 门 + E4 relation 守卫**(`stage_runner.py:318-382`;`orientation.py:515-529`)——生产码在位,负锁活体验证见焦点 5。

### F2-1 [MAJOR] 「stage-root 镜像 vs accepted 字节」同族洞:reading→correction / B5 writer 消费 0_reading 未绑 accepted attempt

- **背景**: 2026-07-08 sm24 实锤过此族缺陷(blocked draw 经 stage-root 镜像喂进内核),当时修法=`_load_snapped` manifest-first(run_stage.py:308-321 注释自述),后 E4 verified loader 把 correction→下游整条封死。**但同一模式只修了 correction 出口这一边**。
- **证据**:
  - `run_stage.py:255-262` — `_draw_correction` 的 `rdir = run_dir/"0_reading"`,`run_correction(rdir, ...)` 直接消费 stage-root 的 `*_view.json`(最后一次 draw 的镜像,可能非 accepted attempt);
  - `src/agent/correction/window_sources.py:477-484` — B5 `build_verified_window_inputs_from_run` 同样从 `reading_dir` 直读 reading 字节,**只对 view_manifest 做 content hash 绑定,对 reading 字节与 0_reading accepted attempt 的 output_hash 零对账**;
  - 对照:0_reading 的 accepted attempt 字节在 `attempts/NNN/output.json` + manifest output_hash 里是有的(与 correction 同构),只是消费侧没接。
- **故障模式**: reading 多 attempt(auto re-read 是设计内流程)后,若 stage root 被后续 blocked reread 覆写而 accepted 指向更早 attempt,correction/B5 resolver 会静默消费非 accepted 字节 —— 与 sm24 那次同构。B5 的 writer replay(十步独立重算)也是从同一 stage-root 字节重算,**replay 对上了也只证明「与 stage root 一致」,不证明「与 accepted reading 一致」**。
- **定性**: 信任链已把 correction→S5 全程 hash 绑定到齿,唯独最上游 reading→correction 这级还是裸的;MINOR-3(replay 前提待真实 run 验证)与此洞相邻但不覆盖它。
- **修法**(建议): `_draw_correction`/`build_verified_window_inputs_from_run` 消费 reading 时经 manifest accepted attempt 对账(有 accepted 记录时 verify 字节 hash;无则维持现状 exploratory 放行)。

### F2-2 [MINOR] S5 消费 4_mep 走 stage-root、input_hashes 只绑 correction

- **证据**: `run_stage.py:530-533`(`mep_path = run_dir/"4_mep"/"mep_output.json"` 直读)+ `:564-568`(`AssemblyE4Write.input_hashes` 只有 `("1_correction", ...)` 一条)。
- **故障模式**: 与 F2-1 同族(mep blocked draw 覆写 root 后 `--from 5_intakeoutput` 再入会静默消费)。E4 审计只管 north_axis 归零(`output_coordinates.py:825-832`),不绑 mep 字节。较 F2-1 低危:mep 是非几何字段,且 4_mep 门序通常紧邻 S5。
- **修法**(建议): S5 经 accepted attempt 读 mep + input_hashes 加 `4_mep` 一条(manifest 侧 StageRecordV2 本就有 hash 可引)。

---

## 3. 焦点 3:跟进债核对

(方法:官方 4 债逐条代码核实〔部分本审计亲核,部分由委派子代理对账 2026-07-14~19 全部 verdict〕)

### 3.1 官方登记 4 债:现状与登记一致,定级无误降

- **NIT-3**(AST 扫描裸 except 缺口):**亲核属实** — `tests/test_c2_b5_artifact_trust.py:741` 的 `handler.type is not None` 条件确使裸 `except:` 逃逸,登记的一行修法准确;且「现实七信任链文件裸 except 零命中」亲核属实(七文件 grep `except:` 零命中)。非误降:现实零命中,纯扫描器盲区。
- **MINOR-3**(writer replay 的 manifest 覆盖前提):待首个真实 v3 run 验证——sm25-L 首跑即验证载体。replay 门本体活(见焦点 5 M-B)。非误降,但见 F2-1:replay 重算与消费同源(stage-root),replay 过≠accepted 对齐。
- **B4b MINOR-1**(correction v3 无 e2e scorer fixture):属实,tests/ 无 correction-stage v3 计分 e2e。**建议升格为 sm25-L 跑测前置**(见 §4b #5)——sm25-L 正是 correction v3 判卷生产首用,identity/proof 门有全套负锁(崩溃向 fail-closed),但**语义级静默错分**(判错也全绿)是真剩余风险,而判卷是 sm25-L 的测量仪器。
- **B4b MINOR-2**(grade renderer hatch 简化):属实,仅可视化,sidecar 权威分不受影响。非误降。

### 3.2 漏网条目:5 条 verdict 说「登记」但官方清单(plan.md/CLAUDE.md)未载

1. [MINOR] B4b Phase C MINOR-2:`window_elevation_geometry` criterion 只吃 sill/head,along/width 被 channel-fuse 不可分——只活在 `src/agent/judge/score_policy.py:119-121` 注释,官方债清单无此条;
2. [MINOR] B4b Phase C MINOR-3:`no_oversplit`/`negative_evidence_complete` 两 criterion 在 v3 policy 下**永久 NA(inert)**(`score_policy.py:124-127`)——官方清单无;对 sm25-L 有直接影响(见 §4b #6);
3. [NIT] B4a PB-C9⑥ TOCTOU 未修(`scripts/tool_scripts/inspect_dxf.py:269-277`);
4. [NIT] B4a PB-C12 `test_inspect_dxf.py` 测试面偏薄(仍 3 测);
5. [NIT] B4b Phase A:facade-segment hash 测试与实现共享序列化器、无独立 byte anchor(与 F5-1 的「自指/共享 helper 弱锁」同族)。

**建议**:5 条并入官方债清单(plan.md ②③ 块),否则下轮换主控即失忆。

### 3.3 误降判断

官方 4 债均非误降。漏网 #2(`no_oversplit` 永久 NA)**接近误降边缘**:sm25-L 是 L 形,oversplit 恰是 sm24 非方形首跑的历史缺陷轴(06-24 L 走廊过度分区),v3 判卷对该轴显式 NA(如实标注、非伪 pass),**复发时判卷不会抓**——不阻断但必须知情兜底(人工肉检 + 区数对账),已提入 §4b。

---

## 4. 焦点 4:sm25-L 跑测前就绪度

### 已核实为「通」的链路

- flow correction draw 路径 v3 全接线:`run_stage.py:262-283` — `schema_version=="3"` 时 `build_verified_window_inputs_from_run` → `finalize_correction_draw(verified_window_inputs=...)` → `check_correction(window_host_proof=..., window_evidence=...)`;
- stage_runner B5 writer 六件套在位:`src/agent/execution/stage_runner.py:460-527`(六件 artifact 逐一 model_validate + `correction_b5_v1`/`correction_b5_orientation_v1` 契约路由);
- 2/3/4/5 段 stepwise 均走 `_load_snapped_with_proof`(run_stage.py:324-336)拿 accepted bytes + proof,`build_geometry(capability_profile, window_host_proof)` 贯通(run_stage.py:338-427);
- S5 装配走 E4 全链(`_draw_assembly` → enrichment → `assemble_intake_artifacts` → `build_assembly_coordinate_audit`,run_stage.py:489-560)。

### 断链 / 风险点

- F1-1(orientation 再入崩溃)——见焦点 1;
- F1-2(capability_profile 靠手带)——见焦点 1;

### F4-1 [MAJOR] v3 判卷断链:`judge_score_bindings.json` 无生产者、无 SOP、缺失时**静默跳过判卷**

- **证据**:
  - `scripts/tool_scripts/run_stage.py:1296-1299` — `_typed_score_input_paths` 要求 `<run>/_run/judge_score_bindings.json`(+ 可选 overlay);
  - `run_stage.py:1339-1342` — `if not base_path.exists() or not bindings_path.exists(): return {"score_vs_gt": None, "grade": None, ...}` = **bindings 缺失时 v3 判卷静默返回 None,不告警、不 fail**;
  - 全仓 grep:`judge_score_bindings` 唯一出现点就是 run_stage.py:1299 这一行 —— **没有任何生产代码/CLI 写这个文件**(`score_reading_vs_gt.py --bindings` 只接受手动传入路径);
  - B4b 细稿 `AI_agent/proposals/c2_b4b_detail_spec.md:345` — 设计口径 = judge-only reviewed input,资产路径「每个 GT v3 case bundle 下 `score_inputs/view_bindings.json`」,**不由产品生成**(设计如此);
  - 但 `AI_agent/guides/new_case_guide.md` 对 `view_bindings`/`score_inputs`/`judge_score_bindings` **零提及**(grep 无命中);GT bundle 现状 `case_tests/test_baseline/gt/` 仅 sm21_anchor(gt.json+renders),无任何 score_inputs 样例;
  - 且 spec 说的 bundle 路径(`gt/<case>/score_inputs/view_bindings.json`)与 run_stage 读的路径(`<run>/_run/judge_score_bindings.json`)之间**没有搬运桥**(无 copy/provision 代码)。
- **定性**: 「judge-reviewed 受信输入」是拍板过的设计(B4b §17),不是 bug;真正的洞是三件事叠加:①无 SOP 文档(操作手册不知道要作这个文件)②无落位桥(作了也没人搬到 `_run/`)③缺失时静默 no-op(违背「judge 以 gt 为权威」的硬规约——sm25-L 若忘作 bindings,整个 v3 判卷层无声消失,流程照样全绿)。
- **必接**: sm25-L 素材清单必须加上「作 sm25 `view_bindings.json`(+判定落位路径)」;建议 flow 在「GT v3 存在但 bindings 缺失」时打 loud warning 或直接 fail(exploratory 档可 warn)。

### sm25-L 素材缺件清单(除图外,基于本次排查)

1. `case_tests/e2e_tests/sm25_*/case_data/`(图 + 视图文件)— 已知,用户+主控做;
2. `0_reading/*_view.json`(冷启识图产物)— 已知;
3. `case_tests/test_baseline/gt/sm25_*/gt.json`(**GroundTruthV3**,现 gt 仓只有 sm21 v2)— 已知(gt_from_dxf v3 build-only 已就位,但 sm25 DXF 未入仓;或手作);
4. **[本次新增] `score_inputs/view_bindings.json`(judge-reviewed)+ 落位到 `<run>/_run/judge_score_bindings.json` 的步骤** — F4-1;
5. **[本次新增] run 时每次带 `--capability-profile orthogonal_polygon`(或先把它进 run_config.yaml)** — F1-2;
6. `run_config.yaml`(judge/scope/models/grade;flow SOP 已有);view_manifest 由 `provision_view_manifest` 自动产(view_manifest.py:886-907,有真生产者,无缺口)。

### 就绪度裁决

**GO-WITH-CAVEATS**。端到端链路结构上已接通(v3 draw → B5 resolver/proof → build → E4 → assembly 在 flow 生产路径全部有真接线,见上「已核实为通」清单);未发现生产链本体的 BLOCKER 级断裂。但除素材入仓外,**三件必接**:

1. **[必接·代码 1 行+回归测试] F1-1 orientation 再入守卫**:不修则 sm25-L 的 S5 只要走一次 blind-resample(gate① 首抽 fail 是常态)或任何再入,flow 即崩(标准重抽循环被打断=run 级 BLOCKER 地雷,虽 fail-closed 不产错值)。
2. **[必接·素材+SOP] F4-1 judge bindings**:作 sm25-L 的 `view_bindings.json`(judge-reviewed)+ 明确落位到 `<run>/_run/judge_score_bindings.json` 的步骤(建议顺手写进 new_case_guide);不接则 v3 判卷层整层静默消失、跑完没人发现没判卷。
3. **[必接·跑测纪律] F1-2 capability_profile**:每次 flow 调用带 `--capability-profile orthogonal_polygon`(写进跑测配置拍板单);或先落 run_config.yaml 槽位。漏带=静默退化为多矩形拆分而全绿。

**另两件强烈建议随跑测一起**(§4b #5/#6):correction v3 计分 e2e fixture 前置(判卷是 sm25-L 的测量仪器,identity 门全 fail-closed 但语义级静默错分无锁)+ `no_oversplit` 永久 NA 知情兜底(L 形 oversplit 判卷不抓,人工肉检+区数对账)。

**已知可接受的首跑风险**(登记债,非新发现):correction LLM 出 v3 从未真跑过(B4b MINOR-1 + B5 MINOR-3 都指着「首个真实 v3 run」),sm25-L 首跑本身就是这两条债的验证载体 → 首跑按 exploratory 档、人盯 gate,符合既定纪律。
**建议同批顺手**(非阻断):F5-1 两条负锁;F2-1 reading accepted 绑定(首跑有人盯 accept/reread 状态可缓);F2-2 mep 绑定。

---

## 4b. sm25-L 必接清单(汇总)

| # | 项 | 类型 | 工作量 |
|---|---|---|---|
| 1 | F1-1:run_stage.py:452 守卫加 `correction_b5_orientation_v1` + 再入回归测试 | 代码 | 1 行 + 1 测试 |
| 2 | F4-1:sm25-L `view_bindings.json` 制作 + 落位步骤 + guide 文档 | 素材+SOP | judge 侧半天内 |
| 3 | F1-2:跑测配置拍板单钉死 `--capability-profile orthogonal_polygon`(或入 run_config.yaml) | 纪律/小代码 | 即时 |
| 4 | 既定素材:图→case_data / reading / gt.json(GroundTruthV3) | 素材 | 用户+主控(已排) |
| 5 | B4b MINOR-1 升格:correction v3 计分 e2e fixture 补在跑测前(判卷=sm25-L 的测量仪器,防语义级静默错分) | 测试 | 小批 |
| 6 | 知情兜底:`no_oversplit` 在 v3 policy 永久 NA(score_policy.py:124-127)——L 形 oversplit 是 sm24 历史缺陷轴,判卷不会抓复发;验收判读时人工肉检 + 区数对账兜底 | 判读纪律 | 写进跑测单 |

---

## 5. 焦点 5:测试真实性抽查

方法:对四个跨批关键锁做 neuter 变异(改生产码守卫为恒通过)→ 跑对应测试文件,验证「锁 neuter 即红、恢复即绿」。四个目标覆盖四个批次族:

| # | 锁(批次) | 生产码位置 | 期望红测试 |
|---|---|---|---|
| M-A | E4 relation 守卫「enrichment 不得改 host 关系」(B5 Phase D MAJOR-2 补锁) | orientation.py:528-529 | test_c2_b5_artifact_trust.py:643/691 |
| M-B | writer replay drift 门(B5 Phase D MAJOR-1 补锁) | stage_runner.py:382 | test_c2_b5_artifact_trust.py:316-333 |
| M-C | view_manifest content hash 自重算(B-M CR-01 修复) | view_manifest.py:454-458 | test_run_manifest_v2 / view manifest 族 |
| M-D | v3 envelope 事务安全拒绝(B2 F1/B2b) | deterministic.py:774-781 分派→envelope_transform 拒绝分支 | test_c2_b2_v3 / test_c2_b2b_envelope_transform |

四文件变异前基线:**123 passed**(9.93s);全量基线本审计独立复跑:**1434 passed + 9 xfailed**(738s,PYTEST_EXIT=0)——与项目声明逐字吻合。

### 变异结果

| # | neuter 后 | 判定 |
|---|---|---|
| M-A E4 relation 守卫(orientation.py:528)| `test_d3_orientation_enrichment_rejects_changed_host_relationship` **1 红**,余 44 绿 | **锁活**,精确对应 Phase D MAJOR-2 补锁 |
| M-B writer replay 门(stage_runner.py:382)| `test_d1_writer_replay_rejects_self_consistent_original_field_forgery[×2 参数化]` **2 红**,余 43 绿 | **锁活**,与 Phase D 判词「neuter 各只红 2/1/1」的 2 吻合 |
| M-C manifest content hash 自重算(view_manifest.py:455)| `test_view_manifest_schema.py`+`test_view_manifest_generator.py` **5 红**(wrong-but-wellformed hash / on-disk tamper / provision reuse tamper) | **锁活**(B-M CR-01 修复的锁在专属测试文件;注:`test_run_manifest_v2.py`/`test_check_view_manifest_coverage.py` 对此零覆盖,锁位置偏门但真) |
| M-D v3 envelope 事务「逐层 footprint 不一致拒绝」(envelope_transform.py:519-520)| **0 红**(52 targeted 全绿) | 见 F5-1 |
| M-D' schema 层同门 `_v3_integrity`「identical geometry」(schema.py:262-263)| **0 红**(52 + `-k "footprint/envelope/v3"` 116 + `-k "fingerprint/integrity/schema"` 114,共 ~230 targeted 全绿) | 见 F5-1 |

### F5-1 [MAJOR·缺锁] C2 核心语义门「v3 逐层 footprint 几何一致」两层守卫全仓零负锁

- **门是真的**(正向活体探针):构造两层不同 footprint 的 v3 payload 经 `ensure_corrected_geometry` → 现网 raise `"v3 per-floor footprints must have identical geometry"`(本审计当场验证);
- **锁是缺的**:schema 层(schema.py:262-263)与 envelope 事务层(envelope_transform.py:519-520)**双层 neuter 均零红**——全仓 grep 无任何测试构造 divergent-footprint 负例(`grep "identical geometry" tests/` 无命中);envelope 层因 schema 层挡在前面属纵深防御不可达,但 schema 层自身也无锁;
- **为什么要紧**: 这道门正是 C2「共底面」语义契约的唯一执行点,也是焦点 6 里认定的 C3 放宽接缝(退台=松这道门)。按项目自家 Phase C 标准(「spec 点名安全拒绝分支缺测试锁=未交付」),这属 REWORK 级;且 C3 放宽改造动这里时,零锁意味着语义漂移没人抓;
- **横向意味**: B5 Phase C/D 两轮「补 17 锁/补 4 负锁」扫的是 B5 自己的 spec 分支,**B2 时代的老门没被同一把梳子梳过**——缺锁巡检存在批次年代盲区,建议对 B2/B2b/B-M 老 spec 的点名拒绝分支做一次同标准的负锁补扫;
- **修法**: 两条负例测试(schema 层 divergent footprint raise + envelope 层用 monkeypatch 绕过 schema 后直调事务层)。

变异完成后 `git status` 确认工作树干净(全部生产码改动已恢复)。

---

## 7. 建议汇总

### 必接(sm25-L 跑测前)
1. **F1-1** run_stage.py:452 守卫补 `correction_b5_orientation_v1` + 再入回归测试(1 行修法);
2. **F4-1** sm25-L `view_bindings.json` 制作 + 落位步骤;new_case_guide 补「v3 case 判卷需 judge sidecar」一节;缺 bindings 时 flow 至少打 loud warning;
3. **F1-2** 跑测配置拍板单钉死 capability_profile(近期);run_config.yaml 加槽位(可 C2.1);
4. **B4b MINOR-1 升格**:correction v3 计分 e2e fixture 跑测前补(§4b #5);
5. **知情兜底**:`no_oversplit` 永久 NA 写进跑测单,人工肉检+区数对账兜 L 形 oversplit 轴(§4b #6)。

### 跟进债(登记、不阻塞;建议与 F1-1 同批顺手的排前)
6. **F5-1** footprint 一致门补两条负锁(schema 层 + envelope 层);并对 B2/B2b/B-M 老 spec 点名拒绝分支做一次 B5 Phase C 同标准的负锁补扫(缺锁巡检的批次年代盲区);
7. **F2-1** reading→correction/B5 resolver 消费经 accepted attempt 对账(与既有 `_load_snapped` manifest-first 同构修法);
8. **F2-2** S5 消费 mep 经 accepted attempt + input_hashes 补 `4_mep`;
9. **§3.2 五条漏网债补登记**(B4b Phase C MINOR-2/MINOR-3、PB-C9⑥ TOCTOU、PB-C12、Phase A byte anchor)进 plan.md 官方清单;
10. **F1-3** `ElevationViewBindingV1` 同名两型改名其一(已知 footgun,REC-C 记档)。

### C2.1+ 再处理
11. 既有登记债照旧:NIT-3(AST 一行)/MINOR-3(replay 前提·sm25-L 首跑即验)/B4b MINOR-2(grade hatch);
12. C3 债(焦点 6 确认已登记):带洞楼板分解守卫/per-cell z_span/旋转系吸附/Facade Literal 类型根。

---

## 8. 诚实声明:未覆盖面

- **未做跨厂商交叉核**(任务授权「可」调 sol 独立核信任根,非必须):因本轮网络两次中断 + 额度约束,焦点 5 的活体锁验证由本审计直接对生产码变异执行(5 处 neuter + 1 处正向探针,结果与各批判词逐一对得上),未再走 GPT 侧独立复核——同厂商自查的独立性弱于跨厂商,此点如实声明;
- **焦点 3 的 verdict 通读**由委派子代理完成(2026-07-14~19 全部 verdict),本审计亲核了其中 NIT-3/七文件裸 except 两项,其余漏网条目引用子代理锚点未逐条二次开文件核对;
- **焦点 5 的 M-D/M-D' 零红判定**基于两轮关键词 targeted 扫描(~230 测)+ 全仓 grep,未在 neuter 态跑全量 1434(时间预算);理论上存在极偏门命名的锁未被关键词覆盖的可能,但 grep「identical geometry」全仓零命中使此概率很低;
- **未逐行重读**判卷子系统 B4b Phase B/C 的计分算法本体(段级 interval 数学)与 Vg 511 子集穷举——依赖其批内对抗审 + 本次接缝/委托关系核查;
- **未实跑**任何 case(横向体检定位,不做 e2e 实跑;sm25-L 首跑本身就是 MINOR-3/B4b MINOR-1 的验证载体);
- **9 xfail 身份**只核到文件级(test_orchestrate_baseline.py:32 / test_validation_run_baseline.py:26 两处 `_RERECORD_XFAIL` legacy golden 族;`test_output_coordinate_identity.py` 零 xfail 与 Phase D 声明一致),未逐个数出 9 个参数化实例;
- **skills/intake_pipeline 的 prompt 面**只核了 correction prompt 的 v3/polygon 指令在位(pipeline.py:318-325)与 1_correction 文档含 polygon 词汇(A0/A1),未评估 prompt 对 L 形 case 的实际引导质量(那是首跑 judge 的事)。

---

## 6. 焦点 6:可扩展性铁律

**总体判断:C2 落地未违反铁律 —— 无实质烤死点**(独立子代理全面扫描,证据锚点逐项核过)。

| 假设 | 状态 | 关键锚点 |
|---|---|---|
| 共用 footprint | **接缝内可长**:数据模型已是 per-floor(`FloorV3.footprint`,schema.py:188-192;`footprint.py:22-28` 单一权威读取);「逐层指纹一致」是 **v3 作用域的语义收紧门**(schema.py:252-263 `_v3_integrity` + envelope_transform.py:519-520),非结构烤死——退台=松这道门+`FEATURE_PER_FLOOR_FOOTPRINT` 已注册(capability.py:22) | schema.py:262 |
| 满铺楼板 | **接缝内可长**:楼板/天花由上下层 cell **逐块 intersection 派生**(split_pairing.py:120-169),未覆盖→Roof、悬挑→Outdoors 三分支已在;无「每层一块 slab」假设。带内环(洞)多边形分解守卫=已登记 C3 债(capability upgrade doc:92) | split_pairing.py:120-169 |
| 固定层高 | **不存在于代码**:`Floor.z_floor`+`ceiling_height` per-floor(schema.py:64-68),全仓无全局层高标量;z-stack 门只要求贴合不要求等高。挑空双层高的 per-cell `z_span` 槽位=已登记 C3 债(upgrade doc:89) | modelling.py:534 |
| 四立面/单θ/矩形 | 烤死的只有「θ=0 轴对齐」(schema.py:143-153 段轴对齐 raise/modelling.py:343/window_host.py:542-543),**已登记 C3/C4 债**(upgrade doc:65/:108)。哈希 preimage(footprint.py:60-78 任意开环通用)/多翼 facade_family 多段/真北 `NorthAxisEvidence.value_deg` 任意角(仅 default 假设强制 0,orientation.py:119-120)/judge frame 均**未**烤矩形 | footprint.py:60-78 |
| schema 版本接缝 | **强接缝**:v1/v3 strict 子类族(schema.py:184-274)+ `SCHEMA_VERSION_FEATURES` map(capability.py:32-39)+ release map(feature_state.py:126-142)三层;加竖向槽位=新增版本行不动老类 | schema.py:184-274 |

结论:未发现「纯只适用当前情况、长不到复杂体量」的方案;三个残余风险点(带洞楼板分解/`z_span`/旋转系)全部已登记 C3/C4 且属「schema 加槽位+kernel 扩展」接缝内。

---

## 7. 建议汇总

(待回填)

---

## 8. 诚实声明:未覆盖面

(待回填)
