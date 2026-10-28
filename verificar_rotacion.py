"""Audita cartera real sin ejecutar órdenes.
Uso: python verificar_rotacion.py
"""
import csv,json
from pathlib import Path
from motor_rotacion import decision

root=Path(__file__).resolve().parent
strategy=json.loads((root/"estrategia_momentum.json").read_text())
portfolio=json.loads((root/"cartera.json").read_text())
held=[x["ticker"] for x in portfolio["momentum_abiertas"] if x.get("estado")=="ABIERTA"]
with (root/"resultados/ranking_teorico_63_ruedas.csv").open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
history=[{} for _ in range(7)]
eligible=set()
for row in rows:
    name=row["ticker"]
    for i in range(7):
        value=row.get(f"score_t_menos_{6-i}_pct","")
        if value:
            history[i][name]=float(value)
    if row.get("sobre_sma50","").lower()=="true":eligible.add(name)
# FAIL CLOSED: no formal review date persisted => never authorize a trade automatically.
result=decision(history,held,eligible,review=False)
result["fecha_cierre"]=rows[0]["pt_fecha"] if rows else None
result["cartera"]=held
result["advertencia"]="Revisión formal no validada automáticamente. Verificar calendario de cinco ruedas desde 21/10/2026, siete scores, disponibilidad y spreads locales antes de actuar."
print(json.dumps(result,ensure_ascii=False,indent=2))
