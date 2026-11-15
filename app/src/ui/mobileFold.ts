// Phones only (see mobileFold.css): the header folds into one slim row with an "Options" button,
// and the step's panel (start screen, mission list, pair card) folds under a handle row so the two
// globes can take the freed height. On wider screens the added controls are hidden by CSS and the
// header keeps its original DOM, so desktop is unchanged.

const PHONE = '(max-width: 820px), (max-height: 480px) and (orientation: landscape)';

export function setupMobileFold(): void {
  const body = document.body;
  const topbar = document.querySelector('.topbar') as HTMLElement | null;
  const tools = document.querySelector('.topbar-tools') as HTMLElement | null;
  const steps = document.getElementById('steps');
  const stage = document.getElementById('stage');
  if (!topbar || !tools || !steps || !stage) return;
  const mq = window.matchMedia(PHONE);

  // ---------- top bar: chip + Options button + sheet ----------
  const chip = document.createElement('span');
  chip.className = 'mf-chip';
  const optBtn = document.createElement('button');
  optBtn.type = 'button';
  optBtn.className = 'btn btn-icon mf-options';
  optBtn.id = 'mf-options';
  optBtn.setAttribute('aria-expanded', 'false');
  optBtn.setAttribute('aria-controls', 'mf-sheet');
  optBtn.setAttribute('aria-label', 'Options');
  optBtn.innerHTML =
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>';
  const sheet = document.createElement('div');
  sheet.className = 'mf-sheet';
  sheet.id = 'mf-sheet';
  topbar.append(chip, optBtn, sheet);

  // On phones the tools and the step row live in the sheet (same keyboard order: they follow the
  // Options button); elsewhere they go back to their original places.
  const placeNodes = () => {
    if (mq.matches) {
      if (tools.parentElement !== sheet) sheet.append(tools, steps);
    } else if (tools.parentElement === sheet) {
      topbar.insertBefore(tools, chip);
      topbar.after(steps);
      setOpen(false);
    }
    body.classList.toggle('mf-phone', mq.matches);
    nudgeResize();
  };

  const setOpen = (open: boolean) => {
    body.classList.toggle('mf-open', open);
    optBtn.setAttribute('aria-expanded', String(open));
  };
  optBtn.addEventListener('click', () => setOpen(!body.classList.contains('mf-open')));
  document.addEventListener('pointerdown', (e) => {
    if (!body.classList.contains('mf-open')) return;
    const t = e.target as Node;
    if (!sheet.contains(t) && !optBtn.contains(t)) setOpen(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || !body.classList.contains('mf-open')) return;
    if (document.querySelector('dialog[open]')) return;
    setOpen(false);
    optBtn.focus();
  });
  // opening a dialog from the sheet folds the sheet
  for (const id of ['keys-button', 'credits-button']) document.getElementById(id)?.addEventListener('click', () => setOpen(false));

  const updateChip = () => {
    const cur = steps.querySelector('.step.is-current');
    const num = cur?.querySelector('.step-num')?.textContent?.trim();
    const label = cur?.querySelector('.step-label')?.textContent?.trim();
    chip.textContent = label ? `${num ? `${num} · ` : ''}${label}` : '';
  };

  // ---------- bottom sheet: one handle for the visible panel ----------
  const handle = document.createElement('button');
  handle.type = 'button';
  handle.className = 'mf-handle';
  handle.id = 'mf-handle';
  handle.setAttribute('aria-expanded', 'true');
  const hText = document.createElement('span');
  hText.className = 'mf-handle-text';
  const hChev = document.createElement('span');
  hChev.className = 'mf-chev';
  hChev.setAttribute('aria-hidden', 'true');
  hChev.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M6 15l6-6 6 6"/></svg>';
  handle.append(hText, hChev);
  stage.append(handle);

  const panelFor = (): HTMLElement | null => {
    for (const id of ['intro', 'mission-panel', 'detail-panel']) {
      const el = document.getElementById(id);
      if (el && !el.hidden) return el;
    }
    return null;
  };
  const txt = (sel: string) => document.querySelector(sel)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';

  const setFolded = (folded: boolean) => {
    body.classList.toggle('mf-folded', folded);
    handle.setAttribute('aria-expanded', String(!folded));
    nudgeResize();
  };
  handle.addEventListener('click', () => setFolded(!body.classList.contains('mf-folded')));

  let lastStep = '';
  let lastSel: unknown = undefined;
  const update = () => {
    updateChip();
    const step = body.dataset.step ?? '';
    const p = panelFor();
    handle.hidden = !p;
    if (p) handle.setAttribute('aria-controls', p.id);
    let label = 'Choose a mission';
    if (p?.id === 'mission-panel') {
      const n = document.querySelectorAll('#mission-panel .top5-score').length;
      const name = txt('#mission-panel .panel-title');
      label = [name, n ? `${n} analogs` : ''].filter(Boolean).join(' · ');
    } else if (p?.id === 'detail-panel') {
      const name = txt('#detail-panel .panel-title');
      const fin = txt('#detail-panel .final');
      label = [name, fin ? `final ${fin}` : ''].filter(Boolean).join(' · ');
    }
    hText.textContent = label || 'Panel';
    const sel = window.starsFlow?.state.selectedId;
    // a new step opens unfolded; a point picked on a globe while folded unfolds the sheet
    if (step !== lastStep || (lastSel !== undefined && sel !== lastSel && sel != null)) {
      if (body.classList.contains('mf-folded')) setFolded(false);
    }
    lastStep = step;
    lastSel = sel;
  };

  let raf = 0;
  const schedule = () => {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      update();
    });
  };
  const mo = new MutationObserver(schedule);
  mo.observe(steps, { childList: true, subtree: true });
  mo.observe(stage, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] });
  mo.observe(body, { attributes: true, attributeFilter: ['data-step'] });

  mq.addEventListener('change', placeNodes);
  placeNodes();
  update();
}

/** The globes follow their panes through ResizeObserver; the window resize event also refits labels. */
function nudgeResize(): void {
  requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
}
