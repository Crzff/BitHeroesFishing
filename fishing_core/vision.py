"""Identidad de pantallas/botones, no decision temporal de CATCH.

Coordenadas para la interfaz comprobada en 1920x1080. Ante una imagen
desconocida se devuelve UNKNOWN: nunca se sustituye texto por color lima.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from .cast_reader import CastReader,MIN_ROI,MAX_ROI,VALUE_ROI

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "ui_templates.npz"
BAIT_ASSETS = ASSETS.with_name("bait_templates.npz")
BUTTON_ROI = (830, 910, 1090, 1020)
PCT_ROI = (1535, 779, 1705, 833)
CAST_NUMBER_ROI = (910, 775, 1005, 840)


@dataclass
class Evidence:
    kind: str = "UNKNOWN"
    xy: tuple | None = None
    ready: bool = False
    percentage: int | None = None
    scores: dict = field(default_factory=dict)


class FrameView:
    def __init__(self, image: np.ndarray, left: int = 0, top: int = 0):
        self.image = image
        self.left = left
        self.top = top

    def crop(self, rect):
        x0, y0, x1, y1 = rect
        x0, x1 = x0-self.left, x1-self.left
        y0, y1 = y0-self.top, y1-self.top
        if x0 < 0 or y0 < 0 or x1 > self.image.shape[1] or y1 > self.image.shape[0]:
            return np.empty((0, 0, 3), dtype=np.uint8)
        return self.image[y0:y1, x0:x1, :3]


class UIClassifier:
    def __init__(self, asset_path: Path = ASSETS):
        self.cast_reader=CastReader()
        self.cast_range=None
        with np.load(asset_path, allow_pickle=False) as data:
            self.templates = {k: data[k].astype(np.float32) for k in data.files}
        with np.load(BAIT_ASSETS, allow_pickle=False) as data:
            for key in ("SELECT_MENU", "SELECT_X"):
                self.templates[key] = data[key].astype(np.float32)

    def match(self, view: FrameView, name: str, roi, threshold: float = .92):
        image = view.crop(roi)
        template = self.templates[name]
        if image.size == 0 or image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
            return 0.0, None
        mask = (image.min(axis=2) >= 210).astype(np.float32)
        if np.count_nonzero(mask) < template.sum() * .85:
            return 0.0, None
        scores = cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, pos = cv2.minMaxLoc(scores)
        if score < threshold:
            return float(score), None
        x, y = pos
        patch = mask[y:y+template.shape[0], x:x+template.shape[1]]
        intersection = float((patch * template).sum())
        dice = 2 * intersection / max(1, patch.sum() + template.sum())
        if dice < .90:
            return min(float(score), .89), None
        return float(score), (int(roi[0]+x+template.shape[1]/2), int(roi[1]+y+template.shape[0]/2))

    def percentage(self, view: FrameView):
        image = view.crop(PCT_ROI)
        if not image.size:
            return None, 0.0
        mask = (image.max(axis=2) >= 220).astype(np.uint8)
        ys, xs = np.where(mask)
        if len(xs) < 80:
            return None, 0.0
        glyph = mask[ys.min():ys.max()+1, xs.min():xs.max()+1]
        candidates = []
        for value in (0, 25, 50, 75, 100):
            ref = self.templates[f"PCT_{value}"][3:-3, 3:-3]
            resized = cv2.resize(glyph, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST)
            dice = 2 * float((resized * ref).sum()) / max(1, resized.sum() + ref.sum())
            penalty = .3 * (abs(glyph.shape[1]-ref.shape[1])/max(glyph.shape[1], ref.shape[1])
                            + abs(glyph.shape[0]-ref.shape[0])/max(glyph.shape[0], ref.shape[0]))
            candidates.append((dice-penalty, value))
        score, value = max(candidates)
        return (value if score >= .90 else None), float(score)

    def catch_status(self, view: FrameView) -> Evidence:
        pct, pct_score = self.percentage(view)
        score, xy = self.match(view, "CATCH", BUTTON_ROI)
        # Ambos indicadores deben pertenecer a la misma captura.
        kind = "CATCH_ACTIVE" if xy and pct is not None else "CATCH_PENDING" if pct is not None else "UNKNOWN"
        return Evidence(kind, xy, bool(xy), pct, {"CATCH": score, "percentage": pct_score})

    def _cast_evidence(self, view: FrameView, score, xy) -> Evidence:
        scores = {"CAST": score, "CAST_NUMBER": 0.0, "CAST_VALUE": None}
        if not xy:
            return Evidence(scores=scores)
        if view.crop(MIN_ROI).size and view.crop(MAX_ROI).size:
            measured=self.cast_reader.measure(view)
            minimum,maximum=measured["CAST_MIN"],measured["CAST_MAX"]
            self.cast_range=({k:measured[k] for k in ("CAST_MIN","CAST_MAX","CAST_MIN_SCORE","CAST_MAX_SCORE")}
                             if minimum is not None and maximum is not None and 0<minimum<maximum<=999 else None)
        else:
            value,number_score=self.cast_reader.number(view.crop(VALUE_ROI))
            measured={**(self.cast_range or {}),"CAST_VALUE":value,"CAST_NUMBER":number_score}
        scores.update(measured)
        minimum,maximum=scores.get("CAST_MIN"),scores.get("CAST_MAX")
        value=scores.get("CAST_VALUE")
        valid=(minimum is not None and maximum is not None and value is not None and minimum<=value<=maximum)
        scores["CAST_RANGE_VALID"]=valid
        scores["CAST_TARGET_MODE"]="DYNAMIC_MAXIMUM_REFERENCE"
        scores["CAST_AT_DISPLAYED_MAXIMUM"]=valid and value==maximum
        ready=valid and value==maximum
        return Evidence("CAST", xy, ready, scores=scores)

    def cast_status(self, view: FrameView) -> Evidence:
        """Revalidacion CAST: maximo leido de los limites de la barra actual.

        Solo se usa despues de una clasificacion completa de la pantalla;
        no decide resultados ni autoriza el clic del minijuego.
        """
        score, xy = self.match(view, "CAST", BUTTON_ROI)
        return self._cast_evidence(view, score, xy)

    def classify(self, view: FrameView) -> Evidence:
        menu = self.menu_status(view)
        if menu.kind == "SELECT_MENU":
            return menu
        scores = {}
        failed, _ = self.match(view, "FAILED", (780, 210, 1140, 550))
        items, _ = self.match(view, "ITEMS", (800, 210, 1120, 460))
        success, _ = self.match(view, "SUCCESS", (700, 110, 1220, 240))
        scores.update(FAILED=failed, ITEMS=items, SUCCESS=success)
        if failed >= .92:
            score, xy = self.match(view, "CLOSE", (810, 640, 1110, 1000))
            scores["CLOSE"] = score
            return Evidence("FAILED", xy, xy is not None, scores=scores)
        if items >= .92:
            score, xy = self.match(view, "ITEMS_X", (1270, 200, 1400, 500))
            scores["ITEMS_X"] = score
            if xy:
                a = view.crop((xy[0]-40, xy[1]-40, xy[0]+40, xy[1]+40)).astype(np.int16)
                if not a.size or np.count_nonzero((a[:,:,2] > 150) & (a[:,:,2] > a[:,:,1]+70)) < 300:
                    xy = None
            return Evidence("ITEMS", xy, xy is not None, scores=scores)
        if success >= .92:
            score, xy = self.match(view, "TRADE", BUTTON_ROI)
            scores["TRADE"] = score
            return Evidence("SUCCESS", xy, xy is not None, scores=scores)
        catch = self.catch_status(view)
        if catch.kind != "UNKNOWN":
            catch.scores.update(scores)
            return catch
        cast, xy_cast = self.match(view, "CAST", BUTTON_ROI)
        start, xy_start = self.match(view, "START", BUTTON_ROI)
        scores.update(CAST=cast, START=start)
        if xy_cast:
            evidence = self._cast_evidence(view, cast, xy_cast)
            evidence.scores.update(scores)
            return evidence
        if xy_start:
            return Evidence("START", xy_start, True, scores=scores)
        return Evidence(scores=scores)

    def menu_status(self, view: FrameView) -> Evidence:
        score, title = self.match(view, "SELECT_MENU", (780, 240, 1130, 350))
        close_score, xy = self.match(view, "SELECT_X", (1290, 245, 1400, 360))
        if title:
            return Evidence("SELECT_MENU", xy, xy is not None, scores={"SELECT": score, "SELECT_X": close_score})
        return Evidence()
