"""Lectura pura de inventario: no selecciona, compra ni consume cebos."""

from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .vision import FrameView

BAIT_SLOT_XY = (1120, 815)
ASSETS = Path(__file__).resolve().parent.parent / "assets/bait_templates.npz"
RARITIES = ("normal", "raro", "epico", "legendario")


@dataclass(frozen=True)
class BaitStack:
    slot: int
    name: str
    rarity: str
    quantity: int
    quantity_source: str
    score: float


@dataclass
class Inventory:
    reliable: bool
    reason: str
    stacks: tuple = ()
    diagnostic: dict = field(default_factory=dict)

    @property
    def total(self):
        return sum(s.quantity for s in self.stacks) if self.reliable else None

    @property
    def signature(self):
        return tuple((s.slot, s.name, s.rarity, s.quantity) for s in self.stacks)

    def payload(self):
        return {"reliable": self.reliable, "reason": self.reason, "total": self.total,
                "estimated_fishing_attempts": self.total, "one_bait_per_attempt_is_estimate": True,
                "stacks": [asdict(s) for s in self.stacks]}


def quantity_boxes(mask):
    """Separa glifos por columnas, no por conectividad de sus trazos.

    El 4 real puede contener un trazo aislado de un pixel de ancho. Sigue
    siendo parte del mismo glifo: no se elimina ni se lee como otro digito.
    Un fragmento en una columna separada conserva su caja y se rechaza.
    """
    active=mask.any(axis=0)
    edges=np.diff(np.r_[False,active,False].astype(np.int8))
    boxes=[]
    for x0,x1 in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
        ys=np.where(mask[:,x0:x1].any(axis=1))[0]
        y0,y1=int(ys[0]),int(ys[-1])+1
        boxes.append((int(x0),y0,int(x1-x0),y1-y0,int(mask[y0:y1,x0:x1].sum())))
    return boxes


def quantity_mask(image):
    """Conserva los digitos y separa fragmentos blancos del icono de fondo.

    Solo excluye componentes cortos, con halo fuertemente coloreado, que
    invaden la parte inferior de un glifo alto con contorno neutro. No
    descarta ruido neutro, trazos sueltos del 4 ni componentes truncados.
    Sin glifo alto de referencia no excluye nada ni fabrica un singleton.
    """
    mask=(image.min(axis=2)>=210).astype(np.uint8)
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    if count>32:
        return mask,()
    chroma=image.max(axis=2).astype(np.int16)-image.min(axis=2).astype(np.int16)>35
    parts=[]
    for index in range(1,count):
        x,y,w,h,area=(int(v) for v in stats[index])
        component=(labels==index).astype(np.uint8)
        halo=(cv2.dilate(component,np.ones((3,3),np.uint8))>0)&(component==0)
        colored=float(chroma[halo].mean()) if halo.any() else 0.0
        parts.append((index,(x,y,w,h,area),colored))
    anchors=[box for _,box,colored in parts if 20<=box[3]<=32 and box[4]>=12 and colored<=.05
             and box[0]>0 and box[1]>0 and box[0]+box[2]<mask.shape[1] and box[1]+box[3]<mask.shape[0]]
    ignored=[]
    for index,box,colored in parts:
        x,y,w,h,area=box
        if not (3<=h<20 and area>=12 and colored>=.35 and x>0 and y>0
                and x+w<mask.shape[1] and y+h<mask.shape[0]):
            continue
        overlaps=any(max(0,min(x+w,ax+aw)-max(x,ax))>=.8*w and y>=ay+ah//3
                     and y+h<=ay+ah for ax,ay,aw,ah,_ in anchors)
        if overlaps:
            mask[labels==index]=0
            ignored.append(box)
    return mask,tuple(ignored)


