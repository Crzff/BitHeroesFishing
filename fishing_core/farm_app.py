"""App del Farm Bot con el aspecto de las ventanas de Bit Heroes. Abrirla no envía input al juego.

Se dibuja con PIL (pixel_ui) en un único Canvas; cada elemento registra una zona clicable.
START lanza fishing_core.farm_all con farm_config.json. STOP solicita la parada
conjunta de los motores propios en Linux, sin cerrar clientes; F8 se conserva.
En modo escritorio, cambiar de ventana pausa el bot; gamescope permite usar el panel.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

from . import farm_config, loot, pixel_ui as ui
from .boss_runtime import BOSSES
from .dungeon_catalog import CATALOG, FAMILIARS, dungeon
from .dungeon_runtime import NODES
from .raid_runtime import RAID_TIER, RAIDS
from .telemetry import ROOT
from .accounts import NAMES as ACCOUNT_NAMES,runs_root,state_root

MULTI_SESSIONS=ROOT/'runs/accounts/sessions.json'  # endpoints de los tres clientes (los escribe quien los abre)
MULTI_STATUS=ROOT/'runs/accounts/multi_status.json'
ACCOUNT_TABS=(('steam','STEAM'),('personal','FMANI'),('perfil-1','KORTZZ'))

W,H=1180,920
NAMES={'quest':'QUEST','pvp':'PVP','boss':'WORLD BOSS','raid':'RAID','expedition':'EXPEDITION','trials':'TRIALS'}
INFO={'expedition':['EVENTO SEMANAL: IDOL DIMENSION','5 BADGES, BAJA HASTA 1','NUNCA COMPRA BADGES','UNA DERROTA NO DETIENE']}
CALIBRATED=set(NODES)
ZONES=sorted({row['zone'] for row in CATALOG})
DIFFICULTY_COLORS=(('NORMAL','blue'),('HARD','green'),('HEROIC','orange'))
GOLD_STEPS=(0,10_000,50_000,100_000,250_000)
# Menú de dificultad de Trials (2026-10-04): (tier, mínimo, máximo, color del juego).
TRIALS_RANGES=((13,2300,2735,'set'),(13,1800,2299,'gold'),(12,1580,1799,'set'),(12,1240,1579,'gold'),
               (11,1080,1239,'set'),(11,675,1079,'gold'),(10,640,674,'set'),(10,500,639,'gold'),
               (9,440,499,'set'),(9,290,439,'gold'),(8,260,289,'set'),(8,210,259,'gold'),
               (7,200,209,'set'),(7,150,199,'gold'),(6,140,149,'set'),(6,110,139,'gold'),
               (5,100,109,'set'),(5,70,99,'gold'),(4,30,69,'red'),(3,20,29,'lav'),(2,10,19,'green'),(1,1,9,'white'))
# Rarezas como las pidió crzf (2026-10-05).
RARITY_COLORS={'COMMON':(110,214,70),'RARE':(70,140,255),'EPIC':(255,150,40),'LEGENDARY':(255,226,60),
               'MYTHIC':(240,60,60),'SET':(110,214,255)}
RESOURCE={'quest':'energy','pvp':'tickets','boss':'xeals','raid':'shards','expedition':'badges','trials':'tokens'}
TEXT_COLORS={'set':(96,224,244),'gold':(252,216,48),'red':(250,112,100),'lav':(150,154,250),
             'green':(140,232,110),'white':(255,255,255)}


def familiars_of(identifier):
    return [name for name,routes in FAMILIARS.items() if identifier in routes]


def trials_range(level):
    return next(r for r in TRIALS_RANGES if r[1]<=level<=r[2])


def short(n):
    return f'{n//1000}K' if n>=1000 else str(n)


class FarmApp(tk.Tk):
    def __init__(self,sessions=None,read_only=False):
        if read_only and sessions is None:raise ValueError('Observación requiere endpoints explícitos de las tres cuentas')
        super().__init__()
        self.title('Bit Heroes Farm Bot');self.resizable(False,False);self.configure(bg='#19283a')
        self.canvas=tk.Canvas(self,width=W,height=H,highlightthickness=0,bg='#19283a');self.canvas.pack()
        self.canvas.bind('<Button-1>',self.on_click);self.tier_scroll=0;self.wheel_zone=None
        for event,step in (('<Button-4>',-1),('<Button-5>',1)):self.canvas.bind(event,lambda e,s=step:self.on_wheel(e,s))
        self.canvas.bind('<MouseWheel>',lambda e:self.on_wheel(e,-1 if e.delta>0 else 1))
        self.sessions=sessions;self.read_only=read_only;self.config_data=farm_config.load();self.screen='main';self.process=None
        self.multi=None;self.account=None
        if sessions is None and MULTI_SESSIONS.exists():  # farmeo de las tres cuentas a la vez
            try:
                from .farm_multi import trial_environments
                self.multi=json.loads(MULTI_SESSIONS.read_text());trial_environments(self.multi)
                self.account='steam';self.config_data=farm_config.load(self.config_path())
            except (OSError,ValueError):self.multi=None
        self.status='LISTO · ELIGE MODOS Y PULSA START';self.zone=dungeon(self.config_data['quest']['dungeon'])['zone']
        if sessions is not None:
            self.status='PRUEBA LIMITADA · 3 CUENTAS · SIN ORO NI GEMAS'
            if read_only:self.status='COMPROBAR STOP · SIN INPUT NI GASTO'
            self.bind('<space>',lambda e:(self.toggle_run(),self.render()))
        self.supervisor_pid=None;self.account_status={}
        self.protocol('WM_DELETE_WINDOW',self.quit_app);self.refresh_multi_status()

    def read_multi_status(self):
        self.supervisor_pid=None
        try:
            data=json.loads(MULTI_STATUS.read_text());pid=data['supervisor_pid'];accounts=data['accounts']
            if type(pid) is not int or pid<=0 or type(accounts) is not dict:return
            if any(type(row) is not dict or any(type(row.get(k)) is not str for k in ('step','state','detail'))
                   for row in accounts.values()):return
            self.account_status=accounts
            if sys.platform=='linux':
                os.kill(pid,0);args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                if b'fishing_core.farm_multi' in args and b'--farm' in args:self.supervisor_pid=pid
        except (OSError,ValueError,KeyError,TypeError,RecursionError):pass

    def refresh_multi_status(self):
        self.read_multi_status();self.render();self.after(2000,self.refresh_multi_status)

    def running(self):return self.process is not None or bool(getattr(self,'supervisor_pid',None))

    def draw_account_status(self,x,y):
        for i,(account,name) in enumerate(ACCOUNT_TABS):
            row=self.account_status.get(account,{});state=row.get('state','PARADO')
            text=f"{name} · {row.get('step','Iniciando').upper()} · {state}"
            if state=='PARADO' and row.get('detail'):text+=': '+row['detail'][:60]
            self.label(text,x,y+i*24,14,TEXT_COLORS['green'] if state=='EN MARCHA' else TEXT_COLORS['red'] if state=='PARADO' else ui.DIM)

    # --- dibujo -----------------------------------------------------------------
    def put(self,img,x,y,action=None):
        self.img.alpha_composite(img,(int(x),int(y)))
        if action:self.zones.append((x,y,x+img.width,y+img.height,action))

    def label(self,txt,x,y,size=22,color=ui.TEXT,center=False):
        t=ui.text(txt,size,color=color);self.put(t,x-(t.width//2 if center else 0),y);return t

    def render(self):
        self.img=Image.new('RGBA',(W,H),(25,40,58,255));self.zones=[];self.wheel_zone=None
        screens=("main","quest","boss","raid","trials","pvp","loot")
        getattr(self,f'draw_{self.screen if self.screen in screens else "info"}')()
        self.photo=ImageTk.PhotoImage(self.img);self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo)

    def window(self,title,back=True,style='settings',art=None,dim=0):
        """Marco real del juego; devuelve la caja útil (x0,y0,x1,y1) dentro de su panel."""
        m=4;self.put(ui.frame(W-2*m,H,None,style),m,0);geo=ui.frame_geometry(W-2*m,H,style)
        x0,y0,x1,y1=geo['interior'];px0,py0,px1,py1=x0+m+14,y0+14,x1+m-14,y1-14
        self.put(ui.art_panel(art,px1-px0,py1-py0,dim) if art is not None else ui.panel(px1-px0,py1-py0),px0,py0)
        plaque,(qx,qy)=ui.title_plaque(W-2*m,title,style);self.put(plaque,qx+m,qy)
        py0=max(py0,qy+plaque.height-30)  # la placa monta sobre el panel, como en el juego
        cx0,cy0,cx1,cy1=geo['close']
        self.zones.append((cx0+m,cy0,cx1+m,cy1,self.go_main if back else self.quit_app))
        return px0+20,py0+18,px1-20,py1-18

    def choice_row(self,x,y,w,label,chosen,action,color=ui.TEXT,size=17,h=50):
        self.put(ui.row(w,h),x,y);self.label(label,x+16,y+(h-ui.text(label,size).height)//2,size,color)
        self.put(ui.checkbox(chosen,h-12),x+w-h+4,y+6,action)

    def buttons(self,options,current,x,y,w,h,action,gap=10,size=22,on=None):
        for i,(value,color) in enumerate(options):
            self.put(ui.button(value,w,h,(on or color) if current.upper()==value else 'gray',size),x,y+i*(h+gap),
                     lambda v=value:action(v))

    def resource(self,name,height=40):
        img=Image.open(ui.ICONS/f'res/{name}.png').convert('RGBA')
        scale=height/max(img.size)  # mismo cuadro para todos (energía es diagonal, xeals cuadrado)
        return img.resize((max(1,round(img.width*scale)),max(1,round(img.height*scale))),Image.NEAREST)

    def draw_main(self):
        if getattr(self,'sessions',None) is not None:return self.draw_trial()
        x0,y0,x1,y1=self.window('FARM BOT',back=False)
        running=self.running();cw=(x1-x0-40)//3;ch=236
        for i,mode in enumerate(farm_config.MODES):
            x=x0+(i%3)*(cw+20);y=y0+(i//3)*(ch+20);on=self.config_data['modes'][mode]
            self.put(ui.row(cw,ch),x,y)
            icon=ui.icon(mode,120);ix=x+round(cw/2-ui.visual_center(icon))
            self.put(icon if on else ui.dimmed(icon),ix,y+14,lambda m=mode:self.open_mode(m))
            res=self.resource(RESOURCE[mode],38);self.put(res if on else ui.dimmed(res),x+14,y+14)
            for j,line in enumerate(self.summary(mode)):self.label(line[:18],x+18,y+148+j*32,16,ui.GOLD if on else ui.DIM)
            self.put(ui.checkbox(on),x+cw-68,y+ch-68,None if running else lambda m=mode:self.toggle_mode(m))
        y=y0+2*(ch+20)+4
        self.put(ui.checkbox(self.config_data['runes'],44),x0,y,None if running else self.toggle_runes)
        self.label('CAMBIAR RUNAS (CAPTURA / ITEM FIND)',x0+58,y+8,18)
        if self.multi:  # se configura una cuenta cada vez; START farmea las tres
            self.label('CUENTA',x0,y+66,18,ui.GOLD)
            for i,(account,label) in enumerate(ACCOUNT_TABS):
                self.put(ui.button(label,140,46,'blue' if self.account==account else 'gray',18),x0+110+i*152,y+52,
                         lambda a=account:self.choose_account(a))  # ver otra cuenta no cambia nada; editar sigue bloqueado
        else:
            self.put(ui.checkbox(self.config_data['background'],44),x0,y+56,None if running else self.toggle_background)
            self.label('SEGUNDO PLANO (JUEGO EN GAMESCOPE)',x0+58,y+64,18)
        if self.account_status:self.draw_account_status(x0,y+112)
        else:self.label(self.status[:52],x0,y+124,16,ui.GOLD if running else ui.DIM)
        self.put(ui.loot_button(150,y1-y),x1-150-170,y,self.open_loot)
        self.put(ui.auto_button(running,150,y1-y),x1-150,y,self.toggle_run)

    def draw_trial(self):
        read_only=getattr(self,'read_only',False)
        x0,y0,x1,y1=self.window('COMPROBAR STOP' if read_only else 'PRUEBA MULTICUENTA',back=False)
        for i,name in enumerate(ACCOUNT_NAMES.values()):
            y=y0+i*140;self.put(ui.row(x1-x0,120),x0,y)
            self.label(name.upper(),x0+18,y+18,22,ui.GOLD)
            self.label('OBSERVAR HOME · 0 INPUTS · 0 ENTRADAS' if read_only else '1 DUNGEON NORMAL · MAXIMO 10 ENERGIA',x0+18,y+60,18)
        self.label('MOTORES REALES · INPUT BLOQUEADO' if read_only else 'SIN ORO, GEMAS, RUNAS NI REINTENTOS',x0,y0+450,18,ui.GOLD)
        self.label('START/STOP: BOTON O ESPACIO · SOLO CLIENTES YA PREPARADOS',x0,y0+494,14,ui.DIM)
        self.label(self.status[:64],x0,y1-150,16,ui.GOLD)
        self.put(ui.auto_button(self.process is not None,150,100),x1-150,y1-110,self.toggle_run)

    def summary(self,mode):
        c=self.config_data
        if mode=='quest':
            q=c['quest'];return [f"{q['dungeon']} {q['difficulty'].upper()}",' '.join(n.upper() for n in q['targets']) or 'SIN OBJETIVO']
        if mode=='boss':
            b=c['boss'];return [BOSSES[b['boss']][0].upper(),f"T{b['tier']} {b['difficulty'].upper()}"]
        if mode=='raid':r=c['raid']['raid'];return [RAIDS[r].upper(),f"T{RAID_TIER[r]} {c['raid']['difficulty'].upper()}"]
        if mode=='trials':
            level=int(c['trials']['difficulty']);tier=trials_range(level)[0];return [f'NIVEL {level}',f'TIER {tier}']
        if mode=='pvp':return ['5 TICKETS','MAS PUNTOS' if c['pvp']['opponent']==4 else f"{5-c['pvp']['opponent']} DESDE ABAJO"]
        return ['SEMANAL']

    def draw_quest(self):
        q=self.config_data['quest'];x0,y0,x1,y1=self.window('QUEST',art=ui.background(f'zone_{self.zone}'))
        zone_rows=[row for row in CATALOG if row['zone']==self.zone]
        self.put(ui.button('<',64,56,'blue',30),x0,y0,lambda:self.step_zone(-1))
        self.label(f"ZONA {self.zone} · {zone_rows[0]['zone_name'].upper()}",(x0+x1)//2,y0+12,26,center=True)
        self.put(ui.button('>',64,56,'blue',30),x1-64,y0,lambda:self.step_zone(1))
        lw=600;rx=x0+lw+24
        for i,row in enumerate(zone_rows):
            y=y0+74+i*60;ok=row['id'] in CALIBRATED
            label=f"{row['id']} {row['name'].upper()}"[:28]
            if ok:self.choice_row(x0,y,lw,label,q['dungeon']==row['id'],lambda d=row['id']:self.choose_dungeon(d))
            else:
                self.put(ui.row(lw,50),x0,y);self.label(label,x0+16,y+14,17,ui.DIM);self.label('SIN CALIBRAR',x0+lw-150,y+18,12,ui.DIM)
        self.label('DIFICULTAD',rx,y0+74,20,ui.GOLD)
        if dungeon(q['dungeon'])['special']:
            self.put(ui.button('SPECIAL · 20',x1-rx,56,'purple'),rx,y0+106)
        else:self.buttons(reversed(DIFFICULTY_COLORS),q['difficulty'],rx,y0+106,x1-rx,52,self.set_difficulty,gap=8)
        fy=y0+74+4*60+14;fam=Image.open(ui.ICONS/'res/familiars.png').convert('RGBA').resize((54,55),Image.NEAREST)
        self.put(fam,x0,fy-8);self.label(f"FAMILIARES DE {q['dungeon']} · MARCADO = CAPTURAR, RESTO = RECHAZAR",x0+64,fy+8,15,ui.GOLD)
        bw=(x1-x0-40)//3
        for i,name in enumerate(familiars_of(q['dungeon'])[:9]):
            self.choice_row(x0+(i%3)*(bw+20),fy+56+(i//3)*58,bw,name.upper()[:14],name in q['targets'],lambda n=name:self.toggle_target(n))
        gy=y1-90;self.label('ORO PARA PERSUADIR (POR SESION, NUNCA GEMAS)',x0,gy,16,ui.GOLD)
        gw=(x1-x0-4*14)//5
        for i,value in enumerate(GOLD_STEPS):
            self.put(ui.button(short(value),gw,52,'orange' if q.get('max_gold',0)==value else 'gray',20),x0+i*(gw+14),gy+34,
                     lambda v=value:self.set_gold(v))

    def draw_boss(self):
        b=self.config_data['boss'];x0,y0,x1,y1=self.window('WORLD BOSS',art=ui.background(f"wb_{b['boss'].lower()}"),dim=.1)
        self.label('JEFE',x0,y0,20,ui.GOLD);lw=500;rx=x1-380
        for i,(key,(name,tiers)) in enumerate(BOSSES.items()):
            self.choice_row(x0,y0+34+i*66,lw,name.upper()[:24],b['boss']==key,lambda k=key:self.set_boss(k),h=56)
        self.label('TIER',rx,y0,20,ui.GOLD);tiers=BOSSES[b['boss']][1];shown=4
        self.tier_scroll=max(0,min(self.tier_scroll,len(tiers)-shown));bw=x1-rx-60
        for i,tier in enumerate(tiers[self.tier_scroll:self.tier_scroll+shown]):
            self.put(ui.button(f'TIER {tier}',bw,52,'wb' if b['tier']==tier else 'gray',20),rx,y0+34+i*60,
                     lambda t=tier:self.set_tier(t))
        # Scroll de tiers, como el menú del juego: flechas o rueda del ratón.
        self.put(ui.arrow_button(52,112,True,self.tier_scroll>0),x1-52,y0+34,lambda:self.scroll_tiers(-1))
        self.put(ui.arrow_button(52,112,False,self.tier_scroll<len(tiers)-shown),x1-52,y0+154,lambda:self.scroll_tiers(1))
        self.wheel_zone=(rx,y0+34,x1,y0+34+shown*60);self.wheel_action=self.scroll_tiers
        self.label('DIFICULTAD',rx,y0+300,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,b['difficulty'],rx,y0+334,x1-rx,52,self.set_boss_difficulty,gap=8,size=20)
        self.label('SALA PRIVADA · REGROUP · UNA DERROTA NO DETIENE',x0,y1-20,14,ui.TEXT)

    def draw_raid(self):
        r=self.config_data['raid'];x0,y0,x1,y1=self.window('RAID',style='raid',art=ui.background(f"raid_{r['raid'].lower()}"),dim=.1)
        self.label('RAID (LA DE TU TIER)',x0,y0,20,ui.GOLD);lw=500;rx=x1-380
        raids=list(reversed(RAIDS.items()));shown=10  # 18 raids: de la de más tier a la primera, con scroll
        self.raid_scroll=max(0,min(getattr(self,'raid_scroll',0),len(raids)-shown))
        for i,(key,name) in enumerate(raids[self.raid_scroll:self.raid_scroll+shown]):
            self.choice_row(x0,y0+34+i*58,lw-60,f'T{RAID_TIER[key]} {name.upper()}'[:26],r['raid']==key,lambda k=key:self.set_raid(k),h=50,size=14)
        self.put(ui.arrow_button(52,280,True,self.raid_scroll>0),x0+lw-52,y0+34,lambda:self.scroll_raids(-1))
        self.put(ui.arrow_button(52,280,False,self.raid_scroll<len(raids)-shown),x0+lw-52,y0+34+290,lambda:self.scroll_raids(1))
        self.wheel_zone=(x0,y0+34,x0+lw,y0+34+shown*58);self.wheel_action=self.scroll_raids
        self.label('DIFICULTAD',rx,y0,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,r['difficulty'],rx,y0+34,x1-rx,60,self.set_raid_difficulty,on='purple')
        for i,line in enumerate(('1 SHARD POR RUN','HASTA AGOTARLOS','UNA DERROTA NO DETIENE','PERSUADE A CUALQUIER FAMILIAR')):
            self.label(line,rx,y0+260+i*36,15,ui.TEXT)
        self.label('ORO PARA PERSUADIR (NUNCA GEMAS)',rx,y0+420,15,ui.GOLD)
        gold=int(r.get('max_gold',250_000))
        for i,value in enumerate(GOLD_STEPS):
            self.put(ui.button(short(value),(x1-rx-8)//2,46,'purple' if gold==value else 'gray',18),
                     rx+(i%2)*((x1-rx+8)//2),y0+452+(i//2)*54,lambda v=value:self.set_raid_gold(v))

    def draw_trials(self):
        x0,y0,x1,y1=self.window('TRIALS');level=int(self.config_data['trials']['difficulty']);current=trials_range(level)
        self.label('DIFICULTAD · AZUL = OBJETOS DE SET',x0,y0,18,ui.GOLD);cw=(x1-x0-20)//2
        for i,span in enumerate(TRIALS_RANGES):
            tier,low,high,color=span;x=x0+(i//11)*(cw+20);y=y0+32+(i%11)*48
            self.choice_row(x,y,cw,f'T{tier}  {low:,} - {high:,}',span==current,lambda s=span:self.set_trials_range(s),
                            color=TEXT_COLORS[color],size=18,h=44)
        by=y0+32+11*48+14;self.label(f'NIVEL {level}',x0,by+12,26,TEXT_COLORS[current[3]])
        for i,(text,delta) in enumerate((('-10',-10),('-1',-1),('+1',1),('+10',10))):
            self.put(ui.button(text,120,56,'blue',22),x1-4*134+14+i*134,by,lambda d=delta:self.step_level(d))
        self.label('5 TOKENS, BAJA HASTA 1 · NUNCA COMPRA · DERROTA NO DETIENE',x0,y1-18,13,ui.DIM)

    def draw_pvp(self):
        x0,y0,x1,y1=self.window('PVP');current=int(self.config_data['pvp']['opponent']);cx=(x0+x1)//2
        icon=ui.icon('pvp',130);self.put(icon,cx-icon.width//2,y0+10)
        self.label('RIVAL (BAJA AL FINAL DE LA LISTA)',cx,y0+170,20,ui.GOLD,center=True)
        labels=('4 DESDE ABAJO','3 DESDE ABAJO','2 DESDE ABAJO','EL QUE MAS PUNTOS DA')
        for i,text in enumerate(labels):
            self.put(ui.button(text,460,60,'blue' if current==i+1 else 'gray',20),cx-230,y0+214+i*72,
                     lambda n=i+1:self.set_opponent(n))
        self.label('5 TICKETS, BAJA HASTA 1 · UNA DERROTA NO DETIENE',cx,y1-24,15,ui.DIM,center=True)

    def set_opponent(self,n):self.config_data['pvp']['opponent']=n;self.save()

    def draw_info(self):
        mode=self.screen;x0,y0,x1,y1=self.window(NAMES[mode]);cx=(x0+x1)//2
        icon=ui.icon(mode,150);self.put(icon,cx-icon.width//2,y0+20)
        for i,line in enumerate(INFO[mode]):self.label(line,cx,y0+220+i*46,20,center=True)

    def draw_loot(self):
        x0,y0,x1,y1=self.window('LOOT');root=self.loot_root();totals=loot.load(root/'loot_totals.json' if root else None)
        album_dir=root/'loot_album' if root else loot.ALBUM
        self.put(self.resource('gold',44),x0,y0);self.label(f"ORO  {totals['gold']:,}",x0+64,y0+10,24,ui.GOLD)
        self.label(f"XP  {totals['xp']:,}",x0+420,y0+10,24,(140,232,110))
        # Solo míticos y de conjunto (crzf): objetos y materiales; a la derecha, los familiares.
        cw=(x1-x0-2*14)//3
        for c,(title,group) in enumerate((('OBJETOS','items'),('MATERIALES','materials'))):
            cx=x0+c*(cw+14);self.label(title,cx,y0+74,18,ui.GOLD)
            for i,rarity in enumerate(loot.TRACKED):
                y=y0+108+i*62;self.put(ui.row(cw,54),cx,y)
                self.label('CONJUNTO' if rarity=='SET' else loot.RARITY_NAMES[rarity],cx+14,y+17,17,RARITY_COLORS[rarity])
                count=str(totals.get(group,{}).get(rarity,0));self.label(count,cx+cw-16-ui.text(count,17).width,y+17,17)
        fx=x0+2*(cw+14);self.label('FAMILIARES',fx,y0+74,18,ui.GOLD)
        fam=Image.open(ui.ICONS/'res/familiars.png').convert('RGBA').resize((40,41),Image.NEAREST)
        for i,(name,count) in enumerate(sorted(totals['familiars'].items())[:6]):
            y=y0+108+i*52;self.put(ui.row(cw,46),fx,y);self.put(fam,fx+6,y+2)
            self.label(f'{name.upper()[:9]} x{count}',fx+52,y+14,14)
        if not totals['familiars']:self.label('NINGUNO TODAVIA',fx,y0+120,14,ui.DIM)
        for i,(mode,res) in enumerate(RESOURCE.items()):
            x=x0+i*((x1-x0)//6);self.put(self.resource(res,40),x,y1-60)
            self.label(str(totals['spent'].get(res,0)),x+52,y1-50,18)
        album=sorted(((k,e) for k,e in totals['album'].items() if e['rarity'] in loot.TRACKED),key=lambda kv:(('ITEM','MATERIAL','CONSUMABLE').index(kv[1]['kind']),loot.ORDER.index(kv[1]['rarity']),-kv[1]['count']))
        ay=y0+108+2*62+40;self.label('ALBUM (MITICOS Y DE CONJUNTO)',x0,ay,16,ui.GOLD);size=58
        for i,(key,entry) in enumerate(album[:(x1-x0)//(size+8)]):
            path=album_dir/f'{key}.png'
            if not path.exists():continue
            x=x0+i*(size+8);self.put(ui.loot_icon(path,entry['rarity'],RARITY_COLORS[entry['rarity']],size),x,ay+28)
            if entry['count']>1:self.label(str(entry['count']),x+4,ay+30,13)
        self.label('GASTADO EN ESTA SESION',x0,y1-96,16,ui.GOLD)
        self.put(ui.button('REINICIAR',200,50,'red',20),x1-200,y0,self.reset_loot)
        if not getattr(self,'loot_job',None):self.loot_job=self.after(5000,self.refresh_loot)  # se actualiza sola

    def refresh_loot(self):
        self.loot_job=None
        if self.screen=='loot':self.render()

    # --- acciones ---------------------------------------------------------------
    def on_click(self,event):
        for x0,y0,x1,y1,action in reversed(self.zones):
            if x0<=event.x<x1 and y0<=event.y<y1:action();self.render();return

    def config_path(self):
        return state_root(ROOT,{'FARM_ACCOUNT':self.account})/'farm_config.json' if self.multi else None

    def loot_root(self):
        return runs_root(ROOT,{'FARM_ACCOUNT':self.account}) if self.multi else None

    def choose_account(self,account):
        self.account=account;self.config_data=farm_config.load(self.config_path())
        self.zone=dungeon(self.config_data['quest']['dungeon'])['zone']

    def save(self):
        farm_config.save(self.config_data,self.config_path())

    def go_main(self):self.screen='main'
    def open_loot(self):self.screen='loot'
    def reset_loot(self):
        root=self.loot_root();loot.reset(root/'loot_totals.json' if root else None)
    def open_mode(self,mode):
        if not self.running():self.screen=mode
        if mode=='boss':self.show_tier()
        if mode=='raid':  # que la raid elegida quede a la vista
            keys=list(reversed(RAIDS));self.raid_scroll=max(0,keys.index(self.config_data['raid']['raid'])-4)

    def show_tier(self):
        """Desplaza la columna de tiers para que el elegido quede a la vista."""
        b=self.config_data['boss'];tiers=BOSSES[b['boss']][1]
        self.tier_scroll=max(0,tiers.index(b['tier'])-3) if b['tier'] in tiers else 0
    def toggle_mode(self,mode):self.config_data['modes'][mode]^=True;self.save()
    def toggle_runes(self):self.config_data['runes']^=True;self.save()
    def toggle_background(self):self.config_data['background']^=True;self.save()
    def step_zone(self,delta):self.zone=ZONES[(ZONES.index(self.zone)+delta)%len(ZONES)]

    def choose_dungeon(self,identifier):
        q=self.config_data['quest']
        if q['dungeon']!=identifier:q['dungeon']=identifier;q['targets']=[]
        special=dungeon(identifier)['special']
        if special!=(q['difficulty']=='Special'):q['difficulty']='Special' if special else 'Heroic'
        self.save()

    def set_difficulty(self,level):self.config_data['quest']['difficulty']=level.title();self.save()
    def set_gold(self,value):self.config_data['quest']['max_gold']=value;self.save()

    def toggle_target(self,name):
        targets=self.config_data['quest']['targets']
        targets.remove(name) if name in targets else targets.append(name);self.save()

    def set_boss(self,key):
        b=self.config_data['boss'];b['boss']=key
        if b['tier'] not in BOSSES[key][1]:b['tier']=BOSSES[key][1][-1]
        self.show_tier();self.save()

    def scroll_tiers(self,step):self.tier_scroll+=step
    def scroll_raids(self,step):self.raid_scroll=getattr(self,'raid_scroll',0)+step

    def on_wheel(self,event,step):
        z=self.wheel_zone
        if z and z[0]<=event.x<z[2] and z[1]<=event.y<z[3]:getattr(self,'wheel_action',self.scroll_tiers)(step);self.render()

    def set_tier(self,tier):self.config_data['boss']['tier']=tier;self.save()
    def set_boss_difficulty(self,level):self.config_data['boss']['difficulty']=level.title();self.save()
    def set_raid(self,key):self.config_data['raid']['raid']=key;self.save()
    def set_raid_gold(self,value):self.config_data['raid']['max_gold']=value;self.save()
    def set_raid_difficulty(self,level):self.config_data['raid']['difficulty']=level.title();self.save()
    def set_trials_range(self,span):self.config_data['trials']['difficulty']=span[2];self.save()

    def step_level(self,delta):
        level=int(self.config_data['trials']['difficulty']);_,low,high,_=trials_range(level)
        self.config_data['trials']['difficulty']=max(low,min(high,level+delta));self.save()

    def toggle_run(self):
        if getattr(self,'account_status',None) is not None:self.read_multi_status()
        if getattr(self,'supervisor_pid',None):
            try:os.kill(self.supervisor_pid,signal.SIGINT)
            except OSError:pass
            self.status='DETENIENDO...';return
        if self.process is not None:
            if sys.platform=='linux':
                from .global_stop import stop_workers
                stop_workers()
            else:self.process.send_signal(signal.SIGINT)
            self.status='DETENIENDO...';return
        if getattr(self,'sessions',None) is not None:
            from .farm_multi import start_trial
            try:self.process=start_trial(self.sessions,read_only=True) if getattr(self,'read_only',False) else start_trial(self.sessions)
            except (ValueError,RuntimeError,OSError):self.status='PRUEBA BLOQUEADA · CLIENTES NO CERTIFICADOS';return
            self.status='PRUEBA EN MARCHA · 3 CUENTAS · STOP EN EL PANEL'
            threading.Thread(target=self.follow,args=(self.process,),daemon=True).start();return
        if self.multi:
            from .farm_multi import start_farm
            self.save()
            try:self.process=start_farm(self.multi)
            except (ValueError,RuntimeError,OSError) as exc:self.status=('NO ARRANCA · '+str(exc))[:52].upper();return
            self.status='EN MARCHA · 3 CUENTAS · STOP EN EL PANEL'
            threading.Thread(target=self.follow,args=(self.process,),daemon=True).start();return
        if not any(self.config_data['modes'].values()):self.status='NINGUN MODO ACTIVO';return
        background=self.config_data['background'] or os.environ.get('FARM_BACKEND')=='gamescope'
        env={**os.environ,'FARM_BACKEND':'gamescope' if background else ''}
        self.save();self.status='EN MARCHA EN SEGUNDO PLANO · STOP EN EL PANEL' if background else 'EN MARCHA · STOP EN EL PANEL · JUEGO CON FOCO'
        self.process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all'],cwd=str(ROOT),env=env,
                                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        threading.Thread(target=self.follow,args=(self.process,),daemon=True).start()

    def follow(self,process):
        trial=getattr(self,'sessions',None) is not None
        steps=('Runas captura','Quest','Runas Item Find','PvP','World Boss','Raid','Expedition','Trials',*ACCOUNT_NAMES.values());results=[]
        path=runs_root(ROOT)/('farm_multi.log' if trial else 'farm_all.log');path.parent.mkdir(parents=True,exist_ok=True)
        log=open(path,'a',encoding='utf-8')  # causa de cada parada, para revisarla después
        log.write(f'\n--- {time.strftime("%Y-%m-%d %H:%M:%S")} inicio pid {process.pid}\n');log.flush()
        multi=getattr(self,'multi',None) is not None and not trial
        for line in process.stdout:
            line=line.strip();log.write(f'{time.strftime("%H:%M:%S")} {line}\n');log.flush()
            if multi:
                continue
            if line.startswith('== '):
                paused='en pausa' in line
                self.after(0,self.set_status,('EN PAUSA · VUELVE AL JUEGO: ' if paused else 'EN MARCHA · ')+line[3:].split(' (')[0].upper()+('' if paused else ' · STOP EN EL PANEL'))
            elif ': ' in line and line.split(':')[0] in steps:results.append(line)
        code=process.wait();log.write(f'{time.strftime("%H:%M:%S")} fin código {code}\n');log.close()
        failed=[r for r in results if not r.split(': ',1)[1].startswith('OK')]  # 'OK (ya hecho)' al reanudar
        if code and not failed:failed.append(f'Código de salida {code}')
        self.after(0,self.finish,('PRUEBA COMPLETADA · LIMITES CONSERVADOS' if trial else 'TERMINADO · TODO GASTADO')
                   if not failed else 'PARADO · '+failed[-1][:46].upper())

    def set_status(self,text):self.status=text;self.render()
    def finish(self,text):self.process=None;self.status=text;self.render()

    def quit_app(self):
        if self.process is not None:self.toggle_run()
        self.destroy()


def main(argv=None):
    if os.name=='nt':raise SystemExit('El Farm Bot multimodo aún no está certificado en Windows')
    argv=sys.argv[1:] if argv is None else argv
    if argv not in ([],['--trial'],['--stop-check']):raise SystemExit('Argumentos no válidos')
    sessions=None
    if argv:
        from .farm_multi import read_sessions,trial_environments
        sessions=read_sessions();trial_environments(sessions)
    if argv==['--stop-check']:FarmApp(sessions=sessions,read_only=True).mainloop()
    else:FarmApp(sessions=sessions).mainloop()


if __name__=='__main__':
    main()
