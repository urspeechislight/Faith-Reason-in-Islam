#!/usr/bin/env python3
"""Inspect one exact GitHub run and its typed artifact; never infer from a glob."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time


def gh(*args):return json.loads(subprocess.check_output(['gh',*args],text=True))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=int,required=True);p.add_argument('--commit',required=True);p.add_argument('--repo',default='urspeechislight/Faith-Reason-in-Islam');p.add_argument('--output',type=Path,required=True);p.add_argument('--wait-seconds',type=int,default=0);a=p.parse_args(argv)
    if not 0<=a.wait_seconds<=60:p.error('--wait-seconds must be 0–60; return control between bounded waits')
    try:
        deadline=time.monotonic()+a.wait_seconds
        while True:
            run=gh('api',f'repos/{a.repo}/actions/runs/{a.run}')
            if run['head_sha']!=a.commit:raise ValueError('run belongs to a different head commit')
            if run['status']=='completed' or time.monotonic()>=deadline:break
            print('CI',run['status'],'run',a.run,flush=True);time.sleep(min(5,max(0,deadline-time.monotonic())))
        jobs=gh('api',f'repos/{a.repo}/actions/runs/{a.run}/attempts/{run["run_attempt"]}/jobs?per_page=100')['jobs']
        result={'schema':1,'run_id':a.run,'attempt':run['run_attempt'],'head_sha':run['head_sha'],'status':run['status'],'conclusion':run.get('conclusion'),'url':run['html_url'],'failed_steps':[{'job':j['name'],'step':s['name']} for j in jobs for s in j.get('steps',[]) if s.get('conclusion')=='failure']}
        if run['status']=='completed':
            artifacts=gh('api',f'repos/{a.repo}/actions/runs/{a.run}/artifacts?per_page=100')['artifacts']
            available={x['name'] for x in artifacts if not x.get('expired')}
            for phase,prefix in [('article','article-release'),('regression','reviewer-regression')]:
                name=f'{prefix}-{a.run}-{run["run_attempt"]}'
                if name not in available:continue
                dest=a.output/f'{a.run}-{run["run_attempt"]}'/phase
                if not dest.exists():
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with tempfile.TemporaryDirectory(prefix='.download-',dir=dest.parent) as temp:
                        subprocess.run(['gh','run','download',str(a.run),'--repo',a.repo,'--name',name,'--dir',temp],check=True)
                        Path(temp).rename(dest)
                report=dest/'result.json'
                if report.is_file():
                    data=json.loads(report.read_text())
                    if data.get('phase')!=phase:raise ValueError('artifact phase mismatch: '+str(report))
                    result[phase]={'report':str(report.resolve()),'result':data}
        a.output.mkdir(parents=True,exist_ok=True);(a.output/'status.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        return 2 if run['status']!='completed' else (0 if run.get('conclusion')=='success' else 1)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
