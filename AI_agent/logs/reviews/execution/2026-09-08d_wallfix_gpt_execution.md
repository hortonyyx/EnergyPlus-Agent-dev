# W#1 / W#4 / W#5 / W#2 · GPT 施工交件

工作树始终是 `/tmp/w1_flow_glm`，分支 `wt/09.07h_w1_flow`。接手 HEAD 是 `55fc8e30`（含基点 `5839a85c` 之后的两份已确认勘误）。已先读派工单与撞墙档附录 B；本次按「24 条 FLAG 同属契约错配噪声」施工，没有重报评分为零或 uv 同步问题。W#3、W#6 没有重做；W#7 和窗的生产逻辑没有修改。

**结果：四项已交付，全量通过；完整 flow 总验收未通过**

W#1 契约分派、W#4 失败记录清理、W#5 归档失败诊断、W#2 凭据与复跑序列均已落库。最终全量 **4075 passed，0 failed**。新建 `run_wallfix_gpt_judge_on`，配置从首次 provisioning 起就是 `judge.mode: stop`，本次 `0_reading` gate① `block=0 / flag=0`，本次新生成的两层平面 C1/C2 为 100.0 / 98.1。J0 已实际查看六张原图、六张原生评分图及 JSON，提交有证据限制的非阻塞判词。correction 两层都经真实 `deepseek-v4-pro` 调用成功，归档重放成功，但 **gate① 被新暴露的 `correction.audit_completeness` 阻塞**；未到 J1、2/3/4/5，也没有 correction/下游的本次出分。没有修改 W#7、窗代码或强行接受候选。

**分段提交与验证**

| 提交 | 内容 | 验证 |
|---|---|---|
| `3a592091` | 接手全量基线 | 4049 passed / 2 skipped / 13 xfailed，0 failed，502.03s |
| `0966c44d` | W#1：三个 reading 检查入口按契约分派 | 178 passed；真实六视图 × exploratory/dev/golden/regression；未知、歧义、坏标定、缺刻度、假闭合负例；legacy 报告逐字段不变 |
| `d8fb122b` | W#4：新一轮链调用先移除上轮 exception 记录 | 33 passed；真链失败→成功与失败→不同失败 |
| `42c880cd` | W#5：归档失败保留 gate 诊断 | 140 passed / 1 xfailed；含 W#3 七把锁、B5 原子归档及拒绝锁 |
| `63c400e8` | 新 run 的 reading 工件和实际 J0 判词 | 标准 flow 返回 checkpoint 10，标准 judge 返回 0；不是复制旧 accepted attempt |
| 代码 `42c880cd` 后最终全量 | 全部四项施工的代码状态 | **4075 passed / 2 skipped / 13 xfailed，0 failed，502.20s** |

W#2 与枚举表提交为 `42f06f53`；本次 correction 完整失败候选和中止观测也已单独提交，路径见下。

全量均使用下列命令，开跑前确认打印的是 `/tmp/w1_flow_glm/src/agent/__init__.py`：

```bash
cd /tmp/w1_flow_glm
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python -c 'import src.agent; print(src.agent.__file__); assert src.agent.__file__.startswith("/tmp/w1_flow_glm/")'
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python -m pytest -n 6 -q
```

日志位于 `AI_agent/logs/experiments/2026-09-08d_wallfix_gpt/`：`baseline_pytest.txt`、`final_pytest.txt`、`w1_tests.txt`、`w4_tests.txt`、`w5_tests.txt`。没有安装依赖、写 site-packages、改 git config、跳 hook 或操作别的树；只 add 本次明确路径，每次提交前均查看 cached numstat。日志被全局忽略，取证文件通过逐路径 `git add -f` 入库。

**W#1：完整的逐检查对照表（交付物）**

范围是 `src/validator/checks/reading.py::check_reading_view` 的全部 24 个可能的 per-view check ID，外加独立入口/消费端枚举。不是只列 24 条红字：撞墙 run 的报告实际有 127 行，即 manifest 1 行 + 六视图各 21 行；没有 room_labels 时三个标签检查不发结果。原四类 FAIL 每类六行，共 24 FLAG。

