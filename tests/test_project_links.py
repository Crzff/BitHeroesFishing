import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import FISHING_BOT_APP as gui
from fishing_core.project_links import support_url


class ProjectLinksTests(unittest.TestCase):
    def test_only_a_direct_https_kofi_profile_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for url in ('http://ko-fi.com/test','https://evil.example/test',
                        'https://ko-fi.com.evil.example/test','javascript:alert(1)',
                        'https://ko-fi.com/test?extra=1','https://ko-fi.com/test/sub',None,42):
                (root/'project_links.json').write_text(json.dumps({'support':url}))
                self.assertIsNone(support_url(root),url)
            (root/'project_links.json').write_text(json.dumps({'support':'https://ko-fi.com/fmani3496'}))
            self.assertEqual(support_url(root),'https://ko-fi.com/fmani3496')

    def test_bad_or_missing_configuration_is_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertIsNone(support_url(root))
            for text in ('not json','[]','null'):
                (root/'project_links.json').write_text(text)
                self.assertIsNone(support_url(root))

    def test_support_never_opens_while_fishing(self):
        app=SimpleNamespace(bot_activo=True)
        with patch('webbrowser.open') as opened:
            gui.FishingBotApp._abrir_apoyo(app)
        opened.assert_not_called()

    def test_explicit_idle_action_only_opens_the_valid_profile(self):
        app=SimpleNamespace(bot_activo=False)
        with patch.object(gui,'support_url',return_value='https://ko-fi.com/fmani3496'), \
             patch('webbrowser.open') as opened:
            gui.FishingBotApp._abrir_apoyo(app)
        opened.assert_called_once_with('https://ko-fi.com/fmani3496')
