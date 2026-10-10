OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { PROGRAM (rwx) : ORIGIN = 0x40000000, LENGTH = 60K }
SECTIONS {
    .text : { KEEP(*(.text.startup)) *(.text .text.*) } > PROGRAM
    .rodata : { *(.rodata .rodata.* .srodata .srodata.*) } > PROGRAM
    .data : ALIGN(4) {
        __data_start = .; *(.data .data.* .sdata .sdata.*)
        . = ALIGN(4); __data_end = .;
    } > PROGRAM
    __global_pointer$ = __data_start + 0x800;
    .image_tail : { KEEP(*(.image_tail)) __file_end = .; } > PROGRAM
    .bss (NOLOAD) : ALIGN(4) {
        __bss_start = .; *(.bss .bss.* .sbss .sbss.*) *(COMMON)
        . = ALIGN(4); __bss_end = .;
    } > PROGRAM
    __stack_bottom = 0x4000F000;
    __stack_top = 0x40010000;
    ASSERT(__bss_end <= __stack_bottom, "Program/BSS overlaps reserved application stack")
    /DISCARD/ : { *(.comment) *(.eh_frame .eh_frame.*) }
}
