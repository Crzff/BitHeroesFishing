"""Recorta los marcos reales del juego (SETTINGS y RAID) de capturas de crzf para la app.

Uso: python scripts/build_ui_frames.py <captura_settings.png> <captura_raid.png>
Escribe assets/ui/frame/<estilo>.png (marco limpio con alfa), <estilo>_plaque.png
(placa sin texto) y frames.json (cortes del 9-slice y zonas). Se ejecuta una vez;
la app solo lee los PNG. Uso personal: arte del juego (ver THIRD_PARTY_NOTICES.md).
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

OUT=Path(__file__).resolve().parent.parent/'assets/ui/frame'


def components(mask,seed,box):
    """Región conexa (4-vecinos) de mask que contiene seed, limitada a box."""
    x0,y0,x1,y1=box;n,lab=cv2.connectedComponents(mask[y0:y1,x0:x1].astype(np.uint8),connectivity=4)
    out=np.zeros(mask.shape,bool);l=lab[seed[1]-y0,seed[0]-x0]
    if l:out[y0:y1,x0:x1]=lab==l
    return out


def grow(mask,px):
    return cv2.dilate(mask.astype(np.uint8),np.ones((2*px+1,2*px+1),np.uint8))>0


def build(f,spec):
    f=f.copy()
    H,W=f.shape[:2];hsv=cv2.cvtColor(f,cv2.COLOR_BGR2HSV);V=f.max(2).astype(int)
    hue,sat=hsv[:,:,0].astype(int),hsv[:,:,1].astype(int)
    x0,y0,x1,y1=spec['body'];body=np.zeros((H,W),np.uint8)
    cv2.fillPoly(body,[np.array(((x0+32,y0),(x1-32,y0),(x1,y0+32),(x1,y1-32),
                                (x1-32,y1),(x0+32,y1),(x0,y1-32),(x0,y0+32)))],1)
    keep=body>0
    poly=np.zeros((H,W),np.uint8);cv2.fillPoly(poly,[np.array(spec['plaque_poly'])],1);plaque=poly>0
    keep|=plaque
    core=components(V>=spec['outline_v'],spec['close_seed'],spec['close_box'])
    close=core|(grow(core,spec['outline_px'])&(V<spec['outline_v']))
    keep|=close
    cols=np.zeros((H,W),bool)
    for a,b in spec['chain_cols']:cols[:y0,a:b]=True
    chain=cols&(sat<spec['chain_sat'])&(V>spec['chain_v'])
    art=chain.copy()
    if spec.get('leaves'):
        green=(hue>=30)&(hue<=85)&(sat>80)&(V>60);zones=np.zeros((H,W),bool)
        for a,b,c,d in spec['leaves']:zones[b:d,a:c]=True
        art|=green&zones
    art|=grow(art,4)&(V<spec.get('art_outline_v',70))&(cols|(np.zeros((H,W),bool) if not spec.get('leaves') else zones))
    keep|=art
    keep=components(keep,(x0+20,y0+60),(0,0,W,H))  # descarta restos de fondo sueltos
    img0=f.copy()
    for a,b,src,flip in spec.get('chain_tile',()):  # tramo limpio de eslabones repetido hacia arriba
        r0,r1=spec['tile_rows'];seg=img0[r0:r1,src:src+b-a];alpha=sat[r0:r1,src:src+b-a]<90
        if flip:seg,alpha=seg[:,::-1],alpha[:,::-1]
        keep[:r1,a:b]=False
        for end in range(r1,0,-(r1-r0)):
            start=max(0,end-(r1-r0));s=seg[(r1-r0)-(end-start):],alpha[(r1-r0)-(end-start):]
            f[start:end,a:b][s[1]]=s[0][s[1]];keep[start:end,a:b]|=s[1]
    # Contenido de la ventana original: se repinta con el color del cuerpo de cada fila.
    cx0,cy0,cx1,cy1=spec['content'];sx0,sx1=spec['grad_cols']
    grad=np.median(f[:,sx0:sx1],axis=1).astype(np.uint8)
    zone=np.zeros((H,W),bool);zone[cy0:cy1,cx0:cx1]=True;zone&=~plaque
    if spec.get('keep_rust'):
        rust=((hue<=25)|(hue>=170))&(sat>55)&(V>70);corner=np.zeros((H,W),bool)
        for a,b,c,d in spec['keep_rust']:corner[b:d,a:c]=True
        zone&=~(rust&corner)
    img=f.copy()
    for a,b in spec.get('side_repairs',()):
        start,end=spec['repair_rows'];img[start:end,a:b]=img[spec['repair_y'],a:b]
    for y in range(cy0,cy1):img[y,zone[y]]=grad[y]
    tx0,ty0,tx1,ty1=spec['title_box']
    for y in range(ty0,ty1):img[y,tx0:tx1]=img[y,spec['title_fill_x']]
    rgba=np.dstack([img,np.where(keep,255,0).astype(np.uint8)])
    px0,py0,px1,py1=spec['plaque_box']
    layer=rgba[py0:py1,px0:px1].copy()
    plaque_keep=plaque|(grow(plaque,8)&(V<70))|(art&grow(plaque,35))
    layer[:,:,3]=np.where((keep&plaque_keep)[py0:py1,px0:px1],255,0)
    # La placa va aparte (centrada en la app): en el marco se sustituye por la columna limpia mx.
    mx=spec['cuts']['mx'];covered=rgba[py0:py1,px0:px1,3]>0
    for y in range(py0,py1):
        xs=np.nonzero(covered[y-py0])[0]+px0
        rgba[y,xs]=rgba[y,mx]
    return rgba,layer


SPECS={
    'settings':dict(body=(87,131,1241,970),plaque_poly=[(330,78),(996,78),(1056,137),(1056,172),(996,230),(330,230),(270,172),(270,137)],
                    outline_v=50,outline_px=7,close_seed=(1215,160),close_box=(1150,100,1290,230),
                    chain_cols=((115,175),(1158,1210)),chain_sat=50,chain_v=110,
                    leaves=((60,75,330,280),(990,75,1299,300),(60,885,180,985),(1140,885,1270,985)),
                    content=(150,240,1179,938),grad_cols=(141,150),keep_rust=((150,240,300,400),(1030,240,1179,400),(150,740,300,882),(1030,740,1179,882)),
                    title_box=(470,108,860,205),title_fill_x=400,title_y=153,plaque_box=(240,40,1100,240),
                    cuts=dict(left=250,right=1049,top=300,bottom=839,mx=250,my=600),interior=(120,164,1209,938),close=(1165,105,1270,215)),
    'raid':dict(body=(424,211,1496,994),plaque_poly=[(605,158),(1315,158),(1315,200),(1362,200),(1362,265),(1315,302),(605,302),(558,265),(558,200),(605,200)],
                outline_v=13,outline_px=6,close_seed=(1468,236),close_box=(1415,180,1525,295),
                chain_cols=(),chain_sat=0,chain_v=255,chain_tile=((456,510,456,False),(1410,1464,456,True)),tile_rows=(126,212),
                content=(493,327,1428,944),grad_cols=(484,492),side_repairs=((424,493),(1428,1496)),repair_rows=(327,928),repair_y=500,
                title_box=(850,185,1075,280),title_fill_x=700,title_y=232,plaque_box=(540,150,1380,320),
                cuts=dict(left=530,right=1390,top=450,bottom=850,mx=530,my=450),interior=(457,243,1463,961),close=(1420,185,1515,285)),
}


def main(settings_png,raid_png):
    OUT.mkdir(parents=True,exist_ok=True);meta={}
    for style,path in (('settings',settings_png),('raid',raid_png)):
        f=cv2.imread(str(path));spec=SPECS[style]
        rgba,plaque=build(f,spec)
        ys,xs=np.nonzero(rgba[:,:,3]);ox,oy,x1,y1=(int(v) for v in (max(0,xs.min()-4),max(0,ys.min()-4),min(f.shape[1],xs.max()+5),min(f.shape[0],ys.max()+5)))
        rgba=rgba[oy:y1,ox:x1];w,h=x1-ox,y1-oy;c=spec['cuts']
        shift=lambda box:[box[0]-ox,box[1]-oy,box[2]-ox,box[3]-oy]
        cv2.imwrite(str(OUT/f'{style}.png'),rgba);cv2.imwrite(str(OUT/f'{style}_plaque.png'),plaque)
        meta[style]={'size':[int(w),int(h)],'slice':{'L':int(c['left']-ox),'R':int(x1-c['right']),'T':int(c['top']-oy),'B':int(y1-c['bottom']),
                     'mx':int(c['mx']-ox),'my':int(c['my']-oy)},'body':shift(spec['body']),'interior':shift(spec['interior']),
                     'plaque_at':[int(spec['plaque_box'][0]-ox),int(spec['plaque_box'][1]-oy)],'title_y':int(spec['title_y']-oy),'close':shift(spec['close'])}
    (OUT/'frames.json').write_text(json.dumps(meta,indent=1)+'\n')


if __name__=='__main__':main(*sys.argv[1:3])
