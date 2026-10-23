"""부동산 분석 REST API (2~5단계: 지역·기간 조회, 월별 통계, 예측)."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from . import predictor, service
from . import stats as S
from .config import KINDS


class PredictRequest(BaseModel):
    kind: str = "apartment"
    district: str
    umd: Optional[str] = None
    area: Optional[float] = Field(default=None, gt=0, description="전용면적(㎡)")
    floor: Optional[int] = None
    build_year: Optional[int] = None


def make_router(store):
    r = APIRouter(prefix="/estate", tags=["estate"])

    def _kind(k):
        if k not in KINDS:
            raise HTTPException(400, f"kind는 {list(KINDS)} 중 하나여야 합니다.")
        return k

    @r.get("/status")
    def status():
        return store.status()

    @r.get("/districts")
    def districts():
        return {"districts": store.districts(), "umd": {d: sorted(u) for d, u in store.umd_map().items()}}

    @r.get("/trades")
    def trades(kind: str = "apartment", district: Optional[str] = None, umd: Optional[str] = None,
               months: int = Query(6, ge=1, le=36), limit: int = Query(50, ge=1, le=500)):
        """2단계: 지역·기간별 실거래 조회"""
        _kind(kind)
        d = store.scope_frame(kind, district, umd)
        if d.empty:
            raise HTTPException(404, "해당 조건의 거래가 없습니다.")
        yms = sorted(d.ym.unique())[-months:]
        d = d[d.ym.isin(yms)].sort_values("deal_date", ascending=False)
        return {"kind": kind, "district": district, "umd": umd, "months": [int(x) for x in yms],
                "count": int(len(d)), "median": float(d.price.median()), "mean": float(d.price.mean()),
                "items": [{"deal_date": x.deal_date, "district": x.district, "umd": x.umd,
                           "name": x.name if isinstance(x.name, str) else None, "area": x.area,
                           "floor": None if x.floor != x.floor else int(x.floor), "price": x.price}
                          for x in d.head(limit).itertuples()]}

    @r.get("/monthly")
    def monthly(kind: str = "apartment", district: Optional[str] = None, umd: Optional[str] = None):
        """3~4단계: 월별 평균/중위 · 전월 대비 · 보정 가격지수 · 추세(차트 데이터)"""
        _kind(kind)
        rows = store.scope_stats(kind, district, umd, persist=True)
        if not rows:
            raise HTTPException(404, "해당 조건의 데이터가 없습니다.")
        return {"kind": kind, "district": district, "umd": umd, "months": rows, "outlook": S.outlook(rows)}

    @r.post("/predict")
    def predict(req: PredictRequest):
        """5단계: 예상 매매가(현재 시세 추정)"""
        _kind(req.kind)
        res = predictor.predict(store, req.kind, req.district, req.umd, req.area, req.floor, req.build_year)
        if not res:
            raise HTTPException(404, "해당 지역 데이터가 없습니다.")
        return {**res, "estimate_text": service.won(res["estimate"]), "evaluation": store.model_eval(req.kind)}

    return r
