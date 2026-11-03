/* Real-mode DOS VGA/SVGA slideshow. Build with Open Watcom. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <conio.h>
#include <dos.h>
#include <i86.h>

#define COUNT 32
#define DAY_TICKS 0x1800B0UL
#define HOLD_TICKS 182UL

static unsigned char palette[768], row[800], info[256];
static unsigned char black[768];
static unsigned int width, height, pitch, segment, window_kb, gran_kb;
static unsigned long bank_base;
static int backend; /* 0 = VESA, 1 = Cirrus GD54xx, 2 = Tseng ET4000 */
static int graphics;

static unsigned int word_at(unsigned char *p) {
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}

static void bios_mode(unsigned int mode) {
    union REGS r;
    memset(&r, 0, sizeof(r));
    r.w.ax = mode;
    int86(0x10, &r, &r);
}

static void text_mode(void) {
    if (graphics) bios_mode(3);
    graphics = 0;
}

static void dac(unsigned char *p) {
    unsigned int n;
    outp(0x3C8, 0);
    for (n = 0; n < 768; ++n) outp(0x3C9, p[n]);
}

static unsigned long ticks(void) {
    union REGS r;
    memset(&r, 0, sizeof(r));
    int86(0x1A, &r, &r);
    return ((unsigned long)r.w.cx << 16) | r.w.dx;
}

static unsigned long elapsed(unsigned long from, unsigned long to) {
    return to >= from ? to - from : DAY_TICKS - from + to;
}

static int set_mode(unsigned int code) {
    union REGS r;
    struct SREGS s;
    unsigned int mode;
    segment = 0xA000;
    window_kb = 64;
    gran_kb = 64;
    bank_base = ~0UL;
    if (code == 0x13) {
        if (width != 320 || height != 200) return 0;
        bios_mode(0x13);
        pitch = 320;
    } else if (backend == 1) {
        /* BIOS modes and GR9 bank register from the GD54xx programming model. */
        mode = code == 0x101 ? 0x5F : 0x5C;
        bios_mode(mode);
        outp(0x3CE, 0x0B);
        outp(0x3CF, inp(0x3CF) & ~0x20); /* 4 KiB bank units */
        pitch = width;
        window_kb = 16;
        gran_kb = 4;
    } else if (backend == 2) {
        bios_mode(code == 0x101 ? 0x2E : 0x30);
        pitch = width;
    } else {
        memset(info, 0, sizeof(info));
        memset(&r, 0, sizeof(r));
        segread(&s);
        s.es = FP_SEG(info);
        r.w.di = FP_OFF(info);
        r.w.ax = 0x4F01;
        r.w.cx = code;
        int86x(0x10, &r, &r, &s);
        if (r.w.ax != 0x004F || (word_at(info) & 0x19) != 0x19 ||
            (info[2] & 5) != 5 || info[25] != 8 || info[27] != 4 ||
            word_at(info + 18) != width || word_at(info + 20) != height)
            return 0;
        gran_kb = word_at(info + 4);
        window_kb = word_at(info + 6);
        segment = word_at(info + 8);
        pitch = word_at(info + 16);
        if (!gran_kb || !window_kb || window_kb > 64 ||
            window_kb < gran_kb || window_kb % gran_kb ||
            pitch < width || !segment) return 0;
        memset(&r, 0, sizeof(r));
        r.w.ax = 0x4F02;
        r.w.bx = code; /* banked mode, no linear framebuffer */
        int86(0x10, &r, &r);
        if (r.w.ax != 0x004F) return 0;
    }
    graphics = 1;
    dac(black);
    return 1;
}

static int select_bank(unsigned long base) {
    union REGS r;
    unsigned int bank;
    if (base == bank_base) return 1;
    if (width == 320 && height == 200) {
        if (base) return 0;
    } else if (backend == 1) {
        bank = (unsigned int)(base / 4096UL);
        outp(0x3CE, 9);
        outp(0x3CF, bank);
    } else if (backend == 2) {
        bank = (unsigned int)(base / 65536UL);
        outp(0x3CD, bank | (bank << 4));
    } else {
        memset(&r, 0, sizeof(r));
        r.w.ax = 0x4F05;
        r.w.dx = (unsigned int)(base / ((unsigned long)gran_kb * 1024UL));
        int86(0x10, &r, &r);
        if (r.w.ax != 0x004F) return 0;
    }
    bank_base = base;
    return 1;
}

