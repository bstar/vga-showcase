/* Test the actual renderer, reading back VRAM with independent bank selection. */
#define main showcase_main
#include "../src/showcase.c"
#undef main
#include <assert.h>
static unsigned char expected[800],actual[800];
static void read_pixels(unsigned long pos,unsigned count) {
 unsigned n=0,chunk,offset;unsigned long base=~0UL,next;union REGS r;
 while(count) {
  next=pos/65536UL;
  if(next!=base && width!=320) {
   if(backend==2)outp(0x3cd,(unsigned)next|((unsigned)next<<4));
   else {memset(&r,0,sizeof(r));r.w.ax=0x4f05;r.w.dx=(unsigned)(next*65536UL/(gran_kb*1024UL));int86(0x10,&r,&r);assert(r.w.ax==0x004f);}
   base=next;
  }
  offset=(unsigned)pos;chunk=(65536UL-offset)<count?(unsigned)(65536UL-offset):count;
  _fmemcpy(actual+n,MK_FP(0xa000,offset),chunk);n+=chunk;pos+=chunk;count-=chunk;
 }
}
int main(int argc,char **argv) {
 unsigned slide,y,x;unsigned char pal[768];char name[32];FILE *f,*out;
 void (__interrupt __far *clock)(void)=_dos_getvect(8);
 freopen("DISPLAY.LOG","w",stderr);backend=argc>1?2:0;
 for(slide=0;slide<COUNT;slide++) {
  assert(show(slide));sprintf(name,"PICS\\PIC%02u.SVI",slide+1);f=fopen(name,"rb");assert(f);
  assert(!fseek(f,16,SEEK_SET));assert(fread(pal,1,768,f)==768);
  outp(0x3c7,0);for(x=0;x<768;x++)assert((inp(0x3c9)&63)==pal[x]);
  for(y=0;y<height;y++) {
   assert(fread(expected,1,width,f)==width);read_pixels((unsigned long)y*width,width);
   assert(!memcmp(actual,expected,width));
  }
  fclose(f);
 }
 text_mode();assert(*((unsigned char far *)MK_FP(0x40,0x49))==3);assert(_dos_getvect(8)==clock);
 out=fopen("PASS.TXT","w");assert(out);fprintf(out,"PASS %u frames: all pixels and 768 DAC values; mode3 and IRQ restored\n",COUNT);fclose(out);return 0;
}
