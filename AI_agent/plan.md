# 输入端 VLM 识别准确性提升计划

> 评估两条候选路线并给出分阶段推进计划：
> **路线 1**：优化 [../skills/energyplus_mcp/](../skills/energyplus_mcp/) skill 文档，采用思维链（CoT）让 VLM 分步识别
> **路线 2**：前置专用视觉小模型，把平面图矢量化为统一格式（墙/门/窗/房间），再交给 VLM

---

## 结论先行

**基于案例集实测数据（[claude.md §3.1.2](claude.md)）的冷结论**：VLM 视觉识别**不是**当前 0/13 端到端通过率的**首要**瓶颈，但确实是 **zone 几何准确性**（6/8 = 75%）和**走廊/楼梯漏识别**的直接原因，值得专门优化。

| 方案 | 推荐指数 | 原因 |
|---|---|---|
| 方案 1（CoT skill 优化）| ★★★★☆ | 零部署成本，先做。**但必须配合评测基线，否则优化无反馈** |
| 方案 2（VLM 前置专用视觉模型）| ★★☆☆☆ | 工程量大，且中文建筑图纸**没有现成高精度预训练模型**可用；适合作为 P1 阶段的**局部增强**（只做尺寸链 OCR），不建议作为 P0 主线 |

---

## 一、先校准「输入端」到底错在哪

从 7 个到达 IDF 的案例回溯错误来源：

| 错误来源 | 频次 | 是不是视觉问题 |
|---|---|---|
| zone 数量对不上声明值 | sm_7（少 12 个） | **是**：漏识别房间/走廊分隔 |
| 房间尺寸偏差 | 未量化（需补工具）| **可能是**：尺寸链 OCR 错 |
| 内墙两侧构造不对称 | sm_0 Fatal 主因 | **否**：tool-call 时的疏忽 |
| Schedule/Lights/HVAC 缺失 | 7/7 | **否**：流程漏调 |
| 大规模案例早停（≥30 zones）| sm_6/9/10 | **否**：tool-call 轮数/上下文 |

**视觉类错误的细分**（按现有 skill 的 Step 2–3 拆解）：
1. **裁剪框定位不准** → 漏房间或把标注当墙
2. **尺寸链数字 OCR 错** → 房间宽度偏移
3. **走廊识别**（宽白带 vs 细线墙）→ zone 数少算
4. **楼梯 / WC / 电梯符号** → 漏特殊 zone
5. **跨层对应**（多层时 F2 vs F1 的对位）→ 垂直几何错位

方案 1 能改善 1、3、4、5；方案 2 对 2、3 帮助大但依赖模型质量。

---

## 二、方案 1：CoT Skill 优化 —— 详细评估

