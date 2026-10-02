import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import FISHING_BOT_APP as gui


class PanelPreferencesTests(unittest.TestCase):
    def test_invalid_types_or_keys_preserve_original_file_and_safe_default(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"preferences.json"
            for data in ({"siempre_visible":"false"},{"siempre_visible":0},{"siempre_visible":False,"other":1},[],{}):
                path.write_text(json.dumps(data),encoding="utf-8")
                before=path.read_bytes()
                app=SimpleNamespace(siempre_visible=False,_log=Mock())
                with patch.object(gui,"CONFIG_FILE",path):
                    gui.FishingBotApp._cargar_config(app)
                self.assertFalse(app.siempre_visible)
                self.assertEqual(path.read_bytes(),before)
                app._log.assert_called_once()

    def test_valid_preference_loads_and_atomic_save_is_used(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"preferences.json"
            path.write_text('{"siempre_visible":true}')
            app=SimpleNamespace(siempre_visible=False,_log=Mock())
            with patch.object(gui,"CONFIG_FILE",path):
                gui.FishingBotApp._cargar_config(app)
                self.assertTrue(app.siempre_visible)
                with patch.object(gui,"atomic_json") as save:
                    gui.FishingBotApp._guardar_config(app)
                save.assert_called_once_with(path,{"siempre_visible":True})

    def test_failed_save_does_not_fall_back_to_overwriting_the_config(self):
        app=SimpleNamespace(siempre_visible=True,_log=Mock())
        with patch.object(gui,"atomic_json",side_effect=OSError("denied")) as save:
            gui.FishingBotApp._guardar_config(app)
        save.assert_called_once()
        self.assertIn("Error guardando",app._log.call_args.args[0])
