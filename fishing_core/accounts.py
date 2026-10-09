"""Identidad de cuenta por proceso. Importar no crea perfiles ni inicia clientes."""

import os
import stat
from pathlib import Path
import re
import json
import tempfile
import unicodedata
from collections.abc import Mapping

ROOT=Path(__file__).resolve().parent.parent
DEFAULT_ACCOUNTS=[{'id':'steam','name':'Steam','type':'steam'},
                  {'id':'personal','name':'FMANI','type':'browser'},
                  {'id':'perfil-1','name':'KORTZZ','type':'browser'}]


def secure_dir(path):
    """Directorio privado POSIX; DACL exclusiva pendiente de la fase Windows."""
    if os.name=='nt':return
    path=Path(path)
    if path.is_symlink():raise ValueError('Directorio enlazado')
    if os.name!='nt':os.chmod(path,0o700)


def secure_file(path):
    """Archivo privado POSIX; DACL exclusiva pendiente de la fase Windows."""
    if os.name=='nt':return
    path=Path(path)
    if path.is_symlink():raise ValueError('Archivo enlazado')
    if os.name!='nt':os.chmod(path,0o600)


def private_directory(path):
    path=Path(path)
    if path.is_symlink():raise ValueError('Directorio enlazado')
    if any(parent.is_symlink() for parent in path.parents):raise ValueError('Padre enlazado')
    if not path.exists():
        if not path.parent.exists():private_directory(path.parent)
        path.mkdir(mode=0o700,exist_ok=True)
    secure_dir(path)
    parents=list(path.parents)
    runs=next((i for i,parent in enumerate(parents) if parent.name=='runs'),None)
    if runs is not None:
        for parent in parents[:runs+1]:secure_dir(parent)


def private_file(path,mode='a',**kwargs):
    path=Path(path)
    if path.is_symlink() or path.parent.is_symlink():raise ValueError('Archivo o padre enlazado')
    flags=os.O_WRONLY|os.O_CREAT|getattr(os,'O_NOFOLLOW',0)
    flags|=os.O_EXCL if mode=='x' else os.O_APPEND if mode=='a' else os.O_TRUNC
    fd=os.open(path,flags,0o600)
    try:
        if os.name!='nt':os.fchmod(fd,0o600)
        secure_file(path)
        stream=os.fdopen(fd,mode,encoding='utf-8',**kwargs)
    except BaseException:
        os.close(fd);raise
    return stream


def _validate(records):
    if type(records) is not list or len(records)>8:raise ValueError('Registro de cuentas inválido')
    ids=set();steam=0
    for record in records:
        if type(record) is not dict or set(record)!={'id','name','type'}:raise ValueError('Cuenta inválida')
        ident,name,kind=record['id'],record['name'],record['type']
        if type(ident) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,31}',ident) or ident in ids or \
                type(name) is not str or not 1<=len(name)<=24 or not name.isprintable() or \
                kind not in ('steam','browser'):raise ValueError('Cuenta inválida')
        ids.add(ident);steam+=kind=='steam'
    if steam>1:raise ValueError('Solo se permite una cuenta Steam')
    return [dict(record) for record in records]


def load_accounts():
    path=ROOT/'runs/accounts/accounts.json'
    if path.is_symlink():raise ValueError('Registro de cuentas enlazado')
    try:
        with path.open(encoding='utf-8') as stream:return _validate(json.load(stream))
    except FileNotFoundError:return _validate(DEFAULT_ACCOUNTS)


def save_accounts(records):
    records=_validate(records);path=ROOT/'runs/accounts/accounts.json'
    private_directory(path.parent)
    if path.is_symlink():raise ValueError('Registro de cuentas enlazado')
    temporary=None
    try:
        fd,temporary=tempfile.mkstemp(prefix='.accounts-',dir=path.parent)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            secure_file(temporary)
            json.dump(records,stream,ensure_ascii=False,indent=2);stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path);temporary=None
    finally:
        if temporary is not None:Path(temporary).unlink()


def account_names():return {record['id']:record['name'] for record in load_accounts()}


def browser_accounts():return [record['id'] for record in load_accounts() if record['type']=='browser']


def steam_account():return next((record['id'] for record in load_accounts() if record['type']=='steam'),None)


