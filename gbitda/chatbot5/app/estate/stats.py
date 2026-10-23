"""월별 통계 · 구성효과를 보정한 가격지수 · 추세(전망) 계산."""
import math

import numpy as np
import pandas as pd


def provisional_months(df: pd.DataFrame, recent: int = 3, ratio: float = 0.7):
    """전체 거래건수가 평소보다 현저히 적은 최근 달(신고 지연 가능) 집합."""
    c = df.groupby("ym").size().sort_index()
    if len(c) < recent + 3:
        return set()
    ref = float(c.iloc[:-recent].median())
    return {int(ym) for ym, n in c.iloc[-recent:].items() if n < ref * ratio}


def adjusted_index(d: pd.DataFrame, geo_col=None, min_month_n=8, min_total=60):
    """헤도닉 회귀로 면적·연식·층·동네 구성 변화를 통제한 월별 가격지수(첫 달=100)."""
    d = d[(d.area > 0) & (d.price > 0)]
    yms = sorted(d.ym.unique())
    if len(yms) < 2 or len(d) < min_total:
        return {}
    age = d.age.fillna(d.age.median() if d.age.notna().any() else 20).clip(0, 60)
    fl = d.floor.fillna(d.floor.median() if d.floor.notna().any() else 5).clip(-1, 30)
    cols = [np.ones(len(d)), np.log(d.area.values), age.values, fl.values]
    if geo_col is not None and d[geo_col].nunique() > 1:
        g = pd.get_dummies(d[geo_col], drop_first=True).astype(float)
        cols += [g[c].values for c in g.columns]
    m = pd.get_dummies(d.ym, drop_first=True).astype(float)
    mcols = list(m.columns)
    cols += [m[c].values for c in mcols]
    X = np.column_stack(cols)
    y = np.log(d.price.values)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    base = len(cols) - len(mcols)
    cnt = d.groupby("ym").size()
    out = {int(yms[0]): 100.0}
    for i, c in enumerate(mcols):
        out[int(c)] = float(100 * math.exp(beta[base + i]))
    return {ym: (v if cnt.get(ym, 0) >= min_month_n else None) for ym, v in out.items()}


def monthly_stats(d: pd.DataFrame, geo_col=None, provisional=frozenset(), index_ok=True):
    rows = []
    idx = adjusted_index(d, geo_col) if index_ok else {}
    prev_adj = prev_med = None
    for ym, g in d.groupby("ym"):
        ym = int(ym)
        n = len(g)
        med = float(g.price.median())
        r = {
            "ym": ym, "label": f"{ym // 100}-{ym % 100:02d}", "n": n,
            "mean": float(g.price.mean()), "median": med,
            "median_m2": float(g.price_m2.median()),
            "adj_index": idx.get(ym),
            "provisional": ym in provisional,
            "low_sample": n < 30,
        }
        r["mom_median"] = (med / prev_med - 1) * 100 if prev_med else None
        a = r["adj_index"]
        r["mom_adj"] = (a / prev_adj - 1) * 100 if (a and prev_adj) else None
        prev_med = med
        prev_adj = a if a else prev_adj
        rows.append(r)
    return rows


def pick_mom(rows):
    """최신 달과 직전 달 비교. 최신 달이 잠정이면 확정 달 기준도 함께 반환."""
    if len(rows) < 2:
        return None
    latest, prev = rows[-1], rows[-2]
    res = {"latest": latest, "prev": prev, "confirmed": None}
    if latest["provisional"]:
        conf = [r for r in rows if not r["provisional"]]
        if len(conf) >= 2:
            res["confirmed"] = {"latest": conf[-1], "prev": conf[-2]}
    return res


def _pct(a, b):
    return (a / b - 1) * 100 if a and b else None


def change_pair(a, b):
    """두 달 행(a=최근, b=이전) 사이 변화율: 보정지수 우선, 없으면 중위가."""
    adj = _pct(a.get("adj_index"), b.get("adj_index"))
    med = _pct(a["median"], b["median"])
    return {"adj": adj, "median": med, "main": adj if adj is not None else med,
            "basis": "adj" if adj is not None else "median"}


def outlook(rows, window=6):
    """최근 확정 월들의 로그가격 기울기로 방향을 설명(예측 아님)."""
    conf = [r for r in rows if not r["provisional"]]
    use_adj = sum(1 for r in conf if r["adj_index"]) >= 4
    pts = [(i, r["adj_index"] if use_adj else r["median_m2"]) for i, r in enumerate(conf)]
    pts = [(i, v) for i, v in pts if v][-window:]
    n = len(pts)
    if n < 4:
        return {"direction": "판단 보류", "n_months": n, "reason": "비교할 월 데이터가 4개월 미만입니다."}
    x = np.array([p[0] for p in pts], float)
    y = np.log([p[1] for p in pts])
    xm = x - x.mean()
    slope = float((xm * (y - y.mean())).sum() / (xm ** 2).sum())
    resid = y - (y.mean() + slope * xm)
    se = float(math.sqrt((resid ** 2).sum() / max(n - 2, 1) / (xm ** 2).sum())) if n > 2 else float("inf")
    t = slope / se if se and se != float("inf") and se > 0 else 0.0
    monthly = (math.exp(slope) - 1) * 100
    if abs(t) < 1.5 or abs(monthly) < 0.3:
        direction = "보합"
    else:
        direction = "상승" if slope > 0 else "하락"
    conf_level = "높음" if (n >= 6 and abs(t) >= 3) else ("보통" if abs(t) >= 1.5 else "낮음")
    return {
        "direction": direction, "monthly_pct": monthly, "n_months": n, "t": t,
        "ci": (math.exp(slope - 1.96 * se) - 1) * 100 if se != float("inf") else None,
        "ci_hi": (math.exp(slope + 1.96 * se) - 1) * 100 if se != float("inf") else None,
        "confidence": conf_level, "basis": "보정지수" if use_adj else "㎡당 중위가",
        "from": conf[-n]["label"] if n <= len(conf) else conf[0]["label"], "to": conf[-1]["label"],
    }
