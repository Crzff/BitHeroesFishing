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

    def test_frames_never_returns_a_frame_older_than_requested(self):
        frames=gamescope.PipeWireFrames.__new__(gamescope.PipeWireFrames)
        frames.lock=__import__('threading').Lock();frames.latest=bytes(gamescope.FRAME);frames.stamp=time.monotonic()-5
        frames.proc=SimpleNamespace(poll=lambda:None)
        with self.assertRaises(RuntimeError):frames.frame(time.monotonic(),timeout=0.05)
        self.assertEqual(frames.frame(time.monotonic()-10).shape,(1080,1920,3))

    def test_io_rejects_coordinates_outside_and_checks_f8_and_window_first(self):
        io=gamescope.GamescopeIO.__new__(gamescope.GamescopeIO);io.control_mode=False
        io.game_guard=SimpleNamespace(desktop=Mock(),check=Mock(),display=Mock())
        with self.assertRaises(SafetyStop):io._move((1920,10))
        io.game_guard.desktop.emergency.side_effect=KeyboardInterrupt('F8')
        with self.assertRaises(KeyboardInterrupt):io.click((10,10))
        io.game_guard.display.sync.assert_not_called()

    def test_backend_selection(self):
        with patch.dict('os.environ',{'FARM_BACKEND':'gamescope'}):
            self.assertIs(gamescope.backend()[0],gamescope.GamescopeIO)
        with patch.dict('os.environ',{'FARM_BACKEND':''}):
            self.assertEqual(gamescope.backend()[0].__name__,'LinuxIO')


if __name__=='__main__':unittest.main()
