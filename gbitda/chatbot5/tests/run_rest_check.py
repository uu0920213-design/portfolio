import sys
from pathlib import Path
import mongomock, pymongo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pymongo.MongoClient = mongomock.MongoClient
from fastapi.testclient import TestClient
from app import main
for k in ("apartment", "villa"):
    main.estate_store.import_kind(k, log=lambda *a: None)
main.estate_store.import_model_eval(log=lambda *a: None)
c = TestClient(main.app)
print(c.get("/estate/status").json())
r = c.get("/estate/trades", params={"kind": "apartment", "district": "종로구", "months": 6, "limit": 2}).json()
print("trades:", r["count"], r["median"], r["items"][:1])
r = c.get("/estate/monthly", params={"kind": "villa", "district": "마포구"}).json()
print("monthly:", [(m["label"], m["n"], round(m["median"]), m["adj_index"] and round(m["adj_index"], 1), m["provisional"]) for m in r["months"]][:3], r["outlook"]["direction"])
r = c.post("/estate/predict", json={"kind": "apartment", "district": "마포구", "area": 84.9, "floor": 10, "build_year": 2015}).json()
print("predict:", r["estimate_text"], r["assumptions"])
print(c.post("/estate/predict", json={"kind": "apartment", "district": "없는구"}).status_code, c.get("/estate/trades", params={"kind": "x"}).status_code)
# 세션 재조회에 estate 카드가 들어오는지
j = c.post("/chat", json={"message": "마포구 아파트 최근 6개월 실거래가"}).json()
h = c.get(f"/sessions/{j['conversation_id']}").json()
print("history estate type:", h["messages"][0]["estate"]["type"], "| sessions:", [s["last_bot_response"][:30] for s in c.get("/sessions").json()])
print("course question:", c.post("/chat", json={"message": "내집마련 클래스 추천해줘"}).json()["recommended_courses"][:1] and "courses ok")
