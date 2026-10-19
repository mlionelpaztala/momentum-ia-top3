"""Auditoría gratuita de cobertura histórica. NO es un backtest IA validado.
Usa S&P 500 point-in-time como proxy para verificar datos, nunca universo IA.
Los precios de tickers deslistados son potencialmente inexistentes en Yahoo.
"""
from pathlib import Path
import json, sys, subprocess
import pandas as pd
import yfinance as yf
import yaml

BASE=Path("resultados/auditoria_historica")
BASE.mkdir(parents=True,exist_ok=True)
ROOT=Path("/tmp/sp500-pit-2026")
SOURCE="https://github.com/shardul0701/SP500-Survivorship-bias-data-2004-2026.git"
END=pd.Timestamp("2026-06-02")
YEARS=[5,10]

def memberships():
    if not ROOT.exists():
        subprocess.run(["git","clone","--depth","1",SOURCE,str(ROOT)],check=True)
    snapshots={}
    for yr in range(2015,2027):
        fp=ROOT/"src"/"sp500_ticker_history"/f"{yr}.yaml"
        if not fp.exists():
            files=list((ROOT/"src"/"sp500_ticker_history").glob(f"*{yr}*"))
            if len(files)!=1: raise RuntimeError(f"Falta membresía {yr}")
            fp=files[0]
        dat=yaml.safe_load(fp.read_text())
        universe=set(dat["tickers_on_Jan_1"])
        snapshots[pd.Timestamp(f"{yr}-01-01")]=set(universe)
        for date,change in sorted((dat.get("changes") or {}).items()):
            universe=(universe-set(change.get("difference") or []))|set(change.get("union") or [])
            snapshots[pd.Timestamp(str(date))]=set(universe)
    return snapshots

def main():
    snaps=memberships()
    required_dates=[d for d in snaps if d<=END and d>=pd.Timestamp("2016-01-01")]
    all_names=sorted(set().union(*(snaps[d] for d in required_dates)))
    # Equivalencias triviales únicamente; cambios históricos requieren verificación individual.
    normalize=lambda t:t.replace(".","-")
    names=sorted(set(map(normalize,all_names)))+["SPY","QQQ"]
    available={}; errors={}
    for i in range(0,len(names),12):
        batch=names[i:i+12]
        try:
            df=yf.download(batch,start="2015-01-01",end="2026-06-03",
                           auto_adjust=True,progress=False,threads=False,
                           group_by="ticker")
            for ticker in batch:
                try:
                    s=df[ticker]["Close"] if isinstance(df.columns,pd.MultiIndex) else df["Close"]
                    s=pd.to_numeric(s,errors="coerce").dropna()
                    if not s.empty: available[ticker]=s
                    else: errors[ticker]="sin cierres"
                except Exception as e:errors[ticker]=str(e)[:100]
        except Exception as e:
            for ticker in batch: errors[ticker]=str(e)[:100]
        print(f"Consulta de precios {min(i+12,len(names))}/{len(names)}",flush=True)
    report={"source":SOURCE,"proxy":"S&P500 histórico — NO ecosistema IA",
            "end":"2026-06-02","unique_historical_symbols":len(all_names),
            "prices_downloaded":len(set(available)&set(names)),
            "missing_symbols":sorted(t for t in names if t not in available),
            "years":{}, "validation":"NO_VALIDATED_RETURN"}
    for years in YEARS:
        start=END-pd.DateOffset(years=years)
        seen=set().union(*(snaps[d] for d in snaps if start<=d<=END))
        absent=sorted(t for t in seen if normalize(t) not in available)
        report["years"][str(years)]={
            "start":str(start.date()),"end":str(END.date()),
            "historical_members_encountered":len(seen),
            "missing_price_symbols":absent,"missing_count":len(absent),
            "cagr":None,
            "reason":"Falta validar eventos de desliste, precios terminales, elegibilidad IA point-in-time y ejecución."}
    (BASE/"auditoria.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    rows=["# Auditoría de datos históricos, NO rentabilidad validada","",
          f"Fuente: {SOURCE}","Universo: S&P 500 histórico (proxy, NO estrategia IA).",
          f"Tickers históricos: {len(all_names)}; series descargadas: {len(available)}.",""]
    for years,v in report["years"].items():
        rows += [f"## {years} años","",f"Miembros históricos encontrados: {v['historical_members_encountered']}",
                 f"Sin precios descargados: {v['missing_count']}",
                 "Ejemplos: "+", ".join(v["missing_price_symbols"][:40]),"",
                 "**CAGR validado: no disponible.**",""]
    (BASE/"LEER_PRIMERO.md").write_text("\n".join(rows))
    print("\n".join(rows),flush=True)
    if any(v["missing_count"] for v in report["years"].values()):
        print("COBERTURA INCOMPLETA: No publicar CAGR",flush=True)

if __name__=="__main__":main()
