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

/* ─── 모달 (브라우저 기본 alert·confirm·prompt 대신) — 2026-10-13 ─────────────
   uiModal({title, html, type, okText, cancelText}) → Promise<boolean>
   type: info · success · warning · error · question  (머리 색이 바뀐다) */
(function () {
  const COLORS = { info: 'var(--accent)', success: 'var(--green)', warning: 'var(--yellow)',
                   error: 'var(--red)', question: 'var(--purple)' };
  const ICONS = { info: 'bi-info-circle-fill', success: 'bi-check-circle-fill', warning: 'bi-exclamation-triangle-fill',
                  error: 'bi-x-circle-fill', question: 'bi-question-circle-fill' };
  window.uiModal = function ({ title = '알림', html = '', type = 'info', okText = '확인', cancelText = null,
                               okClass = 'btn-primary', onOk = null, size = '', requireScroll = false } = {}) {
    return new Promise(resolve => {
      const wrap = document.createElement('div');
      wrap.className = 'modal fade ui-modal';
      wrap.tabIndex = -1;
      wrap.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable ${size}">
          <div class="modal-content">
            <div class="modal-header" style="border-top:4px solid ${COLORS[type] || COLORS.info};border-radius:var(--radius-lg) var(--radius-lg) 0 0">
              <h5 class="modal-title"><i class="bi ${ICONS[type] || ICONS.info} me-2" style="color:${COLORS[type] || COLORS.info}"></i>${title}</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="닫기"></button>
            </div>
            <div class="modal-body" style="font-size:0.88rem;color:var(--text-sub)">${html}</div>
            <div class="modal-footer">
              ${cancelText ? `<button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">${cancelText}</button>` : ''}
              <button type="button" class="btn ${okClass} btn-sm ui-ok">${okText}</button>
            </div>
          </div>
        </div>`;
      document.body.appendChild(wrap);
      const m = new bootstrap.Modal(wrap);
      let result = false;
      wrap.querySelector('.ui-ok').addEventListener('click', () => {
        if (onOk && onOk(wrap) === false) return;   // onOk 가 false 면 닫지 않는다(검증 실패)
        result = true; m.hide();
      });
      wrap.addEventListener('hidden.bs.modal', () => { wrap.remove(); resolve(result); });
      /* requireScroll: 끝까지 읽어야(본문을 맨 아래까지 내려야) 확인 단추가 켜진다.
         본문이 짧아 스크롤이 없으면 바로 켜진다. */
      if (requireScroll) {
        const ok = wrap.querySelector('.ui-ok');
        const body = wrap.querySelector('.modal-body');
        const hint = document.createElement('span');
        hint.className = 'ui-scroll-hint small text-muted me-auto';
        hint.innerHTML = '<i class="bi bi-arrow-down-circle me-1"></i>끝까지 읽으면 단추가 켜집니다';
        ok.parentNode.insertBefore(hint, ok.parentNode.firstChild);
        ok.disabled = true;
        const check = () => {
          if (body.scrollHeight - body.clientHeight - body.scrollTop <= 4) {
            ok.disabled = false; hint.innerHTML = '<i class="bi bi-check2-circle me-1"></i>끝까지 읽었습니다';
            hint.classList.replace('text-muted', 'text-success');
          }
        };
        body.addEventListener('scroll', check);
        wrap.addEventListener('shown.bs.modal', check);
      }
      m.show();
    });
  };
  window.uiAlert = (msg, type = 'info', title = null) =>
    uiModal({ title: title || ({ error: '실패', warning: '확인 필요', success: '완료' }[type] || '알림'), html: msg, type });
  window.uiConfirm = (msg, { title = '확인', okText = '진행', danger = false } = {}) =>
    uiModal({ title, html: msg, type: danger ? 'warning' : 'question', okText, cancelText: '취소',
              okClass: danger ? 'btn-danger' : 'btn-primary' });

  /* 서버 응답에서 사람이 읽을 이유를 뽑는다 */
  window.failReason = async function (res) {
    const map = { 400: '입력값을 확인해 주세요.', 401: '로그인이 풀렸습니다. 새로고침 후 다시 로그인하세요.',
                  403: '권한이 없습니다.', 404: '대상을 찾을 수 없습니다(이미 지워졌을 수 있습니다).',
                  413: '파일이 너무 큽니다(한 번에 50MB 까지).', 500: '서버 오류가 났습니다. 잠시 뒤 다시 시도하세요.' };
    let msg = '';
    try { const d = await res.clone().json(); msg = d.error || ''; } catch (_) {}
    return `${msg || map[res.status] || '알 수 없는 오류'} (HTTP ${res.status})`;
  };

  /* 동의 표 HTML — upload 화면·피검자 편집이 함께 쓴다 */
  window.consentTableHTML = function (item) {
    return `<table class="table table-sm table-bordered mb-0" style="font-size:0.8rem">
      ${item.rows.map(r => `<tr><th style="width:30%;background:var(--bg-card2);white-space:nowrap">${r[0]}</th><td>${r[1]}</td></tr>`).join('')}
    </table>`;
  };

  /* 동의 기록이 없는 피검자에 개인정보를 저장할 때 — 두 동의를 받는다. 동의하면 {consent_privacy:1,...} */
  window.askConsent = async function () {
    let terms;
    try { terms = await api.get('/api/privacy/consent-terms'); }
    catch (e) { await uiAlert('동의서 내용을 불러오지 못했습니다: ' + e.message, 'error'); return null; }
    const html = `<p class="mb-2">이 피검자는 아직 <strong>동의 기록이 없습니다.</strong> 이름·성별·출생연도·진단 소견을 저장하려면
      피검자에게 아래 내용을 알리고 두 가지 동의를 모두 받아야 합니다.</p>
      ${terms.items.map(it => `<div class="mb-3"><div class="fw-semibold mb-1" style="color:var(--text)">${it.label}</div>
        ${consentTableHTML(it)}
        <div class="form-check mt-2"><input class="form-check-input" type="checkbox" id="ask_${it.key}">
        <label class="form-check-label" for="ask_${it.key}">${it.checkbox}</label></div></div>`).join('')}
      <div class="small text-danger d-none" id="askErr">두 항목에 모두 동의해야 저장할 수 있습니다.</div>
      <div class="small mt-1"><a href="/privacy" target="_blank">개인정보처리방침 전문</a></div>`;
    const ok = await uiModal({ title: '개인정보 동의 확인', html, type: 'question', okText: '동의하고 저장', cancelText: '취소',
      size: 'modal-lg', requireScroll: true,
      onOk: w => { const all = terms.items.every(it => w.querySelector('#ask_' + it.key).checked);
                   w.querySelector('#askErr').classList.toggle('d-none', all); return all; } });
    return ok ? { consent_privacy: 1, consent_sensitive: 1, terms_version: terms.version } : null;
  };
})();
