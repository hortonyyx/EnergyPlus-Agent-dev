---
name: tarch-gtv3-converter
description: 天正真实建筑图→GT v3 转换器立项(2026-07-22·sm24收官前置):v3提取器喂不进双线墙+断开洞口·走转换器不改画图习惯·主干=腔体+逐边外扩不做配对·P0-P2施工后⛔sol对抗审REWORK(3BLOCKER假绿主保险+8MAJOR)·✅2026-07-23返工CLOSED(terra施工6轮·sol写审核单·GLM验证性对抗审=APPROVE-WITH-CHANGES·3BLOCKER全修独立验真·G8真独立+同墙门+九门neuter零假锁+hashgate+PASS全门·HC-03/HC-02两MAJOR顺手关·1539绿)·残留MINOR登记跟进债·⚠️sm24 gt bundle待真人签G10才能重生成/晋升·之后素材入仓+跑sm25-L=C2收官·动手前必读实测坑
metadata: 
  node_type: memory
  type: project
  originSessionId: 777db20f-4da4-4093-bbb3-ec03888153ad
  modified: 2026-07-26T06:53:51.405Z
---

**背景**:sm24 收官需补 gt。gt 提取器（[[cad-to-gt-direction]] 记的 v2 矩形网格法）**已被 B4a 重写成 GT v3**（真拓扑 polygonize·支持 L/U/回字）。**但 v3 喂不进天正真实建筑图**——v3 要**单线**区划边界（相邻房间共享一条线·polygonize 每面一房间），天正画**真实建筑图**（墙**双线**·门窗洞处墙线**断开**）。实测：全墙线 polygonize=23 面全双线夹层、仅外皮=0 面 18 dangle。**不能退回 v2**（矩形网格法会把 L 走廊切两块=本 case 要判的缺陷本身）。

**用户拍板(2026-07-21)**:走**转换器**、**不改人类正常画图习惯**（否决手画区划线=违不变量 #6·复杂建筑手画不可行且**画错的是答案**）。保留两条已实证画图约定：`edge` 层视图框+框内图名（切视图从聚类猜变确定判定）·房间名标注 sm25 起（天正导出 DXF **不带房间名**·全图仅图名文字）。**L 走廊算 1 热区·sm24 总 8 区**（⇒ 本 case 考「内核能否合并切碎的碎片」·跑出来大概率当场红=真实水平）。

**方案定稿** = `proposals/tarch_to_gtv3_converter_plan.md`（双独立 Opus+sol **跨家族**互不可见→主控综合→GLM 对抗审 APPROVE-WITH-CHANGES·10 成立/0 不成立/1 无法判定）。**主干 = 腔体+逐边外扩**:补洞→polygonize→面积二分出腔体→逐边测厚外扩（外墙落外皮/内墙落轴线）·**明确不做双线配对**（绕开 sol 自认最脆环节 +「厚墙 vs 窄房间」信息论不可识别）·接头 5 类结构性消解无特例代码。**不改 v3 提取器本体**（转换器落 `src/agent/judge/`·产规范化几何交现有链）。sol 配对路线留 backlog。

