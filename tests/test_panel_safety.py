import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

import FISHING_BOT_APP as gui
from fishing_core.panel_safety import ACTIVE_GEOMETRY,ACTIVE_SIZE,panel_bounds_safe,stop_button_visible


class PanelSafetyTests(unittest.TestCase):
    def app(self,pinned=True):
        return SimpleNamespace(
            _fishing_view=False,_normal_view=None,siempre_visible=pinned,
            _min_width=520,_min_height=850,_max_width=1920,_max_height=1080,
            geometry=Mock(return_value="550x900+20+20"),minsize=Mock(return_value=(520,850)),
            maxsize=Mock(return_value=(1920,1080)),resizable=Mock(return_value=(True,True)),
            overrideredirect=Mock(return_value=False),attributes=Mock(),update_idletasks=Mock(),
            logs_frame=Mock(),game_frame=Mock(),game_selector=Mock(get=Mock(return_value="Steam")),
            btn_iniciar=Mock(),btn_reiniciar=Mock(),
            btn_detener=Mock(winfo_ismapped=Mock(return_value=True),winfo_rootx=Mock(return_value=36),
                             winfo_rooty=Mock(return_value=500),winfo_width=Mock(return_value=470),
                             winfo_height=Mock(return_value=38)),
            btn_siempre_visible=Mock(),_log=Mock())

    def test_safe_rect_excludes_inventory_and_all_fishing_bar_regions(self):
        self.assertTrue(panel_bounds_safe((10,10,530,660)))
        for rect in ((20,20,578,950),(10,10,551,660),(10,10,530,710),
                     (-1,10,530,660),(10,10,10,660)):
            self.assertFalse(panel_bounds_safe(rect),rect)

    def test_pinned_panel_is_compacted_without_changing_saved_preference(self):
        app=self.app()
        with patch.object(gui,"window_bounds",return_value=(10,10,530,660)):
            gui.FishingBotApp._preparar_vista_pesca(app)
        self.assertTrue(app._fishing_view)
        self.assertTrue(app.siempre_visible)
        app.attributes.assert_called_with("-topmost",True)
        app.geometry.assert_called_with(ACTIVE_GEOMETRY)
        app.minsize.assert_called_with(*ACTIVE_SIZE)
        self.assertEqual(app.minsize.call_count,1)
        self.assertEqual(app.maxsize.call_count,1)
        app.maxsize.assert_called_with(*ACTIVE_SIZE)
        app.overrideredirect.assert_called_with(True)
        app.resizable.assert_called_with(False,False)
        app.logs_frame.pack_forget.assert_called_once()
        app.btn_iniciar.pack_forget.assert_called_once()
        app.btn_detener.pack_forget.assert_not_called()

    def test_non_pinned_preference_is_not_enabled_implicitly(self):
        app=self.app(False)
        with patch.object(gui,"window_bounds",return_value=(10,10,530,660)):
            gui.FishingBotApp._preparar_vista_pesca(app)
        app.attributes.assert_called_with("-topmost",False)
        self.assertFalse(app.siempre_visible)

    def test_wrong_dpi_or_occluding_bounds_abort_before_any_engine_start(self):
        app=self.app()
        with patch.object(gui,"window_bounds",return_value=(10,10,660,820)):
            with self.assertRaises(RuntimeError):
                gui.FishingBotApp._preparar_vista_pesca(app)
        self.assertTrue(app._fishing_view)  # El manejador de inicio restaura la vista al fallar.

    def test_stop_restores_geometry_controls_and_visibility_preference(self):
        app=self.app()
        with patch.object(gui,"window_bounds",return_value=(10,10,530,660)):
            gui.FishingBotApp._preparar_vista_pesca(app)
        gui.FishingBotApp._restaurar_vista_panel(app)
        app.geometry.assert_called_with("550x900+20+20")
        app.minsize.assert_called_with(520,850)
        app.overrideredirect.assert_called_with(False)
        app.btn_iniciar.pack.assert_called_once()
        app.btn_reiniciar.pack.assert_called_once()
        app.logs_frame.pack.assert_called_once()
        self.assertFalse(app._fishing_view)
        self.assertIsNone(app._normal_view)

    def test_start_prepares_safe_view_and_game_focus_before_children(self):
        steps=[]
        app=self.app()
        app.bot_activo=False
        app._verificar_scripts=Mock(return_value=True)
        app._preparar_vista_pesca=Mock(side_effect=lambda:steps.append("safe"))
        app._after_idle=Mock()
        catch,control=Mock(pid=1),Mock(pid=2)
        channel=Mock(run_id="test")
        game=SimpleNamespace(client="Steam")
        def focus(client):
            self.assertEqual(client,"Steam")
            steps.append("focus")
            return game
        def start(bound):
            self.assertIs(bound,game)
            steps.append("children")
            return catch,control,channel,Mock()
        with patch.object(gui,"focus_window",side_effect=focus), \
             patch.object(gui,"start_children",side_effect=start), \
             patch.object(gui,"PanelState"),patch.object(gui,"SessionFeed"):
            gui.FishingBotApp.iniciar_bot(app)
        self.assertEqual(steps,["safe","focus","children"])
        self.assertTrue(app.bot_activo)

    def test_focus_failure_does_not_start_children_and_restores_idle_state(self):
        app=self.app()
        app.bot_activo=False
        app._verificar_scripts=Mock(return_value=True)
        app._preparar_vista_pesca=Mock()
        app._after_idle=Mock()
        with patch.object(gui,"focus_window",side_effect=RuntimeError("no game")), \
             patch.object(gui,"start_children") as children:
            gui.FishingBotApp.iniciar_bot(app)
        children.assert_not_called()
        app._after_idle.assert_called_once()

    def test_stop_control_clipped_hidden_or_outside_panel_is_rejected(self):
        app=self.app()
        self.assertTrue(stop_button_visible(app,(10,10,530,660)))
        app.btn_detener.winfo_rooty.return_value=640
        self.assertFalse(stop_button_visible(app,(10,10,530,660)))
        app.btn_detener.winfo_rooty.return_value=500
        app.btn_detener.winfo_ismapped.return_value=False
        self.assertFalse(stop_button_visible(app,(10,10,530,660)))

    def test_active_normal_panel_stops_if_moved_or_stop_control_clipped(self):
        for bounds,visible in (((20,20,580,900),True),((10,10,530,660),False)):
            app=self.app()
            app.bot_activo=True
            app._fishing_view=True
            app.panel_state=None
            app._after_idle=Mock()
            with patch.object(gui,"window_bounds",return_value=bounds), \
                 patch.object(gui,"stop_button_visible",return_value=visible):
                gui.FishingBotApp._comprobar_vista_pesca(app)
            app._after_idle.assert_called_once()

    def test_safe_active_panel_and_idle_panel_do_not_stop_or_query_unnecessarily(self):
        app=self.app()
        app.bot_activo=True
        app._fishing_view=True
        app._after_idle=Mock()
        with patch.object(gui,"window_bounds",return_value=(10,10,530,660)):
            gui.FishingBotApp._comprobar_vista_pesca(app)
        app._after_idle.assert_not_called()
        app.bot_activo=False
        with patch.object(gui,"window_bounds") as query:
            gui.FishingBotApp._comprobar_vista_pesca(app)
        query.assert_not_called()
