"""Backtest de estrategia VIGENTE, USD, sin stops ni caución.
Uso: python backtest_vigente.py --years 5
     python backtest_vigente.py --years 10
La simulación utiliza cierres ajustados, ejecución al cierre siguiente (aproximada),
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
    """Señal al cierre t, ejecución al cierre t+1; sin acceso a precios futuros.
    Restricción: universo fijo actual (sesgo de selección); no es prueba libre de sesgos.
    """
    universe=[t for t in UNIVERSE if t in prices.columns]
    scores=100*(prices[universe]/prices[universe].shift(63)-1)
    sma=prices[universe].rolling(50,min_periods=50).mean()
    eligible=(prices[universe]>sma)&scores.notna()
    days=prices.index[prices.index>=start]
    if len(days)<10: raise ValueError("Período insuficiente")
    def ranking(d):
        valid=[t for t in universe if pd.notna(scores.at[d,t])]
        return sorted(valid,key=lambda t:(-scores.at[d,t],t))
    cash=10000.
    shares={}
    orders=[]
    equity=[]
    outside={}
    streak={}
    pending=None
    incomplete=[]
    for i,d in enumerate(days):
        # Ejecutar instrucciones dictadas SOLO por el cierre previo.
        if pending is not None:
            selection=pending
            pending=None
            if selection["type"]=="initial":
                picks=selection["picks"]
                if all(pd.notna(prices.at[d,t]) and prices.at[d,t]>0 for t in picks):
                    budget=cash/3
                    for t in picks:
                        cost=budget
                        shares[t]=cost*(1-fee)/prices.at[d,t]
                        cash-=cost
                        orders.append({"date":str(d.date()),"action":"BUY","ticker":t,"price_usd":float(prices.at[d,t]),"shares":float(shares[t]),"gross_usd":float(cost*(1-fee)),"fee_usd":float(cost*fee),"reason":"INITIAL"})
            elif selection["type"]=="rebalance" and shares:
                replacements=selection["replacements"]
                for old,new in replacements:
                    if old not in shares or new in shares:continue
                    if pd.isna(prices.at[d,old]) or pd.isna(prices.at[d,new]):continue
                    gross=shares.pop(old)*prices.at[d,old]
                    cash+=gross*(1-fee)
                    orders.append({"date":str(d.date()),"action":"SELL","ticker":old,"price_usd":float(prices.at[d,old]),"shares":float(gross/prices.at[d,old]),"gross_usd":float(gross),"fee_usd":float(gross*fee),"reason":"PODIUM_ROTATION"})
                    outside.pop(old,None)
                    outside[new]=0
                    shares[new]=0.
                    # La compra se documenta con el importe realmente ejecutado en el rebalanceo.
                # Equiponderación con comisiones, conservando caja residual.
                if len(shares)==3 and all(pd.notna(prices.at[d,t]) and prices.at[d,t]>0 for t in shares):
                    wealth=cash+sum(shares[t]*prices.at[d,t] for t in shares)
                    target=wealth/3
                    for t in shares:
                        current=shares[t]*prices.at[d,t]
                        if current>target:
                            delta=current-target
                            n=delta/prices.at[d,t]
                            shares[t]-=n
                            cash+=delta*(1-fee)
                            orders.append({"date":str(d.date()),"action":"SELL","ticker":t,"price_usd":float(prices.at[d,t]),"shares":float(n),"gross_usd":float(delta),"fee_usd":float(delta*fee),"reason":"REBALANCE"})
                    for t in shares:
                        needed=max(0,target-shares[t]*prices.at[d,t])
                        if needed>0:
                            spend=min(cash,needed/(1-fee))
                            quantity=spend*(1-fee)/prices.at[d,t]
                            shares[t]+=quantity
                            cash-=spend
                            orders.append({"date":str(d.date()),"action":"BUY","ticker":t,
                                "price_usd":float(prices.at[d,t]),"shares":float(quantity),
                                "gross_usd":float(spend*(1-fee)),
                                "fee_usd":float(spend*fee),"reason":"REBALANCE"})
        missing=[t for t in shares if pd.isna(prices.at[d,t])]
        if missing:
            incomplete.append((str(d.date()),missing))
            nav=np.nan
        else:
            nav=cash+sum(q*prices.at[d,t] for t,q in shares.items())
        equity.append({"date":str(d.date()),"equity_usd":nav,"holdings":";".join(shares)})
        ranked=ranking(d)
        podium=set(ranked[:3])
        if not shares:
            # Inicio: primera señal al cierre, compra en el cierre posterior.
            if pending is None:
                picks=[t for t in ranked if bool(eligible.at[d,t])][:3]
                if len(picks)==3: pending={"type":"initial","picks":picks}
            continue
        for old in shares:
            outside[old]=outside.get(old,0)+1 if old not in podium else 0
        active=set()
        for old in shares:
            for new in ranked:
                if new in shares:continue
                key=(old,new)
                active.add(key)
                good=outside[old]>0 and bool(eligible.at[d,new]) and scores.at[d,new]-scores.at[d,old]>=5
                streak[key]=streak.get(key,0)+1 if good else 0
        streak={k:v for k,v in streak.items() if k in active}
        if i>0 and i%5==0 and i<len(days)-1:
            candidates=sorted([(scores.at[d,new],old,new) for (old,new),n in streak.items()
                               if n>=7 and outside.get(old,0)>=7 and bool(eligible.at[d,new])],
                              key=lambda x:-x[0])
            used_old=set();used_new=set();replacements=[]
            for _,old,new in candidates:
                if old not in used_old and new not in used_new:
                    replacements.append((old,new));used_old.add(old);used_new.add(new)
            pending={"type":"rebalance","replacements":replacements}
    if any(row["gross_usd"]<=0 or row["shares"]<=0 for row in orders):
        raise RuntimeError("Operación nula o inválida en auditoría")
    curve=pd.DataFrame(equity)
    if incomplete: raise RuntimeError("Faltan cotizaciones de posiciones mantenidas: "+str(incomplete[:3]))
    if len(shares)!=3: raise RuntimeError("No se completaron tres posiciones")
    years=(days[-1]-days[0]).days/365.25
    def metrics(v):
        x=np.asarray(v,dtype=float)
        gain=x[-1]/x[0]-1
        return {"final_usd":round(float(10000*(1+gain)),2),
                "total_pct":round(float(gain*100),2),
                "cagr_pct":round(float(((1+gain)**(1/years)-1)*100),2),
                "max_drawdown_pct":round(float((x/np.maximum.accumulate(x)-1).min()*100),2)}
    result={"momentum":metrics(curve.equity_usd),"start":str(days[0].date()),"end":str(days[-1].date()),
            "transactions":len(orders),"audit_gross_buy_usd":round(sum(o["gross_usd"] for o in orders if o["action"]=="BUY"),2),"audit_fees_usd":round(sum(o["fee_usd"] for o in orders),2),"signal_timing":"cierre t, ejecución cierre t+1"}
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
    # La simulación usa la lista ACTUAL de símbolos; no demuestra elegibilidad
    # histórica ni incorpora automáticamente excluidas, delistadas o quebradas.
    # Estos resultados NO constituyen una prueba libre de sesgo de supervivencia.
    result["validation_status"]="EXPLORATORIO_NO_POINT_IN_TIME"
    result["historical_universe_validated"]=False
    result["point_in_time_data_available"]=False
    result["warnings"]=["NO VALIDADO: universo histórico point-in-time no disponible; no interpretar el CAGR como rendimiento reproducible",
                        "Universo actual aplicado retrospectivamente; sesgo de selección",
                        "Señal al cierre t y ejecución al cierre t+1; sin modelar deslizamiento",
                        "USD acciones estadounidenses; no CEDEAR/ARS",
                        "Comisión estimada por operación: "+str(a.fee*100)+"%"]
    result["failed_downloads"]=failures
    (directory/("resumen_"+prefix+".json")).write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
