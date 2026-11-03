#!/usr/bin/env python3
"""Create a ready-to-run DOS 8.3 ZIP, without installers or host files."""
import hashlib,re,subprocess,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'build/VGADEMO';D=R/'dist';D.mkdir(exist_ok=True)
def text(s):return s.replace('\r\n','\n').replace('\n','\r\n').encode('cp437')
files={n:(B/n).read_bytes() for n in ('SHOWCASE.EXE','DEMO.BAT','CIRRUS.BAT','TSENG.BAT','IMAGES.TXT','README.TXT')}
assert files['SHOWCASE.EXE'].startswith(b'MZ')
for i in range(1,33):
 for folder,ext in [('GIFS','GIF'),('PICS','SVI')]:
  n=f'{folder}/PIC{i:02}.{ext}';files[n]=(B/n).read_bytes()
files['LICENSE.TXT']=text((R/'LICENSE').read_text());files['CREDITS.TXT']=text((R/'CREDITS.md').read_text())
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();version=(R/'VERSION').read_text().strip()
files['VERSION.TXT']=text(f'VGA Showcase {version}\nSource: {commit}\nhttps://github.com/bstar/vga-showcase\n')
a=D/'VGADEMO.ZIP'
with zipfile.ZipFile(a,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,data in sorted(files.items()):
  assert all(re.fullmatch(r'[A-Z0-9_]{1,8}(\.[A-Z0-9_]{1,3})?',s) for s in name.split('/')),name
  info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.create_system=0;info.external_attr=0x20;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
digest=hashlib.sha256(a.read_bytes()).hexdigest();(D/'SHA256.TXT').write_bytes(text(f'{digest}  {a.name}\n'));print(a);print(digest)
