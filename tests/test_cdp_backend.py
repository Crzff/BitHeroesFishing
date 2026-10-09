import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from PIL import Image
from fishing_core.cdp_backend import CdpIO,CdpCapture
from fishing_core.control_flow import SafetyStop


class CdpBackendTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'tests')
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);(self.root/'runs').mkdir()
        self.bridge=Mock();self.desktop=Mock()
        for name,value in [('ROOT',self.root),('brave_target',Mock(return_value=(1,9222,'A'*32))),
                ('account_id',Mock(return_value='personal')),('browser_identity',Mock(return_value=('original',))),
                ('Bridge',Mock(return_value=self.bridge)),('emergency_source',Mock(return_value=self.desktop))]:
            p=patch('fishing_core.cdp_backend.'+name,value);p.start();self.addCleanup(p.stop)
        self.io=CdpIO();self.addCleanup(self.io.close);self.bridge.reset_mock()

    def test_identity_change_or_death_latches_before_input(self):
        for failure in (('replacement',),RuntimeError('Proceso muerto'),ProcessLookupError('muerto')):
            with self.subTest(failure=failure):
                self.io.failed=False;self.io.identity_checked=0;self.bridge.reset_mock()
                with patch('fishing_core.cdp_backend.time.monotonic',return_value=3), \
                     patch('fishing_core.cdp_backend.browser_identity',side_effect=failure if isinstance(failure,Exception) else None,
                           return_value=failure):
                    with self.assertRaises(SafetyStop):self.io.click((10,20))
                    with self.assertRaises(SafetyStop):self.io.escape()
                self.bridge.call.assert_not_called()

    def test_identity_revalidation_is_limited_to_two_seconds(self):
        self.io.identity_checked=10
        with patch('fishing_core.cdp_backend.time.monotonic',side_effect=[11,12,13]), \
             patch('fishing_core.cdp_backend.browser_identity',return_value=self.io.identity) as identity:
            self.io.check();self.io.click((10,20));self.io.check()
        identity.assert_called_once_with(1,9222,'personal')

    def test_mouse_ops(self):
        self.io.click((10,20));self.io._move((30,40));self.io.wheel(-2,(50,60))
        self.assertEqual(self.bridge.call.call_args_list,[
            unittest.mock.call('click',xy=(10,20)),unittest.mock.call('move',xy=(30,40)),
            unittest.mock.call('wheel',xy=(50,60),steps=-2)])

    def test_refusal_latches_without_more_input(self):
        for op in ('click','move','wheel','check','frame','escapeDown'):
            with self.subTest(op=op):
                self.io.failed=False;self.bridge.reset_mock();self.bridge.call.side_effect=RuntimeError('refuse')
                with self.assertRaises(SafetyStop):self.io._call(op)
                with self.assertRaises(SafetyStop):self.io.click((10,20))
                self.assertEqual(self.bridge.call.call_count,1)

    def test_capture_crop_bgra_and_cleanup(self):
        def response(op,**kwargs):
            if op=='frame':
                image=Image.new('RGB',(1920,1080),(1,2,3));image.putpixel((11,21),(4,5,6))
                image.save(self.io.frames_dir/kwargs['path'])
        self.bridge.call.side_effect=response
        with CdpCapture(self.io.game_guard) as capture:
            shot=capture.grab({'left':10,'top':20,'width':2,'height':2})
            self.assertEqual(shot.size,(2,2))
            self.assertEqual(shot.bgra,bytes([3,2,1,255]*3+[6,5,4,255]))
        self.assertEqual(list(self.io.frames_dir.iterdir()),[])

    def test_bad_frame_stops(self):
        def response(op,**kwargs):
            if op=='frame':Image.new('RGB',(1920,1024)).save(self.io.frames_dir/kwargs['path'])
        self.bridge.call.side_effect=response
        with self.assertRaises(SafetyStop):CdpCapture(self.io).grab({'left':0,'top':0,'width':1,'height':1})
        with self.assertRaises(SafetyStop):self.io.click((1,1))
        self.assertEqual(self.bridge.call.call_count,1)

    def test_bad_crop_sends_nothing(self):
        with self.assertRaises(SafetyStop):CdpCapture(self.io).grab({'left':1919,'top':0,'width':2,'height':1})
        self.bridge.call.assert_not_called()

    def test_emergency_and_read_only(self):
        self.desktop.emergency.side_effect=KeyboardInterrupt('F8')
        with self.assertRaises(KeyboardInterrupt):self.io.click((1,1))
        self.bridge.call.assert_not_called()
        self.io.failed=False;self.desktop.emergency.side_effect=None;self.io.read_only=True
        with self.assertRaises(SafetyStop):self.io.escape()
        self.bridge.call.assert_not_called()

    def test_changed_endpoint_stops(self):
        with patch('fishing_core.cdp_backend.brave_target',return_value=(2,9223,'B'*32)):
            with self.assertRaises(SafetyStop):self.io.click((1,1))
        self.bridge.call.assert_not_called()
