"""Persistir decisiones de podio de IBKR. No ejecuta transacciones ni marca fills."""
import csv,json
from pathlib import Path
SOURCE=Path("resultados/validacion_rotacion_ibkr.json")
DEST=Path("resultados/historial_senales_ibkr.csv")
FIELDS=["fecha_cierre","estado","revision","accion_vender","accion_comprar","ejecucion","motivo"]

def main():
    data=json.loads(SOURCE.read_text(encoding="utf-8"))
    asof=data.get("fecha_cierre",data.get("cierre",""))
    if not asof:
        print("Sin cierre confirmado; no añadir historial")
        return
    current=list(csv.DictReader(DEST.open(encoding="utf-8"))) if DEST.exists() else []
    candidates=data.get("rotations",[]) or []
    items=candidates if candidates else [{}]
    new=[]
    for item in items:
        new.append({"fecha_cierre":asof,"estado":data.get("status","BLOCKED"),
            "revision":str(data.get("revision",False)),"accion_vender":item.get("sell",""),
            "accion_comprar":item.get("buy",""),"ejecucion":"PENDIENTE_CONFIRMACION" if item else "NINGUNA",
            "motivo":"; ".join(data.get("reasons",[]))})
    keys={(r["fecha_cierre"],r["accion_vender"],r["accion_comprar"]) for r in current}
    for row in new:
        key=(row["fecha_cierre"],row["accion_vender"],row["accion_comprar"])
        if key not in keys:
            current.append(row);keys.add(key)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with DEST.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS);writer.writeheader();writer.writerows(current)
    print("Señales IBKR registradas:",len(new),"histórico:",len(current))
if __name__=="__main__":main()
