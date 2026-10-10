#include "bsp.h"
volatile unsigned custom __attribute__((section(".other")))=7; int main(void) { return custom; }
