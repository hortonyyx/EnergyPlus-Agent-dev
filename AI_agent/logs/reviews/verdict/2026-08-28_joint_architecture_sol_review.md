# 一体改架构共同出案 · sol 最终对抗审

- 日期：2026-08-28
- 席位：sol（跨家族对抗审）
- 范围：题面 §十/§十一、GLM 方案、现行源码与 sm25 签字件
- 动作纪律：只读探针；未跑全量；未改 `src/`、`tests/`、`skills/`；未安装包；未 commit

## 裁决：**REWORK**

GLM 对 Q11 优先级、profile/逐边数据不是同一轴、门必须拆锚等方向判断有价值；但当前方案还不能施工。阻断原因不是措辞：`ZoneEdgeReportV1` 被错当成投影前事实、G1 的“实现指纹”没有独立权威锚、Q11 的类型/对账门不足以表达或验证真实空间链、F-121 的输入仍是转换器自判。照稿实现会把至少三条同义反复固化成绿门。

### 阻断项

1. **B1｜Q10 的“三明治”少了最关键的一片：期望实现指纹没有独立权威来源。**
2. **B2｜`ZoneEdgeReportV1` 不是 GLM 所称的“逐边测量事实”；它存的是已经按 `basis` 扩张后的答案边。**
3. **B3｜“签字 DXF + 签字 request = 原始层”混淆了“获授权的答案输入”与“as-received 观测源”。**
4. **B4｜Q11 的 `source_unit` 与 controls 对账门都不能按稿落地；前者少 codomain，后者在 plan 上没有所声称的 entity 锚。**
5. **B5｜F-121 不能直接吃现有 `basis`；须新增投影前的拓扑边界条件，但不要复用现有 `role`。**
6. **B6｜“任一坏边 ⇒ 整层 NA”没有依赖闭包判据，作废半径仍会重演历史事故。**

### 不阻断项

1. **N1｜Q11 必须先于“两侧换单位”排期：成立。** 当前同名 affine 的输入域确实不同，先动单位会扩大静默错面。
2. **N2｜facts 纯派生、无人工直改通道、schema/profile 版本入答案键：保留。** 但须先修 B1 的独立指纹锚。
3. **N3｜Q13 的“缺一条边”分辨力夹具与 `unprojectable` 坐标零泄漏：保留。** 夹具预期须按 B6 的依赖闭包改写，不能预写成整层必 NA。
4. **N4｜往返门只防数值不可逆、不能证明方向正确：GLM 已正确降权。** 它只能是冗余数值门，不能计作独立交叉验证。

---

## Finding 详单

### B1｜unsigned facts 自带 fingerprint，不能区分“实现与产物一起改”

**主张。** GLM 把现役 G1 概括为“签字输入 + 指纹先查 + 内容重算”，并要求 `ReferenceFactsV1` “携带指纹照抄”。这个机制只能发现“树变、盘上产物没变”；若实现与 unsigned facts 同时更新，自报指纹与重算内容会一起对上。要有 `implementation_drift` 语义，**expected fingerprint 必须来自 facts 之外的获授权记录**。

**实际核过。** 读 `src/agent/judge/gt_raw_layer.py:419-438`：`converter_sha256`、`judge_config_sha256`、`vg_config_sha256` 的 recorded 值取自未进签字 inventory 的 `conversion_report.json`；只有 `vg_implementation_sha256` 取自已签 `gt.json.generator`。实读数据：

```text
converter_sha256  report=539615ab…  signed_gt=None
judge_config_sha256 report=843466dd… signed_gt=843466dd…
vg_config_sha256    report=ad3aeeb9… signed_gt=ad3aeeb9…
```

现行函数虽然在 signed GT 里已有后两项，仍拿 report 自报值比较当前树；`converter_sha256` 更是没有 signed-GT 对照。GLM 的变化表漏了第四格：**实现变 + facts/指纹一起变**。

**必须改。** `ReferenceFactsV1` 的允许编译器闭包 hash 必须锚在 facts 外：已签 review index、受控 release manifest，或等价的不可随 facts 同写的 admission record。内容重算负责完整性；独立 allowlist 负责“哪个实现获准定义事实”。红必须报告闭包文件 diff。

**本 finding 不成立的条件。** 若 facts 本身被签字覆盖，或部署环境以不可变制品/受控 release manifest 独立钉死编译器闭包，且验证器只从该外部锚读取 expected hash，则该攻击被封住。

