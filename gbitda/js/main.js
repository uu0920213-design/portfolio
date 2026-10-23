/* =========================================================
   집이잇다 gbitda – main.js
   1) CONFIG  : 링크/설정값 (여기만 수정하면 됩니다)
   2) DATA    : 뉴스 · 후기 · 숏츠 · FAQ 데이터
   3) 기능    : 링크 연결, 레터 탭, 후기 더보기, 키워드, 숏츠 슬라이드, FAQ, 로그인 모달
   ========================================================= */

/* ===== 1) CONFIG ===== */
window.GBITDA_CONFIG = {
  links: {
    kakao: '#',      // 카카오톡 채널(친구추가) 링크 → 1:1 문의하기, CTA, 푸터, 챗봇 '문의하기'
    instagram: '#',  // 인스타그램 링크
    youtube: '#'     // 유튜브 채널 링크
  },
  // 챗봇 FastAPI 서버 주소: 화면을 연 주소와 같은 PC(포트 8000)를 자동으로 사용합니다.
  // → localhost 로 열면 localhost:8000, http://192.168.0.64:5500 으로 열면 192.168.0.64:8000. 따로 고칠 필요 없음.
  // (다른 서버를 쓰려면 'http://주소:포트' 로 직접 지정)
  chatApiBase: (location.protocol === 'http:' || location.protocol === 'https:') ? `${location.protocol}//${location.hostname}:8000` : 'http://127.0.0.1:8000',
  historyStep: 6,    // '더 많은 수강생 후기 보기' 클릭 당 추가되는 카드 수
  faqPerPage: 5      // FAQ 한 페이지에 보이는 질문 수
};
const CONFIG = window.GBITDA_CONFIG;

/* ===== 2) DATA ===== */
// 부동산 레터 뉴스. cat 값이 탭 이름(전세/정책/청약/집값/공공주택)과 같으면 해당 탭에 표시됩니다.
const NEWS = [
  { cat:'전세', title:'서울 전셋값, 다시 상승폭 확대', desc:'8월 넷째 주 서울 아파트 전세값은 전주보다 0.22% 상승하며 상승폭이 다시 커졌습니다.', src:'한국부동산원 2026.08.27  기준일 2026.08.24', img:'img/letter-0.jpg', feat:'img/letter-feat.jpg', url:'#' },
  { cat:'공공주택', title:'LH, 2028년부터 매년 10만호 이상 착공', desc:'LH는 올해 5만 호, 2027년 7만 6천호에 이어 2028년부터 매년 10만 호 이상의 주택 착공을 추진합니다. 정부의 8-13 주…', src:'연합뉴스', img:'img/letter-1.jpg', url:'#' },
  { cat:'집값', title:'서울 집값 상승하는 지역이 달라졌다', desc:'강남집값은 내려갔는데 노·도·강은 더 올랐다. 서울 아파트 값은 8월 넷째 주 0.29% 상승했지만 지역별 움직임은 엇갈렸…', src:'매일경제 2026.08.27', img:'img/letter-2.jpg', url:'#' },
  { cat:'정책', title:'공급대책 수도권 10만 호, 어디에 풀리나', desc:'정부가 8월 13일 수도권 주택공급 확대 대책을 발표했습니다. 신규공급 10만호를 추가하고, 관련 대출 지원도 30조원 늘…', src:'KBS, 2026.8.13', img:'img/letter-3.jpg', url:'#' }
];

// 수강생 후기. 아래 6개를 3번 반복해 18개로 만든 임시 데이터입니다 → 실제 후기로 교체하세요.
const HISTORY_BASE = [
  { tag:'내집마련', title:'생애 첫 내집, 꿈을 현실로', desc:'좋은 생활권에서 만난 첫 보금자리', img:'img/history-1.jpg', url:'#' },
  { tag:'경매낙찰성공', title:'법원에서 남긴 낙찰 기록', desc:'물건 분석부터 입찰까지, 직접 준비하고 실행…', img:'img/history-2.jpg', url:'#' },
  { tag:'내집마련', title:'경매로 시작한 첫 내집 마련', desc:'서울의 선호도 높은 주거지, 경매를 통해 새로…', img:'img/history-3.jpg', url:'#' },
  { tag:'내집마련', title:'경매로 시작한 첫 내 집 마련', desc:'서울의 선호도 높은 주거지, 경매를 통해 새로…', img:'img/history-4.jpg', url:'#' },
  { tag:'내집마련', title:'첫 낙찰의 설렘', desc:'꼼꼼하게 분석하고 준비한 끝에 받아 든 소중…', img:'img/history-5.jpg', url:'#' },
  { tag:'내집마련', title:'법원앞, 첫 입찰의 기억', desc:'내 집을 향한 도전의 결실을 함께 기념한 특별…', img:'img/history-6.jpg', url:'#' }
];
const HISTORY = [...HISTORY_BASE, ...HISTORY_BASE, ...HISTORY_BASE];