def glyph_holes(glyph):
    """Cuenta huecos cerrados robustos, sin rellenar ni alterar la tinta.

    Un hueco diminuto/estrecho no sirve para desempatar. La zona exterior
    queda conectada al borde del padding y no cuenta como hueco.
    """
    background=1-np.pad(glyph.astype(np.uint8),1)
    _,_,stats,_=cv2.connectedComponentsWithStats(background,connectivity=4)
    holes=[]
    for x,y,w,h,area in stats[1:]:
        if x==0 or y==0 or x+w==background.shape[1] or y+h==background.shape[0]:
            continue
        if area<12 or w<3 or h<3:
            return None
        holes.append((x,y,w,h,area))
    return len(holes) if len(holes)<=2 else None


def choose_digit(candidates,observed_holes,structures):
    """Nunca promueve otro digito ni baja los filtros de score/margen.

    Si se parecen en pixeles, solo compara rivales estructuralmente posibles.
    El ganador original debe tener la estructura observada; de lo contrario
    se rechaza incluso si el segundo candidato parece compatible.
    """
    ordered=sorted(candidates,reverse=True)
    score,value=ordered[0]
    raw_margin=score-ordered[1][0]
    compatible=[c for c in ordered if observed_holes is not None and observed_holes in structures[c[1]]]
    structure_margin=(score-(compatible[1][0] if len(compatible)>1 else 0.0)
                      if compatible and compatible[0][1]==value else None)
    detail={"best_digit":value,"best_score":float(score),"raw_margin":float(raw_margin),
            "observed_holes":observed_holes,"structure_margin":structure_margin,
            "structure_tiebreak":False,
            "candidates":[{"digit":v,"score":float(s),"template_holes":structures[v]} for s,v in ordered]}
    mismatch=(observed_holes is not None and structures[value] and observed_holes not in structures[value])
    if score<.86 or mismatch:
        return None,float(score),detail
    if raw_margin<.045:
        if structure_margin is None or structure_margin<.045:
            return None,float(score),detail
        detail["structure_tiebreak"]=True
    return value,float(score),detail


