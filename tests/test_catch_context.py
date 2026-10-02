import unittest

from fishing_core.catch_context import can_track,input_block
from fishing_core.vision import Evidence


class CatchContextTests(unittest.TestCase):
    def status(self,kind="CATCH_ACTIVE",pct=100):
        return Evidence(kind,(960,970),True,pct,{"CATCH":.97})

    def test_unknown_percentage_with_accepted_catch_text_is_tracking_only(self):
        status=self.status("UNKNOWN",None)
        self.assertTrue(can_track(status))
        self.assertEqual(input_block(status,0,10_000_000),"DISPLAY_NOT_100")

    def test_no_text_or_other_screen_never_tracks_or_authorizes_input(self):
        for kind in ("CAST","START","SUCCESS","CATCH_PENDING","ITEMS"):
            status=self.status(kind)
            self.assertFalse(can_track(status))
            self.assertEqual(input_block(status,0,10_000_000),"DISPLAY_NOT_100")
        for status in (Evidence("UNKNOWN"),Evidence("UNKNOWN",(960,970),True,None,{"CATCH":.85}),
                       Evidence("CATCH_ACTIVE",None,False,100)):
            self.assertFalse(can_track(status))

    def test_known_percentages_below_100_only_track(self):
        for pct in (0,25,50,75):
            status=self.status(pct=pct)
            self.assertTrue(can_track(status))
            self.assertEqual(input_block(status,0,10_000_000),"DISPLAY_NOT_100")

    def test_fresh_100_required_even_after_other_checks(self):
        status=self.status()
        self.assertIsNone(input_block(status,100,60_000_100))
        self.assertEqual(input_block(status,100,60_000_101),"CAPTURE_TOO_OLD")
        self.assertEqual(input_block(status,100,99),"CAPTURE_TOO_OLD")
