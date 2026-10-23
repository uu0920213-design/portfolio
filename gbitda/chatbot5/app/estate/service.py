"""질문 → 조회/통계/예측 → 챗봇 답변(텍스트 + 카드 데이터)."""
import re

from . import nlu, predictor
from . import stats as S
from .config import KINDS, SQM_PER_PYEONG

PYEONG = SQM_PER_PYEONG


# ---------- 표시용 포맷 ----------
def won(v):
    """만원 단위 숫자 → '12억 3,000만원'"""
    if v is None:
        return "-"
    v = int(round(v / 10.0) * 10)
    eok, man = divmod(abs(v), 10000)
    sign = "-" if v < 0 else ""
    if eok and man:
        return f"{sign}{eok}억 {man:,}만원"
    if eok:
        return f"{sign}{eok}억원"
    return f"{sign}{man:,}만원"


def eun(w):
    """'아파트' → '아파트는', '빌라' → '빌라는', '종로구 홍파동' → '종로구 홍파동은'"""
    ch = str(w).strip()[-1:]
    if "가" <= ch <= "힣":
        return f"{w}{'은' if (ord(ch) - 0xAC00) % 28 else '는'}"
    return f"{w}은(는)"


def pct(v, digits=1):
    return "-" if v is None else f"{v:+.{digits}f}%"


def tone(v, eps=0.3):
    if v is None:
        return None
    return "up" if v > eps else ("down" if v < -eps else "flat")


def word(v, eps=0.3):
    return "올랐어요" if v is not None and v > eps else ("내렸어요" if v is not None and v < -eps else "거의 변동이 없어요")


def ym_label(ym):
    return f"{ym // 100}년 {ym % 100}월"


def scope_label(c):
    if c.get("name"):
        return f"{c['district']} {c['name']}"
    if c.get("umd"):
        return f"{c['district']} {c['umd']}"
    return c.get("district") or "서울 전체"


def place_short(c):
    return c.get("umd") or c.get("name") or c.get("district") or "서울"


def kind_label(k):
    return KINDS[k]["label"]


# ---------- 후속 질문 칩 ----------
def chips(c, intent):
    p = place_short(c)
    k = kind_label(c["kind"])
    base = {
        "trades": [f"{p} {k} 지난달보다 얼마나 올랐어?", f"{p} {k} 최근 1년 가격 추이를 그래프로 보여줘",
                   f"{p} {k} 앞으로 집값 방향은?"],
        "mom": [f"{p} {k} 최근 1년 가격 추이를 그래프로 보여줘", f"{p} {k} 최근 6개월 실거래가 알려줘",
                f"{p} {k} 앞으로 집값 방향은?"],
        "trend": [f"{p} {k} 지난달보다 얼마나 올랐어?", f"{p} {k} 앞으로 집값 방향은?",
                  f"{p} {k} 최근 6개월 실거래가 알려줘"],
        "outlook": [f"{p} {k} 최근 1년 가격 추이를 그래프로 보여줘", f"{p} {k} 지난달보다 얼마나 올랐어?",
                    f"{p} 84㎡ 10층 {k} 예상 매매가는?"],
        "predict": [f"{p} {k} 최근 6개월 실거래가 알려줘", f"{p} {k} 앞으로 집값 방향은?",
                    f"{p} {'빌라' if c['kind'] == 'apartment' else '아파트'} 시세는?"],
    }
    return base.get(intent, base["trades"])


def ask(text, suggestions=None, title="조금 더 알려주세요"):
    return {"type": "ask", "title": title, "notes": [], "suggestions": suggestions or []}, text


def window_rows(rows, months, default=6):
    """최근 months개월 행. 보유 개월보다 많이 요청하면 전체를 반환(short=True)."""
    n = months or default
    win = rows[-n:]
    return win, bool(months and months > len(rows))


