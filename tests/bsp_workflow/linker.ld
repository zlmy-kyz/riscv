OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY {
    /* Existing Loader stays in separate Harvard ROM/RAM, not this BIN. */
    PROGRAM (rwx) : ORIGIN = 0x40000000, LENGTH = 60K
    STACK (rw) : ORIGIN = 0x4000F000, LENGTH = 4K
}
SECTIONS {
    .text : { KEEP(*(.text.startup)) *(.text .text.*) } > PROGRAM
    .rodata : { *(.rodata .rodata.* .srodata .srodata.*) } > PROGRAM
    .data : ALIGN(4) {
        __data_start = .; *(.data .data.* .sdata .sdata.*)
        . = ALIGN(4); __data_end = .;
    } > PROGRAM
    __data_load_start = LOADADDR(.data);
    __global_pointer$ = __data_start + 0x800;
    .bss (NOLOAD) : ALIGN(4) {
        __bss_start = .; *(.bss .bss.* .sbss .sbss.*) *(COMMON)
        . = ALIGN(4); __bss_end = .;
    } > PROGRAM
    __stack_bottom = ORIGIN(STACK);
    __stack_top = ORIGIN(STACK) + LENGTH(STACK);
    ASSERT(__bss_end <= __stack_bottom,"Application overlaps stack")
    /DISCARD/ : { *(.comment) *(.eh_frame .eh_frame.*) }
}