// 유튜브 숏츠. 한 페이지에 3개씩, 6개 = 2페이지. url에 실제 쇼츠 주소를 넣으세요.
// 예) url: 'https://www.youtube.com/shorts/영상ID'
const SHORTS = [
  { url:'', img:'img/short-1.jpg', title:'살아남는 부동산, 딱 한 가지 조건' },
  { url:'', img:'img/short-2.jpg', title:'동부법원 미친 듯이 낙찰됩니다' },
  { url:'', img:'img/short-3.jpg', title:'코스피 5천 시대 부동산은 끝? 주식은 시작' },
  { url:'', img:'img/short-1.jpg', title:'(2페이지) 쇼츠 제목 1' },
  { url:'', img:'img/short-2.jpg', title:'(2페이지) 쇼츠 제목 2' },
  { url:'', img:'img/short-3.jpg', title:'(2페이지) 쇼츠 제목 3' }
];

// FAQ. cat: 수강 안내 / 결제/환불 / 자료 및 혜택 / 현장 임장 ('답변 내용을 입력하세요.' 부분을 채워 주세요)
const TBD = '답변 내용을 입력하세요.';
const FAQS = [
  { cat:'수강 안내', q:'수강 중 촬영된 사진은 어떻게 사용되나요?', a:'강의 현장 사진이 촬영될 수 있으며, 촬영된 사진은 이후 후기 게시물이나 홍보 자료로 활용될 수 있는 점 참고 부탁드립니다.' },
  { cat:'수강 안내', q:'강의 듣다가 궁금한 점이 생기면 어떻게 질문하나요?', a:TBD },
  { cat:'자료 및 혜택', q:'수료증이 발급되나요?', a:TBD },
  { cat:'수강 안내', q:'경매나 NPL클래스도 미리 공부하고 들어야 하나요?', a:TBD },
  { cat:'자료 및 혜택', q:'강의 자료(PDF, 요약본)는 따로 제공되나요?', a:TBD },
  { cat:'수강 안내', q:'수강 신청은 어떻게 하나요?', a:TBD },
  { cat:'결제/환불', q:'결제 수단은 어떤 것이 있나요?', a:TBD },
  { cat:'결제/환불', q:'환불은 어떻게 받을 수 있나요?', a:TBD },
  { cat:'결제/환불', q:'분할 결제가 가능한가요?', a:TBD },
  { cat:'자료 및 혜택', q:'수강생 전용 혜택이 있나요?', a:TBD },
  { cat:'자료 및 혜택', q:'강의 영상을 다시 볼 수 있나요?', a:TBD },
  { cat:'현장 임장', q:'임장은 어디에서 진행되나요?', a:TBD },
  { cat:'현장 임장', q:'임장 준비물이 있나요?', a:TBD },
  { cat:'현장 임장', q:'우천 시 임장은 어떻게 진행되나요?', a:TBD }
];

/* ===== 3) 기능 ===== */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// 링크 연결: [data-link="kakao|instagram|youtube"] 요소의 href를 CONFIG.links에서 가져옴
$$('[data-link]').forEach(a => {
  const url = CONFIG.links[a.dataset.link];
  if (url && url !== '#') { a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; }
  else a.addEventListener('click', e => e.preventDefault());
});

