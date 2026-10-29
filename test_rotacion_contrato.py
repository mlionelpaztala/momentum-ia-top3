import unittest
from motor_rotacion import decision

class RotationContract(unittest.TestCase):
    def fixture(self, advantage=6, outside=True):
        # A is held and outside Top3 if outside=True.
        rows=[]
        for _ in range(7):
            rows.append({"A":10.0 if outside else 40.0, "B":30.0, "C":29.0, "D":28.0, "E":0.0})
        return rows
    def test_valid_rotation_on_review(self):
        h=self.fixture(advantage=25)
        r=decision(h,["A","B","C"],{"D"},True)
        self.assertEqual(r["status"],"CANDIDATE_NOT_ORDER")
        self.assertEqual(r["rotations"],[{"sell":"A","buy":"D"}])
    def test_no_rotation_outside_review(self):
        h=self.fixture(25)
        self.assertEqual(decision(h,["A","B","C"],{"D"},False)["status"],"NO_REVIEW")
    def test_need_seven_closes(self):
        self.assertEqual(decision(self.fixture(25)[:6],["A","B","C"],{"D"},True)["status"],"BLOCKED")
    def test_no_rotation_if_old_reenters_top_three(self):
        h=self.fixture(25);h[2]["A"]=60
        self.assertEqual(decision(h,["A","B","C"],{"D"},True)["rotations"],[])
    def test_gap_must_hold_seven_closes(self):
        h=self.fixture(25);h[4]["D"]=14
        self.assertEqual(decision(h,["A","B","C"],{"D"},True)["rotations"],[])
    def test_sma_entry_filter(self):
        self.assertEqual(decision(self.fixture(25),["A","B","C"],set(),True)["rotations"],[])
    def test_new_candidate_without_seven_scores_is_excluded(self):
        h=self.fixture(25); del h[-1]["D"]
        self.assertEqual(decision(h,["A","B","C"],{"D"},True)["status"],"NO_ROTATION")
    def test_held_position_without_seven_scores_blocks(self):
        h=self.fixture(25); del h[-1]["A"]
        self.assertEqual(decision(h,["A","B","C"],{"D"},True)["status"],"BLOCKED")

if __name__=="__main__":unittest.main()
