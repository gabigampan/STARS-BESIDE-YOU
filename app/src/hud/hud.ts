// Mission Control motion: three of the four transitions (the fourth, the pair link, is drawn by
// src/modules/beams.ts). Only opacity and transform are animated, nothing runs while idle, and
// nothing runs when the user asks for reduced motion.
//  1. Boot, once per page load: body.hud-boot for at most 1.3 s (the CSS staggers the panels).
//  2. Choosing a mission: body.hud-scan for 480 ms (a scan line across both globe viewports and a
//     short fade of the panel content).
//  3. (beams.ts) The reticles and the beam between the Earth site and its twin.
//  4. The pair card's three scores count up. The figure's own text is never changed: while
//     counting it is drawn transparent and the counting value is shown by a ::after whose content
//     has an empty alternative text, so screen readers and tests read the true figure throughout.

const BOOT_MS = 1300;
const SCAN_MS = 480;
const COUNT_MS = 500;

export function setupHud(reduced: () => boolean): void {
  const body = document.body;
  const still = () => reduced() || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  // 1. boot
  if (!still()) {
    body.classList.add('hud-boot');
    performance.mark?.('hud-boot-start');
    window.setTimeout(() => {
      body.classList.remove('hud-boot');
      performance.mark?.('hud-boot-end');
    }, BOOT_MS);
  }

  // 2. choosing a mission: the step goes from the start screen to the ranking
  let lastStep = body.dataset.step ?? '';
  let scanTimer = 0;
  new MutationObserver(() => {
    const step = body.dataset.step ?? '';
    if (step === lastStep) return;
    const from = lastStep;
    lastStep = step;
    if (step !== 'pick' || from !== 'choose' || still()) return;
    body.classList.remove('hud-scan');
    void body.offsetWidth; // restart the one-shot animation if a second mission follows quickly
    body.classList.add('hud-scan');
    window.clearTimeout(scanTimer);
    scanTimer = window.setTimeout(() => body.classList.remove('hud-scan'), SCAN_MS + 40);
  }).observe(body, { attributes: true, attributeFilter: ['data-step'] });

  // 4. the scores count up when a pair card opens
  const detail = document.getElementById('detail-panel');
  if (detail) {
    new MutationObserver((records) => {
      if (still()) return;
      for (const r of records) {
        for (const n of r.addedNodes) {
          if (!(n instanceof HTMLElement)) continue;
          const figs = n.matches('.figs dd') ? [n] : [...n.querySelectorAll<HTMLElement>('.figs dd')];
          for (const dd of figs) countUp(dd);
        }
      }
    }).observe(detail, { childList: true, subtree: true });
  }
}

function countUp(dd: HTMLElement): void {
  const text = dd.textContent ?? '';
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(text.trim());
  if (!m) return; // "n/a" and the like are shown as they are
  const target = Number(text.trim());
  const decimals = m[3]?.length ?? 0;
  if (!Number.isFinite(target)) return;
  const t0 = performance.now();
  dd.classList.add('hud-counting');
  const frame = (now: number) => {
    if (!dd.isConnected) return;
    const p = Math.min(1, (now - t0) / COUNT_MS);
    const e = 1 - Math.pow(1 - p, 3); // ease-out
    if (p < 1) {
      dd.dataset.count = (target * e).toFixed(decimals);
      requestAnimationFrame(frame);
    } else {
      // the end: the element shows its own, untouched text again
      dd.classList.remove('hud-counting');
      delete dd.dataset.count;
    }
  };
  dd.dataset.count = (0).toFixed(decimals);
  requestAnimationFrame(frame);
}
