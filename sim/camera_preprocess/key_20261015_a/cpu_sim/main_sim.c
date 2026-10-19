/* Preprocess key group, real-CPU simulation entry.
 * Shares the MMIO/CRC contract with the board program tests/camera_preprocess_uart
 * but is a separate fixed image: it does not export whole frames over UART and
 * does not recompute the CPU-side sampling reference (that is verified offline).
 * Difference is recorded in the sealed manifest.
 */
#include <stdint.h>
#include "expect.h"
#define CAM  0x10002000u
#define PP   0x10003000u
#define SIMC 0x10000000u
#define CYCL  0x10000008u
#define HZ   93750000u
#define OUT_BASE 0x42000000u
#define OUT_WORDS 6912u
static inline uint32_t rd(uint32_t a){return *(volatile uint32_t *)a;}
static inline void wr(uint32_t a,uint32_t v){*(volatile uint32_t *)a=v;}
volatile uint32_t pp_boot_cookie=0x50503031u;
static uint32_t table[256],cpu_crc,stores;
static void halt(void) __attribute__((noreturn));
static void halt(void){for(;;){}}
static void fail(const char *why) __attribute__((noreturn));
static void fail(const char *why){
    /* SIMC telemetry: high nibble 0xf, low byte = reason index. */
    wr(SIMC,0xf0000000u|(uint32_t)(why[0])|((uint32_t)(why[1])<<8));
    wr(SIMC,0xe0000000u|rd(PP+8));wr(SIMC,0xe1000000u|rd(PP+36));
    wr(SIMC,0xe2000000u|rd(PP+40));wr(SIMC,0xe3000000u|rd(PP+44));
    wr(SIMC,0xe4000000u|rd(CAM+8));wr(SIMC,0xe5000000u|cpu_crc);
    wr(0x10000010u,3);halt();
}
void camera_trap(uint32_t cause,uint32_t pc,uint32_t value){
    wr(SIMC,0xf1000000u|cause);wr(SIMC,0xf2000000u|pc);wr(SIMC,0xf3000000u|value);
    fail("TRAP");
}
static uint32_t cam_state(uint32_t b){return (rd(CAM+48)>>(2*b))&3u;}
static uint32_t deadline;
static void wait_ready(uint32_t b){
    deadline=rd(CYCL)+5u*HZ;
    while(cam_state(b)!=2u){ if((int32_t)(rd(CYCL)-deadline)>=0) fail("RDYTO"); }
}
static void wait_pp_done(void){
    deadline=rd(CYCL)+5u*HZ;
    while(!(rd(PP+8)&2u)){
        if(rd(PP+8)&4u)fail("PPERR");
        if((int32_t)(rd(CYCL)-deadline)>=0)fail("PPTMO");
        /* Ordinary CPU DDR traffic overlapping the preprocess job. */
        wr(0x4001c000u,(uint32_t)(stores*0x01010101u)|0x5a000000u);
        if((stores&15u)==0) (void)rd(0x40020000u+((stores&63u)<<2));
        stores++;
    }
}
static uint32_t crc_words(uint32_t base,uint32_t n,uint32_t *w0,uint32_t *wn){
    uint32_t c=0xffffffffu;uint32_t first=0,last=0;
    for(uint32_t i=0;i<n;i++){
        uint32_t v=rd(base+4u*i),t=v;
        if(i==0)first=v;
        if(i==n-1)last=v;
        for(unsigned j=0;j<4;j++){c=(c>>8)^table[(c^t)&255u];t>>=8;}
    }
    *w0=first;*wn=last;return ~c;
}
int main(void){
    if(pp_boot_cookie!=0x50503031u)fail("DATA");
    wr(0x10000010u,1);
    for(unsigned i=0;i<256;i++){uint32_t c=i;for(unsigned j=0;j<8;j++)c=(c>>1)^((c&1u)?0xedb88320u:0);table[i]=c;}
    if(rd(PP)!=0x50525001u)fail("PPID");
    for(unsigned job=0;job<PP_NJOBS;job++){
        uint32_t buf=pp_buf[job];
        wr(SIMC,0xc0000000u|(job*16u+buf));
        wait_ready(buf);
        wr(CAM+44,buf);
        uint32_t seq=rd(CAM+20);
        wr(CAM+56,seq);wr(CAM+4,32u);
        if(cam_state(buf)!=3u)fail("CLAIM");
        wr(PP+12,buf);wr(PP+16,seq);wr(PP+4,1u);
        wait_pp_done();
        if(rd(PP+20)!=seq || rd(PP+60)!=buf || rd(PP+24)!=OUT_BASE || rd(PP+28)!=27648u ||
           rd(PP+56)!=0x00600060u || rd(PP+40)!=9216u || rd(PP+44)!=864u || rd(PP+48)!=27648u ||
           rd(PP+36)!=0u)fail("PPMETA");
        uint32_t w0,wn;
        cpu_crc=crc_words(OUT_BASE,OUT_WORDS,&w0,&wn);
        if(cpu_crc!=pp_crc[job] || rd(PP+32)!=pp_crc[job])fail("CRC");
        if(w0!=pp_word0[job] || wn!=pp_wordN[job])fail("EDGE");
        uint32_t r0,rn;
        if(crc_words(OUT_BASE,OUT_WORDS,&r0,&rn)!=cpu_crc || r0!=w0 || rn!=wn)fail("REREAD");
        wr(SIMC,cpu_crc);wr(SIMC,0xd0000000u|(buf<<16)|seq);
        wr(CAM+44,buf);wr(CAM+56,seq);wr(CAM+4,64u);
        if(cam_state(buf)==3u)fail("RELEASE");
    }
    wr(SIMC,0xb0000000u|stores);wr(SIMC,0xc0000000u|0xFFu);
    wr(0x10000010u,2);halt();
}
