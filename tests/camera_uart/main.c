#include <stdint.h>
#include "crc32.h"
#define R32(a) (*(volatile uint32_t *)(a))
#define CAM 0x10002000u
#define STATUS R32(CAM+8)
#define CYCLE R32(0x10000008u)
#define HZ 93750000u
#define BASE 0x41000000u
#define BYTES 1843200u
#define PIXELS 921600u
#define BEATS 57600u
#define CHUNK 1024u
volatile uint32_t boot_cookie=0x43414d55u;
static uint8_t payload[CHUNK],header[32];
static uint32_t last_seq,last_crc,captures,exports;
static int valid;
static void putc_uart(uint8_t b) {
    while(!(R32(0x10001008u)&1u)){}
    *(volatile uint8_t *)0x10001000u=b;
}
static void text(const char *s){while(*s)putc_uart((uint8_t)*s++);}
static void hex(uint32_t v) {
    for(int i=7;i>=0;i--)putc_uart((uint8_t)"0123456789abcdef"[(v>>(i*4))&15u]);
}
static void dec(uint32_t v) {
    char buf[10];unsigned n=0;
    do{buf[n++]=(char)('0'+v%10u);v/=10u;}while(v);
    while(n)putc_uart((uint8_t)buf[--n]);
}
static void field(const char *key,uint32_t v){text(key);dec(v);}
static void hfield(const char *key,uint32_t v){text(key);hex(v);}
static void halt(void){for(;;){}}
static void fail(const char *why) __attribute__((noreturn));
static void fail(const char *why) {
    text("ERROR=");text(why);hfield(" STATUS=",STATUS);hfield(" CODE=",R32(CAM+28));
    hfield(" UART=",R32(0x10001008u));text("\n");R32(0x10000010u)=3;halt();__builtin_unreachable();
}
void camera_trap(uint32_t cause,uint32_t pc,uint32_t value) {
    hfield("TRAP_CAUSE=",cause);hfield(" PC=",pc);hfield(" TVAL=",value);text("\n");
    R32(0x10000010u)=3;halt();
}
static int getc_uart(uint32_t timeout) {
    uint32_t start=CYCLE;
    for(;;){
        uint32_t s=R32(0x10001008u);
        if(s&0x30u)fail("UART_RX");
        if(s&4u)return (int)(R32(0x10001004u)&255u);
        if(timeout && (uint32_t)(CYCLE-start)>=timeout)return -1;
    }
}
static void stable(void) {
    if((STATUS&31u)!=5u || R32(CAM+20)!=last_seq || R32(CAM+16)!=BYTES ||
       R32(CAM+24)!=PIXELS || R32(CAM+36)!=BEATS || R32(CAM+40)!=last_crc)
        fail("FRAME_CHANGED");
}
static void capture(void) {
    if(STATUS&2u)fail("ALREADY_BUSY");
    uint32_t before=R32(CAM+20),start=CYCLE;
    valid=0;R32(CAM+4)=1;
    for(;;){
        uint32_t s=STATUS;
        if(s&24u)fail("CAPTURE");
        if((s&6u)==4u)break;
        if((uint32_t)(CYCLE-start)>HZ*5u){R32(CAM+4)=2;fail("CAPTURE_TIMEOUT");}
    }
    if(R32(CAM+12)!=BASE || R32(CAM+16)!=BYTES || R32(CAM+24)!=PIXELS ||
       R32(CAM+36)!=BEATS || R32(CAM+20)!=before+1u)fail("METADATA");
    last_seq=R32(CAM+20);last_crc=R32(CAM+40);stable();
    field("FRAME=",last_seq);field(" PIXELS=",PIXELS);field(" BYTES=",BYTES);field(" WRITES=",BEATS);text("\n");
    uint32_t c=crc32_words((volatile const uint32_t *)BASE,BYTES/4u);stable();
    uint32_t again=crc32_words((volatile const uint32_t *)BASE,BYTES/4u);stable();
    hfield("CRC_CAPTURE=",last_crc);hfield(" CRC_CPU=",c);hfield(" CRC_REREAD=",again);text("\n");
    if(c!=last_crc || again!=c)fail("CRC_MISMATCH");
    text("REREAD=OK OVERFLOW=0 ERROR=0 CPU_CHECK=PASS\n");valid=1;captures++;
}
static void send_packet(uint32_t type,uint32_t offset,uint32_t length,uint32_t crc) {
    camera_header(header,type,last_seq,offset,length,BYTES,crc);
    for(unsigned i=0;i<32;i++)putc_uart(header[i]);
    for(uint32_t i=0;i<length;i++)putc_uart(payload[i]);
    if(getc_uart(HZ*5u)!='K')fail("EXPORT_ACK");
}
static void export_frame(void) {
    if(!valid)fail("NO_CHECKED_FRAME");
    stable();
    text("EXPORT_BEGIN\n");
    for(uint32_t off=0;off<BYTES;off+=CHUNK){
        for(uint32_t i=0;i<CHUNK;i+=4){
            uint32_t w=R32(BASE+off+i);
            payload[i]=(uint8_t)w;payload[i+1]=(uint8_t)(w>>8);
            payload[i+2]=(uint8_t)(w>>16);payload[i+3]=(uint8_t)(w>>24);
        }
        send_packet(1u,off,CHUNK,crc32_bytes(payload,CHUNK));
    }
    stable();send_packet(2u,BYTES,0,last_crc);exports++;
    field("EXPORT_DONE FRAME=",last_seq);text(" PC_ACK=1\n");
}
int main(void) {
    if(boot_cookie!=0x43414d55u)fail("DATA_INIT");
    R32(0x10000010u)=1;crc32_init();text("CAMERA_APP=1\n");
    if(R32(CAM)!=0x43414d01u)fail("CAMERA_MMIO_ID");
    uint32_t start=CYCLE;
    while(!(STATUS&1u)){
        if(STATUS&16u)fail("SCCB_CONFIG");
        if((uint32_t)(CYCLE-start)>HZ*5u)fail("CONFIG_TIMEOUT");
    }
    if((STATUS&26u) || R32(CAM+32)!=0x5640u)fail("SENSOR_STATUS_ID");
    hfield("SENSOR_ID=",R32(CAM+32));text(" CONFIG=OK\nCAMERA_READY\n");
    for(;;){
        int c=getc_uart(0);
        if(c=='C')capture();
        else if(c=='D')export_frame();
        else if(c=='Q'){
            if(!valid || !captures)fail("EMPTY_SESSION");
            field("SESSION_DONE CAPTURES=",captures);field(" EXPORTS=",exports);text(" CPU_CHECK=PASS\n");
            R32(0x10000010u)=2;halt();
        }else fail("COMMAND");
    }
}
