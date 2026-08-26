# 跨家族设计复核 · orchestrator 2026-08-27 夜班四条结论

- **日期**：2026-08-27　**复核席位**：**GPT 家族 sol**（`gpt-5.6-sol`，effort `xhigh`，**只读未改**）
- **冻结 commit**：`e969580`（worktree `/tmp/ep_design_review`，复核方自核工作树零改动）
- **请求单**：`scratchpad/gpt_design_ask.md`（本轮为临时任务书，要点已逐字复述于下方正文）
- **被审对象**：`plan.md` 2026-08-27 整节（§一～§九）· 派工盘 · `proposals/dimension_basis_and_wall_thickness_direction.md` 的 08-27 节

## ⭐ 总判：**A/B/C/D 四条全部只能判「部分成立」**

最需要纠正的三处 = **C 的原点验证** · **D 的「两种读法第一份清单相同」** · **A 漏掉的可复现输入链**。

## ⭐⭐⭐ orchestrator 当场认下的四条（其余见正文 §③ 十二条）

1. ⛔ **「原点也验了」是循环论证** —— 我比的产品侧 `world_zero_px_declared` 来自 **cfg 声明**
   （`as_drawn_v2.py:579/593`：实际观测原点来自 chain fit），而 manifest 的平面标定**本身就是用全部 `WALL` 线峰拟合出来的**
   （`build_request.py:123` RANSAC）⇒ **两条链互相接近 ≠ 裁判原点正确**，而且我建议的「拿 gt 外轮廓贴墙线去验」
   **用的正是参与过拟合的那些墙线，不是 holdout**。
2. ⛔ **「≤15 mm 是尺子自带的残差、从 80 mm 容差里扣」不成立** —— 跨距残差**不是 affine 的误差上界**。
3. ⛔ **manifest 并不在权威 `gt/<case>` 包里**，只在实验归档；我写成了「已在权威处可读」。（hash 绑定成立，晋升未做。）
4. ⛔ **`conversion_report` 不是「原始层」本体** —— 它是 0.1 mm 量化 + 墙厚判定 + cavity 扩张之后的**派生审计件**；
   真正原始的是**签字 DXF + 签字 request**，而 request 里含**非 DXF 事实**（zone 数来自用户输入）。

⭐ **复核方还替我把签字链证明补完了**：promoted `gt.json` 的字节 hash ≠ review inventory 是**合法的**
（promotion 会改写 `verification` 与派生 content hash，`gt_promotion.py:51`）；按允许的逆变换还原 candidate 后，
它实算得到 byte SHA `16fa676…` / content SHA `ca4b246…`，**与签字 inventory 逐位一致** ⇒ 结论成立、我的证明步骤不足。

---

## 以下为 sol 意见正文（逐字，未改）

总判：A/B/C/D 均只能判“部分成立”。最需要纠正的是 C 的原点验证、D 的“不规整清单等价”，以及 A 所漏掉的可复现输入链。

## ① 逐条判定

### A：部分成立

成立的部分：

- 我独立读取 JSON，sm25 确为 29 zone / 136 edge；`basis` 为 90 `wall_axis` + 46 `outer_skin`，墙厚为 78×0.12 m + 58×0.24 m，并带 `offset_m`、`source_handles`、`thickness_evidence`。正式 schema 也确有这些字段：`tarch_converter_schema.py:1096`、`conversion_report.json:5867`。
- 判分 loader 只进入 `gt.json`：`gt.py:55`。
- `conversion_report.json` 被列为 non-indexed runtime file，确实不属于人工签字 inventory：`tarch_review_bundle.py:23`。

不足之处：

- “真缺口只有没人读 + 没签字”不完整。机械复现不只需要源 DXF，还需要签过的 request、manifest、工具配置和实现身份。request 本身含非 DXF 事实，例如 zone 数来自用户输入：`build_request.py:39`。这些文件目前只在实验归档中，未进入稳定的 case-owned 权威包。
- `conversion_report` 是量化、墙厚判定、cavity 扩张之后的派生审计件，不宜称为“原始层”本体；真正原始的是签字 DXF 加签字请求。报告里的边是由 `t` 或 `t/2` 偏移生成的：`tarch_normalize.py:1058`。