### B2｜`ZoneEdgeReportV1.p1/p2/basis/offset` 是投影答案及其补偿记录，不是原始测量

**主张。** GLM Q12 的核心分层“逐边 `basis` = 测量事实，profile = 折叠规则”在当前载体上不成立。源码自己称 `ZoningEdgeV1` 为 “emitted zoning boundary edge”（`tarch_converter_schema.py:964-975`）；生产侧先由 `ext` 选 `basis`，再由 `basis` 选 `t` 或 `t/2` 偏移（`tarch_normalize.py:1023-1029,1058-1059`），最后把扩张后的 `z.vertices` 写成 report 的 `p1/p2`（`:3659-3687`）。

**实际核过。** 对 sm25 `conversion_report.json` 做只读统计：

```text
edges=136; basis={outer_skin:46, wall_axis:90}
offset == (t if outer_skin else t/2): 136/136
zone-edge 272 个端点到 claimed cavity 原边界：272/272 非零
距离范围：0.060000 m … 0.339411 m
```

即 `p1/p2` 已离开投影前 cavity；136/136 的 offset 关系是 `_offset_for` 的定义回放，不是第二列证据。把这些字段放进 facts，再验证 AnswerCompiler 遵循它们，会复现生产者选择而不是重新折叠原始事实。

**必须改。** `ReferenceFactsV1` 至少要在 S7 扩张前截取：cavity support line、方向、两面 source handles、厚度及 proof、邻接/外界 witness、junction 约束。现有 report 可当 migration 输入，但须先证明 `expanded edge + compensation → preprojection support graph` 在转角、厚度台阶、共享墙上是双射；不能直接改名为 facts。

**本 finding 不成立的条件。** 若架构明确把 facts 定义为“reviewer-normalized、已投影答案”，并取消从它编译另一 profile；或先落地并验证上述无损逆变换，则不再构成阻断。那也不能继续称其为“测量事实”。

### B3｜权威根可以是签字件；观测原始层不是这两个文件

**主张。** 对“当前获人批准的 GT 候选”而言，签字 DXF + request 是有效 authority root；对题面要求的“忠实转录、保留图纸偏差”的 raw/as-drawn facts 而言，不是。两种根必须分名，不能用一个 `ReferenceFactsV1` 吞掉。

**实际核过。** 

```text
review_ack.source_dxf_sha256 = 1251f651… = sm25-L_t3.dxf
as_received DXF sha256       = 4a949224…（未出现在 request/ack/index）
两 DXF 均 916 entities、handle 集相同，但 5 个实体坐标改变：
13AD, 13AC, 13AF, 160A, 13AE
```

`gt/README.md:34` 也明确：签字源图在签前修过 5 条线，最大移动约 6 mm。另读 `build_request.py:1-6,21-30,193-246`：request 的光栅标定由六张 PNG + DXF 共同拟合，zone count 则是用户输入；六张 PNG 当前字节 hash 均命中 request 的 `source_sha256`。所以这对签字件是“reviewer-authorized normalized inputs”，不是“所有观测源的最上层”。

**必须改。** 二选一：

- 把包明确命名/声明为 `ReviewerNormalizedFactsV1`，不再承诺保留 as-received 偏差；或
- authority envelope 纳入 content-addressed as-received DXF、六张 raster、签字 intervention ledger（5 线变更及理由），再由 policy 明确哪个层进入哪类评分。

这不是要求给派生 facts 再签一次；是要求先把“授权”与“原始观测”拆开。

**本 finding 不成立的条件。** 若产品契约明确只需要“人批准后的参考答案”，不需要 as-drawn/raw 语义，且文档、类型名、门均删除“忠实保留图纸偏差”的承诺，则现有二元 authority root 足够。

### B4｜Q11：一个 `source_unit` 描述不了 affine 两端；plan controls 也不是所称的 entity-point 锚

**主张 1（类型）。** `pixel_to_source_m` 的 domain 是 pixel、codomain 是 source-metre；request 的 `world_from_source_m` 是 native→world-m；manifest 同名项是 source-metre→world-m。给通用 `Affine2D` 加一个 `source_unit: native|source_m` 无法表达第一条的两端，更无法机械检查组合。

**必须改。** affine 序列化必须同时携带 `domain_space` 与 `codomain_space`（至少 `pixel`, `dxf_native`, `source_metre`, `world_metre`），compose helper 验 `left.codomain == right.domain`；字段改名只作迁移期 fail-fast，不代替空间合同。

