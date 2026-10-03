/* SPDX-License-Identifier: MIT */
OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS
{
	. = 0x200;
	.text : { KEEP(*(.text.init)) *(.text*) }
	/DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