所以，R-6 的“存盘时扔了”确实错；但 G1 不能只做“报告 loader”，必须把完整复现输入链纳入信任根。

### B：部分成立

控制流结论成立：

- correction 会逐轴形成 `accepted/skipped/conflict`：`envelope.py:443`。
- 未 `accepted` 的轴不生成移动 intent：`envelope_transform.py:282`。
- 一轴投影、一轴不投影真实可发生；现有 annotation 明写“纯观测、不设门”：`envelope_transform.py:141`。

但“accepted=外皮、未投影=中轴”没有被代码证明：

- 未投影只是保留 correction 输入几何；输入可能是中轴、外皮或已经混合。
- envelope candidate 只有 `dimension/outline/wall_fill` 等来源，没有墙基准字段：`envelope.py:316`。因此 `accepted` 也不等价于“已证明是外皮”。

B 的落地形状应补一道完整性边界：

- 跑前声明只负责选择 `axis/exterior`，不能补足缺失证据。
- 确定性投影必须从一份逐墙 canonical reference 派生，其中明确面线、轴线、厚度、基准和来源。
- 投影应是整层/整平面的事务：所选形式全部可派生才提交；任一必需墙边不可派生就响亮 `unprojectable/NA`，不得逐轴“保留原样”。
- “一轴有立面证据、一轴没有”时：若平面 canonical reference 本身完整，仍可确定性派生，立面只作核对；若 reference 不完整，则整份不提交。这样不会产生新隐式默认。

“厚度已知即两形式无损互换”也需收窄：还必须有边的法向、墙身份、角点连接规则和投影后拓扑门，单有厚度不够。

### C：部分成立

成立的部分：

- sm25 manifest 确有六个 hash-bound raster affine：`manifest.json:1376`；sm24 确为空数组：`sm24 manifest.json:332`。
- 它独立于 reading 产品生成；当前评分器没有消费它，叠图渲染器会消费：`render_gt_overlay.py:333`。
- 签字语义最终能够闭合，但文中的证明步骤不够。我发现当前 promoted `gt.json` 字节 hash 不等于 review inventory，因为 promotion 会合法改写 `verification` 和派生 content hash；按 promotion 允许的逆变换还原 candidate 后，我实算得到 byte SHA `16fa676…`、content SHA `ca4b246…`，与签字 inventory 逐位一致。允许的唯一变换见 `gt_promotion.py:51`。

自我限定是否够：只对“跨距实验”那一小段够，对整节不够。后文“原点也验了”重新越过了限定：

- 被比较的是产品侧 `world_zero_px_declared`；代码明确它来自 cfg 声明，而实际观测原点来自 chain fit：`as_drawn_v2.py:579`、`as_drawn_v2.py:593`。这只能说明两条链互相接近，不能验证裁判原点正确。
- manifest 平面标定本身使用所有 `WALL` 线峰做 RANSAC/拟合：`build_request.py:123`。因此“GT 外轮廓贴墙线”若仍用这些 WALL 线，不是严格 holdout。
- 应使用判分侧独占且未参与拟合的特征：签字 DXF 中的门窗角点/INSERT 基点、轴网交点、datum 或尺寸延长线端点；由裁判侧在绑定 SHA 的原 PNG 上记录对应像素。每视图至少取三个非共线 holdout，并跨图面分布，报告最大值与 RMS。
- “跨距差 ≤15 mm”不是 affine 的误差上界，不能直接说成“尺子自带 15 mm”并从 80 mm 容差中扣除。若 holdout 才证明误差界为 `e`，严格判法应是：观测误差 `≤T-e` 才确定通过，`>T+e` 才确定失败，中间为不确定带；若必须二值化，要显式签字选择偏向假阳还是假阴。

还有一个落盘缺口：manifest 文件并不在权威 `gt/<case>` bundle 中，只存在实验归档；G3 必须先把它放到稳定位置，并按 promoted GT 所绑定的 candidate manifest hash 校验。现行评分器仍直接吃产品 `pos_m/runs_m`：`reading_grade.py:126`，所以“接上即可、无需契约改动”也证据不足；至少还需绑定像素坐标所对应的原图 SHA、视图及 full-image/crop 坐标框。

### D：部分成立

成立的是资产盘点：

- 签字源 DXF 存在；
- 一份 mixed-frame 派生 `gt.json` 存在；
- 缺显式 answer compiler 和不规整清单。

