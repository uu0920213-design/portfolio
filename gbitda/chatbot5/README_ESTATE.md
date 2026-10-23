# 집이잇다 부동산 AI 챗봇 (실거래 조회 · 가격 추이 · 예상 매매가)

기존 FastAPI 챗봇(`app/main.py`)에 부동산 분석을 붙인 버전입니다. 강의 추천 질문은 예전처럼 동작하고,
**가격 질문이면 실거래 분석 결과가 카드(지표·차트·표)로 답변**됩니다.

## 폴더
```
app/main.py              /chat 에서 가격 질문이면 estate 분석, 아니면 기존 강의 추천
app/estate/
  config.py              경로·컬렉션 이름
  cleaning.py            CSV 정제 (중복 제거 · 취소 거래 짝 제거)
  store.py               MongoDB 저장/조회 (Mongo에 데이터가 없으면 CSV로 대체)
  stats.py               월별 통계 · 구성 보정 가격지수 · 방향(추세) 계산
  predictor.py           RandomForest 예상 매매가 + 비슷한 거래
  nlu.py                 질문 해석 (지역·유형·기간·면적·의도)
  service.py             질문 → 계산 → 답변 카드
  router.py              REST API (/estate/...)
scripts/import_estate_to_mongo.py     CSV → MongoDB 적재
scripts/evaluate_estate_models.py     모델 검증 지표 생성(선택)
data/estate/             여기에 수집 CSV 를 둡니다 (apartment_sale_11110_202601.csv …)
models/estate/           여기에 apartment_price_model.pkl, villa_price_model.pkl
tests/                   mongomock 으로 전체 흐름 점검
```

## 실행 순서
1. `pip install -r requirements.txt`
2. `.env.example` 을 `.env` 로 복사해 `MONGO_URI` 입력 (Atlas 주소 등. **.env 는 git 에 올리지 마세요**)
3. CSV 를 `data/estate/`, 모델 pkl 을 `models/estate/` 에 복사 (모델은 용량이 커서 git 에 올리지 않도록 `.gitignore` 처리됨 — 100MB 초과)
4. 적재: `python -m scripts.import_estate_to_mongo`
5. 서버: `py -m uvicorn app.main:app --reload` (다른 PC 에서도 접속하려면 `--host 0.0.0.0` 추가)  (프런트 CORS: 5500/5501 기본 허용, 배포 주소는 `.env` 의 `ALLOWED_ORIGINS`)

## MongoDB 컬렉션
| 컬렉션 | 내용 |
|---|---|
| `estate_transactions` | 정제된 실거래 (아파트·빌라) |
| `estate_monthly_stats` | 지역·유형별 월간 통계, 보정지수, 방향 |
| `estate_models` | 모델 검증 지표 (오차율 등) |
| `estate_predictions` | 예상 매매가 조회 기록 |
| `estate_meta` | 적재 시각·건수·제외한 행 수 |
| `chat_history` | 기존과 같음 + `estate` 필드(카드 데이터)가 추가되어 대화를 다시 열어도 카드가 보임 |

## REST API
`GET /estate/status` · `GET /estate/districts` · `GET /estate/trades?kind=apartment&district=종로구&months=6` ·
`GET /estate/monthly?kind=villa&district=마포구` · `POST /estate/predict {kind,district,umd?,area?,floor?,build_year?}`

## 챗봇 질문 예시
- 종로구 아파트 최근 6개월 실거래가 알려줘 → 거래 건수·중위/평균가·월별 차트·최근 거래 10건
- 지난달보다 집값이 얼마나 올랐어? → 전월 대비 변화율 (보정/단순 두 가지)
- 최근 1년 가격 추이를 그래프로 보여줘 → 월별 중위가·가격지수 차트와 표
- 이 조건의 아파트 예상 매매가는 얼마야? → 예상가, 오차 범위, 비슷한 최근 거래
- 앞으로 집값 방향은? → 최근 추세 방향(설명용)

지역을 말하지 않으면 직전 대화의 지역·조건을 이어 쓰고, 처음부터 없으면 서울 전체로 답합니다.

## 데이터·모델에 대해 알아둘 점 (답변에도 표시됩니다)
- **중복/취소 처리**: 합본·전처리본 CSV 가 같은 폴더에 있어도 구·월별 원본만 읽고, 완전히 같은 행은 1건으로, 취소(`cdealType=O`) 거래는 짝이 되는 원거래와 함께 제외합니다.
- **보정 가격지수**: 단순 평균은 그 달에 어떤 집(면적·연식·층·동네)이 팔렸는지에 따라 흔들려서, 이를 통제한 지수로 전월 대비를 계산합니다. 거래가 30건 미만이면 경고합니다.
- **잠정 월**: 전체 거래 건수가 평소의 70% 미만인 최근 달은 신고가 덜 반영된 잠정치로 표시하고 확정 월 기준도 같이 보여줍니다.
- **예상 매매가는 '현재 시세 추정'** 입니다. 트리 기반 모델이라 미래 시점을 넣어도 값이 같아 미래 예측이 아니며, 그렇게 표기합니다. 오차 범위는 시간 분리 검증(1~6월 학습 → 7~9월 예측) 결과로 보여줍니다 (아파트 중앙값 약 7%, 빌라 약 15%).
- **'앞으로 방향'은 최근 월별 추세를 설명한 것**이지 예측이 아닙니다. 지금 데이터는 2026년 1~9월(9개월)뿐이라 '최근 1년'을 물어도 보유 기간만 보여줍니다.
- DNN 모델은 RandomForest 보다 오차가 커서(아파트 중앙값 약 19% vs 5%) 답변에는 쓰지 않습니다.
- 진짜 향후 전망을 하려면 최소 2~3년치 월별 데이터로 시간 순서 검증을 통과한 모델이 필요합니다.

## 점검
`ESTATE_DATA_DIR=<CSV 폴더> python tests/run_estate_check.py` — mongomock 으로 적재부터 /chat 질문·세션 조회까지 확인합니다 (`tests/run_rest_check.py` 는 REST API).

## 로그인 / 회원가입 (MongoDB)
- `app/auth.py` — `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`, `POST /auth/find-id`, `POST /auth/reset-password`, `GET /auth/check-id`
- 컬렉션 `users`(회원), `auth_sessions`(로그인 토큰, 7일 후 자동 삭제). 비밀번호는 PBKDF2-SHA256 해시로만 저장하고, 5회 틀리면 5분간 잠깁니다.
- 아이디 찾기는 일부를 가린 아이디(`ki*****`)만 알려주고, 비밀번호 찾기는 아이디+가입 이메일이 맞으면 새 비밀번호로 변경합니다(이메일 발송 서버가 없는 시연용 방식).
