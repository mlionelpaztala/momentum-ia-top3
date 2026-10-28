import unittest
from motor_rotacion import decision

class EngineTests(unittest.TestCase):
    def test_rotation(self):
        h=[dict(A=0,B=10,C=20,D=30) for _ in range(7)]
        self.assertEqual(decision(h,["A","B","C"],{"D"},True)["rotations"],[{"sell":"A","buy":"D"}])
    def test_no_review(self):
        h=[dict(A=0,B=10,C=20,D=30) for _ in range(7)]
        self.assertEqual(decision(h,["A"],{"D"},False)["rotations"],[])
    def test_insufficient(self):
        self.assertEqual(decision([{"A":1}],["A"],{"B"},True)["status"],"BLOCKED")
    def test_noneligible(self):
        h=[dict(A=0,B=10,C=20,D=30) for _ in range(7)]
        self.assertEqual(decision(h,["A"],set(),True)["rotations"],[])
    def test_broken_advantage(self):
        h=[dict(A=0,B=10,C=20,D=30) for _ in range(7)]
        h[4]["D"]=3
        self.assertEqual(decision(h,["A"],{"D"},True)["rotations"],[])
if __name__=="__main__":unittest.main()
