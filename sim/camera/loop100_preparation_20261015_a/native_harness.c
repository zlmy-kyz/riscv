/* Native I/O fixture for the actual firmware source, never RTL or board evidence. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#define CAMERA_LOOP_NATIVE_TEST 1
#define main camera_loop_main
#include "../../../tests/camera_loop100/main.c"
#undef main
static uint8_t frames[2][BYTES];
static uint32_t golden[2],mode,seq,busy_left,arms,words,total_words,reading;
static uint64_t fake_cycle=0xfffffff0ull;
static uint32_t fstatus=1;
static unsigned pattern(void){return arms>50?1:0;}
static int injected(void){return arms==2;}
uint32_t test_read32(uint32_t a){
    if(a==0x10000008u){fake_cycle+=busy_left?40000000u:(reading?(mode==10&&injected()?10000000u:200000u):1000000u);return (uint32_t)fake_cycle;}
    if(a==0x10001008u)return 5;
    if(a==0x10001004u)return mode==12?'X':'G';
    if(a>=BASE && a<BASE+BYTES){
        assert((a-BASE)==4*words && !(a&3u) && fstatus==5);
        uint32_t o=a-BASE;const uint8_t *p=frames[pattern()]+o;words++;total_words++;reading=1;
        if(mode==9&&injected()&&words==1024)seq++;
        return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
    }
    if(a==CAM)return 0x43414d01;
    if(a==CAM+8){
        if(mode==11)return 16;
        if(busy_left){
            if(mode==1&&injected())return 17;
            if(mode==2&&injected())return 3;
            if(mode==8&&injected())return 7;
            if(--busy_left==0){fstatus=5;seq++;}else return 3;
        }
        return fstatus;
    }
    if(a==CAM+12)return BASE;
    if(a==CAM+16)return mode==4&&injected()?BYTES-32:BYTES;
    if(a==CAM+20)return mode==3&&injected()?seq+1:seq;
    if(a==CAM+24)return mode==5&&injected()?PIXELS-1:PIXELS;
    if(a==CAM+28)return mode==1&&injected()?2:0;
    if(a==CAM+32)return 0x5640;
    if(a==CAM+36)return mode==6&&injected()?BEATS-1:BEATS;
    if(a==CAM+40)return golden[pattern()]^(mode==7&&injected()?1u:0u);
    assert(0);return 0;
}
void test_write32(uint32_t a,uint32_t v){
    if(a==0x10001000u){putchar((int)v);return;}
    if(a==0x10000010u)return;
    assert(a==CAM+4 && v==1 && arms<100 && (!arms||words==BYTES/4));
    arms++;words=0;reading=0;busy_left=4;fstatus=3;
    if(mode==13&&injected()){busy_left=0;fstatus=5;seq++;}
}
void test_halt(void){fprintf(stderr,"ARMS=%u FRAME_WORDS=%u TOTAL_WORDS=%u FAKE_CYCLES_HI=%u LO=%u\n",arms,words,total_words,(uint32_t)(fake_cycle>>32),(uint32_t)fake_cycle);exit(0);}
int main(int argc,char **argv){
    assert(argc==7);mode=(uint32_t)strtoul(argv[1],0,0);seq=(uint32_t)strtoul(argv[2],0,0);
    for(unsigned i=0;i<2;i++){FILE *f=fopen(argv[3+i],"rb");assert(f);assert(fread(frames[i],1,BYTES,f)==BYTES);assert(fgetc(f)==EOF);fclose(f);golden[i]=(uint32_t)strtoul(argv[5+i],0,16);}
    return camera_loop_main();
}
