# Development model routing and quota scheduling

Checked: 2026-09-07, approximately 17:04 UTC. Private Codex memory for `/workspaces/EnergyPlus-Agent-dev`. Sources below were opened, not merely read from search snippets. This is a routing starting point, not a project benchmark result or a running scheduler.

## User instructions and scope

- User authorizes researching model capabilities, sensible delegation and quota-aware scheduling. Minimize other GPT calls and preserve GPT capacity for Astra. Opus may take reasoning tasks.
- For large jobs, inspect available quota/balance beforehand; if capacity or allocation is uncertain/material, present a concrete work scope, estimated consumption/time and alternatives for the user to decide. Do not ask for every routine small task or invent a numerical spending cap.
- No development handover yet: Claude must finish the full case first, then inspect and back up. These notes must remain private until handover; no shared project documentation or configurations were changed for this research.
- Development models and billing channels are distinct from product/runtime model ceilings. Runtime still targets local/Flash class, with Sonnet-class upper tier. Strong development help must not become an unreported runtime dependency.

## Initial task allocation — a project judgment, to adjust from results

| Model/channel | Initial responsibilities |
| --- | --- |
| Astra (current root) | Research direction, shared geometry/interface decisions, integration and difficult cross-module diagnosis. Read concise evidence and relevant diffs rather than repeating every worker's exploration. |
| Claude Opus | Bounded deep reasoning: ambiguous geometry semantics, architectural tradeoffs, difficult root-cause analysis and independent review of consequential changes. Do not spend it on every routine task. |
| Claude Sonnet | Cohesive implementation, multi-file fixes, viewer interactions and end-to-end debugging when its quota and task fit are favorable. |
| GLM-5.3 | Substantial but bounded text/code work: module implementation, repository investigation, refactoring and review. Not restricted to clerical tasks. |
| GLM-5.3-Flash | Candidate for routine coding, document/image inspection and visual feedback. Test drawing-specific ability before relying on it for dimensions/topology. |
| DeepSeek V4 Flash | Routine implementation, structured extraction, batch result analysis and economical iteration; an important runtime baseline candidate as well. |
| DeepSeek V4 Pro | More demanding reasoning/coding when Flash struggles or Claude capacity is scarce; choose by delivered cost and quality. |
| Claude Haiku | Small summaries, classification and straightforward changes when shared Claude quota makes it sensible. |
| Other GPT models | Exceptional use only; Sol/Terra/Luna connectivity was verified earlier but user subsequently rejected routine delegation to them. |

- Give each worker a coherent task with necessary context, an output artifact and a clear completion criterion. Avoid fragmenting work into many trivial calls or making every change traverse a multi-model review chain.
- Parallelize independent tasks across providers when useful. Multiple workers on one subscription still consume the same limited capacity; account for Claude's ongoing case work.
- Use actual development tasks to record model ID, effort, task type, acceptable completion, rework, elapsed time and provider usage/cost. Adjust routing by total delivered cost, including retries and Astra/user review effort. Public coding benchmarks do not establish architectural drawing accuracy.

## Verified capability references and limits

