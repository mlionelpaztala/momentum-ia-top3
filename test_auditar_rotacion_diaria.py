import json, tempfile, unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from auditar_rotacion_diaria import audit, validate_dates

NY=ZoneInfo("America/New_York")
NOW=datetime(2026,10,28,17,0,tzinfo=NY)
SESSIONS=pd.bdate_range("2026-10-21","2026-10-28")

class DailyRotationAudit(unittest.TestCase):
    def test_review_day(self):
        self.assertEqual(validate_dates("2026-10-28",SESSIONS,NOW),(True,None))
    def test_non_review_day(self):
        self.assertEqual(validate_dates("2026-10-27",SESSIONS,datetime(2026,10,27,17,tzinfo=NY)),(False,None))
    def test_stale_blocks(self):
        self.assertIsNotNone(validate_dates("2026-10-27",SESSIONS,NOW)[1])
    def test_before_close_blocks(self):
        self.assertIsNotNone(validate_dates("2026-10-28",SESSIONS,datetime(2026,10,28,16,5,tzinfo=NY))[1])
    def test_four_holdings_and_missing_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            rows=[]
            for sym,score in {"A":10,"B":30,"C":29,"D":28,"E":0}.items():
                rows.append({"ticker":sym,"pt_fecha":"2026-10-28","sobre_sma50":True,
                             **{f"score_t_menos_{i}_pct":score for i in range(7)}})
            pd.DataFrame(rows).to_csv(p/"ranking.csv",index=False)
            (p/"cartera.json").write_text(json.dumps({"momentum_abiertas":[
                {"ticker":sym,"estado":"ABIERTA","cantidad":1} for sym in ["A","B","C","E"]]}))
            r=audit(p/"ranking.csv",p/"cartera.json",SESSIONS,NOW)
            self.assertEqual(r["status"],"CANDIDATE_NOT_ORDER")
            self.assertEqual(r["rotations"],[{"sell":"E","buy":"D"}])
            pd.DataFrame(rows).drop(columns=["score_t_menos_2_pct"]).to_csv(p/"ranking.csv",index=False)
            self.assertEqual(audit(p/"ranking.csv",p/"cartera.json",SESSIONS,NOW)["status"],"BLOCKED")

if __name__=="__main__":unittest.main()