static int blit_row(unsigned long pos) {
    unsigned int count = width, offset = 0, chunk, in_window;
    unsigned long span = (unsigned long)window_kb * 1024UL, base, avail;
    while (count) {
        base = pos / span * span;
        if (!select_bank(base)) return 0;
        in_window = (unsigned int)(pos - base);
        avail = span - (pos - base);
        chunk = avail < count ? (unsigned int)avail : count;
        _fmemcpy(MK_FP(segment, in_window), row + offset, chunk);
        count -= chunk;
        offset += chunk;
        pos += chunk;
    }
    return 1;
}

static int show(unsigned int slide) {
    char path[24];
    unsigned char header[16];
    unsigned int mode, y;
    FILE *f;
    sprintf(path, "PICS\\PIC%02u.SVI", slide + 1);
    f = fopen(path, "rb");
    if (!f) return 0;
    if (fread(header, 1, 16, f) != 16 || memcmp(header, "SVI1", 4)) {
        fclose(f);
        return 0;
    }
    width = word_at(header + 4);
    height = word_at(header + 6);
    mode = word_at(header + 8);
    if ((mode != 0x13 && mode != 0x101 && mode != 0x103) ||
        (mode == 0x101 && (width != 640 || height != 480)) ||
        (mode == 0x103 && (width != 800 || height != 600)) ||
        fread(palette, 1, 768, f) != 768 || !set_mode(mode)) {
        fclose(f);
        return 0;
    }
    for (y = 0; y < height; ++y) {
        if (fread(row, 1, width, f) != width ||
            !blit_row((unsigned long)y * pitch)) {
            fclose(f);
            return 0;
        }
    }
    fclose(f);
    dac(palette);
    return 1;
}

int main(int argc, char **argv) {
    unsigned int slide = 0;
    int i, key, paused = 0, one_pass = 0;
    unsigned long before, now, remaining;
    for (i = 1; i < argc; ++i) {
        if (!stricmp(argv[i], "/CIRRUS")) backend = 1;
        else if (!stricmp(argv[i], "/TSENG")) backend = 2;
        else if (!stricmp(argv[i], "/ONCE")) one_pass = 1;
        else if (!stricmp(argv[i], "/START") && i + 1 < argc) {
            slide = (unsigned int)atoi(argv[++i]);
            if (slide < 1 || slide > COUNT) return 1;
            --slide;
        } else {
            puts("SVGA showcase: SHOWCASE [/CIRRUS | /TSENG] [/START 1..32] [/ONCE]");
            puts("Default: VESA BIOS. Space: pause/resume. Arrows/Enter: browse. Esc: exit.");
            return 1;
        }
    }
    while (1) {
        if (!show(slide)) {
            text_mode();
            printf("Cannot display slide %u. Run from the VGADEMO directory.\n", slide + 1);
            puts("SVGA requires VESA support, or CIRRUS.BAT (GD54xx), or TSENG.BAT (ET4000).");
            return 1;
        }
        remaining = HOLD_TICKS;
        before = ticks();
        while (remaining || paused) {
            if (kbhit()) {
                key = getch();
                if (key == 27) { text_mode(); return 0; }
                if (key == 32) paused = !paused;
                else if (key == 13) break;
                else if (!key || key == 0xE0) {
                    key = getch();
                    if (key == 77) break;
                    if (key == 75) {
                        slide = (slide + COUNT - 2) % COUNT;
                        break;
                    }
                }
                before = ticks();
            }
            now = ticks();
            if (!paused) {
                unsigned long dt = elapsed(before, now);
                remaining = dt < remaining ? remaining - dt : 0;
            }
            before = now;
            delay(5);
        }
        paused = 0;
        if (++slide == COUNT) {
            if (one_pass) { text_mode(); return 0; }
            slide = 0;
        }
    }
}
