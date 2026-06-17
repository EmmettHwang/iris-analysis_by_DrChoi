/* ─── Toast ───────────────────────────────────────────────────────────────── */
(function () {
  const container = document.createElement('div');
  container.id = 'toast-container';
  document.body.appendChild(container);

  const ICONS = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', info: 'bi-info-circle-fill' };

  window.toast = function (msg, type = 'info', duration = 3000) {
    const el = document.createElement('div');
    el.className = `app-toast toast-${type}`;
    el.innerHTML = `<i class="bi ${ICONS[type] || ICONS.info} toast-icon"></i><span>${msg}</span>`;
    container.appendChild(el);
    const remove = () => {
      el.classList.add('hiding');
      el.addEventListener('animationend', () => el.remove(), { once: true });
    };
    setTimeout(remove, duration);
    el.addEventListener('click', remove);
  };
})();

/* ─── API helper ──────────────────────────────────────────────────────────── */
window.api = {
  async get(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },
  async put(url, body) {
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },
  async del(url) {
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(res.statusText);
    return res.json().catch(() => ({}));
  },
};

/* ─── Skeleton ────────────────────────────────────────────────────────────── */
window.skeleton = function (lines = 3, height = 16) {
  return Array.from({ length: lines }, (_, i) =>
    `<div class="skeleton mb-2" style="height:${height}px;width:${i === lines - 1 ? '60%' : '100%'}"></div>`
  ).join('');
};

/* ─── Escape HTML ─────────────────────────────────────────────────────────── */
window.esc = function (str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
};

/* ─── Number counter animation ────────────────────────────────────────────── */
window.animateCount = function (el, target, duration = 800) {
  const start = parseInt(el.textContent) || 0;
  const startTime = performance.now();
  const step = (now) => {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(start + (target - start) * ease);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
};

/* ─── Active nav highlight ────────────────────────────────────────────────── */
(function () {
  const path = location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    } else if (href === '/' && path === '/') {
      link.classList.add('active');
    }
  });
})();

/* ─── Chart.js global defaults (light theme) ─────────────────────────────── */
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#4A5568';
  Chart.defaults.borderColor = '#E2E6F0';
  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = '#1A2035';
  Chart.defaults.plugins.tooltip.titleColor = '#F8FAFC';
  Chart.defaults.plugins.tooltip.bodyColor = '#CBD5E1';
  Chart.defaults.plugins.tooltip.borderColor = '#334155';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
}
