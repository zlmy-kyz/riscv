#include "bsp.h"
volatile unsigned char huge[65000]; int main(void) { huge[64999]=1; return huge[0]; }
