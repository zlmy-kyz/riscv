#include "bsp.h"
int main(void) {
    if(!bsp_check()){printf("IRQ_FAIL bsp\r\n");return 1;}
    uart_irq_enable();
    unsigned n=0;int c;
    while(n<4){c=uart_getchar();if(c>=0){if(c!=(int)('1'+n)){printf("IRQ_FAIL order\r\n");return 1;}++n;}}
    uart_irq_disable();
    if(!bsp_irqs){printf("IRQ_FAIL missing\r\n");return 1;}
    puts("IRQ_PASS bytes=4");
    return 0;
}
