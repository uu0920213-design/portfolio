"""mongomock 으로 전체 흐름 점검: 적재 → /chat 질문 → 세션 조회.
사용: ESTATE_DATA_DIR=<csv폴더> python tests/run_estate_check.py"""
import json
import sys
from pathlib import Path

import mongomock
import pymongo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pymongo.MongoClient = mongomock.MongoClient   # 실제 Mongo 없이 점검

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

main.estate_store.import_kind("apartment")
main.estate_store.import_kind("villa")
main.estate_store.import_model_eval()
c = TestClient(main.app)

SCENARIOS = [
    ["종로구 아파트 최근 6개월 실거래가 알려줘.", "지난달보다 집값이 얼마나 올랐어?",
     "최근 1년 가격 추이를 그래프로 보여줘.", "이 조건의 아파트 예상 매매가는 얼마야?", "앞으로 집값 방향은?"],
    ["집값 얼마나 올랐어?", "마포구 빌라 최근 3개월 실거래가", "홍파동 아파트 시세 알려줘", "빌라는?"],
    ["경희궁자이 지난달 대비 얼마나 올랐어?", "송파구 25평 아파트 예상 매매가",
     "강남구 84㎡ 15층 2010년식 아파트 예상 매매가는 얼마야?", "잠실동 84㎡ 아파트 예상 매매가"],
    ["신사동 아파트 실거래가", "부동산 기초 강의 추천해줘", "수강 신청 어떻게 해?", "서초구 아파트 앞으로 오를까?",
     "이 조건의 아파트 예상 매매가는 얼마야?"],
]
if len(sys.argv) > 1:
    SCENARIOS = [sys.argv[1:]]
for qs in SCENARIOS:
    cid = None
    print("\n" + "=" * 70)
    for q in qs:
        r = c.post("/chat", json={"message": q, "conversation_id": cid})
        j = r.json()
        cid = j.get("conversation_id", cid)
        print("\nQ:", q, "→", r.status_code, j.get("intent"))
        print("A:", j.get("bot_response"))
        e = j.get("estate")
        if e:
            print("  type:", e["type"], "| metrics:", [(m["label"], m["value"]) for m in e.get("metrics", [])])
            print("  charts:", [(x["title"], len(x["labels"])) for x in e.get("charts", [])],
                  "| table rows:", len((e.get("table") or {}).get("rows", [])))
            print("  notes:", e.get("notes"))
            print("  chips:", e.get("suggestions"))
        if j.get("recommended_courses"):
            print("  courses:", [x["name"] for x in j["recommended_courses"]])
print("\nmongo collections:", {n: main.db[n].count_documents({}) for n in main.db.list_collection_names()})
print("models doc:", list(main.db["estate_models"].find({}, {"_id": 1})))
