#include "bsp.h"

static volatile unsigned value = 7;
static volatile unsigned zero;

int main(void) {
    if (value != 7 || zero != 0) return 1;
    unsigned sum = 0;
    for (unsigned i = 1; i <= 10; ++i) sum += i;
    printf("MY_PROGRAM_PASS sum=%u\n", sum);
    return sum == 55 ? 0 : 2;
}
