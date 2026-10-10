#ifndef BSP_H
#define BSP_H
#include <stdint.h>
#include <stdarg.h>
#define BSP_CLOCK_HZ 93750000u
#define BSP_DATA_MAGIC 0x42da7a11u
extern volatile uint32_t bsp_data_magic,bsp_ecalls,bsp_irqs;
int putchar(int c);
int puts(const char *s);
int printf(const char *fmt,...);
int uart_getchar(void);
void uart_irq_enable(void);
void uart_irq_disable(void);
void uart_irq_service(void);
uint32_t timer_cycles(void);
void timer_delay_us(uint32_t us);
uint32_t crc32_update(uint32_t crc,const void *data,uint32_t size);
uint32_t crc32(const void *data,uint32_t size);
uint32_t trap_dispatch(uint32_t cause,uint32_t pc,uint32_t value,uint32_t *regs);
int bsp_trap_probe(void);
int bsp_check(void);
#endif
