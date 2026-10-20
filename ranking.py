"""Momentum IA Top3: ranking auditable de 63 ruedas estadounidenses. No envía órdenes."""
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import yfinance as yf
from cartera import lineas_cartera
import json

# Universo de INVESTIGACIÓN ESTADOUNIDENSE: 57 IA/infraestructura + 20 biotecnología + 6 computación cuántica.
# Esto NO demuestra que sea el universo completo históricamente elegible; revisar periódicamente.
UNIVERSE = ['ANET','DELL','CEG','MU','AVGO','CLS','VST','KLAC','NVDA','AMD','TSM','META','GOOGL','MSFT','AMZN','PLTR','MRVL','AMAT','LRCX','CRWD','PANW','SNOW','ORCL','CRM','NOW','COIN','SMCI','FSLR','ENPH','ETN','GE','XOM','V','IBM','INTC','WDC','PATH','GEV','SNDK','TLN','ALAB','CRWV','ARM','APP','VRT','COHR','LITE','PWR','STX','HPE','NBIS','IREN','OKLO','QCOM','CRDO','APLD','BE','VRTX','REGN','MRNA','BNTX','CRSP','NTLA','BEAM','EDIT','ALNY','IONS','SRPT','NBIX','INCY','AMGN','GILD','BIIB','RXRX','EXAS','TMDX','VKTX','IONQ','QBTS','RGTI','QUBT','QNT','INFQ']
# Disponibilidad histórica informada por usuario; no son cotizaciones ni verificación actual de Bull Market.
LOCAL_PREVIAMENTE_INFORMADOS = {'ANET','DELL','CEG','MU','AVGO','CLS','VST','KLAC','GEV','SNDK','TLN','SKHY'}


