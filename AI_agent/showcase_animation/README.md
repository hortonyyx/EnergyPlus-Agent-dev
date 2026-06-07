# EnergyPlus Agent Showcase Animation

Final single-page showcase animation for EnergyPlus Agent.

## Open

Open this file directly in a browser:

```text
prototype/index.html
```

No build step, npm install, or local server is required. GSAP is loaded from CDN; if the
CDN is unavailable, the page keeps a limited CSS-animation fallback.

## Current Shot List

1. Opening
2. Traditional Workflow
3. Building Simulation Copilot
4. EnergyPlus Agent
5. My Pipeline
6. Multimodal Design input
7. Overall Pipeline
8. Path 1: Drawing to BIM
9. Path 2: Drawing to BEM
10. Verifiable workflow

## Controls

- `Continuous`: plays the whole sequence from Shot 1 to Shot 10.
- `Slide`: plays one shot at a time.
- Left directory: plays the selected shot animation.
- Right directory: jumps directly to the selected shot's final frame.

## Files

- `prototype/index.html` - structure and shot content.
- `prototype/styles.css` - layout, visual system, and fallback CSS animation.
- `prototype/script.js` - GSAP timelines and playback controls.
- `prototype/assets/` - final image and SVG assets used by the animation.
- `DESIGN.md` - global color, typography, and motion direction.
- `CHANGELOG.md` - concise summary of final adjustments.

## Final Version Notes

- `index.html` references `styles.css?v=62` and `script.js?v=60`.
- The last pass normalized non-opening shot titles to the same size and position.
- Final validation used local Chrome / Playwright plus `node --check`.
