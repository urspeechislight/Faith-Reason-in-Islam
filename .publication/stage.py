"""Stage the exact inventory and bytes checked by the successful gate."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from public_files import snapshot

def stage(result_path,out):
    result=json.loads(Path(result_path).read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if result.get('status')!='passed' or result.get('commit')!=head:
        raise ValueError('No successful publication check for this commit')
    current=snapshot()
    if not current or current!=result.get('public_files'):
        raise ValueError('Public inventory or bytes changed after review')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for name in current:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(name,target)
    (out/'.nojekyll').touch()
if __name__=='__main__':stage(sys.argv[1],sys.argv[2])
