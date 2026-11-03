#!/usr/bin/env python3
"""Prepare lossless indexed display data; keep the archived GIFs unchanged."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "build/VGADEMO"


def dos_text(path, text):
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("cp437"))


def main():
    for folder in (OUT, OUT / "PICS", OUT / "GIFS"):
        folder.mkdir(parents=True, exist_ok=True)
    slides = []
    for entry in json.loads((ROOT / "images/sources.json").read_text()):
        original = ROOT / "images" / entry["name"]
        if hashlib.sha256(original.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Source image checksum mismatch: " + entry["name"])
        width, height = map(int, entry["size"].split("x"))
        if (width, height) == (320, 200):
            screen_w, screen_h, mode = 320, 200, 0x13
        elif width <= 640 and height <= 480:
            screen_w, screen_h, mode = 640, 480, 0x101
        elif width <= 800 and height <= 600:
            screen_w, screen_h, mode = 800, 600, 0x103
        else:
            raise ValueError(f"Image exceeds 800x600: {original}")
        # Read actual colors, preserving every pixel and avoiding palette quantization.
        rgb = subprocess.check_output([
            "magick", str(original) + "[0]", "-alpha", "off", "-depth", "8", "RGB:-"
        ])
        assert len(rgb) == width * height * 3
        colors = list(dict.fromkeys(rgb[i:i+3] for i in range(0, len(rgb), 3)))
        assert len(colors) <= 256
        if b"\0\0\0" not in colors and len(colors) < 256:
            colors.append(b"\0\0\0")
        darkest = min(range(len(colors)), key=lambda n: sum(c*c for c in colors[n]))
        lookup = {color: i for i, color in enumerate(colors)}
        image = bytes(lookup[rgb[i:i+3]] for i in range(0, len(rgb), 3))
        pixels = bytearray([darkest]) * (screen_w * screen_h)
        left, top = (screen_w - width) // 2, (screen_h - height) // 2
        for y in range(height):
            dest = (top + y) * screen_w + left
            pixels[dest:dest+width] = image[y*width:(y+1)*width]
        palette = bytes(c >> 2 for color in colors for c in color)
        palette += bytes(768 - len(palette))
        number = entry["number"]
        stem = f"PIC{number:02}"
        header = struct.pack("<4sHHH6x", b"SVI1", screen_w, screen_h, mode)
        (OUT / "PICS" / (stem + ".SVI")).write_bytes(header + palette + pixels)
        shutil.copyfile(original, OUT / "GIFS" / (stem + ".GIF"))
        # Verify the prepared image against the original, allowing only VGA DAC precision.
        for y in range(height):
            for x in range(width):
                index = pixels[(top+y)*screen_w+left+x]
                expected = rgb[(y*width+x)*3:(y*width+x+1)*3]
                assert palette[index*3:index*3+3] == bytes(c >> 2 for c in expected)
        slides.append({
            **entry, "dos_name": stem, "screen": [screen_w, screen_h],
            "mode": hex(mode), "colors": len(set(image)),
            "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
            "display_sha256": hashlib.sha256((OUT / "PICS" / (stem + ".SVI")).read_bytes()).hexdigest()
        })
    (ROOT / "build/manifest.json").write_text(json.dumps(slides, indent=2) + "\n")
    for filename, command in [("DEMO.BAT", "SHOWCASE"),
                              ("CIRRUS.BAT", "SHOWCASE /CIRRUS"),
                              ("TSENG.BAT", "SHOWCASE /TSENG")]:
        dos_text(OUT / filename, "@ECHO OFF\n" + command + "\n")
    dos_text(OUT / "IMAGES.TXT", "EARLY GIF SHOWCASE - ORIGINAL IMAGE SOURCES\n\n" + "\n".join(
        f"{s['dos_name']}.GIF  {s['name']}  {s['size']}  {s['colors']} colors\n{s['url']}\n"
        for s in slides))
    dos_text(OUT / "README.TXT", """EARLY VGA / SVGA SHOWCASE
========================
32 archived GIF pictures, looping with a 10-second hold per image.

Run from this directory:
  DEMO       VGA plus VESA SVGA (standard choice)
  CIRRUS     VGA plus native Cirrus Logic GD54xx modes
  TSENG      VGA plus native Tseng ET4000 modes

Controls: Esc quits; Space pauses/resumes; Right/Enter advances;
Left goes back. SHOWCASE /START 17 starts at slide 17.
SHOWCASE /ONCE stops after one pass. Options can be combined.

Pictures use 320x200, 640x480, or 800x600 in 256-color modes.
All original pixels and colors are retained at the hardware's normal
6-bit-per-channel VGA DAC precision. Smaller pictures are centered.
There is no resizing, cropping, or reduction to a common 16-color palette.
Original GIF files are preserved byte-for-byte in GIFS. The player uses
predecoded, uncompressed PICS data for fast loading on a 386-class PC.
The 10-second hold begins after each picture finishes loading. Disk loads
and monitor mode changes add transition time between images.

SVGA modes require a compatible multisync monitor and enough video RAM
(512 KiB for 800x600x256). Native drivers target only the named chipsets.
No TSRs, startup changes, or memory manager changes are required.
DOS 3.0 or later. The new player is 16-bit real-mode code.

Code and build tools: MIT license, copyright 2026 bstar.
Source: https://github.com/bstar/vga-showcase
Archived artwork retains its original ownership. This is a recreation,
not a recovered copy of a particular manufacturer's demonstration disk.
See IMAGES.TXT for filenames and source URLs.
""")
    print(f"Prepared {len(slides)} slides with pixel/palette verification.")


if __name__ == "__main__":
    main()
