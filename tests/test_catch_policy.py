import unittest

from fishing_core.catch_policy import CatchPolicy
from fishing_core.offline_model import load_model


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load_model()

    def pair(self,delta1,delta2,pct1=100,pct2=100,delay=0):
        p=CatchPolicy()
        p.seen(1-delay)
        cfg=self.m.ConfigV6()
        a=self.m.Obs(1,960+delta1,960,76,70)
        b=self.m.Obs(1+.017,960+delta2,960,76,70)
        d=self.m.Decision(False,"sin_ajuste",horizonte_ms=30)
        self.assertFalse(p.evaluate(a,pct1,d,cfg).disparar)
        return p.evaluate(b,pct2,d,cfg)

    def test_initial_100_confirmed_and_projected_inside(self):
        d=self.pair(2,-4)
        self.assertTrue(d.disparar)
        self.assertEqual(d.motivo,"APARICION_100_CONFIRMADA")

    def test_not_a_single_frame_percentage_trigger(self):
        self.assertFalse(self.pair(2,-4,75,100).disparar)
        self.assertFalse(self.pair(2,-4,100,75).disparar)

    def test_departing_or_late_cases_rejected(self):
        self.assertFalse(self.pair(20,28).disparar)
        self.assertFalse(self.pair(2,-4,delay=.3).disparar)

    def test_initial_route_cannot_override_current_sample_mismatch(self):
        p=CatchPolicy()
        p.seen(1)
        cfg=self.m.ConfigV6()
        a=self.m.Obs(1,962,960,76,70)
        b=self.m.Obs(1.017,956,960,76,70)
        p.evaluate(a,100,self.m.Decision(False,"sin_ajuste",horizonte_ms=30),cfg)
        d=self.m.Decision(False,"FIT_CURRENT_SAMPLE_MISMATCH",horizonte_ms=30,endpoint_error_px=31)
        self.assertFalse(p.evaluate(b,100,d,cfg).disparar)


if __name__ == "__main__":
    unittest.main()
