"""Identidad de cuenta por proceso. Importar no crea perfiles ni inicia clientes."""

import os
from pathlib import Path
import re

NAMES={'personal':'Personal','perfil-1':'Perfil 1','steam':'Steam'}


def account_id(env=None):
    env=os.environ if env is None else env
    account=env.get('FARM_ACCOUNT')
    if account is not None and account not in NAMES:
        raise ValueError('FARM_ACCOUNT debe ser personal, perfil-1 o steam')
    if account is not None and os.name=='nt':raise ValueError('Multicuenta requiere Linux/gamescope')
    return account


def state_root(root,env=None):
    account=account_id(env)
    return Path(root)/'runs/accounts'/account if account else Path(root)


def runs_root(root,env=None):
    return state_root(root,env) if account_id(env) else Path(root)/'runs'


def mutex_role(role):
    account=account_id()
    # Steam es la misma cuenta en ambos modos: conservar su exclusividad antigua.
    return f'{role}-{account}' if account not in (None,'steam') else role


def shm_path(env=None):
    account=account_id(env)
    base='/dev/shm/bitheroes-gamescope-frame'
    if account is None:return base
    if (os.environ if env is None else env).get('FARM_BACKEND')=='cdp':
        if brave_target(env) is None:raise ValueError('CDP requiere una cuenta de navegador')
        return f'{base}-{os.getuid()}-{account}-cdp'
    display,serial=gamescope_target(env)
    return f'{base}-{os.getuid()}-{account}-X{display[1:].replace(".","_")}-{serial}'


def gamescope_target(env=None):
    env=os.environ if env is None else env
    if account_id(env) is None:return None
    display=env.get('FARM_GAMESCOPE_DISPLAY','')
    serial=env.get('FARM_GAMESCOPE_SERIAL','')
    if env.get('FARM_BACKEND')!='gamescope' or not re.fullmatch(r':[0-9]{1,5}(?:\.0)?',display) or \
            not re.fullmatch(r'[1-9][0-9]{0,19}',serial) or int(serial)>2**64-1:
        raise ValueError('Multicuenta requiere gamescope y FARM_GAMESCOPE_DISPLAY / FARM_GAMESCOPE_SERIAL explícitos')
    return display,serial


def brave_target(env=None):
    env=os.environ if env is None else env
    if account_id(env) not in ('personal','perfil-1'):return None
    pid=env.get('FARM_BRAVE_PID','');port=env.get('FARM_BRAVE_CDP_PORT','');target=env.get('FARM_BRAVE_TARGET_ID','')
    if not re.fullmatch(r'[1-9][0-9]{0,9}',pid) or int(pid)>2**31-1 or \
            not re.fullmatch(r'[1-9][0-9]{0,4}',port) or int(port)>65535 or \
            not re.fullmatch(r'[0-9A-Fa-f]{32}',target):
        raise ValueError('Brave requiere PID, puerto CDP local y target explícitos por cuenta')
    return int(pid),int(port),target


def prepare_profiles(root):
    """Solo directorios de datos nuevos. No leer ni copiar el navegador personal."""
    if os.name=='nt':raise ValueError('Perfiles multicuenta todavía no certificados en Windows')
    root=Path(root).resolve();profiles={}
    for account in ('personal','perfil-1'):
        path=root
        for part in ('runs','accounts',account,'brave-data'):
            path=path/part
            if path.is_symlink():raise ValueError('No se preparan perfiles a través de enlaces simbólicos')
            path.mkdir(mode=0o700,exist_ok=True)
            if part in (account,'brave-data') and (path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077):
                raise ValueError('El directorio del perfil debe ser privado y pertenecer al usuario')
        profiles[account]=path
    return profiles
