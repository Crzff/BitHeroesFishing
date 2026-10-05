"""Dibujo pixel al estilo de las ventanas de Bit Heroes (PIL); no envía input ni captura.

Fuente Silkscreen (OFL, assets/fonts). Iconos de modo recortados de capturas del
juego (assets/ui): uso personal, no son recursos MIT (ver THIRD_PARTY_NOTICES.md).
"""

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
        'purple':((168,44,160),(214,92,206),(112,20,106))}  # SUMMON de Raid


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
    base,light,dark=COLORS[color];img=bevel(w,h,base,light,dark)
    t=text(label,size);img.alpha_composite(t,((w-t.width)//2,(h-t.height)//2))
    return img


def checkbox(checked,s=52):
    img=Image.new('RGBA',(s,s),(0,0,0,0));d=ImageDraw.Draw(img)
    d.rounded_rectangle((0,0,s-1,s-1),radius=6,fill=OUTLINE)
    d.rounded_rectangle((4,4,s-5,s-5),radius=4,fill=ROW_EDGE)
    d.rectangle((9,9,s-10,s-10),fill=ROW)
    if checked:  # check verde con contorno, como el de SETTINGS
        pts=[(s*.22,s*.52),(s*.42,s*.72),(s*.80,s*.26)]
        d.line(pts,fill=OUTLINE,width=13,joint='curve');d.line(pts,fill=(124,214,62),width=7,joint='curve')
    return img


def row(w,h):
    return bevel(w,h,ROW,(44,59,76),(28,38,50),border=ROW_EDGE,radius=2)


def frame(w,h,title=None):
    """Ventana con marco metálico, panel azul oscuro y placa de título."""
    img=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(img);top=70 if title else 0
    d.rounded_rectangle((0,top,w-1,h-1),radius=14,fill=OUTLINE)
    d.rounded_rectangle((4,top+4,w-5,h-5),radius=12,fill=FRAME)
    d.rounded_rectangle((8,top+8,w-9,top+14),radius=3,fill=FRAME_LIGHT)
    d.rounded_rectangle((26,top+(66 if title else 26),w-27,h-27),radius=8,fill=OUTLINE)
    d.rounded_rectangle((30,top+(70 if title else 30),w-31,h-31),radius=6,fill=INNER)
    for x,y in ((16,h-18),(w-18,h-18)):d.ellipse((x-5,y-5,x+5,y+5),fill=FRAME_DARK,outline=OUTLINE)
    rust(img,(10,top+18,w-10,top+24));rust(img,(10,h-24,w-10,h-14),seed=7)
    if title:
        p=plaque(title,min(w-120,max(320,text(title,40,stroke=4).width+140)));px=(w-p.width)//2
        for x in (px+28,px+p.width-48):img.alpha_composite(chain(44),(x,0))
        img.alpha_composite(p,(px,24))
        img.alpha_composite(leaves(),(px-34,top-6));img.alpha_composite(leaves(True),(px+p.width-36,top-6))
    img.alpha_composite(leaves(),(2,h-62));img.alpha_composite(leaves(True),(w-72,h-62))
    return img


def chain(h,link=18):
    """Cadena vertical de eslabones (como las que cuelgan las ventanas del juego)."""
    img=Image.new('RGBA',(20,h),(0,0,0,0));d=ImageDraw.Draw(img)
    for i,y in enumerate(range(0,h,link)):
        if i%2:d.rounded_rectangle((7,y,13,y+link+2),radius=3,fill=OUTLINE);d.line((10,y+3,10,y+link-1),fill=FRAME_LIGHT,width=2)
        else:d.rounded_rectangle((2,y,18,y+link+2),radius=6,outline=OUTLINE,width=4,fill=None);d.rounded_rectangle((4,y+2,16,y+link),radius=5,outline=FRAME,width=2)
    return img


def leaves(flip=False):
    """Hojas de enredadera pixeladas para las esquinas del marco."""
    img=Image.new('RGBA',(70,56),(0,0,0,0));d=ImageDraw.Draw(img)
    dark,mid,light=(36,92,30),(86,160,48),(150,214,86)
    d.line((6,50,62,12),fill=OUTLINE,width=5);d.line((6,50,62,12),fill=dark,width=3)
    for cx,cy,a,r in ((18,38,-1,12),(34,24,1,13),(50,28,-1,11),(28,46,1,9)):
        pts=[(cx-r,cy+a*r//3),(cx-r//3,cy-r//2),(cx+r,cy-a*r//3),(cx+r//3,cy+r//2)]
        d.polygon(pts,fill=OUTLINE)
        inner=[(x+(cx-x)*0.3,y+(cy-y)*0.3) for x,y in pts];d.polygon(inner,fill=mid)
        d.line((cx-r//2,cy+a*r//6,cx+r//2,cy-a*r//6),fill=light,width=2);d.point((cx+2,cy+3),fill=dark)
    return img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img


def rust(img,box,seed=3):
    """Manchas de óxido discretas sobre el metal del marco."""
    import random
    rnd=random.Random(seed);d=ImageDraw.Draw(img);x0,y0,x1,y1=box
    for _ in range(14):
        x=rnd.randint(x0,x1);y=rnd.randint(y0,y1);s=rnd.choice((3,4,6))
        d.rectangle((x,y,x+s,y+s//2),fill=(176,108,62));d.point((x+1,y),fill=(214,150,96))


def plaque(title,w,h=96):
    img=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(img)
    d.polygon([(18,0),(w-19,0),(w-1,h//2),(w-19,h-1),(18,h-1),(0,h//2)],fill=OUTLINE)
    d.polygon([(22,4),(w-23,4),(w-6,h//2),(w-23,h-5),(22,h-5),(5,h//2)],fill=FRAME_LIGHT)
    d.polygon([(30,12),(w-31,12),(w-18,h//2),(w-31,h-13),(30,h-13),(17,h//2)],fill=OUTLINE)
    d.polygon([(33,15),(w-34,15),(w-22,h//2),(w-34,h-16),(33,h-16),(21,h//2)],fill=(36,49,66))
    for x in (34,w-35):d.ellipse((x-6,h//2-6,x+6,h//2+6),fill=FRAME,outline=OUTLINE)
    t=text(title,40,stroke=4);img.alpha_composite(t,((w-t.width)//2,(h-t.height)//2))
    return img


def close_button(s=64):
    img=Image.new('RGBA',(s,s),(0,0,0,0));d=ImageDraw.Draw(img)
    d.ellipse((0,0,s-1,s-1),fill=OUTLINE);d.ellipse((4,4,s-5,s-5),fill=COLORS['red'][0])
    d.chord((8,6,s-9,s//2),180,360,fill=COLORS['red'][1])
    m=s*.3
    cross=(((m,m),(s-m,s-m)),((s-m,m),(m,s-m)))
    for a,b in cross:d.line([a,b],fill=OUTLINE,width=15)  # contornos primero, luego el blanco
    for a,b in cross:d.line([a,b],fill=TEXT,width=8)
    return img


def auto_button(active,w=150,h=150):
    """Botón START como el AUTO del juego: verde parado, rojo en marcha."""
    base,light,dark=COLORS['red' if active else 'green'];img=bevel(w,h,base,light,dark,radius=8)
    t=text('STOP' if active else 'START',30);img.alpha_composite(t,((w-t.width)//2,h//2-t.height-6))
    a=text('AUTO',22,color=(240,250,230));img.alpha_composite(a,((w-a.width)//2,h//2+10))
    return img


@lru_cache(maxsize=None)
def icon(name,height=110):
    img=Image.open(ICONS/f'{name}.png').convert('RGBA')
    scale=height/img.height
    return img.resize((round(img.width*scale),height),Image.NEAREST)


def dimmed(img,alpha=.35):
    img=img.copy();img.putalpha(img.getchannel('A').point(lambda a:int(a*alpha)));return img
