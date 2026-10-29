"""Informe diario de la cartera Momentum USA en USD, independiente de Argentina."""
import json
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

CARTERA = Path("cartera_ibkr.json")
OUT = Path("resultados/rendimiento_momentum_ibkr.json")

def series(ticker, start, end):
    data=yf.download(ticker,start=start.strftime("%Y-%m-%d"),
        end=(end+timedelta(days=1)).strftime("%Y-%m-%d"),auto_adjust=False,
        progress=False,threads=False)
    if data.empty: raise ValueError(f"Sin cotización: {ticker}")
    close=data["Close"]
    if isinstance(close,pd.DataFrame): close=close.iloc[:,0]
    close.index=pd.to_datetime(close.index).tz_localize(None).normalize()
    return close.dropna()

def run():
    c=json.loads(CARTERA.read_text(encoding="utf-8"))
    held=c["momentum_abiertas"]
    if not held: raise ValueError("Sin compras IBKR confirmadas")
    start=pd.Timestamp(c["fecha_inicio_momentum"]).normalize()
    now=datetime.now(ZoneInfo("America/New_York"))
    end=pd.Timestamp(now.date())
    if now.time()<time(16,20) or end<start:
        raise ValueError("El último cierre completo aún no está disponible")
    ts={p["ticker"]:series(p["ticker"],start-timedelta(days=7),end) for p in held}
    available=set.intersection(*(set(s.index) for s in ts.values()))
    if end not in available: raise ValueError("Falta el cierre actual en alguna posición")
    before=sorted(d for d in available if d<end)
    prev=before[-1] if before else None
    cost=sum(float(p["costo_bruto_usd"])+float(p["comision_usd"]) for p in held)
    value=sum(float(p["cantidad"])*float(ts[p["ticker"]].loc[end]) for p in held)
    if end==start:
        daily=value/cost-1
    else:
        if prev is None:raise ValueError("Sin cierre previo para resultado diario")
        prior=sum(float(p["cantidad"])*float(ts[p["ticker"]].loc[prev]) for p in held)
        daily=value/prior-1
    result={"estado":"CALCULADO","fecha_cierre":str(end.date()),"inicio":str(start.date()),
        "capital_inicial_usd":round(cost,2),"valor_posiciones_usd":round(value,2),
        "resultado_acumulado_usd":round(value-cost,2),
        "rentabilidad_acumulada_pct":round(100*(value/cost-1),4),
        "rentabilidad_diaria_pct":round(100*daily,4),
        "metodologia":"Mark-to-market en USD, sin dividendos ni operaciones posteriores; comisiones de compra incluidas; no GOOGL/TSM/Argentina.",
        "posiciones":[{"ticker":p["ticker"],"cantidad":p["cantidad"],
          "cierre_usd":round(float(ts[p["ticker"]].loc[end]),4)} for p in held]}
    return result

if __name__=="__main__":
    try: result=run()
    except Exception as exc:
        result={"estado":"BLOQUEADO","motivo":str(exc),"nota":"No inventar rentabilidades ni cierres."}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
