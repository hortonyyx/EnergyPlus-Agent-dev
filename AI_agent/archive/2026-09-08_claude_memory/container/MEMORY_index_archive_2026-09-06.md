# MEMORY.md 索引存档 · 2026-09-06 压缩前的逐字全文

> ⛔ **本文件不自动加载**，只作存档。当前索引 = `MEMORY.md`。
> 2026-09-06 索引涨到 24573 字符、逼近读取上限（读不动 = 跨会话通道断），
> 按项目 §0.5「搬家三步」把压缩前全文逐字存此，⛔ 一字未改。
> 压缩只动**索引行的措辞**，⛔ 没有删任何条目、没有动任何条目文件。

---

# Memory index

> 一行一条，只留钩子；细节全在条目文件里。读到相关的**先打开文件再下结论**。

## ⭐⭐⭐ 治理总口径（最先读）

- [本批开发指南=权威口径，动手前先读](as-drawn-batch-guide-is-authoritative.md) — ⭐⭐⭐ 08-23 用户令「这条线上的开发都先读这份指南」；`guides/reading_correction_split_guide.md`；四刀分工（**认=模型在 reading**）· **只判答案不判过程** · ⭐⭐ **08-28 新定：两个判分器各对【一层】gt —— reading 对修正前、correction 对修正后**（「修正前」=没改答案事实之前，转换器自己的规整不算）· 配对归模型 · 墙厚归属 · ⛔ 已定死的别再问
- [设计稿描述了代码没实现的形态](design-doc-described-what-code-never-implemented.md) — ⭐⭐⭐ 08-23 同日两轮跨家族 REJECT **同一病根**：我产出的叙述比我产出的东西更合规；判据=「文档里每个数，我能不能指出它是哪份产物跑的」；有效解=**先实现后写文档** + 送审前按自己列的存疑项去核

- [梳理文档：目标态当主体，现状只作状态标记](write-docs-target-state-first-with-status-marks.md) — ⭐⭐ 08-29 用户校准「主要关注目标态，**现状本身就是施工中**」；⭐ **与上一条不冲突，两条合起来才是正解** = 目标态详写 + **每格标 ✅/🟡/❌ 且能指到 file:line**；⭐ 高潮章不是「现状差距」而是**「目标态里还悬着、要你拍板的」**；🟡 那档必须写清缺的是**接线**还是**产物**

- [跑测是为了升级 harness，不是拿分](harness-upgrade-is-the-goal-not-the-score.md) — ⭐⭐⭐ 08-21 用户战略换挡，**压过下面那条的「第一目标=恢复707」**；四步循环=最强模型先下场造 SOP→固化→降智验收；三种 reading 模式作废；⛔ harness 增量升级不特化
- [科研项目 P0=快跑通，不是产品级完备](research-first-p0-is-speed-not-completeness.md) — ⭐⭐⭐ 2026-08-18 用户拍板，**压过 CLAUDE.md §5 全部流程条款**；三档口径+唯一判断法则；⛔ 第一目标=恢复 707 水平

## 判据 / 验证方法论（最常用）

- [判据量的是【代理量】，不是要守的那件事](gate-measures-a-proxy-not-the-thing-it-guards.md) — ⭐⭐⭐ 09-04/05 **一天四条线四次返工、阻断全是同一形状**（`isinstance` 过了≠过了字节门 · 像不像活键≠能不能解析成功 · 链节点≠链能给出的值 · 类改私有≠造不出来）；⭐ 有效解只有两族=**让那条路在类型层不存在** / **出口全检⛔不是入口收窄**；⛔ 无效=加变形·加类型钉·把反例串写进黑名单；⭐ 自查话术=「我量的和我要守的，是同一个东西还是它的影子」；配套=返工单写死已知无效解 + 交件必含【自设两条同形路径】；⭐⭐⭐ **09-05 第一次【正面证明】**（此前全是从失败反推）：B2 返工 3 复核自造五类攻击，**三类把入口封印整个绕过去**（deepcopy 走 `cls.__new__` · 私有 minter 可外部调用且铸造成功 · `__class__` 重赋值不触发任何钩子），**全部由出口全检接住** ⇒ 「入口收窄不属于有效解那一族」不再是推论

- [worktree 基点必须晚于单里点名要读的文档](worktree-base-must-postdate-the-doc-you-cite.md) — ⭐⭐ 09-04 我建树用的基点早于我当天写的权威口径 ⇒ 席位读不到、把「一档」收窄成「必须是链节点」（差点焊进契约）；⭐ **救场的是跨家族审的【逐条 delta 核对】**（挖出 5 条遗漏），⛔ 不是重写；纪律=基点默认用 `HEAD`

- [GPT 席位会被 provider 安全过滤整轮拦死](gpt-seat-blocked-by-provider-security-filter.md) — ⭐⭐ 09-04 两次实测零产出（各烧 4–5 万 token）；触发=「绕过/伪造/攻击/打穿」密集出现，而内容其实是纯类型不变量复核；解=开头框定「普通软件工程复核、与安全攻防无关」+ 换词 + 清单内联进 prompt；⛔ **措辞最多改一次，第二次仍拦就改派**

