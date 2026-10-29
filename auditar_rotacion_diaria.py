"""Auditor diario de rotaciones: no ejecuta órdenes."""
import argparse, json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from motor_rotacion import decision

COLS=[f"score_t_menos_{i}_pct" for i in range(6,-1,-1)]
ANCHOR=pd.Timestamp("2026-10-21")

def validate_dates(asof, spy_sessions, now=None):
    now=now or datetime.now(ZoneInfo("America/New_York"))
    if now.tzinfo is None: raise ValueError("Reloj sin zona horaria")
    ny=now.astimezone(ZoneInfo("America/New_York"))
    asof=pd.Timestamp(asof).normalize()
    sessions=pd.DatetimeIndex(pd.to_datetime(spy_sessions))
    if sessions.tz is not None: sessions=sessions.tz_convert("America/New_York").tz_localize(None)
    sessions=sessions.normalize().sort_values().unique()
    if not len(sessions) or asof not in sessions:
        return False,"Fecha del ranking no consta como cierre SPY"
    if ny.date()!=asof.date() or ny.time()<time(16,20):
        return False,"Ranking no corresponde al cierre completo de hoy en Nueva York"
    if asof<ANCHOR or ANCHOR not in sessions:
        return False,"Calendario de revisiones no verificable"
    return (sessions.get_loc(asof)-sessions.get_loc(ANCHOR))%5==0,None

def audit(ranking_file,holdings_file,spy_sessions,now=None):
    df=pd.read_csv(ranking_file,encoding="utf-8-sig")
    holdings=json.loads(Path(holdings_file).read_text(encoding="utf-8"))
    held=sorted({str(p["ticker"]).upper() for p in holdings["momentum_abiertas"]
                 if p.get("estado")=="ABIERTA" and float(p.get("cantidad") or 0)>0})
    required=set(COLS)|{"ticker","sobre_sma50","pt_fecha"}
    if not held or required-set(df.columns):
        return {"status":"BLOCKED","rotations":[],"reasons":["Tenencias vacías o columnas requeridas ausentes"]}
    if df["pt_fecha"].nunique()!=1:
        return {"status":"BLOCKED","rotations":[],"reasons":["Fechas de cierre inconsistentes"]}
    asof=df["pt_fecha"].iloc[0]
    review,err=validate_dates(asof,spy_sessions,now)
    if err:return {"status":"BLOCKED","rotations":[],"reasons":[err],"cierre":asof}
    df["ticker"]=df["ticker"].astype(str).str.upper()
    if (df["ticker"].duplicated().any() or df[COLS].isna().any().any()
        or not set(held).issubset(df["ticker"])
        or not df[COLS].apply(pd.to_numeric,errors="coerce").notna().all().all()):
        return {"status":"BLOCKED","rotations":[],"reasons":["Cobertura incompleta, duplicada o posición sin score"]}
    history=[dict(zip(df["ticker"],df[col].astype(float))) for col in COLS]
    eligible=set(df.loc[df["sobre_sma50"].astype(str).str.lower().eq("true"),"ticker"])
    result=decision(history,held,eligible,review)
    return {**result,"held":held,"fecha_cierre":asof,"revision":bool(review),
            "informativo":"Candidato no es orden: verificar CEDEAR, liquidez, spreads y costos"}

def fetch_sessions(asof):
    import yfinance as yf
    start=(ANCHOR-pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    end=(pd.Timestamp(asof)+pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    raw=yf.download("SPY",start=start,end=end,auto_adjust=True,progress=False,threads=False)
    if raw is None or raw.empty:raise RuntimeError("No se pudieron verificar ruedas SPY")
    return raw.index

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ranking",default="resultados/ranking_teorico_63_ruedas.csv")
    parser.add_argument("--cartera",default="cartera.json")
    parser.add_argument("--out",default="resultados/validacion_rotacion.json")
    args=parser.parse_args()
    try:
        preview=pd.read_csv(args.ranking,encoding="utf-8-sig",usecols=["pt_fecha"])
        if preview["pt_fecha"].nunique()!=1:raise ValueError("Fechas inconsistentes")
        result=audit(args.ranking,args.cartera,fetch_sessions(preview["pt_fecha"].iloc[0]))
    except Exception as exc:
        result={"status":"BLOCKED","rotations":[],"reasons":[str(exc)]}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
