# 方案：天正合并 CAD → 满配 gt（评测答案自动生成）

> 状态：**设计待审**（2026-06-20）。前置工具链已落地（ezdxf + `inspect_dxf.py` + 合成天正样例测试）。
> 关联：[gt/README.md](../../case_tests/test_baseline/gt/README.md)（gt 铁律）、[per-stage 校验+judge 架构](../../memory)（judge 用 gt）、`render_gt.py`（gt 渲染核验）。

## 1. 目标与动机

gt（评测标准答案）目前由**人读 PNG** 产出，只能断言人能稳读的字段（窗数/立面/楼层/sill-head/区划），
故意**不含窗 along-facade x**——因为人读窗 x 不准，写错会让 judge 把**正确输出判错**（false negative）。
这是被生产方式逼出的妥协，不是 judge 不需要更全的答案。

**换来源即可解锁满配 gt**：从权威 CAD（天正 DWG/DXF）**机器级精确**地抽出几何 → gt 可安全做满
（精确窗 x+宽、精确区划、门），人为误差归零。这正是用户要的"尽量全的标准答案"。

**一鱼两吃**：同一套 CAD 解析器也是未来 **CAD 矢量输入模态**（区别于当前图片识别腿）的种子——
区别只在消费方（喂 0_reading 而非喂 judge），解析逻辑共享。

## 2. 两个硬问题（决定可行性）

**P-A. 天正自定义对象 ezdxf 读不到——但大概率能由我们这边吸收（2026-06-20 修正）。**
墙/门窗/房间是 TCH_* 专有对象，未炸开时 ezdxf 读成 `DXFTagStorage`（几何无法解释）。**但**天正对象
**另存 DXF 时**（`PROXYGRAPHICS` 默认开）会把炸开图元**缓存进文件且保留原图层** = proxy graphics，
而 **ezdxf 自带 `ProxyGraphic` 解码器**（已验证）能把它解出来。所以**用户负担降到最小**：
- **首选**：用户**正常「另存为 DXF」**（注意是 DXF，ezdxf 不直读 DWG）→ inspector/extractor **先尝试
  proxy-graphics 解码**拿到带语义图层的几何，**不需要专门「图形导出」**；
- **回退**：仅当文件**没存** proxy graphics 时，才让用户在天正「图形导出」（或 EXPLODE 另存）。
- 这是**一次性 per-case，非 per-run**；proxy graphics 是近似图元（弧可能成多段线），对 gt 布局意图够用。
- `inspect_dxf.py` 的 `proxy_or_unsupported` 是初筛；inspector 已能**安全读 TCH 对象的层**（`_layer` 回退
  扫 group code 8）+ 报 `custom_objects` + 给出 图形导出 建议。

**实测结论（2026-06-20，sm21 真文件）**：用户普通**另存 DXF** 后，几何仍锁在活 TCH 对象里
（`TCH_WALL`×48 在 WALL 层 / `TCH_OPENING`×29 在 WINDOW 层 / `TCH_DIMENSION2`×72），**ezdxf 能读层、读不了几何，
proxy-graphics 解码实测返回空**——"首选直接吸收"对天正活对象**行不通**。改走**回退=「图形导出」**后
（`SM_21_t3.dxf`）→ `proxy=0`、WALL 216 线 / WINDOW 29 块 / E_WINDOW 18 / PUB_DIM **165 个 DIMENSION（精确尺寸）** /
6 图名 / **6 视图区全聚出**、块名带语义（`$TCHSYS$WIN2D`×15=正好 gt 15 窗、`$DorLib2D$`×14=门）。
→ **天正路径的既定前置 = 一次「图形导出」**（保留语义层+图名，几何变纯线，干净精确）。SAVEAS 直读
仅在非天正/已炸开文件成立。

**P-B. 合并文件按构件分层、不按视图分层。** 所有平面/立面的墙都在同一 WALL 层、窗都在 WINDOW 层。
所以**不能靠图层分视图**，必须：①**先按空间把模型空间切成各视图区域**（聚类成"一层平面/南立面…"包围盒，
用图名文字命名）→ ②**再在每个视图区内用图层认构件**。`inspect_dxf.py` 的 `candidate_view_regions` +
`titles` 已给出这一步的原料。

## 3. 纪律（务必守住，与 gt 铁律一致）— Codex 审后强化

**逐 case bundle（2026-06-20 用户定）**：一个 case 的全部 gt 内容放一个文件夹
`gt/<case>/`：`gt.json`（答案）+ `source.dxf`（来源 CAD）+ `renders/`。

