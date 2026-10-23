# 집이잇다 gbitda
```
index.html
css/  reset.css, style.css
js/   main.js (링크·데이터·기능·로그인 모달), chatbot.js
img/  섹션/챗봇 이미지
icons/ 아이콘 (chat-*.svg = 챗봇용)
```
- 링크(카카오/인스타/유튜브), 뉴스·후기·숏츠·FAQ 데이터는 `js/main.js` 상단에서 수정합니다.
- 챗봇 답변 API는 `js/chatbot.js` 의 `askBot()` 에서 연결합니다.

## 챗봇 (FastAPI + MongoDB)
- 서버 주소: `js/main.js` 의 `GBITDA_CONFIG.chatApiBase` (기본: 화면을 연 주소의 8000번 포트를 자동 사용 → IP 로 열어도 그대로 동작)
- 사용 API: `POST /chat`, `GET /sessions`, `GET /sessions/{id}`, `PATCH /sessions/{id}/read`, `PATCH /sessions/read-all`, `DELETE /sessions/{id}`, `DELETE /sessions`
- 서버 `main.py` 의 CORS `allow_origins` 에 이 페이지를 여는 주소(예: Live Server `http://127.0.0.1:5500`)가 들어 있어야 합니다. 배포 시에는 실제 사이트 주소를 추가하세요.

## 부동산 가격 카드 (챗봇)
- 서버가 가격 질문에 `estate` 객체를 내려주면 `js/chatbot.js` 의 `addEstateCard()` 가 지표·막대/선 차트(SVG)·표·안내·추천 질문 버튼을 그립니다. 스타일은 `css/style.css` 의 `.cb-est-*`.
- 대화 기록(`GET /sessions/{id}`)에도 `estate` 가 포함되어 다시 열어도 같은 카드가 보입니다.
- 백엔드 설정은 `README_ESTATE.md`(서버 폴더) 참고.

## 같은 네트워크의 다른 PC 에서 보기 (발표/시연)
1. 서버 PC 에서 `ipconfig` → IPv4 주소 확인 (예: 192.168.0.64)
2. 서버: `py -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. 화면: 이 폴더에서 `py -m http.server 5500 --bind 0.0.0.0` (또는 VS Code Live Server)
4. 브라우저에서 `http://192.168.0.64:5500` 접속 — 코드의 주소를 IP 로 바꿀 필요 없음
5. 접속이 안 되면 Windows 방화벽에서 포트 5500·8000 허용




db에 부동산 데이터 넣기
cd "G:\class\gbitda\새 폴더 (2) - 복사본\chatbot5"
py -m scripts.import_estate_to_mongo

창 1: 서버 (켜 놓고 그대로 두기)
cd "E:\class\gbitda\새 폴더\chatbot5"
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000

창 2: 화면 (새 창)
cd "화면 폴더 경로"      ← index.html이 있는 gbitda_github 폴더
py -m http.server 5500 --bind 0.0.0.0

http://192.168.0.93:5500 들어가면 같은 와이파이쓰는 사람끼리 공유가능