原始报告保存在 `AI_agent/logs/experiments/2026-09-08d_wallfix_gpt/reading_checks_before.json`；本次报告是 `case_tests/e2e_tests/sm25-L_anchor/run_wallfix_gpt_judge_on/0_reading/attempts/001/checks.json`，157 行 = manifest 1 + 六视图各 26。下表 ID 均省略共同前缀 `reading.`。这里的 N/A 明确表示**legacy 字段检查不适用**，不宣称 as_drawn 对应内容已通过同等像素核验。

| Check ID | 原检查读的 legacy 字段 | as_drawn 的实际载体 / 差异 | 原报告 → 本次处理 |
|---|---|---|---|
| `plan_scale_origin_usable` | `image_kind`, `scale_origin` | plan：`observations.calibration` 与 face_lines 的世界坐标；elevation：顶层 calibration，契约就是立面 | 六行 FAIL → N/A；新增 native calibration 检查；不再声称新腿会零分 |
| `dimensions_present` | `dimensions[]` | plan：`observations.calibration.{x,y}.cum_mm`；elevation：`calibration.{x,z}.cum_mm` | 六行 FAIL → native PASS；四态 dimensioned applicability 保留 |
| `raw_field_presence` | 原始 `uncaptured` 是否出现 | 三层 observations/declarations/hypotheses 与 ledger，不声明该 legacy 键 | 六行 FAIL → N/A |
| `stroke_provenance_coverage` | `strokes[].pen/provenance` | plan 的 face_lines 像素/米载体与假说分层，不是 stroke provenance | 六行 FAIL → N/A，不以空 strokes 推断 provenance 缺失 |
| `stroke_ids_unique` | `strokes[].id` | plan face_lines IDs / elevation structure_lines；不是同一集合 | 空集合 PASS → N/A；producer 类型校验不等于 ID 唯一性检查 |
| `dimension_ids_unique` | `dimensions[].id` | 累计刻度数组，不携带同种 dimension ID | 空集合 PASS → N/A |
| `pen_kind_valid` | `image_kind`, `strokes[].pen` | plan ink families / hypotheses；elevation 的结构与开口载体 | 空集合 PASS → N/A |
| `no_topology_fields` | strokes 中禁止的 zone/adjacency 字段 | 三层契约允许独立 hypotheses；不能把它当 legacy strokes | 空集合 PASS → N/A；as_drawn plan 用既有 producer type 校验形状 |
| `nondegenerate_geometry` | `strokes[].geometry` | face_lines 的 support/runs/edges，或 elevation structure_lines | 空集合 PASS → N/A；没有冒称做了原生几何/像素完整核验 |
| `dimension_parseable` | `dimensions[].value_m/text` | `values_mm/cum_mm/overall_mm` 是数值链 | 空集合 PASS → N/A；native chain 检查数值、序列与闭合 |
| `axis_endpoint_consistent` | dimensions 的 axis/from/to | calibration 的轴与累计刻度，不是二维 dimension endpoints | 空集合 PASS → N/A |
| `facade_fields` | `image_kind=elevation`, `facade` | elevation 契约、facade_label；legacy facade 字段并不要求 | 被误当 plan 而 N/A → 按 elevation 契约明确 N/A，不伪造朝向声明 |
| `uncaptured_present` | `uncaptured[]`（含迁移默认值） | ledger 与假说分桶，非同一字段 | 默认补空后的 PASS → N/A |
| `dimension_p1a_fields` | text_verbatim/value/axis/chain 等 | native calibration 链 | 因旧 dimensions 空而 N/A → 按契约 N/A |
| `room_label_roles_valid` | `room_labels[].role` | 当前这批 as_drawn 不声明该标签槽 | 原无结果 → 显式 N/A |
| `room_label_basis_valid` | `room_labels[].basis` | 同上 | 原无结果 → 显式 N/A |
| `room_label_anchors_in_bounds` | room_labels.anchor 与 legacy bounds | 同上；不借错格式 bounds 评新数据 | 原无结果 → 显式 N/A |
| `ocr_anchors_in_bounds` | `ocr_texts[].anchor`、strokes 构造的米制参考 | native dimension_witnesses / calibration 匹配像素 | 空集合 PASS → N/A |
| `dimension_endpoints_in_bounds` | dimensions.from/to、strokes 米制参考 | native matched_px 与数值链，不是 legacy 米制端点 | 空集合 PASS → N/A |
| `dimension_chain_closure` | `dimensions[]` 内 chain/overall | plan x/y；elevation x/z 的 values/cum/overall | 原 N/A → native PASS；重新计算每段、累计和总长的误差，不信自报 chain_closure_mm；沿用 `DIMCHAIN_CLOSE_TOL_M` |
| `dimension_derived_refs` | strokes.provenance 引用 dimension IDs | as_drawn 的 evidence locators/face IDs；引用体系不同 | 原 N/A → 按契约 N/A |
| `stroke_dimension_consistency` | legacy strokes 与 dimension positions | 声明尺寸与像素观测分层 | 原 N/A → 按契约 N/A；未添加吸附或几何推断 |
| `partition_on_window_jamb` | legacy wall/window strokes 与 dims | 无该 legacy 检查的输入 | 原 N/A → 按契约 N/A；窗逻辑未改 |
| `door_heal_traced` | legacy healed stroke provenance 与 uncaptured | native gaps/opening hypotheses，后续才解释 | 原 N/A → 按契约 N/A；未改门窗推导 |

