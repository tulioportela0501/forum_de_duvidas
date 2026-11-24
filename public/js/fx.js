// Efeitos visuais "tech": só decoração, não altera dados nem eventos do sistema. Respeita prefers-reduced-motion.
(() => {
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches, $ = s => document.querySelector(s);
  const mk = (id, tag = 'div') => { const e = document.createElement(tag); e.id = id; e.setAttribute('aria-hidden', 'true'); document.body.prepend(e); return e; };
  mk('fx-grid'); const scan = mk('fx-scan');

  // holofote azul que segue o mouse (com atraso suave)
  if (!calmo && matchMedia('(pointer:fine)').matches) {
    const glow = mk('fx-glow'); let gx = innerWidth / 2, gy = -300, tx = gx, ty = gy, on = false;
    const tick = () => { gx += (tx - gx) * .14; gy += (ty - gy) * .14; glow.style.transform = `translate3d(${gx - 220}px,${gy - 220}px,0)`; if (Math.abs(tx - gx) + Math.abs(ty - gy) > .5) requestAnimationFrame(tick); else on = false; };
    addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; glow.classList.add('on'); if (!on) { on = true; requestAnimationFrame(tick); } }, { passive: true });
    document.addEventListener('mouseleave', () => glow.classList.remove('on'));
  }

  // onda de clique nos botões
  document.addEventListener('pointerdown', e => {
    const b = e.target.closest && e.target.closest('.btn'); if (!b || b.disabled) return;
    const r = b.getBoundingClientRect(), d = Math.max(r.width, r.height) * 2, s = document.createElement('span');
    s.className = 'rip'; s.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`;
    b.append(s); setTimeout(() => s.remove(), 650);
  });

  // partículas ao curtir / repostar (roda depois do handler que alterna o estado)
  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('[data-like],[data-rt]');
    if (!b || calmo || !b.classList.contains('on')) return;
    const r = b.querySelector('svg').getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, cor = b.dataset.like ? '#ff4d79' : '#00B2FF';
    for (let i = 0; i < 9; i++) {
      const p = document.createElement('i'), a = (Math.PI * 2 * i) / 9 + Math.random() * .5, k = 22 + Math.random() * 18;
      p.className = 'fx-p'; p.style.cssText = `left:${cx}px;top:${cy}px;background:${cor};box-shadow:0 0 8px ${cor}`; document.body.append(p);
      p.animate([{ transform: 'translate(-50%,-50%) scale(1)', opacity: 1 }, { transform: `translate(calc(-50% + ${Math.cos(a) * k}px),calc(-50% + ${Math.sin(a) * k}px)) scale(.2)`, opacity: 0 }], { duration: 560, easing: 'cubic-bezier(.2,.8,.3,1)' }).onfinish = () => p.remove();
    }
  }, true);

  // a cada troca de página: linha de varredura, título "decodificando" e contadores subindo
  const G = '01<>/{}[]#$%&*+=', decode = h => {
    const t = h.textContent; let f = 0; const n = 14;
    const id = setInterval(() => { f++; h.textContent = [...t].map((c, i) => (c === ' ' || i < t.length * f / n) ? c : G[Math.random() * G.length | 0]).join(''); if (f >= n) { clearInterval(id); h.textContent = t; } }, 38);
  };
  const conta = el => {
    const n = +el.textContent.trim(); if (!Number.isInteger(n) || n <= 0) return;
    const t0 = performance.now(), step = t => { const p = Math.min(1, (t - t0) / 800); el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); else el.textContent = n; };
    el.textContent = '0'; requestAnimationFrame(step);
  };
  const v = $('#view');
  if (v && !calmo) new MutationObserver(() => {
    scan.classList.remove('go'); void scan.offsetWidth; scan.classList.add('go');
    const h = v.querySelector('h1'); if (h && !h.children.length && h.textContent.length < 40) decode(h);
    v.querySelectorAll('.kpi b').forEach(conta);
  }).observe(v, { childList: true });
})();
