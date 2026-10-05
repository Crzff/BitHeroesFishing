"""Backend gamescope sin juego: búsqueda del nodo PipeWire, recorte de fotogramas y guardas."""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from fishing_core import gamescope
from fishing_core.control_flow import SafetyStop

PW="""	id 98, type PipeWire:Interface:Node/3
 		object.serial = "4441"
 		node.name = "gamescope"
 		media.class = "Video/Source"
	id 99, type PipeWire:Interface:Node/3
 		object.serial = "4500"
 		node.name = "otro"
 		media.class = "Audio/Sink"
"""


class GamescopeTests(unittest.TestCase):
    def test_finds_the_gamescope_video_node_and_rejects_its_absence(self):
        with patch('fishing_core.gamescope.subprocess.run',return_value=SimpleNamespace(stdout=PW)):
            self.assertEqual(gamescope.pipewire_serial(),'4441')
        with patch('fishing_core.gamescope.subprocess.run',return_value=SimpleNamespace(stdout=PW.replace('gamescope','x'))):
            with self.assertRaises(RuntimeError):gamescope.pipewire_serial()

    def capture(self,frame,check=None):
        cap=gamescope.GamescopeCapture.__new__(gamescope.GamescopeCapture)
        cap.guard=SimpleNamespace(check=check or (lambda:None))
        cap.frames=SimpleNamespace(frame=lambda newer_than:frame)
        return cap

    def test_grab_crops_the_latest_frame_as_bgra(self):
        frame=np.zeros((1080,1920,3),np.uint8);frame[10,20]=(1,2,3)
        shot=self.capture(frame).grab({'left':20,'top':10,'width':4,'height':2})
        pixels=np.frombuffer(shot.bgra,np.uint8).reshape(2,4,4)
        self.assertEqual(tuple(pixels[0,0]),(1,2,3,255))

    def test_grab_refuses_regions_outside_the_game_and_a_lost_window(self):
        frame=np.zeros((1080,1920,3),np.uint8)
        with self.assertRaises(SafetyStop):self.capture(frame).grab({'left':1900,'top':0,'width':40,'height':10})
        def gone():raise RuntimeError('La ventana de Bit Heroes desapareció de gamescope')
        with self.assertRaises(SafetyStop):self.capture(frame,gone).grab({'left':0,'top':0,'width':10,'height':10})

    def frames(self,latest,alive=True):
        frames=gamescope.PipeWireFrames.__new__(gamescope.PipeWireFrames)
        frames.lock=__import__('threading').Lock();frames.latest=latest;frames.stamp=time.monotonic()-5;frames.error=None
        frames.proc=SimpleNamespace(poll=lambda:None if alive else 1)
        return frames

    def test_a_still_screen_reuses_the_last_frame_only_while_the_stream_is_alive(self):
        self.assertEqual(self.frames(bytes(gamescope.FRAME)).frame(time.monotonic(),timeout=0.05).shape,(1080,1920,3))
        with self.assertRaises(RuntimeError):self.frames(bytes(gamescope.FRAME),alive=False).frame(time.monotonic(),timeout=0.05)

    def test_no_frame_at_all_is_an_error(self):
        with self.assertRaises(RuntimeError):self.frames(None).frame(time.monotonic(),timeout=0.01)

    def test_io_rejects_coordinates_outside_and_checks_f8_and_window_first(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO);io.control_mode=False
        io.game_guard=SimpleNamespace(desktop=Mock(),check=Mock(),display=Mock())
        with self.assertRaises(SafetyStop):io._move((1920,10))
        io.game_guard.desktop.emergency.side_effect=KeyboardInterrupt('F8')
        with self.assertRaises(KeyboardInterrupt):io.click((10,10))
        io.game_guard.display.sync.assert_not_called()

    def guard(self,focused,cls):
        g=gamescope.GamescopeGuard.__new__(gamescope.GamescopeGuard)
        g.window=SimpleNamespace(id=1);state={'focused':focused,'closed':0}
        other=Mock();other.get_wm_class.return_value=cls
        def send(message):state['closed']+=1;state['focused']=1
        other.send_event.side_effect=send
        g.display=Mock();g.display.create_resource_object.return_value=other;g.display.intern_atom.return_value=7
        g.focused=lambda:state['focused']
        return g,state

    def test_a_steam_window_over_the_game_is_closed_and_anything_else_stops(self):
        with patch('fishing_core.gamescope.window_of',return_value=object()),patch('fishing_core.gamescope.time.sleep'), \
                patch('Xlib.protocol.event.ClientMessage'):
            g,state=self.guard(2,('steamwebhelper','steam'));g.check();self.assertEqual(state['closed'],1)
            g,state=self.guard(2,('otra','app'))
            with self.assertRaises(RuntimeError):g.check()
            self.assertEqual(state['closed'],0)
            g,state=self.guard(1,None);g.check();self.assertEqual(state['closed'],0)

    def test_backend_selection(self):
        with patch.dict('os.environ',{'FARM_BACKEND':'gamescope'}):
            self.assertIs(gamescope.backend()[0],gamescope.GamescopeIO)
        with patch.dict('os.environ',{'FARM_BACKEND':''}):
            self.assertEqual(gamescope.backend()[0].__name__,'LinuxIO')


if __name__=='__main__':unittest.main()
