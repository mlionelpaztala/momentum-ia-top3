"""Backtest de estrategia VIGENTE, USD, sin stops ni caución.
Uso: python backtest_vigente.py --years 5
     python backtest_vigente.py --years 10
La simulación utiliza cierres ajustados, ejecución al cierre de señal (optimista),
universo actual fijo (sesgo retrospectivo) y precio fraccionario.
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from ranking import UNIVERSE

def download(start, end):
    names = UNIVERSE + ["SPY", "QQQ"]
    output = {}
    failures = {}
    for i in range(0, len(names), 6):
        batch = names[i:i+6]
        try:
            data = yf.download(batch, start=str(start.date()), end=str((end+pd.Timedelta(days=1)).date()), auto_adjust=True, repair=True, progress=False, threads=False, group_by="ticker")
            for ticker in batch:
                try:
                    s = data[ticker]["Close"] if isinstance(data.columns,pd.MultiIndex) else data["Close"]
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                    if len(s): output[ticker]=s[~s.index.duplicated()]
                    else: failures[ticker]="Sin precios"
                except Exception as e: failures[ticker]=str(e)
        except Exception as e:
            for ticker in batch: failures[ticker]=str(e)
    if not all(t in output for t in ("SPY","QQQ")): raise RuntimeError("No se descargaron ambos benchmarks")
    calendar=output["SPY"].index
    return pd.DataFrame({t:s.reindex(calendar) for t,s in output.items()},index=calendar), failures

def backtest(prices, start, fee=0.00121):
    universe=[t for t in UNIVERSE if t in prices.columns]
    score=100*(prices[universe]/prices[universe].shift(63)-1)
    sma=prices[universe].rolling(50,min_periods=50).mean()
    eligible=(prices[universe]>sma)&score.notna()
    days=prices.index[prices.index>=start]
    first=days[0]
    rank=lambda d: sorted([t for t in universe if pd.notna(score.at[d,t])], key=lambda t:(-score.at[d,t],t))
    chosen=[t for t in rank(first) if eligible.at[first,t]][:3]
    if len(chosen)!=3: raise ValueError("No hay tres activos elegibles al inicio")
    shares={t:(10000/3*(1-fee))/prices.at[first,t] for t in chosen}
    cash=0.
    outside_count={t:0 for t in chosen}
    pair_count={}
    orders=[{"date":str(first.date()),"action":"BUY","ticker":t,"gross_usd":10000/3} for t in chosen]
    equity=[]
    for i,d in enumerate(days):
        ranked=rank(d);podium=set(ranked[:3])
        for old in list(shares):
            outside_count[old]=outside_count.get(old,0)+1 if old not in podium else 0
        valid_pairs=set()
        for old in shares:
            if outside_count[old]==0: continue
            for new in ranked:
                if new in shares: continue
                key=(old,new);valid_pairs.add(key)
                good=bool(eligible.at[d,new]) and (score.at[d,new]-score.at[d,old]>=5)
                pair_count[key]=pair_count.get(key,0)+1 if good else 0
        pair_count={k:v for k,v in pair_count.items() if k in valid_pairs}
        if i and i%5==0:
            candidates=sorted([(score.at[d,new],old,new) for (old,new),n in pair_count.items()
                               if n>=7 and outside_count.get(old,0)>=7 and eligible.at[d,new]],
                              key=lambda x:-x[0])
            used_old=set();used_new=set()
            for _,old,new in candidates:
                if old in used_old or new in used_new or old not in shares or new in shares:continue
                if pd.isna(prices.at[d,old]) or pd.isna(prices.at[d,new]):continue
                gross=shares.pop(old)*prices.at[d,old]
                net=gross*(1-fee)**2
                shares[new]=net/prices.at[d,new]
                orders += [{"date":str(d.date()),"action":"SELL","ticker":old,"gross_usd":float(gross)},
                           {"date":str(d.date()),"action":"BUY","ticker":new,"gross_usd":float(gross*(1-fee))}]
                used_old.add(old);used_new.add(new)
                outside_count.pop(old,None);outside_count[new]=0
            # Mantener la continuidad de siete cierres ENTRE revisiones de cinco ruedas.
            # Eliminar únicamente pares cuya posición salió o cuyo candidato ingresó.
            pair_count={k:n for k,n in pair_count.items()
                        if k[0] in shares and k[1] not in shares}
            # Equiponderar solo si existe precio válido de todas las posiciones.
            if len(shares)==3 and all(pd.notna(prices.at[d,t]) for t in shares):
                nav=sum(q*prices.at[d,t] for t,q in shares.items())+cash
                # Aplicar costos a la negociación neta de rebalanceo (una aproximación).
                target=nav/3
                sells=[t for t in shares if shares[t]*prices.at[d,t]>target]
                for t in sells:
                    delta=shares[t]*prices.at[d,t]-target
                    shares[t]-=delta/prices.at[d,t];cash+=delta*(1-fee)
                for t in shares:
                    deficit=target-shares[t]*prices.at[d,t]
                    if deficit>0 and cash>0:
                        spend=min(cash,deficit/(1-fee))
                        shares[t]+=spend*(1-fee)/prices.at[d,t];cash-=spend
        missing=[t for t in shares if pd.isna(prices.at[d,t])]
        nav=np.nan if missing else cash+sum(shares[t]*prices.at[d,t] for t in shares)
        equity.append({"date":str(d.date()),"equity_usd":nav,"holdings":";".join(shares)})
    curve=pd.DataFrame(equity)
    if curve.equity_usd.isna().any():
        raise RuntimeError("Faltan cotizaciones de una posición abierta: no se publica retorno incompleto")
    def metrics(v):
        x=np.asarray(v,dtype=float)
        years=(days[-1]-days[0]).days/365.25
        gain=x[-1]/x[0]-1
        return {"final_usd":round(float(10000*(1+gain)),2),
                "total_pct":round(float(gain*100),2),
                "cagr_pct":round(float(((1+gain)**(1/years)-1)*100),2),
                "max_drawdown_pct":round(float((x/np.maximum.accumulate(x)-1).min()*100),2)}
    # Capital en t0 y primera compra incluyen comisión; se mide contra capital inicial 10k.
    v=np.r_[10000.,curve.equity_usd.to_numpy()]
    result={"momentum":metrics(v),"start":str(days[0].date()),"end":str(days[-1].date()),
            "valid_at_start":int(eligible.loc[first].sum()),"transactions":len(orders)}
    for t in ("SPY","QQQ"):
        z=prices.loc[days,t].to_numpy(dtype=float)
        result[t]=metrics(z)
    return result,curve,pd.DataFrame(orders)

def main():
    p=argparse.ArgumentParser();p.add_argument("--years",type=int,choices=[5,10],required=True)
    p.add_argument("--end",default="2026-10-19");p.add_argument("--fee",type=float,default=.00121)
    a=p.parse_args();end=pd.Timestamp(a.end);start=end-pd.DateOffset(years=a.years)
    prices,failures=download(start-pd.Timedelta(days=180),end)
    result,curve,orders=backtest(prices,start,a.fee)
    directory=Path("resultados/backtest_vigente");directory.mkdir(parents=True,exist_ok=True)
    prefix=str(a.years)+"y"
    curve.to_csv(directory/("curva_"+prefix+".csv"),index=False)
    orders.to_csv(directory/("operaciones_"+prefix+".csv"),index=False)
    result["warnings"]=["Universo actual aplicado retrospectivamente; sesgo de selección",
                        "Ejecución al cierre de señal, no reproducible en vivo sin deslizamiento",
                        "USD acciones estadounidenses; no CEDEAR/ARS",
                        "Comisión estimada por operación: "+str(a.fee*100)+"%"]
    result["failed_downloads"]=failures
    (directory/("resumen_"+prefix+".json")).write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
