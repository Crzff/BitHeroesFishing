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

from . import farm_config, loot, pixel_ui as ui
from .boss_runtime import BOSSES
from .dungeon_catalog import CATALOG, FAMILIARS, dungeon
from .dungeon_runtime import NODES
from .raid_runtime import RAIDS
from .telemetry import ROOT

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
        return img.resize((round(img.width*height/img.height),height),Image.NEAREST)

    def draw_main(self):
        x0,y0,x1,y1=self.window('FARM BOT',back=False)
        running=self.process is not None;cw=(x1-x0-40)//3;ch=236
        for i,mode in enumerate(farm_config.MODES):
            x=x0+(i%3)*(cw+20);y=y0+(i//3)*(ch+20);on=self.config_data['modes'][mode]
            self.put(ui.row(cw,ch),x,y)
            icon=ui.icon(mode,120);self.put(icon if on else ui.dimmed(icon),x+(cw-icon.width)//2,y+14,lambda m=mode:self.open_mode(m))
            res=self.resource(RESOURCE[mode],38);self.put(res if on else ui.dimmed(res),x+14,y+14)
            for j,line in enumerate(self.summary(mode)):self.label(line[:18],x+18,y+148+j*32,16,ui.GOLD if on else ui.DIM)
            self.put(ui.checkbox(on),x+cw-68,y+ch-68,None if running else lambda m=mode:self.toggle_mode(m))
        y=y0+2*(ch+20)+4
        self.put(ui.checkbox(self.config_data['runes'],44),x0,y,None if running else self.toggle_runes)
        self.label('CAMBIAR RUNAS (CAPTURA / ITEM FIND)',x0+58,y+8,18)
        self.put(ui.checkbox(self.config_data['background'],44),x0,y+56,None if running else self.toggle_background)
        self.label('SEGUNDO PLANO (JUEGO EN GAMESCOPE)',x0+58,y+64,18)
        self.label(self.status[:52],x0,y+124,16,ui.GOLD if running else ui.DIM)
        self.put(ui.loot_button(150,y1-y),x1-150-170,y,self.open_loot)
        self.put(ui.auto_button(running,150,y1-y),x1-150,y,self.toggle_run)

    def summary(self,mode):
        c=self.config_data
        if mode=='quest':
            q=c['quest'];return [f"{q['dungeon']} {q['difficulty'].upper()}",' '.join(n.upper() for n in q['targets']) or 'SIN OBJETIVO']
        if mode=='boss':
            b=c['boss'];return [BOSSES[b['boss']][0].upper(),f"T{b['tier']} {b['difficulty'].upper()}"]
        if mode=='raid':return [RAIDS[c['raid']['raid']].upper(),c['raid']['difficulty'].upper()]
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
        self.label('TIER',rx,y0,20,ui.GOLD)
        for i,tier in enumerate(BOSSES[b['boss']][1]):
            self.put(ui.button(f'TIER {tier}',x1-rx,52,'wb' if b['tier']==tier else 'gray',20),rx,y0+34+i*60,
                     lambda t=tier:self.set_tier(t))
        self.label('DIFICULTAD',rx,y0+360,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,b['difficulty'],rx,y0+394,x1-rx,52,self.set_boss_difficulty,gap=8,size=20)
        self.label('SALA PRIVADA · REGROUP · UNA DERROTA NO DETIENE',x0,y1-20,14,ui.TEXT)

    def draw_raid(self):
        r=self.config_data['raid'];x0,y0,x1,y1=self.window('RAID',style='raid',art=ui.background(f"raid_{r['raid'].lower()}"),dim=.1)
        self.label('RAID (LA DE TU TIER)',x0,y0,20,ui.GOLD);lw=500;rx=x1-380
        for i,(key,name) in enumerate(RAIDS.items()):
            self.choice_row(x0,y0+34+i*58,lw,name.upper()[:24],r['raid']==key,lambda k=key:self.set_raid(k),h=50)
        self.label('DIFICULTAD',rx,y0,20,ui.GOLD)
        self.buttons(DIFFICULTY_COLORS,r['difficulty'],rx,y0+34,x1-rx,60,self.set_raid_difficulty,on='purple')
        for i,line in enumerate(('1 SHARD POR RUN','HASTA AGOTARLOS','UNA DERROTA NO DETIENE')):
            self.label(line,rx,y0+260+i*36,15,ui.TEXT)

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
        x0,y0,x1,y1=self.window('LOOT');totals=loot.load()
        self.put(self.resource('gold',44),x0,y0);self.label(f"ORO  {totals['gold']:,}",x0+64,y0+10,24,ui.GOLD)
        self.label(f"XP  {totals['xp']:,}",x0+420,y0+10,24,(140,232,110))
        self.label('OBJETOS',x0,y0+74,20,ui.GOLD);self.label('MATERIALES',x0+340,y0+74,20,ui.GOLD)
        self.label('FAMILIARES CAPTURADOS',x0+680,y0+74,20,ui.GOLD)
        for i,rarity in enumerate(RARITY_COLORS):
            y=y0+110+i*56;self.put(ui.row(320,48),x0,y)
            self.label(loot.RARITY_NAMES[rarity],x0+16,y+13,17,RARITY_COLORS[rarity]);self.label(str(totals['items'].get(rarity,0)),x0+260,y+13,17)
            self.put(ui.row(320,48),x0+340,y)
            self.label(loot.RARITY_NAMES[rarity],x0+356,y+13,17,RARITY_COLORS[rarity]);self.label(str(totals['materials'].get(rarity,0)),x0+600,y+13,17)
        fam=Image.open(ui.ICONS/'res/familiars.png').convert('RGBA').resize((44,45),Image.NEAREST)
        for i,(name,count) in enumerate(sorted(totals['familiars'].items())[:9]):
            y=y0+110+i*56;self.put(ui.row(x1-x0-680,48),x0+680,y);self.put(fam,x0+688,y+2)
            self.label(f'{name.upper()[:12]} x{count}',x0+740,y+13,17)
        if not totals['familiars']:self.label('NINGUNO TODAVIA',x0+680,y0+122,16,ui.DIM)
        for i,(mode,res) in enumerate(RESOURCE.items()):
            x=x0+i*((x1-x0)//6);self.put(self.resource(res,40),x,y1-60)
            self.label(str(totals['spent'].get(res,0)),x+52,y1-50,18)
        self.label('GASTADO EN ESTA SESION',x0,y1-96,16,ui.GOLD)
        self.put(ui.button('REINICIAR',200,50,'red',20),x1-200,y0,self.reset_loot)

    # --- acciones ---------------------------------------------------------------
    def on_click(self,event):
        for x0,y0,x1,y1,action in reversed(self.zones):
            if x0<=event.x<x1 and y0<=event.y<y1:action();self.render();return

    def save(self):
        farm_config.save(self.config_data)

    def go_main(self):self.screen='main'
    def open_loot(self):self.screen='loot'
    def reset_loot(self):loot.reset()
    def open_mode(self,mode):
        if self.process is None:self.screen=mode
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
        background=self.config_data['background'] or os.environ.get('FARM_BACKEND')=='gamescope'
        env={**os.environ,'FARM_BACKEND':'gamescope' if background else ''}
        self.save();self.status='EN MARCHA EN SEGUNDO PLANO · F8 DETIENE' if background else 'EN MARCHA · F8 DETIENE · NO CAMBIES DE VENTANA'
        self.process=subprocess.Popen([sys.executable,'-B','-u','-m','fishing_core.farm_all'],cwd=str(ROOT),env=env,
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
