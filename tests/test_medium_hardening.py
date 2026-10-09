import os
import signal
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

from fishing_core.retention import prune_runs,RotatingLog
from fishing_core.farm_multi import Heartbeat
from scripts import instalar


class HardeningTests(unittest.TestCase):
    def test_retention_age_quota_and_protected_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/'runs';runs.mkdir()
            protected=['brave-data','configs','sessions','accounts/enabled','boost_purchases','loot_totals']
            for name in protected:
                p=runs/name;p.mkdir(parents=True);(p/'keep').write_text('private')
            protected_session=runs/'accounts/enabled/20261001_120000_eeeeeeeeeeee'
            protected_session.mkdir();(protected_session/'keep').write_text('protected')
            paths=[runs/'20261001_120000_aaaaaaaaaaaa',runs/'accounts/personal/20261002_120000_bbbbbbbbbbbb',
                   runs/'20261003_120000_cccccccccccc']
            for i,p in enumerate(paths):
                p.mkdir(parents=True);(p/'log').write_bytes(b'x'*10)
                os.utime(p/'log',(100+i,100+i));os.utime(p,(100+i,100+i))
            (runs/'20261004_120000_dddddddddddd').symlink_to(runs/'brave-data',target_is_directory=True)
            self.assertEqual(prune_runs(root,now=1000,max_age=899,max_bytes=10),paths[:2])
            self.assertTrue(paths[2].exists())
            for name in protected:self.assertEqual((runs/name/'keep').read_text(),'private')
            self.assertTrue((protected_session/'keep').exists())

    def test_log_rotation_and_large_record_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'app.log'
            with RotatingLog(p,max_bytes=10) as log:
                log.write('12345678');log.write('abcd');log.write('x'*100)
            self.assertEqual(p.read_text(),'x'*10)
            self.assertEqual(p.with_name('app.log.1').read_text(),'abcd')

    def test_heartbeat_progress_and_escalation(self):
        worker=Mock()
        with patch('fishing_core.farm_multi.time.monotonic',return_value=0):beat=Heartbeat()
        self.assertFalse(beat.check(worker,2699))
        with patch('fishing_core.farm_multi.time.monotonic',return_value=200):beat.progress()
        self.assertFalse(beat.check(worker,2700))
        for now in (2900,2930,2960):self.assertTrue(beat.check(worker,now))
        beat.check(worker,4000)
        if os.name=='nt':
            worker.send_signal.assert_called_once_with(signal.SIGINT)
            worker.terminate.assert_called_once();worker.kill.assert_called_once()
        else:
            self.assertEqual([c.args[0] for c in worker.send_signal.call_args_list],
                             [signal.SIGINT,signal.SIGTERM,signal.SIGKILL])

    def test_installer_requires_hashes_only_with_lock(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(instalar,'ROOT',Path(tmp)):
            self.assertNotIn('--require-hashes',instalar.install_command('python'))
            (Path(tmp)/'requirements.lock').write_text('package==1 --hash=sha256:example')
            cmd=instalar.install_command('python')
            self.assertIn('--require-hashes',cmd);self.assertEqual(cmd[-1],str(Path(tmp)/'requirements.lock'))

    def test_installer_main_passes_hash_option_to_pip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);python=root/'.venv/Scripts/python.exe'
            python.parent.mkdir(parents=True);python.touch()
            (root/'requirements.lock').write_text('placeholder')
            with patch.object(instalar,'ROOT',root),patch.object(instalar,'os',SimpleNamespace(name='nt')), \
                    patch.object(instalar.sys,'version_info',(3,13)), \
                    patch.object(instalar.subprocess,'run') as run,patch('builtins.print'):
                self.assertEqual(instalar.main(),0)
            self.assertEqual(run.call_args_list[0].args[0],
                             [str(python),'-m','pip','install','--require-hashes','-r',str(root/'requirements.lock')])
            self.assertEqual(run.call_count,2)
