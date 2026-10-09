"""Dibujo PIL offline, sin Tk ni pantalla."""
import unittest
from unittest.mock import patch
from PIL import Image
from fishing_core import pixel_ui as ui

class PixelUITests(unittest.TestCase):
    def test_weekly_art_and_fallback(self):
        for mode,name in ui.WEEKLY.items():
            with Image.open(ui.ICONS/f'{name.lower()}.png') as art:
                alpha=art.getchannel('A');box=alpha.getbbox()
                self.assertTrue(0<box[0]<box[2]<art.width)
                self.assertTrue(0<box[1]<box[3]<art.height)
                self.assertEqual(alpha.getpixel((0,0)),0)
            ui.icon.cache_clear()
            self.assertEqual(ui.icon(mode,120).height,120)
            with patch.object(ui,'WEEKLY',{}):
                ui.icon.cache_clear();original=ui.icon(mode,120).copy()
            with patch.object(ui,'WEEKLY',{mode:'MISSING_WEEKLY'}):
                ui.icon.cache_clear();self.assertEqual(ui.icon(mode,120).tobytes(),original.tobytes())
        ui.icon.cache_clear()

    def test_loot_chest_visual_center(self):
        captured=[]
        composite=Image.Image.alpha_composite
        def record(img,art,dest=(0,0),source=(0,0)):
            captured.append((art.copy(),dest));return composite(img,art,dest,source)
        for width in (150,190):
            captured.clear()
            with patch.object(Image.Image,'alpha_composite',record):ui.loot_button(width)
            chest,(x,y)=captured[0]
            self.assertLessEqual(abs(x+ui.visual_center(chest)-width/2),.5)
