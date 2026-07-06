# CV 工具箱 C0+C1 执行简报(待 Codex 方案审)

> 缘起:体检报告 B2/C1(`logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md`)+ `capability/reading_improvement_methodology.md` §2/§4(Phase B 算术下沉的具体载体=经典 CV 工具箱)+ `logs/experiments/2026-07-05_fable5_project_audit/codex_cv_plan.md`(蓝本)。已定裁决(B2 裁决 1-4):**CV=Phase B 载体;sidecar 先行不动 reading schema;工具放执行侧零 gt 可达;Haiku 4.5=首个验收模型**。
> 本批=codex_cv_plan 的 C0(契约)+C1(平面测量)+最小立面对(窗连通域+楼层线,为 Haiku 复测凑齐平面+立面两条判卷线)。
> 纪律:备份 `backup/{src,scripts,Skill}_history/2026-07-06_cv_toolbox/`;**零 reading/correction schema 契约改动;零 gate①/Phase A 行为改动;不跑任何 case**(跑 Haiku 复测=另一轮,须用户跑前拍配置)。

## 1. 形态与放置

- **模块** `src/agent/reading/cv_toolbox/`:纯 Python、确定性(无 RNG、参数全显式)、只依赖 PIL(pillow)+numpy+scipy(**执行第一步核对三者是否已在 pyproject 直接声明,缺则按 M2 模式补+裸 `uv lock`**)。
- **CLI 薄包装** `scripts/tool_scripts/cv_probe.py <tool> <args> --image <png> --out-dir <dir>`:冷启 reading 子代理经 Bash 调用,不需要懂仓库内部;CLI 负责写 sidecar(见 §3)。
- **gt 隔离**:cv_toolbox 与 cv_probe 均为执行侧件,**零 gt import/路径**;`tests/test_gt_discipline.py` 的扫描范围**扩到 `src/agent/reading/**` 与 `scripts/tool_scripts/cv_probe.py`**。
- **skill 文档** `skills/intake_pipeline/0_reading/cv_toolbox.md`(英文、纯当前 spec):何时调用、工具清单与调用样例、纪律三条(①工具只测量、语义分类仍归你按 reading_guide 判;②宁可空手不给错锚——低置信候选别硬当墙;③接受/拒绝的候选都要留在 sidecar,拒绝要给理由)。`session_kickoff.md` 加一行指针(不复制内容,防漂移)。

## 2. 工具清单 v1(6 件,codex_cv_plan 的 12 件砍半;OCR/链分组/Hough/declutter/sheet_segmenter 全 defer)

| 工具 | 输入→输出 | 核心实现(=sm21 forensics 固化) |
|---|---|---|
| `crop_zoom` | image+bbox_px(+scale)→crop PNG+**逆变换记录** | PIL crop;所有下游像素坐标必须可经变换链映回源图 |
| `wall_line_profiler` | image/crop+axis(row\|col)+recipe→peaks[](px 位置+强度+估宽) | 灰度带掩膜(R≈G≈B 且 lo<v<hi)+行/列投影取峰(prominence 阈值) |
| `px_m_calibrator` | anchor 对[(px_a,px_b,value_m),…]→scale(px/m)+**逐锚残差** | 多锚最小二乘;单锚也可但残差字段置 null;残差超阈在结果里显式 warn |
| `window_cc_detector` | 立面 image/crop+mask recipe+min_area→merged rect boxes[]+计数 | 掩膜+`scipy.ndimage.label` 连通域+近邻框合并 |
| `storey_line_profiler` | 立面 image+recipe→水平线候选(y px+强度) | 与 wall_line_profiler 同核,行投影薄包装 |
| `overlay_logger` | image+candidates(accepted/rejected+理由)→标注 PNG | 调试叠图;PNG 归 sidecar 目录 |

