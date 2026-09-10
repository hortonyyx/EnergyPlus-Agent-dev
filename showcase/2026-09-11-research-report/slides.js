(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const slides = [...document.querySelectorAll('.slide')];
  const stage = $('#stage');
  const overview = $('#overview');
  const dialog = $('#demo-dialog');
  const frame = $('#demo-frame');
  const variants = $('#demo-variants');
  let current = 0;
  let lastFocus = null;
  let activeDemo = null;
  const models = {
    sm25: { title: 'sm25 · 图纸还原 / Reconstruction', src: 'demos/sm25/sm25_showcase.html', label: '轻量 BIM / Lightweight BIM', family: 'sm25' },
    'voima-input': { title: 'Voimatalo · 真实贴图体量 / Textured mesh', src: 'demos/textured-mass/input_viewer.html', label: '原始体量 / Source mesh', family: 'voima' },
    'voima-envelope': { title: 'Voimatalo · 合并空间 / Merged spaces', src: 'demos/textured-mass/envelope.html', label: '外壳版 / Envelope', family: 'voima' },
    voima: { title: 'Voimatalo · 内部推理 / Inferred interiors', src: 'demos/textured-mass/index.html', label: '内部推理 / Inferred interiors', family: 'voima' }
  };
  function fit() {
    stage.style.setProperty('--scale', Math.min(window.innerWidth / 1600, window.innerHeight / 900));
  }
  function goTo(index, updateHash = true) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach((slide, i) => {
      slide.hidden = i !== current;
      slide.classList.toggle('active', i === current);
    });
    $('#prev').disabled = current === 0;
    $('#next').disabled = current === slides.length - 1;
    $('#page-current').textContent = String(current + 1).padStart(2, '0');
    $('#progress').style.width = `${(current + 1) / slides.length * 100}%`;
    $('#announcement').textContent = `第 ${current + 1} 页，共 7 页。${slides[current].dataset.title}`;
    document.querySelectorAll('#overview-items button').forEach((button, i) => {
      if (i === current) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    if (updateHash && location.hash !== `#${current + 1}`) {
      // Works on both file:// and a static HTTP server.
      history.replaceState(null, '', `#${current + 1}`);
    }
  }
  function toggleOverview(show = overview.hidden) {
    overview.hidden = !show;
    $('#slides').inert = show;
    $('.deck-footer').inert = show;
    if (show) $('#overview-items').children[current].focus();
    else $('#page-toggle').focus();
  }
  function openDemo(key, rememberFocus = true) {
    const model = models[key];
    if (!model) return;
    if (rememberFocus && dialog.hidden) lastFocus = document.activeElement;
    activeDemo = key;
    dialog.hidden = false;
    stage.inert = true;
    $('#demo-title').textContent = model.title;
    $('#demo-loading').hidden = false;
    variants.replaceChildren();
    if (model.family === 'voima') {
      ['voima-input', 'voima-envelope', 'voima'].forEach((item) => {
        const button = document.createElement('button');
        button.textContent = models[item].label;
        button.setAttribute('aria-pressed', String(item === key));
        button.addEventListener('click', () => openDemo(item, false));
        variants.append(button);
      });
    }
    frame.title = model.title;
    frame.src = model.src;
    $('#demo-close').focus();
  }
  function closeDemo() {
    if (dialog.hidden) return;
    dialog.hidden = true;
    stage.inert = false;
    activeDemo = null;
    frame.removeAttribute('src');
    if (lastFocus && !lastFocus.closest('[hidden]')) lastFocus.focus();
  }
  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (_) {
      $('#announcement').textContent = '浏览器未允许全屏，请使用浏览器的全屏命令。 Fullscreen is unavailable; use the browser fullscreen command.';
    }
  }
  function trapTab(event, container) {
    if (event.key !== 'Tab') return;
    const focusable = [...container.querySelectorAll('button:not(:disabled), iframe, a[href]')].filter(el => !el.hidden);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  function handleKey(event) {
    if (!dialog.hidden) {
      if (event.key === 'Escape') { event.preventDefault(); closeDemo(); }
      else trapTab(event, dialog);
      return;
    }
    if (!overview.hidden) {
      if (event.key === 'Escape' || event.key.toLowerCase() === 'o') { event.preventDefault(); toggleOverview(false); }
      else trapTab(event, overview);
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey || /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) return;
    // Let Space/Enter activate focused buttons instead of navigating twice.
    if ([' ', 'Enter'].includes(event.key) && event.target.closest('button, a')) return;
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(event.key)) { event.preventDefault(); goTo(current + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) { event.preventDefault(); goTo(current - 1); }
    else if (event.key === 'Home') { event.preventDefault(); goTo(0); }
    else if (event.key === 'End') { event.preventDefault(); goTo(6); }
    else if (/^[1-7]$/.test(event.key)) goTo(Number(event.key) - 1);
    else if (event.key.toLowerCase() === 'f') toggleFullscreen();
    else if (event.key.toLowerCase() === 'o') toggleOverview();
  }
  frame.addEventListener('load', () => {
    if (!activeDemo) return;
    $('#demo-loading').hidden = true;
    // Same-origin pages can return with Esc even when the model has keyboard focus.
    // file:// isolation varies by browser; the always-visible Back button also works.
    try { frame.contentWindow.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); closeDemo(); }
    }); } catch (_) { /* Separate file origins retain the visible return control. */ }
  });
  slides.forEach((slide, i) => {
    const button = document.createElement('button');
    const number = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    button.append(number, document.createTextNode(slide.dataset.title));
    button.addEventListener('click', () => { goTo(i); toggleOverview(false); });
    $('#overview-items').append(button);
  });
  document.querySelectorAll('[data-demo]').forEach(button => button.addEventListener('click', () => openDemo(button.dataset.demo)));
  $('#prev').addEventListener('click', () => goTo(current - 1));
  $('#next').addEventListener('click', () => goTo(current + 1));
  $('#page-toggle').addEventListener('click', () => toggleOverview());
  $('#overview-close').addEventListener('click', () => toggleOverview(false));
  $('#demo-close').addEventListener('click', closeDemo);
  $('#fullscreen').addEventListener('click', toggleFullscreen);
  document.addEventListener('keydown', handleKey);
  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', () => {
    closeDemo();
    if (!overview.hidden) toggleOverview(false);
    goTo((Number(location.hash.slice(1)) || 1) - 1, false);
  });
  fit();
  goTo((Number(location.hash.slice(1)) || 1) - 1);
})();
