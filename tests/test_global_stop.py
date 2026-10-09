import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fishing_core import global_stop


@unittest.skipUnless(sys.platform=='linux','Parada global Linux/niri')
class GlobalStopTests(unittest.TestCase):
    def test_only_known_python_workers_of_this_user_and_project_are_selected(self):
        root=global_stop.ROOT;uid=os.getuid()
        for argv in ([sys.executable,'-B','-u','-m','fishing_core.farm_all'],
                     [sys.executable,'-B','-u','-m','fishing_core.farm_multi'],
                     [sys.executable,'-B',str(root/'FARM_DUNGEON_PROCESS.py')],
                     [sys.executable,'-B',str(root/'CATCH_FAST_PROCESS_V6_FINAL.py')],
                     [sys.executable,'-B',str(root/'FISHING_CONTROL_PROCESS.py')]):
            self.assertTrue(global_stop.is_worker(argv,root,uid),argv)
            self.assertFalse(global_stop.is_worker(argv,root.parent,uid))
            self.assertFalse(global_stop.is_worker(argv,root,uid+1))

    def test_browsers_panels_frames_tests_and_command_snippets_are_never_selected(self):
        root=global_stop.ROOT
        for argv in ([],['brave','fishing_core.farm_all'],['steam'],
                     [sys.executable,'-m','fishing_core.farm_app'],
                     [sys.executable,'-m','fishing_core.gamescope','serve'],
                     [sys.executable,'-m','unittest'],
                     [sys.executable,'-m','fishing_core.farm_all_other'],
                     [sys.executable,'-m','fishing_core.farm_multi_other'],
                     [sys.executable,'-c','print("fishing_core.farm_all")'],
                     [sys.executable,str(root/'FISHING_BOT_APP.py')],
                     [sys.executable,str(root/'global_stop.py')]):
            self.assertFalse(global_stop.is_worker(argv,root,os.getuid()),argv)

    def test_probe_can_be_stopped_but_the_stop_command_cannot_stop_itself(self):
        argv=[sys.executable,'-B',str(global_stop.ROOT/'fishing_core/global_stop.py')]
        self.assertFalse(global_stop.is_worker(argv,global_stop.ROOT,os.getuid()))
        self.assertTrue(global_stop.is_worker(argv+['--probe'],global_stop.ROOT,os.getuid()))

    def test_pidfd_is_opened_before_identity_checks_and_only_workers_receive_sigint(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc=Path(tmp)
            for pid,argv in ((123,[sys.executable,'-B','-m','fishing_core.farm_all']),
                             (456,['brave','--kiosk'])):
                directory=proc/str(pid);directory.mkdir();(directory/'cwd').symlink_to(global_stop.ROOT)
                (directory/'cmdline').write_bytes(b'\0'.join(os.fsencode(a) for a in argv)+b'\0')
            with patch.object(global_stop.os,'pidfd_open',side_effect=lambda pid:pid+1000) as opened, \
                    patch.object(global_stop.signal,'pidfd_send_signal') as sent, \
                    patch.object(global_stop.os,'close') as closed:
                self.assertEqual(global_stop.stop_workers(proc),1)
                sent.assert_called_once_with(1123,global_stop.signal.SIGINT)
                self.assertEqual(opened.call_count,2)
                self.assertCountEqual([call.args[0] for call in closed.call_args_list],[1123,1456])

    @unittest.skipUnless(sys.platform=='linux','pidfd Linux')
    def test_real_probe_exits_cleanly_on_the_same_stop_path_without_a_game(self):
        p=subprocess.Popen([sys.executable,'-B','-m','fishing_core.global_stop','--probe'],
                           cwd=global_stop.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertEqual(p.stdout.readline().strip(),'PROBE_READY')
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp)/str(p.pid)).symlink_to(Path('/proc')/str(p.pid))
                self.assertEqual(global_stop.stop_workers(Path(tmp)),1)
            out,err=p.communicate(timeout=5)
            self.assertEqual(p.returncode,0,err)
            self.assertIn('PROBE_STOPPED',out)
        finally:
            if p.poll() is None:p.terminate()
            p.communicate(timeout=5)


if __name__=='__main__':unittest.main()
