"""Dibujo pixel al estilo de las ventanas de Bit Heroes (PIL); no envía input ni captura.

Fuente Silkscreen (OFL, assets/fonts). Iconos de modo recortados de capturas del
juego (assets/ui): uso personal, no son recursos MIT (ver THIRD_PARTY_NOTICES.md).
"""

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent.parent
FONT=ROOT/'assets/fonts/Silkscreen-Bold.ttf'
ICONS=ROOT/'assets/ui'

# Paleta tomada de la ventana SETTINGS del juego.
OUTLINE=(16,20,28)
FRAME=(184,196,208)
FRAME_LIGHT=(226,232,238)
FRAME_DARK=(122,136,152)
INNER=(46,61,79)
ROW=(36,49,63)
ROW_EDGE=(143,160,178)
TEXT=(255,255,255)
DIM=(150,166,184)
GOLD=(255,214,92)
COLORS={'blue':((47,167,214),(111,206,240),(26,110,150)),
        'orange':((240,138,36),(255,186,92),(170,86,16)),
        'green':((139,198,62),(186,232,108),(86,138,30)),
        'red':((216,45,45),(250,110,96),(150,24,24)),
        'gray':((92,106,122),(128,142,158),(60,72,86)),
        'purple':((168,44,160),(214,92,206),(112,20,106)),  # SUMMON de Raid
        'wb':((24,104,214),(78,152,240),(12,62,150))}  # SUMMON de World Boss


@lru_cache(maxsize=None)
def font(size):
    return ImageFont.truetype(str(FONT),size)


def text(label,size=24,color=TEXT,outline=OUTLINE,stroke=3):
    """Texto blanco con contorno oscuro grueso, sin suavizado (como el juego)."""
    f=font(size);probe=ImageDraw.Draw(Image.new('L',(1,1)))
    x0,y0,x1,y1=probe.textbbox((0,0),label,font=f,stroke_width=stroke)
    img=Image.new('RGBA',(x1-x0,y1-y0),(0,0,0,0));draw=ImageDraw.Draw(img);draw.fontmode='1'
    draw.text((-x0,-y0),label,font=f,fill=color,stroke_width=stroke,stroke_fill=outline)
    return img


def bevel(w,h,base,light,dark,border=OUTLINE,radius=3):
    """Bloque con borde negro, brillo arriba y sombra abajo (botones y filas)."""
    img=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(img)
    d.rounded_rectangle((0,0,w-1,h-1),radius=radius,fill=border)
    d.rounded_rectangle((3,3,w-4,h-4),radius=max(0,radius-2),fill=base)
    d.rectangle((6,4,w-7,7),fill=light)
    d.rectangle((6,h-8,w-7,h-5),fill=dark)
    return img


