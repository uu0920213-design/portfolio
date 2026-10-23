"""학습된 모델 검증: 무작위 분할 + 시간 분할(1~6월 학습 → 7~9월 예측) 지표를 data/estate/model_eval.json 에 저장.
사용:  python -m scripts.evaluate_estate_models --train-dir <apartment_sale_clean.csv 가 있는 폴더> --model-dir <모델 폴더>
결과 파일을 만든 뒤 python -m scripts.import_estate_to_mongo 를 다시 실행하면 MongoDB(estate_models)에 저장됩니다."""
import os, json, warnings, sys, argparse
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--train-dir',default='data'); ap.add_argument('--model-dir',default='models/estate')
ap.add_argument('--out',default=str(Path(__file__).resolve().parents[1]/'data'/'estate'/'model_eval.json')); A=ap.parse_args()
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'; warnings.filterwarnings('ignore')
import joblib, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.base import clone
NUM=["excluUseAr","buildYear","buildingAge","floor","dealYear","dealMonth"]; CAT=["districtName","umdNm"]; F=NUM+CAT; T="dealAmount"
def metrics(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float); ape=np.abs(p-y)/y
    return dict(mae=float(np.mean(np.abs(p-y))),rmse=float(np.sqrt(np.mean((p-y)**2))),r2=float(1-np.sum((y-p)**2)/np.sum((y-y.mean())**2)),mape=float(ape.mean()*100),median_ape=float(np.median(ape)*100),p75_ape=float(np.percentile(ape,75)*100))
out={}
import tensorflow as tf   # DNN 비교가 필요 없으면 이 줄과 DNN 블록을 지우세요
for name in ('apartment','villa'):
    df=pd.read_csv(f'{A.train_dir}/{name}_sale_clean.csv',encoding='utf-8-sig',low_memory=False)
    d=df[F+[T]].copy()
    for c in NUM+[T]: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d[T].notna()&(d[T]>0)].copy()
    # RF: 학습 스크립트와 동일한 분할 (test_size=.2, random_state=42)
    X=d[F]; y=d[T].astype(float)
    _,Xte,_,yte=train_test_split(X,y,test_size=0.2,random_state=42)
    rf=joblib.load(f'{A.model_dir}/{name}_price_model.pkl'); prf=rf.predict(Xte)
    r={'rf_random_split':{**metrics(yte,prf),'n_test':int(len(yte)),'n_total':int(len(d))}}
    # DNN: 70/15/15 분할, 마지막 15% 테스트
    _,Xtmp,_,ytmp=train_test_split(X,y.astype('float32'),test_size=0.30,random_state=42)
    _,Xte2,_,yte2=train_test_split(Xtmp,ytmp,test_size=0.50,random_state=42)
    pre=joblib.load(f'{A.model_dir}/{name}_dnn_preprocessor.pkl'); dn=tf.keras.models.load_model(f'{A.model_dir}/{name}_dnn.keras',compile=False)
    pdn=np.maximum(np.expm1(dn.predict(pre.transform(Xte2).astype('float32'),verbose=0).reshape(-1)),0)
    r['dnn_random_split']={**metrics(yte2,pdn),'n_test':int(len(yte2))}
    # 시간 분할 백테스트: 1~6월 학습 → 7~9월 예측 (미래 시점 검증)
    tr=d[d.dealMonth<=6]; te=d[d.dealMonth>=7]
    m=clone(rf); m.set_params(regressor__n_estimators=60); m.fit(tr[F],tr[T].astype(float)); pt=m.predict(te[F])
    # 단순 기준선: (구, 동) 단위 ㎡당 중앙가(1~6월) × 면적
    tr2=tr.assign(ppm=tr[T]/tr.excluUseAr); g_umd=tr2.groupby(['districtName','umdNm']).ppm.median(); g_d=tr2.groupby('districtName').ppm.median()
    base=te.apply(lambda s: g_umd.get((s.districtName,s.umdNm),g_d.get(s.districtName,np.nan)),axis=1)*te.excluUseAr
    ok=base.notna()
    r['time_backtest_rf_jan_jun_to_jul_sep']={**metrics(te[T],pt),'n_train':int(len(tr)),'n_test':int(len(te))}
    r['time_backtest_naive_baseline']={**metrics(te[T][ok],base[ok]),'n_test':int(ok.sum())}
    # 7~9월 실제 평균 변화 vs 모델이 본 변화: 모델 예측의 월별 평균 vs 실제 월별 평균
    cmp=pd.DataFrame({'m':te.dealMonth.values,'act':te[T].values,'pred':pt}).groupby('m').mean().round(0); r['time_backtest_monthly_mean']=cmp.to_dict('index')
    out[name]=r
    print('\n',name); 
    for k,v in r.items():
        print(' ',k,{a:(round(b,1) if isinstance(b,float) else b) for a,b in v.items()} if k!='time_backtest_monthly_mean' else v)
Path(A.out).parent.mkdir(parents=True,exist_ok=True); json.dump(out,open(A.out,'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('saved',A.out)