- [OpenAI Astra](https://developers.openai.com/api/docs/models/gpt-6-astra): official positioning is difficult end-to-end reasoning/coding/research work; supports image input and tools. API token prices are not a measurement of this Codex subscription's remaining quota.
- [Claude model overview](https://platform.claude.com/docs/en/models/overview): current lineup includes Opus 5, Sonnet 5 and Haiku 4.5; models support image input and tools. Existing project references to Opus 4.8 are historical. Do not assume the user's subscription/installed CLI can access a newly listed model or silently change aliases. Record the actual resolved model. Previous live check verified Sonnet 5, not Opus.
- [GLM-5.3 author model card](https://huggingface.co/zai-org/GLM-5.3): emphasizes coding and long-horizon agent tasks. Vendor benchmark gains are not our measured advantage.
- [GLM-5.3-Flash author model card](https://huggingface.co/zai-org/GLM-5.3-Flash): native multimodality; 320B total / 18B active parameters. Active parameters do not imply Qwen-27B-like deployment memory. Explicit reasoning levels are low/high/max; omitted or unsupported values default to max. Benchmark results use substantial task-specific settings; budget reductions need project testing. Check adapter forwarding before assuming CLI effort controls the provider correctly.
- [DeepSeek V4 Pro release](https://api-docs.deepseek.com/news/news260813/): Flash and Pro support low/high/max effort and agent workflows. [Current API table](https://api-docs.deepseek.com/quick_start/pricing/) lists JSON, tool calls and Anthropic/Responses compatibility, plus a separate `deepseek-v4-flash-vision-exp` model. Do not infer native image support for the ordinary Flash/Pro IDs from that separate model. Vision-exp has not been tested in this project.
- Earlier local shape/color probes in the project guide favored GLM-5.3-Flash over GLM-5.3 for images. Those historical tiny probes are neither fresh tests nor evidence of building-plan fidelity. This research made no additional inference calls.

## Current billing windows and quota rules

Use explicit timezones. The workspace clock is UTC; the working schedule below is Beijing time (UTC+8).

### GLM — domestic BigModel Coding Plan channel

Source: [current plan overview](https://docs.bigmodel.cn/cn/coding-plan/overview), [FAQ](https://docs.bigmodel.cn/cn/coding-plan/faq).

- Peak: Monday–Friday 14:00–18:00 Beijing (06:00–10:00 UTC). Other hours deduct 50% of base model points.
- Base coefficients (uncached input / cached input / output): GLM-5.3 = 6.9 / 1.7 / 24; Flash = 2.3 / 0.56 / 8. Points = weighted token sum / 10,000. Use disjoint cached/uncached counts.
- Both five-hour and weekly point limits apply. Five-hour points refresh dynamically after consumption; weekly cycle starts from the subscription order. Read account usage for actual capacity/reset time.
- Old search snippets and project notes saying peak 3x/nonpeak 2x or 1x are superseded by the current overview.
- A temporary 23:00–09:00 activity is advertised: Flash unlimited in ZCode, doubled allowance in other agents. Details could not be fetched; do not assume duration, stacking or unlimited access in our Claude Code launcher.
- Coding Plan is for supported coding tools. Our custom simulation harness must use appropriate standard API billing, not assume this development subscription covers product inference.

### DeepSeek — metered API balance

Source: [current pricing](https://api-docs.deepseek.com/quick_start/pricing/).

- Peak: Monday–Friday 09:00–12:00 and 14:00–18:00 Beijing (01:00–04:00 and 06:00–10:00 UTC). Other hours, including weekends, are half price.
- USD per million tokens, peak: Flash = 0.014 cached input / 0.44 uncached input / 1.32 output; Pro = 0.044 / 1.32 / 3.96. Off-peak rates are half these. Use the account's actual currency and current tariff when estimating a job.
- The platform marketing page and older snippets show other prices; use the current API pricing page.
- [Documented balance query](https://api-docs.deepseek.com/api/get-user-balance/): GET `/user/balance`; returns availability and currency balances. Query before large jobs. The same account funds the simulation pipeline, so available cash is not an allocation exclusively for development.

### Claude — current subscription channel

Sources: [usage limits](https://support.claude.com/en/articles/9797557-usage-limit-best-practices), [Claude Code with Pro/Max](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan).

- Inspect both five-hour session and weekly limits, including any model-specific limits shown by the account. Claude chat and Code share subscription capacity.
- Context, attachments, tools, model choice and effort affect usage. Inspect actual Usage/reset information; do not assume five hours from now or a fixed messages-per-job allowance.
- No remaining quota was queried in this research. A tiny successful request proves availability, not sufficient capacity for a long task.
- Do not treat Claude Code's Anthropic-style cost estimates for GLM/DeepSeek as actual provider charges.

## Scheduling practice for future authorized work

- Prefer nonurgent GLM/DeepSeek batches after 18:00 Beijing, before 09:00, at lunch 12:00–14:00, or weekends. All are off-peak for both under the current base schedules. GLM also has off-peak weekday mornings when DeepSeek may be peak.
- Keep the critical path moving when waiting costs more than the tariff saving. Claude planning/review timing should follow its actual quota/reset and current case needs.
- Before a large run: inspect provider usage/balance and concurrent work; estimate from a representative task or previous comparable usage; bound the task and preserve intermediate artifacts. Ask the user to choose only when material allocation, unknown capacity or an unresolved cost/time tradeoff warrants it. Do not silently consume extra paid credits or switch billing accounts.
- Try a suitable economical model first when task evidence supports it; escalate effort/model or clarify the task when failures show a capability/context problem. Avoid repeated cheap failures that cost more in total. No blanket requirement to start every task at the lowest effort/model.
- A lightweight task/usage record suffices initially. No new autonomous scheduler, quota monitor or background job was installed. Recheck prices, promotions, model IDs and account capacity when the relevant job starts.
