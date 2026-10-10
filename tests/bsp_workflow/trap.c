#include "bsp.h"
volatile uint32_t bsp_data_magic=BSP_DATA_MAGIC;
volatile uint32_t bsp_ecalls,bsp_irqs;
uint32_t trap_dispatch(uint32_t cause,uint32_t pc,uint32_t value,uint32_t *regs) {
    (void)regs;
    if(cause==11u){++bsp_ecalls;return pc+4u;}
    if(cause==0x8000000bu){++bsp_irqs;uart_irq_service();return pc;}
    printf("TRAP_FAIL cause=%08X pc=%08X value=%08X\r\n",cause,pc,value);
    for(;;) {}
}
int bsp_check(void) {
    if(bsp_data_magic!=BSP_DATA_MAGIC||bsp_ecalls||bsp_irqs)return 0;
    if(!bsp_trap_probe()||bsp_ecalls!=1u)return 0;
    uint32_t start=timer_cycles();timer_delay_us(10u);
    return (uint32_t)(timer_cycles()-start)>=938u;
}