# ---------- 의도별 답변 ----------
def do_trades(store, c, months):
    rows = store.scope_stats(c["kind"], c["district"], c.get("umd"), c.get("name"), persist=True)
    win, short = window_rows(rows, months)
    d = store.scope_frame(c["kind"], c["district"], c.get("umd"), c.get("name"))
    d = d[d.ym.isin([r["ym"] for r in win])]
    n = len(d)
    med, mean = float(d.price.median()), float(d.price.mean())
    m2 = float(d.price_m2.median())
    last = win[-1]
    sc = scope_label(c)
    text = (f"{sc} {kind_label(c['kind'])} 최근 {len(win)}개월({win[0]['label']}~{last['label']}) 실거래는 "
            f"{n:,}건이에요. 중위 매매가는 {won(med)}, 평균은 {won(mean)}입니다.")
    notes = []
    if short:
        notes.append(f"요청하신 {months}개월 중 보유 데이터는 {len(win)}개월이라 가능한 기간만 보여드려요.")
    notes += provisional_note(win)
    if n < 30:
        notes.append("거래 건수가 적어 평균·중위가가 크게 흔들릴 수 있어요." +
                     (f" {c['district']} 전체로 물어보면 더 안정적이에요." if c.get("umd") or c.get("name") else ""))
    card = {
        "type": "trades", "title": f"{sc} {kind_label(c['kind'])} 실거래", "subtitle": f"{win[0]['label']} ~ {last['label']}",
        "metrics": [
            {"label": "거래 건수", "value": f"{n:,}건"},
            {"label": "중위 매매가", "value": won(med)},
            {"label": "평균 매매가", "value": won(mean)},
            {"label": "3.3㎡당 중위(전용)", "value": won(m2 * PYEONG)},
        ],
        "charts": [{"type": "bar", "title": "월별 중위 매매가", "format": "won",
                    "labels": [r["label"][2:] for r in win], "series": [{"name": "중위 매매가",
                    "values": [r["median"] for r in win]}], "flags": [r["provisional"] for r in win]}],
        "notes": notes,
    }
    if c.get("district"):
        recent = d.sort_values(["deal_date"], ascending=False).head(10)
        card["table"] = {"title": "최근 거래 10건", "columns": ["거래일", "단지/동", "면적", "층", "매매가"],
                         "rows": [[r.deal_date[2:], f"{(r.name if isinstance(r.name, str) and r.name else r.umd)}",
                                   f"{r.area:g}㎡", "-" if r.floor != r.floor else f"{int(r.floor)}층", won(r.price)]
                                  for r in recent.itertuples()]}
    return card, text


def provisional_note(rows):
    prov = [r["label"] for r in rows if r["provisional"]]
    if prov:
        return [f"{', '.join(prov)}은(는) 전체 거래 건수가 평소보다 적어 신고가 덜 반영된 잠정치일 수 있어요."]
    return []


