"""Regresion del 9 junto al brillo de Hooked Spoon; solo 81x40 pixels del juego."""

import base64
import unittest

import cv2
import numpy as np

from fishing_core.bait_inventory import BaitReader


# Recorte de la cantidad, sin inventario completo ni datos de la cuenta.
NINE = (
    "iVBORw0KGgoAAAANSUhEUgAAAFEAAAAoCAYAAACGohY/AAADQElEQVR4nO2azU8TQRjGn9mPfgjGKAfQQ0UIIRwxMZ7hSDg0IQiXJnAxsRcTrlwE/wFDCLE37iQc1GCaGDx4kXDqQWK8oBeLGi5Q2rJlZ8wsbEtxB7dlWzrb/SWbbmd2ZjfPzvu+szMvCUXvMQQIMQo/HcuTL2j5XBE3D3CLBokJ6YCuMyik/j4oBYwSQemkDUWMhIGOqDeeKBxiyOUJjFJ97aU0Z8JFDHnnygm5Wn/SjURFAVR+qJWy6enpuvo6ODjAxsZGuV9NA0wTYMzHIkYjQDTMrJFznuHhYSQSiZr7W1xcLJ/zl3Krk1k+snBMUDx2349GzSJkIBJWcSPS+HfORyT3tabpPthI4xNDenMfVdf8aM6kcjo6Oor5+fny/+7u7rq6nJmZweTkpHVuGAaSySR2d3fParljJD4T8QJDQ0O4KrFYDF4gjTm3MtKORBGpVApra2vC+rm5OYyNjcFLNGoW0Czoh991t2VLz4HP7/97XS6Xw87OjrC+WPR+NhKYswcEInqA73xiPB7HyMiIsL6vr8/ze/pOxP7+/qbfMzDnlozOHw+FVSur3xzLn60+FLbp6blr/RK+6nD2AZHJZDA+Pl6+ZnZ2FhMTE7gupDTn/f1967CZmpq61ueRxpwZYzWv8zULqUYiO6eipugw2elaVT6fRzqddtXH4OAgent721dEjq2jTqIw2an/XVhYgFuWl5c9F1Eac77I/Y5HaBWkG4k2j28noEDF9/w2DHpULmeobKrbUGaiNUUUTGVevRZ//N+JdV06jXFiby/rWH749HRSXTSBglnZtUp//VN13a+SipXsTTQSaUeiTUTlR2UFukOtDuGdtPEhXVqf2EoEInpAIKIHBCI2PLBcspggisI9ggjMyXyytyOr+fHyibCNHYUv8vaLc95gYqt6m1NTgS7xI3mC9NG5VtbX163DiWzWeTqFdhfRpDwlhELlWVAANjc3XbWj1H3So+99ImMMR/nadvh4nmLRcH+970cip1AwrNEYDkf/ySjjEFL54uGJTLUI2DYicgzjBCemc5qXol5NBt+bczPQ6l1MEE1l4gNLwjbxAedyY/udsI1oKvPmgWBatCVOIWkUfwEp2O36G68+fQAAAABJRU5ErkJggg=="
)


class BaitInventoryTests(unittest.TestCase):
    def image(self):
        return cv2.imdecode(np.frombuffer(base64.b64decode(NINE),np.uint8),cv2.IMREAD_COLOR)

    def test_nine_with_adjacent_colored_icon_is_not_a_merged_glyph(self):
        image=self.image()
        self.assertIsNotNone(image)
        quantity,score,source=BaitReader().quantity(image)
        self.assertEqual(quantity,9)
        self.assertGreaterEqual(score,.86)
        self.assertEqual(source,"DIGITS")

    def test_neutral_noise_and_cropped_digits_still_reject_inventory(self):
        image=self.image()
        self.assertIsNotNone(image)
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        neutral=cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)
        self.assertIsNone(BaitReader().quantity(neutral)[0])
        self.assertIsNone(BaitReader().quantity(image[6:33])[0])

    def test_icon_fragment_separated_from_eight_is_not_an_extra_digit(self):
        image=self.image()
        reader=BaitReader()
        eight=reader.templates["DIGIT_8"]
        image[5:34,45:68]=0  # Contorno neutro, como el numero observado en el juego.
        image[6:33,46:46+eight.shape[1]]=np.where(eight[:,:,None],255,0)
        # El 8 tapa parte del icono y deja cuatro columnas entre ambos.
        image[19:32,42:45]=(255,80,20)
        quantity,score,source=reader.quantity(image)
        self.assertEqual(quantity,8)
        self.assertGreaterEqual(score,.86)
        self.assertEqual(source,"DIGITS")


if __name__=="__main__":
    unittest.main()
