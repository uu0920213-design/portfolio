
import joblib

# 서버가 시작될 때 학습된 모델 불러오기
model = joblib.load("app/models/intent_model.joblib")

def classify_intent(message: str) -> dict:
    # 질문의 의도 예측
    intent = model.predict([message])[0]

    # 클래스별 점수는 확률과 동일하지 않을 수 있음
    scores = model.predict_proba([message])[0]
    confidence = float(max(scores))

    return {
        "intent": intent,
        "confidence": confidence
    }
