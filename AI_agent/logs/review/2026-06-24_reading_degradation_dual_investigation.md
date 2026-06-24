# Reading 退化调查（Codex 独立 + 主控亲验，双路收敛）— 2026-06-24

## 缘起
sm21_pre（~06-09）那份识图被视为最好；近期 Sonnet 识图在**坐标级 vs gt** 对账上明显差
（Sonnet 1f 竖隔墙偏 0.36m、7 窗只 1 窗位置命中）。问：reading 定义从那时到现在**是否退化**？

## 方法
两路独立：① Codex（gpt，high effort，danger-full-access，read-only，禁读 gt）查 git 历史；
② 主控亲取旧 prompt 原文比对。

## 时间线（reading 定义如何被治理）
- 06-09 前：规则在 `skills/energyplus_mcp_twostep/phase1/{guide,reading_guide,pen_library,prompt_template}.md`，无 schema。
- 06-09 `29845ea`：phase1/ → 0_reading/（100% rename）。**sm21_pre 好识图 = 这个时代的规则形态**（且其识别本体实为 05-28 pocv2 的 **Opus** 识图，见 reading-quality memory）。
- 06-10 `fc31ea5`/`0558146`：skill 库迁 `skills/intake_pipeline/0_reading/` + 术语清理，行为基本不变。
- 06-15 `0d267bf`：首建 `src/agent/reading/schema.py`（Pydantic canonical，Dimension 加 chain_id/role/order/value_m/text_verbatim/anchor；elevation 转 image-local facade）。
- 06-22 `fa04ef6`：reading-honest（provenance/confidence/dimension_refs + two-channel prose）。
- 06-22 `600d30e`：auto-reread 协议。

## 结论:核心 skill 规则没退化,但 **启动 prompt + 坐标精度责任退化了**（两路收敛）
1. **坐标精度硬压力被软化（真退化，对坐标 vs gt 指标）**：
   - 旧 prompt：“perception errors can only be caught in phase 1. Once phase 1 misreads a dimension,
     **offsets a coordinate**, flips the axis, or misses a stroke, phase 2 cannot backtrack.”
   - `fa04ef6` 改成：“…unless the reading JSON still carries an independent redundant channel… an
     **offset coordinate with a surviving dimension chain… can be recovered by correction**.”
   - → 放掉了“每个坐标必须在 reading 读准”的弦；我们量的恰是坐标 vs gt。
2. **启动 prompt 06-16 缩水**：旧 `prompt_template.md` 强制 ① 用 testdata 的**总尺寸/层高**锚定坐标
   ② summary 写**四立面 x_local↔world 映射表**（逼模型显式算坐标变换）③ 8 条编号 core discipline；
   现 `new_case_guide.md` Appendix A 把这些砍成几行、丢了①②。
3. **schema/guide 不同步**：schema 支持 `text_verbatim/value_m/chain_id/role/order`，但 guide 的
   `dimensions[]` 示例仍教旧 `text/from/to/axis/note` → 模型没被教产出可校验的尺寸链字段。

## 诚实标注（不可越界的限制）
- 这是**指令/prompt 层面**的退化，是“坐标 vs gt 变差”的**合理机制**，**未证明**是 Sonnet 坐标错的成因。
- sm21_pre 好识图本体是 **Opus**，“旧 prompt 强”与“Opus 强”在历史里仍混在一起，单此不能分开。
- 非退化项：rename/术语、reading_guide/pen_library 后续加的防错规则（dim-tick/door/provenance）、schema/legacy adapter。

## 下一步（下次起，plan N1d #2）
**Sonnet 强/弱 prompt A/B**：给 Sonnet 恢复旧式强 prompt（坐标必须读准·别指望 correction 恢复 + 总尺寸锚定 +
四立面映射表 + 尺寸链算式入 note），对比现 prompt，**两边都用 `score_reading_vs_gt` 按 gt 坐标对账**，
看 Sonnet 1f 竖墙 0.36m 偏差 + 窗错位能否压下去。先修 schema/guide 不同步亦可顺带。