新增两个检查：`reading.product_contract` 记录统一 `vector_contract` 分类结果及真实 plan/elevation；`reading.as_drawn.calibration_usable` 检查该契约的公共像素比例、世界零点和逐轴比例/原点的有限性与可用性。未知、声明损坏、歧义契约及 sidecar 作为 view 输入均 BLOCK，不回退 legacy。未声明的历史输入维持原迁移行为。

**W#1：入口与同类消费端枚举**

检索包括 `parse_reading_view` / `load_reading_view` / `ReadingView.model_validate` / `check_reading_view` 的所有生产调用，以及 validator/execution/run_stage 对 `strokes`、`dimensions`、`image_kind`、`scale_origin`、`uncaptured` 的直接读取。下表区分修复、已有分派、残留边界；不宣称全仓库所有 legacy 消费端都已迁移。

| 入口 / 位置 | 用旧字段量新产物的风险 | 本次结果 / 范围 |
|---|---|---|
| `src/validator/checks/view_manifest.py::check_reading_stage` | flat flow 与 isolation merge 共用；无条件 parse 成 legacy 空壳 | **已修**：共用 `reading_product.check_reading_product`；覆盖检查、stem 前缀、冻结 policy hash/source 保留 |
| `src/agent/execution/evidence_preflight.py::compute_reading_report_from_vector_dir` | 直接 load + legacy check；会把假红重新投影成 evidence debt | **已修**：同一原始 JSON 分派器；没有改 W#7 债的认领规则 |
| `src/agent/execution/validation_run.py::validate_case` | 离线重验又做一遍 legacy check | **已修**：同一分派器；只把真实 legacy ReadingView 传给后续 legacy facade 交叉检查 |
| `src/validator/checks/reading.py::check_calibration_evidence` | 名在 reading 模块，但实际读 CV sidecar | **非同类误用**：检查 sidecar 自己的轴标定事实，不解析 ReadingView；本次未改 |
| `src/validator/checks/as_drawn.py` 的 11 个 image checks | 原生 face_lines / masks / hypotheses / declarations | **不是 legacy 检查**；有独立原图+配置入口，本次未接入全部 11 项，也不以新 gate PASS 代替其像素核验 |
| `src/agent/reading/vector_contract.py::_detect_legacy_reading_view` | ReadingView 本身过度宽松 | **已有防护**：显式 strokes conjunct + 所有 detector 一起判断 + schema 声明不回退；本次复用，没有再写分类器 |
| `scripts/tool_scripts/run_stage.py::_grade_as_drawn_reading_branch` / `src/agent/judge/as_drawn/flow_wiring.py` | legacy/typed score 的 schema/default 风险 | **已有正确分派**：标准评分在 typed/legacy 前按 vector_contract 进入原生 grader；本次 fresh attempt 实测出分 |
| `src/agent/judge/reading_typed_adapter.py` 的 plan/elevation `ReadingView.model_validate`；`run_stage.py::_score_reading_attempt_output`；`src/agent/judge/reading_score.py` | 若直接喂 as_drawn 仍会按 strokes/scale_origin 衡量 | **legacy/typed 消费边界仍在**；标准 as_drawn 评分先返回，不走这些分支；本次未改这些 scorer |
| `scripts/tool_scripts/run_stage.py::_finalize_reading_renders` → `scripts/tool_scripts/render_vector_to_png.py::render` | 无条件读取 strokes/dimensions；把 as_drawn 渲染为空 | **本次新实测残留**：六张通用 renders 均为 400×80 `empty vector`，render_manifest 却为 complete。原生 grade 图存在且由同次标准 flow 生成。列账，未修改渲染器；J0 明示材料缺陷 |
| `src/agent/correction/envelope.py::extract_envelope_candidates_from_dir` / `extract_authoritative_envelope` | 仍 load legacy views，读 dimensions/facade | **legacy 专用路径仍在**；标准新腿 `_draw_correction_as_drawn` 使用专用 finalize，W#3 的 record replay 已按 chain_provenance 分腿；本次未重做 |
| `src/agent/pipeline.py::run_pipeline_artifacts` 的 reading_views 列表 | 复合旧入口仍直接 load_reading_view；不能据此称所有入口已支持新腿 | **残留边界**：本次只修其共用 reading preflight；总验收走指定 run_stage flow，未宣称旧复合入口完成迁移 |
| `src/validator/checks/correction.py::_reading_elevation_windows` / `_facade_frame_cross_check` | 只理解 legacy facade/strokes | **窗相关边界，未改**；本次 validation 不再送入伪造的 legacy plan 空壳。原生窗的交叉检查不在本单范围 |
| `src/agent/correction/window_sources.py` 的 parse 调用（source windows、observation catalog、legacy direction facts/check） | 直接使用时会按 legacy facade/strokes 解析 | **窗归属另一席，未改**；当前标准 as_drawn builder 与 `_check_direction_facts_as_drawn` 已有专用分支；原生窗内容不宣称补齐 |
| `src/agent/reading/legacy.py` 的 parse/load/migrate API | 直接拿新格式调用仍可造空壳 | **API 本身仍为 legacy**；本次三个检查调用端先分派，没有全局改 parser 去影响另一席的窗工作 |
| `src/validator/checks/kernel.py` / `mep.py` / `assembly.py` | 不直接消费 reading JSON | **非同类**：消费 corrected geometry / kernel / MEP / assembly 产物，不能据其通过推断 reading 完整 |

