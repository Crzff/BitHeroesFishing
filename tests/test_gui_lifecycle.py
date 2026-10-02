import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import FISHING_BOT_APP as gui


class GuiTests(unittest.TestCase):
    def test_survivor_closed_before_handles_forgotten(self):
        first,second=Mock(),Mock()
        first.poll.return_value=0
        second.poll.return_value=None
        mutex=Mock()
        app=SimpleNamespace(p_catch=first,p_control=second,channel=Mock(),launch_mutex=mutex,
                             bot_activo=True,_idle_pending=True,_log=Mock(),_actualizar_ui=Mock(),_restaurar_vista_panel=Mock())
        def close(children,channel):
            self.assertIs(app.p_control,second)
            second.poll.return_value=0
        with patch.object(gui,"close_children",side_effect=close) as closed:
            gui.FishingBotApp._after_idle(app)
        closed.assert_called_once()
        self.assertIsNone(app.p_catch)
        self.assertIsNone(app.p_control)
        self.assertFalse(app.bot_activo)
        app._restaurar_vista_panel.assert_called_once()
        mutex.close.assert_called_once()

    def test_unclosed_survivor_remains_referenced(self):
        p=Mock()
        p.poll.return_value=None
        app=SimpleNamespace(p_catch=None,p_control=p,channel=Mock(),launch_mutex=Mock(),
                             bot_activo=True,_idle_pending=True,_log=Mock(),_actualizar_ui=Mock(),_restaurar_vista_panel=Mock())
        with patch.object(gui,"close_children",side_effect=OSError("denied")):
            gui.FishingBotApp._after_idle(app)
        self.assertIs(app.p_control,p)
        self.assertTrue(app.bot_activo)
        app.launch_mutex.close.assert_not_called()
        app._restaurar_vista_panel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
