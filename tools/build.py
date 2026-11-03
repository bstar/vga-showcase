#!/usr/bin/env python3
"""Build the real-mode DOS player and prepare the full GIF collection."""
import argparse,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'build';B.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--watcom',type=Path);a=p.parse_args();env=os.environ.copy()
if a.watcom:env.update(WATCOM=str(a.watcom.resolve()),INCLUDE=str(a.watcom.resolve()/'h'),PATH=str(a.watcom.resolve()/'binl64')+os.pathsep+env['PATH'])
subprocess.run([sys.executable,str(R/'tools/prepare.py')],cwd=R,env=env,check=True)
subprocess.run(['wcl','-q','-bt=dos','-0','-ms','-os','-k8192','-w4','-fe='+str(B/'VGADEMO/SHOWCASE.EXE'),str(R/'src/showcase.c')],cwd=B,env=env,check=True)
print(B/'VGADEMO/SHOWCASE.EXE')
