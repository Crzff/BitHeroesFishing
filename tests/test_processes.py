import subprocess
import unittest
from uuid import uuid4
from unittest.mock import Mock, patch

from fishing_core.processes import close_children, Mutex, console_launcher


class ProcessTests(unittest.TestCase):
    def test_windows_mutex_refuses_duplicate(self):
        role="TEST_"+uuid4().hex
        first=Mutex(role)
        try:
            with self.assertRaises(RuntimeError):
                Mutex(role)
        finally:
            first.close()

    def test_survivor_is_closed_when_other_exited(self):
        exited=Mock()
        exited.poll.return_value=0
        alive=Mock()
        alive.poll.return_value=None
        alive.wait.side_effect=[subprocess.TimeoutExpired("python",1),None]
        channel=Mock()
        close_children((exited,alive),channel)
        alive.terminate.assert_called_once()
        exited.terminate.assert_not_called()
        channel.stop.assert_called_once()

    def test_stop_ipc_error_still_closes_both(self):
        channel=Mock()
        channel.stop.side_effect=OSError("denied")
        children=[]
        for _ in range(2):
            p=Mock()
            p.poll.return_value=None
            p.wait.side_effect=[subprocess.TimeoutExpired("python",1),None]
            children.append(p)
        with self.assertRaises(RuntimeError):
            close_children(children,channel)
        for p in children:
            p.terminate.assert_called_once()

    def test_launcher_releases_mutex_when_close_reports_error(self):
        catch,control,channel,mutex=Mock(),Mock(),Mock(run_id="test"),Mock()
        catch.poll.return_value=0
        with patch("fishing_core.processes.start_children",return_value=(catch,control,channel,mutex)), \
             patch("fishing_core.processes.minimize_console"), \
             patch("fishing_core.processes.close_children",side_effect=RuntimeError("IPC error")):
            with self.assertRaises(RuntimeError):
                console_launcher()
        mutex.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