**统一返回结构**(每工具):`{tool, tool_version, recipe_id, params, results[], diagnostics{...}, applicability: "clean_vector"}`。**工具绝不写 reading JSON、绝不产最终建筑几何**——产的是 image-local 证据候选(不变量 #1:感知归 VLM 语义判断,测量归确定性代码,几何归内核)。

## 3. sidecar(C0 契约核心)

- 路径 `0_reading/cv_evidence/{image_stem}/NNN_{tool}.json`(+同名 `_overlay.png`),NNN 递增 append-only(复用 manifest 的最小未用序号惯例,已存在即 raise)。
- 每份 sidecar:`cv_schema: "1"`(**版本位从第一天就有**——体检 C3 的教训)+ 工具返回结构 + `source_image`(文件名+sha256 短形)+ `crop_chain`(逆变换链,顶层图坐标可还原)。
- sidecar 是**审计证据非真相源**:gate①/correction/judge 本批一律不消费(未来 J0 可引用、Phase B 双通道 schema 落地时 `anchor_px` 从这里来——留注释标接缝,不实现)。

## 4. recipe/风格档(泛化护栏,体检 B2 三机制的本批份额)

- `recipes.py` 单一常数源:`clean_vector_v1 = {gray_lo:60, gray_hi:230, rgb_tol:…, prominence:…, min_cc_area:…}`(值以 sm21 forensics 配方为种子,执行时按合成 fixture 调定)。
- 每工具结果携带 `applicability: "clean_vector"`;**v1 只此一档**,扫描/照片档不做(codex_cv_plan C5)——但字段从第一天就在,调用方看得见适用边界。
- 禁止工具内部隐式自适应阈值(那是 C5 的活):v1 递给什么 recipe 用什么,保确定性可复现。

## 5. 测试(全部不碰 gt)

1. **合成 fixture 单测**(主体):测试内用 PIL 画已知几何(灰墙线/白底/黑 tick/矩形窗阵)→ profiler 峰位 ±1px、calibrator 精确值+残差、cc detector 计数与 bbox、crop 逆变换往返、overlay smoke。
2. sidecar:append-only(重复 NNN raise)、`cv_schema` 在位、crop_chain 可还原顶层坐标。
3. gt-discipline 扩展范围绿。
4. **真图 smoke ×1**(sm21 `case_data` 平面图,非 gt):wall_line_profiler 在整图上找到 ≥5 个竖向峰(宽松断言防 flaky,只证"真图上跑得动")。
5. CLI:`cv_probe.py` 端到端一次(合成图)产出 sidecar+overlay。

## 6. 非目标(显式)

不改 reading/correction schema;不改 gate①/judge/Phase A;不做 OCR/尺寸链分组/斜线检测/杂物掩膜/sheet 切分;不做扫描/照片档;不训练任何模型;不跑 case(Haiku 复测=下一轮,用户拍配置)。

## 7. 验收与后续接缝

- 本批 done = 全量 pytest 绿 + 上述测试齐 + skill 文档/kickoff 指针落地。
- 下一轮(不在本批):Haiku 4.5 复测(同 case 同判卷尺,唯一变量=工具箱有无,promotion 线用 codex_cv_plan C1/C2 档:平面墙 ≥8/9 且 extra ≤1、立面窗 ≥12/15 且 extra ≤3)——**这是北极星战略的判决性实验**(报告 C1)。
- 远期接缝已留:sidecar→Phase B `anchor_px`;`applicability`→C5 风格档;`cv_evidence/`→attempts 集成(flow runner 落 attempts/NNN 时把 cv_evidence 一并收编,本批注释标记)。

## 8. 审阅需求

1. pillow/numpy/scipy 依赖现状核对;2. sidecar 放 `0_reading/cv_evidence/` 与现有 flow/attempts/资产收集(report eyeball collector)有无路径冲突;3. 工具返回结构有无漏掉 Phase B 必需的字段(宁可现在多留槽);4. 合成 fixture 的判定阈值建议(±1px 是否过紧);5. cv_probe CLI 参数面是否够冷启子代理无痛使用(它只有 Bash+Read);6. 有无与污染硬隔离未来设计相抵触的决定(工具应该在隔离工作区里也能跑=不依赖仓库其他路径)。

## 9. 裁决(2026-07-06,Codex 审 APPROVE-WITH-CHANGES,4 findings 全采纳,定案)

1. **API 精确定义采纳审阅件版本**(verdict §finding 1:坐标约定/峰强=prominence+FWHM/校准=强制过原点最小二乘/CC 合并规则/overlay 决策留痕)——执行以 verdict 文本为准,与本简报冲突处 verdict 胜。
2. **sidecar v1 即预留 Phase B 槽位**:`candidate_id`/`coord_space`/`anchor_px`/`visual.*`/`metric.*`/`provenance`(不改 reading schema,只在 sidecar 结构里留位)。
3. `cv_evidence/` 与 attempts/report collector 的关系=**未来集成**,实现与文档按此措辞,不声称当前已收编。
4. 范围措辞:本批不测弱 VLM 尺寸抄录能力(OCR 探针=下一轮,见报告 B2 挑战一)。