**动手前必读的坑（实测·血泪）**:
- **墙厚不统一**:外墙 240/**内墙 120**（禁 `DEFAULT_WALL_THICKNESS`·厚度走六类离散证据逐墙存 proof）。⚠️ 主控事实底座第一行就写错「墙厚统一 240」、派单里还专门警告别烤死墙厚统一 = **自己打脸**；双独立两方都独立纠正了（双独立的价值实证）。
- **门块 bbox ≠ 洞口**（含开启扇·越出墙皮 660mm；**窗块**才 = 洞口 240）·门窗须分别处理。
- **v3 拒 INSERT 仅在边界选择器路径**·开口路径 `virtual_entity_bbox` 反而**要求** INSERT。
- **内部洞口 v3 不可表达**（sm24 21 洞仅 14 外围·剩 7 内门 = 判卷盲区，非「没有内门」而是「有但判不了」）。
- **回字形带洞 = 硬例外**（profile/提取器/validator 三处拒内环·**S7 远端分类只查外环、带洞时朝内院墙会误判**·sm27 前须单独立项，见方案 §4.3）。
- **G8 反演门须真独立**（禁引用 S5 `WallRegion`·否则塌缩成 `footprint−zones` 恒等式 = 假绿·九门每门配必红夹具）。

**治理教训（本轮·通用）**:**探针数字必须随稿落盘脚本**——Opus 报的拓扑数字（faces=51/Σ=200/8 腔体…）初次未落盘,GLM 复现不出即判「无法判定」、不能作裁决依据;落 17 脚本（`logs/experiments/2026-07-21_sm24_gt_extraction/probes/`）后主控独立跑 `final.py`/`final2.py` 逐项吻合才结清。另:**对 GLM 用结构化核验清单**（每条写死「验什么/什么算不成立」·禁「看起来合理」）= 把任务从其弱项探索性改造为强项验证性,有效（主动构造反例+独立推翻数字+3 清单外发现）。见 [[opus-controller-fable-spot]]。

**下一步** = 下轮开新会话施工 P0–P2 = **GLM-5.2 施工 + sol 审**（返工复核按需·复杂任务才加保险=Opus 子代理·用户 2026-07-21 拍板）·派单 `logs/reviews/request/2026-07-22_tarch_converter_construction_dispatch.md`·**P0 必先解决 §6.1 保护路径矛盾**（`_protected_dxf_source` 与 bundle 约定打架·施工须在 staging 跑）。**转换器落地即 sm24 收官**;之后素材入仓+跑 sm25-L = C2 收官。

**施工状态(2026-07-22·主控 Opus 全程 GLM 施工)**:
- **✅ P0 已完成并 commit(`edf1477`)**=契约冻结(request/IR **多环+逐层 footprint+逐墙逐段厚度 proof**/report/source_map·全 strict)+**39 码诊断表**(无 WARN·每 BLOCK 有 remedy·`DiagCode` Literal==registry 机械守)+config 通道(**复用 `load_gt_tooling_config` 零新造容差**·量化步长 `τ_node/10` 派生)+staging+gt 隔离 opus §8.5 三条。**1473 绿零回归**。主控轻门过(独立全量+亲核 §6.1 代码属实)。
- **✅ §6.1 主控裁定 = 方案 A**(不动 `_protected_dxf_source`+`_protected_candidate_path` 双侧重保护·转换派生件晋升进 `gt_sources/<case>/`·重建走 staging 从 source.dxf)。方案 B(松输入侧保护+擦「不改 v3 入口」红线)否决。
- **✅ P1(S0–S4)已完成并 commit(`d5e57e3`)**=新增 `tarch_normalize.py`(S0 体检/S1 量化非精确正交/S2 jamb-cap 厚度证据/S3 洞口双证据**门窗分离**/S4 拓扑 polygonize)。退出门**独立重导**:洞口 **21/21**(11 窗+10 门)/三零残留(faces 51)/Σ面积 **200.0==200.0**/D2 门开启扇正确排除/外内 **14/7** 吻合 D5。13 码必红夹具。契约加 `wall_thickness_range_m`(**sanity 过滤器非厚度来源**·已披露)。**1494 绿零回归**。主控轻门过(**无抄探针·厚度取自测量证据·G4 不装恒 pass 桩避 false-lock**)。
- **✅ P2(S5–S9)已完成并 commit(`a0c2a6c`)**:GLM 分三次会话(两次撞 5h 额度墙·第三次非高峰窗口跑完)。**结构教训**:GLM 冷启动重读大文件 + 3x 高峰⇒单窗 ~43min 走不到验证;非高峰窗口才够。用户两次拍板均=等 GLM 自己收尾(保谁写谁不批)。**S5 腔体(面积二分/多环阻断)+S6 意图绑定(数量 G6 判据)+S7 逐边外扩(混合基准框/厚度变化分裂)+S8 九门(G4/G6/G7/G8 独立反演/G9 v3 预检/G10)+S9 落盘(方案A 追加 GTV3_* 图层+manifest+report+source_map 逐边 ancestry+overlay·staging 跑后显式 cp 晋升 `gt_sources/sm24_anchor/`)**。契约加域参数 `min_room_area_m2`。退出门**全绿独立重导**:8 腔体→8 区/G7 对称差 1.5e-13+**两两重叠 0**/G8 独立反演 8.3e-13/G4 14==14/G9 v3 预检 PASS/**晋升后独立复跑 v3=PASS/8 区**。14 测(sm24 退出门+L/丁字/十字/自由端接头矩阵+G4/G6/G7/**G8 翻 basis**/G9 必红)。**1508 绿+9 xfail 零回归·主控轻门过**(亲核 G8 结构独立只读 zones·pad 用域参数非烤死常数·S9 产物真落盘)。
- **⭐ 验证的价值坐实**:上两轮 892 行未验算法体藏 **4 个阻断级真 bug**,第三轮跑退出门时全暴露并修(源句柄非层名/**march pad 太小测出 8000mm 荒唐厚度令 zone 鼓进邻居**/共线 jamb 顶点塌零长边/manifest 双缩放)——每条落证+必红夹具。**bug#2 关键教训**:G8 没抓到该重叠(补偿误差在 ∪zones−∪cav 抵消)、是 **G7-overlap 子门**抓的 = **实证三道承重闸门缺一不可**。另:**v3 manifest 仿射=metres→world(m00=1)、非 tarch request 的 native→world(m00=mpu),两契约不同**(踩坑点)。
- **跟进债(登记·非阻断)**:变厚度跨边独立夹具未单造(逻辑已实现+sm24 间接验)/PNG overlay 未做(SVG only 无 matplotlib)/9 门 G1-G5 必红在 P1 文件复用/**G8 强度待 sol 活体探针深究**(∪zones−∪cav 会不会近恒等式·bug#2 暴露其盲区)/march pad 对接近 0.5m 上界极厚墙短边的边界。
- **⛔ sol 对抗审(2026-07-22·gpt-5.6-sol max)= REWORK·3 BLOCKER+8 MAJOR+2 MINOR**(裁决书 `logs/reviews/verdict/2026-07-22_tarch_converter_p0p2_sol.md`·27KB·真活体探针〔构造反例+neuter 门变异测试〕)。**主控轻门+GLM 自验双双漏判、sol 活体探针独抓**——**治理数据点:升一档交叉对抗审的价值再证,轻门非其替代**(我轻门时已标"G8 强度待 sol 深究"·路由对了)。
  - **B-01 G8 主保险失效(假绿)**:G8 名义只读 zones,**实际回放正向 S7 的 `offset_native`、不读 basis/thickness**(sol 改二者为垃圾值→G8 WKB 字节不变残差仍 0)。逼近 `footprint−S5cavities` 恒等式。两反例(墙轴线偏 60mm 无缝铺满 / 面积补偿误差)G7+G8 全过。**GLM 必红夹具是假的**(同时改 offset 掩盖 G8 忽略 basis/thickness)。
  - **B-02 三承重门两道摆设**:近阈值仅 evidence 不阻断;G10 candidate 即 passed=true;报告 status 不检查全门(令 G4 返 -1→仍 PASS)。overlay_asset 是绝对 staging 路径(fresh clone 失效)。
  - **B-03 source/request hash 运行时零校验**:声明 sha256 改 64 个 0→sm24 仍全绿 PASS(A 图意图文件能用在 B 图)。
  - **8 MAJOR**:M-01 S7 采样启发式(写死 1/50000/1)非精确事件求解+合法墙厚上限直接驱动输出/M-02 厚度没绑六类证据(source_map 34 条 proof_ids 全空)/M-03 九门必红大面积 false-lock(neuter G1/2/3/4/7/8/9→35 测全绿·仅 G6 真绑·G5 仅 free-end)/M-04 fail-closed 破(buffer(0) 静默修非法多边形/门窗规则重叠固定猜 window/hash 静默 PASS)/M-05 17/39 诊断码从未接线/M-06 P0 契约冻结被 P1/P2 加字段破坏无版本迁移/M-07 写死 mm/单层 floors[0]/方向假设+"无烤死常量"测试只扫 3 个变量名/M-08 接头矩阵负例缺+失败 overlay 缺+披露不完整。
  - **sol 验真的正确项(§5)**:测试基线可复现(51 转换器测+1508 全量+11 隔离)/sm24 数字真实/S3 门开启扇排除对/S9 hash 对/原句柄 384/384 保留+34 新增全有 source_map/gt 隔离守住/4 bug 里 #1#3#4 修到根因(#2 仅症状修复)。
- **返工出口 9 条(裁决书 §6·缺一不可)**:①G8 从 zone edge 的 p1/p2+basis+thickness 独立重算〔禁读正向 offset〕②三承重门真承重(G10 未签字不 pass·report PASS 验全门·overlay 路径 bundle-relative)③接 source/request hash gate ④S7 按事件坐标精确求解〔移除采样常量·厚度对账六类证据〕⑤补真门级变异测试〔逐门 neuter 恰对应夹具红·从触发输入重跑 gate〕⑥补强制接头矩阵五类正负例⑦恢复 fail-closed〔禁 buffer(0) 猜·未接线码接实或删〕⑧修契约版本+去烤死 /1000+floors[0]⑨补失败人核件〔BLOCK 产 overlay_diagnostics·凹区标签用 representative_point〕。
- **下一步待用户拍策略**:大返工(≈重做 G8+S7+门体系),且 GLM 两撞额度墙。P0–P2 三 commit(edf1477/d5e57e3/a0c2a6c)在 feature 分支〔WIP·未 push〕,sm24 gt bundle 由**已知有缺陷的转换器**产出、返工后需重生成、**当前不可信**。**转换器落地/sm24 收官被此 REWORK 阻断**。

**✅ 返工 CLOSED(2026-07-23·主控 Opus)= GLM 对抗审 APPROVE-WITH-CHANGES**:
- **派工(用户拍板)**:terra(gpt-5.6-terra high)施工 / **sol 写结构化核验清单**(GLM 强项=验证性审阅、弱项=探索性⇒sol 把攻击面写死成 60+ 命题清单)/ **GLM-5.2 照单验证性对抗审**(谁写谁不批:terra=GPT 侧、GLM=GLM 侧跨家族)/ 主控轻门。Claude 侧额度近顶⇒重活全在 GPT/GLM 侧、主控只写派工单+轻门。
- **terra 六轮**(1a02fc6→…→cef0de9):核心一次落(G8+同墙门+hash+PASS+G10 机制+S7 事件+证据),但**九门 neuter 测试连推三轮**(命脉·上轮 7 门假锁死在这)、我 firm 卡住+给 seam 用法才落;场景 B/五类矩阵续作补;**诚实披露不伪造自查表**(对标正面样板)。
- **主控轻门**:独立复跑全仓逐字对齐 + 亲核 G8/同墙门核心。**GLM 独立验真**(12 探针在 /tmp·零 terra fixture 导入):**3 BLOCKER 全修**——B-01 G8 trap(挖空 offset_native/nx/ny→WKB 字节不变 sd=0、basis 翻转 sd=0.42/厚度变异 sd=0.21 变红)/B-02 近阈值进 G6 承重+G10 三 hash 绑定+PASS 强制十门/B-03 hash 前置 BLOCK 全零不写几何。**九门 neuter 10×表零假锁**。转换器 fail-closed **无假绿 PASS 路径**。**1539 绿+10 xfail**。
- **顺手关两 MAJOR**(cef0de9):HC-03(`_outer_skin_gap_count` 过滤子句用原始端点→LINE 反转 gap 计数翻转=**假红**·M-07-B 未修到根·归一化 min/max 修+反转不变性测试)/HC-02(build_p1_report `/1000`→mpu)。
- **残留 MINOR 跟进债(登记 plan.md·全 fail-safe)**:TE-01 六类证据仅 1/6 落地·FC-03 多解无 solutions·FC-04 far-side 未检测·H-03 重复 plan_view id 不查唯一·HC-01 G4 `>1.0` native 阈值·HC-04 多层静默 floors[0]·S7 junction「同邻居夹住的未证变厚」静默归并(G7/G8 兜底、无假绿)·自由端 §2.6 non_zoning 证明式处理 defer(自由端一律 S4 fail-closed BLOCK·MX-01 正例 xfail 待立项)。
- **⚠️ sm24 收官尚未完成**:转换器代码已 APPROVE,但 **sm24 gt bundle 要真人签 G10 才能重生成+晋升**(source/request/overlay 三 hash 绑定·需真人看 8 区 overlay 确认语义)。旧 bundle(缺陷转换器产)仍不可信、待新转换器重跑+签字覆盖。**下一步=sm24 真人签字收官→素材入仓+跑 sm25-L=C2 收官**。
- 审轨:清单 `logs/reviews/request/2026-07-23_tarch_converter_rework_review_checklist.md`·terra 简报 `execution/2026-07-23_tarch_converter_rework_terra.md`·GLM 裁决 `verdict/2026-07-23_tarch_converter_rework_glm_r1.md`。**治理数据点**:GLM 结构化清单打法(见 [[opus-controller-fable-spot]])再次奏效=Fable 级验证性审阅、独立探针验真 3 BLOCKER+抓 HC-03/HC-02 两 MAJOR;terra 连推命脉三轮=中档执行档遇「验收纪律」类硬活需主控 firm 盯+给使能 seam。

**⏳ sm24 gt 生产(2026-07-24·进行中)= 洞口修复 CLOSED + 立面批立项**:转换器过审后跑 sm24→v3 提取产标准 gt(用户要对齐 `case_tests/test_baseline/gt/sm21_anchor` 形态·gt.json+renders/·检查过即锁定),暴露两个真缺口:
- **① v3 提取「多房间共用外墙→窗无法唯一归属」CLOSED(`2b7affad`)**:v3 边界段从 footprint 按 NSEW 切、东立面整条段贴 5 房→`_host_zones` 返 5 宿主→`opening_host_zone_ambiguous`。v3 潜伏缺口(B4a·sm24 首个多房间共用外墙案例暴露·G9 只 preflight 没跑窗挂载故审漏)。**terra option b** `_host_zones_for_opening`(按窗区间的区边完整覆盖·跨界 fail-closed)+ **Opus 子代理审 APPROVE**(2 NIT·活体探针 sm24 8 区/14 洞口唯一挂载·双 neuter 变红·补完整 extract_gt_v3 e2e 堵 preflight≠全提取)+ 轻门 1541 绿。
- **② 转换器没处理立面(`elevation_views` 声明不用=D8·又一 D8)= 立面处理批**:sm24 DXF 有 **4 命名立面**(北南西东·edge 层 5 框)+E_WINDOW 49,但 `_build_manifest` 只塞平面→无窗高/立面/overlay。**用户拍板走「设计细稿先行」**:sol 出 `proposals/tarch_elevation_spec.md`(命名立面 exact 绑定/44 线→11 窗规范闭合轮廓/5 门块→3 外门/立面窗↔平面洞口全局唯一链接/**z 只从 request 绑定地面线 datum·禁「最低线=z=0」**/G9 升完整 extract_gt_v3/修 v3 `_assign_elevation` kind 缺口=第三处 D8/typed raster/四 overlay 原子打包)→ **[M] G10 ack 主控裁=绑 review-index 整包清单 hash** → Opus 子代理审细稿(**首轮撞会话限额半截死**·抓门 z 零形状校验弱〔门块含 CIRCLE 11C=开启扇坑活体〕+对称立面镜像 sign 隐患〔South 窗严格镜像〕)→ sol 累计修订(门 z 只取受校验结构轮廓+强校验/镜像改 datum 端点定向/补 raster 第三控制点)→ **完整 Opus 审 revised 在跑**(限额已重置)。
- **③ z 基准=受信人工输入**:sm24 地面线无机读 ±0.000·窗高依赖「地面线=1F z=0」·datum handle 机器定死绑 request 但语义要**用户 review overlay 人眼核**四立面基准线。
- **派工阶梯(全轮 terra 施工 + Opus 子代理升一档审·Claude 侧额度已重置)**;codex MCP 撞 30min idle-timeout(git log 核·任务照跑)。**⇒ sm24 收官 = 立面批过审+施工+审→产完整 gt(plan+4 立面+窗高+overlay)→用户签字锁定**。立面批是剩余最重一块·尚未施工。审轨 `logs/reviews/{request}/2026-07-24_*`。

