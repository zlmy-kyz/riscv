#include "crc32.h"
static uint32_t table[256];
void crc32_init(void) {
    for (uint32_t i=0;i<256;i++) {
        uint32_t c=i;
        for (unsigned bit=0;bit<8;bit++) c=(c>>1)^((c&1u)?0xedb88320u:0u);
        table[i]=c;
    }
}
uint32_t crc32_bytes(const uint8_t *p,uint32_t n) {
    uint32_t c=0xffffffffu;
    while(n--) c=(c>>8)^table[(c^*p++)&255u];
    return ~c;
}
uint32_t crc32_words(volatile const uint32_t *p,uint32_t words) {
    uint32_t c=0xffffffffu;
    while(words--) {
        uint32_t v=*p++; /* One uncached load per 32-bit frame word. */
        c=(c>>8)^table[(c^v)&255u];v>>=8;
        c=(c>>8)^table[(c^v)&255u];v>>=8;
        c=(c>>8)^table[(c^v)&255u];v>>=8;
        c=(c>>8)^table[(c^v)&255u];
    }
    return ~c;
}
static void le32(uint8_t *p,uint32_t v) {
    for(unsigned i=0;i<4;i++){p[i]=(uint8_t)v;v>>=8;}
}
void camera_header(uint8_t out[32],uint32_t type,uint32_t seq,uint32_t offset,
                   uint32_t length,uint32_t total,uint32_t crc) {
    out[0]='C';out[1]='A';out[2]='M';out[3]='1';
    le32(out+4,type);le32(out+8,seq);le32(out+12,offset);
    le32(out+16,length);le32(out+20,total);le32(out+24,crc);
    le32(out+28,crc32_bytes(out,28));
}
