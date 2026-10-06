/* Preserve the original 100-byte arithmetic baseline independently of tests/development. */
int main(void)
{
    volatile int a = 10;
    volatile int b = 20;
    volatile int c = a + b;
    while (1) {}
    return 0;
}
