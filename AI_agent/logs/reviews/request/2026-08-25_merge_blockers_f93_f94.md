# 派工单 · 清合并阻塞（F-93 全仓 4 项红 · F-94 装机路径硬编码）

- **日期**：2026-08-25
- **分支**：`08.23_AsDrawnReading`（当前 HEAD `60453eb`）
- **档位**：**工程档**（碰 `tests/` + 夹具 + 环境装机）⇒ gate① + 全量绿 + 同族自审；⛔ 本单不产成绩
- **为什么现在做**：用户 2026-08-25 定序 —— **① 支线回并 → ② reading/correction 一体改 → ③ 拿 sm25 撞 C2**。
  这两条是 ① 的**前置**：全仓红着无法判断回并有没有踩坏东西；装机路径的问题**合并后会从"响亮失败"变成"静默串台"**。

> ⚠️ **本单的每个数都由 orchestrator 于 2026-08-25 亲手复跑得到**（命令附在每条下面），
> ⛔ 不是照抄此前的登记。
> ⭐⭐ **但派工单本身可能题错** —— 历史上「停下上报」累计 **23/23 全是派工方（orchestrator）题错**。
> **凡本单的判断句（尤其"这是陈旧锁""前提已不存在"）请当作【可能错的前提】对待：
> 发现不符即停下上报，⛔ 不要顺着错的前提施工。**

---

## 一、F-93：全仓 4 项红，四项同源

复跑命令与结果（`-n0`，15.4 秒）：

```
python -m pytest tests/test_elevation_score_bindings.py tests/test_reading_typed_score_f67.py -n0 -q
→ 1 failed, 12 passed, 3 errors
```

**同一个根因**：sm25 的 gt 于 **2026-08-23**（`e982eba`）重签入库，
而这两个测试文件分别改于 **08-22**（`96604c9`）和 **08-21**（`8d08a47`）
⇒ **gt 晚于锁一天入库，锁与夹具都没跟着走。**

### 1-a 陈旧锁（1 failed）

`tests/test_elevation_score_bindings.py::test_generator_fails_closed_on_sm25_multi_floor_fingerprint`

它断言：**当一个 case 的多层轮廓指纹不一致时，绑定生成器必须 fail closed**（`returncode != 0`）。
实测现在生成器正常退出 0，因为它拿到的 sm25 已经不满足那个前提了：

```
F1 footprint_fingerprint = 52f382ee6abb40bcb2284a822a01fe27f80d2e026df53a4bc8b8c462e3d98621
F2 footprint_fingerprint = 52f382ee6abb40bcb2284a822a01fe27f80d2e026df53a4bc8b8c462e3d98621
两层顶点亦逐位相同；distinct fingerprints = 1
```

⇒ orchestrator 的判断（**请证伪**）：**锁想守的行为没坏，是它挑的样本不再是那个行为的样本**。

⭐ **建议的修法方向（但由施工席位判断并说明理由）**：
**别删这个锁** —— 它守的「多层指纹不一致要 fail closed」仍然是要守的行为。
应当**给它一个真正满足前提的样本**（构造一份指纹确实不一致的合成 gt），
让锁**先自证前提**再断言（[[regression-case-must-prove-its-own-premise]]）。
⛔ 如果施工席位认为「这条行为已经不该守了」，**停下上报，不要自行删锁**。

### 1-b 陈旧夹具（3 errors）

`tests/test_reading_typed_score_f67.py` 三项，均 `ScoreContractError: score_view_binding_invalid`。

夹具从历史 run `run_2026-08-21_c2_first_sonnet_T1/_run/judge_score_bindings.json` 拷贝，其中记的是**旧 gt**：

```
fixture.gt_content_sha256 = f97cea65b445148d5e3ee79f51eebdc30114d1c357163ae2bc557cc02a912f9b
当前 gt.content_sha256    = 135b282ce142002bf89e29905763d5940e9cc1a18cf87ca1d9580e872a51c485   ← 不匹配
```

⭐ **修法已有现成参照**：08-25 重建过的 `run_2026-08-25_c2_rescore_R0/_run/judge_score_bindings.json`
里记的**已经是** `135b282c…`（实测匹配）。

**两条路，请施工席位选并说明理由**：

| | 做法 | 代价 |
|---|---|---|
| (a) | 就地重建 T1 那份绑定 | 会改**历史 run** 的文件 —— 请先确认这是否可接受 |
| (b) | 夹具改指向 R0 | **换了被测对象**（f67 测的是 T1 的识图产物 + 它的 `score_vs_gt.json`）⇒ 须确认三条断言在 R0 上仍然测的是同一件事 |

⛔ **两条都有坑，orchestrator 不预设答案**；若两条都不成立，**停下上报**。

---

## 二、F-94：装机路径硬编码指向主树

实测（`cat`）：

```
/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
内容 = /workspaces/EnergyPlus-Agent-dev        （主树绝对路径，无换行）
```

**后果**：在**任何非主树的工作树**里**裸跑**一个 `from src.… import …` 的脚本
（非 `-m`、非 pytest），若脚本自身目录下没有 `src/` 包，`src` 会**静默从主树解析**。
跨家族审（GLM）已独立确证根因链并实测了三处受影响面。

⭐⭐ **合并前必须处理的理由**：合并后同名文件在两棵树都存在
⇒ 踩坑不再报错，而是**静默用错那棵树的代码**。

⛔ **本条先出方案、后施工**（它碰的是所有席位共用的环境）：
请先给出 2–3 个候选做法 + 各自代价（至少覆盖：多工作树并存、pytest 与裸跑两种入口、
新席位开机时会不会重新踩坑），**交回 orchestrator 与用户拍板后再动手**。

---

## 三、验收判据（两条都适用）

1. **全量绿**：`python -m pytest -n auto`（主树，16 核 4.5–8 分钟）⇒ **0 failed / 0 errors**；
   xfailed 数量与修前一致或有解释。
   ⛔ **全量在跑时不许动树**（[[green-suite-is-a-property-of-tree-and-launcher]]）。
2. **锁要能变红**：改完的锁/夹具必须当场证明**摘掉修复后它确实会红**，
   并说明**变红的方向是对的**（[[neuter-proves-wiring-not-discriminating-power]]）。
3. **不得为过测而放宽判据**：⛔ 调阈值、加 skip、改断言方向都属于停下上报的情形。
4. 交件写明 **commit hash**，并附**自己跑的**测试输出原文（⛔ 不写自述结论）。

## 四、席位与审

| | |
|---|---|
| **施工** | 执行档（建议 GLM 席位）—— 碰 `tests/` 与环境配置，⛔ 不碰 `src/agent/pipeline` 内核与交接契约 |
| **审** | **换家族、恒升一档**；复核只看原始需求 + `git diff` + 测试输出，⛔ 不看执行者长篇自述 |
| **⛔ 谁写谁不批** | orchestrator 出单，⛔ 不参与施工 |

## 五、⛔ 本单明确不含

- **F-95 / F-96**（答案直喂内核撞出的两条内核缺陷）⇒ 归用户定的第 ③ 步「拿 sm25 撞 C2」。
- **gt 保留逐边厚度 + 不规整校验**（R-6）⇒ 归第 ③ 步之后的 gt 层。
- 支线 `toolbox_into_src_08.25` 的**合并动作本身** ⇒ 本单清完阻塞后另行安排。
