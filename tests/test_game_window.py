"""Ventanas e input falsos: estas pruebas no hacen clic ni abren el juego."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fishing_core.game_window import (CHROME_TITLE, ENV_WINDOW, GameWindow, WindowGuard,
                                      focus_window, select_window, validate_geometry, window_client)
from fishing_core import processes, runtime


class GameWindowTests(unittest.TestCase):
    def game(self, client="Steam", hwnd=123):
        return GameWindow(hwnd,456,client,(0,0,1920,1080))

    def api(self, game):
        api=Mock()
        api.screen.return_value=(1920,1080)
        api.windows.return_value=[game]
        api.inspect.return_value=game
        api.foreground.return_value=game.hwnd
        api.pid.return_value=game.pid
        api.title.return_value="Bit Heroes" if game.client=="Steam" else CHROME_TITLE
        api.rect.return_value=game.rect
        api.user.IsWindow.return_value=True
        api.user.IsWindowVisible.return_value=True
        api.user.IsIconic.return_value=False
        return api

    def test_steam_identity_requires_title_class_and_executable(self):
        self.assertEqual(window_client("Bit Heroes","UnityWndClass",r"D:\Steam\Bit Heroes.exe"),"Steam")
        for title,cls,exe in (("Bit Heroes","UnityWndClass","other.exe"),
                              ("Bit Heroes","Chrome_WidgetWin_1","Bit Heroes.exe"),
                              ("Other Game","UnityWndClass","Bit Heroes.exe")):
            self.assertIsNone(window_client(title,cls,exe))

    def test_chrome_and_steam_are_independent(self):
        self.assertEqual(window_client(CHROME_TITLE,"Chrome_WidgetWin_1","chrome.exe"),"Chrome")
        self.assertIsNone(window_client(CHROME_TITLE,"Chrome_WidgetWin_1","brave.exe"))
        steam=self.game()
        chrome=self.game("Chrome",789)
        self.assertEqual(select_window([steam],"Auto"),steam)
        self.assertEqual(select_window([steam,chrome],"Steam"),steam)
        self.assertEqual(select_window([steam,chrome],"Chrome"),chrome)

    def test_missing_ambiguous_and_duplicate_windows_are_not_guessed(self):
        for windows,client in (([],"Auto"),([self.game()],"Chrome"),
                               ([self.game(),self.game("Chrome",789)],"Auto"),
                               ([self.game(),self.game(hwnd=789)],"Steam"),([self.game()],"Other")):
            with self.assertRaises(RuntimeError):
                select_window(windows,client)

    def test_geometry_rejects_scaled_moved_or_second_monitor_steam(self):
        validate_geometry(self.game(),(1920,1080))
        validate_geometry(GameWindow(123,456,"Chrome",(0,87,1920,1080)),(1920,1080))
        for rect in ((10,10,1930,1090),(0,0,1280,720),(1920,0,3840,1080),(0,30,1920,1080)):
            with self.assertRaises(RuntimeError):
                validate_geometry(GameWindow(123,456,"Steam",rect),(1920,1080))
        with self.assertRaises(RuntimeError):
            validate_geometry(self.game(),(2560,1440))

    def test_binding_round_trip_and_invalid_types(self):
        game=self.game()
        self.assertEqual(GameWindow.deserialize(game.serialize()),game)
        value=json.loads(game.serialize())
        for key,invalid in (("hwnd",True),("pid",0),("client","Auto"),("rect",[0,0,1920])):
            altered={**value,key:invalid}
            with self.assertRaises(RuntimeError):
                GameWindow.deserialize(json.dumps(altered))

    def test_focus_steam_uses_no_game_click_and_confirms_identity(self):
        game=self.game()
        api=self.api(game)
        self.assertEqual(focus_window("Steam",api),game)
        api.activate.assert_called_once_with(game.hwnd)
        api.user.mouse_event.assert_not_called()
        api.user.SendInput.assert_not_called()

    def test_failed_focus_or_f8_never_proceeds(self):
        for exception in (RuntimeError("focus denied"),KeyboardInterrupt("F8")):
            api=self.api(self.game())
            api.activate.side_effect=exception
            with self.assertRaises(type(exception)):
                focus_window("Steam",api)

    def test_focus_does_not_accept_replaced_process(self):
        game=self.game()
        api=self.api(game)
        api.inspect.return_value=GameWindow(game.hwnd,999,"Steam",game.rect)
        with self.assertRaises(RuntimeError):
            focus_window("Steam",api)

    def test_guard_rejects_focus_minimize_hide_close_pid_tab_and_resize_changes(self):
        for attribute,invalid in (("foreground",999),("pid",999),("title","Other tab"),
                                   ("rect",(0,0,1280,720)),("screen",(1280,720))):
            api=self.api(self.game())
            guard=WindowGuard(self.game(),api)
            getattr(api,attribute).return_value=invalid
            with self.assertRaises(RuntimeError):
                guard.check()
        for attribute,invalid in (("IsWindow",False),("IsWindowVisible",False),("IsIconic",True)):
            api=self.api(self.game())
            guard=WindowGuard(self.game(),api)
            getattr(api.user,attribute).return_value=invalid
            with self.assertRaises(RuntimeError):
                guard.check()

    def test_guard_accepts_unchanged_steam_and_chrome(self):
        for client in ("Steam","Chrome"):
            game=self.game(client)
            WindowGuard(game,self.api(game)).check()

    def test_both_children_receive_same_binding_without_global_environment_change(self):
        game=self.game()
        env={"FISHING_RUN_ID":"fake-run"}
        catch,control=Mock(),Mock()
        channel=Mock()
        channel.ready.return_value={"ready":True}
        with patch.object(processes,"Mutex"),patch.object(processes,"WindowGuard"), \
             patch.object(processes,"run_environment",return_value=env), \
             patch.object(processes,"Channel",return_value=channel), \
             patch.object(processes.subprocess,"Popen",side_effect=[catch,control]) as popen, \
             patch.dict(os.environ,{ENV_WINDOW:"parent-value"}):
            result=processes.start_children(game)
            self.assertEqual(result[:2],(catch,control))
            self.assertEqual(os.environ[ENV_WINDOW],"parent-value")
        for call in popen.call_args_list:
            self.assertEqual(GameWindow.deserialize(call.kwargs["env"][ENV_WINDOW]),game)
            self.assertEqual(call.kwargs["startupinfo"].wShowWindow,7)

    def test_no_window_or_f8_closes_launcher_mutex_without_spawning_children(self):
        for exception in (RuntimeError("no game"),KeyboardInterrupt("F8")):
            mutex=Mock()
            with patch.object(processes,"Mutex",return_value=mutex), \
                 patch.object(processes,"focus_window",side_effect=exception), \
                 patch.dict(os.environ,{},clear=True), \
                 patch.object(processes.subprocess,"Popen") as popen:
                with self.assertRaises(type(exception)):
                    processes.start_children()
            popen.assert_not_called()
            mutex.close.assert_called_once()

    def io(self):
        io=runtime.WindowsIO.__new__(runtime.WindowsIO)
        io.emergency=Mock()
        io.user32=Mock()
        io.user32.SetCursorPos.return_value=1
        io.expected_hwnd=123
        io.game_guard=Mock()
        def cursor(pointer):
            pointer._obj.x,pointer._obj.y=960,970
            return 1
        io.user32.GetCursorPos.side_effect=cursor
        return io

    def test_runtime_window_guard_blocks_control_catch_and_cast_input(self):
        for method in ("click","cast_click"):
            io=self.io()
            io.game_guard.check.side_effect=RuntimeError("focus lost")
            with self.assertRaises(runtime.SafetyStop):
                getattr(io,method)((960,970))
            io.user32.SetCursorPos.assert_not_called()
            io.user32.mouse_event.assert_not_called()
            io.user32.SendInput.assert_not_called()

    def test_focus_change_after_cursor_move_blocks_mouse_down_or_cast_packet(self):
        for method in ("click","cast_click"):
            io=self.io()
            io.game_guard.check.side_effect=[None,RuntimeError("focus lost")]
            with self.assertRaises(runtime.SafetyStop):
                getattr(io,method)((960,970))
            io.user32.mouse_event.assert_not_called()
            io.user32.SendInput.assert_not_called()

    def test_shared_loop_checks_window_before_any_capture(self):
        io=self.io()
        io.game_guard.check.side_effect=RuntimeError("minimized")
        stop_path=Mock()
        stop_path.exists.return_value=False
        with self.assertRaises(runtime.SafetyStop):
            runtime.check_stop(io,SimpleNamespace(stop_path=stop_path),Mock())

    def test_runtime_refuses_missing_or_malformed_window_binding(self):
        for env in ({},{ENV_WINDOW:"not json"},{ENV_WINDOW:"null"}):
            with patch.dict(os.environ,env,clear=True),self.assertRaises(runtime.SafetyStop):
                runtime.WindowsIO()
