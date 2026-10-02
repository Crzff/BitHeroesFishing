"""Deteccion contextual: franja superior de zona y componente 2D del pez.

No se proyectan juntos plantas, botones y casillas vecinas. Se conserva
diagnostico de candidatos rechazados; una ambiguedad no autoriza input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .vision import FrameView

ZONE_STRIP = (470, 741, 1445, 751)
FISH_ROI = (470, 751, 1445, 855)


@dataclass
class Detection:
    centro_pez: float
    centro_zona: float
    ancho_pez: float
    ancho_zona: float
    pez: tuple
    zona: tuple
    candidates: dict = field(default_factory=dict)


class Detector:
    def __init__(self):
        self.previous_zone = None
        self.previous_fish = None
        self.previous_time = None

    def reset(self):
        self.previous_zone = self.previous_fish = self.previous_time = None

    def detect(self, view: FrameView, now: float):
        strip = view.crop(ZONE_STRIP).astype(np.int16)
        image = view.crop(FISH_ROI).astype(np.int16)
        diagnostic = {"zones": [], "fish": [], "rejected": []}
        if not strip.size or not image.size:
            return None, {**diagnostic, "reason":"ROI_INCOMPLETA"}
        b,g,r = strip[:,:,0],strip[:,:,1],strip[:,:,2]
        mask = (g >= 145) & (g-r >= 35) & (g-b >= 35)
        scores = mask.sum(axis=0)
        xs = np.where(scores >= 6)[0]
        groups = np.split(xs, np.where(np.diff(xs)>3)[0]+1) if xs.size else []
        zones = []
        for group in groups:
            left,right = int(group[0])+470,int(group[-1])+470
            width = right-left+1
            center = (left+right)/2
            candidate = {"left":left,"right":right,"width":width,"center":center}
            diagnostic["zones"].append(candidate)
            if 20 <= width <= 110:
                zones.append(candidate)
            else:
                diagnostic["rejected"].append({**candidate,"type":"zone","reason":"ANCHO"})
        if not zones:
            return None, {**diagnostic,"reason":"SIN_ZONA_CENTRAL"}
        dt = now-self.previous_time if self.previous_time is not None else None
        continuity = dt is not None and 0 < dt <= .05
        if continuity:
            limit = 1200*dt+12
            zones = [z for z in zones if abs(z["center"]-self.previous_zone) <= limit]
        if len(zones) != 1:
            return None, {**diagnostic,"reason":"ZONA_AMBIGUA_O_SALTO"}
        zone = zones[0]

        b,g,r = image[:,:,0],image[:,:,1],image[:,:,2]
        orange = ((r >= 150) & (g >= 65) & (g <= 175) & (r-g >= 45) & (b <= 70)).astype(np.uint8)
        count, labels, stats, centers = cv2.connectedComponentsWithStats(orange, 8)
        fish = []
        for k in range(1,count):
            x,y,width,height,area = map(int,stats[k])
            candidate = {"left":x+470,"right":x+width-1+470,"top":y+751,
                         "width":width,"height":height,"area":area,
                         "center":float(centers[k,0])+470}
            if area < 30:
                continue
            diagnostic["fish"].append(candidate)
            if 25 <= width <= 120 and 40 <= height <= 104 and area >= max(400,width*height*.15):
                if not continuity or abs(candidate["center"]-self.previous_fish) <= 8000*dt+25:
                    fish.append(candidate)
                else:
                    diagnostic["rejected"].append({**candidate,"type":"fish","reason":"SALTO"})
            else:
                diagnostic["rejected"].append({**candidate,"type":"fish","reason":"FORMA_2D"})
        fish.sort(key=lambda p:p["area"],reverse=True)
        if not fish or len(fish)>1 and fish[0]["area"] < fish[1]["area"]*1.8:
            return None, {**diagnostic,"reason":"PEZ_AUSENTE_O_AMBIGUO"}
        selected = fish[0]
        self.previous_zone,self.previous_fish,self.previous_time = zone["center"],selected["center"],now
        # El margen interior se aplica al objeto correcto, no a una union de casillas.
        width_zone = max(1,zone["width"]-4)
        return Detection(selected["center"],zone["center"],float(selected["width"]),float(width_zone),
                         (selected["left"],selected["right"]),(zone["left"],zone["right"]),diagnostic), diagnostic