**主张 2（对账门）。** GLM 说“controls 的 `source_point_dxf` 按 entity handle 从签字 DXF 重取”。现有 plan 数据做不到。

**实际核过。** 读 `build_request.py:241-246`：三个 plan controls 的点来自 wall bbox，却统一填图框 handle `37B/380`。用 ezdxf 重取该 handle 顶点，control 点到最近顶点距离：

```text
plan-F1: 12375.117 / 12920.917 / 11801.297 native units
plan-F2: 12573.569 / 12712.667 / 12009.234 native units
四个 elevation view 的对应 control：最近实体端点距离均 0
```

当前 validator 也没有按 plan control 的 `entity_handle` 重取；它从转换器生成的 `GTV3_FOOTPRINT` 求 bbox，再验证 control（`tarch_normalize.py:2579-2600`）。此外 `pixel_point` 与 `pixel_to_source_m` 均由同一个 calibration 解生成（`build_request.py:180-189,193-204`），所以 residual 门只能证明成对自洽。它确实能抓“把 source-metre 错喂给 native affine”的**组合错误**，但不能被宣传为独立物理标定门。

**必须改。** 分成两门：A）纯空间类型/组合门，专抓 1000×；B）标定证据门，锚真实 source feature geometry 与独立观测的 pixel feature。plan control schema 要么给真实 wall/footprint source handles + feature definition，要么明确是 `reviewed_coordinate`，不要伪装成 entity point。

**本 finding 不成立的条件。** 若 affine 改成双端空间合同，且 plan controls 重签为能从指定 source entity 唯一重取的点（或明确以人工签字坐标为 oracle、取消“独立重取”主张），则该阻断消失。

### B5｜F-121：需要新增“边界条件”，不能复用 zone `role`，也不能直接吃现有 `basis`

**裁定。** **新增一列，但不是 GLM 所写的泛化 `role`；新增投影前 `boundary_condition` + evidence。** 建议至少：`exterior`, `interzone`, `unclaimed_void`, `unknown`。证据应含 cavity-side/far-side source handles、相邻 cavity/zone 或 outside witness，并在 S7 选 offset 前形成。

**实际核过。** `ZoneReportV1.role` 位于 zone 模型，不在 edge 模型（`tarch_converter_schema.py:984-995,1107-1115`）；`review_annotations.json` 的实际值是 `corridor/office/meeting`。因此“29/29 role=unspecified”证明的是**房间用途没入答案**，不是 edge 外/内墙列缺失。另一方面，现有 `basis` 在 `tarch_normalize.py:1023-1029,1456-1463` 由“穿过墙后是否落 footprint exterior”判出，并立即决定输出偏移；它是已经坍缩的投影选择。让 exterior profile 直接吃它，等价于 identity：转换器判什么，编译器就复述什么。

profile 应映射：

```text
axis:      any resolvable wall boundary -> wall_axis
exterior:  exterior -> outer_skin; interzone -> wall_axis;
           unclaimed_void/unknown -> unprojectable（仅传播到依赖闭包，见 B6）
```

**本 finding 不成立的条件。** 只有在产品永久只保留当前这一种输出、并把 converter `basis` 明定为规范答案而非可审事实时，才可直接吃 `basis`；那会取消 profile 折叠与双投影校验目标，不能再声称实现了 Q12(c)。

### B6｜作废半径 = 依赖闭包，不是“层”或“边”

**裁定。** 原子单位应由**输出不变量的依赖图**决定。对失败事实节点 `f`，作废集合是 `f` 到可评分输出节点的最小传递闭包；闭包之外可继续出结果。绝不允许为了继续出分而产生开环、单侧共享墙或偷偷缩小分母。

**实际核过。** sm25 共 136 edge；按 `(floor, 无向 p1/p2)` 合并后 108 条几何边，其中 28 条被同层两个 zone 共享（56 个 edge instances）。所以“逐边作废”会立刻破坏相邻 zone 的共同边；“整层作废”又会把 80 条不共享/大量不依赖边一起杀掉。

**必须写进设计的传播规则。**

