# Codex project memory index

## EnergyPlus-Agent-dev

- Workspace: `/workspaces/EnergyPlus-Agent-dev`.
- User-confirmed strategy and pending handover: [energyplus-agent-dev.md](energyplus-agent-dev.md).
- Read this project memory when resuming the EnergyPlus-Agent-dev takeover. It records the user's 2026-09-07 decisions, including corrections to earlier assistant proposals.
- Current status: wait for Claude to complete one full case run; inspect that result and make backups before taking over development. Do not synchronize project management documents until the takeover.
- Core deliverable: configurable multi-agent harness producing a generic lightweight building geometry model ("丐版 BIM"); EnergyPlus is the first downstream simulation plugin.
- Runtime targets: local-deployment-class and Flash-class models via API for now, with Sonnet-class as the accepted upper tier. These runtime limits are distinct from the development team's model allocation.
- User authorizes delegation, with a later explicit priority: preserve GPT quota for Astra and minimize other GPT model calls. Reasoning can go to Opus; prefer Claude/GLM/DeepSeek for routine delegated work. Sol/Terra/Luna are available but not default workers. Live connectivity results are recorded in the project memory.
- Current capability sources, corrected peak/off-peak schedules and large-job preflight guidance: [model routing, checked 2026-09-07](energyplus-agent-dev-model-routing-2026-09-07.md). Read before allocating substantial model work; account capacity and promotions require fresh checks.
