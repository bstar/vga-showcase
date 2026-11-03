# Display data and backends

An SVI file starts with a 16-byte little-endian header: `SVI1`, width (u16),
height (u16), BIOS/VESA mode (u16), and six reserved bytes. A 768-byte RGB palette
follows, with each channel in 0..63. Remaining bytes are row-major pixel indices.

`tools/prepare.py` verifies source GIF hashes, decodes the first frame without
palette quantization, centers it in the smallest supported mode, and checks the
result against every original pixel at VGA DAC precision. Borders use black
when an unused palette entry is available, otherwise the darkest existing color.

The player uses one 800-byte row buffer and banked real-mode accesses. Standard
VGA uses BIOS mode 13h. VESA uses modes 101h/103h, validates mode attributes and
window parameters, and selects windows with function 4F05h. The GD54xx backend
uses BIOS modes 5Fh/5Ch and GR9 with 4 KiB bank units. ET4000 uses modes 2Eh/30h
and the segment register at port 3CDh. Native backends must match the hardware;
they are selected explicitly, not auto-detected.

The ten-second hold starts after the image finishes loading; disk access and
monitor mode changes add transition time. Space freezes the remaining hold
period. Left/right/Enter select the next image immediately. The player returns
to standard text mode on exit or a load error; it does not promise to preserve
a previous application's text screen.

Current automated tests use DOSBox-X VESA/S3 and ET4000 with a 386 and no FPU.
A test driver calls the actual renderer, independently selects read banks and
checks every displayed index and DAC value. It also checks text mode and the
unchanged timer vector. The ZIP's original GIF hashes and `/START 32 /ONCE`
exit are exercised. Earlier tests of the unchanged native Cirrus renderer used
QEMU's Cirrus device with FreeDOS and compared all 32 captured frames.
