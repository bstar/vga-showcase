#!/usr/bin/env python3
"""Build, package, and exercise the shipped files in DOSBox-X."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[1];B=R/'build';p=argparse.ArgumentParser();p.add_argument('--no-build',action='store_true');a=p.parse_args()
if not a.no_build:subprocess.run([sys.executable,str(R/'tools/build.py')],cwd=R,check=True)
subprocess.run([sys.executable,str(R/'tools/package.py')],cwd=R,check=True)
archive=R/'dist/VGADEMO.ZIP';assert hashlib.sha256(archive.read_bytes()).hexdigest()==(R/'dist/SHA256.TXT').read_text().split()[0]
slides=json.loads((B/'manifest.json').read_text());assert len(slides)==32
for s in slides:assert hashlib.sha256((B/'VGADEMO/GIFS'/(s['dos_name']+'.GIF')).read_bytes()).hexdigest()==s['sha256']
subprocess.run(['wcl','-q','-bt=dos','-0','-ms','-os','-k8192','-fe=DISPLAY.EXE',str(R/'tests/display.c')],cwd=B,check=True)
box=os.environ.get('DOSBOX') or shutil.which('dosbox-x');assert box,'DOSBox-X is required'
for adapter,machine,options in [('vesa','svga_s3',''),('tseng','svga_et4000',' tseng')]:
 d=B/('test-'+adapter);shutil.rmtree(d,ignore_errors=True);d.mkdir()
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None;z.extractall(d)
 shutil.copyfile(B/'DISPLAY.EXE',d/'DISPLAY.EXE')
 commands=['DISPLAY'+options,'addkey p1200 enter','SHOWCASE'+(' /TSENG' if adapter=='tseng' else '')+' /START 32 /ONCE > ONCE.TXT','if errorlevel 1 echo FAIL>BAD.TXT','echo RETURNED>DONE.TXT','SHOWCASE /START 0 > INVALID.TXT','exit']
 config=d/'test.conf';config.write_text(f'[sdl]\noutput=surface\n[dosbox]\nmachine={machine}\n[cpu]\ncore=normal\ncputype=386\nfpu=false\ncycles=fixed 24000\n[mixer]\nnosound=true\n[autoexec]\nmount c {d}\nc:\n'+'\n'.join(commands)+'\n')
 subprocess.run([box,'-conf',str(config),'-noconsole'],env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120,check=True)
 assert (d/'PASS.TXT').exists(),(d/'DISPLAY.LOG').read_text();assert (d/'DONE.TXT').exists() and not (d/'BAD.TXT').read_text().strip()
 assert not (d/'ONCE.TXT').read_text().strip(),(d/'ONCE.TXT').read_text()
 print(adapter,':',(d/'PASS.TXT').read_text().strip())
print('PASS release ZIP, all 32 original GIF hashes, VESA and ET4000 framebuffer readback, CLI exit and text mode')
