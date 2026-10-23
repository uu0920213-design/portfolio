import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# 공공데이터 CSV(수집 결과)와 학습된 모델 위치. 환경변수로 바꿀 수 있습니다.
DATA_DIR = Path(os.getenv("ESTATE_DATA_DIR", BASE_DIR / "data" / "estate"))
MODEL_DIR = Path(os.getenv("ESTATE_MODEL_DIR", BASE_DIR / "models" / "estate"))
EVAL_PATH = Path(os.getenv("ESTATE_EVAL_PATH", BASE_DIR / "data" / "estate" / "model_eval.json"))

KINDS = {
    "apartment": {"label": "아파트", "prefix": "apartment_sale_", "model": "apartment_price_model.pkl"},
    "villa": {"label": "빌라", "prefix": "villa_sale_", "model": "villa_price_model.pkl"},
}

GU = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구",
    "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구",
    "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구",
]

# 컬렉션 이름
C_TX = "estate_transactions"      # 정제된 실거래 (원본 + 취소건 제거)
C_STATS = "estate_monthly_stats"  # 지역·유형별 월간 통계(조정지수, 증감률, 전망)
C_MODELS = "estate_models"        # 모델 성능(검증 지표)
C_PRED = "estate_predictions"     # 예상 매매가 조회 기록
C_META = "estate_meta"            # 적재 시각, 건수

SQM_PER_PYEONG = 3.3058
# '33평형' 같은 평형은 공급면적 기준이 일반적이라 전용면적으로 환산할 때 쓰는 비율
EXCLUSIVE_RATIO = 0.75