1. **局部 wall segment 的 thickness/boundary_condition 缺失**：作废该 segment、两端 junction、所有 incident zone ring，以及依赖这些 ring 的几何指标；传播到每个 ring 重新闭合且共享边双侧一致为止。
2. **junction/corner 不确定**：作废该 junction 的全部 incident segments 与 incident rings；不是只杀报错边。
3. **view affine/domain/calibration 失败**：该 view/floor 的所有世界坐标同源，故对应坐标指标整 view/floor NA。
4. **opening 局部歧义**：默认只作废该 opening、host segment 及消费它的 opening 指标；只有当它同时是 wall thickness/拓扑证据时才沿 segment 传播。一个洞口不得无条件杀 zone 数、外轮廓等无依赖指标。
5. **profile-sensitive**：boundary condition 缺失可能使 `exterior` NA，但若 axis 所需 baseline/thickness 完整，axis 仍可出；作废的是 `(component, profile, metric)`，不是裸 floor。
6. **评分层**：每个 metric 声明 required components 与 coverage。缺 required component ⇒ 该 metric NA；不得对剩余边重归一化。顶层若政策要求所有 metric 完整，可显示总 verdict NA，但必须保留其它 metric 的有效读数与局部诊断。

**本 finding 不成立的条件。** 若用户明确签字规定“任一几何分量缺失，整层所有指标均无意义”，且评分契约从不消费局部结果，则整层事务可成立；当前“角部洞口曾杀整份判卷”的反例与多指标结构均不支持该前提。

---

## 其它同义反复 / 非独立门清单

1. **Q11 plan calibration residual**：`pixel_point` 与 affine 同一拟合生成，再用 affine 映回该 point；这是配对一致性，不是独立标定。B4 已给修法。
2. **Q12/Q13 gate 1**：现有 `basis` 同时选“哪些边移动”和移动量 `t`/`t/2`；实测 offset identity 136/136。若 exterior edge 集仍从 `basis` 取，门会验证生产者定义本身。须改锚 B5 的投影前 boundary condition + 独立 thickness proof。
3. **Q13 往返**：同一 shift 实现正向/逆向，符号同错可恢复。GLM 已承认；不得算第二条独立证据。
4. **G1 reproduction**：同实现重算只证明 artifact integrity；不能证明派生语义正确。再加 B1 的 unsigned expected fingerprint 后，连“实现漂移”也只覆盖单边变化。
5. **R-3 台阶双向对账**：若“不规整事实表”由 AnswerCompiler 输出台阶反写，仍是自报。表必须从投影前相邻 support lines + boundary-condition transition 独立求出，compiler 只消费，不得生产自己的 expected ledger。

## ⭐ 本审自己找到、题面/GLM 未点名的问题

1. **最重要：G1 的三项 report-side fatal fingerprint 全取自 unsigned report，自报 fingerprint 可与产物一起改。** GLM 把现役样板当成完整信任机制，实际缺独立 expected-hash authority（B1）。
2. **`ZoneEdgeReportV1.p1/p2` 全是投影后坐标。** 272/272 端点不在 claimed cavity 边界；“把现有逐边正式类型接进 facts”不是接线，是一次语义逆迁移（B2）。
3. **`Affine2D.source_unit` 只有一端，无法表示 pixel affine 的 codomain。** 应建 domain/codomain 空间合同，不是再加一个单位字符串（B4）。
4. **plan control 的 handle 是图框、点却是墙外包 bbox。** “handle→DXF 点重取”在 F1/F2 会差约 11.8k–12.9k native units；现有 validator 实际绕过该 handle，改用转换器产出的 footprint（B4）。
5. **GLM 用错了 `role` 的语义。** 现有列是房间用途，不是 edge 外/内墙；D-2 的数值真、论证对象错（B5）。

## 施工前最小返工清单

1. 给 facts compiler 建外部获授权 fingerprint anchor；画清 input/implementation/facts 三者谁签谁。
2. 定义真正投影前的 `ReferenceFactsV1`；不得直接复制 `ZoneEdgeReportV1.p1/p2/basis`。
3. 将 authority root 与 as-received observation root 分名；决定 sm25 五线修订属于哪一层。
4. affine 改成 domain/codomain；重做 plan controls 的证据语义；类型门与标定门分开。
5. 新增 edge `boundary_condition`（非 zone role），附投影前 evidence；profile 不直接吃 emitted basis。
6. 把 B6 的依赖闭包和 metric coverage 写成 AnswerCompiler 契约，再写“缺一边”夹具预期。

## 我最没把握的地方

