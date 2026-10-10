#include "bsp.h"

int app_main(void);

int main(void) {
    if (!bsp_check()) {
        puts("C_APP_BSP_FAIL");
        return 1;
    }
    int result = app_main();
    printf("\nC_APP_DONE return=%d\n", result);
    return result;
}
