"""Copy only tracked public assets into the Pages artifact after gate success."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
result=json.loads(Path(sys.argv[1]).read_text())
if result.get('status')!='passed':raise SystemExit('No successful publication check')
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
allowed={'.html','.htm','.css','.js','.json','.svg','.png','.jpg','.jpeg','.webp','.ico','.woff','.woff2','.ttf','.pdf','.txt','.xml'}
for name in subprocess.check_output(['git','ls-files','-z']).decode().strip('\0').split('\0'):
 p=Path(name)
 if any(part.startswith('.') for part in p.parts) or p.suffix.lower() not in allowed:continue
 if p.is_symlink():raise SystemExit('Symlink in public assets: '+name)
 dest=out/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
(out/'.nojekyll').touch()
