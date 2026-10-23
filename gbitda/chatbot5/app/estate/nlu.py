"""한국어 질문에서 지역·유형·기간·면적·의도를 뽑아내는 규칙 기반 해석기."""
import re

from .config import EXCLUSIVE_RATIO, GU, SQM_PER_PYEONG

SHORT_GU = {g[:-1]: g for g in GU if len(g) >= 3}

COURSE_WORDS = ("강의", "클래스", "수강", "커리큘럼", "교육", "신청", "환불", "결제", "강사", "후기")
STRONG_PRICE = ("실거래", "집값", "매매가", "매매 가격", "시세", "거래가", "올랐", "내렸", "오를", "내릴",
                "상승", "하락", "추이", "추세", "그래프", "차트", "예상 매매", "예상가", "예상 가격",
                "매매 예상", "얼마나 올", "얼마나 내", "전망", "거래 내역", "가격 변동", "가격 흐름")
FOLLOWUP = ("그래프", "추이", "지난달", "전월", "올랐", "내렸", "전망", "오를", "내릴", "예상", "실거래",
            "거래", "시세", "가격", "상승", "하락", "흐름", "변동", "방향")


def _find_district(text):
    for g in sorted(GU, key=len, reverse=True):
        if g in text:
            return g
    for s, g in SHORT_GU.items():
        if s in text:
            return g
    return None


def _find_umd(text, district, umd_map):
    """동 이름. 지역이 없으면 한 구에만 있는 동일 때만 확정."""
    names = {}
    for d, us in umd_map.items():
        for u in us:
            names.setdefault(u, set()).add(d)
    found = []
    for u in sorted(names, key=len, reverse=True):
        if len(u) >= 2 and u in text and not any(u in f for f in found):
            found.append(u)
    for u in found:
        ds = names[u]
        if district:
            if district in ds:
                return u, district, None
        elif len(ds) == 1:
            return u, next(iter(ds)), None
        else:
            return None, None, (u, sorted(ds))
    return None, None, None


def parse(message, umd_map):
    t = message.strip()
    s = {}
    district = _find_district(t)
    umd, d2, ambiguous = _find_umd(t, district, umd_map)
    if umd:
        s["umd"], s["district"] = umd, d2
    elif district:
        s["district"] = district
    if ambiguous:
        s["ambiguous_umd"] = ambiguous

    if not district and re.search(r"서울(시| 전체| 전역)?(?!\w*구)", t) and not umd:
        s["seoul"] = True          # '서울 빌라…' → 이전 지역 맥락을 버리고 서울 전체
    if re.search(r"빌라|다세대|연립|villa", t, re.I):
        s["kind"] = "villa"
    elif re.search(r"아파트|apt", t, re.I):
        s["kind"] = "apartment"

    # 기간 ("5년 된", "2015년식" 같은 연식 표현은 제외)
    p = re.sub(r"\d+\s*년\s*(차|된|식|전에|전)", "", t)
    m = re.search(r"(\d+)\s*(개월|달)", p)
    if m:
        s["months"] = int(m.group(1))
    else:
        m = re.search(r"(\d+)\s*년", p)
        if m and int(m.group(1)) < 20 and re.search(r"최근|지난|동안|간|추이|흐름|그래프", p):
            s["months"] = int(m.group(1)) * 12
        elif re.search(r"일년|작년", p):
            s["months"] = 12
        elif "반년" in p:
            s["months"] = 6
        elif "올해" in p:
            s["months"] = 12

    # 면적(㎡ → 전용, 평 → 공급 평형을 전용으로 환산)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|m2|m²|제곱미터)", t, re.I)
    if m:
        s["area"] = float(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*평", t)
        if m:
            s["area"] = round(float(m.group(1)) * SQM_PER_PYEONG * EXCLUSIVE_RATIO, 1)
            s["area_from_pyeong"] = float(m.group(1))
    m = re.search(r"(\d{1,2})\s*층", t)
    if m:
        s["floor"] = int(m.group(1))
    m = re.search(r"((?:19|20)\d{2})\s*년\s*(?:식|준공|건축|에 지어|입주|생|축)", t) or re.search(
        r"(?:준공|건축|입주)\s*((?:19|20)\d{2})", t)
    if m:
        s["build_year"] = int(m.group(1))
    else:
        m = re.search(r"(\d{1,2})\s*년\s*(?:차|된)", t) or re.search(r"연식\s*(\d{1,2})\s*년", t)
        if m:
            s["age"] = int(m.group(1))
        elif "신축" in t:
            s["age"] = 2

    # 의도
    intent = None
    if re.search(r"예상|예측|적정|추정", t) and re.search(r"매매|가격|가치|집값|시세|얼마|값", t) \
            and not re.search(r"전망", t):
        intent = "predict"
    elif re.search(r"전망|앞으로|향후|오를까|내릴까|오를\s*것|내릴\s*것|올라갈|내려갈|방향|상승세|하락세", t):
        intent = "outlook"
    elif re.search(r"그래프|차트|추이|추세|흐름|시각화|그려", t) or (
            re.search(r"가격\s*변화|변화\s*(알려|보여)|어떻게\s*(변|바뀌)", t) and not re.search(r"지난달|전월|저번", t)):
        intent = "trend"
    elif re.search(r"지난달|전월|저번\s*달|이번\s*달|얼마나\s*(올랐|내렸|떨어|상승|하락)|올랐|내렸|상승률|하락률|"
                   r"변동률|증감", t):
        intent = "mom"
    elif re.search(r"실거래|거래\s*내역|거래가|매매가|시세|얼마|가격|집값|거래", t):
        intent = "trades"
    s["intent"] = intent
    return s


def is_estate_message(t, slots, ctx):
    """부동산 가격 질문인지. 강의 추천/수강 문의는 기존 흐름에 맡긴다."""
    has_strong = any(w in t for w in STRONG_PRICE)
    has_course = any(w in t for w in COURSE_WORDS)
    place = bool(slots.get("district") or slots.get("umd") or slots.get("seoul"))
    typed = "kind" in slots
    if has_course and not has_strong:
        return False
    if has_strong or ((typed or place) and slots.get("intent")):
        return True
    if ctx and any(w in t for w in FOLLOWUP) and slots.get("intent"):
        return True
    if ctx and (typed or place) and len(t) <= 25:   # "빌라는?", "마포구는?" 같은 짧은 후속 질문
        return True
    return False
