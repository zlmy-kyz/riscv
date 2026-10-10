#include <stdint.h>
volatile uint32_t app_data[32] = {
    1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
    17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32
};
volatile uint32_t app_bss[32];
const uint8_t image_tail[3] __attribute__((section(".image_tail"),used))={0x7e,0x53,0x32};
static void print(const char *s) {
    while(*s) {
        while(!(*(volatile uint32_t*)0x10001008u&1u)) {}
        *(volatile uint8_t*)0x10001000u=(uint8_t)*s++;
    }
}
int main(void) {
    uint32_t bad=0,sum=0;
    for(unsigned i=0;i<32;++i)bad|=app_bss[i];
    for(unsigned i=0;i<32;++i) {
        if(app_data[i]!=i+1)bad|=1;
        app_bss[i]=app_data[i]*app_data[i];sum+=app_bss[i];
    }
    print(!bad && sum==11440u ? "SECOND_PROGRAM_PASS sum=11440\r\n" : "SECOND_PROGRAM_FAIL\r\n");
    return 0;
}
