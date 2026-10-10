#include "bsp.h"
int main(void) {
    if(!bsp_check()){printf("HELLO_FAIL\r\n");return 1;}
    printf("Hello %s\r\n","World");
    printf("BSP_PASS signed=%d unsigned=%u hex=%08X char=%c %%\r\n",(-2147483647-1),4294967295u,0xa5u,'Q');
    return 0;
}
