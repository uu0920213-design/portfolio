
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
COURSE_PATH = BASE_DIR / "data" / "courses.json"


def load_courses():
    """JSON 파일에서 강의 목록을 불러옵니다."""
    with open(COURSE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def recommend_courses(message, limit=3):
    """질문과 강의 키워드를 비교해 관련 강의를 추천합니다."""
    courses = load_courses()
    message = message.lower()

    results = []

    for course in courses:
        score = 0
        matched_keywords = []

        for keyword in course.get("keywords", []):
            if keyword.lower() in message:
                score += 2
                matched_keywords.append(keyword)

        for target in course.get("target", []):
            if target.lower() in message:
                score += 1

        if score > 0:
            results.append({
                "course": course,
                "score": score,
                "matched_keywords": matched_keywords
            })

    # 관련성이 높은 강의부터 정렬
    results.sort(key=lambda item: item["score"], reverse=True)

    # 동점이면 JSON에 등록한 순서 유지
    return results[:limit]
