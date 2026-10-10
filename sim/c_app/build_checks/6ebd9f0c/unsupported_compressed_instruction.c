#include "bsp.h"
int main(void) { __asm__ volatile(".word 0x00010001"); return 0; }