1. **五线修订的授权语义。** README 说用户已拍板接受，但我没看到独立 intervention ledger/签名字段；若团队把“签了修后 overlay”定义为同时追认 as-received→edited 的全部差异，B3 的授权风险降低。不过 raw/as-received 命名冲突仍在。
2. **斜墙/曲墙的 boundary witness。** sm25 无斜边；我给的 adjacency/topology 模型比二元 role 稳，但尚未用非正交 case 验证法向、joint closure 与多面命中。
3. **依赖闭包是否允许局部计分。** 技术上可精确传播；产品层是否接受“总 verdict NA、部分 metric 仍有读数”需要用户政策。我的硬线只有两条：不得破坏几何不变量，不得因缺失而缩分母获益。
4. **现役 G1 的对抗威胁模型。** 若仓库权限保证实现文件与 report 永远不可能被同一主体同时改，B1 的现实攻击面会下降；但本任务是对抗审，且 unsigned facts 设计不能靠这种未声明运维假设立信。

## 复核命令摘录

```bash
# 读类型/生产链
nl -ba src/agent/judge/tarch_converter_schema.py | sed -n '760,775p;960,1000p;1090,1120p'
nl -ba src/agent/judge/tarch_normalize.py | sed -n '1018,1065p;1400,1470p;2550,2625p;3655,3692p'
nl -ba src/agent/judge/gt_raw_layer.py | sed -n '390,455p'

# 签字根与 as-received 差异
sha256sum case_tests/test_baseline/gt_sources/sm25-L_anchor/{sm25-L_t3_as_received.dxf,sm25-L_t3.dxf}
python3 - <<'PY'
import ezdxf
def sig(path):
    out={}
    for e in ezdxf.readfile(path).modelspace():
        if e.dxftype() == 'LINE':
            out[e.dxf.handle]=(e.dxftype(),tuple(e.dxf.start),tuple(e.dxf.end),e.dxf.layer)
        elif e.dxftype() == 'LWPOLYLINE':
            out[e.dxf.handle]=(e.dxftype(),tuple(e.get_points()),e.closed,e.dxf.layer)
        else:
            out[e.dxf.handle]=(e.dxftype(),e.dxf.layer)
    return out
a=sig('case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf')
b=sig('case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf')
changed=[h for h in a.keys() & b.keys() if a[h] != b[h]]
print(len(a),len(b),set(a)==set(b),len(changed),changed)
# 916 916 True 5 ['13AD','13AC','13AF','160A','13AE']（次序可异）
PY

# request 的六个 raster 内容锚
python3 - <<'PY'
import hashlib,json,pathlib
r=json.load(open('case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json'))
root=pathlib.Path('case_tests/e2e_tests/sm25-L_anchor/case_data')
print([(x['source_label'],hashlib.sha256((root/x['source_label']).read_bytes()).hexdigest()==x['source_sha256']) for x in r['raster_overlays']])
# 六项均 True
PY

# report 语义探针（json + shapely，只读）
python3 - <<'PY'
import collections,json
from shapely.geometry import Point,Polygon
r=json.load(open('case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json'))
edges=[e for z in r['zones'] for e in z['edges']]
ok=sum(abs(e['offset_m']-(e['thickness_m'] if e['basis']=='outer_skin' else e['thickness_m']/2))<1e-12 for e in edges)
cavity={c['claimed_by']:Polygon(c['vertices_m']) for c in r['cavities'] if c['claimed_by']}
d=[cavity[z['zone_id']].boundary.distance(Point(p)) for z in r['zones'] for e in z['edges'] for p in (e['p1'],e['p2'])]
q=lambda p:tuple(round(x,6) for x in p)
g=collections.defaultdict(list)
for z in r['zones']:
    for e in z['edges']:
        g[(z['floor_id'],tuple(sorted((q(e['p1']),q(e['p2'])))))].append(z['zone_id'])
print(len(edges),ok,sum(x>1e-9 for x in d),len(d),min(d),max(d),len(g),sum(len(v)==2 for v in g.values()))
# 136 136 272 272 0.05999999999999516 0.33941125496955066 108 28
PY

# controls 锚点探针（ezdxf，只读）
python3 - <<'PY'
import json,ezdxf,math
req=json.load(open('case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json'))
doc=ezdxf.readfile('case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf')
ent={e.dxf.handle:e for e in doc.modelspace()}
for ro in req['raster_overlays']:
    ds=[]
    for c in ro['calibration_controls']:
        e=ent[c['entity_handle']]
        pts=([tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]] if e.dxftype()=='LINE'
             else [tuple(x)[:2] for x in e.get_points()])
        ds.append(round(min(math.dist(c['source_point_dxf'],p) for p in pts),3))
    print(ro['id'],ds)
# plan-F1 [12375.117,12920.917,11801.297]; plan-F2 [12573.569,12712.667,12009.234]
# 四个 elevation view 均 [0.0,0.0,0.0]
PY
```
