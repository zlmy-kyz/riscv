#include "bsp.h"
static uint8_t bytes[256];
int main(void) {
    if(!bsp_check()){printf("CRC32_FAIL bsp\r\n");return 1;}
    for(unsigned i=0;i<256;++i)bytes[i]=(uint8_t)i;
    uint32_t vector=crc32("123456789",9),all=crc32(bytes,256);
    uint32_t split=crc32_update(0xffffffffu,bytes,73);
    split=crc32_update(split,bytes+73,183)^0xffffffffu;
    if(vector!=0xcbf43926u||all!=0x29058c73u||split!=all||crc32(bytes,0)!=0){printf("CRC32_FAIL algorithm\r\n");return 1;}
    printf("CRC32_PASS vector=%08X bytes256=%08X split=%08X\r\n",vector,all,split);
    return 0;
}
