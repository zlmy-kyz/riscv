#include "bsp.h"
uint32_t timer_cycles(void) {return *(volatile uint32_t *)0x10000008u;}
void timer_delay_us(uint32_t us) {
    while(us) {
        uint32_t part=us>1000000u?1000000u:us;
        uint32_t ticks=(part/1000u)*93750u+((part%1000u)*93750u+999u)/1000u;
        uint32_t start=timer_cycles();
        while((uint32_t)(timer_cycles()-start)<ticks) {}
        us-=part;
    }
}
