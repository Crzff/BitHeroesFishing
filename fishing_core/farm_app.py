"""App del Farm Bot con el aspecto de las ventanas de Bit Heroes. Abrirla no envía input al juego.

Se dibuja con PIL (pixel_ui) en un único Canvas; cada elemento registra una zona clicable.
START lanza fishing_core.farm_all en un proceso aparte con farm_config.json; STOP le
envía SIGINT (los modos lo tratan como F8). Mientras juega, el juego debe tener el foco:
cambiar a esta ventana ya detiene el bot por seguridad.
"""

import os
import signal
import subprocess
import sys
import threading
import tkinter as tk

from PIL import Image, ImageTk

from . import farm_config, pixel_ui as ui
from .dungeon_catalog import CATALOG, FAMILIARS, dungeon
from .dungeon_runtime import ROUTE_COSTS
from .telemetry import ROOT

W,H=1100,860
NAMES={'quest':'QUEST','pvp':'PVP','boss':'BOSS','raid':'RAID','expedition':'EXPEDITION','trials':'TRIALS'}
SUMMARY={'pvp':'5 TICKETS','raid':'STORM T13','expedition':'SEMANAL','trials':'SEMANAL'}
INFO={'pvp':['ARENA · 5 TICKETS, BAJA HASTA 1','RIVAL: EL QUE MAS PUNTOS DA','UNA DERROTA NO DETIENE'],
      'raid':['STORM (TIER 13) EN HEROIC','1 SHARD POR RUN, HASTA AGOTARLOS','UNA DERROTA NO DETIENE'],
      'expedition':['EVENTO SEMANAL: IDOL DIMENSION','5 BADGES, BAJA HASTA 1','NUNCA COMPRA BADGES'],
      'trials':['EVENTO SEMANAL: NYXN TRIALS','DIFICULTAD 499 · 5 TOKENS, BAJA HASTA 1','NUNCA COMPRA TOKENS']}
CALIBRATED={d for d,_ in ROUTE_COSTS}
ZONES=sorted({row['zone'] for row in CATALOG})


def familiars_of(identifier):
    return [name for name,routes in FAMILIARS.items() if identifier in routes]


class FarmApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Bit Heroes Farm Bot');self.resizable(False,False);self.configure(bg='#19283a')
        self.canvas=tk.Canvas(self,width=W,height=H,highlightthickness=0,bg='#19283a');self.canvas.pack()
        self.canvas.bind('<Button-1>',self.on_click)
        self.config_data=farm_config.load();self.screen='main';self.process=None
        self.status='LISTO · ELIGE MODOS Y PULSA START';self.zone=dungeon(self.config_data['quest']['dungeon'])['zone']
        self.protocol('WM_DELETE_WINDOW',self.quit_app);self.render()

    # --- dibujo -----------------------------------------------------------------
    def put(self,img,x,y,action=None):
        self.img.alpha_composite(img,(int(x),int(y)))
        if action:self.zones.append((x,y,x+img.width,y+img.height,action))

    def label(self,txt,x,y,size=22,color=ui.TEXT,center=False):
        t=ui.text(txt,size,color=color);self.put(t,x-(t.width//2 if center else 0),y);return t

    def render(self):
        self.img=Image.new('RGBA',(W,H),(25,40,58,255));self.zones=[]
        getattr(self,f'draw_{self.screen if self.screen in ("main","quest","boss") else "info"}')()
        self.photo=ImageTk.PhotoImage(self.img);self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo)

    def window(self,title,back=True):
        self.put(ui.frame(W-40,H-40,title),20,20)
        if back:self.put(ui.close_button(),W-112,62,self.go_main)

    def draw_main(self):
        self.window('FARM BOT',back=False);self.put(ui.close_button(),W-112,62,self.quit_app)
        running=self.process is not None
        for i,mode in enumerate(farm_config.MODES):
            x=82+(i%3)*318;y=146+(i//3)*250;on=self.config_data['modes'][mode]
            self.put(ui.row(298,230),x,y)
            icon=ui.icon(mode,118);self.put(icon if on else ui.dimmed(icon),x+(298-icon.width)//2,y+14,lambda m=mode:self.open_mode(m))
            for j,line in enumerate(self.summary(mode)):self.label(line[:17],x+16,y+164+j*30,16,ui.GOLD if on else ui.DIM)
            self.put(ui.checkbox(on),x+232,y+164,None if running else lambda m=mode:self.toggle_mode(m))
        self.put(ui.checkbox(self.config_data['runes'],44),82,664,None if running else self.toggle_runes)
        self.label('CAMBIAR RUNAS (CAPTURA / ITEM FIND)',138,670,18)
        self.label(self.status[:58],82,730,16,ui.DIM)
        self.put(ui.auto_button(running,150,124),W-232,652,self.toggle_run)

    def summary(self,mode):
        if mode=='quest':
            q=self.config_data['quest']
            return [f"{q['dungeon']} {q['difficulty'].upper()}",' '.join(n.upper() for n in q['targets']) or 'SIN OBJETIVO']
        if mode=='boss':return ['NETHERWORLD',f"T9 {self.config_data['boss']['difficulty'].upper()}"]
        return [SUMMARY[mode]]

    def draw_quest(self):
        self.window('QUEST');q=self.config_data['quest']
        zone_rows=[row for row in CATALOG if row['zone']==self.zone]
        self.put(ui.button('<',64,56,'blue',30),70,140,lambda:self.step_zone(-1))
        self.label(f"ZONA {self.zone} · {zone_rows[0]['zone_name'].upper()}",W//2,152,24,center=True)
        self.put(ui.button('>',64,56,'blue',30),W-134,140,lambda:self.step_zone(1))
        for i,row in enumerate(zone_rows):
            y=214+i*66;ok=row['id'] in CALIBRATED;chosen=q['dungeon']==row['id']
            self.put(ui.row(560,58),70,y)
            self.label(f"{row['id']} {row['name'].upper()}"[:26],86,y+16,17,ui.TEXT if ok else ui.DIM)
            if ok:self.put(ui.checkbox(chosen,44),572,y+7,lambda d=row['id']:self.choose_dungeon(d))
            else:self.label('SIN CALIBRAR',470,y+20,12,ui.DIM)
        self.label('DIFICULTAD',660,214,20,ui.GOLD)
        for i,(level,color) in enumerate((('HEROIC','orange'),('HARD','green'),('NORMAL','blue'))):
            selected=q['difficulty'].upper()==level
            self.put(ui.button(level,330,60,color if selected else 'gray',22),660,250+i*72,lambda l=level:self.set_difficulty(l))
        self.label('EMPIEZA EN LA ELEGIDA Y BAJA SI FALTA ENERGIA',660,476,11,ui.DIM)
        self.label(f"FAMILIARES DE {q['dungeon']} (MARCA LOS OBJETIVOS)",70,494,18,ui.GOLD)
        for i,name in enumerate(familiars_of(q['dungeon'])[:12]):
            x=70+(i%3)*325;y=530+(i//3)*58;on=name in q['targets']
            self.put(ui.row(305,50),x,y);self.label(name.upper()[:14],x+14,y+14,17)
            self.put(ui.checkbox(on,40),x+256,y+5,lambda n=name:self.toggle_target(n))
        self.label('OBJETIVO: PAUSA PARA PERSUADIR · RESTO: SE RECHAZA',70,770,13,ui.DIM)

    def draw_boss(self):
        self.window('WORLD BOSS')
        icon=ui.icon('boss',150);self.put(icon,(W-icon.width)//2,150)
        for i,line in enumerate(('NETHERWORLD · TIER 9 · SALA PRIVADA','REGROUP ENTRE RUNS · UNA DERROTA NO DETIENE')):
            self.label(line,W//2,330+i*40,18,center=True)
        current=self.config_data['boss']['difficulty']
        for i,(level,color) in enumerate((('NORMAL','blue'),('HEROIC','orange'))):
            self.put(ui.button(level,300,70,color if current.upper()==level else 'gray',26),220+i*360,470,
                     lambda l=level:self.set_boss(l))
        self.label('EL TIER Y LA DIFICULTAD DEL JUEGO DEBEN COINCIDIR',W//2,580,14,ui.DIM,center=True)

    def draw_info(self):
        mode=self.screen;self.window(NAMES[mode])
        icon=ui.icon(mode,150);self.put(icon,(W-icon.width)//2,150)
        for i,line in enumerate(INFO[mode]):self.label(line,W//2,350+i*46,20,center=True)

    # --- acciones ---------------------------------------------------------------
    def on_click(self,event):
        for x0,y0,x1,y1,action in reversed(self.zones):
            if x0<=event.x<x1 and y0<=event.y<y1:action();self.render();return

    def save(self):
        farm_config.save(self.config_data)

    def go_main(self):self.screen='main'
    def open_mode(self,mode):
        if self.process is None:self.screen=mode
    def toggle_mode(self,mode):self.config_data['modes'][mode]^=True;self.save()
    def toggle_runes(self):self.config_data['runes']^=True;self.save()
    def step_zone(self,delta):self.zone=ZONES[(ZONES.index(self.zone)+delta)%len(ZONES)]

    def choose_dungeon(self,identifier):
        q=self.config_data['quest']
        if q['dungeon']!=identifier:q['dungeon']=identifier;q['targets']=[]
        self.save()

    def set_difficulty(self,level):self.config_data['quest']['difficulty']=level.title();self.save()
    def set_boss(self,level):self.config_data['boss']['difficulty']=level.title();self.save()

    def toggle_target(self,name):
        targets=self.config_data['quest']['targets']
        targets.remove(name) if name in targets else targets.append(name);self.save()

    def toggle_run(self):
        if self.process is not None:
            self.process.send_signal(signal.SIGINT);self.status='DETENIENDO...';return
        if not any(self.config_data['modes'].values()):self.status='NINGUN MODO ACTIVO';return
        self.save();self.status='EN MARCHA · F8 DETIENE · NO CAMBIES DE VENTANA'
        self.process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all'],cwd=str(ROOT),
                                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        threading.Thread(target=self.follow,args=(self.process,),daemon=True).start()

    def follow(self,process):
        results=[]
        for line in process.stdout:
            line=line.strip()
            if line.startswith('== '):self.after(0,self.set_status,f'EN MARCHA · {line[3:].upper()} · F8 DETIENE')
            elif ': ' in line and line.split(':')[0] in ('Runas captura','Quest','Runas Item Find','PvP','World Boss','Raid','Expedition','Trials'):
                results.append(line)
        process.wait()
        failed=[r for r in results if not r.endswith(': OK')]
        self.after(0,self.finish,'TERMINADO · TODO GASTADO' if not failed else 'PARADO · '+failed[-1][:46].upper())

    def set_status(self,text):self.status=text;self.render()
    def finish(self,text):self.process=None;self.status=text;self.render()

    def quit_app(self):
        if self.process is not None:self.process.send_signal(signal.SIGINT)
        self.destroy()


def main():
    if os.name=='nt':raise SystemExit('El Farm Bot multimodo aún no está certificado en Windows')
    FarmApp().mainloop()


if __name__=='__main__':
    main()
