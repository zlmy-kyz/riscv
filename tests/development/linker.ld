OUTPUT_ARCH(riscv)
ENTRY(_start)

/* A standalone DDR program. A loader must populate its loadable sections. */
MEMORY
{
    DDR (rwx) : ORIGIN = 0x40000000, LENGTH = 64K
}

SECTIONS
{
    .text :
    {
        KEEP(*(.text.startup))
        *(.text .text.*)
    } > DDR

    .rodata :
    {
        *(.rodata .rodata.* .srodata .srodata.*)
    } > DDR

    .data : ALIGN(4)
    {
        __data_start = .;
        *(.data .data.* .sdata .sdata.*)
        . = ALIGN(4);
        __data_end = .;
    } > DDR
    __global_pointer$ = __data_start + 0x800;

    .bss (NOLOAD) : ALIGN(4)
    {
        __bss_start = .;
        *(.bss .bss.* .sbss .sbss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > DDR

    __stack_top = ORIGIN(DDR) + LENGTH(DDR);
    __stack_bottom = __stack_top - 4K;
    ASSERT(__bss_end <= __stack_bottom, "Program overlaps the reserved 4 KiB stack")

    /DISCARD/ : { *(.comment) *(.eh_frame .eh_frame.*) }
}