| 数据 | 谁能看 | 放哪 |
|---|---|---|
| **源 CAD（DXF）** = 答案级精确几何 | 仅 gt 生成器 / judge / 人 | `gt/<case>/source.dxf`（与 gt.json 同 bundle，**绝不放 `case_data/`**——执行器读到=识图任务作弊）|
| 抽出的 `gt.json`（含精确 x） | judge / 人 | `gt/<case>/gt.json` |
| 渲染件 | judge / 人 | `gt/<case>/renders/` |
| 识图输入 PNG | 管线（0_reading）| `case_data/*_view.png`（原位）|

> **与 Codex H1（"DXF 别在 gt 根下被 rglob 吃"）的调和**：用户要逐 case 聚拢，故 `source.dxf` 留在
> judge-only 的 gt 根下而非独立 `gt_sources/`。安全靠两点而非靠分目录：①`load_gt` **只按 case 读
> `gt/<case>/gt.json` 这一个文件、不 rglob**（DXF 安放其侧不被误读）；②真正的边界 = `source.dxf`
> **绝不进 `case_data/`**，由下方 (b)3 文件系统隔离测试机械守。代价：放弃"物理隔离"换"逐 case 聚拢"，
> 由测试补上保证。

**(a) 绑定做成机械指纹（非仅口诀）**[Codex H3]：gt.json 记 `_cad_sha256` + `_png_sha256_by_view{}` + 每视图 `bbox/origin/scale`；`gt_from_dxf` 生成时**校验 PNG 与 CAD 指纹对得上**才出 gt，对不上 fail-fast（防"陈旧 PNG + 新 CAD"生成貌似合理实则假的 gt，overlay 未必逮得住）。

**(b) discipline 测试拆三个目的**[Codex H2]（原"扩禁扫名单"是错的——`_scan` 扫 Python 子串，塞 `.dxf`(二进制)会崩；把离线工具 `gt_from_dxf`/`inspect_dxf` 塞禁扫又自相矛盾，它们本就该引用 gt 路径）：
  1. **runtime import 面递归 AST 扫**：`src/agent/{pipeline,correction,nodes,…}` + `src/validator/checks/*` 不得 import `src.agent.judge.gt`、不得出现 `test_baseline/gt` 路径、不得访问 `_source`/`openings` fixture。
  2. **离线工具不被 runtime import**：断言 `gt_from_dxf`/`inspect_dxf` 不在任何 runtime 模块 import 图里。
  3. **文件系统隔离**：断言 `case_data/` 及任何执行器可读 fixture 路径下**没有** `.dxf`/`.dwg`。

**(c) 绑定铁律**：被识别的 PNG 必须从同一份 CAD 导出（由 (a) 指纹机械守）。`gt_from_dxf.py`/`inspect_dxf.py` 是离线工具（`scripts/tool_scripts/`），写 gt 目录；gate①（`src/validator/checks/*`）/执行器（`src/agent/pipeline.py`）绝不 import。

## 4. 抽取管线（确定性，逐视图）

```
DXF (天正图形导出后)
  → [S1 inspect]      inspect_dxf.py：单位/图层/proxy 体检 + 图名 + 视图区预览
  → [S2 segment]      结构实体 bbox 聚类成视图区 → **命名按三档（真文件常无图名）**：
                      ①图名文字(若有,最稳) ②per-case 布局 manifest(零改图) ③几何启发式
                      (宽: N/S=footprint W·E/W=D; 门: 入口立面/底层平面有门洞; 窗数对 gt) → 判 plan/elev/facade
  → [S3 plan extract] 每平面区：WALL→footprint+隔墙→cells/zones；房间对象/房名 TEXT→role；
                                WINDOW→中心+宽→吸到外墙边→定 facade + along-facade x；DOOR 同理
  → [S4 elev extract] 每立面区：WINDOW 矩形→竖向 [z_bot,z_top]；地线/层分隔线标定→sill/head；
                                按层带计数；DOOR 同理；facade 来自图名
  → [S5 cross-ref]    每 facade×floor：plan 给 (x,宽,数) ↔ elev 给 (sill,head,数)；
                                **计数必须对上**（不对=抽取错或图纸不一致→flag），合成统一窗记录
  → [S6 normalize]    各视图本地坐标→世界坐标（footprint SW=原点，项目 §5.1 全局系）；mm→m(÷1000)
  → [S7 emit]         满配 gt.json（窗带精确 x+宽，区划精确，门）+ _source 元数据
  → [S8 overlay]      render_gt 叠到原 PNG（同源→变换精确）→ 人确认对齐
```