// ----- 부동산 레터: 탭별 뉴스 -----
const newsView = $('#newsView');
const href = u => u || '#';
function renderNews(cat) {
  const items = cat === '전체' ? NEWS : NEWS.filter(n => n.cat === cat);
  if (!items.length) {
    newsView.className = 'lg empty';
    newsView.innerHTML = '<p class="nempty fade">해당 카테고리의 뉴스가 아직 없어요.</p>';
    return;
  }
  if (cat === '전체') {
    const [f, ...rest] = items;
    newsView.className = 'lg';
    newsView.innerHTML =
      `<a class="feat fade" href="${href(f.url)}" style="background-image:linear-gradient(180deg,transparent 45%,rgba(0,0,0,.78)),url('${f.feat || f.img}')"><span class="bdg org lg2">${f.cat}</span><h3>${f.title}</h3><p>${f.desc}</p><div class="meta"><span>${f.src}</span><img src="icons/ci_arrow-right-lg-1.svg" alt="" width="18" height="18"></div></a>` +
      `<div class="fade">${rest.map(n => `<a class="li" href="${href(n.url)}"><img src="${n.img}" alt=""><div><span class="bdg org lg2">${n.cat}</span><h4>${n.title}</h4><p>${n.desc}</p><small>${n.src}</small></div></a>`).join('')}</div>`;
  } else {
    newsView.className = 'lg rows';
    newsView.innerHTML = items.map(n => `<a class="nrow fade" href="${href(n.url)}"><img src="${n.img}" alt=""><div class="tx"><span class="bdg org lg2">${n.cat}</span><h4>${n.title}</h4><p>${n.desc}</p></div><span class="mt">${n.src}</span></a>`).join('');
  }
}
$('#ltabs').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  $$('#ltabs button').forEach(x => x.classList.toggle('on', x === b));
  renderNews(b.textContent.trim());
});
renderNews('전체');

// ----- 수강생 후기: 6개씩 더 보기 -----
const historyList = $('#historyList'), historyMore = $('#historyMore');
let historyShown = 0;
function showMoreHistory() {
  const next = HISTORY.slice(historyShown, historyShown + CONFIG.historyStep);
  historyList.insertAdjacentHTML('beforeend', next.map(h =>
    `<a class="hc fade" href="${href(h.url)}"><img src="${h.img}" alt=""><div class="bd"><span class="bdg org">${h.tag}</span><h4>${h.title}</h4><p>${h.desc}</p></div></a>`).join(''));
  historyShown += next.length;
  historyMore.hidden = historyShown >= HISTORY.length;
}
historyMore.addEventListener('click', showMoreHistory);
showMoreHistory();

// ----- 키워드: 기본은 모두 비선택, 클릭하면 선택(다시 클릭하면 해제) -----
$('#kws').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const was = b.classList.contains('on');
  $$('#kws button').forEach(x => x.classList.remove('on'));
  if (!was) b.classList.add('on');
});

// ----- 유튜브 숏츠: 3개씩 페이지 슬라이드 -----
const ytTrack = $('#ytTrack'), ytPrev = $('#ytPrev'), ytNext = $('#ytNext');
const ytPages = Math.ceil(SHORTS.length / 3);
let ytPage = 0;
ytTrack.innerHTML = Array.from({ length: ytPages }, (_, p) =>
  `<div class="yt-page">${SHORTS.slice(p * 3, p * 3 + 3).map(s =>
    `<a class="sh" href="${s.url || '#'}"${s.url ? ' target="_blank" rel="noopener noreferrer"' : ' data-empty'} aria-label="${s.title}"><img src="${s.img}" alt="${s.title}"></a>`).join('')}</div>`).join('');
ytTrack.addEventListener('click', e => { if (e.target.closest('[data-empty]')) e.preventDefault(); });
function ytGo(p) {
  ytPage = Math.max(0, Math.min(ytPages - 1, p));
  ytTrack.style.transform = `translateX(-${ytPage * 100}%)`;
  ytPrev.disabled = ytPage === 0; ytNext.disabled = ytPage === ytPages - 1;
}
ytPrev.addEventListener('click', () => ytGo(ytPage - 1));
ytNext.addEventListener('click', () => ytGo(ytPage + 1));
ytGo(0);