def button(label,w,h=64,color='blue',size=26):
    """Botón del juego (NEWS/SUMMON): contorno negro, franja clara arriba y oscura abajo."""
    base,light,dark=COLORS[color];img=Image.new('RGBA',(w,h),(0,0,0,0))
    bands(img,(0,0,w-1,h-1),OUTLINE,[light],[base],[dark],[base],base,px=5)
    t=text(label,size);img.alpha_composite(t,((w-t.width)//2,(h-t.height)//2))
    return img


def bands(img,box,outline,top,left,bottom,right,fill,px=4):
    """Bloque como los del juego: contorno y bandas interiores de px (luz/sombra por lado)."""
    d=ImageDraw.Draw(img);x0,y0,x1,y1=box
    d.rectangle(box,fill=outline);x0+=px;y0+=px;x1-=px;y1-=px
    for colors in zip(top,left,bottom,right):
        t,l,b,r=colors
        d.rectangle((x0,y0,x1,y1),fill=t);d.rectangle((x0,y0+px,x0+px-1,y1),fill=l)
        d.rectangle((x0+px,y1-px+1,x1,y1),fill=b);d.rectangle((x1-px+1,y0+px,x1,y1-px),fill=r)
        x0+=px;y0+=px;x1-=px;y1-=px
    d.rectangle((x0,y0,x1,y1),fill=fill)
    return img


def checkbox(checked,s=52):
    """Casilla de SETTINGS: negro, borde azul claro, negro, fondo oscuro; check verde."""
    img=Image.new('RGBA',(s,s),(0,0,0,0))
    bands(img,(0,0,s-1,s-1),(0,0,0),[(154,186,223),(0,0,0)],[(154,186,223),(0,0,0)],[(154,186,223),(0,0,0)],
          [(154,186,223),(0,0,0)],(28,33,40),px=max(3,s//13))
    if checked:
        d=ImageDraw.Draw(img);pts=[(s*.22,s*.52),(s*.42,s*.72),(s*.80,s*.26)]
        d.line(pts,fill=OUTLINE,width=13,joint='curve');d.line(pts,fill=(124,214,62),width=7,joint='curve')
    return img


def row(w,h):
    """Fila de SETTINGS (MUSIC/SOUND): borde claro con luz arriba, interior oscuro con degradado."""
    img=Image.new('RGBA',(w,h),(0,0,0,0))
    bands(img,(0,0,w-1,h-1),(0,0,0),[(238,241,249),(20,26,36)],[(209,217,224),(27,33,43)],
          [(144,151,158),(39,45,54)],[(209,217,224),(27,33,43)],(40,47,55),px=4)
    return img


def panel(w,h):
    """Panel oscuro del interior de SETTINGS: sombra arriba/izquierda, luz abajo."""
    img=Image.new('RGBA',(w,h),(0,0,0,0))
    return bands(img,(0,0,w-1,h-1),(22,34,40),[(22,30,42),(39,49,63)],[(42,52,64),(48,58,72)],
                 [(75,85,99),(59,69,83)],[(42,52,64),(48,58,72)],(53,63,75),px=5)


def art_panel(art,w,h,dim=0):
    """Panel negro de los carruseles (Raid/WB) con el arte recortado para cubrirlo."""
    img=Image.new('RGBA',(w,h),(0,0,0,0))
    bands(img,(0,0,w-1,h-1),(7,7,7),[(47,53,53),(40,43,50)],[(47,53,53),(40,43,50)],[(47,53,53),(40,43,50)],
          [(47,53,53),(40,43,50)],(0,0,0),px=5)
    iw,ih=w-30,h-30;wide=False  # ponytail: siempre cubre; el modo apaisado queda por si un arte no cabe
    scale=iw/art.width if wide else max(iw/art.width,ih/art.height)
    a=art.convert('RGBA').resize((round(art.width*scale),round(art.height*scale)),Image.NEAREST)  # arte pixelado
    a=a.crop(((a.width-iw)//2,(a.height-ih)//2 if not wide else 0,(a.width-iw)//2+iw,((a.height-ih)//2 if not wide else 0)+min(ih,a.height)))
    if dim:a=Image.blend(a,Image.new('RGBA',a.size,(0,0,0,255)),dim)
    if wide:  # arte apaisado arriba y fundido a negro, como la franja de texto del carrusel
        fade=Image.linear_gradient('L').resize((a.width,a.height//3));band=Image.new('RGBA',fade.size,(0,0,0,255));band.putalpha(fade)
        a.alpha_composite(band,(0,a.height-fade.height))
    img.alpha_composite(a,(15,15));return img


FRAME_SCALE=0.8  # el arte del juego mide ~6,5 px por píxel; la app es más pequeña que el juego


@lru_cache(maxsize=None)
def frame_art(style):
    meta=json.loads((ICONS/'frame/frames.json').read_text())[style];s=FRAME_SCALE
    def load(name):
        img=Image.open(ICONS/f'frame/{name}.png').convert('RGBA')
        return img.resize((round(img.width*s),round(img.height*s)),Image.NEAREST)
    return meta,load(style),load(style+'_plaque')


def frame_geometry(w,h,style='settings'):
    """Zonas del marco a tamaño (w,h): interior del cuerpo y botón X."""
    meta,_,_=frame_art(style);s=FRAME_SCALE;W0,H0=meta['size']
    x0,y0,x1,y1=meta['interior'];cx0,cy0,cx1,cy1=meta['close']
    return {'interior':(round(x0*s),round(y0*s),w-round((W0-x1)*s),h-round((H0-y1)*s)),
            'close':(w-round((W0-cx0)*s),round(cy0*s),w-round((W0-cx1)*s),round(cy1*s))}


def frame(w,h,title=None,style='settings'):
    """Marco real del juego (SETTINGS o RAID) en 9 piezas, con su placa y su X."""
    meta,art,plq=frame_art(style);s=FRAME_SCALE;sl={k:round(v*s) for k,v in meta['slice'].items()}
    L,R,T,B,mx,my=sl['L'],sl['R'],sl['T'],sl['B'],sl['mx'],sl['my'];aw,ah=art.size
    img=Image.new('RGBA',(w,h),(0,0,0,0))
    def piece(box,size,at):img.alpha_composite(art.crop(box).resize(size,Image.NEAREST),at)
    piece((0,0,L,T),(L,T),(0,0));piece((aw-R,0,aw,T),(R,T),(w-R,0))
    piece((0,ah-B,L,ah),(L,B),(0,h-B));piece((aw-R,ah-B,aw,ah),(R,B),(w-R,h-B))
    piece((mx,0,mx+1,T),(w-L-R,T),(L,0));piece((mx,ah-B,mx+1,ah),(w-L-R,B),(L,h-B))
    piece((0,my,L,my+1),(L,h-T-B),(0,T));piece((aw-R,my,aw,my+1),(R,h-T-B),(w-R,T))
    piece((mx,my,mx+1,my+1),(w-L-R,h-T-B),(L,T))
    if title:img.alpha_composite(*title_plaque(w,title,style))
    return img


def title_plaque(w,title,style='settings'):
    """(placa con el título, posición) centrada en un marco de ancho w; va encima del panel."""
    meta,_,plq=frame_art(style);s=FRAME_SCALE
    img=plq.copy();t=text(title,34,stroke=4);cy=round((meta['title_y']-meta['plaque_at'][1])*s)
    img.alpha_composite(t,((img.width-t.width)//2,cy-t.height//2))
    return img,((w-img.width)//2,round(meta['plaque_at'][1]*s))


def auto_button(active,w=150,h=150):
    """Botón START como el AUTO del juego: verde parado, rojo en marcha."""
    base,light,dark=COLORS['red' if active else 'green'];img=bevel(w,h,base,light,dark,radius=8)
    t=text('STOP' if active else 'START',30);img.alpha_composite(t,((w-t.width)//2,h//2-t.height-6))
    a=text('AUTO',22,color=(240,250,230));img.alpha_composite(a,((w-a.width)//2,h//2+10))
    return img


def loot_button(w=150,h=150):
    """Botón LOOT con el cofre del juego."""
    base,light,dark=COLORS['orange'];img=Image.new('RGBA',(w,h),(0,0,0,0))
    bands(img,(0,0,w-1,h-1),OUTLINE,[light],[base],[dark],[base],base,px=5)
    chest=Image.open(ICONS/'res/chest.png').convert('RGBA');chest=chest.resize((w-40,round(chest.height*(w-40)/chest.width)),Image.NEAREST)
    img.alpha_composite(chest,(round(w/2-visual_center(chest)),10));t=text('LOOT',28);img.alpha_composite(t,((w-t.width)//2,h-t.height-12))
    return img


@lru_cache(maxsize=None)
def icon(name,height=110):
    img=Image.open(ICONS/f'{name}.png').convert('RGBA');img=img.crop(img.getbbox())  # centrado real
    scale=height/img.height
    return img.resize((round(img.width*scale),height),Image.NEAREST)


def visual_center(img):
    """Centro horizontal del dibujo según su masa (no su caja): las rayas sueltas no lo desplazan."""
    import numpy as np
    a=np.asarray(img.getchannel('A'),dtype=float);cols=a.sum(0)
    return float((cols*np.arange(len(cols))).sum()/max(1.0,cols.sum()))


def dimmed(img,alpha=.35):
    img=img.copy();img.putalpha(img.getchannel('A').point(lambda a:int(a*alpha)));return img


@lru_cache(maxsize=None)
def background(name):
    """Fondo real del juego (assets/ui/bg): mapa de zona, carrusel de WB o de Raid."""
    path=ICONS/f'bg/{name}.jpg'
    return Image.open(path).convert('RGBA') if path.exists() else None


def loot_icon(path,rarity,color,size=58):
    """Icono guardado del LOOT RECAP con su borde de rareza."""
    img=Image.new('RGBA',(size,size),(0,0,0,0));ImageDraw.Draw(img).rectangle((0,0,size-1,size-1),fill=OUTLINE)
    ImageDraw.Draw(img).rectangle((2,2,size-3,size-3),fill=color)
    icon=Image.open(path).convert('RGBA').resize((size-8,size-8),Image.NEAREST);img.alpha_composite(icon,(4,4))
    return img


def arrow_button(w,h,up,active=True):
    """Botón de scroll con triángulo (la fuente no tiene flechas)."""
    img=button('',w,h,'blue' if active else 'gray');d=ImageDraw.Draw(img);cx,cy,s=w//2,h//2,w//4
    pts=[(cx-s,cy+s//2),(cx+s,cy+s//2),(cx,cy-s//2)] if up else [(cx-s,cy-s//2),(cx+s,cy-s//2),(cx,cy+s//2)]
    d.polygon(pts,fill=TEXT,outline=OUTLINE,width=3)
    return img
