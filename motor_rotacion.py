"""Único contrato de rotación para cartera y backtest. No ejecuta órdenes.

Score = retorno USD 63 ruedas; la selección del podio usa ese score.
Solo en revisión cada 5 ruedas se permite sustituir una posición que haya
estado fuera del Top3 durante 7 cierres, por un ticker del podio vigente
con ventaja >= 5 puntos durante esos mismos 7 cierres y SMA50 vigente.
"""
from math import isfinite

def decision(history, held, eligible, review):
    if len(history) < 7:
        return {"status":"BLOCKED","reasons":["Faltan siete cierres"],"rotations":[]}
    last = history[-7:]
    held = list(dict.fromkeys(held))
    if not held or not all(set(held).issubset(row) for row in last):
        return {"status":"BLOCKED","reasons":["Tenencias sin siete scores"],"rotations":[]}
    # Un IPO nuevo puede carecer de siete scores: se excluye de las
    # sustituciones hasta disponer de historia completa, no se rellena.
    common = set.intersection(*(set(row) for row in last))
    if len(common) < 3:
        return {"status":"BLOCKED","reasons":["Menos de tres símbolos con siete scores"],"rotations":[]}
    if any(not all(isfinite(float(row[t])) for t in common) for row in last):
        return {"status":"BLOCKED","reasons":["Scores no finitos"],"rotations":[]}
    podiums = [set(sorted(common,key=lambda t:(-row[t],t))[:3]) for row in last]
    if not review:
        return {"status":"NO_REVIEW","rotations":[]}
    options = []
    for old in held:
        if any(old in podium for podium in podiums):
            continue
        for new in podiums[-1]:
            if new in held or new not in eligible:
                continue
            if all(row[new]-row[old] >= 5 for row in last):
                options.append((float(last[-1][new]-last[-1][old]),old,new))
    taken_old=set();taken_new=set();rotations=[]
    for _,old,new in sorted(options,key=lambda x:(-x[0],x[1],x[2])):
        if old not in taken_old and new not in taken_new:
            rotations.append({"sell":old,"buy":new})
            taken_old.add(old);taken_new.add(new)
    return {"status":"CANDIDATE_NOT_ORDER" if rotations else "NO_ROTATION",
            "rotations":rotations}