class BaitReader:
    def __init__(self, path=ASSETS):
        with np.load(path, allow_pickle=False) as data:
            self.templates = {k: data[k] for k in data.files}
        # Misma altura de la fuente del inventario; evita reescalar el observado
        # arriba/abajo contra referencias del porcentaje de distinto tamano.
        for key in tuple(self.templates):
            if not key.startswith("DIGIT_"):
                continue
            ref = self.templates[key]
            self.templates[key] = cv2.resize(ref, (max(1, round(ref.shape[1]*27/ref.shape[0])), 27),
                                             interpolation=cv2.INTER_NEAREST)
        self.digit_holes={value:tuple(sorted({holes for key,ref in self.templates.items()
                                            if key==f"DIGIT_{value}" or key.startswith(f"DIGIT_{value}_")
                                            if (holes:=glyph_holes(ref)) is not None}))
                          for value in range(10)}

    def quantity(self, image, diagnostic=None):
        if not image.size:
            return None, 0.0, "QUANTITY_UNREADABLE"
        if not np.any(image.min(axis=2)>=210):
            return 1, 1.0, "SINGLETON_NO_DIGITS"
        mask,ignored = quantity_mask(image)
        components = quantity_boxes(mask)
        if not components:
            return None, 0.0, "QUANTITY_UNREADABLE"
        # No se descartan caracteres truncados o ruido para convertirlos en 1.
        if len(components) > 6 or any(area < 12 or h < 20 or h > 32 or y == 0 or y+h >= mask.shape[0]
                                      or x == 0 or x+w >= mask.shape[1]
                                      for x, y, w, h, area in components):
            return None, 0.0, "QUANTITY_UNREADABLE"
        values = []
        scores = []
        details=[]
        if diagnostic is not None:
            diagnostic["glyph_diagnostics"]=details
        for x, y, w, h, area in components:
            glyph = mask[y:y+h, x:x+w]
            candidates = []
            for value in range(10):
                variants = [ref for key, ref in self.templates.items()
                            if key == f"DIGIT_{value}" or key.startswith(f"DIGIT_{value}_")]
                variant_scores = []
                for ref in variants:
                    resized = cv2.resize(glyph, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST)
                    dice = 2*float((resized*ref).sum())/max(1, resized.sum()+ref.sum())
                    penalty = .25*abs(w/h-ref.shape[1]/ref.shape[0])
                    variant_scores.append(dice-penalty)
                candidates.append((max(variant_scores), value))
            value,score,detail=choose_digit(candidates,glyph_holes(glyph),self.digit_holes)
            details.append({"box":[x,y,w,h,area],**detail})
            if value is None:
                return None, float(score), "QUANTITY_AMBIGUOUS"
            values.append(str(value))
            scores.append(float(score))
        text = "".join(values)
        if len(text) > 1 and text[0] == "0":
            return None, min(scores), "QUANTITY_LEADING_ZERO"
        return int(text), min(scores), "DIGITS"

    def read(self, view: FrameView):
        # La barra completa es evidencia de que no hay otra pagina oculta.
        rail = view.crop((1256, 448, 1278, 654))
        if not rail.size:
            return Inventory(False, "INVENTORY_CROPPED")
        grey = rail.max(axis=2)-rail.min(axis=2) < 10
        bright = rail.mean(axis=2) > 85
        if float((grey & bright).mean()) < .95:
            return Inventory(False, "INVENTORY_REQUIRES_SCROLL_OR_OCCLUDED")
        stacks = []
        for row in range(2):
            for col in range(4):
                x, y = 638+154*col, 410+154*row
                card = view.crop((x, y, x+136, y+136))
                if not card.size:
                    return Inventory(False, "INVENTORY_CROPPED")
                # Un lugar vacio debe ser uniforme; una tarjeta incompleta nunca es cero.
                if float(card.std(axis=(0, 1)).max()) < 3 and 35 < float(card.mean()) < 100:
                    continue
                ring = np.concatenate((card[3:8, 10:124].reshape(-1, 3),
                                       card[10:124, 3:8].reshape(-1, 3),
                                       card[125:130, 10:124].reshape(-1, 3),
                                       card[10:124, 125:130].reshape(-1, 3)))
                hsv = cv2.cvtColor(ring[None, :, :], cv2.COLOR_BGR2HSV)[0]
                active = (hsv[:, 1] > 80) & (hsv[:, 2] > 130)
                if float(active.mean()) < .85:
                    return Inventory(False, "CARD_BORDER_UNKNOWN")
                hue = float(np.median(hsv[active, 0]))
                rarity = "epico" if hue < 12 or hue > 165 else "legendario" if hue < 36 else "normal" if hue < 85 else "raro"
                quantity_detail={}
                quantity, score, source = self.quantity(card[15:55, 45:126],quantity_detail)
                if quantity is None:
                    quantity_image=card[15:55,45:126]
                    mask,ignored=quantity_mask(quantity_image)
                    boxes=quantity_boxes(mask)
                    return Inventory(False, source, diagnostic={"slot":row*4+col,"quantity_score":score,
                                     "quantity_roi":[x+45,y+15,x+126,y+55],"glyph_boxes":boxes,
                                     "background_fragments_excluded":ignored,**quantity_detail})
                icon = card[56:116, 18:114]
                if float(icon.std()) < 12:
                    return Inventory(False, "ITEM_ICON_MISSING")
                matches = [(float(cv2.matchTemplate(icon, ref, cv2.TM_CCOEFF_NORMED)[0, 0]), key[5:])
                           for key, ref in self.templates.items() if key.startswith("ICON_")]
                icon_score, name = max(matches)
                if icon_score < .94:
                    name = f"Cebo {rarity} ({row*4+col+1})"
                stacks.append(BaitStack(row*4+col, name, rarity, quantity, source, score))
        return Inventory(True, "FULL_VISIBLE_INVENTORY", tuple(stacks))
