# Showcase Animation Changelog

## Final State - 2026-06-06

- Reduced the showcase to 10 final shots.
- Rebuilt the narrative around:
  - product framing,
  - EnergyPlus Agent internals,
  - the user's pipeline,
  - Drawing-to-BIM and Drawing-to-BEM paths,
  - human-verifiable workflow checkpoints.
- Added dual directories:
  - left side plays a shot animation,
  - right side jumps to the shot's final frame.
- Normalized non-opening shot titles to one shared size and position.
- Applied the final semantic color system:
  - agent/capability: blue,
  - data flow/review: teal,
  - BIM/BEM/model outputs: orange,
  - pain/broken feedback only: red.
- Cleaned Shot 4 direct navigation state so repeated direct playback lands reliably.
- Tuned Shot 10 review cards so review artifacts, knowledge base, and user confirmation
  appear at a readable cadence.

## Validation

- `node --check prototype/script.js` passed.
- `git diff --check` passed after final edits.
- Browser checks were run in local Chrome at 1600x900:
  - GSAP loaded.
  - Left/right directories were symmetric.
  - Shot 2, 4, 5, 7, 8, 9, and 10 target colors and final states were checked.
  - Shot 4 direct playback was stress-tested repeatedly without display errors.

## Cleanup - 2026-06-06

Removed process-only artifacts from the delivery folder:

- iterative `_snapshots/`
- local QA screenshots
- Playwright/audit output folders
- early full prototype backup
- old part-by-part planning notes
- unused legacy `asset (1..5)` images
- one-off preview page

The remaining folder is intended to be the clean handoff package.