**W#4 / W#5 的实际边界**

W#4 在每次 `run_correction_evidence_chain` 开始、source_read 之前清除同一 `_run/evidence_chain_failure.json`。成功和普通 non-success outcome 都由本轮 outcome/route 描述；本轮再抛异常会重写当前 failure。它不提供历史失败归档，也没有修用户排除的多层 run-level route last-writer-wins。

W#5 在 `StageRunner.record` 外围观察异常退出，不压掉原异常；checked writer 的重放、逐字段校验、原子发布顺序不变。失败诊断存放于 `<stage>/record_failures/NNN/{checks.json,failure.json}`，包括原 gate 结果、异常类型/消息、checks hash、候选 output hash。这里没有 output/proof，不在 manifest 接受链中。**没有把未验证候选塞进 attempts 以换取可见报告**；既有 B5「重放失败不生成 attempt」锁继续通过。诊断 IO 自身失败时给原异常附加 note，仍传播原拒绝。

**W#2：凭据来源与本次逐字命令序列**

共享主树已有由主控配置的 `/workspaces/EnergyPlus-Agent-dev/.env`；它被 gitignore，worktree 不包含副本。本次在每个需要 API 的 shell 中 `set -a && . ... && set +a`，使本树的 `src/configs/llm.yaml` 的 `${oc.env:DEEPSEEK_API_KEY,null}` 能解析到凭据。只检查非空，不打印、复制或提交密钥。新机器由运行者先配置同等凭据来源；仓库不能提供秘密文件本身。

