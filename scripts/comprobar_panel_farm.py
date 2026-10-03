"""Prueba opt-in del panel real, sin motores ni entradas al juego."""

import argparse
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import customtkinter as ctk
from FISHING_BOT_APP import FishingBotApp


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshot',type=Path,help='Captura opcional del escritorio mediante grim')
    args=parser.parse_args();errors=[]
    ctk.set_appearance_mode('dark');app=FishingBotApp(farm_primary=True)

    def finish():
        try:
            assert app.mode_tabs.get()=='Dungeons' and app.dungeon_panel.start.winfo_ismapped()
            assert not app.bot_activo and app.p_control is None and app.p_catch is None
            if args.screenshot:subprocess.run(['grim',str(args.screenshot)],check=True)
            print('Panel OK: fondo, marcos, START verde / DETENER rojo y foco; Dungeons/Fishing conservados; cero motores')
        except Exception as exc:errors.append(exc)
        finally:app._on_close()

    def fishing():
        try:
            assert app.btn_iniciar.winfo_ismapped()
            assert app.log_textbox.winfo_ismapped() and app.log_textbox.winfo_height()>=32
            app.mode_tabs.set('Dungeons');app.after(300,finish)
        except Exception as exc:errors.append(exc);app._on_close()

    def check():
        try:
            assert app.cget('fg_color')=='#172b38'
            assert app.background.find_withtag('stone')
            size=SimpleNamespace(width=128,height=64)
            app._draw_background(size)
            assert len(app.background.find_withtag('stone'))==5
            app._draw_background(size)
            assert len(app.background.find_withtag('stone'))==5
            app._draw_background(SimpleNamespace(width=app.winfo_width(),height=app.winfo_height()))
            for start,stop in ((app.dungeon_panel.start,app.dungeon_panel.stop),
                               (app.btn_iniciar,app.btn_detener)):
                assert start.cget('background')=='#426b0e'
                assert stop.cget('background')=='#a52828'
                assert start.cget('relief')=='raised' and stop.cget('relief')=='raised'
                assert str(start.cget('takefocus'))=='1' and str(stop.cget('takefocus'))=='1'
            assert app.window_frame.cget('relief')=='ridge'
            app.dungeon_panel.start.focus_force()
            assert app.focus_get()==app.dungeon_panel.start
            assert app.mode_tabs.get()=='Dungeons'
            panel=app.dungeon_panel;panel.familiar.set('Bob');panel.search()
            assert panel.plan()['dungeon_id']=='Z1D2'
            assert 'pendiente de calibrar' in panel.details.cget('text')
            panel.familiar.set('Tealk');panel.search();panel.difficulty.set('Heroic')
            panel.route_changed(panel.route.get())
            assert panel.plan()['dungeon_id']=='Z5D3'
            assert 'Disponible' in panel.details.cget('text') and '1 run' in panel.details.cget('text')
            panel.difficulty.set('Normal');panel.route_changed(panel.route.get())
            assert 'pendiente de calibrar' in panel.details.cget('text')
            panel.familiar.set('');panel.search();assert len(panel.route.cget('values'))==77
            panel.route.set(next(label for label,identifier in panel.labels.items() if identifier=='Z5D2'))
            panel.route_changed(panel.route.get())
            panel.active(True)
            assert panel.start.cget('state')=='disabled' and panel.stop.cget('state')=='normal'
            panel.active(False)
            assert panel.start.cget('state')=='normal' and panel.stop.cget('state')=='disabled'
            app.mode_tabs.set('Fishing');app.after(300,fishing)
        except Exception as exc:errors.append(exc);app._on_close()

    app.after(1000,check);app.mainloop()
    if errors:raise errors[0]


if __name__=='__main__':main()