不成立或尚未定义的是：

- `conversion_report` 不是忠实原始层，而是 0.1 mm 量化及多步几何推导后的报告；`quantization_step_m=0.0001` 只能证明没有做 120/240 mm 一类模数吸附，不能证明“原样未动”：`conversion_report.json:12`。
- “读法甲与乙第一份清单恰好相同”过早。偏差表与吸附动作流水最多共享一个前置残差表；动作流水还依赖格点原点/相位、适用对象、最近点与并列规则、最大移动量、拓扑约束及豁免。计划自己又承认该参数尚无名字、无人签字：`plan.md:166`。这些未定前，G2 不能先产出所谓同一份清单。
- 若 correction 负责规整，裁判仍须拥有独立的预期关系或可判定约束；只给“偏多少”的事实清单不足以判断 correction 吸到了正确一侧。

## ② 严格更优的第三条路

有：先建立一个“签字事实包 + 单一答案编译器”，不要把 G1/G2/G3 和双出模投影拆成四套临时接口。

- `ReferenceFactsV1` 固定签字 DXF、精确 request、manifest、原 PNG hash、逐墙原生证据和模数政策。
- 一个纯确定性 `AnswerCompiler(profile)` 从同一 facts 同时派生 `axis`、`exterior`、像素描图分母和不规整事实表。
- run config 在起跑前只选择哪一个 projection 是正式提交/榜单，不让证据阈值选择形式；两个投影仍同时生成作互证。
- 加 metamorphic 门：两投影只允许出现声明的 `t/2` 差异；往返投影恢复；缺资料时整个投影 `unprojectable`，绝不逐轴 fallback。
- 裁判只信 harness 冻结的 config digest；产品的 frame/标定声明均只是被核对对象。

这比当前排期更优，因为它一次解决信任根、双答案一致性、C 的像素标定消费和 D 的派生边界，也避免 G1/G2/G3 各自长出不同的“原始事实”定义。

## ③ orchestrator 题面/推理错误清单

1. 只比 `ack.review_index_sha256 == inventory_sha256` 就宣布签字链完好，漏了 candidate→promoted 的合法变换证明；结论可成立，但原证明不充分。
2. 把“manifest hash 被签字 GT 绑定”写成“manifest 已在权威 case 中可读”；文件实际上未晋升。
3. 把产品选锚的跨距残差当成裁判标定误差预算。
4. 先声明跨距不能验原点，后又用产品声明原点宣布“原点也验了”。
5. 建议用 GT 外轮廓贴 WALL 线验原点，却未注意这些 WALL 线已参与 manifest 拟合。
6. B 中偷用了“未投影=axis、accepted=exterior”两个未声明前提。
7. 把“厚度已知”误写成“双投影无损”的充分条件。
8. 把 derived conversion report 称作原始层，并遗漏签字 request/manifest 对机械复现的必要性。
9. 在模数格点政策未签字时，先判两种不规整清单相同。
10. G3 被排在 G2 后没有依赖依据；标定信任与像素契约反而应先证实。
11. ①-5 写成“必须与②同批”，与“先把判分修好再改 producer”的四步顺序冲突；应先冻结判分 schema/语义，再允许 producer 实现。
12. “这段代码在新方案里还在吗”仍不够判排期；还应问它是否在受支持的迁移/兼容路径上可达。

## ④ 本批下一件最该做的事

先做一个 sm25-F1 的“裁判事实包垂直切片”，暂缓 G2 和 ②-1 扩面：

1. 从 promoted GT 机械还原并核对签字 candidate；
2. 将 exact manifest/request 放入稳定 case-owned 路径并按签字 hash 校验；
3. 用未参与拟合的 DXF 门窗/轴网特征做原点 holdout；
4. 直接以产品 `*_px` 做一次像素判分；
5. 做“只篡改产品标定：标定分变、描图分不变”的判别实验。

理由：这一步会同时决定 C 是否真能成为裁判尺、G1 的信任根究竟包含什么，以及后续双投影/不规整清单应挂在哪个统一接口上。若先做 G2 或 ②-1，很可能再次把一个尚未签字的前提固化进多处实现。

本轮保持只读；冻结提交已核为 `e969580`，工作树无新增改动。