def do_mom(store, c):
    rows = store.scope_stats(c["kind"], c["district"], c.get("umd"), c.get("name"), persist=True)
    pm = S.pick_mom(rows)
    sc = scope_label(c)
    if not pm:
        return ask(f"{eun(sc)} 비교할 수 있는 두 달 이상의 데이터가 없어요.")
    a, b = pm["latest"], pm["prev"]
    ch = S.change_pair(a, b)
    main = ch["main"]
    basis = "면적·연식·층·동네 구성을 보정한 가격지수" if ch["basis"] == "adj" else "중위 매매가"
    text = (f"{eun(sc + ' ' + kind_label(c['kind']))} {ym_label(a['ym'])}에 {ym_label(b['ym'])}보다 "
            f"{pct(main)} {word(main)}. ({basis} 기준)")
    if ch["basis"] == "adj":
        text += f" 단순 중위가로는 {pct(ch['median'])}입니다."
    notes = []
    gap = (a["ym"] // 100 * 12 + a["ym"] % 100) - (b["ym"] // 100 * 12 + b["ym"] % 100)
    if gap > 1:
        notes.append(f"바로 전달({gap - 1}개월 사이) 거래가 없어 {b['label']}과 비교했어요.")
    if ch["basis"] == "adj" and ch["median"] is not None and main is not None and abs(ch["median"] - main) >= 3:
        notes.append("단순 중위가와 보정 변화율의 차이가 큰 건, 그 달에 거래된 집의 면적·연식·위치 구성이 달랐기 때문일 수 있어요.")
    if a["provisional"]:
        notes.append(f"{a['label']}은 신고가 덜 반영된 잠정치라 확정 달 기준도 함께 보여드려요.")
        if pm["confirmed"]:
            cc = S.change_pair(pm["confirmed"]["latest"], pm["confirmed"]["prev"])
            notes.append(f"확정 달 기준: {pm['confirmed']['latest']['label']}은 {pm['confirmed']['prev']['label']}보다 "
                         f"{pct(cc['main'])}")
    if a["low_sample"] or b["low_sample"]:
        notes.append("거래 건수가 30건 미만인 달이 있어 변화율이 크게 흔들릴 수 있어요.")
    win = rows[-7:]
    card = {
        "type": "mom", "title": f"{sc} {kind_label(c['kind'])} 전월 대비", "subtitle": f"{b['label']} → {a['label']}",
        "metrics": [
            {"label": "가격 변화(보정)" if ch["basis"] == "adj" else "가격 변화", "value": pct(main), "tone": tone(main)},
            {"label": "단순 중위가 변화", "value": pct(ch["median"]), "tone": tone(ch["median"])},
            {"label": f"{a['label']} 중위가", "value": won(a["median"]), "sub": f"{a['n']:,}건"},
            {"label": f"{b['label']} 중위가", "value": won(b["median"]), "sub": f"{b['n']:,}건"},
        ],
        "charts": [{"type": "bar", "title": "월별 가격 변화율(%)", "format": "pct",
                    "labels": [r["label"][2:] for r in win[1:]],
                    "series": [{"name": "전월 대비", "values": [r["mom_adj"] if r["mom_adj"] is not None else r["mom_median"]
                                                              for r in win[1:]]}],
                    "flags": [r["provisional"] for r in win[1:]]}],
        "notes": notes,
    }
    return card, text


def do_trend(store, c, months):
    rows = store.scope_stats(c["kind"], c["district"], c.get("umd"), c.get("name"), persist=True)
    sc = scope_label(c)
    win, short = window_rows(rows, months, 12)
    if len(win) < 2:
        return ask(f"{eun(sc)} 추이를 그릴 만큼 데이터가 없어요.")
    conf = [r for r in win if not r["provisional"] and r["adj_index"]]
    tot, tot_label = None, "기간 변화(보정)"
    if len(conf) >= 2:
        tot = (conf[-1]["adj_index"] / conf[0]["adj_index"] - 1) * 100
    else:
        cm = [r for r in win if not r["provisional"]]
        if len(cm) >= 2:
            tot, tot_label = (cm[-1]["median"] / cm[0]["median"] - 1) * 100, "기간 변화(중위가)"
            conf = cm
    notes = []
    if short:
        notes.append(f"요청하신 {months or 12}개월 중 보유 데이터는 {len(win)}개월({win[0]['label']}~{win[-1]['label']})이라 "
                     "가능한 전체 기간을 보여드려요.")
    notes += provisional_note(win)
    if sum(1 for r in win if r["adj_index"]) >= 3:
        notes.append("지수는 면적·연식·층·동네 구성을 보정한 값이며 첫 달을 100으로 맞췄어요.")
    if c["kind"] == "villa":
        notes.append("빌라는 건물·상태별 편차가 커서 아파트보다 월별 변동폭이 크게 나올 수 있어요.")
    if any(r["low_sample"] for r in win):
        notes.append("거래 건수가 30건 미만인 달은 값이 흔들릴 수 있어요.")
    first, last = win[0], win[-1]
    text = (f"{sc} {kind_label(c['kind'])} {first['label']}~{last['label']} 가격 추이예요. "
            f"중위 매매가는 {won(first['median'])} → {won(last['median'])}")
    if tot is not None:
        what = "구성 보정 지수는" if tot_label == "기간 변화(보정)" else "중위가는"
        text += f", {what} 확정 월 기준 {conf[0]['label']} 대비 {conf[-1]['label']}에 {pct(tot)} 변했어요."
    else:
        text += "."
    labels = [r["label"][2:] for r in win]
    charts = [{"type": "line", "title": "월별 중위 매매가", "format": "won", "labels": labels,
               "series": [{"name": "중위 매매가", "values": [r["median"] for r in win]}],
               "flags": [r["provisional"] for r in win]}]
    if sum(1 for r in win if r["adj_index"]) >= 3:
        charts.append({"type": "line", "title": "보정 가격지수 (첫 달=100)", "format": "index", "labels": labels,
                       "series": [{"name": "가격지수", "values": [r["adj_index"] for r in win]}],
                       "flags": [r["provisional"] for r in win]})
    card = {
        "type": "trend", "title": f"{sc} {kind_label(c['kind'])} 가격 추이", "subtitle": f"{first['label']} ~ {last['label']}",
        "metrics": [
            {"label": tot_label, "value": pct(tot), "tone": tone(tot, 0.5)},
            {"label": "최근 중위가", "value": won(last["median"]), "sub": last["label"]},
            {"label": "총 거래", "value": f"{sum(r['n'] for r in win):,}건"},
        ],
        "charts": charts,
        "table": {"title": "월별 요약", "columns": ["월", "거래", "중위가", "지수", "전월비"],
                  "rows": [[r["label"], f"{r['n']:,}", won(r["median"]),
                            "-" if not r["adj_index"] else f"{r['adj_index']:.1f}",
                            pct(r["mom_adj"] if r["mom_adj"] is not None else r["mom_median"]) +
                            (" *" if r["provisional"] else "")] for r in win]},
        "notes": notes,
    }
    return card, text


def do_outlook(store, c):
    rows = store.scope_stats(c["kind"], c["district"], c.get("umd"), c.get("name"), persist=True)
    sc = scope_label(c)
    o = S.outlook(rows)
    if o["direction"] == "판단 보류":
        return ask(f"{eun(sc)} 방향을 설명할 만큼의 월 데이터가 부족해요. ({o['reason']})")
    sym = {"상승": "상승세", "하락": "하락세", "보합": "보합권"}[o["direction"]]
    text = (f"{eun(sc + ' ' + kind_label(c['kind']))} 최근 {o['n_months']}개월({o['from']}~{o['to']}) {sym}예요. "
            f"월평균 {pct(o['monthly_pct'], 2)}씩 움직였고, 방향에 대한 통계적 확신은 '{o['confidence']}'입니다. "
            "이건 지금까지 흐름을 설명한 것이지, 앞으로의 가격을 예측한 값은 아니에요.")
    win = [r for r in rows if not r["provisional"]][-8:]
    use_idx = sum(1 for r in win if r["adj_index"]) >= 3
    notes = [
        f"방향은 최근 {o['n_months']}개월 {o['basis']}의 추세선으로 판단했고, 월 {pct(o['ci'], 2)}~{pct(o['ci_hi'], 2)} 범위에서 불확실해요."
        if o.get("ci") is not None else "추세 불확실성 범위를 계산할 수 없었어요.",
        "보유한 데이터가 2026년 한 해(약 9개월)뿐이라 계절성·금리·정책 변화는 반영되지 않았어요.",
        "학습된 가격 모델은 '현재 가격 추정용'이라 미래 시점 가격을 예측하지 못해요. 투자 판단의 근거로 쓰지 마세요.",
    ]
    notes += provisional_note(rows[-3:])
    card = {
        "type": "outlook", "title": f"{sc} {kind_label(c['kind'])} 가격 방향", "subtitle": f"최근 {o['n_months']}개월 추세",
        "metrics": [
            {"label": "최근 방향", "value": o["direction"], "tone": {"상승": "up", "하락": "down"}.get(o["direction"], "flat")},
            {"label": "월평균 변화", "value": pct(o["monthly_pct"], 2), "tone": tone(o["monthly_pct"])},
            {"label": "확신도", "value": o["confidence"], "sub": f"t={o['t']:.1f}"},
        ],
        "charts": [{"type": "line", "title": "보정 가격지수" if use_idx else "㎡당 중위 매매가",
                    "format": "index" if use_idx else "won",
                    "labels": [r["label"][2:] for r in win],
                    "series": [{"name": "지수", "values": [r["adj_index"] if use_idx else r["median_m2"] for r in win]}],
                    "flags": [False] * len(win)}],
        "notes": notes,
    }
    return card, text


def do_predict(store, c):
    kind = c["kind"]
    if not c.get("district"):
        return ask("예상 매매가를 계산하려면 최소한 지역(구)을 알려주세요. 면적·층·준공연도까지 알려주면 더 정확해요.",
                   [f"종로구 84㎡ 10층 2015년식 {kind_label(kind)} 예상 매매가는?",
                    f"마포구 59㎡ {kind_label(kind)} 예상 매매가는?",
                    f"송파구 25평 {kind_label(kind)} 예상 매매가는?"], title="조건이 필요해요")
    build_year = c.get("build_year")
    if build_year is None and c.get("age") is not None:
        build_year = int(store.load(kind).ym.max() // 100) - c["age"]
    area = c.get("area")
    if c.get("name") and area is None:
        d = store.scope_frame(kind, c["district"], c.get("umd"), c["name"])
        if len(d):
            area = float(d.area.mode().iloc[0])
    r = predictor.predict(store, kind, c["district"], c.get("umd"), area, c.get("floor"), build_year)
    if not r:
        return ask(f"{c['district']}의 {kind_label(kind)} 거래 데이터가 없어요.")
    ev = (store.model_eval(kind) or {}).get("time_backtest_rf_jan_jun_to_jul_sep") or {}
    med_e = (ev.get("median_ape") or 10) / 100
    p75 = (ev.get("p75_ape") or 20) / 100
    est = r["estimate"]
    comps = predictor.comparables(store, kind, c["district"], c.get("umd"), r["area"], r["floor"], r["build_year"])
    comp_med = float(comps.price.median()) if len(comps) else None
    sc = f"{c['district']}" + (f" {c['umd']}" if c.get("umd") else "")
    cond = f"전용 {r['area']:g}㎡ · {r['floor']:g}층 · {int(r['build_year'])}년 준공"
    text = (f"{sc} {kind_label(kind)} ({cond}) 예상 매매가는 약 {won(est)}이에요. "
            f"보통 ±{med_e * 100:.0f}% 안팎, 넓게 보면 {won(est * (1 - p75))}~{won(est * (1 + p75))} "
            f"(과거 검증에서 4건 중 3건이 들어간 범위)입니다. {ym_label(r['basis_ym'])} 기준 현재 시세 추정이고 미래 가격 예측은 아니에요.")
    notes = list(r["assumptions"])
    if c.get("area_from_pyeong"):
        notes.append(f"{c['area_from_pyeong']:g}평은 공급면적 평형으로 보고 전용면적 약 {r['area']:g}㎡로 환산했어요. "
                     "전용면적을 직접 알려주시면 더 정확해요.")
    if comp_med and abs(est / comp_med - 1) > 0.3:
        notes.append("모델 추정치와 비슷한 최근 거래의 중위가 차이가 큽니다. 비슷한 단지·동의 실거래도 같이 확인해 주세요.")
    if kind == "villa":
        notes.append("빌라는 단지·대지지분·상태에 따라 가격 편차가 커서 아파트보다 오차가 큽니다.")
    notes.append(f"학습 데이터는 2026년 서울 실거래이며, 이 모델의 시간 분리 검증 오차(중앙값)는 {med_e * 100:.0f}%예요.")
    card = {
        "type": "predict", "title": f"{sc} {kind_label(kind)} 예상 매매가", "subtitle": cond,
        "metrics": [
            {"label": "예상 매매가", "value": won(est), "big": True},
            {"label": "일반 오차 범위", "value": f"{won(est * (1 - med_e))} ~ {won(est * (1 + med_e))}"},
            {"label": "넓은 범위(75%)", "value": f"{won(est * (1 - p75))} ~ {won(est * (1 + p75))}"},
            {"label": "비슷한 최근 거래 중위", "value": won(comp_med), "sub": f"{len(comps)}건"},
        ],
        "notes": notes,
    }
    if len(comps):
        card["table"] = {"title": "비슷한 최근 거래", "columns": ["거래일", "단지/동", "면적", "층", "매매가"],
                         "rows": [[x.deal_date[2:], (x.name if isinstance(x.name, str) and x.name else x.umd),
                                   f"{x.area:g}㎡", "-" if x.floor != x.floor else f"{int(x.floor)}층", won(x.price)]
                                  for x in comps.itertuples()]}
    store.log_prediction({"kind": kind, "district": c["district"], "umd": c.get("umd"), "input": {
        "area": r["area"], "floor": r["floor"], "build_year": r["build_year"]}, "estimate": est,
        "basis_ym": r["basis_ym"], "comp_median": comp_med, "model": "RandomForest"})
    return card, text


# ---------- 진입점 ----------
def _norm(s):
    return re.sub(r"[\s()·\-]", "", str(s))


_names = {}
# 두 글자 단지명 중 브랜드/시공사 이름과 겹치는 것은 단지 검색에서 제외
GENERIC_NAMES = {"현대", "삼성", "대림", "롯데", "한양", "우성", "신동", "동아", "주공", "두산", "쌍용", "금호", "벽산",
                 "대우", "한신", "진흥", "경남", "동부", "태영", "풍림", "성원", "청구", "삼호", "신안", "건영",
                 "서울", "한강", "강남", "강북", "강서", "강동"} | set(nlu.SHORT_GU)


def _name_index(store, kind):
    """(단지명 → 가장 거래가 많은 구) 인덱스. 구 이름이 없어도 단지명으로 지역을 찾는다."""
    df = store.load(kind)
    key = (kind, len(df))
    if key not in _names:
        g = df.dropna(subset=["name"]).groupby(["name", "district"]).size().reset_index(name="n")
        g = g.sort_values("n", ascending=False).drop_duplicates("name")
        idx = []
        for r in g.itertuples():
            for alias in {_norm(r.name), _norm(re.sub(r"\(.*?\)", "", r.name))}:   # '경희궁자이(2단지)' → '경희궁자이'도 인식
                if len(alias) >= 3 or (len(alias) == 2 and alias not in GENERIC_NAMES):
                    idx.append((alias, r.name, r.district))
        _names[key] = idx
    return _names[key]


def find_complex(store, kind, district, text):
    """아파트 단지명을 질문에서 찾는다 → (단지명, 구) / 없으면 (None, None)"""
    if kind != "apartment":
        return None, None
    nt = _norm(text)
    best = None
    for nn, n, d in _name_index(store, kind):
        if nn in nt and (not district or d == district) and (best is None or len(nn) > len(best[0])):
            best = (nn, n, d)
    if best:
        return best[1], best[2]
    return None, None


def answer(store, message, ctx):
    """부동산 질문이면 {text, estate, context}, 아니면 None."""
    ctx = dict(ctx or {})
    if not store.available():
        t = message
        if any(w in t for w in nlu.STRONG_PRICE):
            return {"text": "부동산 데이터가 아직 준비되지 않았어요. 관리자에게 데이터 적재를 요청해 주세요.",
                    "estate": {"type": "ask", "title": "데이터 준비 중", "notes": [], "suggestions": []},
                    "context": ctx}
        return None
    slots = nlu.parse(message, store.umd_map())
    if not nlu.is_estate_message(message, slots, ctx):
        return None

    if slots.get("ambiguous_umd"):
        u, ds = slots["ambiguous_umd"]
        card, text = ask(f"'{u}'은(는) 여러 구에 있어요. 어느 구인지 알려주세요.",
                         [f"{d} {u} 실거래가 알려줘" for d in ds[:4]], title="지역을 골라주세요")
        return {"text": text, "estate": card, "context": ctx}

    c = {k: v for k, v in ctx.items() if k not in ("last_intent",)}
    placed = bool(slots.get("district") or slots.get("umd"))
    if slots.get("seoul") and not placed:
        for k in ("district", "umd", "name"):
            c.pop(k, None)
    if placed:
        if slots.get("district") != c.get("district"):
            c.pop("umd", None)
        c.pop("name", None)
        if "umd" not in slots:
            c.pop("umd", None)
        c["district"] = slots["district"]
        if "umd" in slots:
            c["umd"] = slots["umd"]
        for k in ("area", "floor", "build_year", "age"):   # 새 지역을 물으면 이전 조건은 초기화
            if k not in slots and slots.get("intent") != "predict":
                pass
    c["kind"] = slots.get("kind") or c.get("kind") or "apartment"
    for k in ("area", "floor", "build_year", "age", "area_from_pyeong"):
        if k in slots:
            c[k] = slots[k]
        if k == "area" and k in slots and "area_from_pyeong" not in slots:
            c.pop("area_from_pyeong", None)
    c.setdefault("district", None)
    name, name_gu = find_complex(store, c["kind"], c["district"], message)
    if name:
        c["name"] = name
        c["district"] = c.get("district") or name_gu
        c.pop("umd", None) if "umd" not in slots else None
    elif slots.get("kind") and c.get("name") and slots["kind"] != ctx.get("kind"):
        c.pop("name", None)

    intent = slots.get("intent") or ctx.get("last_intent") or "trades"
    months = slots.get("months")
    notes_prefix = []
    if not c.get("district") and not c.get("umd") and intent != "predict":
        notes_prefix.append("지역을 말씀하지 않으셔서 서울 전체 기준으로 보여드려요.")

    if not store.scope_frame(c["kind"], c["district"], c.get("umd"), c.get("name")).shape[0]:
        card, text = ask(f"{scope_label(c)} {kind_label(c['kind'])} 거래 데이터를 찾지 못했어요.",
                         [f"{c['district'] or '종로구'} {kind_label(c['kind'])} 최근 6개월 실거래가 알려줘"])
    elif intent == "predict":
        card, text = do_predict(store, c)
    elif intent == "mom":
        card, text = do_mom(store, c)
    elif intent == "trend":
        card, text = do_trend(store, c, months)
    elif intent == "outlook":
        card, text = do_outlook(store, c)
    else:
        intent = "trades"
        card, text = do_trades(store, c, months)

    if card.get("type") != "ask":
        card["notes"] = notes_prefix + card.get("notes", [])
        card["scope"] = {"kind": c["kind"], "district": c.get("district"), "umd": c.get("umd"), "name": c.get("name")}
        card["suggestions"] = chips(c, intent)
        c["last_intent"] = intent
    else:
        c["last_intent"] = ctx.get("last_intent")
    return {"text": text, "estate": card, "context": c}
