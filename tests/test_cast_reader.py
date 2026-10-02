import unittest

import numpy as np

from fishing_core.cast_reader import CastReader
from fishing_core.vision import UIClassifier,FrameView


class CastReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader=CastReader()

    def stamp(self,image,value,x,y):
        for digit in str(value):
            glyph=self.reader.refs[int(digit)][0]*255
            image[y:y+glyph.shape[0],x:x+glyph.shape[1]]=glyph[:,:,None]
            x+=glyph.shape[1]+3

    def image(self,minimum=20,maximum=40,value=40,button=True):
        image=np.zeros((1080,1920,3),np.uint8)
        self.stamp(image,minimum,290,785)
        self.stamp(image,maximum,1530,785)
        self.stamp(image,value,910,785)
        if button:
            glyph=UIClassifier().templates["CAST"].astype(np.uint8)*255
            image[950:950+glyph.shape[0],875:875+glyph.shape[1]]=glyph[:,:,None]
        return image

    def test_all_real_digits_and_synthetic_1_to_99_numbers(self):
        for value in range(1,100):
            image=np.zeros((65,140,3),np.uint8)
            self.stamp(image,value,5,10)
            self.assertEqual(self.reader.number(image)[0],value,value)

    def test_current_20_to_40_and_other_limits_are_dynamic_not_fixed_target(self):
        for maximum in (30,40,48,50,60,80,99,100):
            measured=self.reader.measure(FrameView(self.image(maximum=maximum,value=maximum)))
            self.assertTrue(measured["CAST_RANGE_VALID"],measured)
            self.assertEqual(measured["CAST_MAX"],maximum)

    def test_only_exact_maximum_is_ready_including_current_worse_rod(self):
        ui=UIClassifier()
        for maximum in (40,48):
            for value in range(20,maximum+1):
                status=ui.classify(FrameView(self.image(maximum=maximum,value=value)))
                self.assertEqual(status.kind,"CAST")
                self.assertEqual(status.ready,value==maximum,(maximum,value,status.scores))

    def test_local_capture_requires_a_full_range_first_then_reads_peak(self):
        ui=UIClassifier()
        image=self.image()
        local=FrameView(image[775:1020,830:1090],830,775)
        self.assertFalse(ui.cast_status(local).ready)
        ui.classify(FrameView(image))
        status=ui.cast_status(local)
        self.assertTrue(status.ready)
        self.assertEqual((status.scores["CAST_MIN"],status.scores["CAST_MAX"],status.scores["CAST_VALUE"]),(20,40,40))

    def test_bad_limits_out_of_range_and_missing_button_do_not_click(self):
        for image in (self.image(minimum=40,maximum=20),self.image(minimum=20,maximum=20),
                      self.image(value=41),self.image(value=10),self.image(button=False)):
            self.assertFalse(UIClassifier().classify(FrameView(image)).ready)

    def test_missing_or_truncated_number_is_not_promoted_from_a_score(self):
        self.assertIsNone(self.reader.number(np.zeros((65,140,3),np.uint8))[0])
        image=np.zeros((38,140,3),np.uint8)
        self.stamp(image,40,0,0)
        self.assertIsNone(self.reader.number(image)[0])

    def test_unknown_or_scaled_fonts_reject_instead_of_guessing_peak(self):
        image=np.zeros((65,140,3),np.uint8)
        image[10:48,10:70]=255
        self.assertIsNone(self.reader.number(image)[0])

    def test_missing_endpoint_clears_old_range_on_next_full_classification(self):
        ui=UIClassifier()
        self.assertTrue(ui.classify(FrameView(self.image())).ready)
        image=self.image()
        image[775:840,1520:1640]=0
        self.assertFalse(ui.classify(FrameView(image)).ready)
        self.assertFalse(ui.cast_status(FrameView(image[775:1020,830:1090],830,775)).ready)
