"""Cadena de modos: pausa si el usuario usa el ordenador, un reintento y reanudación tras START."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fishing_core import farm_all
from fishing_core.control_flow import SafetyStop


class RunStepsTests(unittest.TestCase):
    def run_chain(self,plan,progress,waits=True):
        results=[]
        with patch.object(farm_all,'steps',return_value=plan),patch.object(farm_all,'PROGRESS',progress), \
                patch.object(farm_all,'wait_for_game_focus',return_value=waits) as focus:
            farm_all.run_steps({},results,False,lambda m:False,lambda:False,{})
        return results,focus

    def failing(self,*errors):
        calls=[];errors=list(errors)
        def step():
            calls.append(1)
            if errors:raise errors.pop(0)
        return step,calls

    def test_focus_loss_pauses_and_the_same_mode_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            quest,calls=self.failing(SafetyStop('Steam perdio el foco o cambio su identidad en niri; no se envia input'))
            results,focus=self.run_chain([('Quest',quest),('PvP',lambda:None)],Path(tmp)/'p.json')
            self.assertEqual(results,[('Quest','OK'),('PvP','OK')]);self.assertEqual(len(calls),2);focus.assert_called_once()
            self.assertFalse((Path(tmp)/'p.json').exists())  # ciclo completo: el próximo START empieza de nuevo

    def test_other_stops_are_retried_once_and_then_the_next_start_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress=Path(tmp)/'p.json';ran=[]
            raid,calls=self.failing(SafetyStop('Pantalla no confirmada'),SafetyStop('Pantalla no confirmada'))
            results,_=self.run_chain([('Quest',lambda:ran.append('Quest')),('Raid',raid),('Trials',lambda:ran.append('Trials'))],progress)
            self.assertEqual(results,[('Quest','OK'),('Raid','Pantalla no confirmada')]);self.assertEqual(len(calls),2)
            results,_=self.run_chain([('Quest',lambda:ran.append('Quest')),('Raid',lambda:None),('Trials',lambda:ran.append('Trials'))],progress)
            self.assertEqual(results[0],('Quest','OK (ya hecho)'));self.assertEqual(ran,['Quest','Trials'])


    def test_reaching_the_one_hour_session_limit_opens_another_session_without_using_the_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            limit=SafetyStop('Límite de sesión: 60 minutos')
            raid,calls=self.failing(limit,limit,limit,SafetyStop('Pantalla no confirmada'))
            results,_=self.run_chain([('Raid',raid)],Path(tmp)/'p.json')
            self.assertEqual(results,[('Raid','OK')]);self.assertEqual(len(calls),5)  # 3 sesiones más + 1 reintento


if __name__=='__main__':unittest.main()
