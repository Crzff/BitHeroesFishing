import unittest
import numpy as np

from fishing_core.detector import Detector
from fishing_core.vision import FrameView

class DetectorTests(unittest.TestCase):
    def scene(self,fish_left=865,fish_width=48):
        """Escena sintetica; no depende de capturas de una cuenta."""
        image=np.zeros((1080,1920,3),np.uint8)
        image[741:751,860:918]=(80,210,100)
        image[770:825,fish_left:fish_left+fish_width]=(30,100,240)
        return FrameView(image)

    def test_synthetic_centered_fish_and_single_zone(self):
        d,info=Detector().detect(self.scene(),1)
        self.assertIsNotNone(d,info)
        self.assertLess(abs(d.centro_zona-888.5),8)
        self.assertLess(abs(d.centro_pez-d.centro_zona),15)
        self.assertLess(d.ancho_zona,100)

    def test_synthetic_offset_fish_has_separate_geometry(self):
        d,info=Detector().detect(self.scene(fish_left=910,fish_width=60),1)
        self.assertIsNotNone(d,info)
        self.assertGreater(d.ancho_pez,50)
        self.assertLess(d.ancho_zona,100)

    def test_background_and_tiny_red_object_rejected(self):
        image=np.zeros((1080,1920,3),np.uint8)
        image[741:751,900:950]=(80,210,100)
        image[770:810,880:887]=(30,100,240)
        d,info=Detector().detect(FrameView(image),1)
        self.assertIsNone(d)
        self.assertEqual(info["reason"],"PEZ_AUSENTE_O_AMBIGUO")

    def test_multiple_zones_rejected_without_identity(self):
        image=np.zeros((1080,1920,3),np.uint8)
        image[741:751,900:950]=(80,210,100)
        image[741:751,1100:1150]=(80,210,100)
        self.assertIsNone(Detector().detect(FrameView(image),1)[0])


if __name__ == "__main__":
    unittest.main()