**确定性边界 + Codex 审后修正**：
- S2–S7 是代码（无 LLM）；唯一非确定性点 = **S3 房间 role 推断兜底**（无房间对象/房名时）——**单独隔离**，输出标 `role_inferred=true`，不污染其余确定性字段。
- **S2 是"提案"非"权威"**[Codex M-S2]（最脆步）：bbox 聚类**先滤掉标注/轴线/引线/图框层**再聚；单一全局 gap 在视图尺寸悬殊或标注/引线跨视图时会误并/误分 → 聚类结果须经**图名/图框证据 + inspector 报告 / 用户确认**坐实；歧义不静默，报出来。
- **S5 计数核做分级**[Codex M-S5]（非硬相等）：必备规范立面 exact-match；缺/偏/重复视图（背立面省略、详图放大重画、内窗）= warning；仍有不一致时**要人确认**才出"答案级"gt。

## 5. gt schema 扩展（**加字段、后向兼容**）

```jsonc
"windows": [
  { "facade": "South", "floor": "Floor 2", "count": 4,
    "sill_m": 4.0, "head_m": 5.8,
    "openings": [                         // 新增：精确逐窗（CAD 来源才有）
      { "x_m": 0.9, "width_m": 1.2 }, ... // along-facade 起点 + 宽（世界 m）
    ] }
]
// zones[].rect_m 仍在，但 CAD 来源时是精确值（非 ±墙厚意图）
// 顶层新增： "_source": "cad_dxf", "_cad_file": "source.dxf"(bundle 内相对), "_extractor": "gt_from_dxf vX"
```

- **兼容**：现有 judge / `load_gt` / `render_gt` 读 count/sill/head/rect_m 不变；`openings` 是**可选附加**（unknown key 透传）。
- **加 `"schema_version": 2`**[Codex M-§5]——区分 v1 人读意图 gt 与 v2 CAD 精确 gt，消费方据此决定是否吃 `openings`。
- **`openings` 语义须显式定义**[Codex M-§5 / Low-render]，否则"精确画在错坐标系"：①坐标系 = **facade-local**；②原点 = 该 facade 的**具名角**（如 South 从西端 x=0 向东，规则随 facade 列表固定）；③单位 m；④`x_m` = 窗左缘 along-facade；⑤不变量 **`count == len(openings)`**；⑥**容差意图 = judge/人的参考真值，非 gate① 阈值**（见 §6）。render_gt overlay 须按此坐标系画并对每个 facade 方向加测试。
- **指纹**（§3a）：`_cad_sha256` / `_png_sha256_by_view{}` / 每视图 `bbox/origin/scale` 一并落 gt，供绑定校验。
- `render_gt`：检测到 `openings`（且 schema_version≥2）则按精确 x+宽画窗（不再 `x schematic`）；无则维持示意。

## 6. 与 §2 "精确坐标谁判" 的关系（不冲突）

gt/README 定过：精确坐标的**容差带判过/不过**归确定性层（gate①），不归 gt/judge。**仍成立**：
- gt 的 `openings.x_m` 是**真值参考**（judge 拿来对、人拿来核），**不是** gate① 的判定阈值；
- gate① 上线无 gt，仍只用带容差不变量判管线输出；
- judge 用精确 gt 把"窗 x 对不对"从"看原图估"升级为"对精确答案"，检出 #2（South 2F 窗 x bug）更稳、可定位。

