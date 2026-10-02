import unittest

import CATCH_FAST_PROCESS_V6_FINAL as model


class PredictorTests(unittest.TestCase):
    def test_unequal_intervals_have_containment_plateau(self):
        self.assertAlmostEqual(model.solape_fraccion(10,83,55),55/83)
        self.assertAlmostEqual(model.solape_fraccion(-10,83,55),55/83)
        self.assertEqual(model.solape_fraccion(100,83,55),0)
        self.assertEqual(model.solape_fraccion(0,0,55),0)

    def test_quiet_narrow_zone_is_not_impossible(self):
        cfg=model.ConfigV6()
        tracker=model.TrackerBarra(cfg)
        for i in range(5):
            obs=model.Obs(1+i*.017,500,500,83,43)
            tracker.agregar(obs)
        d=model.decidir(tracker,obs,.008,cfg,.01)
        self.assertTrue(d.disparar,d)
        self.assertEqual(d.motivo,"QUIETO_EN_ZONA")

    def test_theil_sen_and_historical_routes_preserved(self):
        v,delta=model.theil_sen([(0,20),(.05,10),(.1,0)])
        self.assertAlmostEqual(v,-200)
        self.assertAlmostEqual(delta,0)
        cfg=model.ConfigV6()
        tracker=model.TrackerBarra(cfg)
        for i in range(2):
            obs=model.Obs(1+i*.017,500,500,83,43)
            tracker.agregar(obs)
        self.assertEqual(model.decidir(tracker,obs,.008,cfg).motivo,"ALINEADO_SIN_HISTORIAL")

    def test_reset_clears_intervals_and_confirmation(self):
        tracker=model.TrackerBarra(model.ConfigV6())
        tracker.dts.append(.019)
        tracker.frames_acercando=5
        tracker.reset("test")
        self.assertEqual(len(tracker.dts),0)
        self.assertEqual(tracker.frames_acercando,0)

    def test_slow_frame_rejected_not_clamped(self):
        cfg=model.ConfigV6()
        tracker=model.TrackerBarra(cfg)
        for i in range(5):
            obs=model.Obs(1+i*.025,500,500,83,43)
            tracker.agregar(obs)
        self.assertAlmostEqual(tracker.dt_frame,.025)
        d=model.decidir(tracker,obs,.008,cfg)
        self.assertFalse(d.disparar)
        self.assertEqual(d.motivo,"FRAME_LENTO")

    def test_input_latency_update_does_not_add_capture(self):
        cfg=model.ConfigV6()
        self.assertAlmostEqual(model.actualizar_latencia_click(cfg,.02,.01),.017)


if __name__ == "__main__":
    unittest.main()
