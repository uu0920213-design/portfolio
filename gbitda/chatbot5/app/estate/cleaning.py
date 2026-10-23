"""공공데이터 CSV → 분석용 DataFrame.

- 해제(취소) 거래 제거: cdealType == 'O' 행과 짝이 되는 원거래 행을 함께 제거
- 금액(쉼표 제거), 면적, 층, 건축연도 숫자화
"""
import glob
import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR, KINDS

KEY = ["districtName", "umdNm", "jibun", "excluUseAr", "floor",
       "dealYear", "dealMonth", "dealDay", "dealAmount"]


def _num(s):
    return pd.to_numeric(s.astype("string").str.replace(",", "", regex=False).str.strip(), errors="coerce")


def clean_frame(raw: pd.DataFrame, kind: str) -> pd.DataFrame:
    df = raw.copy()
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    name_col = "aptNm" if kind == "apartment" else "mhouseNm"
    df["_name"] = df[name_col] if name_col in df else pd.NA
    # 같은 거래를 비교할 키(원본 문자열 기준)
    keycols = KEY + ([name_col] if name_col in df else [])
    k = df[keycols].astype(str).agg("|".join, axis=1)
    df["_k"] = k
    canc = df[df["cdealType"].astype(str).str.strip() == "O"]
    act = df[df["cdealType"].astype(str).str.strip() != "O"].copy()
    removed = len(df) - len(act)
    if len(canc):
        act["_n"] = act.groupby("_k").cumcount()
        cc = canc.groupby("_k").size().rename("_c")
        act = act.join(cc, on="_k")
        act["_c"] = act["_c"].fillna(0)
        act = act[act["_n"] >= act["_c"]]
    paired = len(df) - len(canc) - len(act)

    out = pd.DataFrame({
        "kind": kind,
        "sggCd": act["sggCd"].astype(str).str.strip(),
        "district": act["districtName"].astype(str).str.strip(),
        "umd": act["umdNm"].astype(str).str.strip(),
        "name": act["_name"].astype("string").str.strip(),
        "house_type": act["houseType"] if "houseType" in act else pd.NA,
        "jibun": act["jibun"].astype("string").str.strip(),
        "price": _num(act["dealAmount"]),
        "area": _num(act["excluUseAr"]),
        "floor": _num(act["floor"]),
        "build_year": _num(act["buildYear"]),
        "year": _num(act["dealYear"]),
        "month": _num(act["dealMonth"]),
        "day": _num(act["dealDay"]),
        "deal_type": act["dealingGbn"] if "dealingGbn" in act else pd.NA,
    })
    out = out[(out.price > 0) & (out.area > 0) & out.year.notna() & out.month.notna()].copy()
    out["year"] = out.year.astype(int)
    out["month"] = out.month.astype(int)
    out["day"] = out.day.fillna(1).astype(int)
    out["ym"] = out.year * 100 + out.month
    out["age"] = (out.year - out.build_year).where(lambda s: (s >= 0) & (s <= 100))
    out["deal_date"] = (out.year.astype(str) + "-" + out.month.astype(str).str.zfill(2)
                        + "-" + out.day.astype(str).str.zfill(2))
    out["price_m2"] = out.price / out.area
    out.attrs["removed_cancel_rows"] = int(removed)
    out.attrs["removed_paired_rows"] = int(paired)
    return out.reset_index(drop=True)


def load_csv_kind(kind: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    # 구·월별 원본 파일(apartment_sale_11110_202601.csv)만 사용한다.
    # 합본(…_seoul_…)·전처리본(…_clean.csv)이 같은 폴더에 있어도 중복 집계되지 않게 한다.
    pat = re.compile(rf"{KINDS[kind]['prefix']}\d{{5}}_\d{{6}}\.csv")
    files = sorted(f for f in glob.glob(str(Path(data_dir) / f"{KINDS[kind]['prefix']}*.csv"))
                   if pat.fullmatch(Path(f).name))
    if not files:
        return pd.DataFrame()
    raw = pd.concat([pd.read_csv(f, dtype=str, encoding="utf-8-sig") for f in files], ignore_index=True)
    n0 = len(raw)
    raw = raw.drop_duplicates().reset_index(drop=True)      # 수집 중 겹친 완전 동일 행
    out = clean_frame(raw, kind)
    out.attrs["removed_duplicate_rows"] = n0 - len(raw)
    return out


def doc_ids(df: pd.DataFrame) -> pd.Series:
    """같은 값의 거래가 여러 건이어도 구분되는 안정적인 _id (재적재해도 중복되지 않음)."""
    base = (df.kind + "|" + df.district + "|" + df.umd + "|" + df.name.astype(str) + "|" + df.jibun.astype(str)
            + "|" + df.area.astype(str) + "|" + df.floor.astype(str) + "|" + df.deal_date + "|" + df.price.astype(str))
    n = base.groupby(base).cumcount().astype(str)
    return (base + "#" + n).map(lambda s: hashlib.sha1(s.encode()).hexdigest()[:24])
