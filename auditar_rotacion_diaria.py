"""Auditor de rotación: usa exactamente motor_rotacion.decision. No ejecuta órdenes."""
import argparse
import json
from pathlib import Path
import pandas as pd
from motor_rotacion import decision

COLS = [f"score_t_menos_{i}_pct" for i in range(6, -1, -1)]

def audit(ranking_file, holdings_file, review=False):
    df = pd.read_csv(ranking_file)
    holdings = json.loads(Path(holdings_file).read_text(encoding="utf-8"))
    held = sorted({str(p["ticker"]).upper() for p in holdings["momentum_abiertas"]
                   if p.get("estado") == "ABIERTA" and float(p.get("cantidad") or 0) > 0})
    required = set(COLS) | {"ticker", "sobre_sma50"}
    missing_cols = required - set(df.columns)
    if not held or missing_cols:
        return {"status": "BLOCKED", "rotations": [], "reasons": ["Tenencias vacías o columnas faltantes: " + str(sorted(missing_cols))]}
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if df["ticker"].duplicated().any() or df[COLS].isna().any().any() or not set(held).issubset(df["ticker"]):
        return {"status": "BLOCKED", "rotations": [], "reasons": ["Datos incompletos/duplicados o posiciones sin score"]}
    history = [dict(zip(df["ticker"], df[col].astype(float))) for col in COLS]
    eligible = set(df.loc[df["sobre_sma50"].astype(str).str.lower().isin(["true", "1"]), "ticker"])
    result = decision(history, held, eligible, bool(review))
    return {**result, "held": held, "revision_confirmada": bool(review),
            "advertencia": "CANDIDATE_NOT_ORDER no es una orden; verificar vigencia, fecha de revisión y operabilidad CEDEAR"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking", default="resultados/ranking_teorico_63_ruedas.csv")
    parser.add_argument("--cartera", default="cartera.json")
    parser.add_argument("--review", action="store_true", help="Solo si se confirmó que hoy corresponde revisión")
    args = parser.parse_args()
    print(json.dumps(audit(args.ranking, args.cartera, args.review), ensure_ascii=False, indent=2))