// ----- FAQ: 카테고리 탭 + 아코디언 + 페이지네이션 -----
const faqList = $('#faqList'), faqPg = $('#faqPg');
let faqCat = 'all', faqPage = 1;
const ico = (n, w, h) => `<img src="icons/${n}" alt="" width="${w}" height="${h}">`;
function renderFaq() {
  const list = FAQS.filter(f => faqCat === 'all' || f.cat === faqCat);
  const pages = Math.max(1, Math.ceil(list.length / CONFIG.faqPerPage));
  faqPage = Math.min(faqPage, pages);
  const slice = list.slice((faqPage - 1) * CONFIG.faqPerPage, faqPage * CONFIG.faqPerPage);
  faqList.innerHTML = slice.map(f =>
    `<div class="q fade"><button type="button" class="qh" aria-expanded="false">${f.q}<span class="qi">${ico('weui_arrow-filled-5.svg', 24, 12).replace('<img', '<img class="d"')}${ico('weui_arrow-filled-4.svg', 24, 12).replace('<img', '<img class="u"')}</span></button><div class="qa"><p>${f.a}</p></div></div>`).join('');
  faqPg.innerHTML =
    `<button type="button" data-p="prev" aria-label="이전 페이지"${faqPage === 1 ? ' disabled' : ''}>${ico('weui_arrow-filled-2.svg', 12, 24)}</button>` +
    Array.from({ length: pages }, (_, i) => `<button type="button" data-p="${i + 1}"${i + 1 === faqPage ? ' class="on" aria-current="page"' : ''}>${i + 1}</button>`).join('') +
    `<button type="button" data-p="next" aria-label="다음 페이지"${faqPage === pages ? ' disabled' : ''}>${ico('weui_arrow-filled-3.svg', 12, 24)}</button>`;
}
faqList.addEventListener('click', e => {
  const h = e.target.closest('.qh'); if (!h) return;
  const q = h.parentElement, open = q.classList.contains('open');
  $$('.q', faqList).forEach(x => { x.classList.remove('open'); $('.qh', x).setAttribute('aria-expanded', 'false'); });
  if (!open) { q.classList.add('open'); h.setAttribute('aria-expanded', 'true'); }
});
faqPg.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b || b.disabled) return;
  const p = b.dataset.p;
  faqPage = p === 'prev' ? faqPage - 1 : p === 'next' ? faqPage + 1 : +p;
  renderFaq();
});
$('#ftabs').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  $$('#ftabs button').forEach(x => x.classList.toggle('on', x === b));
  faqCat = b.dataset.c; faqPage = 1; renderFaq();
});
renderFaq();

