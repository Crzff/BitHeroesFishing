"""Numeros de CAST, con fuente/escala propia y sin cantidades de cuenta fijas."""

from pathlib import Path

import cv2
import numpy as np

MIN_ROI=(275,775,390,840)
MAX_ROI=(1520,775,1640,840)
VALUE_ROI=(890,775,1025,840)
ASSETS=Path(__file__).resolve().parent.parent/"assets/cast_digits.npz"


class CastReader:
    def __init__(self,path=ASSETS):
        with np.load(path,allow_pickle=False) as data:
            self.refs={digit:[data[key].copy() for key in data.files if key.startswith(f"DIGIT_{digit}_")]
                       for digit in range(10)}

    def number(self,image):
        if image.size==0:
            return None,0.0
        mask=(image[:,:,:3].min(axis=2)>=210).astype(np.uint8)
        active=mask.any(axis=0)
        edges=np.diff(np.r_[False,active,False].astype(np.int8))
        bounds=list(zip(np.where(edges==1)[0],np.where(edges==-1)[0]))
        if not 1<=len(bounds)<=3:
            return None,0.0
        digits=[]
        scores=[]
        for x0,x1 in bounds:
            ys=np.where(mask[:,x0:x1].any(axis=1))[0]
            y0,y1=int(ys.min()),int(ys.max())+1
            if y0==0 or y1==mask.shape[0] or x0==0 or x1==mask.shape[1] or not 37<=y1-y0<=39:
                return None,0.0
            glyph=mask[y0:y1,x0:x1]
            candidates=[]
            for digit,variants in self.refs.items():
                best=0.0
                for ref in variants:
                    resized=cv2.resize(glyph,(ref.shape[1],ref.shape[0]),interpolation=cv2.INTER_NEAREST)
                    dice=2*float((resized*ref).sum())/max(1,resized.sum()+ref.sum())
                    score=dice-.25*abs(glyph.shape[1]/glyph.shape[0]-ref.shape[1]/ref.shape[0])
                    best=max(best,score)
                candidates.append((best,digit))
            candidates.sort(reverse=True)
            score,digit=candidates[0]
            if score<.92 or score-candidates[1][0]<.045:
                return None,float(score)
            digits.append(str(digit))
            scores.append(float(score))
        if len(digits)>1 and digits[0]=="0":
            return None,min(scores)
        return int("".join(digits)),min(scores)

    def measure(self,view):
        minimum,min_score=self.number(view.crop(MIN_ROI))
        maximum,max_score=self.number(view.crop(MAX_ROI))
        value,value_score=self.number(view.crop(VALUE_ROI))
        valid=(minimum is not None and maximum is not None and 0<minimum<maximum<=999
               and value is not None and minimum<=value<=maximum)
        return {"CAST_MIN":minimum,"CAST_MAX":maximum,"CAST_VALUE":value,
                "CAST_MIN_SCORE":min_score,"CAST_MAX_SCORE":max_score,"CAST_NUMBER":value_score,
                "CAST_RANGE_VALID":valid}
