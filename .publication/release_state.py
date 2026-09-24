"""Preserve verified deployed bytes while leaving pre-migration failed edits unpublished.

These immutable commits were inspected during migration. The deployment is GitHub
Pages deployment 6621253632, successful run 35901364247. This is preservation of
existing public bytes, never a retrospective source/editorial approval.
"""
import hashlib
import json
from pathlib import Path
import subprocess
DEPLOYED='4c60f1d23f417fb52cbe6ad36b05468ff0f8e24d'
MIGRATION='a97290d4ddb6ec9a37d0785e3413609c5ba339f9'

def blob(commit,path):
    try:return subprocess.check_output(['git','show',commit+':'+path],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:return None

def check_registry():
    expected=blob(MIGRATION,'.publication/legacy.json')
    if expected is None or Path('.publication/legacy.json').read_bytes()!=expected:
        raise ValueError('legacy registry is immutable; changed article hashes cannot grant grandfathered approval')
    for commit in (DEPLOYED,MIGRATION):
        if subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],stderr=subprocess.DEVNULL).returncode:
            raise ValueError('migration provenance is not an ancestor of this checkout')

def preserved(path,dependencies):
    current=Path(path).read_bytes();deployed=blob(DEPLOYED,path)
    if deployed is not None and current==deployed:return {'status':'preserved-deployed','commit':DEPLOYED,'bytes':deployed}
    def exact(name):
        expected=blob(MIGRATION,name);actual=Path(name).read_bytes() if Path(name).is_file() else None
        return expected==actual
    if deployed is not None and current==blob(MIGRATION,path) and all(exact(n) for n in dependencies):
        return {'status':'held-unpublished-migration','commit':DEPLOYED,'bytes':deployed}
    return None
