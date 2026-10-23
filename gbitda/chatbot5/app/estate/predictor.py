"""학습된 RandomForest 모델로 '현재 시점' 예상 매매가를 추정하고 유사 거래를 함께 제시."""
import numpy as np
import pandas as pd

from .config import KINDS, MODEL_DIR

_models = {}


def get_model(kind):
    if kind not in _models:
        import joblib
        _models[kind] = joblib.load(MODEL_DIR / KINDS[kind]["model"])
    return _models[kind]


def _frame(rows):
    return pd.DataFrame(rows)[["excluUseAr", "buildYear", "buildingAge", "floor", "dealYear", "dealMonth",
                               "districtName", "umdNm"]]


def predict(store, kind, district, umd=None, area=None, floor=None, build_year=None):
    """반환: dict(estimate, assumptions, per_umd...). 모델은 학습 기간 안의 가격 수준을 반영하므로
    '가장 최근 데이터 월' 기준 현재가 추정입니다(미래 시점 예측 아님)."""
    df = store.load(kind)
    dd = df[df.district == district]
    if dd.empty:
        return None
    latest = int(df.ym.max())
    last3 = sorted(df.ym.unique())[-3:]
    recent = dd[dd.ym.isin(last3)]
    if recent.empty:
        recent = dd
    assumptions = []
    if area is None:
        area = float(round(recent.area.median()))
        assumptions.append(f"전용면적 미입력 → {district} 최근 거래 중앙값 {area:g}㎡로 가정")
    near = recent[(recent.area - area).abs() <= area * 0.15]
    base = near if len(near) >= 5 else recent
    if floor is None:
        floor = float(round(base.floor.median()))
        assumptions.append(f"층 미입력 → {floor:g}층으로 가정")
    if build_year is None:
        build_year = float(round(base.build_year.median()))
        assumptions.append(f"준공연도 미입력 → {build_year:g}년으로 가정")
    y, m = latest // 100, latest % 100
    age = max(0, y - build_year)

    umds = [umd] if umd else None
    if umds is None:
        cnt = recent.groupby("umd").size().sort_values(ascending=False)
        umds = list(cnt.index)
        weights = (cnt / cnt.sum()).values
        assumptions.append(f"동 미입력 → {district} 거래량 비중으로 가중 평균 (동을 알려주시면 더 정확해요)")
    else:
        weights = np.array([1.0])
    # '84㎡'처럼 딱 떨어지는 입력은 실제 거래(84.9㎡ 등)와 달라 트리 모델의 분기점을 벗어날 수 있어,
    # 해당 지역에서 실제로 많이 거래된 비슷한 면적들로 나눠 계산한 뒤 거래량 가중 평균을 쓴다.
    pool = dd[(dd.area - area).abs() <= max(1.5, area * 0.03)]
    if umd:
        pool = pool[pool.umd == umd] if (pool.umd == umd).sum() >= 5 else pool
    ac = pool.area.round(2).value_counts().head(5)
    if len(ac) and not (ac.index == area).all():
        areas, aw = list(ac.index), (ac / ac.sum()).values
        assumptions.append(f"입력 면적 {area:g}㎡ → 실제 거래가 많은 {', '.join(f'{a:g}' for a in areas[:3])}㎡ 등으로 맞춰 계산")
    else:
        areas, aw = [area], np.array([1.0])
    rows, wts = [], []
    for u, w1 in zip(umds, weights):
        for a, w2 in zip(areas, aw):
            rows.append(dict(excluUseAr=float(a), buildYear=build_year, buildingAge=age, floor=floor, dealYear=y,
                             dealMonth=m, districtName=district, umdNm=u))
            wts.append(w1 * w2)
    preds = get_model(kind).predict(_frame(rows))
    est = float(np.dot(preds, np.array(wts) / np.sum(wts)))
    return {"estimate": est, "area": area, "floor": floor, "build_year": build_year, "age": age,
            "basis_ym": latest, "umd": umd, "assumptions": assumptions}


def comparables(store, kind, district, umd, area, floor, build_year, n=5):
    df = store.load(kind)
    d = df[(df.district == district) & df.ym.isin(sorted(df.ym.unique())[-3:])]
    if d.empty:
        d = df[df.district == district]
    c = d[(d.area - area).abs() <= area * 0.10]
    if umd and len(c[c.umd == umd]) >= 3:
        c = c[c.umd == umd]
    if c.empty:
        return pd.DataFrame()
    age = (df.ym.max() // 100) - build_year if build_year else None
    score = (c.area - area).abs() / area * 5
    if age is not None and c.age.notna().any():
        score += (c.age.fillna(c.age.median()) - age).abs() / 20
    if floor is not None:
        score += (c.floor.fillna(floor) - floor).abs() / 30
    c = c.assign(_s=score).sort_values(["_s", "deal_date"], ascending=[True, False]).head(n)
    return c.sort_values("deal_date", ascending=False)
