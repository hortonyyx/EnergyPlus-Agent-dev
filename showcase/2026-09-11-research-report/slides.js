(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const slides = [...document.querySelectorAll('.slide')];
  const frames = [...document.querySelectorAll('iframe[data-src]')];
  const stage = $('#stage');
  const overview = $('#overview');
  let current = 0;

  function fit() {
    stage.style.setProperty('--scale', Math.min(innerWidth / 1600, innerHeight / 900));
  }
  function syncModels() {
    frames.forEach(frame => {
      const visible = frame.closest('.slide') === slides[current] && overview.hidden;
      if (visible && !frame.hasAttribute('src')) frame.src = frame.dataset.src;
      else if (!visible && frame.hasAttribute('src')) {
        frame.removeAttribute('src');
        frame.parentElement.classList.remove('is-loaded');
      }
    });
  }
  function goTo(index, updateHash = true) {
    current = Math.max(0, Math.min(6, Number.isFinite(index) ? Math.floor(index) : 0));
    if (frames.includes(document.activeElement)) document.activeElement.blur();
    slides.forEach((slide, i) => {
      slide.hidden = i !== current;
      slide.classList.toggle('active', i === current);
    });
    $('#prev').disabled = current === 0;
    $('#next').disabled = current === 6;
    $('#page-current').textContent = String(current + 1).padStart(2, '0');
    $('#progress').style.width = `${(current + 1) / 7 * 100}%`;
    $('#announcement').textContent = `第 ${current + 1} 页，共 7 页。${slides[current].dataset.title}`;
    [...$('#overview-items').children].forEach((button, i) => {
      if (i === current) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    if (updateHash && location.hash !== `#${current + 1}`) history.replaceState(null, '', `#${current + 1}`);
    syncModels();
  }
  function toggleOverview(show = overview.hidden) {
    overview.hidden = !show;
    $('#slides').inert = show;
    $('.deck-footer').inert = show;
    syncModels();
    if (show) $('#overview-items').children[current].focus();
    else $('#page-toggle').focus();
  }
  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (_) {
      $('#announcement').textContent = '请使用浏览器的全屏命令。 Use the browser fullscreen command.';
    }
  }
  function navigateKey(key) {
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(key)) goTo(current + 1);
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(key)) goTo(current - 1);
    else if (key === 'Home') goTo(0);
    else if (key === 'End') goTo(6);
    else if (/^[1-7]$/.test(key)) goTo(Number(key) - 1);
    else if (key.toLowerCase() === 'f') toggleFullscreen();
    else if (key.toLowerCase() === 'o') toggleOverview();
    else return false;
    return true;
  }
  function handleKey(event) {
    if (!overview.hidden) {
      if (event.key === 'Escape' || event.key.toLowerCase() === 'o') { event.preventDefault(); toggleOverview(false); }
      if (event.key === 'Tab') {
        const buttons = [...overview.querySelectorAll('button')];
        if (event.shiftKey && document.activeElement === buttons[0]) { event.preventDefault(); buttons.at(-1).focus(); }
        else if (!event.shiftKey && document.activeElement === buttons.at(-1)) { event.preventDefault(); buttons[0].focus(); }
      }
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey || /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) return;
    if ([' ', 'Enter'].includes(event.key) && event.target.closest('button, a')) return;
    if (navigateKey(event.key)) event.preventDefault();
  }
  // Explicit relays work even when file:// child pages have isolated origins.
  // Only a currently displayed child frame may send a presentation command.
  window.addEventListener('message', event => {
    const sender = frames.find(frame => frame.hasAttribute('src') && frame.contentWindow === event.source && frame.closest('.slide') === slides[current]);
    if (!sender || !overview.hidden || !event.data || event.data.type !== 'bim-slide-key') return;
    if (typeof event.data.key === 'string' && ['ArrowLeft','ArrowRight','PageUp','PageDown','Home','End','f','F','o','O'].includes(event.data.key)) navigateKey(event.data.key);
  });
  frames.forEach(frame => frame.addEventListener('load', () => {
    if (frame.hasAttribute('src')) frame.parentElement.classList.add('is-loaded');
  }));
  slides.forEach((slide, i) => {
    const button = document.createElement('button');
    const number = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    button.append(number, document.createTextNode(slide.dataset.title));
    button.addEventListener('click', () => { goTo(i); toggleOverview(false); });
    $('#overview-items').append(button);
  });
  $('#prev').addEventListener('click', () => goTo(current - 1));
  $('#next').addEventListener('click', () => goTo(current + 1));
  $('#page-toggle').addEventListener('click', () => toggleOverview());
  $('#overview-close').addEventListener('click', () => toggleOverview(false));
  $('#fullscreen').addEventListener('click', toggleFullscreen);
  document.addEventListener('keydown', handleKey);
  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', () => {
    if (!overview.hidden) toggleOverview(false);
    goTo((Number(location.hash.slice(1)) || 1) - 1, false);
  });
  fit();
  goTo((Number(location.hash.slice(1)) || 1) - 1);
})();