以下为可直接复制的初始化及首次 flow 命令。本次实测把 `wallfix_run_name` 设置为 `run_wallfix_gpt_judge_on`；该取证 run 已落库，所以下面仅将 run 名改为自动生成的新名字，其余初始化和入口参数与本次相同。`test ! -e` 防止把旧 accepted 工件冒充新验收。

```bash
cd /tmp/w1_flow_glm
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
test -n "${DEEPSEEK_API_KEY:-}"
wallfix_run_name=run_wallfix_gpt_judge_$(date -u +%Y%m%dT%H%M%S)_$$
wallfix_run_dir=case_tests/e2e_tests/sm25-L_anchor/$wallfix_run_name
test ! -e "$wallfix_run_dir"
mkdir -p "$wallfix_run_dir/0_reading"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json "$wallfix_run_dir/0_reading/1f_view.json"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json "$wallfix_run_dir/0_reading/2f_view.json"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json "$wallfix_run_dir/0_reading/East_view.json"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_north_as_drawn.json "$wallfix_run_dir/0_reading/North_view.json"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_south_as_drawn.json "$wallfix_run_dir/0_reading/South_view.json"
cp AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_west_as_drawn.json "$wallfix_run_dir/0_reading/West_view.json"
cat > "$wallfix_run_dir/run_config.yaml" <<'YAML'
run_profile: exploratory
capability_profile: orthogonal_polygon
judge:
  mode: stop
review:
  reading: false
  correction: false
  geometry: false
YAML
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python scripts/tool_scripts/run_stage.py flow sm25-L_anchor "$wallfix_run_name" --from 0_reading --judge stop --geometry auto
```

首次返回码 **10 = awaiting_judge**，是启用 judge 的标准检查点。继续在同一个 shell 使用刚才的 run 名：

```bash
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python scripts/tool_scripts/run_stage.py judge sm25-L_anchor "$wallfix_run_name" 0_reading --verdict AI_agent/logs/experiments/2026-09-08d_wallfix_gpt/j0_verdict.json
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python scripts/tool_scripts/run_stage.py flow sm25-L_anchor "$wallfix_run_name" --judge stop --geometry auto
```

本次后两条入口的逐字记录（两次调用各自的 shell 均已 source 上述 .env）：

```bash
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python scripts/tool_scripts/run_stage.py judge sm25-L_anchor run_wallfix_gpt_judge_on 0_reading --verdict AI_agent/logs/experiments/2026-09-08d_wallfix_gpt/j0_verdict.json
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python scripts/tool_scripts/run_stage.py flow sm25-L_anchor run_wallfix_gpt_judge_on --judge stop --geometry auto
```

这里的 `j0_verdict.json` 是本次主 Agent 按 packet/rubric 查看实际材料后写的判词，通过标准 judge 入口提交；不是预制全 PASS。按同一输入复现本次轨迹可以使用该判词；若重新识图或输入字节改变，必须重新审阅，不能复制本次判词当新审阅。全过程从已落库的六份 reading 产品开始，没有重新做 reading 感知，没有手写 geometry/归档/评分绕过脚本，没有借旧 run 的分数当本次验收。

**标准 flow 的新阻塞：停下上报证据**

