"""Escenas sinteticas, no capturas de cuentas ni inputs reales al juego."""

import unittest
from unittest.mock import Mock,patch

import numpy as np

from fishing_core import navigation
from fishing_core.vision import Evidence,FrameView


class NavigationTests(unittest.TestCase):
    def scene(self,kind):
        vision=navigation.NavigationClassifier()
        image=np.zeros((1080,1920,3),np.uint8)
        keys={"HOME":("HOME_FISHING","HOME_SETTINGS"),
              "FISHING_MENU":("FISHING_TITLE","FISHING_PLAY","FISHING_EVENTS")}.get(kind,())
        for key in keys:
            x0,y0,x1,y1=navigation.ROIS[key]
            template=vision.templates[key].astype(np.uint8)
            x=x0+(x1-x0-template.shape[1])//2
            y=y0+(y1-y0-template.shape[0])//2
            image[y:y+template.shape[0],x:x+template.shape[1]]=template[:,:,None]*255
        if kind=="START":image[0,0]=1
        return image

    def test_home_and_menu_need_multiple_independent_labels(self):
        vision=navigation.NavigationClassifier()
        for kind in ("HOME","FISHING_MENU"):
            image=self.scene(kind)
            result=vision.classify(FrameView(image),Evidence())
            self.assertEqual(result.kind,kind)
            self.assertTrue(result.ready)
        image=self.scene("HOME")
        x0,y0,x1,y1=navigation.ROIS["HOME_SETTINGS"]
        image[y0:y1,x0:x1]=0
        self.assertEqual(vision.classify(FrameView(image)).kind,"UNKNOWN")
        image=self.scene("FISHING_MENU")
        x0,y0,x1,y1=navigation.ROIS["FISHING_TITLE"]
        image[y0:y1,x0:x1]=0
        self.assertEqual(vision.classify(FrameView(image)).kind,"UNKNOWN")

    def test_existing_fishing_screen_always_has_priority_over_home_labels(self):
        vision=navigation.NavigationClassifier()
        for kind in navigation.ALREADY_FISHING:
            existing=Evidence(kind,(960,970),True)
            self.assertIs(vision.classify(FrameView(self.scene("HOME")),existing),existing)

    def run_navigation(self,initial="HOME",mode="normal"):
        stage=initial
        clock=[0.]
        ui=Mock()
        ui.classify.side_effect=lambda view:Evidence("START",(960,970),True) if view.image[0,0,0]==1 else Evidence()
        io,log,stop=Mock(),Mock(),Mock()
        def grab():
            return self.scene(stage)
        def click(xy):
            nonlocal stage
            if stage=="HOME":stage="FISHING_MENU"
            elif stage=="FISHING_MENU":stage="UNKNOWN" if mode=="travel_timeout" else "START"
            else:raise AssertionError("No navigation input is allowed in this screen")
        io.click.side_effect=click
        if mode=="f8":stop.side_effect=KeyboardInterrupt("F8")
        def seconds():
            clock[0]+=.01
            return clock[0]
        def sleep(duration):clock[0]+=duration
        error=result=None
        with patch.object(navigation.time,"perf_counter",side_effect=seconds), \
             patch.object(navigation.time,"perf_counter_ns",side_effect=lambda:round(clock[0]*1e9)), \
             patch.object(navigation.time,"sleep",side_effect=sleep):
            try:result=navigation.enter_fishing(io,ui,grab,stop,log,timeout=3)
            except (navigation.SafetyStop,KeyboardInterrupt) as exc:error=exc
        return io,log,result,error

    def test_home_route_opens_fishing_then_play_and_never_clicks_start(self):
        io,log,result,error=self.run_navigation()
        self.assertIsNone(error)
        self.assertEqual(result[1].kind,"START")
        self.assertEqual(io.click.call_count,2)
        purposes=[call.args[0] and call.kwargs.get("purpose") for call in log.emit.call_args_list if call.args[0]=="NAVIGATION_INPUT_SENT"]
        self.assertEqual(purposes,["OPEN_FISHING","PLAY_FISHING"])
        self.assertTrue(all(call.args[0]!=(960,970) for call in io.click.call_args_list))

    def test_open_menu_only_clicks_play_and_start_entry_is_idempotent(self):
        io,log,result,error=self.run_navigation("FISHING_MENU")
        self.assertIsNone(error)
        io.click.assert_called_once()
        io,log,result,error=self.run_navigation("START")
        self.assertIsNone(error)
        io.click.assert_not_called()

    def test_unknown_screen_never_clicks_and_travel_does_not_repeat_play(self):
        io,log,result,error=self.run_navigation("UNKNOWN")
        self.assertIsInstance(error,navigation.SafetyStop)
        io.click.assert_not_called()
        io,log,result,error=self.run_navigation(mode="travel_timeout")
        self.assertIsInstance(error,navigation.SafetyStop)
        self.assertEqual(io.click.call_count,2)

    def test_f8_aborts_navigation_before_any_input(self):
        io,log,result,error=self.run_navigation(mode="f8")
        self.assertIsInstance(error,KeyboardInterrupt)
        io.click.assert_not_called()

    def test_fresh_verification_that_changed_screen_does_not_click_old_target(self):
        io,ui,log=Mock(),Mock(),Mock()
        ui.classify.return_value=Evidence()
        navigator=Mock()
        navigator.classify.side_effect=[Evidence("HOME",(1830,841),True)]*3+[Evidence("UNKNOWN")]*20
        clock=[0.]
        def seconds():clock[0]+=.12;return clock[0]
        with patch.object(navigation.time,"perf_counter",side_effect=seconds), \
             patch.object(navigation.time,"sleep"),self.assertRaises(navigation.SafetyStop):
            navigation.enter_fishing(io,ui,lambda:self.scene("UNKNOWN"),Mock(),log,navigator=navigator,timeout=1.5)
        io.click.assert_not_called()
