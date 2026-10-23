/* =========================================================
   집이잇다 gbitda – chatbot.js (AI 상담봇 · FastAPI + MongoDB 연동)
   - 서버 주소: js/main.js 의 GBITDA_CONFIG.chatApiBase
   - 사용하는 API
       POST   /chat                       질문 전송 (conversation_id 없으면 새 대화방)
       GET    /sessions                   대화 목록
       GET    /sessions/{id}              대화방 전체 기록
       PATCH  /sessions/{id}/read         대화방 읽음
       PATCH  /sessions/read-all          모두 읽음
       DELETE /sessions/{id}              대화방 1개 삭제
       DELETE /sessions                   전체 삭제
   - 부동산 가격 질문이면 응답의 estate 객체(지표·차트·표·안내·추천질문)를 카드로 그립니다.
   ========================================================= */
(() => {
  'use strict';
  const cfg = window.GBITDA_CONFIG || {};
  const API = (cfg.chatApiBase || 'http://127.0.0.1:8000').replace(/\/$/, '');

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = $('#cb');
  if (!root) return;

  const fab = $('.cb-fab', root), panel = $('.cb-panel', root);
  const form = $('.cb-input', root), input = $('input', form);
  const msgs = $('.cb-msgs', root);
  const items = $('.cb-session-items', root), dot = $('.cb-nav .dot', root);
  const readBtn = $('[data-readall]', root), unreadLabel = $('.cb-unread', root);
  const WELCOME = msgs.innerHTML;          // HTML에 적어둔 첫 인사 말풍선

  let view = 'home', currentId = null, sessions = [], sending = false, loading = false, listError = false;

  /* ---------- 유틸 ---------- */
  // 서버(pymongo)는 UTC 시간을 'Z' 없이 내려주므로 UTC로 해석 후 로컬 날짜로 표시 (MM-DD)
  function fmtDate(v) {
    if (!v) return '';
    const s = typeof v === 'string' && !/(Z|[+-]\d\d:?\d\d)$/i.test(v) ? v + 'Z' : v;
    const d = new Date(s);
    if (isNaN(d)) return '';
    return String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  async function api(path, opt) {
    let res;
    try { res = await fetch(API + path, opt); }
    catch (_) { const e = new Error('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.'); e.network = true; throw e; }
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) { const e = new Error(data.detail || data.message || `요청 실패 (${res.status})`); e.status = res.status; throw e; }
    return data;
  }
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const scrollDown = () => { msgs.scrollTop = msgs.scrollHeight; };

  /* ---------- 화면 전환 ---------- */
  function show(v) {
    view = v;
    $$('.cb-views > section', root).forEach(s => s.classList.toggle('on', s.dataset.v === v));
    const tab = v === 'chat' ? 'list' : v;
    $$('.cb-nav button', root).forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    form.hidden = v === 'set';
    if (v === 'chat') { scrollDown(); setTimeout(() => !input.disabled && input.focus(), 50); }
  }
  function openPanel(open) {
    panel.hidden = !open; fab.classList.toggle('open', open);
    if (open) { show('home'); loadSessions(); }
  }

  /* ---------- 메시지 ---------- */
  function addMessage(text, type) {
    const m = el('div', 'm ' + (type === 'user' ? 'u' : 'b'), text);
    msgs.appendChild(m); scrollDown(); return m;
  }
  function clearMessages() { msgs.innerHTML = WELCOME; }
  function addLoading() { const m = addMessage('답변을 작성하고 있어요...', 'bot'); m.classList.add('cb-loading'); return m; }

  // FastAPI 응답의 recommended_courses → 카드
  function addCourseCards(courses) {
    if (!Array.isArray(courses) || !courses.length) return;
    const wrap = el('div', 'cb-course-list');
    courses.forEach(c => {
      if (!c || typeof c !== 'object') return;
      const card = el('div', 'cb-course-card');
      card.append(el('span', 'cb-course-category', c.category || '추천 클래스'), el('h4', '', c.name || '추천 클래스'));
      if (c.description) card.append(el('p', 'cb-course-desc', c.description));
      if (c.price != null && c.price !== '') card.append(el('p', 'cb-course-price', typeof c.price === 'number' ? c.price.toLocaleString('ko-KR') + '원' : String(c.price)));
      try {
        const u = new URL(c.url, location.href);
        if (/^https?:$/.test(u.protocol)) {
          const a = el('a', 'cb-course-link', '클래스 자세히 보기 →');
          a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; card.append(a);
        }
      } catch (_) {}
      wrap.append(card);
    });
    if (wrap.children.length) { msgs.appendChild(wrap); scrollDown(); }
  }

  /* ---------- 부동산 분석 카드 (실거래·전월 대비·추이 차트·방향·예상 매매가) ---------- */
  const SVGNS = 'http://www.w3.org/2000/svg';
  const svg = (tag, attrs = {}, text) => {
    const n = document.createElementNS(SVGNS, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    if (text != null) n.textContent = text;
    return n;
  };
  // 차트 숫자 표기: 만원 → "9.7억", 퍼센트, 지수
  function fmtVal(v, f) {
    if (v == null || Number.isNaN(v)) return '-';
    if (f === 'won') return v >= 10000 ? (v / 10000).toFixed(v >= 100000 ? 1 : 2).replace(/\.?0+$/, '') + '억' : Math.round(v).toLocaleString('ko-KR') + '만';
    if (f === 'pct') return (v > 0 ? '+' : '') + v.toFixed(1) + '%';
    if (f === 'index') return v.toFixed(1);
    return String(v);
  }
  function drawChart(ch) {
    const box = el('div', 'cb-est-chart');
    box.append(el('p', 'cb-est-chart-title', ch.title || ''));
    const vals = (ch.series && ch.series[0] && ch.series[0].values) || [];
    const labels = ch.labels || [], flags = ch.flags || [];
    const pts = vals.map((v, i) => ({ v, i })).filter(p => p.v != null && !Number.isNaN(p.v));
    if (!pts.length) { box.append(el('p', 'cb-est-muted', '표시할 데이터가 없어요.')); return box; }
    const W = 320, H = 150, L = 8, R = 8, T = 22, B = 24, n = Math.max(labels.length, vals.length);
    const min0 = Math.min(...pts.map(p => p.v)), max0 = Math.max(...pts.map(p => p.v));
    let lo = ch.type === 'bar' ? Math.min(0, min0) : min0, hi = ch.type === 'bar' ? Math.max(0, max0) : max0;
    if (hi === lo) { hi += Math.abs(hi) * .05 || 1; lo -= Math.abs(lo) * .05 || 1; }
    const pad = ch.type === 'bar' ? 0 : (hi - lo) * .15; lo -= pad; hi += pad;
    const x = i => L + (n === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (n - 1));
    const slot = (W - L - R) / n;
    const bx = i => L + slot * i + slot / 2;
    const y = v => T + (H - T - B) * (1 - (v - lo) / (hi - lo));
    const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'cb-est-svg', role: 'img', 'aria-label': ch.title || '차트' });
    s.append(svg('line', { x1: L, x2: W - R, y1: y(Math.max(lo, Math.min(0, hi))), y2: y(Math.max(lo, Math.min(0, hi))), class: 'cb-est-axis' }));
    if (ch.type === 'bar') {
      const bw = Math.min(30, slot * .6);
      pts.forEach(p => {
        const y0 = y(0), yy = y(p.v), prov = flags[p.i];
        const r = svg('rect', { x: bx(p.i) - bw / 2, width: bw, y: Math.min(y0, yy), height: Math.max(1, Math.abs(yy - y0)), rx: 3,
          class: 'cb-est-bar' + (ch.format === 'pct' ? (p.v >= 0 ? ' up' : ' down') : '') + (prov ? ' prov' : '') });
        s.append(r, svg('text', { x: bx(p.i), y: (p.v >= 0 ? yy - 4 : yy + 11), class: 'cb-est-val', 'text-anchor': 'middle' }, fmtVal(p.v, ch.format) + (prov ? '*' : '')));
      });
    } else {
      const d = pts.map((p, k) => (k ? 'L' : 'M') + x(p.i).toFixed(1) + ' ' + y(p.v).toFixed(1)).join(' ');
      s.append(svg('path', { d, class: 'cb-est-line', fill: 'none' }));
      pts.forEach((p, k) => {
        const prov = flags[p.i];
        s.append(svg('circle', { cx: x(p.i), cy: y(p.v), r: prov ? 3 : 3.5, class: 'cb-est-dot' + (prov ? ' prov' : '') }));
        if (k === 0 || k === pts.length - 1 || p.v === max0 || p.v === min0)
          s.append(svg('text', { x: Math.min(W - 14, Math.max(14, x(p.i))), y: y(p.v) - 7, class: 'cb-est-val', 'text-anchor': 'middle' }, fmtVal(p.v, ch.format) + (prov ? '*' : '')));
      });
    }
    const every = n > 8 ? 2 : 1;
    labels.forEach((lb, i) => {
      if (i % every === 0 || i === n - 1) s.append(svg('text', { x: ch.type === 'bar' ? bx(i) : x(i), y: H - 7, class: 'cb-est-x', 'text-anchor': 'middle' }, lb));
    });
    box.append(s);
    if (flags.some(Boolean)) box.append(el('p', 'cb-est-muted', '* 신고가 덜 반영된 잠정치'));
    return box;
  }
  function addEstateCard(e) {
    if (!e || typeof e !== 'object' || e.type === 'ask' && !(e.suggestions || []).length) return;
    const card = el('div', 'cb-est');
    if (e.type !== 'ask') {
      const hd = el('div', 'cb-est-hd');
      hd.append(el('h4', '', e.title || '부동산 분석'));
      if (e.subtitle) hd.append(el('span', '', e.subtitle));
      card.append(hd);
    }
    if ((e.metrics || []).length) {
      const g = el('div', 'cb-est-metrics');
      e.metrics.forEach(m => {
        const c = el('div', 'cb-est-metric' + (m.big ? ' big' : '') + (m.tone ? ' ' + m.tone : ''));
        c.append(el('span', 'cb-est-k', m.label), el('b', 'cb-est-v', m.value));
        if (m.sub) c.append(el('span', 'cb-est-sub', m.sub));
        g.append(c);
      });
      card.append(g);
    }
    (e.charts || []).forEach(ch => card.append(drawChart(ch)));
    if (e.table && (e.table.rows || []).length) {
      const box = el('div', 'cb-est-tablebox');
      if (e.table.title) box.append(el('p', 'cb-est-chart-title', e.table.title));
      const t = el('table', 'cb-est-table'), tr = el('tr');
      (e.table.columns || []).forEach(c => tr.append(el('th', '', c)));
      const th = el('thead'); th.append(tr); t.append(th);
      const tb = el('tbody');
      e.table.rows.forEach(r => { const row = el('tr'); r.forEach(v => row.append(el('td', '', String(v)))); tb.append(row); });
      t.append(tb); box.append(t); card.append(box);
    }
    if ((e.notes || []).length) {
      const ul = el('ul', 'cb-est-notes');
      e.notes.forEach(n => ul.append(el('li', '', n)));
      card.append(ul);
    }
    if ((e.suggestions || []).length) {
      const row = el('div', 'cb-est-chips');
      e.suggestions.forEach(q => {
        const b = el('button', 'cb-est-chip', q); b.type = 'button';
        b.addEventListener('click', () => send(q));
        row.append(b);
      });
      card.append(row);
    }
    msgs.appendChild(card);
    const prev = card.previousElementSibling;   // 답변 말풍선부터 보이도록 (카드가 길어 맨 아래로 내리면 윗부분이 가려짐)
    if (prev) msgs.scrollTop += prev.getBoundingClientRect().top - msgs.getBoundingClientRect().top - 12; else scrollDown();
  }
  function renderHistory(list) {
    msgs.innerHTML = '';
    (list || []).forEach(it => {
      if (it.user_message) addMessage(it.user_message, 'user');
      if (it.bot_response) addMessage(it.bot_response, 'bot');
      addCourseCards(it.recommended_courses); addEstateCard(it.estate);
    });
    if (!msgs.children.length) clearMessages();
    scrollDown();
  }

  /* ---------- 읽음 상태 ---------- */
  const unreadCount = () => sessions.filter(s => s.is_read === false).length;
  function updateReadAll() {
    const n = unreadCount();
    readBtn.textContent = n ? '모두 읽기' : '모두 읽음';
    readBtn.disabled = n === 0;
    unreadLabel.textContent = n ? `${n}개의 안읽은 알림이 있어요` : '읽지 않은 대화가 없습니다.';
    dot.hidden = n === 0;
    $$('.cb-th', items).forEach(r => r.classList.toggle('is-unread', sessions.find(s => s.conversation_id === r.dataset.id)?.is_read === false));
  }
  async function markRead(id) {
    const s = sessions.find(x => x.conversation_id === id); if (s) s.is_read = true; updateReadAll();
    try { await api(`/sessions/${encodeURIComponent(id)}/read`, { method: 'PATCH' }); } catch (e) { console.warn('읽음 저장 실패', e); }
  }
  async function markAllRead() {
    sessions.forEach(s => { s.is_read = true; }); updateReadAll();
    try { await api('/sessions/read-all', { method: 'PATCH' }); } catch (e) { console.warn('모두 읽기 실패', e); }
  }

  /* ---------- 대화 목록 ---------- */
  function renderSessions() {
    items.innerHTML = '';
    if (!sessions.length) {
      const box = el('div', 'cb-empty');
      box.append(el('p', '', listError ? '서버에 연결하지 못했어요.\n잠시 후 다시 시도해 주세요.' : '아직 상담 기록이 없어요.'));
      items.append(box); updateReadAll(); return;
    }
    sessions.forEach(s => {
      const row = el('div', 'cb-th'); row.dataset.id = s.conversation_id;
      const open = el('button', 'cb-th-open'); open.type = 'button'; open.setAttribute('aria-label', '상담 기록 열기');
      const body = el('div', 'cb-th-content');
      body.append(
        el('b', '', '집이잇다  AI 상담봇'),
        el('p', 'cb-q', s.last_user_message ? `최근 질문: ${s.last_user_message}` : (s.last_message || '새로운 상담을 시작해 보세요.')),
        el('p', '', s.last_bot_response ? `마지막 답변: ${s.last_bot_response}` : '아직 답변 기록이 없습니다.'));
      open.append(el('div', 'cb-av'), body);
      open.onclick = () => openSession(s.conversation_id);
      const side = el('div', 'cb-date-area');
      const del = el('button', 'cb-delete-session', '대화기록 삭제'); del.type = 'button';
      del.onclick = e => { e.stopPropagation(); deleteSession(s.conversation_id); };
      side.append(el('span', 'cb-date', fmtDate(s.updated_at || s.created_at)), del);
      row.append(open, side); items.append(row);
    });
    updateReadAll();
  }
  async function loadSessions() {
    if (loading) return; loading = true;
    try { sessions = await api('/sessions'); listError = false; }
    catch (e) { console.warn('대화 목록 불러오기 실패', e); listError = true; }
    finally { loading = false; renderSessions(); }
  }

  /* ---------- 대화방 열기 / 새 상담 ---------- */
  function startNewChat() {
    if (sending) return;
    currentId = null; clearMessages(); show('chat');
  }
  async function openSession(id) {
    if (sending) return;
    currentId = id; msgs.innerHTML = ''; show('chat');
    const wait = addLoading();
    try {
      const data = await api(`/sessions/${encodeURIComponent(id)}`);
      renderHistory(data.messages); markRead(id);
    } catch (e) {
      wait.remove(); addMessage(e.message, 'bot');
      if (e.status === 404) { currentId = null; loadSessions(); }
    }
  }

  /* ---------- 질문 전송 ---------- */
  async function send(text) {
    if (sending) return;
    if (view !== 'chat') { currentId = null; clearMessages(); show('chat'); }   // 홈/목록에서 질문 → 새 대화방
    sending = true; input.disabled = true;
    addMessage(text, 'user'); const wait = addLoading();
    try {
      const body = { message: text }; if (currentId) body.conversation_id = currentId;
      const d = await api('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      wait.remove(); currentId = d.conversation_id;
      addMessage(d.bot_response, 'bot'); addCourseCards(d.recommended_courses); addEstateCard(d.estate);
      const now = new Date().toISOString().replace('Z', '');
      const i = sessions.findIndex(s => s.conversation_id === currentId);
      const prev = i >= 0 ? sessions.splice(i, 1)[0] : { conversation_id: currentId, created_at: now };
      sessions.unshift({ ...prev, last_user_message: text, last_bot_response: d.bot_response, updated_at: now, is_read: true });
      renderSessions(); markRead(currentId);
    } catch (e) {
      wait.remove(); addMessage(e.message, 'bot');
      if (e.status === 404) currentId = null;   // 삭제된 대화방이면 다음 질문은 새 대화방
    } finally { sending = false; input.disabled = false; input.focus(); }
  }

  /* ---------- 삭제 ---------- */
  async function deleteSession(id) {
    if (!confirm('이 대화 기록을 삭제할까요?\n삭제한 기록은 복구할 수 없습니다.')) return;
    try {
      await api(`/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' });
      sessions = sessions.filter(s => s.conversation_id !== id);
      if (currentId === id) { currentId = null; clearMessages(); }
      renderSessions();
    } catch (e) { alert('대화 기록을 삭제하지 못했어요.\n' + e.message); }
  }
  async function deleteAll() {
    if (!sessions.length) { alert('삭제할 대화 기록이 없습니다.'); return; }
    if (!confirm('모든 대화 기록을 삭제할까요?\n삭제한 기록은 복구할 수 없습니다.')) return;
    try {
      await api('/sessions', { method: 'DELETE' });
      sessions = []; currentId = null; clearMessages(); renderSessions(); show('home');
      alert('모든 대화 기록을 삭제했습니다.');
    } catch (e) { alert('대화 기록을 삭제하지 못했어요.\n' + e.message); }
  }

  /* ---------- 이벤트 ---------- */
  fab.onclick = () => openPanel(panel.hidden);
  $$('[data-close]', root).forEach(b => b.onclick = () => openPanel(false));
  $$('.cb-nav button', root).forEach(b => b.onclick = () => { show(b.dataset.tab); if (b.dataset.tab === 'list') loadSessions(); });
  $('[data-back]', root).onclick = () => { show('list'); loadSessions(); };
  root.addEventListener('click', e => { if (e.target.closest('[data-new-chat]')) startNewChat(); });
  readBtn.onclick = markAllRead;
  $('[data-clear]', root).onclick = deleteAll;
  form.onsubmit = e => { e.preventDefault(); const q = input.value.trim(); if (!q) return; input.value = ''; send(q); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) openPanel(false); });

  updateReadAll();
})();
