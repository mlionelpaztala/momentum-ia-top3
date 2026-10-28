"""Pure Momentum rotation rule. No orders."""
def decision(history, held, eligible, review):
    if len(history)<7: return {"status":"BLOCKED","reasons":["missing seven closes"],"rotations":[]}
    last=history[-7:]
    names=set(last[0])
    if len(names)<3 or any(set(x)!=names for x in last) or not set(held)<=names:
        return {"status":"BLOCKED","reasons":["inconsistent coverage"],"rotations":[]}
    podium=[set(sorted(x,key=lambda t:(-x[t],t))[:3]) for x in last]
    rotations=[]
    for old in held:
        if not all(old not in x for x in podium):continue
        for new in podium[-1]:
            if new in held or new not in eligible:continue
            if all(x[new]-x[old]>=5 for x in last):
                rotations.append((last[-1][new],old,new))
    if not review:return {"status":"NO_REVIEW","rotations":[]}
    seen_old=set();seen_new=set();out=[]
    for _,old,new in sorted(rotations,reverse=True):
        if old in seen_old or new in seen_new:continue
        out.append({"sell":old,"buy":new})
        seen_old.add(old);seen_new.add(new)
    return {"status":"CANDIDATE_NOT_ORDER" if out else "NO_ROTATION","rotations":out}
