#include "bsp.h"
uint32_t crc32_update(uint32_t crc,const void *data,uint32_t size) {
    const uint8_t *p=data;
    while(size--){crc^=*p++;for(unsigned b=0;b<8;++b)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
    return crc;
}
uint32_t crc32(const void *data,uint32_t size){return crc32_update(0xffffffffu,data,size)^0xffffffffu;}
