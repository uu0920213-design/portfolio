
import pandas as pd
import joblib

from pathlib import Path

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score
)
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# 1. 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "intent_train.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 2. 데이터 불러오기
df = pd.read_csv(DATA_PATH)

# 질문 또는 의도가 비어 있는 행 제거
df = df.dropna(subset=["text", "intent"])

# 질문과 의도가 모두 같은 중복 행 제거
df = df.drop_duplicates(subset=["text", "intent"])

X = df["text"].astype(str)
y = df["intent"].astype(str)

print("전체 데이터:", len(df))
print("\n유형별 데이터 개수:")
print(y.value_counts())

# 3. 학습 데이터와 최종 테스트 데이터 분리
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# 4. 비교할 모델 준비
models = {
    "Logistic Regression": LogisticRegression(
        max_iter=2000,
        class_weight="balanced"
    ),
    "Linear SVM": LinearSVC(
        class_weight="balanced",
        random_state=42
    )
}

# 5. 교차 검증 설정
cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

results = {}
cv_scores = {}

print("\n===== 교차 검증 결과 =====")

for name, classifier in models.items():

    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                analyzer="char",
                ngram_range=(2, 4)
            )
        ),
        ("classifier", classifier)
    ])

    scores = cross_val_score(
        pipeline,
        X_train,
        y_train,
        cv=cv,
        scoring="f1_macro"
    )

    cv_scores[name] = scores.mean()

    print(f"\n모델: {name}")
    print("각 fold의 Macro F1:", scores.round(3))
    print("평균 Macro F1:", round(scores.mean(), 4))

    # 전체 학습 데이터로 모델 학습
    pipeline.fit(X_train, y_train)
    results[name] = pipeline

# 6. 교차 검증 평균 Macro F1이 높은 모델 선택
best_name = max(cv_scores, key=cv_scores.get)
best_model = results[best_name]

print("\n선택된 모델:", best_name)

# 7. 최종 테스트 데이터로 평가
y_pred = best_model.predict(X_test)


# 틀리게 분류한 질문 확인
print("\n===== 오분류 질문 분석 =====")

for question, actual, predicted in zip(X_test, y_test, y_pred):
    if actual != predicted:
        print(f"질문: {question}")
        print(f"실제 유형: {actual}")
        print(f"예측 유형: {predicted}")
        print("-" * 40)


accuracy = accuracy_score(y_test, y_pred)
macro_f1 = f1_score(
    y_test,
    y_pred,
    average="macro",
    zero_division=0
)

print("\n===== 최종 테스트 결과 =====")
print("정확도:", round(accuracy, 4))
print("Macro F1:", round(macro_f1, 4))

print("\n유형별 분류 결과:")
print(classification_report(
    y_test,
    y_pred,
    zero_division=0
))

# 8. 혼동행렬 출력
labels = sorted(y.unique())

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=labels
)

print("\n혼동행렬 (행=실제 유형, 열=예측 유형)")
print("유형 순서:", labels)
print(cm)

# 9. 최종 모델 저장
model_path = MODEL_DIR / "intent_model.joblib"
joblib.dump(best_model, model_path)

print("\n저장 완료:", model_path)

# 10. 새로운 질문 테스트
test_questions = [
    "부동산 초보 강의를 추천해 줘",
    "마포구 아파트 가격을 분석해 줘",
    "실거래가가 무슨 뜻이야",
    "경매 권리분석을 배우고 싶어",
    "강의 신청은 어떻게 해?"
]

print("\n===== 새 질문 분류 =====")

for question in test_questions:
    prediction = best_model.predict([question])[0]
    print(f"질문: {question}")
    print(f"예측 유형: {prediction}\n")