def add_account(name,type):
    records=load_accounts()
    if not isinstance(name,str):raise ValueError('Nombre inválido')
    base=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower()).strip('-')[:32] or 'cuenta'
    ident=base;number=2;ids={record['id'] for record in records}
    while ident in ids:
        suffix=f'-{number}';ident=base[:32-len(suffix)]+suffix;number+=1
    save_accounts(records+[{'id':ident,'name':name,'type':type}])
    return ident


def remove_account(id):
    records=load_accounts()
    if id not in {record['id'] for record in records}:raise ValueError('Cuenta desconocida')
    save_accounts([record for record in records if record['id']!=id])


class _AccountNames(Mapping):
    """Vista compatible para consumidores antiguos; nunca almacena el registro."""
    def __getitem__(self,key):return account_names()[key]
    def __iter__(self):return iter(account_names())
    def __len__(self):return len(account_names())


NAMES=_AccountNames()


def account_id(env=None):
    env=os.environ if env is None else env
    account=env.get('FARM_ACCOUNT')
    if account is not None and account not in account_names():
        raise ValueError('FARM_ACCOUNT debe estar en el registro de cuentas')
    if account is not None and os.name=='nt' and env.get('FARM_BACKEND')!='cdp':
        raise ValueError('Multicuenta Windows requiere CDP')
    return account


def state_root(root,env=None):
    account=account_id(env)
    return Path(root)/'runs/accounts'/account if account else Path(root)


def runs_root(root,env=None):
    return state_root(root,env) if account_id(env) else Path(root)/'runs'


def mutex_role(role):
    account=account_id()
    # Steam es la misma cuenta en ambos modos: conservar su exclusividad antigua.
    return f'{role}-{account}' if account is not None and account!=steam_account() else role


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


def validate_cdp_endpoint(endpoint):
    if type(endpoint) is not str:raise ValueError('Endpoint CDP inválido')
    if os.name=='nt':
        if not re.fullmatch(r'\\\\\.\\pipe\\bitheroes-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',endpoint):
            raise ValueError('Pipe CDP inválido')
        return endpoint
    path=Path(endpoint);runs=ROOT/'runs'
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(runs) or path.parent==runs:
        raise ValueError('Endpoint CDP fuera de runs')
    try:
        for part in (path,*path.parents):
            if part.is_symlink():raise ValueError('Endpoint CDP enlazado')
        info=path.lstat();directory=path.parent.stat()
        if not stat.S_ISSOCK(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.getuid() or \
                stat.S_IMODE(directory.st_mode)!=0o700 or directory.st_uid!=os.getuid():raise ValueError
    except OSError:raise ValueError('Endpoint CDP ausente') from None
    return endpoint


def brave_target(env=None):
    env=os.environ if env is None else env
    if account_id(env) not in browser_accounts():return None
    pid=env.get('FARM_BRAVE_PID','');port=env.get('FARM_BRAVE_CDP_PORT','');target=env.get('FARM_BRAVE_TARGET_ID','')
    endpoint=env.get('FARM_BRAVE_CDP_ENDPOINT','')
    if ('FARM_BRAVE_CDP_PORT' in env)==('FARM_BRAVE_CDP_ENDPOINT' in env) or \
            not re.fullmatch(r'[1-9][0-9]{0,9}',pid) or int(pid)>2**31-1 or \
            not re.fullmatch(r'[0-9A-Fa-f]{32}',target):
        raise ValueError('Brave requiere PID, puerto CDP local y target explícitos por cuenta')
    if 'FARM_BRAVE_CDP_ENDPOINT' in env:return int(pid),validate_cdp_endpoint(endpoint),target
    if not re.fullmatch(r'[1-9][0-9]{0,4}',port) or int(port)>65535:raise ValueError('Puerto CDP inválido')
    return int(pid),int(port),target


def prepare_profiles(root):
    """Solo directorios de datos nuevos. No leer ni copiar el navegador personal."""
    root=Path(root).resolve();profiles={}
    for account in browser_accounts():
        path=root
        for part in ('runs','accounts',account,'brave-data'):
            path=path/part
            if path.is_symlink():raise ValueError('No se preparan perfiles a través de enlaces simbólicos')
            path.mkdir(mode=0o700,exist_ok=True)
            if os.name!='nt' and part in (account,'brave-data') and (path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077):
                raise ValueError('El directorio del perfil debe ser privado y pertenecer al usuario')
            secure_dir(path)
        profiles[account]=path
    return profiles