我的工作假设 X 是「W#3 归档成功、W#6 守恒通过后，标准 flow 能把新腿交给 J1」；实际 Y 是「**归档已经成功，标准入口还有一条必填审计条件没有满足，gate① 在 J1 前 BLOCK**」。这不是旧的 uv / W#1 评分题面问题，也不是 W#3 重放再次失败。

证据来自本次不可变候选目录 `case_tests/e2e_tests/sm25-L_anchor/run_wallfix_gpt_judge_on/1_correction/attempts/001/`，不是离线重算 gate：

| 实测项 | 结果 / 证据 |
|---|---|
| 两层链 | 两个 `decision_loop_outcome.json` 均 success；route 的 `response_source=model:correction_decision`、`llm_model_resolved=deepseek-v4-pro`，不是 fixed responses |
| W#3 | attempts/001 内九件归档工件完整，包含 chain_provenance 与 deterministic_core_proof；writer 没有抛异常 |
| W#6 | `checks.json` 两条 `correction.coverage` 均 PASS，zstack 与 cell polygon 检查 PASS |
| 新 BLOCK | `correction.audit_completeness`，evidence=`{"changed":false,"relied_on_testdata":true}` |
| 审计内容 | `audit.json` 与 `output.json` 中 corrections/conflicts 都是空数组 |
| W#7 | `correction.evidence_debt_coverage` 仍 FAIL→FLAG，认领缺口没有被掩盖 |
| 接受/出分 | run_manifest 只有 accepted 0_reading，没有 accepted 1_correction；未生成本次 correction score，未运行下游 |

接线证据：`run_stage.py:1189` 用 `td_path.exists()` 生成 `relied`；`:676` 不变地传入 as_drawn 的 `check_correction`。`correction.py:513` 的 `needs_audit = changed or relied_on_testdata`，`:520` 要求 corrections/conflicts 至少一条。`finalize.py:336` 只镜像新腿几何已有的审计列表。本次列表为空，所以不是重采样几何就能保证消除的错误。现有 `test_w1_flow_routing.py::test_new_leg_draw_runs_through_the_flow_shape` 用 `relied=False` 调该函数，不能代替标准入口这次的 `True` 路径。

我没有自行决定「把 relied 改 False」或凭空补审计条目，也没有把 W#7 的债加进审计来顺带消红。应由派工方明确新腿到底是否消费 testdata，以及应由哪一处记录该事实，并与另一席的审计认领工作协调。

标准 runner 对 stochastic gate failure 会立即盲重试。发现 attempt 001 的固定接线问题后，我在第二次 draw 等待 provider 时向**本次进程**发 SIGINT 停止重复调用；进程退出 **130**，不是宣称 flow 正常结束或到达 quarantine。`flow_02_correction_interrupted.txt` 保存原始 traceback，`flow_stop.json` 记录本次终点及原因。未手改 run_manifest / orchestration_state / checks。后者因 run_one_stage 尚未正常返回而仍停留在 reading 的状态，排障应同时读 attempt 001 和 flow_stop，不可把这个旧状态当“correction 没运行”。逐层工作文件可能被第二次 draw 触碰；completed draw 的证据以 attempts/001 内冻结字节为准。

复跑上述完整命令会重新经过同一标准门；模型耗时/输出可变，本交件不承诺不同调用逐字相同。修复新审计接线后，应以**新 run、judge 保持开启**继续验证 J1 和 2/3/4/5，不能把本次 reading 高分或已有历史工件折算成完整验收通过。

**我这次最薄弱的一处**

最弱的是**尚未取得完整 flow 通过和下游出分的证据**：本次真实入口停在新暴露的审计接线 BLOCK。另一方面，W#1 只排除了不适用的 legacy 检查并核验原生契约/标定/尺寸链，没有接入全部原图像素检查；通用渲染空图和原生立面语义/方向声明限制都已列账。清掉 24 FLAG、4075 项测试通过、J0 非阻塞和高 reading 分数，都不能替代尚未完成的总验收。
