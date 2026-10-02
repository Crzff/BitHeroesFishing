"""Carga por AST solamente el predictor real, excluyendo captura/input/main."""

import ast
import sys
import types
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Deque, List, Optional, Tuple

import numpy as np

MODEL = Path(__file__).resolve().parent.parent / "CATCH_FAST_PROCESS_V6_FINAL.py"


def load_model():
    allowed = {"ConfigV6", "Obs", "Ajuste", "Decision", "TrackerBarra", "solape_fraccion",
               "solape_maximo", "tolerancia_px", "theil_sen", "mad", "decidir", "actualizar_latencia_click"}
    tree = ast.parse(MODEL.read_text(encoding="utf-8-sig"))
    selected = [n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in allowed]
    if {n.name for n in selected} != allowed:
        raise ValueError("Faltan definiciones del predictor")
    module = types.ModuleType("_fishing_offline_predictor")
    module.__dict__.update(dataclass=dataclass,deque=deque,median=median,np=np,
                           Deque=Deque,List=List,Optional=Optional,Tuple=Tuple)
    sys.modules[module.__name__]=module
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(MODEL),"exec"),module.__dict__)
    return module
