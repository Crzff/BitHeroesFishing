"""Enlaces publicos opcionales. No procesa pagos ni inicia motores."""

import json
from pathlib import Path
import re


def support_url(root):
    try:
        data=json.loads((Path(root)/'project_links.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(data,dict):
        return None
    url=data.get('support')
    if isinstance(url,str) and re.fullmatch(r'https://ko-fi\.com/[A-Za-z0-9_\-]{1,60}',url):
        return url
    return None
