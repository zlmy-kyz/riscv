#include "bsp.h"
int calculate(void);
static volatile unsigned numerator = 12345;
static volatile unsigned denominator = 17;
static volatile unsigned zero;
int main(void) {
    unsigned quotient = numerator / denominator;
    int result = calculate();
    if (quotient != 726 || result != 77 || zero != 0) return 3;
    printf("SECOND_AUTO_PASS sum=%d div=%u bss=%u\n", result, quotient, zero);
    return 0;
}
