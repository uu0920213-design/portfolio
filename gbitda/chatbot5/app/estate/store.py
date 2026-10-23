"""MongoDB 저장/조회. Mongo에 적재된 데이터가 없으면 CSV로 대체해서 동작합니다."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import stats as S
from .cleaning import doc_ids, load_csv_kind
from .config import C_META, C_MODELS, C_PRED, C_STATS, C_TX, DATA_DIR, EVAL_PATH, KINDS

FIELDS = ["kind", "sggCd", "district", "umd", "name", "house_type", "jibun", "price", "area", "floor",
          "build_year", "year", "month", "day", "ym", "age", "deal_date", "deal_type"]


class EstateStore:
    def __init__(self, db, data_dir=DATA_DIR):
        self.db = db
        self.data_dir = data_dir
        self._cache = {}      # kind -> (stamp, df)
        self._stat_cache = {}

    # ---------- 적재 ----------
    def import_kind(self, kind: str, df: pd.DataFrame | None = None, log=print):
        if df is None:
            df = load_csv_kind(kind, self.data_dir)
        if df.empty:
            log(f"[{kind}] CSV가 없습니다: {self.data_dir}")
            return 0
        ids = doc_ids(df)
        tx = self.db[C_TX]
        tx.delete_many({"kind": kind})
        recs = df[FIELDS].astype(object).where(df[FIELDS].notna(), None).to_dict("records")
        for r, i in zip(recs, ids):
            r["_id"] = i
            for k in ("year", "month", "day", "ym"):
                r[k] = int(r[k])
        for s in range(0, len(recs), 5000):
            tx.insert_many(recs[s:s + 5000], ordered=False)
        now = datetime.now(timezone.utc)
        self.db[C_META].update_one(
            {"_id": kind},
            {"$set": {"imported_at": now, "n": len(recs), "months": sorted(int(x) for x in df.ym.unique()),
                      "removed_cancel_rows": df.attrs.get("removed_cancel_rows", 0),
                      "removed_paired_rows": df.attrs.get("removed_paired_rows", 0),
                      "removed_duplicate_rows": df.attrs.get("removed_duplicate_rows", 0)}},
            upsert=True)
        tx.create_index([("kind", 1), ("district", 1), ("ym", 1)])
        log(f"[{kind}] {len(recs):,}건 저장 (중복 {df.attrs.get('removed_duplicate_rows', 0):,}행 · "
            f"취소건 {df.attrs.get('removed_cancel_rows', 0):,}행 · 취소된 원거래 {df.attrs.get('removed_paired_rows', 0):,}행 제외)")
        self._cache.pop(kind, None)
        self._stat_cache.clear()
        return len(recs)

    def import_model_eval(self, path=EVAL_PATH, log=print):
        if not path.exists():
            log("모델 평가 파일이 없어 건너뜁니다:", path)
            return
        ev = json.loads(path.read_text(encoding="utf-8"))
        for kind, v in ev.items():
            self.db[C_MODELS].update_one(
                {"_id": kind}, {"$set": {"eval": v, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
        log("모델 검증 지표 저장:", ", ".join(ev))

    def rebuild_stats(self, log=print):
        n = 0
        for kind in KINDS:
            df = self.load(kind)
            if df.empty:
                continue
            for district in [None] + sorted(df.district.unique()):
                self.scope_stats(kind, district, persist=True)
                n += 1
        log(f"월간 통계 {n}개 범위 저장 (컬렉션 {C_STATS})")

    # ---------- 조회 ----------
    def load(self, kind: str) -> pd.DataFrame:
        meta = self.db[C_META].find_one({"_id": kind})
        stamp = meta.get("imported_at") if meta else "csv"
        hit = self._cache.get(kind)
        if hit and hit[0] == stamp:
            return hit[1]
        df = pd.DataFrame()
        if meta:
            docs = list(self.db[C_TX].find({"kind": kind}, {f: 1 for f in FIELDS} | {"_id": 0}))
            if docs:
                df = pd.DataFrame(docs)
                df["price_m2"] = df.price / df.area
        if df.empty:
            df = load_csv_kind(kind, self.data_dir)
        df.attrs["source"] = "mongo" if meta and not df.empty and stamp != "csv" else "csv"
        self._cache[kind] = (stamp, df)
        return df

    def available(self):
        return {k: self.load(k) for k in KINDS if not self.load(k).empty}

    def status(self):
        out = {}
        for k in KINDS:
            df = self.load(k)
            out[k] = {"rows": int(len(df)), "source": df.attrs.get("source"),
                      "months": sorted(int(x) for x in df.ym.unique()) if len(df) else []}
        return out

    def districts(self):
        for df in self.available().values():
            return sorted(df.district.unique())
        return []

    def umd_map(self):
        m = {}
        for df in self.available().values():
            for d, u in df[["district", "umd"]].drop_duplicates().itertuples(index=False):
                m.setdefault(d, set()).add(u)
        return m

    def scope_frame(self, kind, district=None, umd=None, name=None):
        df = self.load(kind)
        if district:
            df = df[df.district == district]
        if umd:
            df = df[df.umd == umd]
        if name:
            df = df[df.name == name]
        return df

    def provisional(self, kind):
        return S.provisional_months(self.load(kind))

    def scope_stats(self, kind, district=None, umd=None, name=None, persist=False):
        key = (kind, district, umd, name)
        if key in self._stat_cache:
            return self._stat_cache[key]
        d = self.scope_frame(kind, district, umd, name)
        if d.empty:
            return []
        geo = "district" if district is None else ("umd" if umd is None and name is None else None)
        rows = S.monthly_stats(d, geo, self.provisional(kind), index_ok=True)
        self._stat_cache[key] = rows
        if persist:
            self.save_stats(kind, district, umd, name, rows)
        return rows

    def save_stats(self, kind, district, umd, name, rows):
        sid = "|".join(str(x or "-") for x in (kind, district, umd, name))
        self.db[C_STATS].update_one(
            {"_id": sid},
            {"$set": {"kind": kind, "district": district, "umd": umd, "name": name, "months": rows,
                      "outlook": S.outlook(rows), "updated_at": datetime.now(timezone.utc)}},
            upsert=True)

    def log_prediction(self, doc):
        try:
            self.db[C_PRED].insert_one({**doc, "created_at": datetime.now(timezone.utc)})
        except Exception as e:  # 기록 실패가 답변을 막지 않도록
            print("예측 기록 저장 실패:", e)

    def model_eval(self, kind):
        d = self.db[C_MODELS].find_one({"_id": kind})
        if d:
            return d.get("eval")
        if EVAL_PATH.exists():
            return json.loads(EVAL_PATH.read_text(encoding="utf-8")).get(kind)
        return None
