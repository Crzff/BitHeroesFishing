"""Retención limitada a directorios de sesión y registros de texto."""
import os
import re
import shutil
import time
from pathlib import Path

from .accounts import private_file

RUN_ID=re.compile(r'\d{8}_\d{6}_[0-9a-f]{12}\Z')
PROTECTED={'brave-data','configs','sessions','accounts','enabled','boost_purchases','loot_totals'}


def prune_runs(root,now=None,max_age=7*86400,max_bytes=2*1024**3):
    runs=Path(root)/'runs';now=time.time() if now is None else now
    if runs.is_symlink() or not runs.is_dir():return []
    parents=[runs];accounts=runs/'accounts'
    if accounts.is_dir() and not accounts.is_symlink():
        parents += [p for p in accounts.iterdir() if p.name not in PROTECTED and p.is_dir() and not p.is_symlink()]
    sessions=[]
    for parent in parents:
        for path in parent.iterdir():
            if not RUN_ID.fullmatch(path.name) or path.is_symlink() or not path.is_dir():continue
            try:stamp=path.stat().st_mtime
            except OSError:continue  # Otra cuenta puede estar podando la misma sesión.
            size=0
            for directory,dirs,files in os.walk(path,followlinks=False):
                dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink()]
                for name in files:
                    file=Path(directory)/name
                    if file.is_symlink():continue
                    try:stat=file.stat()
                    except OSError:continue
                    size+=stat.st_size;stamp=max(stamp,stat.st_mtime)
            sessions.append((stamp,path,size))
    total=sum(s for _,_,s in sessions);removed=[]
    for stamp,path,size in sorted(sessions):
        if now-stamp<=max_age and total<=max_bytes:continue
        try:shutil.rmtree(path)
        except OSError:continue
        total-=size;removed.append(path)
    return removed


class RotatingLog:
    def __init__(self,path,max_bytes=5*1024**2,**kwargs):
        self.path=Path(path);self.max_bytes=max_bytes;self.kwargs=kwargs
        self.stream=private_file(self.path,'a',**kwargs)

    def write(self,text):
        self.stream.flush()
        if self.path.stat().st_size+len(text.encode('utf-8'))>self.max_bytes:
            self.stream.close();self.path.replace(self.path.with_name(self.path.name+'.1'))
            self.stream=private_file(self.path,'a',**self.kwargs)
        # Incluso una línea anormalmente grande queda acotada.
        text=text.encode('utf-8')[:self.max_bytes].decode('utf-8',errors='ignore')
        return self.stream.write(text)

    def flush(self):self.stream.flush()
    def close(self):self.stream.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
