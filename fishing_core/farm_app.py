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
from .boss_runtime import BOSSES
from .dungeon_catalog import CATALOG, FAMILIARS, dungeon
from .dungeon_runtime import ROUTE_COSTS
from .raid_runtime import RAIDS
from .telemetry import ROOT

W,H=1100,880
NAMES={'quest':'QUEST','pvp':'PVP','boss':'WORLD BOSS','raid':'RAID','expedition':'EXPEDITION','trials':'TRIALS'}
INFO={'expedition':['EVENTO SEMANAL: IDOL DIMENSION','5 BADGES, BAJA HASTA 1','NUNCA COMPRA BADGES','UNA DERROTA NO DETIENE']}
CALIBRATED={d for d,_ in ROUTE_COSTS}
ZONES=sorted({row['zone'] for row in CATALOG})
DIFFICULTY_COLORS=(('NORMAL','blue'),('HARD','green'),('HEROIC','orange'))
GOLD_STEPS=(0,10_000,50_000,100_000,250_000)
# Menú de dificultad de Trials (2026-10-04): (tier, mínimo, máximo, color del juego).
TRIALS_RANGES=((13,2300,2735,'set'),(13,1800,2299,'gold'),(12,1580,1799,'set'),(12,1240,1579,'gold'),
               (11,1080,1239,'set'),(11,675,1079,'gold'),(10,640,674,'set'),(10,500,639,'gold'),
               (9,440,499,'set'),(9,290,439,'gold'),(8,260,289,'set'),(8,210,259,'gold'),
               (7,200,209,'set'),(7,150,199,'gold'),(6,140,149,'set'),(6,110,139,'gold'),
               (5,100,109,'set'),(5,70,99,'gold'),(4,30,69,'red'),(3,20,29,'lav'),(2,10,19,'green'),(1,1,9,'white'))
TEXT_COLORS={'set':(96,224,244),'gold':(252,216,48),'red':(250,112,100),'lav':(150,154,250),
             'green':(140,232,110),'white':(255,255,255)}


def familiars_of(identifier):
    return [name for name,routes in FAMILIARS.items() if identifier in routes]


def trials_range(level):
    return next(r for r in TRIALS_RANGES if r[1]<=level<=r[2])


