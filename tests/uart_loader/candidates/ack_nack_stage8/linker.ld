OUTPUT_ARCH(riscv)
ENTRY(_start)
/* Harvard ROM and RAM have overlapping CPU VMAs, but different buses.
   Build with --no-check-sections; audit and extract each bus separately. */
MEMORY {
    ROM (rx) : ORIGIN = 0, LENGTH = 16K
    DIAG (rw) : ORIGIN = 0x20, LENGTH = 0xE0
    CONST (r) : ORIGIN = 0x100, LENGTH = 0xF00
    STATE (rw) : ORIGIN = 0x1000, LENGTH = 4K
    BUFFER (rw) : ORIGIN = 0x2000, LENGTH = 4K
}
PHDRS { rom PT_LOAD FLAGS(5); ram PT_LOAD FLAGS(6); }
SECTIONS {
    .text : { KEEP(*(.text.startup)) *(.text .text.*) . = ALIGN(4); } > ROM :rom
    .diagnostics (NOLOAD) : { KEEP(*(.diagnostics)) } > DIAG :NONE
    .rodata : { *(.rodata .rodata.* .srodata .srodata.*) . = ALIGN(4); } > CONST :ram
    .data : { *(.data .data.* .sdata .sdata.*) } > STATE :ram
    .bss (NOLOAD) : ALIGN(4) {
        __bss_start = .;
        *(.bss .bss.* .sbss .sbss.*) *(COMMON)
        . = ALIGN(4); __bss_end = .;
    } > STATE :ram
    .rx_buffer (NOLOAD) : ALIGN(4) { KEEP(*(.rx_buffer)) } > BUFFER :NONE
    __global_pointer$ = 0x1800;
    __stack_bottom = 0x3000;
    __stack_top = 0x3FF0;
    ASSERT(SIZEOF(.text) <= 0x4000, "Loader ROM exceeds 16 KiB")
    ASSERT(SIZEOF(.data) == 0, "Mutable initialized data requires a reset restore path")
    ASSERT(ADDR(.rodata) + SIZEOF(.rodata) <= 0x1000, "RAM constants exceed partition")
    ASSERT(__bss_end <= 0x2000, "Loader state exceeds partition")
    ASSERT(ADDR(.rx_buffer) + SIZEOF(.rx_buffer) <= 0x3000, "RX buffer overlaps stack")
    /DISCARD/ : { *(.comment) *(.eh_frame .eh_frame.*) *(.note.GNU-stack) }
}