**✅✅ sm24 收官已达成(2026-07-26·主控 Opus 5)= 建成「受控转正通道」并签字落库**(1583→**1656 绿**·派工=GPT 侧 terra 施工 / GLM 验证性审 / 主控轻门):
- **卡点本质**:仓库**根本没有**把候选答案转正的路径(候选写入器拒写受保护根且只肯写 `candidate`·读取端只认 `human_verified`·中间无代码)。另查出两条:用户 07-25 签收的**候选包整个不在版本控制内**(`.gitignore` 的 `20*_*/`)、**组装包与算清单指纹的代码只在未入库实验脚本** = 07-25 治理教训在**签名绑定根**上同型复发。
- **⭐ 主控范围裁定(关键)= 先做「可复现」再建通道**:清 G6 近阈值的唯一路径是 G10 签名且**同一次 run 内**生效 ⇒ 必然带签名重跑;而重跑每次写新时间戳/GUID→答案指纹变→**签名当场失效**。两者互相否定 ⇒ 可复现是地基不是后续债。裁掉三条替代路(另写一套清门判定=第二把尺子 / 收 BLOCKED 报告=假绿 / 手工拼装 gt.json=在最高信任资产上重犯治理教训)。**实测非确定源**:`$TDCREATE`/`$TDUPDATE`/`$VERSIONGUID` + **`WRITTEN_BY_EZDXF` 内嵌写入时间**(主控起点清单不全·施工方查全)。
- **⚠️「可复现」准确口径 = 同代码 + 同输入 ⇒ 同字节**:GT 的 `generator.*_sha256` 绑**九个源码文件字节**(`gt_schema.py:731`)⇒ 涉及那些文件的改动必改指纹。故签名可验证性走「拿落盘文件重算对签名」,**不是**「从源图重新推导」——这也是为什么签名证据(`review/`)必须随答案入库。
- **主控轻门 r1=REWORK 抓 2 MAJOR**(施工方自查全绿):**恒真假门**(`if data != canonical_gt_v3_bytes(promoted)` 同一纯函数比自己·分支永不可达·注释却声称防漂移)+ **false-lock**(`test_r4_3` 直调守卫不经生产路径⇒**摘掉守卫调用后它与 R4-2 全绿**)。
- **terra 变异矩阵连推三轮**(与 07-23 完全同型)→ 主控 firm 卡 + **给死骨架**(源码行变异+镜像仓库+子进程 `-m "not mutation"` 防递归+精确串命中恰 1 次+**失败集合严格相等**)→ 预算耗尽**诚实交接**→ 新 terra 会话接手落 **25 格矩阵**,并**自查出两处真洞**(R4-9 用例先被身份门拦截**从未到达**它声称保护的 guard;ack 缺失原仅底层 `read_bytes()` 兜底)。
- **GLM 审=APPROVE-WITH-CHANGES**(命脉三条全成立·抽 8 格重跑+**裸探针独立复算**不采信测试内部断言·独立全量与主控逐数字一致·只审不修自证 9 文件 hash IDENTICAL)。**唯一 MAJOR Y-06**:所谓「双向完整性」实为 declared↔**固定白名单**、非 declared↔**目录实际文件**⇒三处 rogue 文件双双放行(fail-safe 但**声称大于实况**)→主控裁定本轮窄修(目录级真双向·白名单**精确列举**·唯一目录豁免注明理由·三位置必红+矩阵加格)+补「**纯几何篡改**」正向证明(原用例注入 `case` 被下游门冗余覆盖)。
- **终点**:主控亲跑 `build→sign(reviewer hortonyyx)→带签名重跑十门全绿 PASS→promote`,答案+7 图+**5 份签名证据**落 `case_tests/test_baseline/gt/sm24_anchor/`。请签前出具**机械比对(排除三指纹字段后逐字段全等)+ 7 图逐像素 diff(差异仅限标题指纹横条)**。**带签名重跑这步同时活体证明了可复现地基**(否则清单校验当场拒)。
- **通道形状(以后所有 v3 答案都走)**:`build_review_bundle`→`gt_review_sign.py`→`gt_review_rerun.py`→`gt_promote.py`;转正**只许动三处**(status/reviewer_id/reviewed_on + 派生 content hash),几何一律不得触碰(语义不变式门+变异矩阵锁)。答案库 README 已补该段。
- **下一站** = 测试提速小批(见 [[test-run-cadence-policy]])→ 素材入仓(sm25-L)→ 跑 sm25-L = C2 收官。
