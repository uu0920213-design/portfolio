"""CSV(공공데이터 수집 결과) → 정제 → MongoDB 적재 + 월간 통계/모델 지표 저장.

사용:  python -m scripts.import_estate_to_mongo [--data-dir data/estate]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app.estate.config import DATA_DIR, EVAL_PATH, KINDS  # noqa: E402
from app.estate.store import EstateStore  # noqa: E402


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    ap.add_argument("--db", default=os.getenv("MONGO_DB", "gbitda"))
    a = ap.parse_args()
    db = MongoClient(a.uri, serverSelectionTimeoutMS=5000)[a.db]
    db.client.admin.command("ping")
    store = EstateStore(db, Path(a.data_dir))
    for kind in KINDS:
        store.import_kind(kind)
    store.import_model_eval(EVAL_PATH)
    store.rebuild_stats()
    print("완료:", store.status())


if __name__ == "__main__":
    main()