- [门量得准，但【载体】被换掉了](gate-measures-right-but-carrier-gets-swapped.md) — ⭐⭐⭐ 08-23→08-30 跨家族审**连续六轮击穿、六次同一病族**，**没有一次是「门算错了」**（两头读到中间没读到 · 一个像素桥回满分 · `band_collapse` 无一假数却八门全绿 · 换轴/换图层伪装 translate · `case` 路径穿越把未签字候选种进**答案根** · ⭐ **第六轮=「公开面没有 Path」这个判断本身**：只查了 `import *` 面，Path 从**返回类型**出去了，全公开面**两行**就拷进答案根）；⇒ **立门必须三问**：①量得准不准 ②⭐**它量的那个东西能不能被换掉**（锚/坐标系/分组键/目标目录/比较字段集/**每个名词的外延** —— 全在门自己的计算之外，加严阈值碰不到）③⭐⭐⭐ **反查「哪个方向没有锁」并问为什么 —— 答案若是「加了就会红」，那是缺陷本身在挡锁**；⛔ 别用词法锁堵，有效解=**让那条路在类型层不存在**或**出口全检（不是入口收窄）**

- [转引别人的事实不免责，写进承重位置前自己量一遍](citing-someone-elses-fact-does-not-transfer-responsibility.md) — ⭐⭐⭐ 08-30 一天栽两次（把「sm24 是两栋楼」这个**叙述**当成 `exterior ring≠1` 这个**拓扑**；拿**近亲变体**的复现去驳对方结论）；⭐ 反向同样成立：复现失败≠对方错，08-30 另一例是**换探针后发现代价更重**
- [「输入确定」证明不了「推导正确」](deterministic-input-does-not-imply-correct-derivation.md) — ⭐⭐⭐ 08-29 我的论证被施工方驳回、复核方确认：**同一份确定性 DXF 上，上一版产出 33 条虚构墙**；承重理由只能是**外部可证伪 + 不含被禁机制**，且要写成**准入条件 + 测试函数名清单**，⛔ 不写散文
- [席位跑全量时连文档提交都不做](no-tree-writes-while-a-seat-runs-the-suite.md) — ⭐⭐ 08-29 同型**第三次**：纯 md 提交造出假红（`record_baseline` 把「整树 90 秒不许变」写进了前提）

- [影子模块替换必须同时改父包属性](shadow-module-swap-must-touch-parent-attr.md) — ⭐⭐ 08-29 变异矩阵撞上：`from X import Y` 走**父包属性**不走 sys.modules ⇒ monkeypatch 打错对象、seam 测试集体 DID NOT RAISE 假红；配套=变异方向本身要实测（粗化无牙/细化恒等，有牙方向=回到历史缺陷形状）

- [把答案当【输入】喂给下游，单测代码自己](feed-the-answer-in-to-test-the-code-alone.md) — ⭐⭐⭐ 08-25 用户提「捏份答案从 correction 之后走，反正不计入跑测」；**真实产物没行使的能力 = 缺陷躺着的地方**（sm25 现有产物 38 个房间 `polygon` 全 null ⇒ 多边形路径落地一个月没走过）；一喂答案撞出两条；⛔ 产物永不作成绩 · ⛔ 不伪造信任根（骨架取答案、证据引用取真产物）
- [把返工题从【修这个例子】提到【枚举这一类】](enumerate-the-class-not-the-example-found-six-more.md) — ⭐⭐⭐ 09-06 实证：跨家族审**按症状**只找到 1 个洞，返工单改写成「`submit()` 每项检查 `consume()` 各自重做了没有？逐项列表」⇒ 施工方交回 17 项表、**另外 6 项**从未重做，新增 17 条测试**零既有测试被改**；⭐ **那张对照表本身就是交付物**，且必须允许「结构上不必」一档但**每条写清「被绕过后坏数据流到哪、谁接住」**；⚠️ **表的外延是施工方自己划的** ⇒ 复核单第一优先必须是「这张表是不是全部」+ **两套互不依赖口径独立枚举**
- [返工审必须加第三条：换同形输入仍走不通](rework-review-needs-the-same-shape-input.md) — ⭐⭐⭐ 08-27 实测：「旧 commit 复现得出 + 新 commit 复现不出」**两条全绿**，而唯一新加的第三条**一次抓出全部 3 条阻断**（只修半句 · 修法挪了位置 · 前提本身不成立）；⛔ ①② 只验证「这个例子修好了」，③ 才验证「这类缺陷修好了」；配套=上一轮返工要求要**逐字贴原文**、别人没交成件的探针当**线索非证据**交下去
- [锁只在【夹具有存货】的方向上有牙](gate-teeth-direction-follows-fixture-inventory.md) — ⭐⭐⭐ **08-29 实质推进：存货不是给定的，它是【检查形态】的函数** —— 我与复核方**同时**把一条门判成「潜伏」（理由：没有成对的对照物），实测是**今天就有 8 个满存货**；换成「让被测对象自己提供尺子」后主力 case 存货 **0→10** ⇒ ⛔ **别问「有没有对照物」，要问「它声称覆盖的每种量各自有没有被量到」**；⭐⭐⭐ 08-27 GLM 主发现、我已复现：6 把锁被「以向后兼容为名加回旧搜索根」**全绿骗过**（17 passed），实害真的（信任根静默挂回可清理目录）；根因=主锁夹具选了 sm24 而 **sm24 在病灶方向下 0 份存货、sm25 有 4 份** ⇒ **病灶方向恰是它唯一没牙的方向**；配套=**None-断言分不清「拒绝」与「没去找」**；该锁结构性质（搜索根面）不是字面（glob 名）
- [跨表示比同一个变异，必须两边等价且探针自证](cross-representation-mutation-must-be-equivalent.md) — ⭐⭐⭐ 08-27 实犯两次：字段**叫** `pos_m` 却装着像素 ⇒ 扰动打错通道；世界 y 与像素行**反向**、端点配对按下标直配 ⇒ 残差 **7.29 m**，据此差点发出「像素空间丢了免费的正确性」这个**自己造的**重大发现；解=穷举配对方向+残差硬上限+每行自证变异生效+未扰动两表示必须同答案
- [离线夹具测「新门有没有分辨力」](offline-fixtures-test-gate-discriminating-power.md) — ⭐⭐⭐ 08-21 落地 5好+9坏；判据=好的全绿+坏的至少红一条；**第一个被拦下的是我自己写的门**；此前「改脚手架伤没伤 reading」只能花钱跑抽

- [自洽门的锚若由产物自选，表示法塌缩全绿](self-consistent-gates-anchor-on-product-chosen-apertures.md) — ⭐⭐⭐ 08-24 五审：重算只验证「没算错自己的谎」；关门=镜像生产者分组定义数墨列组（诚实全1/塌缩全2、零阈值）；平行墙门洞米数重叠会偷命名
- [重算式判据必须复刻生产者的定义](recompute-gate-must-mirror-producer-definition.md) — ⭐⭐⭐ 08-24 我按「中心±半宽」重算产物自报的边界，偷设了「质心=中点」；诚实 sm24 偏 1.480 px 而门是 1.5 px，**差一点判红一份对的产物**；照生产者的仿射映射逐边重算后偏差 0.004 px
- [改了上游规则，之前那次扫描就作废](upstream-change-voids-the-earlier-sweep.md) — ⭐⭐⭐ 08-24 我扫完 `merge_m` 说「不承重」，随后改了上游的门垛判定却没重扫；跨家族审一扫就翻，**而且那个值下的合并跨过了答案自己的一扇 0.6 m 窗**；⭐ 正解是让参数不再承重（加「不许跨洞口合并」），不是把它调好
- [送审后到裁决前不许动被审对象](dont-touch-the-tree-while-a-review-runs.md) — ⭐⭐ 08-24 我在 GLM 审阅期间继续改树（9 文件 6000+ 行），它只好自己导出冻结副本再审；送审要写明 commit，然后去做不碰它的事
- [把阈值调硬 ≠ 让判据重算](threshold-hardening-is-not-recomputation.md) — ⭐⭐⭐ 08-24 三审：我把「门窗墨>0」改成「占空档长度10%」以为堵住了，**那个占比仍是产物自己报的** ⇒ 真丢 1.2 m 墙 + 谎报门窗墨 = **gt 回到诚实产物的 94.6、六门全绿**；阈值防噪声、重算防伪造
- [两把尺子：对答案的 vs 对原图的](two-rulers-answer-side-and-source-side.md) — ⭐⭐⭐ 08-24 实测「谎称画满全图」在 gt 侧 93.3→**97.3 高于诚实产物**、在原图对账上 49 条违规；⭐ **多画在对答案的尺子上通常是加分的**
- [「覆盖不到」不等于「是个洞」，先读声明范围](coverage-gap-is-not-a-defect-until-scope-is-read.md) — ⭐⭐⭐ 09-03 用户当场驳回：我把「出网闸只装在 pytest、`python -c` 不在场」升级成缺陷还提议清查付费钥匙，而那道闸的范围**就写在任务书文件名里**（`..._in_suite`）· 缺陷判断要**两个**输入①覆盖不到②本该覆盖，⛔ 我把②默认掉了而它是**沉默的** · 自查话术=「**这件事本来就该被它管吗、谁在什么时候说过**」
- [拿代理量当成了它代表的东西](proxy-mistaken-for-the-thing.md) — ⭐⭐⭐ **09-01 一天栽三次、三种形态**（#57 条数当环成立 · #59 `valid`+面积当环对 · #62 拿**两个不同基准**的多边形比对称差）⇒ **自查话术定为三句**：①这个数达标了那件事就一定成立吗 ②这个数是**对着谁**达标的 ③⭐**我拿来比的这两个东西本来就该一样吗**；⭐ 正解=**能做到零阈值就别设阈值**（按答案基准投影后 25 个腔恰好 0.000000）；⚠️ **挑着读一份输出的子集 = 自己造了一个代理量**（`vertices=8` 旁边就印着 `source_symdiff=0`）· ⭐⭐⭐ **代理量进【验收项】比进测量更贵** —— 「产出 boundary edges」是**条数**、消费者要的是**有效多边形** ⇒ 88/91 条边全达标而**环自交**；自查话术=「**这个数达标了，那件事就一定成立吗**」· 08-18 一天犯 10 次；问「我量的是它本身还是影子」；解法=完整快照而非我挑的子集
- [复现要的是【形式】不是【某一次】+ 用完整 worktree](reproduce-the-form-not-the-run.md) — ⭐⭐⭐ 用户 08-18 三次纠正；07-02 Sonnet 无工具箱=来源不是实例；翻历史先读当时的实验 README

- [`EP 0 Severe` ≠ 物理输入对](ep-zero-severe-is-not-physical-correctness.md) — ⭐⭐⭐ 全链零门管 MEP 数值合理性；问「谁在管数值合不合理」
- [判缺陷多严重，先查产物的真实消费者怎么读它](artifact-severity-depends-on-real-consumer.md) — ⭐⭐⭐ 格式长相≠契约；按位置读还是按含义读
- [漏一格导致整行位移，而全仓零字段对齐校验](whole-stage-redraw-cannot-fix-systematic-field-confusion.md) — ⭐⭐⭐ 门报症状还是病因；修法=让它填不错
- [下「某方报的数不对」前先重复跑](repeat-the-run-before-accusing-a-seat.md) — ⭐⭐⭐ 08-20 我拿一次红就确认了对同事席位的虚报指控；同树 6 次 1 绿 5 红 ⇒ 三方全真无人说谎；**一次跑出来的红同样不是证据**；90 秒 vs 冤枉一个席位
- [「一口气不出错」验收口径一天内打掉四个已写好的结论](one-shot-acceptance-bar-kills-false-claims.md) — ⭐⭐⭐ 拼接出来的「跑通」是假的；须连跑≥3次
- [「否则就是 X」背后藏着一个没人签字的阈值](silent-default-threshold-behind-otherwise-conclusions.md) — ⭐⭐⭐ 08-20 「不接触就一定是两樘」= 把界限偷设成 0；问「这句话等价于把哪个数设成几、谁签的字」；它是领域参数不是容差
- [输入形态无上界 ⇒ 声明化 + 消费对账门](declare-the-dialect-plus-consumption-ledger.md) — ⭐⭐⭐ 08-20 F-65；加分支穷举不完、启发式错得静悄悄；⭐ 对账门才是拓展性的兑现（没声明过的形态从静默漏变成点名红）；旧输入走纯翻译层、执行仍只一条路
- [词法匹配判无界输入的防线永远补不完](lexical-guard-cannot-be-completed.md) — ⭐⭐⭐ 08-18 同一条缝六次现形；⛔ 不是护栏太多、是这一个护栏类型选错；边界要搬到进程/文件系统层
- [换地基先普查基座，别一个一个撞](sweep-the-substrate-dont-hit-defects-one-at-a-time.md) — ⭐⭐⭐ 用户 08-16 拍板；三缺陷串行遮挡、每层烧一次跑测；缺的是一次普查+一层锁，不是更多实验
- [VLM 的像素帧 ≠ 文件的像素帧（差 1.544×）](vlm-pixel-frame-differs-from-file-pixel-frame.md) — ⭐⭐⭐ 标定自洽却整体错 54%·跨轴门放行·crop 落空成「诚实的假阴性」；多点同比例偏差=坐标系问题
- [时对时错先问「尺子看得见这个量吗」](instrument-blind-to-the-asked-quantity.md) — ⭐⭐⭐ 08-22 F-69 真因：唯一掩膜对门窗**颜色图层**灵敏度=0（青色像素数实测 0），而它照样返回漂亮的 `window_rect` 候选 ⇒ 读图器不是在选极性、是在猜；**sm21/sm24 也有该图层 ⇒ 全项目历史 reading 都对它是瞎的**；修法=加观测手段不加纪律，降级必须显式
- [判「模型不肯做 X」前先确认做 X 的路是通的](verify-the-path-works-before-blaming-the-model.md) — ⭐⭐⭐ 工具坏掉与模型不用它在产物上一模一样，只有过程日志分得开；**08-18 F-60 第二次现形，我差点把冤枉话发出去**
- [数字进承重位置前必须【量】不能【推】](verify-the-number-before-writing-it-into-a-load-bearing-place.md) — ⭐⭐ 09-06 连续两次把估算当读数写进提交信息（写 498/499，实测 503/502）；⚠️ 病灶是「压缩了就应该变短」这类**看起来必然成立**的推断 —— 那两次替换块恰好与原块**等长**、净减 0；⭐ 纪律=**改→量→写**三步不许换序，行数压缩要**先打印「净减」再落盘**；自查话术=「这个数是我量出来的还是推出来的」
- [自述总比产物更合规 ⇒ 验收只能读文件](self-report-more-compliant-than-artifact.md) — ⭐⭐⭐ 自检检的是意图不是文件；「pilot 门 vs 自检」的第一份直接证据；硬要求诱发伪造、出口才是解
- [作废半径要就事论事，株连整组=产物与「全错」不可区分](invalidation-blast-radius-must-be-scoped.md) — ⭐⭐⭐ 08-21 一个角部歧义洞口作废整份判卷（实际是外轮廓 94.4%/窗 8/15）；⭐ **分母是参照侧派生的，产品侧的不确定性无权删参照目标**；判据给极端结果时先问「是被测对象差，还是这把尺子没量」
- [对 diff 输出 `grep -n` 拿到的不是文件行号](line-numbers-from-diff-output-are-not-file-lines.md) — ⭐⭐ 08-28 复核单里四个行号**全错**（写 95/115/117/118、实际 394/414/415/417）；`git show` 输出前面有 header+提交说明+hunk 头且只含改动行，**与文件行号无固定偏移**；⭐ 引用位置一律回文件 `grep -n "<锚点>"`
- [`grep` 零结果 = 「存在但没人用」还是「根本没这名字」](grep-zero-hits-conflates-unused-with-nonexistent.md) — ⭐⭐⭐ 08-22 我把 docstring 里的中文描述当函数名，grep 零结果读成「全仓零调用者」，当实测事实发进三份文档；**本轮唯一工具拦不住的错**（不是量错，是把读到的东西记成了另一个东西）；引用标识符前先查它的**定义**
- [半量半填的标定，错会伪装成下游筛选的缝](half-measured-calibration-hides-as-downstream-gap.md) — ⭐⭐⭐ 08-23 尺度靠链拟合、原点靠手填；我细看过的两张准到 0.31 px，**没细看的那张偏 1.73 px** 直接顶穿容差；我把它判成「候选筛选有缝」且把 `axis=row` 的 `pos_m` 当成了 x；⭐ 判别实验要挑**没人盯过的输入**；配套=刚变全绿的判据须当场证明还能变红，且变异方向要对
- [观测量的「缺席」会把多种原因压成同一个空白](absence-conflates-causes-in-observables.md) — ⭐⭐⭐ 缺席不是信号除非显式变成信号
- [`grep … || echo 通过`：文件不存在也算通过](absent-file-read-as-passing-check.md) — ⭐⭐ 08-19 我把「文件没了」读成「检查通过」；验内容前先断言存在
- [只有负向断言的门 = 恒红结构上不可观测](gate-with-only-negative-assertions-is-unobservable.md) — ⭐⭐⭐ 问「不加这处改动，这门本来红不红」
- [多个「不相干」的错常同源于一个有损的表示步骤](representation-collapse-manufactures-unrelated-errors.md) — ⭐⭐⭐ **09-01 最硬证据**：F-153 判过「这是**两个**病别当一个修」，换一个表示步骤后**两个一起好了**（含那个 0.1 mm 错位的）⇒ 原结论**只在旧表示下成立**；⭐ 附带 **`interval_misses=0` ⇒ 答案本来就在上游，是推导把它扔了** ⇒ 换表示前先量这一下 · 08-23 走廊幻墙+凹口漏段+画穿多段三错同源；我连错两次诊断才找到；**换表示 > 加容差 > 加分支**
- [把观测量命名成事实性名字，它就以事实身份往下游走](observation-named-as-fact-travels-as-fact.md) — ⭐⭐ 08-23 F-78 被自己推翻：「不存在的墙厚 0.131」实为 **0.49 像素**噪声；叫 `thickness` 就成了图纸属性，叫 `spacing` 就是观测量
- [换表示会让「免费的正确性」静默蒸发](free-correctness-evaporates-when-representation-changes.md) — ⭐⭐⭐ 加规范化问「谁在拿变换前的形态跟它比」；问到【实现】粒度
- [neuter 必须覆盖接线不只机制 + 判接线只能行为验证](neuter-must-cover-wiring-not-just-mechanism.md) — ⭐⭐⭐ 形状匹配必漏；orchestrator 独立 neuter 必须换方向
- [立规则不给合法出口 ⇒ 模型自己发明出口](rule-without-legal-exit-breeds-invention.md) — ⭐⭐⭐ 问「不调这工具门还在吗」「拆开分次喂门还成立吗」
- [排查回归先读 diff 再设实验；参照系=多份成功的交集](read-the-diff-before-guessing-variables.md) — ⭐⭐⭐ 七轮实验没查出的东西 diff 只有 400 行；单点 diff 只出候选
- [换判据=搬测量点；旧判据覆盖的每种形态都要重问一遍](moving-a-gate-to-a-new-measurement-point.md) — ⭐⭐⭐ 载体≠机制；「写出来的路径」vs「取出来的路径」；我搬了两次才对
- [撤一道限制前先确保放行面有记录](removing-a-restriction-needs-the-allow-side-logged-first.md) — ⭐⭐⭐ 门紧时证据全来自 deny；门一松，能带出信息的那面恰好不记录
- [判据前面若有缓存，缓存就是第二个入口](cache-in-front-of-a-gate-is-a-second-entrance.md) — ⭐⭐ 问「我验的是这道门，还是绕过它的那条路」
- [哈希整份报告的 digest 不能当子事实的相等判据](hash-of-whole-report-is-not-an-equality-test-for-its-parts.md) — ⭐⭐ 判几何必须比顶点
- [版本号证明不了「产生它的代码修没修过」](version-number-is-not-behavior-attestation.md) — ⭐⭐⭐ 同一版本号必然横跨修复前后
- [回归用例必须自证前提](regression-case-must-prove-its-own-premise.md) — ⭐⭐ 先断言旧判据在此夹具确实会失败
- [锁必须走真实入口 + 恒等锁≠正确性锁](lock-must-exercise-real-entry-point.md) — ⭐⭐ 摘得动才算数
- [neuter/分辨力实测证明的范围比你想的窄](neuter-proves-wiring-not-discriminating-power.md) — ⭐⭐ 变红≠有分辨力
- [摸排：暴露面−门 的机械判据会假绿](interface-sweep-gate-vs-range-check.md) — ⭐⭐ 范围校验≠语义门；暴露面比 schema 窄本身就是防线
- [对称载荷证明不了方向 +「镜像一致≠无害」](symmetric-evidence-cannot-prove-direction.md) — ⭐⭐ 判无害须逐属性含宿主字段
- [两种潜伏：没尺子量 vs 没跑到那一段](two-kinds-of-latency-no-ruler-vs-never-reached.md) — ⭐⭐⭐ 新门第一次报红先问「门什么时候接上的」
- [「未声明的参数」可能承载真实语义](undeclared-parameter-may-carry-real-semantics.md) — ⭐⭐⭐ 09-02 复核方**撤回它自己上一轮的处方**：删掉探针里那个「我的半厚」缓冲，真实数据上**砍掉 40 条必需延伸**（13→5 / 15→8），而出界深度**全是半厚整倍数** ⇒ 它承载的是**端头搭接**语义；⇒ 清理魔数前必须量「删掉后塌了什么」，承载语义就**显式化为前提**⛔ 不是删掉
- [删「多余」规范化前先找它服务的对外契约](dont-delete-normalization-without-finding-its-contract.md) — ⭐⭐⭐ 首选证据=引入它那次的提交说明
- [同一条缝六次现形：模型看得见但不该它管](model-visible-but-not-its-business.md) — ⭐⭐⭐ 有效修法只有「让它看不见」；prompt 不是防线
- [真链路跑一次撞出 8 条工程缺陷](real-chain-run-exposes-what-tests-cannot.md) — ⭐⭐ 问「换台机器/换份真产物还成立吗」
- [用历史跑通产物绕开卡点、先撞后段](probe-past-the-blocker-to-find-hidden-walls.md) — ⭐⭐⭐ 串行修墙会让后段缺陷无限期潜伏
- [播种绕开已知 blocker ⇒ 撞出下游第二处](seed-bypass-exposes-hidden-downstream-blocker.md) — ⭐⭐ 「卡在 X」≠「X 之后没问题」
- [被截断的工具调用只存在于 provider 的账上](truncated-tool-call-desyncs-provider-ledger.md) — ⭐⭐⭐ 问「错误消息指名的那件事，我核过它真坏了吗」

## 协作 / 派工 / 审阅

- [写「新」文档前先 ls 一眼同目录](list-the-directory-before-writing-a-new-doc.md) — ⭐⭐ 08-25 用户问「上轮不是写过一份讨论吗」——写过；**代价不是重复劳动是质量倒退**：旧稿已写对的两个字段被我重写时漏掉，跨家族第一条就抓住；默认累计式改写那一份，并存必须互加指针
- [「谁写谁不批」防的是作者对自己推理的系统性盲区](whoever-writes-cannot-review-blind-spot.md) — ⭐⭐⭐ 机械测量作者可做／判断类必须换人；施工席自述一律以 git diff 为准
- [拆成两份请求书送审 ⇒ 两份范围的并集要显式对账](review-scope-complement-must-be-reconciled.md) — ⭐⭐⭐ 缝里那半没人审，而每份自己看都完整；排除条款只证明我想到了 X
- [跨家族出设计稿=不继承派工单的错误前提](cross-family-design-draft-catches-own-family-blindspot.md) — ⭐⭐⭐ 派工单里的分类句要当【可能错的前提】写并邀请证伪
- [派工单的【选项清单】本身就是个没签字的前提](dispatch-options-list-is-itself-a-hidden-premise.md) — ⭐⭐ 08-25 GLM 指出（**第 25 次，累计 25/25**）：写「两条都有坑、不预设答案」仍预设了「只有这两条」，而第三条严格更优；停报触发器要覆盖**都次优但有更优解**，否则把施工方逼进「停报浪费一轮 vs 自行扩路」
- [「停下上报」至今无一例外都是派工方的题错](stop-and-report-catches-dispatcher-errors.md) — ⭐⭐ **09-01 第二程 #69（69/69）+ 单子被抓 7 条 B 层、其中三条同形 =「改了一处，没扫这处改动的外延」**（改派席位没扫正文的「你」· §一改判据而 §五漏改 · 引「派工单说…」引的是**执行档转述**）⇒ ⭐⭐⭐ **发单前最后一步：对本轮改过的每个名词/字段/收件人，`grep` 一遍它在本单里的全部出现处**；同程另一条 = **我给输出贴了标签而不是断言它**（`git status` 打印了 ` M file`，我的 echo 无条件说「(空)」）· ⭐⭐⭐ **09-01 一天四次（#55–#58，累计 58/58），停报 3 次各省下一整轮返工**；⭐⭐ **两条新纪律**：①验收表与设计稿点名的**每个通道机械对账**（治 #55）②判据写成**规则**不写成**现状名单**（治 #58）· 08-31 一天三次（#52/#53/#54）证明【三格对撞全拦不住】这一类**（不是矛盾，是对**外部事实**判断错）⇒ 三格之外再加**三句查证**：①原料树上真存在吗（`ls`，别靠记忆）②**机制**在设计稿里指派给谁了（⛔ 别拿「语义规则写在哪节」代替）③⭐⭐⭐ **本单口径与上一单刚定的口径推到底会不会打架**；⭐⭐ **#54 最贵**：把**派生值**存进被哈希覆盖的产物 ⇒ **改算法也要重做基线**（⛔ 不只是「加字段」），我对用户讲窄了；⭐ **救场的是合法出口不是对撞** · **08-30 对撞清单补成【三格】**（第 51 次 ⑯：加字段 ⇒ 落库 `content_sha256` 变 ⇒ 台账失配 ⇒ 11 条既有锁红；⭐ **做了原来那两格对撞仍然没拦下**，因为它是**单外矛盾** —— 第三格 = **已落库/已签字产物的既有承诺**；⭐⭐ 附带：**停报常常是一条没人走过的线索的入口**，这次顺着它撞出了 F-153 的真根因）· **08-29 唯一一条【可机械执行】的自查**：写完派工单把**验收项**逐条与 ①**本单禁令** ②**本单任务项** 对撞（当天 ⑬「验收要求哈希不变而任务项加了必填字段」/ ⑭「验收要求做一件本单自己禁止的事」**各只需一次对撞就能拦下**；⑮「把两种机制的缺口混算成一个数」拦不住 ⇒ 那类要么派工前自己先量一次、要么把验收写成「**差异必须逐条有出处**」而不是写死一个目标数）；⭐⭐ **08-27 触发器本身要【分层】**（承重前提错才停 · 外围数值错只记不停）：一处「3 份还是 4 份 md」把整轮实体复核挡在门外、空转两轮，**而这条 08-12 就写进条目却没执行**；⭐ 另两条：「工作树干净」写下时是真的、是我**自己后续拷文件进去**才变假 ⇒ 描述环境现状的话要在**最后一个准备动作之后**重核；计数一律贴 `--numstat` 原文，别用中文数词
- [施工审恒升一档](construction-review-one-tier-up.md) — 执行审=次高档交叉；主控大节点=轻门
- [GPT-6 Astra 可以接【整块】施工](gpt6-astra-takes-large-blocks.md) — ⭐⭐⭐ 09-05 用户令「能力较强且**不会过度设计**，相对大块的工作可以一气交给它落地」；⇒ **改的是派工形状**：⛔ 别再切成三四个小单（切小的动机对它不成立，而接缝的代价一直在）；⛔ 大块 ≠ 放松验收，块越大**停报分层越要写清**；⚠️ 现实约束是**额度与 provider 容量**（大块撞上=一次丢一整条线）⇒ **派前探针实测 + 单里写死分段提交**；⭐⭐⭐ **09-05 正面证明**：astra 在一个 A-6 大块里**三次**撞 `Selected model is at capacity` 退出，**三次都发生在活干完之后**（实现+契约+证据 / 全量+README / 执行档248行且已 git add），每次只丢 `git commit` 那一个动作 ⇒ **一行代码没丢**；⭐ 容量≠额度，探针当场 `PROBE_OK` 就能续，配套见 [[codex-resume-resets-reasoning-effort]]
- [多模型家族协作规约](codex-execution-protocol.md) — 四家族角色矩阵；禁裸调用；MCP 必须 danger-full-access
- [GLM 接入⇒四模型家族](glm-family-onboarding.md) — GLM=执行档主力；验证性审阅 Fable 级/探索性不及格；**08-16 席位默认升 5.3 + DeepSeek 加席位（按量、与管线共用余额）**；headless 需 `--allowedTools`
- [Fable 经额度恢复可点射](opus-controller-fable-spot.md) — 只做规划/审；主控整场不切模型
- [用户拍板必须白话](user-ratification-plain-language.md) — 禁用代号当主语，四段讲
- [用中文沟通](communicate-in-chinese.md) — 无特殊要求时统一中文
- [跑前必确认配置](pre-run-config-confirmation.md) — 动手前停下问用户拍配置
- [细稿必须累计式自包含](spec-must-be-cumulative.md) — 禁「vN 不变」引用已覆写正文
- [Comate 网关=人工中继通道](comate-gateway-relay-channel.md) — 只走人工中继；沙箱 DNS 测试全假阳性
- [codex MCP 30min 超时根因 + CLI 通道已通](codex-mcp-idle-timeout-and-cli-channel.md) — 中止的只是等待；监控只跑只读命令；**⛔ 08-16：审隔离壳的活被 GPT provider 过滤拦死 6 次，改派 GLM，措辞最多改一次**
- [术语规范：orchestrator / 子环节-agent](agent-terminology-convention.md) — 三词指代不一造成排查分类错误

## 环境 / 工程操作（踩过的坑）

- [「全仓绿」是【树+启动器+这段时间】的属性](green-suite-is-a-property-of-tree-and-launcher.md) — ⭐⭐⭐ 权威全量只在主树；⭐⭐⭐ **09-01 第五种，且它改写了第四种的归因：没有任何席位跑过安装** —— `.mcp.json` 用 `uv run` 起 MCP server + 全局 `UV_PROJECT_ENVIRONMENT` ⇒ **claude 家族席位以 worktree 为工作目录【启动】就改掉共享 editable 安装**（codex 席位不触发）；我第一判定「席位违纪」被它自己的会话记录证伪 ⇒ ⭐⭐⭐ **`.pth` 哨兵是代理量，承重不变量是 `m.__file__` 落在自己工作目录里**（cwd 胜过 `.pth`）；席位禁跑 editable 安装；**08-22 第三种假红：全量跑着时我自己又跑了写仓库的判分命令**；⭐⭐⭐ **08-27 第四种：跑测【途中】启动器被第三方改掉** —— 共享 venv 的 editable `.pth` 被某席位改指到 `/tmp/ep_f97`，`mtime` 正好落在主树权威全量窗口内 ⇒ 合并门读数作废重跑；⇒ **派工单固定禁 `pip install -e .`** + **权威全量必须带 `.pth` 前后哨兵**；⛔ 全量在跑时不许动树
- [派子 agent 用内置 worktree 隔离，可能建在几百个提交之前](agent-worktree-isolation-may-branch-from-stale-base.md) — ⭐⭐ 08-25 实测落后 **560 个提交**（连 CLAUDE.md 都是旧编号、没有 gt 铁律）；⭐ 解=**主控自建 worktree + 提示里写死工作目录 + 要它开工先自检关键文件**；配套坑=editable `.pth` 硬编码主树 ⇒ 非主树里裸跑会**静默串台**
- [被 ignore 的已跟踪文件 `git add` 静默失败](gitignored-tracked-file-add-fails-silently.md) — ⛔⛔ 验收禁用「status 干净」，必须 `git show HEAD:<path>`
- [收工 `git add -A` 会扫走并行席位的半成品](wrapup-commit-sweeps-other-seats-wip.md) — ⛔ 提交前完整通读 status，禁 head 截断；⭐⭐ **08-29 第三次同型：席位【还在飞】时扫走了它写了一半的 129 行** ⇒ **有席位在飞就禁 `git add -A`，只 add 明确路径 + commit 前必看 `--cached --numstat`**
- [退出码文件跨两次跑复用⇒陈旧的 0 被当本轮结果](exit-code-file-must-not-be-reused-across-runs.md) — ⛔ 判跑完看汇总行；别用 nohup
- [headless 席位「日志空白」≠ 它死了](headless-seat-silence-is-not-death.md) — ⭐⭐ 08-28 一次踩三个：`-p` 只在结束时输出 ⇒ 我砍了正在干活的会话；grep **脚本名**没找到又重启 ⇒ **两个 GLM 跑同一份题**；⭐ 认家族只能按 `/proc/<pid>/environ` 的 `ANTHROPIC_BASE_URL`（进程名全叫 `claude`）；正解=工具自带 `run_in_background`。⭐⭐ **08-30 补两条**：① `pgrep -f '<命令串>'` **会匹配到我自己那条命令**，把死席位读成活着 ⇒ 认进程只用**可执行名**或 environ；② **席位撞额度上限会留下污染主线的孤儿半成品**（未提交/未跑测/未过审，日志里一字不提）⇒ **收到席位失败通知第一件事是 `git status`**，然后三步：移出 `src/` 存进 `logs/experiments/` · README 写死「**线索非证据**」· 主控点名可疑处但**不代判**；派下去要写明「**重新实现**，复用任何一段须自己重新论证+补锁」
- [codex 的 reasoning effort 默认值靠不住（resume 会降、⭐ 全新启动也会）](codex-resume-resets-reasoning-effort.md) — ⭐⭐ 09-05 resume 实测：原会话 `xhigh`、起来 `low`，**只在横幅印一行、不报错**；⛔ 选项必须放在 `resume` 之前 · ⭐⭐⭐ **09-06 扩写：不止 resume** —— 同一个 `seat_gpt.sh`、**全新**起 `gpt-6-astra` 横幅是 `low`，而历史 gpt-5.x 席位日志**全是 `high`** ⇒ **默认值是【按模型】的**，⛔ 不是启动器坏也不是 resume 专属；⭐ 判别签名=**同脚本历史日志 vs 本次横幅不同**（只看本次会误判「一直如此」）；⭐ **要一个档 ≠ 拿到那个档 ⇒ 起完必须回读横幅比对**（已写进 `seat_gpt.sh`，asked≠got 响亮报错）
- [跑测节奏三档](test-run-cadence-policy.md) — 主控轻门独立全量=唯一权威门；轻门不加 `-m`
- [跑测每个环节的产物必须出全](stage-artifact-set-must-be-complete.md) — ⭐⭐ 规矩 07-03 就写过、是没执行；`judge: off` 会关掉产 grade 的那条路
- [产物落仓库别放 tmp](artifacts-into-repo-not-tmp.md) — 用户编辑器看不到、易失
- [根目录不许乱落文件](no-stray-files-in-repo-root.md) — 过程痕迹一律 `AI_agent/logs/`
- [logs 重排为纯过程痕迹](logs-reorg-process-only.md) — `reviews/{request,verdict,execution}` + `experiments/`
- [管理文档体量纪律：翻篇的日更收工时当场搬](management-docs-size-discipline.md) — ⭐⭐ 08-18 用户令；CLAUDE.md >400 / plan.md >900 即搬 `logs/worklog/`；读不动 = 跨会话通道坏了
- [只有 run_config.yaml 声明的才配被冻结](freeze-only-what-has-external-trust-root.md) — ⛔ 别用「塞进哈希」回答篡改问题
- [run 溯源记录要求](run-provenance-recording-requirement.md) — 每 run 详记模型配置 + 脚手架状态

## reading 主线

- [⛔质量杠杆：行为清单 #2#3 已改完+F-51 单帧化，08-17 只欠开抽](reading-quality-lever-is-crop-budget-not-review-ring.md) — ⭐⭐⭐ 配置已拍：haiku-4-5 + 先 1 抽探路；**跑 sm24 前必须先解 v3 对 null `scale_origin` 的 retain_as_miss**；⛔ 模型漂移说从根上不成立（三模型两家族都做到过）
- [⛔别再问「谁当审阅者」：07-07 模式已被接受](707-mode-accepted-reading-agent-deferred.md) — ⭐⭐⭐ reading-agent/合规 lane 已打包归 reading 专项；§1.5#7 是长期目标不是本批准入门
- [基准不可审计时别把它的分数当靶子](baseline-unauditable-dont-chase-its-number.md) — ⭐⭐⭐ 07-07 的 9/9 既不能证干净也不能证泄漏；产物自身无推导链；sm24 无 gt 时也出过好 reading ⇒ 泄漏说排除
- [reading 杠杆=模式不是纠偏 ⇒ 接口层强制测量](reading-lever-is-measurement-enforcement.md) — ⭐⭐⭐ 主修法=读图器只写像素锚点+引用标注，代码唯一换算
- [一把尺子回放：老产物真的全对](one-ruler-replay-old-artifact-perfect.md) — ⭐⭐ 07-07 老件内墙 100%/多画 0m vs Sonnet 92.1%/6.77m
- [本批 reading 目标=controlled lane 非 autonomous](reading-batch-target-controlled-lane.md) — ⭐⭐ 不是提分，是用合规形态重新达到一次
- [先保质量·从高档模型往下降档](quality-first-descend-from-strong-model.md) — 实证减卷有害（92.1% vs 70.9%）
- [不变量 #7：环节控制边界 + 成绩归因](controller-must-stay-out-of-product.md) — ⛔ 禁端到端主控伸手与成绩记错人
- [reading 监督污染 → 08-01 病灶定位](reading-supervision-contamination.md) — ⚠️ 多处已被推翻，先读上面两条；任何识图成绩至少两抽
- [reading CV 工具箱方法论](reading-cv-toolkit-methodology.md) — ⛔ 核心主张已降级；「给了工具就会去量」是错的隐含假设
- [Haiku 降级=模型是杠杆](haiku-downgrade-model-is-lever.md) — 07-07 改写：杠杆是「量而非看」
- [review 环效果不迁移 +「停下等审」是会话形态属性](reading-intervention-does-not-transfer.md) — ⭐⭐ 硬纪律诱发伪造，立规则须给合法退出口
- [污染硬隔离已落地](contamination-hard-isolation-requirement.md) — 一律走 `spawn_isolated_reader.py`
- [reading 脚手架补全口径](reading-scaffold-restore-policy.md) — 先补全后精简
- [reading 演进 + Phase A](reading-evolution-and-phase-a.md) — 病根=prose↔gate 落差；剩 Phase B
- [识图质量诊断 2026-06-24](reading-quality-investigation-2026-06-24.md) — prompt 强度不是杠杆；judge 归因未验证不得成修法依据
- [sm24 端到端首次尝试 ⛔卡在识图判卷门](sm24-e2e-blocked-reading-judge.md) — 硬隔离脚手架把识图打崩 8/8→1/8

## 判卷 / gt

- [judge 以 gt 为权威·看图仅辅助](judge-gt-authoritative-images-auxiliary.md) — 唯一标准=坐标 vs gt 逐元素对账
- [判卷身份+度量+仲裁批 ✅CLOSED](judge-identity-and-metric-design.md) — 共同病根=边界留给施工方猜；放水比冤枉危险
- [规范跑测流程 + judge 架构](standardize-test-flow-and-judge-arch.md) — 单一 `flow` 编排；三层叠加；禁手搓判卷
- [Per-stage validation + judge architecture](per-stage-validation-judge-architecture.md) — 每段①确定性+②judge；judge 不给流程信息
- [Reading-honest + judge routing architecture](reading-honest-judge-routing-architecture.md) — correction 永 image-blind；看图仲裁归 judge
- [gt 标准产物清单](gt-standard-artifact-checklist.md) — 缺件即红
- [天正→GT v3 转换器立项](tarch-gtv3-converter.md) — ✅ sm24 收官；立面处理批未施工
- [CAD→gt direction](cad-to-gt-direction.md) — 天正 DXF 自动生成满配 gt

## 架构 / 项目状态

- [考虑可升级性 ≠ 现在就要泛化](extensibility-is-not-generalization-now.md) — ⭐⭐⭐ 09-02 用户校准，**给不变量 #6 定分寸**；判别法则=「以后松动它时**是改一处还是翻遍全仓**」；只有【尺寸不写死 + 假设局部化】现在做，⛔ 非正交的拒绝路径/泛化分支**现在不做**（今天根本没有非正交输入=空防御）
- [建筑复杂度可扩展性铁律](building-complexity-extensibility-principle.md) — ⭐ 禁烤死「共底面盒子」假设（不变量 #6）
- [Pipeline 0–5 refactor status](pipeline-0-5-refactor-status.md) — 引用老路径前先核位置
- [尺寸基准+墙厚方向定案](wall-thickness-dimension-basis-direction.md) — `zone_frame: axis|exterior`，默认 axis
- [derive_facade_frame ✅已接线](derive-facade-frame-unwired-ew-sign-trap.md) — 剩 per-segment + 真替 LLM 落位
- [C2 收官冲刺](c2-full-unlock-sprint.md) — ✅ B5 收官；MAJOR 常见形状=「门是真的、锁是缺的」
- [Report org: curated report/ folder](report-org-curated-folder.md) — 用户只看 `report/`
- [Skills lib clean-spec policy](skills-lib-clean-spec-policy.md) — 纯当前版本 spec
- [Phase1 output conventions](phase1-output-conventions.md) — SVG + PNG + `_source.png`
- [Geometry pipeline terminology](geometry-pipeline-terminology.md) — 再拓扑 vs 切配
- [Recognition→modeling capability](recognition-modeling-capability.md) — 两腿并行
- [Editable geometry-confirmation vision](editable-geometry-confirmation-vision.md) — DEFERRED
- [Two-step POC v2 status](twostep-poc-v2-status.md) — sm22=第 3 个干净 anchor
- [sm21 EP anchor: two real defects](sm21-ep-anchor-two-real-defects.md) — 待硬化的是稳定性非内核
- [sm24 非方形首跑+C2 B1 首实战](sm24-nonsquare-first-run-2026-06-24.md) — 一房一 cell
- [sm21 dual-model round 2026-06-21](sm21-dualmodel-round-2026-06-21.md) — codex 看图坑=喂 stdin EOF
- [sm21 dual-model backlog](sm21-dualmodel-backlog.md) · [sm21 review backlog](sm21-review-backlog.md) — 待办
- [Fable5 项目大审已交付](fable5-audit-2026-07-05.md) — Top8 风险；管理文档同步项未执行
- [shapely covers 共线误判 + 跨版本锁盲区](shapely-covers-collinear-misjudge-and-cross-version-lock-blindness.md) — distance=0 仍 covers=False；「同代码跑两次」锁看不见跨版本漂移，逐字段红线只能双提交重建 diff
- [判据从结果反推出来 ⇒ 它就不是判据](acceptance-bar-must-not-be-written-from-the-result.md) — ⭐⭐⭐ **09-01 第三形态：绿锚锚在「整份全绿」上 ⇒ 本锁成了【别人家已知缺陷】的人质**（我判「改成规则就好」，实测 5 条红里 **4 条死在 `assert audit.passed` 本身**，改名单一条都不变绿）⇒ **绿锚必须锚在本锁自己负责的那一段上**；排除别人家缺陷要**具名列码 + 注明归谁**，并把「删掉这两行」挂进那个单的验收表 · ⭐⭐⭐ **09-01 镜像形态：判据钉住了【缺陷本身的存在】**（写「**那 3 个**必须登记」⇒ 缺陷一修好锁必红）；解=拆成**规则**+**读数**两半 · 08-26 GLM 点名：我把复核单的「范围」清单照着实际 diff 写 ⇒ 「有没有超范围」永远不可能不通过；自查话术=「这条判据什么情况下会不通过」；同日同族第二犯=把具体报错码写死为通过标志
- [「换一份产物，这条结论还在吗」](is-this-conclusion-product-side-or-code-side.md) — ⭐⭐⭐ 08-26 用户纠偏：我把验收对象锚在即将作废的旧产物上，施工方白试三轮；⭐ 能力 ≠ 读数（「polygon 全 null」是读数、「得能产多边形」是能力）
- [席位撞额度留下静默孤儿件 ⇒ 分段提交](seat-quota-failure-leaves-silent-orphans.md) — ⭐⭐ 09-02 一天两次（1035+1273 行），**日志只有 2-3 行只字不提**；⛔ 收到失败先 `git status`（含 worktree），⛔ 别只看日志；⭐ 解法=**派工单一律要求分段提交**，立后三次中断零丢失；⭐⭐ **09-03 附条：席位报的「额度重置时间」是北京时间（UTC+8），⛔ 别直接减容器 UTC** —— 我算成 11.2h 判「今天没了要改派」，实为 3h10min，**整 8 小时差就是判别签名**