def calc(out='resultados', end=None):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    # Un mismo calendario para todos. auto_adjust=True: cierres ajustados por splits/dividendos.
    symbols=UNIVERSE+['SPY','QQQ']
    if end: endarg=(pd.Timestamp(end)+pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    else: endarg=None
    end_ts=pd.Timestamp.now(tz='America/New_York').strftime('%Y-%m-%d %H:%M:%S %Z')
    downloaded={};errors={}
    for i in range(0,len(symbols),8):
        batch=symbols[i:i+8]
        try:
            block=yf.download(batch, period='9mo' if endarg is None else None,
                              start=None if endarg is None else (pd.Timestamp(end)-pd.Timedelta(days=285)).strftime('%Y-%m-%d'),
                              end=endarg, auto_adjust=True, progress=False,
                              group_by='ticker', threads=False, repair=True)
            for sym in batch:
                try:
                    sub=block[sym] if isinstance(block.columns,pd.MultiIndex) else block
                    s=pd.to_numeric(sub['Close'],errors='coerce').dropna()
                    if not s.empty:
                        s.index=pd.to_datetime(s.index).tz_localize(None).normalize()
                        downloaded[sym]=s[~s.index.duplicated(keep='last')]
                    else: errors[sym]='Sin cierres descargados'
                except Exception as exc:errors[sym]=str(exc)[:170]
        except Exception as exc:
            for sym in batch: errors[sym]=str(exc)[:170]
    if 'SPY' not in downloaded: raise RuntimeError('No se descargó SPY; imposible fijar calendario común. No hay ranking válido.')
    dates=downloaded['SPY'].index.sort_values().unique()
    if len(dates)<70:raise RuntimeError(f'Calendario insuficiente: {len(dates)} ruedas; se necesitan al menos 70 cierres para serie de siete scores y SMA50.')
    now_ny=datetime.now(ZoneInfo('America/New_York'))
    # Restringir a ruedas de cierre completas: si se ejecuta antes de las 16:20 ET, descartar la sesión actual.
    if not end and now_ny.time()<datetime.strptime('16:20','%H:%M').time():
        dates=dates[dates.date<now_ny.date()]
    today=dates[-1];back=dates[-64];window=dates[-64:]
    prices=pd.DataFrame(index=dates)
    for sym,s in downloaded.items():prices[sym]=s.reindex(dates)
    rows=[];excluded=[]
    for sym in UNIVERSE:
        if sym not in prices:
            excluded.append({'ticker':sym,'motivo':errors.get(sym,'sin descarga')});continue
        s=prices[sym];hist=s.loc[window]
        if hist.isna().any() or len(hist)!=64:
            excluded.append({'ticker':sym,'motivo':f'Cierres incompletos en 64 puntos ({hist.notna().sum()}/64)'});continue
        p0=float(hist.iloc[0]);pt=float(hist.iloc[-1]);sma=float(s.loc[:today].tail(50).mean())
        if s.loc[:today].tail(50).isna().any():
            excluded.append({'ticker':sym,'motivo':'SMA50 incompleta'});continue
        # Score del cierre y siete cierres previos, comparando cada fecha contra 63 ruedas atrás.
        scores=[]
        for date in dates[-7:]:
            ix=dates.get_loc(date)
            if ix<63: scores.append(np.nan);continue
            a=s.loc[dates[ix]];b=s.loc[dates[ix-63]]
            scores.append(float(100*(a/b-1)) if pd.notna(a) and pd.notna(b) and b>0 else np.nan)
        rows.append({'ticker':sym,'p0_fecha':str(back.date()),'pt_fecha':str(today.date()),
                     'precio_63_antes_usd_aj':round(p0,6),'precio_hoy_usd_aj':round(pt,6),
                     'score_63_pct':round(100*(pt/p0-1),4),'sma50_usd_aj':round(sma,5),
                     'sobre_sma50':bool(pt>sma),
                     'cedear_previamente_informado':sym in LOCAL_PREVIAMENTE_INFORMADOS,
                     **{f'score_t_menos_{6-j}_pct':round(v,4) if np.isfinite(v) else np.nan for j,v in enumerate(scores)}})
    df=pd.DataFrame(rows)
    if df.empty:raise RuntimeError('Ningún ticker con 64 cierres homogéneos. No hay ranking válido.')
    df=df.sort_values('score_63_pct',ascending=False).reset_index(drop=True)
    df.insert(0,'puesto',np.arange(1,len(df)+1))
    df.to_csv(dest/'ranking_teorico_63_ruedas.csv',index=False,encoding='utf-8-sig')
    df[df.cedear_previamente_informado].to_csv(dest/'cedears_previamente_informados.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(excluded,columns=['ticker','motivo']).to_csv(dest/'sin_datos.csv',index=False,encoding='utf-8-sig')
    # Registro diario para que un posterior ejecutable pueda conservar trazabilidad de siete cierres.
    top=df[['puesto','ticker','score_63_pct','sobre_sma50','cedear_previamente_informado']].head(10)
    bench=[]
    for sym in ['SPY','QQQ']:
        a=prices[sym].loc[window] if sym in prices else pd.Series(dtype=float)
        bench.append({'benchmark':sym,'retorno_63_pct':round(100*(a.iloc[-1]/a.iloc[0]-1),4) if len(a)==64 and a.notna().all() else np.nan})
    pd.DataFrame(bench).to_csv(dest/'benchmarks.csv',index=False)
    summary=[f'MOMENTUM IA Top 3 | cierre NY {today.date()} | generado {end_ts}',
             f'Fórmula: 100% retorno de EXACTAMENTE 63 intervalos bursátiles estadounidenses; {back.date()} a {today.date()}.',
             f'Universo estadounidense seguido: {len(UNIVERSE)} símbolos; válidos: {len(df)}; excluidos/N/D: {len(excluded)}.',
             'RANKING PRINCIPAL: acciones de EE.UU. sin excluir por falta de CEDEAR. Comprabilidad local se revisa APARTE.',
             'TOP 10 ESTADOUNIDENSE (sin filtrar disponibilidad de CEDEAR):', top.to_string(index=False),
             '\nREGISTRO DE CARTERA (independiente del ranking):']
    summary.extend(lineas_cartera())
    estrategia=json.loads(Path(__file__).with_name('estrategia_momentum.json').read_text(encoding='utf-8'))
    summary += [f"\nESTRATEGIA VIGENTE: {estrategia['salida']['tipo']}; SIN STOP DE PRECIO; revisión cada 5 ruedas; fuera del Top3 7 cierres y ventaja >=5 pp durante 7 cierres antes de rotar. No colocar órdenes automáticamente.",
                'ROTACIÓN: no es automáticamente ejecutable. Exige confirmar además filtro SMA50 del sustituto, costos y puntas locales; la simple caída del precio NO determina salida.',
                'Criterio de 7 cierres: valores históricos de score están en el CSV para evaluar comparaciones; no afirmar ejecución.',
                '\nBENCHMARKS:', pd.DataFrame(bench).to_string(index=False)]
    (dest/'informe_resumen.txt').write_text('\n'.join(summary),encoding='utf-8')
    print('\n'.join(summary))
    return dest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='resultados');parser.add_argument('--end',default=None)
    args=parser.parse_args();calc(args.out,args.end)

