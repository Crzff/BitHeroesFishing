"""Pruebas Linux sin captura del escritorio ni input real."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fishing_core.game_window import GameWindow, focus_window, WindowGuard
from fishing_core.control_flow import SafetyStop
from fishing_core.linux import LinuxAPI, LinuxIO, LinuxCapture, validate_niri_window
from fishing_core import processes
import FISHING_BOT_APP as gui


class LinuxTests(unittest.TestCase):
    def game(self):
        return GameWindow(123,456,"Steam",(0,0,1920,1080),compositor_id=75)

    def window(self):
        return {"id":75,"title":"Bit Heroes","app_id":"steam_app_666860",
                "pid":999,  # niri ve satellite; el PID del juego se comprueba en X11.
                "is_focused":True,"layout":{"window_size":[1920,1080],
                "tile_size":[1920,1080],"window_offset_in_tile":[0,0],
                "tile_pos_in_workspace_view":None}}

    def test_compositor_binding_round_trip_and_invalid_id(self):
        game=self.game()
        self.assertEqual(GameWindow.deserialize(game.serialize()),game)
        for invalid in (True,0,-1,"75"):
            value=json.loads(game.serialize())
            value["compositor_id"]=invalid
            with self.assertRaises(RuntimeError):
                GameWindow.deserialize(json.dumps(value))

    def test_niri_requires_same_game_focus_identity_and_geometry(self):
        validate_niri_window(self.window(),self.game())
        for key,invalid in (("id",76),("title","Other"),("app_id","kitty"),("is_focused",False)):
            window={**self.window(),key:invalid}
            with self.assertRaises(RuntimeError):
                validate_niri_window(window,self.game())
        for key,invalid in (("window_size",[1280,720]),("tile_size",[1930,1080]),
                            ("window_offset_in_tile",[1,0]),("tile_pos_in_workspace_view",[10,0])):
            window=self.window()
            window["layout"][key]=invalid
            with self.assertRaises(RuntimeError):
                validate_niri_window(window,self.game())
        with self.assertRaises(RuntimeError):
            validate_niri_window(None,self.game())

    def io(self):
        io=LinuxIO.__new__(LinuxIO)
        io.game_guard=Mock()
        io.game_guard.api.emergency=Mock()
        io.pointer=Mock()
        io.game_guard.api.cursor.return_value=(960,970)
        return io

    def test_control_catch_and_cast_refuse_input_after_focus_loss(self):
        for method in ("click","cast_click"):
            io=self.io()
            io.game_guard.check.side_effect=RuntimeError("focus lost")
            with self.assertRaises(SafetyStop):
                getattr(io,method)((960,970))
            io.pointer.move.assert_not_called()
            io.pointer.button.assert_not_called()

    def test_focus_change_after_motion_blocks_down(self):
        io=self.io()
        io.game_guard.check.side_effect=[None,RuntimeError("focus lost")]
        with self.assertRaises(SafetyStop):
            io.click((960,970))
        io.pointer.button.assert_not_called()

    def test_unconfirmed_pointer_position_never_clicks(self):
        io=self.io()
        io.game_guard.api.cursor.return_value=(0,0)
        with self.assertRaisesRegex(SafetyStop,r"esperada \(960, 970\), actual \(0, 0\)"):
            io.click((960,970))
        io.pointer.button.assert_not_called()

    def test_down_is_released_even_if_control_hold_is_interrupted(self):
        io=self.io()
        io.control_mode=True
        with patch("fishing_core.linux.time.sleep",side_effect=[None,KeyboardInterrupt("F8")]):
            with self.assertRaises(KeyboardInterrupt):
                io.click((960,970))
        self.assertEqual([c.args for c in io.pointer.button.call_args_list],[(True,),(False,)])

    def test_f8_blocks_motion_and_click(self):
        io=self.io()
        io.game_guard.api.emergency.side_effect=KeyboardInterrupt("F8")
        with self.assertRaises(KeyboardInterrupt):
            io.cast_click((960,970))
        io.pointer.move.assert_not_called()
        io.pointer.button.assert_not_called()

    def test_escape_requires_focus_and_f8_guard_and_always_releases_the_key(self):
        from Xlib import X
        for failure in ('focus','F8','unmapped','hold','none'):
            io=self.io();io.game_guard.api.display.keysym_to_keycode.return_value=9 if failure!='unmapped' else 0
            if failure=='focus':io.game_guard.check.side_effect=RuntimeError('focus lost')
            if failure=='F8':io.game_guard.api.emergency.side_effect=KeyboardInterrupt('F8')
            with patch('Xlib.ext.xtest.fake_input') as send, \
                    patch('fishing_core.linux.time.sleep',side_effect=KeyboardInterrupt('F8') if failure=='hold' else None):
                if failure=='none':io.escape()
                else:
                    with self.assertRaises((SafetyStop,KeyboardInterrupt)):io.escape()
            expected=[(X.KeyPress,9),(X.KeyRelease,9)] if failure in ('none','hold') else []
            self.assertEqual([c.args[1:] for c in send.call_args_list],expected,failure)
            io.pointer.move.assert_not_called();io.pointer.button.assert_not_called()

    def test_click_coordinates_are_validated(self):
        for xy in ((-1,0),(1920,0),(0,1080),(True,10),(10.5,20)):
            io=self.io()
            with self.assertRaises(SafetyStop):
                io.click(xy)
            io.pointer.move.assert_not_called()

    def test_linux_children_have_no_windows_console_flags(self):
        with patch.object(processes.os,"name","posix"):
            self.assertEqual(processes.child_options(),{"start_new_session":True})

    def test_windows_console_safety_options_are_preserved(self):
        startup=SimpleNamespace(dwFlags=0,wShowWindow=0)
        with patch.object(processes.os,"name","nt"), \
             patch.object(processes.subprocess,"STARTUPINFO",return_value=startup,create=True), \
             patch.object(processes.subprocess,"CREATE_NEW_CONSOLE",16,create=True), \
             patch.object(processes.subprocess,"STARTF_USESHOWWINDOW",1,create=True):
            options=processes.child_options()
        self.assertEqual(options["creationflags"],16|0x200)
        self.assertEqual(options["startupinfo"].wShowWindow,7)
        self.assertEqual(options["startupinfo"].dwFlags,1)
        self.assertNotIn("start_new_session",options)

    def test_linux_panel_hides_and_restores_only_after_stop(self):
        app=SimpleNamespace(_linux_panel=True,_fishing_view=False,withdraw=Mock(),
            deiconify=Mock(),update_idletasks=Mock(),state=Mock(return_value="withdrawn"),_log=Mock())
        gui.FishingBotApp._preparar_vista_pesca(app)
        self.assertTrue(app._fishing_view)
        app.withdraw.assert_called_once()
        app.bot_activo=True
        gui.FishingBotApp._comprobar_vista_pesca(app)
        gui.FishingBotApp._restaurar_vista_panel(app)
        self.assertFalse(app._fishing_view)
        app.deiconify.assert_called_once()

    def test_linux_refuses_a_panel_that_did_not_hide(self):
        app=SimpleNamespace(_linux_panel=True,_fishing_view=False,withdraw=Mock(),
            update_idletasks=Mock(),state=Mock(return_value="normal"),_log=Mock())
        with self.assertRaises(RuntimeError):
            gui.FishingBotApp._preparar_vista_pesca(app)

    def test_pointer_over_another_window_is_not_a_game_click(self):
        api=LinuxAPI.__new__(LinuxAPI)
        api.game=self.game()
        api.display=Mock()
        api.display.screen().root.query_pointer.return_value=SimpleNamespace(
            child=SimpleNamespace(id=999),root_x=960,root_y=970)
        with self.assertRaises(RuntimeError):
            api.cursor()

    def activation(self,results):
        api=LinuxAPI.__new__(LinuxAPI);clock=[0.0];game=self.game()
        api.emergency=Mock();api.inspect=Mock(return_value=game);api.niri=Mock()
        outcomes=iter(results)
        def check(_):
            if not next(outcomes,True):raise RuntimeError("focus")
        api.check_window=Mock(side_effect=check)
        def sleep(seconds):clock[0]+=seconds
        fake=SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep)
        return api,clock,fake

    def test_activate_waits_for_continuous_confirmed_focus_not_time_since_request(self):
        # Foco tarda 0,6 s y parpadea una vez: la espera cuenta desde la ultima confirmacion.
        api,clock,fake=self.activation([False]*30+[True]*10+[False]+[True]*100)
        with patch("fishing_core.linux.time",fake):api.activate(123)
        self.assertGreaterEqual(clock[0],(30+10+1)*.02+1.0-1e-9)

    def test_activate_stops_when_focus_never_settles(self):
        api,clock,fake=self.activation([True,False]*200)
        with patch("fishing_core.linux.time",fake):
            with self.assertRaises(RuntimeError):api.activate(123)
        self.assertLess(clock[0],3.1)

    def test_overview_blocks_game_input_despite_keyboard_focus(self):
        api=LinuxAPI.__new__(LinuxAPI)
        api.inspect=Mock(return_value=self.game())
        api.screen=Mock(return_value=(1920,1080))
        api.niri=Mock()
        api.niri.request.return_value={"is_open":True}
        api.display=Mock()
        with self.assertRaises(RuntimeError):
            api.check_window(self.game())
        api.display.get_input_focus.assert_not_called()

    def test_focus_closes_only_a_linux_api_it_created_even_on_failure(self):
        for fail in (False,True):
            api=Mock(platform="linux")
            api.windows.return_value=[self.game()]
            api.inspect.return_value=self.game()
            api.screen.return_value=(1920,1080)
            if fail:
                api.activate.side_effect=RuntimeError("focus denied")
            with patch("fishing_core.game_window.window_api",return_value=api):
                if fail:
                    with self.assertRaises(RuntimeError):focus_window("Steam")
                else:
                    self.assertEqual(focus_window("Steam"),self.game())
            api.close.assert_called_once()
        supplied=Mock(platform="linux")
        supplied.windows.return_value=[self.game()]
        supplied.inspect.return_value=self.game()
        supplied.screen.return_value=(1920,1080)
        focus_window("Steam",supplied)
        supplied.close.assert_not_called()

    def test_failed_guard_closes_its_linux_connection(self):
        api=Mock(platform="linux")
        api.screen.side_effect=RuntimeError("invalid screen")
        with patch("fishing_core.game_window.window_api",return_value=api):
            with self.assertRaises(RuntimeError):WindowGuard(self.game())
        api.close.assert_called_once()

    def test_failed_pointer_init_closes_linux_guard(self):
        guard=Mock()
        with patch("fishing_core.linux.WindowGuard",return_value=guard), \
             patch("fishing_core.linux.WaylandPointer",side_effect=RuntimeError("no pointer")), \
             patch.dict(os.environ,{"FISHING_GAME_WINDOW":self.game().serialize()}):
            with self.assertRaises(SafetyStop):LinuxIO()
        guard.api.close.assert_called_once()

    def test_io_closes_x11_even_if_pointer_cleanup_fails(self):
        io=self.io()
        io.pointer.close.side_effect=RuntimeError("broken connection")
        with self.assertRaises(RuntimeError):io.close()
        io.game_guard.api.close.assert_called_once()

    def test_linux_control_allows_two_30fps_frames_but_cast_and_catch_stay_fast(self):
        io=self.io()
        io.control_mode=True
        with patch("fishing_core.linux.time.sleep") as sleep:
            io.click((960,970))
        self.assertEqual(len(sleep.call_args_list),2)
        self.assertGreaterEqual(sleep.call_args_list[0].args[0],2/30)
        self.assertGreaterEqual(sleep.call_args_list[1].args[0],1/30)
        with patch("fishing_core.linux.time.sleep") as sleep:
            io.cast_click((960,970))
            io.control_mode=False
            io.click((960,970))
        sleep.assert_not_called()

    def capture_guard(self):
        guard=Mock()
        guard.api.X=SimpleNamespace(ZPixmap=2,LSBFirst=0)
        guard.api.display.display.info=SimpleNamespace(image_byte_order=0,
            pixmap_formats=[SimpleNamespace(depth=24,bits_per_pixel=32)])
        # La imagen X11 anterior no coincide con el frame nuevo del compositor.
        guard.api._window.return_value.get_image.return_value=SimpleNamespace(depth=24,data=b"\0"*4)
        return guard

    def test_capture_uses_fresh_wayland_pixels_not_the_old_x11_surface(self):
        guard=self.capture_guard()
        native=Mock();native.grab.return_value=bytes((30,20,10,255))
        result=SimpleNamespace(stdout=b"P6\n1 1\n255\n"+bytes((10,20,30)))
        with patch("fishing_core.linux.WaylandCapture",return_value=native,create=True), \
             patch("subprocess.run",return_value=result) as run:
            shot=LinuxCapture(guard).grab({"left":0,"top":0,"width":1,"height":1})
        self.assertEqual(shot.bgra,bytes((30,20,10,255)))
        guard.api._window.assert_not_called()
        self.assertEqual(guard.check.call_count,2)
        run.assert_not_called()  # No proceso/PPM por frame en la ruta rapida.
        native.grab.assert_called_once_with(0,0,1,1)

    def test_capture_never_falls_back_to_x11_on_native_failure(self):
        for failure in (FileNotFoundError("adapter"),TimeoutError("Wayland"),
                        RuntimeError("capture failed")):
            guard=self.capture_guard()
            with patch("fishing_core.linux.WaylandCapture",side_effect=failure,create=True), \
                 patch("subprocess.run",return_value=SimpleNamespace(stdout=b"P6\n1 1\n255\n"+b"\0"*3)):
                with self.assertRaises(SafetyStop):
                    LinuxCapture(guard).grab({"left":0,"top":0,"width":1,"height":1})
            guard.api._window.assert_not_called()

    def test_native_capture_rejects_focus_loss_wrong_size_and_invalid_pixels(self):
        cases=(b"\0"*8,b"",b"\0"*4)
        for index,pixels in enumerate(cases):
            guard=self.capture_guard()
            if index==2:guard.check.side_effect=[None,RuntimeError("focus lost")]
            native=Mock();native.grab.return_value=pixels
            with patch("fishing_core.linux.WaylandCapture",return_value=native,create=True), \
                 patch("subprocess.run",return_value=SimpleNamespace(stdout=b"invalid")):
                with self.assertRaises(SafetyStop):
                    LinuxCapture(guard).grab({"left":0,"top":0,"width":1,"height":1})

    def test_capture_reuses_connection_and_closes_even_on_failure(self):
        guard=self.capture_guard();native=Mock();native.grab.side_effect=[b"\0"*4,RuntimeError("copy failed")]
        with patch("fishing_core.linux.WaylandCapture",return_value=native,create=True) as constructor, \
             patch("subprocess.run",return_value=SimpleNamespace(stdout=b"P6\n1 1\n255\n"+b"\0"*3)):
            with self.assertRaises(SafetyStop):
                with LinuxCapture(guard) as capture:
                    capture.grab({"left":0,"top":0,"width":1,"height":1})
                    capture.grab({"left":0,"top":0,"width":1,"height":1})
        constructor.assert_called_once()
        native.close.assert_called_once()

    def test_invalid_capture_region_never_starts_grim(self):
        for region in ({"left":-1,"top":0,"width":1,"height":1},
                       {"left":0,"top":0,"width":1921,"height":1},
                       {"left":True,"top":0,"width":1,"height":1}):
            with patch("subprocess.run") as run:
                with self.assertRaises(SafetyStop):LinuxCapture(self.capture_guard()).grab(region)
            run.assert_not_called()

    def test_linux_catch_copies_only_the_envelope_of_all_required_regions(self):
        from fishing_core import runtime
        from fishing_core.detector import ZONE_STRIP,FISH_ROI
        from fishing_core.vision import BUTTON_ROI,PCT_ROI
        regions=(ZONE_STRIP,FISH_ROI,BUTTON_ROI,PCT_ROI)
        left=min(r[0] for r in regions);top=min(r[1] for r in regions)
        expected={"left":left,"top":top,"width":max(r[2] for r in regions)-left,
                  "height":max(r[3] for r in regions)-top}
        self.assertEqual(getattr(runtime,"LINUX_FAST_MONITOR",None),expected)
        self.assertEqual(runtime.FAST_MONITOR,{"left":430,"top":710,"width":1310,"height":320})


if __name__=="__main__":
    unittest.main()
