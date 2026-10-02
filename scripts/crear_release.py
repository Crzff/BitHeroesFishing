"""ZIP de codigo con lista explicita. Nunca agrega .git, .venv, sesiones o logs."""

import hashlib
import argparse
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parent.parent
VERSION='v0.1.0-beta.1'
CORE=(
    '__init__.py','bait_budget.py','bait_inventory.py','bait_runtime.py','cast_audit.py',
    'cast_peak.py','cast_reader.py','cast_sampling.py','cast_test.py','catch_context.py',
    'catch_policy.py','control_flow.py','detector.py','offline_model.py','panel_safety.py',
    'panel_state.py','processes.py','project_links.py','protocol.py','result_closure.py',
    'runtime.py','session_watch.py','telemetry.py','vision.py',
)
TESTS=(
    'test_bait_budget.py','test_cast_audit.py','test_cast_peak.py','test_cast_reader.py',
    'test_cast_sampling.py','test_cast_test.py','test_catch_context.py','test_catch_policy.py',
    'test_control_flow.py','test_detector.py','test_gui_lifecycle.py','test_panel_preferences.py',
    'test_panel_safety.py','test_panel_state.py','test_predictor.py','test_processes.py',
    'test_project_links.py','test_protocol.py','test_session_watch.py','test_telemetry.py',
)
FILES=(
    'FISHING_BOT_APP.py','CATCH_FAST_PROCESS_V6_FINAL.py','FISHING_CONTROL_PROCESS.py',
    'README.md','LICENSE','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md','SECURITY.md',
    'CHANGELOG.md','RELEASE_NOTES.md','requirements.txt','project_links.json',
    'fishing_runtime_config.json','INSTALAR.bat','ABRIR_BOT.bat','COMPROBAR.bat',
    '.gitignore','.gitattributes','.github/FUNDING.yml',
    '.github/ISSUE_TEMPLATE/error.yml','.github/ISSUE_TEMPLATE/sugerencia.yml',
    '.github/ISSUE_TEMPLATE/config.yml','docs/ci-windows.example.yml',
    'assets/bait_templates.npz','assets/cast_digits.npz','assets/ui_templates.npz',
    'docs/INSTALACION.md','docs/FUNCIONAMIENTO.md','docs/FAQ.md','docs/VALIDACION.md',
    'docs/images/logo.png','docs/images/banner.png','docs/images/panel.png',
    'scripts/instalar.py','scripts/comprobar.py','scripts/crear_imagenes.py','scripts/crear_release.py',
)+tuple('fishing_core/'+name for name in CORE)+tuple('tests/'+name for name in TESTS)
PRIVATE=re.compile(r'C:[\\/]Users[\\/]Administrator|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY',re.I)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-unpublished',metavar='KNOWN_SHA256',
                        help='Reemplazar solo un ZIP local no publicado cuyo hash sea el indicado.')
    args=parser.parse_args()
    contents={}
    for name in FILES:
        path=ROOT/name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Archivo requerido ausente o enlace: '+name)
        data=path.read_bytes()
        if path.suffix in ('.py','.md','.json','.yml','.txt','.bat'):
            if PRIVATE.search(data.decode('utf-8-sig')):
                raise RuntimeError('Posible dato privado en '+name)
        if path.suffix=='.bat':
            data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        contents[name]=data
    manifest={'distribution':VERSION,'engine_profile':'AUDIT-R3.15','package_type':'PYTHON_SOURCE_NOT_PORTABLE_EXE',
              'private_sessions_included':False,'sha256':{name:hashlib.sha256(data).hexdigest() for name,data in contents.items()}}
    contents['PACKAGE_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    out=ROOT/'dist'
    out.mkdir(exist_ok=True)
    path=out/f'BitHeroesFishing-{VERSION}-source.zip'
    checksum_path=out/'SHA256SUMS.txt'
    if path.exists() or checksum_path.exists():
        known=args.replace_unpublished
        if (not known or not re.fullmatch('[a-f0-9]{64}',known) or not path.is_file()
                or not checksum_path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=known
                or checksum_path.read_text(encoding='utf-8').strip()!=f'{known}  {path.name}'):
            raise FileExistsError('No sobrescribir: falta el hash exacto de un paquete local no publicado.')
    elif args.replace_unpublished:
        raise FileNotFoundError('No hay un paquete existente que corresponda al hash indicado.')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(contents.items()):
            info=zipfile.ZipInfo('BitHeroesFishing/'+name,date_time=(2026,10,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'SHA256SUMS.txt').write_text(f'{checksum}  {path.name}\n',encoding='utf-8')
    print(json.dumps({'zip':path.name,'files':len(contents),'bytes':path.stat().st_size,'sha256':checksum},indent=2))


if __name__=='__main__':
    main()
