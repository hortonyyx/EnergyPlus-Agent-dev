"""DeepSeek v4-pro path of the reading-scaffold migration-completeness audit.

The script reads every material file itself (so the orchestrator never pulls the
file bodies into its own context) and runs a single-shot DeepSeek v4-pro call with
thinking ON, writing the audit to deepseek_findings.md next to this file.

Run from repo root:  python AI_agent/logs/review/2026-06-25_reading_migration_completeness_audit/run_deepseek_audit.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from openai import OpenAI  # noqa: E402
from src.agent.llm import load_llm_section  # noqa: E402  (triggers load_dotenv)

AUDIT_DIR = pathlib.Path(__file__).resolve().parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


OLD = "AI_agent/logs/review/2026-06-25_scaffold_degradation_audit/old_scaffold_127ba06"
NEW = "skills/intake_pipeline/0_reading"

blocks: list[str] = []
for f in ["guide.md", "reading_guide.md", "pen_library.md", "prompt_template.md"]:
    blocks.append(f"### [BASELINE · old two-step sm21_pre] {OLD}/{f}\n```\n{read(OLD + '/' + f)}\n```")
for f in ["guide.md", "reading_guide.md", "pen_library.md", "session_kickoff.md"]:
    blocks.append(f"### [CURRENT · 0-5 skill] {NEW}/{f}\n```\n{read(NEW + '/' + f)}\n```")
blocks.append(f"### [CURRENT · code] src/agent/reading/schema.py\n```python\n{read('src/agent/reading/schema.py')}\n```")
blocks.append(f"### [CURRENT · code] src/validator/checks/reading.py\n```python\n{read('src/validator/checks/reading.py')}\n```")

SYSTEM = """你是 DeepSeek v4-pro，做一路【独立】的「旧两步法 reading 脚手架 → 当前 0-5 架构 约束/能力迁移完整性通查」。

这【不是】文档措辞 diff（那个已做过），是核对「旧脚手架施加的每条约束/能力，在当前架构里还在不在、起不起作用、有没有被几何确定性化重构斩断」。背景：6.10-6.16 那次大重构把「LLM 做几何」改成「代码做所有几何（建模+切配）+ 装配，LLM 只做感知/校正判断/物理语义」。约束的载体可能因此从 prompt 搬到了代码。

【基线·迁移源】= 我贴的 [BASELINE] 4 个旧 skill 文件（两步法 sm21_pre 时代，在 sm21_pre 上表现良好、用户定为基准）。
【当前·迁移目标】= 我贴的 [CURRENT] skill 文档 + schema.py + reading.py（确定性校验门）。

【重要】有些旧 prompt 约束的载体可能被搬到了【下游确定性代码】（如 src/agent/correction/deterministic.py 的 cross-floor reconcile、envelope.py、几何内核）——这些代码【没有贴给你】。对这类「疑似迁到代码」的约束，备注里写 **[需代码核验]**，不要臆断已迁或遗漏。

【任务】枚举旧脚手架施加的每条约束/能力（不只措辞，是「它要求模型做/不做什么、保证什么」），逐条核到当前落点，分四桶：
- ✅ 已迁：约束仍在（prompt→prompt，或 prompt→schema/校验门，载体变了但约束在）。注明新落点。
- ❌ 遗漏：旧有、当前文档/schema/门都没有、且看不出是有意删 → 候选要补。
- ⚠️ 冲突/斩断：旧约束在当前架构【机制上无法恢复】（依赖一个被重构去掉的东西），或与【新加约束矛盾】 → 这桶最重要，详述机制为什么斩断 / 和谁冲突。
- 🗑 有意删：架构变更使其不再适用（如旧「四立面世界轴映射表」→ 新 image-local 把世界轴归 correction）。注明对应架构决策。

【特别盯】
- 几何/坐标/世界系/跨层/窗位 的约束被改架构后是否【等价保留】还是【悄悄弱化/丢失】。
- 5.12/5.29 迁移补的三条硬约束：per-floor window chain（每层窗尺寸链）/ absolute world z（绝对世界 z）/ cross-floor split-pairing（跨层切配）——现在去哪了、还成立吗。

【输出】只输出 markdown 正文：四桶表格（列：约束 | 旧出处 | 新落点 或「无」或「[需代码核验]」| 桶 | 备注），⚠️冲突桶【单独一节详述机制】。开头一行给四桶各计数。"""

HUMAN = "## 材料\n\n" + "\n\n".join(blocks) + "\n\n## 现在产出完整的迁移完整性审计 markdown。"

section = load_llm_section("intake_correction")
api_key = section.get("api_key")
if not api_key:
    raise SystemExit("no DEEPSEEK_API_KEY (.env)")

print(f"prompt: system={len(SYSTEM)} human={len(HUMAN)} chars", flush=True)
client = OpenAI(api_key=api_key, base_url=section.get("base_url"), timeout=1200.0, max_retries=2)
resp = client.chat.completions.create(
    model=section["model_name"],
    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": HUMAN}],
    temperature=0.3,
    max_tokens=64000,
    extra_body={"thinking": {"type": "enabled"}},
    reasoning_effort="max",
)
msg = resp.choices[0].message
content = msg.content or ""
reasoning = getattr(msg, "reasoning_content", None)
usage = resp.usage

(AUDIT_DIR / "deepseek_findings.md").write_text(content, encoding="utf-8")
if reasoning:
    (AUDIT_DIR / "deepseek_thinking.txt").write_text(reasoning, encoding="utf-8")

print(
    f"DONE finish_reason={resp.choices[0].finish_reason} "
    f"out_chars={len(content)} "
    f"prompt_tokens={getattr(usage, 'prompt_tokens', None)} "
    f"completion_tokens={getattr(usage, 'completion_tokens', None)}",
    flush=True,
)