**"参考非阈值"要机械守、非口头**[Codex H4]：光写规矩挡不住后人把 `openings.x_m` 接进 gate①。靠 §3b(1) 的 runtime AST 扫强制（checks/* 与执行器不得引用 `openings`/`judge.gt`/gt 路径）；并把"`openings` = judge-only 参考"写进 gt/README + schema_version 注释，不只写在本方案。

## 7. 风险 / 待真文件确认的开放项

- **窗的 DXF 表达**：LINE 对 / LWPOLYLINE 矩形 / 块 INSERT / 天正洞口残留——抽法不同，**看 inspector 报告定**。
- **房间对象**在不在：在则区划+role 直接拿；不在则 role 靠布局启发式（弱），区划靠隔墙切分。
- **立面 z 标定**：依赖可靠地线 + 层分隔线/标注；若立面只画窗洞无楼层线，需用尺寸链文字辅助。
- **plan↔elev 计数交叉核**：可能暴露图纸本身不一致（人画的）→ 作为 gt 质量信号 flag，不静默。
- **多余视图**：同文件里的详图/大样/总图按图名过滤掉。
- **单位/比例**：天正常 mm；若某视图被缩放比例放置需用标注真值反算（一般 1:1 模型空间）。
- **泛化**：sm21 跑通后，别的 case / 真实脏图（无分层、炸开、无房间对象）需额外鲁棒性——属未来模态轨。
- **inspector P1 硬化**[Codex Low]：①proxy=0 不等于几何可用（窗可能是匿名块）→ 加**逐构件可用性核**（块展开后数到 usable wall/window/door 图元）；②`_entity_bbox` 对嵌套 INSERT/XREF/匿名块不全 → 递归解块、报未解析/xref 计数；③图名正则放宽（`一层平面`/`首层平面`/`南立面`无"图"/`1-1剖面`+东西南北朝向词）+ 暴露未分类文字簇；④分桶 bbox（几何/标注/图框/全部）让坏分割可见。本轮已先放宽图名正则（见 inspect_dxf）。

## 8. 分阶段

- **P0（本轮 ✅）**：装 ezdxf；`inspect_dxf.py` + 合成天正样例测试（2 测）；本方案文档。
- **P1（✅ 进行中，2026-06-20）**：用户天正「图形导出」sm21 → DXF 放 `gt/sm21_anchor/source.dxf`（**已到位**，inspector 实测 `proxy=0`/WALL 216 线/WINDOW 29 块/E_WINDOW 18/PUB_DIM 165/6 图名/6 视图区都聚出）；逐 case bundle 已建。**P1 出口规格（gate，不达不准进 P2）**[Codex M-S3/S4 planning hole]：把 inspector 报告里**实测**的实体编码逐项列出（窗=LINE 对/矩形/块/洞口？房间对象在否？立面层分隔线/地线在否？），并为**每个 gt 必填字段**指定 **唯一**：解析规则 | 人工 override 路径 | fail-fast 诊断——三者缺一不写该字段的解析。
- **P2**：写 `scripts/tool_scripts/gt_from_dxf.py`（S2–S7，含指纹校验 §3a + 分级核 §4-S5）→ 生成 sm21 满配 gt；与现人读 gt 对账（计数/sill/head 应一致，x 新增）。
- **P3**：`render_gt` 加精确 overlay 模式；人浏览器/图片确认对齐。
- **P4**：测试（合成 + 真 sm21 子集）；扩 `test_gt_discipline`；更新 gt/README + 手册。
- **P5（later）**：泛化其他 case；CAD 输入模态轨复用解析器。

## 9. 验收

- `inspect_dxf.py` 在真 sm21 DXF 上：proxy=0（导出正确）、6 视图区、6 图名、构件层可辨。
- `gt_from_dxf.py` 出的 sm21 gt：计数/sill/head 与现人读 gt **一致**（回归锚），新增精确 `openings`。
- overlay 图：gt 区块/窗/门与原 PNG **严丝对齐**（人确认）。
- 纪律测试守住：源 DXF 不在 case_data、gate①/执行器不碰 gt 与 dxf 工具。

## 10. 输入来源适配与归一化（gt vs CAD 模态，2026-06-20 加）

**两个消费者，需求不同，别混为一谈**：

| 消费者 | 源格式谁定 | 要不要归一化层 |
|---|---|---|
| **gt（内部评测数据）** | **我们说了算**（测试 case 用啥画我们定）| **不需要**——统一一种干净格式，一个天正适配器够 |
| **CAD 输入模态（产品，真实用户）** | 用户**任意**（天正/ACA/Revit 导出/纯手画）| **需要** |

**模态的归一化架构** = **各方言适配器 → 一个 canonical 几何 IR**，且该 IR **= 0_reading（图片识别）
产出的同一目标**（per-view: walls 段 / openings 位置+尺寸 / rooms 多边形+名 / dims，世界坐标）——
下游（correction / 几何内核 / gt）对来源无感。按"语义富→贫"排谱：

- **语义富**（天正/ACA：对象自带类型+图层）→ **确定性适配器**（读对象/层，便宜可靠）。本方案的天正抽取
  即第一个（最富）适配器。
- **语义贫**（纯线条/手画：无构件语义）→ 类型从几何**推断**，**这恰好退化成"识别"**，与图片管线同构。

**关键洞察**：越往语义贫端，"解析 CAD" ≡ "识别"。归一化层在贫端**复用识别栈、不另造平行系统**，
否则长成庞杂的分叉。

**现在的边界**：**不全建**。本轮只建天正适配器（gt 用），但**把 canonical IR 边界先定死**（天正适配器
输出 = IR），避免被天正锁死；将来加 ACA/手画适配器 = 接插件而非重写，**真实 case 出现一个加一个**。
