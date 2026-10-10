#include "bsp.h"
#define USTATUS (*(volatile uint32_t *)0x10001008u)
#define UCONTROL (*(volatile uint32_t *)0x1000100cu)
static volatile uint8_t rx_queue[32];
static volatile uint32_t rx_head,rx_tail;
int putchar(int c) {
    while(!(USTATUS&1u)) {}
    *(volatile uint8_t *)0x10001000u=(uint8_t)c;
    return (uint8_t)c;
}
int puts(const char *s) { int n=0;while(*s){putchar(*s++);++n;}putchar('\n');return n+1; }
static int number(uint32_t n,unsigned base,unsigned width,int zero) {
    char buf[32];unsigned count=0;int out=0;
    do {unsigned d=n%base;buf[count++]=(char)(d<10?'0'+d:'A'+d-10);n/=base;}while(n);
    while(width>count){putchar(zero?'0':' ');--width;++out;}
    while(count){putchar(buf[--count]);++out;}return out;
}
int printf(const char *fmt,...) {
    va_list ap;va_start(ap,fmt);int n=0;
    while(*fmt) {
        if(*fmt!='%'){putchar(*fmt++);++n;continue;}
        ++fmt;unsigned width=0;int zero=*fmt=='0';
        while(*fmt>='0'&&*fmt<='9'){width=width*10u+(unsigned)(*fmt++-'0');if(width>32){va_end(ap);return -1;}}
        char c=*fmt;if(!c){va_end(ap);return -1;}++fmt;
        if(c=='s'){const char *s=va_arg(ap,const char*);if(!s)s="(null)";while(*s){putchar(*s++);++n;}}
        else if(c=='c'){putchar(va_arg(ap,int));++n;}
        else if(c=='%'){putchar('%');++n;}
        else if(c=='d'||c=='i'){int32_t v=va_arg(ap,int);uint32_t mag=(uint32_t)v;if(v<0){putchar('-');++n;mag=0u-mag;}n+=number(mag,10,width,zero);}
        else if(c=='u'||c=='x'||c=='X')n+=number(va_arg(ap,unsigned),c=='u'?10:16,width,zero);
        else {va_end(ap);return -1;}
    }
    va_end(ap);return n;
}
void uart_irq_service(void) {
    while(USTATUS&4u) {
        uint8_t c=*(volatile uint8_t *)0x10001004u;
        uint32_t next=(rx_head+1u)&31u;
        if(next!=rx_tail){rx_queue[rx_head]=c;rx_head=next;}
    }
}
int uart_getchar(void) {
    if(rx_tail!=rx_head){int c=rx_queue[rx_tail];rx_tail=(rx_tail+1u)&31u;return c;}
    if(!(USTATUS&(1u<<6))&&(USTATUS&4u))return *(volatile uint8_t *)0x10001004u;
    return -1;
}
void uart_irq_enable(void) {
    UCONTROL=0x100u;
    __asm__ volatile("li t0,2048\n.word 0x3042a073\n.word 0x30046073":::"t0","memory");
}
void uart_irq_disable(void) {
    __asm__ volatile(".word 0x30047073\n.word 0x30401073":::"memory");
    UCONTROL=0x200u;
}