def short(n):
    return f'{n//1000}K' if n>=1000 else str(n)


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
        getattr(self,f'draw_{self.screen if self.screen in ("main","quest","boss","raid","trials","pvp") else "info"}')()
        self.photo=ImageTk.PhotoImage(self.img);self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo)

    def window(self,title,back=True):
        self.put(ui.frame(W-40,H-30,title),20,10)
        self.put(ui.close_button(),W-112,74,self.go_main if back else self.quit_app)

    def choice_row(self,x,y,w,label,chosen,action,color=ui.TEXT,size=17,h=50):
        self.put(ui.row(w,h),x,y);self.label(label,x+14,y+(h-24)//2,size,color)
        self.put(ui.checkbox(chosen,h-12),x+w-h+4,y+6,action)

    def buttons(self,options,current,x,y,w,h,action,gap=10,size=22):
        for i,(value,color) in enumerate(options):
            self.put(ui.button(value,w,h,color if current.upper()==value else 'gray',size),x,y+i*(h+gap),
                     lambda v=value:action(v))

    def draw_main(self):
        self.window('FARM BOT',back=False)
        running=self.process is not None
        for i,mode in enumerate(farm_config.MODES):
            x=82+(i%3)*318;y=158+(i//3)*250;on=self.config_data['modes'][mode]
            self.put(ui.row(298,230),x,y)
            icon=ui.icon(mode,118);self.put(icon if on else ui.dimmed(icon),x+(298-icon.width)//2,y+14,lambda m=mode:self.open_mode(m))
            for j,line in enumerate(self.summary(mode)):self.label(line[:17],x+16,y+164+j*30,16,ui.GOLD if on else ui.DIM)
            self.put(ui.checkbox(on),x+232,y+164,None if running else lambda m=mode:self.toggle_mode(m))
        self.put(ui.checkbox(self.config_data['runes'],44),82,676,None if running else self.toggle_runes)
        self.label('CAMBIAR RUNAS (CAPTURA / ITEM FIND)',138,682,18)
        self.label('PULSA UN ICONO PARA ELEGIR QUE HACE CADA MODO',82,724,14,ui.DIM)
        self.label(self.status[:58],82,756,16,ui.GOLD if running else ui.DIM)
        self.put(ui.auto_button(running,150,124),W-232,664,self.toggle_run)

    def summary(self,mode):
        c=self.config_data
        if mode=='quest':
            q=c['quest'];return [f"{q['dungeon']} {q['difficulty'].upper()}",' '.join(n.upper() for n in q['targets']) or 'SIN OBJETIVO']
        if mode=='boss':
            b=c['boss'];return [BOSSES[b['boss']][0].upper(),f"T{b['tier']} {b['difficulty'].upper()}"]
        if mode=='raid':return [RAIDS[c['raid']['raid']].upper(),c['raid']['difficulty'].upper()]
        if mode=='trials':
            level=int(c['trials']['difficulty']);tier=trials_range(level)[0];return [f'NIVEL {level}',f'TIER {tier}']
        if mode=='pvp':return ['5 TICKETS',f"RIVAL {c['pvp']['opponent']} DE 4"]
        return ['SEMANAL']

    def draw_quest(self):
        self.window('QUEST');q=self.config_data['quest']
        zone_rows=[row for row in CATALOG if row['zone']==self.zone]
        self.put(ui.button('<',64,56,'blue',30),70,152,lambda:self.step_zone(-1))
        self.label(f"ZONA {self.zone} · {zone_rows[0]['zone_name'].upper()}",W//2,164,24,center=True)
        self.put(ui.button('>',64,56,'blue',30),W-134,152,lambda:self.step_zone(1))
        for i,row in enumerate(zone_rows):
            y=222+i*62;ok=row['id'] in CALIBRATED
            label=f"{row['id']} {row['name'].upper()}"[:26]
            if ok:self.choice_row(70,y,560,label,q['dungeon']==row['id'],lambda d=row['id']:self.choose_dungeon(d))
            else:
                self.put(ui.row(560,50),70,y);self.label(label,84,y+13,17,ui.DIM);self.label('SIN CALIBRAR',480,y+18,12,ui.DIM)
        self.label('DIFICULTAD',660,222,20,ui.GOLD)
        self.buttons(reversed(DIFFICULTY_COLORS),q['difficulty'],660,256,330,56,self.set_difficulty)
        self.label('EMPIEZA EN LA ELEGIDA Y BAJA SI FALTA ENERGIA',660,452,11,ui.DIM)
        self.label(f"FAMILIARES DE {q['dungeon']} (MARCA LOS OBJETIVOS)",70,486,18,ui.GOLD)
        for i,name in enumerate(familiars_of(q['dungeon'])[:9]):
            self.choice_row(70+(i%3)*325,518+(i//3)*56,305,name.upper()[:14],name in q['targets'],lambda n=name:self.toggle_target(n))
        self.label('ORO PARA PERSUADIR (POR SESION, NUNCA GEMAS)',70,700,16,ui.GOLD)
        for i,value in enumerate(GOLD_STEPS):
            self.put(ui.button(short(value),170,54,'orange' if q.get('max_gold',0)==value else 'gray',20),70+i*186,730,
                     lambda v=value:self.set_gold(v))

    def draw_boss(self):
        self.window('WORLD BOSS');b=self.config_data['boss']
        self.label('JEFE',70,150,20,ui.GOLD)
        for i,(key,(name,tiers)) in enumerate(BOSSES.items()):
            self.choice_row(70,180+i*62,560,name.upper()[:24],b['boss']==key,lambda k=key:self.set_boss(k),h=54)
        self.label('TIER',660,150,20,ui.GOLD)
        for i,tier in enumerate(BOSSES[b['boss']][1]):
            self.put(ui.button(f'TIER {tier}',330,52,'blue' if b['tier']==tier else 'gray',20),660,180+i*60,
                     lambda t=tier:self.set_tier(t))
        self.label('DIFICULTAD',660,500,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,b['difficulty'],660,532,330,52,self.set_boss_difficulty,gap=8,size=20)
        self.label('SALA PRIVADA · REGROUP · UNA DERROTA NO DETIENE',70,758,14,ui.DIM)

    def draw_raid(self):
        self.window('RAID');r=self.config_data['raid']
        self.label('RAID (LA DE TU TIER)',70,150,20,ui.GOLD)
        for i,(key,name) in enumerate(RAIDS.items()):
            self.choice_row(70,180+i*58,560,name.upper()[:24],r['raid']==key,lambda k=key:self.set_raid(k),h=50)
        self.label('DIFICULTAD',660,150,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,r['difficulty'],660,184,330,60,self.set_raid_difficulty)
        for i,line in enumerate(('1 SHARD POR RUN','HASTA AGOTARLOS','UNA DERROTA NO DETIENE')):
            self.label(line,660,420+i*36,15,ui.DIM)

    def draw_trials(self):
        self.window('TRIALS');level=int(self.config_data['trials']['difficulty']);current=trials_range(level)
        self.label('DIFICULTAD · AZUL = OBJETOS DE SET',70,148,18,ui.GOLD)
        for i,span in enumerate(TRIALS_RANGES):
            tier,low,high,color=span;x=70+(i//11)*490;y=180+(i%11)*48
            self.choice_row(x,y,470,f'T{tier}  {low:,} - {high:,}',span==current,lambda s=span:self.set_trials_range(s),
                            color=TEXT_COLORS[color],size=18,h=44)
        self.label(f'NIVEL {level}',70,724,26,TEXT_COLORS[current[3]])
        for i,(text,delta) in enumerate((('-10',-10),('-1',-1),('+1',1),('+10',10))):
            self.put(ui.button(text,120,56,'blue',22),420+i*134,716,lambda d=delta:self.step_level(d))
        self.label('5 TOKENS, BAJA HASTA 1 · NUNCA COMPRA · DERROTA NO DETIENE',70,786,13,ui.DIM)

    def draw_pvp(self):
        self.window('PVP');current=int(self.config_data['pvp']['opponent'])
        icon=ui.icon('pvp',130);self.put(icon,(W-icon.width)//2,150)
        self.label('RIVAL (DE MENOS A MAS PUNTOS)',W//2,320,20,ui.GOLD,center=True)
        labels=('1 · MAS FACIL','2','3','4 · MAS PUNTOS')
        for i,text in enumerate(labels):
            self.put(ui.button(text,440,60,'blue' if current==i+1 else 'gray',20),(W-440)//2,360+i*72,
                     lambda n=i+1:self.set_opponent(n))
        self.label('5 TICKETS, BAJA HASTA 1 · UNA DERROTA NO DETIENE',W//2,680,15,ui.DIM,center=True)

    def set_opponent(self,n):self.config_data['pvp']['opponent']=n;self.save()

    def draw_info(self):
        mode=self.screen;self.window(NAMES[mode])
        icon=ui.icon(mode,150);self.put(icon,(W-icon.width)//2,170)
        for i,line in enumerate(INFO[mode]):self.label(line,W//2,370+i*46,20,center=True)

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
    def set_gold(self,value):self.config_data['quest']['max_gold']=value;self.save()

    def toggle_target(self,name):
        targets=self.config_data['quest']['targets']
        targets.remove(name) if name in targets else targets.append(name);self.save()

    def set_boss(self,key):
        b=self.config_data['boss'];b['boss']=key
        if b['tier'] not in BOSSES[key][1]:b['tier']=BOSSES[key][1][-1]
        self.save()

    def set_tier(self,tier):self.config_data['boss']['tier']=tier;self.save()
    def set_boss_difficulty(self,level):self.config_data['boss']['difficulty']=level.title();self.save()
    def set_raid(self,key):self.config_data['raid']['raid']=key;self.save()
    def set_raid_difficulty(self,level):self.config_data['raid']['difficulty']=level.title();self.save()
    def set_trials_range(self,span):self.config_data['trials']['difficulty']=span[2];self.save()

    def step_level(self,delta):
        level=int(self.config_data['trials']['difficulty']);_,low,high,_=trials_range(level)
        self.config_data['trials']['difficulty']=max(low,min(high,level+delta));self.save()

    def toggle_run(self):
        if self.process is not None:
            self.process.send_signal(signal.SIGINT);self.status='DETENIENDO...';return
        if not any(self.config_data['modes'].values()):self.status='NINGUN MODO ACTIVO';return
        background=os.environ.get('FARM_BACKEND')=='gamescope'
        self.save();self.status='EN MARCHA EN SEGUNDO PLANO · F8 DETIENE' if background else 'EN MARCHA · F8 DETIENE · NO CAMBIES DE VENTANA'
        self.process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all'],cwd=str(ROOT),
                                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        threading.Thread(target=self.follow,args=(self.process,),daemon=True).start()

    def follow(self,process):
        steps=('Runas captura','Quest','Runas Item Find','PvP','World Boss','Raid','Expedition','Trials');results=[]
        for line in process.stdout:
            line=line.strip()
            if line.startswith('== '):self.after(0,self.set_status,f'EN MARCHA · {line[3:].upper()} · F8 DETIENE')
            elif ': ' in line and line.split(':')[0] in steps:results.append(line)
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
