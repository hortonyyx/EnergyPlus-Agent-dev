(function () {
  // 10 shots after removing the final End-to-End Case scene.
  // Global pacing pass: each shot includes a readable final-state hold.
  const slideDurationsMs = [
    3300, // 1 opening
    8000, // 2 traditional workflow
    4800, // 3 product reframe
    4400, // 4 inside the agent
    4400, // 5 my pipeline
    3600, // 6 multimodal evidence
    6000, // 7 pipeline overview
    9000, // 8 BIM path; includes the full correction tour and final hold
    6600, // 9 BEM path; includes all embedded SVG builds and final hold
    7000, // 10 verifiable workflow and closing hold
  ];
  const continuousShotStartMs = [
    0,
    3300,
    11300,
    16100,
    20500,
    24900,
    28500,
    34500,
    43500,
    50100,
  ];
  const totalDurationMs = 57100;
  const transitionProfiles = [
    null,
    { duration: 0.34, x: 16, scale: 1 },
    { duration: 0.46, x: 0, scale: 0.992 },
    { duration: 0.62, x: 0, scale: 0.996 },
    { duration: 0.44, x: 22, scale: 0.994 },
    { duration: 0.34, x: 16, scale: 1 },
    { duration: 0.38, x: 16, scale: 1 },
    { duration: 0.46, x: 24, scale: 0.992 },
    { duration: 0.38, x: 0, scale: 0.996 },
    { duration: 0.52, x: 0, scale: 0.996 },
  ];

  const body = document.body;
  const stage = document.querySelector(".stage");
  const scenes = Array.from(document.querySelectorAll(".scene"));
  const shotNavButtons = Array.from(document.querySelectorAll("[data-shot-target]"));
  const finalShotNavButtons = Array.from(document.querySelectorAll("[data-shot-final-target]"));
  const continuousModeButton = document.getElementById("continuousModeButton");
  const slideModeButton = document.getElementById("slideModeButton");
  const playButton = document.getElementById("playButton");
  const restartButton = document.getElementById("restartButton");
  const previousButton = document.getElementById("previousButton");
  const nextButton = document.getElementById("nextButton");
  const hasGsap = Boolean(window.gsap);

  let mode = "continuous";
  let currentShotIndex = 0;
  let completionTimer = null;
  let progressTimer = null;
  let continuousStartedAt = 0;
  let activeTimeline = null;
  let assetReplayNonce = 0;

  if (hasGsap) {
    body.classList.add("use-gsap");
    window.gsap.defaults({ overwrite: "auto", force3D: false });
  }

  function clampShotIndex(index) {
    return Math.min(Math.max(index, 0), scenes.length - 1);
  }

  function clearCompletionTimer() {
    if (completionTimer) {
      window.clearTimeout(completionTimer);
      completionTimer = null;
    }
  }

  function clearProgressTimer() {
    if (progressTimer) {
      window.clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function stopActiveTimeline() {
    if (activeTimeline) {
      activeTimeline.kill();
      activeTimeline = null;
    }
  }

  function resetPlaybackState() {
    clearCompletionTimer();
    clearProgressTimer();
    stopActiveTimeline();
    body.classList.remove("is-running", "is-complete", "is-shot-complete", "is-final-preview");
    playButton.setAttribute("aria-pressed", "false");
  }

  function setMode(nextMode) {
    mode = nextMode;
    body.classList.toggle("mode-continuous", mode === "continuous");
    body.classList.toggle("mode-slide", mode === "slide");
    continuousModeButton.classList.toggle("is-active", mode === "continuous");
    slideModeButton.classList.toggle("is-active", mode === "slide");
    continuousModeButton.setAttribute("aria-pressed", String(mode === "continuous"));
    slideModeButton.setAttribute("aria-pressed", String(mode === "slide"));
    restartButton.hidden = mode === "slide";
  }

  function updateShotUi() {
    scenes.forEach((scene, index) => {
      scene.classList.toggle("is-active", index === currentShotIndex);
    });

    const updateButtons = (buttons) => {
      buttons.forEach((button, index) => {
        const isActive = index === currentShotIndex;
        button.classList.toggle("is-active", isActive);
        if (isActive) {
          button.setAttribute("aria-current", "step");
        } else {
          button.removeAttribute("aria-current");
        }
      });
    };

    updateButtons(shotNavButtons);
    updateButtons(finalShotNavButtons);

    previousButton.disabled = currentShotIndex === 0;
    nextButton.disabled = currentShotIndex === scenes.length - 1;
  }

  function setCurrentShot(index) {
    currentShotIndex = clampShotIndex(index);
    updateShotUi();
  }

  function forceAnimationRestart() {
    void stage.offsetWidth;
  }

  function shotIndexForElapsed(elapsedMs) {
    let activeIndex = 0;
    continuousShotStartMs.forEach((startMs, index) => {
      if (elapsedMs >= startMs) {
        activeIndex = index;
      }
    });
    return activeIndex;
  }

  function trackContinuousProgress() {
    clearProgressTimer();
    progressTimer = window.setInterval(() => {
      const elapsedMs = hasGsap && activeTimeline
        ? activeTimeline.time() * 1000
        : window.performance.now() - continuousStartedAt;
      setCurrentShot(shotIndexForElapsed(elapsedMs));
    }, 160);
  }

  function select(scene, selector) {
    return Array.from(scene.querySelectorAll(selector));
  }

  function replayEmbeddedAsset(img) {
    if (!img) return;
    assetReplayNonce += 1;
    img.src = `${img.src.split("?")[0]}?replay=${assetReplayNonce}`;
  }

  function setLineDrawState(lines, length) {
    if (!hasGsap || !lines.length) return;
    window.gsap.set(lines, {
      opacity: 0,
      strokeDasharray: length,
      strokeDashoffset: length,
    });
  }

  function prepareGsapSceneState() {
    if (!hasGsap) return;
    const gsap = window.gsap;
    gsap.killTweensOf("*");
    gsap.set(scenes, { opacity: 0, pointerEvents: "none", x: 0, scale: 1, zIndex: 0 });

    scenes.forEach((scene) => {
      gsap.set(select(scene, ".opening-title, .building-visual"), { clearProps: "all" });
      gsap.set(select(scene, ".workflow-title, .pain-point, .workflow-package, .blocked-feedback, .blocked-x"), { opacity: 0 });
      gsap.set(select(scene, ".workflow-map"), { x: 0, y: 0, scale: 1, opacity: 1, transformOrigin: "left center" });
      gsap.set(select(scene, ".blocked-path"), { strokeDashoffset: 720 });
      gsap.set(select(scene, ".reframe-title, .legacy-strip, .agent-module, .loop-node, .product-claim"), { opacity: 0 });
      setLineDrawState(select(scene, ".loop-line"), 780);
      gsap.set(select(scene, ".inside-title, .expanded-agent, .expanded-agent-head, .capability-flow, .capability"), { clearProps: "all" });
      gsap.set(select(scene, ".inside-title, .design-input-package, .expanded-agent, .capability, .inside-output"), { opacity: 0 });
      gsap.set(select(scene, ".inside-line"), { opacity: 0, strokeDashoffset: 220 });
      gsap.set(select(scene, ".iteration-title, .iteration-agent-source, .iteration-feedback-source, .suggestion-panel, .suggestion-card, .user-selection, .next-design-option"), { opacity: 0 });
      gsap.set(select(scene, ".metric-card"), { opacity: 0, y: 8 });
      gsap.set(select(scene, ".iteration-line"), { opacity: 0, strokeDashoffset: 360 });
    });
  }

  function buildShotTimeline(index) {
    const gsap = window.gsap;
    const scene = scenes[index];
    const tl = gsap.timeline({ paused: true });

    if (scene.classList.contains("scene-opening")) {
      tl.set(select(scene, ".building-visual"), { opacity: 0, y: -105 })
        .set(select(scene, ".opening-title"), { opacity: 0, y: 16 })
        .to(select(scene, ".building-visual"), { opacity: 1, y: 0, duration: 0.95, ease: "power3.out" }, 0.18)
        .to(select(scene, ".opening-title"), { opacity: 1, y: 0, duration: 0.52, ease: "power2.out" }, 1.18);
      return tl;
    }

    if (scene.classList.contains("scene-workflow")) {
      const panEnd = -2195;
      tl.set(select(scene, ".workflow-map"), { x: 0, y: 0, scale: 1, opacity: 1, transformOrigin: "left center" })
        .to(select(scene, ".workflow-title"), { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }, 0.18)
        // reveal nodes (translateY) and connectors (scaleX) as the chain scrolls in
        .fromTo(select(scene, ".workflow-node"), { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.28, stagger: 0.19, ease: "power2.out" }, 0.32)
        .fromTo(select(scene, ".connector"), { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, transformOrigin: "left center", duration: 0.24, stagger: 0.19, ease: "sine.out" }, 0.44)
        // hold on the start (Design readable), pan across the long chain, hold on the end (Results readable)
        .to(select(scene, ".workflow-map"), { x: 0, duration: 0.9, ease: "none" }, 0.2)
        .to(select(scene, ".workflow-map"), { x: panEnd, duration: 3.9, ease: "none" }, 1.1)
        .to(select(scene, ".workflow-map"), { x: panEnd, duration: 0.7, ease: "none" }, 5.0)
        // pain points appear during the pan
        .to(select(scene, ".pain-one"), { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, 1.45)
        .to(select(scene, ".pain-two"), { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, 2.65)
        .to(select(scene, ".pain-three"), { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, 3.85)
        // fold: long chain compresses toward center as the packaged strip scales in (overlapping, no gap)
        .to(select(scene, ".workflow-map"), { opacity: 0, scale: 0.82, duration: 0.5, ease: "power2.inOut" }, 5.7)
        .fromTo(select(scene, ".workflow-package"), { opacity: 0, scale: 1.28, y: 0 }, { opacity: 1, scale: 1, duration: 0.62, ease: "power2.inOut" }, 5.75)
        // broken feedback loop: dashed arrow draws back to Design, then the X
        .to(select(scene, ".blocked-feedback"), { opacity: 1, duration: 0.2 }, 6.45)
        .to(select(scene, ".blocked-path"), { strokeDashoffset: 0, duration: 0.8, ease: "power1.inOut" }, 6.5)
        .to(select(scene, ".blocked-x"), { opacity: 1, duration: 0.25 }, 7.2);
      return tl;
    }

    if (scene.classList.contains("scene-reframe")) {
      const loopLines = select(scene, ".loop-line");
      const lsDesign = scene.querySelector(".ls-design");
      const lsResults = scene.querySelector(".ls-results");
      const blueBlock = scene.querySelector(".blue-block");
      const loopDesign = scene.querySelector(".loop-design");
      const loopResults = scene.querySelector(".loop-feedback");
      const agentEl = scene.querySelector(".agent-module");
      // reset any leftover transforms from a previous play so the measurement is clean
      gsap.set([lsDesign, lsResults, blueBlock], { x: 0, y: 0, scale: 1, opacity: 1 });
      gsap.set(agentEl, { clearProps: "transform" });
      // measure where each chain part should land (its matching loop slot)
      const centerDelta = (node, target) => {
        const a = node.getBoundingClientRect();
        const b = target.getBoundingClientRect();
        return {
          x: (b.left + b.width / 2) - (a.left + a.width / 2),
          y: (b.top + b.height / 2) - (a.top + a.height / 2),
        };
      };
      const dDesign = centerDelta(lsDesign, loopDesign);
      const dResults = centerDelta(lsResults, loopResults);
      const dBlue = centerDelta(blueBlock, agentEl);

      tl.set(loopLines, { opacity: 0, strokeDasharray: 760, strokeDashoffset: 760 })
        // 0. the SAME chain carried over from Shot 2 (identical look + position)
        .set(select(scene, ".legacy-strip"), { opacity: 1 })
        .set([lsDesign, lsResults, blueBlock], { opacity: 1, x: 0, y: 0, scale: 1 })
        .set(select(scene, ".legacy-strip i"), { opacity: 1 })
        // 1. on entry from Shot 2, the edge connectors drop away
        .to(select(scene, ".legacy-strip .ls-edge"), { opacity: 0, duration: 0.3, ease: "power1.in" }, 0.12)
        // 2. the chain splits to its loop slots: Design -> Design card, blue -> Agent, Results -> Results card
        .to(lsDesign, { x: dDesign.x, y: dDesign.y, scale: 1.7, opacity: 0, duration: 0.8, ease: "power2.inOut" }, 0.4)
        .to(lsResults, { x: dResults.x, y: dResults.y, scale: 1.7, opacity: 0, duration: 0.8, ease: "power2.inOut" }, 0.4)
        .to(blueBlock, { x: dBlue.x, y: dBlue.y, scale: 0.42, opacity: 0, duration: 0.8, ease: "power2.inOut" }, 0.4)
        // 3. the loop nodes + agent settle in where each part arrives
        .to(loopDesign, { opacity: 1, duration: 0.4, ease: "power1.out" }, 0.95)
        .to(loopResults, { opacity: 1, duration: 0.4, ease: "power1.out" }, 0.95)
        .fromTo(agentEl, { opacity: 0, scale: 0.86, y: 0 }, { opacity: 1, scale: 1, y: 0, duration: 0.55, ease: "power3.out" }, 1.0)
        // 4. title appears after the agent is established
        .to(select(scene, ".reframe-title"), { opacity: 1, y: 0, duration: 0.45, ease: "power1.out" }, 1.55)
        // 5. clockwise triangle loop arrows draw: Design -> Agent -> Results -> Design
        .to(select(scene, ".line-design-agent"), { opacity: 1, strokeDashoffset: 0, duration: 0.55, ease: "power1.inOut" }, 1.95)
        .to(select(scene, ".line-agent-feedback"), { opacity: 1, strokeDashoffset: 0, duration: 0.55, ease: "power1.inOut" }, 2.4)
        .to(select(scene, ".line-feedback-design"), { opacity: 1, strokeDashoffset: 0, duration: 0.6, ease: "power1.inOut" }, 2.9)
        // 6. closing claim
        .to(select(scene, ".product-claim"), { opacity: 1, y: 0, duration: 0.5, ease: "power1.out" }, 3.4);
      return tl;
    }

    if (scene.classList.contains("scene-inside")) {
      const ea = scene.querySelector(".expanded-agent");
      const head = scene.querySelector(".expanded-agent-head");
      const flow = scene.querySelector(".capability-flow");
      const capabilities = select(scene, ".capability");
      gsap.set([ea, head, flow].concat(capabilities), { clearProps: "all" });
      gsap.set(select(scene, ".inside-title"), { clearProps: "all", opacity: 0, y: 12 });
      gsap.set(ea, { opacity: 0, x: 0, y: 0, scale: 1 });
      gsap.set(capabilities, { opacity: 0, y: 10 });
      const finalW = ea.offsetWidth;   // natural full-frame size
      const finalH = ea.offsetHeight;
      // carry-over from Shot 3: the box must be a pixel-match of the Shot-3 "EnergyPlus
      // Agent" block (.agent-module), then GROW into the frame. We animate real width/height
      // (NOT transform scale) so the 25px label stays 25px and matches Shot 3 exactly.
      // In continuous mode reframe is built first, leaving .agent-module at its scale-0.8
      // from-state, so neutralise scale/y to read its true Shot-3-END box, then restore.
      const am = document.querySelector(".scene-reframe .agent-module");
      const savedScale = gsap.getProperty(am, "scaleX");
      const savedY = gsap.getProperty(am, "y");
      gsap.set(am, { scale: 1, y: 0 });
      const amR = am.getBoundingClientRect();
      gsap.set(am, { scale: savedScale, y: savedY });
      // size ea down to the block size, read where it lands, derive the offset onto the block
      gsap.set(ea, { width: amR.width, height: amR.height, x: 0, y: 0, scale: 1 });
      const small = ea.getBoundingClientRect();
      const startX = (amR.left + amR.width / 2) - (small.left + small.width / 2);
      const startY = (amR.top + amR.height / 2) - (small.top + small.height / 2);
      gsap.set(ea, { width: finalW, height: finalH, x: 0, y: 0, scale: 1 });

      tl.to(select(scene, ".inside-title"), { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }, 0.16)
        // become a pixel-match of Shot-3's blue block: same SIZE (real w/h), same blue skin,
        // real 25px white label, positioned exactly on the Shot-3 block
        .set(ea, { opacity: 1, width: amR.width, height: amR.height, x: startX, y: startY, scale: 1, gap: 0, backgroundColor: "#135d96", borderColor: "rgba(222,248,250,0.45)", boxShadow: "0 18px 40px rgba(24,78,94,0.2)" }, 0)
        // collapse the cards area so the lone label sits centred (single line) in the block
        .set(flow, { height: 0, overflow: "hidden" }, 0)
        .set(head, { backgroundColor: "rgba(255,255,255,0)", borderColor: "rgba(255,255,255,0)", color: "#ffffff", fontSize: 25, whiteSpace: "nowrap" }, 0)
        // hold briefly, then the SAME block GROWS (real w/h) into the full frame — label
        // stays a real 25px and, being top-anchored, floats from block-centre to the header row
        .to(ea, { width: finalW, height: finalH, x: 0, y: 0, duration: 0.96, ease: "power3.inOut" }, 0.52)
        // at full size, morph the blue block INTO the white capability frame
        .to(ea, { backgroundColor: "rgba(255,255,255,0.98)", borderColor: "rgba(43,133,136,0.45)", boxShadow: "0 18px 40px rgba(31,48,54,0.085)", gap: 12, duration: 0.5, ease: "sine.inOut" }, 1.28)
        .to(head, { fontSize: 19, backgroundColor: "#f2f8f8", borderColor: "#cfe2e3", color: "#24434a", duration: 0.5, ease: "sine.inOut" }, 1.28)
        // re-open the cards area (label is now the header bar), then reveal the four steps
        .set(flow, { clearProps: "height,overflow" }, 1.72)
        .set(head, { whiteSpace: "normal" }, 1.72)
        .to(capabilities, { opacity: 1, y: 0, duration: 0.38, stagger: 0.2, ease: "power2.out" }, 1.86);
      return tl;
    }

    if (scene.classList.contains("scene-contribution")) {
      // Carry the two drawing-to-model capabilities from Shot 4 into the core flow.
      // Simulation Model Pipeline is revealed later, downstream of the BEM output.
      const insideCaps = Array.from(document.querySelectorAll(".scene-inside .capability.cap-mine"));
      const coreCaps = select(scene, ".contrib-pipeline .contrib-cap");
      const carry = coreCaps.map((card, i) => {
        const src = insideCaps[i];
        if (!src) return { x: 0, y: 0 };
        const s = src.getBoundingClientRect();
        const c = card.getBoundingClientRect();
        return { x: (s.left + s.width / 2) - (c.left + c.width / 2), y: (s.top + s.height / 2) - (c.top + c.height / 2) };
      });

      tl.fromTo(select(scene, ".contribution-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.44, ease: "power2.out" }, 0.18);
      coreCaps.forEach((card, i) => {
        tl.fromTo(card, { opacity: 0, x: carry[i].x, y: carry[i].y, scale: 0.94 }, { opacity: 1, x: 0, y: 0, scale: 1, duration: 0.62, ease: i === 0 ? "power3.out" : "power2.out" }, 0.48 + i * 0.14);
      });
      tl
        // then the multimodal inputs appear on the left as my input boundary
        .fromTo(select(scene, ".contrib-inputs"), { opacity: 0, x: -28 }, { opacity: 1, x: 0, duration: 0.48, ease: "power3.out" }, 1.24)
        .fromTo(select(scene, ".cin"), { opacity: 0, x: -5 }, { opacity: 1, x: 0, duration: 0.24, stagger: 0.07, ease: "power1.out" }, 1.48)
        .fromTo(select(scene, ".contrib-arrow-in"), { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.26, ease: "power2.out" }, 1.8)
        .fromTo(select(scene, ".contrib-arrow-out"), { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.26, ease: "power2.out" }, 2.02)
        // re-trigger the BIM/BEM figure SVGs so their one-shot build animation plays
        // in sync with this shot (an <img> SVG cannot be controlled, so reload it)
        .add(() => {
          scene.querySelectorAll(".out-figure img").forEach((img) => {
            replayEmbeddedAsset(img);
          });
        }, 2.08)
        .fromTo(select(scene, ".out-bim"), { opacity: 0, x: 24 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, 2.2)
        .fromTo(select(scene, ".out-bem"), { opacity: 0, x: 24 }, { opacity: 1, x: 0, duration: 0.45, ease: "power2.out" }, 2.52)
        // The BEM model is the input to the downstream simulation-model pipeline.
        .fromTo(select(scene, ".contrib-arrow-bem"), { opacity: 0, scale: 0.72 }, { opacity: 1, scale: 1, duration: 0.26, ease: "power2.out" }, 3.02)
        .fromTo(select(scene, ".contrib-simulation"), { opacity: 0, x: -18 }, { opacity: 1, x: 0, duration: 0.52, ease: "power3.out" }, 3.25);
      return tl;
    }

    if (scene.classList.contains("scene-evidence")) {
      tl.fromTo(select(scene, ".evidence-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.44, ease: "power2.out" }, 0.18)
        // the four modality cards appear (real reference images)
        .fromTo(select(scene, ".evidence-card"), { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.42, stagger: 0.12, ease: "power3.out" }, 0.55)
        // then they flow straight down into the pipeline
        .fromTo(select(scene, ".ev-down-arrow"), { opacity: 0, y: -6 }, { opacity: 1, y: 0, duration: 0.34, ease: "sine.out" }, 1.58)
        .fromTo(select(scene, ".evidence-next-node"), { opacity: 0, y: -8, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.46, ease: "power3.out" }, 1.9);
      return tl;
    }

    if (scene.classList.contains("scene-pipeline")) {
      // all connectors start undrawn AND invisible (opacity 0 so marker-end arrowheads
      // don't show before their line is drawn); each fades in as it draws.
      gsap.set(select(scene, ".pl"), { strokeDasharray: 280, strokeDashoffset: 280, opacity: 0 });

      tl.fromTo(select(scene, ".pipeline-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.44, ease: "power2.out" }, 0.18)
        // 1. shared chain: Design Evidence -> Drawing Understanding -> Vector Redraw
        .fromTo(select(scene, ".g-share"), { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.34, stagger: 0.2, ease: "power2.out" }, 0.62)
        .to(select(scene, ".pl-share"), { strokeDashoffset: 0, opacity: 1, duration: 0.32, stagger: 0.2, ease: "sine.out" }, 0.9)
        // 2. fork: Vector Redraw splits into BIM + BEM branches
        .to(select(scene, ".pl-fork"), { strokeDashoffset: 0, opacity: 1, duration: 0.46, ease: "power2.out" }, 1.72)
        .fromTo(select(scene, ".tag-bim, .tag-bem"), { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.32, ease: "power2.out" }, 1.9)
        .fromTo(select(scene, ".g-bim.pnode:not(.pout), .g-bem.pnode:not(.pout)"), { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.34, stagger: 0.14, ease: "power3.out" }, 2.18)
        // 3. branch internal steps (error correction -> 3D recon / thermal topology -> zoning)
        .to(select(scene, ".pl-branch"), { strokeDashoffset: 0, opacity: 1, duration: 0.32, stagger: 0.1, ease: "sine.out" }, 2.88)
        // 4. merge: both branches converge into the 9 domain agents
        .to(select(scene, ".pl-merge"), { strokeDashoffset: 0, opacity: 1, duration: 0.48, ease: "power2.out" }, 3.32)
        .fromTo(select(scene, ".p-agents"), { opacity: 0, scale: 0.94 }, { opacity: 1, scale: 1, duration: 0.44, ease: "power3.out" }, 3.72)
        // 5. fork again: the agents produce the two model outputs
        .to(select(scene, ".pl-out"), { strokeDashoffset: 0, opacity: 1, duration: 0.44, ease: "power2.out", stagger: 0.08 }, 4.42)
        .fromTo(select(scene, ".pout"), { opacity: 0, scale: 0.94 }, { opacity: 1, scale: 1, duration: 0.42, stagger: 0.12, ease: "power3.out" }, 4.72);
      return tl;
    }

    if (scene.classList.contains("scene-bim")) {
      // BIM and BEM use the same short, fixed card-to-card reveal cadence.
      // Their embedded SVG animations continue independently after each card appears.
      const cards = select(scene, ".s4card");
      const arrows = select(scene, ".s4arrow");
      const techs = select(scene, ".s4tech");
      const svgs = select(scene, ".plansvg"); // [0]=redraw, [1]=corrected, [2]=3d-reconstruction
      const REVEAL = 0.4, STEP_INTERVAL = 1.05, LEAD = 0.14;
      const t1 = 0.6;
      const t2 = t1 + STEP_INTERVAL;
      const t3 = t2 + STEP_INTERVAL;
      const t4 = t3 + STEP_INTERVAL;
      const reveal = [t1, t2, t3, t4];
      // retrigger BEFORE the card reveals (while opacity 0) so the fade-in shows the SVG
      // playing from frame 0 — not its already-finished end frame.
      const retrigger = (img, t) => {
        if (!img) return;
        tl.add(() => { replayEmbeddedAsset(img); }, Math.max(0, t));
      };

      tl.fromTo(select(scene, ".path-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" }, 0.18);
      cards.forEach((card, i) => {
        tl.fromTo(card, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: REVEAL, ease: i % 2 === 0 ? "power3.out" : "power2.out" }, reveal[i]);
      });
      techs.forEach((tech, i) => {
        tl.fromTo(tech, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.26, ease: "power1.out" }, reveal[i] + 0.2);
      });
      // Each connector uses the same short lead-in before its following card.
      arrows.forEach((a, i) => {
        tl.fromTo(a, { opacity: 0, scale: 0.82 }, { opacity: 1, scale: 1, duration: 0.22, ease: "sine.out" }, reveal[i + 1] - 0.2);
      });
      retrigger(svgs[0], t2 - LEAD);
      retrigger(svgs[1], t3 - LEAD);
      retrigger(svgs[2], t4 - LEAD);
      // Keep playback active until the 5.5s correction tour has visibly landed.
      tl.add(() => {}, t3 + 5.75);
      return tl;
    }

    if (scene.classList.contains("scene-bem")) {
      // Match BIM's short, fixed card-to-card reveal cadence.
      const cards = select(scene, ".s4card");
      const arrows = select(scene, ".s4arrow");
      const techs = select(scene, ".s4tech");
      const svgs = select(scene, ".plansvg"); // [0]=redraw, [1]=thermal-zoning, [2]=zone-construction
      const REVEAL = 0.4, STEP_INTERVAL = 1.05, LEAD = 0.14;
      const t1 = 0.6;
      const t2 = t1 + STEP_INTERVAL;
      const t3 = t2 + STEP_INTERVAL;
      const t4 = t3 + STEP_INTERVAL;
      const reveal = [t1, t2, t3, t4];
      // retrigger BEFORE the card reveals (while opacity 0) so the fade-in shows the SVG
      // playing from frame 0 — not its already-finished end frame.
      const retrigger = (img, t) => {
        if (!img) return;
        tl.add(() => { replayEmbeddedAsset(img); }, Math.max(0, t));
      };

      tl.fromTo(select(scene, ".path-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" }, 0.18);
      cards.forEach((card, i) => {
        tl.fromTo(card, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: REVEAL, ease: i % 2 === 0 ? "power3.out" : "power2.out" }, reveal[i]);
      });
      techs.forEach((tech, i) => {
        tl.fromTo(tech, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.26, ease: "power1.out" }, reveal[i] + 0.2);
      });
      // Each connector uses the same short lead-in before its following card.
      arrows.forEach((a, i) => {
        tl.fromTo(a, { opacity: 0, scale: 0.82 }, { opacity: 1, scale: 1, duration: 0.22, ease: "sine.out" }, reveal[i + 1] - 0.2);
      });
      retrigger(svgs[0], t2 - LEAD);
      retrigger(svgs[1], t3 - LEAD);
      retrigger(svgs[2], t4 - LEAD);
      tl.add(() => {}, t3 + 3.4);
      return tl;
    }

    if (scene.classList.contains("scene-verifiable")) {
      const reviewStart = 1.42;
      const reviewStep = 0.5;
      const ragStart = reviewStart + (reviewStep * 5);
      const userStart = ragStart + reviewStep;
      gsap.set(select(scene, ".vl-review, .vl-rag, .vl-interactive"), {
        strokeDasharray: 180,
        strokeDashoffset: 180,
        opacity: 0,
      });
      tl.fromTo(select(scene, ".verification-title"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.44, ease: "power2.out" }, 0.18)
        // Reuse Shot 7's completed pipeline as the stable context.
        .fromTo(select(scene, ".verification-core, .vl-core"), { opacity: 0 }, { opacity: 1, duration: 0.52, ease: "sine.out" }, 0.58)
        // Then expose the five reviewable intermediate artifacts.
        .to(select(scene, ".vl-review"), { strokeDashoffset: 0, opacity: 1, duration: 0.34, stagger: reviewStep, ease: "sine.out" }, reviewStart - 0.12)
        .fromTo(select(scene, ".verification-review"), { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.38, stagger: reviewStep, ease: "power3.out" }, reviewStart)
        // Add knowledge grounding above the unchanged Shot 7 agents, then user confirmation below.
        .fromTo(select(scene, ".verification-rag"), { opacity: 0, y: -8 }, { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" }, ragStart)
        .to(select(scene, ".vl-rag"), { strokeDashoffset: 0, opacity: 1, duration: 0.34, ease: "sine.out" }, ragStart + 0.3)
        .fromTo(select(scene, ".verification-user"), { opacity: 0, scale: 0.92 }, { opacity: 1, scale: 1, duration: 0.44, ease: "power3.out" }, userStart)
        .to(select(scene, ".vl-interactive"), { strokeDashoffset: 0, opacity: 1, duration: 0.48, ease: "power2.out" }, userStart + 0.32);
      return tl;
    }

    if (scene.classList.contains("scene-iteration")) {
      tl.to(select(scene, ".iteration-title"), { opacity: 1, y: 0, duration: 0.5 }, 0)
        .to(select(scene, ".iteration-agent-source"), { opacity: 1, y: 0, duration: 0.45 }, 0.25)
        .to(select(scene, ".line-agent-feedback"), { opacity: 1, strokeDashoffset: 0, duration: 0.45 }, 0.65)
        .to(select(scene, ".iteration-feedback-source"), { opacity: 1, y: 0, duration: 0.5 }, 1.0)
        .to(select(scene, ".metric-card"), { opacity: 1, y: 0, duration: 0.25, stagger: 0.12 }, 1.45)
        .to(select(scene, ".line-feedback-cards"), { opacity: 1, strokeDashoffset: 0, duration: 0.45 }, 1.85)
        .to(select(scene, ".suggestion-panel"), { opacity: 1, y: 0, duration: 0.4 }, 2.15)
        .to(select(scene, ".suggestion-card"), { opacity: 1, x: 0, duration: 0.25, stagger: 0.16 }, 2.3)
        .to(select(scene, ".line-cards-selection"), { opacity: 1, strokeDashoffset: 0, duration: 0.5 }, 3.55)
        .to(select(scene, ".user-selection"), { opacity: 1, y: 0, duration: 0.4 }, 3.9)
        .to(select(scene, ".line-selection-agent"), { opacity: 1, strokeDashoffset: 0, duration: 0.55 }, 4.45)
        .to(select(scene, ".line-agent-option"), { opacity: 1, strokeDashoffset: 0, duration: 0.5 }, 5.15)
        .to(select(scene, ".next-design-option"), { opacity: 1, y: 0, duration: 0.4 }, 5.5);
      return tl;
    }

    const visibleChildren = Array.from(scene.children).filter((child) => !child.matches("svg"));
    tl.set(select(scene, "*"), { opacity: 1, clearProps: "transform" }, 0)
      .fromTo(visibleChildren, { opacity: 0, y: 10 }, {
        opacity: 1,
        y: 0,
        duration: 0.45,
        stagger: 0.12,
        ease: "power1.out",
      }, 0.1);
    return tl;
  }

  function showOnlyScene(index) {
    if (!hasGsap) return;
    window.gsap.set(scenes, { opacity: 0, pointerEvents: "none", x: 0, scale: 1, zIndex: 0 });
    window.gsap.set(scenes[index], { opacity: 1, pointerEvents: "auto", x: 0, scale: 1, zIndex: 1 });
  }

  function playContinuousGsap() {
    const gsap = window.gsap;
    prepareGsapSceneState();
    activeTimeline = gsap.timeline({
      paused: true,
      onUpdate: () => setCurrentShot(shotIndexForElapsed(activeTimeline.time() * 1000)),
      onComplete: () => {
        clearProgressTimer();
        setCurrentShot(scenes.length - 1);
        body.classList.add("is-complete");
        playButton.setAttribute("aria-pressed", "false");
      },
    });

    activeTimeline.set(scenes, { opacity: 0, pointerEvents: "none", x: 0, scale: 1, zIndex: 0 }, 0);
    scenes.forEach((scene, index) => {
      const start = continuousShotStartMs[index] / 1000;
      const nextStart = index < scenes.length - 1
        ? continuousShotStartMs[index + 1] / 1000
        : totalDurationMs / 1000;
      const incoming = transitionProfiles[index];
      if (index === 0) {
        activeTimeline.set(scene, { opacity: 1, pointerEvents: "auto", x: 0, scale: 1, zIndex: 1 }, 0);
      } else {
        const transitionStart = start - incoming.duration / 2;
        activeTimeline.set(scene, {
          opacity: 0,
          pointerEvents: "auto",
          x: incoming.x,
          scale: incoming.scale,
          zIndex: 2,
        }, transitionStart);
        activeTimeline.to(scene, {
          opacity: 1,
          x: 0,
          scale: 1,
          duration: incoming.duration,
          ease: "power2.inOut",
        }, transitionStart);
        activeTimeline.set(scene, { zIndex: 1 }, transitionStart + incoming.duration);
      }
      const shotTl = buildShotTimeline(index);
      activeTimeline.add(shotTl, start + (index === 0 ? 0 : 0.08));
      // buildShotTimeline() returns a paused timeline (so slide mode can play it on
      // demand); when nested in the continuous master it must be un-paused or the master
      // won't drive its inner reveals (scenes would show empty).
      shotTl.paused(false);
      if (index < scenes.length - 1) {
        const outgoing = transitionProfiles[index + 1];
        const transitionStart = nextStart - outgoing.duration / 2;
        activeTimeline.to(scene, {
          opacity: 0,
          x: outgoing.x ? -Math.min(10, outgoing.x / 2) : 0,
          scale: outgoing.scale < 1 ? 1.004 : 1,
          duration: outgoing.duration,
          ease: "sine.inOut",
        }, transitionStart);
        activeTimeline.set(scene, { pointerEvents: "none", zIndex: 0 }, transitionStart + outgoing.duration);
      }
    });
    activeTimeline.set(scenes[scenes.length - 1], {
      opacity: 1,
      pointerEvents: "auto",
      x: 0,
      scale: 1,
      zIndex: 1,
    }, totalDurationMs / 1000 - 0.01);
    activeTimeline.duration(totalDurationMs / 1000);
    activeTimeline.play(0);
  }

  function playSlideGsap(index) {
    prepareGsapSceneState();
    showOnlyScene(index);
    activeTimeline = buildShotTimeline(index);
    activeTimeline.eventCallback("onComplete", () => {
      body.classList.add("is-shot-complete");
      playButton.setAttribute("aria-pressed", "false");
    });
    activeTimeline.play(0);
    completionTimer = window.setTimeout(() => {
      if (!body.classList.contains("is-shot-complete")) {
        body.classList.add("is-shot-complete");
        playButton.setAttribute("aria-pressed", "false");
      }
    }, slideDurationsMs[index] + 150);
  }

  function playContinuousFallback() {
    setCurrentShot(0);
    forceAnimationRestart();
    continuousStartedAt = window.performance.now();
    trackContinuousProgress();
    completionTimer = window.setTimeout(() => {
      clearProgressTimer();
      setCurrentShot(scenes.length - 1);
      body.classList.add("is-complete");
      playButton.setAttribute("aria-pressed", "false");
    }, totalDurationMs + 250);
  }

  function playSlideFallback(index) {
    setCurrentShot(index);
    forceAnimationRestart();
    completionTimer = window.setTimeout(() => {
      body.classList.add("is-shot-complete");
      playButton.setAttribute("aria-pressed", "false");
    }, slideDurationsMs[currentShotIndex] + 150);
  }

  function playContinuous() {
    setMode("continuous");
    resetPlaybackState();
    body.classList.add("is-running");
    playButton.setAttribute("aria-pressed", "true");
    if (hasGsap) {
      playContinuousGsap();
    } else {
      playContinuousFallback();
    }
  }

  function playSlide(index) {
    setMode("slide");
    resetPlaybackState();
    setCurrentShot(index);
    body.classList.add("is-running");
    playButton.setAttribute("aria-pressed", "true");
    if (hasGsap) {
      playSlideGsap(currentShotIndex);
    } else {
      playSlideFallback(currentShotIndex);
    }
  }

  function showFinalShot(index) {
    setMode("slide");
    resetPlaybackState();
    setCurrentShot(index);
    if (hasGsap) {
      prepareGsapSceneState();
      showOnlyScene(currentShotIndex);
      activeTimeline = buildShotTimeline(currentShotIndex);
      activeTimeline.progress(1, true).pause();
    } else {
      forceAnimationRestart();
    }
    body.classList.add("is-final-preview", "is-shot-complete");
    playButton.setAttribute("aria-pressed", "false");
  }

  function playCurrentMode() {
    if (mode === "continuous") {
      if (!body.classList.contains("is-running") || body.classList.contains("is-complete")) {
        playContinuous();
      }
      return;
    }
    playSlide(currentShotIndex);
  }

  continuousModeButton.addEventListener("click", playContinuous);
  slideModeButton.addEventListener("click", () => playSlide(currentShotIndex));
  playButton.addEventListener("click", playCurrentMode);
  restartButton.addEventListener("click", () => {
    if (mode === "continuous") {
      playContinuous();
    } else {
      playSlide(0);
    }
  });

  previousButton.addEventListener("click", () => {
    if (mode === "slide" && currentShotIndex > 0) {
      playSlide(currentShotIndex - 1);
    }
  });

  nextButton.addEventListener("click", () => {
    if (mode === "slide" && currentShotIndex < scenes.length - 1) {
      playSlide(currentShotIndex + 1);
    }
  });

  shotNavButtons.forEach((button) => {
    button.addEventListener("click", () => {
      playSlide(Number(button.dataset.shotTarget));
    });
  });

  finalShotNavButtons.forEach((button) => {
    button.addEventListener("click", () => {
      showFinalShot(Number(button.dataset.shotFinalTarget));
    });
  });

  window.addEventListener("load", playContinuous);
  updateShotUi();
})();
