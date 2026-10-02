"""Integracion Steam simulada; IO/MSS falsos y ninguna captura privada."""

import contextlib
import io as streams
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import mss
import numpy as np

from fishing_core import runtime
from fishing_core.vision import Evidence


class SteamRuntimeTests(unittest.TestCase):
    def simulate(self,cycles=1,mode="normal"):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"fishing_runtime_config.json").write_text(json.dumps({"max_ciclos_por_sesion":cycles}))
            clock=[20_000_000_000]
            stage=[0]
            cast_start=[None]
            records=[]
            io=Mock()
            io.game_guard=SimpleNamespace(game=SimpleNamespace(client="Steam"))
            log=Mock()
            log.emit.side_effect=lambda event,**fields:records.append((event,fields))
            channel=SimpleNamespace(run_id="simulated",stop_path=root/"stop.json",
                request_path=root/"cycle.json",directory=root,signal=lambda:None,
                ready=lambda:{"run_id":"simulated","catch_pid":123})
            def ns():
                clock[0]+=1000
                return clock[0]
            def sleep(seconds):clock[0]+=round(seconds*1e9)
            def click(xy):
                if stage[0]%4==0:cast_start[0]=clock[0]
                stage[0]+=1
            io.click.side_effect=click
            io.cast_click.side_effect=click
            def emergency():
                if mode=="f8" and stage[0]==1:raise KeyboardInterrupt("F8")
            io.emergency.side_effect=emergency
            ui=Mock()
            ui.match.return_value=(0,None)
            ui.cast_reader.measure.return_value={}
            def classify(view):
                kind=("START","CAST","SUCCESS","ITEMS")[stage[0]%4]
                if kind!="CAST":return Evidence(kind,(960,970),True)
                phase=(clock[0]-cast_start[0])%800_000_000/800_000_000
                value=20+round(28*phase**3)
                return Evidence(kind,(960,970),value==48,scores={
                    "CAST_MIN":20,"CAST_MAX":48,"CAST_VALUE":value,"CAST_RANGE_VALID":True})
            ui.classify.side_effect=classify
            ui.cast_status.side_effect=classify
            def capture(sct,monitor):
                local=monitor==runtime.CAST_MONITOR
                clock[0]+=51_000_000 if mode=="slow" else 26_000_000 if local else 40_000_000
                # Las pruebas de navegacion prueban las etiquetas con escenas
                # sinteticas completas; aqui solo se prueba el flujo temporal.
                return np.zeros((1,1,4),np.uint8)
            error=None
            with patch.dict(runtime.os.environ,{"FISHING_CAST_DELAY_MS":"32",
                    "FISHING_CAST_OBSERVE_SECONDS":"0"},clear=True), \
                 patch.object(runtime,"ROOT",root),patch.object(mss,"mss"), \
                 patch.object(runtime,"capture",side_effect=capture), \
                 patch.object(runtime,"audit_baits",return_value=SimpleNamespace(total=100)) as audit, \
                 patch.object(runtime.time,"perf_counter_ns",side_effect=ns), \
                 patch.object(runtime.time,"perf_counter",side_effect=lambda:ns()/1e9), \
                 patch.object(runtime.time,"sleep",side_effect=sleep), \
                 contextlib.redirect_stdout(streams.StringIO()):
                try:runtime._control_loop(io,ui,channel,log,None)
                except (runtime.SafetyStop,KeyboardInterrupt) as exc:error=exc
            return stage[0],io,records,audit.call_count,error

    def test_frame_paced_steam_completes_and_confirms_one_closure(self):
        stage,io,records,audits,error=self.simulate()
        self.assertIsNone(error)
        self.assertEqual(stage,4)
        self.assertEqual(audits,1)
        io.cast_click.assert_called_once()
        inputs=[f for e,f in records if e=="CONTROL_INPUT_SENT"]
        self.assertEqual([f["purpose"] for f in inputs],["START","CAST","TRADE","ITEMS"])
        cast=next(f for f in inputs if f["purpose"]=="CAST")
        self.assertLessEqual(cast["fresh_age_ms"],80)
        self.assertLess(cast["full_cast_context_age_ms"],200)
        self.assertEqual(sum(e=="CYCLE_COMPLETE" for e,f in records),1)

    def test_three_cycles_do_not_recount_or_send_fourth_start(self):
        stage,io,records,audits,error=self.simulate(cycles=3)
        self.assertIsNone(error)
        self.assertEqual(stage,12)
        self.assertEqual(audits,1)
        self.assertEqual(io.cast_click.call_count,3)
        self.assertEqual([f["purpose"] for e,f in records if e=="CONTROL_INPUT_SENT"],
                         ["START","CAST","TRADE","ITEMS"]*3)
        self.assertEqual(sum(e=="CYCLE_COMPLETE" for e,f in records),3)

    def test_f8_during_wait_cast_cannot_send_or_debit_cast(self):
        stage,io,records,audits,error=self.simulate(mode="f8")
        self.assertIsInstance(error,KeyboardInterrupt)
        self.assertEqual(stage,1)
        io.cast_click.assert_not_called()
        self.assertFalse(any(e=="BAIT_BUDGET_UPDATED" for e,f in records))

    def test_slow_steam_captures_cannot_bypass_timing_guard(self):
        stage,io,records,audits,error=self.simulate(mode="slow")
        self.assertIsInstance(error,runtime.SafetyStop)
        self.assertEqual(stage,1)
        io.cast_click.assert_not_called()
        self.assertFalse(any(e=="BAIT_BUDGET_UPDATED" for e,f in records))
