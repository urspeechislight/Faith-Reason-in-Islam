"""Stage only the release tree produced and hashed by the complete publication gate."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from public_files import snapshot,digest

def stage(result_path,out):
    result_path=Path(result_path);result=json.loads(result_path.read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if result.get('status')!='passed' or result.get('mode')!='publication' or result.get('commit')!=head:
        raise ValueError('No successful full publication check for this commit')
    if snapshot()!=result.get('input_files'):raise ValueError('Working public bytes changed after review')
    source=result_path.parent/'checked-site';expected=result.get('public_files',{})
    names={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if names!=set(expected):raise ValueError('Checked release inventory changed')
    for name,want in expected.items():
        path=source/name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or digest(path.read_bytes())!=want:
            raise ValueError('Checked release bytes changed: '+name)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for name in expected:
        raw=(source/name).read_bytes()
        if digest(raw)!=expected[name]:raise ValueError('Checked release changed during staging: '+name)
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if any(digest((out/name).read_bytes())!=want for name,want in expected.items()):raise ValueError('Staged output changed during copy')
    (out/'.nojekyll').touch()
if __name__=='__main__':stage(sys.argv[1],sys.argv[2])
