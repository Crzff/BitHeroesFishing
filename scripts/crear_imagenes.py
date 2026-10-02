"""Marca propia, dibujada con formas; no usa graficos ni capturas del juego."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent.parent


def font(size,bold=False):
    for name in (('segoeuib.ttf' if bold else 'segoeui.ttf'),
                 ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')):
        try:
            return ImageFont.truetype(name,size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def logo():
    image=Image.new('RGB',(1024,1024),'#101010')
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((92,92,932,932),radius=180,outline='#424242',width=6)
    draw.ellipse((626,220,702,296),outline='#ededed',width=18)
    draw.line((664,296,664,597),fill='#ededed',width=20)
    draw.arc((360,445,664,748),0,180,fill='#ededed',width=20)
    draw.line((360,596,360,486),fill='#ededed',width=20)
    draw.polygon(((350,486),(402,548),(350,530)),fill='#ededed')
    for x,y in ((292,296),(702,386),(256,684)):
        draw.rectangle((x,y,x+18,y+18),fill='#676767')
    return image.resize((512,512),Image.Resampling.LANCZOS)


def main():
    out=ROOT/'docs/images'
    out.mkdir(parents=True,exist_ok=True)
    icon=logo()
    icon.save(out/'logo.png')
    banner=Image.new('RGB',(1600,500),'#101010')
    draw=ImageDraw.Draw(banner)
    for y in (376,402,428,454):
        for x in range(-20,1640,80):
            draw.line((x,y,x+40,y,x+40,y+12,x+80,y+12),fill='#282828',width=3)
    banner.paste(icon.resize((270,270),Image.Resampling.LANCZOS),(110,84))
    draw.text((425,155),'BIT HEROES',font=font(68,True),fill='#ededed')
    draw.text((425,240),'FISHING BOT',font=font(68,True),fill='#ededed')
    draw.text((428,330),'Fmani  /  Windows  /  Beta',font=font(27),fill='#a3a3a3')
    banner.save(out/'banner.png')


if __name__=='__main__':
    main()