### 2.1 可行性
✅ **非常高**。[../skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 已是半 CoT 结构（Step 0 → Step 7），但有几处可以强化。

### 2.2 具体改造建议

| 现状 | CoT 改造 |
|---|---|
| Step 2b 让模型「一次标完所有 zone」 | 拆成 **① 只识别外墙边界** → ② 只识别尺寸链数字 → ③ 只识别走廊（宽白带）→ ④ 只识别楼梯/WC 符号 → ⑤ 综合成坐标表。**每步单独输出中间产物** |
| 没有自检回路 | 每步末尾要求模型**自问一致性**：`sum(segments)+2×wall ≟ total_width？`，失败则回到该步重试 |
| 「Read 图片后裁剪」裁剪框靠 LLM 猜 | 让模型**先画一张 overview 网格叠加图**（10×10 等分），再用网格坐标定位建筑外包，而不是直接给像素值 |
| Step 3 坐标表让模型一次写全 | 先生成 **房间列表（只有名字和类型）** → 再生成 **x/y 范围** → 再生成 **Floor Vertices** → 最后生成**邻接矩阵**（可从 x/y 范围机械推导） |
| 没有视觉 Self-Check | 画完 `top_view_annotated.png` 后，再 Read 一次自己画的图做 sanity check（「红字有没有压到墙上？」「有没有 zone 没标？」）|

### 2.3 开源 VLM 适配性
- **Qwen2.5-VL / InternVL3 / MiniCPM-V 2.6** 对 CoT 指令跟随比 Llama 3.2-Vision 好
- 但都比 Claude Opus 差 → CoT 的每一步**必须有明确的结构化输出约束**（JSON schema），不能指望模型自觉按格式回
- 建议改造时把每个子步骤的输出都定成 Pydantic model，逐步填 `IntakeOutput` 而不是一次填满

### 2.4 成本与收益
- **工程成本**：1–2 周重写 skill + 做 few-shot
- **预期收益**：zone 识别率 75% → 90%+（估计值）；走廊漏识别 → 可根本解决
- **风险**：提示词变长，上下文占用增加；开源模型长 CoT 容易跑偏

---

## 三、方案 2：前置专用视觉模型 —— 详细评估

### 3.1 可行性警告
⚠️ **别被现成的预训练模型误导**。公开可用的平面图解析模型基本都是西式住宅训练的：

| 模型 / 数据集 | 覆盖场景 | 对本任务的可用度 |
|---|---|---|
| **CubiCasa5K**（Kalervo 2019）| 芬兰公寓手绘 | 外墙识别可用，内部房间类型标签不通用 |
| **Raster-to-Vector / Floor-SP** | 公寓矢量化 | 对中文办公楼效果差 |
| **RPLAN**（清华）| 住宅布局 | 只做生成，不做识别 |
| **FloorPlanCAD**（阿里）| CAD 级建筑图 | **最接近**，但需 CAD 输入非 PNG |
| **LayoutLMv3 / DocLayNet** | 文档版面 | 不适用 |
| **PaddleOCR / Tesseract** | 文字 / 数字 OCR | **局部可用**（尺寸链数字） |

**中文建筑渲染图 / 混合风格**（现 `test_data` 里的那种）**没有开箱即用模型**。要达到替代 VLM 感知的精度，需：
- 自建标注数据集（≥ 500 张）
- 训 HRNet / Mask R-CNN 做墙/门/窗/符号分割
- 做后处理 raster → vector

### 3.2 如果硬做，推荐的最小版本

**不做完整矢量化，只做 3 个定向小模块**：

| 模块 | 技术 | 收益 |
|---|---|---|
| **尺寸链 OCR** | PaddleOCR + 规则后处理（找 `3600` 这类 4 位数字序列） | 直接解决问题 2（尺寸 OCR 错），最值得做 |
| **走廊识别** | 传统 CV：`cv2` 形态学运算，提取宽连通白区域（宽度 > 阈值） | 直接解决问题 3 |
| **楼梯/WC 符号检测** | YOLOv8 在 ~200 张标注图上微调 | 解决问题 4 |

3 个模块的产出塞进 prompt 作为**结构化视觉先验**（JSON），VLM 读图 + 读这份 JSON，准确率会显著抬升。

### 3.3 完整矢量化路线（不推荐作为 P0）

```
原图 → 墙分割（U-Net）→ 骨架化 → 吸附成直线 → 识别闭合区域 = 房间
     → 门窗洞检测（YOLOv8）→ 落到墙线上
     → 尺寸链 OCR（PaddleOCR）→ 房间标注
     → 符号检测（楼梯/WC/电梯）→ 特殊 zone 类型
     → 输出统一 JSON（房间列表 + 门窗 + 尺寸 + 类型）→ 喂 VLM
```

工程量估计 **2–3 个月 + 数据标注**。收益高但 ROI 不划算，除非把这套模型作为「建筑图纸理解库」长期维护。

---

## 四、分阶段推进计划

### P0（必须先做，1 周）—— 建评测基线
> **现在没有自动化评测，任何优化都是盲打。** 这是一切改造的前提。

1. 把 [new_case_guide.md §6](new_case_guide.md) 的 5 档验证清单脚本化：`AI_agent/eval/run_case.py`
2. 把 13 个案例跑一遍 Claude Opus 产出当前基线分
3. **单独为视觉层建专项指标**：
   - zone 数匹配率（已知 6/8 = 75%）
   - 房间尺寸误差（需把 `claude_ep.md` 里的坐标表解析出来和 ground truth 比）
   - 走廊识别 F1
   - 楼梯/WC zone 识别 F1
4. 把 ground truth 补进 `testdata_prompt.json`（现在只有 zone 总数，应加逐房间 x/y 范围）

**没有 P0 就做 P1/P2 = 白做。**

### P1（主攻，2–3 周）—— CoT Skill 优化 + 尺寸链 OCR
> 即方案 1 + 方案 2 的**最小可行模块**

1. 按 §2.2 重写 [../skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 的 Step 2–3 为分步 CoT
2. 每个子步骤用 Pydantic 结构化输出约束
3. 在 [../src/agent/nodes/intake.py](../src/agent/nodes/intake.py) 前挂 `preprocess_floorplan` 节点：
   - 调 PaddleOCR 提取俯视图所有数字 + 坐标 → 注入 HumanMessage 作为「已识别尺寸链」
   - 用 `cv2` 做走廊候选（宽白连通区）→ 注入「可能的走廊 bbox 列表」
4. 用 P0 基线评测前后差异
5. Claude Opus 下提升明显后，再在 Qwen2.5-VL / InternVL3 跑同一套验证

**预期：zone 几何准确率 75% → 90%+；尺寸 OCR 错 → 基本消除。**

### P2（只在 P1 不够时做，1.5–2 个月）—— 补训楼梯/WC/电梯符号检测器
> 即方案 2 的**中等增量**

1. 在 13 个现有案例 + 爬 200 张公开办公建筑平面图，标注楼梯/WC/电梯 bbox
2. YOLOv8n 微调（显存友好，几小时可训）
3. 作为 `preprocess_floorplan` 的第二个输出通道
4. 重新评测

### P3（不建议做，除非要做通用产品）—— 全矢量化
> 即方案 2 的**最大版本**

自建 500+ 标注 + 训墙分割 + 房间闭合提取 + 整套 raster-to-vector。只有在把这套东西做成**独立通用产品**时才值得。

---

## 五、技术选型清单

| 阶段 | 组件 | 选型 | 理由 |
|---|---|---|---|
| P0 | 评测脚本 | 复用 [../src/agent/](../src/agent/) LangGraph + `pytest` | 已有基础设施 |
| P1 | OCR | **PaddleOCR**（中英混排好于 Tesseract）| 中文建筑图纸标注多为中英混排 |
| P1 | 走廊提取 | `opencv-python` 形态学运算 | 不需训练，零成本 |
| P1 | VLM 本地部署 | **vLLM + Qwen2.5-VL-7B-Instruct** | tool-calling 支持好，OpenAI 兼容 API，[../src/configs/llm.yaml](../src/configs/llm.yaml) 改 `provider: openai` 即可接入 |
| P1 | 结构化输出兼容层 | `outlines` 或 LangChain `with_structured_output(method="json_mode")` | 开源模型 tool-calling 不如 Claude 稳，需兜底 |
| P2 | 符号检测器 | **YOLOv8n** + `ultralytics` | 易训、易部署 |

---

## 六、风险登记

| 风险 | 缓解 |
|---|---|
| 建评测基线的工作量被低估（标注 ground truth 费时）| 先标 3–5 个案例的逐房间 x/y 范围，边做边扩 |
| PaddleOCR 在建筑图数字上召回不够 | 配合传统 CV 找水平数字条带 ROI 再 OCR |
| 开源 VLM 即便有视觉先验也无法做长 tool-call 链路 | 本 PR 只解决输入端；tool-call 稳定性留给另一路工作（如强制 checklist 节点） |
| 方案 1 与方案 2 同时上线导致变量耦合 | **严格分阶段**：先 CoT、再加 OCR、再加符号检测，每步单独跑基线 |
| 视觉层提升但下游 Schedule/Lights/HVAC 仍系统性漏调 | 输入端准确率再高，端到端通过率也上不去 —— 必须并行推进子系统覆盖修复 |

---

## 七、一句话行动指令

> **P0 先行：2 周内把评测基线和视觉专项指标做出来**；然后再在方案 1（CoT）+ 方案 2 最小模块（PaddleOCR 尺寸链）上做 A/B，P2/P3 按数据决定要不要投入。

---

## 八、与其他文档的关系

- 本文档聚焦**输入端 VLM 识别准确性**。
- 端到端跑通率的**系统性缺陷**（Schedule/Lights/HVAC 漏调、内墙对称）见 [claude.md §3.1.2](claude.md)。
- 新建测试样例的操作手册见 [new_case_guide.md](new_case_guide.md)。
- 开源模型迁移的总体里程碑（M1–M6）见 [claude.md §4.3](claude.md)，本计划对应其中 **M1（数据集）+ M2（评测）+ M5（提示词/微调）** 的输入端子集。

---

_最后更新：2026-04-20_