/* ===== 인증 API (FastAPI + MongoDB users) ===== */
window.GBITDA_AUTH = (function(){
  var KEY='gbitda_auth', st={token:null,user:null}, listeners=[];
  function load(){ try{ var v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&v.token){ st=v; } }catch(_){} }
  function save(){ try{ st.token?localStorage.setItem(KEY,JSON.stringify(st)):localStorage.removeItem(KEY); }catch(_){} }
  function emit(){ listeners.forEach(function(f){ f(st.user); }); }
  // 서버 응답의 detail(문자열)을 사용자에게 보여줄 메시지로 바꿔 던짐
  function call(path,opt){
    opt=opt||{}; var h={'Content-Type':'application/json'};
    if(opt.auth&&st.token) h.Authorization='Bearer '+st.token;
    return fetch(CONFIG.chatApiBase.replace(/\/$/,'')+path,{method:opt.method||'POST',headers:h,body:opt.body?JSON.stringify(opt.body):undefined})
      .then(function(r){ return r.json().catch(function(){return {};}).then(function(d){
        if(!r.ok){ var e=new Error(typeof d.detail==='string'?d.detail:'입력 내용을 확인해 주세요.'); e.status=r.status; throw e; }
        return d; }); },
      function(){ throw new Error('서버에 연결할 수 없어요. 서버가 켜져 있는지 확인해 주세요.'); });
  }
  load();
  return {
    get user(){ return st.user; },
    call:call,
    onChange:function(f){ listeners.push(f); f(st.user); },
    login:function(id,pw){ return call('/auth/login',{body:{user_id:id,password:pw}}).then(function(d){ st={token:d.token,user:d.user}; save(); emit(); return d.user; }); },
    logout:function(){ var t=st.token; st={token:null,user:null}; save(); emit(); if(t) fetch(CONFIG.chatApiBase.replace(/\/$/,'')+'/auth/logout',{method:'POST',headers:{Authorization:'Bearer '+t}}).catch(function(){}); },
    restore:function(){ if(!st.token) return; call('/auth/me',{method:'GET',auth:true}).then(function(d){ st.user=d.user; save(); emit(); },function(e){ if(e.status===401){ st={token:null,user:null}; save(); emit(); } }); }
  };
})();
/* ===== 로그인 · 회원가입 · 약관동의 · 아이디/비밀번호 찾기 모달 ===== */
(function(){
  var overlay=document.getElementById('overlay'),
      openBtn=document.getElementById('openLogin'),
      closeBtn=document.getElementById('closeLogin'),
      form=document.getElementById('loginForm'),
      uid=document.getElementById('uid'),
      upw=document.getElementById('upw'),
      err=document.getElementById('err');

  function open(){
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden','false');
    document.body.classList.add('modal-open');
    setTimeout(function(){uid.focus()},50);
  }
  function close(){
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    err.textContent='';
    openBtn.focus();
  }

  // 로그인 상태면 헤더 버튼이 '로그아웃'으로 바뀜
  GBITDA_AUTH.onChange(function(u){
    openBtn.textContent=u?'로그아웃':'로그인';
    openBtn.title=u?(u.name+'님 로그인 중'):'';
  });
  GBITDA_AUTH.restore();
  openBtn.addEventListener('click',function(){
    if(GBITDA_AUTH.user){ GBITDA_AUTH.logout(); window.gbitdaToast&&window.gbitdaToast('로그아웃 되었습니다.'); return; }
    open();
  });
  closeBtn.addEventListener('click',close);
  overlay.addEventListener('mousedown',function(e){ if(e.target===overlay) close(); });

  document.addEventListener('keydown',function(e){
    if(!overlay.classList.contains('open')) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key==='Tab'){ // 포커스를 모달 안에 가둠
      var f=overlay.querySelectorAll('button,input,a[href]');
      var first=f[0], last=f[f.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  });

  form.addEventListener('submit',function(e){
    e.preventDefault();
    if(!uid.value.trim()){ err.textContent='아이디를 입력해 주세요.'; uid.focus(); return; }
    if(!upw.value){ err.textContent='비밀번호를 입력해 주세요.'; upw.focus(); return; }
    err.textContent='';
    var btn=form.querySelector('button[type=submit]'); if(btn) btn.disabled=true;
    GBITDA_AUTH.login(uid.value.trim(),upw.value).then(function(u){
      upw.value=''; close(); window.gbitdaToast&&window.gbitdaToast(u.name+'님, 환영해요.');
    }).catch(function(e){ err.textContent=e.message; upw.focus(); })
      .then(function(){ if(btn) btn.disabled=false; });
  });
})();
// ===== 회원가입 모달 =====
(function(){
  var so=document.getElementById('signupOverlay'),
      openLink=document.getElementById('openSignup'),
      closeBtn=document.getElementById('closeSignup'),
      loginClose=document.getElementById('closeLogin'),
      loginBtn=document.getElementById('openLogin');

  function open(){
    so.classList.add('open');
    so.setAttribute('aria-hidden','false');
    document.body.classList.add('modal-open');
    setTimeout(function(){closeBtn.focus()},50);
  }
  function close(){
    so.classList.remove('open');
    so.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    loginBtn.focus();
  }

  // 로그인 모달 → 회원가입 모달로 교체
  openLink.addEventListener('click',function(e){
    e.preventDefault();
    loginClose.click();
    open();
  });
  closeBtn.addEventListener('click',close);
  so.addEventListener('mousedown',function(e){ if(e.target===so) close(); });
  document.addEventListener('keydown',function(e){
    if(!so.classList.contains('open')) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key==='Tab'){
      var f=so.querySelectorAll('button');
      var first=f[0], last=f[f.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  });
})();
// ===== 약관동의 모달 =====
(function(){
  var to=document.getElementById('termsOverlay'),
      openBtn=document.getElementById('openTerms'),
      cancel=document.getElementById('cancelTerms'),
      join=document.getElementById('joinBtn'),
      all=document.getElementById('agreeAll'),
      reqs=Array.prototype.slice.call(document.querySelectorAll('.req-chk')),
      err=document.getElementById('termsErr'),
      signupClose=document.getElementById('closeSignup'),
      loginBtn=document.getElementById('openLogin');

  function open(){
    to.classList.add('open');
    to.setAttribute('aria-hidden','false');
    document.body.classList.add('modal-open');
    setTimeout(function(){all.focus()},50);
  }
  function close(){
    to.classList.remove('open');
    to.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    err.textContent='';
    loginBtn.focus();
  }
  function reset(){ all.checked=false; reqs.forEach(function(c){c.checked=false}); }

  // 회원가입 모달 → 약관동의 모달로 교체
  openBtn.addEventListener('click',function(){
    signupClose.click();
    reset();
    open();
  });
  cancel.addEventListener('click',close);

  all.addEventListener('change',function(){
    reqs.forEach(function(c){c.checked=all.checked});
    err.textContent='';
  });
  reqs.forEach(function(c){
    c.addEventListener('change',function(){
      all.checked=reqs.every(function(x){return x.checked});
      err.textContent='';
    });
  });

  join.addEventListener('click',function(){
    if(!reqs.every(function(x){return x.checked})){
      err.textContent='필수 약관에 모두 동의해 주세요.';
      return;
    }
    close();
    document.dispatchEvent(new CustomEvent('open-signup-form'));
  });

  // 약관 모달은 바깥 클릭으로 닫히지 않음 (실수 방지). ESC·취소로 닫기
  document.addEventListener('keydown',function(e){
    if(!to.classList.contains('open')) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key==='Tab'){
      var f=to.querySelectorAll('button,input,.terms-box');
      var first=f[0], last=f[f.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  });
})();
// ===== 가입 정보 입력 모달 =====
(function(){
  var fo=document.getElementById('formOverlay'),
      modal=document.getElementById('formModal'),
      form=document.getElementById('joinForm'),
      closeBtn=document.getElementById('closeForm'),
      loginBtn=document.getElementById('openLogin'),
      err=document.getElementById('formErr'),
      toast=document.getElementById('toast'),
      picBox=document.getElementById('picBox'),
      picFile=document.getElementById('picFile'),
      camBtn=document.getElementById('camBtn'),
      eyeBtn=document.getElementById('eyeBtn'),
      eyeSlash=document.getElementById('eyeSlash'),
      pw=document.getElementById('fpw'), pw2=document.getElementById('fpw2'),
      fy=document.getElementById('fy'), fm=document.getElementById('fm'), fd=document.getElementById('fd'),
      defaultPic=picBox.innerHTML, toastTimer;

  // 생년월일 옵션
  function fill(sel,label,from,to,step,selected){
    var h='<option value="">'+label+'</option>';
    for(var i=from;step>0?i<=to:i>=to;i+=step){ h+='<option value="'+i+'"'+(i===selected?' selected':'')+'>'+i+'</option>'; }
    sel.innerHTML=h;
  }
  function fillDate(){
    fy.innerHTML='<option value="">년</option>';
    fill(fy,'년',2010,1930,-1,1990); fill(fm,'월',1,12,1); fill(fd,'일',1,31,1);
  }

  function open(){
    form.reset(); fillDate(); err.textContent='';
    picBox.innerHTML=defaultPic;
    Array.prototype.forEach.call(form.querySelectorAll('.bad'),function(x){x.classList.remove('bad')});
    setEye(false);
    fo.classList.add('open'); fo.setAttribute('aria-hidden','false');
    document.body.classList.add('modal-open');
    modal.scrollTop=0;
    setTimeout(function(){document.getElementById('fid').focus()},50);
  }
  function close(){
    fo.classList.remove('open'); fo.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    loginBtn.focus();
  }
  function showToast(msg){
    toast.textContent=msg; toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer=setTimeout(function(){toast.classList.remove('show')},2400);
  }
  window.gbitdaToast=showToast;   // 로그인/찾기 모달에서도 같은 토스트 사용
  function setEye(show){
    pw.type=show?'text':'password'; pw2.type=show?'text':'password';
    eyeBtn.setAttribute('aria-pressed',show?'true':'false');
    eyeBtn.setAttribute('aria-label',show?'비밀번호 숨기기':'비밀번호 보기');
    eyeSlash.style.display=show?'none':'';
  }

  document.addEventListener('open-signup-form',open);
  closeBtn.addEventListener('click',close);
  eyeBtn.addEventListener('click',function(){ setEye(pw.type==='password'); });

  // 프로필 사진 미리보기
  camBtn.addEventListener('click',function(){ picFile.click(); });
  picFile.addEventListener('change',function(){
    var f=picFile.files[0];
    if(!f) return;
    var r=new FileReader();
    r.onload=function(){ picBox.innerHTML='<img alt="프로필 미리보기" src="'+r.result+'">'; };
    r.readAsDataURL(f);
  });

  form.addEventListener('input',function(e){ e.target.classList.remove('bad'); err.textContent=''; });

  form.addEventListener('submit',function(e){
    e.preventDefault();
    var id=document.getElementById('fid'), mail=document.getElementById('fmail'), name=document.getElementById('fname');
    Array.prototype.forEach.call(form.querySelectorAll('.bad'),function(x){x.classList.remove('bad')});
    function fail(el,msg){ el.classList.add('bad'); err.textContent=msg; el.focus(); }
    if(!id.value.trim()) return fail(id,'아이디를 입력해 주세요.');
    if(!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(pw.value))
      return fail(pw,'비밀번호는 8자리 이상의 대소문자, 숫자, 특수문자를 포함해야 해요.');
    if(pw.value!==pw2.value) return fail(pw2,'비밀번호가 일치하지 않아요.');
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail.value)) return fail(mail,'이메일 주소를 확인해 주세요.');
    if(!name.value.trim()) return fail(name,'이름을 입력해 주세요.');
    var addr=form.querySelector('input[placeholder="주소"]'), addr2=form.querySelector('input[placeholder="상세주소"]'),
        tel=document.getElementById('ftel'), btn=form.querySelector('button[type=submit]');
    var birth=(fy.value&&fm.value&&fd.value)?fy.value+'-'+String(fm.value).padStart(2,'0')+'-'+String(fd.value).padStart(2,'0'):'';
    if(btn) btn.disabled=true;
    GBITDA_AUTH.call('/auth/signup',{body:{user_id:id.value.trim(),password:pw.value,email:mail.value.trim(),name:name.value.trim(),
      phone:tel?tel.value:'',address:addr?addr.value:'',address_detail:addr2?addr2.value:'',birth:birth,agreed_terms:true}})
    .then(function(){ close(); showToast('회원가입이 완료되었습니다. 로그인해 주세요.'); })
    .catch(function(e){
      var t=e.status===409?(/이메일/.test(e.message)?mail:id):null;
      if(t) fail(t,e.message); else err.textContent=e.message;
    }).then(function(){ if(btn) btn.disabled=false; });
  });

  // 입력 내용 유실 방지를 위해 바깥 클릭으로는 닫지 않음. X·ESC로 닫기
  document.addEventListener('keydown',function(e){
    if(!fo.classList.contains('open')) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key==='Tab'){
      var f=fo.querySelectorAll('button,input:not([type=file]),select');
      var first=f[0], last=f[f.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  });
})();
// ===== 아이디·비밀번호 찾기 모달 =====
(function(){
  var fo=document.getElementById('findOverlay'),
      title=document.getElementById('findTitle'),
      tabId=document.getElementById('tabId'), tabPw=document.getElementById('tabPw'),
      panelId=document.getElementById('panelId'), panelPw=document.getElementById('panelPw'),
      email=document.getElementById('findEmail'), phone=document.getElementById('findPhone'),
      pwId=document.getElementById('findPwId'),
      idMsg=document.getElementById('idMsg'), pwMsg=document.getElementById('pwMsg'),
      radios=Array.prototype.slice.call(document.querySelectorAll('input[name="idway"]')),
      loginClose=document.getElementById('closeLogin'),
      loginBtn=document.getElementById('openLogin'),
      closeBtn=document.getElementById('closeFind');

  function say(el,msg,ok){ el.textContent=msg; el.className='find-msg'+(ok?' ok':''); }

  function setTab(name){
    var isId=name==='id';
    tabId.setAttribute('aria-selected',isId); tabPw.setAttribute('aria-selected',!isId);
    tabId.tabIndex=isId?0:-1; tabPw.tabIndex=isId?-1:0;
    panelId.hidden=!isId; panelPw.hidden=isId;
    title.textContent=isId?'아이디 찾기':'비밀번호 찾기';
    say(idMsg,''); say(pwMsg,'');
  }
  function syncWay(){
    var byEmail=radios[0].checked;
    email.hidden=!byEmail; phone.hidden=byEmail;
    say(idMsg,'');
  }
  function open(tab){
    email.value=''; phone.value=''; pwId.value=''; pwMail.value=''; pwNew.value='';
    radios[0].checked=true; syncWay(); setTab(tab);
    fo.classList.add('open'); fo.setAttribute('aria-hidden','false');
    document.body.classList.add('modal-open');
    setTimeout(function(){ (tab==='id'?email:pwId).focus(); },50);
  }
  function close(){
    fo.classList.remove('open'); fo.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    loginBtn.focus();
  }

  // 로그인 모달 → 찾기 모달로 교체
  document.getElementById('openFindId').addEventListener('click',function(e){ e.preventDefault(); loginClose.click(); open('id'); });
  document.getElementById('openFindPw').addEventListener('click',function(e){ e.preventDefault(); loginClose.click(); open('pw'); });

  closeBtn.addEventListener('click',close);
  fo.addEventListener('mousedown',function(e){ if(e.target===fo) close(); });

  tabId.addEventListener('click',function(){ setTab('id'); });
  tabPw.addEventListener('click',function(){ setTab('pw'); });
  [tabId,tabPw].forEach(function(t){
    t.addEventListener('keydown',function(e){
      if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
        e.preventDefault();
        var next=t===tabId?tabPw:tabId;
        setTab(next===tabId?'id':'pw'); next.focus();
      }
    });
  });
  radios.forEach(function(r){ r.addEventListener('change',function(){ syncWay(); (radios[0].checked?email:phone).focus(); }); });

  panelId.addEventListener('submit',function(e){
    e.preventDefault();
    var byEmail=radios[0].checked, el=byEmail?email:phone;
    if(!el.value.trim()){ say(idMsg,byEmail?'가입한 이메일을 입력해 주세요.':'휴대폰 번호를 입력해 주세요.'); el.focus(); return; }
    if(byEmail&&el.value.indexOf('@')<0){ say(idMsg,'가입한 이메일 주소를 입력해 주세요.'); el.focus(); return; }
    GBITDA_AUTH.call('/auth/find-id',{body:byEmail?{email:el.value.trim()}:{phone:el.value.trim()}})
      .then(function(d){ say(idMsg,'가입된 아이디는 '+d.masked_id+' 입니다. (개인정보 보호를 위해 일부만 표시)',true); })
      .catch(function(err){ say(idMsg,err.message); });
  });
  // 비밀번호 찾기: 아이디 + 가입 이메일 확인 후 새 비밀번호 설정 (입력칸은 여기서 추가)
  var pwMail=document.createElement('input'), pwNew=document.createElement('input');
  [[pwMail,'email','가입한 이메일','email','findPwMail'],[pwNew,'password','새 비밀번호 (8자 이상, 대소문자·숫자·특수문자)','new-password','findPwNew']].forEach(function(a){
    var i=a[0]; i.className=pwId.className; i.type=a[1]; i.placeholder=a[2]; i.autocomplete=a[3]; i.id=a[4]; i.setAttribute('aria-label',a[2]);
    pwId.parentNode.insertBefore(i,document.getElementById('pwMsg'));
  });
  panelPw.querySelector('button[type=submit]').textContent='비밀번호 변경';
  panelPw.addEventListener('submit',function(e){
    e.preventDefault();
    if(!pwId.value.trim()){ say(pwMsg,'가입한 아이디를 입력해 주세요.'); pwId.focus(); return; }
    if(!pwMail.value.trim()){ say(pwMsg,'가입한 이메일을 입력해 주세요.'); pwMail.focus(); return; }
    if(!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(pwNew.value)){ say(pwMsg,'새 비밀번호는 8자리 이상의 대소문자, 숫자, 특수문자를 포함해야 해요.'); pwNew.focus(); return; }
    GBITDA_AUTH.call('/auth/reset-password',{body:{user_id:pwId.value.trim(),email:pwMail.value.trim(),new_password:pwNew.value}})
      .then(function(){ say(pwMsg,'비밀번호가 변경되었어요. 새 비밀번호로 로그인해 주세요.',true); pwNew.value=''; })
      .catch(function(err){ say(pwMsg,err.message); });
  });
  fo.addEventListener('input',function(){ say(idMsg,''); say(pwMsg,''); });

  document.addEventListener('keydown',function(e){
    if(!fo.classList.contains('open')) return;
    if(e.key==='Escape'){ close(); return; }
    if(e.key==='Tab'){
      var f=Array.prototype.filter.call(fo.querySelectorAll('button,input'),function(x){ return x.offsetParent!==null && x.tabIndex>=0; });
      var first=f[0], last=f[f.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  });
})();
